Here’s the Gherkin feature file for the **"Cancel Leave Request"** user story, based on the provided context:

Feature: Cancel Leave Request
  As a user
  In order to manage my leave requests
  I want to cancel a leave request that is pending or under validation

  Background:
    Given the system is logged in as a user with valid permissions
    And a leave request exists with one of the following statuses: "Pending", "Under Validation"



  Scenario: Cancel a pending leave request without observations
    When the user attempts to cancel a leave request with status "Pending"
    Then the request status should change to "Canceled"
    And the cancellation date should be recorded
    And no observation should be stored


  Scenario: Cancel a leave request under validation with observations
    When the user attempts to cancel a leave request with status "Under Validation" and provides an observation "Family emergency"
    Then the request status should change to "Canceled"
    And the cancellation date should be recorded
    And the observation "Family emergency" should be stored


  Scenario: Attempt to cancel a granted leave request
    Given a leave request exists with status "Granted"
    When the user attempts to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request cannot be canceled as it has already been granted"


  Scenario: Attempt to cancel a refused leave request
    Given a leave request exists with status "Refused"
    When the user attempts to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request cannot be canceled as it has already been refused"


  Scenario: Attempt to cancel a passed leave request
    Given a leave request exists with status "Passed"
    When the user attempts to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request cannot be canceled as it has already been processed"


  Scenario: Attempt to cancel an already canceled leave request
    Given a leave request exists with status "Canceled"
    When the user attempts to cancel the leave request
    Then the system should prevent cancellation
    And display an error message "This request cannot be canceled as it has already been canceled"
### Notes:
- **Background**: Assumes the user is logged in with valid permissions (adjust if needed).
- **Scenarios**:
  - **Happy Path**: Two valid cancellation cases (with and without observations).
  - **Edge Cases**: Attempts to cancel requests in invalid states (`Granted`, `Refused`, `Passed`, `Canceled`).
- **Assumptions**:
  - "Under Validation" is treated as a cancellable state (like "Pending").
  - Error messages are displayed to the user (adjust based on actual UI/UX requirements).
  - The cancellation date is auto-recorded by the system.
