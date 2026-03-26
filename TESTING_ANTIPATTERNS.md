# ⚠️ Microservices Testing: What NOT to Do

## Critical Mistakes to AVOID

### ❌ **1. Don't Test Services in Isolation (Without Integration)**

**Bad Approach:**
```yaml
# Only test each service alone
services:
  auth: test alone
  leave: test alone  
  payment: test alone
```

**Problem:**
- ❌ Auth works fine in isolation
- ❌ Leave works fine in isolation
- ✅ But together they FAIL (service-to-service communication breaks)
- ❌ Discover bugs in production, not in testing

**What to Do Instead:**
```python
# Test BOTH isolated AND integrated
# 1. Unit/Contract tests (single service)
# 2. E2E tests (service interactions)

# Example: "Employee cancels account"
# Should test:
#   auth.cancel() → leave.cancelRequests() → payment.refund()
# NOT just: auth.cancel() in isolation
```

---

### ❌ **2. Don't Ignore Service Dependencies**

**Bad Approach:**
```yaml
# Treat all services equally
services:
  auth:
    enabled: true
    dependencies: []
  
  leave:
    enabled: true
    dependencies: []  # ❌ WRONG! Leave depends on Auth
  
  payment:
    enabled: true
    dependencies: []  # ❌ WRONG! Payment depends on Auth
```

**Problem:**
- ❌ Test Leave before Auth is ready
- ❌ Leave calls Auth service → FAILS
- ❌ False negatives (tests fail for wrong reasons)

**What to Do Instead:**
```yaml
# Define explicit dependencies
services:
  auth:
    enabled: true
    dependencies: []  # ✅ No dependencies
  
  leave:
    enabled: true
    dependencies: ["auth"]  # ✅ Explicit
  
  payment:
    enabled: true
    dependencies: ["auth", "leave"]  # ✅ Explicit
```

---

### ❌ **3. Don't Hardcode Service Ports/URLs**

**Bad Approach:**
```python
# Hardcoded everywhere
auth_url = "http://localhost:9000"
leave_url = "http://localhost:9001"

# If port changes: update 10+ files
# If add payment service: remember to add it everywhere
# If run in CI/cloud: URLs are different
```

**Problem:**
- ❌ Can't change ports without code changes
- ❌ Breaks when environment changes
- ❌ Can't run multiple test suites in parallel
- ❌ Not scalable

**What to Do Instead:**
```python
# ✅ Configuration-driven (like you now have)
from tools.service_registry import get_service_registry

registry = get_service_registry()
for service in registry.get_enabled_services():
    url = service.get_base_url()
    # Works anywhere, any port, any environment
```

---

### ❌ **4. Don't Run All Tests Against Production**

**Bad Approach:**
```bash
python test_runner.py --environment=production
# 🔥 DISASTER: Your tests delete production data!
# Your tests create fake users in production
# Your tests modify real user accounts
```

**Problem:**
- ❌ Destroys real data
- ❌ Affects real users
- ❌ Illegal (depends on data privacy laws)
- ❌ Company fires you

**What to Do Instead:**
```yaml
# ✅ Separate environments
environments:
  local:      # ✅ Test here (safe)
    base_url: http://localhost:9000
    
  ci:         # ✅ Test here (isolated)
    base_url: http://ci-services:9000
    
  staging:    # ⚠️ Test carefully (staging data only)
    base_url: https://staging.internal
    
  production: # ❌ NO TESTING (read-only only)
    base_url: https://api.production.com
```

---

### ❌ **5. Don't Mock Everything**

**Bad Approach:**
```python
# Mock all external services
@mock("http://localhost:9000")  # Mock auth
@mock("http://localhost:9001")  # Mock leave
def test_user_creation():
    # ❌ Testing with mocks only
    user = create_user()
    assert user is not None
    # But mocks always return success!
    # Real service might fail differently
```

**Problem:**
- ❌ Mocks hide real failures
- ❌ Real service might return different error format
- ❌ Network issues never detected
- ❌ False confidence (tests pass, prod fails)

**What to Do Instead:**
```python
# ✅ Mix of testing strategies
# 1. Unit tests (fast, isolated) → Mock everything
# 2. Contract tests (medium) → Mock selective services
# 3. Integration tests (slow) → Use REAL services
# 4. E2E tests (slowest) → All real services

# Test pyramid:
#       E2E (10% - few tests)
#      /  \
#    Contract (30%)
#    /      \
#   Unit (60% - many tests, mocks)
```

