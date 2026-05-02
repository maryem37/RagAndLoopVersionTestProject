"""
Agent 5: Test Executor
Runs generated Cucumber/JUnit contract-level E2E tests and captures results.

FIXES applied:
  1. _build_mvn_command: forces IPv4 (127.0.0.1) in AUTH_BASE_URL and LEAVE_BASE_URL
     so Java's HTTP client connects correctly on Windows (where localhost resolves
     to IPv6 ::1 at the OS level but Java connects via IPv4 127.0.0.1).
  2. _run_maven: command is a SINGLE STRING (required for shell=True on Windows).
  3. _parse_cucumber_json / _locate_html_report: searches per-service subdirectories
     in addition to the legacy flat path.
  4. Explicit encoding="utf-8" on all file reads.
"""

import os
import re
import time
import base64
import json
import subprocess
import shutil
import socket
import zipfile
from pathlib import Path
from datetime import datetime, timezone
import locale
from typing import Dict, List, Optional
from loguru import logger
from dotenv import load_dotenv

from graph.state import TestAutomationState, AgentOutput, AgentStatus
from config.settings import get_settings
from tools.jacoco_filtering import is_low_signal_jacoco_class

load_dotenv(Path(__file__).parent.parent / ".env")


def _force_ipv4(url: str) -> str:
    """Replace //localhost: with //127.0.0.1: so Java connects via IPv4."""
    return url.replace("//localhost:", "//127.0.0.1:")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _parse_jwt_claims(token: str) -> Optional[dict]:
    """Parse JWT payload claims without verifying signature.

    This is used only to surface a clear 'expired token' message before
    running the Maven tests. Never logs the token.
    """
    parts = token.split(".")
    if len(parts) < 2:
        return None
    try:
        payload = _b64url_decode(parts[1]).decode("utf-8")
        return json.loads(payload)
    except Exception:
        return None


def _redact_secrets(text: str) -> str:
    """Redact secrets from logs (never print JWTs to terminal)."""
    if not text:
        return text
    # Redact Maven system property (command-line) token.
    text = re.sub(r"(-DTEST_JWT_TOKEN=)([^\s]+)", r"\1[REDACTED]", text)
    return text


class TestExecutionResult:
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


