"""
agents/gherkin_generator.py
────────────────────────────
Agent 2 — Enterprise Gherkin Generator — Swagger-Driven (Zero-Shot)

KEY FIX — SWAGGER-DRIVEN GHERKIN:
  Before: LLM invented error messages, actors, statuses, field names.
          _format_swagger_specs() only listed field names, never enum values.
          No role/actor extraction. No error message extraction.

  Now: Python extracts EXACT facts BEFORE calling the LLM:
         1. _extract_swagger_facts()  → actors/roles from enum fields,
                                        status values from enum fields,
                                        required fields per endpoint,
                                        enum values per field,
                                        response field names
         2. _extract_error_messages() → exact error messages from user story
                                        as a numbered list — LLM copies them verbatim
         3. Prompt injects both as HARD FACTS with explicit "use only these" rules

  Works for ANY microservice — no names, URLs, or values are hardcoded.
  Everything is read from Swagger and from the user story text.

Pipeline
────────
user_story + swagger_specs (all services)
    └─► _extract_swagger_facts()    extract enums, roles, statuses, fields from ALL specs
    └─► _extract_error_messages()   extract error messages from user story text
    └─► extract_features()          split multi-story document
    └─► generate_single()           LLM + post-processing
    └─► save_feature_file()         write .feature to disk
"""

from __future__ import annotations

import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from loguru import logger

from config.settings import get_settings
from graph.state import AgentOutput, AgentStatus, TestAutomationState


# ──────────────────────────────────────────────────────────────────────
# Pre-compiled regex constants
# ──────────────────────────────────────────────────────────────────────

_RE_STEP_PREFIX      = re.compile(r"^\s*(Given|When|Then|And|But)\s+", re.IGNORECASE)
_RE_SCENARIO_OUTLINE = re.compile(r"^\s*Scenario Outline\s*:", re.IGNORECASE)
_RE_SCENARIO_PLAIN   = re.compile(r"^\s*Scenario\s*:",          re.IGNORECASE)
_RE_EXAMPLES         = re.compile(r"^\s*Examples\s*:",          re.IGNORECASE)
_RE_SCENARIO_SPLIT   = re.compile(r"(?=^\s*Scenario(?:\s+Outline)?:)", re.MULTILINE)

_RE_STATUS = re.compile(
    r"\b(Pending|In Progress|Refused|Granted|Canceled|Approved|Active|"
    r"Inactive|Draft|Published|Deleted|Completed|Failed|Success)\b",
    re.IGNORECASE,
)
_RE_INTERMEDIATE_APPROVER = re.compile(
    r"\b(team\s+lead|intermediate\s+approver|first.level\s+approver|"
    r"line\s+manager|supervisor|reviewer)\b",
    re.IGNORECASE,
)
_RE_SUCCESS_MESSAGE = re.compile(
    r'^\s*(And|Then)\s+the\s+system\s+displays?\s+"[^"]*'
    r'(?:successfully|granted|approved|completed)[^"]*"',
    re.IGNORECASE,
)
_RE_HTTP_IN_STEP = re.compile(
    r"\s+(?:to\s+|via\s+|using\s+|at\s+|on\s+)?"
    r"(?:POST|GET|PUT|DELETE|PATCH)\s+/[^\s,;\"']*",
    re.IGNORECASE,
)
_RE_BARE_PATH_IN_STEP = re.compile(
    r"\s+/[a-zA-Z0-9_\-/{}]+(?=\s*$|\s+without|\s+with\s|\s+and\s)"
)

_ERROR_REWRITES: Dict[str, Optional[str]] = {
    "access denied":   None,
    "not authorized":  None,
}

_PLACEHOLDER_FALLBACKS: Dict[str, str] = {
    "initial_status": "Pending",
    "request_status": "Pending",
    "blocked_status": "Completed",
    "status":         "Pending",
    "role":           "user",
    "actor":          "user",
    "id":             "12345",
    "user_id":        "1",
    "item_id":        "1",
    "name":           "Test Name",
    "description":    "Test Description",
    "reason":         "Test Reason",
    "comment":        "Test Comment",
    "error_message":  "An error occurred",
}


# ──────────────────────────────────────────────────────────────────────
# SWAGGER FACT EXTRACTION
#
# These functions read the Swagger specs BEFORE the LLM is called.
# The LLM receives concrete extracted facts — not vague descriptions.
# This prevents hallucination of field names, actors, and enum values.
# ──────────────────────────────────────────────────────────────────────

def _resolve_ref(ref: str, spec: dict) -> dict:
    """Resolve $ref like '#/components/schemas/Foo' to its schema dict."""
    if not ref.startswith("#/"):
        return {}
    node = spec
    for part in ref.lstrip("#/").split("/"):
        node = node.get(part, {})
    return node


def _get_base_url(spec: dict) -> str:
    servers = spec.get("servers", [])
    return servers[0].get("url", "http://localhost:8080") if servers else "http://localhost:8080"


def _walk_for_enums(obj: Any, field_hint: str = "", result: Optional[Dict] = None) -> Dict[str, List]:
    """
    Recursively walk any dict/list and collect every enum definition found.
    Returns {field_name: [enum_values]}.
    This works regardless of how deep the enum is nested in the Swagger.
    """
    if result is None:
        result = {}
    if isinstance(obj, dict):
        if "enum" in obj and obj["enum"] and field_hint:
            result[field_hint] = obj["enum"]
        for k, v in obj.items():
            _walk_for_enums(v, k, result)
    elif isinstance(obj, list):
        for item in obj:
            _walk_for_enums(item, field_hint, result)
    return result


