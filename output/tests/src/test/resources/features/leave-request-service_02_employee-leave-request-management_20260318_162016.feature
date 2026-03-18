Feature: Employee Leave Request Management
  As an employee I want to create, consult, and cancel leave requests via the API so that I can manage my absences.

  Scenario: Employee successfully creates a leave request
    Given the employee is authenticated
    When the employee submits the leave request with fromDate, toDate, type, and userId
    Then the system updates the request status to "Pending"

  Scenario: Employee cancels a pending leave request
    Given the employee is authenticated
    And there is a pending leave request
    When the employee cancels the leave request
    Then the system updates the request status to "Canceled"

  Scenario: Employee cannot cancel a granted leave request
    Given the employee is authenticated
    And there is a granted leave request
    When the employee tries to cancel the leave request
    Then the system displays the error "This request has already been validated."

  Scenario: Employee cannot cancel a refused leave request
    Given the employee is authenticated
    And there is a refused leave request
    When the employee tries to cancel the leave request
    Then the system displays the error "This request has already been refused."

  Scenario: Employee cannot cancel a canceled leave request
    Given the employee is authenticated
    And there is a canceled leave request
    When the employee tries to cancel the leave request
    Then the system displays the error "This request has been canceled and can no longer be processed."

  Scenario: Unauthorized users cannot access leave request endpoints
    Given there is an unauthorized user
    When the user attempts to create a leave request
    Then the system blocks the action

  Scenario: Employee cannot create a leave request without required fields
    Given the employee is authenticated
    When the employee submits the leave request with value
    And the employee enters all other required fields
    Then the system displays the error "Missing required field: value"
