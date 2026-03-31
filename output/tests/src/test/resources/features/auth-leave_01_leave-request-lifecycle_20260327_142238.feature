Feature: Leave Request Lifecycle
  As an Employee, I want to submit, manage, and track leave requests so that I can manage my time off effectively

  Background:
    Given the Employee logs in with valid credentials

  Scenario: Employee submits a valid leave request
    Given the Employee has sufficient leave balance
    When the Employee submits an annual leave request from "future date" to "future date"
    And the request includes a valid reason
    Then the leave request status is "Pending"

  Scenario: Employee submits without filling all required fields
    Given the Employee has sufficient leave balance
    When the Employee submits a leave request without a reason
    Then the system displays the error "Request cannot be created without a reason"

  Scenario: Employee submits with invalid leave type
    Given the Employee has sufficient leave balance
    When the Employee submits a leave request with type "INVALID_LEAVE_TYPE"
    Then the system displays the error "Invalid leave type"

  Scenario: Employee submits overlapping with another request
    Given the Employee has sufficient leave balance
    When the Employee submits a leave request overlapping with an existing request
    Then the system displays the error "Leave request overlaps with an existing request"

  Scenario: Employee submits with insufficient balance
    Given the Employee has zero balance
    When the Employee submits an annual leave request from "future date" to "future date"
    Then the system displays the error "Insufficient leave balance"

  Scenario: Unauthorized employee attempts to create request
    Given the Employee does not have valid credentials
    When the Employee tries to submit a leave request
    Then the system blocks the action

  Scenario Outline: Employee submits with different date ranges
    When the Employee submits a leave request from "<fromDate>" to "<toDate>"
    Then the status is "<status>"

    Examples:
      | fromDate     | toDate       | status  |
      | future date  | future date  | Pending |
      | future date  | future date  | Rejected|
      | future date  | future date  | Approved|

  Scenario Outline: Employee submits with different leave types
    When the Employee submits a "<leaveType>" leave request from "future date" to "future date"
    Then the status is "<status>"

    Examples:
      | leaveType         | status  |
      | ANNUAL_LEAVE      | Pending |
      | UNPAID_LEAVE      | Pending |
      | RECOVERY_LEAVE    | Pending |
      | AUTHORIZED_ABSENCE| Pending |

  Scenario Outline: Employee submits with different period types
    When the Employee submits a leave request with period type "<periodType>" from "future date" to "future date"
    Then the status is "<status>"

    Examples:
      | periodType       | status  |
      | JOURNEE_COMPLETE | Pending |
      | MATIN            | Pending |
      | APRES_MIDI       | Pending |
      | PAR_HEURE        | Pending |

  Scenario Outline: Employee submits with different balances
    Given the Employee has "<balance>" balance
    When the Employee submits a leave request from "future date" to "future date"
    Then the system displays the error "<errorMessage>"

    Examples:
      | balance  | errorMessage                  |
      | zero     | Insufficient leave balance  |
      | negative | Insufficient leave balance  |

  Scenario Outline: Employee submits with different notice periods
    When the Employee submits a leave request less than "<noticePeriod>" hours before start date
    Then the system displays the error "<errorMessage>"

    Examples:
      | noticePeriod | errorMessage                           |
      | 48           | Request must respect the notice period |

  Scenario Outline: Employee submits with different day counts
    When the Employee submits a leave request with "<dayCount>" days
    Then the system displays the error "<errorMessage>"

    Examples:
      | dayCount | errorMessage                         |
      | zero     | Request cannot be created with zero days |
      | max+1    | Exceeds maximum continuous days allowed|

  Scenario: Employee submits with different boundary conditions
    When the Employee submits a leave request from "value" to "value"
    Then the status is "value"