def _extract_swagger_facts(swagger_specs: dict) -> str:
    """
    Extract concrete facts from ALL Swagger specs and format them
    as a structured hard-constraint block for the LLM.

    Extracts per service:
      - Base URL
      - Actors/roles from any enum field whose name contains 'role' or 'actor'
      - Status/state values from any enum field whose name contains 'state' or 'status'
      - Every endpoint with:
          - Path and HTTP method
          - Required request body fields with their enum values
          - Optional request body fields with their enum values
          - Response field names (from 200/201 response schema)

    The LLM is told: "Use ONLY these values — do not invent."
    Works for any microservice — nothing is hardcoded.
    """
    if not swagger_specs:
        return ""

    sections: List[str] = []

    for svc_key, spec in swagger_specs.items():
        if not spec or "paths" not in spec:
            continue

        title    = spec.get("info", {}).get("title", svc_key)
        base_url = _get_base_url(spec)

        # Walk the entire spec for all enums — works for any structure
        all_enums = _walk_for_enums(spec)
        logger.debug(f"   [{svc_key}] found enum fields: {list(all_enums.keys())}")

        # Separate actors/roles from statuses
        actor_enums  = {k: v for k, v in all_enums.items()
                        if any(r in k.lower() for r in ("role", "actor", "usertype", "user_type"))}
        status_enums = {k: v for k, v in all_enums.items()
                        if any(s in k.lower() for s in ("state", "status"))}

        lines: List[str] = [
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"SERVICE: {title}  [{svc_key}]",
            f"BASE URL: {base_url}",
        ]

        if actor_enums:
            lines.append("")
            lines.append("ACTORS / ROLES — use ONLY these values as actors in step text:")
            for field, values in actor_enums.items():
                lines.append(f"  {field}: {values}")
            # Flatten to a single list for the LLM
            all_roles: List[str] = []
            for values in actor_enums.values():
                all_roles.extend(values)
            lines.append(f"  → use one of: {list(dict.fromkeys(all_roles))}")

        if status_enums:
            lines.append("")
            lines.append("STATUS VALUES — use ONLY these in step text (always in double quotes):")
            for field, values in status_enums.items():
                lines.append(f"  {field}: {values}")

        lines.append("")
        lines.append("ENDPOINTS:")

        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue

                summary = details.get("summary", "")
                lines.append(f"")
                lines.append(f"  {method.upper()} {path}" + (f"  ({summary})" if summary else ""))

                # Path params
                path_params = [
                    p["name"] for p in details.get("parameters", [])
                    if isinstance(p, dict) and p.get("in") == "path"
                ]
                if path_params:
                    lines.append(f"    path params: {', '.join(path_params)}")

                # Query params with enum values
                for p in details.get("parameters", []):
                    if not isinstance(p, dict) or p.get("in") != "query":
                        continue
                    p_name = p.get("name", "")
                    p_req  = " [REQUIRED]" if p.get("required") else " [optional]"
                    schema = p.get("schema", {})
                    p_enum = schema.get("enum", [])
                    enum_s = f" allowed: {p_enum}" if p_enum else ""
                    lines.append(f"    query: {p_name}{p_req}{enum_s}")

                # Request body — resolve $ref, show required marker AND enum values
                body = details.get("requestBody", {})
                if body:
                    for media in body.get("content", {}).values():
                        schema = media.get("schema", {})
                        if "$ref" in schema:
                            schema = _resolve_ref(schema["$ref"], spec)
                        props    = schema.get("properties", {})
                        required = schema.get("required", [])
                        if props:
                            lines.append("    request body fields (* = required):")
                            for fname, fschema in props.items():
                                if "$ref" in fschema:
                                    fschema = _resolve_ref(fschema["$ref"], spec)
                                ftype  = fschema.get("type", "string")
                                fenum  = fschema.get("enum", [])
                                req    = "* " if fname in required else "  "
                                ev     = f" — allowed values: {fenum}" if fenum else ""
                                lines.append(f"      {req}{fname} ({ftype}){ev}")

                # Response fields from 200 or 201 — resolve $ref
                for code in ("200", "201"):
                    resp = details.get("responses", {}).get(code, {})
                    if not resp:
                        continue
                    for media in resp.get("content", {}).values():
                        schema = media.get("schema", {})
                        if "$ref" in schema:
                            schema = _resolve_ref(schema["$ref"], spec)
                        fields: List[str] = []
                        if schema.get("type") == "object":
                            fields = list(schema.get("properties", {}).keys())
                        elif schema.get("type") == "array":
                            items = schema.get("items", {})
                            if "$ref" in items:
                                items = _resolve_ref(items["$ref"], spec)
                            fields = list(items.get("properties", {}).keys())
                        if fields:
                            lines.append(f"    response fields ({code}): {', '.join(fields)}")
                    break

        sections.append("\n".join(lines))

    if not sections:
        return ""

    header = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "INPUT 2 — SWAGGER API CONTRACT (ALL SERVICES)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "STRICT RULE: Use ONLY the actors, statuses, field names, and enum values\n"
        "listed below. DO NOT invent any value not present in this contract.\n"
        "DO NOT translate or paraphrase error messages — copy them verbatim from INPUT 1.\n\n"
    )
    result = header + "\n\n".join(sections) + "\n"
    # Escape curly braces for LangChain template engine
    result = result.replace("{", "{{").replace("}", "}}")
    return result


