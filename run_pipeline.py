#!/usr/bin/env python3
"""
Dynamic pipeline runner that works with any number of microservices
Loads services from services_matrix.yaml and processes them accordingly

Usage:
  python run_pipeline.py                    # Run all enabled services
  python run_pipeline.py --services auth    # Run specific service
  python run_pipeline.py --services auth,leave,payment  # Multiple services
  python run_pipeline.py --list            # Show available services
"""

import json
import sys
import argparse
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from graph.workflow import TestAutomationWorkflow
from tools.service_registry import get_service_registry


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Test automation pipeline for microservices"
    )
    parser.add_argument(
        '--services',
        type=str,
        help='Comma-separated list of services to test (e.g., auth,leave,payment)'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available services and exit'
    )
    parser.add_argument(
        '--order',
        action='store_true',
        help='Show execution order and exit'
    )
    
    args = parser.parse_args()
    
    # Load service registry
    try:
        registry = get_service_registry()
        registry.print_summary()
    except Exception as e:
        logger.error(f"❌ Failed to load service registry: {e}")
        return 1
    
    # Handle --list
    if args.list:
        print("\n📋 Available Services:")
        for service in registry.get_all_services():
            status = "✅ ENABLED" if service.enabled else "⏸️  DISABLED"
            print(f"  {service.name:20} {status:15} port={service.port}")
        return 0
    
    # Handle --order
    if args.order:
        order = registry.get_execution_order()
        print(f"\n📊 Execution Order: {' → '.join(order)}")
        return 0
    
    # Determine which services to run
    if args.services:
        requested = args.services.split(',')
        services_to_run = [s.strip() for s in requested]
        
        # Validate requested services exist
        available = registry.get_service_names(enabled_only=False)
        invalid = [s for s in services_to_run if s not in available]
        if invalid:
            logger.error(f"❌ Unknown services: {', '.join(invalid)}")
            return 1
    else:
        # Run all enabled services
        services_to_run = registry.get_service_names(enabled_only=True)
    
    if not services_to_run:
        logger.error("❌ No services to run. Enable services in services_matrix.yaml")
        return 1
    
    logger.info(f"📋 Services to test: {', '.join(services_to_run)}")
    
    # Load Swagger specs for ALL services (needed for E2E tests)
    # But only pass the relevant ones to the workflow for the service being tested
    all_swagger_specs = {}
    for service_name in registry.get_service_names(enabled_only=False):
        service = registry.get_service(service_name)
        
        # Try to load from configured swagger_spec file path
        swagger_file = None
        if hasattr(service, 'swagger_spec') and service.swagger_spec:
            swagger_file = Path(service.swagger_spec)
        
        if swagger_file and swagger_file.exists():
            try:
                with open(swagger_file, 'r', encoding='utf-8') as f:
                    all_swagger_specs[service_name] = json.load(f)
                logger.info(f"✅ Loaded Swagger spec for {service_name} from {swagger_file}")
            except Exception as e:
                logger.warning(f"⚠️  Could not load Swagger for {service_name}: {e}")
        else:
            logger.warning(f"⚠️  No Swagger spec found for {service_name}")
    
    print("\n" + "="*80)
    print("  TEST AUTOMATION PIPELINE (CONSOLIDATED E2E)")
    print("="*80 + "\n")
    
    # Load user story
    user_story_file = Path("examples/comprehensive_user_story.md")
    if not user_story_file.exists():
        logger.error(f"❌ User story not found: {user_story_file}")
        return 1
    
    user_story = user_story_file.read_text(encoding='utf-8')
    
    # Run workflow for ALL services together (E2E consolidated)
    results = {}
    try:
        workflow = TestAutomationWorkflow()
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 END-TO-END Testing Services: {', '.join(services_to_run)}")
        logger.info(f"{'='*80}\n")
        
        # Process all services together as one consolidated E2E test
        consolidated_service_name = "_".join(services_to_run)
        
        result = workflow.run(
            user_story=user_story,
            service_name=consolidated_service_name,
            swagger_spec=all_swagger_specs,  # Pass all specs for consolidated testing
            swagger_specs=all_swagger_specs,  # Pass ALL swagger specs for E2E context
            is_e2e=True,  # Flag to indicate end-to-end consolidated testing
            e2e_services=services_to_run,  # List of services being tested together
        )
        
        results[consolidated_service_name] = {
            'workflow_id': result.workflow_id,
            'status': result.workflow_status,
            'gherkin_files': result.gherkin_files,
            'test_files': result.test_files,
            'coverage_percentage': result.coverage_percentage,
        }
        
        # Print summary
        print("\n" + "="*80)
        print("  CONSOLIDATED E2E PIPELINE COMPLETED")
        print("="*80 + "\n")
        
        for service_name, result in results.items():
            status_text = "PASSED" if result['status'] == 'completed' else "FAILED"
            print(f"[{status_text}] {service_name:30} | Status: {result['status']}")
            if result['gherkin_files']:
                print(f"   Generated {len(result['gherkin_files'])} consolidated feature file(s)")
            if result['test_files']:
                print(f"   Generated {len(result['test_files'])} test file(s)")
            if result['coverage_percentage'] is not None:
                print(f"   Coverage: {result['coverage_percentage']:.1f}%")
        
        print("\n[OK] End-to-end consolidated tests completed!\n")
        return 0
        
    except Exception as e:
        logger.exception(f"❌ Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

