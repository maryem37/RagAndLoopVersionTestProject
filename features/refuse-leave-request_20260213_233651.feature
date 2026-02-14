Here’s the Gherkin feature file for the **"Refuse Leave Request"** user story, structured with clear scenarios covering the acceptance criteria and business rules:

Feature: Refuse Leave Request
  Description: Allow authorized users (Administrator/Team Lead) to refuse an employee's leave request when conditions or justifications are unsatisfactory.

  Background:
    Given the user is logged in to the system
    And the user belongs to the validation chain for leave requests



  Scenario: Refuse a pending leave request with a reason and optional observation
    And the user optionally adds an observation (e.g., "Please submit a formal request")
    Then the system records:
    And the system displays: "Request refused successfully"
      | Field          | Value                          |
      | Status         | "Refused"                      |
      | Refusal Date  | Current date/time                |
      | Refusal Reason | "Insufficient notice"           |
      | Observation    | "Please submit a formal request" |


  Scenario: Refuse a pending leave request with only a mandatory reason
    And the user enters a mandatory refusal reason (e.g., "Invalid justification")
    Then the system records:
    And the system displays: "Request refused successfully"
      | Field          | Value                          |
      | Status         | "Refused"                      |
      | Refusal Date  | Current date/time                |
      | Refusal Reason | "Invalid justification"          |
      | Observation    | "" (empty)                     |


  Scenario: Attempt to refuse a request that is already refused/granted/canceled
    And the user selects the "Refuse" action
    Then the system displays: "This request cannot be refused again (already refused/granted/canceled)"
    And the refusal action is blocked


  Scenario: Attempt to refuse a request with no selected reason
    And the user does not select a refusal reason
    Then the system displays: "Refusal reason is mandatory"
    And the refusal action is blocked


  Scenario: Attempt to refuse a request when user is not authorized
    And the user selects the "Refuse" action
    Then the system displays: "You are not authorized to refuse this request"
    And the refusal action is blocked


  Scenario: Refuse an "In Progress" leave request with a reason
    And the user enters a mandatory refusal reason (e.g., "Conflict with team schedule")
    Then the system records:
    And the system displays: "Request refused successfully"
      | Field          | Value                          |
      | Status         | "Refused"                      |
      | Refusal Date  | Current date/time                |
      | Refusal Reason | "Conflict with team schedule"     |
      | Observation    | "" (empty)                     |
### Key Notes:
1. **Background**: Assumes authentication and validation chain membership (per business rules).
2. **Scenarios**:
   - Cover both optional and mandatory observations.
   - Block refusal for invalid statuses (`Refused`, `Granted`, `Canceled`).
   - Enforce mandatory refusal reason.
   - Restrict action to authorized users.
   - Include the "In Progress" status as a valid refusal case (per business rules).
3. **Table Format**: Used for recording fields (adjust columns as needed for your system).
4. **Messages**: Explicitly match the acceptance criteria (e.g., "Request refused successfully").