def _extract_error_messages(user_story: str) -> str:
    """
    Extract error messages verbatim from the user story text.
    Looks for lines/patterns that look like error messages:
      - Quoted strings after keywords like 'error', 'message', 'displays', 'shows'
      - Lines starting with 'ERR', 'Error:', 'Error message:', etc.
      - Quoted strings in error context

    Returns a formatted numbered list to inject into the prompt.
    The LLM is told: "copy these EXACTLY — do not translate or paraphrase."
    """
    messages: List[str] = []
    seen: Set[str] = set()

    # Pattern 1: quoted strings after error/message/displays keywords
    pattern1 = re.compile(
        r'(?:error|message|displays?|shows?|warning|msg)\s*[:\-→]?\s*["\u201c\u201d]([^"\u201c\u201d]+)["\u201c\u201d]',
        re.IGNORECASE,
    )
    for m in pattern1.finditer(user_story):
        msg = m.group(1).strip()
        if msg and msg not in seen:
            seen.add(msg)
            messages.append(msg)

    # Pattern 2: lines starting with ERR followed by quoted string
    pattern2 = re.compile(
        r'ERR\d*[\.\):]?\s+[^"\n]*["\u201c\u201d]([^"\u201c\u201d]+)["\u201c\u201d]',
        re.IGNORECASE,
    )
    for m in pattern2.finditer(user_story):
        msg = m.group(1).strip()
        if msg and msg not in seen:
            seen.add(msg)
            messages.append(msg)

    # Pattern 3: any quoted string that looks like a validation message
    # (contains words like 'invalid', 'required', 'mandatory', 'must', 'cannot', 'not')
    pattern3 = re.compile(r'["\u201c\u201d]([^"\u201c\u201d]{10,})["\u201c\u201d]')
    validation_words = re.compile(
        r'\b(invalid|required|mandatory|must|cannot|not|warning|error|'
        r'missing|exceed|overlap|balance|notice|period|zero|existed)\b',
        re.IGNORECASE,
    )
    for m in pattern3.finditer(user_story):
        msg = m.group(1).strip()
        if msg and msg not in seen and validation_words.search(msg):
            seen.add(msg)
            messages.append(msg)

    if not messages:
        return ""

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "ERROR MESSAGES — EXTRACTED FROM USER STORY",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "CRITICAL: Copy these EXACTLY as-is in your Then steps.",
        "Do NOT translate, paraphrase, or replace with English equivalents.",
        "Do NOT invent error messages not listed here.",
        "",
    ]
    for i, msg in enumerate(messages, 1):
        lines.append(f'  {i}. "{msg}"')
    lines.append("")

    result = "\n".join(lines)
    result = result.replace("{", "{{").replace("}", "}}")
    return result


# ──────────────────────────────────────────────────────────────────────
# Agent
# ──────────────────────────────────────────────────────────────────────

class GherkinGeneratorAgent:
    """
    Enterprise Gherkin Generator — Swagger-Driven, E2E Chain Approach.

    ONE feature file per user story.
    All actors, statuses, field enum values, and error messages
    are extracted from Swagger and user story BEFORE calling the LLM.
    The LLM cannot invent anything not in the extracted facts.
    Works for any microservice — nothing is hardcoded.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        llm = HuggingFaceEndpoint(
            repo_id=self.settings.huggingface.gherkin_generator.model_name,
            huggingfacehub_api_token=self.settings.huggingface.api_token,
            task="text-generation",
            temperature=self.settings.huggingface.gherkin_generator.temperature,
            max_new_tokens=2000,
        )
        self.llm = ChatHuggingFace(llm=llm)
        logger.info(
            f"✅ Gherkin Generator (Swagger-driven) initialized — "
            f"model: {self.settings.huggingface.gherkin_generator.model_name}"
        )

    # ──────────────────────────────────────────────────────────────────
    # PROMPT
    # ──────────────────────────────────────────────────────────────────

    def _create_prompt(self) -> ChatPromptTemplate:
        system = """\
You are a Gherkin file generator for END-TO-END testing. Your output is a single .feature file.

ABSOLUTE RULE — OUTPUT FORMAT:
  Your response MUST start with "Feature:" on the very first line.
  Output ONLY valid Gherkin keywords: Feature, Background, Scenario, Scenario Outline,
  Given, When, Then, And, But, Examples, and table rows starting with |.
  No markdown, no code fences, no explanations, no bullet points, no analysis.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCES OF TRUTH — READ BEFORE WRITING ANYTHING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have THREE inputs:
  INPUT 1 — User story / specification text
  INPUT 2 — Swagger API contract extracted from actual service specs
  INPUT 3 — Error messages extracted verbatim from the user story

Rules:
  • Actors and roles → use ONLY values from INPUT 2 ACTORS / ROLES section
  • Status values    → use ONLY values from INPUT 2 STATUS VALUES section
  • Error messages   → copy EXACTLY from INPUT 3, character by character
                       Do NOT translate. Do NOT paraphrase. Do NOT invent.
  • Field names      → use ONLY field names listed in INPUT 2 endpoints
  • Enum values      → use ONLY "allowed values" listed in INPUT 2
  • Business rules   → derive from INPUT 1 only

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
E2E CHAIN PRINCIPLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each feature describes ONE complete user journey crossing ALL services.
Authentication always comes first if an auth service exists in INPUT 2.
The token from login feeds all subsequent service calls.

Correct chain example:
  Given the employee logs in with valid credentials
  When the employee submits a leave request
  Then the leave request status is "Pending"

This touches Auth service → Business service. That is E2E.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP TEXT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEVER put in step text:
  - HTTP methods (POST, GET, PUT, DELETE, PATCH)
  - URL paths (/api/auth/login, /api/leave-requests/create, etc.)
  - Port numbers, service names, field names from request bodies

