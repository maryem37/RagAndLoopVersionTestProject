Feature: Leave Request Management

Scenario: Submit a new leave request
  Given I am a registered user
  And I am on the leave requests page
  When I click on "New Leave Request"
  And I fill in the required fields: type, start date, end date, reason
  And I submit the form
  Then I should see a success message
  And my leave request should be listed under pending requests

Scenario: Cancel an approved leave request
  Given I am a registered user with an approved leave request
  And I am on the leave requests page
  When I find my approved leave request and click "Cancel"
  Then I should see a confirmation message
  And my leave request status should change to cancelled

Scenario: Edit an existing leave request
  Given I am a registered user with an existing leave request
  And I am on the leave requests page
  When I find my leave request and click "Edit"
  And I update the required fields: type, start date, end date, reason
  And I submit the form
  Then I should see a success message
  And my updated leave request details should be displayed

Scenario: View leave balance
  Given I am a registered user
  And I am on the leave requests page
  When I click on "View Leave Balance"
  Then I should see my remaining leave days for each type (e.g., annual, sick)

Scenario: Approve a pending leave request
  Given an administrator is logged in
  And there is a pending leave request
  When the administrator navigates to the leave requests page
  And finds the pending leave request
  And clicks "Approve"
  Then a success message should be displayed
  And the leave request status should change to approved

Scenario: Reject a pending leave request
  Given an administrator is logged in
  And there is a pending leave request
  When the administrator navigates to the leave requests page
  And finds the pending leave request
  And clicks "Reject"
  Then a success message should be displayed
  And the leave request status should change to rejected

Scenario: Search for leave requests
  Given I am a registered user or an administrator
  And I am on the leave requests page
  When I enter search criteria (e.g., user, date range, status)
  Then only the matching leave requests should be displayed

Scenario: Filter leave requests by user
  Given I am a registered user or an administrator
  And I am on the leave requests page
  When I select a specific user from the filter options
  Then only the leave requests for that user should be displayed

Scenario: Filter leave requests by status
  Given I am a registered user or an administrator
  And I am on the leave requests page
  When I select a specific status (e.g., pending, approved, rejected) from the filter options
  Then only the leave requests with that status should be displayed