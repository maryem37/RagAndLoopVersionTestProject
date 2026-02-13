Feature: Refuse Leave Request

  Background:
    Given the employee "John Doe" has submitted a leave request for "2024-07-15" to "2024-07-19" with leave type "Annual"
    And the system contains reference data for leave types, reasons, and validation chains
    And the user "Admin User" is authenticated and belongs to the validation chain for "John Doe"



  Scenario: Refuse a pending leave request with a valid reason and optional observation
    And "Admin User" confirms the refusal
    Then the leave request status changes to "Refused"
    And the refusal date is recorded as "2024-07-10"
    And the refusal reason is recorded as "Insufficient coverage"
    And the manager's observation is recorded as "Team is understaffed during this period"
    And the system displays "Request refused successfully"


  Scenario: Refuse a pending leave request with a valid reason but no observation
    And "Admin User" confirms the refusal without entering an observation
    Then the leave request status changes to "Refused"
    And the refusal date is recorded as "2024-07-10"
    And the refusal reason is recorded as "Personal reasons"
    And the manager's observation field remains empty
    And the system displays "Request refused successfully"


  Scenario: Attempt to refuse a leave request that is already refused
    And "Admin User" attempts to select the reason "Insufficient coverage" for refusal
    Then the system displays "This request has already been refused and cannot be refused again"


  Scenario: Attempt to refuse a leave request that is already granted
    And "Admin User" attempts to select the reason "Insufficient coverage" for refusal
    Then the system displays "This request has already been granted and cannot be refused"


  Scenario: Attempt to refuse a leave request that is already canceled
    And "Admin User" attempts to select the reason "Insufficient coverage" for refusal
    Then the system displays "This request has already been canceled and cannot be refused"


  Scenario: Attempt to refuse a leave request without selecting a reason
    And "Admin User" attempts to confirm the refusal without selecting a reason
    Then the system displays "Please select a reason for refusal"


  Scenario: Attempt to refuse a leave request that is not in the validation chain
    And "Team Lead User" attempts to view the leave request details for "John Doe"
    Then the system displays "You are not authorized to view or refuse this request"


  Scenario: Attempt to refuse a leave request with status "Approved"
    And "Admin User" attempts to select the reason "Insufficient coverage" for refusal
    Then the system displays "This request cannot be refused as it is already approved"


  Scenario: Attempt to refuse a leave request with status "In Progress"
    And "Admin User" confirms the refusal
    Then the leave request status changes to "Refused"
    And the refusal date is recorded as "2024-07-10"
    And the refusal reason is recorded as "Insufficient coverage"
    And the system displays "Request refused successfully"


  Scenario: Attempt to refuse a leave request with status "Pending" but user is not authorized
    And "Unauthorized User" attempts to view the leave request details for "John Doe" with status "Pending"
    Then the system displays "You are not authorized to refuse this request"