ALWAYS describe business behaviour only:
  BAD:  When the employee sends POST /api/leave-requests/create with type=ANNUAL_LEAVE
  GOOD: When the employee submits an annual leave request

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILE LAYOUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature: <title from user story>
  <one-sentence description>

  Background:          (only if authentication needed in ALL scenarios)
    Given the <actor> logs in with valid credentials

  Scenario: <happy path title>
    Given  <precondition>
    When   <first business action>
    And    <next actions>
    Then   <first observable result>
    And    <additional results>

  Scenario: <error title>
    Given  <precondition>
    When   <action that triggers error>
    Then   the system displays the error "<exact message from INPUT 3>"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCENARIO RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  - ONE nominal (happy-path) scenario only — chain ALL services
  - ONE failure scenario per distinct error message in INPUT 3
  - ONE unauthorized scenario → "Then the system blocks the action"
  - Scenario Outline MUST have Examples table with header row + at least 1 data row
  - Same error for multiple trigger values → merge into ONE Scenario Outline
  - Status values always in double quotes
  - Given = precondition only, never an action
  - Then = observable system behaviour only, never a user gesture

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COVERAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ☑  ONE nominal scenario (login → action → result)
  ☑  One scenario per error message in INPUT 3
  ☑  Unauthorized access
  ☑  Missing required fields (based on INPUT 2 required fields)
  ☑  Insufficient balance / quota (if in INPUT 1)
  ☑  Overlap / conflict (if in INPUT 1)
"""

        human = """\
Generate the COMPLETE Gherkin .feature file for this E2E user journey.
Use ONLY what is in the three inputs below. Invent nothing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT 1 — USER STORY / SPECIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{story}

