"""
LangGraph Workflow for Multi-Agent Test Automation
Orchestrates all agents in the test automation pipeline with CONTRACT-LEVEL testing philosophy
"""

from typing import Literal
from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import TestAutomationState, AgentStatus
from agents.gherkin_generator import gherkin_generator_node
from agents.gherkin_validator import gherkin_validator_node
from agents.test_writer import test_writer_node


class TestAutomationWorkflow:
    """
    Main workflow orchestrating all test automation agents using LangGraph
    
    WORKFLOW PHILOSOPHY:
    1. Generate Gherkin scenarios from user stories
    2. Validate Gherkin quality and coverage
    3. Generate CONTRACT-LEVEL E2E tests (NOT business logic tests)
    """
    
    def __init__(self):
        """Initialize the workflow with memory checkpointing"""
        # CRITICAL: Initialize memory BEFORE building graph
        self.memory = MemorySaver()
        
        # Build the graph (this uses self.memory)
        self.graph = self._build_graph()
        
        logger.info("✅ Test Automation Workflow initialized")
        logger.info("📋 Test Type: CONTRACT-LEVEL E2E (API Structure & Interoperability)")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow graph
        
        Flow:
        1. Gherkin Generator → Convert user stories to Gherkin
        2. Gherkin Validator → Validate generated scenarios
        3. Contract-Level Test Writer → Generate executable API contract tests
        
        Future Extensions:
        4. Test Executor → Run tests
        5. Coverage Analyst → Measure coverage
        6. Self-Healing → Fix failures
        """
        
        # Create workflow
        workflow = StateGraph(TestAutomationState)
        
        # Add nodes
        workflow.add_node("gherkin_generator", gherkin_generator_node)
        workflow.add_node("gherkin_validator", gherkin_validator_node)
        workflow.add_node("test_writer", test_writer_node)
        
        # Define entry point
        workflow.set_entry_point("gherkin_generator")
        
        # Add edges with conditional routing
        workflow.add_conditional_edges(
            "gherkin_generator",
            self._should_continue_after_generation,
            {
                "validate": "gherkin_validator",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "gherkin_validator",
            self._should_continue_after_validation,
            {
                "write_tests": "test_writer",
                "end": END
            }
        )
        
        workflow.add_edge("test_writer", END)
        
        logger.info("📊 Workflow graph built successfully")
        logger.info("   Nodes: gherkin_generator → gherkin_validator → test_writer")
        
        # Compile with memory checkpointing
        return workflow.compile(checkpointer=self.memory)
    
    def _should_continue_after_generation(self, state: TestAutomationState) -> Literal["validate", "end"]:
        """
        Decide whether to continue to validation after Gherkin generation
        """
        # Check if generation was successful
        last_output = state.agent_outputs[-1] if state.agent_outputs else None
        
        if last_output and last_output.status == AgentStatus.SUCCESS:
            if state.gherkin_content and state.gherkin_files:
                logger.info("✓ Gherkin generation successful → Proceeding to validation")
                return "validate"
            else:
                logger.warning("✗ No Gherkin content generated → Ending workflow")
                return "end"
        
        logger.warning("✗ Gherkin generation failed → Ending workflow")
        return "end"
    
    def _should_continue_after_validation(self, state: TestAutomationState) -> Literal["write_tests", "end"]:
        """
        Decide whether to continue to test writing after validation
        
        IMPORTANT: Contract tests may have warnings (e.g., missing business scenarios)
        but we proceed if there are no critical errors
        """
        # Check validation result
        if state.validation_result:
            if state.validation_result.is_valid:
                logger.info("✓ Validation passed → Proceeding to contract-level test writing")
                return "write_tests"
            else:
                # Count errors vs warnings
                errors = sum(1 for issue in state.validation_result.issues if issue.level == "error")
                warnings = sum(1 for issue in state.validation_result.issues if issue.level == "warning")
                
                logger.warning(f"⚠ Validation issues found: {errors} errors, {warnings} warnings")
                
                # Only proceed if no critical errors
                if errors == 0:
                    logger.info("✓ No critical errors → Proceeding to contract-level test writing")
                    logger.info("   (Warnings are acceptable for contract tests)")
                    return "write_tests"
                else:
                    logger.error("✗ Critical validation errors → Ending workflow")
                    logger.error("   Fix Gherkin syntax errors before generating tests")
                    return "end"
        
        logger.warning("✗ No validation result → Ending workflow")
        return "end"
    
    def run(
        self,
        user_story: str,
        service_name: str,
        swagger_spec: dict = None,
        swagger_specs: dict = None,
        config: dict = None
    ) -> TestAutomationState:
        """
        Run the complete test automation workflow
        
        Args:
            user_story: User story or functional specification
            service_name: Name of the service being tested
            swagger_spec: Single Swagger/OpenAPI specification (for backward compatibility)
            swagger_specs: Multiple Swagger specifications (recommended for multi-service)
            config: Additional configuration (optional)
        
        Returns:
            Final state with all generated artifacts
        
        Example:
            >>> workflow = TestAutomationWorkflow()
            >>> state = workflow.run(
            ...     user_story=story_text,
            ...     service_name="leave-request",
            ...     swagger_specs={
            ...         "auth": auth_swagger,
            ...         "leave": leave_swagger
            ...     }
            ... )
        """
        import uuid
        from datetime import datetime
        
        logger.info("=" * 80)
        logger.info(f"🚀 Starting CONTRACT-LEVEL Test Automation Workflow")
        logger.info(f"   Service: {service_name}")
        logger.info(f"   Test Type: Contract-Level E2E (API Structure Validation)")
        logger.info("=" * 80)
        
        # Generate workflow ID
        workflow_id = f"{service_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # Prepare Swagger specs
        # Priority: swagger_specs (multi-service) > swagger_spec (single)
        final_swagger_specs = swagger_specs or {}
        
        # Backward compatibility: if only swagger_spec provided, use it
        if not final_swagger_specs and swagger_spec:
            final_swagger_specs = {"primary": swagger_spec}
            logger.info("   Using single Swagger spec (legacy mode)")
        
        if final_swagger_specs:
            logger.info(f"   Swagger specs: {len(final_swagger_specs)} service(s)")
            for service_key in final_swagger_specs.keys():
                logger.info(f"      - {service_key}")
        else:
            logger.warning("   ⚠️ No Swagger specs provided - tests may be incomplete")
        
        # Initialize state
        initial_state = TestAutomationState(
            workflow_id=workflow_id,
            user_story=user_story,
            service_name=service_name,
            swagger_spec=swagger_spec or {},  # For gherkin_generator compatibility
            swagger_specs=final_swagger_specs,  # For test_writer
            config=config or {}
        )
        
        # Run workflow
        try:
            # Execute the graph
            logger.info("\n🎯 Executing workflow...")
            result = self.graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": service_name}}
            )
            
            # LangGraph returns a dict, convert back to TestAutomationState
            if isinstance(result, dict):
                final_state = TestAutomationState(**result)
            else:
                final_state = result
            
            # Update workflow status
            if final_state.errors:
                final_state.workflow_status = "failed"
            else:
                final_state.workflow_status = "completed"
            
            # Log summary
            self._log_workflow_summary(final_state)
            
            return final_state
            
        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            raise
    
    def _log_workflow_summary(self, state: TestAutomationState):
        """Log a comprehensive summary of the workflow execution"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 WORKFLOW EXECUTION SUMMARY")
        logger.info("=" * 80)
        
        # Basic info
        logger.info(f"Workflow ID: {state.workflow_id}")
        logger.info(f"Service: {state.service_name}")
        logger.info(f"Status: {state.workflow_status.upper()}")
        
        # Agent execution summary
        logger.info(f"\n📋 Agent Execution:")
        total_duration = 0
        for output in state.agent_outputs:
            status_icon = "✓" if output.status == AgentStatus.SUCCESS else "✗"
            duration = output.duration_ms or 0
            total_duration += duration
            
            logger.info(f"  {status_icon} {output.agent_name}")
            logger.info(f"      Status: {output.status}")
            logger.info(f"      Duration: {duration:.0f}ms")
            
            # Show key metrics
            if output.output_data:
                if output.agent_name == "gherkin_generator":
                    logger.info(f"      Features: {output.output_data.get('features_generated', 0)}")
                    logger.info(f"      Files: {output.output_data.get('feature_files', [])}")
                elif output.agent_name == "gherkin_validator":
                    logger.info(f"      Valid: {output.output_data.get('is_valid', False)}")
                    logger.info(f"      Coverage: {output.output_data.get('coverage_score', 0)}%")
                    logger.info(f"      Issues: {output.output_data.get('total_issues', 0)}")
                elif output.agent_name == "test_writer":
                    logger.info(f"      Test Type: {output.output_data.get('test_type', 'N/A')}")
                    logger.info(f"      Files: {output.output_data.get('files_generated', 0)}")
                    logger.info(f"      Critical Violations: {output.output_data.get('critical_violations', 0)}")
        
        logger.info(f"\nTotal Duration: {total_duration:.0f}ms ({total_duration/1000:.1f}s)")
        
        # Artifacts generated
        logger.info(f"\n📁 Generated Artifacts:")
        logger.info(f"  Gherkin files: {len(state.gherkin_files)}")
        for gherkin_file in state.gherkin_files:
            logger.info(f"    - {gherkin_file}")
        
        logger.info(f"  Test files: {len(state.test_files)}")
        for test_file in state.test_files:
            logger.info(f"    - {test_file}")
        
        # Validation summary
        if state.validation_result:
            logger.info(f"\n✅ Validation Results:")
            logger.info(f"  Valid: {state.validation_result.is_valid}")
            logger.info(f"  Coverage Score: {state.validation_result.coverage_score}%")
            
            errors = [i for i in state.validation_result.issues if i.level == "error"]
            warnings = [i for i in state.validation_result.issues if i.level == "warning"]
            
            logger.info(f"  Errors: {len(errors)}")
            logger.info(f"  Warnings: {len(warnings)}")
            
            if state.validation_result.missing_scenarios:
                logger.info(f"  Missing Scenarios: {len(state.validation_result.missing_scenarios)}")
                for scenario in state.validation_result.missing_scenarios[:3]:
                    logger.info(f"    - {scenario}")
                if len(state.validation_result.missing_scenarios) > 3:
                    logger.info(f"    ... and {len(state.validation_result.missing_scenarios) - 3} more")
        
        # Test code summary
        if state.test_code:
            logger.info(f"\n🧪 Test Code Generated:")
            for code_type, code_content in state.test_code.items():
                lines = len(code_content.splitlines())
                logger.info(f"  {code_type}: {lines} lines")
        
        # Errors and warnings
        if state.errors:
            logger.info(f"\n❌ Errors ({len(state.errors)}):")
            for error in state.errors:
                logger.error(f"  - {error}")
        
        if state.warnings:
            logger.info(f"\n⚠️ Warnings ({len(state.warnings)}):")
            for warning in state.warnings[:5]:  # Show first 5
                logger.warning(f"  - {warning}")
            if len(state.warnings) > 5:
                logger.info(f"  ... and {len(state.warnings) - 5} more")
        
        # Final status
        logger.info("\n" + "=" * 80)
        if state.errors:
            logger.error("❌ WORKFLOW COMPLETED WITH ERRORS")
            logger.error("   Fix the errors above and retry")
        elif state.warnings:
            logger.warning("⚠️ WORKFLOW COMPLETED WITH WARNINGS")
            logger.info("   Review warnings - tests may need manual refinement")
        else:
            logger.success("✅ WORKFLOW COMPLETED SUCCESSFULLY")
            logger.success("   CONTRACT-LEVEL E2E tests are ready!")
        
        logger.info("=" * 80 + "\n")
        
        # Next steps
        if state.test_files:
            logger.info("📋 Next Steps:")
            logger.info("   1. Review generated test files")
            logger.info("   2. Set TEST_JWT_TOKEN environment variable")
            logger.info("   3. Configure test data in your test environment")
            logger.info("   4. Run: mvn test -Dtest=ContractTestRunner")
            logger.info("   5. Review CONTRACT_TEST_SETUP.md for details\n")
    
    async def arun(
        self,
        user_story: str,
        service_name: str,
        swagger_spec: dict = None,
        swagger_specs: dict = None,
        config: dict = None
    ) -> TestAutomationState:
        """
        Async version of run() for concurrent execution
        
        Args:
            user_story: User story or functional specification
            service_name: Name of the service being tested
            swagger_spec: Single Swagger/OpenAPI specification (optional)
            swagger_specs: Multiple Swagger specifications (recommended)
            config: Additional configuration (optional)
        
        Returns:
            Final state with all generated artifacts
        """
        import uuid
        from datetime import datetime
        
        logger.info("=" * 80)
        logger.info(f"🚀 Starting ASYNC CONTRACT-LEVEL Test Automation Workflow")
        logger.info(f"   Service: {service_name}")
        logger.info("=" * 80)
        
        # Generate workflow ID
        workflow_id = f"{service_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # Prepare Swagger specs
        final_swagger_specs = swagger_specs or {}
        if not final_swagger_specs and swagger_spec:
            final_swagger_specs = {"primary": swagger_spec}
        
        # Initialize state
        initial_state = TestAutomationState(
            workflow_id=workflow_id,
            user_story=user_story,
            service_name=service_name,
            swagger_spec=swagger_spec or {},
            swagger_specs=final_swagger_specs,
            config=config or {}
        )
        
        # Run workflow asynchronously
        try:
            # Execute the graph
            result = await self.graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": service_name}}
            )
            
            # LangGraph returns a dict, convert back to TestAutomationState
            if isinstance(result, dict):
                final_state = TestAutomationState(**result)
            else:
                final_state = result
            
            # Update workflow status
            if final_state.errors:
                final_state.workflow_status = "failed"
            else:
                final_state.workflow_status = "completed"
            
            # Log summary
            self._log_workflow_summary(final_state)
            
            return final_state
            
        except Exception as e:
            logger.error(f"❌ Async workflow execution failed: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            raise
    
    def get_workflow_state(self, thread_id: str) -> TestAutomationState:
        """
        Retrieve the current state of a workflow by thread ID
        
        Args:
            thread_id: The thread ID (usually service_name)
        
        Returns:
            Current workflow state
        """
        try:
            # Get state from memory checkpoint
            config = {"configurable": {"thread_id": thread_id}}
            state_snapshot = self.graph.get_state(config)
            
            if state_snapshot and state_snapshot.values:
                return TestAutomationState(**state_snapshot.values)
            else:
                logger.warning(f"No state found for thread_id: {thread_id}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving workflow state: {e}")
            return None


def create_workflow() -> TestAutomationWorkflow:
    """
    Factory function to create a new workflow instance
    
    Returns:
        Configured TestAutomationWorkflow
    
    Example:
        >>> workflow = create_workflow()
        >>> result = workflow.run(
        ...     user_story="...",
        ...     service_name="my-service",
        ...     swagger_specs={"auth": {...}, "api": {...}}
        ... )
    """
    return TestAutomationWorkflow()


# For direct execution testing
if __name__ == "__main__":
    import json
    from pathlib import Path
    
    # Example usage
    logger.info("Testing workflow creation...")
    
    workflow = create_workflow()
    
    # Load example data
    examples_dir = Path(__file__).parent.parent / "examples"
    
    # Load user story
    user_story_path = examples_dir / "sample_user_story.md"
    if user_story_path.exists():
        user_story = user_story_path.read_text(encoding="utf-8")
    else:
        user_story = """
User Story: Employee Leave Request

As an employee
I want to submit leave requests through the API
So that I can manage my time off programmatically

Acceptance Criteria:
- AC1: Employee can submit leave request with start date, end date, and leave type
- AC2: System validates leave balance exists (API returns balance field)
- AC3: System returns request ID and status in response

Business Rules:
- BR1: API must return 200 OK for valid requests
- BR2: API must return request status field
- BR3: API response must include request ID
"""
    
    # Load Swagger specs
    swagger_spec1_path = examples_dir / "sample_swagger1.json"
    swagger_spec2_path = examples_dir / "sample_swagger2.json"
    
    swagger_specs = {}
    
    if swagger_spec1_path.exists():
        with open(swagger_spec1_path, 'r', encoding="utf-8") as f:
            swagger_specs["auth"] = json.load(f)
    
    if swagger_spec2_path.exists():
        with open(swagger_spec2_path, 'r', encoding="utf-8") as f:
            swagger_specs["leave"] = json.load(f)
    
    # Run workflow
    logger.info("Running test workflow...")
    
    try:
        final_state = workflow.run(
            user_story=user_story,
            service_name="leave-request-service",
            swagger_specs=swagger_specs
        )
        
        logger.success("✅ Workflow test completed successfully!")
        
        # Show summary
        summary = final_state.get_workflow_summary()
        logger.info("\n📊 Summary:")
        for key, value in summary.items():
            logger.info(f"  {key}: {value}")
        
    except Exception as e:
        logger.error(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()