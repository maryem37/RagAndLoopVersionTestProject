"""
agents/gherkin_generator.py
────────────────────────────
Agent 2 — Enterprise Gherkin Generator (Zero-Shot)

Converts user stories + Swagger specs into valid BDD .feature files.
Compatible with any domain (Leave Management, E-commerce, Finance, etc.).

Pipeline
────────
user_story + swagger_specs
    └─► extract_features()       split multi-story document
    └─► generate_single()        LLM (HuggingFace) + post-processing
    └─► save_feature_file()      write .feature to disk
    └─► state updated            gherkin_content, gherkin_files

FIX v2:
  _fix_empty_examples_tables() is now called in the generate_single()
  post-processing pipeline (was defined but never invoked).
  This prevents Cucumber 7 NoSuchElementException crashes caused by
  Scenario Outlines whose Examples table is empty or has no header row.
"""

from __future__ import annotations

import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from loguru import logger

from config.settings import get_settings
from graph.state import AgentOutput, AgentStatus, TestAutomationState


# ──────────────────────────────────────────────────────────────────────
# Pre-compiled regex constants
# ──────────────────────────────────────────────────────────────────────

_RE_STEP_PREFIX = re.compile(
    r"^\s*(Given|When|Then|And|But)\s+", re.IGNORECASE
)
_RE_SCENARIO_OUTLINE = re.compile(r"^\s*Scenario Outline\s*:", re.IGNORECASE)
_RE_SCENARIO_PLAIN   = re.compile(r"^\s*Scenario\s*:",         re.IGNORECASE)
_RE_EXAMPLES         = re.compile(r"^\s*Examples\s*:",         re.IGNORECASE)

_RE_STATUS = re.compile(
    r"\b(Pending|In Progress|Refused|Granted|Canceled|Approved|Active|"
    r"Inactive|Draft|Published|Deleted|Completed|Failed|Success)\b",
    re.IGNORECASE,
)

_RE_SCENARIO_SPLIT = re.compile(
    r"(?=^\s*Scenario(?:\s+Outline)?:)", re.MULTILINE
)

_RE_INTERMEDIATE_APPROVER = re.compile(
    r"\b(team\s+lead|intermediate\s+approver|first.level\s+approver|"
    r"line\s+manager|supervisor|reviewer)\b",
    re.IGNORECASE,
)

_RE_FINAL_APPROVER = re.compile(
    r"\b(final\s+approver|administrator|admin|hr\s+manager|"
    r"department\s+head|director)\b",
    re.IGNORECASE,
)

_RE_SUCCESS_MESSAGE = re.compile(
    r'^\s*(And|Then)\s+the\s+system\s+displays?\s+"[^"]*'
    r'(?:successfully|granted|approved|completed)[^"]*"',
    re.IGNORECASE,
)

# ──────────────────────────────────────────────────────────────────────
# Error message rewrite map (Generic)
# ──────────────────────────────────────────────────────────────────────

_ERROR_REWRITES: dict[str, Optional[str]] = {
    "access denied":  None,
    "not authorized": None,
    "mandatory field": "This field is required",
    "invalid input":   "Invalid input provided",
}

