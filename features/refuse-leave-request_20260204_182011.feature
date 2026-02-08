Feature: Refuse Leave Request

  Background:
    Given the administrator or team lead is authenticated
    And the employee's leave request exists with status "Pending" or "In Progress"
    And required reference data exists
    And at least one leave type is available



  Scenario: Refuse Leave Request - Happy Path
    Given the administrator or team lead navigates to the leave request details page
    When they select a reason for refusal and optionally enter an observation
    Then the system displays "Request refused successfully"
    And the status of the leave request changes to "Refused"
    And the refusal date, reason, and observation are recorded


  Scenario: Refuse Leave Request - Already Refused/Granted/Canceled
    Given an employee's leave request with a status other than "Pending" or "In Progress"
    When the administrator or team lead attempts to refuse the request
    Then the system displays "This request cannot be refused again"


  Scenario: Refuse Leave Request - No Reason Provided
    Given the administrator or team lead navigates to the leave request details page without selecting a reason for refusal
    When they attempt to refuse the request
    Then the system displays "A reason for refusal is mandatory"


  Scenario: Refuse Leave Request - Unauthorized User
    Given an unauthorized user attempts to refuse an employee's leave request
    When they navigate to the leave request details page and attempt to refuse the request
    Then the system displays "You are not authorized to perform this action"
