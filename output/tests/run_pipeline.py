"""Convenience wrapper to run the project pipeline from within output/tests.

The real pipeline entrypoint lives at the workspace root: ../../run_pipeline.py

Usage:
  python run_pipeline.py

This keeps the current Python interpreter/venv.
"""

from __future__ import annotations

import runpy
from pathlib import Path
import os
import sys


def main() -> int:
    here = Path(__file__).resolve()
    root_pipeline = (here.parent / ".." / ".." / "run_pipeline.py").resolve()

    if not root_pipeline.exists():
        print(f"ERROR: Expected pipeline at: {root_pipeline}", file=sys.stderr)
        print("Run from repo root instead: python run_pipeline.py", file=sys.stderr)
        return 2

    # The root pipeline uses repo-relative paths; make execution identical to
    # running `python run_pipeline.py` from the workspace root.
    os.chdir(str(root_pipeline.parent))

    # Execute the root pipeline as if it were __main__
    runpy.run_path(str(root_pipeline), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
