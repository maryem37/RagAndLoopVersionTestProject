from graph.workflow import build_workflow
from graph.state import TestAutomationState
import uuid
from pathlib import Path

def main():
    user_story = Path("examples/sample_user_story.md").read_text()

    state = TestAutomationState(
        workflow_id=str(uuid.uuid4()),
        service_name="user-service",
        user_story=user_story
    )

    workflow = build_workflow()
    final_state = workflow.invoke(state)

    print("\n✅ WORKFLOW FINISHED")
    print("Generated tests:", final_state.test_files)

if __name__ == "__main__":
    main()
