"""
State definition for the multi-agent test automation workflow.

CHANGES vs previous version:
  - Coverage Analysis section (formerly "Agent 5") now carries ALL fields
    that coverage_analyst.py needs to read and write:
      · coverage_report       (Dict)       — full structured report written by Agent 6
      · coverage_files        (List[str])  — paths to YAML + JSON report files
      · coverage_percentage   (float)      — kept for backward compat (= line_rate)
    The agent reads:
      · execution_result      (Dict)       — written by test_executor (Agent 5)
        keys consumed: "total", "passed", "failed", "skipped", "raw_output_tail"
  - Self-Healing section renumbered to Agent 7 (was 6)
  - get_workflow_summary() extended with coverage fields
"""

from typing import Any, List, Dict, Optional, Union
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────
# Agent output tracking
# ──────────────────────────────────────────────────────────────────────

class AgentStatus:
    """Constants for agent execution status"""
    SUCCESS     = "success"
    FAILED      = "failed"
    SKIPPED     = "skipped"
    IN_PROGRESS = "in_progress"


class AgentOutput(BaseModel):
    """Tracks individual agent execution results"""
    agent_name:    str
    status:        str
    duration_ms:   Optional[float] = None
    output_data:   Optional[Dict]  = Field(default_factory=dict)
    error_message: Optional[str]   = None


# ──────────────────────────────────────────────────────────────────────
# Validation models
# ──────────────────────────────────────────────────────────────────────

class ValidationIssue(BaseModel):
    """Represents a single validation issue"""
    level:       str            # "error" | "warning"
    message:     str
    line_number: Optional[int]  = None
    scenario:    Optional[str]  = None
    suggestion:  Optional[str]  = None


class ValidationResult(BaseModel):
    """Complete validation result from Gherkin validator"""
    is_valid:          bool
    issues:            List[ValidationIssue] = Field(default_factory=list)
    coverage_score:    float                 = 0.0
    missing_scenarios: List[str]             = Field(default_factory=list)
    suggestions:       List[str]             = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# LLM Validation Output Models
# ──────────────────────────────────────────────────────────────────────

class LLMValidationIssue(BaseModel):
    """Issue identified by LLM during validation"""
    scenario: Optional[str] = None
    message:  str


class LLMValidationOutput(BaseModel):
    """Structured output from LLM validation"""
    coverage_score:    float                     = Field(..., ge=0, le=100)
    missing_scenarios: List[str]                 = Field(default_factory=list)
    issues:            List[LLMValidationIssue]  = Field(default_factory=list)
    suggestions:       List[str]                 = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# Multi-service test code model
# ──────────────────────────────────────────────────────────────────────

class TestCodeOutput(BaseModel):
    """
    Holds generated test code for one OR multiple services.

    Single service  → step_definitions / runners are plain strings
    Multi-service   → step_definitions / runners are dicts
                      { "auth": "<java code>", "leave": "<java code>" }
    """
    step_definitions: Union[str, Dict[str, str]] = ""
    runners:          Union[str, Dict[str, str]] = ""
    pom_dependencies: str                        = ""

    def get_steps_for_service(self, service_name: str) -> str:
        if isinstance(self.step_definitions, dict):
            return self.step_definitions.get(service_name, "")
        return self.step_definitions

    def get_runner_for_service(self, service_name: str) -> str:
        if isinstance(self.runners, dict):
            return self.runners.get(service_name, "")
        return self.runners

    def list_services(self) -> List[str]:
        if isinstance(self.step_definitions, dict):
            return list(self.step_definitions.keys())
        return []


# ──────────────────────────────────────────────────────────────────────
# Main workflow state
# ──────────────────────────────────────────────────────────────────────

