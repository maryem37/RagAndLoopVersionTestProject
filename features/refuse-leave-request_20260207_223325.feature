Feature: Refuse Leave Request

  Background:
    Given the administrator or team lead is authenticated
    And the employee's leave request exists with status "Pending" or "In Progress"
    And required reference data exists
    And at least one leave type is available



  Scenario: Refuse Leave Request - Happy Path
    Given the administrator or team lead navigates to the leave request details page
    When they select a reason for refusal and optionally enter an observation
    Then the system updates the leave request status to "Refused"
    And the system records the refusal date, reason, and observation
    And the system displays: "Request refused successfully"


  Scenario: Refuse Leave Request - Already Refused, Granted, or Canceled
    Given an employee's leave request with status other than "Pending" or "In Progress"
    When the administrator or team lead attempts to refuse the request
    Then the system displays: "This request cannot be refused as it has already been [Refused, Granted, or Canceled]"


  Scenario: Refuse Leave Request - No Reason for Refusal
    Given the administrator or team lead navigates to the leave request details page
    When they attempt to refuse the request without selecting a reason
    Then the system displays: "A reason for refusal is mandatory to validate the action"


  Scenario: Refuse Leave Request - Unauthorized User
    Given an unauthorized user navigates to the leave request details page
    When they attempt to refuse a leave request
    Then the system displays: "You are not authorized for this validation level"


  Scenario: Refuse Leave Request - Viewing Request Details
    Given the administrator or team lead navigates to the leave request details page
    When they view the complete details of the request
    Then they can see the requestor's name, leave type, start and end dates, status, and any observations


  Scenario: Refuse Leave Request - Recording Observation
    Given the administrator or team lead navigates to the leave request details page
    When they enter an observation (optional) before refusing the request
    Then the system records the observation along with the refusal date, reason, and user information


  Scenario: Refuse Leave Request - Confirmation Message
    Given the administrator or team lead successfully refuses a leave request
    When they navigate away from the leave request details page
    Then the system displays: "Request refused successfully" on the subsequent page
