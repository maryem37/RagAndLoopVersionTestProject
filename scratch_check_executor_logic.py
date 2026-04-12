from agents.test_executor import TestExecutorAgent, TestExecutionResult
from graph.state import TestAutomationState


def main() -> int:
    # Minimal state
    state = TestAutomationState(
        workflow_id="scratch",
        user_story="x",
        service_name="auth_leave",
        swagger_spec={},
        swagger_specs={},
    )
    state.test_files = ["dummy.java"]
    state.gherkin_files = []

    agent = TestExecutorAgent()

    # Monkeypatch preflight to pass
    agent._preflight_checks = lambda s: []
    # Avoid touching filesystem for staging
    agent._stage_feature_files = lambda s: []
    # Avoid jacoco collection/backup
    agent._collect_backend_jacoco_report = lambda: None
    agent._backup_jacoco_reports = lambda tests_dir: None
    # Skip parsing from disk; we inject our own result values
    agent._parse_surefire_summary = lambda tests_dir, r: None
    agent._parse_cucumber_json = lambda tests_dir, r: None
    agent._locate_html_report = lambda tests_dir, r: None

    # Fake maven run: returncode 0 but failed scenarios present
    fake = TestExecutionResult()
    fake.success = True
    fake.total = 10
    fake.passed = 9
    fake.failed = 1
    fake.skipped = 0
    fake.raw_output = "ok"

    agent._run_maven = lambda tests_dir, service_name: fake

    out = agent.execute(state)

    print("workflow_errors=", out.errors)
    print("agent_status=", out.agent_outputs[-1].status)
    print("execution_success=", out.execution_result.get("success"))

    # Default behavior should fail the agent + record an error.
    assert out.errors, "Expected state.errors to be non-empty when failed>0"
    assert out.agent_outputs[-1].status == "failed", "Expected agent status 'failed' when failed>0"
    assert out.execution_result.get("success") is False, "Expected execution_result.success False when failed>0"

    print("OK: executor correctly fails when scenarios fail.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