class TestAutomationState(BaseModel):
    """
    Central state object passed between all agents in the workflow.

    DATA FLOW (agent → fields written → fields read by next agent):

      Agent 2  gherkin_generator  →  gherkin_content, gherkin_files
      Agent 3  gherkin_validator  →  validation_result, validation_passed
      Agent 4  test_writer        →  test_code, test_files
      Agent 5  test_executor      →  execution_result   ← coverage_analyst READS this
      Agent 6  coverage_analyst   →  coverage_report, coverage_files, coverage_percentage
      Agent 7  self_healing       →  healing_attempts, healed_tests
    """

    # ── Input ─────────────────────────────────────────────────────────
    user_story:           str
    swagger_spec:         Dict            = Field(default_factory=dict)
    swagger_specs:        Dict[str, Dict] = Field(default_factory=dict)
    source_code_context:  Optional[str]   = None
    config:               Dict            = Field(
        default_factory=dict,
        description=(
            "Runtime configuration. Recognised keys:\n"
            "  coverage_thresholds: {"
            "    'line_coverage_%': float,"
            "    'branch_coverage_%': float,"
            "    'method_coverage_%': float"
            "  }"
        ),
    )

    # ── Agent 2 — Gherkin Generation ──────────────────────────────────
    gherkin_scenarios: List[str]    = Field(default_factory=list)
    gherkin_file_path: Optional[str] = None
    gherkin_content:   str           = ""
    gherkin_files:     List[str]     = Field(default_factory=list)

    # ── Agent 3 — Gherkin Validation ──────────────────────────────────
    validation_passed: bool                      = False
    validation_errors: List[str]                 = Field(default_factory=list)
    validation_result: Optional[ValidationResult] = None

    # ── Agent 4 — Test Writing ─────────────────────────────────────────
    test_code:  Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Generated test code. "
            "Keys: 'step_definitions', 'runners', 'pom_dependencies'. "
            "Values: str (single service) or Dict[str,str] (multi-service)."
        ),
    )
    test_files: List[str] = Field(default_factory=list)

    # ── Agent 5 — Test Execution ───────────────────────────────────────
    #
    # execution_result is written by TestExecutorAgent and READ by
    # CoverageAnalystAgent.  The coverage analyst accesses these keys:
    #
    #   execution_result["total"]           int   — total scenarios run
    #   execution_result["passed"]          int   — scenarios that passed
    #   execution_result["failed"]          int   — scenarios that failed
    #   execution_result["skipped"]         int   — scenarios skipped
    #   execution_result["raw_output_tail"] str   — last 3 000 chars of
    #                                               Maven stdout+stderr,
    #                                               used by the heuristic
    #                                               fallback when no JaCoCo
    #                                               reports are present
    #
    execution_result:      Optional[Dict] = Field(
        default=None,
        description=(
            "Results from TestExecutorAgent. "
            "Keys: total, passed, failed, skipped, pass_rate, duration_ms, "
            "success, errors, report_path, hints, raw_output_tail."
        ),
    )
    # Backward-compatibility alias (not written by any agent; kept so that
    # old code referencing test_execution_result does not break)
    test_execution_result: Optional[Dict] = None
    test_passed:           bool           = False
    failed_tests:          List[str]      = Field(default_factory=list)

    # ── Agent 6 — Coverage Analysis ────────────────────────────────────
    #
    # Written by CoverageAnalystAgent after it reads execution_result
    # and parses JaCoCo XML/CSV from target/site/jacoco/.
    #
    # coverage_report  — full structured dict (matches CoverageReport.to_dict())
    #   {
    #     "summary": {
    #       "service":      str,
    #       "generated_at": str,
    #       "data_source":  "jacoco-xml" | "jacoco-csv" | "heuristic-console",
    #       "aggregate": {
    #         "total_classes":  int,
    #         "total_packages": int,
    #         "lines":    { "covered": int, "missed": int, "rate_%": float },
    #         "branches": { "covered": int, "missed": int, "rate_%": float },
    #         "methods":  { "covered": int, "missed": int, "rate_%": float },
    #       },
    #       "quality_gate": {
    #         "passed":     bool,
    #         "thresholds": Dict[str, float],
    #         "violations": List[str],
    #       },
    #       "test_execution": { ... },   # from Surefire or execution_result
    #       "warnings":       List[str], # present only when data is incomplete
    #     },
    #     "packages": [ { package-level dict with nested classes } ]
    #   }
    #
    # coverage_files   — absolute paths to the two persisted reports:
    #   [ "…/output/reports/coverage_report_<svc>_<ts>.yaml",
    #     "…/output/reports/coverage_report_<svc>_<ts>.json" ]
    #
    # coverage_percentage — shortcut = summary.aggregate.lines.rate_%
    #   kept for backward compatibility with any dashboard that reads this
    #   single float directly.
    #
    coverage_report:     Optional[Dict] = Field(
        default=None,
        description=(
            "Full structured coverage report written by CoverageAnalystAgent. "
            "Contains summary (aggregate metrics + quality gate) "
            "and per-package / per-class breakdown."
        ),
    )
    coverage_files:      List[str]      = Field(
        default_factory=list,
        description=(
            "Absolute paths to the persisted YAML and JSON coverage reports "
            "written to settings.paths.reports_dir by CoverageAnalystAgent."
        ),
    )
    coverage_percentage: float          = Field(
        default=0.0,
        description=(
            "Shortcut = line coverage rate in %. "
            "Populated by CoverageAnalystAgent from coverage_report."
            "summary.aggregate.lines.rate_% for backward compatibility."
        ),
    )

    # ── Agent 7 — Self-Healing ─────────────────────────────────────────
    healing_attempts: List[Dict] = Field(default_factory=list)
    healed_tests:     List[str]  = Field(default_factory=list)

    # ── E2E Configuration ──────────────────────────────────────────────
    is_e2e:        bool       = Field(
        default=False,
        description="Whether to generate consolidated E2E tests vs per-service tests"
    )
    e2e_services:  List[str]  = Field(
        default_factory=list,
        description="List of services for consolidated E2E testing"
    )

    # ── Workflow metadata ──────────────────────────────────────────────
    workflow_id:     str
    service_name:    str
    current_agent:   Optional[str] = None
    workflow_status: str           = "in_progress"

    # ── Agent tracking ─────────────────────────────────────────────────
    agent_outputs: List[AgentOutput] = Field(default_factory=list)
    warnings:      List[str]         = Field(default_factory=list)
    errors:        List[str]         = Field(default_factory=list)

    # ── Pydantic config ────────────────────────────────────────────────
    class Config:
        arbitrary_types_allowed = True

    # ── Generic helpers ────────────────────────────────────────────────

    def add_agent_output(self, output: AgentOutput) -> None:
        self.agent_outputs.append(output)
        self.current_agent = output.agent_name

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def get_agent_output(self, agent_name: str) -> Optional[AgentOutput]:
        for output in reversed(self.agent_outputs):
            if output.agent_name == agent_name:
                return output
        return None

    # ── Multi-service test code helpers ────────────────────────────────

    def get_steps_for_service(self, service_name: str) -> str:
        steps = self.test_code.get("step_definitions", "")
        if isinstance(steps, dict):
            return steps.get(service_name, "")
        return steps

    def get_runner_for_service(self, service_name: str) -> str:
        runners = self.test_code.get("runners", "")
        if isinstance(runners, dict):
            return runners.get(service_name, "")
        return runners

    def get_generated_services(self) -> List[str]:
        steps = self.test_code.get("step_definitions", "")
        if isinstance(steps, dict):
            return list(steps.keys())
        return [self.service_name] if steps else []

    def is_multi_service(self) -> bool:
        return isinstance(self.test_code.get("step_definitions", ""), dict)

    # ── Coverage helpers ───────────────────────────────────────────────

    def get_coverage_line_rate(self) -> float:
        """
        Return the line coverage percentage written by CoverageAnalystAgent.
        Returns 0.0 if coverage has not been analysed yet.
        """
        if self.coverage_report:
            try:
                return float(
                    self.coverage_report["summary"]["aggregate"]["lines"]["rate_%"]
                )
            except (KeyError, TypeError, ValueError):
                pass
        return self.coverage_percentage

    def get_coverage_quality_gate(self) -> Optional[bool]:
        """
        Return the quality-gate result from the coverage report.
        Returns None if coverage analysis has not run yet.
        """
        if self.coverage_report:
            try:
                return bool(
                    self.coverage_report["summary"]["quality_gate"]["passed"]
                )
            except (KeyError, TypeError):
                pass
        return None

    def get_coverage_violations(self) -> List[str]:
        """
        Return the list of threshold violations from the coverage report.
        Returns [] if coverage analysis has not run or gate passed.
        """
        if self.coverage_report:
            try:
                return list(
                    self.coverage_report["summary"]["quality_gate"]["violations"]
                )
            except (KeyError, TypeError):
                pass
        return []

    # ── Workflow status helpers ────────────────────────────────────────

    def is_workflow_successful(self) -> bool:
        return (
            self.workflow_status == "completed"
            and not self.errors
            and all(
                output.status == AgentStatus.SUCCESS
                for output in self.agent_outputs
            )
        )

    def get_workflow_summary(self) -> Dict:
        summary = {
            # ── Workflow metadata ──────────────────────────────────────
            "workflow_id":           self.workflow_id,
            "service_name":          self.service_name,
            "status":                self.workflow_status,
            "agents_executed":       len(self.agent_outputs),
            "errors":                len(self.errors),
            "warnings":              len(self.warnings),
            "total_duration_ms":     sum(
                o.duration_ms for o in self.agent_outputs if o.duration_ms
            ),
            # ── Gherkin ───────────────────────────────────────────────
            "gherkin_files":         len(self.gherkin_files),
            # ── Validation ────────────────────────────────────────────
            "validation_passed":     self.validation_passed,
            # ── Test code ─────────────────────────────────────────────
            "test_files_generated":  len(self.test_files),
            "swagger_specs_count":   len(self.swagger_specs),
            "generated_services":    self.get_generated_services(),
            "is_multi_service":      self.is_multi_service(),
            # ── Execution ─────────────────────────────────────────────
            "tests_total":           (self.execution_result or {}).get("total",    0),
            "tests_passed":          (self.execution_result or {}).get("passed",   0),
            "tests_failed":          (self.execution_result or {}).get("failed",   0),
            "tests_pass_rate_%":     (self.execution_result or {}).get("pass_rate", 0.0),
            # ── Coverage ──────────────────────────────────────────────
            "coverage_analysed":     self.coverage_report is not None,
            "coverage_line_%":       self.get_coverage_line_rate(),
            "coverage_quality_gate": self.get_coverage_quality_gate(),
            "coverage_violations":   self.get_coverage_violations(),
            "coverage_files":        self.coverage_files,
        }
        return summary


# ──────────────────────────────────────────────────────────────────────
# Additional helper models
# ──────────────────────────────────────────────────────────────────────

class WorkflowConfig(BaseModel):
    """Configuration for workflow execution"""
    enable_validation:        bool  = True
    enable_self_healing:      bool  = True
    max_healing_attempts:     int   = 3
    enable_coverage_analysis: bool  = True
    min_coverage_threshold:   float = 80.0


class TestExecutionResult(BaseModel):
    """Result from test execution"""
    total_tests:      int
    passed_tests:     int
    failed_tests:     int
    skipped_tests:    int
    execution_time_ms: float
    test_details:     List[Dict] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────────────────────────────

__all__ = [
    "TestAutomationState",
    "AgentStatus",
    "AgentOutput",
    "ValidationIssue",
    "ValidationResult",
    "LLMValidationIssue",
    "LLMValidationOutput",
    "TestCodeOutput",
    "WorkflowConfig",
    "TestExecutionResult",
]