class TestExecutorAgent:

    def __init__(self):
        self.settings = get_settings()
        self._java_cmd = self._detect_java()
        self._mvn_cmd  = self._detect_maven()
        logger.info(
            f"✅ Test Executor initialized  "
            f"[java={'[OK]' if self._java_cmd else '[FAIL]'}] "
            f"[maven={'[OK]' if self._mvn_cmd else '[FAIL]'}]"
        )

    def _detect_java(self) -> Optional[str]:
        for cmd in ["java", "java.exe"]:
            if shutil.which(cmd):
                return cmd
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            candidate = Path(java_home) / "bin" / "java"
            if candidate.exists():
                return str(candidate)
        logger.warning("[WARN]️ java not found in PATH or JAVA_HOME")
        return None

    def _detect_maven(self) -> Optional[str]:
        for cmd in ["mvn", "mvn.cmd", "mvn.exe"]:
            found = shutil.which(cmd)
            if found:
                return found
        mvn_home = os.environ.get("MAVEN_HOME") or os.environ.get("M2_HOME")
        if mvn_home:
            for name in ["mvn", "mvn.cmd"]:
                candidate = Path(mvn_home) / "bin" / name
                if candidate.exists():
                    return str(candidate)
        common = Path(r"C:\Users") / os.environ.get("USERNAME", "") / "Downloads"
        for p in common.glob("apache-maven-*/bin/mvn.cmd"):
            return str(p)
        logger.warning("[WARN]️ mvn not found in PATH, MAVEN_HOME, or M2_HOME")
        return None

    def _get_raw_jwt_token(self) -> str:
        return (
            os.environ.get("TEST_JWT_TOKEN", "")
            or (self.settings.test_execution.jwt_token or "")
        ).strip()

    def _get_jwt_token(self) -> str:
        """Return the effective JWT token to pass to Maven.

        By default this refuses to pass an expired or non-JWT token, so the
        generated Java steps will fall back to auto-login.

        Set FORCE_TEST_JWT_TOKEN=1 to require a token and fail-fast.
        Set SKIP_JWT_EXPIRY_CHECK=1 to bypass expiry validation.
        """
        raw = self._get_raw_jwt_token()
        if not raw:
            return ""

        force = os.environ.get("FORCE_TEST_JWT_TOKEN", "").strip().lower()
        force_env_token = force in {"1", "true", "yes", "y"}
        skip_jwt_exp_check = os.environ.get("SKIP_JWT_EXPIRY_CHECK", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
        }
        if skip_jwt_exp_check:
            return raw

        claims = _parse_jwt_claims(raw)
        if not claims:
            if force_env_token:
                return raw
            logger.warning(
                "[WARN] TEST_JWT_TOKEN is set but is not a valid JWT; ignoring it and falling back to auto-login. "
                "(Set FORCE_TEST_JWT_TOKEN=1 to fail-fast.)"
            )
            return ""

        exp_raw = claims.get("exp")
        now_s = int(time.time())
        exp_s: Optional[int] = None
        try:
            if isinstance(exp_raw, (int, float)):
                exp_s = int(exp_raw)
            elif isinstance(exp_raw, str) and exp_raw.strip().isdigit():
                exp_s = int(exp_raw.strip())
        except Exception:
            exp_s = None

        if exp_s is None:
            # No usable exp: keep the token (some services may accept non-expiring tokens).
            return raw

        # Small skew allowance to avoid flaky edge cases.
        if exp_s <= (now_s + 30):
            if force_env_token:
                return raw
            exp_dt = datetime.fromtimestamp(exp_s, tz=timezone.utc).isoformat()
            now_dt = datetime.fromtimestamp(now_s, tz=timezone.utc).isoformat()
            logger.warning(
                "[WARN] TEST_JWT_TOKEN is expired; ignoring it and falling back to auto-login. "
                f"(exp={exp_dt} UTC, now={now_dt} UTC)"
            )
            return ""

        return raw

    def _preflight_checks(self, state: TestAutomationState) -> List[str]:
        issues = []
        if not self._java_cmd:
            issues.append("Java is not installed or not in PATH.")
        if not self._mvn_cmd:
            issues.append(
                "Maven (mvn) is not installed or not in PATH. "
                "Add Maven's bin directory to your system PATH."
            )
        force = os.environ.get("FORCE_TEST_JWT_TOKEN", "").strip().lower()
        force_env_token = force in {"1", "true", "yes", "y"}

        raw_jwt_token = self._get_raw_jwt_token()
        if force_env_token:
            if not raw_jwt_token:
                issues.append(
                    "FORCE_TEST_JWT_TOKEN=1 but TEST_JWT_TOKEN is not set in .env or environment."
                )
            else:
                skip_jwt_exp_check = os.environ.get("SKIP_JWT_EXPIRY_CHECK", "").strip().lower() in {
                    "1", "true", "yes", "y"
                }
                if not skip_jwt_exp_check:
                    claims = _parse_jwt_claims(raw_jwt_token)
                    if not claims:
                        issues.append(
                            "TEST_JWT_TOKEN is not a valid JWT (cannot decode payload). "
                            "Provide a real token with 3 dot-separated parts."
                        )
                    else:
                        exp_raw = claims.get("exp")
                        now_s = int(time.time())
                        exp_s: Optional[int] = None
                        try:
                            if isinstance(exp_raw, (int, float)):
                                exp_s = int(exp_raw)
                            elif isinstance(exp_raw, str) and exp_raw.strip().isdigit():
                                exp_s = int(exp_raw.strip())
                        except Exception:
                            exp_s = None

                        if exp_s is None:
                            logger.warning(
                                "[WARN] JWT has no usable 'exp' claim; cannot preflight-check expiry."
                            )
                        else:
                            exp_dt = datetime.fromtimestamp(exp_s, tz=timezone.utc).isoformat()
                            now_dt = datetime.fromtimestamp(now_s, tz=timezone.utc).isoformat()
                            ttl_s = exp_s - now_s
                            logger.info(f"   JWT exp (UTC): {exp_dt}  (ttl={ttl_s}s)")

                            # Small skew allowance to avoid flaky edge cases.
                            if exp_s <= (now_s + 30):
                                issues.append(
                                    "TEST_JWT_TOKEN is expired. "
                                    f"exp={exp_dt} UTC, now={now_dt} UTC. "
                                    "Refresh the token in .env (TEST_JWT_TOKEN=...)."
                                )
                            elif ttl_s <= 15 * 60:
                                logger.warning(
                                    f"[WARN] JWT will expire soon (in {ttl_s}s). "
                                    "Tests may fail with HTTP 401 mid-run."
                                )
        else:
            if raw_jwt_token:
                effective = self._get_jwt_token()
                if effective:
                    logger.info(
                        "   TEST_JWT_TOKEN is set; generated steps will use it. (Set FORCE_TEST_JWT_TOKEN=1 to fail-fast if it is missing/blank.)"
                    )
                else:
                    logger.info(
                        "   TEST_JWT_TOKEN is set but will be ignored (expired/invalid); generated steps will fall back to auto-login."
                    )
        pom_file = self.settings.paths.tests_dir / "pom.xml"
        if not pom_file.exists():
            issues.append(
                f"pom.xml not found at {pom_file}. "
                "Cannot run Maven without a project descriptor."
            )
        if not state.test_files:
            issues.append("No test files found in state. Run TestWriterAgent first.")

        # Backend availability check (contract tests require live services).
        # Can be disabled by setting SKIP_BACKEND_PORT_CHECK=1 in the environment.
        skip_backend_check = os.environ.get("SKIP_BACKEND_PORT_CHECK", "").strip().lower() in {
            "1", "true", "yes", "y"
        }
        if not skip_backend_check:
            try:
                from tools.service_registry import get_service_registry

                registry = get_service_registry()
                enabled = registry.get_enabled_services()
                host = "127.0.0.1"

                # Retry briefly to avoid flaky failures when services are still
                # initializing or temporarily restarting.
                try:
                    total_timeout_s = float(os.getenv("BACKEND_PORT_CHECK_TIMEOUT_S", "15"))
                except Exception:
                    total_timeout_s = 15.0
                total_timeout_s = max(1.0, min(180.0, total_timeout_s))

                for svc in enabled:
                    if not getattr(svc, "port", None):
                        continue
                    port = int(svc.port)
                    if not self._wait_for_tcp_port_open(host, port, total_timeout_s=total_timeout_s):
                        diag = self._netstat_port_lines(port)
                        if diag:
                            logger.warning(
                                f"   [WARN] netstat for port {port} (trimmed):\n" + "\n".join(diag)
                            )
                        issues.append(
                            f"Backend service '{svc.name}' is not running (port {svc.port}). "
                            f"Start it before running contract tests."
                        )
            except Exception as exc:
                issues.append(f"Could not validate backend ports from services_matrix.yaml: {exc}")
        return issues

    def _stage_feature_files(self, state: TestAutomationState) -> List[Path]:
        resources_dir = (
            self.settings.paths.tests_dir
            / "src" / "test" / "resources" / "features"
        )
        resources_dir.mkdir(parents=True, exist_ok=True)
        for old in resources_dir.glob("*.feature"):
            old.unlink()
            logger.info(f"   🗑 Removed old feature: {old.name}")
        staged: List[Path] = []
        
        # Stage feature files from state.gherkin_files
        for src_path_str in (state.gherkin_files or []):
            src = Path(src_path_str)
            if src.exists():
                dest = resources_dir / src.name
                shutil.copy2(src, dest)
                staged.append(dest)
                logger.info(f"   [OK] Staged: {src.name} -> {dest}")
            else:
                logger.warning(f"   [WARN] Feature file not found: {src}")
        
        # Fallback: if the workflow did not provide feature paths in state, stage
        # whatever exists in the features directory.
        if not staged:
            features_dir = self.settings.paths.features_dir
            if features_dir.exists():
                for feature_file in sorted(features_dir.glob("*.feature")):
                    dest = resources_dir / feature_file.name
                    shutil.copy2(feature_file, dest)
                    staged.append(dest)
                    logger.info(f"   [OK] Staged (fallback): {feature_file.name} -> {dest}")
        
        logger.info(f"   {len(staged)} .feature file(s) staged in {resources_dir}")
        return staged

    def _build_mvn_command(self, service_name: str) -> str:
        """
        Build the Maven command as a SINGLE STRING (required for shell=True on Windows).
        Uses ServiceRegistry to get service configuration dynamically.
        Forces IPv4 (127.0.0.1) in all service URLs to avoid the Windows IPv6 issue
        where localhost resolves to ::1 at OS level but Java connects via IPv4.
        """
        from tools.service_registry import get_service_registry
        
        registry = get_service_registry()
        jwt_token = self._get_jwt_token()
        mvn = f'"{self._mvn_cmd}"' if " " in str(self._mvn_cmd) else str(self._mvn_cmd)

        def _maven_prop(name: str, value: object) -> str:
            raw = str(value)
            # Maven property values that contain spaces must be quoted as a single
            # token, otherwise cmd.exe/shell=True splits them and Maven sees a
            # stray lifecycle phase like "-".
            if any(ch.isspace() for ch in raw):
                raw = f'"{raw}"'
            return f"-D{name}={raw}"

        parts = [
            mvn,
            "clean",
            # Run the test phase only. Real backend coverage is collected separately
            # (via JaCoCo tcpserver dump) and converted into jacoco.xml under output/jacoco/report/.
            "test",
            _maven_prop("maven.repo.local", self.settings.paths.output_dir / ".m2" / "repository"),
            _maven_prop("service.name", service_name),
            _maven_prop("skipTests", "false"),
        ]

        if os.environ.get("ALLOW_TEST_FAILURES", "").strip().lower() in {"1", "true", "yes", "y"}:
            parts.append(_maven_prop("maven.test.failure.ignore", "true"))

        if jwt_token:
            parts.append(_maven_prop("TEST_JWT_TOKEN", jwt_token))

        # Build dynamic URLs for all enabled services
        enabled_services = registry.get_enabled_services()
        
        # Always force IPv4 to avoid Windows localhost resolution issues
        for service in enabled_services:
            base_url = _force_ipv4(service.get_base_url())
            env_var_name = f"{service.name.upper()}_BASE_URL"
            parts.append(_maven_prop(env_var_name, base_url))
            logger.debug(f"   Set {env_var_name}={base_url}")

        return " ".join(parts)

    def _clear_stale_test_artifacts(self, tests_dir: Path) -> None:
        stale_paths = [
            tests_dir / "target" / "surefire-reports",
            tests_dir / "target" / "cucumber-reports",
            tests_dir / "target" / "site" / "jacoco",
        ]
        for path in stale_paths:
            try:
                if path.exists():
                    shutil.rmtree(path, ignore_errors=True)
                    logger.info(f"   [OK] Cleared stale artifact directory: {path}")
            except Exception as exc:
                logger.warning(f"   [WARN] Could not clear stale artifact directory {path}: {exc}")

    def _tcp_port_open(self, host: str, port: int, timeout_s: float = 1.0) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout_s):
                return True
        except OSError:
            return False

    def _wait_for_tcp_port_open(
        self,
        host: str,
        port: int,
        total_timeout_s: float = 15.0,
        per_try_timeout_s: float = 1.0,
        sleep_s: float = 1.0,
    ) -> bool:
        deadline = time.time() + max(0.0, total_timeout_s)
        while time.time() < deadline:
            if self._tcp_port_open(host, port, timeout_s=per_try_timeout_s):
                return True
            time.sleep(max(0.1, sleep_s))
        return self._tcp_port_open(host, port, timeout_s=per_try_timeout_s)

    def _netstat_port_lines(self, port: int, max_lines: int = 10) -> List[str]:
        """Return a trimmed set of netstat lines for a given port (Windows-friendly)."""
        try:
            preferred_encoding = locale.getpreferredencoding(False) or "utf-8"
            proc = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                encoding=preferred_encoding,
                errors="replace",
                timeout=5,
                shell=False,
            )
            if proc.returncode != 0:
                return []
            needle = f":{port} "
            lines = [ln.rstrip() for ln in (proc.stdout or "").splitlines() if needle in ln]
            return lines[: max(1, max_lines)]
        except Exception:
            return []

    def _is_local_port_listening(self, port: int) -> bool:
        """Check if a local port is LISTENING without connecting to it."""
        lines = self._netstat_port_lines(port, max_lines=200)
        for ln in lines:
            up = ln.upper()
            # netstat state strings may be localized (e.g., French: "ECOUTE" / "ÉCOUTE")
            if "LISTEN" in up or "ECOUTE" in up or "ÉCOUTE" in up:
                return True
        return False

    def _extract_boot_inf_classes(self, jar_path: Path, out_dir: Path) -> int:
        """Extract BOOT-INF/classes/**.class from a Spring Boot fat JAR into out_dir."""
        if out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        with zipfile.ZipFile(jar_path, "r") as zf:
            for info in zf.infolist():
                name = info.filename
                if not name.startswith("BOOT-INF/classes/"):
                    continue
                if not name.endswith(".class"):
                    continue
                rel = name[len("BOOT-INF/classes/"):]
                dest = out_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, dest.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                count += 1
        return count

    def _prune_jacoco_excluded_classes(self, classes_dir: Path) -> int:
        """Remove low-signal classes so JaCoCo gates reflect business logic."""
        if not classes_dir.exists():
            return 0

        removed = 0
        for class_file in classes_dir.rglob("*.class"):
            rel_path = class_file.relative_to(classes_dir).as_posix()
            if not is_low_signal_jacoco_class(rel_path):
                continue
            try:
                class_file.unlink()
                removed += 1
            except OSError as exc:
                logger.warning(f"   [WARN] Could not exclude JaCoCo class {class_file}: {exc}")

        for path in sorted(classes_dir.rglob("*"), reverse=True):
            if not path.is_dir():
                continue
            try:
                path.rmdir()
            except OSError:
                pass

        return removed

    def _run_java(self, args: List[str], cwd: Optional[Path] = None, timeout_s: int = 120) -> subprocess.CompletedProcess:
        java = self._java_cmd or "java"
        cmd = [java] + args
        preferred_encoding = locale.getpreferredencoding(False) or "utf-8"
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding=preferred_encoding,
            errors="replace",
            timeout=timeout_s,
            shell=False,
        )

    def _discover_jacoco_ports(self) -> Dict[str, int]:
        """Scan running Java processes to find JaCoCo tcpserver ports.

        Parses command lines like:
          -javaagent:...jacocoagent.jar=output=tcpserver,port=64685,...
        Returns a dict mapping service name (auth/leave) to port number.
        """
        import re
        ports: Dict[str, int] = {}
        try:
            preferred_encoding = locale.getpreferredencoding(False) or "utf-8"
            # Use WMIC to get command lines of all java.exe processes
            result = subprocess.run(
                ["wmic", "process", "where", "name='java.exe'", "get", "ProcessId,CommandLine", "/format:csv"],
                capture_output=True,
                text=True,
                encoding=preferred_encoding,
                errors="replace",
                timeout=15,
                shell=False,
            )
            if result.returncode != 0:
                logger.warning(f"   [WARN] WMIC failed: {result.stderr[:200]}")
                return ports

            # Pattern to extract port from -javaagent:...jacocoagent.jar=...port=NNNN...
            # Example: -javaagent:D:\...\jacocoagent.jar=output=tcpserver,port=64685,address=127.0.0.1
            jacoco_re = re.compile(r"-javaagent:[^\s]*jacocoagent\.jar=[^\s]*?port=(\d+)")
            # Service detection patterns
            service_patterns = [
                (r"DemandeConge", "auth"),
                (r"conge[\W]", "leave"),
                (r"CongeeApplication", "leave"),
            ]

            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("Node,"):
                    continue
                # CSV format: Node,CommandLine,ProcessId
                parts = line.split(",")
                if len(parts) < 3:
                    continue
                cmdline = ",".join(parts[1:-1])  # CommandLine may contain commas
                pid = parts[-1].strip()

                port_match = jacoco_re.search(cmdline)
                if not port_match:
                    continue
                port = int(port_match.group(1))

                # Determine which service this is
                service_name = None
                for pattern, svc in service_patterns:
                    if re.search(pattern, cmdline, re.IGNORECASE):
                        service_name = svc
                        break

                if service_name and service_name not in ports:
                    ports[service_name] = port
                    logger.info(f"   [OK] Discovered JaCoCo tcpserver for {service_name} on port {port} (PID {pid})")
                elif service_name and service_name in ports:
                    logger.warning(f"   [WARN] Duplicate JaCoCo process for {service_name} on port {port} (PID {pid}); using first port {ports[service_name]}")

        except Exception as exc:
            logger.warning(f"   [WARN] Could not discover JaCoCo ports: {exc}")

        return ports

    def _collect_backend_jacoco_report(self) -> Optional[Path]:
        """Attempt to dump coverage from running services (tcpserver) and generate jacoco.xml.

        Requires services to be started with JaCoCo agent output=tcpserver.
        Produces: output/jacoco/report/jacoco.xml
        """
        project_root = Path(__file__).parent.parent
        cli_jar = project_root / "jacococli.jar"
        if not cli_jar.exists():
            logger.warning("   [WARN] jacococli.jar not found — cannot dump real backend coverage")
            return None

        # Discover actual JaCoCo ports from running Java processes
        discovered_ports = self._discover_jacoco_ports()
        
        # Fallback to env vars / defaults if discovery failed
        host = "127.0.0.1"
        env_auth = os.getenv("JACOCO_PORT_AUTH")
        env_leave = os.getenv("JACOCO_PORT_LEAVE")
        try:
            auth_port = int(env_auth) if env_auth else 36320
        except ValueError:
            auth_port = 36320
        try:
            leave_port = int(env_leave) if env_leave else 36321
        except ValueError:
            leave_port = 36321

        ports = {
            "auth": discovered_ports.get("auth", auth_port),
            "leave": discovered_ports.get("leave", leave_port),
        }

        # IMPORTANT: do NOT probe JaCoCo tcpserver ports with a raw TCP connect.
        # That can cause JaCoCo to log SocketExceptions and, in some setups,
        # destabilize coverage collection.
        if not all(self._is_local_port_listening(p) for p in ports.values()):
            diag_auth = self._netstat_port_lines(ports["auth"], max_lines=8)
            diag_leave = self._netstat_port_lines(ports["leave"], max_lines=8)
            if diag_auth:
                logger.warning(
                    "   [WARN] netstat for auth JaCoCo port (trimmed):\n" + "\n".join(diag_auth)
                )
            if diag_leave:
                logger.warning(
                    "   [WARN] netstat for leave JaCoCo port (trimmed):\n" + "\n".join(diag_leave)
                )
            logger.warning(
                "   [WARN] JaCoCo tcpserver ports are not open "
                f"(auth={ports['auth']}, leave={ports['leave']}). "
                "Start services with JaCoCo tcpserver (see run_with_coverage.ps1), then rerun."
            )
            return None

        output_dir = project_root / "output" / "jacoco"
        output_dir.mkdir(parents=True, exist_ok=True)
        report_dir = output_dir / "report"
        report_dir.mkdir(parents=True, exist_ok=True)

        auth_exec = output_dir / "auth.exec"
        leave_exec = output_dir / "leave.exec"

        # Dump and reset after dump to avoid stale accumulation.
        for name, port in ports.items():
            dest = auth_exec if name == "auth" else leave_exec
            proc = self._run_java(
                [
                    "-jar",
                    str(cli_jar),
                    "dump",
                    "--address",
                    host,
                    "--port",
                    str(port),
                    "--destfile",
                    str(dest),
                    "--reset",
                ],
                timeout_s=30,
            )
            if proc.returncode != 0:
                logger.warning(
                    f"   [WARN] JaCoCo dump failed for {name} (port {port}). "
                    f"stderr tail: {(proc.stderr or '')[-300:]}"
                )
                return None
            if not dest.exists() or dest.stat().st_size < 1024:
                logger.warning(f"   [WARN] JaCoCo dump produced empty exec for {name}: {dest}")
                return None

        # Locate service JARs (known default paths). If missing, abort.
        conge_jar = Path(r"C:\Bureau\Bureau\microservices\conge\target\congee-0.0.1-SNAPSHOT.jar")
        demande_jar = Path(r"C:\Bureau\Bureau\microservices\DemandeConge\target\DemandeConge-0.0.1-SNAPSHOT.jar")
        if not conge_jar.exists() or not demande_jar.exists():
            logger.warning(
                "   [WARN] Microservice fat JARs not found at expected paths; cannot generate jacoco.xml. "
                "Update paths in scripts or place jars under microservices/*/target/*.jar."
            )
            return None

        conge_classes = output_dir / "conge-classes"
        demande_classes = output_dir / "demande-classes"
        try:
            conge_count = self._extract_boot_inf_classes(conge_jar, conge_classes)
            demande_count = self._extract_boot_inf_classes(demande_jar, demande_classes)
            logger.info(f"   [OK] Extracted classes: conge={conge_count} demande={demande_count}")
        except Exception as exc:
            logger.warning(f"   [WARN] Could not extract classes from service jars: {exc}")
            return None

        conge_pruned = self._prune_jacoco_excluded_classes(conge_classes)
        demande_pruned = self._prune_jacoco_excluded_classes(demande_classes)
        logger.info(
            "   [OK] Applied JaCoCo exclusions before report generation: "
            f"conge_removed={conge_pruned} demande_removed={demande_pruned}"
        )

        jacoco_xml = report_dir / "jacoco.xml"
        jacoco_html = report_dir / "html"
        proc = self._run_java(
            [
                "-jar",
                str(cli_jar),
                "report",
                str(auth_exec),
                str(leave_exec),
                "--classfiles",
                str(conge_classes),
                "--classfiles",
                str(demande_classes),
                "--xml",
                str(jacoco_xml),
                "--html",
                str(jacoco_html),
            ],
            timeout_s=120,
        )
        if proc.returncode != 0 or not jacoco_xml.exists():
            logger.warning(
                "   [WARN] JaCoCo report generation failed. "
                f"stderr tail: {(proc.stderr or '')[-500:]}"
            )
            return None

        logger.info(f"   [OK] Real backend jacoco.xml generated: {jacoco_xml}")
        return jacoco_xml

    def _run_maven(self, tests_dir: Path, service_name: str) -> TestExecutionResult:
        result = TestExecutionResult()
        cmd    = self._build_mvn_command(service_name)
        logger.info(f"   Running: {_redact_secrets(cmd)}")
        logger.info(f"   Working directory: {tests_dir}")
        start = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(tests_dir),
                capture_output=True,
                text=False,
                timeout=300,
                shell=True,
                env={**os.environ, "TEST_JWT_TOKEN": self._get_jwt_token()},
            )
            preferred_encoding = locale.getpreferredencoding(False) or "utf-8"
            stdout_text = (proc.stdout or b"").decode(preferred_encoding, errors="replace")
            stderr_text = (proc.stderr or b"").decode(preferred_encoding, errors="replace")
            result.raw_output = stdout_text + stderr_text
            result.success    = proc.returncode == 0
            if result.raw_output:
                # Log full output for debugging
                logger.debug(f"   Maven output:\n{result.raw_output}")
        except subprocess.TimeoutExpired:
            result.raw_output = "[ERROR] Maven execution timed out after 300s."
            result.errors.append("Execution timeout exceeded.")
            result.success = False
        except FileNotFoundError as exc:
            result.raw_output = (
                f"[ERROR] Maven executable not found: {exc}\n"
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

    def _contains_backend_packages(self, jacoco_xml: Path) -> bool:
        """Check if a JaCoCo XML report contains backend service packages.

        The test harness's own report only covers test classes (com.example.e2e.*).
        Real backend reports contain service packages (tn.enis.*, com.enis.*).
        """
        try:
            text = jacoco_xml.read_text(encoding="utf-8")
            # Backend package signatures — adjust if your services use different roots
            backend_signatures = ("tn.enis.", "com.enis.", "tn/enis/", "com/enis/")
            return any(sig in text for sig in backend_signatures)
        except Exception:
            return False

    def _backup_jacoco_reports(self, tests_dir: Path) -> None:
        """
        Copy JaCoCo XML/CSV reports from target/site/jacoco/ to output/jacoco/report/
        so they survive Maven's next clean phase. Allows coverage_analyst to find them.

        CRITICAL: Only copy if the source actually contains backend service classes.
        The test harness's own jacoco.xml only covers test runners/steps and would
        overwrite real backend coverage with 0% metrics.
        """
        source_xml = tests_dir / "target" / "site" / "jacoco" / "jacoco.xml"
        source_csv = tests_dir / "target" / "site" / "jacoco" / "jacoco.csv"

        backup_dir = tests_dir.parent / "jacoco" / "report"  # output/jacoco/report/
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            if source_xml.exists():
                if not self._contains_backend_packages(source_xml):
                    logger.info(
                        "   [SKIP] Test-harness JaCoCo XML contains no backend packages; "
                        "not overwriting real backend coverage report."
                    )
                else:
                    dest_xml = backup_dir / "jacoco.xml"
                    if (not dest_xml.exists()) or (source_xml.stat().st_mtime > dest_xml.stat().st_mtime):
                        shutil.copy2(source_xml, dest_xml)
                        logger.info(f"   [OK] Backed up JaCoCo XML with backend coverage: {dest_xml}")
                    else:
                        logger.info("   [OK] Kept existing JaCoCo XML (newer already present)")
            if source_csv.exists():
                # CSV doesn't have package names inline, so only copy if XML was also valid
                dest_xml = backup_dir / "jacoco.xml"
                if dest_xml.exists() and self._contains_backend_packages(dest_xml):
                    dest_csv = backup_dir / "jacoco.csv"
                    if (not dest_csv.exists()) or (source_csv.stat().st_mtime > dest_csv.stat().st_mtime):
                        shutil.copy2(source_csv, dest_csv)
                        logger.info(f"   [OK] Backed up JaCoCo CSV: {dest_csv}")
                    else:
                        logger.info("   [OK] Kept existing JaCoCo CSV (newer already present)")
        except Exception as exc:
            logger.warning(f"   [WARN] Could not backup JaCoCo reports: {exc}")

    def _parse_surefire_summary(self, tests_dir: Path, result: TestExecutionResult) -> None:
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
        surefire_dir = tests_dir / "target" / "surefire-reports"
        if not surefire_dir.exists():
            logger.warning("   surefire-reports directory not found — Maven may not have run at all.")
            return
        for xml_file in surefire_dir.glob("*.xml"):
            try:
                content = xml_file.read_text(encoding="utf-8")
                m = re.search(
                    r'tests="(\d+)"[^>]*failures="(\d+)"[^>]*errors="(\d+)"[^>]*skipped="(\d+)"',
                    content,
                )
                if m:
                    result.total   += int(m.group(1))
                    result.failed  += int(m.group(2)) + int(m.group(3))
                    result.skipped += int(m.group(4))
            except Exception:
                pass
        result.passed = result.total - result.failed - result.skipped

    def _parse_cucumber_json(self, tests_dir: Path, result: TestExecutionResult) -> None:
        import json
        reports_root = tests_dir / "target" / "cucumber-reports"
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
                        failure_statuses = {"failed", "undefined", "pending", "ambiguous"}

                        hook_statuses: List[str] = []
                        hook_errors: List[str] = []
                        for hook_group in ("before", "after"):
                            for hook in scenario.get(hook_group, []) or []:
                                res = hook.get("result", {}) or {}
                                hook_statuses.append(res.get("status", "undefined"))
                                err = res.get("error_message") or hook.get("error_message")
                                if err:
                                    hook_errors.append(str(err))

                        step_statuses: List[str] = [
                            (step.get("result", {}) or {}).get("status", "undefined")
                            for step in scenario.get("steps", [])
                        ]
                        step_errors: List[str] = []
                        for step in scenario.get("steps", []):
                            err = (step.get("result", {}) or {}).get("error_message")
                            if err:
                                step_errors.append(str(err))

                        all_statuses = hook_statuses + step_statuses
                        if all_statuses and all(s == "passed" for s in all_statuses):
                            passed += 1
                        elif any(s in failure_statuses for s in all_statuses):
                            failed += 1
                            for err in hook_errors + step_errors:
                                result.errors.append(f"[{scenario.get('name', '?')}] {err[:200]}")
                        else:
                            skipped += 1
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

    def _locate_html_report(self, tests_dir: Path, result: TestExecutionResult) -> None:
        reports_root = tests_dir / "target" / "cucumber-reports"
        flat_html = reports_root / "cucumber.html"
        if flat_html.exists():
            result.report_path = flat_html
            logger.info(f"   HTML report: {flat_html}")
            return
        for sub_html in reports_root.glob("*/cucumber.html"):
            result.report_path = sub_html
            logger.info(f"   HTML report: {sub_html}")
            return

    def _analyze_failures(self, result: TestExecutionResult) -> List[str]:
        hints  = []
        output = result.raw_output
        if "Connection refused" in output or "ConnectException" in output:
            hints.append(
                "One or more services are unreachable. "
                "Ensure all microservices are running on ports 9000/9001."
            )
        if "401" in output or "Unauthorized" in output:
            hints.append("HTTP 401 detected. Verify TEST_JWT_TOKEN is valid and not expired.")
        if "403" in output or "Forbidden" in output:
            hints.append("HTTP 403 detected. The JWT token may lack the required role/permissions.")
        if "404" in output or "Not Found" in output:
            hints.append("HTTP 404 detected. An API endpoint may have changed — update your Swagger specs.")
        if "ClassNotFoundException" in output or "NoClassDefFoundError" in output:
            hints.append("Java class not found. Run `mvn compile` in the tests directory.")
        if "Undefined step" in output or "PendingException" in output:
            hints.append("Undefined Cucumber steps detected. Re-run the TestWriterAgent.")
        if "[WinError 2]" in output or "Le fichier spécifié est introuvable" in output:
            hints.append(
                "Maven executable not found (WinError 2). "
                "Add Maven's bin/ directory to your system PATH."
            )
        if "BUILD FAILURE" in output and not hints:
            hints.append("Maven BUILD FAILURE with no specific pattern detected. Check the raw Maven output.")
        return hints

    def execute(self, state: TestAutomationState) -> TestAutomationState:
        start_time = time.time()
        logger.info(f"[START] Test Executor starting for: {state.service_name}")

        blocking = self._preflight_checks(state)
        if blocking:
            for issue in blocking:
                logger.error(f"   [ERROR] Pre-flight: {issue}")
                state.add_error(f"Test execution pre-flight failed: {issue}")

            # Make the failure explicit for downstream agents (coverage analyst).
            # This prevents stale Surefire/JaCoCo artifacts from being interpreted as
            # "tests executed" during this run.
            state.execution_result = {
                "total":           0,
                "passed":          0,
                "failed":          0,
                "skipped":         0,
                "pass_rate":       0.0,
                "duration_ms":     0.0,
                "success":         False,
                "errors":          blocking,
                "report_path":     None,
                "hints":           [],
                "raw_output_tail": "",
                "source":          "preflight",
            }
            duration = (time.time() - start_time) * 1000
            state.add_agent_output(AgentOutput(
                agent_name="test_executor",
                status=AgentStatus.FAILED,
                duration_ms=duration,
                error_message="; ".join(blocking),
            ))
            return state

        tests_dir = self.settings.paths.tests_dir

        logger.info("1️⃣  Staging .feature files...")
        staged = self._stage_feature_files(state)
        if not staged:
            state.add_warning("No .feature files were staged — Cucumber will find no scenarios.")

        logger.info("2️⃣  Executing Maven contract tests...")
        self._clear_stale_test_artifacts(tests_dir)
        exec_result = self._run_maven(tests_dir, state.service_name)

        # Optional: collect *real backend* coverage via JaCoCo tcpserver and generate a fresh jacoco.xml.
        # If services are not started with JaCoCo tcpserver, this will safely no-op with warnings.
        try:
            self._collect_backend_jacoco_report()
        except Exception as exc:
            logger.warning(f"   [WARN] Real backend JaCoCo collection failed: {exc}")

        # Backup JaCoCo XML to safe location (outside target/ so mvn clean won't delete it)
        self._backup_jacoco_reports(tests_dir)

        logger.info("3️⃣  Parsing test reports...")
        self._parse_surefire_summary(tests_dir, exec_result)
        self._parse_cucumber_json(tests_dir, exec_result)
        self._locate_html_report(tests_dir, exec_result)

        # Decide pass/fail based on observed scenario results.
        # Maven can be configured to ignore test failures (returncode=0),
        # so we apply an explicit policy here.
        allow_failures = os.environ.get("ALLOW_TEST_FAILURES", "").strip().lower() in {
            "1", "true", "yes", "y"
        }

        # Threshold-based gating (defaults to strict).
        # - MIN_TEST_PASS_RATE: percent [0..100], default 100
        # - MAX_TEST_FAILED_SCENARIOS: integer >= 0, optional
        min_pass_rate_raw = os.environ.get("MIN_TEST_PASS_RATE", "").strip()
        try:
            min_pass_rate = float(min_pass_rate_raw) if min_pass_rate_raw else 100.0
        except Exception:
            min_pass_rate = 100.0

        max_failed_raw = os.environ.get("MAX_TEST_FAILED_SCENARIOS", "").strip()
        max_failed: Optional[int] = None
        if max_failed_raw:
            try:
                max_failed = int(max_failed_raw)
            except Exception:
                max_failed = None

        has_tests = exec_result.total > 0
        meets_pass_rate = has_tests and (exec_result.pass_rate >= min_pass_rate)
        meets_max_failed = (max_failed is None) or (exec_result.failed <= max_failed)
        tests_within_threshold = has_tests and meets_pass_rate and meets_max_failed

        overall_success = (
            (exec_result.success and tests_within_threshold)
            or (allow_failures and exec_result.success)
        )

        hints = self._analyze_failures(exec_result)
        for hint in hints:
            state.add_warning(f"Execution hint: {hint}")

        if overall_success and tests_within_threshold and exec_result.failed == 0:
            logger.success(
                f"✅ All tests PASSED  "
                f"({exec_result.passed}/{exec_result.total}  "
                f"pass_rate={exec_result.pass_rate}%)"
            )
        elif overall_success and tests_within_threshold and exec_result.failed > 0:
            logger.warning(
                f"[WARN]️  Tests have failures but meet threshold  "
                f"passed={exec_result.passed}  failed={exec_result.failed}  "
                f"skipped={exec_result.skipped}  pass_rate={exec_result.pass_rate}%  "
                f"(min_pass_rate={min_pass_rate}%, max_failed={max_failed})"
            )
        else:
            logger.warning(
                f"[WARN]️  Tests completed with failures  "
                f"passed={exec_result.passed}  failed={exec_result.failed}  "
                f"skipped={exec_result.skipped}  pass_rate={exec_result.pass_rate}%"
            )
            for err in exec_result.errors[:5]:
                logger.warning(f"   ↳ {err}")

            # If Maven itself failed/timed out, that is always a workflow failure unless explicitly allowed.
            if not exec_result.success and not allow_failures:
                state.add_error(
                    "Maven test execution failed (non-zero exit or timeout). "
                    "Fix the underlying failure or increase the timeout, then rerun."
                )

            if exec_result.total == 0:
                state.add_error("No tests were executed (0 scenarios).")
            elif not allow_failures and not tests_within_threshold:
                state.add_error(
                    "Test threshold not met: "
                    f"failed={exec_result.failed} total={exec_result.total} pass_rate={exec_result.pass_rate}%. "
                    f"min_pass_rate={min_pass_rate}%, max_failed={max_failed}."
                )

        state.execution_result = {
            "total":           exec_result.total,
            "passed":          exec_result.passed,
            "failed":          exec_result.failed,
            "skipped":         exec_result.skipped,
            "pass_rate":       exec_result.pass_rate,
            "duration_ms":     exec_result.duration_ms,
            "success":         overall_success,
            "errors":          exec_result.errors,
            "report_path":     str(exec_result.report_path) if exec_result.report_path else None,
            "hints":           hints,
            "raw_output_tail": exec_result.raw_output[-3000:],
        }

        duration = (time.time() - start_time) * 1000
        state.add_agent_output(AgentOutput(
            agent_name="test_executor",
            status=AgentStatus.SUCCESS if overall_success else AgentStatus.FAILED,
            duration_ms=duration,
            output_data={
                "total":                exec_result.total,
                "passed":               exec_result.passed,
                "failed":               exec_result.failed,
                "skipped":              exec_result.skipped,
                "pass_rate":            exec_result.pass_rate,
                "feature_files_staged": len(staged),
                "report_path":          str(exec_result.report_path) if exec_result.report_path else None,
                "allow_failures":        allow_failures,
                "min_test_pass_rate":    min_pass_rate,
                "max_test_failed":       max_failed,
                "meets_threshold":       tests_within_threshold,
            },
            error_message=(None if overall_success else ("; ".join(exec_result.errors[:3]) if exec_result.errors else None)),
        ))

        logger.success(f"✅ Test Executor finished in {duration:.0f}ms")
        return state


def test_executor_node(state: TestAutomationState) -> TestAutomationState:
    agent = TestExecutorAgent()
    return agent.execute(state)
