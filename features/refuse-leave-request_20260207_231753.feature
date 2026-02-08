Feature: Refuse Leave Request

  Background:
    Given the administrator or team lead is authenticated
    And the employee's leave request exists with status "Pending" or "In Progress"
    And required reference data exists
    And at least one leave type is available



  Scenario: Refuse leave request - happy path
    Given the administrator or team lead navigates to the leave request details page
    When they select a reason for refusal and optionally enter an observation
    Then the system displays "Request details"
    And the status changes to "Refused"
    And the refusal date, reason, and observation are recorded
    And the system confirms the operation with the message "Request refused successfully"


  Scenario: Refuse leave request - no reason provided
    Given the administrator or team lead navigates to the leave request details page
    When they attempt to refuse the leave request without providing a reason
    Then the system displays "<Refusal reason is mandatory>"


  Scenario: Refuse already refused, granted, or canceled leave request
    Given an employee's leave request exists with status "Refused", "Granted", or "Canceled"
    When the administrator or team lead attempts to refuse the leave request again
    Then the system displays "<This request has already been (refused/granted/canceled)>"


  Scenario: Refuse leave request - unauthorized user
    Given an unauthorized user navigates to the leave request details page
    When they attempt to refuse a leave request
    Then the system displays "<You are not authorized for this validation level>"
