User Story: Employee Authentication
As an employee I want to authenticate via the API so that I can access the system securely.

Acceptance Criteria:
- AC1: Employee can log in with valid email and password and receive a JWT token
- AC2: System returns 401 Unauthorized when credentials are invalid
- AC3: System returns 400 Bad Request when required fields are missing

Business Rules:
- BR1: The login endpoint is POST /api/auth/login
- BR2: Credentials must include email and password fields
- BR3: On success the response must contain a valid JWT token

---

User Story: Employee Leave Request Management
As an employee I want to create, consult, and cancel leave requests via the API so that I can manage my absences.

Acceptance Criteria:
- AC1: Employee can submit a leave request with fromDate, toDate, type, and userId
- AC2: Employee can cancel a pending leave request
- AC3: Employee cannot cancel a request that is already granted, refused, or canceled
- AC4: System returns the updated request status after each operation
- AC5: Unauthorized users cannot access leave request endpoints

Business Rules:
- BR1: Create endpoint is POST /api/leave-requests/create
- BR2: Cancel endpoint is PUT /api/leave-requests/{id}/cancel
- BR3: Required fields for creation: fromDate, toDate, type, userId
- BR4: Status transitions: Pending → Canceled (employee), Pending → Granted (approver)
- BR5: A request in status Granted, Refused, or Canceled cannot be canceled again

Error Messages:
- "Action impossible: the period concerned by this request has already passed."
- "This request has been canceled and can no longer be processed."
- "This request has already been refused."
- "This request has already been validated."

