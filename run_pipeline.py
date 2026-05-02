#!/usr/bin/env python3
"""
Dynamic pipeline runner that works with any number of microservices.
Loads services from services_matrix.yaml and processes them accordingly.

Usage:
  python run_pipeline.py
  python run_pipeline.py --services auth
  python run_pipeline.py --services auth,leave,payment
  python run_pipeline.py --list
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
import yaml
from loguru import logger

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from graph.workflow import TestAutomationWorkflow
from tools.service_registry import get_service_registry


def _load_business_requirements_thresholds() -> dict[str, float]:
    """Load coverage thresholds from business_requirements.yaml when available."""
    req_path = Path(__file__).parent / "business_requirements.yaml"
    if not req_path.exists():
        return {}

    try:
        data = yaml.safe_load(req_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning(f"Could not parse business_requirements.yaml for coverage targets: {exc}")
        return {}

    if not isinstance(data, dict):
        return {}

    raw_targets = data.get("COVERAGE_TARGETS", {}) or {}
    if not isinstance(raw_targets, dict):
        return {}

    mapping = {
        "LINE_COVERAGE": "line_coverage_%",
        "BRANCH_COVERAGE": "branch_coverage_%",
        "METHOD_COVERAGE": "method_coverage_%",
    }

    thresholds: dict[str, float] = {}
    for source_key, target_key in mapping.items():
        raw = raw_targets.get(source_key)
        if raw is None or str(raw).strip() == "":
            continue
        try:
            thresholds[target_key] = float(str(raw).strip())
        except ValueError:
            logger.warning(
                f"Ignoring invalid COVERAGE_TARGETS.{source_key}={raw!r} "
                "(expected float)"
            )
    return thresholds


def _load_swagger_for_service(service):
    """Load Swagger from local file first, then fall back to swagger_url."""
    swagger_file = Path(service.swagger_spec) if getattr(service, "swagger_spec", None) else None

    if swagger_file and swagger_file.exists():
        try:
            with swagger_file.open("r", encoding="utf-8") as f:
                spec = json.load(f)
            logger.info(f"Loaded Swagger spec for {service.name} from file: {swagger_file}")
            return spec
        except Exception as exc:
            logger.warning(f"Could not parse Swagger file for {service.name}: {exc}")

    swagger_url = getattr(service, "swagger_url", None)
    if swagger_url:
        try:
            response = requests.get(swagger_url, timeout=20)
            response.raise_for_status()
            spec = response.json()
            logger.info(f"Loaded Swagger spec for {service.name} from URL: {swagger_url}")
            return spec
        except Exception as exc:
            logger.warning(f"Could not fetch Swagger for {service.name} from {swagger_url}: {exc}")

    logger.warning(
        f"No Swagger spec available for {service.name}. "
        "Set swagger_spec to a file path or swagger_url to a reachable OpenAPI endpoint."
    )
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Test automation pipeline for microservices"
    )
    parser.add_argument(
        "--services",
        type=str,
        help="Comma-separated list of services to test (e.g., auth,leave,payment)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available services and exit",
    )
    parser.add_argument(
        "--order",
        action="store_true",
        help="Show execution order and exit",
    )

    args = parser.parse_args()

    try:
        registry = get_service_registry()
        registry.print_summary()
    except Exception as exc:
        logger.error(f"Failed to load service registry: {exc}")
        return 1

    if args.list:
        print("\nAvailable Services:")
        for service in registry.get_all_services():
            status = "ENABLED" if service.enabled else "DISABLED"
            print(f"  {service.name:20} {status:10} port={service.port}")
        return 0

    if args.order:
        order = registry.get_execution_order()
        print(f"\nExecution Order: {' -> '.join(order)}")
        return 0

    if args.services:
        requested = args.services.split(",")
        services_to_run = [s.strip() for s in requested]
        available = registry.get_service_names(enabled_only=False)
        invalid = [s for s in services_to_run if s not in available]
        if invalid:
            logger.error(f"Unknown services: {', '.join(invalid)}")
            return 1
    else:
        services_to_run = registry.get_service_names(enabled_only=True)

    if not services_to_run:
        logger.error("No services to run. Enable services in services_matrix.yaml")
        return 1

    logger.info(f"Services to test: {', '.join(services_to_run)}")

    all_swagger_specs = {}
    for service_name in registry.get_service_names(enabled_only=False):
        service = registry.get_service(service_name)
        spec = _load_swagger_for_service(service)
        if spec:
            all_swagger_specs[service_name] = spec

    print("\n" + "=" * 80)
    print("  TEST AUTOMATION PIPELINE (CONSOLIDATED E2E)")
    print("=" * 80 + "\n")

    user_story_file = Path("examples/comprehensive_user_story.md")
    if not user_story_file.exists():
        logger.error(f"User story not found: {user_story_file}")
        return 1

    user_story = user_story_file.read_text(encoding="utf-8")

    results = {}
    try:
        workflow = TestAutomationWorkflow()

        coverage_thresholds = _load_business_requirements_thresholds()
        env_to_key = {
            "MIN_LINE_COVERAGE": "line_coverage_%",
            "MIN_BRANCH_COVERAGE": "branch_coverage_%",
            "MIN_METHOD_COVERAGE": "method_coverage_%",
            "COVERAGE_MIN_LINE": "line_coverage_%",
            "COVERAGE_MIN_BRANCH": "branch_coverage_%",
            "COVERAGE_MIN_METHOD": "method_coverage_%",
        }
        for env_name, key in env_to_key.items():
            raw = os.getenv(env_name)
            if raw is None or not str(raw).strip():
                continue
            try:
                coverage_thresholds[key] = float(str(raw).strip())
            except ValueError:
                logger.warning(f"Ignoring invalid {env_name}={raw!r} (expected float)")

        runtime_config = {}
        if coverage_thresholds:
            runtime_config["coverage_thresholds"] = coverage_thresholds
            logger.info(f"Coverage thresholds for this run: {coverage_thresholds}")

        logger.info(f"\n{'=' * 80}")
        logger.info(f"END-TO-END Testing Services: {', '.join(services_to_run)}")
        logger.info(f"{'=' * 80}\n")

        consolidated_service_name = "_".join(services_to_run)

        workflow_state = workflow.run(
            user_story=user_story,
            service_name=consolidated_service_name,
            swagger_spec=all_swagger_specs,
            swagger_specs=all_swagger_specs,
            config=runtime_config,
            is_e2e=True,
            e2e_services=services_to_run,
        )

        results[consolidated_service_name] = {
            "workflow_id": workflow_state.workflow_id,
            "status": workflow_state.workflow_status,
            "gherkin_files": workflow_state.gherkin_files,
            "test_files": workflow_state.test_files,
            "coverage_percentage": workflow_state.coverage_percentage,
        }

        print("\n" + "=" * 80)
        print("  CONSOLIDATED E2E PIPELINE COMPLETED")
        print("=" * 80 + "\n")

        for service_name, summary in results.items():
            status_text = "PASSED" if summary["status"] == "completed" else "FAILED"
            print(f"[{status_text}] {service_name:30} | Status: {summary['status']}")
            if summary["gherkin_files"]:
                print(f"   Generated {len(summary['gherkin_files'])} consolidated feature file(s)")
            if summary["test_files"]:
                print(f"   Generated {len(summary['test_files'])} test file(s)")
            if summary["coverage_percentage"] is not None:
                print(f"   Coverage: {summary['coverage_percentage']:.1f}%")

        if workflow_state.workflow_status == "completed":
            print("\n[OK] End-to-end consolidated tests completed!\n")
        else:
            print("\n[FAILED] End-to-end consolidated tests failed.\n")

        return 0 if workflow_state.workflow_status == "completed" else 1

    except Exception as exc:
        logger.exception(f"Pipeline failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
