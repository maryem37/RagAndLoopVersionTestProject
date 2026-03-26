# JWT Configuration: Visual Guide

## Your Question in a Diagram

```
WHERE SHOULD I PUT THIS?

Option 1:
┌─────────────────────────────┐
│ Email & Password            │
│ admin@test.com              │
│ password123                 │
└─────────────────────────────┘
         │
         └─→ Generate JWT ✅

Option 2:
┌─────────────────────────────┐
│ Pre-generated JWT           │
│ eyJhbGciOiJIUzI1NiJ9...    │
└─────────────────────────────┘
         │
         └─→ Use directly ✅

Option 3: (BEST)
┌─────────────────────────────┐
│ Email & Password            │  ├─ Generate JWT when needed
├─────────────────────────────┤  │
│ Pre-generated JWT           │  ├─ Use for speed
└─────────────────────────────┘  │
         │                        └─ Fallback if stored expires
         └─→ Smart choice ✅
```

---

## Where to Put Them?

```
.env File:
┌──────────────────────────────┐
│ TEST_JWT_TOKEN=eyJ...        │ ← JWT for quick access
│ HUGGINGFACE_API_TOKEN=...    │
└──────────────────────────────┘

services_matrix.yaml:
┌──────────────────────────────┐
│ test_credentials:            │
│   jwt_token: eyJ...          │ ← Also here (persistent)
│   test_users:                │
│     admin:                   │
│       email: admin@...       │ ← Email/Password here
│       password: ...          │
└──────────────────────────────┘
```

---

## Flow: How It Works

```
TEST STARTS
    │
    ↓
┌─────────────────────┐
│ Load ServiceRegistry│
│ (reads YAML)        │
└────────┬────────────┘
         │
         ↓
    ┌─────────────┐
    │ Get JWT?    │
    └─┬───────┬───┘
      │       │
      ↓       ↓
   YES       NO
   │         │
   │         └─→ ┌──────────────────┐
   │             │ Login with       │
   │             │ email/password   │
   │             └────────┬─────────┘
   │                      ↓
   │              ┌──────────────────┐
   │              │ Get JWT from     │
   │              │ Auth Service     │
   │              └────────┬─────────┘
   │                       │
   └───────┬───────────────┘
           ↓
   ┌──────────────────┐
   │ Add to Header:   │
   │ Authorization:   │
   │ Bearer eyJ...    │
   └────────┬─────────┘
            ↓
   ┌──────────────────┐
   │ Send Request     │
   │ to Service       │
   └──────────────────┘
```

---

## Storage Diagram

```
YOUR SYSTEM ARCHITECTURE:

┌─────────────────────────────────────────────────────┐
│                   .env FILE                         │
│                                                     │
│  TEST_JWT_TOKEN=eyJhbGciOiJIUzI1NiJ9...          │
│  TEST_USER_EMAIL=admin@test.com                   │
│  TEST_USER_PASSWORD=admin123                      │
└────────────┬────────────────────────────────────────┘
             │ (Read by)
             ↓
┌─────────────────────────────────────────────────────┐
│           ServiceRegistry                           │
│  (tools/service_registry.py)                       │
│                                                     │
│  credentials = {                                   │
│    "jwt_token": "eyJ...",    ← From .env           │
│    "test_users": {                                 │
│      "admin": {              ← From services_matrix│
│        "email": "...",                             │
│        "password": "..."                           │
│      }                                             │
│    }                                               │
│  }                                                 │
└────────────┬────────────────────────────────────────┘
             │ (Used by)
    ┌────────┴────────┬──────────────┐
    ↓                 ↓              ↓
┌────────────┐  ┌──────────────┐  ┌─────────┐
│Test Writer │  │Test Executor │  │ Agents  │
└────────────┘  └──────────────┘  └─────────┘
```

---

## Decision Tree

```
SHOULD I USE JWT FROM REGISTRY?

    START
      │
      ↓
  Is service protected?
  (requires auth)
    /         \
   YES        NO
   │           └─→ No JWT needed ✓
   │
   ↓
Do I need to test login?
    /          \
   YES         NO
   │            └─→ Use pre-generated JWT ✓
   │
   ↓
Should I support multiple roles?
    /           \
   YES          NO
   │             └─→ Use pre-generated JWT ✓
   │
   ↓
Use BOTH in registry:
├─ Pre-generated JWT (fast path)
├─ Email/Password (test path)
└─ Let system choose ✓
```

---

## Code Structure

```
services_matrix.yaml
─────────────────────

test_credentials:          ← You add this
  jwt_token: "eyJ..."
  test_users:
    admin:
      email: "..."
      password: "..."

services:
  auth:
    port: 9000
  leave:
    port: 9001
```

```python
# ServiceRegistry loads it
registry = ServiceRegistry()

# You use it
jwt = registry.get_jwt_token()          # Fast path
user = registry.get_test_user("admin")  # Fresh JWT path
```

---

## Simple Comparison

| Need | Store In | Access From |
|------|----------|------------|
| **JWT** | .env + matrix.yaml | registry.get_jwt_token() |
| **Email** | matrix.yaml | registry.get_test_user("admin")["email"] |
| **Password** | matrix.yaml | registry.get_test_user("admin")["password"] |
| **Service URL** | matrix.yaml | registry.get_service("auth").get_base_url() |

---

## YOUR ANSWER

**"Email/Password OR JWT in ServiceRegistry?"**

```
     ┌─────────────────────────────┐
     │        BOTH!                │
     ├─────────────────────────────┤
     │ JWT      → For speed        │
     │ Email    → For test login   │
     │ Password → For test login   │
     └─────────────────────────────┘
            │
            ↓
     ┌─────────────────────────────┐
     │  Put in ServiceRegistry     │
     │  (services_matrix.yaml)     │
     └─────────────────────────────┘
```

**That's the answer!** 🎯

