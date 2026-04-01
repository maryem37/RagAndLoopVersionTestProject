#!/usr/bin/env python3
"""
run_pipeline_windows.py
──────────────────────

Windows-safe wrapper for the test automation pipeline.
Fixes console encoding before running the pipeline to prevent UnicodeEncodeError.

Usage:
  python run_pipeline_windows.py                      # Run all services
  python run_pipeline_windows.py --services auth      # Run specific service
  python run_pipeline_windows.py --services auth,leave
"""

import sys
import os
from pathlib import Path

# Fix Windows UTF-8 encoding BEFORE importing anything else
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Now we can import the rest
sys.path.insert(0, str(Path(__file__).parent))

from run_pipeline import main

if __name__ == "__main__":
    sys.exit(main())
