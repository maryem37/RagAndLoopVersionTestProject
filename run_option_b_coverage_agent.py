#!/usr/bin/env python3
"""Generate/refresh OPTION_B_COVERAGE_REPORT.md from the latest JaCoCo outputs.

Usage:
  python run_option_b_coverage_agent.py

Prereq:
  - You already ran the Option B flow to produce JaCoCo outputs under output/tests/target/site/jacoco
    (e.g., run_real_coverage.ps1 or manual: copy real-*.exec then mvn -DskipTests verify)
"""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

# Ensure local imports work when executed from repo root
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from graph.state import TestAutomationState
from agents.coverage_analyst import CoverageAnalystAgent


def main() -> int:
    state = TestAutomationState(
        workflow_id="option_b_coverage_report",
        user_story="Option B coverage report generation",
        service_name="option-b-real-services",
        swagger_spec={},
        swagger_specs={},
    )

    agent = CoverageAnalystAgent()
    state = agent.analyze(state)

    # Write the human-friendly Option B report
    agent.write_option_b_report(state)

    out_path = Path(agent.settings.paths.base_dir) / "OPTION_B_COVERAGE_REPORT.md"
    print(f"[OK] Wrote {out_path}")

    # Open the JaCoCo HTML report (if present)
    html_report = Path(agent.settings.paths.tests_dir) / "target" / "site" / "jacoco" / "index.html"
    if html_report.exists():
      webbrowser.open(html_report.resolve().as_uri())
      print(f"[OK] Opened {html_report}")
    else:
      print(f"[WARN] Missing HTML report: {html_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
