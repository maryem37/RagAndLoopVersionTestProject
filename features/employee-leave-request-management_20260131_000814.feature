Feature: Employee Leave Request Management

Scenario: Successful Leave Request for a Full Day
  Given an authenticated employee with valid credentials
  When the employee navigates to the leave request page
  And selects a full day for the desired leave date
  And enters a reason for the leave request
  And submits the leave request form
  Then the system should display a success message
  And the employee's leave balance should be updated accordingly

Scenario: Unsuccessful Leave Request due to Insufficient Balance
  Given an authenticated employee with valid credentials and insufficient leave balance
  When the employee navigates to the leave request page
  And selects a full day for the desired leave date
  And enters a reason for the leave request
  And submits the leave request form
  Then the system should display an error message about insufficient leave balance

Scenario: Unsuccessful Leave Request due to Invalid Date Range
  Given an authenticated employee with valid credentials and sufficient leave balance
  When the employee navigates to the leave request page
  And selects an invalid date range for the desired leave period
  And enters a reason for the leave request
  And submits the leave request form
  Then the system should display an error message about the invalid date range

Scenario: Unsuccessful Leave Request due to Incomplete Information
  Given an authenticated employee with valid credentials and sufficient leave balance
  When the employee navigates to the leave request page
  And leaves any required field blank for the leave request
  And submits the leave request form
  Then the system should display an error message about incomplete information

Scenario: Successful Cancellation of a Leave Request
  Given an authenticated employee with valid credentials and a pending leave request
  When the employee navigates to the leave requests page
  And selects the pending leave request to cancel
  And confirms the cancellation
  Then the system should display a success message
  And the employee's leave balance should be updated accordingly

Scenario: Unsuccessful Cancellation of a Leave Request due to Already Approved Status
  Given an authenticated employee with valid credentials and an approved leave request
  When the employee navigates to the leave requests page
  And selects the approved leave request to cancel
  And confirms the cancellation
  Then the system should display an error message about the already approved status

Scenario: Unsuccessful Cancellation of a Leave Request due to Already Started Status
  Given an authenticated employee with valid credentials and a started leave request
  When the employee navigates to the leave requests page
  And selects the started leave request to cancel
  And confirms the cancellation
  Then the system should display an error message about the already started status

Scenario: Successful Approval of a Leave Request by Manager
  Given a manager with valid credentials and a pending leave request from an employee
  When the manager navigates to the leave requests page
  And selects the pending leave request for approval
  And enters any comments (optional)
  And approves the leave request
  Then the system should display a success message
  And the employee's leave balance should be updated accordingly

Scenario: Unsuccessful Approval of a Leave Request by Manager due to Insufficient Balance
  Given a manager with valid credentials and a pending leave request from an employee with insufficient leave balance
  When the manager navigates to the leave requests page
  And selects the pending leave request for approval
  And enters any comments (optional)
  And approves the leave request
  Then the system should display an error message about insufficient leave balance for the employee

Scenario: Unsuccessful Approval of a Leave Request by Manager due to Invalid Date Range
  Given a manager with valid credentials and a pending leave request from an employee with an invalid date range
  When the manager navigates to the leave requests page
  And selects the pending leave request for approval
  And enters any comments (optional)
  And approves the leave request
  Then the system should display an error message about the invalid date range in the leave request