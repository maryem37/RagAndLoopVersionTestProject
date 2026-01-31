# tools/gherkin_lint.py

from typing import List
from graph.state import ValidationIssue


STEP_KEYWORDS = ("Given", "When", "Then", "And", "But")


def lint_gherkin_content(
    content: str,
    source: str = "internal-lint"
) -> List[ValidationIssue]:
    """
    Lightweight Gherkin syntax & structure validation.
    Used as fallback when gherkin-lint CLI is unavailable.
    """
    issues: List[ValidationIssue] = []
    lines = content.splitlines()

    has_feature = False
    has_scenario = False
    current_scenario = ""
    scenario_steps = []

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # ---- Feature ----
        if stripped.startswith("Feature:"):
            has_feature = True

        # ---- Scenario ----
        if stripped.startswith(("Scenario:", "Scenario Outline:")):
            has_scenario = True

            # Validate previous scenario
            _validate_scenario_steps(
                scenario_steps,
                current_scenario,
                issues
            )

            current_scenario = stripped
            scenario_steps = []
            continue

        # ---- Steps ----
        if stripped.startswith(STEP_KEYWORDS):
            scenario_steps.append((line_num, stripped))

            # Empty step
            if stripped in STEP_KEYWORDS:
                issues.append(ValidationIssue(
                    level="error",
                    message="Empty step definition",
                    line_number=line_num,
                    scenario=current_scenario
                ))

        # ---- Invalid lines inside scenario ----
        elif current_scenario and stripped and not stripped.startswith("#"):
            if ":" not in stripped:
                issues.append(ValidationIssue(
                    level="warning",
                    message=f"Unrecognized line inside scenario: '{stripped}'",
                    line_number=line_num,
                    scenario=current_scenario
                ))

    # Validate last scenario
    _validate_scenario_steps(
        scenario_steps,
        current_scenario,
        issues
    )

    if not has_feature:
        issues.append(ValidationIssue(
            level="error",
            message="Missing Feature declaration",
            line_number=1,
            scenario=source
        ))

    if not has_scenario:
        issues.append(ValidationIssue(
            level="error",
            message="No Scenario found",
            line_number=1,
            scenario=source
        ))

    return issues


def _validate_scenario_steps(steps, scenario, issues):
    if not scenario:
        return

    keywords = [s[1].split()[0] for s in steps]

    if not any(k == "Given" for k in keywords):
        issues.append(ValidationIssue(
            level="error",
            message="Scenario missing Given step",
            scenario=scenario
        ))

    if not any(k == "When" for k in keywords):
        issues.append(ValidationIssue(
            level="error",
            message="Scenario missing When step",
            scenario=scenario
        ))

    if not any(k == "Then" for k in keywords):
        issues.append(ValidationIssue(
            level="error",
            message="Scenario missing Then step",
            scenario=scenario
        ))
