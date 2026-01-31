Feature: Leave Request Management

Scenario Outline: Create Leave Request

  Given a user with username "john"
  When they submit a leave request for date range "2023-03-01" to "2023-03-05"
  Then the system should create a new leave request
  And the leave request should have status "Pending"
  And the employee's balance should be updated by 5 days

Scenario Outline: Update Leave Request Status

  Given a user with username "john"
  When they update the status of their leave request to "Approved"
  Then the system should update the status to "Approved"
  And the employee's balance should be updated by 5 days
  And the manager should receive an email notification

Scenario Outline: Update Leave Request Status (Manager)

  Given a user with username "john" as manager
  When they update the status of their leave request to "Rejected"
  Then the system should update the status to "Rejected"
  And the employee's balance should be updated by -5 days
  And the manager should receive an email notification

Scenario Outline: Cancel Leave Request

  Given a user with username "john"
  When they cancel their leave request
  Then the system should delete the leave request
  And the employee's balance should be reset to original amount

Scenario Outline: Get Employee Balance

  Given a user with username "john"
  When they retrieve their current balance
  Then the system should return the updated balance
  And the balance should reflect any changes made by leave requests

Scenario Outline: Get Leave Request History

  Given a user with username "john"
  When they retrieve their leave request history
  Then the system should return all past leave requests
  And each leave request should have its status and dates

Scenario Outline: Get Manager's Leave Requests

  Given a manager with username "jane"
  When they retrieve their leave requests
  Then the system should return all leave requests assigned to them
  And each leave request should have its status and dates

Scenario Outline: Assign Leave Request to Manager

  Given a user with username "john" as manager
  When they assign a leave request to themselves
  Then the system should update the status of the leave request to "In Progress"
  And the employee's balance should be updated by -5 days

Scenario Outline: Reject Leave Request

  Given a manager with username "jane"
  When they reject a leave request for date range "2023-03-01" to "2023-03-05"
  Then the system should update the status of the leave request to "Rejected"
  And the employee's balance should be updated by -5 days
  And the manager should receive an email notification