---

### ❌ **6. Don't Test One Feature Per File**

**Bad Approach:**
```
tests/
├── test_auth_login.feature
├── test_auth_logout.feature
├── test_auth_register.feature
├── test_leave_request.feature
├── test_leave_approval.feature
├── test_leave_cancellation.feature
├── test_leave_balance.feature
├── ... 100+ files
```

**Problem:**
- ❌ Maintenance nightmare (change one business rule → update 20 files)
- ❌ Duplicate step definitions
- ❌ Hard to see complete feature coverage
- ❌ Slow to find what you're testing

**What to Do Instead:**
```
features/
├── auth.feature          # All auth scenarios
│   ├── Scenario: Login
│   ├── Scenario: Logout
│   └── Scenario: Register
│
├── leave-request.feature # All leave request scenarios
│   ├── Scenario: Submit request
│   ├── Scenario: Approve request
│   └── Scenario: Cancel request
│
└── cross-service/        # Multi-service flows
    └── cancel-employee.feature  # Auth → Leave → Payment
```

---

### ❌ **7. Don't Ignore Database State**

**Bad Approach:**
```python
def test_1_create_user():
    user = create_user("john@example.com")
    assert user.id == 1

def test_2_create_second_user():
    user = create_user("jane@example.com")
    assert user.id == 2  # ❌ WRONG if test_1 didn't run first
                         # ❌ WRONG if test_1 created multiple users

def test_3_list_users():
    users = list_all_users()
    assert len(users) == 2  # ❌ What if previous tests added more?
```

**Problem:**
- ❌ Tests depend on execution order
- ❌ Tests interfere with each other
- ❌ Random failures (flaky tests)
- ❌ Can't run tests in parallel
- ❌ Can't run single test in isolation

**What to Do Instead:**
```python
# ✅ Clean database before EACH test
class TestLeaveRequest:
    
    def setup(self):
        """Run BEFORE each test"""
        clear_database()
        create_test_user("john@example.com")
    
    def test_create_request(self):
        # Fresh DB, known state
        request = create_leave_request(...)
        assert request.status == "PENDING"
    
    def test_cancel_request(self):
        # Fresh DB again, independent of test_create_request
        request = create_leave_request(...)
        cancel_request(request.id)
        assert request.status == "CANCELLED"
```

---

### ❌ **8. Don't Ignore Async/Distributed Issues**

**Bad Approach:**
```python
def test_payment_notification():
    payment = create_payment()
    
    # ❌ Immediately check notification
    notifications = get_notifications()
    assert len(notifications) == 1
    # ❌ But notification service is async!
    # It takes 100ms to process
    # Test fails randomly
```

**Problem:**
- ❌ Payment service returns immediately
- ❌ Notification service processes asynchronously
- ❌ Test checks BEFORE notification is ready
- ❌ Flaky tests (sometimes pass, sometimes fail)
- ❌ Race conditions

**What to Do Instead:**
```python
# ✅ Wait for async operations
def test_payment_notification():
    payment = create_payment()
    
    # Wait up to 5 seconds for notification
    notifications = wait_for(
        lambda: get_notifications(),
        condition=lambda n: len(n) == 1,
        timeout=5
    )
    assert len(notifications) == 1
```

---

### ❌ **9. Don't Test with Test-Only Code Paths**

**Bad Approach:**
```java
// In production code
if (isTestMode) {
    // ❌ Special code path for tests
    return mockResponse;
}
// Production code path
```

**Problem:**
- ❌ Tests never exercise real code
- ❌ Real code path untested
- ❌ Bugs in production code never caught
- ❌ Test-specific code clutters production

**What to Do Instead:**
```java
// ✅ No test-specific code in production
// Use environment/configuration instead

if (environment.equals("test")) {
    // Configure services to use test URLs
} else {
    // Configure services to use prod URLs
}
// Same code path executes in both
```

---

### ❌ **10. Don't Ignore Error Cases**

**Bad Approach:**
```gherkin
Feature: Leave Request Management

Scenario: Submit leave request
  Given employee exists
  When employee submits leave request
  Then status is PENDING
  
# ❌ NO error scenarios!
# What if balance insufficient?
# What if dates invalid?
# What if unauthorized?
```

