"""
graph/__main__.py
------------------------------
Entry point for running: python -m graph
Shows pipeline progress in console with formatted output.
"""

import json
import sys
from pathlib import Path

# Configure loguru to also output to console
from loguru import logger
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="<level>{message}</level>", colorize=True, level="INFO")

from graph.workflow import TestAutomationWorkflow

def main():
    """Run the full test automation pipeline."""
    
    print("\n" + "="*80)
    print("  [START] TEST AUTOMATION PIPELINE")
    print("="*80 + "\n")
    
    try:
        # Load user story
        user_story_file = Path("examples/sample_user_story.md")
        if not user_story_file.exists():
            print(f"[ERROR] User story not found: {user_story_file}")
            return 1
        
        user_story = user_story_file.read_text(encoding="utf-8")
        print(f"[OK] Loaded user story from {user_story_file}")
        
        # Load Swagger specs
        swagger_files = {
            "auth": Path("examples/sample_swagger1.json"),
            "leave": Path("examples/sample_swagger2.json"),
        }
        
        swagger_specs = {}
        for name, path in swagger_files.items():
            if path.exists():
                swagger_specs[name] = json.load(path.open())
                print(f"[OK] Loaded Swagger spec: {name}")
            else:
                print(f"[WARN] Swagger file not found: {path}")
        
        if not swagger_specs:
            print("[ERROR] No Swagger specs found")
            return 1
        
        print("\n" + "-"*80)
        print("  Starting pipeline stages...")
        print("-"*80 + "\n")
        
        # Run workflow
        workflow = TestAutomationWorkflow()
        result = workflow.run(
            user_story=user_story,
            service_name="leave-request-service",
            swagger_specs=swagger_specs,
        )
        
        print("\n" + "="*80)
        print("  ✅ PIPELINE COMPLETED SUCCESSFULLY")
        print("="*80)
        
        # Summary
        print("\n[CHART] RESULTS:")
        print(f"   Workflow ID: {result.workflow_id}")
        print(f"   Status: {result.workflow_status}")
        
        if hasattr(result, 'coverage_files') and result.coverage_files:
            print(f"\n📄 Generated Reports:")
            for f in result.coverage_files:
                print(f"   - {f}")
        
        if hasattr(result, 'test_files') and result.test_files:
            print(f"\n📝 Generated Test Files: {len(result.test_files)}")
            for f in result.test_files[:3]:
                print(f"   - {Path(f).name}")
        
        if result.errors:
            print(f"\n[WARN]️  Errors ({len(result.errors)}):")
            for err in result.errors[:3]:
                print(f"   - {err}")
        
        print("\n" + "="*80 + "\n")
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

# Auto-run when module is executed
if __name__ != "__main__":
    # This runs when imported as a module via -m flag
    sys.exit(main())

