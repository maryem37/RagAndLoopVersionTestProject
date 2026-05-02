from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class BenchmarkEntry:
    label: str
    model_name: str
    metrics_path: Path
    coverage_path: Path


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _parse_inline_entry(raw: str) -> BenchmarkEntry:
    parts = [part.strip() for part in str(raw).split("|")]
    if len(parts) != 4:
        raise ValueError(
            "Each --entry must use: label|model_name|metrics_json_path|coverage_json_path"
        )

    label, model_name, metrics_raw, coverage_raw = parts
    return BenchmarkEntry(
        label=label,
        model_name=model_name,
        metrics_path=Path(metrics_raw),
        coverage_path=Path(coverage_raw),
    )


def _load_manifest_entries(manifest_path: Path) -> List[BenchmarkEntry]:
    payload = _read_json(manifest_path)
    raw_entries = payload.get("entries", [])
    if not isinstance(raw_entries, list):
        raise ValueError("Manifest must contain an 'entries' list")

    entries: List[BenchmarkEntry] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        model_name = str(item.get("model_name", "")).strip() or label
        metrics_path = Path(str(item.get("metrics_path", "")).strip())
        coverage_path = Path(str(item.get("coverage_path", "")).strip())
        if not label or not metrics_path or not coverage_path:
            continue
        entries.append(
            BenchmarkEntry(
                label=label,
                model_name=model_name,
                metrics_path=metrics_path,
                coverage_path=coverage_path,
            )
        )
    return entries


def load_entries(
    *,
    inline_entries: Sequence[str],
    manifest_path: Optional[Path],
) -> List[BenchmarkEntry]:
    entries: List[BenchmarkEntry] = []

    if manifest_path is not None:
        entries.extend(_load_manifest_entries(manifest_path))

    for raw in inline_entries:
        entries.append(_parse_inline_entry(raw))

    if not entries:
        raise ValueError("Provide at least one benchmark entry through --manifest or --entry")

    resolved: List[BenchmarkEntry] = []
    for entry in entries:
        metrics_path = entry.metrics_path.resolve()
        coverage_path = entry.coverage_path.resolve()
        if not metrics_path.exists():
            raise FileNotFoundError(f"Metrics file not found: {metrics_path}")
        if not coverage_path.exists():
            raise FileNotFoundError(f"Coverage file not found: {coverage_path}")
        resolved.append(
            BenchmarkEntry(
                label=entry.label,
                model_name=entry.model_name,
                metrics_path=metrics_path,
                coverage_path=coverage_path,
            )
        )
    return resolved


def _coverage_value(coverage_data: Dict[str, Any], bucket: str) -> Optional[float]:
    summary = coverage_data.get("summary", {})
    aggregate = summary.get("aggregate", {}) if isinstance(summary, dict) else {}
    metric = aggregate.get(bucket, {}) if isinstance(aggregate, dict) else {}
    if not isinstance(metric, dict):
        return None
    return _safe_float(metric.get("rate_%"))


def _metrics_value(metrics_data: Dict[str, Any], key: str) -> Optional[float]:
    return _safe_float(metrics_data.get(key))


def _is_no_tests_executed(*payloads: Dict[str, Any]) -> bool:
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        summary = payload.get("summary")
        if isinstance(summary, dict) and str(summary.get("data_source", "")).strip() == "no-tests-executed":
            return True
        details = payload.get("details")
        if isinstance(details, dict):
            workflow = details.get("workflow")
            if isinstance(workflow, dict) and workflow.get("no_tests_executed") is True:
                return True
    return False


def _annotate_bars(ax, bars, labels: Optional[List[str]] = None) -> None:
    for idx, bar in enumerate(bars):
        height = bar.get_height()
        if height is None:
            continue
        text = None
        if labels is not None and idx < len(labels):
            text = labels[idx]
        if text is None:
            text = f"{height:.1f}"
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            (height if height == height else 0.0) + 1.2,
            text,
            ha="center",
            va="bottom",
            fontsize=9,
        )


