Feature: Leave Request Lifecycle
  As an Employee, I want to submit, manage, and track leave requests so that I can manage my time off effectively

  Background:
    Given the Employee logs in with valid credentials

  Scenario: Employee submits a valid leave request
    Given the Employee has sufficient leave balance
    When the Employee submits an annual leave request from "future date" to "future date"
    And the request has a valid reason
    Then the leave request status is "Pending"

  Scenario: Employee submits without filling all required fields
    Given the Employee has sufficient leave balance
    When the Employee submits a leave request without a reason
    Then the system displays the error "Request cannot be created without a reason"

  Scenario: Employee submits overlapping with another request
    Given the Employee has a pending leave request from "future date" to "future date"
    When the Employee submits another leave request overlapping the existing one
    Then the system displays the error "Leave request overlaps with an existing request"

  Scenario: Employee submits with insufficient balance
    Given the Employee has zero balance
    When the Employee submits an annual leave request from "future date" to "future date"
    Then the system displays the error "Insufficient balance"

  Scenario: Employee submits without respecting notice period (48 hours)
    Given the Employee has sufficient leave balance
    When the Employee submits a leave request starting within 48 hours
    Then the system displays the error "Notice period must be respected"

  Scenario: Unauthorized employee attempts to create request
    Given the Employee is not logged in
    When the Employee attempts to submit a leave request
    Then the system blocks the action

  Scenario Outline: Employee submits with different leave types
    Given the Employee has sufficient leave balance
    When the Employee submits a leave request of type "<leaveType>"
    Then the leave request type is "<leaveType>"

    Examples:
      | leaveType       |
      | ANNUAL_LEAVE    |
      | UNPAID_LEAVE    |
      | RECOVERY_LEAVE  |
      | AUTHORIZED_ABSENCE |

  Scenario Outline: Employee submits with different period types
    Given the Employee has sufficient leave balance
    When the Employee submits a leave request with period type "<periodType>"
    Then the leave request period type is "<periodType>"

    Examples:
      | periodType       |
      | JOURNEE_COMPLETE |
      | MATIN            |
      | APRES_MIDI       |
      | PAR_HEURE        |

  Scenario Outline: Employee submits with different date ranges
    When the Employee submits a leave request from "<fromDate>" to "<toDate>"
    Then the status is "<status>"

    Examples:
      | fromDate     | toDate       | status  |
      | future date  | future date  | Pending |
      | past date    | past date    | Rejected|
      | future date  | past date    | Rejected|

  Scenario Outline: Employee submits with different balances
    Given the Employee has "<balance>" balance
    When the Employee submits a leave request
    Then the system displays the error "<errorMessage>"

    Examples:
      | balance    | errorMessage             |
      | zero       | Insufficient balance   |
      | negative   | Insufficient balance   |

  Scenario Outline: Employee submits with different continuous days
    Given the Employee has sufficient leave balance
    When the Employee submits a leave request exceeding maximum continuous days allowed
    Then the system displays the error "<errorMessage>"

    Examples:
      | errorMessage                             |
      | Request exceeds maximum continuous days|

  Scenario: Employee submits with different reasons
    Given the Employee has sufficient leave balance
    When the Employee submits a leave request with reason "value"
    Then the leave request reason is "value"
