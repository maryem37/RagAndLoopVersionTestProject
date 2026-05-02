"""
agents/scenario_designer.py
---------------------------
Agent 0 - Scenario Designer Agent

LLM-first scenario design that reads:
  - user story text
  - business_requirements.yaml
  - Swagger/OpenAPI specs

The model returns structured Given/When/Then scenarios, and a deterministic
fallback keeps the pipeline working if the LLM is unavailable or returns
invalid JSON.
"""

from __future__ import annotations

import json
import os
import re
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from config.settings import get_settings
from graph.state import AgentOutput, AgentStatus, TestAutomationState
from tools.chat_model_factory import create_chat_model
from tools.rag_scenario_retriever import (
    retrieve_branch_targeting_scenarios,
    build_rag_prompt_examples,
)


ALLOWED_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
ALLOWED_TEST_TYPES = {"happy_path", "error_case", "edge_case", "security", "integration"}
ALLOWED_PRIORITIES = {"P0", "P1", "P2"}


class TestScenario:
    """Single test scenario with Given/When/Then structure."""

    def __init__(
        self,
        scenario_id: str,
        title: str,
        endpoint: str,
        method: str,
        given: str,
        when: str,
        then: str,
        test_type: str,
        priority: str,
        service: str,
        is_integration: bool = False,
    ):
        self.scenario_id = scenario_id
        self.title = title
        self.endpoint = endpoint
        self.method = method
        self.given = given
        self.when = when
        self.then = then
        self.test_type = test_type
        self.priority = priority
        self.service = service
        self.is_integration = is_integration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "endpoint": self.endpoint,
            "method": self.method,
            "given": self.given,
            "when": self.when,
            "then": self.then,
            "test_type": self.test_type,
            "priority": self.priority,
            "service": self.service,
            "is_integration": self.is_integration,
        }


