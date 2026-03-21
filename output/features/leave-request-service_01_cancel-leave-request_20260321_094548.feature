Feature: Cancel Leave Request
  As an employee, I want to cancel a pending leave request, so that I can withdraw a request that has not yet been granted.

  Background:
    Given the employee logs in with valid credentials

  Scenario: Employee cancels a pending leave request
    Given the employee has a pending leave request
    When the employee submits a request to cancel the leave request
    Then the system responds with "Leave request cancelled successfully."
    And the leave request status is "Cancelled"

  Scenario: Employee tries to cancel an already cancelled leave request
    Given the employee has a cancelled leave request
    When the employee submits a request to cancel the leave request
    Then the system displays the error "This leave request has already been cancelled and cannot be processed."

  Scenario: Unauthorized user tries to cancel a leave request
    Given the employee does not have a valid token
    When the employee submits a request to cancel the leave request
    Then the system blocks the action

  Scenario: Employee tries to cancel a leave request without providing required fields
    Given the employee has a pending leave request
    When the employee submits a request to cancel the leave request without providing required fields
    Then the system displays the error "Cancel Leave Request As an employee, I want to cancel a pending leave request, so that I can withdraw a request that has not yet been granted. Business Rules â€"

  Scenario: Employee tries to cancel a leave request with invalid value
    Given the employee has a pending leave request
    When the employee submits a request to cancel the leave request with invalid value
    Then the system displays the error "Cancel Leave Request As an employee, I want to cancel a pending leave request, so that I can withdraw a request that has not yet been granted. Business Rules â€"
