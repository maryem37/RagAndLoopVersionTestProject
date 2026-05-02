from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import yaml


@dataclass(frozen=True)
class ScenarioRef:
    name: str
    origin: str


@dataclass(frozen=True)
class ScenarioLoc:
    file: Path
    name: str
    start_line: int
    end_line: int


_GHERKIN_SCENARIO_RE = re.compile(r"^\s*Scenario(?:\s+Outline)?:\s*(.+?)\s*$")
_GHERKIN_FEATURE_RE = re.compile(r"^\s*Feature:\s*(.+?)\s*$")


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _path_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except Exception:
        return 0.0


def _path_birth_or_mtime(path: Path) -> float:
    try:
        stat = path.stat()
        birth = getattr(stat, "st_ctime", 0.0) or 0.0
        modified = getattr(stat, "st_mtime", 0.0) or 0.0
        return min(birth, modified) if birth and modified else max(birth, modified)
    except Exception:
        return 0.0


def _is_recent_for_run(path: Path, run_anchor_ts: Optional[float], slack_seconds: float = 2.0) -> bool:
    if run_anchor_ts is None:
        return True
    return _path_mtime(path) >= (run_anchor_ts - slack_seconds)


def _recent_existing_paths(paths: Sequence[Path], run_anchor_ts: Optional[float]) -> List[Path]:
    existing = [p for p in paths if p.exists()]
    if run_anchor_ts is None:
        return existing
    recent = [p for p in existing if _is_recent_for_run(p, run_anchor_ts)]
    return recent or existing


def parse_feature_file_scenarios(feature_path: Path) -> List[ScenarioLoc]:
    lines = _read_text(feature_path).splitlines()
    scenarios: List[ScenarioLoc] = []

    current_name: Optional[str] = None
    current_start: Optional[int] = None

    for i, line in enumerate(lines, start=1):
        m = _GHERKIN_SCENARIO_RE.match(line)
        if not m:
            continue

        if current_name is not None and current_start is not None:
            scenarios.append(
                ScenarioLoc(
                    file=feature_path,
                    name=current_name,
                    start_line=current_start,
                    end_line=i - 1,
                )
            )

        current_name = m.group(1).strip()
        current_start = i

    if current_name is not None and current_start is not None:
        scenarios.append(
            ScenarioLoc(
                file=feature_path,
                name=current_name,
                start_line=current_start,
                end_line=len(lines),
            )
        )

    return scenarios


def discover_feature_files(dirs: Sequence[Path]) -> List[Path]:
    out: List[Path] = []
    for d in dirs:
        if not d.exists():
            continue
        out.extend(sorted(d.glob("*.feature")))
    # de-dup by absolute path
    seen = set()
    uniq: List[Path] = []
    for p in out:
        ap = str(p.resolve())
        if ap in seen:
            continue
        seen.add(ap)
        uniq.append(p)
    return uniq


def filter_feature_files_for_run(feature_files: Sequence[Path], run_anchor_ts: Optional[float]) -> List[Path]:
    if run_anchor_ts is None:
        return list(feature_files)
    recent = [p for p in feature_files if _is_recent_for_run(p, run_anchor_ts)]
    return recent or list(feature_files)


