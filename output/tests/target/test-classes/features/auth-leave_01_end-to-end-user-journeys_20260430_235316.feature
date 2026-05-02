Feature: End-to-End User Journeys
  Test scenarios covering all microservices

  Scenario: [AUT-001] Create valid user with all required fields (happy_path)
    Given Setup for business rule: Create valid user with all required fields
    When POST /api/admin/create-employee executed
    Then Returns a successful response and enforces: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-002] Fetch existing user by ID (happy_path)
    Given Setup for business rule: Fetch existing user by ID
    When GET /api/users/{id} executed
    Then Returns a successful response and enforces: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-003] Update user details (happy_path)
    Given Setup for business rule: Update user details
    When GET /api/users/{id} executed
    Then Returns a successful response and enforces: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-004] List all users in department (happy_path)
    Given Setup for business rule: List all users in department
    When GET /api/admin/departments/{id} executed
    Then Returns a successful response and enforces: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-005] Assign user to valid department (happy_path)
    Given Setup for business rule: Assign user to valid department
    When PUT /api/admin/departments/{id} executed
    Then Returns a successful response and enforces: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [LEA-001] Create valid leave request with future dates (happy_path)
    Given Setup for business rule: Create valid leave request with future dates
    When POST /api/leave-requests/create executed
    Then Returns a successful response and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-002] Retrieve created leave request (happy_path)
    Given Setup for business rule: Retrieve created leave request
    When GET /api/leave-requests/search executed
    Then Returns a successful response and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-003] Approve pending leave request as Team Leader (happy_path)
    Given Setup for business rule: Approve pending leave request as Team Leader
    When PUT /api/leave-requests/{id}/approve executed
    Then Returns a successful response and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-004] Reject pending leave request as Employer (happy_path)
    Given Setup for business rule: Reject pending leave request as Employer
    When PUT /api/leave-requests/{id}/reject executed
    Then Returns a successful response and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-005] List all leave requests for user (happy_path)
    Given Setup for business rule: List all leave requests for user
    When GET /api/leave-requests/search executed
    Then Returns a successful response and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-006] Search leave requests by date range (happy_path)
    Given Setup for business rule: Search leave requests by date range
    When GET /api/leave-requests/search executed
    Then Returns a successful response and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [AUT-006E] Create user with missing email (error_case)
    Given Precondition for error: Create user with missing email
    When POST /api/admin/create-employee called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-007E] Create user with duplicate email (error_case)
    Given Precondition for error: Create user with duplicate email
    When POST /api/admin/create-employee called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-008E] Fetch non-existent user (404) (error_case)
    Given Precondition for error: Fetch non-existent user (404)
    When GET /api/users/{id} called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-009E] Update user with invalid role (error_case)
    Given Precondition for error: Update user with invalid role
    When POST /api/admin/create-employee called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-010E] Assign user to non-existent department (error_case)
    Given Precondition for error: Assign user to non-existent department
    When POST /api/admin/departments/create called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [LEA-007E] Create leave with past dates (rejected) (error_case)
    Given Precondition for error: Create leave with past dates (rejected)
    When POST /api/leave-requests/create called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-008E] Create leave with fromDate > toDate (rejected) (error_case)
    Given Precondition for error: Create leave with fromDate > toDate (rejected)
    When POST /api/leave-requests/create called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-009E] Create overlapping leave request (rejected) (error_case)
    Given Precondition for error: Create overlapping leave request (rejected)
    When POST /api/leave-requests/create called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-010E] Request more than 30 days per year (rejected) (error_case)
    Given Precondition for error: Request more than 30 days per year (rejected)
    When POST /api/leave-requests/create called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-011E] Request more than 5 consecutive days (rejected) (error_case)
    Given Precondition for error: Request more than 5 consecutive days (rejected)
    When POST /api/leave-requests/create called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-012E] Create leave without authentication (401) (error_case)
    Given Precondition for error: Create leave without authentication (401)
    When POST /api/leave-requests/create called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-013E] Approve leave that's not PENDING (rejected) (error_case)
    Given Precondition for error: Approve leave that's not PENDING (rejected)
    When PUT /api/leave-requests/{id}/approve called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-014E] Try to approve as non-Team Leader (403) (error_case)
    Given Precondition for error: Try to approve as non-Team Leader (403)
    When PUT /api/leave-requests/{id}/approve called with invalid or missing data
    Then Returns a 4xx error when this rule is violated: Leave dates must be in the future (cannot be past dates)

  Scenario: [AUT-015S] Access user endpoint without JWT token (401) (security)
    Given Security condition: Access user endpoint without JWT token (401)
    When GET /api/users/search-ids accessed under restricted authorization
    Then Returns 401 Unauthorized

  Scenario: [AUT-016S] Access user endpoint with expired token (401) (security)
    Given Security condition: Access user endpoint with expired token (401)
    When POST /api/auth/change-password accessed under restricted authorization
    Then Returns 401 Unauthorized

  Scenario: [AUT-017S] Non-admin user trying to delete another user (403) (security)
    Given Security condition: Non-admin user trying to delete another user (403)
    When POST /api/admin/create-employee accessed under restricted authorization
    Then Returns 403 Forbidden

  Scenario: [AUT-018S] Team leader trying to access other department (403) (security)
    Given Security condition: Team leader trying to access other department (403)
    When GET /api/admin/departments accessed under restricted authorization
    Then Returns 403 Forbidden

  Scenario: [LEA-021S] Access leave endpoint without JWT token (401) (security)
    Given Security condition: Access leave endpoint without JWT token (401)
    When POST /api/leave-requests/create accessed under restricted authorization
    Then Returns 401 Unauthorized

  Scenario: [LEA-022S] Access other user's leave request without permission (403) (security)
    Given Security condition: Access other user's leave request without permission (403)
    When POST /api/leave-requests/create accessed under restricted authorization
    Then Returns 403 Forbidden

  Scenario: [LEA-023S] Team leader approving leave outside their department (403) (security)
    Given Security condition: Team leader approving leave outside their department (403)
    When PUT /api/leave-requests/{id}/approve accessed under restricted authorization
    Then Returns 403 Forbidden

  Scenario: [LEA-024S] Non-Employer role trying to reject leave (403) (security)
    Given Security condition: Non-Employer role trying to reject leave (403)
    When PUT /api/leave-requests/{id}/reject accessed under restricted authorization
    Then Returns 403 Forbidden

  Scenario: [AUT-011X] User ID at boundary (0, 1, 9999999) (edge_case)
    Given Edge case condition: User ID at boundary (0, 1, 9999999)
    When GET /api/users/search-ids called with boundary values
    Then Handles the boundary condition gracefully with the correct outcome

  Scenario: [AUT-012X] Department with no users (edge_case)
    Given Edge case condition: Department with no users
    When GET /api/admin/departments called with boundary values
    Then Handles the boundary condition gracefully with the correct outcome

  Scenario: [AUT-013X] User with special characters in name (edge_case)
    Given Edge case condition: User with special characters in name
    When GET /api/users/search-ids called with boundary values
    Then Handles the boundary condition gracefully with the correct outcome

  Scenario: [AUT-014X] Empty department name (edge_case)
    Given Edge case condition: Empty department name
    When GET /api/admin/departments called with boundary values
    Then Handles the boundary condition gracefully with the correct outcome

  Scenario: [LEA-015X] Same start and end date (0 days leave) (edge_case)
    Given Edge case condition: Same start and end date (0 days leave)
    When PUT /api/admin/holidays/{id} called with boundary values
    Then Handles the boundary condition gracefully with the correct outcome

  Scenario: [LEA-016X] Leave spanning weekends (edge_case)
    Given Edge case condition: Leave spanning weekends
    When POST /api/leave-requests/create called with boundary values
    Then Handles the boundary condition gracefully with the correct outcome

  Scenario: [LEA-017X] Leave on public holidays (edge_case)
    Given Edge case condition: Leave on public holidays
    When GET /api/admin/holidays called with boundary values
    Then Handles the boundary condition gracefully with the correct outcome

  Scenario: [LEA-018X] User with zero leave balance remaining (edge_case)
    Given Edge case condition: User with zero leave balance remaining
    When POST /api/balances/init/{userId} called with boundary values
    Then Handles the boundary condition gracefully with the correct outcome

  Scenario: [LEA-019X] Multiple approvals for same request (edge_case)
    Given Edge case condition: Multiple approvals for same request
    When POST /api/leave-requests/create called with boundary values
    Then Handles the boundary condition gracefully with the correct outcome

  Scenario: [LEA-020X] Reject already approved leave (rejected) (edge_case)
    Given Edge case condition: Reject already approved leave (rejected)
    When PUT /api/leave-requests/{id}/reject called with boundary values
    Then Handles the boundary condition gracefully with the correct outcome

  Scenario: [E2E-001] User Authentication → Leave Request Flow (integration)
    Given User authenticates with conge service → Gets JWT token -> User creates leave request in DemandeConge with token
    When DemandeConge calls conge to verify user role -> Team leader receives notification of pending leave -> Team leader approves leave
    Then User receives approval notification

  Scenario: [E2E-002] Overlapping Leave Rejection (integration)
    Given User creates leave from 2026-05-01 to 2026-05- -> User tries to create overlapping leave 2026-05-05 to 2026-05-
    When Services exchange data to complete the workflow
    Then System rejects second request

  Scenario: [E2E-003] Role-Based Approval Workflow (integration)
    Given User (Employee) creates leave request -> Team Leader with different role tries to approve
    When System verifies Team Leader role from conge -> Team Leader successfully approves
    Then Employer verifies approval in audit log

  Scenario: [E2E-004] Integration rule: Verify user exists in conge service before creating leave (integration)
    Given A cross-service workflow is in progress
    When One service validates or enriches data by calling another service
    Then Verify user exists in conge service before creating leave

  Scenario: [E2E-005] Integration rule: Fetch user role from conge to authorize approve/reject (integration)
    Given A cross-service workflow is in progress
    When One service validates or enriches data by calling another service
    Then Fetch user role from conge to authorize approve/reject

  Scenario: [E2E-006] Integration rule: Validate user department from conge for team leader scope (integration)
    Given A cross-service workflow is in progress
    When One service validates or enriches data by calling another service
    Then Validate user department from conge for team leader scope
