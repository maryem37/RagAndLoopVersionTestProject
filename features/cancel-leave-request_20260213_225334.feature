Here’s the Gherkin feature file for the **"Cancel Leave Request"** user story, based on the provided context:

Feature: Cancel Leave Request
  As a user
  I want to cancel my leave request
  So that I can withdraw it if it hasn't been approved yet

  Background:
    Given the user is logged into the system
    And the leave request system is available



  Scenario: Cancel a pending leave request with an observation
    Given a leave request exists with status "Pending"
    When the user cancels the leave request with observation "Urgent meeting rescheduled"
    Then the request status should change to "Canceled"
    And the cancellation date should be recorded as "{today}"
    And the observation "Urgent meeting rescheduled" should be saved


  Scenario: Cancel a pending leave request without an observation
    Given a leave request exists with status "Pending"
    When the user cancels the leave request without providing an observation
    Then the request status should change to "Canceled"
    And the cancellation date should be recorded as "{today}"
    And no observation should be saved


  Scenario: Attempt to cancel an already granted leave request
    Given a leave request exists with status "Granted"
    When the user tries to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request cannot be canceled as it has already been granted"


  Scenario: Attempt to cancel an already refused leave request
    Given a leave request exists with status "Refused"
    When the user tries to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request cannot be canceled as it has already been refused"


  Scenario: Attempt to cancel an already canceled leave request
    Given a leave request exists with status "Canceled"
    When the user tries to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request cannot be canceled as it has already been canceled"


  Scenario: Attempt to cancel a leave request under validation
    Given a leave request exists with status "Under Validation"
    When the user cancels the leave request with observation "No longer needed"
    Then the request status should change to "Canceled"
    And the cancellation date should be recorded as "{today}"
    And the observation "No longer needed" should be saved
### Notes:
- **`{today}`** is a placeholder for the current date (you may replace it with a Gherkin function like `current_date()` if needed).
- The scenarios cover all valid and invalid cases based on the business rules.
- Error messages are included for invalid cancellation attempts.
