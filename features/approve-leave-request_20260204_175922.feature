Feature: Approve Leave Request

  Background:
    Given the employee is authenticated
    And required reference data exists
    And at least one leave type is available
    And the user is an administrator or team lead
    And a leave request with valid state ("Pending" or "In Progress") and appropriate approval chain exists



  Scenario: Approve Leave Request - Happy Path
    Given the user navigates to the leave request page
    When the user clicks "Approve"
    Then the status changes to "In Progress" for the manager
    And the system marks the manager's validation as TRUE
    And the system displays "Request granted successfully"


  Scenario: Approve Leave Request - Not Authorized
    Given the user navigates to the leave request page
    When the user selects a leave request not in their approval chain
    Then the system displays "You are not authorized to modify the status of this request."


  Scenario: Approve Leave Request - Invalid State
    Given the user navigates to the leave request page
    When the user selects a leave request with an invalid state (not "Pending" or "In Progress")
    Then the validation is blocked and the system displays "This request cannot be approved at this time."


  Scenario: Approve Leave Request - Previously Validated
    Given the user navigates to the leave request page
    When the user selects a leave request previously validated by the user
    Then the validation is refused and the system displays "You have already validated this request."


  Scenario: Final Approver - Grant Leave
    Given the user navigates to the leave request page
    When the final approver clicks "Approve" on a leave request
    Then the status changes to "Granted" for the final approver
    And the leave balance is adjusted according to the rules of the leave type
    And the system displays "Request granted successfully"


  Scenario: Final Approver - Already Granted
    Given the user navigates to the leave request page
    When the final approver clicks "Approve" on a leave request with status "Granted"
    Then the validation is refused and the system displays "This request has already been granted."


  Scenario: Approve Leave Request - Already In Progress
    Given the user navigates to the leave request page
    When the final approver clicks "Approve" on a leave request with status "In Progress"
    Then the validation is refused and the system displays "This request is already in progress."


  Scenario: Approve Leave Request - Already Pending
    Given the user navigates to the leave request page
    When the final approver clicks "Approve" on a leave request with status "Pending"
    Then the validation is refused and the system displays "This request is already pending."
