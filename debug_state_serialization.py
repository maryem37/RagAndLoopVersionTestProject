#!/usr/bin/env python3
"""
Debug script to trace state through the workflow
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from graph.state import TestAutomationState
from tools.service_registry import get_service_registry

def main():
    print("\n" + "="*80)
    print(" DEBUG: State Initialization Test")
    print("="*80 + "\n")
    
    # Load registry
    registry = get_service_registry()
    
    # Load Swagger specs
    all_swagger_specs = {}
    for service_name in registry.get_service_names(enabled_only=False):
        service = registry.get_service(service_name)
        swagger_file = None
        if hasattr(service, 'swagger_spec') and service.swagger_spec:
            swagger_file = Path(service.swagger_spec)
        
        if swagger_file and swagger_file.exists():
            with open(swagger_file, 'r', encoding='utf-8') as f:
                all_swagger_specs[service_name] = json.load(f)
    
    print(f"✓ Loaded {len(all_swagger_specs)} Swagger specs")
    
    # Create a state like workflow.run() does
    initial_state = TestAutomationState(
        workflow_id="test_workflow_001",
        user_story="Test user story",
        service_name="auth_leave",
        swagger_spec=all_swagger_specs,  # This is dict
        swagger_specs=all_swagger_specs,  # This is dict
        is_e2e=True,
        e2e_services=["auth", "leave"],
    )
    
    print(f"\nInitial State Created:")
    print(f"  swagger_spec type: {type(initial_state.swagger_spec)}")
    print(f"  swagger_spec keys: {list(initial_state.swagger_spec.keys()) if initial_state.swagger_spec else 'empty'}")
    print(f"  swagger_specs type: {type(initial_state.swagger_specs)}")
    print(f"  swagger_specs keys: {list(initial_state.swagger_specs.keys()) if initial_state.swagger_specs else 'empty'}")
    
    # Simulate what langgraph might do (convert to dict and back)
    print(f"\nSimulating LangGraph serialization...")
    state_dict = initial_state.dict() if hasattr(initial_state, 'dict') else initial_state.model_dump()
    print(f"  state_dict['swagger_spec'] keys: {list(state_dict.get('swagger_spec', {}).keys())}")
    print(f"  state_dict['swagger_specs'] keys: {list(state_dict.get('swagger_specs', {}).keys())}")
    
    # Reconstruct from dict
    restored_state = TestAutomationState(**state_dict)
    print(f"\nRestored State:")
    print(f"  swagger_spec type: {type(restored_state.swagger_spec)}")
    print(f"  swagger_spec keys: {list(restored_state.swagger_spec.keys()) if restored_state.swagger_spec else 'empty'}")
    print(f"  swagger_specs type: {type(restored_state.swagger_specs)}")
    print(f"  swagger_specs keys: {list(restored_state.swagger_specs.keys()) if restored_state.swagger_specs else 'empty'}")
    
    # Test the condition from test_writer
    specs = {}
    if hasattr(restored_state, "swagger_specs") and restored_state.swagger_specs:
        specs = restored_state.swagger_specs
    elif hasattr(restored_state, "swagger_spec") and restored_state.swagger_spec:
        specs = {restored_state.service_name: restored_state.swagger_spec}
    
    print(f"\ntest_writer would find: {len(specs)} specs")
    print(f"Specs keys: {list(specs.keys())}")
    
    if not specs:
        print("✗ ERROR: No specs found!")
        return 1
    else:
        print("✓ SUCCESS: Specs preserved through serialization!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
