
if __name__ == "__main__":
    from rich import print as rprint
    import uuid
    
    # Test validation
    test_state = TestAutomationState(
        workflow_id=str(uuid.uuid4()),
        service_name="test",
        user_story="Test story",
        gherkin_content="Feature: Test\n  Scenario: Test\n    Given test",
        gherkin_files=[]
    )
    
    agent = GherkinValidatorAgent()
    result = agent.validate(test_state)
    
    rprint("[CHART] Validation Result:")
    if result.validation_result:
        rprint(f"Valid: {result.validation_result.is_valid}")
        rprint(f"Coverage: {result.validation_result.coverage_score}%")