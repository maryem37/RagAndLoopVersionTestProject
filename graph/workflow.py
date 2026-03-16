"""
LangGraph Workflow for Multi-Agent Test Automation
Pipeline complet :
  gherkin_generator → gherkin_validator → test_writer → test_executor
"""

from typing import Literal
from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import TestAutomationState, AgentStatus
from agents.gherkin_generator import gherkin_generator_node
from agents.gherkin_validator import gherkin_validator_node
from agents.test_writer       import test_writer_node
from agents.test_executor     import test_executor_node   # ← AJOUTÉ


class TestAutomationWorkflow:

    def __init__(self):
        self.memory = MemorySaver()
        self.graph  = self._build_graph()
        logger.info("✅ Test Automation Workflow initialized")
        logger.info("📋 Pipeline: gherkin_generator → gherkin_validator → test_writer → test_executor")

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(TestAutomationState)

        # ── Nœuds ────────────────────────────────────────────────────
        workflow.add_node("gherkin_generator", gherkin_generator_node)
        workflow.add_node("gherkin_validator", gherkin_validator_node)
        workflow.add_node("test_writer",       test_writer_node)
        workflow.add_node("test_executor",     test_executor_node)   # ← AJOUTÉ

        # ── Point d'entrée ───────────────────────────────────────────
        workflow.set_entry_point("gherkin_generator")

        # ── Transitions ──────────────────────────────────────────────
        workflow.add_conditional_edges(
            "gherkin_generator",
            self._should_continue_after_generation,
            {"validate": "gherkin_validator", "end": END},
        )
        workflow.add_conditional_edges(
            "gherkin_validator",
            self._should_continue_after_validation,
            {"write_tests": "test_writer", "end": END},
        )
        workflow.add_conditional_edges(
            "test_writer",
            self._should_continue_after_writing,
            {"execute": "test_executor", "end": END},   # ← AJOUTÉ
        )
        workflow.add_edge("test_executor", END)          # ← AJOUTÉ

        logger.info("📊 Workflow graph built successfully")
        logger.info("   Nodes: gherkin_generator → gherkin_validator → test_writer → test_executor")

        return workflow.compile(checkpointer=self.memory)

    # ------------------------------------------------------------------
    # Routing conditions
    # ------------------------------------------------------------------

    def _should_continue_after_generation(
        self, state: TestAutomationState
    ) -> Literal["validate", "end"]:
        last = state.agent_outputs[-1] if state.agent_outputs else None
        if last and last.status == AgentStatus.SUCCESS:
            if state.gherkin_content and state.gherkin_files:
                logger.info("✓ Gherkin generation successful → Proceeding to validation")
                return "validate"
            logger.warning("✗ No Gherkin content generated → Ending workflow")
            return "end"
        logger.warning("✗ Gherkin generation failed → Ending workflow")
        return "end"

    def _should_continue_after_validation(
        self, state: TestAutomationState
    ) -> Literal["write_tests", "end"]:
        if state.validation_result:
            if state.validation_result.is_valid:
                logger.info("✓ Validation passed → Proceeding to test writing")
                return "write_tests"
            errors = sum(1 for i in state.validation_result.issues if i.level == "error")
            if errors == 0:
                logger.info("✓ No critical errors → Proceeding to test writing")
                return "write_tests"
            logger.error("✗ Critical validation errors → Ending workflow")
            return "end"
        logger.warning("✗ No validation result → Ending workflow")
        return "end"

    def _should_continue_after_writing(
        self, state: TestAutomationState
    ) -> Literal["execute", "end"]:
        """
        Continue vers test_executor si les fichiers Java ont été générés.
        """
        last = state.agent_outputs[-1] if state.agent_outputs else None
        if last and last.status == AgentStatus.SUCCESS and state.test_files:
            logger.info("✓ Test files generated → Proceeding to execution")
            return "execute"
        logger.warning("✗ Test writing failed or no files → Skipping execution")
        return "end"

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    def run(
        self,
        user_story:     str,
        service_name:   str,
        swagger_spec:   dict = None,
        swagger_specs:  dict = None,
        config:         dict = None,
    ) -> TestAutomationState:
        import uuid
        from datetime import datetime

        logger.info("=" * 80)
        logger.info("🚀 Starting CONTRACT-LEVEL Test Automation Workflow")
        logger.info(f"   Service: {service_name}")
        logger.info("=" * 80)

        workflow_id = (
            f"{service_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            f"_{str(uuid.uuid4())[:8]}"
        )

        final_swagger_specs = swagger_specs or {}
        if not final_swagger_specs and swagger_spec:
            final_swagger_specs = {"primary": swagger_spec}

        if final_swagger_specs:
            logger.info(f"   Swagger specs: {len(final_swagger_specs)} service(s)")
            for key in final_swagger_specs:
                logger.info(f"      - {key}")
        else:
            logger.warning("   ⚠️ No Swagger specs provided")

        initial_state = TestAutomationState(
            workflow_id=workflow_id,
            user_story=user_story,
            service_name=service_name,
            swagger_spec=swagger_spec or {},
            swagger_specs=final_swagger_specs,
            config=config or {},
        )

        try:
            logger.info("\n🎯 Executing workflow...")
            result = self.graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": service_name}},
            )
            final_state = (
                TestAutomationState(**result) if isinstance(result, dict) else result
            )
            final_state.workflow_status = "failed" if final_state.errors else "completed"
            self._log_workflow_summary(final_state)
            return final_state

        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            raise

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    @staticmethod
    def _count_lines(value) -> int:
        if isinstance(value, str):
            return len(value.splitlines())
        if isinstance(value, dict):
            return sum(len(v.splitlines()) for v in value.values() if isinstance(v, str))
        return 0

    def _log_workflow_summary(self, state: TestAutomationState) -> None:
        logger.info("\n" + "=" * 80)
        logger.info("📊 WORKFLOW EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Workflow ID : {state.workflow_id}")
        logger.info(f"Service     : {state.service_name}")
        logger.info(f"Status      : {state.workflow_status.upper()}")

        logger.info("\n📋 Agent Execution:")
        total_duration = 0
        for output in state.agent_outputs:
            icon     = "✓" if output.status == AgentStatus.SUCCESS else "✗"
            duration = output.duration_ms or 0
            total_duration += duration
            logger.info(f"  {icon} {output.agent_name}")
            logger.info(f"      Status   : {output.status}")
            logger.info(f"      Duration : {duration:.0f}ms")

            if output.output_data:
                if output.agent_name == "gherkin_generator":
                    logger.info(f"      Features : {output.output_data.get('features_generated', 0)}")
                    logger.info(f"      Files    : {output.output_data.get('feature_files', [])}")
                elif output.agent_name == "gherkin_validator":
                    logger.info(f"      Valid    : {output.output_data.get('is_valid', False)}")
                    logger.info(f"      Coverage : {output.output_data.get('coverage_score', 0)}%")
                elif output.agent_name == "test_writer":
                    logger.info(f"      Files    : {output.output_data.get('files_generated', 0)}")
                    logger.info(f"      Services : {output.output_data.get('services_processed', [])}")
                elif output.agent_name == "test_executor":
                    logger.info(f"      Total    : {output.output_data.get('total', 0)}")
                    logger.info(f"      Passed   : {output.output_data.get('passed', 0)}")
                    logger.info(f"      Failed   : {output.output_data.get('failed', 0)}")
                    logger.info(f"      Rate     : {output.output_data.get('pass_rate', 0)}%")
                    report = output.output_data.get("report_path")
                    if report:
                        logger.info(f"      Report   : {report}")

        logger.info(f"\nTotal Duration: {total_duration:.0f}ms ({total_duration / 1000:.1f}s)")

        logger.info(f"\n📁 Generated Artifacts:")
        logger.info(f"  Gherkin files : {len(state.gherkin_files)}")
        for f in state.gherkin_files:
            logger.info(f"    - {f}")
        logger.info(f"  Test files    : {len(state.test_files)}")
        for f in state.test_files:
            logger.info(f"    - {f}")

        if state.validation_result:
            vr = state.validation_result
            logger.info(f"\n✅ Validation Results:")
            logger.info(f"  Valid          : {vr.is_valid}")
            logger.info(f"  Coverage Score : {vr.coverage_score}%")
            errors   = [i for i in vr.issues if i.level == "error"]
            warnings = [i for i in vr.issues if i.level == "warning"]
            logger.info(f"  Errors         : {len(errors)}")
            logger.info(f"  Warnings       : {len(warnings)}")

        # Résultats d'exécution
        if hasattr(state, "execution_result") and state.execution_result:
            er = state.execution_result
            logger.info(f"\n🧪 Test Execution Results:")
            logger.info(f"  Total    : {er.get('total', 0)}")
            logger.info(f"  Passed   : {er.get('passed', 0)}")
            logger.info(f"  Failed   : {er.get('failed', 0)}")
            logger.info(f"  Skipped  : {er.get('skipped', 0)}")
            logger.info(f"  Pass Rate: {er.get('pass_rate', 0)}%")
            if er.get("report_path"):
                logger.info(f"  Report   : {er['report_path']}")
            if er.get("hints"):
                logger.info(f"  Hints:")
                for h in er["hints"]:
                    logger.warning(f"    → {h}")

        if state.errors:
            logger.info(f"\n❌ Errors ({len(state.errors)}):")
            for err in state.errors:
                logger.error(f"  - {err}")

        if state.warnings:
            logger.info(f"\n⚠️ Warnings ({len(state.warnings)}):")
            for w in state.warnings[:5]:
                logger.warning(f"  - {w}")

        logger.info("\n" + "=" * 80)
        if state.errors:
            logger.error("❌ WORKFLOW COMPLETED WITH ERRORS")
        elif state.warnings:
            logger.warning("⚠️ WORKFLOW COMPLETED WITH WARNINGS")
        else:
            logger.success("✅ WORKFLOW COMPLETED SUCCESSFULLY — Tests exécutés sur le backend!")
        logger.info("=" * 80 + "\n")

    # ------------------------------------------------------------------
    # Async version
    # ------------------------------------------------------------------

    async def arun(
        self,
        user_story:    str,
        service_name:  str,
        swagger_spec:  dict = None,
        swagger_specs: dict = None,
        config:        dict = None,
    ) -> TestAutomationState:
        import uuid
        from datetime import datetime

        workflow_id = (
            f"{service_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            f"_{str(uuid.uuid4())[:8]}"
        )
        final_swagger_specs = swagger_specs or {}
        if not final_swagger_specs and swagger_spec:
            final_swagger_specs = {"primary": swagger_spec}

        initial_state = TestAutomationState(
            workflow_id=workflow_id,
            user_story=user_story,
            service_name=service_name,
            swagger_spec=swagger_spec or {},
            swagger_specs=final_swagger_specs,
            config=config or {},
        )

        result = await self.graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": service_name}},
        )
        final_state = TestAutomationState(**result) if isinstance(result, dict) else result
        final_state.workflow_status = "failed" if final_state.errors else "completed"
        self._log_workflow_summary(final_state)
        return final_state

    def get_workflow_state(self, thread_id: str) -> TestAutomationState:
        try:
            snapshot = self.graph.get_state({"configurable": {"thread_id": thread_id}})
            if snapshot and snapshot.values:
                return TestAutomationState(**snapshot.values)
            return None
        except Exception as e:
            logger.error(f"Error retrieving state: {e}")
            return None


