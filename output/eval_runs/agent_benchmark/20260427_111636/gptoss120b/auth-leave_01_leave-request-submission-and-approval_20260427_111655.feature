Feature: Leave request submission and approval
  Employees can submit leave requests and managers can approve them while authentication is enforced.

Scenario: Employee submits a leave request successfully
  Given the Employer logs in with valid credentials
  When the Employer submits a leave request with future start and end dates
  Then the leave request status is "Pending"

Scenario: Unauthorized user attempts to submit a leave request
  When an unauthenticated user attempts to submit a leave request
  Then the system blocks the action
