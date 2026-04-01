"""
graph/workflow.py
------------------------------
LangGraph Workflow — Multi-Agent Test Automation Pipeline

Pipeline:
  gherkin_generator -> gherkin_validator -> test_writer -> test_executor -> coverage_analyst -> END
"""

from typing import Literal, Optional
from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import TestAutomationState, AgentStatus
from agents.gherkin_generator import gherkin_generator_node
from agents.gherkin_validator import gherkin_validator_node
from agents.test_writer        import test_writer_node
from agents.test_executor      import test_executor_node
from agents.coverage_analyst   import coverage_analyst_node   # ← Agent 6


class TestAutomationWorkflow:

    def __init__(self):
        self.memory = MemorySaver()
        self.graph  = self._build_graph()
        logger.info("✅ Test Automation Workflow initialized")
        logger.info(
            "[LIST] Pipeline: gherkin_generator -> gherkin_validator -> "
            "test_writer -> test_executor -> coverage_analyst"
        )

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(TestAutomationState)

        # ── Nodes ------------------------------
        workflow.add_node("gherkin_generator",  gherkin_generator_node)
        workflow.add_node("gherkin_validator",  gherkin_validator_node)
        workflow.add_node("test_writer",        test_writer_node)
        workflow.add_node("test_executor",      test_executor_node)
        workflow.add_node("coverage_analyst",   coverage_analyst_node)   # ← NEW

        # ── Entry point ------------------------------
        workflow.set_entry_point("gherkin_generator")

        # ── Transitions ------------------------------
        workflow.add_conditional_edges(
            "gherkin_generator",
            self._after_generation,
            {"validate": "gherkin_validator", "end": END},
        )
        workflow.add_conditional_edges(
            "gherkin_validator",
            self._after_validation,
            {"write_tests": "test_writer", "end": END},
        )
        workflow.add_conditional_edges(
            "test_writer",
            self._after_writing,
            {"execute": "test_executor", "end": END},
        )
        # Always analyse coverage after execution (even on partial failure)
        workflow.add_edge("test_executor",    "coverage_analyst")   # ← NEW
        workflow.add_edge("coverage_analyst", END)                  # ← NEW

        logger.info("[CHART] Workflow graph compiled successfully")
        return workflow.compile(checkpointer=self.memory)

    # ── Routing conditions ------------------------------

    def _after_generation(self, state: TestAutomationState) -> Literal["validate", "end"]:
        last = state.agent_outputs[-1] if state.agent_outputs else None
        if last and last.status == AgentStatus.SUCCESS and state.gherkin_content and state.gherkin_files:
            logger.info("[OK] Gherkin generation successful -> validation")
            return "validate"
        logger.warning("[FAIL] Gherkin generation failed -> end")
        return "end"

    def _after_validation(self, state: TestAutomationState) -> Literal["write_tests", "end"]:
        if state.validation_result:
            errors = sum(1 for i in state.validation_result.issues if i.level == "error")
            if state.validation_result.is_valid or errors == 0:
                logger.info("[OK] Validation passed -> test writing")
                return "write_tests"
            logger.error("[FAIL] Critical validation errors -> end")
            return "end"
        logger.warning("[FAIL] No validation result -> end")
        return "end"

    def _after_writing(self, state: TestAutomationState) -> Literal["execute", "end"]:
        last = state.agent_outputs[-1] if state.agent_outputs else None
        if last and last.status == AgentStatus.SUCCESS and state.test_files:
            logger.info("[OK] Test files generated -> execution")
            return "execute"
        logger.warning("[FAIL] Test writing failed -> end")
        return "end"

    # ── Main run ------------------------------

    def run(
        self,
        user_story:    str,
        service_name:  str,
        swagger_spec:  dict = None,
        swagger_specs: dict = None,
        config:        dict = None,
        is_e2e:        bool = False,
        e2e_services:  list = None,
    ) -> TestAutomationState:
        import uuid
        from datetime import datetime

        logger.info("=" * 80)
        logger.info("[START] Starting Test Automation Workflow")
        logger.info(f"   Service: {service_name}")
        logger.info("=" * 80)

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
            is_e2e=is_e2e,
            e2e_services=e2e_services or [],
        )

        result = self.graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": service_name}},
        )
        final_state = TestAutomationState(**result) if isinstance(result, dict) else result
        final_state.workflow_status = "failed" if final_state.errors else "completed"
        self._log_summary(final_state)
        return final_state

    # ── Summary ------------------------------

    def _log_summary(self, state: TestAutomationState) -> None:
        logger.info("\n" + "=" * 80)
        logger.info("[CHART] WORKFLOW EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Workflow ID : {state.workflow_id}")
        logger.info(f"Service     : {state.service_name}")
        logger.info(f"Status      : {state.workflow_status.upper()}")

        logger.info("\n[LIST] Agent Execution:")
        for output in state.agent_outputs:
            icon = "[OK]" if output.status == AgentStatus.SUCCESS else "[FAIL]"
            logger.info(f"  {icon} {output.agent_name}  [{output.duration_ms:.0f}ms]")
            if output.agent_name == "coverage_analyst" and output.output_data:
                d = output.output_data
                logger.info(f"      Lines    : {d.get('line_coverage_%', 'N/A')}%")
                logger.info(f"      Branches : {d.get('branch_coverage_%', 'N/A')}%")
                logger.info(f"      Methods  : {d.get('method_coverage_%', 'N/A')}%")
                logger.info(f"      QG       : {'PASSED ✅' if d.get('quality_gate_passed') else 'FAILED [ERROR]'}")
                if d.get("yaml_report"):
                    logger.info(f"      YAML     : {d['yaml_report']}")
                if d.get("json_report"):
                    logger.info(f"      JSON     : {d['json_report']}")

        logger.info("\n[FILE] Artifacts:")
        logger.info(f"  Gherkin files : {len(state.gherkin_files)}")
        logger.info(f"  Test files    : {len(state.test_files)}")
        coverage_files = getattr(state, "coverage_files", [])
        logger.info(f"  Coverage files: {len(coverage_files)}")
        for f in coverage_files:
            logger.info(f"    - {f}")

        if state.errors:
            for err in state.errors:
                logger.error(f"  [ERROR] {err}")

        logger.info("=" * 80 + "\n")

    # ── Async run ------------------------------

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
        self._log_summary(final_state)
        return final_state

    def get_workflow_state(self, thread_id: str) -> Optional[TestAutomationState]:
        try:
            snapshot = self.graph.get_state({"configurable": {"thread_id": thread_id}})
            if snapshot and snapshot.values:
                return TestAutomationState(**snapshot.values)
        except Exception as e:
            logger.error(f"Error retrieving state: {e}")
        return None


def create_workflow() -> TestAutomationWorkflow:
    return TestAutomationWorkflow()