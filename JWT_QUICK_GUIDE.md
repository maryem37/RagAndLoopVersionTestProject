# JWT: Quick Decision Guide

## Do I Need JWT? ✅ vs ❌

### **✅ YES - Use JWT If:**

- [ ] Services require authentication
- [ ] You have an Auth service
- [ ] Services call other services
- [ ] You have multiple user roles
- [ ] You want stateless API (no server sessions)
- [ ] You need token-based access control

### **❌ NO - Skip JWT If:**

- [ ] All endpoints are public (no auth)
- [ ] Using session-based authentication (cookies)
- [ ] Single monolithic app (not microservices)
- [ ] Testing internal-only services (same network)
- [ ] Simple API key authentication is sufficient

---

## Your System: ✅ YES, USE JWT

**Evidence:**
- ✅ Have auth service (port 9000)
- ✅ Leave service requires JWT
- ✅ Already in `.env`: `TEST_JWT_TOKEN=eyJ...`
- ✅ test_writer.py generates JWT scenarios
- ✅ test_executor.py passes JWT to tests

**Status: Already Implemented ✅**

---

## JWT Quick Reference

### Where JWT Goes:
```java
// HTTP Header
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
```

### In Your Tests:
```java
// test_writer.py generated code
.header("Authorization", "Bearer " + jwt)
.post("/api/leave/request")
```

### From Environment:
```python
# .env
TEST_JWT_TOKEN=eyJhbGciOiJIUzI1NiJ9...

# Python reads it
jwt = os.getenv("TEST_JWT_TOKEN")
```

### In Maven:
```bash
# test_executor.py passes it
mvn verify -DTEST_JWT_TOKEN=eyJ...
```

---

## JWT Scenarios to Test

```gherkin
✅ HAPPY PATH (1 scenario)
   Scenario: Valid JWT allows access

⚠️ ERROR CASES (5+ scenarios)
   Scenario: Missing JWT → 401
   Scenario: Invalid JWT → 401
   Scenario: Expired JWT → 401
   Scenario: Wrong role → 403
   Scenario: Malformed JWT → 401
```

Your test_writer.py **already covers these!**

---

## If You're NOT Using JWT

Remove from:
1. `.env` - Delete `TEST_JWT_TOKEN` line
2. `config/settings.py` - Remove jwt_token config
3. `agents/test_executor.py` - Remove JWT Maven args
4. `agents/test_writer.py` - Remove Authorization headers

But **you ARE using it**, so keep it!

---

## JWT Token Structure (Yours)

```
Header:      eyJhbGciOiJIUzI1NiJ9
             {"alg": "HS256"}

Payload:     eyJzdWIiOiJqYW5lLnNtaXRoQGV4YW1wbGUuY29tIiwiaWF0IjoxNzc0MDAwMzI2LCJleHAiOjE3NzQwODY3MjZ9
             {
               "sub": "jane.smith@example.com",
               "iat": 1774000326,      (issued at)
               "exp": 1774086726       (expires at)
             }

Signature:   snILgUjdNzXNVz5D8ud9SAIyk_I5KbmqXWu9pThbz9I
             (HMAC-SHA256 signature)
```

---

## Common Mistakes (Avoid These!)

❌ **DON'T:**
```
Hardcode JWT in code
Use same JWT forever (it expires)
Send JWT without "Bearer " prefix
Test only happy path (no error scenarios)
Ignore token expiration
Forget to validate JWT in responses
```

✅ **DO:**
```
Store JWT in .env
Generate fresh tokens at test time
Use "Bearer <token>" format
Test error cases (invalid, expired, missing)
Check token expiration timestamps
Validate JWT in response parsing
```

---

## Quick Checklist

- [x] JWT is in `.env`
- [x] test_writer.py uses JWT
- [x] test_executor.py passes JWT
- [x] Bearer format is correct
- [ ] Error cases tested (invalid JWT)
- [ ] Role-based access tested
- [ ] Token expiration tested

**Grade: B+** - Working well, could enhance error testing