def create_workflow() -> TestAutomationWorkflow:
    return TestAutomationWorkflow()


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    from pathlib import Path

    logger.info("Testing workflow creation...")
    workflow = create_workflow()

    examples_dir = Path(__file__).parent.parent / "examples"

    user_story_path = examples_dir / "sample_user_story.md"
    user_story = (
        user_story_path.read_text(encoding="utf-8")
        if user_story_path.exists()
        else """
User Story: Employee Leave Request
As an employee I want to submit leave requests through the API.
Acceptance Criteria:
- AC1: Employee can submit leave request with start date, end date, and leave type
- AC2: System validates leave balance exists (API returns balance field)
- AC3: System returns request ID and status in response
Business Rules:
- BR1: API must return 200 OK for valid requests
- BR2: API must return request status field
- BR3: API response must include request ID
"""
    )

    swagger_specs = {}
    for key, filename in [("auth", "sample_swagger1.json"), ("leave", "sample_swagger2.json")]:
        path = examples_dir / filename
        if path.exists():
            with open(path, encoding="utf-8") as f:
                swagger_specs[key] = json.load(f)

    logger.info("Running test workflow...")
    try:
        final_state = workflow.run(
            user_story=user_story,
            service_name="leave-request-service",
            swagger_specs=swagger_specs,
        )
        logger.success("✅ Workflow test completed successfully!")
        summary = final_state.get_workflow_summary()
        logger.info("\n📊 Summary:")
        for k, v in summary.items():
            logger.info(f"  {k}: {v}")
    except Exception as e:
        logger.error(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()