Feature: Employee Authentication
  As an employee I want to authenticate via the API so that I can access the system securely.

  Scenario: Employee logs in with valid email and password
    Given the employee has valid credentials
    When the employee submits the login request with email and password
    Then the system returns a valid JWT token

  Scenario: Employee submits login request with invalid credentials
    Given the employee has invalid credentials
    When the employee submits the login request with email and password
    Then the system blocks the action

  Scenario: Employee submits login request with missing required fields
    Given the employee has incomplete credentials
    When the employee submits the login request without email and password
    Then the system displays the error "Bad Request"
