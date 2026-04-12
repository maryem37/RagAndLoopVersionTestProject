```markdown

# COMPREHENSIVE USER STORY WITH ERROR HANDLING & EDGE CASES

## Base User Story — Cancel Leave Request
As an employee, I want to cancel a pending leave request, So that I can withdraw a request that has not yet been granted.

### Business Rules — Cancel Leave Request
- Only requests that have not been granted (pending or under validation) can be canceled
- A request that is already canceled, granted, refused, or passed cannot be canceled
- The system must record the cancellation date and the observation if the user provides one
- Upon cancellation, the request status changes to "Canceled"

### Acceptance Criteria — Cancel Leave Request
- The employee can view their pending or in-progress requests
- The employee can select a request and enter a cancellation observation (optional)
- If the request is valid for cancellation, the status changes to "Canceled" and the cancellation date is recorded
- If the request has already passed, an appropriate error message is displayed: "Action impossible: the period concerned by this request has already passed."
- If the request is already canceled, an appropriate error message is displayed: "This request has been canceled and can no longer be processed."
- If the request is refused, an appropriate error message is displayed: "This request has already been refused."
- If the request is granted, an appropriate error message is displayed: "This request has already been validated."
- The system displays "Request canceled successfully" after confirmation

---

## ERROR HANDLING - Invalid Request Data (400 Bad Request)

### Missing Required Fields
- When a user submits missing required fields (id, startDate, endDate), the system shall return HTTP 400 Bad Request with field validation errors
- When cancellation reason is required but not provided, return 400 with error message

### Malformed Data
- When a user submits malformed JSON, the system shall return HTTP 400 Bad Request with JSON parse error
- When a user submits an invalid date format (not ISO 8601), the system shall return HTTP 400 Bad Request with date format error
- When a user submits empty request body, the system shall return HTTP 400 Bad Request

### Data Type Validation
- When userId is not a number, the system shall return HTTP 400 Bad Request
- When requestId is not a number, the system shall return HTTP 400 Bad Request
- When dates have invalid format, the system shall return HTTP 400 Bad Request

---

## SECURITY REQUIREMENTS - Authentication & Authorization

### Authentication Errors (401 Unauthorized)
- When a request is made without JWT token, the system shall return HTTP 401 Unauthorized
- When a request is made with expired JWT token, the system shall return HTTP 401 Unauthorized with token expiration message
- When a request is made with invalid JWT token format (corrupted, wrong signature), the system shall return HTTP 401 Unauthorized
- When JWT token cannot be decoded, the system shall return HTTP 401 Unauthorized

### Authorization Errors (403 Forbidden)
- When a non-admin user attempts admin operations (create department), the system shall return HTTP 403 Forbidden
- When a user attempts to cancel another user's leave request without authorization, return 403 Forbidden
- When a request is made without proper permissions, the system shall return HTTP 403 Forbidden
- When an employee tries to approve leave (team leader only), return 403 Forbidden

---

## NOT FOUND ERRORS (404 Not Found)

### Resource Does Not Exist
- When a leave request ID does not exist, the system shall return HTTP 404 Not Found
- When a department ID does not exist, the system shall return HTTP 404 Not Found
- When a user ID does not exist, the system shall return HTTP 404 Not Found
- When an employee ID does not exist, the system shall return HTTP 404 Not Found

---

## CONFLICT & CONCURRENCY (409 Conflict)

### State Conflicts
- When a user attempts to cancel an already-canceled request, the system shall return HTTP 409 Conflict with message: "This request has been canceled and can no longer be processed."
- When a user attempts to cancel an already-approved request, the system shall return HTTP 409 Conflict with message: "This request has already been validated."
- When a user attempts to cancel a refused request, the system shall return HTTP 409 Conflict with message: "This request has already been refused."

### Concurrency Issues
- When two users attempt concurrent modifications of the same resource, the system shall return HTTP 409 Conflict with version mismatch error
- When a user attempts to create overlapping leave requests, the system shall return HTTP 409 Conflict or detect and prevent overlap
- When a duplicate resource creation is attempted (same key), the system shall return HTTP 409 Conflict

---

## EDGE CASES & BOUNDARY CONDITIONS

### Boundary Values for IDs
- When a user provides boundary value IDs (0, negative, max integer), the system shall handle gracefully or reject with 400/404
- When ID is 0, the system should return 404 Not Found or 400 Bad Request
- When ID is negative, the system should return 400 Bad Request or 404 Not Found
- When ID exceeds max integer (2147483647), handle gracefully

### Empty and Null Values
- When a user provides empty string for required fields, the system shall validate and reject appropriately with 400 Bad Request
- When a user provides null values for optional fields, the system shall handle gracefully
- When a user provides empty object {}, the system shall reject with 400 Bad Request

### String Length and Content
- When a user provides very long strings (5000+ characters), the system shall reject or truncate with 400 Bad Request
- When a user provides special characters (SQL keywords, XSS scripts <script>, unicode), the system shall escape or reject appropriately
- When strings contain SQL injection attempts ('; DROP TABLE--), the system shall escape or reject

### Numeric Boundary Values
- When a user provides negative numbers for duration fields, the system shall reject with 400 Bad Request validation error
- When a user provides zero for duration, the system shall reject or accept based on business rules
- When a user provides very large numbers (exceeding int/long max), handle appropriately

### Date Boundary Values
- When a user provides dates at boundaries (epoch 1970-01-01, year 1900, year 2100), the system shall validate date range
- When startDate is after endDate, the system shall return 400 Bad Request
- When past dates are submitted for future leave, handle based on business rules

### Whitespace Handling
- When a user provides strings with leading/trailing whitespace, the system shall trim or handle appropriately
- When a user provides only whitespace in required fields, treat as empty and reject with 400 Bad Request

### Request Volume & Performance
- When rapid sequential requests are sent (100+ per second), the system shall handle without race conditions
- When a batch operation with 1000+ records is attempted, the system shall handle or reject with size limit error
- When multiple concurrent requests modify same resource, system must be thread-safe

---

## SERVICE INTEGRATION & WORKFLOWS

### Service Dependencies
- When a user creates a leave request while the balance service is unavailable, the system shall return HTTP 503 Service Unavailable
- When inter-service communication fails, the system shall return 503 Service Unavailable

### Timeout & Performance
- When a request timeout occurs (service slow > 30s), the system shall return HTTP 504 Gateway Timeout or 408 Request Timeout
- When database connection pool is exhausted, the system shall return 503 Service Unavailable

### Database Errors
- When a database connection error occurs, the system shall return HTTP 503 Service Unavailable
- When a database transaction fails, rollback and return appropriate error

### Cross-Service Validation
- When an inter-service JWT validation fails between services, the system shall return HTTP 401 Unauthorized
- When service-to-service call times out, return 504 Gateway Timeout

### Cascading Operations
- When cascading delete is needed (department delete with employees), the system shall handle properly or prevent deletion
- When deleting resource with related data, validate impact or cascade delete appropriately

---

## INTEGRATION FLOW SCENARIOS

### Complete User Journeys
- User authenticates → receives JWT token → creates leave request → cancels leave request → receives confirmation
- Team leader authenticates → views all employee leave requests → approves/rejects requests

### Multi-Service Interactions
- DemandeConge calls conge service for balance verification → receives response → updates balance
- conge service validates user role from enum values (employee, team_leader, admin)
- Overlapping leave detection across all leave types

### Error Recovery
- User receives 401 → re-authenticates → retries request → succeeds
- Service unavailable temporarily → client retries → succeeds
- Concurrent modification → client receives 409 → retries with fresh data → succeeds

```
