"""tools/analyze_cucumber_failures.py

Small helper to summarize failures from a Cucumber JSON report.

Usage (PowerShell):
  python -m tools.analyze_cucumber_failures
  python -m tools.analyze_cucumber_failures --report output/tests/target/cucumber-reports/e2e/cucumber.json

It prints:
- Total scenarios + failed scenarios
- HTTP code frequency found in error messages
- Top failing step names overall and per code
- Best-effort extraction of API paths (e.g. /api/foo/123) from messages

Note: Not all assertion failures include the request path; in those cases, we can
still identify the failing step name.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Iterable


_HTTP_CODES = ("401", "403", "404", "409", "422", "500")
_CODE_RE = re.compile(r"\b(" + "|".join(_HTTP_CODES) + r")\b")
_PATH_RE = re.compile(r'"path"\s*:\s*"([^"]+)"')
_API_RE = re.compile(r"(/api/[A-Za-z0-9_\-./]+)")


def _iter_scenarios(cucumber_json: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(cucumber_json, list):
        return
    for feature in cucumber_json:
        if not isinstance(feature, dict):
            continue
        for scenario in feature.get("elements") or []:
            if isinstance(scenario, dict):
                yield scenario


def analyze(report_path: Path) -> dict[str, Any]:
    data = json.loads(report_path.read_text(encoding="utf-8"))

    scenario_total = 0
    scenario_failed = 0

    code_counts: Counter[str] = Counter()
    step_counts: Counter[str] = Counter()

    step_by_code: DefaultDict[str, Counter[str]] = defaultdict(Counter)
    path_by_code: DefaultDict[str, Counter[str]] = defaultdict(Counter)

    for scenario in _iter_scenarios(data):
        scenario_total += 1
        scen_failed = False

        for step in scenario.get("steps") or []:
            if not isinstance(step, dict):
                continue
            res = step.get("result") or {}
            status = (res.get("status") or "").strip().lower()
            if status not in {"failed", "undefined"}:
                continue

            scen_failed = True
            step_name = (step.get("name") or "").strip() or "(no step name)"
            msg = res.get("error_message") or ""

            step_counts[step_name] += 1

            codes = set(_CODE_RE.findall(msg))
            if not codes:
                codes = {"?"}

            for code in codes:
                if code != "?":
                    code_counts[code] += 1

                step_by_code[code][step_name] += 1

                for path in _PATH_RE.findall(msg):
                    path_by_code[code][path] += 1
                for path in _API_RE.findall(msg):
                    path_by_code[code][path] += 1

        if scen_failed:
            scenario_failed += 1

    pass_rate = (
        (100.0 * (scenario_total - scenario_failed) / scenario_total)
        if scenario_total
        else 0.0
    )

    return {
        "scenario_total": scenario_total,
        "scenario_failed": scenario_failed,
        "pass_rate": pass_rate,
        "code_counts": code_counts,
        "step_counts": step_counts,
        "step_by_code": step_by_code,
        "path_by_code": path_by_code,
    }


def _print_counter(title: str, counter: Counter[str], limit: int) -> None:
    print(title)
    if not counter:
        print("  (none)")
        return
    for k, n in counter.most_common(limit):
        print(f"  {n:4d}  {k}")


def main() -> int:
    # Windows consoles can default to legacy encodings (e.g. cp1252) that cannot
    # print certain Unicode characters found in step names/messages.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Summarize failures from a Cucumber JSON report")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("output/tests/target/cucumber-reports/e2e/cucumber.json"),
        help="Path to cucumber.json",
    )
    parser.add_argument("--top", type=int, default=15, help="Top N to show")

    args = parser.parse_args()

    if not args.report.exists():
        raise SystemExit(f"Report not found: {args.report}")

    result = analyze(args.report)

    total = result["scenario_total"]
    failed = result["scenario_failed"]
    pass_rate = result["pass_rate"]
    print(f"Scenarios: total={total} failed={failed} pass_rate={pass_rate:.2f}%")

    print("\nHTTP codes in failure messages:")
    code_counts: Counter[str] = result["code_counts"]
    if code_counts:
        for code, n in code_counts.most_common():
            print(f"  {code}: {n}")
    else:
        print("  (none detected)")

    _print_counter("\nTop failing steps (all):", result["step_counts"], args.top)

    step_by_code: DefaultDict[str, Counter[str]] = result["step_by_code"]
    path_by_code: DefaultDict[str, Counter[str]] = result["path_by_code"]

    for code in list(_HTTP_CODES) + ["?"]:
        if code not in step_by_code:
            continue

        _print_counter(f"\nTop failing steps for {code}:", step_by_code[code], min(args.top, 10))

        if path_by_code.get(code):
            _print_counter(f"Top paths for {code}:", path_by_code[code], min(args.top, 10))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
