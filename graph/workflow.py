"""
graph/workflow.py
------------------------------
LangGraph Workflow — Multi-Agent Test Automation Pipeline

Pipeline:
  scenario_designer -> gherkin_generator -> gherkin_validator -> test_writer
  gherkin_validator -> gherkin_generator (bounded validation retry)
  -> test_executor -> failure_analyst? -> test_writer (bounded retry)
  -> coverage_analyst? -> scenario_designer (bounded coverage retry) -> END
"""

from typing import Literal, Optional
import os
from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import TestAutomationState, AgentStatus
from agents.scenario_designer   import scenario_designer_agent_node  # ← Agent 0 (NEW)
from agents.gherkin_generator import gherkin_generator_node
from agents.gherkin_validator import gherkin_validator_node
from agents.test_writer        import test_writer_node
from agents.test_executor      import test_executor_node
from agents.failure_analyst    import failure_analyst_node
from agents.coverage_analyst   import coverage_analyst_node   # ← Agent 6


class TestAutomationWorkflow:

    def __init__(self):
        self.memory = MemorySaver()
        self.graph  = self._build_graph()
        logger.info("✅ Test Automation Workflow initialized")
        logger.info(
            "[LIST] Pipeline: scenario_designer -> gherkin_generator -> gherkin_validator -> "
            "test_writer -> test_executor -> failure_analyst? -> coverage_analyst? "
            "(validation failures loop back to gherkin_generator)"
        )

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(TestAutomationState)

        # ── Nodes ------------------------------
        workflow.add_node("scenario_designer",   scenario_designer_agent_node)  # ← Agent 0 (NEW)
        workflow.add_node("gherkin_generator",  gherkin_generator_node)
        workflow.add_node("gherkin_validator",  gherkin_validator_node)
        workflow.add_node("test_writer",        test_writer_node)
        workflow.add_node("test_executor",      test_executor_node)
        workflow.add_node("failure_analyst",    failure_analyst_node)
        workflow.add_node("coverage_analyst",   coverage_analyst_node)   # ← Agent 6

        # ── Entry point ------------------------------
        workflow.set_entry_point("scenario_designer")  # ← NOW STARTS WITH SCENARIO DESIGNER

        # ── Transitions ------------------------------
        workflow.add_edge("scenario_designer", "gherkin_generator")  # ← NEW
        workflow.add_conditional_edges(
            "gherkin_generator",
            self._after_generation,
            {"validate": "gherkin_validator", "end": END},
        )
        workflow.add_conditional_edges(
            "gherkin_validator",
            self._after_validation,
            {
                "write_tests": "test_writer",
                "regenerate": "gherkin_generator",
                "end": END,
            },
        )
        workflow.add_conditional_edges(
            "test_writer",
            self._after_writing,
            {"execute": "test_executor", "end": END},
        )
        workflow.add_conditional_edges(
            "test_executor",
            self._after_execution,
            {"analyze_failures": "failure_analyst", "coverage": "coverage_analyst"},
        )
        workflow.add_conditional_edges(
            "failure_analyst",
            self._after_failure_analysis,
            {"rewrite_tests": "test_writer", "coverage": "coverage_analyst"},
        )
        workflow.add_conditional_edges(
            "coverage_analyst",
            self._after_coverage_analysis,
            {"improve_coverage": "scenario_designer", "end": END},
        )

        logger.info("[CHART] Workflow graph compiled successfully")
        return workflow.compile(checkpointer=self.memory)

    # ── Routing conditions ------------------------------

    def _max_healing_attempts(self, state: TestAutomationState) -> int:
        cfg = getattr(state, "config", {}) or {}
        raw = cfg.get("max_healing_attempts", os.getenv("MAX_HEALING_ATTEMPTS", "3"))
        try:
            value = int(raw)
        except Exception:
            value = 3
        return max(0, value)

    def _max_coverage_improvement_attempts(self, state: TestAutomationState) -> int:
        cfg = getattr(state, "config", {}) or {}
        raw = cfg.get(
            "max_coverage_improvement_attempts",
            os.getenv("MAX_COVERAGE_IMPROVEMENT_ATTEMPTS", "1"),
        )
        try:
            value = int(raw)
        except Exception:
            value = 1
        return max(0, value)

    def _max_gherkin_validation_retries(self, state: TestAutomationState) -> int:
        cfg = getattr(state, "config", {}) or {}
        raw = cfg.get(
            "max_gherkin_validation_retries",
            os.getenv("MAX_GHERKIN_VALIDATION_RETRIES", "2"),
        )
        try:
            value = int(raw)
        except Exception:
            value = 2
        return max(0, value)

    def _coverage_improvement_enabled(self, state: TestAutomationState) -> bool:
        cfg = getattr(state, "config", {}) or {}
        if "enable_coverage_improvement" in cfg:
            return bool(cfg.get("enable_coverage_improvement"))
        raw = os.getenv("ENABLE_COVERAGE_IMPROVEMENT")
        if raw is None:
            return True
        return raw.strip().lower() in {"1", "true", "yes", "y", "on"}

    def _clear_retryable_execution_errors(self, state: TestAutomationState) -> None:
        retryable_prefixes = (
            "Maven test execution failed",
            "Test threshold not met",
            "No tests were executed",
            "Test execution pre-flight failed",
        )
        state.errors = [
            err for err in state.errors
            if not any(str(err).startswith(prefix) for prefix in retryable_prefixes)
        ]

    def _after_generation(self, state: TestAutomationState) -> Literal["validate", "end"]:
        last = state.agent_outputs[-1] if state.agent_outputs else None
        if last and last.status == AgentStatus.SUCCESS and state.gherkin_content and state.gherkin_files:
            logger.info("[OK] Gherkin generation successful -> validation")
            return "validate"
        logger.warning("[FAIL] Gherkin generation failed -> end")
        return "end"

    def _after_validation(self, state: TestAutomationState) -> Literal["write_tests", "regenerate", "end"]:
        if state.validation_result:
            errors = sum(1 for i in state.validation_result.issues if i.level == "error")
            if state.validation_result.is_valid or errors == 0:
                logger.info("[OK] Validation passed -> test writing")
                return "write_tests"

            attempts_used = len(getattr(state, "gherkin_validation_retries", []) or [])
            max_attempts = self._max_gherkin_validation_retries(state)
            if attempts_used <= max_attempts:
                logger.warning(
                    f"[RETRY] Critical validation errors -> gherkin_generator "
                    f"(attempt {attempts_used}/{max_attempts})"
                )
                return "regenerate"

            logger.error(
                f"[FAIL] Critical validation errors -> end "
                f"(attempts_used={attempts_used}, max_attempts={max_attempts})"
            )
            return "end"
        logger.warning("[FAIL] No validation result -> end")
        return "end"

    def _after_writing(self, state: TestAutomationState) -> Literal["execute", "end"]:
        def _env_flag(name: str, default: bool = False) -> bool:
            v = os.getenv(name)
            if v is None:
                return default
            return v.strip().lower() in {"1", "true", "yes", "y", "on"}

        if _env_flag("SKIP_TEST_EXECUTION", False):
            logger.warning("[SKIP] SKIP_TEST_EXECUTION=1 -> skipping test_executor + coverage_analyst")
            return "end"

        last = state.agent_outputs[-1] if state.agent_outputs else None
        if last and last.status == AgentStatus.SUCCESS and state.test_files:
            logger.info("[OK] Test files generated -> execution")
            return "execute"
        logger.warning("[FAIL] Test writing failed -> end")
        return "end"

    def _after_execution(self, state: TestAutomationState) -> Literal["analyze_failures", "coverage"]:
        execution = state.execution_result or {}
        if bool(execution.get("success", False)):
            self._clear_retryable_execution_errors(state)
            logger.info("[OK] Test execution passed threshold -> coverage")
            return "coverage"

        failed = int(execution.get("failed", 0) or 0)
        attempts_used = len(state.healing_attempts)
        max_attempts = self._max_healing_attempts(state)

        if failed > 0 and attempts_used < max_attempts:
            self._clear_retryable_execution_errors(state)
            logger.warning(
                f"[RETRY] Test execution failed -> failure analysis "
                f"(attempt {attempts_used + 1}/{max_attempts})"
            )
            return "analyze_failures"

        logger.warning(
            f"[STOP] Execution failure will not be retried "
            f"(failed={failed}, attempts_used={attempts_used}, max_attempts={max_attempts})"
        )
        return "coverage"

    def _after_failure_analysis(self, state: TestAutomationState) -> Literal["rewrite_tests", "coverage"]:
        analysis = getattr(state, "failure_analysis", None) or {}
        retry_recommended = bool(analysis.get("retry_recommended", False))
        retry_target = str(analysis.get("retry_target", "none"))
        attempts_used = len(state.healing_attempts)
        max_attempts = self._max_healing_attempts(state)

        if retry_recommended and retry_target == "test_writer" and attempts_used <= max_attempts:
            logger.info(
                f"[REPAIR] Failure analysis routed to test_writer "
                f"(attempt {attempts_used}/{max_attempts})"
            )
            return "rewrite_tests"

        logger.warning(
            f"[STOP] Failure analysis ended retry loop "
            f"(retry_recommended={retry_recommended}, target={retry_target})"
        )
        return "coverage"

    def _after_coverage_analysis(self, state: TestAutomationState) -> Literal["improve_coverage", "end"]:
        if not self._coverage_improvement_enabled(state):
            logger.info("[STOP] Coverage improvement loop disabled -> end")
            return "end"

        execution = state.execution_result or {}
        failed = int(execution.get("failed", 0) or 0)
        allow_retry_with_failures = any(
            os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}
            for name in ("ALLOW_COVERAGE_RETRY_WITH_FAILURES", "COVERAGE_LOOP_IGNORE_TEST_FAILURES")
        )
        if failed > 0 and not allow_retry_with_failures:
            logger.warning(
                f"[STOP] Coverage loop skipped because tests are still failing (failed={failed})"
            )
            return "end"
        if failed > 0 and allow_retry_with_failures:
            logger.warning(
                f"[COVERAGE RETRY] Tests have failures (failed={failed}) but "
                f"coverage retry with failures is enabled — proceeding to coverage analysis"
            )

        feedback = getattr(state, "coverage_feedback", None) or {}

        retry_recommended = bool(feedback.get("retry_recommended", False))
        attempts_used = len(getattr(state, "coverage_improvement_attempts", []) or [])
        max_attempts = self._max_coverage_improvement_attempts(state)

        if retry_recommended and attempts_used <= max_attempts:
            logger.info(
                f"[COVERAGE RETRY] Coverage analysis routed to scenario_designer "
                f"(attempt {attempts_used}/{max_attempts})"
            )
            return "improve_coverage"

        logger.info(
            "[STOP] Coverage analysis ended coverage loop "
            f"(retry_recommended={retry_recommended}, attempts_used={attempts_used}, "
            f"max_attempts={max_attempts})"
        )
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

        # Treat a failed coverage quality gate as a workflow failure by default.
        # Opt out by setting ALLOW_COVERAGE_QG_FAILURE=1 or FAIL_ON_COVERAGE_QG=0.
        def _env_flag(name: str, default: bool = False) -> bool:
            v = os.getenv(name)
            if v is None:
                return default
            return v.strip().lower() in {"1", "true", "yes", "y", "on"}

        fail_on_coverage_qg = _env_flag("FAIL_ON_COVERAGE_QG", True) and not _env_flag(
            "ALLOW_COVERAGE_QG_FAILURE", False
        )
        qg = final_state.get_coverage_quality_gate()
        if fail_on_coverage_qg and qg is False:
            violations = final_state.get_coverage_violations()
            details = "; ".join(violations) if violations else "(no details)"
            final_state.add_error(f"Coverage quality gate failed: {details}")

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
            duration_str = f"[{output.duration_ms:.0f}ms]" if output.duration_ms is not None else "[?ms]"
            logger.info(f"  {icon} {output.agent_name}  {duration_str}")
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
            if output.agent_name == "failure_analyst" and output.output_data:
                d = output.output_data
                logger.info(f"      Category : {d.get('failure_category', 'N/A')}")
                logger.info(f"      Retry    : {d.get('retry_recommended', 'N/A')}")
                logger.info(f"      Target   : {d.get('retry_target', 'N/A')}")

        logger.info("\n[FILE] Artifacts:")
        logger.info(f"  Gherkin files : {len(state.gherkin_files)}")
        logger.info(f"  Test files    : {len(state.test_files)}")
        coverage_files = getattr(state, "coverage_files", [])
        logger.info(f"  Coverage files: {len(coverage_files)}")
        logger.info(f"  Healing tries : {len(state.healing_attempts)}")
        logger.info(
            f"  Validation retries: "
            f"{len(getattr(state, 'gherkin_validation_retries', []) or [])}"
        )
        logger.info(f"  Coverage tries: {len(getattr(state, 'coverage_improvement_attempts', []) or [])}")
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

        def _env_flag(name: str, default: bool = False) -> bool:
            v = os.getenv(name)
            if v is None:
                return default
            return v.strip().lower() in {"1", "true", "yes", "y", "on"}

        fail_on_coverage_qg = _env_flag("FAIL_ON_COVERAGE_QG", True) and not _env_flag(
            "ALLOW_COVERAGE_QG_FAILURE", False
        )
        qg = final_state.get_coverage_quality_gate()
        if fail_on_coverage_qg and qg is False:
            violations = final_state.get_coverage_violations()
            details = "; ".join(violations) if violations else "(no details)"
            final_state.add_error(f"Coverage quality gate failed: {details}")

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
