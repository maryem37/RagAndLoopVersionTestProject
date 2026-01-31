Feature: Employee Leave Request Management

  Scenario: Successful creation of a new leave request
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request page
    And selects a type of leave and desired start date
    And enters the desired end date
    And submits the leave request form
    Then the system should display a success message for the submitted leave request

  Scenario: Employee tries to submit an overlapping leave request
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request page
    And selects a type of leave and desired start date that overlaps with an existing request
    And enters the desired end date
    And submits the leave request form
    Then the system should display an error message indicating the overlap with an existing request

  Scenario: Employee tries to submit a leave request without selecting a leave type
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request page
    And leaves the leave type field empty
    And enters the desired start date and end date
    And submits the leave request form
    Then the system should display an error message indicating that a leave type is required

  Scenario: Employee tries to submit a leave request with invalid start date
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request page
    And selects a type of leave and an invalid start date (e.g., future date before today)
    And enters the desired end date
    And submits the leave request form
    Then the system should display an error message indicating that the start date is invalid

  Scenario: Employee tries to submit a leave request with invalid end date
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request page
    And selects a type of leave and a valid start date
    And enters an invalid end date (e.g., start date is after end date)
    And submits the leave request form
    Then the system should display an error message indicating that the end date is invalid

  Scenario: Employee tries to submit a leave request with insufficient balance
    Given an authenticated employee with valid credentials and insufficient leave balance for the requested period
    When the employee navigates to the leave request page
    And selects a type of leave and desired start date within the insufficient balance period
    And enters the desired end date
    And submits the leave request form
    Then the system should display an error message indicating that the employee has insufficient leave balance for the requested period

  Scenario: Employee cancels a pending leave request
    Given an authenticated employee with valid credentials and a pending leave request
    When the employee navigates to the leave request page
    And selects the pending leave request
    And clicks on the cancel button
    Then the system should display a confirmation message for cancelling the leave request
    And the leave request status should be updated to cancelled in the system

  Scenario: Employee tries to cancel a already approved leave request
    Given an authenticated employee with valid credentials and an already approved leave request
    When the employee navigates to the leave request page
    And selects the already approved leave request
    And clicks on the cancel button
    Then the system should display an error message indicating that the leave request cannot be cancelled once it has been approved

  Scenario: Employee views their past leave requests
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request history page
    Then the system should display a list of all past leave requests made by the employee, including start and end dates, leave type, and status