def load_reference_scenarios(req_yaml: Path) -> List[ScenarioRef]:
    data = yaml.safe_load(_read_text(req_yaml)) or {}
    refs: List[ScenarioRef] = []

    services = data.get("SERVICES", []) or []
    for svc in services:
        svc_name = str(svc.get("SERVICE_NAME", ""))
        ts = svc.get("TEST_SCENARIOS", {}) or {}
        for bucket in ("HAPPY_PATH", "ERROR_CASES", "EDGE_CASES", "SECURITY_CASES"):
            for item in (ts.get(bucket) or []):
                refs.append(ScenarioRef(name=str(item), origin=f"{svc_name}:{bucket}"))

    for integ in (data.get("INTEGRATION_SCENARIOS", []) or []):
        if "SCENARIO" in integ:
            refs.append(ScenarioRef(name=str(integ["SCENARIO"]), origin="integration"))

    # de-dup by normalized name
    seen = set()
    out: List[ScenarioRef] = []
    for r in refs:
        key = r.name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def compute_scenario_coverage(
    reference: Sequence[ScenarioRef],
    generated_names: Sequence[str],
    threshold: float,
) -> Tuple[int, int, Dict[str, Any]]:
    covered = 0
    details: List[Dict[str, Any]] = []

    for r in reference:
        best_score = 0.0
        best_match: Optional[str] = None
        for g in generated_names:
            s = _ratio(r.name, g)
            if s > best_score:
                best_score = s
                best_match = g

        is_covered = best_score >= threshold
        if is_covered:
            covered += 1

        details.append(
            {
                "reference": r.name,
                "origin": r.origin,
                "covered": is_covered,
                "best_score": round(best_score, 4),
                "best_match": best_match,
            }
        )

    return covered, len(reference), {"threshold": threshold, "matches": details}


def _which(cmd: str) -> Optional[str]:
    from shutil import which

    return which(cmd)


def _run(cmd: List[str], cwd: Optional[Path] = None, timeout_s: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        shell=False,
    )


def _npx_gherkin_lint_cmd() -> Optional[List[str]]:
    local_cmd = Path("node_modules/.bin/gherkin-lint.cmd")
    if local_cmd.exists():
        return [str(local_cmd)]

    local = Path("node_modules/.bin/gherkin-lint")
    if local.exists():
        return [str(local)]

    if _which("npx"):
        return ["npx", "gherkin-lint"]

    if _which("gherkin-lint"):
        return ["gherkin-lint"]

    return None


