"""
Agent 3: Gherkin Validator
Validates generated Gherkin scenarios using internal Python lint and LLM analysis.
Integrated with LangGraph state management.
"""

import json
import re
import time
from pathlib import Path
from typing import List
from loguru import logger

from graph.state import (
    TestAutomationState,
    AgentOutput,
    AgentStatus,
    ValidationResult,
    ValidationIssue,
    LLMValidationOutput,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import PydanticOutputParser
from config.settings import get_settings
from tools.gherkin_lint import lint_gherkin_content


class GherkinValidatorAgent:
    """
    Agent responsible for validating Gherkin scenarios.
    Uses internal Python linter and LLM-based business logic validation.
    """

    def __init__(self):
        self.settings = get_settings()
        self.llm = OllamaLLM(
            base_url=self.settings.ollama.base_url,
            model=self.settings.ollama.model,
            temperature=0.0,
            format="json",  # Force Ollama to return JSON
        )
        # Use PydanticOutputParser to enforce structured output
        self.output_parser = PydanticOutputParser(pydantic_object=LLMValidationOutput)
        logger.info("✅ Gherkin Validator initialized (using internal Python lint + Pydantic LLM parsing)")

    def validate(self, state: TestAutomationState) -> TestAutomationState:
        """
        Validate Gherkin scenarios from the state.
        """
        start_time = time.time()
        all_issues: List[ValidationIssue] = []

        try:
            # 1. Syntax validation (internal Python linter)
            if state.gherkin_content:
                syntax_issues = lint_gherkin_content(state.gherkin_content)
                all_issues.extend(syntax_issues)
                logger.info(f"   Syntax check: {len(syntax_issues)} issues")
            else:
                logger.warning("No Gherkin content to validate")

            # 2. Semantic validation (step order Given → When → Then)
            for feature_file in state.gherkin_files:
                semantic_issues = self._validate_semantics(Path(feature_file))
                all_issues.extend(semantic_issues)
                logger.info(f"   Semantic check: {len(semantic_issues)} issues")

            # 3. Business logic validation with LLM (Pydantic parser)
            logger.info("   Running LLM validation...")
            llm_result = self._validate_with_llm(
                state.gherkin_content,
                state.user_story
            )

            # Create ValidationResult
            validation_result = ValidationResult(
                is_valid=not any(issue.level == "error" for issue in all_issues),
                issues=all_issues,
                coverage_score=llm_result.coverage_score,
                missing_scenarios=llm_result.missing_scenarios,
                suggestions=llm_result.suggestions
            )

            # Update state
            state.validation_result = validation_result

            # Record agent output
            duration = (time.time() - start_time) * 1000
            agent_output = AgentOutput(
                agent_name="gherkin_validator",
                status=AgentStatus.SUCCESS if validation_result.is_valid else AgentStatus.FAILED,
                duration_ms=duration,
                output_data={
                    "is_valid": validation_result.is_valid,
                    "total_issues": len(all_issues),
                    "errors": sum(1 for i in all_issues if i.level == "error"),
                    "warnings": sum(1 for i in all_issues if i.level == "warning"),
                    "coverage_score": llm_result.coverage_score,
                    "missing_scenarios_count": len(llm_result.missing_scenarios)
                }
            )
            state.add_agent_output(agent_output)

            # Log summary
            if validation_result.is_valid:
                logger.success(f"✅ Validation PASSED - Coverage: {llm_result.coverage_score}%")
            else:
                logger.warning(f"⚠️ Validation FAILED - Coverage: {llm_result.coverage_score}%")

            # Add missing scenarios as warnings
            for missing in llm_result.missing_scenarios:
                state.add_warning(f"Missing scenario: {missing}")

        except Exception as e:
            logger.error(f"❌ Validation error: {str(e)}")
            duration = (time.time() - start_time) * 1000
            agent_output = AgentOutput(
                agent_name="gherkin_validator",
                status=AgentStatus.FAILED,
                duration_ms=duration,
                error_message=str(e)
            )
            state.add_agent_output(agent_output)
            state.add_error(f"Validation failed: {str(e)}")

        return state

    def _validate_semantics(self, feature_file: Path) -> List[ValidationIssue]:
        """Validate step order in scenarios (Given → When → Then)"""
        issues: List[ValidationIssue] = []

        with open(feature_file, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()

        current_scenario = ""
        last_step_type = None
        step_order = {"Given": 0, "When": 1, "Then": 2}

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith(("Scenario:", "Scenario Outline:")):
                current_scenario = stripped
                last_step_type = None
                continue

            for keyword in ["Given", "When", "Then"]:
                if stripped.startswith(keyword):
                    if last_step_type and step_order[keyword] < step_order[last_step_type]:
                        issues.append(ValidationIssue(
                            level="warning",
                            message=f"Unexpected step order: {keyword} after {last_step_type}",
                            line_number=line_num,
                            scenario=current_scenario,
                            suggestion="Follow Given-When-Then pattern"
                        ))
                    last_step_type = keyword
                    break

        return issues

    def _validate_with_llm(self, gherkin_content: str, user_story: str) -> LLMValidationOutput:
        """Validate business logic coverage using LLM with PydanticOutputParser"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a validation API. You MUST return ONLY valid JSON.
DO NOT write any code, DO NOT write explanations.
Return EXACTLY the following JSON structure:

{
  "coverage_score": 0,
  "missing_scenarios": [],
  "issues": [],
  "suggestions": []
}

- coverage_score = integer 0-100
- missing_scenarios = list of strings (scenarios missing from user story)
- issues = list of strings (problems detected)
- suggestions = list of strings (improvements)
Your response MUST start with { and end with } and be valid JSON.
""")

            ,
            ("human", "User Story:\n{user_story}\n\nGherkin:\n{gherkin_content}\n\nValidate:")
        ])

        chain = prompt | self.llm | self.output_parser

        try:
            result = chain.invoke({
                "user_story": user_story,
                "gherkin_content": gherkin_content,
                "format_instructions": self.output_parser.get_format_instructions()
            })
            return result
        except Exception as e:
            logger.warning(f"LLM validation failed: {e}")
            return self._heuristic_validation(gherkin_content, user_story)

    def _heuristic_validation(self, gherkin_content: str, user_story: str) -> LLMValidationOutput:
        """Fallback: Simple heuristic-based validation when LLM fails"""

        scenario_count = gherkin_content.lower().count("scenario")
        ac_count = user_story.lower().count("acceptance criteria")
        ac_count += user_story.lower().count("- ")  # Count bullet points

        coverage = min(100, (scenario_count / max(1, ac_count // 2)) * 100)

        logger.info(f"Heuristic validation: {scenario_count} scenarios, estimated coverage {coverage:.0f}%")

        return LLMValidationOutput(
            coverage_score=coverage,
            missing_scenarios=[],
            issues=[],
            suggestions=["LLM validation unavailable - using heuristic estimate"]
        )


def gherkin_validator_node(state: TestAutomationState) -> TestAutomationState:
    """LangGraph node wrapper for Gherkin validation"""
    agent = GherkinValidatorAgent()
    return agent.validate(state)


# -------------------------------
# Standalone test
# -------------------------------
if __name__ == "__main__":
    from rich import print as rprint
    import uuid

    test_gherkin = """Feature: User Login
As a user
I want to log in to the system
So that I can access my account

Scenario: Successful login
    Given the user is on the login page
    When the user enters email "user@test.com"
    And the user enters password "password123"
    Then the user should be logged in

Scenario: Failed login
    Given the user is on the login page
    When the user enters invalid credentials
    Then the user should see an error message
"""

    test_user_story = """
User Story: User Login

Acceptance Criteria:
- User can log in with valid credentials
- System shows error for invalid credentials
- System shows error for missing fields
- User is redirected after login
- Account locks after 3 failed attempts
"""

    test_state = TestAutomationState(
        workflow_id=str(uuid.uuid4()),
        service_name="test",
        user_story=test_user_story,
        gherkin_content=test_gherkin,
        gherkin_files=[]
    )

    print("\n🚀 Running Validator Test...\n")
    result_state = GherkinValidatorAgent().validate(test_state)

    rprint("\n📊 RESULTS:")
    if result_state.validation_result:
        rprint(f"Coverage: {result_state.validation_result.coverage_score}%")
        rprint(f"Missing: {result_state.validation_result.missing_scenarios}")
        rprint(f"Suggestions: {result_state.validation_result.suggestions}")