def plot_coverage_comparison(out_path: Path, entries: Sequence[BenchmarkEntry]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    coverage_payloads = [_read_json(entry.coverage_path) for entry in entries]
    labels = [entry.label for entry in entries]

    metric_defs = [
        ("instructions", "Stmts Coverage"),
        ("branches", "Branch Coverage"),
        ("methods", "Funcs Coverage"),
        ("lines", "Lines Coverage"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes = axes.flatten()
    colors = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]

    for idx, (bucket, title) in enumerate(metric_defs):
        ax = axes[idx]
        raw_values: List[Optional[float]] = []
        no_tests_flags: List[bool] = []
        for coverage_data in coverage_payloads:
            no_tests = _is_no_tests_executed(coverage_data)
            no_tests_flags.append(no_tests)
            raw_values.append(None if no_tests else _coverage_value(coverage_data, bucket))

        plotted_values = [value if value is not None else 0.0 for value in raw_values]
        bars = ax.bar(labels, plotted_values, color=colors[: len(labels)], edgecolor="#1f2937", linewidth=0.5)

        ann = ["n/a" if value is None else f"{value:.1f}" for value in raw_values]
        _annotate_bars(ax, bars, ann)

        for bar, is_na in zip(bars, [value is None for value in raw_values]):
            if is_na:
                bar.set_facecolor("#e5e7eb")
                bar.set_edgecolor("#6b7280")
                bar.set_hatch("//")
                bar.set_alpha(0.9)
        ax.set_title(title)
        ax.set_ylabel("Coverage (%)")
        ax.set_ylim(0, max(100.0, max(plotted_values) + 10.0 if plotted_values else 100.0))
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.tick_params(axis="x", rotation=25)

    fig.suptitle("Average Coverage Metrics by LLM", fontsize=16, y=0.98)
    if any(_is_no_tests_executed(payload) for payload in coverage_payloads):
        fig.text(
            0.5,
            0.01,
            "Note: hatched gray bars indicate N/A (no tests executed / no coverage).",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#374151",
        )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_eval_metrics_comparison(out_path: Path, entries: Sequence[BenchmarkEntry]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    metrics_payloads = [_read_json(entry.metrics_path) for entry in entries]
    labels = [entry.label for entry in entries]
    metric_keys = ["SV", "SC", "TC", "ESR", "TPR", "RSR"]

    x = np.arange(len(metric_keys))
    width = min(0.8 / max(len(entries), 1), 0.25)

    fig, ax = plt.subplots(figsize=(14, 6))
    colors = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]

    plotted_any = False
    for idx, entry in enumerate(entries):
        payload = metrics_payloads[idx]
        no_tests = _is_no_tests_executed(payload)
        values: List[Optional[float]] = []
        for key in metric_keys:
            value = _metrics_value(payload, key)
            if no_tests and key in {"TC", "ESR", "TPR", "RSR"}:
                value = None
            values.append(value)

        numeric_values = [value if value is not None else 0.0 for value in values]
        offset = (idx - (len(entries) - 1) / 2.0) * width
        bars = ax.bar(
            x + offset,
            numeric_values,
            width=width,
            label=entry.label,
            color=colors[idx % len(colors)],
            edgecolor="#1f2937",
            linewidth=0.5,
        )
        ann = ["n/a" if value is None else f"{value:.1f}" for value in values]
        _annotate_bars(ax, bars, ann)

        for bar, value in zip(bars, values):
            if value is None:
                bar.set_facecolor("#e5e7eb")
                bar.set_edgecolor("#6b7280")
                bar.set_hatch("//")
                bar.set_alpha(0.9)
        plotted_any = True

    if not plotted_any:
        raise RuntimeError("No evaluation metrics could be plotted")

    ax.set_xticks(x)
    ax.set_xticklabels(metric_keys)
    ax.set_ylabel("Score (%)")
    ax.set_ylim(0, 110)
    ax.set_title("Evaluation Metrics by LLM")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(title="LLM")

    if any(_is_no_tests_executed(payload) for payload in metrics_payloads):
        fig.text(
            0.5,
            0.01,
            "Note: hatched gray bars indicate N/A (no tests executed).",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#374151",
        )

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate LLM comparison graph images from benchmark artifacts"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional benchmark manifest JSON produced by tools/run_llm_benchmark.py",
    )
    parser.add_argument(
        "--entry",
        action="append",
        default=[],
        help="Inline entry: label|model_name|metrics_json_path|coverage_json_path",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("output/eval_runs/plots"),
    )
    parser.add_argument(
        "--coverage-out",
        type=str,
        default="llm_coverage_comparison.png",
    )
    parser.add_argument(
        "--eval-out",
        type=str,
        default="llm_eval_comparison.png",
    )

    args = parser.parse_args(argv)

    entries = load_entries(inline_entries=args.entry, manifest_path=args.manifest)
    coverage_out = args.out_dir / args.coverage_out
    eval_out = args.out_dir / args.eval_out

    plot_coverage_comparison(coverage_out, entries)
    plot_eval_metrics_comparison(eval_out, entries)

    print(f"Wrote: {coverage_out}")
    print(f"Wrote: {eval_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
