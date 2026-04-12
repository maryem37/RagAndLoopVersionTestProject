Feature: End-to-End User Journeys
  Test scenarios covering all microservices

  Scenario: [AUT-001] Valid GET to /api/admin/departments/{id} (happy_path)
    Given Valid parameters for GET /api/admin/departments/\{id\}
    When GET /api/admin/departments/\{id\} called with valid data
    Then Returns success response (200/201)

  Scenario: [AUT-002] Valid PUT to /api/admin/departments/{id} (happy_path)
    Given Valid parameters for PUT /api/admin/departments/\{id\}
    When PUT /api/admin/departments/\{id\} called with valid data
    Then Returns success response (200/201)

  Scenario: [AUT-003] Valid DELETE to /api/admin/departments/{id} (happy_path)
    Given Valid parameters for DELETE /api/admin/departments/\{id\}
    When DELETE /api/admin/departments/\{id\} called with valid data
    Then Returns success response (200/201)

  Scenario: [AUT-004] Valid POST to /api/auth/login (happy_path)
    Given Valid parameters for POST /api/auth/login
    When POST /api/auth/login called with valid data
    Then Returns success response (200/201)

  Scenario: [AUT-005] Valid POST to /api/admin/departments/create (happy_path)
    Given Valid parameters for POST /api/admin/departments/create
    When POST /api/admin/departments/create called with valid data
    Then Returns success response (200/201)

  Scenario: [AUT-006] Valid POST to /api/admin/create-employee (happy_path)
    Given Valid parameters for POST /api/admin/create-employee
    When POST /api/admin/create-employee called with valid data
    Then Returns success response (200/201)

  Scenario: [AUT-007] Valid GET to /api/users/{id} (happy_path)
    Given Valid parameters for GET /api/users/\{id\}
    When GET /api/users/\{id\} called with valid data
    Then Returns success response (200/201)

  Scenario: [AUT-008] Valid GET to /api/users/search-ids (happy_path)
    Given Valid parameters for GET /api/users/search-ids
    When GET /api/users/search-ids called with valid data
    Then Returns success response (200/201)

  Scenario: [AUT-009] Valid GET to /api/admin/departments (happy_path)
    Given Valid parameters for GET /api/admin/departments
    When GET /api/admin/departments called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-001] Valid PUT to /api/leave-requests/{id}/reject (happy_path)
    Given Valid parameters for PUT /api/leave-requests/\{id\}/reject
    When PUT /api/leave-requests/\{id\}/reject called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-002] Valid PUT to /api/leave-requests/{id}/cancel (happy_path)
    Given Valid parameters for PUT /api/leave-requests/\{id\}/cancel
    When PUT /api/leave-requests/\{id\}/cancel called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-003] Valid PUT to /api/leave-requests/{id}/approve (happy_path)
    Given Valid parameters for PUT /api/leave-requests/\{id\}/approve
    When PUT /api/leave-requests/\{id\}/approve called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-004] Valid GET to /api/balances/{userId} (happy_path)
    Given Valid parameters for GET /api/balances/\{userId\}
    When GET /api/balances/\{userId\} called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-005] Valid PUT to /api/balances/{userId} (happy_path)
    Given Valid parameters for PUT /api/balances/\{userId\}
    When PUT /api/balances/\{userId\} called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-006] Valid DELETE to /api/balances/{userId} (happy_path)
    Given Valid parameters for DELETE /api/balances/\{userId\}
    When DELETE /api/balances/\{userId\} called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-007] Valid GET to /api/admin/holidays/{id} (happy_path)
    Given Valid parameters for GET /api/admin/holidays/\{id\}
    When GET /api/admin/holidays/\{id\} called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-008] Valid PUT to /api/admin/holidays/{id} (happy_path)
    Given Valid parameters for PUT /api/admin/holidays/\{id\}
    When PUT /api/admin/holidays/\{id\} called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-009] Valid DELETE to /api/admin/holidays/{id} (happy_path)
    Given Valid parameters for DELETE /api/admin/holidays/\{id\}
    When DELETE /api/admin/holidays/\{id\} called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-010] Valid POST to /api/leave-requests/create (happy_path)
    Given Valid parameters for POST /api/leave-requests/create
    When POST /api/leave-requests/create called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-011] Valid POST to /api/balances/init/{userId} (happy_path)
    Given Valid parameters for POST /api/balances/init/\{userId\}
    When POST /api/balances/init/\{userId\} called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-012] Valid GET to /api/admin/holidays (happy_path)
    Given Valid parameters for GET /api/admin/holidays
    When GET /api/admin/holidays called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-013] Valid POST to /api/admin/holidays (happy_path)
    Given Valid parameters for POST /api/admin/holidays
    When POST /api/admin/holidays called with valid data
    Then Returns success response (200/201)

  Scenario: [LEA-014] Valid GET to /api/leave-requests/search (happy_path)
    Given Valid parameters for GET /api/leave-requests/search
    When GET /api/leave-requests/search called with valid data
    Then Returns success response (200/201)

  Scenario: [AUT-001E] Missing required fields for /api/admin/departments/{id} (error_case)
    Given Required parameters missing
    When GET /api/admin/departments/\{id\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [AUT-002E] Missing required fields for /api/admin/departments/{id} (error_case)
    Given Required parameters missing
    When PUT /api/admin/departments/\{id\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [AUT-003E] Missing required fields for /api/admin/departments/{id} (error_case)
    Given Required parameters missing
    When DELETE /api/admin/departments/\{id\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [AUT-004E] Missing required fields for /api/auth/login (error_case)
    Given Required parameters missing
    When POST /api/auth/login called without required fields
    Then Returns 400 Bad Request

  Scenario: [AUT-005E] Missing required fields for /api/admin/departments/create (error_case)
    Given Required parameters missing
    When POST /api/admin/departments/create called without required fields
    Then Returns 400 Bad Request

  Scenario: [AUT-006E] Missing required fields for /api/admin/create-employee (error_case)
    Given Required parameters missing
    When POST /api/admin/create-employee called without required fields
    Then Returns 400 Bad Request

  Scenario: [AUT-007E] Missing required fields for /api/users/{id} (error_case)
    Given Required parameters missing
    When GET /api/users/\{id\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [AUT-008E] Missing required fields for /api/users/search-ids (error_case)
    Given Required parameters missing
    When GET /api/users/search-ids called without required fields
    Then Returns 400 Bad Request

  Scenario: [AUT-009E] Missing required fields for /api/admin/departments (error_case)
    Given Required parameters missing
    When GET /api/admin/departments called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-001E] Missing required fields for /api/leave-requests/{id}/reject (error_case)
    Given Required parameters missing
    When PUT /api/leave-requests/\{id\}/reject called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-002E] Missing required fields for /api/leave-requests/{id}/cancel (error_case)
    Given Required parameters missing
    When PUT /api/leave-requests/\{id\}/cancel called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-003E] Missing required fields for /api/leave-requests/{id}/approve (error_case)
    Given Required parameters missing
    When PUT /api/leave-requests/\{id\}/approve called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-004E] Missing required fields for /api/balances/{userId} (error_case)
    Given Required parameters missing
    When GET /api/balances/\{userId\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-005E] Missing required fields for /api/balances/{userId} (error_case)
    Given Required parameters missing
    When PUT /api/balances/\{userId\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-006E] Missing required fields for /api/balances/{userId} (error_case)
    Given Required parameters missing
    When DELETE /api/balances/\{userId\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-007E] Missing required fields for /api/admin/holidays/{id} (error_case)
    Given Required parameters missing
    When GET /api/admin/holidays/\{id\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-008E] Missing required fields for /api/admin/holidays/{id} (error_case)
    Given Required parameters missing
    When PUT /api/admin/holidays/\{id\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-009E] Missing required fields for /api/admin/holidays/{id} (error_case)
    Given Required parameters missing
    When DELETE /api/admin/holidays/\{id\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-010E] Missing required fields for /api/leave-requests/create (error_case)
    Given Required parameters missing
    When POST /api/leave-requests/create called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-011E] Missing required fields for /api/balances/init/{userId} (error_case)
    Given Required parameters missing
    When POST /api/balances/init/\{userId\} called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-012E] Missing required fields for /api/admin/holidays (error_case)
    Given Required parameters missing
    When GET /api/admin/holidays called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-013E] Missing required fields for /api/admin/holidays (error_case)
    Given Required parameters missing
    When POST /api/admin/holidays called without required fields
    Then Returns 400 Bad Request

  Scenario: [LEA-014E] Missing required fields for /api/leave-requests/search (error_case)
    Given Required parameters missing
    When GET /api/leave-requests/search called without required fields
    Then Returns 400 Bad Request

  Scenario: [AUT-001S] Unauthorized access to /api/admin/departments/{id} (security)
    Given No authentication token provided
    When GET /api/admin/departments/\{id\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [AUT-002S] Unauthorized access to /api/admin/departments/{id} (security)
    Given No authentication token provided
    When PUT /api/admin/departments/\{id\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [AUT-003S] Unauthorized access to /api/admin/departments/{id} (security)
    Given No authentication token provided
    When DELETE /api/admin/departments/\{id\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [AUT-004S] Unauthorized access to /api/auth/login (security)
    Given No authentication token provided
    When POST /api/auth/login without JWT token
    Then Returns 401 Unauthorized

  Scenario: [AUT-005S] Unauthorized access to /api/admin/departments/create (security)
    Given No authentication token provided
    When POST /api/admin/departments/create without JWT token
    Then Returns 401 Unauthorized

  Scenario: [AUT-006S] Unauthorized access to /api/admin/create-employee (security)
    Given No authentication token provided
    When POST /api/admin/create-employee without JWT token
    Then Returns 401 Unauthorized

  Scenario: [AUT-007S] Unauthorized access to /api/users/{id} (security)
    Given No authentication token provided
    When GET /api/users/\{id\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [AUT-008S] Unauthorized access to /api/users/search-ids (security)
    Given No authentication token provided
    When GET /api/users/search-ids without JWT token
    Then Returns 401 Unauthorized

  Scenario: [AUT-009S] Unauthorized access to /api/admin/departments (security)
    Given No authentication token provided
    When GET /api/admin/departments without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-001S] Unauthorized access to /api/leave-requests/{id}/reject (security)
    Given No authentication token provided
    When PUT /api/leave-requests/\{id\}/reject without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-002S] Unauthorized access to /api/leave-requests/{id}/cancel (security)
    Given No authentication token provided
    When PUT /api/leave-requests/\{id\}/cancel without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-003S] Unauthorized access to /api/leave-requests/{id}/approve (security)
    Given No authentication token provided
    When PUT /api/leave-requests/\{id\}/approve without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-004S] Unauthorized access to /api/balances/{userId} (security)
    Given No authentication token provided
    When GET /api/balances/\{userId\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-005S] Unauthorized access to /api/balances/{userId} (security)
    Given No authentication token provided
    When PUT /api/balances/\{userId\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-006S] Unauthorized access to /api/balances/{userId} (security)
    Given No authentication token provided
    When DELETE /api/balances/\{userId\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-007S] Unauthorized access to /api/admin/holidays/{id} (security)
    Given No authentication token provided
    When GET /api/admin/holidays/\{id\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-008S] Unauthorized access to /api/admin/holidays/{id} (security)
    Given No authentication token provided
    When PUT /api/admin/holidays/\{id\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-009S] Unauthorized access to /api/admin/holidays/{id} (security)
    Given No authentication token provided
    When DELETE /api/admin/holidays/\{id\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-010S] Unauthorized access to /api/leave-requests/create (security)
    Given No authentication token provided
    When POST /api/leave-requests/create without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-011S] Unauthorized access to /api/balances/init/{userId} (security)
    Given No authentication token provided
    When POST /api/balances/init/\{userId\} without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-012S] Unauthorized access to /api/admin/holidays (security)
    Given No authentication token provided
    When GET /api/admin/holidays without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-013S] Unauthorized access to /api/admin/holidays (security)
    Given No authentication token provided
    When POST /api/admin/holidays without JWT token
    Then Returns 401 Unauthorized

  Scenario: [LEA-014S] Unauthorized access to /api/leave-requests/search (security)
    Given No authentication token provided
    When GET /api/leave-requests/search without JWT token
    Then Returns 401 Unauthorized

  Scenario: [AUT-001N] Non-existent resource for /api/admin/departments/{id} (error_case)
    Given Resource does not exist
    When GET /api/admin/departments/\{id\} with non-existent ID
    Then Returns 404 Not Found

  Scenario: [AUT-002N] Non-existent resource for /api/admin/departments/{id} (error_case)
    Given Resource does not exist
    When PUT /api/admin/departments/\{id\} with non-existent ID
    Then Returns 404 Not Found

  Scenario: [AUT-003N] Non-existent resource for /api/admin/departments/{id} (error_case)
    Given Resource does not exist
    When DELETE /api/admin/departments/\{id\} with non-existent ID
    Then Returns 404 Not Found

  Scenario: [AUT-007N] Non-existent resource for /api/users/{id} (error_case)
    Given Resource does not exist
    When GET /api/users/\{id\} with non-existent ID
    Then Returns 404 Not Found

  Scenario: [LEA-001N] Non-existent resource for /api/leave-requests/{id}/reject (error_case)
    Given Resource does not exist
    When PUT /api/leave-requests/\{id\}/reject with non-existent ID
    Then Returns 404 Not Found

  Scenario: [LEA-002N] Non-existent resource for /api/leave-requests/{id}/cancel (error_case)
    Given Resource does not exist
    When PUT /api/leave-requests/\{id\}/cancel with non-existent ID
    Then Returns 404 Not Found

  Scenario: [LEA-003N] Non-existent resource for /api/leave-requests/{id}/approve (error_case)
    Given Resource does not exist
    When PUT /api/leave-requests/\{id\}/approve with non-existent ID
    Then Returns 404 Not Found

  Scenario: [LEA-007N] Non-existent resource for /api/admin/holidays/{id} (error_case)
    Given Resource does not exist
    When GET /api/admin/holidays/\{id\} with non-existent ID
    Then Returns 404 Not Found

  Scenario: [LEA-008N] Non-existent resource for /api/admin/holidays/{id} (error_case)
    Given Resource does not exist
    When PUT /api/admin/holidays/\{id\} with non-existent ID
    Then Returns 404 Not Found

  Scenario: [LEA-009N] Non-existent resource for /api/admin/holidays/{id} (error_case)
    Given Resource does not exist
    When DELETE /api/admin/holidays/\{id\} with non-existent ID
    Then Returns 404 Not Found

  Scenario: [AUT-001X] Boundary values for /api/admin/departments/{id} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When GET /api/admin/departments/\{id\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [AUT-002X] Boundary values for /api/admin/departments/{id} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When PUT /api/admin/departments/\{id\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [AUT-003X] Boundary values for /api/admin/departments/{id} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When DELETE /api/admin/departments/\{id\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [AUT-004X] Boundary values for /api/auth/login (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When POST /api/auth/login with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [AUT-005X] Boundary values for /api/admin/departments/create (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When POST /api/admin/departments/create with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [AUT-006X] Boundary values for /api/admin/create-employee (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When POST /api/admin/create-employee with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [AUT-007X] Boundary values for /api/users/{id} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When GET /api/users/\{id\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [AUT-008X] Boundary values for /api/users/search-ids (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When GET /api/users/search-ids with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [AUT-009X] Boundary values for /api/admin/departments (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When GET /api/admin/departments with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-001X] Boundary values for /api/leave-requests/{id}/reject (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When PUT /api/leave-requests/\{id\}/reject with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-002X] Boundary values for /api/leave-requests/{id}/cancel (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When PUT /api/leave-requests/\{id\}/cancel with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-003X] Boundary values for /api/leave-requests/{id}/approve (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When PUT /api/leave-requests/\{id\}/approve with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-004X] Boundary values for /api/balances/{userId} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When GET /api/balances/\{userId\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-005X] Boundary values for /api/balances/{userId} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When PUT /api/balances/\{userId\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-006X] Boundary values for /api/balances/{userId} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When DELETE /api/balances/\{userId\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-007X] Boundary values for /api/admin/holidays/{id} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When GET /api/admin/holidays/\{id\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-008X] Boundary values for /api/admin/holidays/{id} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When PUT /api/admin/holidays/\{id\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-009X] Boundary values for /api/admin/holidays/{id} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When DELETE /api/admin/holidays/\{id\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-010X] Boundary values for /api/leave-requests/create (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When POST /api/leave-requests/create with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-011X] Boundary values for /api/balances/init/{userId} (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When POST /api/balances/init/\{userId\} with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-012X] Boundary values for /api/admin/holidays (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When GET /api/admin/holidays with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-013X] Boundary values for /api/admin/holidays (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When POST /api/admin/holidays with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [LEA-014X] Boundary values for /api/leave-requests/search (edge_case)
    Given Boundary value parameters (0, empty string, max int)
    When GET /api/leave-requests/search with boundary values
    Then Handles gracefully or rejects with clear error

  Scenario: [E2E-001] User Authentication → Leave Request Flow (integration)
    Given 1. User authenticates with conge service → Gets JWT token → 2. User creates leave request in DemandeConge with token
    When 3. DemandeConge calls conge to verify user role → 4. Team leader receives notification of pending leave → 5. Team leader approves leave
    Then Leave request successfully approved

  Scenario: [E2E-002] Overlapping Leave Rejection (integration)
    Given 1. User creates leave from 2026-05-01 to 2026-05-10 → 2. User tries to create overlapping leave 2026-05-05 to 2026-05-15
    When Services interact
    Then 409 Conflict - Overlapping leave detected

  Scenario: [E2E-003] Role-Based Approval Workflow (integration)
    Given 1. User (Employee) creates leave request → 2. Team Leader with different role tries to approve
    When 3. System verifies Team Leader role from conge → 4. Team Leader successfully approves
    Then Approval workflow executed with proper authorization
