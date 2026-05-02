from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PIL import Image, ImageDraw, ImageFont


AGENT_ORDER = [
    "scenario_designer",
    "gherkin_generator",
    "gherkin_validator",
    "test_writer",
    "test_executor",
    "failure_analyst",
    "coverage_analyst",
]


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(float(value))
    except Exception:
        return None


def _short_label(value: str) -> str:
    aliases = {
        "scenario_designer": "scenario",
        "gherkin_generator": "gherkin_gen",
        "gherkin_validator": "validator",
        "test_writer": "writer",
        "test_executor": "executor",
        "failure_analyst": "failure",
        "coverage_analyst": "coverage",
    }
    return aliases.get(value, value)


def parse_agent_summary(log_path: Path) -> List[Dict[str, Any]]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    rows: List[Dict[str, Any]] = []

    summary_start = text.rfind("[LIST] Agent Execution:")
    if summary_start >= 0:
        summary_text = text[summary_start:]
        for status, agent, duration in re.findall(
            r"\[(OK|FAIL|SKIP|SKIPPED)\]\s+([a-z_]+)\s+\[(\d+(?:\.\d+)?)ms\]",
            summary_text,
        ):
            rows.append(
                {
                    "agent": agent,
                    "status": "success" if status == "OK" else status.lower(),
                    "duration_ms": _safe_int(duration),
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                }
            )

    if rows:
        return _ordered_rows(rows)

    # Fallback for logs that do not include the workflow summary.
    patterns = [
        ("scenario_designer", r"Scenario Designer produced .*? in (\d+)ms"),
        ("gherkin_generator", r"Gherkin.*?(?:Generated|generated).*?\((\d+)ms\)|Gherkin generated.*? in (\d+(?:\.\d+)?) ms"),
        ("test_writer", r"TestWriter finished in (\d+(?:\.\d+)?) ms"),
        ("test_executor", r"Test Executor finished in (\d+(?:\.\d+)?)ms"),
        ("failure_analyst", r"Failure Analyst finished in (\d+(?:\.\d+)?)ms"),
        ("coverage_analyst", r"Coverage Analyst finished in (\d+(?:\.\d+)?) ms"),
    ]
    for agent, pattern in patterns:
        found = re.findall(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not found:
            continue
        raw = found[-1]
        if isinstance(raw, tuple):
            raw = next((x for x in raw if x), None)
        rows.append(
            {
                "agent": agent,
                "status": "success",
                "duration_ms": _safe_int(raw),
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
            }
        )
    return _ordered_rows(rows)


def parse_execution_metrics(log_path: Path) -> Dict[str, Optional[int]]:
    text = log_path.read_text(encoding="utf-8", errors="replace")

    metrics: Dict[str, Optional[int]] = {
        "total": None,
        "passed": None,
        "failed": None,
        "skipped": None,
    }

    coverage_block_matches = re.findall(
        r"Tests total\s+:\s+(\d+).*?"
        r"Tests passed\s+:\s+(\d+).*?"
        r"Tests failed\s+:\s+(\d+).*?"
        r"Tests skipped\s+:\s+(\d+)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if coverage_block_matches:
        total, passed, failed, skipped = coverage_block_matches[-1]
        return {
            "total": _safe_int(total),
            "passed": _safe_int(passed),
            "failed": _safe_int(failed),
            "skipped": _safe_int(skipped),
        }

    inline_matches = re.findall(
        r"passed=(\d+)\s+failed=(\d+)\s+skipped=(\d+)",
        text,
        flags=re.IGNORECASE,
    )
    if inline_matches:
        passed, failed, skipped = inline_matches[-1]
        passed_i = _safe_int(passed) or 0
        failed_i = _safe_int(failed) or 0
        skipped_i = _safe_int(skipped) or 0
        return {
            "total": passed_i + failed_i + skipped_i,
            "passed": passed_i,
            "failed": failed_i,
            "skipped": skipped_i,
        }

    return metrics


def _ordered_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    order = {name: idx for idx, name in enumerate(AGENT_ORDER)}
    return sorted(rows, key=lambda r: order.get(str(r.get("agent", "")), len(order)))


def _draw_text_centered(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    x_center: int,
    y: int,
    value: str,
    fill: str = "#111827",
) -> None:
    bbox = draw.textbbox((0, 0), value, font=font)
    draw.text((x_center - (bbox[2] - bbox[0]) // 2, y), value, fill=fill, font=font)


def _render_chart(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    labels: List[str],
    title: str,
    values: List[Optional[int]],
    box: tuple[int, int, int, int],
    colors: List[str],
) -> None:
    x0, y0, x1, y1 = box
    left = x0 + 58
    right = x1 - 20
    top = y0 + 35
    bottom = y1 - 62

    draw.rectangle([x0, y0, x1, y1], outline="#dbe4f0", width=1)
    draw.text((x0 + 10, y0 + 8), title, fill="#111827", font=font)

    numeric = [v for v in values if v is not None]
    max_value = max(numeric or [1])
    max_value = max(1, max_value)

    for tick_idx in range(5):
        frac = tick_idx / 4
        y = bottom - int((bottom - top) * frac)
        draw.line([left, y, right, y], fill="#d1d5db", width=1)
        tick_value = int(max_value * frac)
        draw.text((x0 + 8, y - 6), str(tick_value), fill="#374151", font=font)

    draw.line([left, top, left, bottom], fill="#374151", width=2)
    draw.line([left, bottom, right, bottom], fill="#374151", width=2)

    slot = (right - left) / max(len(labels), 1)
    bar_w = max(18, int(slot * 0.45))

    for idx, label in enumerate(labels):
        value = values[idx] if idx < len(values) else None
        center_x = int(left + slot * (idx + 0.5))
        bar_left = center_x - (bar_w // 2)
        bar_right = center_x + (bar_w // 2)

        if value is None:
            bar_top = bottom - 4
            fill = "#e5e7eb"
            annotation = "n/a"
        else:
            bar_height = int((bottom - top) * (value / max_value))
            bar_top = bottom - bar_height
            fill = colors[idx % len(colors)]
            annotation = str(value)

        draw.rectangle([bar_left, bar_top, bar_right, bottom], fill=fill, outline="#1f2937", width=1)
        if value is None:
            for hatch_y in range(bar_top, bottom, 8):
                draw.line([bar_left, hatch_y, bar_right, min(bottom, hatch_y + 8)], fill="#9ca3af", width=1)

        _draw_text_centered(draw, font, center_x, max(top + 4, bar_top - 14), annotation)
        _draw_text_centered(draw, font, center_x, bottom + 10, label, fill="#374151")


def _has_any_value(values: List[Optional[int]]) -> bool:
    return any(value is not None for value in values)


def render_pipeline_usage(log_path: Path, out_path: Path, title: Optional[str] = None) -> None:
    rows = parse_agent_summary(log_path)
    if not rows:
        raise ValueError(f"No agent execution summary found in {log_path}")

    labels = [_short_label(str(row["agent"])) for row in rows]
    runtime_values = [_safe_int(row.get("duration_ms")) for row in rows]
    prompt_values = [_safe_int(row.get("prompt_tokens")) for row in rows]
    completion_values = [_safe_int(row.get("completion_tokens")) for row in rows]
    total_token_values = [_safe_int(row.get("total_tokens")) for row in rows]

    if _has_any_value(prompt_values) or _has_any_value(completion_values) or _has_any_value(total_token_values):
        charts = [
            ("Run Time (ms)", labels, runtime_values),
            ("Prompt Tokens", labels, prompt_values),
            ("Completion Tokens", labels, completion_values),
            ("Total Tokens", labels, total_token_values),
        ]
        subtitle = f"Source: {log_path}"
    else:
        total_runtime = sum(value or 0 for value in runtime_values)
        runtime_share = [
            int(round(((value or 0) / total_runtime) * 100))
            if total_runtime > 0 and value is not None
            else None
            for value in runtime_values
        ]
        cumulative: List[Optional[int]] = []
        running_total = 0
        for value in runtime_values:
            if value is None:
                cumulative.append(None)
                continue
            running_total += value
            cumulative.append(running_total)
        execution_metrics = parse_execution_metrics(log_path)
        execution_labels = ["total", "passed", "failed", "skipped"]
        execution_values = [execution_metrics[label] for label in execution_labels]
        charts = [
            ("Run Time (ms)", labels, runtime_values),
            ("Runtime Share (%)", labels, runtime_share),
            ("Cumulative Time (ms)", labels, cumulative),
            ("Test Execution Result", execution_labels, execution_values),
        ]
        subtitle = f"Source: {log_path} | per-agent token usage was not recorded in this log"

    width = 1400
    height = 900
    margin = 40
    gap = 30
    top_offset = 90
    plot_w = (width - (2 * margin) - gap) // 2
    plot_h = (height - top_offset - margin - gap) // 2

    image = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    colors = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626", "#7c3aed", "#0891b2", "#0f766e"]

    chart_title = title or "All Pipeline Agents - Runtime and Token Usage"
    _draw_text_centered(draw, font, width // 2, 25, chart_title)
    _draw_text_centered(draw, font, width // 2, 43, subtitle, fill="#6b7280")

    for idx, (chart_name, chart_labels, values) in enumerate(charts):
        col = idx % 2
        row = idx // 2
        x = margin + col * (plot_w + gap)
        y = top_offset + row * (plot_h + gap)
        _render_chart(draw, font, chart_labels, chart_name, values, (x, y, x + plot_w, y + plot_h), colors)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)


def render_manifest_runtime(manifest_path: Path, out_path: Path) -> None:
    payload = _read_json(manifest_path)
    entries = payload.get("entries", [])
    if not isinstance(entries, list) or not entries:
        raise ValueError("Manifest must contain a non-empty 'entries' list")

    model_labels: List[str] = []
    by_model: Dict[str, Dict[str, Optional[int]]] = {}
    for entry in entries:
        label = str(entry.get("label") or entry.get("run_id") or "").strip()
        log_path = Path(str(entry.get("log_path") or ""))
        if not label or not log_path.exists():
            continue
        model_labels.append(label)
        rows = parse_agent_summary(log_path)
        by_model[label] = {str(row["agent"]): _safe_int(row.get("duration_ms")) for row in rows}

    if not model_labels:
        raise ValueError(f"No usable log_path entries found in {manifest_path}")

    charts: List[tuple[str, List[Optional[int]]]] = []
    for agent in AGENT_ORDER:
        values = [by_model.get(model, {}).get(agent) for model in model_labels]
        if any(v is not None for v in values):
            charts.append((_short_label(agent), values))

    if not charts:
        raise ValueError("No agent durations found in manifest logs")

    cols = 2
    rows_count = (len(charts) + cols - 1) // cols
    width = 1400
    height = max(900, 130 + rows_count * 300)
    margin = 40
    gap = 28
    top_offset = 90
    plot_w = (width - (2 * margin) - gap) // 2
    plot_h = (height - top_offset - margin - gap * (rows_count - 1)) // rows_count

    image = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    colors = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]

    title = f"All Pipeline Agents - Runtime by Model ({payload.get('benchmark_id', manifest_path.parent.name)})"
    _draw_text_centered(draw, font, width // 2, 25, title)
    _draw_text_centered(draw, font, width // 2, 43, f"Source: {manifest_path}", fill="#6b7280")

    for idx, (agent_label, values) in enumerate(charts):
        col = idx % cols
        row = idx // cols
        x = margin + col * (plot_w + gap)
        y = top_offset + row * (plot_h + gap)
        _render_chart(draw, font, model_labels, f"{agent_label} Run Time (ms)", values, (x, y, x + plot_w, y + plot_h), colors)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Render full-pipeline agent benchmark diagrams")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--log", type=Path, help="Pipeline log containing a workflow execution summary")
    source.add_argument("--manifest", type=Path, help="LLM benchmark_manifest.json containing log_path entries")
    parser.add_argument("--out", type=Path, required=True, help="Output PNG path")
    parser.add_argument("--title", type=str, default=None, help="Optional title for --log mode")
    args = parser.parse_args(argv)

    if args.log:
        render_pipeline_usage(args.log.resolve(), args.out.resolve(), title=args.title)
    else:
        render_manifest_runtime(args.manifest.resolve(), args.out.resolve())

    print(f"Wrote: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
