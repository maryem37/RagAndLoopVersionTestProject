from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml
from aiohttp import web


ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "config" / "services_matrix.yaml"
USER_STORY_PATH = ROOT_DIR / "examples" / "comprehensive_user_story.md"
BUSINESS_REQUIREMENTS_PATH = ROOT_DIR / "business_requirements.yaml"
DIST_DIR = ROOT_DIR / "dist"
OUTPUT_DIR = ROOT_DIR / "output"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    return content if isinstance(content, dict) else {}


def _coverage_threshold_env_from_requirements() -> dict[str, str]:
    """Map business requirement coverage targets to subprocess env vars."""
    requirements = _read_yaml(BUSINESS_REQUIREMENTS_PATH)
    targets = requirements.get("COVERAGE_TARGETS", {}) if isinstance(requirements, dict) else {}
    if not isinstance(targets, dict):
        return {}

    mapping = {
        "LINE_COVERAGE": "MIN_LINE_COVERAGE",
        "BRANCH_COVERAGE": "MIN_BRANCH_COVERAGE",
        "METHOD_COVERAGE": "MIN_METHOD_COVERAGE",
    }

    env_updates: dict[str, str] = {}
    for source_key, env_key in mapping.items():
        raw = targets.get(source_key)
        if raw is None or str(raw).strip() == "":
            continue
        try:
            env_updates[env_key] = str(float(str(raw).strip()))
        except ValueError:
            continue
    return env_updates


def _service_to_ui(name: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "original_name": name,
        "name": name,
        "enabled": bool(config.get("enabled", True)),
        "port": int(config.get("port", 0) or 0),
        "base_url": config.get("base_url", ""),
        "swagger_spec": config.get("swagger_spec", ""),
        "swagger_url": config.get("swagger_url", ""),
        "role": config.get("role", ""),
        "dependencies": list(config.get("dependencies", []) or []),
        "db": dict(config.get("db", {}) or {}),
        "java_package": config.get("java_package", ""),
        "test_runner_class": config.get("test_runner_class", ""),
        "pom_location": config.get("pom_location", ""),
        "steps_class": config.get("steps_class", ""),
        "test_data": dict(config.get("test_data", {}) or {}),
    }


def _load_frontend_state() -> dict[str, Any]:
    matrix = _read_yaml(CONFIG_PATH)
    services_map = matrix.get("services", {})
    services = [
        _service_to_ui(name, cfg)
        for name, cfg in services_map.items()
        if isinstance(cfg, dict)
    ]

    global_config = dict(matrix.get("global", {}) or {})
    return {
        "services": services,
        "global": global_config,
        "user_story_text": _read_text(USER_STORY_PATH),
        "business_requirements_text": _read_text(BUSINESS_REQUIREMENTS_PATH),
    }


def _dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _merge_services(existing: dict[str, Any], incoming_services: list[dict[str, Any]]) -> dict[str, Any]:
    existing_services = dict(existing.get("services", {}) or {})
    merged_services: dict[str, Any] = {}

    for service in incoming_services:
        name = str(service.get("name", "")).strip()
        if not name:
            continue

        original_name = str(service.get("original_name", "")).strip() or name
        previous = dict(existing_services.get(original_name, existing_services.get(name, {})) or {})

        if "db" in service and isinstance(service["db"], dict):
            previous["db"] = service["db"]
        if "test_data" in service and isinstance(service["test_data"], dict):
            previous["test_data"] = service["test_data"]

        previous.update(
            {
                "enabled": bool(service.get("enabled", True)),
                "port": int(service.get("port", 0) or 0),
                "base_url": str(service.get("base_url", "")).strip(),
                "swagger_spec": str(service.get("swagger_spec", "")).strip(),
                "swagger_url": str(service.get("swagger_url", "")).strip(),
                "role": str(service.get("role", "")).strip(),
                "dependencies": [str(dep) for dep in service.get("dependencies", []) if str(dep).strip()],
            }
        )

        optional_keys = [
            "java_package",
            "test_runner_class",
            "pom_location",
            "steps_class",
        ]
        for key in optional_keys:
            if key in service and str(service.get(key, "")).strip():
                previous[key] = str(service[key]).strip()

        merged_services[name] = previous

    existing["services"] = merged_services
    return existing


