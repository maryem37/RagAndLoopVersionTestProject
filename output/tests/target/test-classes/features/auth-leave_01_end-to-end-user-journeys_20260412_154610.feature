Feature: End-to-End User Journeys
  Test scenarios covering all microservices

  Scenario: [AUT-001] [CRITICAL] Create valid user with all required fields (happy_path)
    Given Preconditions met for: Create valid user with all required fields
    When GET /api/users/{id} executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [AUT-002] [CRITICAL] Fetch existing user by ID (happy_path)
    Given Preconditions met for: Fetch existing user by ID
    When GET /api/users/{id} executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [AUT-003] [CRITICAL] Update user details (happy_path)
    Given Preconditions met for: Update user details
    When GET /api/users/{id} executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [AUT-004] [CRITICAL] List all users in department (happy_path)
    Given Preconditions met for: List all users in department
    When GET /api/admin/departments/{id} executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [AUT-005] [CRITICAL] Assign user to valid department (happy_path)
    Given Preconditions met for: Assign user to valid department
    When PUT /api/admin/departments/{id} executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [AUT-006] Create valid user with all required fields (happy_path)
    Given Setup for business rule: Create valid user with all required fields
    When POST /api/admin/create-employee executed
    Then Returns 200/201 and enforces: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-007] Fetch existing user by ID (happy_path)
    Given Setup for business rule: Fetch existing user by ID
    When GET /api/users/search-ids executed
    Then Returns 200/201 and enforces: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-008] Update user details (happy_path)
    Given Setup for business rule: Update user details
    When GET /api/users/search-ids executed
    Then Returns 200/201 and enforces: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-009] List all users in department (happy_path)
    Given Setup for business rule: List all users in department
    When GET /api/admin/departments executed
    Then Returns 200/201 and enforces: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [AUT-010] Assign user to valid department (happy_path)
    Given Setup for business rule: Assign user to valid department
    When POST /api/admin/departments/create executed
    Then Returns 200/201 and enforces: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION

  Scenario: [LEA-001] [CRITICAL] Create valid leave request with future dates (happy_path)
    Given Preconditions met for: Create valid leave request with future dates
    When GET /api/leave-requests/search executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [LEA-002] [CRITICAL] Retrieve created leave request (happy_path)
    Given Preconditions met for: Retrieve created leave request
    When GET /api/leave-requests/search executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [LEA-003] [CRITICAL] Approve pending leave request as Team Leader (happy_path)
    Given Preconditions met for: Approve pending leave request as Team Leader
    When PUT /api/leave-requests/{id}/approve executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [LEA-004] [CRITICAL] Reject pending leave request as Employer (happy_path)
    Given Preconditions met for: Reject pending leave request as Employer
    When PUT /api/leave-requests/{id}/reject executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [LEA-005] [CRITICAL] List all leave requests for user (happy_path)
    Given Preconditions met for: List all leave requests for user
    When GET /api/leave-requests/search executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [LEA-006] [CRITICAL] Search leave requests by date range (happy_path)
    Given Preconditions met for: Search leave requests by date range
    When GET /api/leave-requests/search executed per business requirement
    Then Returns success response (200/201) and follows business rule

  Scenario: [LEA-007] Create valid leave request with future dates (happy_path)
    Given Setup for business rule: Create valid leave request with future dates
    When POST /api/leave-requests/create executed
    Then Returns 200/201 and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-008] Retrieve created leave request (happy_path)
    Given Setup for business rule: Retrieve created leave request
    When POST /api/leave-requests/create executed
    Then Returns 200/201 and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-009] Approve pending leave request as Team Leader (happy_path)
    Given Setup for business rule: Approve pending leave request as Team Leader
    When PUT /api/leave-requests/{id}/approve executed
    Then Returns 200/201 and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-010] Reject pending leave request as Employer (happy_path)
    Given Setup for business rule: Reject pending leave request as Employer
    When PUT /api/leave-requests/{id}/reject executed
    Then Returns 200/201 and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-011] List all leave requests for user (happy_path)
    Given Setup for business rule: List all leave requests for user
    When GET /api/balances/{userId} executed
    Then Returns 200/201 and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-012] Search leave requests by date range (happy_path)
    Given Setup for business rule: Search leave requests by date range
    When GET /api/leave-requests/search executed
    Then Returns 200/201 and enforces: Leave dates must be in the future (cannot be past dates)

  Scenario: [LEA-031C] [COVERAGE] Update leave balances with valid annual and recovery values (happy_path)
    Given Coverage setup is ready for leave
    When PUT /api/balances/{userId} executed
    Then Returns success response (200/201) and follows business rule

  Scenario: [LEA-032C] [COVERAGE] Cancel an existing leave request (happy_path)
    Given Coverage setup is ready for leave
    When PUT /api/leave-requests/{id}/cancel executed
    Then Returns success response (200/201) and follows business rule

  Scenario: [LEA-033C] [COVERAGE] Create a public holiday entry (happy_path)
    Given Coverage setup is ready for leave
    When POST /api/admin/holidays executed
    Then Returns success response (200/201) and follows business rule

  Scenario: [AUT-011E] Create user with missing email (error_case)
    Given Precondition for error: Create user with missing email
    When POST /api/admin/create-employee called with invalid/missing data
    Then Returns 4xx error when: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION is violated

  Scenario: [AUT-012E] Create user with duplicate email (error_case)
    Given Precondition for error: Create user with duplicate email
    When POST /api/admin/create-employee called with invalid/missing data
    Then Returns 4xx error when: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION is violated

  Scenario: [AUT-013E] Fetch non-existent user (404) (error_case)
    Given Precondition for error: Fetch non-existent user (404)
    When GET /api/users/search-ids called with invalid/missing data
    Then Returns 4xx error when: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION is violated

  Scenario: [AUT-014E] Update user with invalid role (error_case)
    Given Precondition for error: Update user with invalid role
    When GET /api/users/search-ids called with invalid/missing data
    Then Returns 4xx error when: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION is violated

  Scenario: [AUT-015E] Assign user to non-existent department (error_case)
    Given Precondition for error: Assign user to non-existent department
    When POST /api/admin/departments/create called with invalid/missing data
    Then Returns 4xx error when: User roles are: EMPLOYER, TEAM_LEADER, ADMINISTRATION is violated

  Scenario: [LEA-013E] Create leave with past dates (rejected) (error_case)
    Given Precondition for error: Create leave with past dates (rejected)
    When PUT /api/leave-requests/{id}/reject called with invalid/missing data
    Then Returns 4xx error when: Leave dates must be in the future (cannot be past dates) is violated

  Scenario: [LEA-014E] Create leave with fromDate > toDate (rejected) (error_case)
    Given Precondition for error: Create leave with fromDate > toDate (rejected)
    When PUT /api/leave-requests/{id}/reject called with invalid/missing data
    Then Returns 4xx error when: Leave dates must be in the future (cannot be past dates) is violated

  Scenario: [LEA-015E] Create overlapping leave request (rejected) (error_case)
    Given Precondition for error: Create overlapping leave request (rejected)
    When PUT /api/leave-requests/{id}/reject called with invalid/missing data
    Then Returns 4xx error when: Leave dates must be in the future (cannot be past dates) is violated

  Scenario: [LEA-016E] Request more than 30 days per year (rejected) (error_case)
    Given Precondition for error: Request more than 30 days per year (rejected)
    When PUT /api/leave-requests/{id}/reject called with invalid/missing data
    Then Returns 4xx error when: Leave dates must be in the future (cannot be past dates) is violated

  Scenario: [LEA-017E] Request more than 5 consecutive days (rejected) (error_case)
    Given Precondition for error: Request more than 5 consecutive days (rejected)
    When PUT /api/leave-requests/{id}/reject called with invalid/missing data
    Then Returns 4xx error when: Leave dates must be in the future (cannot be past dates) is violated

  Scenario: [LEA-018E] Create leave without authentication (401) (error_case)
    Given Precondition for error: Create leave without authentication (401)
    When POST /api/leave-requests/create called with invalid/missing data
    Then Returns 4xx error when: Leave dates must be in the future (cannot be past dates) is violated

  Scenario: [LEA-019E] Approve leave that's not PENDING (rejected) (error_case)
    Given Precondition for error: Approve leave that's not PENDING (rejected)
    When PUT /api/leave-requests/{id}/approve called with invalid/missing data
    Then Returns 4xx error when: Leave dates must be in the future (cannot be past dates) is violated

  Scenario: [LEA-020E] Try to approve as non-Team Leader (403) (error_case)
    Given Precondition for error: Try to approve as non-Team Leader (403)
    When PUT /api/leave-requests/{id}/approve called with invalid/missing data
    Then Returns 4xx error when: Leave dates must be in the future (cannot be past dates) is violated

  Scenario: [AUT-020S] Access user endpoint without JWT token (401) (security)
    Given Security constraint: Access user endpoint without JWT token (401)
    When POST /api/auth/login accessed under security restriction
    Then Returns 401 Unauthorized

  Scenario: [AUT-021S] Access user endpoint with expired token (401) (security)
    Given Security constraint: Access user endpoint with expired token (401)
    When POST /api/auth/login accessed under security restriction
    Then Returns 401 Unauthorized

  Scenario: [AUT-022S] Non-admin user trying to delete another user (403) (security)
    Given Security constraint: Non-admin user trying to delete another user (403)
    When POST /api/admin/create-employee accessed under security restriction
    Then Returns 403 Forbidden

  Scenario: [AUT-023S] Team leader trying to access other department (403) (security)
    Given Security constraint: Team leader trying to access other department (403)
    When GET /api/admin/departments accessed under security restriction
    Then Returns 403 Forbidden

  Scenario: [LEA-027S] Access leave endpoint without JWT token (401) (security)
    Given Security constraint: Access leave endpoint without JWT token (401)
    When POST /api/leave-requests/create accessed under security restriction
    Then Returns 401 Unauthorized

  Scenario: [LEA-028S] Access other user's leave request without permission (403) (security)
    Given Security constraint: Access other user's leave request without permission (403)
    When POST /api/balances/init/{userId} accessed under security restriction
    Then Returns 403 Forbidden

  Scenario: [LEA-029S] Team leader approving leave outside their department (403) (security)
    Given Security constraint: Team leader approving leave outside their department (403)
    When POST /api/leave-requests/create accessed under security restriction
    Then Returns 403 Forbidden

  Scenario: [LEA-030S] Non-Employer role trying to reject leave (403) (security)
    Given Security constraint: Non-Employer role trying to reject leave (403)
    When PUT /api/leave-requests/{id}/reject accessed under security restriction
    Then Returns 403 Forbidden

  Scenario: [AUT-016X] User ID at boundary (0, 1, 9999999) (edge_case)
    Given Edge case condition: User ID at boundary (0, 1, 9999999)
    When GET /api/users/search-ids called with boundary/edge values
    Then Handles gracefully and returns appropriate status or error

  Scenario: [AUT-017X] Department with no users (edge_case)
    Given Edge case condition: Department with no users
    When GET /api/admin/departments called with boundary/edge values
    Then Handles gracefully and returns appropriate status or error

  Scenario: [AUT-018X] User with special characters in name (edge_case)
    Given Edge case condition: User with special characters in name
    When GET /api/users/search-ids called with boundary/edge values
    Then Handles gracefully and returns appropriate status or error

  Scenario: [AUT-019X] Empty department name (edge_case)
    Given Edge case condition: Empty department name
    When GET /api/admin/departments called with boundary/edge values
    Then Handles gracefully and returns appropriate status or error

  Scenario: [LEA-021X] Same start and end date (0 days leave) (edge_case)
    Given Edge case condition: Same start and end date (0 days leave)
    When PUT /api/admin/holidays/{id} called with boundary/edge values
    Then Handles gracefully and returns appropriate status or error

  Scenario: [LEA-022X] Leave spanning weekends (edge_case)
    Given Edge case condition: Leave spanning weekends
    When POST /api/leave-requests/create called with boundary/edge values
    Then Handles gracefully and returns appropriate status or error

  Scenario: [LEA-023X] Leave on public holidays (edge_case)
    Given Edge case condition: Leave on public holidays
    When GET /api/admin/holidays called with boundary/edge values
    Then Handles gracefully and returns appropriate status or error

  Scenario: [LEA-024X] User with zero leave balance remaining (edge_case)
    Given Edge case condition: User with zero leave balance remaining
    When POST /api/balances/init/{userId} called with boundary/edge values
    Then Handles gracefully and returns appropriate status or error

  Scenario: [LEA-025X] Multiple approvals for same request (edge_case)
    Given Edge case condition: Multiple approvals for same request
    When POST /api/leave-requests/create called with boundary/edge values
    Then Handles gracefully and returns appropriate status or error

  Scenario: [LEA-026X] Reject already approved leave (rejected) (edge_case)
    Given Edge case condition: Reject already approved leave (rejected)
    When PUT /api/leave-requests/{id}/reject called with boundary/edge values
    Then Handles gracefully and returns appropriate status or error

  Scenario: [E2E-001] User Authentication → Leave Request Flow (integration)
    Given User authenticates with conge service → Gets JWT token → User creates leave request in DemandeConge with token
    When DemandeConge calls conge to verify user role → Team leader receives notification of pending leave → Team leader approves leave
    Then User receives approval notification | Verify: Verify user exists in conge service before creating leave | Verify: Fetch user role from conge to authorize approve/reject

  Scenario: [E2E-002] Overlapping Leave Rejection (integration)
    Given User creates leave from 2026-05-01 to 2026-05- → User tries to create overlapping leave 2026-05-05 to 2026-05-
    When Services interact
    Then System rejects second request | Verify: Verify user exists in conge service before creating leave | Verify: Fetch user role from conge to authorize approve/reject

  Scenario: [E2E-003] Role-Based Approval Workflow (integration)
    Given User (Employee) creates leave request → Team Leader with different role tries to approve
    When System verifies Team Leader role from conge → Team Leader successfully approves
    Then Employer verifies approval in audit log | Verify: Verify user exists in conge service before creating leave | Verify: Fetch user role from conge to authorize approve/reject

  Scenario: [E2E-004] Integration Rule: Verify user exists in conge service before creating leave (integration)
    Given Leave request workflow initiated
    When DemandeConge service calls conge service per business rule
    Then ✓ Verify user exists in conge service before creating leave

  Scenario: [E2E-005] Integration Rule: Fetch user role from conge to authorize approve/reject (integration)
    Given Leave request workflow initiated
    When DemandeConge service calls conge service per business rule
    Then ✓ Fetch user role from conge to authorize approve/reject

  Scenario: [E2E-006] Integration Rule: Validate user department from conge for team leader scope (integration)
    Given Leave request workflow initiated
    When DemandeConge service calls conge service per business rule
    Then ✓ Validate user department from conge for team leader scope
