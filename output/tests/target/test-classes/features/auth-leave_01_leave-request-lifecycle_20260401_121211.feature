Feature: Leave Request Lifecycle
  Employees can submit, manage, and track leave requests

  Background:
    Given the employee logs in with valid credentials

  Scenario: Employee submits a valid leave request
    Given the employee has sufficient leave balance
    When the employee submits an annual leave request from "future date" to "future date"
    And the request includes a valid reason
    Then the leave request status is "Pending"

  Scenario: Employee submits without filling all required fields
    Given the employee has sufficient leave balance
    When the employee submits a leave request without a reason
    Then the system displays the error "Request cannot be processed due to missing fields"

  Scenario: Employee submits overlapping with another request
    Given the employee has a pending leave request from "future date" to "future date"
    When the employee submits another leave request overlapping the existing one
    Then the system displays the error "Leave request overlaps with an existing request"

  Scenario: Employee submits with insufficient balance
    Given the employee has zero leave balance
    When the employee submits an annual leave request from "future date" to "future date"
    Then the system displays the error "Insufficient leave balance"

  Scenario: Unauthorized employee attempts to create request
    Given the unauthorized employee logs in with valid credentials
    When the unauthorized employee submits a leave request
    Then the system blocks the action

  Scenario Outline: Employee submits with different date ranges
    When the employee submits a leave request from "<fromDate>" to "<toDate>"
    Then the status is "<status>"

    Examples:
      | fromDate     | toDate       | status  |
      | future date  | future date  | Pending |
      | future date  | future date  | Rejected|
      | future date  | future date  | Approved|

  Scenario Outline: Employee submits with different leave types
    When the employee submits a leave request with type "<leaveType>"
    Then the status is "<status>"

    Examples:
      | leaveType         | status  |
      | ANNUAL_LEAVE      | Pending |
      | UNPAID_LEAVE      | Pending |
      | RECOVERY_LEAVE    | Pending |
      | AUTHORIZED_ABSENCE| Pending |

  Scenario Outline: Employee submits with different balances
    Given the employee has "<balance>" leave balance
    When the employee submits a leave request from "future date" to "future date"
    Then the system displays the error "<errorMessage>"

    Examples:
      | balance | errorMessage                  |
      | zero    | Insufficient leave balance  |
      | negative| Insufficient leave balance  |

  Scenario Outline: Employee submits with different notice periods
    When the employee submits a leave request less than "<noticePeriod>" hours before start
    Then the system displays the error "<errorMessage>"

    Examples:
      | noticePeriod | errorMessage                           |
      | 48           | Request does not respect notice period |

  Scenario: Employee submits with different day counts
    When the employee submits a leave request with "value" days
    Then the system displays the error "value"
