Feature: Refuse Leave Request

  Background:
    Given the administrator or team lead is authenticated
    And the employee's leave request exists with status "Pending" or "In Progress"
    And required reference data exists
    And at least one leave type is available



  Scenario: Refuse leave request - happy path
    Given the administrator or team lead navigates to the leave request details page
    And (optional) enter an observation
    Then the system displays "Request details"
    And the system allows the administrator or team lead to submit the refusal
    Then the system confirms the operation with "Request refused successfully"
    And the leave request status changes to "Refused"
    And the refusal date, reason, observation, and user are recorded


  Scenario: Refuse leave request - no reason provided
    Given the administrator or team lead navigates to the leave request details page with a reason for refusal left blank
    When they submit the refusal
    Then the system displays "Please select a reason for refusal"


  Scenario: Refuse already refused, granted, or canceled leave request
    Given an employee's leave request exists with status other than "Pending" or "In Progress"
    When the administrator or team lead attempts to refuse the leave request
    Then the system displays "This request has already been refused, granted, or canceled"


  Scenario: Administrator or team lead not authorized for validation level
    Given an employee's leave request exists with status "Pending" or "In Progress"
    And the administrator or team lead is not authorized for this validation level
    When they attempt to refuse the leave request
    Then the system displays "You are not authorized to perform this action"


  Scenario: Refuse leave request - missing required data
    Given an employee's leave request exists with status "Pending" or "In Progress"
    And at least one mandatory field is left blank (e.g., reason for refusal)
    When the administrator or team lead attempts to refuse the leave request
    Then the system displays "Please fill in all required fields"