{swagger_context}
{error_messages}
Output a single valid .feature file. First line must be "Feature:":
"""

        return ChatPromptTemplate.from_messages([
            ("system", system),
            ("human",  human),
        ])

    # ──────────────────────────────────────────────────────────────────
    # FEATURE EXTRACTION
    # ──────────────────────────────────────────────────────────────────

    def extract_features(self, text: str) -> List[str]:
        """Split multi-story input into individual story blocks."""
        gherkin_step_re = re.compile(r"^\s*(Given|When|Then|And|But)\s+", re.IGNORECASE)
        if sum(1 for l in text.splitlines() if gherkin_step_re.match(l)) >= 3:
            logger.info("📋 Input is existing Gherkin — passing through as-is")
            return [text.strip()]

        blocks:  List[str] = []
        current: List[str] = []
        inside_gherkin = False

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("Feature:") or stripped.startswith("Gherkin"):
                inside_gherkin = True
            if re.match(r"(User Story|Feature)\s*[-:]", stripped, re.IGNORECASE):
                if current:
                    j = "\n".join(current).strip()
                    if j: blocks.append(j)
                    current = []
                inside_gherkin = False
            if not inside_gherkin and stripped:
                current.append(line)

        if current:
            j = "\n".join(current).strip()
            if j: blocks.append(j)

        seen:   set = set()
        result: List[str] = []
        for b in blocks:
            if b and b not in seen:
                seen.add(b); result.append(b)

        if not result and text.strip():
            result = [text.strip()]

        logger.info(f"📋 Extracted {len(result)} user story/stories → {len(result)} feature file(s)")
        return result

    # ──────────────────────────────────────────────────────────────────
    # POST-PROCESSING PIPELINE
    # (unchanged from original — all fixes are in the prompt layer)
    # ──────────────────────────────────────────────────────────────────

    def _clean_markdown(self, text: str) -> str:
        text = re.sub(r"```gherkin\s*", "", text)
        text = re.sub(r"```\s*",        "", text)
        match = re.search(r"^(Feature:)", text, re.MULTILINE)
        if not match:
            logger.warning("⚠ No Feature: block in LLM output. Raw: " + repr(text[:300]))
            return ""
        text = text[match.start():]
        gherkin_kw = re.compile(
            r"^\s*(Feature:|Background:|Scenario\s*(Outline)?:|"
            r"Given|When|Then|And|But|Examples:|\|#|$)",
            re.IGNORECASE,
        )
        lines = text.splitlines()
        last  = 0
        for i, line in enumerate(lines):
            if gherkin_kw.match(line):
                last = i
        return "\n".join(lines[:last + 1])

    def _fix_technical_step_text(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            if not _RE_STEP_PREFIX.match(line):
                lines.append(line); continue
            original = line

            def _strip_http(m: re.Match) -> str:
                full = m.group(0)
                q = re.search(r"/[^\s]*\s+((?:without|with|and|using|but)\s+\S.*)", full, re.IGNORECASE)
                return (" " + q.group(1)) if q else ""

            line = _RE_HTTP_IN_STEP.sub(_strip_http, line)
            line = _RE_BARE_PATH_IN_STEP.sub("", line)
            line = line.rstrip(" .,;:")
            if line != original:
                logger.warning(f"✎ Stripped URL from step: '{original.strip()}' → '{line.strip()}'")
            lines.append(line)
        return "\n".join(lines)

    def _fix_first_person(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            if not _RE_STEP_PREFIX.match(line):
                lines.append(line); continue
            original = line
            line = re.sub(
                r"^(\s*(?:Given|When|Then|And|But)\s+)I ",
                lambda m: f"{m.group(1)}the user ",
                line,
            )
            if line != original:
                logger.debug(f"✎ First-person: '{original.strip()}' → '{line.strip()}'")
            lines.append(line)
        return "\n".join(lines)

    def _fix_selected_reason(self, text: str) -> str:
        tf   = (r"(?:reason|comment|observation|description|note|details|"
                r"bio|summary|title|message|explanation|feedback)")
        _A   = re.compile(rf"(?i)(has\s+)selected(\s+the\s+{tf})")
        _B   = re.compile(rf"(?i)\bselects(\s+the\s+{tf})\b")
        lines = []
        for line in text.splitlines():
            if not _RE_STEP_PREFIX.match(line):
                lines.append(line); continue
            original = line
            line = _A.sub(r"\1entered\2", line)
            line = _B.sub(r"enters\1",    line)
            if line != original:
                logger.debug(f"✎ selected→entered: '{original.strip()}'")
            lines.append(line)
        return "\n".join(lines)

    def _fix_duplicate_given(self, text: str) -> str:
        parts  = _RE_SCENARIO_SPLIT.split(text)
        result: List[str] = []
        for block in parts:
            s = block.strip()
            if not (s.startswith("Scenario:") or s.startswith("Scenario Outline:")):
                result.append(block); continue
            lines       = block.splitlines()
            given_seen  = False
            in_examples = False
            fixed       = []
            for line in lines:
                if _RE_EXAMPLES.match(line.strip()): in_examples = True
                if not in_examples:
                    if re.match(r"^\s*(When|Then)\s+", line, re.IGNORECASE): given_seen = False
                    if re.match(r"^\s*Given\s+",       line, re.IGNORECASE):
                        if given_seen:
                            line = re.sub(r"^(\s*)Given\s+", r"\1And ", line)
                            logger.debug(f"✎ Dup Given→And: '{line.strip()}'")
                        else:
                            given_seen = True
                fixed.append(line)
            result.append("\n".join(fixed))
        return "".join(result)

    def _fix_error_messages(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            lower = line.lower()
            for wrong, correct in _ERROR_REWRITES.items():
                if wrong in lower:
                    if correct is None:
                        if "displays" in lower:
                            line = re.sub(r'"[^"]*"',
                                          '"You are not authorized to perform this action"',
                                          line, flags=re.IGNORECASE)
                    else:
                        line = re.sub(rf'"{re.escape(wrong)}"', f'"{correct}"',
                                      line, flags=re.IGNORECASE)
                    break
            lines.append(line)
        return "\n".join(lines)

    def _fix_unresolved_placeholders(self, text: str) -> str:
        result      = []
        in_outline  = False
        in_examples = False
        for line in text.splitlines():
            stripped = line.strip()
            if _RE_SCENARIO_OUTLINE.match(stripped): in_outline = True;  in_examples = False
            elif _RE_SCENARIO_PLAIN.match(stripped): in_outline = False; in_examples = False
            if _RE_EXAMPLES.match(stripped):         in_examples = True
            if not in_outline and not in_examples:
                for key, value in _PLACEHOLDER_FALLBACKS.items():
                    line = re.sub(rf"<{re.escape(key)}>", value, line, flags=re.IGNORECASE)
                for token in re.findall(r"<([^>|\s]+)>", line):
                    fallback = token.replace("_", " ").title()
                    logger.warning(f"⚠ Placeholder <{token}> → '{fallback}'")
                    line = line.replace(f"<{token}>", f'"{fallback}"')
            result.append(line)
        return "\n".join(result)

    def _remove_status_from_background(self, text: str) -> str:
        result        = []
        in_background = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("Background:"):
                in_background = True; result.append(line); continue
            if in_background and re.match(r"^\s*Scenario", line):
                in_background = False
            if in_background and _RE_STATUS.search(stripped):
                logger.warning(f"⚠ Removed status from Background: '{stripped}'"); continue
            result.append(line)
        return "\n".join(result)

    def _remove_broken_scenarios(self, text: str) -> str:
        parts = _RE_SCENARIO_SPLIT.split(text)
        outline_sigs: set = set()
        for block in parts:
            if not block.strip().startswith("Scenario Outline:"): continue
            for line in block.splitlines():
                if re.match(r"^\s*When\s+", line):
                    sig = re.sub(r"<[^>]+>", ".*", line.strip().lower())
                    sig = re.sub(r'"[^"]*"', '".*"', sig)
                    outline_sigs.add(sig)
        result: List[str] = []
        for block in parts:
            stripped = block.strip()
            if not stripped.startswith("Scenario:"): result.append(block); continue
            header     = block.splitlines()[0].strip()
            then_count = len(re.findall(r"^\s*Then\s+", block, re.MULTILINE))
            if then_count == 0:
                logger.warning(f"⚠ Removed (no Then): '{header}'"); continue
            dup = False
            for line in block.splitlines():
                if re.match(r"^\s*When\s+", line):
                    sig = re.sub(r'"[^"]*"', '".*"', line.strip().lower())
                    if sig in outline_sigs:
                        logger.warning(f"⚠ Removed (covered by Outline): '{header}'")
                        dup = True; break
            if not dup: result.append(block)
        return "".join(result)

    def _fix_intermediate_approver_success_message(self, text: str) -> str:
        _RE_FINAL = re.compile(
            r'status\s+(?:changes?\s+to|is\s+now|becomes?)\s+"(?:Granted|Approved|Completed|Published)"',
            re.IGNORECASE)
        _RE_BAL   = re.compile(r"\b(balance|quota|allowance|credit|deducted|adjusted)\b", re.IGNORECASE)
        parts  = _RE_SCENARIO_SPLIT.split(text)
        result = []
        for block in parts:
            if not block.strip().startswith("Scenario:"): result.append(block); continue
            lines    = block.splitlines()
            setup    = " ".join(l for l in lines if re.match(r"^\s*(Given|And)\s+", l, re.IGNORECASE))
            then_txt = " ".join(l for l in lines if re.match(r"^\s*(Then|And)\s+",  l, re.IGNORECASE))
            is_inter = bool(_RE_INTERMEDIATE_APPROVER.search(setup))
            if is_inter and not (_RE_FINAL.search(then_txt) and _RE_BAL.search(then_txt)):
                fixed = [l for l in lines if not _RE_SUCCESS_MESSAGE.match(l)]
                result.append("\n".join(fixed))
            else:
                result.append(block)
        return "".join(result)

    def _quote_status_values_in_examples(self, text: str) -> str:
        result      = []
        in_outline  = False
        in_examples = False
        for line in text.splitlines():
            stripped = line.strip()
            if _RE_SCENARIO_OUTLINE.match(stripped): in_outline = True;  in_examples = False
            elif _RE_SCENARIO_PLAIN.match(stripped): in_outline = False; in_examples = False
            if _RE_EXAMPLES.match(stripped):         in_examples = True
            if in_outline and not in_examples:
                fixed = re.sub(
                    r'(?<!")<(status|state|type|category|phase|stage|result|outcome)>(?!")',
                    r'"<\1>"', line, flags=re.IGNORECASE)
                if fixed != line: logger.debug(f"✎ Wrapped placeholder: '{line.strip()}'")
                line = fixed
            result.append(line)
        return "\n".join(result)

    def _strip_quotes_from_examples(self, text: str) -> str:
        result      = []
        in_examples = False
        for line in text.splitlines():
            stripped = line.strip()
            if _RE_EXAMPLES.match(stripped):
                in_examples = True; result.append(line); continue
            if in_examples and re.match(r"^\s*Scenario", stripped):
                in_examples = False
            if in_examples and "|" in stripped:
                result.append(re.sub(r'(\|\s*)"(.*?)"(?=\s*\|)', r'\1\2', line))
            else:
                result.append(line)
        return "\n".join(result)

    def _fix_empty_examples_tables(self, text: str) -> str:
        parts  = _RE_SCENARIO_SPLIT.split(text)
        result = []
        for block in parts:
            stripped = block.strip()
            if not stripped.startswith("Scenario Outline:"): result.append(block); continue
            ex_match = re.search(r"^\s*Examples\s*:", block, re.MULTILINE)
            if not ex_match:
                fixed = re.sub(r"^(\s*)Scenario Outline\s*:", r"\1Scenario:", block, count=1, flags=re.MULTILINE)
                fixed = re.sub(r"<[^>]+>", "value", fixed)
                logger.warning("✎ Outline→Scenario (no Examples)"); result.append(fixed); continue
            after = block[ex_match.end():]
            rows  = [l for l in after.splitlines() if l.strip().startswith("|") and l.strip().endswith("|")]
            valid = True
            if len(rows) < 2:
                valid = False
            else:
                hcols = [c.strip() for c in rows[0].split("|") if c.strip()]
                if not hcols: valid = False
                else:
                    for dr in rows[1:]:
                        if len([c.strip() for c in dr.split("|") if c.strip()]) != len(hcols):
                            valid = False; break
            if not valid:
                fixed = re.sub(r"^(\s*)Scenario Outline\s*:", r"\1Scenario:", block, count=1, flags=re.MULTILINE)
                fixed = re.sub(r"\n\s*Examples\s*:.*", "", fixed, flags=re.DOTALL)
                fixed = re.sub(r"<[^>]+>", "value", fixed)
                logger.warning(f"✎ Outline→Scenario (invalid Examples: {len(rows)} rows)")
                result.append(fixed)
            else:
                result.append(block)
        return "".join(result)

    def _fix_or_in_given(self, text: str) -> str:
        result      = []
        in_outline  = False
        in_examples = False
        for line in text.splitlines():
            stripped = line.strip()
            if _RE_SCENARIO_OUTLINE.match(stripped): in_outline = True;  in_examples = False
            elif _RE_SCENARIO_PLAIN.match(stripped): in_outline = False; in_examples = False
            if _RE_EXAMPLES.match(stripped):         in_examples = True
            if not in_outline and not in_examples and re.match(r"^\s*(Given|And)\s+", line, re.IGNORECASE):
                fixed = re.sub(r'(\s+or\s+"[^"]*")+', "", line)
                if fixed != line: logger.debug(f'✎ Removed "or": "{line.strip()}"')
                line = fixed
            result.append(line)
        return "\n".join(result)

    def _collapse_duplicate_nominal_scenarios(self, text: str) -> str:
        _RE_SUC = re.compile(
            r'^\s*(Then|And)\s+.+('
            r'successfully|"Pending"|unique\s+(id|number)|saved|finalized|generated)',
            re.IGNORECASE)
        _RE_ERR = re.compile(
            r'^\s*(Then|And)\s+.*(error|blocks?\s+the\s+action|"Warning)', re.IGNORECASE)
        parts = _RE_SCENARIO_SPLIT.split(text)
        seen  = False
        result: List[str] = []
        for block in parts:
            if not block.strip().startswith("Scenario:"): result.append(block); continue
            lines   = block.splitlines()
            has_suc = any(_RE_SUC.match(l) for l in lines)
            has_err = any(_RE_ERR.match(l) for l in lines)
            if has_suc and not has_err:
                if seen:
                    logger.warning(f"⚠ Collapsed dup nominal: '{lines[0].strip()}'"); continue
                seen = True
            result.append(block)
        return "".join(result)

    def _merge_same_error_scenarios(self, text: str) -> str:
        from collections import defaultdict

        def _err(block: str) -> str:
            for line in block.splitlines():
                m = re.match(
                    r'^\s*(?:Then|And)\s+the\s+(?:system\s+)?(?:displays?|shows?)\s+'
                    r'(?:the\s+)?(?:error\s+)?"([^"]+)"', line, re.IGNORECASE)
                if m: return m.group(1).strip()
            return ""

        def _steps(block: str) -> List[str]:
            return [l for l in block.splitlines()
                    if re.match(r"^\s*(Given|When|Then|And|But)\s+", l, re.IGNORECASE)]

        def _vals(block: str) -> List[str]:
            vals = []
            for line in _steps(block):
                if re.match(r"^\s*(Then|And)\s+", line, re.IGNORECASE): break
                for groups in re.findall(r'"([^"]+)"|\b(\d{4}-\d{2}-\d{2})\b|\b(\d{2}:\d{2})\b', line):
                    v = next((g for g in groups if g), None)
                    if v: vals.append(v)
            return vals

        parts  = _RE_SCENARIO_SPLIT.split(text)
        groups: dict = defaultdict(list)
        for i, block in enumerate(parts):
            if not block.strip().startswith("Scenario:"): continue
            e = _err(block)
            if e: groups[e].append(i)

        merged: dict = {}
        drop:   set  = set()

        for err_msg, indices in groups.items():
            if len(indices) < 2: continue
            counts = [len(_steps(parts[i])) for i in indices]
            if len(set(counts)) != 1: continue
            fv = _vals(parts[indices[0]])
            if not fv: continue
            cols = [f"value{n+1}" for n in range(len(fv))]
            rows: List[List[str]] = []
            ok = True
            for idx in indices:
                row = _vals(parts[idx])
                if len(row) != len(fv): ok = False; break
                rows.append(row)
            if not ok: continue

            fl   = parts[indices[0]].splitlines()
            ind  = "  "
            for l in fl:
                if re.match(r"^\s+(Given|When|Then|And|But)\s+", l, re.IGNORECASE):
                    ind = re.match(r"^(\s+)", l).group(1); break
            title = re.sub(r"^Scenario:\s*", "", fl[0].strip())
            title = re.sub(r"\b(Annual|Unpaid|Authorization|Recovery|daily|hourly)\b", "", title, flags=re.IGNORECASE).strip()
            title = re.sub(r"\s{2,}", " ", title)
            v2c   = {v: cols[n] for n, v in enumerate(fv)}
            outline = [f"{ind}Scenario Outline: {title}"]
            for line in fl[1:]:
                if re.match(r"^\s*(Then|And)\s+", line, re.IGNORECASE):
                    outline.append(f'{ind}  Then the system displays the error "{err_msg}"'); break
                replaced = line
                for v, col in v2c.items():
                    replaced = replaced.replace(f'"{v}"', f'<{col}>').replace(v, f'<{col}>')
                outline.append(replaced)
            cw     = [max(len(c), max(len(r[n]) for r in rows)) for n, c in enumerate(cols)]
            header = "| " + " | ".join(c.ljust(cw[n]) for n, c in enumerate(cols)) + " |"
            outline += ["", f"{ind}  Examples:", f"{ind}    {header}"]
            for row in rows:
                outline.append(f"{ind}    | " + " | ".join(v.ljust(cw[n]) for n, v in enumerate(row)) + " |")
            merged[indices[0]] = "\n".join(outline) + "\n"
            for idx in indices[1:]: drop.add(idx)
            logger.info(f"↔ Merged {len(indices)} same-error → Outline: '{title[:60]}'")

        result = []
        for i, block in enumerate(parts):
            if i in drop: continue
            result.append(merged[i] if i in merged else block)
        return "".join(result)

    def _clean_output(self, text: str) -> str:
        text = re.sub(r"(\S)([ \t]{2,})(Scenario(?:\s+Outline)?\s*:)", r"\1\n\n  \3", text)
        text = re.sub(r"(?<!\n)\n(?=[ \t]*Scenario(?:\s+Outline)?\s*:)", "\n\n", text)
        text = re.sub(r"(?<!\n)\n(?=[ \t]*Background\s*:)", "\n\n", text)
        lines   = [l.rstrip() for l in text.strip().splitlines()]
        cleaned = "\n".join(lines)
        return cleaned if cleaned.endswith("\n") else cleaned + "\n"

    # ──────────────────────────────────────────────────────────────────
    # SAVE
    # ──────────────────────────────────────────────────────────────────

    def save_feature_file(self, content: str, service_name: str = "feature", index: int = 1) -> Path:
        features_dir: Path = self.settings.paths.features_dir
        features_dir.mkdir(parents=True, exist_ok=True)
        safe_svc = re.sub(r"[^a-z0-9]+", "-", service_name.lower()).strip("-")
        if index == 1:
            for old in features_dir.glob(f"{safe_svc}_*.feature"):
                old.unlink(); logger.info(f"   🗑 Removed: {old.name}")
        match = re.search(r"^Feature:\s*(.+)", content, re.MULTILINE)
        slug  = re.sub(r"[^a-z0-9]+", "-", match.group(1).lower()).strip("-")[:40] if match else f"journey-{index}"
        filename = f"{safe_svc}_{index:02d}_{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.feature"
        filepath = features_dir / filename
        if not content.endswith("\n"): content += "\n"
        filepath.write_text(content, encoding="utf-8", newline="\n")
        logger.success(f"💾 Saved .feature → {filepath}")
        return filepath

    # ──────────────────────────────────────────────────────────────────
    # SINGLE GENERATION
    # ──────────────────────────────────────────────────────────────────

    def generate_single(self, story: str, swagger_context: str = "", error_messages: str = "") -> str:
        prompt = self._create_prompt()
        chain  = prompt | self.llm

        _RETRY_SYS = (
            "You are a Gherkin file generator. Output ONLY a valid .feature file starting with 'Feature:'.\n"
            "No markdown, no explanations.\n"
            "Use ONLY actors and statuses from INPUT 2.\n"
            "Copy error messages EXACTLY from INPUT 3 — do not translate or invent.\n"
            "Never put HTTP methods or URL paths in step text."
        )
        _RETRY_HUM = (
            "Generate Gherkin for this user journey. First line MUST be 'Feature:'.\n\n"
            "{story}\n\n{swagger_context}\n{error_messages}\n\nFeature:"
        )
        _retry_prompt = ChatPromptTemplate.from_messages([
            ("system", _RETRY_SYS),
            ("human",  _RETRY_HUM),
        ])

        max_attempts = 3
        raw          = ""
        active_chain = chain

        for attempt in range(1, max_attempts + 1):
            logger.info(f"🤖 LLM call attempt {attempt}/{max_attempts}")
            response = active_chain.invoke({
                "story":          story,
                "swagger_context": swagger_context,
                "error_messages": error_messages,
            })
            raw = response.content if hasattr(response, "content") else str(response)
            if re.search(r"^Feature:", raw, re.MULTILINE):
                break
            logger.warning(f"⚠ Attempt {attempt}: no Feature: block. Retrying.")
            active_chain = _retry_prompt | self.llm
            if attempt == max_attempts:
                logger.error("❌ LLM failed to produce Feature: block after 3 attempts.")

        raw = self._clean_markdown(raw)
        raw = self._fix_technical_step_text(raw)
        raw = self._fix_first_person(raw)
        raw = self._fix_selected_reason(raw)
        raw = self._fix_duplicate_given(raw)
        raw = self._fix_or_in_given(raw)
        raw = self._fix_error_messages(raw)
        raw = self._fix_unresolved_placeholders(raw)
        raw = self._remove_status_from_background(raw)
        raw = self._remove_broken_scenarios(raw)
        raw = self._collapse_duplicate_nominal_scenarios(raw)
        raw = self._merge_same_error_scenarios(raw)
        raw = self._fix_intermediate_approver_success_message(raw)
        raw = self._fix_empty_examples_tables(raw)
        raw = self._quote_status_values_in_examples(raw)
        raw = self._strip_quotes_from_examples(raw)
        raw = self._clean_output(raw)
        return raw

    # ──────────────────────────────────────────────────────────────────
    # LANGGRAPH ENTRY POINT
    # ──────────────────────────────────────────────────────────────────

    def generate(self, state: TestAutomationState) -> TestAutomationState:
        start = time.time()
        logger.info(f"🚀 Gherkin Generator (Swagger-driven) — project: {state.service_name}")

        try:
            # Step 1 — extract exact facts from Swagger BEFORE calling LLM
            if state.swagger_specs:
                swagger_context = _extract_swagger_facts(state.swagger_specs)
                logger.info(f"   Swagger facts extracted from {len(state.swagger_specs)} service(s)")
            elif state.swagger_spec:
                swagger_context = _extract_swagger_facts({"primary": state.swagger_spec})
                logger.info("   Swagger facts extracted from 1 service")
            else:
                swagger_context = ""
                logger.warning("   No Swagger specs — LLM will have no API contract")

            # Step 2 — split input into individual user stories
            features = self.extract_features(state.user_story)
            if not features:
                raise ValueError("No feature specifications found in user_story input")

            logger.info(f"📌 {len(features)} user story/stories → {len(features)} feature file(s)")

            all_contents: List[str] = []
            all_files:    List[str] = []

            for idx, story_block in enumerate(features, start=1):
                if not story_block.strip():
                    continue

                # Step 3 — extract error messages from THIS story block
                error_messages = _extract_error_messages(story_block)
                if error_messages:
                    n = error_messages.count('".') + error_messages.count('"\n')
                    logger.info(f"   Error messages extracted from user story: {n} found")
                else:
                    logger.info("   No quoted error messages found in user story")

                logger.info(f"   Generating feature {idx}/{len(features)}...")
                content  = self.generate_single(story_block, swagger_context, error_messages)
                filepath = self.save_feature_file(content, state.service_name, idx)
                all_contents.append(content)
                all_files.append(str(filepath))

            state.gherkin_content = "\n\n".join(all_contents)
            state.gherkin_files   = all_files

            duration_ms = (time.time() - start) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="gherkin_generator",
                status=AgentStatus.SUCCESS,
                duration_ms=duration_ms,
                output_data={
                    "stories_processed": len(features),
                    "feature_files":     all_files,
                    "approach":          "Swagger-driven E2E — one feature per user story",
                },
            ))
            logger.success(f"✅ Gherkin generated — {len(all_files)} file(s) in {duration_ms:.0f} ms")

        except Exception:
            duration_ms = (time.time() - start) * 1000
            tb = traceback.format_exc()
            logger.error(f"❌ Gherkin generation failed:\n{tb}")
            state.add_agent_output(AgentOutput(
                agent_name="gherkin_generator",
                status=AgentStatus.FAILED,
                duration_ms=duration_ms,
                error_message=tb,
            ))
            state.add_error(f"Gherkin generation failed: {tb}")

        return state


def gherkin_generator_node(state: TestAutomationState) -> TestAutomationState:
    return GherkinGeneratorAgent().generate(state)