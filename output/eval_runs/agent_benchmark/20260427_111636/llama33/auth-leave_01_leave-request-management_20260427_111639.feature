Feature: Leave Request Management
  As an Employee, I want to submit a leave request and track its status.

  Background:
    Given the Administration logs in with valid credentials

  Scenario: Employee submits a leave request
    Given the employee has a valid account
    When the employee submits a leave request from "future date" to "future date"
    Then the leave request status is "Pending"

  Scenario Outline: Manager approves or rejects a leave request
    Given the employee has a pending leave request
    When the TeamLeader ""TestValue"" the leave request with reason ""TestValue""
    Then the leave request status is ""Pending""

    Examples:
      | action | reason | status |
      | approves | valid reason | Approved |
      | rejects | valid reason | Rejected |

  Scenario: Unauthorized user tries to submit a leave request
    Given the user is not logged in
    When the user tries to submit a leave request
    Then the system blocks the action

  Scenario: Employee tries to submit a leave request with invalid dates
    Given the employee has a valid account
    When the employee submits a leave request from "past date" to "past date"
    Then the system displays the error "Invalid dates"

  Scenario: Manager tries to approve a non-pending leave request
    Given the employee has a leave request with status "Approved"
    When the TeamLeader tries to approve the leave request
    Then the system displays the error "Invalid request status"
