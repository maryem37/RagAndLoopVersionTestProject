"""
Agent 5: Test Executor
Runs generated Cucumber/JUnit contract-level E2E tests and captures results.

FIXES applied v2:
  1. _run_maven: when shell=True on Windows, subprocess.run must receive the
     command as a SINGLE STRING (not a list). Passing a list with shell=True
     causes Python to join only the first element and ignore the rest on
     Windows (cmd.exe treats argv[0] as the command and discards the list).
     Fixed by joining the list into a space-separated string before passing.
  2. _parse_cucumber_json: now searches for per-service report files
     (target/cucumber-reports/<pkg>/cucumber.json) to match the updated
     runner output paths from test_writer.py, in addition to the legacy
     flat path for backward compatibility.
  3. _locate_html_report: same per-service path search as above.
  4. Minor: added explicit encoding="utf-8" to all file reads for Windows
     compatibility.
"""

import os
import re
import time
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional
from loguru import logger
from dotenv import load_dotenv

from graph.state import TestAutomationState, AgentOutput, AgentStatus
from config.settings import get_settings

# Load .env before anything reads os.environ
load_dotenv(Path(__file__).parent.parent / ".env")


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

class TestExecutionResult:
    """Holds the result of a test execution run."""

    def __init__(self):
        self.total: int = 0
        self.passed: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        self.errors: List[str] = []
        self.duration_ms: float = 0.0
        self.raw_output: str = ""
        self.report_path: Optional[Path] = None
        self.success: bool = False

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.passed / self.total) * 100, 2)

    def __repr__(self):
        return (
            f"TestExecutionResult(total={self.total}, passed={self.passed}, "
            f"failed={self.failed}, skipped={self.skipped}, "
            f"pass_rate={self.pass_rate}%)"
        )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class TestExecutorAgent:
    """
    Agent 5: Executes generated Cucumber/JUnit contract tests.

    Responsibilities:
    - Copy .feature files into the Maven project structure
    - Run `mvn clean test` using the detected Maven executable
    - Parse Surefire / Cucumber JSON reports
    - Populate state with execution results
    - Detect environment issues (missing Java, Maven, token, services down)
    """

    def __init__(self):
        self.settings = get_settings()
        self._java_cmd = self._detect_java()
        self._mvn_cmd  = self._detect_maven()

        logger.info(
            f"✅ Test Executor initialized  "
            f"[java={'✓' if self._java_cmd else '✗'}] "
            f"[maven={'✓' if self._mvn_cmd else '✗'}]"
        )

    # ------------------------------------------------------------------
    # Tool detection
    # ------------------------------------------------------------------

    def _detect_java(self) -> Optional[str]:
        for cmd in ["java", "java.exe"]:
            if shutil.which(cmd):
                return cmd
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            candidate = Path(java_home) / "bin" / "java"
            if candidate.exists():
                return str(candidate)
        logger.warning("⚠️ java not found in PATH or JAVA_HOME")
        return None

    def _detect_maven(self) -> Optional[str]:
        # 1. Check PATH first (covers mvn.cmd on Windows)
        for cmd in ["mvn", "mvn.cmd", "mvn.exe"]:
            found = shutil.which(cmd)
            if found:
                return found

        # 2. Check environment variables
        mvn_home = os.environ.get("MAVEN_HOME") or os.environ.get("M2_HOME")
        if mvn_home:
            for name in ["mvn", "mvn.cmd"]:
                candidate = Path(mvn_home) / "bin" / name
                if candidate.exists():
                    return str(candidate)

        # 3. Check the common Windows download location as last resort
        common = Path(r"C:\Users") / os.environ.get("USERNAME", "") / "Downloads"
        for p in common.glob("apache-maven-*/bin/mvn.cmd"):
            return str(p)

        logger.warning("⚠️ mvn not found in PATH, MAVEN_HOME, or M2_HOME")
        return None

    # ------------------------------------------------------------------
    # JWT token helper
    # ------------------------------------------------------------------

    def _get_jwt_token(self) -> str:
        """
        Read JWT token — tries os.environ first (populated by load_dotenv),
        then falls back to settings.test_execution.jwt_token.
        """
        token = (
            os.environ.get("TEST_JWT_TOKEN", "")
            or (self.settings.test_execution.jwt_token or "")
        ).strip()
        return token

    # ------------------------------------------------------------------
    # Pre-flight checks
    # ------------------------------------------------------------------

    def _preflight_checks(self, state: TestAutomationState) -> List[str]:
        """Return list of blocking issues before attempting execution."""
        issues = []

        if not self._java_cmd:
            issues.append("Java is not installed or not in PATH.")

        if not self._mvn_cmd:
            issues.append(
                "Maven (mvn) is not installed or not in PATH. "
                "Add Maven's bin directory to your system PATH."
            )

        jwt_token = self._get_jwt_token()
        if not jwt_token:
            issues.append(
                "TEST_JWT_TOKEN is not set in .env or environment. "
                "Contract tests require a valid JWT token."
            )

        pom_file = self.settings.paths.tests_dir / "pom.xml"
        if not pom_file.exists():
            issues.append(
                f"pom.xml not found at {pom_file}. "
                "Cannot run Maven without a project descriptor."
            )

        if not state.test_files:
            issues.append(
                "No test files found in state. Run TestWriterAgent first."
            )

        return issues

    # ------------------------------------------------------------------
    # Feature file staging
    # ------------------------------------------------------------------

    def _stage_feature_files(self, state: TestAutomationState) -> List[Path]:
        resources_dir = (
            self.settings.paths.tests_dir
            / "src" / "test" / "resources" / "features"
        )
        resources_dir.mkdir(parents=True, exist_ok=True)

        # Delete ALL old feature files before staging — prevents stale
        # files from previous runs causing undefined step errors
        for old in resources_dir.glob("*.feature"):
            old.unlink()
            logger.info(f"   🗑 Removed old feature: {old.name}")

        staged: List[Path] = []
        for src_path_str in (state.gherkin_files or []):
            src = Path(src_path_str)
            if src.exists():
                dest = resources_dir / src.name
                shutil.copy2(src, dest)
                staged.append(dest)
                logger.info(f"   ✓ Staged: {src.name} → {dest}")
            else:
                logger.warning(f"   ⚠ Feature file not found: {src}")

        logger.info(
            f"   {len(staged)} .feature file(s) staged in {resources_dir}"
        )
        return staged

    # ------------------------------------------------------------------
    # Maven execution
    # ------------------------------------------------------------------

    def _build_mvn_command(self, service_name: str) -> str:
        """
        Build the Maven command as a SINGLE STRING.

        FIX: subprocess.run with shell=True on Windows requires a string
        command, not a list. When passed a list with shell=True, Python on
        Windows passes only argv[0] to cmd.exe and discards all subsequent
        arguments — so -Dservice.name, -DTEST_JWT_TOKEN, etc. are silently
        lost and Maven runs with no properties set.

        Returning a string here ensures the full command reaches cmd.exe.
        """
        jwt_token = self._get_jwt_token()

        # Quote the mvn path in case it contains spaces (e.g. C:\Program Files\...)
        mvn = f'"{self._mvn_cmd}"' if " " in str(self._mvn_cmd) else str(self._mvn_cmd)

        parts = [
            mvn,
            "clean",
            "test",
            f"-Dservice.name={service_name}",
        ]

        if jwt_token:
            parts.append(f"-DTEST_JWT_TOKEN={jwt_token}")

        parts.append(
            f"-DAUTH_BASE_URL="
            f"{os.environ.get('AUTH_BASE_URL', 'http://localhost:9000')}"
        )
        parts.append(
            f"-DLEAVE_BASE_URL="
            f"{os.environ.get('LEAVE_BASE_URL', 'http://localhost:9001')}"
        )

        return " ".join(parts)

    def _run_maven(self, tests_dir: Path, service_name: str) -> TestExecutionResult:
        """Execute Maven and capture output."""
        result = TestExecutionResult()

        # FIX: cmd is now a string, not a list (required for shell=True on Windows)
        cmd = self._build_mvn_command(service_name)

        logger.info(f"   Running: {cmd}")
        logger.info(f"   Working directory: {tests_dir}")

        start = time.time()
        try:
            proc = subprocess.run(
                cmd,                    # ← string, not list
                cwd=str(tests_dir),
                capture_output=True,
                text=True,
                timeout=300,
                shell=True,             # ← required on Windows for .cmd executables
                env={
                    **os.environ,
                    "TEST_JWT_TOKEN": self._get_jwt_token(),
                },
            )
            result.raw_output = proc.stdout + proc.stderr
            result.success = proc.returncode == 0

            # Log first 2000 chars of Maven output for diagnostics
            if result.raw_output:
                preview = result.raw_output[:2000]
                logger.debug(f"   Maven output (first 2000 chars):\n{preview}")

        except subprocess.TimeoutExpired:
            result.raw_output = "❌ Maven execution timed out after 300s."
            result.errors.append("Execution timeout exceeded.")
            result.success = False
        except FileNotFoundError as exc:
            result.raw_output = (
                f"❌ Maven executable not found: {exc}\n"
                f"   Tried: {self._mvn_cmd}\n"
                f"   Add Maven's bin/ directory to your system PATH."
            )
            result.errors.append(str(exc))
            result.success = False
        except Exception as exc:
            result.raw_output = str(exc)
            result.errors.append(str(exc))
            result.success = False

        result.duration_ms = (time.time() - start) * 1000
        return result

    # ------------------------------------------------------------------
    # Report parsing
    # ------------------------------------------------------------------

    def _parse_surefire_summary(
        self, tests_dir: Path, result: TestExecutionResult
    ) -> None:
        """Parse Maven Surefire summary from stdout/stderr or XML reports."""

        # 1. Fast path: parse from console output
        pattern = re.search(
            r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),"
            r"\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)",
            result.raw_output,
        )
        if pattern:
            total    = int(pattern.group(1))
            failures = int(pattern.group(2))
            errors   = int(pattern.group(3))
            skipped  = int(pattern.group(4))
            result.total   = total
            result.failed  = failures + errors
            result.skipped = skipped
            result.passed  = total - result.failed - skipped
            logger.debug(f"   Surefire (console): {result}")
            return

        # 2. Fallback: scan XML reports
        surefire_dir = tests_dir / "target" / "surefire-reports"
        if not surefire_dir.exists():
            logger.warning(
                "   surefire-reports directory not found — "
                "Maven may not have run at all."
            )
            return

        for xml_file in surefire_dir.glob("*.xml"):
            try:
                content = xml_file.read_text(encoding="utf-8")
                m = re.search(
                    r'tests="(\d+)"[^>]*failures="(\d+)"'
                    r'[^>]*errors="(\d+)"[^>]*skipped="(\d+)"',
                    content,
                )
                if m:
                    result.total   += int(m.group(1))
                    result.failed  += int(m.group(2)) + int(m.group(3))
                    result.skipped += int(m.group(4))
            except Exception:
                pass

        result.passed = result.total - result.failed - result.skipped

    def _parse_cucumber_json(
        self, tests_dir: Path, result: TestExecutionResult
    ) -> None:
        """
        Supplement stats from Cucumber JSON reports.

        FIX: test_writer.py now writes reports to
          target/cucumber-reports/<package_name>/cucumber.json
        so we search both the legacy flat path and all per-service
        subdirectories, then aggregate across all found files.
        """
        import json

        reports_root = tests_dir / "target" / "cucumber-reports"

        # Collect all cucumber.json files: flat legacy + per-service subdirs
        json_reports: List[Path] = []
        flat = reports_root / "cucumber.json"
        if flat.exists():
            json_reports.append(flat)
        for sub in reports_root.glob("*/cucumber.json"):
            if sub not in json_reports:
                json_reports.append(sub)

        if not json_reports:
            logger.debug("   No Cucumber JSON reports found yet.")
            return

        passed = failed = skipped = 0

        for json_report in json_reports:
            try:
                data = json.loads(json_report.read_text(encoding="utf-8"))
                for feature in data:
                    for scenario in feature.get("elements", []):
                        statuses = [
                            step.get("result", {}).get("status", "undefined")
                            for step in scenario.get("steps", [])
                        ]
                        if all(s == "passed" for s in statuses):
                            passed += 1
                        elif any(s in ("failed", "undefined") for s in statuses):
                            failed += 1
                            for step in scenario.get("steps", []):
                                err = step.get("result", {}).get("error_message")
                                if err:
                                    result.errors.append(
                                        f"[{scenario.get('name', '?')}] {err[:200]}"
                                    )
                        else:
                            skipped += 1

                # Use the first report found as the primary report path
                if result.report_path is None:
                    result.report_path = json_report

                logger.info(f"   Cucumber JSON report parsed: {json_report}")

            except Exception as exc:
                logger.warning(f"   Could not parse Cucumber JSON report {json_report}: {exc}")

        if passed + failed + skipped > 0:
            result.total   = passed + failed + skipped
            result.passed  = passed
            result.failed  = failed
            result.skipped = skipped

    def _locate_html_report(
        self, tests_dir: Path, result: TestExecutionResult
    ) -> None:
        """
        Find HTML report.

        FIX: check both flat legacy path and per-service subdirectory paths
        (target/cucumber-reports/<pkg>/cucumber.html) to match the updated
        runner output from test_writer.py.
        """
        reports_root = tests_dir / "target" / "cucumber-reports"

        # Legacy flat path
        flat_html = reports_root / "cucumber.html"
        if flat_html.exists():
            result.report_path = flat_html
            logger.info(f"   HTML report: {flat_html}")
            return

        # Per-service subdirectory paths
        for sub_html in reports_root.glob("*/cucumber.html"):
            result.report_path = sub_html
            logger.info(f"   HTML report: {sub_html}")
            return  # Use the first one found

    # ------------------------------------------------------------------
    # Failure analysis
    # ------------------------------------------------------------------

    def _analyze_failures(self, result: TestExecutionResult) -> List[str]:
        """Extract actionable failure hints from raw Maven output."""
        hints = []
        output = result.raw_output

        if "Connection refused" in output or "ConnectException" in output:
            hints.append(
                "One or more services are unreachable. "
                "Ensure all microservices are running on ports 9000/9001."
            )
        if "401" in output or "Unauthorized" in output:
            hints.append(
                "HTTP 401 detected. "
                "Verify TEST_JWT_TOKEN is valid and not expired."
            )
        if "403" in output or "Forbidden" in output:
            hints.append(
                "HTTP 403 detected. "
                "The JWT token may lack the required role/permissions."
            )
        if "404" in output or "Not Found" in output:
            hints.append(
                "HTTP 404 detected. "
                "An API endpoint may have changed — update your Swagger specs."
            )
        if "ClassNotFoundException" in output or "NoClassDefFoundError" in output:
            hints.append(
                "Java class not found. "
                "Run `mvn compile` in the tests directory or check step definitions."
            )
        if "Undefined step" in output or "PendingException" in output:
            hints.append(
                "Undefined Cucumber steps detected. "
                "Re-run the TestWriterAgent to regenerate step definitions."
            )
        if "[WinError 2]" in output or "Le fichier spécifié est introuvable" in output:
            hints.append(
                "Maven executable not found (WinError 2). "
                "Add Maven's bin/ directory to your system PATH, "
                "or set MAVEN_HOME / M2_HOME in your .env file."
            )
        if "BUILD FAILURE" in output and not hints:
            hints.append(
                "Maven BUILD FAILURE with no specific pattern detected. "
                "Check the raw Maven output for details."
            )

        return hints

    # ------------------------------------------------------------------
    # Main execute() method
    # ------------------------------------------------------------------

    def execute(self, state: TestAutomationState) -> TestAutomationState:
        """LangGraph node entry point."""
        start_time = time.time()
        logger.info(f"🚀 Test Executor starting for: {state.service_name}")

        # 1. Pre-flight checks
        blocking = self._preflight_checks(state)
        if blocking:
            for issue in blocking:
                logger.error(f"   ❌ Pre-flight: {issue}")
                state.add_error(f"Test execution pre-flight failed: {issue}")

            duration = (time.time() - start_time) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="test_executor",
                status=AgentStatus.FAILED,
                duration_ms=duration,
                error_message="; ".join(blocking),
            ))
            return state

        tests_dir = self.settings.paths.tests_dir

        # 2. Stage feature files
        logger.info("1️⃣  Staging .feature files...")
        staged = self._stage_feature_files(state)
        if not staged:
            state.add_warning(
                "No .feature files were staged — Cucumber will find no scenarios."
            )

        # 3. Run Maven
        logger.info("2️⃣  Executing Maven contract tests...")
        exec_result = self._run_maven(tests_dir, state.service_name)

        # 4. Parse reports
        logger.info("3️⃣  Parsing test reports...")
        self._parse_surefire_summary(tests_dir, exec_result)
        self._parse_cucumber_json(tests_dir, exec_result)
        self._locate_html_report(tests_dir, exec_result)

        # 5. Failure analysis
        hints = self._analyze_failures(exec_result)
        for hint in hints:
            state.add_warning(f"Execution hint: {hint}")

        # 6. Log summary
        if exec_result.success and exec_result.failed == 0:
            logger.success(
                f"✅ All tests PASSED  "
                f"({exec_result.passed}/{exec_result.total}  "
                f"pass_rate={exec_result.pass_rate}%)"
            )
        else:
            logger.warning(
                f"⚠️  Tests completed with failures  "
                f"passed={exec_result.passed}  failed={exec_result.failed}  "
                f"skipped={exec_result.skipped}  "
                f"pass_rate={exec_result.pass_rate}%"
            )
            for err in exec_result.errors[:5]:
                logger.warning(f"   ↳ {err}")

        # 7. Update state
        state.execution_result = {
            "total":       exec_result.total,
            "passed":      exec_result.passed,
            "failed":      exec_result.failed,
            "skipped":     exec_result.skipped,
            "pass_rate":   exec_result.pass_rate,
            "duration_ms": exec_result.duration_ms,
            "success":     exec_result.success,
            "errors":      exec_result.errors,
            "report_path": (
                str(exec_result.report_path)
                if exec_result.report_path else None
            ),
            "hints": hints,
            "raw_output_tail": exec_result.raw_output[-3000:],  # last 3000 chars
        }

        duration = (time.time() - start_time) * 1000
        state.add_agent_output(AgentOutput(
            agent_name="test_executor",
            status=AgentStatus.SUCCESS if exec_result.success else AgentStatus.FAILED,
            duration_ms=duration,
            output_data={
                "total":                exec_result.total,
                "passed":               exec_result.passed,
                "failed":               exec_result.failed,
                "skipped":              exec_result.skipped,
                "pass_rate":            exec_result.pass_rate,
                "feature_files_staged": len(staged),
                "report_path": (
                    str(exec_result.report_path)
                    if exec_result.report_path else None
                ),
            },
            error_message=(
                "; ".join(exec_result.errors[:3])
                if exec_result.errors else None
            ),
        ))

        logger.success(f"✅ Test Executor finished in {duration:.0f}ms")
        return state


# ---------------------------------------------------------------------------
# LangGraph node wrapper
# ---------------------------------------------------------------------------

def test_executor_node(state: TestAutomationState) -> TestAutomationState:
    """LangGraph node wrapper for the Test Executor agent."""
    agent = TestExecutorAgent()
    return agent.execute(state)