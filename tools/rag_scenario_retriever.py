"""
RAG-based scenario enrichment for branch coverage.

Queries the GivenWhenThen dataset (via ChromaDB) for real-world error-case,
edge-case, and validation scenarios, then converts them into structured
TestScenario templates that the ScenarioDesigner can use.

This bridges the gap between Swagger-based happy-path generation and
the conditional-branch coverage needed for high branch-coverage scores.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from rag.retriever import query as rag_query


COMMON_DOMAIN_STOPWORDS = {
    "api", "test", "tests", "scenario", "feature", "request", "response", "valid",
    "invalid", "error", "case", "cases", "edge", "security", "happy", "path",
    "create", "update", "delete", "get", "post", "put", "patch", "when", "then",
    "given", "with", "without", "from", "into", "user", "users", "role", "roles",
}
FOREIGN_PROTOCOL_MARKERS = {
    "smtp", "imap", "mailbox", "inbox", "tls", "ssl", "email", "e-mail", "kafka",
    "rabbitmq", "redis", "ftp", "sftp", "ssh", "websocket",
}


def _clean_gherkin_step(text: str) -> str:
    """Normalize a Gherkin step for reuse in our pipeline."""
    text = re.sub(r"\s+", " ", text.strip())
    # Remove project-specific prefixes
    text = re.sub(r"^I (?:am |have |click |see |should )", "", text, flags=re.IGNORECASE)
    return text


def _extract_scenario_from_feature(feature_text: str, endpoint_hint: str = "") -> List[Dict[str, Any]]:
    """Parse raw feature text and extract individual scenarios."""
    scenarios: List[Dict[str, Any]] = []
    lines = feature_text.splitlines()
    current_scenario: Optional[Dict[str, Any]] = None
    current_keyword = "Given"

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.lower().startswith("scenario:") or stripped.lower().startswith("scenario outline:"):
            if current_scenario and current_scenario.get("steps"):
                scenarios.append(current_scenario)
            title = re.sub(r"(?i)^scenario(?: outline)?:\s*", "", stripped).strip()
            current_scenario = {
                "title": title,
                "steps": [],
                "type": "outline" if "outline" in stripped.lower() else "scenario",
            }
            current_keyword = "Given"
            continue

        if current_scenario is None:
            continue

        for kw in ("Given", "When", "Then", "And", "But"):
            if stripped.startswith(kw + " "):
                text = stripped[len(kw):].strip()
                eff = current_keyword if kw in ("And", "But") else kw
                if kw not in ("And", "But"):
                    current_keyword = kw
                current_scenario["steps"].append({"keyword": eff, "text": text})
                break

    if current_scenario and current_scenario.get("steps"):
        scenarios.append(current_scenario)

    return scenarios


def _keyword_tokens(text: str) -> set[str]:
    tokens = set()
    for raw in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", (text or "").lower()):
        token = raw.strip("_-")
        if token and token not in COMMON_DOMAIN_STOPWORDS:
            tokens.add(token)
    return tokens


def _endpoint_catalog_tokens(service_endpoints: List[Dict[str, Any]]) -> set[str]:
    tokens: set[str] = set()
    for endpoint in service_endpoints:
        parts = [
            endpoint.get("path", ""),
            endpoint.get("summary", ""),
            endpoint.get("operation_id", ""),
        ]
        for part in parts:
            tokens.update(_keyword_tokens(str(part)))
    return tokens


def _is_relevant_to_service(
    title: str,
    steps: List[Dict[str, str]],
    service_endpoints: List[Dict[str, Any]],
) -> bool:
    """Reject obviously unrelated scenarios before mapping them to our APIs."""
    combined = " ".join([title] + [s.get("text", "") for s in steps]).strip().lower()
    if not combined:
        return False

    # Hard reject foreign protocol / messaging scenarios unless they also
    # clearly reference one of our REST API paths.
    if any(marker in combined for marker in FOREIGN_PROTOCOL_MARKERS) and "/api/" not in combined:
        return False

    # If the scenario already references one of our API paths, keep it.
    mentioned_paths = re.findall(r"(/api/[a-zA-Z0-9/_\-{}]+)", combined)
    known_paths = {str(ep.get("path", "")).lower() for ep in service_endpoints}
    for path in mentioned_paths:
        if path.lower() in known_paths:
            return True

    scenario_tokens = _keyword_tokens(combined)
    endpoint_tokens = _endpoint_catalog_tokens(service_endpoints)
    overlap = scenario_tokens & endpoint_tokens

    # Require a meaningful keyword overlap to avoid pulling in unrelated
    # examples that happen to contain generic QA words.
    return len(overlap) >= 2


def _classify_scenario_type(title: str, steps: List[Dict[str, str]]) -> str:
    """Classify a retrieved scenario as happy_path, error_case, edge_case, or security."""
    title_lower = title.lower()
    step_text = " ".join(s["text"].lower() for s in steps)
    combined = title_lower + " " + step_text

    error_markers = [
        "error", "invalid", "missing", "reject", "fail", "unauthorized",
        "forbidden", "not found", "bad request", "403", "401", "404",
        "400", "cannot", "unable", "not allowed", "denied", "expired",
        "wrong", "duplicate", "already exists", "does not exist",
    ]
    edge_markers = [
        "boundary", "edge", "limit", "maximum", "minimum", "empty",
        "null", "zero", "negative", "extreme", "too long", "too short",
        "max length", "min length", "overflow", "underflow",
    ]
    security_markers = [
        "security", "injection", "sql injection", "xss", "csrf",
        "authentication", "authorization", "token", "jwt", "credential",
        "session", "privilege", "permission", "role",
    ]

    if any(m in combined for m in security_markers):
        return "security"
    if any(m in combined for m in error_markers):
        return "error_case"
    if any(m in combined for m in edge_markers):
        return "edge_case"
    return "happy_path"


def _map_to_endpoint(steps: List[Dict[str, str]], service_endpoints: List[Dict[str, Any]]) -> Optional[Tuple[str, str]]:
    """Try to match a retrieved scenario to one of our service endpoints."""
    step_text = " ".join(s["text"].lower() for s in steps)

    # Direct method+path mentions
    method_match = re.search(r"\b(get|post|put|patch|delete)\b", step_text)
    method = method_match.group(1).upper() if method_match else ""

    path_match = re.search(r"(/api/[a-zA-Z0-9/_\-{}]+)", step_text)
    path = path_match.group(1) if path_match else ""

    if method and path:
        for ep in service_endpoints:
            if ep["method"] == method and path in ep["path"]:
                return method, ep["path"]

    # Keyword matching
    keyword_scores: List[Tuple[int, Dict[str, Any]]] = []
    for ep in service_endpoints:
        score = 0
        path_lower = ep["path"].lower()
        summary_lower = ep.get("summary", "").lower()
        op_id_lower = ep.get("operation_id", "").lower()
        haystack = f"{path_lower} {summary_lower} {op_id_lower}"

        if "login" in step_text and "/login" in path_lower:
            score += 20
        if "register" in step_text and ("register" in haystack or "signup" in haystack):
            score += 15
        if "create" in step_text and ep["method"] == "POST":
            score += 10
        if "update" in step_text and ep["method"] in ("PUT", "PATCH"):
            score += 10
        if "delete" in step_text and ep["method"] == "DELETE":
            score += 10
        if "search" in step_text and ep["method"] == "GET":
            score += 8
        if "approve" in step_text and "/approve" in path_lower:
            score += 15
        if "reject" in step_text and "/reject" in path_lower:
            score += 15
        if "cancel" in step_text and "/cancel" in path_lower:
            score += 15
        if "balance" in step_text and "/balance" in path_lower:
            score += 12

        if score > 0:
            keyword_scores.append((score, ep))

    if keyword_scores:
        keyword_scores.sort(key=lambda x: -x[0])
        best = keyword_scores[0][1]
        return best["method"], best["path"]

    return None


def retrieve_branch_targeting_scenarios(
    service_name: str,
    service_endpoints: List[Dict[str, Any]],
    coverage_feedback: Optional[Dict[str, Any]] = None,
    k_per_query: int = 5,
) -> List[Dict[str, Any]]:
    """
    Query RAG for real-world scenarios that target branches (error/edge/security).

    Returns a list of scenario dicts ready for ScenarioDesigner to convert
    into TestScenario objects.
    """
    scenarios: List[Dict[str, Any]] = []
    seen_titles: set = set()

    # Build targeted queries based on weak coverage areas
    queries: List[str] = []

    if coverage_feedback:
        weak_classes = coverage_feedback.get("weak_classes") or []
        weak_packages = coverage_feedback.get("weak_packages") or []
        for wc in weak_classes[:3]:
            class_name = wc.get("class", "")
            pkg = wc.get("package", "")
            queries.append(f"API validation error test for {pkg}.{class_name}")
            queries.append(f"boundary value test {class_name} API")
        for wp in weak_packages[:3]:
            pkg = wp.get("package", "")
            queries.append(f"API error handling test {pkg}")
            queries.append(f"invalid payload test {pkg}")

    # Always add generic branch-targeting queries
    queries.extend([
        "API test invalid input validation error scenario",
        "API test boundary value edge case scenario",
        "API test unauthorized access security scenario",
        "API test null empty payload rejection scenario",
        "API test duplicate conflict error scenario",
        "API test missing required field validation",
        "API test expired token authentication failure",
        "API test bad request malformed JSON scenario",
    ])

    # Deduplicate queries
    queries = list(dict.fromkeys(queries))

    for q in queries:
        try:
            chunks = rag_query(q, k=k_per_query)
        except Exception as exc:
            logger.debug(f"RAG query failed for '{q}': {exc}")
            continue

        for chunk in chunks:
            content = chunk.content or ""
            if not content:
                continue

            # Only process feature-type content
            if "Feature:" not in content and "Scenario" not in content:
                continue

            extracted = _extract_scenario_from_feature(content)
            for ex in extracted:
                title = ex.get("title", "")
                if not title or title in seen_titles:
                    continue
                if not _is_relevant_to_service(title, ex.get("steps", []), service_endpoints):
                    continue
                seen_titles.add(title)

                test_type = _classify_scenario_type(title, ex.get("steps", []))
                # Skip happy_path — we already generate plenty of those
                if test_type == "happy_path":
                    continue

                endpoint_match = _map_to_endpoint(ex.get("steps", []), service_endpoints)
                if endpoint_match is None:
                    continue

                method, endpoint = endpoint_match

                # Build Given/When/Then from steps
                given_steps = [s["text"] for s in ex["steps"] if s["keyword"] == "Given"]
                when_steps = [s["text"] for s in ex["steps"] if s["keyword"] == "When"]
                then_steps = [s["text"] for s in ex["steps"] if s["keyword"] == "Then"]

                given = "; ".join(given_steps) if given_steps else f"Preconditions for {title}"
                when = "; ".join(when_steps) if when_steps else f"{method} {endpoint} executed"
                then = "; ".join(then_steps) if then_steps else "Returns appropriate response"

                scenarios.append({
                    "title": f"[RAG-{test_type.upper()}] {title}",
                    "endpoint": endpoint,
                    "method": method,
                    "given": given,
                    "when": when,
                    "then": then,
                    "test_type": test_type,
                    "priority": "P0" if test_type in ("error_case", "security") else "P1",
                    "service": service_name,
                    "is_integration": False,
                    "source": chunk.source,
                })

    logger.info(
        f"RAG enrichment found {len(scenarios)} branch-targeting scenarios "
        f"for {service_name}"
    )
    return scenarios


def build_rag_prompt_examples(
    service_name: str,
    endpoint_catalog: List[Dict[str, Any]],
    k: int = 3,
) -> str:
    """
    Build a prompt block with real-world error/edge-case examples from RAG.
    This is injected into the LLM prompt in scenario_designer.py.
    """
    examples: List[str] = []

    query_templates = [
        f"API validation error {service_name}",
        f"API boundary test {service_name}",
        f"API unauthorized access test",
        f"API invalid payload rejection",
    ]

    for q in query_templates:
        try:
            chunks = rag_query(q, k=k)
        except Exception:
            continue
        for chunk in chunks:
            content = chunk.content or ""
            if "Scenario" in content and ("error" in content.lower() or "invalid" in content.lower()):
                extracted = _extract_scenario_from_feature(content)
                for ex in extracted:
                    if not _is_relevant_to_service(
                        ex.get("title", ""),
                        ex.get("steps", []),
                        endpoint_catalog,
                    ):
                        continue
                    scenario_lines = [f"Scenario: {ex.get('title', '').strip()}"]
                    for step in ex.get("steps", []):
                        keyword = step.get("keyword", "").strip() or "Given"
                        text = step.get("text", "").strip()
                        if text:
                            scenario_lines.append(f"{keyword} {text}")
                    if scenario_lines:
                        examples.append("\n".join(scenario_lines[:15]))
                    if len(examples) >= 6:
                        break
                if len(examples) >= 6:
                    break
        if len(examples) >= 6:
            break

    if not examples:
        return ""

    return (
        "REAL-WORLD ERROR/EDGE CASE EXAMPLES (from production test suites):\n"
        + "\n---\n".join(examples[:6])
        + "\n\nUse these patterns as inspiration for generating validation, "
        "boundary, and error scenarios.\n"
    )

