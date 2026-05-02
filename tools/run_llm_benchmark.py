from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence


@dataclass(frozen=True)
class ModelRun:
    label: str
    model_name: str


def _latest_file(root: Path, pattern: str) -> Optional[Path]:
    matches = sorted(root.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _parse_model_entry(raw: str) -> ModelRun:
    if "=" not in str(raw):
        raise ValueError("Each --model must use: label=model_name")
    label, model_name = str(raw).split("=", 1)
    label = label.strip()
    model_name = model_name.strip()
    if not label or not model_name:
        raise ValueError("Each --model must use non-empty label and model_name")
    return ModelRun(label=label, model_name=model_name)


def _run_command(
    command: List[str],
    *,
    cwd: Path,
    env: Dict[str, str],
    log_path: Path,
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            sys.stdout.write(line)
            log_file.write(line)
        return process.wait()


def _is_port_open(host: str, port: int, timeout_s: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _wait_for_ports_closed(ports: Sequence[int], *, timeout_s: int = 60, poll_s: float = 1.5) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        still_open = [port for port in ports if _is_port_open("127.0.0.1", int(port))]
        if not still_open:
            return True
        time.sleep(poll_s)
    return False


def _find_port_owner_pids(ports: Sequence[int]) -> List[int]:
    if not ports:
        return []
    port_args = ",".join(str(int(port)) for port in ports)
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f"Get-NetTCPConnection -LocalPort {port_args} -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty OwningProcess -Unique"
        ),
    ]
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    pids: List[int] = []
    for line in completed.stdout.splitlines():
        raw = line.strip()
        if raw.isdigit():
            pids.append(int(raw))
    return sorted(set(pids))


def _stop_port_owners(ports: Sequence[int]) -> None:
    pids = _find_port_owner_pids(ports)
    if not pids:
        return
    for pid in pids:
        print(f"Stopping lingering service PID {pid} on benchmark ports...")
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def _copy_artifact(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    return dst


def _in_time_window(path: Path, *, start_ts: float, end_ts: float, slack_s: float = 2.0) -> bool:
    try:
        mtime = path.stat().st_mtime
        return (start_ts - slack_s) <= mtime <= (end_ts + slack_s)
    except Exception:
        return False


def _copy_recent_files(src_dir: Path, dst_dir: Path, pattern: str, *, start_ts: float, end_ts: float) -> int:
    if not src_dir.exists():
        return 0
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for p in sorted(src_dir.glob(pattern)):
        if p.is_file() and _in_time_window(p, start_ts=start_ts, end_ts=end_ts):
            shutil.copy2(p, dst_dir / p.name)
            copied += 1
    return copied


def _extract_paths_from_log(log_path: Path, regex: str) -> List[Path]:
    if not log_path.exists():
        return []
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    import re

    out: List[Path] = []
    for m in re.finditer(regex, text, flags=re.MULTILINE):
        raw = (m.group(1) or "").strip().strip('"')
        if raw:
            out.append(Path(raw))
    return out


def _build_pipeline_command(services: Sequence[str]) -> List[str]:
    command = [sys.executable, "run_pipeline.py"]
    if services:
        command.extend(["--services", ",".join(services)])
    return command


def _build_real_coverage_command(workspace_root: Path) -> List[str]:
    return [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str((workspace_root / "run_real_coverage.ps1").resolve()),
    ]


def _build_eval_command(run_id: str, log_path: Path) -> List[str]:
    return [
        sys.executable,
        "tools/eval_metrics.py",
        "--run-id",
        run_id,
        "--run-log",
        str(log_path),
    ]


def _build_plot_command(manifest_path: Path, out_dir: Path) -> List[str]:
    return [
        sys.executable,
        "tools/plot_llm_comparison.py",
        "--manifest",
        str(manifest_path),
        "--out-dir",
        str(out_dir),
    ]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run up to 3 LLM benchmark passes and generate comparison graphs"
    )
    parser.add_argument(
        "--model",
        action="append",
        required=True,
        help="Model mapping in the form label=model_name",
    )
    parser.add_argument(
        "--services",
        type=str,
        default="",
        help="Optional comma-separated service list passed to run_pipeline.py",
    )
    parser.add_argument(
        "--runner",
        type=str,
        choices=["real_coverage", "pipeline"],
        default="real_coverage",
        help="Execution backend. Use real_coverage to start services + JaCoCo via run_real_coverage.ps1.",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("output/eval_runs/llm_benchmark"),
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=int,
        default=15,
        help="Seconds to wait between model runs to reduce Groq rate-limit and port reuse issues.",
    )

    args = parser.parse_args(argv)

    model_runs = [_parse_model_entry(raw) for raw in args.model]
    if len(model_runs) > 3:
        raise SystemExit("This helper is limited to 3 models, matching your requested comparison.")

    workspace_root = args.workspace_root.resolve()
    out_root = (workspace_root / args.out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    services = [item.strip() for item in args.services.split(",") if item.strip()]
    benchmark_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    benchmark_dir = out_root / benchmark_id
    benchmark_dir.mkdir(parents=True, exist_ok=True)

    entries: List[Dict[str, object]] = []

    for model_run in model_runs:
        run_start_ts = time.time()
        run_id = f"{benchmark_id}_{model_run.label}"
        run_dir = benchmark_dir / model_run.label
        artifacts_dir = run_dir / "artifacts"
        log_path = run_dir / "pipeline.log"

        env = os.environ.copy()
        env["LLM_MODEL_SCENARIO_DESIGNER"] = model_run.model_name
        env["LLM_MODEL_GHERKIN_GENERATOR"] = model_run.model_name
        env["LLM_MODEL_GHERKIN_VALIDATOR"] = model_run.model_name
        env["LLM_MODEL_TESTWRITER_AGENT"] = model_run.model_name
        env["PYTHONIOENCODING"] = "utf-8"
        env.setdefault("PYTHONUTF8", "1")
        # Benchmarks should compare model behavior, not spend time in optional RAG
        # enrichment or long retry loops that make runs look hung.
        env.setdefault("RAG_ENABLE", "0")
        env.setdefault("MAX_HEALING_ATTEMPTS", "0")
        env.setdefault("ENABLE_COVERAGE_IMPROVEMENT", "0")
        env.setdefault("MAX_COVERAGE_IMPROVEMENT_ATTEMPTS", "0")
        if services:
            env["TARGET_SERVICES"] = ",".join(services)

        print(f"\n=== Benchmarking {model_run.label} ({model_run.model_name}) ===")
        command = (
            _build_real_coverage_command(workspace_root)
            if args.runner == "real_coverage"
            else _build_pipeline_command(services)
        )
        pipeline_rc = _run_command(
            command,
            cwd=workspace_root,
            env=env,
            log_path=log_path,
        )
        run_end_ts = time.time()
        print(f"=== Completed {model_run.label} with pipeline exit code {pipeline_rc} ===")

        # Snapshot per-run artifacts into the benchmark folder to avoid stale cross-run contamination.
        snapshot_dir = artifacts_dir / "snapshot"
        features_dst = snapshot_dir / "features"
        test_features_dst = snapshot_dir / "test_features"
        surefire_dst = snapshot_dir / "surefire-reports"

        # Prefer the exact feature file paths printed by the pipeline, if present.
        saved_features = _extract_paths_from_log(log_path, r"Saved \\.feature ->\\s*(.+?\\.feature)\\s*$")
        if saved_features:
            for fp in saved_features:
                if fp.exists():
                    _copy_artifact(fp, features_dst)
        else:
            _copy_recent_files(
                workspace_root / "output" / "features",
                features_dst,
                "*.feature",
                start_ts=run_start_ts,
                end_ts=run_end_ts,
            )

        _copy_recent_files(
            workspace_root / "output" / "tests" / "src" / "test" / "resources" / "features",
            test_features_dst,
            "*.feature",
            start_ts=run_start_ts,
            end_ts=run_end_ts,
        )
        _copy_recent_files(
            workspace_root / "output" / "tests" / "target" / "surefire-reports",
            surefire_dst,
            "TEST-*.xml",
            start_ts=run_start_ts,
            end_ts=run_end_ts,
        )

        cucumber_src = workspace_root / "output" / "tests" / "target" / "cucumber-reports" / "e2e" / "cucumber.json"
        if cucumber_src.exists() and _in_time_window(cucumber_src, start_ts=run_start_ts, end_ts=run_end_ts):
            shutil.copy2(cucumber_src, snapshot_dir / "cucumber.json")

        maven_log_src = workspace_root / "output" / "tests" / "test_full_report.txt"
        if maven_log_src.exists() and _in_time_window(maven_log_src, start_ts=run_start_ts, end_ts=run_end_ts):
            shutil.copy2(maven_log_src, snapshot_dir / "test_full_report.txt")

        # Compute metrics from the snapshot and write directly into artifacts.
        metrics_out = artifacts_dir / f"metrics_{run_id}.json"
        eval_cmd = _build_eval_command(run_id, log_path)
        eval_cmd += ["--out-file", str(metrics_out)]
        eval_cmd += ["--req-yaml", str((workspace_root / "business_requirements.yaml").resolve())]
        eval_cmd += ["--features-dir", str(features_dst.resolve())]
        eval_cmd += ["--features-dir", str(test_features_dst.resolve())]
        eval_cmd += ["--surefire-dir", str(surefire_dst.resolve())]
        eval_cmd += ["--cucumber-json", str((snapshot_dir / "cucumber.json").resolve())]
        eval_cmd += ["--maven-log", str((snapshot_dir / "test_full_report.txt").resolve())]

        eval_rc = _run_command(
            eval_cmd,
            cwd=workspace_root,
            env=env,
            log_path=run_dir / "eval_metrics.log",
        )

        if not metrics_out.exists():
            raise FileNotFoundError(f"Expected metrics file was not created: {metrics_out}")

        coverage_path = _latest_file(workspace_root / "output" / "reports", "coverage_report_*.json")
        if coverage_path is None:
            raise FileNotFoundError("No coverage report JSON found under output/reports")

        copied_metrics = metrics_out
        copied_coverage = _copy_artifact(coverage_path, artifacts_dir)

        entries.append(
            {
                "label": model_run.label,
                "model_name": model_run.model_name,
                "run_id": run_id,
                "pipeline_returncode": pipeline_rc,
                "eval_returncode": eval_rc,
                "metrics_path": str(copied_metrics),
                "coverage_path": str(copied_coverage),
                "log_path": str(log_path),
            }
        )

        if args.runner == "real_coverage":
            _stop_port_owners([9000, 9001])

        ports_closed = _wait_for_ports_closed([9000, 9001], timeout_s=20, poll_s=1.0)
        if not ports_closed:
            print("WARNING: ports 9000/9001 are still open after the run; the next model may fail to start cleanly.")

        if model_run != model_runs[-1] and args.cooldown_seconds > 0:
            print(f"Cooling down for {args.cooldown_seconds}s before the next model...")
            time.sleep(args.cooldown_seconds)

    manifest_path = benchmark_dir / "benchmark_manifest.json"
    manifest_payload = {
        "benchmark_id": benchmark_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "entries": entries,
    }
    manifest_path.write_text(
        json.dumps(manifest_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    plots_dir = workspace_root / "output" / "eval_runs" / "plots"
    plot_rc = _run_command(
        _build_plot_command(manifest_path, plots_dir),
        cwd=workspace_root,
        env=os.environ.copy(),
        log_path=benchmark_dir / "plot.log",
    )

    print(f"\nBenchmark manifest: {manifest_path}")
    print(f"Plot command exit code: {plot_rc}")
    return 0 if plot_rc == 0 else plot_rc


if __name__ == "__main__":
    raise SystemExit(main())
