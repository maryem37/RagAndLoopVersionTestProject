# JWT Configuration in ServiceRegistry: Complete Guide

## The Question: Where Should Credentials Go?

You have 3 options:

```
Option 1: Store EMAIL/PASSWORD in ServiceRegistry
  ↓ Generate JWT at test time
  
Option 2: Store JWT token directly in ServiceRegistry
  ↓ Use pre-generated JWT
  
Option 3: Store BOTH (Recommended)
  ↓ Generate JWT when needed, fallback to stored JWT
```

---

## Option 1: ❌ Store Email/Password (NOT RECOMMENDED)

**Bad Idea:**
```yaml
# ❌ DON'T DO THIS
test_users:
  admin:
    email: "admin@test.com"
    password: "admin123"  # ❌ Password in plain text!
```

**Problems:**
- ❌ Security risk (passwords in config file)
- ❌ Not scalable (different environments have different credentials)
- ❌ Hard to manage (password changes break tests)
- ❌ Violates security best practices

**Only use for local development, never for CI/production.**

---

## Option 2: ✅ Store JWT Token (CURRENT - GOOD)

**Good Idea (what you're doing now):**
```yaml
# ✅ This is what you have
test_credentials:
  jwt_token: "eyJhbGciOiJIUzI1NiJ9..."
  jwt_expiry: "2026-03-24T12:00:00Z"
```

```env
# .env
TEST_JWT_TOKEN=eyJhbGciOiJIUzI1NiJ9...
```

**Advantages:**
- ✅ No passwords in code
- ✅ Can pre-generate once and reuse
- ✅ Works across all test environments
- ✅ Current approach (you're using this!)

**Disadvantages:**
- ❌ Token can expire
- ❌ Doesn't test login flow
- ❌ Can't test token generation

---

## Option 3: ✅ Store BOTH (BEST FOR GENERIC SYSTEM)

**Best Practice (Recommended):**
```yaml
# config/services_matrix.yaml

# Global test credentials
test_credentials:
  # Option A: Use pre-generated JWT (fast)
  jwt_token: "eyJhbGciOiJIUzI1NiJ9..."
  jwt_expiry: "2026-03-24"
  
  # Option B: Generate fresh JWT each test (proper testing)
  login_service: "auth"
  test_users:
    admin:
      email: "admin@test.com"
      password: "admin123"
    
    manager:
      email: "manager@test.com"
      password: "manager123"
    
    employee:
      email: "employee@test.com"
      password: "employee123"

services:
  auth:
    enabled: true
    port: 9000
    login_endpoint: "/api/auth/login"
    jwt_field: "jwt"  # Field name in response
```

---

## Implementation: Store in ServiceRegistry

### **Step 1: Add to services_matrix.yaml**

```yaml
# config/services_matrix.yaml

# ===== TEST CREDENTIALS =====
test_credentials:
  # Pre-generated JWT (for quick tests)
  jwt_token: "eyJhbGciOiJIUzI1NiJ9..."
  jwt_expiry: "2026-03-24"
  
  # Test users (for generating fresh JWT)
  test_users:
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

# ===== SERVICES =====
services:
  auth:
    enabled: true
    port: 9000
    login_endpoint: "/api/auth/login"
    jwt_field: "jwt"  # What field contains JWT in response
    
  leave:
    enabled: true
    port: 9001
    requires_auth: true
    auth_via_service: "auth"
```

### **Step 2: Update ServiceRegistry to Load Credentials**

```python
# tools/service_registry.py

class CredentialManager:
    """Manages test credentials and JWT"""
    
    def __init__(self, config: Dict):
        self.jwt_token = config.get('jwt_token')
        self.jwt_expiry = config.get('jwt_expiry')
        self.test_users = config.get('test_users', {})
    
    def get_jwt_token(self) -> str:
        """Get pre-generated JWT"""
        return self.jwt_token
    
    def get_test_user(self, role: str = "employee") -> Dict:
        """Get test user credentials for a role"""
        return self.test_users.get(role, {})
    
    def is_jwt_expired(self) -> bool:
        """Check if stored JWT is expired"""
        if not self.jwt_expiry:
            return False
        from datetime import datetime
        expiry = datetime.fromisoformat(self.jwt_expiry)
        return datetime.now() > expiry


class ServiceRegistry:
    
    def __init__(self, config_path: Optional[Path] = None):
        # ... existing code ...
        self.credentials = None
        self._load_credentials()
    
    def _load_credentials(self) -> None:
        """Load test credentials from matrix"""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        test_creds = config.get('test_credentials', {})
        self.credentials = CredentialManager(test_creds)
    
    def get_credentials(self) -> CredentialManager:
        """Get credential manager"""
        return self.credentials
    
    def get_jwt_token(self) -> str:
        """Convenience method to get JWT"""
        return self.credentials.get_jwt_token()
    
    def get_test_user(self, role: str = "employee") -> Dict:
        """Get test user by role"""
        return self.credentials.get_test_user(role)
```

### **Step 3: Use in Test Writer**

```python
# agents/test_writer.py

def get_authorization_header() -> str:
    """Get Authorization header for tests"""
    registry = get_service_registry()
    
    # Option A: Use pre-generated JWT (fast)
    if not registry.get_credentials().is_jwt_expired():
        jwt = registry.get_jwt_token()
        return f"Bearer {jwt}"
    
    # Option B: Generate fresh JWT by logging in
    # (implemented below)
    return generate_jwt_by_login(registry)


def generate_jwt_by_login(registry: ServiceRegistry) -> str:
    """Generate fresh JWT by calling login endpoint"""
    # Get auth service
    auth_service = registry.get_service("auth")
    user = registry.get_test_user("employee")
    
    # Login request
    import requests
    response = requests.post(
        f"{auth_service.get_base_url()}{auth_service.login_endpoint}",
        json={
            "email": user["email"],
            "password": user["password"]
        }
    )
    
    if response.status_code == 200:
        jwt = response.json().get(auth_service.jwt_field)
        return f"Bearer {jwt}"
    else:
        # Fallback to pre-generated
        return f"Bearer {registry.get_jwt_token()}"
```

---

## Complete Example: Generic System

### **services_matrix.yaml (For Any Services)**

```yaml
# Global test configuration
test_credentials:
  # Pre-generated JWT (use if available)
  jwt_token: "eyJhbGciOiJIUzI1NiJ9..."
  jwt_expiry: "2026-03-24"
  
  # Test users (for generating fresh JWT)
  test_users:
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

# Services configuration
services:
  auth:
    enabled: true
    port: 9000
    db: {type: "postgres", port: 5432}
    java_package: "com.example.auth"
    test_runner_class: "com.example.auth.AuthTestRunner"
    pom_location: "output/tests"
    dependencies: []
    
    # JWT-specific config
    auth_enabled: true
    login_endpoint: "/api/auth/login"
    jwt_field: "jwt"  # Response field containing JWT
    jwt_algorithm: "HS256"
  
  leave:
    enabled: true
    port: 9001
    db: {type: "mysql", port: 3306}
    java_package: "com.example.leave"
    test_runner_class: "com.example.leave.LeaveTestRunner"
    pom_location: "output/tests"
    dependencies: ["auth"]
    
    # Authorization
    auth_required: true
    auth_via_service: "auth"
  
  payment:
    enabled: false
    port: 9002
    db: {type: "postgres", port: 5433}
    java_package: "com.example.payment"
    test_runner_class: "com.example.payment.PaymentTestRunner"
    pom_location: "output/tests"
    dependencies: ["auth", "leave"]
    
    auth_required: true
    auth_via_service: "auth"
```

### **Usage in Agents**

```python
# agents/test_executor.py

def _build_mvn_command(self, service_name: str) -> str:
    """Build Maven command with JWT"""
    registry = get_service_registry()
    
    parts = [
        "mvn", "clean", "verify",
        f"-Dservice.name={service_name}",
    ]
    
    # Get JWT (generic)
    jwt = registry.get_jwt_token()
    if jwt:
        parts.append(f"-DTEST_JWT_TOKEN={jwt}")
    
    # Dynamic service URLs (existing code)
    for service in registry.get_enabled_services():
        base_url = service.get_base_url()
        env_var = f"{service.name.upper()}_BASE_URL"
        parts.append(f"-D{env_var}={base_url}")
    
    return " ".join(parts)
```

---

## Decision: What Should YOU Do?

### **For Local Development (What You Have Now) ✅**
```yaml
# Store JWT in .env
TEST_JWT_TOKEN=eyJ...

# ServiceRegistry loads it
jwt = registry.get_jwt_token()
```

**This is GOOD for:**
- Fast test runs
- Reproducible results
- Local development

### **For Production/CI (Better) ✅**
```yaml
# Store email/password securely
test_users:
  employee:
    email: "employee@test.com"
    password: "employee123"  # Read from CI secret, not file

# Generate JWT at test time
jwt = generate_jwt_by_login("employee")
```

**This is GOOD for:**
- Testing actual login flow
- Ensuring JWT works
- Role-based testing

### **For Generic System (Recommended) ✅✅**
```yaml
# Do BOTH:
jwt_token: "pre-generated"      # Fast fallback

test_users:
  employee:
    email: "..."
    password: "..."            # Generate fresh JWT if needed

# System uses whichever is available
if jwt_expired():
    jwt = generate_fresh()
else:
    jwt = use_stored()
```

---

## Quick Answer to Your Question

**"Should I put email/password OR JWT in ServiceRegistry?"**

### Answer:
```
PUT IN SERVICE REGISTRY:
✅ Email/password (for generating JWT when needed)
✅ Pre-generated JWT (for fast tests)
✅ Both (for flexibility)

DON'T PUT IN CODE:
❌ Never hardcode credentials in Python
❌ Never hardcode JWT in Python
❌ Use config file or environment variables
```

**Current Setup (Good):**
```env
# .env - Use this
TEST_JWT_TOKEN=eyJ...
```

**Enhanced Setup (Better):**
```yaml
# services_matrix.yaml - Add this
test_credentials:
  jwt_token: "eyJ..."  # Pre-generated
  test_users:
    employee:
      email: "emp@test.com"
      password: "password123"
```

---

## Summary Table

| Approach | Store Where | Use Case | Security | Flexibility |
|----------|------------|----------|----------|-------------|
| **JWT only** | .env | Fast tests | Good | Low |
| **Email/Password only** | .yaml | Fresh JWT | ⚠️ Medium | High |
| **Both (Hybrid)** | .yaml + .env | Any case | Good | High |

**Recommendation: Use Hybrid (Both)** ✅

---

## What NOT to Do

```yaml
# ❌ WRONG
services:
  auth:
    password: "admin123"  # In code!
    
# ❌ WRONG  
def test():
    jwt = "eyJhbGciOiJIUzI1NiJ9..."  # Hardcoded!

# ✅ CORRECT
# In .env or config file:
TEST_JWT_TOKEN=eyJ...

# In Python:
jwt = registry.get_jwt_token()
```

