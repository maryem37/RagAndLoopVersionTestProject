"""
agents/scenario_designer.py
------------------------------
Agent 0 — Scenario Designer Agent (NEW AGENT)

ROLE:
  This agent runs BEFORE gherkin_generator and transforms Swagger specs
  into high-quality test scenarios based on business requirements.

INPUTS:
  1. Swagger specifications (both services: conge + DemandeConge)
  2. business_requirements.yaml (user stories, business rules, edge cases)

OUTPUTS:
  1. Structured test scenarios with Given/When/Then format
  2. Covers: happy path, error cases, edge cases, security, integration
  3. JSON output fed to gherkin_generator (replaces direct Swagger→Gherkin)

WHY THIS AGENT:
  - Auto-generated tests from Swagger alone = weak coverage (34%)
  - With business requirements = contextual scenarios = strong coverage (60%+)
  - Identifies edge cases developers miss
  - Tests integration points between two services

POSITION IN PIPELINE:
  swagger_specs → scenario_designer → gherkin_generator → test_writer → ...
"""

from __future__ import annotations

import json
import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from loguru import logger

from config.settings import get_settings
from graph.state import AgentOutput, AgentStatus, TestAutomationState


class TestScenario:
    """Single test scenario with Given/When/Then structure"""

    def __init__(
        self,
        scenario_id: str,
        title: str,
        endpoint: str,
        method: str,
        given: str,
        when: str,
        then: str,
        test_type: str,
        priority: str,
        service: str,
        is_integration: bool = False,
    ):
        self.scenario_id = scenario_id
        self.title = title
        self.endpoint = endpoint
        self.method = method
        self.given = given
        self.when = when
        self.then = then
        self.test_type = test_type  # happy_path, error_case, edge_case, security
        self.priority = priority  # P0, P1, P2
        self.service = service  # auth or leave
        self.is_integration = is_integration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "endpoint": self.endpoint,
            "method": self.method,
            "given": self.given,
            "when": self.when,
            "then": self.then,
            "test_type": self.test_type,
            "priority": self.priority,
            "service": self.service,
            "is_integration": self.is_integration,
        }


