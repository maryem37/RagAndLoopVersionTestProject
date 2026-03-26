# JWT in Microservices Testing: When, Why, and How

## Quick Answer

**Do you NEED JWT?**
- ✅ **YES, if** your services require authentication
- ❌ **NO, if** services are public or have no auth

**Are you currently using JWT?**
- ✅ **YES** - Already in `.env` and test_writer.py

---

## When to Use JWT

### ✅ **USE JWT When:**

1. **Services require authentication** (protected endpoints)
   ```java
   @PostMapping("/api/leave/request")
   @Secured("ROLE_EMPLOYEE")  // ← Requires authentication
   public LeaveRequest submitRequest() { ... }
   ```

2. **Service-to-service communication** (microservice calls other services)
   ```
   Employee Login (public)
   ↓ Returns JWT
   Leave Service (protected - needs JWT)
   ↓ Uses JWT to call Auth Service
   Payment Service (protected - needs JWT)
   ```

3. **Multiple user roles** (different access levels)
   ```
   ROLE_EMPLOYEE → Can request leave
   ROLE_MANAGER → Can approve leave
   ROLE_ADMIN → Can view all
   ```

4. **Session management** (stateless API)
   ```
   Client sends JWT in every request
   Server validates without database lookup (stateless)
   ```

### ❌ **DON'T USE JWT When:**

1. **All endpoints are public** (no authentication needed)
   ```yaml
   /api/public/status      # Public
   /api/public/health      # Public
   /api/public/docs        # Public
   ```

2. **Using session-based auth** (cookies, server-side sessions)
   ```
   Instead of JWT, use traditional sessions
   ```

3. **Testing only internal services** (no external clients)
   ```
   Only server-to-server calls, same infrastructure
   ```

---

## Your Current Setup: ✅ Using JWT

### **Evidence:**

**1. In `.env`:**
```env
TEST_JWT_TOKEN=eyJhbGciOiJIUzI1NiJ9...
TEST_USER_EMAIL=admin@test.com
TEST_USER_PASSWORD=admin123
```

**2. In `agents/test_writer.py`:**
```java
.header("Authorization", "Bearer invalid_token_for_test")  // Line 433
// Login scenario extracts JWT
String jwt = response.jsonPath().getString("jwt");
```

**3. In `config/settings.py`:**
```python
test_execution=SimpleNamespace(
    jwt_token=os.getenv("TEST_JWT_TOKEN")
)
```

**4. In `agents/test_executor.py`:**
```python
if jwt_token:
    parts.append(f"-DTEST_JWT_TOKEN={jwt_token}")
```

---

## JWT Flow in Your System

```
┌─────────────────────────────────────────┐
│ Test Starts                             │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│ 1. Load JWT from .env                   │
│    TEST_JWT_TOKEN=eyJ...                │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│ 2. Test Writer generates Java code      │
│    .header("Authorization", "Bearer jwt")
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│ 3. Maven executes test                  │
│    POST /api/leave/request              │
│    Headers: Authorization: Bearer eyJ... │
└────────────┬────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────┐
│ 4. Auth Service validates JWT           │
│    ✅ Valid → Process request           │
│    ❌ Invalid → Return 401               │
└─────────────────────────────────────────┘
```

---

## JWT Components (What You Have)

### **What's in Your JWT?**

```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJqYW5lLnNtaXRoQGV4YW1wbGUuY29tIiwiaWF0IjoxNzc0MDAwMzI2LCJleHAiOjE3NzQwODY3MjZ9.snILgUjdNzXNVz5D8ud9SAIyk_I5KbmqXWu9pThbz9I

Part 1 - Header:
  {
    "alg": "HS256"  ← Algorithm (HMAC SHA-256)
  }

Part 2 - Payload:
  {
    "sub": "jane.smith@example.com",
    "iat": 1774000326,               ← Issued at (timestamp)
    "exp": 1774086726                ← Expires (timestamp)
  }

Part 3 - Signature:
  snILgUjdNzXNVz5D8ud9SAIyk_I5KbmqXWu9pThbz9I
  ← Verifies token hasn't been tampered
```

