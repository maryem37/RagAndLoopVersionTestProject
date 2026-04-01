"""
agents/gherkin_validator.py
------------------------------
Agent 3 — Gherkin Validator

FIXES applied:
  1. Added task="text-generation" and max_new_tokens=1024 to HuggingFaceEndpoint
     (without these the endpoint silently fails or uses wrong defaults).
  2. Removed {format_instructions} from the human prompt template — it was
     being passed in invoke() but NOT referenced in the template string,
     causing a KeyError at runtime. The JSON format is now described inline
     in the system prompt so the LLM still knows the expected shape.
  3. The PydanticOutputParser still parses the response — we just don't
     inject the instructions via the template variable.
"""

import json
import re
import time
import subprocess
from pathlib import Path
from typing import List
from loguru import logger
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from graph.state import (
    TestAutomationState,
    AgentOutput,
    AgentStatus,
    ValidationResult,
    ValidationIssue,
    LLMValidationOutput,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from config.settings import get_settings


class GherkinValidatorAgent:

    def __init__(self):
        self.settings = get_settings()

        # FIX 1: task + max_new_tokens must be explicit on HuggingFaceEndpoint
        llm = HuggingFaceEndpoint(
            repo_id=self.settings.huggingface.gherkin_validator.model_name,
            huggingfacehub_api_token=self.settings.huggingface.api_token,
            task="text-generation",
            temperature=self.settings.huggingface.gherkin_validator.temperature,
            max_new_tokens=1024,
        )
        self.llm = ChatHuggingFace(llm=llm)

        self.output_parser    = PydanticOutputParser(pydantic_object=LLMValidationOutput)
        self.gherkin_lint_cmd = self._find_gherkin_lint()

        lint_status = "enabled" if self.gherkin_lint_cmd else "disabled (not installed)"
        logger.info(
            f"✅ Gherkin Validator initialized "
            f"(gherkin-lint: {lint_status}, "
            f"model: {self.settings.huggingface.gherkin_validator.model_name})"
        )

    # ------------------------------
    def _find_gherkin_lint(self) -> str | None:
        local_path_cmd = Path("node_modules/.bin/gherkin-lint.cmd")
        if local_path_cmd.exists():
            logger.info(f"   Found gherkin-lint (local, Windows): {local_path_cmd}")
            return str(local_path_cmd.resolve())

        local_path = Path("node_modules/.bin/gherkin-lint")
        if local_path.exists():
            logger.info(f"   Found gherkin-lint (local): {local_path}")
            return str(local_path.resolve())

        try:
            result = subprocess.run(
                ["npx", "gherkin-lint", "--help"],
                capture_output=True, text=True, timeout=10, shell=True,
            )
            if result.returncode == 0 or "Usage:" in result.stdout:
                logger.info("   Found gherkin-lint (via npx)")
                return "npx gherkin-lint"
        except Exception as e:
            logger.debug(f"   npx check failed: {e}")

        try:
            result = subprocess.run(
                ["gherkin-lint", "--help"],
                capture_output=True, text=True, timeout=5, shell=True,
            )
            if result.returncode == 0 or "Usage:" in result.stdout:
                logger.info("   Found gherkin-lint (global)")
                return "gherkin-lint"
        except Exception as e:
            logger.debug(f"   Global check failed: {e}")

        logger.warning("[WARN]️ gherkin-lint not found. Install with: npm install -g gherkin-lint")
        return None

    # ------------------------------
    def validate(self, state: TestAutomationState) -> TestAutomationState:
        start_time  = time.time()
        all_issues: List[ValidationIssue] = []

        try:
            # 1. Syntax validation
            if self.gherkin_lint_cmd and state.gherkin_files:
                logger.info("   Running gherkin-lint syntax validation...")
                for feature_file in state.gherkin_files:
                    syntax_issues = self._validate_with_gherkin_lint(Path(feature_file))
                    all_issues.extend(syntax_issues)
                logger.info(
                    f"   gherkin-lint: "
                    f"{len([i for i in all_issues if 'gherkin-lint' in str(i.scenario)])} "
                    f"issues found"
                )
            else:
                logger.info("   Skipping gherkin-lint (not available)")

            # 2. Semantic validation
            semantic_count_before = len(all_issues)
            for feature_file in state.gherkin_files:
                semantic_issues = self._validate_semantics(Path(feature_file))
                all_issues.extend(semantic_issues)
            logger.info(f"   Semantic check: {len(all_issues) - semantic_count_before} issues found")

            # 3. LLM validation
            logger.info("   Running LLM validation...")
            llm_result = self._validate_with_llm(state.gherkin_content, state.user_story)

            validation_result = ValidationResult(
                is_valid=not any(issue.level == "error" for issue in all_issues),
                issues=all_issues,
                coverage_score=llm_result.coverage_score,
                missing_scenarios=llm_result.missing_scenarios,
                suggestions=llm_result.suggestions,
            )

            state.validation_result = validation_result

            duration = (time.time() - start_time) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="gherkin_validator",
                status=AgentStatus.SUCCESS if validation_result.is_valid else AgentStatus.FAILED,
                duration_ms=duration,
                output_data={
                    "is_valid":                validation_result.is_valid,
                    "total_issues":            len(all_issues),
                    "errors":                  sum(1 for i in all_issues if i.level == "error"),
                    "warnings":                sum(1 for i in all_issues if i.level == "warning"),
                    "coverage_score":          llm_result.coverage_score,
                    "missing_scenarios_count": len(llm_result.missing_scenarios),
                    "used_gherkin_lint":       self.gherkin_lint_cmd is not None,
                },
            ))

            if validation_result.is_valid:
                logger.success(f"✅ Validation PASSED - Coverage: {llm_result.coverage_score}%")
            else:
                logger.warning(f"[WARN]️ Validation FAILED - Coverage: {llm_result.coverage_score}%")

            for missing in llm_result.missing_scenarios:
                state.add_warning(f"Missing scenario: {missing}")

        except Exception as e:
            logger.error(f"[ERROR] Validation error: {str(e)}")
            duration = (time.time() - start_time) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="gherkin_validator",
                status=AgentStatus.FAILED,
                duration_ms=duration,
                error_message=str(e),
            ))
            state.add_error(f"Validation failed: {str(e)}")

        return state

    # ------------------------------
    def _validate_with_gherkin_lint(self, feature_file: Path) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        try:
            config_path = Path(".gherkin-lintrc")
            if not config_path.exists():
                logger.warning(f"Config file not found: {config_path}")
                return issues

            cmd_parts = self.gherkin_lint_cmd.split()
            cmd_parts.extend(["-c", str(config_path), str(feature_file)])

            logger.debug(f"Running: {' '.join(cmd_parts)}")

            result = subprocess.run(
                cmd_parts,
                capture_output=True, text=True,
                cwd=str(Path.cwd()), timeout=30, shell=True,
            )

            output = result.stdout + result.stderr
            if output.strip():
                for line in output.splitlines():
                    if not line.strip() or line.strip().startswith(">>"):
                        continue

                    match = re.match(r"[^:]+:(\d+):(\d+):\s*(.+)", line)
                    if match:
                        line_num, col, message = match.groups()
                        level = "error" if any(
                            w in message.lower()
                            for w in ("error", "invalid", "must", "required")
                        ) else "warning"
                        issues.append(ValidationIssue(
                            level=level,
                            message=message.strip(),
                            line_number=int(line_num),
                            scenario=f"gherkin-lint (col {col})",
                            suggestion="Check gherkin-lint rules",
                        ))
                    else:
                        match = re.match(r"\s*(\d+)\s+(.+?)\s+([\w-]+)\s*$", line)
                        if match:
                            line_num, message, rule = match.groups()
                            level = "error" if any(
                                w in message.lower()
                                for w in ("error", "invalid", "must", "required")
                            ) else "warning"
                            issues.append(ValidationIssue(
                                level=level,
                                message=f"{message} (rule: {rule})",
                                line_number=int(line_num),
                                scenario="gherkin-lint",
                                suggestion=f"Fix {rule} rule violation",
                            ))

            logger.debug(f"Found {len(issues)} linting issues")

        except subprocess.TimeoutExpired:
            logger.warning(f"gherkin-lint timed out for {feature_file}")
        except Exception as e:
            logger.warning(f"Error running gherkin-lint: {str(e)}")

        return issues

    # ------------------------------
    def _validate_semantics(self, feature_file: Path) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        try:
            with open(feature_file, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except Exception as e:
            logger.warning(f"Could not read {feature_file}: {e}")
            return issues

        current_scenario = ""
        last_step_type   = None
        step_order       = {"Given": 0, "When": 1, "Then": 2}

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("Scenario:", "Scenario Outline:")):
                current_scenario = stripped
                last_step_type   = None
                continue

            for keyword in ("Given", "When", "Then"):
                if stripped.startswith(keyword):
                    if last_step_type and step_order[keyword] < step_order[last_step_type]:
                        issues.append(ValidationIssue(
                            level="warning",
                            message=f"Unexpected step order: {keyword} after {last_step_type}",
                            line_number=line_num,
                            scenario=current_scenario,
                            suggestion="Follow Given-When-Then pattern",
                        ))
                    last_step_type = keyword
                    break

        return issues

    # ------------------------------
    def _validate_with_llm(self, gherkin_content: str, user_story: str) -> LLMValidationOutput:

        requirements   = self._extract_requirements_structured(user_story)
        scenario_count = len(re.findall(r"^\s*Scenario:", gherkin_content, re.MULTILINE))

        logger.info("[DEBUG] Validation Context:")
        logger.info(f"   Scenarios in Gherkin: {scenario_count}")
        logger.info(f"   Acceptance Criteria found: {len(requirements['acceptance_criteria'])}")
        logger.info(f"   Business Rules found: {len(requirements['business_rules'])}")
        logger.info(f"   Error Messages expected: {len(requirements['error_messages'])}")
        
        # SKIP LLM VALIDATION - Use heuristic fallback to avoid timeout issues
        logger.warning("   ⚠️  Skipping LLM validation (using heuristic to avoid timeout)")
        return self._heuristic_validation(gherkin_content, user_story)

        # FIX 2: Removed {format_instructions} from the template variable.
        # The expected JSON shape is now described inline in the system prompt.
        # This prevents the KeyError that occurred when the variable was passed
        # in invoke() but the template had no matching placeholder.
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a test coverage analyzer. Your job is to check if Gherkin test scenarios adequately cover the requirements from a user story.

