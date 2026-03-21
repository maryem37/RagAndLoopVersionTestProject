#!/usr/bin/env python3
"""Test coverage analyst with actual test state"""

import sys
import os
sys.path.insert(0, '.')
os.environ['PYTHONIOENCODING'] = 'utf-8'

from pathlib import Path
from graph.state import TestAutomationState
from agents.coverage_analyst import CoverageAnalystAgent

# Create a mock state
state = TestAutomationState(
    workflow_id="test_coverage_001",
    user_story="Test user story",
    service_name="leave-request-service",
    swagger_spec={},
    swagger_specs={},
)

# Set paths to where tests actually ran
state.test_files = [
    str(Path("output/tests/src/test/java/com/example/auth/steps/AuthSteps.java"))
]
state.execution_result = {
    "total": 12,
    "passed": 12,
    "failed": 0,
    "skipped": 0,
    "raw_output_tail": "Tests run: 12, Failures: 0, Errors: 0, Skipped: 0",
}

# Run coverage analysis
try:
    agent = CoverageAnalystAgent()
    print("[OK] Agent initialized")
    
    updated_state = agent.analyze(state)
    print("[OK] Analysis completed")
    
    if hasattr(updated_state, 'coverage_files') and updated_state.coverage_files:
        print(f"[OK] Generated {len(updated_state.coverage_files)} report files:")
        for f in updated_state.coverage_files:
            print(f"   - {f}")
    else:
        print("[WARNING] No coverage files in state")
        
    if hasattr(updated_state, 'coverage_report') and updated_state.coverage_report:
        print(f"[OK] Coverage report in state exists")
    
except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# Check if files were created
reports_dir = Path("output/reports")
if reports_dir.exists():
    files = list(reports_dir.glob("*.yaml")) + list(reports_dir.glob("*.json"))
    if files:
        print(f"\n[OK] Found {len(files)} report files in {reports_dir}:")
        for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            print(f"   - {f.name}")
    else:
        print(f"\n[WARNING] No reports found in {reports_dir}")
else:
    print(f"\n[WARNING] Reports directory doesn't exist: {reports_dir}")

