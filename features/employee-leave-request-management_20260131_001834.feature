Feature: Employee Leave Request Management

  Scenario: Successful creation of a new leave request
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request page
    And selects a type of leave and desired start date
    And enters an end date for the leave
    And provides a reason for the leave
    And submits the leave request form
    Then the system should display a success message
    And the leave request should be created in the system

  Scenario: Employee tries to create a leave request with invalid start date
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request page
    And selects a type of leave and an invalid start date
    And enters an end date for the leave
    And provides a reason for the leave
    And submits the leave request form
    Then the system should display an error message about the invalid start date

  Scenario: Employee tries to create a leave request with an overlapping period
    Given an authenticated employee with valid credentials and an existing leave request with overlapping period
    When the employee navigates to the leave request page
    And selects a type of leave and a start date within the overlapping period
    And enters an end date for the leave
    And provides a reason for the leave
    And submits the leave request form
    Then the system should display an error message about the overlapping period

  Scenario: Employee tries to create a leave request with an invalid end date
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request page
    And selects a type of leave and a valid start date
    And enters an invalid end date for the leave
    And provides a reason for the leave
    And submits the leave request form
    Then the system should display an error message about the invalid end date

  Scenario: Employee tries to create a leave request without providing a reason
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request page
    And selects a type of leave and a valid start date
    And enters an end date for the leave
    And does not provide a reason for the leave
    And submits the leave request form
    Then the system should display an error message about missing reason

  Scenario: Employee tries to create a leave request with an empty form
    Given an authenticated employee with valid credentials
    When the employee navigates to the leave request page and does not select a type of leave or enter any dates
    And submits the leave request form without providing a reason
    Then the system should display an error message about incomplete form

  Scenario: Employee tries to create a leave request after expiration of maximum allowed leaves
    Given an authenticated employee with valid credentials and maximum number of allowed leaves for the year already taken
    When the employee navigates to the leave request page
    And selects a type of leave and a valid start date
    And enters an end date for the leave
    And provides a reason for the leave
    And submits the leave request form
    Then the system should display an error message about maximum leaves reached

  Scenario: Employee tries to create a leave request with insufficient balance of leave credits
    Given an authenticated employee with valid credentials and insufficient leave credits for the requested leave period
    When the employee navigates to the leave request page
    And selects a type of leave and a valid start date
    And enters an end date for the leave
    And provides a reason for the leave
    And submits the leave request form
    Then the system should display an error message about insufficient leave credits

  Scenario: Employee cancels an existing leave request
    Given an authenticated employee with valid credentials and an existing leave request
    When the employee navigates to the leave request page
    And selects the existing leave request to cancel
    Then the system should display a confirmation message about cancelling the leave request
    And the leave request should be cancelled in the system