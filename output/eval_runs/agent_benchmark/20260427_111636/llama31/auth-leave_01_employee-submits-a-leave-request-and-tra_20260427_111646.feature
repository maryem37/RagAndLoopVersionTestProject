Feature: Employee submits a leave request and tracks its status
  As an Employee, I want to submit a leave request and track its status.

  Background:
    Given the user logs in with valid credentials

  Scenario: Manager approves a pending leave request
    Given the manager has a valid user role
    And the leave request is in the "Pending" state
    When the manager approves the leave request
    Then the leave request status is "Approved"

  Scenario: Unauthorized user receives 4xx error
    Given the unauthorized user has an invalid user role
    When the unauthorized user submits a leave request
    Then the system displays the error "Unauthorized"

  Scenario Outline: Employee submits with different date ranges
    Given the employee has a valid user role
    When the employee submits a leave request from ""TestValue"" to ""TestValue""
    Then the status is ""Pending""

    Examples:
      | fromDate | toDate | status |
      | future   | future | Pending |
      | past     | past   | Pending |
      | future   | past   | Pending |
      | past     | future | Pending |

  Scenario: Employee tries to create a leave request with insufficient balance
    Given the employee has an insufficient balance
    When the employee submits a leave request
    Then the system displays the error "Insufficient balance"

  Scenario: Employee tries to create a leave request with overlap/conflict
    Given the employee has an overlapping/conflicting request
    When the employee submits a leave request
    Then the system displays the error "Overlap/conflict"
