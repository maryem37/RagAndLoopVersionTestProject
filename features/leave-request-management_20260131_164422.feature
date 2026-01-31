Feature: Leave Request Management

Scenario: Submit a new leave request
  Given I am a registered user
  And I am on the leave requests page
  When I click "New Leave Request"
  And I fill in the required fields: type, start date, end date, reason
  And I submit the form
  Then I should see a success message
  And my leave request should be listed in the pending requests table

Scenario: Cancel an approved leave request
  Given I am a registered user with an approved leave request
  And I am on the leave requests page
  When I find my approved leave request and click "Cancel"
  Then I should see a confirmation message
  And my leave request status should change to "Cancelled" in the approved requests table

Scenario: Approve a pending leave request
  Given an admin is logged in
  And there is a pending leave request
  When the admin navigates to the leave requests page
  And finds the pending leave request and clicks "Approve"
  Then I should see a success message
  And the leave request status should change to "Approved" in the pending requests table

Scenario: Reject a pending leave request
  Given an admin is logged in
  And there is a pending leave request
  When the admin navigates to the leave requests page
  And finds the pending leave request and clicks "Reject"
  Then I should see a success message
  And the leave request status should change to "Rejected" in the pending requests table

Scenario: View leave balance
  Given I am a registered user
  When I navigate to my profile page
  Then I should see my current leave balance displayed

Scenario: Request for extended leave
  Given I am a registered user with sufficient leave balance
  And I have a pending leave request
  When I edit the leave request and extend the end date
  Then I should see a success message
  And my leave request should be updated in the pending requests table

Scenario: Request for leave on blackout dates
  Given I am a registered user with sufficient leave balance
  And there are blackout dates during the requested leave period
  When I submit the leave request
  Then I should see an error message
  And my leave request should not be submitted and remain in the pending requests table

Scenario: Request for leave on public holidays
  Given I am a registered user with sufficient leave balance
  And there are public holidays during the requested leave period
  When I submit the leave request
  Then I should see an error message
  And my leave request should not be submitted and remain in the pending requests table

Scenario: Request for leave on weekends
  Given I am a registered user with sufficient leave balance
  And there are weekends during the requested leave period
  When I submit the leave request
  Then I should see an error message
  And my leave request should not be submitted and remain in the pending requests table