"""
State definition for the multi-agent test automation workflow.
"""

from typing import List, Dict, Optional
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
    swagger_spec: Optional[Dict] = None
    source_code_context: Optional[str] = None

    # ----------------------------
    # Gherkin Generation (Agent 2)
    # ----------------------------
    gherkin_scenarios: List[str] = Field(default_factory=list)
    gherkin_file_path: Optional[str] = None
    gherkin_content: str = ""  # Changed from Optional[str] to str with default
    gherkin_files: List[str] = Field(default_factory=list)

    # ----------------------------
    # Validation (Agent 3)
    # ----------------------------
    validation_passed: bool = False
    validation_errors: List[str] = Field(default_factory=list)
    validation_result: Optional[ValidationResult] = None

    # ----------------------------
    # Generated test artifacts (Agent 4)
    # ----------------------------
    test_code: Dict[str, str] = Field(default_factory=dict)
    test_files: List[str] = Field(default_factory=list)

    # ----------------------------
    # Test Execution (Agent 5)
    # ----------------------------
    test_execution_results: Optional[Dict] = None
    test_passed: bool = False
    failed_tests: List[str] = Field(default_factory=list)

    # ----------------------------
    # Coverage Analysis (Agent 6)
    # ----------------------------
    coverage_report: Optional[Dict] = None
    coverage_percentage: float = 0.0

    # ----------------------------
    # Self-Healing (Agent 7)
    # ----------------------------
    healing_attempts: List[Dict] = Field(default_factory=list)
    healed_tests: List[str] = Field(default_factory=list)

    # ----------------------------
    # Workflow metadata
    # ----------------------------
    workflow_id: str
    service_name: str
    current_agent: Optional[str] = None
    workflow_status: str = "in_progress"  # "in_progress" | "completed" | "failed"

    # ----------------------------
    # Agent tracking
    # ----------------------------
    agent_outputs: List[AgentOutput] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    # ----------------------------
    # Configuration
    # ----------------------------
    class Config:
        arbitrary_types_allowed = True

    # ----------------------------
    # Helper methods
    # ----------------------------
    def add_agent_output(self, output: AgentOutput) -> None:
        """Add an agent execution result to tracking"""
        self.agent_outputs.append(output)
        self.current_agent = output.agent_name

    def add_warning(self, message: str) -> None:
        """Add a warning message"""
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """Add an error message"""
        self.errors.append(message)

    def get_agent_output(self, agent_name: str) -> Optional[AgentOutput]:
        """Retrieve output from a specific agent"""
        for output in reversed(self.agent_outputs):  # Get most recent
            if output.agent_name == agent_name:
                return output
        return None

    def is_workflow_successful(self) -> bool:
        """Check if workflow completed successfully"""
        return (
            self.workflow_status == "completed" and
            not self.errors and
            all(output.status == AgentStatus.SUCCESS for output in self.agent_outputs)
        )

    def get_workflow_summary(self) -> Dict:
        """Get summary of workflow execution"""
        return {
            "workflow_id": self.workflow_id,
            "service_name": self.service_name,
            "status": self.workflow_status,
            "agents_executed": len(self.agent_outputs),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "validation_passed": self.validation_passed,
            "test_files_generated": len(self.test_files),
            "total_duration_ms": sum(
                output.duration_ms for output in self.agent_outputs 
                if output.duration_ms
            )
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
# Export all models
# ----------------------------
__all__ = [
    'TestAutomationState',
    'AgentStatus',
    'AgentOutput',
    'ValidationIssue',
    'ValidationResult',
    'LLMValidationIssue',
    'LLMValidationOutput',
    'WorkflowConfig',
    'TestExecutionResult',
]