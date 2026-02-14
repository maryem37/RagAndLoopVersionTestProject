Here’s the conversion of the user story into Gherkin syntax, structured as a **Feature** with multiple **Scenario**s to cover the acceptance criteria and business rules:

Feature: Approve Leave Request
  As an Administrator or Team Lead, I want to approve an employee's leave request
  So that I can officially validate their absence according to the defined approval chain.

  Background:
    Given the user is logged in as an Administrator or Team Lead
    And the leave request system is accessible



  Scenario: Approve a leave request in a valid state ("Pending" or "In Progress")
    Given a leave request with status "Pending" or "In Progress"
    And the user is part of the request's approval chain
    And the user has not previously approved this request
    And the user adds an optional observation (if applicable)
    Then the system displays "Request granted successfully"
    And the status changes to:
    And the system marks the user's validation as TRUE
      | "In Progress" | if not the final approver |
      | "Granted"      | if the final approver     |


  Scenario: Block approval when the user is not authorized
    Given a leave request with status "Pending" or "In Progress"
    And the user is not part of the request's approval chain
    When the user attempts to approve the request
    Then the system displays the error message: "You are not authorized to modify the status of this request."
    And the request status remains unchanged


  Scenario: Block approval when the request is not in a valid state
    Given a leave request with status "Granted", "Rejected", or "Cancelled"
    And the user is part of the approval chain
    When the user attempts to approve the request
    Then the system displays an error message: "Request cannot be approved in its current state."
    And the request status remains unchanged


  Scenario: Block approval when the user has already approved the request
    Given a leave request with status "Pending" or "In Progress"
    And the user is part of the approval chain
    And the user has previously approved this request
    When the user attempts to approve the request again
    Then the system displays an error message: "You have already approved this request."
    And the request status remains unchanged


  Scenario: Final approver grants leave and adjusts leave balance
    Given a leave request with status "In Progress"
    And the user is the final approver in the approval chain
    And the user has not previously approved this request
    When the user approves the request
    Then the request status changes to "Granted"
    And the system deducts the leave balance according to the leave type (annual, authorization, recovery)
    And the system displays "Request granted successfully"


  Scenario: Non-final approver validates and moves request to "In Progress"
    Given a leave request with status "Pending"
    And the user is part of the approval chain but not the final approver
    And the user has not previously approved this request
    When the user approves the request
    Then the request status changes to "In Progress"
    And the system marks the user's validation as TRUE
    And the system displays "Request granted successfully"
### Notes:
1. **Hierarchical Validation Logic**:
   - The `Background` ensures the user is logged in and the system is ready.
   - Scenarios distinguish between **final approvers** (who change status to `"Granted"` and adjust balance) and **non-final approvers** (who move it to `"In Progress"`).

2. **Error Handling**:
   - Explicitly covers unauthorized users, invalid states, and duplicate approvals.

3. **Optional Observation**:
   - Included in the first scenario (can be omitted or tested separately if needed).

4. **Leave Balance Adjustment**:
   - Only triggered for **final approvers** (Scenario 5). Non-final approvers only mark validation as `TRUE` (Scenario 6).
