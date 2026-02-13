Here’s the user story converted into Gherkin syntax, following the given context and business rules:

Feature: Cancel Leave Request

  Background:
    Given the system is logged in as a user with valid permissions to manage leave requests



  Scenario: Cancel a pending leave request
    Given a leave request is in "Pending" status
    When the user cancels the leave request with an optional observation "Family emergency"
    Then the request status should change to "Canceled"
    And the cancellation date should be recorded as {today}
    And the observation "Family emergency" should be saved in the system


  Scenario: Cancel a leave request under validation
    Given a leave request is in "Under Validation" status
    When the user cancels the leave request with an optional observation "Changed plans"
    Then the request status should change to "Canceled"
    And the cancellation date should be recorded as {today}
    And the observation "Changed plans" should be saved in the system


  Scenario: Attempt to cancel a granted leave request
    Given a leave request is in "Granted" status
    When the user tries to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request cannot be canceled as it has already been granted"


  Scenario: Attempt to cancel a refused leave request
    Given a leave request is in "Refused" status
    When the user tries to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request cannot be canceled as it has already been refused"


  Scenario: Attempt to cancel an already canceled leave request
    Given a leave request is in "Canceled" status
    When the user tries to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request cannot be canceled as it has already been canceled"


  Scenario: Cancel a leave request without providing an observation
    Given a leave request is in "Pending" status
    When the user cancels the leave request without providing an observation
    Then the request status should change to "Canceled"
    And the cancellation date should be recorded as {today}
    And no observation should be saved in the system
### Notes:
- `{today}` is a placeholder for the current date (you can replace it with a specific date or use a Gherkin timestamp if needed).
- The scenarios cover all valid and invalid cases based on the business rules provided.
- Error messages are included for invalid cancellation attempts.
