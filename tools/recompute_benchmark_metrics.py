from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Entry:
    label: str
    model_name: str
    run_id: str
    metrics_path: Path
    coverage_path: Path
    log_path: Path


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _ts_range_for_log(log_path: Path) -> Tuple[Optional[float], Optional[float]]:
    try:
        st = log_path.stat()
        # On Windows, st_ctime is creation time
        return float(st.st_ctime), float(st.st_mtime)
    except Exception:
        return None, None


def _in_range(path: Path, start_ts: Optional[float], end_ts: Optional[float], slack_s: float = 2.0) -> bool:
    if start_ts is None or end_ts is None:
        return True
    try:
        m = path.stat().st_mtime
        return (start_ts - slack_s) <= m <= (end_ts + slack_s)
    except Exception:
        return False


def _copy_recent_files(src_dir: Path, dst_dir: Path, pattern: str, start_ts: Optional[float], end_ts: Optional[float]) -> int:
    if not src_dir.exists():
        return 0
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for p in sorted(src_dir.glob(pattern)):
        if p.is_file() and _in_range(p, start_ts, end_ts):
            shutil.copy2(p, dst_dir / p.name)
            copied += 1
    return copied


def _copy_recent_tree(src_dir: Path, dst_dir: Path, start_ts: Optional[float], end_ts: Optional[float], patterns: Sequence[str]) -> int:
    if not src_dir.exists():
        return 0
    copied = 0
    for pat in patterns:
        copied += _copy_recent_files(src_dir, dst_dir, pat, start_ts, end_ts)
    return copied


def _copy_one_if_recent(src: Path, dst: Path, start_ts: Optional[float], end_ts: Optional[float]) -> bool:
    if not src.exists() or not src.is_file():
        return False
    if not _in_range(src, start_ts, end_ts):
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def load_entries(manifest_path: Path) -> List[Entry]:
    payload = _read_json(manifest_path)
    raw_entries = payload.get("entries", [])
    if not isinstance(raw_entries, list):
        raise ValueError("Manifest must contain an 'entries' list")

    entries: List[Entry] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        model_name = str(item.get("model_name", "")).strip()
        run_id = str(item.get("run_id", "")).strip() or label
        metrics_path = Path(str(item.get("metrics_path", "")).strip())
        coverage_path = Path(str(item.get("coverage_path", "")).strip())
        log_path = Path(str(item.get("log_path", "")).strip())
        if not label or not metrics_path or not coverage_path or not log_path:
            continue
        entries.append(
            Entry(
                label=label,
                model_name=model_name,
                run_id=run_id,
                metrics_path=metrics_path,
                coverage_path=coverage_path,
                log_path=log_path,
            )
        )
    return entries


def recompute_one(
    *,
    workspace_root: Path,
    entry: Entry,
    snapshot_dir: Path,
    req_yaml: Path,
) -> None:
    # If a global per-run metrics file already exists for this run_id, prefer it.
    # It was generated immediately after the run (before artifacts could be overwritten later).
    global_metrics = workspace_root / "output" / "eval_runs" / "metrics" / f"metrics_{entry.run_id}.json"
    if global_metrics.exists():
        entry.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(global_metrics, entry.metrics_path)
        return

    start_ts, end_ts = _ts_range_for_log(entry.log_path)

    # Snapshot likely artifacts for THIS run (to avoid stale cross-run contamination)
    features_dst = snapshot_dir / "features"
    test_features_dst = snapshot_dir / "test_features"
    surefire_dst = snapshot_dir / "surefire-reports"

    _copy_recent_files(workspace_root / "output" / "features", features_dst, "*.feature", start_ts, end_ts)
    _copy_recent_files(
        workspace_root / "output" / "tests" / "src" / "test" / "resources" / "features",
        test_features_dst,
        "*.feature",
        start_ts,
        end_ts,
    )

    _copy_recent_files(
        workspace_root / "output" / "tests" / "target" / "surefire-reports",
        surefire_dst,
        "TEST-*.xml",
        start_ts,
        end_ts,
    )

    cucumber_src = workspace_root / "output" / "tests" / "target" / "cucumber-reports" / "e2e" / "cucumber.json"
    cucumber_dst = snapshot_dir / "cucumber.json"
    _copy_one_if_recent(cucumber_src, cucumber_dst, start_ts, end_ts)

    maven_src = workspace_root / "output" / "tests" / "test_full_report.txt"
    maven_dst = snapshot_dir / "test_full_report.txt"
    _copy_one_if_recent(maven_src, maven_dst, start_ts, end_ts)

    # Run eval_metrics pointing at the snapshot, and overwrite the entry's metrics_path
    cmd: List[str] = [
        sys.executable,
        str((workspace_root / "tools" / "eval_metrics.py").resolve()),
        "--run-id",
        entry.run_id,
        "--out-file",
        str(entry.metrics_path),
        "--run-log",
        str(entry.log_path),
        "--req-yaml",
        str(req_yaml),
    ]

    # Feature dirs: always pass both snapshot dirs (even if empty)
    cmd += ["--features-dir", str(features_dst)]
    cmd += ["--features-dir", str(test_features_dst)]

    # Surefire/cucumber/maven log are redirected to snapshot equivalents
    cmd += ["--surefire-dir", str(surefire_dst)]
    cmd += ["--cucumber-json", str(cucumber_dst)]
    cmd += ["--maven-log", str(maven_dst)]

    completed = subprocess.run(
        cmd,
        cwd=str(workspace_root),
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"eval_metrics failed for {entry.label}: rc={completed.returncode}\n{completed.stdout}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Recompute benchmark metrics using per-run snapshots and regenerate plots")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--workspace-root", type=Path, default=Path("."))
    p.add_argument("--req-yaml", type=Path, default=Path("business_requirements.yaml"))
    p.add_argument("--out-dir", type=Path, default=Path("output/eval_runs/plots"))

    args = p.parse_args(argv)
    workspace_root = args.workspace_root.resolve()
    manifest_path = args.manifest.resolve()
    req_yaml = (workspace_root / args.req_yaml).resolve() if not args.req_yaml.is_absolute() else args.req_yaml

    entries = load_entries(manifest_path)
    if not entries:
        raise SystemExit("No entries found in manifest")

    # Snapshot into each run's folder next to artifacts
    for entry in entries:
        run_dir = entry.metrics_path.parent
        snapshot_dir = run_dir / "snapshot"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        print(f"Recomputing metrics for {entry.label} -> {entry.metrics_path}")
        recompute_one(
            workspace_root=workspace_root,
            entry=entry,
            snapshot_dir=snapshot_dir,
            req_yaml=req_yaml,
        )

    # Regenerate plots from the same manifest
    plot_cmd = [
        sys.executable,
        str((workspace_root / "tools" / "plot_llm_comparison.py").resolve()),
        "--manifest",
        str(manifest_path),
        "--out-dir",
        str((workspace_root / args.out_dir).resolve()),
    ]
    completed = subprocess.run(
        plot_cmd,
        cwd=str(workspace_root),
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    print(completed.stdout)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