def _save_frontend_state(payload: dict[str, Any]) -> dict[str, Any]:
    current = _read_yaml(CONFIG_PATH)
    services = payload.get("services", [])
    if isinstance(services, list):
        current = _merge_services(current, services)

    incoming_global = payload.get("global")
    if isinstance(incoming_global, dict):
        current_global = dict(current.get("global", {}) or {})
        current_global.update(incoming_global)
        if isinstance(incoming_global.get("jwt"), dict):
            jwt_cfg = dict(current_global.get("jwt", {}) or {})
            jwt_cfg.update(incoming_global["jwt"])
            current_global["jwt"] = jwt_cfg
            credentials = incoming_global["jwt"].get("credentials")
            if isinstance(credentials, dict):
                jwt_credentials = dict(jwt_cfg.get("credentials", {}) or {})
                jwt_credentials.update(credentials)
                jwt_cfg["credentials"] = jwt_credentials

        if isinstance(incoming_global.get("maven"), dict):
            maven_cfg = dict(current_global.get("maven", {}) or {})
            maven_cfg.update(incoming_global["maven"])
            current_global["maven"] = maven_cfg

        current["global"] = current_global

    _dump_yaml(CONFIG_PATH, current)

    if "user_story_text" in payload:
        USER_STORY_PATH.write_text(str(payload.get("user_story_text", "")), encoding="utf-8")
    if "business_requirements_text" in payload:
        BUSINESS_REQUIREMENTS_PATH.write_text(
            str(payload.get("business_requirements_text", "")),
            encoding="utf-8",
        )

    return _load_frontend_state()


def _safe_project_path(relative_path: str) -> Path:
    target = (ROOT_DIR / relative_path).resolve()
    if ROOT_DIR not in target.parents and target != ROOT_DIR:
        raise ValueError("Invalid path")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(relative_path)
    return target


def _latest_file(pattern: str) -> Path | None:
    matches = sorted(ROOT_DIR.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _artifact_entry(path: Path) -> dict[str, Any]:
    relative = path.relative_to(ROOT_DIR).as_posix()
    return {
        "path": relative,
        "url": f"/files/{relative}",
        "name": path.name,
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
        "size": path.stat().st_size,
    }


def _collect_latest_result() -> dict[str, Any]:
    summary: dict[str, Any] = {}
    artifacts: list[dict[str, Any]] = []
    report_path: str | None = None
    report_modified_at: str | None = None

    latest_report = _latest_file("output/reports/coverage_report_*.json")
    if latest_report:
        try:
            report_data = json.loads(latest_report.read_text(encoding="utf-8"))
            summary = report_data.get("summary", {})
            report_artifact = _artifact_entry(latest_report)
            report_path = report_artifact["path"]
            report_modified_at = report_artifact["modified_at"]
            artifacts.append(report_artifact)
        except Exception:
            summary = {}

    candidate_patterns = [
        "output/jacoco/report/html/index.html",
        "output/tests/target/cucumber-reports/e2e/cucumber.html",
        "output/tests/VERIFICATION_REPORT.md",
        "output/tests/TEST_GENERATION_SUMMARY.md",
    ]
    for pattern in candidate_patterns:
        path = ROOT_DIR / pattern
        if path.exists():
            artifacts.append(_artifact_entry(path))

    for feature in sorted((OUTPUT_DIR / "features").glob("*.feature"), key=lambda item: item.stat().st_mtime, reverse=True)[:5]:
        artifacts.append(_artifact_entry(feature))

    seen = set()
    unique_artifacts = []
    for artifact in artifacts:
        if artifact["path"] in seen:
            continue
        seen.add(artifact["path"])
        unique_artifacts.append(artifact)

    return {
        "summary": summary,
        "artifacts": unique_artifacts,
        "report_path": report_path,
        "report_modified_at": report_modified_at,
        "collected_at": _now_iso(),
    }


def _is_real_coverage_completion_marker(message: str) -> bool:
    msg = (message or "").strip()
    if msg == "Done.":
        return True
    if msg.startswith("XML:") or msg.startswith("HTML:") or msg.startswith("Open:"):
        return True
    if "End-to-end consolidated tests completed!" in msg:
        return True
    if "CONSOLIDATED E2E PIPELINE COMPLETED" in msg:
        return True
    if "WORKFLOW EXECUTION SUMMARY" in msg:
        return True
    if "Status: completed" in msg:
        return True
    return False


@dataclass
class PipelineRunState:
    status: str = "idle"
    started_at: str | None = None
    finished_at: str | None = None
    returncode: int | None = None
    logs: list[dict[str, str]] = field(default_factory=list)
    selected_services: list[str] = field(default_factory=list)
    run_mode: str = "real_coverage"
    result: dict[str, Any] | None = None
    task: asyncio.Task | None = None
    completion_marker_seen: bool = False
    last_output_at_monotonic: float = field(default_factory=time.monotonic, repr=False)

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "returncode": self.returncode,
            "selected_services": self.selected_services,
            "run_mode": self.run_mode,
            "logs": self.logs[-400:],
            "result": self.result or _collect_latest_result(),
            "is_running": self.status == "running",
        }


