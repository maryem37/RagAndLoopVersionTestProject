#!/usr/bin/env python3
"""
Quick debug script to trace the Swagger spec loading
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from tools.service_registry import get_service_registry

# Configure logging
logger.remove()
logger.add(sys.stderr, format="<level>{level: <8}</level> | {message}")

def main():
    print("\n" + "="*80)
    print(" DEBUG: Tracing Swagger Spec Loading")
    print("="*80 + "\n")
    
    # Load registry
    try:
        registry = get_service_registry()
        print(f"✓ Registry loaded with {len(registry.get_all_services())} services\n")
    except Exception as e:
        print(f"✗ Failed to load registry: {e}\n")
        return 1
    
    # Check each service
    all_swagger_specs = {}
    for service_name in registry.get_service_names(enabled_only=False):
        service = registry.get_service(service_name)
        print(f"\nService: {service_name}")
        print(f"  Enabled: {service.enabled}")
        print(f"  swagger_spec attribute: {service.swagger_spec}")
        
        swagger_file = None
        if hasattr(service, 'swagger_spec') and service.swagger_spec:
            swagger_file = Path(service.swagger_spec)
            print(f"  swagger_file path: {swagger_file}")
            print(f"  File exists: {swagger_file.exists()}")
            print(f"  Absolute path: {swagger_file.absolute()}")
        
        if swagger_file and swagger_file.exists():
            try:
                with open(swagger_file, 'r', encoding='utf-8') as f:
                    spec = json.load(f)
                    all_swagger_specs[service_name] = spec
                    print(f"  ✓ Loaded {len(spec)} top-level keys from {swagger_file}")
            except Exception as e:
                print(f"  ✗ Load failed: {e}")
        else:
            print(f"  ⚠ Swagger file not found for {service_name}")
    
    print(f"\n{'='*80}")
    print(f"Total loaded: {len(all_swagger_specs)} services")
    print(f"Services with specs: {list(all_swagger_specs.keys())}")
    print(f"{'='*80}\n")
    
    return 0 if all_swagger_specs else 1

if __name__ == "__main__":
    sys.exit(main())