def lint_feature_file(
    feature_path: Path,
    config_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    cmd = _npx_gherkin_lint_cmd()
    if not cmd:
        return []

    args = cmd[:]
    if config_path and config_path.exists():
        args.extend(["-c", str(config_path)])
    args.append(str(feature_path))

    try:
        cp = _run(args, timeout_s=60)
    except Exception as exc:
        return [{"file": str(feature_path), "line": None, "col": None, "message": str(exc)}]

    output = (cp.stdout or "") + (cp.stderr or "")
    issues: List[Dict[str, Any]] = []

    # gherkin-lint typically prints: <file>:<line>:<col>: <message>
    for line in output.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^(.*?):(\d+):(\d+):\s*(.+)$", line.strip())
        if m:
            f, ln, col, msg = m.groups()
            issues.append(
                {
                    "file": f,
                    "line": int(ln),
                    "col": int(col),
                    "message": msg.strip(),
                }
            )

    return issues


def map_lint_issues_to_scenarios(
    scenarios_by_file: Dict[Path, List[ScenarioLoc]],
    lint_issues: List[Dict[str, Any]],
) -> Dict[str, Any]:
    invalid_scenarios: List[Dict[str, Any]] = []

    # Build quick lookup for scenario by line
    for issue in lint_issues:
        try:
            raw_file = issue.get("file")
            if not raw_file:
                continue
            file_path = Path(raw_file)
            # gherkin-lint may output relative paths; try to resolve against cwd
            if not file_path.is_absolute():
                file_path = (Path.cwd() / file_path).resolve()

            scenarios = scenarios_by_file.get(file_path)
            if not scenarios:
                continue

            line_no = issue.get("line")
            if not isinstance(line_no, int):
                continue

            matched: Optional[ScenarioLoc] = None
            for s in scenarios:
                if s.start_line <= line_no <= s.end_line:
                    matched = s
                    break

            if matched is None:
                # fall back: closest scenario above
                above = [s for s in scenarios if s.start_line <= line_no]
                if above:
                    matched = max(above, key=lambda x: x.start_line)

            if matched is None:
                continue

            invalid_scenarios.append(
                {
                    "file": str(matched.file),
                    "scenario": matched.name,
                    "issue": issue,
                }
            )
        except Exception:
            continue

    invalid_keys = {(i["file"], i["scenario"]) for i in invalid_scenarios}
    return {
        "invalid_scenarios": invalid_scenarios,
        "invalid_count": len(invalid_keys),
    }


def parse_cucumber_json(cucumber_json: Path) -> Dict[str, Any]:
    data = json.loads(_read_text(cucumber_json))

    scenarios: List[Dict[str, Any]] = []

    for feat in data:
        elements = feat.get("elements", []) or []
        for el in elements:
            if el.get("type") != "scenario":
                continue

            steps = el.get("steps", []) or []
            statuses = [((s.get("result") or {}).get("status")) for s in steps]
            err_msgs = [
                (s.get("result") or {}).get("error_message", "")
                for s in steps
                if ((s.get("result") or {}).get("status") == "failed")
            ]

            if any(st == "failed" for st in statuses):
                status = "failed"
            elif any(st in ("undefined", "pending", "skipped") for st in statuses):
                status = "skipped"
            else:
                status = "passed"

            # Runtime/framework error heuristic:
            # - assertion failures count against TPR but are still "executed"
            # - other exceptions count as runtime errors (hurt ESR)
            runtime_error = False
            for msg in err_msgs:
                if "AssertionFailedError" in msg:
                    continue
                runtime_error = True

            scenarios.append(
                {
                    "name": el.get("name", ""),
                    "status": status,
                    "runtime_error": runtime_error,
                }
            )

    executed = [s for s in scenarios if s["status"] in ("passed", "failed")]
    passed = [s for s in executed if s["status"] == "passed"]
    runtime_failed = [s for s in executed if s["runtime_error"]]

    esr = ((len(executed) - len(runtime_failed)) / len(executed) * 100.0) if executed else 0.0
    tpr = (len(passed) / len(executed) * 100.0) if executed else 0.0

    return {
        "scenarios": scenarios,
        "counts": {
            "total": len(scenarios),
            "executed": len(executed),
            "passed": len(passed),
            "failed": sum(1 for s in executed if s["status"] == "failed"),
            "skipped": sum(1 for s in scenarios if s["status"] == "skipped"),
            "runtime_errors": len(runtime_failed),
        },
        "ESR": esr,
        "TPR": tpr,
    }


def parse_surefire_summary(surefire_dir: Path, run_anchor_ts: Optional[float] = None) -> Dict[str, Any]:
    from xml.etree import ElementTree as ET

    xmls_all = sorted(surefire_dir.glob("TEST-*.xml"))
    xmls = [x for x in xmls_all if _is_recent_for_run(x, run_anchor_ts)]
    if not xmls:
        return {"present": False, "files": 0, "recent_files": 0, "stale_files": len(xmls_all)}

    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    suites: List[Dict[str, Any]] = []

    for x in xmls:
        try:
            root = ET.fromstring(_read_text(x))
            tests = int(root.attrib.get("tests", "0") or 0)
            failures = int(root.attrib.get("failures", "0") or 0)
            errors = int(root.attrib.get("errors", "0") or 0)
            skipped = int(root.attrib.get("skipped", "0") or 0)
            suite_name = root.attrib.get("name")

            totals["tests"] += tests
            totals["failures"] += failures
            totals["errors"] += errors
            totals["skipped"] += skipped

            suites.append(
                {
                    "file": str(x),
                    "name": suite_name,
                    "tests": tests,
                    "failures": failures,
                    "errors": errors,
                    "skipped": skipped,
                }
            )
        except Exception:
            continue

    return {
        "present": True,
        "files": len(xmls),
        "recent_files": len(xmls),
        "stale_files": max(len(xmls_all) - len(xmls), 0),
        "totals": totals,
        "suites": suites,
    }


def parse_run_log_for_workflow(run_log: Path) -> Dict[str, Any]:
    if not run_log.exists():
        return {}

    text = _read_text(run_log)

    status = None
    m = re.search(r"Status\s*:\s*(\w+)", text, flags=re.IGNORECASE)
    if m:
        status = m.group(1).strip().lower()

    healing_tries = None
    m = re.search(r"^\s*Healing tries\s*:\s*(\d+)\s*$", text, flags=re.MULTILINE)
    if m:
        healing_tries = int(m.group(1))

    preflight_failed = "Test execution pre-flight failed" in text or "[ERROR] Pre-flight:" in text
    no_tests_executed = (
        "NO TESTS WERE EXECUTED" in text
        or "no-tests-executed" in text
        or "Tests total      : 0" in text
    )

    return {
        "workflow_status": status,
        "healing_tries": healing_tries,
        "preflight_failed": preflight_failed,
        "no_tests_executed": no_tests_executed,
    }


def compute_rsr_from_log(workflow_status: Optional[str], healing_tries: Optional[int]) -> Optional[float]:
    if healing_tries is None:
        return None
    if healing_tries <= 0:
        return None

    # Per-run RSR: if there were repairs attempted, consider it successful only when the workflow completes.
    if workflow_status == "completed":
        return 100.0
    return 0.0


def compute_tc_from_artifacts(
    surefire_summary: Dict[str, Any],
    maven_log: Optional[Path],
    workflow_info: Optional[Dict[str, Any]] = None,
) -> Optional[float]:
    # Practical per-run definition:
    # - 0 if Maven log includes compilation error
    # - 100 if Surefire XML exists
    # - None otherwise
    workflow_info = workflow_info or {}

    if workflow_info.get("preflight_failed") or workflow_info.get("no_tests_executed"):
        return 0.0

    if maven_log and maven_log.exists():
        t = _read_text(maven_log)
        if "COMPILATION ERROR" in t or "Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin" in t:
            return 0.0

    if surefire_summary.get("present"):
        return 100.0

    return None


def compute_sv(
    scenarios_by_file: Dict[Path, List[ScenarioLoc]],
    lint_details: Dict[str, Any],
    total_scenarios: int,
) -> Optional[float]:
    invalid = int(lint_details.get("invalid_count") or 0)
    if total_scenarios <= 0:
        return None

    # If gherkin-lint isn't available, we leave SV as None.
    issues = lint_details.get("lint_issues")
    if issues is None:
        return None

    valid = max(total_scenarios - invalid, 0)
    return valid / total_scenarios * 100.0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Compute evaluation metrics and write JSON artifacts")

    p.add_argument("--run-id", type=str, default=None, help="Run identifier (default: timestamp)")
    p.add_argument("--out-dir", type=Path, default=Path("output/eval_runs"))
    p.add_argument(
        "--out-file",
        type=Path,
        default=None,
        help="Optional explicit output JSON path. If set, overrides --out-dir/metrics/metrics_<run_id>.json",
    )

    p.add_argument(
        "--features-dir",
        type=Path,
        action="append",
        default=[],
        help="Directory containing generated .feature files (can be repeated)",
    )
    p.add_argument("--gherkin-lintrc", type=Path, default=Path(".gherkin-lintrc"))

    p.add_argument("--req-yaml", type=Path, default=Path("business_requirements.yaml"))
    p.add_argument("--sc-threshold", type=float, default=0.62)

    p.add_argument("--cucumber-json", type=Path, default=Path("output/tests/target/cucumber-reports/e2e/cucumber.json"))
    p.add_argument("--surefire-dir", type=Path, default=Path("output/tests/target/surefire-reports"))
    p.add_argument("--maven-log", type=Path, default=Path("output/tests/test_full_report.txt"))

    p.add_argument("--run-log", type=Path, default=None, help="Optional pipeline run log to derive RSR/healing tries")
    p.add_argument("--gt-seconds", type=float, default=None, help="Optional generation time (seconds) for this run")

    args = p.parse_args(argv)

    # If the user didn't provide any --features-dir, fall back to the repo defaults.
    if not args.features_dir:
        args.features_dir = [Path("output/features"), Path("output/tests/src/test/resources/features")]

    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_anchor_ts = _path_birth_or_mtime(args.run_log) if args.run_log else None

    out_root = Path(args.out_dir)
    metrics_dir = out_root / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    feature_files = filter_feature_files_for_run(
        discover_feature_files(args.features_dir),
        run_anchor_ts,
    )

    scenarios_by_file: Dict[Path, List[ScenarioLoc]] = {}
    all_scenarios: List[ScenarioLoc] = []
    for f in feature_files:
        scs = parse_feature_file_scenarios(f)
        scenarios_by_file[f.resolve()] = scs
        all_scenarios.extend(scs)

    generated_names = [s.name for s in all_scenarios]

    # --- SV (gherkin-lint)
    gherkin_lint_cmd = _npx_gherkin_lint_cmd()
    lint_issues: Optional[List[Dict[str, Any]]] = None
    lint_map: Dict[str, Any] = {"invalid_count": 0, "invalid_scenarios": [], "lint_issues": None}

    if gherkin_lint_cmd is not None:
        lint_issues = []
        for f in feature_files:
            lint_issues.extend(lint_feature_file(f, config_path=args.gherkin_lintrc))
        mapped = map_lint_issues_to_scenarios(scenarios_by_file, lint_issues)
        lint_map = {
            **mapped,
            "lint_issues": lint_issues,
            "used": True,
            "cmd": gherkin_lint_cmd,
        }
    else:
        lint_map = {"invalid_count": 0, "invalid_scenarios": [], "lint_issues": None, "used": False, "cmd": None}

    SV = compute_sv(scenarios_by_file, lint_map, total_scenarios=len(all_scenarios))

    # --- SC
    reference = load_reference_scenarios(args.req_yaml) if args.req_yaml.exists() else []
    covered, total_refs, sc_details = compute_scenario_coverage(reference, generated_names, args.sc_threshold)
    SC = (covered / total_refs * 100.0) if total_refs else None

    # --- RSR + healing tries (from run log)
    workflow_info = {}
    if args.run_log:
        workflow_info = parse_run_log_for_workflow(args.run_log)

    # --- Surefire / TC
    surefire_summary = parse_surefire_summary(args.surefire_dir, run_anchor_ts=run_anchor_ts)
    TC = compute_tc_from_artifacts(surefire_summary, args.maven_log, workflow_info=workflow_info)

    # --- Cucumber / ESR+TPR
    cucumber_summary: Optional[Dict[str, Any]] = None
    ESR = TPR = None
    cucumber_recent = args.cucumber_json.exists() and _is_recent_for_run(args.cucumber_json, run_anchor_ts)
    if workflow_info.get("preflight_failed") or workflow_info.get("no_tests_executed"):
        ESR = 0.0
        TPR = 0.0
    elif cucumber_recent:
        cucumber_summary = parse_cucumber_json(args.cucumber_json)
        ESR = float(cucumber_summary["ESR"])
        TPR = float(cucumber_summary["TPR"])

    RSR = compute_rsr_from_log(
        workflow_status=workflow_info.get("workflow_status"),
        healing_tries=workflow_info.get("healing_tries"),
    )

    metrics: Dict[str, Any] = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "features_dirs": [str(d) for d in args.features_dir],
            "req_yaml": str(args.req_yaml),
            "cucumber_json": str(args.cucumber_json),
            "surefire_dir": str(args.surefire_dir),
            "maven_log": str(args.maven_log),
            "run_log": str(args.run_log) if args.run_log else None,
            "run_anchor_ts": run_anchor_ts,
        },
        "counts": {
            "feature_files": len(feature_files),
            "generated_scenarios": len(all_scenarios),
            "reference_scenarios": total_refs,
        },
        "SV": SV,
        "SC": SC,
        "TC": TC,
        "ESR": ESR,
        "TPR": TPR,
        "RSR": RSR,
        "GT_seconds": args.gt_seconds,
        "details": {
            "sv": lint_map,
            "sc": {"covered": covered, "total": total_refs, **sc_details},
            "tc": {"surefire": surefire_summary},
            "execution": cucumber_summary,
            "workflow": workflow_info,
        },
    }

    if args.out_file:
        out_path = Path(args.out_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_path = metrics_dir / f"metrics_{run_id}.json"

    out_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote metrics: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