class PipelineRunner:
    def __init__(self) -> None:
        self.state = PipelineRunState(result=_collect_latest_result())
        self._lock = asyncio.Lock()

    async def start(
        self,
        selected_services: list[str] | None = None,
        run_mode: str = "real_coverage",
    ) -> dict[str, Any]:
        async with self._lock:
            self._reconcile_status()
            if self.state.status == "running":
                raise RuntimeError("A pipeline run is already in progress.")

            self.state = PipelineRunState(
                status="running",
                started_at=_now_iso(),
                selected_services=selected_services or [],
                run_mode=run_mode,
                result=self.state.result or _collect_latest_result(),
            )
            self.state.logs.append(
                {
                    "timestamp": _now_iso(),
                    "source": "system",
                    "message": f"Execution requested in '{run_mode}' mode.",
                }
            )
            self.state.task = asyncio.create_task(
                self._run_subprocess(selected_services or [], run_mode)
            )
            return self.state.snapshot()

    def _append_log(self, source: str, message: str) -> None:
        if message:
            self.state.last_output_at_monotonic = time.monotonic()
            if self.state.run_mode == "real_coverage" and _is_real_coverage_completion_marker(message):
                self.state.completion_marker_seen = True
        self.state.logs.append(
            {
                "timestamp": _now_iso(),
                "source": source,
                "message": message,
            }
        )

    def _finalize_state(self, returncode: int, status: str, message: str) -> None:
        self.state.returncode = returncode
        self.state.finished_at = _now_iso()
        self.state.result = _collect_latest_result()
        self.state.status = status
        self.state.task = None
        self._append_log("system", message)

    def _reconcile_status(self) -> None:
        if self.state.status != "running":
            return

        task = self.state.task
        if task and task.done():
            try:
                exc = task.exception()
            except asyncio.CancelledError:
                exc = None

            if exc is not None:
                self._finalize_state(
                    returncode=1,
                    status="failed",
                    message=f"Pipeline runner crashed: {exc}",
                )
                return

            self._finalize_state(
                returncode=self.state.returncode if self.state.returncode is not None else 0,
                status="completed" if (self.state.returncode in (None, 0)) else "failed",
                message="Pipeline task finished; status reconciled.",
            )

    async def _run_subprocess(self, selected_services: list[str], run_mode: str) -> None:
        process: asyncio.subprocess.Process | None = None
        stdout_task: asyncio.Task | None = None
        stderr_task: asyncio.Task | None = None
        guard_task: asyncio.Task | None = None

        try:
            if run_mode == "real_coverage":
                command = [
                    "powershell.exe",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ROOT_DIR / "run_real_coverage.ps1"),
                ]
                if selected_services:
                    self._append_log(
                        "system",
                        f"Passing TARGET_SERVICES={','.join(selected_services)} to run_real_coverage.ps1.",
                    )
            else:
                command = [sys.executable, "run_pipeline.py"]
                if selected_services:
                    command.extend(["--services", ",".join(selected_services)])

            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env.update(_coverage_threshold_env_from_requirements())
            if selected_services:
                env["TARGET_SERVICES"] = ",".join(selected_services)

            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(ROOT_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            async def read_stream(stream: asyncio.StreamReader | None, source: str) -> None:
                if stream is None:
                    return
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    message = line.decode("utf-8", errors="replace").rstrip()
                    self._append_log(source, message)

            stdout_task = asyncio.create_task(read_stream(process.stdout, "stdout"))
            stderr_task = asyncio.create_task(read_stream(process.stderr, "stderr"))

            async def completion_guard() -> None:
                while process is not None and process.returncode is None:
                    await asyncio.sleep(2)
                    if run_mode != "real_coverage":
                        continue
                    if not self.state.completion_marker_seen:
                        continue
                    if time.monotonic() - self.state.last_output_at_monotonic < 6:
                        continue

                    self._append_log(
                        "system",
                        "Completion marker detected; closing lingering PowerShell wrapper.",
                    )

                    try:
                        process.terminate()
                    except ProcessLookupError:
                        break

                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        self._append_log(
                            "system",
                            "PowerShell wrapper did not exit after terminate(); forcing kill.",
                        )
                        try:
                            process.kill()
                        except ProcessLookupError:
                            break
                    break

            guard_task = asyncio.create_task(completion_guard())

            returncode = await process.wait()
            reader_tasks = [task for task in (stdout_task, stderr_task) if task is not None]
            if reader_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*reader_tasks, return_exceptions=True),
                        timeout=2,
                    )
                except asyncio.TimeoutError:
                    self._append_log(
                        "system",
                        "Log streams stayed open after process exit; closing readers and finalizing run.",
                    )
                    for task in reader_tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*reader_tasks, return_exceptions=True)

            self._finalize_state(
                returncode=returncode,
                status="completed" if returncode == 0 else "failed",
                message=f"Pipeline finished with exit code {returncode}.",
            )
        except Exception as exc:
            self._finalize_state(
                returncode=1,
                status="failed",
                message=f"Pipeline execution failed unexpectedly: {exc}",
            )
            raise
        finally:
            if guard_task is not None:
                guard_task.cancel()
            for task in (stdout_task, stderr_task):
                if task is not None and not task.done():
                    task.cancel()

    def get_status(self) -> dict[str, Any]:
        self._reconcile_status()
        return self.state.snapshot()


