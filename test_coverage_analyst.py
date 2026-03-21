#!/usr/bin/env python3
"""Quick test of coverage analyst initialization"""

import sys
sys.path.insert(0, '.')

try:
    from agents.coverage_analyst import CoverageAnalystAgent
    agent = CoverageAnalystAgent()
    print("✅ Coverage Analyst Agent initialized successfully")
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
