Feature: Refuse Leave Request

  Background:
    Given the administrator or team lead is authenticated
    And the employee's leave request exists with status "Pending" or "In Progress"
    And required reference data exists
    And at least one leave type is available



  Scenario: Refuse Leave Request - Happy Path
    Given the administrator or team lead navigates to the leave request details page
    And (optional) enter an observation
    Then the system displays "Request details"
    And the administrator or team lead clicks "Refuse Leave Request"
    Then the system confirms the operation with "Request refused successfully"
    And the leave request status changes to "Refused"
    And the refusal date, reason, observation, and user are recorded


  Scenario: Refuse Leave Request - Already Refused/Granted/Canceled
    Given an employee's leave request exists with a status other than "Pending" or "In Progress"
    When the administrator or team lead attempts to refuse the leave request
    Then the system displays "This request cannot be refused again"


  Scenario: Refuse Leave Request - Unauthorized User
    Given an unauthorized user navigates to the leave request details page
    When they attempt to refuse a leave request
    Then the system displays "You are not authorized for this validation level"


  Scenario: Refuse Leave Request - No Reason Provided
    Given the administrator or team lead navigates to the leave request details page
    When they do not select a reason for refusal
    Then the system displays "A reason for refusal is mandatory"