**Problem:**
- ❌ Only 20% of code tested (happy path)
- ❌ 80% of bugs are in error handling
- ❌ Production crashes on edge cases
- ❌ Poor error messages to users

**What to Do Instead:**
```gherkin
Feature: Leave Request Management

# Happy Path (1 scenario)
Scenario: Valid leave request
  Given employee has sufficient balance
  When employee submits valid request
  Then status is PENDING

# Error Cases (7+ scenarios)
Scenario: Insufficient balance
  Given employee has 0 days balance
  When employee submits request
  Then error "Insufficient balance"

Scenario: Invalid date range
  Given start date > end date
  When employee submits request
  Then error "Invalid date range"

Scenario: Missing required fields
  Given employee omits employee ID
  When employee submits request
  Then error "Missing required fields"

# ... 5 more error scenarios
```

---

### ❌ **11. Don't Ignore API Versioning**

**Bad Approach:**
```python
# Always use /v1 endpoint
def call_service(endpoint):
    return requests.get(f"http://service/v1/{endpoint}")

# API team releases /v2
# Your tests still use /v1 (deprecated)
# Discovers bugs AFTER /v1 is removed
```

**Problem:**
- ❌ Tests use old API versions
- ❌ Real services use new versions
- ❌ Integration failures in production
- ❌ Migration plan unclear

**What to Do Instead:**
```yaml
# ✅ Define API versions in configuration
services:
  auth:
    port: 9000
    api_version: "v2"  # Explicit version
    
  leave:
    port: 9001
    api_version: "v3"
```

```python
# Use from configuration
def call_service(service_name, endpoint):
    version = registry.get_service(service_name).api_version
    return requests.get(f"http://service/{version}/{endpoint}")
```

---

### ❌ **12. Don't Test in a Vacuum**

**Bad Approach:**
```
Tests pass ✅
CI/CD passes ✅
Deploy to production ❌ FAILS
```

**Problem:**
- ❌ Tests work on your machine
- ❌ Infrastructure different in production
- ❌ Network latency different
- ❌ Load/concurrency untested

**What to Do Instead:**
```yaml
# ✅ Test in environments that match production
# 1. Local (development)
# 2. CI (isolated, but similar to prod)
# 3. Staging (exact copy of production)
# 4. Production (read-only validation)

test_environments:
  local:
    duration: 5 min
    cost: free
    
  ci:
    duration: 10 min
    cost: cheap
    
  staging:
    duration: 20 min
    cost: moderate
    
  production:
    duration: 5 min (read-only)
    cost: free
```

---

## Summary: What NOT to Do

| ❌ Don't | ✅ Do Instead |
|---------|--------------|
| Test services in isolation | Test integrated flows |
| Ignore dependencies | Explicit dependency graph |
| Hardcode URLs/ports | Configuration-driven |
| Test against production | Separate test environment |
| Mock everything | Mix strategies (unit/contract/E2E) |
| One feature per file | Group by business capability |
| Ignore database state | Clean state before each test |
| Ignore async issues | Wait for async operations |
| Test-specific code paths | Same code, different config |
| Only happy path | Happy path + error cases |
| Ignore API versions | Version-aware configuration |
| Test in isolation | Test in production-like environment |

---

## Risk Matrix: Impact of NOT Following These Rules

```
Severity │ Issue
─────────┼──────────────────────────────────
   CRITICAL (Don't do!)
   ↑      │
   │      ├─ Test against production
   │      ├─ Ignore dependencies
   │      ├─ No error case testing
   │
   HIGH   │
   │      ├─ Hardcoded URLs
   │      ├─ Mock everything
   │      ├─ Ignore async
   │
   MEDIUM │
   │      ├─ One feature per file
   │      ├─ Ignore versioning
   │
   LOW    │
   └──────┴─ Minor file organization
```

---

## Your Current System: Doing It RIGHT ✅

Your generalized system **AVOIDS most of these pitfalls:**

✅ ServiceRegistry (not hardcoded)
✅ Dependency management (order)
✅ Configuration-driven (not code)
✅ Service-agnostic agents (scales)
✅ Error case testing (Gherkin scenarios)
✅ Integration testing (cross-service)
✅ Proper state management
✅ No hardcoded test paths

**Grade: A-** (Avoid these 12 pitfalls!)

