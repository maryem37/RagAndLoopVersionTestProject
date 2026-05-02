from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RunMetrics:
    label: str
    metrics_path: Path
    generated_scenarios: Optional[int]
    SV: Optional[float]
    SC: Optional[float]
    TC: Optional[float]
    ESR: Optional[float]
    TPR: Optional[float]


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _load_metrics(label: str, path: Path) -> RunMetrics:
    payload = _read_json(path)
    counts = payload.get("counts")
    if not isinstance(counts, dict):
        counts = {}

    return RunMetrics(
        label=label,
        metrics_path=path,
        generated_scenarios=_safe_int(counts.get("generated_scenarios")),
        SV=_safe_float(payload.get("SV")),
        SC=_safe_float(payload.get("SC")),
        TC=_safe_float(payload.get("TC")),
        ESR=_safe_float(payload.get("ESR")),
        TPR=_safe_float(payload.get("TPR")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Plot a simple comparison between a 'one-loop' run and a 'no-loop' run based on eval_metrics JSON outputs."
    )
    parser.add_argument("--one-loop", required=True, type=Path, help="Path to metrics JSON for the run WITH loop")
    parser.add_argument("--no-loop", required=True, type=Path, help="Path to metrics JSON for the run WITHOUT loop")
    parser.add_argument("--out", default=Path("output/plots/loop_vs_no_loop_comparison.png"), type=Path)
    parser.add_argument(
        "--title",
        default="Comparison: One Loop vs No Loop",
        help="Figure title",
    )
    parser.add_argument(
        "--one-loop-label",
        default="one loop",
        help="Label used in the plot for the one-loop run",
    )
    parser.add_argument(
        "--no-loop-label",
        default="no loop",
        help="Label used in the plot for the no-loop run",
    )
    args = parser.parse_args()

    one_loop_path = args.one_loop.resolve()
    no_loop_path = args.no_loop.resolve()
    out_path = args.out.resolve()

    if not one_loop_path.exists():
        raise FileNotFoundError(f"Metrics file not found: {one_loop_path}")
    if not no_loop_path.exists():
        raise FileNotFoundError(f"Metrics file not found: {no_loop_path}")

    one = _load_metrics(args.one_loop_label, one_loop_path)
    no = _load_metrics(args.no_loop_label, no_loop_path)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # --- Figure layout
    fig = plt.figure(figsize=(14, 6))
    gs = fig.add_gridspec(1, 2, width_ratios=[2.6, 1.4])

    ax_metrics = fig.add_subplot(gs[0, 0])
    ax_counts = fig.add_subplot(gs[0, 1])

    metric_defs = [
        ("SV", "Scenario Validity"),
        ("SC", "Scenario Coverage"),
        ("TC", "Test Compile"),
        ("ESR", "Exec Success Rate"),
        ("TPR", "Test Pass Rate"),
    ]

    labels = [no.label, one.label]
    colors = ["#64748b", "#2563eb"]

    # --- Metrics subplot (grouped bars)
    x = list(range(len(metric_defs)))
    width = 0.36

    def _val(run: RunMetrics, key: str) -> Optional[float]:
        return getattr(run, key)

    no_vals = [_val(no, k) for k, _ in metric_defs]
    one_vals = [_val(one, k) for k, _ in metric_defs]

    no_plot = [v if v is not None else 0.0 for v in no_vals]
    one_plot = [v if v is not None else 0.0 for v in one_vals]

    bars_no = ax_metrics.bar([i - width / 2 for i in x], no_plot, width=width, label=no.label, color=colors[0], edgecolor="#1f2937", linewidth=0.5)
    bars_one = ax_metrics.bar([i + width / 2 for i in x], one_plot, width=width, label=one.label, color=colors[1], edgecolor="#1f2937", linewidth=0.5)

    def _annotate(ax, bars, raw_values):
        for bar, raw in zip(bars, raw_values):
            h = bar.get_height()
            txt = "n/a" if raw is None else f"{raw:.1f}"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 1.2,
                txt,
                ha="center",
                va="bottom",
                fontsize=9,
            )
            if raw is None:
                bar.set_facecolor("#e5e7eb")
                bar.set_edgecolor("#6b7280")
                bar.set_hatch("//")
                bar.set_alpha(0.9)

    _annotate(ax_metrics, bars_no, no_vals)
    _annotate(ax_metrics, bars_one, one_vals)

    ax_metrics.set_xticks(x)
    ax_metrics.set_xticklabels([title for _, title in metric_defs], rotation=20, ha="right")
    ax_metrics.set_ylabel("Score (%)")
    ax_metrics.set_ylim(0, 110)
    ax_metrics.grid(axis="y", linestyle="--", alpha=0.35)
    ax_metrics.legend(loc="upper right")

    # --- Counts subplot
    count_labels = ["Generated scenarios"]
    count_x = [0]
    count_width = 0.45

    no_count = no.generated_scenarios
    one_count = one.generated_scenarios

    no_count_plot = float(no_count) if no_count is not None else 0.0
    one_count_plot = float(one_count) if one_count is not None else 0.0

    bars_noc = ax_counts.bar([count_x[0] - count_width / 2], [no_count_plot], width=count_width, color=colors[0], edgecolor="#1f2937", linewidth=0.5)
    bars_onec = ax_counts.bar([count_x[0] + count_width / 2], [one_count_plot], width=count_width, color=colors[1], edgecolor="#1f2937", linewidth=0.5)

    ax_counts.set_xticks(count_x)
    ax_counts.set_xticklabels(count_labels)
    ax_counts.set_ylabel("Count")
    ax_counts.grid(axis="y", linestyle="--", alpha=0.35)

    # annotate
    def _annot_count(ax, bar, raw):
        height = bar[0].get_height()
        txt = "n/a" if raw is None else str(raw)
        ax.text(bar[0].get_x() + bar[0].get_width() / 2, height + max(1.0, height * 0.02), txt, ha="center", va="bottom", fontsize=9)
        if raw is None:
            bar[0].set_facecolor("#e5e7eb")
            bar[0].set_edgecolor("#6b7280")
            bar[0].set_hatch("//")
            bar[0].set_alpha(0.9)

    _annot_count(ax_counts, bars_noc, no_count)
    _annot_count(ax_counts, bars_onec, one_count)

    fig.suptitle(args.title, fontsize=16)
    fig.text(0.5, 0.01, "Hatched gray bars = N/A (metric missing).", ha="center", va="bottom", fontsize=9, color="#374151")
    fig.tight_layout(rect=[0, 0.03, 1, 0.93])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote: {out_path}")
    print(f"One-loop metrics: {one_loop_path}")
    print(f"No-loop metrics:  {no_loop_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
