Here’s the user story converted into valid Gherkin syntax, structured as a **Feature** with multiple **Scenario** examples covering the business rules for canceling a leave request:

Feature: Cancel Leave Request
  As a user
  I want to cancel my leave request
  So that I can adjust my plans if the request hasn't been approved yet

  Background:
    Given I am logged into the leave management system
    And I have submitted a leave request



  Scenario: Cancel a pending leave request with an observation
    And I provide an observation "Urgent work came up"
    Then the request status changes to "Canceled"
    And the cancellation date is recorded as "{today}"
    And the observation "Urgent work came up" is saved in the system


  Scenario: Cancel a leave request under validation with no observation
    And I do not provide an observation
    Then the request status changes to "Canceled"
    And the cancellation date is recorded as "{today}"
    And no observation is saved in the system


  Scenario: Attempt to cancel a granted leave request
    When I attempt to cancel my leave request with status "Granted"
    Then I receive an error message "This request cannot be canceled as it has already been approved"
    And the request status remains "Granted"


  Scenario: Attempt to cancel a refused leave request
    When I attempt to cancel my leave request with status "Refused"
    Then I receive an error message "This request cannot be canceled as it has been rejected"
    And the request status remains "Refused"


  Scenario: Attempt to cancel a canceled leave request
    When I attempt to cancel my leave request with status "Canceled"
    Then I receive an error message "This request cannot be canceled as it has already been canceled"
    And the request status remains "Canceled"


  Scenario: Attempt to cancel a leave request with no status (edge case)
    When I attempt to cancel my leave request with no status assigned
    Then I receive an error message "Invalid request status: cannot cancel a request without a defined status"
    And the request status remains unchanged
### Notes:
1. **`{today}`** is a placeholder for the current date (resolved dynamically by tools if needed).
2. Scenarios cover:
   - Valid cancellation (pending/under validation) with/without observation.
   - Invalid cancellation attempts (granted/refused/canceled).
   - Edge case (no status).
3. Assumes the system returns clear error messages for invalid actions. Adjust phrasing if needed.
4. No Swagger context was provided, so the scenarios focus purely on the business rules.