_PLACEHOLDER_FALLBACKS: dict[str, str] = {
    "initial_status": "Pending",
    "request_status": "Pending",
    "blocked_status": "Completed",
    "status":         "Pending",
    "role":           "administrator",
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
# Agent
# ──────────────────────────────────────────────────────────────────────

class GherkinGeneratorAgent:
    """
    Enterprise Gherkin Generator (Zero-Shot).
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
            f"✅ Gherkin Generator initialized — model: "
            f"{self.settings.huggingface.gherkin_generator.model_name}"
        )

    # ──────────────────────────────────────────────────────────────────
    # PROMPT (Zero-Shot)
    # ──────────────────────────────────────────────────────────────────

    def _create_prompt(self) -> ChatPromptTemplate:
        """
        Zero-shot prompt that produces the target Gherkin style:
        - ONE unified nominal scenario (not one per variant/type)
        - Narrative When→And flow for action sequences
        - Lean failure scenarios without redundant date literals
        - Scenario Outlines only when the SAME error fires for multiple values
        """
        system = """\
You are a Gherkin file generator. Your output is a single .feature file.

ABSOLUTE RULE — OUTPUT FORMAT:
  Your response MUST start with the word "Feature:" on the very first line.
  Do NOT write any of the following before or after the Gherkin:
    - Reviews, assessments, or evaluations of the specification
    - Numbered lists, bullet points, headers, or markdown
    - Strengths / weaknesses / suggestions / improvements
    - Explanations, comments, or analysis of any kind
    - Code fences (``` or similar)
  If you find yourself writing anything other than Gherkin keywords
  (Feature, Background, Scenario, Given, When, Then, And, But, Examples),
  STOP and delete it. The entire response is a .feature file — nothing else.

Your ONLY sources of truth are INPUT 1 (specification) and INPUT 2 (Swagger).
Do NOT invent field names, actors, statuses, error messages, or business rules
that are not present in those two inputs.

══════════════════════════════════════════════════════════════
FILE LAYOUT
══════════════════════════════════════════════════════════════

Feature: <title from spec>
  <one-sentence description from spec>

  Background:
    Given <universal authentication precondition>
    And   <other precondition true for ALL scenarios>

  Scenario: <nominal title>
    ...

  Scenario: <failure title>
    ...

══════════════════════════════════════════════════════════════
BACKGROUND
══════════════════════════════════════════════════════════════

• Contain ONLY steps unconditionally true for every scenario.
• NEVER put a status value, a specific role, or scenario-specific
  state in Background.
• Omit Background if no universal precondition exists.

══════════════════════════════════════════════════════════════
NOMINAL SCENARIO — ONE ONLY
══════════════════════════════════════════════════════════════

Write EXACTLY ONE nominal scenario for the whole feature.
Do NOT write one per type, variant, or role — pick one representative flow.

Keyword roles:
  Given = precondition only; never an action.
          Only one Given per scenario; further setup lines use And.
  When  = the FIRST action that starts the flow.
  And   = every subsequent action or system reaction; no limit.
  Then  = the FIRST observable outcome.
  And   = every additional observable outcome.

The nominal scenario must reflect ALL creation/confirmation criteria
from the spec. Use only values from the spec or Swagger.

══════════════════════════════════════════════════════════════
FAILURE SCENARIOS
══════════════════════════════════════════════════════════════

One focused scenario per distinct error in the spec. Keep them short.

Data-entry failure pattern:
  Given  <minimal precondition>
  When   <action that triggers the error>
  And    <submit action>
  Then   the system displays the error "<verbatim message from spec>"

Precondition failure pattern:
  Given  <minimal precondition>
  And    <bad precondition state>
  When   <submit action>
  Then   the system displays the error "<verbatim message from spec>"

Rules:
  • Error messages — verbatim from spec, never paraphrased.
  • No specific dates/times/numbers unless the value IS the failure cause.
  • Same error message for multiple values → ONE Scenario Outline.
  • Same error message for multiple statuses → ONE Scenario Outline.

══════════════════════════════════════════════════════════════
SCENARIO OUTLINE RULES — CRITICAL
══════════════════════════════════════════════════════════════

A Scenario Outline MUST always have a complete Examples table.
The Examples table MUST have:
  • A header row with column names: | col1 | col2 |
  • At least one data row with actual values: | val1 | val2 |
NEVER write a Scenario Outline with an empty Examples: section.
If you cannot provide example values, write a plain Scenario instead.

══════════════════════════════════════════════════════════════
CONTENT RULES
══════════════════════════════════════════════════════════════

ACTORS         Derive from spec. Never use "I", "I am", "I have".
SWAGGER        Reflect endpoint paths, required fields (*), response codes.
               Required fields → mandatory-field validation scenario.
               Optional fields → never fail on them.
UNAUTHORIZED   One scenario; outcome: "Then the system blocks the action".
OUTLINES       Use when same logic applies to multiple values. Never
               write a plain Scenario covered by an Outline.
DUPLICATES     Same Then error in two scenarios → merge into one Outline.
FORMATTING     Status/state values in double quotes in step text.
               UI control names in double quotes.
               Examples table cells have no surrounding quotes.
THEN STEPS     Observable system behaviour only — no user gestures.
FREE TEXT      reason/comment/observation/note/description → "enters", not "selects".
PLACEHOLDERS   <tokens> only in Scenario Outline step text; never in plain Scenarios.
APPROVALS      Intermediate approver → intermediate status, no success message.
               Final approver → final status + success message.

══════════════════════════════════════════════════════════════
COVERAGE — one scenario or outline per item (skip if not in spec)
══════════════════════════════════════════════════════════════
  ☑  ONE nominal / happy-path scenario
  ☑  Initial display / data pre-fill
  ☑  Each distinct validation error
  ☑  Unauthorized access
  ☑  Missing required fields (spec/Swagger required only)
  ☑  Insufficient balance / quota
  ☑  Overlap / conflict with existing records
  ☑  Notice / lead-time violation
  ☑  Zero-duration result (one Outline if same error message)
"""

        human = """\
Generate the COMPLETE Gherkin .feature file from the inputs below.
Every field name, actor, status value, error message, and business rule
in your output MUST come from these inputs — invent nothing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT 1 — USER STORY / SPECIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{story}

{swagger_context}
Output a single valid Gherkin .feature file. First line must be "Feature:":
"""

        return ChatPromptTemplate.from_messages([
            ("system", system),
            ("human",  human),
        ])

    # ──────────────────────────────────────────────────────────────────
    # SWAGGER CONTEXT
    # ──────────────────────────────────────────────────────────────────

    def _format_swagger_specs(self, swagger_specs: dict) -> str:
        if not swagger_specs:
            return ""

        all_parts: List[str] = []

        for service_key, spec in swagger_specs.items():
            if not spec or "paths" not in spec:
                continue

            title   = spec.get("info", {}).get("title", service_key)
            version = spec.get("info", {}).get("version", "")
            header  = f"[{title} {version}]".strip()
            lines: List[str] = [header]

            for path, methods in spec.get("paths", {}).items():
                for method, details in methods.items():
                    if not isinstance(details, dict):
                        continue

                    summary      = details.get("summary", "")
                    operation_id = details.get("operationId", "")

                    path_params = [
                        p.get("name", "")
                        for p in details.get("parameters", [])
                        if isinstance(p, dict) and p.get("in") == "path"
                    ]

                    body_fields: List[str] = []
                    body = details.get("requestBody", {})
                    if body:
                        for media in body.get("content", {}).values():
                            schema   = media.get("schema", {})
                            props    = schema.get("properties", {})
                            required = schema.get("required", [])
                            for fname, fschema in props.items():
                                req_marker = "*" if fname in required else ""
                                ftype      = fschema.get("type", "string")
                                body_fields.append(f"{fname}{req_marker}:{ftype}")

                    response_codes = list(details.get("responses", {}).keys())

                    line = f"  {method.upper()} {path}"
                    if summary:
                        line += f"  → {summary}"
                    if operation_id:
                        line += f" [{operation_id}]"
                    lines.append(line)

                    if path_params:
                        lines.append(f"    Path params: {', '.join(path_params)}")
                    if body_fields:
                        lines.append(f"    Body (* = required): {', '.join(body_fields)}")
                    if response_codes:
                        lines.append(f"    Responses: {', '.join(response_codes)}")

            all_parts.append("\n".join(lines))

        if not all_parts:
            return ""

        body = "\n\n".join(all_parts)
        result = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "INPUT 2 — SWAGGER / API CONTRACT\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + body + "\n"
        )
        result = result.replace("{", "{{").replace("}", "}}")
        return result

    # ──────────────────────────────────────────────────────────────────
    # FEATURE EXTRACTION
    # ──────────────────────────────────────────────────────────────────

    def extract_features(self, text: str) -> List[str]:
        """
        Split a multi-story document into individual specification blocks.
        """
        gherkin_step_re = re.compile(
            r"^\s*(Given|When|Then|And|But)\s+", re.IGNORECASE
        )
        lines_with_steps = sum(
            1 for l in text.splitlines() if gherkin_step_re.match(l)
        )
        if lines_with_steps >= 3:
            logger.info(
                "📋 Input appears to be existing Gherkin — "
                "passing full text as single specification block"
            )
            return [text.strip()]

        blocks: List[str] = []
        current: List[str] = []
        inside_gherkin = False

        for line in text.splitlines():
            stripped = line.strip()

            if stripped.startswith("Feature:") or stripped.startswith("Gherkin"):
                inside_gherkin = True

            if re.match(r"(User Story|Feature)\s*[-:]", stripped, re.IGNORECASE):
                if current:
                    blocks.append("\n".join(current).strip())
                    current = []
                inside_gherkin = False

            if not inside_gherkin and stripped:
                current.append(line)

        if current:
            blocks.append("\n".join(current).strip())

        seen: set = set()
        result: List[str] = []
        for b in blocks:
            if b and b not in seen:
                seen.add(b)
                result.append(b)

        if not result and text.strip():
            result = [text.strip()]

        logger.info(f"📋 Extracted {len(result)} feature specification(s)")
        return result

    # ──────────────────────────────────────────────────────────────────
    # POST-PROCESSING PIPELINE
    # ──────────────────────────────────────────────────────────────────

    def _clean_markdown(self, text: str) -> str:
        text = re.sub(r"```gherkin\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        match = re.search(r"^(Feature:)", text, re.MULTILINE)
        if not match:
            logger.warning(
                "⚠ LLM output contains no Feature: block — "
                "model emitted a review/analysis instead of Gherkin. "
                "Raw output (first 300 chars): "
                + repr(text[:300])
            )
            return ""

        text = text[match.start():]

        gherkin_keywords = re.compile(
            r"^\s*(Feature:|Background:|Scenario\s*(Outline)?:|"
            r"Given|When|Then|And|But|Examples:|\|#|$)",
            re.IGNORECASE,
        )
        lines = text.splitlines()
        last_gherkin = 0
        for i, line in enumerate(lines):
            if gherkin_keywords.match(line):
                last_gherkin = i
        text = "\n".join(lines[: last_gherkin + 1])

        return text

    def _fix_first_person(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            if not _RE_STEP_PREFIX.match(line):
                lines.append(line)
                continue
            original = line
            line = re.sub(
                r"^(\s*(?:Given|When|Then|And|But)\s+)I ",
                lambda m: f"{m.group(1)}the user ",
                line,
            )
            if line != original:
                logger.debug(f"✎ First-person rewrite: '{original.strip()}' → '{line.strip()}'")
            lines.append(line)
        return "\n".join(lines)

    def _fix_selected_reason(self, text: str) -> str:
        text_fields = (
            r"(?:reason|comment|observation|description|note|details|"
            r"bio|summary|title|message|explanation|feedback)"
        )
        _RE_SELECTED_FIELD = re.compile(
            rf"(?i)(has\s+)selected(\s+the\s+{text_fields})"
        )
        _RE_SELECTS_FIELD = re.compile(
            rf"(?i)\bselects(\s+the\s+{text_fields})\b"
        )
        lines = []
        for line in text.splitlines():
            if not _RE_STEP_PREFIX.match(line):
                lines.append(line)
                continue
            original = line
            line = _RE_SELECTED_FIELD.sub(r"\1entered\2", line)
            line = _RE_SELECTS_FIELD.sub(r"enters\1", line)
            if line != original:
                logger.debug(
                    f"✎ selected→entered: '{original.strip()}' → '{line.strip()}'"
                )
            lines.append(line)
        return "\n".join(lines)

    def _fix_duplicate_given(self, text: str) -> str:
        parts = _RE_SCENARIO_SPLIT.split(text)
        result: List[str] = []

        for block in parts:
            stripped_block = block.strip()
            if not (
                stripped_block.startswith("Scenario:")
                or stripped_block.startswith("Scenario Outline:")
            ):
                result.append(block)
                continue

            lines = block.splitlines()
            given_seen = False
            in_examples = False
            fixed_lines: List[str] = []

            for line in lines:
                s = line.strip()

                if _RE_EXAMPLES.match(s):
                    in_examples = True

                if not in_examples:
                    if re.match(r"^\s*(When|Then)\s+", line, re.IGNORECASE):
                        given_seen = False

                    if re.match(r"^\s*Given\s+", line, re.IGNORECASE):
                        if given_seen:
                            line = re.sub(r"^(\s*)Given\s+", r"\1And ", line)
                            logger.debug(
                                f"✎ Duplicate Given→And: '{line.strip()}'"
                            )
                        else:
                            given_seen = True

                fixed_lines.append(line)

            result.append("\n".join(fixed_lines))

        return "".join(result)

    def _fix_error_messages(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            lower = line.lower()
            for wrong, correct in _ERROR_REWRITES.items():
                if wrong in lower:
                    if correct is None:
                        if "displays" in lower:
                            line = re.sub(
                                r'"[^"]*"',
                                '"You are not authorized to perform this action"',
                                line,
                                flags=re.IGNORECASE,
                            )
                    else:
                        line = re.sub(
                            rf'"{re.escape(wrong)}"',
                            f'"{correct}"',
                            line,
                            flags=re.IGNORECASE,
                        )
                    break
            lines.append(line)
        return "\n".join(lines)

    def _fix_unresolved_placeholders(self, text: str) -> str:
        lines = text.splitlines()
        result = []
        in_outline = False
        in_examples = False
        for line in lines:
            stripped = line.strip()
            if _RE_SCENARIO_OUTLINE.match(stripped):
                in_outline = True
                in_examples = False
            elif _RE_SCENARIO_PLAIN.match(stripped):
                in_outline = False
                in_examples = False
            if _RE_EXAMPLES.match(stripped):
                in_examples = True

            if not in_outline and not in_examples:
                for key, value in _PLACEHOLDER_FALLBACKS.items():
                    line = re.sub(
                        rf"<{re.escape(key)}>", value, line, flags=re.IGNORECASE
                    )
                for token in re.findall(r"<([^>|\s]+)>", line):
                    fallback = token.replace("_", " ").title()
                    logger.warning(
                        f"⚠ Unresolved placeholder <{token}> → '{fallback}'"
                    )
                    line = line.replace(f"<{token}>", f'"{fallback}"')
            result.append(line)
        return "\n".join(result)

    def _remove_status_from_background(self, text: str) -> str:
        lines = text.splitlines()
        result = []
        in_background = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Background:"):
                in_background = True
                result.append(line)
                continue
            if in_background and re.match(r"^\s*Scenario", line):
                in_background = False
            if in_background and _RE_STATUS.search(stripped):
                logger.warning(
                    f"⚠ Removed status step from Background: '{stripped}'"
                )
                continue
            result.append(line)
        return "\n".join(result)

    def _remove_broken_scenarios(self, text: str) -> str:
        parts = _RE_SCENARIO_SPLIT.split(text)

        outline_signatures: set = set()
        for block in parts:
            if not block.strip().startswith("Scenario Outline:"):
                continue
            for line in block.splitlines():
                if re.match(r"^\s*When\s+", line):
                    sig = line.strip().lower()
                    sig = re.sub(r"<[^>]+>", ".*", sig)
                    sig = re.sub(r'"[^"]*"', '".*"', sig)
                    outline_signatures.add(sig)

        result: List[str] = []
        for block in parts:
            stripped = block.strip()
            if not stripped.startswith("Scenario:"):
                result.append(block)
                continue

            header = block.splitlines()[0].strip()
            then_count = len(re.findall(r"^\s*Then\s+", block, re.MULTILINE))

            if then_count == 0:
                logger.warning(f"⚠ Removed broken scenario (no Then): '{header}'")
                continue

            is_outline_duplicate = False
            for line in block.splitlines():
                if re.match(r"^\s*When\s+", line):
                    sig = re.sub(r'"[^"]*"', '".*"', line.strip().lower())
                    if sig in outline_signatures:
                        logger.warning(
                            f"⚠ Removed duplicate scenario (covered by Outline): '{header}'"
                        )
                        is_outline_duplicate = True
                        break
            if is_outline_duplicate:
                continue

            result.append(block)

        return "".join(result)

    def _fix_intermediate_approver_success_message(self, text: str) -> str:
        _RE_FINAL_STATE = re.compile(
            r'status\s+(?:changes?\s+to|is\s+now|becomes?)\s+"(?:Granted|Approved|Completed|Published)"',
            re.IGNORECASE,
        )
        _RE_BALANCE_ADJUST = re.compile(
            r"\b(balance|quota|allowance|credit|deducted|adjusted)\b",
            re.IGNORECASE,
        )

        parts = _RE_SCENARIO_SPLIT.split(text)
        result: List[str] = []

        for block in parts:
            stripped_block = block.strip()
            if not stripped_block.startswith("Scenario:"):
                result.append(block)
                continue

            lines = block.splitlines()
            setup_text = " ".join(
                l for l in lines
                if re.match(r"^\s*(Given|And)\s+", l, re.IGNORECASE)
            )
            then_text = " ".join(
                l for l in lines
                if re.match(r"^\s*(Then|And)\s+", l, re.IGNORECASE)
            )

            is_intermediate = bool(_RE_INTERMEDIATE_APPROVER.search(setup_text))
            has_final_state  = bool(_RE_FINAL_STATE.search(then_text))
            has_balance_step = bool(_RE_BALANCE_ADJUST.search(then_text))

            if is_intermediate and not (has_final_state and has_balance_step):
                fixed_lines = []
                for line in lines:
                    if _RE_SUCCESS_MESSAGE.match(line):
                        logger.warning(
                            f"✎ Removed success message from intermediate-approver "
                            f"scenario: '{line.strip()}'"
                        )
                        continue
                    fixed_lines.append(line)
                result.append("\n".join(fixed_lines))
            else:
                result.append(block)

        return "".join(result)

    def _quote_status_values_in_examples(self, text: str) -> str:
        lines = text.splitlines()
        result = []
        in_outline = False
        in_examples = False

        for line in lines:
            stripped = line.strip()
            if _RE_SCENARIO_OUTLINE.match(stripped):
                in_outline = True
                in_examples = False
            elif _RE_SCENARIO_PLAIN.match(stripped):
                in_outline = False
                in_examples = False
            if _RE_EXAMPLES.match(stripped):
                in_examples = True

            if in_outline and not in_examples:
                fixed = re.sub(
                    r'(?<!")<(status|state|type|category|phase|stage|result|outcome)>(?!")',
                    r'"<\1>"',
                    line,
                    flags=re.IGNORECASE,
                )
                if fixed != line:
                    logger.debug(
                        f"✎ Wrapped bare placeholder: '{line.strip()}' → '{fixed.strip()}'"
                    )
                line = fixed

            result.append(line)

        return "\n".join(result)

    def _strip_quotes_from_examples(self, text: str) -> str:
        lines = text.splitlines()
        result = []
        in_examples = False
        for line in lines:
            stripped = line.strip()
            if _RE_EXAMPLES.match(stripped):
                in_examples = True
                result.append(line)
                continue
            if in_examples and re.match(r"^\s*Scenario", stripped):
                in_examples = False
            if in_examples and "|" in stripped:
                new_line = re.sub(r'(\|\s*)"(.*?)"(?=\s*\|)', r'\1\2', line)
                result.append(new_line)
            else:
                result.append(line)
        return "\n".join(result)

    def _fix_empty_examples_tables(self, text: str) -> str:
        """
        Cucumber 7 crashes with NoSuchElementException when a Scenario Outline
        has an Examples table with no header row, or fewer than 2 rows total,
        or mismatched column counts between header and data rows.

        Converts any such broken Outline into a plain Scenario, replacing
        <placeholder> tokens with literal "value" so the scenario is still
        runnable.
        """
        parts = _RE_SCENARIO_SPLIT.split(text)
        result: List[str] = []

        for block in parts:
            stripped = block.strip()
            if not stripped.startswith("Scenario Outline:"):
                result.append(block)
                continue

            ex_match = re.search(r"^\s*Examples\s*:", block, re.MULTILINE)
            if not ex_match:
                # No Examples section at all — demote to plain Scenario
                fixed = re.sub(
                    r"^(\s*)Scenario Outline\s*:",
                    r"\1Scenario:",
                    block, count=1, flags=re.MULTILINE,
                )
                fixed = re.sub(r"<[^>]+>", "value", fixed)
                logger.warning("✎ Converted Outline→Scenario (no Examples section)")
                result.append(fixed)
                continue

            after_ex = block[ex_match.end():]
            table_rows = [
                l for l in after_ex.splitlines()
                if l.strip().startswith("|") and l.strip().endswith("|")
            ]

            valid = True
            if len(table_rows) < 2:
                valid = False
            else:
                header_cols = [c.strip() for c in table_rows[0].split("|") if c.strip()]
                if not header_cols:
                    valid = False
                else:
                    for data_row in table_rows[1:]:
                        data_cols = [c.strip() for c in data_row.split("|") if c.strip()]
                        if len(data_cols) != len(header_cols):
                            valid = False
                            break

            if not valid:
                fixed = re.sub(
                    r"^(\s*)Scenario Outline\s*:",
                    r"\1Scenario:",
                    block, count=1, flags=re.MULTILINE,
                )
                fixed = re.sub(
                    r"\n\s*Examples\s*:.*",
                    "",
                    fixed,
                    flags=re.DOTALL,
                )
                fixed = re.sub(r"<[^>]+>", "value", fixed)
                logger.warning(
                    f"✎ Converted Outline→Scenario "
                    f"(Examples table invalid: {len(table_rows)} rows)"
                )
                result.append(fixed)
            else:
                result.append(block)

        return "".join(result)

    def _fix_or_in_given(self, text: str) -> str:
        lines = text.splitlines()
        result = []
        in_outline = False
        in_examples = False
        for line in lines:
            stripped = line.strip()
            if _RE_SCENARIO_OUTLINE.match(stripped):
                in_outline = True
                in_examples = False
            elif _RE_SCENARIO_PLAIN.match(stripped):
                in_outline = False
                in_examples = False
            if _RE_EXAMPLES.match(stripped):
                in_examples = True
            if not in_outline and not in_examples:
                if re.match(r"^\s*(Given|And)\s+", line, re.IGNORECASE):
                    fixed = re.sub(r'(\s+or\s+"[^"]*")+', "", line)
                    if fixed != line:
                        logger.debug(
                            f'✎ Removed "or": "{line.strip()}" → "{fixed.strip()}"'
                        )
                    line = fixed
            result.append(line)
        return "\n".join(result)

    def _collapse_duplicate_nominal_scenarios(self, text: str) -> str:
        _RE_SUCCESS_THEN = re.compile(
            r'^\s*(Then|And)\s+.+('
            r'successfully|"Pending"|unique\s+(id|number)|'
            r'saved|finalized|generated|adminApproval|managerApproval'
            r')',
            re.IGNORECASE,
        )
        _RE_ERROR_THEN = re.compile(
            r'^\s*(Then|And)\s+.*(error|blocks?\s+the\s+action|"Warning)',
            re.IGNORECASE,
        )

        def _is_nominal(block: str) -> bool:
            lines = block.splitlines()
            has_success = any(_RE_SUCCESS_THEN.match(l) for l in lines)
            has_error   = any(_RE_ERROR_THEN.match(l) for l in lines)
            return has_success and not has_error

        parts = _RE_SCENARIO_SPLIT.split(text)
        nominal_seen = False
        result: List[str] = []

        for block in parts:
            stripped = block.strip()
            if not stripped.startswith("Scenario:"):
                result.append(block)
                continue

            if _is_nominal(block):
                if nominal_seen:
                    title = block.splitlines()[0].strip()
                    logger.warning(
                        f"⚠ Collapsed duplicate nominal scenario: '{title}'"
                    )
                    continue
                nominal_seen = True

            result.append(block)

        return "".join(result)

    def _merge_same_error_scenarios(self, text: str) -> str:
        def _extract_error_msg(block: str) -> str:
            for line in block.splitlines():
                m = re.match(
                    r'^\s*(?:Then|And)\s+the\s+(?:system\s+)?'
                    r'(?:displays?|shows?)\s+(?:the\s+)?(?:error\s+)?'
                    r'"([^"]+)"',
                    line, re.IGNORECASE,
                )
                if m:
                    return m.group(1).strip()
            return ""

        def _step_lines(block: str) -> List[str]:
            return [
                l for l in block.splitlines()
                if re.match(r"^\s*(Given|When|Then|And|But)\s+", l, re.IGNORECASE)
            ]

        parts = _RE_SCENARIO_SPLIT.split(text)

        from collections import defaultdict
        error_groups: dict = defaultdict(list)

        for i, block in enumerate(parts):
            if not block.strip().startswith("Scenario:"):
                continue
            err = _extract_error_msg(block)
            if err:
                error_groups[err].append(i)

        merged_into: dict   = {}
        drop_indices: set   = set()

        for err_msg, indices in error_groups.items():
            if len(indices) < 2:
                continue

            step_counts = [len(_step_lines(parts[i])) for i in indices]
            if len(set(step_counts)) != 1:
                continue

            rows: List[List[str]] = []
            col_names: List[str] = []

            def _values_from(block: str) -> List[str]:
                vals = []
                for line in _step_lines(block):
                    if re.match(r"^\s*(Then|And)\s+", line, re.IGNORECASE):
                        break
                    found = re.findall(r'"([^"]+)"|\b(\d{4}-\d{2}-\d{2})\b|\b(\d{2}:\d{2})\b', line)
                    for groups in found:
                        v = next((g for g in groups if g), None)
                        if v:
                            vals.append(v)
                return vals

            first_vals = _values_from(parts[indices[0]])
            if not first_vals:
                continue

            col_names = [f"value{n+1}" for n in range(len(first_vals))]

            valid = True
            for idx in indices:
                row = _values_from(parts[idx])
                if len(row) != len(first_vals):
                    valid = False
                    break
                rows.append(row)

            if not valid:
                continue

            first_block = parts[indices[0]]
            first_lines  = first_block.splitlines()
            ind = "  "
            for l in first_lines:
                if re.match(r"^\s+(Given|When|Then|And|But)\s+", l, re.IGNORECASE):
                    ind = re.match(r"^(\s+)", l).group(1)
                    break

            first_title = first_lines[0].strip()
            first_title = re.sub(r"^Scenario:\s*", "", first_title)
            generic_title = re.sub(
                r"\b(Annual|Unpaid|Authorization|Recovery|daily|hourly)\b",
                "", first_title, flags=re.IGNORECASE,
            ).strip()
            generic_title = re.sub(r"\s{2,}", " ", generic_title)

            outline_lines = [f"{ind}Scenario Outline: {generic_title}"]

            value_to_col: dict = {}
            for n, v in enumerate(first_vals):
                value_to_col[v] = col_names[n]

            for line in first_lines[1:]:
                if re.match(r"^\s*(Then|And)\s+", line, re.IGNORECASE):
                    outline_lines.append(
                        f"{ind}  Then the system displays the error \"{err_msg}\""
                    )
                    break
                replaced = line
                for v, col in value_to_col.items():
                    replaced = replaced.replace(f'"{v}"', f'<{col}>')
                    replaced = replaced.replace(v, f'<{col}>')
                outline_lines.append(replaced)

            col_widths = [
                max(len(c), max(len(r[n]) for r in rows))
                for n, c in enumerate(col_names)
            ]
            header = "| " + " | ".join(
                c.ljust(col_widths[n]) for n, c in enumerate(col_names)
            ) + " |"
            outline_lines.append("")
            outline_lines.append(f"{ind}  Examples:")
            outline_lines.append(f"{ind}    {header}")
            for row in rows:
                row_str = "| " + " | ".join(
                    v.ljust(col_widths[n]) for n, v in enumerate(row)
                ) + " |"
                outline_lines.append(f"{ind}    {row_str}")

            merged_into[indices[0]] = "\n".join(outline_lines) + "\n"
            for idx in indices[1:]:
                drop_indices.add(idx)

            title_short = generic_title[:60]
            logger.info(
                f"↔ Merged {len(indices)} same-error scenarios → Outline: '{title_short}'"
            )

        result = []
        for i, block in enumerate(parts):
            if i in drop_indices:
                continue
            if i in merged_into:
                result.append(merged_into[i])
            else:
                result.append(block)
        return "".join(result)

    def _clean_output(self, text: str) -> str:
        text = re.sub(
            r"(\S)([ \t]{2,})(Scenario(?:\s+Outline)?\s*:)",
            r"\1\n\n  \3",
            text,
        )
        text = re.sub(
            r"(?<!\n)\n(?=[ \t]*Scenario(?:\s+Outline)?\s*:)",
            "\n\n",
            text,
        )
        text = re.sub(
            r"(?<!\n)\n(?=[ \t]*Background\s*:)", "\n\n", text
        )
        lines = [line.rstrip() for line in text.strip().splitlines()]
        cleaned = "\n".join(lines)
        if not cleaned.endswith("\n"):
            cleaned += "\n"
        return cleaned

    # ──────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────

    def save_feature_file(
        self,
        content: str,
        service_name: str = "feature",
        index: int = 1,
    ) -> Path:
        features_dir: Path = self.settings.paths.features_dir
        features_dir.mkdir(parents=True, exist_ok=True)

        for old in features_dir.glob(f"{re.sub(r'[^a-z0-9]+', '-', service_name.lower()).strip('-')}_*.feature"):
            old.unlink()
            logger.info(f"   🗑 Removed old feature: {old.name}")

        match = re.search(r"^Feature:\s*(.+)", content, re.MULTILINE)
        if match:
            slug = re.sub(
                r"[^a-z0-9]+", "-", match.group(1).lower()
            ).strip("-")[:40]
        else:
            slug = f"story-{index}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_svc = re.sub(r"[^a-z0-9]+", "-", service_name.lower()).strip("-")
        filename = f"{safe_svc}_{slug}_{timestamp}.feature"
        filepath = features_dir / filename

        if not content.endswith("\n"):
            content += "\n"

        filepath.write_text(content, encoding="utf-8", newline="\n")
        logger.success(f"💾 Saved .feature → {filepath}")
        return filepath

    # ──────────────────────────────────────────────────────────────────
    # SINGLE GENERATION
    # ──────────────────────────────────────────────────────────────────

    def generate_single(self, story: str, swagger_context: str = "") -> str:
        prompt = self._create_prompt()
        chain = prompt | self.llm

        _RETRY_SYSTEM = (
            "You are a Gherkin file generator. "
            "CRITICAL: Your ENTIRE response must be a valid Gherkin .feature file. "
            "Start with 'Feature:' on the very first line. "
            "No reviews, no markdown, no bullet points, no explanations whatsoever."
        )
        _RETRY_HUMAN = (
            "Generate the Gherkin .feature file for this specification. "
            "First line MUST be 'Feature:':\n\n"
            "{story}\n\n{swagger_context}\n\nFeature:"
        )
        _retry_prompt = ChatPromptTemplate.from_messages([
            ("system", _RETRY_SYSTEM),
            ("human",  _RETRY_HUMAN),
        ])

        max_attempts = 3
        raw = ""
        active_chain = chain
        for attempt in range(1, max_attempts + 1):
            logger.info(f"🤖 Calling LLM… (attempt {attempt}/{max_attempts})")
            response = active_chain.invoke({
                "story": story,
                "swagger_context": swagger_context,
            })

            if hasattr(response, "content"):
                raw = response.content
            elif isinstance(response, str):
                raw = response
            else:
                raw = str(response)

            if re.search(r"^Feature:", raw, re.MULTILINE):
                break

            logger.warning(
                f"⚠ Attempt {attempt}: LLM produced no Feature: block "
                f"(first 200 chars: {repr(raw[:200])}). Retrying."
            )
            active_chain = _retry_prompt | self.llm

            if attempt == max_attempts:
                logger.error(
                    "❌ LLM failed to produce a Gherkin Feature: block "
                    f"after {max_attempts} attempts."
                )

        # ── Post-processing pipeline (order matters) ──────────────────
        raw = self._clean_markdown(raw)
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
        raw = self._fix_empty_examples_tables(raw)      # FIX: was defined but never called
        raw = self._quote_status_values_in_examples(raw)
        raw = self._strip_quotes_from_examples(raw)
        raw = self._clean_output(raw)

        return raw

    # ──────────────────────────────────────────────────────────────────
    # LANGGRAPH ENTRY POINT
    # ──────────────────────────────────────────────────────────────────

    def generate(self, state: TestAutomationState) -> TestAutomationState:
        start = time.time()
        logger.info(
            f"🚀 Gherkin Generator starting — service: {state.service_name}"
        )

        try:
            if state.swagger_specs:
                swagger_context = self._format_swagger_specs(state.swagger_specs)
            elif state.swagger_spec:
                swagger_context = self._format_swagger_specs(
                    {"primary": state.swagger_spec}
                )
            else:
                swagger_context = ""

            features = self.extract_features(state.user_story)
            if not features:
                raise ValueError(
                    "No feature specifications found in user_story input"
                )

            logger.info(f"📌 {len(features)} feature(s) to generate")

            all_contents: List[str] = []
            all_files: List[str] = []

            for idx, story_block in enumerate(features, start=1):
                if not story_block.strip():
                    continue

                content = self.generate_single(story_block, swagger_context)
                filepath = self.save_feature_file(
                    content, state.service_name, idx
                )
                all_contents.append(content)
                all_files.append(str(filepath))

            state.gherkin_content = "\n\n".join(all_contents)
            state.gherkin_files = all_files

            duration_ms = (time.time() - start) * 1000
            state.add_agent_output(
                AgentOutput(
                    agent_name="gherkin_generator",
                    status=AgentStatus.SUCCESS,
                    duration_ms=duration_ms,
                    output_data={
                        "features_extracted": len(features),
                        "feature_files": all_files,
                    },
                )
            )

            logger.success(
                f"✅ Gherkin generated — {len(all_files)} file(s) in {duration_ms:.0f} ms"
            )

        except Exception:
            duration_ms = (time.time() - start) * 1000
            tb = traceback.format_exc()
            logger.error(f"❌ Gherkin generation failed:\n{tb}")
            state.add_agent_output(
                AgentOutput(
                    agent_name="gherkin_generator",
                    status=AgentStatus.FAILED,
                    duration_ms=duration_ms,
                    error_message=tb,
                )
            )
            state.add_error(f"Gherkin generation failed: {tb}")

        return state


def gherkin_generator_node(state: TestAutomationState) -> TestAutomationState:
    return GherkinGeneratorAgent().generate(state)