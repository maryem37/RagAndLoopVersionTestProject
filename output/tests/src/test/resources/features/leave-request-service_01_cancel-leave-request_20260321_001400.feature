Feature: Cancel Leave Request
  As an employee, I want to cancel a pending leave request, so that I can withdraw a request that has not yet been granted.

Background:
  Given the employee logs in with valid credentials

Scenario: Employee cancels a pending leave request
  Given the employee has a pending leave request
  When the employee cancels the pending request
  Then the system responds with "Leave request cancelled successfully."

Scenario: Employee tries to cancel an already cancelled leave request
  Given the employee has a cancelled leave request
  When the employee cancels the already cancelled request
  Then the system displays the error "This leave request has already been cancelled and cannot be processed."

Scenario: Unauthorized user tries to cancel a leave request
  Given the user does not have a valid token
  When the user attempts to cancel a leave request
  Then the system blocks the action

Scenario: Employee tries to cancel a leave request without required fields
  Given the employee has a pending leave request
  When the employee submits a cancellation request without required fields
  Then the system displays the error "This leave request has already been cancelled and cannot be processed."
