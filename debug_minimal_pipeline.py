#!/usr/bin/env python3
"""
Minimal pipeline test - trace where swagger_specs gets lost
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from graph.workflow import TestAutomationWorkflow
from tools.service_registry import get_service_registry

def main():
    print("\n" + "="*80)
    print(" DEBUG: Running Minimal Pipeline Test")
    print("="*80 + "\n")
    
    # Setup logging
    logger.add(sys.stdout, format="<level>{level: <8}</level> | {message}")
    
    # Load registry and Swagger specs
    registry = get_service_registry()
    all_swagger_specs = {}
    for service_name in registry.get_service_names(enabled_only=False):
        service = registry.get_service(service_name)
        swagger_file = None
        if hasattr(service, 'swagger_spec') and service.swagger_spec:
            swagger_file = Path(service.swagger_spec)
        
        if swagger_file and swagger_file.exists():
            with open(swagger_file, 'r', encoding='utf-8') as f:
                all_swagger_specs[service_name] = json.load(f)
    
    print(f"[OK] Loaded {len(all_swagger_specs)} Swagger specs")
    
    # Load user story
    user_story_file = Path("examples/comprehensive_user_story.md")
    if not user_story_file.exists():
        print(f"[ERROR] User story not found: {user_story_file}")
        return 1
    
    user_story = user_story_file.read_text(encoding='utf-8')
    print(f"[OK] Loaded user story ({len(user_story)} chars)")
    
    # Run workflow
    try:
        print("\n" + "="*80)
        print(" Running Workflow...")
        print("="*80 + "\n")
        
        workflow = TestAutomationWorkflow()
        
        result = workflow.run(
            user_story=user_story,
            service_name="auth_leave",
            swagger_spec=all_swagger_specs,
            swagger_specs=all_swagger_specs,
            is_e2e=True,
            e2e_services=["auth", "leave"],
        )
        
        print(f"\n[OK] Workflow completed")
        print(f"  Status: {result.workflow_status}")
        print(f"  Gherkin files: {len(result.gherkin_files)}")
        print(f"  Test files: {len(result.test_files)}")
        print(f"  Errors: {len(result.errors)}")
        
        if result.errors:
            print(f"\nErrors:")
            for err in result.errors[:3]:
                print(f"  - {err[:200]}")
        
        return 0
        
    except Exception as e:
        print(f"[ERROR] Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
