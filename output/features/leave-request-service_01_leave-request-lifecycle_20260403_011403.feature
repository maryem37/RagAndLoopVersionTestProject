Feature: Leave Request Lifecycle
  As an Employee, I want to submit, manage, and track leave requests so that I can manage my time off effectively

  Background:
    Given the employee logs in with valid credentials

  Scenario: Employee submits a valid leave request
    Given the employee has sufficient leave balance
    When the employee submits an annual leave request from "future date" to "future date" with a valid reason
    Then the leave request status is "Pending"
    And the employee's leave balance is updated accordingly

  Scenario: Employee submits without filling all required fields
    When the employee submits a leave request without a reason
    Then the system displays the error "Reason is required"

  Scenario: Employee submits overlapping with another request
    Given the employee has an existing leave request from "future date" to "future date"
    When the employee submits another leave request overlapping the existing one
    Then the system displays the error "Leave dates overlap with an existing request"

  Scenario: Employee submits with insufficient balance
    Given the employee has zero leave balance
    When the employee submits an annual leave request from "future date" to "future date"
    Then the system displays the error "Insufficient leave balance"

  Scenario: Employee submits without respecting notice period (48 hours)
    When the employee submits a leave request starting within 48 hours from now
    Then the system displays the error "Leave request must be submitted at least 48 hours in advance"

  Scenario: Unauthorized employee attempts to create request
    When an unauthorized employee attempts to create a leave request
    Then the system blocks the action

  Scenario Outline: Employee submits with different leave types
    When the employee submits a leave request of type "<leaveType>" from "future date" to "future date"
    Then the leave request status is "Pending"

    Examples:
      | leaveType     |
      | ANNUAL_LEAVE  |
      | SICK_LEAVE    |

  Scenario Outline: Employee submits with different date ranges
    When the employee submits a leave request from "<fromDate>" to "<toDate>"
    Then the leave request status is "<status>"

    Examples:
      | fromDate     | toDate       | status  |
      | future date  | future date  | Pending |
      | past date    | past date    | Rejected|
      | future date  | very old date| Rejected|
