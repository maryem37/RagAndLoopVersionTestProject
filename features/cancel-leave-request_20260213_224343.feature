Here’s the Gherkin feature file for the **"Cancel Leave Request"** user story, based on the provided context:

Feature: Cancel Leave Request
  As a user
  I want to cancel my leave request
  So that I can withdraw it if it hasn't been processed yet

  Background:
    Given I am a logged-in user with an active leave request



  Scenario: Cancel a pending leave request with an observation
    And I provide an observation "Personal emergency"
    Then the request status changes to "Canceled"
    And the cancellation date is recorded as "{today}"
    And the observation "Personal emergency" is saved in the system


  Scenario: Cancel a leave request under validation with an observation
    And I provide an observation "Miscommunication"
    Then the request status changes to "Canceled"
    And the cancellation date is recorded as "{today}"
    And the observation "Miscommunication" is saved in the system


  Scenario: Cancel a pending leave request without an observation
    When I submit a cancellation request for a leave request with status "Pending"
    Then the request status changes to "Canceled"
    And the cancellation date is recorded as "{today}"
    And no observation is saved in the system


  Scenario: Attempt to cancel a granted leave request
    When I submit a cancellation request for a leave request with status "Granted"
    Then the system rejects the cancellation with an error message "This request cannot be canceled as it has already been approved"
    And the request status remains "Granted"


  Scenario: Attempt to cancel a refused leave request
    When I submit a cancellation request for a leave request with status "Refused"
    Then the system rejects the cancellation with an error message "This request cannot be canceled as it has already been declined"
    And the request status remains "Refused"


  Scenario: Attempt to cancel a previously canceled leave request
    When I submit a cancellation request for a leave request with status "Canceled"
    Then the system rejects the cancellation with an error message "This request is already canceled"
    And the request status remains "Canceled"


  Scenario: Attempt to cancel a leave request with no status (edge case)
    When I submit a cancellation request for a leave request with no status
    Then the system rejects the cancellation with an error message "Invalid request status"
    And the request status remains unchanged
### Notes:
- **`{today}`** is a placeholder for the current date (you may replace it with a dynamic value if needed).
- The **Background** step is optional but helps set up a common context for all scenarios.
- **Edge cases** (like a request with no status) are included for robustness.
- **Error messages** are assumed based on the context; adjust them if your system uses different wording.
