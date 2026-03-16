User Story — Approve Leave Request
As an Administrator or Team Lead, I want to approve an employee's leave request, So that I can officially validate their absence according to the defined approval chain.
Business Rules — Approve Leave Request
The user must belong to the request's approval chain.
A request can only be approved if its status is "Pending" or "In Progress".
An approver cannot validate a request they have already previously approved.
Validation follows a hierarchical chain:
As long as the administrator has not approved, the request remains "In Progress".
When the final approver grants approval, the request status becomes "Granted".
Upon final validation:
The leave balance is deducted according to the type (annual, authorization, recovery).

Acceptance Criteria — Approve Leave Request
The user can view the complete details of the request before validation.
The user can add an observation (optional).
If the user is not authorized to validate this step, an error message is displayed: "You are not authorized to modify the status of this request."
If the request is not in a valid state ("Pending" or "In Progress"), validation is blocked.
If the user has already validated previously, the validation is refused.
If the user is the final approver:
The request status changes to "Granted".
The leave balance is adjusted according to the rules of the leave type.
Otherwise:
The status changes to "In Progress".
The system marks the manager's validation as TRUE.
After validation, the system displays "Request granted successfully".