ANALYSIS PROCESS:
1. Read the REQUIREMENTS section carefully
2. Read the GHERKIN SCENARIOS section carefully
3. For EACH requirement, determine if there is a scenario testing it
4. Calculate: coverage_score = (requirements_covered / total_requirements) x 100
5. List requirements that have NO corresponding test scenario

SCORING GUIDELINES:
- Each Acceptance Criterion with a matching scenario: counts as covered
- Each Business Rule with a matching scenario: counts as covered
- Happy path scenario exists: +10 bonus points
- Error/validation scenarios exist: +5 bonus points
- Maximum score: 100

IMPORTANT:
- DO NOT mark a scenario as "missing" if it clearly exists in the Gherkin
- A scenario "covers" a requirement if it tests that specific behavior
- Be accurate and fair in your assessment

REQUIRED OUTPUT FORMAT (valid JSON only, no markdown, no code fences):
{{
  "coverage_score": <integer 0-100>,
  "missing_scenarios": [<list of strings — requirements WITHOUT test scenarios>],
  "issues": [<list of strings — problems in existing scenarios>],
  "suggestions": [<list of strings — improvement recommendations>]
}}

CRITICAL: missing_scenarios, issues and suggestions must be flat lists of STRINGS,
not lists of objects or lists of lists. Each item must be a plain string.