### **Your JWT Includes:**
- ✅ User email (`sub`)
- ✅ Issue time (`iat`)
- ✅ Expiration time (`exp`)
- ❌ Roles/permissions (not visible in your token)

---

## When You NEED JWT - Decision Tree

```
Does your auth service issue JWTs?
├─ YES → Use JWT in testing ✅
└─ NO  → Skip JWT, use basic auth or API key

Do protected endpoints require Bearer token?
├─ YES → Use JWT ✅
└─ NO  → Skip JWT

Do services call other services?
├─ YES → Need JWT for service-to-service ✅
└─ NO  → Skip JWT

Are there multiple user roles?
├─ YES → Use JWT (contains role info) ✅
└─ NO  → Skip JWT
```

---

## How to Use JWT in Your Tests

### **Option 1: Use Pre-Generated Token (Current)**
```python
# In .env
TEST_JWT_TOKEN=eyJ...

# In test
.header("Authorization", "Bearer " + System.getenv("TEST_JWT_TOKEN"))
```

**✅ Pros:**
- Fast (no login step)
- Works for all tests
- Reproducible

**❌ Cons:**
- Token might expire
- Doesn't test login flow
- Can't test role-based access

### **Option 2: Generate Token at Test Time (Better)**
```gherkin
Feature: Leave Request
  Scenario: Employee submits leave request
    Given employee logs in with "john@example.com" and "password123"
    When employee receives JWT from auth service
    And employee submits leave request with JWT
    Then status is "PENDING"
```

**✅ Pros:**
- Tests actual login flow
- Gets fresh token each time
- Ensures token isn't expired

**❌ Cons:**
- Slower (requires login call)
- More complex test setup

### **Option 3: Multiple Test Users (For Role Testing)**
```python
# In .env
TEST_JWT_ADMIN=eyJ...        # Admin token
TEST_JWT_MANAGER=eyJ...      # Manager token
TEST_JWT_EMPLOYEE=eyJ...     # Employee token

# In test
if (user_role == "MANAGER") {
    token = System.getenv("TEST_JWT_MANAGER");
}
```

**✅ Pros:**
- Test different permissions
- Test role-based access
- Test error cases (unauthorized)

**❌ Cons:**
- Need multiple valid tokens
- Tokens must match service's role system

---

## JWT Best Practices for Testing

### ✅ **DO:**
1. **Store JWT in `.env`** (not in code)
   ```env
   TEST_JWT_TOKEN=eyJ...
   ```

2. **Test JWT scenarios:**
   ```gherkin
   Scenario: Valid JWT
   Scenario: Expired JWT
   Scenario: Invalid JWT
   Scenario: Missing JWT (401)
   Scenario: Wrong role (403)
   ```

3. **Generate tokens for different roles:**
   ```python
   admin_jwt = login("admin", "password")
   manager_jwt = login("manager", "password")
   employee_jwt = login("employee", "password")
   ```

4. **Test token refresh:**
   ```gherkin
   Scenario: Refresh expired token
     Given JWT is expired
     When employee requests token refresh
     Then receives new JWT
   ```

5. **Validate JWT in responses:**
   ```java
   String jwt = response.jsonPath().getString("jwt");
   assertThat(jwt).isNotNull().isNotBlank();
   ```

### ❌ **DON'T:**
1. **Hardcode JWT in test code**
   ```java
   // ❌ BAD
   String jwt = "eyJ...hardcoded...";
   ```

2. **Skip JWT testing**
   ```gherkin
   // ❌ BAD - No JWT scenarios
   Scenario: Valid request
   ```

3. **Use same JWT for all tests**
   ```java
   // ❌ BAD - Token expires during test suite
   ```

4. **Send JWT in wrong format**
   ```java
   // ❌ BAD
   .header("Authorization", "jwt_value")  // Missing "Bearer"
   .header("Authorization", jwt_value)    // Missing "Bearer"
   
   // ✅ GOOD
   .header("Authorization", "Bearer " + jwt_value)
   ```

5. **Ignore token expiration**
   ```java
   // ❌ BAD - Assumes token always valid
   
   // ✅ GOOD - Check expiration
   if (isExpired(jwt)) {
       jwt = refresh(jwt);
   }
   ```

