Feature: Approve Leave Request
  As an Administrator or Team Lead, I want to approve an employee's leave request, so that I can officially validate their absence according to the defined approval chain.

  Background:
    Given the user is authenticated

  Scenario: Administrator approves a leave request
    Given the leave request status is "In Progress"
    And the user is the final approver in the approval chain
    And the user has not previously approved the request
    When the user approves the leave request
    And the system adjusts the leave balance according to the leave type
    Then the request status changes to "Granted"
    And the system displays "Request granted successfully"

  Scenario: Team Lead approves a leave request
    Given the leave request status is "Pending"
    And the user is an intermediate approver in the approval chain
    And the user has not previously approved the request
    When the user approves the leave request
    Then the request status changes to "In Progress"
    And the system marks the manager's validation as TRUE

  Scenario: User is not authorized to approve the leave request
    Given the leave request status is "Pending"
    And the user is not in the approval chain
    When the user attempts to approve the leave request
    Then the system displays the error You are not authorized to modify the status of this request.

  Scenario: User tries to approve a request that is not in a valid state
    Given the leave request status is "Granted"
    And the user is in the approval chain
    When the user attempts to approve the leave request
    Then the system displays the error If the request is not in a valid state ("Pending" or "In Progress"), validation is blocked.

  Scenario: User tries to approve a request they have already previously approved
    Given the leave request status is "Pending"
    And the user is in the approval chain
    And the user has previously approved the request
    When the user attempts to approve the leave request
    Then the system displays the error If the user has already validated previously, the validation is refused.
