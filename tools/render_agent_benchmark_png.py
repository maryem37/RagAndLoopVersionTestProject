from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PIL import Image, ImageDraw, ImageFont


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _count_lint_issues(result: Dict[str, Any]) -> Optional[int]:
    issues = _safe_int(((result.get("gherkin_lint") or {}).get("issues")))
    if issues is not None:
        return issues

    output = str((result.get("gherkin_lint") or {}).get("output") or "")
    if not output.strip():
        return None

    stripped = re.sub(r"\x1b\[[0-9;]*m", "", output)
    lines = [
        line for line in stripped.splitlines()
        if re.match(r"^\s*\d+\s+", line)
    ]
    return len(lines) if lines else None


def _usage_value(result: Dict[str, Any], key: str) -> Optional[int]:
    usage = result.get("llm_usage", {})
    if not isinstance(usage, dict):
        return None
    return _safe_int(usage.get(key))


def _draw_text_centered(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont, x_center: int, y: int, value: str, fill: str = "#111827") -> None:
    bbox = draw.textbbox((0, 0), value, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text((x_center - text_w // 2, y), value, fill=fill, font=font)


def _render_chart(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont, labels: List[str], title: str, values: List[Optional[int]], box: tuple[int, int, int, int], colors: List[str]) -> None:
    x0, y0, x1, y1 = box
    left = x0 + 55
    right = x1 - 20
    top = y0 + 35
    bottom = y1 - 50

    draw.rectangle([x0, y0, x1, y1], outline="#dbe4f0", width=1)
    draw.text((x0 + 10, y0 + 8), title, fill="#111827", font=font)

    max_value = max([v for v in values if v is not None] or [1])
    max_value = max(1, max_value)

    for tick_idx in range(5):
        frac = tick_idx / 4
        y = bottom - int((bottom - top) * frac)
        draw.line([left, y, right, y], fill="#d1d5db", width=1)
        draw.text((x0 + 8, y - 6), str(int(max_value * frac)), fill="#374151", font=font)

    draw.line([left, top, left, bottom], fill="#374151", width=2)
    draw.line([left, bottom, right, bottom], fill="#374151", width=2)

    slot = (right - left) / max(len(labels), 1)
    bar_w = max(24, int(slot * 0.45))

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

        _draw_text_centered(draw, font, center_x, bar_top - 14, annotation)
        _draw_text_centered(draw, font, center_x, bottom + 10, label, fill="#374151")


def render_manifest(manifest_path: Path, out_path: Path, mode: str = "quality") -> None:
    payload = _read_json(manifest_path)
    results = payload.get("results", [])
    if not isinstance(results, list) or not results:
        raise ValueError("Manifest must contain a non-empty 'results' list")

    agent = str(payload.get("agent", "agent")).strip() or "agent"
    labels = [str((item.get("model") or {}).get("label", "")) for item in results]

    if mode == "usage":
        title = f"{agent} - LLM Runtime and Token Usage"
        charts = [
            ("Run Time (ms)", [_safe_int(item.get("duration_ms")) for item in results]),
            ("Prompt Tokens", [_usage_value(item, "prompt_tokens") for item in results]),
            ("Completion Tokens", [_usage_value(item, "completion_tokens") for item in results]),
            ("Total Tokens", [_usage_value(item, "total_tokens") for item in results]),
        ]
    else:
        title = f"{agent} - 3-Model Comparison"
        charts = [
            ("Duration (ms)", [_safe_int(item.get("duration_ms")) for item in results]),
            ("Scenarios", [_safe_int((item.get("gherkin") or {}).get("scenarios")) for item in results]),
            ("Steps", [_safe_int((item.get("gherkin") or {}).get("steps")) for item in results]),
            ("Gherkin Lint Issues", [_count_lint_issues(item) for item in results]),
        ]

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
    colors = ["#2563eb", "#f59e0b", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]

    _draw_text_centered(draw, font, width // 2, 25, title)

    for idx, (title, values) in enumerate(charts):
        col = idx % 2
        row = idx // 2
        x = margin + col * (plot_w + gap)
        y = top_offset + row * (plot_h + gap)
        _render_chart(draw, font, labels, title, values, (x, y, x + plot_w, y + plot_h), colors)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Render a single-agent benchmark manifest to a PNG chart")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to benchmark_manifest.json")
    parser.add_argument("--out", type=Path, required=True, help="Output PNG path")
    parser.add_argument(
        "--mode",
        type=str,
        default="quality",
        choices=["quality", "usage"],
        help="Which chart set to render",
    )
    args = parser.parse_args(argv)

    render_manifest(args.manifest.resolve(), args.out.resolve(), mode=args.mode)
    print(f"Wrote: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
