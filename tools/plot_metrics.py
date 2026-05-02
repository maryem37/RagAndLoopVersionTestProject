from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def load_metrics(metrics_dir: Path) -> List[Dict[str, Any]]:
    files = sorted(metrics_dir.glob("metrics_*.json"))
    rows = []
    for f in files:
        d = _read_json(f)
        d.setdefault("run_id", f.stem.replace("metrics_", ""))
        d["_file"] = str(f)
        rows.append(d)
    return rows


def plot_latest_bar(out_path: Path, latest: Dict[str, Any], keys: Sequence[str]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    values: List[Tuple[str, float]] = []
    for k in keys:
        v = _safe_float(latest.get(k))
        if v is None:
            continue
        values.append((k, v))

    if not values:
        raise RuntimeError("No numeric metrics available for latest-run plot")

    labels = [k for k, _ in values]
    data = [v for _, v in values]

    plt.figure(figsize=(10, 4))
    plt.bar(labels, data)
    plt.ylim(0, max(100.0, max(data) * 1.05))
    plt.ylabel("Value")
    plt.title(f"Metrics (latest run: {latest.get('run_id', '?')})")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=160)
    plt.close()


def plot_trend(out_path: Path, rows: List[Dict[str, Any]], keys: Sequence[str]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    run_ids = [str(r.get("run_id")) for r in rows]

    plt.figure(figsize=(10, 4))
    plotted_any = False

    for k in keys:
        ys: List[Optional[float]] = [_safe_float(r.get(k)) for r in rows]
        if all(v is None for v in ys):
            continue

        xs = list(range(len(rows)))
        # replace None with NaN for matplotlib
        ys2 = [float("nan") if v is None else float(v) for v in ys]
        plt.plot(xs, ys2, marker="o", label=k)
        plotted_any = True

    if not plotted_any:
        raise RuntimeError("No numeric metrics available for trend plot")

    plt.xticks(list(range(len(rows))), run_ids, rotation=45, ha="right")
    plt.ylabel("Value")
    plt.title("Metrics over runs")
    plt.legend(ncol=3, fontsize=9)
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=160)
    plt.close()


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Plot metrics diagrams from metrics_*.json")
    p.add_argument("--metrics-dir", type=Path, default=Path("output/eval_runs/metrics"))
    p.add_argument("--out-dir", type=Path, default=Path("output/eval_runs/plots"))
    p.add_argument(
        "--keys",
        type=str,
        default="SV,SC,TC,ESR,TPR,RSR,GT_seconds",
        help="Comma-separated metric keys to plot",
    )

    args = p.parse_args(argv)
    keys = [k.strip() for k in str(args.keys).split(",") if k.strip()]

    rows = load_metrics(args.metrics_dir)
    if not rows:
        raise SystemExit(f"No metrics_*.json found in: {args.metrics_dir}")

    latest = rows[-1]

    latest_png = args.out_dir / "metrics_latest.png"
    trend_png = args.out_dir / "metrics_over_time.png"

    plot_latest_bar(latest_png, latest, keys)
    plot_trend(trend_png, rows, keys)

    print(f"Wrote: {latest_png}")
    print(f"Wrote: {trend_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
