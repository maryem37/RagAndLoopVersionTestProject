"""
State definition for the multi-agent test automation workflow.
"""

from typing import Any, List, Dict, Optional, Union
from pydantic import BaseModel, Field


# ----------------------------
# Agent output tracking
# ----------------------------
class AgentStatus:
    """Constants for agent execution status"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    IN_PROGRESS = "in_progress"


class AgentOutput(BaseModel):
    """Tracks individual agent execution results"""
    agent_name: str
    status: str
    duration_ms: Optional[float] = None
    output_data: Optional[Dict] = Field(default_factory=dict)
    error_message: Optional[str] = None


# ----------------------------
# Validation models
# ----------------------------
class ValidationIssue(BaseModel):
    """Represents a single validation issue"""
    level: str  # "error" | "warning"
    message: str
    line_number: Optional[int] = None
    scenario: Optional[str] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """Complete validation result from Gherkin validator"""
    is_valid: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    coverage_score: float = 0.0
    missing_scenarios: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# ----------------------------
# LLM Validation Output Models
# ----------------------------
class LLMValidationIssue(BaseModel):
    """Issue identified by LLM during validation"""
    scenario: Optional[str] = None
    message: str


class LLMValidationOutput(BaseModel):
    """Structured output from LLM validation"""
    coverage_score: float = Field(..., ge=0, le=100)
    missing_scenarios: List[str] = Field(default_factory=list)
    issues: List[LLMValidationIssue] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# ----------------------------
# Multi-service test code model
# ----------------------------
class TestCodeOutput(BaseModel):
    """
    Holds generated test code for one OR multiple services.

    Single service  → step_definitions / runners are plain strings
    Multi-service   → step_definitions / runners are dicts
                      { "auth": "<java code>", "leave": "<java code>" }
    """
    # Union[str, Dict] accepte les 2 cas (single + multi-service)
    step_definitions: Union[str, Dict[str, str]] = ""
    runners:          Union[str, Dict[str, str]] = ""
    pom_dependencies: str = ""

    # ── helpers ──────────────────────────────────────────────────────

    def get_steps_for_service(self, service_name: str) -> str:
        """Retourne le code step defs pour un service donné."""
        if isinstance(self.step_definitions, dict):
            return self.step_definitions.get(service_name, "")
        return self.step_definitions

    def get_runner_for_service(self, service_name: str) -> str:
        """Retourne le code runner pour un service donné."""
        if isinstance(self.runners, dict):
            return self.runners.get(service_name, "")
        return self.runners

    def list_services(self) -> List[str]:
        """Retourne la liste des services générés."""
        if isinstance(self.step_definitions, dict):
            return list(self.step_definitions.keys())
        return []


# ----------------------------
# Main workflow state
# ----------------------------
class TestAutomationState(BaseModel):
    """
    Central state object passed between all agents in the workflow.
    Contains inputs, outputs, and metadata for the entire test automation process.
    """

    # ----------------------------
    # Input data
    # ----------------------------
    user_story: str

    # Single Swagger spec (backward compat with gherkin_generator)
    swagger_spec: Dict = Field(
        default_factory=dict,
        description="Single Swagger/OpenAPI spec (backward compatibility)"
    )

    # Multi-service Swagger specs (used by test_writer)
    swagger_specs: Dict[str, Dict] = Field(
        default_factory=dict,
        description="{ service_name: swagger_dict } — one entry per microservice"
    )

    source_code_context: Optional[str] = None
    config: Dict = Field(default_factory=dict)

    # ----------------------------
    # Gherkin Generation (Agent 1)
    # ----------------------------
    gherkin_scenarios: List[str] = Field(default_factory=list)
    gherkin_file_path: Optional[str] = None
    gherkin_content: str = ""
    gherkin_files: List[str] = Field(default_factory=list)

    # ----------------------------
    # Validation (Agent 2)
    # ----------------------------
    validation_passed: bool = False
    validation_errors: List[str] = Field(default_factory=list)
    validation_result: Optional[ValidationResult] = None

    # ----------------------------
    # Generated test artifacts (Agent 3)
    # ----------------------------

    # ── CORRECTION PRINCIPALE ────────────────────────────────────────
    # Avant : Dict[str, str]  → n'acceptait que des strings
    # Après : Dict[str, Any]  → accepte strings ET dicts imbriqués
    # Le TestWriter stocke :
    #   {
    #     "step_definitions": { "auth": "...java", "leave": "...java" },
    #     "runners":          { "auth": "...java", "leave": "...java" },
    #   }
    test_code: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Generated test code. "
            "Keys: 'step_definitions', 'runners', 'pom_dependencies'. "
            "Values: str (single service) or Dict[str,str] (multi-service)."
        )
    )

    test_files: List[str] = Field(default_factory=list)

    # ----------------------------
    # Test Execution (Agent 4)
    # ----------------------------
    execution_result: Optional[Dict] = Field(
        default=None,
        description="Results from TestExecutorAgent"
    )
    # Backward compat alias
    test_execution_result: Optional[Dict] = None
    test_passed: bool = False
    failed_tests: List[str] = Field(default_factory=list)

    # ----------------------------
    # Coverage Analysis (Agent 5)
    # ----------------------------
    coverage_report: Optional[Dict] = None
    coverage_percentage: float = 0.0

    # ----------------------------
    # Self-Healing (Agent 6)
    # ----------------------------
    healing_attempts: List[Dict] = Field(default_factory=list)
    healed_tests: List[str] = Field(default_factory=list)

    # ----------------------------
    # Workflow metadata
    # ----------------------------
    workflow_id: str
    service_name: str
    current_agent: Optional[str] = None
    workflow_status: str = "in_progress"

    # ----------------------------
    # Agent tracking
    # ----------------------------
    agent_outputs: List[AgentOutput] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    # ----------------------------
    # Pydantic config
    # ----------------------------
    class Config:
        arbitrary_types_allowed = True

    # ----------------------------
    # Helper methods
    # ----------------------------
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

    # ── Helpers spécifiques multi-service ───────────────────────────

    def get_steps_for_service(self, service_name: str) -> str:
        """
        Retourne le code step definitions pour un service donné.
        Fonctionne que test_code soit single ou multi-service.
        """
        steps = self.test_code.get("step_definitions", "")
        if isinstance(steps, dict):
            return steps.get(service_name, "")
        return steps

    def get_runner_for_service(self, service_name: str) -> str:
        """
        Retourne le code runner pour un service donné.
        """
        runners = self.test_code.get("runners", "")
        if isinstance(runners, dict):
            return runners.get(service_name, "")
        return runners

    def get_generated_services(self) -> List[str]:
        """
        Retourne la liste des services pour lesquels des tests ont été générés.
        """
        steps = self.test_code.get("step_definitions", "")
        if isinstance(steps, dict):
            return list(steps.keys())
        return [self.service_name] if steps else []

    def is_multi_service(self) -> bool:
        """True si le TestWriter a généré des tests pour plusieurs services."""
        return isinstance(
            self.test_code.get("step_definitions", ""), dict
        )

    # ── Workflow status helpers ──────────────────────────────────────

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
        return {
            "workflow_id":         self.workflow_id,
            "service_name":        self.service_name,
            "status":              self.workflow_status,
            "agents_executed":     len(self.agent_outputs),
            "errors":              len(self.errors),
            "warnings":            len(self.warnings),
            "validation_passed":   self.validation_passed,
            "test_files_generated": len(self.test_files),
            "swagger_specs_count": len(self.swagger_specs),
            "generated_services":  self.get_generated_services(),
            "is_multi_service":    self.is_multi_service(),
            "total_duration_ms": sum(
                output.duration_ms
                for output in self.agent_outputs
                if output.duration_ms
            ),
        }


# ----------------------------
# Additional helper models
# ----------------------------
class WorkflowConfig(BaseModel):
    """Configuration for workflow execution"""
    enable_validation: bool = True
    enable_self_healing: bool = True
    max_healing_attempts: int = 3
    enable_coverage_analysis: bool = True
    min_coverage_threshold: float = 80.0


class TestExecutionResult(BaseModel):
    """Result from test execution"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    execution_time_ms: float
    test_details: List[Dict] = Field(default_factory=list)


# ----------------------------
# Export
# ----------------------------
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