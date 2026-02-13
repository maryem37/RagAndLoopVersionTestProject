from pathlib import Path
from loguru import logger

from agents.gherkin_generator import GherkinGeneratorAgent
from graph.state import TestAutomationState

USER_STORY_FILE = Path("examples/sample_user_story.md")

def main():
    try:
        logger.info("🚀 Starting Gherkin Generator Test")

        if not USER_STORY_FILE.exists():
            logger.error(f"❌ File not found: {USER_STORY_FILE}")
            return

        user_story_text = USER_STORY_FILE.read_text(encoding="utf-8")

        state = TestAutomationState(
            user_story=user_story_text,
            workflow_id="test_workflow_001",
            service_name="leave_request_service",
            swagger_spec={}
        )

        agent = GherkinGeneratorAgent()
        updated_state = agent.generate(state)

        if updated_state.gherkin_files:
            logger.success(f"✔ Generated {len(updated_state.gherkin_files)} feature file(s)")
            for f in updated_state.gherkin_files:
                print(f" - {f}")
        else:
            logger.warning("⚠ No Gherkin files were generated")

    except Exception as e:
        logger.exception(f"🔥 Unexpected crash: {e}")


if __name__ == "__main__":
    main()
