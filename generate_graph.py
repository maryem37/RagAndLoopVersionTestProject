"""
generate_graph.py
Generate workflow visualization without running the workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents.coverage_analyst import coverage_analyst_node
from agents.failure_analyst import failure_analyst_node
from agents.gherkin_generator import gherkin_generator_node
from agents.gherkin_validator import gherkin_validator_node
from agents.scenario_designer import scenario_designer_agent_node
from agents.test_executor import test_executor_node
from agents.test_writer import test_writer_node
from graph.state import AgentStatus, TestAutomationState


def _after_generation(state: TestAutomationState) -> Literal["validate", "end"]:
    """Route after gherkin generation."""
    last = state.agent_outputs[-1] if state.agent_outputs else None
    if last and last.status == AgentStatus.SUCCESS and state.gherkin_content and state.gherkin_files:
        return "validate"
    return "end"


def _after_validation(state: TestAutomationState) -> Literal["write_tests", "regenerate", "end"]:
    """Route after gherkin validation."""
    if state.validation_result:
        errors = sum(1 for issue in state.validation_result.issues if issue.level == "error")
        if state.validation_result.is_valid or errors == 0:
            return "write_tests"
        attempts_used = len(getattr(state, "gherkin_validation_retries", []) or [])
        return "regenerate" if attempts_used <= 2 else "end"
    return "end"


def _after_writing(state: TestAutomationState) -> Literal["execute", "end"]:
    """Route after test writing."""
    last = state.agent_outputs[-1] if state.agent_outputs else None
    if last and last.status == AgentStatus.SUCCESS and state.test_files:
        return "execute"
    return "end"


def _after_execution(state: TestAutomationState) -> Literal["analyze_failures", "coverage"]:
    execution = state.execution_result or {}
    if bool(execution.get("success", False)):
        return "coverage"

    failed = int(execution.get("failed", 0) or 0)
    attempts_used = len(state.healing_attempts)
    max_attempts = 3
    if failed > 0 and attempts_used < max_attempts:
        return "analyze_failures"
    return "coverage"


def _after_failure_analysis(state: TestAutomationState) -> Literal["rewrite_tests", "coverage"]:
    analysis = state.failure_analysis or {}
    if bool(analysis.get("retry_recommended", False)) and analysis.get("retry_target") == "test_writer":
        return "rewrite_tests"
    return "coverage"


def build_workflow():
    """Build the workflow graph visualization with the failure-repair loop."""
    workflow = StateGraph(TestAutomationState)

    workflow.add_node("scenario_designer", scenario_designer_agent_node)
    workflow.add_node("gherkin_generator", gherkin_generator_node)
    workflow.add_node("gherkin_validator", gherkin_validator_node)
    workflow.add_node("test_writer", test_writer_node)
    workflow.add_node("test_executor", test_executor_node)
    workflow.add_node("failure_analyst", failure_analyst_node)
    workflow.add_node("coverage_analyst", coverage_analyst_node)

    workflow.set_entry_point("scenario_designer")
    workflow.add_edge("scenario_designer", "gherkin_generator")

    workflow.add_conditional_edges(
        "gherkin_generator",
        _after_generation,
        {"validate": "gherkin_validator", "end": END},
    )
    workflow.add_conditional_edges(
        "gherkin_validator",
        _after_validation,
        {
            "write_tests": "test_writer",
            "regenerate": "gherkin_generator",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "test_writer",
        _after_writing,
        {"execute": "test_executor", "end": END},
    )
    workflow.add_conditional_edges(
        "test_executor",
        _after_execution,
        {"analyze_failures": "failure_analyst", "coverage": "coverage_analyst"},
    )
    workflow.add_conditional_edges(
        "failure_analyst",
        _after_failure_analysis,
        {"rewrite_tests": "test_writer", "coverage": "coverage_analyst"},
    )
    workflow.add_edge("coverage_analyst", END)

    return workflow.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    app = build_workflow()
    graph = app.get_graph()

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    try:
        png_data = graph.draw_mermaid_png()
        png_path = output_dir / "workflow_graph.png"
        png_path.write_bytes(png_data)
        print(f"[OK] PNG saved: {png_path}")
    except Exception as exc:
        print(f"[WARN] PNG generation failed: {exc}")

    try:
        mermaid_text = graph.draw_mermaid()
        mermaid_path = output_dir / "workflow_graph.mmd"
        mermaid_path.write_text(mermaid_text, encoding="utf-8")
        print(f"[OK] Mermaid saved: {mermaid_path}")
        print("\nMermaid Diagram:")
        print(mermaid_text)
    except Exception as exc:
        print(f"[WARN] Mermaid generation failed: {exc}")
