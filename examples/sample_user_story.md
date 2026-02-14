User Story — Refuse Leave Request
As an Administrator or Team Lead, I want to refuse an employee's leave request, So that I can properly manage absences when conditions or justifications are not satisfactory.
Business Rules — Refuse Leave Request
The user must be authenticated and belong to the validation chain.
A request can only be refused if its status is "Pending" or "In Progress".
A reason for refusal is mandatory to validate the action.
A request that is already refused, granted, or canceled cannot be refused again.
Upon refusal:
The status changes to "Refused".
The refusal date and reason are recorded.
The manager's observation can be recorded if provided.
The system must confirm the operation with a clear message.
Acceptance Criteria — Refuse Leave Request
The user can view the complete details of the request before deciding.
The user can enter an observation (optional).
The user must select a reason for refusal.
If no reason is selected, validation is impossible.
If the request is already refused, granted, or canceled, the refusal is blocked.
If the user is not authorized for this validation level, the system blocks the action.
Once refused:
The status changes to "Refused".
The user, date, reason, and observation are recorded.
The system displays: "Request refused successfully".

