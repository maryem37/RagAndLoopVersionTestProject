from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ModelRun:
    label: str
    model_name: str


def _parse_model_entry(raw: str) -> ModelRun:
    if "=" not in str(raw):
        raise ValueError("Each --model must use: label=model_name")
    label, model_name = str(raw).split("=", 1)
    label = label.strip()
    model_name = model_name.strip()
    if not label or not model_name:
        raise ValueError("Each --model must use non-empty label and model_name")
    return ModelRun(label=label, model_name=model_name)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _count_gherkin_items(text: str) -> Dict[str, int]:
    scenarios = len(re.findall(r"^\s*Scenario(?: Outline)?:\s+", text, flags=re.MULTILINE))
    steps = len(re.findall(r"^\s*(Given|When|Then|And|But)\b", text, flags=re.MULTILINE))
    features = len(re.findall(r"^\s*Feature:\s+", text, flags=re.MULTILINE))
    return {"features": features, "scenarios": scenarios, "steps": steps}


def _find_gherkin_lint_cmd(workspace_root: Path) -> Optional[Path]:
    candidates = [
        workspace_root / "node_modules" / ".bin" / "gherkin-lint.cmd",
        workspace_root / "node_modules" / ".bin" / "gherkin-lint",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _run_gherkin_lint(workspace_root: Path, feature_path: Path) -> Tuple[Optional[int], str]:
    cmd = _find_gherkin_lint_cmd(workspace_root)
    if cmd is None:
        return None, "gherkin-lint not found"

    # gherkin-lint returns non-zero when issues found.
    # We parse "N error" patterns as an approximate count.
    completed = subprocess.run(
        [str(cmd), str(feature_path)],
        cwd=str(workspace_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    out = completed.stdout or ""

    # Common outputs include:
    #   "X errors" or individual lines. We fallback to counting lines with ": error".
    m = re.search(r"(?i)(\d+)\s+errors?", out)
    if m:
        return int(m.group(1)), out

    # Heuristic: count lint lines that look like findings.
    findings = [ln for ln in out.splitlines() if re.search(r"(?i)\berror\b", ln)]
    if not findings:
        findings = [
            ln for ln in out.splitlines()
            if re.match(r"^\s*\d+\s+", re.sub(r"\x1b\[[0-9;]*m", "", ln))
        ]
    if completed.returncode == 0:
        return 0, out
    if findings:
        return len(findings), out
    return None, out


def _build_default_user_story() -> str:
    # Keep this short and stable to reduce token count and make comparisons fair.
    return (
        "As an Employee, I want to submit a leave request and track its status.\n"
        "As a Manager, I want to approve or reject pending leave requests.\n"
        "As an Admin, I want authentication and authorization enforced.\n\n"
        "Acceptance Criteria:\n"
        "- Employee can create a leave request with future start/end dates\n"
        "- Request is created with status PENDING\n"
        "- Manager can approve a PENDING request\n"
        "- Unauthorized users receive 4xx\n"
    )


def _ensure_env_for_run(model_name: str) -> None:
    # Gherkin Generator uses settings.llm.gherkin_generator.model_name.
    os.environ["LLM_PROVIDER"] = os.environ.get("LLM_PROVIDER", "groq")
    os.environ["LLM_MODEL_GHERKIN_GENERATOR"] = model_name
    os.environ["GROQ_MODEL_GHERKIN_GENERATOR"] = model_name

    # Avoid timeouts causing apparent hangs.
    os.environ.setdefault("LLM_HTTP_TIMEOUT_S", "30")

    # Prevent RAG retrieval from adding variability/time.
    os.environ.setdefault("RAG_ENABLE", "0")


def _run_gherkin_generator(
    *,
    workspace_root: Path,
    model: ModelRun,
    user_story: str,
) -> Dict[str, Any]:
    _ensure_env_for_run(model.model_name)

    # Clear cached settings so model change is picked up per run.
    from config import settings as settings_mod
    from tools import chat_model_factory as chat_model_factory_mod

    try:
        settings_mod.get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass

    try:
        chat_model_factory_mod.reset_usage_tracker()
    except Exception:
        pass

    from agents.gherkin_generator import GherkinGeneratorAgent
    from graph.state import TestAutomationState

    swagger_auth = _read_json(workspace_root / "examples" / "sample_swagger1.json")
    swagger_leave = _read_json(workspace_root / "examples" / "sample_swagger2.json")

    state = TestAutomationState(
        workflow_id=f"agent_benchmark_{model.label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        service_name="auth_leave",
        user_story=user_story,
        swagger_specs={"auth": swagger_auth, "leave": swagger_leave},
    )

    started = time.monotonic()
    ok = True
    err = ""
    try:
        agent = GherkinGeneratorAgent()
        state = agent.generate(state)
    except Exception as exc:
        ok = False
        err = f"{type(exc).__name__}: {exc}"
    duration_s = time.monotonic() - started

    gherkin_text = getattr(state, "gherkin_content", "") or ""
    counts = _count_gherkin_items(gherkin_text)

    feature_paths = getattr(state, "gherkin_files", None) or []
    feature_path = Path(feature_paths[0]) if feature_paths else None

    lint_issues = None
    lint_out = ""
    if feature_path and feature_path.exists():
        lint_issues, lint_out = _run_gherkin_lint(workspace_root, feature_path)

    try:
        llm_usage = chat_model_factory_mod.get_usage_tracker_snapshot()
    except Exception:
        llm_usage = {}

    return {
        "ok": ok,
        "error": err,
        "model": {"label": model.label, "name": model.model_name},
        "duration_ms": int(duration_s * 1000),
        "llm_usage": llm_usage,
        "gherkin": {
            "chars": len(gherkin_text),
            **counts,
            "feature_file": str(feature_path) if feature_path else "",
        },
        "gherkin_lint": {
            "issues": lint_issues,
            "output": lint_out[-4000:],
        },
    }


def _plot_results(out_path: Path, results: Sequence[Dict[str, Any]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [str(r.get("model", {}).get("label", "")) for r in results]

    duration = [_safe_int(r.get("duration_ms")) for r in results]
    scenarios = [_safe_int(r.get("gherkin", {}).get("scenarios")) for r in results]
    steps = [_safe_int(r.get("gherkin", {}).get("steps")) for r in results]
    lint = [_safe_int(r.get("gherkin_lint", {}).get("issues")) for r in results]

    def _values_or_zero(values: List[Optional[int]]) -> List[int]:
        return [int(v) if v is not None else 0 for v in values]

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes = axes.flatten()

    charts = [
        ("Duration (ms)", duration),
        ("Scenarios", scenarios),
        ("Steps", steps),
        ("gherkin-lint issues (lower is better)", lint),
    ]

    colors = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]

    for ax, (title, raw) in zip(axes, charts):
        plotted = _values_or_zero(raw)
        bars = ax.bar(labels, plotted, color=colors[: len(labels)], edgecolor="#1f2937", linewidth=0.5)

        for idx, (bar, val) in enumerate(zip(bars, raw)):
            is_na = val is None
            if is_na:
                bar.set_facecolor("#e5e7eb")
                bar.set_edgecolor("#6b7280")
                bar.set_hatch("//")
                text = "n/a"
            else:
                text = str(val)
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                (bar.get_height() if bar.get_height() == bar.get_height() else 0.0) + max(1.0, 0.03 * (max(plotted) if plotted else 1)),
                text,
                ha="center",
                va="bottom",
                fontsize=9,
            )

        ax.set_title(title)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.tick_params(axis="x", rotation=20)

    fig.suptitle("Gherkin Generator Agent — 3-Model Comparison", fontsize=16, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark a single agent against up to 3 Groq models and generate a comparison graph"
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="gherkin_generator",
        choices=["gherkin_generator"],
        help="Which agent to benchmark (currently: gherkin_generator)",
    )
    parser.add_argument(
        "--model",
        action="append",
        required=True,
        help="Model mapping in the form label=model_name",
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=int,
        default=10,
        help="Seconds to wait between model runs (helps avoid Groq rate limits)",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("output/eval_runs/agent_benchmark"),
    )
    parser.add_argument(
        "--user-story",
        type=Path,
        default=None,
        help="Optional path to a user story markdown/text file. If omitted, uses a small built-in story.",
    )

    args = parser.parse_args(argv)

    models = [_parse_model_entry(m) for m in args.model]
    if len(models) > 3:
        raise SystemExit("This helper is limited to 3 models.")

    workspace_root = args.workspace_root.resolve()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = (workspace_root / args.out_root / run_id).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    if args.user_story is not None:
        user_story = Path(args.user_story).read_text(encoding="utf-8", errors="replace")
    else:
        user_story = _build_default_user_story()

    results: List[Dict[str, Any]] = []
    for idx, model in enumerate(models, start=1):
        print(f"\n=== [{idx}/{len(models)}] Agent={args.agent} Model={model.label} ({model.model_name}) ===")
        r = _run_gherkin_generator(workspace_root=workspace_root, model=model, user_story=user_story)
        results.append(r)

        model_dir = out_root / model.label
        model_dir.mkdir(parents=True, exist_ok=True)
        _write_json(model_dir / "agent_metrics.json", r)

        # Copy the generated feature file (best-effort)
        feature_file = str(r.get("gherkin", {}).get("feature_file", "") or "").strip()
        if feature_file:
            src = Path(feature_file)
            if src.exists():
                dst = model_dir / src.name
                dst.write_text(src.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

        if idx < len(models):
            time.sleep(max(0, int(args.cooldown_seconds)))

    manifest = {
        "run_id": run_id,
        "agent": args.agent,
        "provider": os.getenv("LLM_PROVIDER", ""),
        "models": [{"label": m.label, "model_name": m.model_name} for m in models],
        "results": results,
    }
    _write_json(out_root / "benchmark_manifest.json", manifest)

    plot_path = (workspace_root / "output" / "plots" / f"agent_{args.agent}_comparison.png").resolve()
    _plot_results(plot_path, results)

    print("\nSaved:")
    print(f"  Manifest: {out_root / 'benchmark_manifest.json'}")
    print(f"  Plot    : {plot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
