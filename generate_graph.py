"""
generate_graph.py
Generate workflow visualization without running the workflow
"""

from pathlib import Path
from loguru import logger
from langgraph.graph import StateGraph, END

from graph.state import TestAutomationState
from graph.workflow import (
    gherkin_generator_node,
    gherkin_validator_node,
    test_writer_node
)

def build_workflow() -> StateGraph:
    """Build the workflow graph structure"""
    workflow = StateGraph(TestAutomationState)
    
    # Add nodes
    workflow.add_node("generate_gherkin", gherkin_generator_node)
    workflow.add_node("validate_gherkin", gherkin_validator_node)
    workflow.add_node("write_tests", test_writer_node)
    
    # Define flow
    workflow.set_entry_point("generate_gherkin")
    workflow.add_edge("generate_gherkin", "validate_gherkin")
    workflow.add_edge("validate_gherkin", "write_tests")
    workflow.add_edge("write_tests", END)
    
    return workflow.compile()

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