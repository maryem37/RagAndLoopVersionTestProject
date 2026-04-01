Feature: Leave Request Management - Complete Feature Story
  As an Employee I want to Submit, manage, and track leave requests so that I can manage my time off effectively

  Background:
    Given the Employer logs in with valid credentials

  Scenario: Employee submits a leave request with invalid leave type
    Given the employee has sufficient balance
    When the employee submits a leave request with invalid type
    Then the system displays the error "Invalid leave type provided"

  Scenario: Employee submits a leave request with empty fields
    Given the employee has sufficient balance
    When the employee submits a leave request with missing required fields
    Then the system displays the error "All required fields must be filled"

  Scenario: Employee submits with zero days requested
    Given the employee has sufficient balance
    When the employee submits a leave request with zero days
    Then the system displays the error "Leave request must cover at least one day"

  Scenario: Employee submits without respecting notice period
    Given the employee has sufficient balance
    When the employee submits a leave request with less than 48 hours notice
    Then the system displays the error "Leave request must be submitted at least 48 hours in advance"

  Scenario: Unauthorized employee attempts to create request
    Given an unauthorized user tries to submit a leave request
    Then the system blocks the action

  Scenario: Manager approves pending leave request
    Given there is a pending leave request
    When the manager approves the leave request
    Then the leave request status is "Approved"

  Scenario: Manager rejects pending leave request
    Given there is a pending leave request
    When the manager rejects the leave request with reason "Not approved"
    Then the leave request status is "Rejected"

  Scenario: Cannot approve already processed request
    Given there is an approved leave request
    When the manager attempts to approve the already processed request
    Then the system displays the error "Request already processed"

  Scenario: Cannot approve non-existent request
    Given there is no such leave request
    When the manager attempts to approve a non-existent request
    Then the system displays the error "Request not found"

  Scenario Outline: Employee submits with different date ranges
    Given the employee has sufficient balance
    When the employee submits a leave request from "<fromDate>" to "<toDate>"
    Then the status is "<status>"

    Examples:
      | fromDate     | toDate       | status   |
      | future       | future       | Pending  |
      | future       | future       | Pending  |

  Scenario Outline: Employee submits with different leave types
    Given the employee has sufficient balance
    When the employee submits a leave request with type "<leaveType>"
    Then the status is "Pending"

    Examples:
      | leaveType         |
      | ANNUAL_LEAVE      |
      | UNPAID_LEAVE      |
      | RECOVERY_LEAVE    |
      | AUTHORIZED_ABSENCE|

  Scenario Outline: Employee submits with different period types
    Given the employee has sufficient balance
    When the employee submits a leave request with period type "<periodType>"
    Then the status is "Pending"

    Examples:
      | periodType         |
      | JOURNEE_COMPLETE   |
      | MATIN              |
      | APRES_MIDI         |
      | PAR_HEURE          |

  Scenario Outline: Test boundary conditions with days
    Given the employee has sufficient balance
    When the employee submits a leave request with "<days>" days
    Then the status is "Pending"

    Examples:
      | days |
      | 1    |
      | 5    |
      | 10   |

  Scenario: Test with different balances
    Given the employee has "value" balance
    When the employee submits an annual leave request from "future date" to "future date"
    Then the status is "value"
