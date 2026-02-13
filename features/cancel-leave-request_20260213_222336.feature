Here’s the Gherkin feature file for the **"Cancel Leave Request"** user story, structured with clear scenarios covering the business rules:

Feature: Cancel Leave Request
  As a user
  I want to cancel my leave request
  So that I can withdraw it if it hasn't been processed yet

  Background:
    Given I have submitted a leave request with status "Pending" or "Under Validation"
    And I am logged into the system with appropriate permissions



  Scenario: Cancel a pending leave request
    When I attempt to cancel my leave request with status "Pending"
    Then the system should allow cancellation
    And the request status should change to "Canceled"
    And the cancellation date should be recorded
    And the observation field should be updated (if provided)


  Scenario: Cancel a leave request under validation
    When I attempt to cancel my leave request with status "Under Validation"
    Then the system should allow cancellation
    And the request status should change to "Canceled"
    And the cancellation date should be recorded
    And the observation field should be updated (if provided)


  Scenario: Attempt to cancel a granted leave request
    When I attempt to cancel my leave request with status "Granted"
    Then the system should reject the cancellation
    And display an error message: "This request cannot be canceled as it has already been granted"


  Scenario: Attempt to cancel a refused leave request
    When I attempt to cancel my leave request with status "Refused"
    Then the system should reject the cancellation
    And display an error message: "This request cannot be canceled as it has been refused"


  Scenario: Attempt to cancel a leave request already marked as canceled
    When I attempt to cancel my leave request with status "Canceled"
    Then the system should reject the cancellation
    And display an error message: "This request cannot be canceled as it has already been canceled"


  Scenario: Cancel a leave request with an observation
    Given my leave request has status "Pending"
    When I cancel the request and provide an observation "I am unwell"
    Then the request status should change to "Canceled"
    And the cancellation date should be recorded
    And the observation field should reflect "I am unwell"


  Scenario: Cancel a leave request without an observation
    Given my leave request has status "Under Validation"
   Given the API endpoint for cancellation is "/leave-requests/{id}/cancel"
   And the request payload includes:
    When I cancel the request without providing an observation
    Then the request status should change to "Canceled"
    And the cancellation date should be recorded
    And the observation field should remain empty
### Notes:
1. **Assumptions**:
   - The system has a clear way to identify request statuses (e.g., via API or UI).
   - The user is authenticated and has permission to cancel requests.
   - The observation field is optional but must be recorded if provided.

2. **Edge Cases Covered**:
   - Pending/Under Validation → Allowed (with/without observation).
   - Granted/Refused/Canceled → Rejected with appropriate feedback.

3. **Swagger Context**:
   If there are specific API endpoints or payloads (e.g., `PATCH /leave-requests/{id}/cancel`), you can add a `Background` or `Given` step like:
   """
     {
       "status": "Canceled",
       "cancellationDate": "YYYY-MM-DD",
       "observation": "Optional text"
     }
     """
