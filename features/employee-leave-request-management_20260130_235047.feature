Feature: Employee Leave Request Management

Scenario: Successful leave request for a full day
  Given an authenticated employee with valid credentials
  When the employee navigates to the leave request page
  And selects a full day for the desired leave date
  And enters a reason for the leave request
  And submits the leave request
  Then the system should display a success message
  And the employee's leave balance should be updated accordingly

Scenario: Unsuccessful leave request due to insufficient balance
  Given an authenticated employee with valid credentials and insufficient leave balance
  When the employee navigates to the leave request page
  And selects a full day for the desired leave date
  And enters a reason for the leave request
  And submits the leave request
  Then the system should display an error message about insufficient leave balance

Scenario: Unsuccessful leave request due to invalid leave type selection
  Given an authenticated employee with valid credentials
  When the employee navigates to the leave request page
  And selects an invalid leave type for the desired leave date
  And enters a reason for the leave request
  And submits the leave request
  Then the system should display an error message about the selected leave type being invalid

Scenario: Unsuccessful leave request due to empty reason field
  Given an authenticated employee with valid credentials
  When the employee navigates to the leave request page
  And selects a full day for the desired leave date
  And leaves the reason field empty
  And submits the leave request
  Then the system should display an error message about the reason field being required

Scenario: Successful leave request for a partial day
  Given an authenticated employee with valid credentials and sufficient leave balance
  When the employee navigates to the leave request page
  And selects a partial day for the desired leave date
  And enters a reason for the leave request
  And submits the leave request
  Then the system should display a success message
  And the employee's leave balance should be updated accordingly

Scenario: Unsuccessful leave request due to insufficient balance for partial day
  Given an authenticated employee with valid credentials and insufficient leave balance for a partial day
  When the employee navigates to the leave request page
  And selects a partial day for the desired leave date
  And enters a reason for the leave request
  And submits the leave request
  Then the system should display an error message about insufficient leave balance for the selected days

Scenario: Successful cancellation of a pending leave request
  Given an authenticated employee with valid credentials and a pending leave request
  When the employee navigates to the leave requests page
  And selects the pending leave request to cancel
  And confirms the cancellation
  Then the system should display a success message
  And the employee's leave balance should be updated accordingly

Scenario: Unsuccessful cancellation of a past leave request
  Given an authenticated employee with valid credentials and a past leave request
  When the employee navigates to the leave requests page
  And selects the past leave request to cancel
  Then the system should display an error message about the selected leave request being ineligible for cancellation

Scenario: Unsuccessful cancellation of another employee's leave request
  Given an authenticated employee with valid credentials and a pending leave request belonging to another employee
  When the employee navigates to the leave requests page
  And selects the other employee's pending leave request to cancel
  Then the system should display an error message about not having permission to cancel someone else's leave request