---

## Adding JWT to ServiceRegistry Config

**Recommendation:** Make JWT configuration dynamic

```yaml
# config/services_matrix.yaml
services:
  auth:
    enabled: true
    port: 9000
    auth:
      type: "jwt"
      algorithm: "HS256"
    
  leave:
    enabled: true
    port: 9001
    requires_auth: true
    auth_type: "bearer_jwt"
    
  payment:
    enabled: true
    port: 9002
    requires_auth: true
    auth_type: "bearer_jwt"

test_credentials:
  admin:
    email: "admin@test.com"
    password: "admin123"
    roles: ["ROLE_ADMIN"]
  
  manager:
    email: "manager@test.com"
    password: "manager123"
    roles: ["ROLE_MANAGER"]
  
  employee:
    email: "employee@test.com"
    password: "employee123"
    roles: ["ROLE_EMPLOYEE"]
```

Then in your agents:
```python
# Dynamically use JWT based on service requirements
for service in registry.get_enabled_services():
    if service.requires_auth:
        # Get appropriate token for role
        token = get_token_for_role(test_user_role)
        headers["Authorization"] = f"Bearer {token}"
```

---

## Testing JWT Scenarios

Your test_writer.py already covers some! Here's the complete checklist:

```gherkin
Feature: Authentication & JWT

# HAPPY PATH
Scenario: Login with valid credentials returns JWT
  When employee logs in with valid credentials
  Then response contains JWT
  And JWT is valid and not expired

# ERROR CASES  
Scenario: Login with invalid credentials returns error
  When employee logs in with wrong password
  Then HTTP 401 Unauthorized
  And response contains error message

Scenario: Protected endpoint without JWT returns 401
  When accessing protected endpoint without JWT
  Then HTTP 401 Unauthorized

Scenario: Protected endpoint with invalid JWT returns 401
  When accessing endpoint with invalid JWT
  Then HTTP 401 Unauthorized

Scenario: Expired JWT returns 401
  When accessing endpoint with expired JWT
  Then HTTP 401 Unauthorized

Scenario: Accessing endpoint with insufficient permissions returns 403
  When employee (ROLE_EMPLOYEE) tries manager endpoint
  Then HTTP 403 Forbidden
  And error "Insufficient permissions"

Scenario: JWT refresh works
  When token is about to expire
  And employee requests refresh
  Then receives new valid JWT

Scenario: JWT malformed returns 401
  When sending malformed JWT
  Then HTTP 401 Unauthorized
```

---

## Summary: Do You Need JWT?

| Question | Your Answer | Need JWT? |
|----------|-------------|-----------|
| Do services require authentication? | ✅ YES (you have auth service) | ✅ YES |
| Do you test login/logout? | ✅ YES (test_writer.py) | ✅ YES |
| Do services call other services? | ✅ YES (leave calls auth) | ✅ YES |
| Do you have multiple roles? | ✅ YES (employee, manager) | ✅ YES |
| Are all endpoints public? | ❌ NO | ✅ YES |

**Verdict: ✅ YES, you NEED JWT**

You're **already using it correctly** in your current setup!

---

## Checklist: Is Your JWT Setup Good?

- [x] JWT defined in `.env` (not hardcoded)
- [x] Bearer token format used correctly
- [x] Test token generated from auth service
- [x] test_writer.py validates JWT scenarios
- [x] test_executor.py passes JWT to Maven
- [x] settings.py loads JWT from config
- [ ] Multiple tokens for different roles
- [ ] JWT expiration testing
- [ ] JWT refresh scenario testing
- [ ] Invalid JWT scenario testing

**Current Grade: B+** (Good basics, could add role-based testing)

---

## Next Steps (Optional)

1. **Add role-based JWT testing:**
   - Generate tokens for admin/manager/employee
   - Test each role's access permissions

2. **Add JWT expiration testing:**
   - Create expired token
   - Verify returns 401

3. **Add JWT refresh testing:**
   - Test token refresh endpoint
   - Ensure new token is valid

