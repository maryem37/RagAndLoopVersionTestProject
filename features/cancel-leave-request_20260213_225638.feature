Here’s the Gherkin feature file for the **"Cancel Leave Request"** user story, following the given context and best practices for scenario structure:

Feature: Cancel Leave Request
  As a user
  I want to cancel my leave request
  So that I can withdraw my request if it hasn't been processed yet

  Background:
    Given I am logged into the system
    And I have submitted a leave request



  Scenario: Cancel a pending leave request with an observation
    And I provide an observation "Sick leave, need to reschedule"
    Then the system allows me to cancel the request
    And the request status changes to "Canceled"
    And the cancellation date is recorded
    And the provided observation is saved


  Scenario: Cancel a pending leave request without an observation
    And I do not provide an observation
    Then the system allows me to cancel the request
    And the request status changes to "Canceled"
    And the cancellation date is recorded
    And no observation is saved


  Scenario: Attempt to cancel a granted leave request
    When I attempt to cancel my leave request that is currently "Granted"
    Then the system prevents me from canceling the request
    And an error message is displayed: "This request cannot be canceled as it has already been approved"


  Scenario: Attempt to cancel a refused leave request
    When I attempt to cancel my leave request that is currently "Refused"
    Then the system prevents me from canceling the request
    And an error message is displayed: "This request cannot be canceled as it has already been rejected"


  Scenario: Attempt to cancel a leave request that is already "Canceled"
    When I attempt to cancel my leave request that is currently "Canceled"
    Then the system prevents me from canceling the request
    And an error message is displayed: "This request is already canceled"


  Scenario: Attempt to cancel a leave request that is "Under Validation"
    And I provide an observation "Meeting conflict, need to adjust dates"
    Then the system allows me to cancel the request
    And the request status changes to "Canceled"
    And the cancellation date is recorded
    And the provided observation is saved
### Key Notes:
1. **Statuses Covered**:
   - `Pending` (cancelable)
   - `Under Validation` (cancelable)
   - `Granted`/`Refused`/`Canceled` (non-cancelable, with appropriate error messages).

2. **Observation Handling**:
   - Scenarios include both cases where the user provides an observation and where they don’t.

3. **Assumptions**:
   - The system displays clear error messages for invalid cancellation attempts.
   - The cancellation date is automatically recorded by the system.
   - The user is logged in (covered in `Background`). Adjust if needed (e.g., add steps for authentication).