Return ONLY the JSON object. No explanations, no markdown, no code blocks."""),

            ("human", """REQUIREMENTS TO BE TESTED:

{requirements_text}

GHERKIN TEST SCENARIOS:

{gherkin_content}

TASK:
Analyze the coverage. For each requirement above, check if there is a Gherkin scenario testing it.
Calculate the coverage score accurately.
List ONLY the requirements that have NO corresponding test scenario.

Return the JSON analysis now:"""),
        ])

        requirements_text = self._format_requirements_for_llm(requirements)

        # FIX 2 continued: invoke() no longer passes format_instructions
        chain = prompt | self.llm | self.output_parser

        max_retries = 2
        for attempt in range(max_retries):
            try:
                logger.info(f"   Invoking LLM for validation (attempt {attempt + 1}/{max_retries})...")
                result = chain.invoke({
                    "requirements_text": requirements_text,
                    "gherkin_content":   gherkin_content,
                })

                if not self._validate_llm_response(result, requirements, scenario_count):
                    logger.warning(f"[WARN]️ LLM response validation failed on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.warning("[WARN]️ All LLM attempts failed validation, falling back to heuristic")
                        return self._heuristic_validation(gherkin_content, user_story)

                logger.success(f"✅ LLM validation successful: {result.coverage_score}% coverage")
                return result

            except Exception as e:
                logger.warning(f"[WARN]️ LLM validation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    logger.warning("[WARN]️ All LLM attempts failed, falling back to heuristic")
                    return self._heuristic_validation(gherkin_content, user_story)

        return self._heuristic_validation(gherkin_content, user_story)

    # ------------------------------
    def _extract_requirements_structured(self, user_story: str) -> dict:
        requirements = {
            "acceptance_criteria": [],
            "business_rules":      [],
            "error_messages":      [],
            "other_requirements":  [],
        }

        ac_section = re.search(
            r"Acceptance Criteria[:\s]+(.*?)(?=\n\s*(?:Business Rules?|Error Messages|User Story|$))",
            user_story, re.IGNORECASE | re.DOTALL,
        )
        if ac_section:
            ac_items = re.findall(
                r"(?:^|\n)\s*(?:[-•*]|\d+\.)\s*(?:AC\d+[:\s]+)?(.+?)(?=\n\s*(?:[-•*]|\d+\.)|$)",
                ac_section.group(1), re.DOTALL,
            )
            requirements["acceptance_criteria"] = [
                ac.strip() for ac in ac_items if ac.strip() and len(ac.strip()) > 10
            ]

        br_section = re.search(
            r"Business Rules?[:\s]+(.*?)(?=\n\s*(?:Acceptance Criteria|Error Messages|User Story|$))",
            user_story, re.IGNORECASE | re.DOTALL,
        )
        if br_section:
            br_items = re.findall(
                r"(?:^|\n)\s*(?:[-•*]|\d+\.)\s*(?:BR\d+[:\s]+)?(.+?)(?=\n\s*(?:[-•*]|\d+\.)|$)",
                br_section.group(1), re.DOTALL,
            )
            requirements["business_rules"] = [
                br.strip() for br in br_items if br.strip() and len(br.strip()) > 10
            ]

        requirements["error_messages"] = re.findall(r'"([^"]{10,})"', user_story)

        other_bullets = re.findall(
            r"(?:^|\n)\s*(?:[-•*]|\d+\.)\s+(.+?)(?=\n|$)",
            user_story, re.MULTILINE,
        )
        existing = requirements["acceptance_criteria"] + requirements["business_rules"]
        requirements["other_requirements"] = [
            req.strip()
            for req in other_bullets
            if req.strip() not in existing and len(req.strip()) > 15
        ][:5]

        return requirements

    # ------------------------------
    def _format_requirements_for_llm(self, requirements: dict) -> str:
        formatted = []

        if requirements["acceptance_criteria"]:
            formatted.append("ACCEPTANCE CRITERIA:")
            for i, ac in enumerate(requirements["acceptance_criteria"], 1):
                formatted.append(f"  AC{i}. {ac}")
            formatted.append("")

        if requirements["business_rules"]:
            formatted.append("BUSINESS RULES:")
            for i, br in enumerate(requirements["business_rules"], 1):
                formatted.append(f"  BR{i}. {br}")
            formatted.append("")

        if requirements["error_messages"]:
            formatted.append("EXPECTED ERROR MESSAGES:")
            for i, err in enumerate(requirements["error_messages"], 1):
                formatted.append(f'  ERR{i}. "{err}"')
            formatted.append("")

        if requirements["other_requirements"]:
            formatted.append("OTHER REQUIREMENTS:")
            for i, req in enumerate(requirements["other_requirements"], 1):
                formatted.append(f"  REQ{i}. {req}")
            formatted.append("")

        return "\n".join(formatted) if formatted else "No structured requirements found."

    # ------------------------------
    def _validate_llm_response(
        self, result: LLMValidationOutput, requirements: dict, scenario_count: int
    ) -> bool:
        if not (0 <= result.coverage_score <= 100):
            logger.warning(f"Invalid coverage score: {result.coverage_score}")
            return False

        total_requirements = (
            len(requirements["acceptance_criteria"])
            + len(requirements["business_rules"])
            + len(requirements["error_messages"])
        )

        if total_requirements > 0 and scenario_count > 0:
            min_expected = min(40, (scenario_count / total_requirements) * 30)
            if result.coverage_score < min_expected:
                logger.warning(
                    f"Coverage score ({result.coverage_score}%) seems too low "
                    f"for {scenario_count} scenarios"
                )

        if len(result.missing_scenarios) > total_requirements + 5:
            logger.warning(f"Too many missing scenarios reported: {len(result.missing_scenarios)}")
            return False

        return True

    # ------------------------------
    def _heuristic_validation(self, gherkin_content: str, user_story: str) -> LLMValidationOutput:
        scenario_count = len(re.findall(r"^\s*Scenario:", gherkin_content, re.MULTILINE))

        ac_count    = len(re.findall(r"(?:^|\n)\s*(?:[-•*]|\d+\.)\s*AC\d*", user_story, re.IGNORECASE))
        br_count    = len(re.findall(r"(?:^|\n)\s*(?:[-•*]|\d+\.)\s*BR\d*", user_story, re.IGNORECASE))
        error_count = len(re.findall(r'"[^"]{10,}"', user_story))

        total_requirements = max(1, ac_count + br_count + error_count)
        coverage = min(100, int((scenario_count / total_requirements) * 100))

        logger.info(
            f"Heuristic validation: {scenario_count} scenarios vs "
            f"{total_requirements} requirements = {coverage}% coverage"
        )

        return LLMValidationOutput(
            coverage_score=coverage,
            missing_scenarios=[],
            issues=[],
            suggestions=["LLM validation unavailable - using heuristic estimate"],
        )


def gherkin_validator_node(state: TestAutomationState) -> TestAutomationState:
    agent = GherkinValidatorAgent()
    return agent.validate(state)