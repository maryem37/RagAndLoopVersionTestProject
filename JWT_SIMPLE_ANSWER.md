# JWT in ServiceRegistry: Simple Answer

## Your Question (Simplified)

> "Should I put EMAIL/PASSWORD or JWT in ServiceRegistry?"

---

## Simple Answer

### **PUT BOTH in ServiceRegistry**

```yaml
# config/services_matrix.yaml

test_credentials:
  # JWT (pre-generated - use for speed)
  jwt_token: "eyJhbGciOiJIUzI1NiJ9..."
  
  # Email/Password (use to generate fresh JWT)
  test_users:
    admin:
      email: "admin@test.com"
      password: "admin123"
    
    employee:
      email: "employee@test.com"
      password: "employee123"
```

---

## When to Use What?

```
├─ Pre-generated JWT
│  ├─ Use WHEN: Want fast tests
│  ├─ How: registry.get_jwt_token()
│  └─ Problem: Token might expire
│
└─ Email/Password
   ├─ Use WHEN: Need to test login flow
   ├─ How: registry.get_test_user("employee")
   └─ How: Login → Get JWT → Use JWT
```

---

## The Flow

### Option A: Use Pre-Generated JWT (Current - FAST)
```
1. Load JWT from registry
2. Add to Authorization header
3. Send request
✅ Fast ✅ Works offline ⚠️ Token expires
```

### Option B: Generate JWT at Test Time (Better - PROPER)
```
1. Load email/password from registry
2. Call auth service login endpoint
3. Auth returns JWT
4. Add JWT to Authorization header
5. Send request
✅ Tests login ✅ Fresh token ⚠️ Slower
```

### Option C: Use Both (Best - HYBRID)
```
1. Try using pre-generated JWT
   ├─ If not expired → Use it (FAST)
   └─ If expired → Generate fresh (PROPER)
✅ Fast when possible ✅ Fresh when needed
```

---

## Code Example

### ServiceRegistry Enhanced

```python
# tools/service_registry.py

class ServiceRegistry:
    
    def __init__(self, config_path):
        # Load credentials from YAML
        self.credentials = {
            "jwt_token": "eyJ...",
            "test_users": {
                "admin": {"email": "admin@test.com", "password": "admin123"},
                "employee": {"email": "emp@test.com", "password": "emp123"},
            }
        }
    
    def get_jwt_token(self) -> str:
        """Get pre-generated JWT"""
        return self.credentials.get("jwt_token")
    
    def get_test_user(self, role: str) -> Dict:
        """Get email/password for role"""
        return self.credentials["test_users"].get(role, {})
```

### In Tests

```python
# agents/test_writer.py

registry = get_service_registry()

# Method 1: Use pre-generated JWT (FAST)
jwt = registry.get_jwt_token()

# Method 2: Generate fresh JWT (PROPER)
user = registry.get_test_user("employee")
# Login with: user["email"], user["password"]
# Get JWT from response

# Method 3: Use whichever is best (SMART)
if jwt_is_valid(jwt):
    use_jwt(jwt)
else:
    jwt = login(user["email"], user["password"])
    use_jwt(jwt)
```

---

## Current Setup: What You Have

```
✅ JWT in .env
   TEST_JWT_TOKEN=eyJ...

❌ Missing: Email/Password config

👉 ADD THIS to services_matrix.yaml:
test_credentials:
  test_users:
    employee:
      email: "employee@test.com"
      password: "employee123"
```

---

## Comparison: Where to Store What?

| Item | Where? | Why |
|------|--------|-----|
| **JWT** | .env + ServiceRegistry | Easy to load, pre-generated |
| **Email** | ServiceRegistry YAML | Needed to generate JWT |
| **Password** | ServiceRegistry YAML | Needed to generate JWT |
| **Secrets** | Environment vars | Security - never in files |
| **Public config** | ServiceRegistry YAML | Service ports, names |

---

## For Your Generic System

When you add a NEW service (payment, notification), users should:

```yaml
# Just add service to matrix
# Everything else works automatically!

services:
  payment:
    enabled: true
    port: 9002
    dependencies: ["auth"]

# Uses existing test_credentials automatically
# ✅ No JWT changes needed
# ✅ No email/password changes needed
```

---

## The Answer

**"Email/Password OR JWT?"**

### ✅ Answer: **BOTH**

- **JWT** → Fast tests (use pre-generated)
- **Email/Password** → Proper testing (generate fresh)

**In ServiceRegistry? YES!**

Store both in `services_matrix.yaml` under `test_credentials`:
```yaml
test_credentials:
  jwt_token: "..."           ← JWT for speed
  test_users:                ← Email/Password for proper testing
    admin:
      email: "..."
      password: "..."
```

**That's it!** 🎯