class ScenarioDesignerAgent:
    """
    Agent 0 — Scenario Designer.

    Reads business requirements + Swagger specs → generates test scenarios.
    Works for ANY microservice architecture (1 or 2 services).
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.scenarios: List[TestScenario] = []
        logger.info("✅ Scenario Designer Agent initialized")

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN EXECUTION
    # ══════════════════════════════════════════════════════════════════════════

    def execute(self, state: TestAutomationState) -> AgentOutput:
        """
        Main execution method. Called by workflow.

        INPUT: TestAutomationState with swagger_spec
        OUTPUT: AgentOutput with test_scenarios populated
        """
        start_time = time.time()
        logger.info("🎬 [SCENARIO DESIGNER] Starting scenario generation...")

        try:
            # Step 1: Load business requirements
            business_reqs = self._load_business_requirements()
            if not business_reqs:
                logger.warning("⚠️ business_requirements.yaml not found, using defaults")
                business_reqs = self._get_default_requirements()

            # Step 2: Parse Swagger specs (both services)
            swagger_specs = getattr(state, "swagger_specs", None) or {}
            if swagger_specs:
                logger.info(
                    f"   Using {len(swagger_specs)} Swagger spec(s) from workflow state"
                )
            else:
                swagger_specs = self._load_all_swagger_specs()
            if not swagger_specs:
                logger.error("❌ No Swagger specs found")
                return AgentOutput(
                    agent_name="scenario_designer",
                    status=AgentStatus.FAILED,
                    error="No Swagger specifications available",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Step 3: Generate scenarios for each service
            self.scenarios = []
            for service_name, spec in swagger_specs.items():
                service_reqs = self._get_service_requirements(
                    business_reqs, service_name
                )
                service_scenarios = self._generate_service_scenarios(
                    service_name, spec, service_reqs
                )
                self.scenarios.extend(service_scenarios)
                logger.info(
                    f"   Generated {len(service_scenarios)} scenarios for {service_name} service"
                )

            # Step 4: Generate integration scenarios
            integration_scenarios = self._generate_integration_scenarios(
                business_reqs, swagger_specs
            )
            self.scenarios.extend(integration_scenarios)
            logger.info(
                f"   Generated {len(integration_scenarios)} integration scenarios"
            )

            # Step 5: Consolidate scenarios (if multiple services)
            consolidated = self._consolidate_scenarios(self.scenarios)

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Step 6: Log summary
            logger.info(
                f"   [OK] Generated {len(self.scenarios)} total test scenarios ({elapsed_ms}ms)"
            )
            logger.info(f"   Happy Path: {len([s for s in self.scenarios if s.test_type == 'happy_path'])}")
            logger.info(f"   Error Cases: {len([s for s in self.scenarios if s.test_type == 'error_case'])}")
            logger.info(f"   Edge Cases: {len([s for s in self.scenarios if s.test_type == 'edge_case'])}")
            logger.info(f"   Security: {len([s for s in self.scenarios if s.test_type == 'security'])}")
            logger.info(f"   Integration: {len([s for s in self.scenarios if s.is_integration])}")

            # Step 7: Store scenarios in state for next agents
            state.test_scenarios = consolidated

            return AgentOutput(
                agent_name="scenario_designer",
                status=AgentStatus.SUCCESS,
                result={
                    "scenarios": consolidated,
                    "scenario_count": len(self.scenarios),
                    "by_type": {
                        "happy_path": len(
                            [s for s in self.scenarios if s.test_type == "happy_path"]
                        ),
                        "error_case": len(
                            [s for s in self.scenarios if s.test_type == "error_case"]
                        ),
                        "edge_case": len(
                            [s for s in self.scenarios if s.test_type == "edge_case"]
                        ),
                        "security": len(
                            [s for s in self.scenarios if s.test_type == "security"]
                        ),
                        "integration": len(
                            [s for s in self.scenarios if s.is_integration]
                        ),
                    },
                },
                execution_time_ms=elapsed_ms,
            )

        except Exception as e:
            logger.error(f"❌ Scenario Designer failed: {e}")
            logger.error(traceback.format_exc())
            return AgentOutput(
                agent_name="scenario_designer",
                status=AgentStatus.FAILED,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    # ══════════════════════════════════════════════════════════════════════════
    # LOADING CONFIGURATION
    # ══════════════════════════════════════════════════════════════════════════

    def _load_business_requirements(self) -> Optional[Dict[str, Any]]:
        """Load business requirements from YAML file"""
        req_file = Path("business_requirements.yaml")
        if not req_file.exists():
            logger.warning(f"⚠️ {req_file} not found")
            return None

        try:
            with open(req_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading requirements: {e}")
            return None

    def _load_all_swagger_specs(self) -> Dict[str, Dict[str, Any]]:
        """Load all Swagger specs from examples/"""
        specs = {}
        examples_dir = Path("examples")

        if not examples_dir.exists():
            logger.error("❌ examples/ directory not found")
            return specs

        # Load all swagger JSON files
        for swagger_file in examples_dir.glob("sample_swagger*.json"):
            try:
                with open(swagger_file, "r", encoding="utf-8") as f:
                    spec = json.load(f)

                # Extract service name from port
                port = self._extract_port_from_spec(spec)
                service_name = self._map_port_to_service(port)

                if service_name:
                    specs[service_name] = spec
                    logger.info(
                        f"   Loaded {swagger_file.name} → {service_name} (port {port})"
                    )

            except Exception as e:
                logger.warning(f"Error loading {swagger_file}: {e}")

        return specs

    def _extract_port_from_spec(self, spec: Dict[str, Any]) -> Optional[int]:
        """Extract port number from Swagger spec"""
        try:
            servers = spec.get("servers", [])
            if servers:
                url = servers[0].get("url", "")
                match = re.search(r":(\d+)", url)
                if match:
                    return int(match.group(1))
        except Exception:
            pass
        return None

    def _map_port_to_service(self, port: Optional[int]) -> Optional[str]:
        """Map port number to service name"""
        if port is None:
            return None

        # Prefer dynamic mapping from services_matrix.yaml to keep a single source of truth.
        try:
            from tools.service_registry import get_service_registry

            registry = get_service_registry()
            for svc in registry.get_enabled_services():
                try:
                    if int(svc.port) == int(port):
                        return svc.name
                except Exception:
                    continue
        except Exception:
            pass

        # Fallback for legacy setups.
        port_to_service = {
            9000: "auth",
            9001: "leave",
        }
        return port_to_service.get(port)

    def _get_service_requirements(
        self, business_reqs: Dict[str, Any], service_name: str
    ) -> Dict[str, Any]:
        """Extract requirements for a specific service"""
        services = business_reqs.get("SERVICES", [])
        for service in services:
            if service.get("SERVICE_NAME") == service_name:
                return service
        return {}

    def _get_default_requirements(self) -> Dict[str, Any]:
        """Default requirements if YAML not found"""
        return {
            "SERVICES": [
                {
                    "SERVICE_NAME": "auth",
                    "BUSINESS_RULES": [
                        "Users must have valid email",
                        "Passwords must be at least 8 characters",
                    ],
                    "CRITICAL_ENDPOINTS": [
                        "GET /api/users/{id}",
                        "POST /api/users",
                    ],
                },
                {
                    "SERVICE_NAME": "leave",
                    "BUSINESS_RULES": [
                        "Leave dates must be in future",
                        "Cannot have overlapping leaves",
                    ],
                    "CRITICAL_ENDPOINTS": [
                        "POST /api/leave-requests",
                        "PUT /api/leave-requests/{id}/approve",
                    ],
                },
            ]
        }

    def _tokenize(self, text: str) -> List[str]:
        return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]

    def _score_endpoint_for_spec(
        self,
        spec_text: str,
        path: str,
        method: str,
        endpoint_spec: Dict[str, Any],
    ) -> int:
        """
        Score how well a business scenario text matches a Swagger endpoint.
        Higher is better. This avoids the previous cartesian-product behavior
        where every business rule was paired with every endpoint.
        """
        spec_lower = spec_text.lower()
        path_lower = path.lower()
        tokens = set(self._tokenize(spec_text))
        op_id = str(endpoint_spec.get("operationId", "")).lower()
        summary = str(endpoint_spec.get("summary", "")).lower()
        description = str(endpoint_spec.get("description", "")).lower()
        haystack = f"{path_lower} {op_id} {summary} {description}"

        score = 0

        action_map = {
            "create": {"post"},
            "add": {"post"},
            "assign": {"post", "put"},
            "update": {"put", "patch"},
            "approve": {"put", "patch"},
            "reject": {"put", "patch"},
            "delete": {"delete"},
            "cancel": {"delete", "put", "patch"},
            "fetch": {"get"},
            "get": {"get"},
            "retrieve": {"get"},
            "list": {"get"},
            "search": {"get"},
            "view": {"get"},
        }
        for word, methods in action_map.items():
            if word in spec_lower and method.lower() in methods:
                score += 4

        keyword_groups = [
            {"user", "users", "employee", "employees"},
            {"department", "departments"},
            {"role", "roles"},
            {"auth", "login", "token", "jwt"},
            {"leave", "leaves", "request", "requests", "balance", "balances", "holiday", "holidays"},
            {"approve", "approved"},
            {"reject", "rejected"},
            {"cancel", "canceled", "cancelled"},
            {"search"},
        ]
        for group in keyword_groups:
            if tokens & group and any(k in haystack for k in group):
                score += 5

        for token in tokens:
            if len(token) >= 4 and token in haystack:
                score += 1

        if "without" in spec_lower or "non-" in spec_lower or "expired" in spec_lower:
            if any(x in haystack for x in ("auth", "token", "jwt", "role", "permission")):
                score += 2

        return score

    def _choose_best_endpoint(
        self,
        spec_text: str,
        available_endpoints: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for endpoint in available_endpoints:
            score = self._score_endpoint_for_spec(
                spec_text,
                endpoint["path"],
                endpoint["method"],
                endpoint["details"],
            )
            if score > 0:
                scored.append((score, endpoint))

        if not scored:
            return None

        scored.sort(key=lambda item: (-item[0], item[1]["path"], item[1]["method"]))
        return scored[0][1]

    # ══════════════════════════════════════════════════════════════════════════
    # SCENARIO GENERATION
    # ══════════════════════════════════════════════════════════════════════════

    def _generate_service_scenarios(
        self, service_name: str, swagger_spec: Dict[str, Any], requirements: Dict[str, Any]
    ) -> List[TestScenario]:
        """Generate test scenarios for a single service using business rules from YAML"""
        scenarios = []
        paths = swagger_spec.get("paths", {})
        business_rules = requirements.get("BUSINESS_RULES", [])
        critical_endpoints = requirements.get("CRITICAL_ENDPOINTS", [])
        test_scenarios_config = requirements.get("TEST_SCENARIOS", {})

        # Extract YAML-defined test scenarios by type
        happy_path_specs = test_scenarios_config.get("HAPPY_PATH", [])
        error_case_specs = test_scenarios_config.get("ERROR_CASES", [])
        edge_case_specs = test_scenarios_config.get("EDGE_CASES", [])
        security_case_specs = test_scenarios_config.get("SECURITY_CASES", [])

        scenario_counter = 0
        prefix = service_name.upper()[:3]

        available_endpoints: List[Dict[str, Any]] = []
        for path, methods in paths.items():
            for method, endpoint_spec in methods.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue
                if not isinstance(endpoint_spec, dict):
                    endpoint_spec = {}
                available_endpoints.append(
                    {
                        "path": path,
                        "method": method.upper(),
                        "details": endpoint_spec,
                    }
                )

        # Step 1: Generate scenarios for CRITICAL_ENDPOINTS first (high priority),
        # but map each business scenario to its best critical endpoint only.
        critical_endpoint_pool: List[Dict[str, Any]] = []
        for critical_endpoint_spec in critical_endpoints:
            parts = critical_endpoint_spec.split(" - ")
            endpoint_info = parts[0].strip().split()
            if len(endpoint_info) < 2:
                continue

            method = endpoint_info[0].upper()
            path = endpoint_info[1]
            if path not in paths:
                continue

            details = paths.get(path, {}).get(method.lower())
            if not isinstance(details, dict):
                continue
            critical_endpoint_pool.append(
                {
                    "path": path,
                    "method": method,
                    "details": details,
                }
            )

        for happy_spec in happy_path_specs:
            endpoint = self._choose_best_endpoint(happy_spec, critical_endpoint_pool)
            if not endpoint:
                continue
            scenario_counter += 1
            scenarios.append(
                TestScenario(
                    scenario_id=f"{prefix}-{scenario_counter:03d}",
                    title=f"[CRITICAL] {happy_spec}",
                    endpoint=endpoint["path"],
                    method=endpoint["method"],
                    given=f"Preconditions met for: {happy_spec}",
                    when=f"{endpoint['method']} {endpoint['path']} executed per business requirement",
                    then="Returns success response (200/201) and follows business rule",
                    test_type="happy_path",
                    priority="P0",
                    service=service_name,
                )
            )

        # Step 2: Generate ONE best-matched endpoint per YAML scenario instead of
        # pairing every spec with every path.
        for happy_spec in happy_path_specs:
            endpoint = self._choose_best_endpoint(happy_spec, available_endpoints)
            if not endpoint:
                continue
            scenario_counter += 1
            scenarios.append(
                TestScenario(
                    scenario_id=f"{prefix}-{scenario_counter:03d}",
                    title=f"{happy_spec}",
                    endpoint=endpoint["path"],
                    method=endpoint["method"],
                    given=f"Setup for business rule: {happy_spec}",
                    when=f"{endpoint['method']} {endpoint['path']} executed",
                    then=self._generate_assertion_from_business_rules(
                        business_rules, "success"
                    ),
                    test_type="happy_path",
                    priority="P0",
                    service=service_name,
                )
            )

        for error_spec in error_case_specs:
            endpoint = self._choose_best_endpoint(error_spec, available_endpoints)
            if not endpoint:
                continue
            scenario_counter += 1
            scenarios.append(
                TestScenario(
                    scenario_id=f"{prefix}-{scenario_counter:03d}E",
                    title=f"{error_spec}",
                    endpoint=endpoint["path"],
                    method=endpoint["method"],
                    given=f"Precondition for error: {error_spec}",
                    when=f"{endpoint['method']} {endpoint['path']} called with invalid/missing data",
                    then=self._generate_assertion_from_business_rules(
                        business_rules, "error"
                    ),
                    test_type="error_case",
                    priority="P0",
                    service=service_name,
                )
            )

        for edge_spec in edge_case_specs:
            endpoint = self._choose_best_endpoint(edge_spec, available_endpoints)
            if not endpoint:
                continue
            scenario_counter += 1
            scenarios.append(
                TestScenario(
                    scenario_id=f"{prefix}-{scenario_counter:03d}X",
                    title=f"{edge_spec}",
                    endpoint=endpoint["path"],
                    method=endpoint["method"],
                    given=f"Edge case condition: {edge_spec}",
                    when=f"{endpoint['method']} {endpoint['path']} called with boundary/edge values",
                    then="Handles gracefully and returns appropriate status or error",
                    test_type="edge_case",
                    priority="P1",
                    service=service_name,
                )
            )

        for security_spec in security_case_specs:
            endpoint = self._choose_best_endpoint(security_spec, available_endpoints)
            if not endpoint:
                continue
            scenario_counter += 1
            scenarios.append(
                TestScenario(
                    scenario_id=f"{prefix}-{scenario_counter:03d}S",
                    title=f"{security_spec}",
                    endpoint=endpoint["path"],
                    method=endpoint["method"],
                    given=f"Security constraint: {security_spec}",
                    when=f"{endpoint['method']} {endpoint['path']} accessed under security restriction",
                    then=self._generate_security_assertion(security_spec),
                    test_type="security",
                    priority="P0",
                    service=service_name,
                )
            )

        # Step 3: Add small, deterministic coverage anchors for setup-heavy endpoints
        # that unlock deeper stateful flows and branch coverage.
        seen_pairs = {(s.method, s.endpoint) for s in scenarios}
        coverage_anchors: List[Tuple[str, str, str]] = []
        if service_name == "auth":
            coverage_anchors = [
                ("POST", "/api/auth/login", "Authenticate and capture JWT for downstream flows"),
                ("POST", "/api/admin/departments/create", "Create a department for employee provisioning"),
                ("POST", "/api/admin/create-employee", "Create an employee with a valid department"),
                ("GET", "/api/users/search-ids", "Search employee identifiers after creation"),
                ("GET", "/api/users/{id}", "Fetch an existing user by identifier"),
                ("GET", "/api/admin/departments", "List departments after changes"),
            ]
        elif service_name == "leave":
            coverage_anchors = [
                ("POST", "/api/balances/init/{userId}", "Initialize leave balance for the active user"),
                ("PUT", "/api/balances/{userId}", "Update leave balances with valid annual and recovery values"),
                ("GET", "/api/balances/{userId}", "Fetch balances for the active user"),
                ("POST", "/api/leave-requests/create", "Create a leave request with valid dates"),
                ("GET", "/api/leave-requests/search", "Search leave requests with filters"),
                ("PUT", "/api/leave-requests/{id}/approve", "Approve a pending leave request"),
                ("PUT", "/api/leave-requests/{id}/reject", "Reject a pending leave request with a reason"),
                ("PUT", "/api/leave-requests/{id}/cancel", "Cancel an existing leave request"),
                ("GET", "/api/admin/holidays", "List public holidays"),
                ("POST", "/api/admin/holidays", "Create a public holiday entry"),
            ]

        for method, path, title in coverage_anchors:
            if (method, path) in seen_pairs:
                continue
            endpoint_details = paths.get(path, {}).get(method.lower())
            if not endpoint_details:
                continue
            scenario_counter += 1
            scenarios.append(
                TestScenario(
                    scenario_id=f"{prefix}-{scenario_counter:03d}C",
                    title=f"[COVERAGE] {title}",
                    endpoint=path,
                    method=method,
                    given=f"Coverage setup is ready for {service_name}",
                    when=f"{method} {path} executed",
                    then="Returns success response (200/201) and follows business rule",
                    test_type="happy_path",
                    priority="P0",
                    service=service_name,
                )
            )

        return scenarios

    def _generate_integration_scenarios(
        self,
        business_reqs: Dict[str, Any],
        swagger_specs: Dict[str, Any],
    ) -> List[TestScenario]:
        """Generate end-to-end integration scenarios between services using business rules"""
        scenarios = []

        if len(swagger_specs) < 2:
            return scenarios

        integration_scenarios_config = business_reqs.get("INTEGRATION_SCENARIOS", [])
        services = business_reqs.get("SERVICES", [])

        # Extract integration points from leave service
        leave_service = next(
            (s for s in services if s.get("SERVICE_NAME") == "leave"), {}
        )
        integration_with_conge = leave_service.get("INTEGRATION_WITH_CONGE", [])

        for idx, scenario_config in enumerate(integration_scenarios_config, 1):
            title = scenario_config.get("SCENARIO", "Integration Test")
            steps = scenario_config.get("STEPS", [])
            expected = scenario_config.get("EXPECTED_RESULT", "Success")

            # Convert steps to Given/When/Then, extracting meaningful parts
            given_parts = []
            when_parts = []
            then_parts = []

            # First 1-2 steps are preconditions (Given)
            for step in steps[:2]:
                given_parts.append(step.strip("0123456789. "))

            # Middle steps are actions (When)
            for step in steps[2:-1]:
                when_parts.append(step.strip("0123456789. "))

            # Last step or expected result (Then)
            if steps:
                then_parts.append(steps[-1].strip("0123456789. "))

            # Enhance Then with integration validation rules
            then_text = " → ".join(then_parts) if then_parts else expected
            for rule in integration_with_conge[:2]:
                then_text += f" | Verify: {rule}"

            scenarios.append(
                TestScenario(
                    scenario_id=f"E2E-{idx:03d}",
                    title=title,
                    endpoint="INTEGRATION",
                    method="MULTI-STEP",
                    given=" → ".join(given_parts) if given_parts else "Two services initialized",
                    when=" → ".join(when_parts) if when_parts else "Services interact",
                    then=then_text,
                    test_type="integration",
                    priority="P0",
                    service="integration",
                    is_integration=True,
                )
            )

        # Add integration scenarios for each INTEGRATION_WITH_CONGE rule
        for idx, integration_rule in enumerate(integration_with_conge, 1):
            scenario_counter = len(integration_scenarios_config) + idx
            scenarios.append(
                TestScenario(
                    scenario_id=f"E2E-{scenario_counter:03d}",
                    title=f"Integration Rule: {integration_rule}",
                    endpoint="INTEGRATION",
                    method="MULTI-STEP",
                    given="Leave request workflow initiated",
                    when="DemandeConge service calls conge service per business rule",
                    then=f"✓ {integration_rule}",
                    test_type="integration",
                    priority="P0",
                    service="integration",
                    is_integration=True,
                )
            )

        return scenarios

    def _consolidate_scenarios(self, scenarios: List[TestScenario]) -> List[Dict[str, Any]]:
        """Convert scenarios to dictionary format for output"""
        # Sort by priority and type
        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        type_order = {
            "happy_path": 0,
            "error_case": 1,
            "edge_case": 2,
            "security": 3,
            "integration": 4,
        }

        sorted_scenarios = sorted(
            scenarios,
            key=lambda s: (
                priority_order.get(s.priority, 99),
                type_order.get(s.test_type, 99),
            ),
        )

        return [s.to_dict() for s in sorted_scenarios]

    def _generate_assertion_from_business_rules(
        self, business_rules: List[str], context: str
    ) -> str:
        """Generate assertion text based on business rules"""
        if not business_rules:
            return (
                "Returns error response with validation failure"
                if context == "error"
                else "Returns success (200/201) and validates business rule compliance"
            )

        # Pick first relevant rule for assertion
        relevant_rule = business_rules[0] if business_rules else ""

        if context == "success":
            return f"Returns 200/201 and enforces: {relevant_rule}"
        elif context == "error":
            return f"Returns 4xx error when: {relevant_rule} is violated"
        else:
            return f"Validates business rule: {relevant_rule}"

    def _generate_security_assertion(self, security_spec: str) -> str:
        """Generate security assertion based on security scenario"""
        if "401" in security_spec or "Unauthorized" in security_spec:
            return "Returns 401 Unauthorized"
        elif "403" in security_spec or "Forbidden" in security_spec:
            return "Returns 403 Forbidden"
        elif "without JWT" in security_spec or "without token" in security_spec:
            return "Returns 401 when JWT token is missing"
        else:
            return "Returns appropriate authorization error (401/403)"


def scenario_designer_agent_node(state: TestAutomationState) -> TestAutomationState:
    """Workflow node for ScenarioDesignerAgent"""
    agent = ScenarioDesignerAgent()
    output = agent.execute(state)
    state.add_agent_output(output)
    return state
