Here’s the Gherkin feature file for the **"Cancel Leave Request"** user story, based on the provided context:

Feature: Cancel Leave Request
  As a user
  I want to cancel my leave request
  So that I can withdraw it if it hasn't been processed yet

  Background:
    Given I am logged into the system with valid credentials



  Scenario: Cancel a pending leave request
    And I provide an optional observation "Personal emergency"
    Then I should see a "Cancel Request" option
    Then the leave request status should change to "Canceled"
    And the cancellation date should be recorded as "{today}"
    And the observation "Personal emergency" should be saved
    And I should receive a confirmation message "Leave request canceled successfully"


  Scenario: Cancel a leave request under validation
    And I provide an optional observation "No longer needed"
    Then I should see a "Cancel Request" option
    Then the leave request status should change to "Canceled"
    And the cancellation date should be recorded as "{today}"
    And the observation "No longer needed" should be saved
    And I should receive a confirmation message "Leave request canceled successfully"


  Scenario: Attempt to cancel a granted leave request
    And I select the leave request to cancel
    Then I should not see a "Cancel Request" option
    And I should receive an error message "This leave request cannot be canceled as it has already been granted"


  Scenario: Attempt to cancel a refused leave request
    And I select the leave request to cancel
    Then I should not see a "Cancel Request" option
    And I should receive an error message "This leave request cannot be canceled as it has already been refused"


  Scenario: Attempt to cancel a leave request that was previously canceled
    And I select the leave request to cancel
    Then I should not see a "Cancel Request" option
    And I should receive an error message "This leave request cannot be canceled as it has already been canceled"


  Scenario: Cancel a leave request without providing an observation
    When I click "Cancel Request" without providing an observation
    Then I should see a "Cancel Request" option
    Then the leave request status should change to "Canceled"
    And the cancellation date should be recorded as "{today}"
    And no observation should be saved
    And I should receive a confirmation message "Leave request canceled successfully"
### Notes:
1. **Statuses**: The scenarios cover all valid and invalid states (`Pending`, `Under Validation`, `Granted`, `Refused`, `Canceled`).
2. **Observation Handling**: Optional observation is included in valid cancellation cases but omitted in invalid ones.
3. **Date Recording**: Uses `{today}` as a placeholder (replace with actual date logic if needed).
4. **Error Messages**: Explicitly defined for invalid cancellation attempts.
5. **Assumptions**:
   - The system has a UI for managing leave requests.
   - The user is logged in (covered in `Background`).
   - Adjust step phrasing (e.g., "submit a leave request") based on your actual system workflow.
