"""
generate_graph.py
Generate workflow visualization without running the workflow
"""

from pathlib import Path
from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Literal

from graph.state import TestAutomationState, AgentStatus
from agents.gherkin_generator import gherkin_generator_node
from agents.gherkin_validator import gherkin_validator_node
from agents.test_writer import test_writer_node
from agents.test_executor import test_executor_node
from agents.coverage_analyst import coverage_analyst_node

def _after_generation(state: TestAutomationState) -> Literal["validate", "end"]:
    """Route after gherkin generation"""
    last = state.agent_outputs[-1] if state.agent_outputs else None
    if last and last.status == AgentStatus.SUCCESS and state.gherkin_content and state.gherkin_files:
        return "validate"
    return "end"

def _after_validation(state: TestAutomationState) -> Literal["write_tests", "end"]:
    """Route after gherkin validation"""
    if state.validation_result:
        errors = sum(1 for i in state.validation_result.issues if i.level == "error")
        if state.validation_result.is_valid or errors == 0:
            return "write_tests"
        return "end"
    return "end"

def _after_writing(state: TestAutomationState) -> Literal["execute", "end"]:
    """Route after test writing"""
    last = state.agent_outputs[-1] if state.agent_outputs else None
    if last and last.status == AgentStatus.SUCCESS and state.test_files:
        return "execute"
    return "end"

def build_workflow() -> StateGraph:
    """Build the complete workflow graph structure with all 5 nodes"""
    workflow = StateGraph(TestAutomationState)
    
    # Add all nodes
    workflow.add_node("gherkin_generator", gherkin_generator_node)
    workflow.add_node("gherkin_validator", gherkin_validator_node)
    workflow.add_node("test_writer", test_writer_node)
    workflow.add_node("test_executor", test_executor_node)
    workflow.add_node("coverage_analyst", coverage_analyst_node)
    
    # Set entry point
    workflow.set_entry_point("gherkin_generator")
    
    # Define conditional edges for intelligent routing
    workflow.add_conditional_edges(
        "gherkin_generator",
        _after_generation,
        {"validate": "gherkin_validator", "end": END},
    )
    workflow.add_conditional_edges(
        "gherkin_validator",
        _after_validation,
        {"write_tests": "test_writer", "end": END},
    )
    workflow.add_conditional_edges(
        "test_writer",
        _after_writing,
        {"execute": "test_executor", "end": END},
    )
    
    # Always analyze coverage after execution
    workflow.add_edge("test_executor", "coverage_analyst")
    workflow.add_edge("coverage_analyst", END)
    
    return workflow.compile(checkpointer=MemorySaver())

if __name__ == "__main__":
    app = build_workflow()
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Generate PNG
        from langgraph.graph import draw_mermaid_png
        png_data = draw_mermaid_png(app.get_graph())
        png_path = output_dir / "workflow_graph.png"
        with open(png_path, "wb") as f:
            f.write(png_data)
        print(f"✅ PNG saved: {png_path}")
        
    except Exception as e:
        print(f"⚠️ PNG generation failed: {e}")
    
    try:
        # Generate Mermaid text
        mermaid_text = app.get_graph().draw_mermaid()
        mermaid_path = output_dir / "workflow_graph.mmd"
        with open(mermaid_path, "w") as f:
            f.write(mermaid_text)
        print(f"✅ Mermaid saved: {mermaid_path}")
        print("\nMermaid Diagram:")
        print(mermaid_text)
        
    except Exception as e:
        print(f"⚠️ Mermaid generation failed: {e}")