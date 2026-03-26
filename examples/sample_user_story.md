
User Story — Cancel Leave Request
As an employee, I want to cancel a pending leave request, So that I can withdraw a request that has not yet been granted.
Business Rules — Cancel Leave Request
Only requests that have not been granted (pending or under validation) can be canceled.
A request that is already canceled, granted, refused, or passed cannot be canceled.
The system must record the cancellation date and the observation if the user provides one.
Upon cancellation, the request status changes to "Canceled".

Acceptance Criteria — Cancel Leave Request
The employee can view their pending or in-progress requests.
The employee can select a request and enter a cancellation observation (optional).
If the request is valid for cancellation, the status changes to "Canceled" and the cancellation date is recorded.
If the request has already passed, an appropriate error message is displayed: "Action impossible: the period concerned by this request has already passed."
If the request is already canceled, an appropriate error message is displayed: "This request has been canceled and can no longer be processed."
If the request is refused, an appropriate error message is displayed: "This request has already been refused."
If the request is granted, an appropriate error message is displayed: "This request has already been validated."
The system displays "Request canceled successfully" after confirmation.
