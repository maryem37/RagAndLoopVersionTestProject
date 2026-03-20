User Story — Cancel Leave Request
As an employee, I want to cancel a pending leave request,
so that I can withdraw a request that has not yet been granted.

Business Rules — Cancel Leave Request
Only pending requests can be canceled by the employee who owns them.
A request that is already canceled cannot be canceled again.
An employee without a valid token cannot cancel any request.

Acceptance Criteria — Cancel Leave Request
The employee logs in with email "jane.smith@example.com" and password "Secure@567".
The employee creates a pending leave request with future dates, type ANNUAL_LEAVE,
periodType JOURNEE_COMPLETE.
When the employee cancels the pending request, the system responds with
"Leave request cancelled successfully."
If the employee tries to cancel the same request again, the system returns an error:
"This leave request has already been cancelled and cannot be processed."
If a user with an invalid token tries to cancel a request,
the system blocks the action with HTTP 401 or 403.