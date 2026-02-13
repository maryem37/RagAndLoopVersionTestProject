Here’s the Gherkin feature file for the **"Cancel Leave Request"** user story, following the given context and best practices for BDD scenarios:

Feature: Cancel Leave Request
  As a user
  I want to cancel my leave request
  So that I can withdraw my request if it hasn't been processed yet

  Background:
    Given the system is logged in as a user with an active leave request



  Scenario: Cancel a pending leave request with an observation
    When the user cancels their leave request with an observation "Medical emergency"
    Then the request status should be "Canceled"
    And the cancellation date should be recorded as {today}
    And the observation "Medical emergency" should be saved in the system


  Scenario: Cancel a pending leave request without an observation
    When the user cancels their leave request without providing an observation
    Then the request status should be "Canceled"
    And the cancellation date should be recorded as {today}
    And no observation should be saved in the system


  Scenario: Attempt to cancel an already granted leave request
    Given a leave request that has been granted
    When the user tries to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request has already been granted and cannot be canceled"


  Scenario: Attempt to cancel a refused leave request
    Given a leave request that has been refused
    When the user tries to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request has been refused and cannot be canceled"


  Scenario: Attempt to cancel a leave request that is already canceled
    Given a leave request that has been canceled
    When the user tries to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request is already canceled and cannot be modified"


  Scenario: Attempt to cancel a leave request that is under validation
    Given a leave request that is under validation
    When the user cancels their leave request with an observation "Changed plans"
    Then the request status should be "Canceled"
    And the cancellation date should be recorded as {today}
    And the observation "Changed plans" should be saved in the system
### Notes:
1. **`{today}`** is a placeholder for the current date (resolved dynamically when the scenario runs).
2. **Error messages** are included for refused/granted/canceled states to reflect system behavior.
3. **Assumptions**:
   - The user has a valid leave request in the system (covered in `Background`).
   - "Under validation" is treated as a cancellable state (like "pending").
   - Adjust placeholders (e.g., `{today}`) or error messages based on your actual system requirements.