class ScenarioDesignerAgent:
    """
    Agent 0 - Scenario Designer.

    Uses an LLM to turn requirements + Swagger into structured scenarios.
    Falls back to deterministic endpoint matching if the model call fails.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.scenarios: List[TestScenario] = []
        self._scenario_counters: Dict[str, int] = {}
        self.llm: Optional[Any] = None
        self._llm_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are a senior QA scenario designer for API and end-to-end testing. "
                        "Return JSON only. Do not use markdown fences. "
                        "Use only services, methods, and endpoints that appear in the provided context. "
                        "For non-integration scenarios, the 'when' field must include the exact HTTP method "
                        "and exact endpoint path from the catalog."
                    ),
                ),
                ("human", "{prompt_text}"),
            ]
        )
        self._init_llm()
        logger.info("Scenario Designer Agent initialized")

    def _init_llm(self) -> None:
        """Initialize the configured chat model."""
        skip = (os.getenv("SCENARIO_DESIGNER_SKIP_LLM") or os.getenv("SKIP_LLM") or "").strip().lower()
        if skip in {"1", "true", "yes", "y", "on"}:
            self.llm = None
            logger.warning("Scenario Designer LLM disabled via env; using deterministic fallback only")
            return
        try:
            llm = create_chat_model(
                provider=self.settings.llm.provider,
                api_key=self.settings.llm.api_key,
                base_url=self.settings.llm.base_url,
                model_name=self.settings.llm.scenario_designer.model_name,
                temperature=self.settings.llm.scenario_designer.temperature,
                max_completion_tokens=self.settings.llm.scenario_designer.max_completion_tokens,
            )
            self.llm = llm
            logger.info(
                "Scenario Designer LLM ready - provider: "
                f"{self.settings.llm.provider} model: {self.settings.llm.scenario_designer.model_name}"
            )
        except Exception as exc:
            self.llm = None
            logger.warning(f"Scenario Designer LLM unavailable, fallback will be used: {exc}")

    def _rag_enabled(self) -> bool:
        """Return whether RAG enrichment is enabled for scenario generation."""
        raw = (os.getenv("RAG_ENABLE", "auto") or "").strip().lower()
        return raw not in {"0", "false", "no", "n", "off", "disabled"}

    def execute(self, state: TestAutomationState) -> AgentOutput:
        """Run scenario generation and populate state.test_scenarios."""
        start_time = time.time()
        logger.info("[SCENARIO DESIGNER] Starting scenario generation")

        try:
            business_reqs = self._load_business_requirements() or self._get_default_requirements()
            swagger_specs = getattr(state, "swagger_specs", None) or self._load_all_swagger_specs()
            if not swagger_specs:
                return AgentOutput(
                    agent_name="scenario_designer",
                    status=AgentStatus.FAILED,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error_message="No Swagger specifications available",
                )

            existing_scenarios = [
                item for item in (getattr(state, "test_scenarios", None) or []) if isinstance(item, dict)
            ]
            coverage_retry_mode = bool(getattr(state, "coverage_feedback", None))

            self.scenarios = []
            self._scenario_counters = {}
            if coverage_retry_mode and existing_scenarios:
                self._seed_scenario_counters_from_existing(existing_scenarios)
            endpoint_catalog = self._build_endpoint_catalog(swagger_specs)
            used_llm = False
            generation_sources: Dict[str, str] = {}

            for service_name, spec in swagger_specs.items():
                service_requirements = self._get_service_requirements(business_reqs, service_name)
                service_scenarios: List[TestScenario] = []

                if self.llm:
                    service_scenarios = self._generate_service_scenarios_with_llm(
                        service_name=service_name,
                        swagger_spec=spec,
                        requirements=service_requirements,
                        user_story=state.user_story,
                        endpoint_catalog=endpoint_catalog,
                        coverage_feedback=self._build_coverage_feedback_block(
                            state,
                            service_name=service_name,
                            available_endpoints=endpoint_catalog.get(service_name, []),
                        ),
                    )

                if service_scenarios:
                    generation_sources[service_name] = "llm"
                    used_llm = True
                else:
                    service_scenarios = self._generate_service_scenarios_deterministic(
                        service_name=service_name,
                        swagger_spec=spec,
                        requirements=service_requirements,
                    )
                    generation_sources[service_name] = "fallback"

                # ── RAG enrichment: fetch real-world error/edge/security scenarios ──
                if self._rag_enabled():
                    try:
                        rag_scenarios = retrieve_branch_targeting_scenarios(
                            service_name=service_name,
                            service_endpoints=endpoint_catalog.get(service_name, []),
                            coverage_feedback=getattr(state, "coverage_feedback", None),
                            k_per_query=3,
                        )
                        for rs in rag_scenarios:
                            service_scenarios.append(
                                TestScenario(
                                    scenario_id=self._next_scenario_id(
                                        service_name=service_name,
                                        test_type=rs["test_type"],
                                        is_integration=False,
                                    ),
                                    title=rs["title"],
                                    endpoint=rs["endpoint"],
                                    method=rs["method"],
                                    given=rs["given"],
                                    when=rs["when"],
                                    then=rs["then"],
                                    test_type=rs["test_type"],
                                    priority=rs["priority"],
                                    service=service_name,
                                    is_integration=False,
                                )
                            )
                        if rag_scenarios:
                            logger.info(
                                f"Added {len(rag_scenarios)} RAG-enriched branch-targeting scenarios "
                                f"for {service_name}"
                            )
                    except Exception as exc:
                        logger.debug(f"RAG scenario retrieval failed for {service_name}: {exc}")
                else:
                    logger.info(f"RAG enrichment disabled for {service_name} (RAG_ENABLE=0)")

                if coverage_retry_mode:
                    current_pairs = self._covered_endpoint_pairs(existing_scenarios, service_name)
                    current_pairs.update(
                        {(scenario.method, scenario.endpoint) for scenario in service_scenarios}
                    )
                    # Pull weak areas from coverage feedback so gap scenarios target them
                    feedback = getattr(state, "coverage_feedback", None) or {}
                    service_scenarios.extend(
                        self._build_endpoint_gap_scenarios(
                            service_name=service_name,
                            available_endpoints=endpoint_catalog.get(service_name, []),
                            covered_pairs=current_pairs,
                            limit=5,
                            weak_packages=feedback.get("weak_packages"),
                            weak_classes=feedback.get("weak_classes"),
                        )
                    )

                self.scenarios.extend(service_scenarios)
                logger.info(
                    f"Generated {len(service_scenarios)} scenarios for {service_name} "
                    f"using {generation_sources[service_name]}"
                )

            integration_scenarios: List[TestScenario] = []
            if len(swagger_specs) > 1 and self.llm:
                integration_scenarios = self._generate_integration_scenarios_with_llm(
                    user_story=state.user_story,
                    business_reqs=business_reqs,
                    swagger_specs=swagger_specs,
                    endpoint_catalog=endpoint_catalog,
                    coverage_feedback=self._build_coverage_feedback_block(
                        state,
                        service_name=None,
                        available_endpoints=[],
                    ),
                )

            if integration_scenarios:
                generation_sources["integration"] = "llm"
                used_llm = True
            else:
                integration_scenarios = self._generate_integration_scenarios_deterministic(
                    business_reqs=business_reqs,
                    swagger_specs=swagger_specs,
                )
                if integration_scenarios:
                    generation_sources["integration"] = "fallback"

            self.scenarios.extend(integration_scenarios)

            generated = self._consolidate_scenarios(self.scenarios)
            consolidated = (
                self._merge_scenario_dicts(existing_scenarios, generated)
                if coverage_retry_mode and existing_scenarios
                else generated
            )
            state.test_scenarios = consolidated
            elapsed_ms = int((time.time() - start_time) * 1000)

            by_type = {
                "happy_path": len([s for s in consolidated if s.get("test_type") == "happy_path"]),
                "error_case": len([s for s in consolidated if s.get("test_type") == "error_case"]),
                "edge_case": len([s for s in consolidated if s.get("test_type") == "edge_case"]),
                "security": len([s for s in consolidated if s.get("test_type") == "security"]),
                "integration": len([s for s in consolidated if s.get("is_integration")]),
            }

            logger.info(
                f"Scenario Designer produced {len(consolidated)} scenarios in {elapsed_ms}ms"
            )

            return AgentOutput(
                agent_name="scenario_designer",
                status=AgentStatus.SUCCESS,
                duration_ms=elapsed_ms,
                output_data={
                    "scenarios": consolidated,
                    "scenario_count": len(consolidated),
                    "by_type": by_type,
                    "used_llm": used_llm,
                    "generation_sources": generation_sources,
                    "coverage_retry_mode": coverage_retry_mode,
                },
            )

        except Exception as exc:
            logger.error(f"Scenario Designer failed: {exc}")
            logger.error(traceback.format_exc())
            return AgentOutput(
                agent_name="scenario_designer",
                status=AgentStatus.FAILED,
                duration_ms=int((time.time() - start_time) * 1000),
                error_message=str(exc),
            )

    def _seed_scenario_counters_from_existing(self, scenarios: List[Dict[str, Any]]) -> None:
        """Continue scenario ids from the existing suite during coverage retries."""
        for item in scenarios:
            if not isinstance(item, dict):
                continue
            scenario_id = self._clean_text(item.get("scenario_id"))
            service_name = self._clean_text(item.get("service")) or "integration"
            is_integration = bool(item.get("is_integration")) or service_name == "integration"
            match = re.search(r"-(\d+)", scenario_id)
            if not match:
                continue
            next_num = int(match.group(1))
            key = "integration" if is_integration else service_name
            self._scenario_counters[key] = max(self._scenario_counters.get(key, 0), next_num)

    def _scenario_dict_signature(self, item: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
        title = re.sub(r"\s+", " ", str(item.get("title", "")).strip().lower())
        return (
            str(item.get("service", "")).strip().lower(),
            str(item.get("method", "")).strip().upper(),
            str(item.get("endpoint", "")).strip(),
            str(item.get("test_type", "")).strip().lower(),
            title,
        )

    def _merge_scenario_dicts(
        self,
        existing: List[Dict[str, Any]],
        generated: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Merge scenario dictionaries while keeping the first copy of duplicates."""
        merged: List[Dict[str, Any]] = []
        seen = set()
        for item in list(existing) + list(generated):
            if not isinstance(item, dict):
                continue
            signature = self._scenario_dict_signature(item)
            if signature in seen:
                continue
            seen.add(signature)
            merged.append(item)

        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        type_order = {
            "happy_path": 0,
            "error_case": 1,
            "edge_case": 2,
            "security": 3,
            "integration": 4,
        }
        merged.sort(
            key=lambda scenario: (
                priority_order.get(str(scenario.get("priority", "P2")).upper(), 99),
                type_order.get(str(scenario.get("test_type", "")).lower(), 99),
                str(scenario.get("service", "")),
                str(scenario.get("scenario_id", "")),
            )
        )
        return merged

    def _covered_endpoint_pairs(
        self,
        scenarios: List[Dict[str, Any]],
        service_name: str,
    ) -> set[Tuple[str, str]]:
        pairs: set[Tuple[str, str]] = set()
        for item in scenarios:
            if not isinstance(item, dict):
                continue
            if bool(item.get("is_integration")):
                continue
            if str(item.get("service", "")).strip() != service_name:
                continue
            method = str(item.get("method", "")).strip().upper()
            endpoint = str(item.get("endpoint", "")).strip()
            if method and endpoint:
                pairs.add((method, endpoint))
        return pairs

    def _build_coverage_feedback_block(
        self,
        state: TestAutomationState,
        service_name: Optional[str],
        available_endpoints: List[Dict[str, Any]],
    ) -> str:
        feedback = getattr(state, "coverage_feedback", None) or {}
        if not feedback:
            return ""

        lines = ["COVERAGE FEEDBACK:"]
        current_metrics = feedback.get("current_metrics") or {}
        if current_metrics:
            lines.append(
                "Current metrics: "
                f"line={current_metrics.get('line_coverage_%', 'n/a')}%, "
                f"branch={current_metrics.get('branch_coverage_%', 'n/a')}%, "
                f"method={current_metrics.get('method_coverage_%', 'n/a')}%"
            )
            branch_cov = float(current_metrics.get('branch_coverage_%', 0) or 0)
            line_cov = float(current_metrics.get('line_coverage_%', 0) or 0)
            method_cov = float(current_metrics.get('method_coverage_%', 0) or 0)
            if branch_cov < line_cov and branch_cov < method_cov:
                lines.append(
                    f"BRANCH COVERAGE IS THE BOTTLENECK ({branch_cov}%). "
                    "Prioritize scenarios that exercise validation branches, "
                    "null-checks, conditional logic, and both true/false paths."
                )
        threshold_violations = feedback.get("threshold_violations") or []
        if threshold_violations:
            lines.append("Threshold violations:")
            for violation in threshold_violations[:5]:
                lines.append(f"- {violation}")

        weak_packages = feedback.get("weak_packages") or []
        if weak_packages:
            lines.append("Weak packages (sorted by branch coverage gap):")
            for item in weak_packages[:4]:
                lines.append(
                    f"- {item.get('package')}: "
                    f"line={item.get('line_coverage_%', 'n/a')}%, "
                    f"branch={item.get('branch_coverage_%', 'n/a')}%, "
                    f"method={item.get('method_coverage_%', 'n/a')}%"
                )

        weak_classes = feedback.get("weak_classes") or []
        if weak_classes:
            lines.append("Weak classes (sorted by branch coverage gap):")
            for item in weak_classes[:6]:
                lines.append(
                    f"- {item.get('package')}.{item.get('class')}: "
                    f"line={item.get('line_coverage_%', 'n/a')}%, "
                    f"branch={item.get('branch_coverage_%', 'n/a')}%, "
                    f"method={item.get('method_coverage_%', 'n/a')}%"
                )

        existing = getattr(state, "test_scenarios", None) or []
        if service_name and available_endpoints:
            covered = self._covered_endpoint_pairs(existing, service_name)
            uncovered = [
                f"{endpoint['method']} {endpoint['path']}"
                for endpoint in available_endpoints
                if (endpoint["method"], endpoint["path"]) not in covered
            ]
            if covered:
                lines.append("Already covered endpoints for this service:")
                for method, path in sorted(covered)[:8]:
                    lines.append(f"- {method} {path}")
            if uncovered:
                lines.append("Prefer NEW scenarios for these uncovered endpoints:")
                for item in uncovered[:10]:
                    lines.append(f"- {item}")
            lines.append(
                "Add NEW scenarios that complement the existing suite. Do not simply restate the same endpoint/title combinations."
            )
            lines.append(
                "FOCUS ON BRANCH COVERAGE: generate error_case and edge_case scenarios that exercise validation failures, "
                "null-checks, state transitions, and boundary conditions so both true and false branches are hit."
            )
        else:
            integration_count = sum(
                1 for item in existing if isinstance(item, dict) and bool(item.get("is_integration"))
            )
            lines.append(
                f"Existing integration scenarios already present: {integration_count}. "
                "Add only new cross-service flows if they help weak coverage areas."
            )

        return "\n".join(lines)

    def _build_endpoint_gap_scenarios(
        self,
        service_name: str,
        available_endpoints: List[Dict[str, Any]],
        covered_pairs: set[Tuple[str, str]],
        limit: int = 3,
        weak_packages: Optional[List[Dict[str, Any]]] = None,
        weak_classes: Optional[List[Dict[str, Any]]] = None,
    ) -> List[TestScenario]:
        """Create targeted endpoint-expansion scenarios for weak endpoints.

        Prioritises weak endpoints that are likely to contain business decisions.
        For coverage retries we intentionally include already-covered endpoints so
        we can exercise the opposite branch instead of only discovering new URLs.
        """
        weak_packages = weak_packages or []
        weak_classes = weak_classes or []

        # Build a set of package/class substrings to prioritise
        weak_pkg_names = {self._clean_text(p.get("package", "")).lower() for p in weak_packages}
        weak_class_names = {
            f"{self._clean_text(c.get('package', '')).lower()}.{self._clean_text(c.get('class', '')).lower()}"
            for c in weak_classes
        }

        covered = [
            endpoint
            for endpoint in available_endpoints
            if (endpoint["method"], endpoint["path"]) in covered_pairs
        ]
        uncovered = [
            endpoint
            for endpoint in available_endpoints
            if (endpoint["method"], endpoint["path"]) not in covered_pairs
        ]

        # Score each endpoint: higher = more urgent (weak package match + state-changing method)
        method_priority = {"POST": 30, "PUT": 25, "PATCH": 20, "DELETE": 15, "GET": 5}

        def _score_endpoint(endpoint: Dict[str, Any]) -> int:
            score = method_priority.get(endpoint["method"], 0)
            path_lower = endpoint["path"].lower()
            if (endpoint["method"], endpoint["path"]) in covered_pairs:
                score += 25
            if "leave-requests" in path_lower:
                score += 30
            elif "balances" in path_lower or "/approve" in path_lower or "/reject" in path_lower or "/cancel" in path_lower:
                score += 20
            elif "auth" in path_lower or "users" in path_lower:
                score += 10
            # Boost if path resembles a weak package path segment
            for pkg in weak_pkg_names:
                if pkg and pkg.replace(".", "/") in path_lower.replace(".", "/"):
                    score += 20
            # Boost for endpoints that likely touch weak classes (heuristic via path keywords)
            for wc in weak_class_names:
                if wc:
                    parts = wc.split(".")
                    for part in parts:
                        if len(part) > 3 and part in path_lower:
                            score += 10
            return score

        candidate_endpoints = covered + uncovered
        deduped_candidates: List[Dict[str, Any]] = []
        seen_pairs: set[Tuple[str, str]] = set()
        for endpoint in sorted(candidate_endpoints, key=_score_endpoint, reverse=True):
            pair = (endpoint["method"], endpoint["path"])
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            deduped_candidates.append(endpoint)

        scenarios: List[TestScenario] = []
        scenario_cap = max(limit, 1) * 4
        for endpoint in deduped_candidates:
            branch_scenarios = self._build_branch_targeted_variants(service_name, endpoint, covered_pairs)
            if not branch_scenarios:
                branch_scenarios = self._build_generic_coverage_variants(service_name, endpoint)
            for scenario in branch_scenarios:
                scenarios.append(scenario)
                if len(scenarios) >= scenario_cap:
                    return scenarios

        return scenarios

    def _build_generic_coverage_variants(
        self,
        service_name: str,
        endpoint: Dict[str, Any],
    ) -> List[TestScenario]:
        summary = self._clean_text(
            endpoint["details"].get("summary")
            or endpoint["details"].get("operationId")
            or f"{endpoint['method']} {endpoint['path']}"
        )
        path = endpoint["path"]
        method = endpoint["method"]
        variants: List[TestScenario] = [
            TestScenario(
                scenario_id=self._next_scenario_id(
                    service_name=service_name,
                    test_type="happy_path",
                    is_integration=False,
                ),
                title=f"[COVERAGE] {summary} - valid request",
                endpoint=path,
                method=method,
                given=f"Valid input data and authorised caller for {method} {path}",
                when=f"{method} {path} is invoked with all required fields populated correctly",
                then="Returns a successful 2xx response conforming to the OpenAPI schema",
                test_type="happy_path",
                priority="P1",
                service=service_name,
                is_integration=False,
            )
        ]
        if method in {"POST", "PUT", "PATCH"}:
            variants.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name=service_name,
                        test_type="edge_case",
                        is_integration=False,
                    ),
                    title=f"[COVERAGE] {summary} - boundary values",
                    endpoint=path,
                    method=method,
                    given=f"Boundary-value input prepared for {method} {path}",
                    when=f"{method} {path} is invoked with boundary-value payloads that sit at validation limits",
                    then="Handles boundary conditions without unhandled exceptions and returns the appropriate response code",
                    test_type="edge_case",
                    priority="P1",
                    service=service_name,
                    is_integration=False,
                )
            )
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            variants.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name=service_name,
                        test_type="error_case",
                        is_integration=False,
                    ),
                    title=f"[COVERAGE] {summary} - validation failure",
                    endpoint=path,
                    method=method,
                    given=f"Malformed or missing mandatory fields for {method} {path}",
                    when=f"{method} {path} is invoked with invalid or incomplete payload",
                    then="Returns a 4xx validation error and the error message references the violated constraint",
                    test_type="error_case",
                    priority="P1",
                    service=service_name,
                    is_integration=False,
                )
            )
        return variants

    def _build_branch_targeted_variants(
        self,
        service_name: str,
        endpoint: Dict[str, Any],
        covered_pairs: set[Tuple[str, str]],
    ) -> List[TestScenario]:
        path = endpoint["path"]
        method = endpoint["method"]
        pair = (method, path)
        path_lower = path.lower()
        summary = self._clean_text(
            endpoint["details"].get("summary")
            or endpoint["details"].get("operationId")
            or f"{method} {path}"
        )
        already_covered = pair in covered_pairs
        variants: List[Dict[str, str]] = []

        def add_variant(test_type: str, title: str, given: str, then: str) -> None:
            variants.append(
                {
                    "test_type": test_type,
                    "title": title,
                    "given": given,
                    "then": then,
                }
            )

        if method == "POST" and "/api/leave-requests/create" in path_lower:
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - past dates",
                "User is authenticated and enters past dates",
                "Returns a 4xx validation error for past dates",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - fromDate > toDate",
                "User is authenticated and enters fromDate > toDate",
                "Returns a 4xx validation error when fromDate > toDate",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - overlapping leave request",
                "User submits an overlapping leave request",
                "Second leave request is rejected due to overlapping dates",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - more than 30 days",
                "User is authenticated and requests more than 30 days of leave",
                "Returns a 4xx validation error for more than 30 days",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - more than 5 consecutive days",
                "User is authenticated and requests more than 5 consecutive days",
                "Returns a 4xx validation error for more than 5 consecutive days",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - insufficient balance",
                "User has insufficient balance",
                "Leave request is rejected due to insufficient balance",
            )
            if not already_covered:
                add_variant(
                    "happy_path",
                    f"[COVERAGE] {summary} - valid request",
                    "Valid leave request data and sufficient balance are prepared",
                    "Returns a successful 2xx response conforming to the OpenAPI schema",
                )
        elif method == "PUT" and path_lower.endswith("/approve"):
            add_variant(
                "security",
                f"[COVERAGE] {summary} - invalid token",
                "User attempts approval with invalid token",
                "Approval is rejected with 401, 403, or 400 for invalid token",
            )
            add_variant(
                "security",
                f"[COVERAGE] {summary} - expired token",
                "User attempts approval with expired token",
                "Approval is rejected with 401, 403, or 400 for expired token",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - non-team leader",
                "User attempts approval as a non-team leader",
                "Approval is rejected with 403 Forbidden - Invalid role",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - not pending",
                "User attempts approval for a leave request that is not pending",
                "Returns a 4xx error when the leave request is not pending",
            )
        elif method == "PUT" and path_lower.endswith("/reject"):
            add_variant(
                "security",
                f"[COVERAGE] {summary} - invalid token",
                "User attempts rejection with invalid token",
                "Rejection is denied with an authentication or authorization error",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - non-team leader",
                "User attempts rejection as a non-team leader",
                "Rejection is denied with 403 Forbidden - Invalid role",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - not pending",
                "User attempts rejection for a leave request that is not pending",
                "Returns a 4xx error when the leave request is not pending",
            )
        elif method == "PUT" and path_lower.endswith("/cancel"):
            add_variant(
                "security",
                f"[COVERAGE] {summary} - invalid token",
                "User attempts cancel with invalid token",
                "Cancellation is denied with an authentication or authorization error",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - already rejected",
                "User attempts cancel for a leave request that is not pending",
                "Returns a 4xx error because the leave request has already been rejected",
            )
        elif method == "GET" and ("/api/balances/" in path_lower or path_lower.endswith("/api/balances")):
            add_variant(
                "security",
                f"[COVERAGE] {summary} - other user",
                "Authenticated caller attempts to access another user balance",
                "Returns 4xx and blocks access to other user balance",
            )
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - non-existent user",
                "Authenticated caller requests a non-existent user balance",
                "Returns a 4xx error for non-existent user",
            )
        elif "users" in path_lower and "{id}" in path_lower:
            add_variant(
                "error_case",
                f"[COVERAGE] {summary} - non-existent user",
                "Request targets a non-existent user",
                "Returns a 4xx error for non-existent user",
            )
            add_variant(
                "security",
                f"[COVERAGE] {summary} - invalid token",
                "Caller uses invalid token",
                "Returns an authentication or authorization error",
            )

        scenarios: List[TestScenario] = []
        for variant in variants:
            scenarios.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name=service_name,
                        test_type=variant["test_type"],
                        is_integration=False,
                    ),
                    title=variant["title"],
                    endpoint=path,
                    method=method,
                    given=variant["given"],
                    when=f"{method} {path} is invoked for branch-focused coverage",
                    then=variant["then"],
                    test_type=variant["test_type"],
                    priority="P1",
                    service=service_name,
                    is_integration=False,
                )
            )
        return scenarios

    def _load_business_requirements(self) -> Optional[Dict[str, Any]]:
        """Load business requirements from YAML."""
        req_file = Path("business_requirements.yaml")
        if not req_file.exists():
            logger.warning(f"{req_file} not found")
            return None
        try:
            with req_file.open("r", encoding="utf-8") as handle:
                return yaml.safe_load(handle)
        except Exception as exc:
            logger.error(f"Error loading requirements: {exc}")
            return None

    def _load_all_swagger_specs(self) -> Dict[str, Dict[str, Any]]:
        """Load sample Swagger specs when none were provided in state."""
        specs: Dict[str, Dict[str, Any]] = {}
        examples_dir = Path("examples")
        if not examples_dir.exists():
            logger.error("examples/ directory not found")
            return specs

        for swagger_file in examples_dir.glob("sample_swagger*.json"):
            try:
                with swagger_file.open("r", encoding="utf-8") as handle:
                    spec = json.load(handle)
                port = self._extract_port_from_spec(spec)
                service_name = self._map_port_to_service(port)
                if service_name:
                    specs[service_name] = spec
            except Exception as exc:
                logger.warning(f"Error loading {swagger_file}: {exc}")

        return specs

    def _extract_port_from_spec(self, spec: Dict[str, Any]) -> Optional[int]:
        """Extract the first port found in a Swagger server URL."""
        try:
            servers = spec.get("servers", [])
            if servers:
                match = re.search(r":(\d+)", servers[0].get("url", ""))
                if match:
                    return int(match.group(1))
        except Exception:
            pass
        return None

    def _map_port_to_service(self, port: Optional[int]) -> Optional[str]:
        """Map port to service using the service registry when possible."""
        if port is None:
            return None

        try:
            from tools.service_registry import get_service_registry

            registry = get_service_registry()
            for service in registry.get_enabled_services():
                try:
                    if int(service.port) == int(port):
                        return service.name
                except Exception:
                    continue
        except Exception:
            pass

        return {9000: "auth", 9001: "leave"}.get(port)

    def _get_service_requirements(
        self, business_reqs: Dict[str, Any], service_name: str
    ) -> Dict[str, Any]:
        """Extract requirements for a specific service."""
        for service in business_reqs.get("SERVICES", []):
            if service.get("SERVICE_NAME") == service_name:
                return service
        return {}

    def _get_default_requirements(self) -> Dict[str, Any]:
        """Fallback requirements if YAML is unavailable.

        Includes branch-targeting scenarios designed to hit both sides of
        conditional statements in the service layer (validation, state checks,
        role checks, null checks).
        """
        return {
            "SERVICES": [
                {
                    "SERVICE_NAME": "auth",
                    "BUSINESS_RULES": [
                        "Users must have valid email",
                        "Passwords must be at least 8 characters",
                        "User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION",
                    ],
                    "CRITICAL_ENDPOINTS": [
                        "GET /api/users/{id}",
                        "POST /api/admin/create-employee",
                        "PUT /api/admin/departments/{id}",
                    ],
                    "TEST_SCENARIOS": {
                        "HAPPY_PATH": [
                            "Create valid user with all required fields",
                            "Fetch existing user by ID",
                            "Login with valid credentials",
                        ],
                        "ERROR_CASES": [
                            "Create user with missing email",
                            "Create user with duplicate email",
                            "Create user with invalid role",
                            "Fetch non-existent user (404)",
                            "Assign user to non-existent department",
                            "Login with invalid credentials",
                            "Login with blank password",
                        ],
                        "EDGE_CASES": [
                            "User ID at boundary (0, 1, 9999999)",
                            "Department with no users",
                            "User with special characters in name",
                            "Empty department name",
                        ],
                        "SECURITY_CASES": [
                            "Access user endpoint without JWT token (401)",
                            "Access user endpoint with expired token (401)",
                            "Non-admin user trying to delete another user (403)",
                            "Team leader trying to access other department (403)",
                        ],
                    },
                },
                {
                    "SERVICE_NAME": "leave",
                    "BUSINESS_RULES": [
                        "Leave dates must be in future",
                        "Cannot have overlapping leaves",
                        "Leave request must have fromDate before toDate",
                        "Maximum 30 leave days per year",
                        "Maximum 5 consecutive leave days",
                        "Only TEAM_LEADER can approve",
                        "Only EMPLOYER can reject",
                    ],
                    "CRITICAL_ENDPOINTS": [
                        "POST /api/leave-requests/create",
                        "PUT /api/leave-requests/{id}/approve",
                        "PUT /api/leave-requests/{id}/reject",
                        "PUT /api/leave-requests/{id}/cancel",
                    ],
                    "TEST_SCENARIOS": {
                        "HAPPY_PATH": [
                            "Create valid leave request with future dates",
                            "Retrieve created leave request",
                            "Approve pending leave request as Team Leader",
                            "Reject pending leave request as Employer",
                            "List all leave requests for user",
                            "Search leave requests by date range",
                        ],
                        "ERROR_CASES": [
                            "Create leave with past dates (rejected)",
                            "Create leave with fromDate > toDate (rejected)",
                            "Create overlapping leave request (rejected)",
                            "Request more than 30 days per year (rejected)",
                            "Request more than 5 consecutive days (rejected)",
                            "Create leave without authentication (401)",
                            "Approve leave that's not PENDING (rejected)",
                            "Try to approve as non-Team Leader (403)",
                            "Reject already approved leave (rejected)",
                            "Cancel already cancelled leave (rejected)",
                        ],
                        "EDGE_CASES": [
                            "Same start and end date (0 days leave)",
                            "Leave spanning weekends",
                            "Leave on public holidays",
                            "User with zero leave balance remaining",
                            "Multiple approvals for same request",
                            "Reject already approved leave (rejected)",
                        ],
                        "SECURITY_CASES": [
                            "Access leave endpoint without JWT token (401)",
                            "Access other user's leave request without permission (403)",
                            "Team leader approving leave outside their department (403)",
                            "Non-Employer role trying to reject leave (403)",
                        ],
                    },
                },
            ],
            "INTEGRATION_SCENARIOS": [
                {
                    "SCENARIO": "User Authentication → Leave Request Flow",
                    "STEPS": [
                        "1. User authenticates with conge service",
                        "2. Gets JWT token",
                        "3. User creates leave request in DemandeConge with token",
                        "4. DemandeConge calls conge to verify user role",
                        "5. Team leader receives notification of pending leave",
                        "6. Team leader approves leave",
                    ],
                    "EXPECTED_RESULT": "User receives approval notification",
                },
                {
                    "SCENARIO": "Overlapping Leave Rejection",
                    "STEPS": [
                        "1. User creates leave from 2026-05-01 to 2026-05-10",
                        "2. User tries to create overlapping leave 2026-05-05 to 2026-05-15",
                    ],
                    "EXPECTED_RESULT": "System rejects second request",
                },
                {
                    "SCENARIO": "Role-Based Approval Workflow",
                    "STEPS": [
                        "1. User (Employee) creates leave request",
                        "2. Team Leader with different role tries to approve",
                        "3. System verifies Team Leader role from conge",
                        "4. Team Leader successfully approves",
                    ],
                    "EXPECTED_RESULT": "Employer verifies approval in audit log",
                },
            ],
        }

    def _build_endpoint_catalog(
        self, swagger_specs: Dict[str, Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Build a searchable catalog of endpoints for every service."""
        catalog: Dict[str, List[Dict[str, Any]]] = {}
        for service_name, spec in swagger_specs.items():
            endpoints: List[Dict[str, Any]] = []
            for path, methods in spec.get("paths", {}).items():
                for method, details in methods.items():
                    method_upper = str(method).upper()
                    if method_upper not in ALLOWED_HTTP_METHODS:
                        continue
                    details = details if isinstance(details, dict) else {}
                    parameters = details.get("parameters", [])
                    param_bits: List[str] = []
                    for param in parameters:
                        if not isinstance(param, dict):
                            continue
                        name = param.get("name", "")
                        location = param.get("in", "")
                        required = "required" if param.get("required") else "optional"
                        param_bits.append(f"{location}:{name} ({required})")

                    endpoint = {
                        "service": service_name,
                        "path": path,
                        "method": method_upper,
                        "details": details,
                        "summary": str(details.get("summary", "")).strip(),
                        "operation_id": str(details.get("operationId", "")).strip(),
                        "description": str(details.get("description", "")).strip(),
                        "params_text": ", ".join(param_bits),
                    }
                    endpoints.append(endpoint)
            catalog[service_name] = endpoints
        return catalog

    def _format_service_requirements(self, requirements: Dict[str, Any]) -> str:
        """Create a compact prompt block from service requirements."""
        if not requirements:
            return "No service-specific business requirements were provided."

        sections = []
        for key in [
            "DESCRIPTION",
            "USER_STORIES",
            "BUSINESS_RULES",
            "CRITICAL_ENDPOINTS",
            "TEST_SCENARIOS",
            "INTEGRATION_WITH_CONGE",
        ]:
            if key in requirements and requirements.get(key):
                sections.append(f"{key}: {json.dumps(requirements.get(key), ensure_ascii=True)}")
        return "\n".join(sections) if sections else "No service-specific business requirements were provided."

    def _format_swagger_summary(
        self,
        service_name: str,
        swagger_spec: Dict[str, Any],
        endpoints: List[Dict[str, Any]],
    ) -> str:
        """Create a compact endpoint summary for prompting."""
        title = swagger_spec.get("info", {}).get("title", service_name)
        lines = [f"SERVICE: {service_name}", f"TITLE: {title}", "ENDPOINTS:"]
        for endpoint in endpoints:
            summary_bits = [f"{endpoint['method']} {endpoint['path']}"]
            if endpoint["summary"]:
                summary_bits.append(f"summary={endpoint['summary']}")
            if endpoint["operation_id"]:
                summary_bits.append(f"operationId={endpoint['operation_id']}")
            if endpoint["params_text"]:
                summary_bits.append(f"params={endpoint['params_text']}")
            lines.append(" - " + " | ".join(summary_bits))
        return "\n".join(lines)

    def _format_integration_context(
        self,
        business_reqs: Dict[str, Any],
        swagger_specs: Dict[str, Dict[str, Any]],
        endpoint_catalog: Dict[str, List[Dict[str, Any]]],
    ) -> str:
        """Create a compact cross-service context block for integration prompts."""
        parts = [
            "GLOBAL INTEGRATION REQUIREMENTS:",
            json.dumps(business_reqs.get("INTEGRATION_SCENARIOS", []), ensure_ascii=True),
        ]
        for service_name, spec in swagger_specs.items():
            parts.append("")
            parts.append(
                self._format_swagger_summary(service_name, spec, endpoint_catalog.get(service_name, []))
            )
            requirements = self._get_service_requirements(business_reqs, service_name)
            parts.append(self._format_service_requirements(requirements))
        return "\n".join(parts)

    def _build_service_prompt(
        self,
        service_name: str,
        user_story: str,
        requirements: Dict[str, Any],
        swagger_spec: Dict[str, Any],
        endpoint_catalog: Dict[str, List[Dict[str, Any]]],
        coverage_feedback: str = "",
    ) -> str:
        """Build the LLM prompt for one service."""
        swagger_summary = self._format_swagger_summary(
            service_name, swagger_spec, endpoint_catalog.get(service_name, [])
        )
        req_summary = self._format_service_requirements(requirements)
        scenario_range = (
            "Create between 4 and 10 NEW scenarios that expand coverage without duplicating the current suite.\n"
            if coverage_feedback
            else "Create between 8 and 16 scenarios when enough input exists.\n"
        )

        # RAG examples for branch-coverage inspiration
        rag_examples = ""
        if self._rag_enabled():
            try:
                rag_examples = build_rag_prompt_examples(
                    service_name=service_name,
                    endpoint_catalog=endpoint_catalog.get(service_name, []),
                    k=2,
                )
            except Exception:
                pass

        type_distribution = (
            "TYPE DISTRIBUTION (enforced):\n"
            "- happy_path:   30% (minimum)\n"
            "- error_case:   30% (minimum)\n"
            "- edge_case:    20% (minimum)\n"
            "- security:     20% (minimum)\n"
            "Ensure the final scenario mix roughly follows these proportions.\n"
        )

        return "".join(
            [
                f"Design API test scenarios for the '{service_name}' service.\n\n",
                "Rules:\n",
                "- Return a JSON object only.\n",
                "- Use this schema exactly:\n",
                '  {"scenarios":[{"title":"...","endpoint":"...","method":"GET|POST|PUT|PATCH|DELETE",',
                '"given":"...","when":"...","then":"...","test_type":"happy_path|error_case|edge_case|security",',
                '"priority":"P0|P1|P2","service":"',
                service_name,
                '","is_integration":false}]}\n',
                scenario_range,
                "- Cover the most important happy paths, validation failures, security checks, and edge cases.\n",
                "- Use ONLY endpoints from the endpoint list below.\n",
                "- The 'when' field must include the exact method and exact endpoint path.\n",
                "- Keep each field concise and concrete.\n",
                "- Do not invent actors, statuses, or endpoints that are not present in the input.\n\n",
                f"USER STORY:\n{user_story.strip()}\n\n",
                f"SERVICE REQUIREMENTS:\n{req_summary}\n\n",
                f"{coverage_feedback}\n\n" if coverage_feedback else "",
                f"{type_distribution}\n\n",
                f"{rag_examples}\n\n" if rag_examples else "",
                f"SWAGGER SUMMARY:\n{swagger_summary}\n",
            ]
        )

    def _build_integration_prompt(
        self,
        user_story: str,
        business_reqs: Dict[str, Any],
        swagger_specs: Dict[str, Dict[str, Any]],
        endpoint_catalog: Dict[str, List[Dict[str, Any]]],
        coverage_feedback: str = "",
    ) -> str:
        """Build the LLM prompt for integration scenarios."""
        integration_context = self._format_integration_context(
            business_reqs, swagger_specs, endpoint_catalog
        )
        service_names = ", ".join(sorted(swagger_specs.keys()))
        return "".join(
            [
                "Design cross-service integration scenarios for this microservice system.\n\n",
                "Rules:\n",
                "- Return a JSON object only.\n",
                '- Use this schema exactly: {"scenarios":[{"title":"...","endpoint":"INTEGRATION",',
                '"method":"MULTI-STEP","given":"...","when":"...","then":"...",',
                '"test_type":"integration","priority":"P0|P1|P2","service":"integration","is_integration":true}]}\n',
                (
                    "- Create between 2 and 4 NEW integration scenarios that complement the current suite.\n"
                    if coverage_feedback
                    else "- Create between 2 and 6 integration scenarios when enough input exists.\n"
                ),
                f"- The scenarios must involve more than one service from: {service_names}.\n",
                "- Focus on end-to-end flows, authorization handoffs, and cross-service validation.\n",
                "- Do not use markdown fences or explanations.\n\n",
                f"USER STORY:\n{user_story.strip()}\n\n",
                f"{coverage_feedback}\n\n" if coverage_feedback else "",
                f"INTEGRATION CONTEXT:\n{integration_context}\n",
            ]
        )

    def _call_llm_json(self, prompt_text: str) -> Optional[Dict[str, Any]]:
        """Call the LLM and parse the first JSON object from the response."""
        if not self.llm:
            return None
        
        # Truncate prompt to avoid Groq 400 (prompt too long)
        # llama-3.3-70b has 128k context; keep well under it
        MAX_PROMPT_CHARS = 60000
        if len(prompt_text) > MAX_PROMPT_CHARS:
            logger.warning(
                f"Prompt too long ({len(prompt_text)} chars), truncating to {MAX_PROMPT_CHARS}"
            )
            prompt_text = prompt_text[:MAX_PROMPT_CHARS] + "\n...[truncated]"
        
        try:
            chain = self._llm_prompt | self.llm
            response = chain.invoke({"prompt_text": prompt_text})
            raw = response.content if hasattr(response, "content") else str(response)
            return self._extract_json_payload(raw)
        except Exception as exc:
            logger.warning(f"Scenario Designer LLM call failed: {exc}")
            return None

    def _extract_json_payload(self, raw: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from raw LLM text, tolerating code fences and prose."""
        if not raw:
            return None

        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        candidates = [cleaned]
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidates.append(cleaned[first_brace : last_brace + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue

        logger.warning("Scenario Designer returned non-JSON content")
        return None

    def _next_scenario_id(
        self,
        service_name: str,
        test_type: str,
        is_integration: bool,
    ) -> str:
        """Generate a stable scenario id for each service."""
        key = "integration" if is_integration else service_name
        next_num = self._scenario_counters.get(key, 0) + 1
        self._scenario_counters[key] = next_num

        if is_integration:
            return f"E2E-{next_num:03d}"

        prefix = re.sub(r"[^A-Z0-9]", "", service_name.upper())[:3] or "SCN"
        suffix = {
            "error_case": "E",
            "edge_case": "X",
            "security": "S",
        }.get(test_type, "")
        return f"{prefix}-{next_num:03d}{suffix}"

    def _clean_text(self, value: Any) -> str:
        """Normalize text fields."""
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _normalize_test_type(self, value: Any) -> str:
        """Normalize test type values from LLM output."""
        text = self._clean_text(value).lower()
        aliases = {
            "happy": "happy_path",
            "happy path": "happy_path",
            "success": "happy_path",
            "error": "error_case",
            "error case": "error_case",
            "validation": "error_case",
            "edge": "edge_case",
            "edge case": "edge_case",
            "security_case": "security",
            "auth": "security",
        }
        normalized = aliases.get(text, text)
        return normalized if normalized in ALLOWED_TEST_TYPES else "happy_path"

    def _normalize_priority(self, value: Any) -> str:
        """Normalize priority values from LLM output."""
        text = self._clean_text(value).upper()
        if text in ALLOWED_PRIORITIES:
            return text
        if text in {"HIGH", "CRITICAL"}:
            return "P0"
        if text in {"MEDIUM"}:
            return "P1"
        return "P2"

    def _tokenize(self, text: str) -> List[str]:
        return [token for token in re.split(r"[^a-z0-9]+", text.lower()) if token]

    def _score_endpoint_for_spec(
        self,
        spec_text: str,
        path: str,
        method: str,
        endpoint_spec: Dict[str, Any],
    ) -> int:
        """
        Score how well a business phrase matches an endpoint.

        This is the deterministic fallback matcher and is also used to repair
        incomplete LLM output.

        CRITICAL FOR BRANCH COVERAGE: error/edge cases must route to the
        correct endpoint so validation branches in the service layer are hit.
        """
        spec_lower = spec_text.lower()
        path_lower = path.lower()
        tokens = set(self._tokenize(spec_text))
        op_id = str(endpoint_spec.get("operationId", "")).lower()
        summary = str(endpoint_spec.get("summary", "")).lower()
        description = str(endpoint_spec.get("description", "")).lower()
        haystack = f"{path_lower} {op_id} {summary} {description}"
        method_lower = method.lower()

        score = 0

        # ── Branch-coverage-critical routing rules ──────────────────────
        # These override generic keyword matching to ensure validation errors
        # are sent to the endpoint that actually contains the validation logic.

        # Leave creation validation errors → POST /api/leave-requests/create
        leave_creation_errors = [
            "past dates", "fromdate > todate", "overlapping",
            "more than 30 days", "more than 5 consecutive",
            "create leave", "create valid leave", "future dates",
        ]
        if any(marker in spec_lower for marker in leave_creation_errors):
            if method_lower == "post" and "/api/leave-requests/create" in path_lower:
                score += 50  # Very strong match
            elif "/api/leave-requests/create" in path_lower:
                score += 30
            # Penalize routing to reject/approve/search endpoints
            if "/reject" in path_lower or "/approve" in path_lower or "/search" in path_lower:
                score -= 30

        # Leave approval errors → PUT /api/leave-requests/{id}/approve
        approval_errors = [
            "approve leave", "approve pending", "not pending",
            "non-team leader", "exceeds validation authority",
            "outside their department",
        ]
        if any(marker in spec_lower for marker in approval_errors):
            if method_lower in {"put", "patch"} and "/approve" in path_lower:
                score += 50
            elif "/approve" in path_lower:
                score += 30
            if "/reject" in path_lower or "/create" in path_lower:
                score -= 20

        # Leave rejection errors → PUT /api/leave-requests/{id}/reject
        rejection_errors = [
            "reject leave", "reject pending", "already been rejected",
            "already approved", "non-employer",
        ]
        if any(marker in spec_lower for marker in rejection_errors):
            if method_lower in {"put", "patch"} and "/reject" in path_lower:
                score += 50
            elif "/reject" in path_lower:
                score += 30
            if "/approve" in path_lower or "/create" in path_lower:
                score -= 20

        # Leave cancellation → PUT /api/leave-requests/{id}/cancel
        cancel_errors = ["cancel leave", "already cancelled"]
        if any(marker in spec_lower for marker in cancel_errors):
            if method_lower in {"put", "patch"} and "/cancel" in path_lower:
                score += 50
            elif "/cancel" in path_lower:
                score += 30

        # Auth/login errors → POST /api/auth/login
        auth_errors = ["invalid credentials", "wrong password", "login failure", "locked account"]
        if any(marker in spec_lower for marker in auth_errors):
            if method_lower == "post" and "/api/auth/login" in path_lower:
                score += 50

        # User creation errors → POST /api/admin/create-employee
        user_creation_errors = ["missing email", "duplicate email", "invalid role"]
        if any(marker in spec_lower for marker in user_creation_errors):
            if method_lower == "post" and "/api/admin/create-employee" in path_lower:
                score += 50

        # Balance update errors → PUT /api/balances/{userId}
        balance_errors = ["negative balance", "invalid balance"]
        if any(marker in spec_lower for marker in balance_errors):
            if method_lower in {"put", "patch"} and "/api/balances/" in path_lower:
                score += 50

        # ── Generic action mapping ──────────────────────────────────────
        action_map = {
            "create": {"post"},
            "add": {"post"},
            "assign": {"post", "put"},
            "update": {"put", "patch"},
            "approve": {"put", "patch"},
            "reject": {"put", "patch"},
            "delete": {"delete"},
            "cancel": {"delete", "put", "patch"},
            "fetch": {"get"},
            "get": {"get"},
            "retrieve": {"get"},
            "list": {"get"},
            "search": {"get"},
            "view": {"get"},
            "login": {"post"},
            "authenticate": {"post"},
        }
        for word, methods in action_map.items():
            if word in spec_lower and method_lower in methods:
                score += 4

        keyword_groups = [
            {"user", "users", "employee", "employees"},
            {"department", "departments"},
            {"role", "roles"},
            {"auth", "login", "token", "jwt"},
            {"leave", "leaves", "request", "requests", "balance", "balances", "holiday", "holidays"},
            {"approve", "approved"},
            {"reject", "rejected"},
            {"cancel", "canceled", "cancelled"},
            {"search"},
        ]
        for group in keyword_groups:
            if tokens & group and any(item in haystack for item in group):
                score += 5

        for token in tokens:
            if len(token) >= 4 and token in haystack:
                score += 1

        is_auth_negative = any(
            marker in spec_lower
            for marker in (
                "without jwt",
                "without token",
                "missing token",
                "expired token",
                "invalid token",
                "unauthorized",
                "forbidden",
                "not authorized",
                "not authorised",
                "without authentication",
            )
        )
        if is_auth_negative and "/api/auth/login" in path_lower:
            score -= 12

        if "without" in spec_lower or "expired" in spec_lower:
            if any(item in haystack for item in ("auth", "token", "jwt", "role", "permission")):
                score += 2

        if any(word in spec_lower for word in ("fetch", "retrieve", "existing user", "non-existent user", "user by id")):
            if method_lower == "get" and "/api/users/{id}" in path_lower:
                score += 10

        if "assign user" in spec_lower or "department" in spec_lower:
            if "/api/admin/departments" in path_lower:
                score += 8

        if any(word in spec_lower for word in ("retrieve created leave request", "list all leave requests", "search leave requests")):
            if method_lower == "get" and "/api/leave-requests/search" in path_lower:
                score += 10

        if "without jwt" in spec_lower or "without token" in spec_lower:
            if any(item in path_lower for item in ("/api/users", "/api/admin/", "/api/leave-requests", "/api/balances")):
                score += 8

        if "other user's leave request" in spec_lower and "/api/leave-requests/" in path_lower:
            score += 10
            if "/api/balances/init/" in path_lower:
                score -= 6

        if "outside their department" in spec_lower and "/approve" in path_lower:
            score += 8

        if "delete another user" in spec_lower and method_lower == "delete" and "/api/users/" in path_lower:
            score += 10

        return score

    def _choose_best_endpoint(
        self,
        spec_text: str,
        available_endpoints: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Pick the best matching endpoint for a phrase."""
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for endpoint in available_endpoints:
            score = self._score_endpoint_for_spec(
                spec_text=spec_text,
                path=endpoint["path"],
                method=endpoint["method"],
                endpoint_spec=endpoint["details"],
            )
            if score > 0:
                scored.append((score, endpoint))

        if not scored:
            return None

        scored.sort(key=lambda item: (-item[0], item[1]["path"], item[1]["method"]))
        return scored[0][1]

    def _coerce_llm_service_scenarios(
        self,
        service_name: str,
        raw_items: Any,
        available_endpoints: List[Dict[str, Any]],
        requirements: Dict[str, Any],
    ) -> List[TestScenario]:
        """Validate and normalize LLM-produced service scenarios."""
        if not isinstance(raw_items, list):
            return []

        scenarios: List[TestScenario] = []
        endpoint_lookup = {
            (endpoint["method"], endpoint["path"]): endpoint for endpoint in available_endpoints
        }

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            title = self._clean_text(item.get("title"))
            given = self._clean_text(item.get("given"))
            when = self._clean_text(item.get("when"))
            then = self._clean_text(item.get("then"))
            test_type = self._normalize_test_type(item.get("test_type"))
            priority = self._normalize_priority(item.get("priority"))

            method = self._clean_text(item.get("method")).upper()
            endpoint = self._clean_text(item.get("endpoint"))
            match = endpoint_lookup.get((method, endpoint))
            lookup_text = " ".join(part for part in [title, given, when, then] if part)
            guessed = self._choose_best_endpoint(lookup_text, available_endpoints)

            if guessed and match:
                current_score = self._score_endpoint_for_spec(
                    spec_text=lookup_text,
                    path=match["path"],
                    method=match["method"],
                    endpoint_spec=match["details"],
                )
                guessed_score = self._score_endpoint_for_spec(
                    spec_text=lookup_text,
                    path=guessed["path"],
                    method=guessed["method"],
                    endpoint_spec=guessed["details"],
                )
                if guessed_score >= current_score + 4:
                    method = guessed["method"]
                    endpoint = guessed["path"]
                    match = guessed
            elif guessed:
                method = guessed["method"]
                endpoint = guessed["path"]
                match = guessed

            if not (title and given and then and match):
                continue

            if not when:
                when = f"{method} {endpoint} executed for scenario '{title}'"
            elif method not in when or endpoint not in when:
                when = f"{method} {endpoint} executed - {when}"

            scenarios.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name=service_name,
                        test_type=test_type,
                        is_integration=False,
                    ),
                    title=title,
                    endpoint=endpoint,
                    method=method,
                    given=given,
                    when=when,
                    then=then,
                    test_type=test_type,
                    priority=priority,
                    service=service_name,
                    is_integration=False,
                )
            )

        return self._ensure_critical_endpoint_coverage(
            scenarios=scenarios,
            requirements=requirements,
            available_endpoints=available_endpoints,
            service_name=service_name,
        )

    def _coerce_llm_integration_scenarios(self, raw_items: Any) -> List[TestScenario]:
        """Validate and normalize integration scenarios from the LLM."""
        if not isinstance(raw_items, list):
            return []

        scenarios: List[TestScenario] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue

            title = self._clean_text(item.get("title"))
            given = self._clean_text(item.get("given"))
            when = self._clean_text(item.get("when"))
            then = self._clean_text(item.get("then"))
            priority = self._normalize_priority(item.get("priority"))

            if not (title and given and when and then):
                continue

            scenarios.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name="integration",
                        test_type="integration",
                        is_integration=True,
                    ),
                    title=title,
                    endpoint="INTEGRATION",
                    method="MULTI-STEP",
                    given=given,
                    when=when,
                    then=then,
                    test_type="integration",
                    priority=priority,
                    service="integration",
                    is_integration=True,
                )
            )

        return scenarios

    def _ensure_critical_endpoint_coverage(
        self,
        scenarios: List[TestScenario],
        requirements: Dict[str, Any],
        available_endpoints: List[Dict[str, Any]],
        service_name: str,
    ) -> List[TestScenario]:
        """Backfill a small number of generic scenarios for uncovered critical endpoints."""
        critical_endpoints = requirements.get("CRITICAL_ENDPOINTS", [])
        if not critical_endpoints:
            return scenarios

        seen_pairs = {(scenario.method, scenario.endpoint) for scenario in scenarios}
        lookup = {
            (endpoint["method"], endpoint["path"]): endpoint for endpoint in available_endpoints
        }

        for critical_spec in critical_endpoints:
            parts = str(critical_spec).split(" - ", 1)[0].strip().split()
            if len(parts) < 2:
                continue

            method = parts[0].upper()
            path = parts[1]
            if (method, path) in seen_pairs or (method, path) not in lookup:
                continue

            scenarios.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name=service_name,
                        test_type="happy_path",
                        is_integration=False,
                    ),
                    title=f"[CRITICAL] Exercise {method} {path}",
                    endpoint=path,
                    method=method,
                    given="Preconditions for the critical business flow are satisfied",
                    when=f"{method} {path} executed for critical coverage",
                    then="Returns the expected response and respects the documented business rules",
                    test_type="happy_path",
                    priority="P0",
                    service=service_name,
                    is_integration=False,
                )
            )
            seen_pairs.add((method, path))

        return scenarios

    def _generate_service_scenarios_with_llm(
        self,
        service_name: str,
        swagger_spec: Dict[str, Any],
        requirements: Dict[str, Any],
        user_story: str,
        endpoint_catalog: Dict[str, List[Dict[str, Any]]],
        coverage_feedback: str = "",
    ) -> List[TestScenario]:
        """Generate service scenarios with the LLM, then normalize them."""
        available_endpoints = endpoint_catalog.get(service_name, [])
        if not available_endpoints:
            return []

        prompt_text = self._build_service_prompt(
            service_name=service_name,
            user_story=user_story,
            requirements=requirements,
            swagger_spec=swagger_spec,
            endpoint_catalog=endpoint_catalog,
            coverage_feedback=coverage_feedback,
        )
        payload = self._call_llm_json(prompt_text)
        if not payload:
            return []

        scenarios = self._coerce_llm_service_scenarios(
            service_name=service_name,
            raw_items=payload.get("scenarios", []),
            available_endpoints=available_endpoints,
            requirements=requirements,
        )
        if not scenarios:
            logger.warning(f"No valid LLM scenarios survived normalization for {service_name}")
        return scenarios

    def _generate_integration_scenarios_with_llm(
        self,
        user_story: str,
        business_reqs: Dict[str, Any],
        swagger_specs: Dict[str, Dict[str, Any]],
        endpoint_catalog: Dict[str, List[Dict[str, Any]]],
        coverage_feedback: str = "",
    ) -> List[TestScenario]:
        """Generate cross-service scenarios with the LLM."""
        prompt_text = self._build_integration_prompt(
            user_story=user_story,
            business_reqs=business_reqs,
            swagger_specs=swagger_specs,
            endpoint_catalog=endpoint_catalog,
            coverage_feedback=coverage_feedback,
        )
        payload = self._call_llm_json(prompt_text)
        if not payload:
            return []

        scenarios = self._coerce_llm_integration_scenarios(payload.get("scenarios", []))
        if not scenarios:
            logger.warning("No valid LLM integration scenarios survived normalization")
        return scenarios

    def _generate_service_scenarios_deterministic(
        self,
        service_name: str,
        swagger_spec: Dict[str, Any],
        requirements: Dict[str, Any],
    ) -> List[TestScenario]:
        """Deterministic fallback generator based on business phrases and endpoint matching."""
        scenarios: List[TestScenario] = []
        paths = swagger_spec.get("paths", {})
        business_rules = requirements.get("BUSINESS_RULES", [])
        critical_endpoints = requirements.get("CRITICAL_ENDPOINTS", [])
        test_scenarios_config = requirements.get("TEST_SCENARIOS", {})

        happy_path_specs = test_scenarios_config.get("HAPPY_PATH", [])
        error_case_specs = test_scenarios_config.get("ERROR_CASES", [])
        edge_case_specs = test_scenarios_config.get("EDGE_CASES", [])
        security_case_specs = test_scenarios_config.get("SECURITY_CASES", [])

        available_endpoints: List[Dict[str, Any]] = []
        for path, methods in paths.items():
            for method, endpoint_spec in methods.items():
                method_upper = str(method).upper()
                if method_upper not in ALLOWED_HTTP_METHODS:
                    continue
                available_endpoints.append(
                    {
                        "path": path,
                        "method": method_upper,
                        "details": endpoint_spec if isinstance(endpoint_spec, dict) else {},
                    }
                )

        critical_endpoint_pool: List[Dict[str, Any]] = []
        for critical_endpoint_spec in critical_endpoints:
            parts = str(critical_endpoint_spec).split(" - ", 1)[0].strip().split()
            if len(parts) < 2:
                continue
            method = parts[0].upper()
            path = parts[1]
            details = paths.get(path, {}).get(method.lower())
            if isinstance(details, dict):
                critical_endpoint_pool.append(
                    {"path": path, "method": method, "details": details}
                )

        for happy_spec in happy_path_specs:
            critical_guess = self._choose_best_endpoint(happy_spec, critical_endpoint_pool)
            available_guess = self._choose_best_endpoint(happy_spec, available_endpoints)
            endpoint = critical_guess or available_guess
            if critical_guess and available_guess:
                critical_score = self._score_endpoint_for_spec(
                    spec_text=happy_spec,
                    path=critical_guess["path"],
                    method=critical_guess["method"],
                    endpoint_spec=critical_guess["details"],
                )
                available_score = self._score_endpoint_for_spec(
                    spec_text=happy_spec,
                    path=available_guess["path"],
                    method=available_guess["method"],
                    endpoint_spec=available_guess["details"],
                )
                if available_score >= critical_score + 4:
                    endpoint = available_guess
            if not endpoint:
                continue
            scenarios.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name=service_name,
                        test_type="happy_path",
                        is_integration=False,
                    ),
                    title=self._clean_text(happy_spec),
                    endpoint=endpoint["path"],
                    method=endpoint["method"],
                    given=f"Setup for business rule: {self._clean_text(happy_spec)}",
                    when=f"{endpoint['method']} {endpoint['path']} executed",
                    then=self._generate_assertion_from_business_rules(business_rules, "success"),
                    test_type="happy_path",
                    priority="P0",
                    service=service_name,
                )
            )

        for error_spec in error_case_specs:
            endpoint = self._choose_best_endpoint(error_spec, available_endpoints)
            if not endpoint:
                continue
            scenarios.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name=service_name,
                        test_type="error_case",
                        is_integration=False,
                    ),
                    title=self._clean_text(error_spec),
                    endpoint=endpoint["path"],
                    method=endpoint["method"],
                    given=f"Precondition for error: {self._clean_text(error_spec)}",
                    when=f"{endpoint['method']} {endpoint['path']} called with invalid or missing data",
                    then=self._generate_assertion_from_business_rules(business_rules, "error"),
                    test_type="error_case",
                    priority="P0",
                    service=service_name,
                )
            )

        for edge_spec in edge_case_specs:
            endpoint = self._choose_best_endpoint(edge_spec, available_endpoints)
            if not endpoint:
                continue
            scenarios.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name=service_name,
                        test_type="edge_case",
                        is_integration=False,
                    ),
                    title=self._clean_text(edge_spec),
                    endpoint=endpoint["path"],
                    method=endpoint["method"],
                    given=f"Edge case condition: {self._clean_text(edge_spec)}",
                    when=f"{endpoint['method']} {endpoint['path']} called with boundary values",
                    then="Handles the boundary condition gracefully with the correct outcome",
                    test_type="edge_case",
                    priority="P1",
                    service=service_name,
                )
            )

        for security_spec in security_case_specs:
            endpoint = self._choose_best_endpoint(security_spec, available_endpoints)
            if not endpoint:
                continue
            scenarios.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name=service_name,
                        test_type="security",
                        is_integration=False,
                    ),
                    title=self._clean_text(security_spec),
                    endpoint=endpoint["path"],
                    method=endpoint["method"],
                    given=f"Security condition: {self._clean_text(security_spec)}",
                    when=f"{endpoint['method']} {endpoint['path']} accessed under restricted authorization",
                    then=self._generate_security_assertion(str(security_spec)),
                    test_type="security",
                    priority="P0",
                    service=service_name,
                )
            )

        return self._ensure_critical_endpoint_coverage(
            scenarios=scenarios,
            requirements=requirements,
            available_endpoints=available_endpoints,
            service_name=service_name,
        )

    def _generate_integration_scenarios_deterministic(
        self,
        business_reqs: Dict[str, Any],
        swagger_specs: Dict[str, Any],
    ) -> List[TestScenario]:
        """Deterministic fallback for cross-service scenarios."""
        scenarios: List[TestScenario] = []
        if len(swagger_specs) < 2:
            return scenarios

        integration_scenarios_config = business_reqs.get("INTEGRATION_SCENARIOS", [])
        services = business_reqs.get("SERVICES", [])
        leave_service = next((service for service in services if service.get("SERVICE_NAME") == "leave"), {})
        integration_rules = leave_service.get("INTEGRATION_WITH_CONGE", [])

        for scenario_config in integration_scenarios_config:
            title = scenario_config.get("SCENARIO", "Integration Scenario")
            steps = scenario_config.get("STEPS", [])
            expected = scenario_config.get("EXPECTED_RESULT", "Integration flow succeeds")

            given_parts = [str(step).strip("0123456789. ") for step in steps[:2]]
            when_parts = [str(step).strip("0123456789. ") for step in steps[2:-1]]
            then_value = str(steps[-1]).strip("0123456789. ") if steps else str(expected)

            scenarios.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name="integration",
                        test_type="integration",
                        is_integration=True,
                    ),
                    title=self._clean_text(title),
                    endpoint="INTEGRATION",
                    method="MULTI-STEP",
                    given=" -> ".join([part for part in given_parts if part]) or "Multiple services are initialized",
                    when=" -> ".join([part for part in when_parts if part]) or "Services exchange data to complete the workflow",
                    then=self._clean_text(then_value),
                    test_type="integration",
                    priority="P0",
                    service="integration",
                    is_integration=True,
                )
            )

        for rule in integration_rules:
            scenarios.append(
                TestScenario(
                    scenario_id=self._next_scenario_id(
                        service_name="integration",
                        test_type="integration",
                        is_integration=True,
                    ),
                    title=f"Integration rule: {self._clean_text(rule)}",
                    endpoint="INTEGRATION",
                    method="MULTI-STEP",
                    given="A cross-service workflow is in progress",
                    when="One service validates or enriches data by calling another service",
                    then=self._clean_text(rule),
                    test_type="integration",
                    priority="P0",
                    service="integration",
                    is_integration=True,
                )
            )

        return scenarios

    def _generate_assertion_from_business_rules(
        self, business_rules: List[str], context: str
    ) -> str:
        """Generate deterministic assertion text from the first business rule."""
        if not business_rules:
            if context == "error":
                return "Returns a 4xx response with a validation or authorization failure"
            return "Returns a successful response and enforces the documented rules"

        relevant_rule = str(business_rules[0]).strip()
        if context == "error":
            return f"Returns a 4xx error when this rule is violated: {relevant_rule}"
        return f"Returns a successful response and enforces: {relevant_rule}"

    def _generate_security_assertion(self, security_spec: str) -> str:
        """Generate deterministic security expectations."""
        spec = security_spec.lower()
        if "403" in spec or "forbidden" in spec:
            return "Returns 403 Forbidden"
        if "401" in spec or "unauthorized" in spec or "without jwt" in spec or "without token" in spec:
            return "Returns 401 Unauthorized"
        return "Returns the appropriate authorization error (401 or 403)"

    def _consolidate_scenarios(self, scenarios: List[TestScenario]) -> List[Dict[str, Any]]:
        """Sort and convert scenarios to dictionaries for downstream agents."""
        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        type_order = {
            "happy_path": 0,
            "error_case": 1,
            "edge_case": 2,
            "security": 3,
            "integration": 4,
        }

        deduped: List[TestScenario] = []
        seen = set()
        for scenario in scenarios:
            signature = self._scenario_dict_signature(scenario.to_dict())
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(scenario)

        sorted_scenarios = sorted(
            deduped,
            key=lambda scenario: (
                priority_order.get(scenario.priority, 99),
                type_order.get(scenario.test_type, 99),
                scenario.service,
                scenario.scenario_id,
            ),
        )
        return [scenario.to_dict() for scenario in sorted_scenarios]


def scenario_designer_agent_node(state: TestAutomationState) -> TestAutomationState:
    """Workflow node for the Scenario Designer."""
    agent = ScenarioDesignerAgent()
    output = agent.execute(state)
    state.add_agent_output(output)
    return state