RUNNER = PipelineRunner()


async def get_state(request: web.Request) -> web.Response:
    data = _load_frontend_state()
    data["run_status"] = RUNNER.get_status()
    data["latest_result"] = _collect_latest_result()
    return web.json_response(data)


async def save_state(request: web.Request) -> web.Response:
    payload = await request.json()
    saved = _save_frontend_state(payload)
    saved["run_status"] = RUNNER.get_status()
    saved["latest_result"] = _collect_latest_result()
    return web.json_response(saved)


async def run_pipeline(request: web.Request) -> web.Response:
    payload = await request.json()
    _save_frontend_state(payload)

    selected_services = payload.get("selected_services", [])
    selected_services = [str(item) for item in selected_services if str(item).strip()]
    run_mode = str(payload.get("run_mode", "real_coverage")).strip() or "real_coverage"
    try:
        state = await RUNNER.start(selected_services, run_mode=run_mode)
    except RuntimeError as exc:
        return web.json_response({"error": str(exc)}, status=409)

    return web.json_response(state)


async def run_status(request: web.Request) -> web.Response:
    status = RUNNER.get_status()
    status["latest_result"] = _collect_latest_result()
    return web.json_response(status)


async def serve_project_file(request: web.Request) -> web.StreamResponse:
    relative_path = unquote(request.match_info["path"])
    try:
        file_path = _safe_project_path(relative_path)
    except FileNotFoundError:
        raise web.HTTPNotFound(text="File not found")
    except ValueError:
        raise web.HTTPForbidden(text="Invalid path")
    return web.FileResponse(file_path)


async def index(request: web.Request) -> web.StreamResponse:
    index_path = DIST_DIR / "index.html"
    if not index_path.exists():
        raise web.HTTPNotFound(text="Frontend build not found. Run `npm.cmd run build` first.")
    return web.FileResponse(index_path)


def create_app() -> web.Application:
    app = web.Application(client_max_size=8 * 1024 * 1024)
    app.router.add_get("/api/state", get_state)
    app.router.add_post("/api/save", save_state)
    app.router.add_post("/api/run", run_pipeline)
    app.router.add_get("/api/run-status", run_status)
    app.router.add_get("/files/{path:.*}", serve_project_file)

    if DIST_DIR.exists():
        assets_dir = DIST_DIR / "assets"
        if assets_dir.exists():
            app.router.add_static("/assets/", assets_dir, show_index=False)

    app.router.add_get("/", index)
    app.router.add_get("/{tail:.*}", index)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8000)
