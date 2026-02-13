Here’s the user story converted into Gherkin syntax, following the given context and business rules:

Feature: Cancel Leave Request
  As a user
  I want to cancel my leave request
  So that I can withdraw my request if it hasn't been processed yet

  Background:
    Given the system is logged in as a user with an active leave request



  Scenario: Cancel a pending leave request
    Given a leave request exists with status "Pending"
    When the user cancels the leave request with observation "Personal reasons"
    Then the leave request status should change to "Canceled"
    And the cancellation date should be recorded
    And the observation "Personal reasons" should be saved with the cancellation


  Scenario: Cancel a leave request under validation
    Given a leave request exists with status "Under Validation"
    When the user cancels the leave request without providing an observation
    Then the leave request status should change to "Canceled"
    And the cancellation date should be recorded
    And the observation field should remain empty


  Scenario: Attempt to cancel a granted leave request
    Given a leave request exists with status "Granted"
    When the user tries to cancel the leave request
    Then the system should reject the cancellation attempt
    And display an error message "This request cannot be canceled as it has already been granted"


  Scenario: Attempt to cancel a refused leave request
    Given a leave request exists with status "Refused"
    When the user tries to cancel the leave request
    Then the system should reject the cancellation attempt
    And display an error message "This request cannot be canceled as it has already been refused"


  Scenario: Attempt to cancel a canceled leave request
    Given a leave request exists with status "Canceled"
    When the user tries to cancel the leave request
    Then the system should reject the cancellation attempt
    And display an error message "This request cannot be canceled as it has already been canceled"


  Scenario: Attempt to cancel a leave request that is passed
    Given a leave request exists with status "Passed"
    When the user tries to cancel the leave request
    Then the system should reject the cancellation attempt
    And display an error message "This request cannot be canceled as it has already been processed"
### Notes:
- The **Background** is optional but helps set up common preconditions for the scenarios.
- **Scenarios** cover both valid and invalid cases based on the business rules.
- **Then** steps include the expected system behavior (status change, date recording, or error message).
