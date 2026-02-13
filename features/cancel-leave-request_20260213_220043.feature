Here’s the Gherkin feature file for the **"Cancel Leave Request"** user story, following the given context and best practices for scenario structure:

Feature: Cancel Leave Request
  As a user
  I want to cancel my leave request
  So that I can withdraw it if it hasn't been processed yet

  Background:
    Given the system is logged in as a valid user
    And the user has submitted a leave request



  Scenario: Cancel a pending leave request without observation
    When the user attempts to cancel a leave request with status "Pending"
    Then the system allows cancellation
    And the request status changes to "Canceled"
    And the cancellation date is recorded


  Scenario: Cancel a leave request under validation without observation
    When the user attempts to cancel a leave request with status "Under Validation"
    Then the system allows cancellation
    And the request status changes to "Canceled"
    And the cancellation date is recorded


  Scenario: Cancel a pending leave request with an observation
    And provides an observation "Need to reschedule due to urgent work"
    Then the system allows cancellation
    And the request status changes to "Canceled"
    And the cancellation date is recorded
    And the observation is saved with the request


  Scenario: Attempt to cancel a granted leave request
    When the user attempts to cancel a leave request with status "Granted"
    Then the system prevents cancellation
    And displays an error message "This request cannot be canceled as it has already been approved"


  Scenario: Attempt to cancel a refused leave request
    When the user attempts to cancel a leave request with status "Refused"
    Then the system prevents cancellation
    And displays an error message "This request cannot be canceled as it has been rejected"


  Scenario: Attempt to cancel a canceled leave request
    When the user attempts to cancel a leave request with status "Canceled"
    Then the system prevents cancellation
    And displays an error message "This request cannot be canceled as it is already canceled"


  Scenario: Attempt to cancel a leave request with no status (edge case)
    When the user attempts to cancel a leave request with no defined status
    Then the system prevents cancellation
    And displays an error message "Invalid request status"
### Key Notes:
1. **Statuses Covered**:
   - Only `Pending` and `Under Validation` can be canceled (as per business rules).
   - `Granted`, `Refused`, and `Canceled` are explicitly blocked.

2. **Observation Handling**:
   - Optional observation is included in one scenario (with validation).

3. **Edge Cases**:
   - Added a scenario for an undefined status (though unlikely in practice).

4. **Assumptions**:
   - The system enforces status checks before allowing cancellation.
   - Error messages are displayed for invalid actions (customize as needed).
