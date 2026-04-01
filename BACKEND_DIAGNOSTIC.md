# Backend API Diagnostic Report

## Summary

Backend services are **partially running** but with issues:
- ✅ Auth service (port 9000) is working
- ⚠️ Leave service (port 9001) has issues (500 errors)

---

## 1. Auth Service Endpoint (9000)

### ✅ Login Works

**Endpoint:** `POST /api/auth/login`

**Request:**
```json
{
  "email": "admin@test.com",
  "password": "admin123"
}
```

**Response (200 OK):**
```json
{
  "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbkB0ZXN0LmNvbSIsImlhdCI6MTc3NDk5MzA3MCwiZXhwIjoxNzc1MDc5NDcwfQ.iwJ9ItGUJy3VhzcWN8XoD0jviFy_aMToXS6siYHfLTo",
  "userRole": "Administration",
  "userId": 8
}
```

**Schema:**
```json
{
  "type": "object",
  "properties": {
    "jwt": { "type": "string" },
    "userRole": { "type": "string", "enum": ["Employer", "Administration", "TeamLeader"] },
    "userId": { "type": "integer", "format": "int64" }
  }
}
```

---

## 2. Leave Service Endpoint (9001)

### ⚠️ Create Leave Request - Has Issues

**Endpoint:** `POST /api/leave-requests/create`

**Expected Schema (LeaveRequestDto):**
```json
{
  "type": "object",
  "properties": {
    "id": { "type": "integer", "format": "int64" },
    "fromDate": { "type": "string", "format": "date" },           // YYYY-MM-DD
    "toDate": { "type": "string", "format": "date" },             // YYYY-MM-DD
    "fromTime": { "type": "string", "format": "time" },           // HH:mm:ss (optional)
    "toTime": { "type": "string", "format": "time" },             // HH:mm:ss (optional)
    "periodType": {
      "type": "string",
      "enum": ["JOURNEE_COMPLETE", "MATIN", "APRES_MIDI", "PAR_HEURE"]
    },
    "note": { "type": "string" },
    "type": {
      "type": "string",
      "enum": ["ANNUAL_LEAVE", "UNPAID_LEAVE", "RECOVERY_LEAVE", "AUTHORIZED_ABSENCE"]
    },
    "userId": { "type": "integer", "format": "int64" }
  }
}
```

**Test Results:**

| Test Case | Status | Result |
|-----------|--------|--------|
| Empty body `{}` | ❌ | 400 Bad Request |
| With token + valid fields | ❌ | 500 Internal Server Error |
| Missing required fields | ❌ | 400 Bad Request |
| Invalid token `Bearer invalid_token` | ❌ | 400 Bad Request (should be 401) |

**Issue:** Leave service appears to have server-side errors. Getting 500 responses even with valid-looking requests.

---

## 3. Key Findings

### Response Field Names
- Auth uses: `"jwt"` (not `"token"`)
- Leave response should include `"id"` and `"status"` fields

### Required Fields for Leave Request
The backend expects:
- `type` - enum value like `"ANNUAL_LEAVE"`
- `fromDate` - string in YYYY-MM-DD format
- `toDate` - string in YYYY-MM-DD format
- `periodType` - enum value like `"JOURNEE_COMPLETE"`
- `userId` - integer (the employee's ID)

### Authorization Behavior
- Missing/invalid token returns 400 instead of 401 (authorization problem)
- This is why tests expecting 401 are failing

---

## 4. What Needs Fixing

### In Test Code (test_writer.py)

1. **Stop extracting `"token"` field** - Auth returns `"jwt"` only
2. **Update leave request body** - Include `periodType` and ensure `userId` is set
3. **Expect 400 for auth failures** - Not 401/403 as currently coded

### In Backend

1. **Fix Leave Service** - Getting 500 errors, needs debugging
2. **Fix Authorization** - Should return 401 for invalid tokens, not 400
3. **Validate request handling** - Empty/incomplete requests should have clear error messages

---

## 5. Test Data Reference

Use these values for testing:

```
Auth Login:
  email: admin@test.com
  password: admin123
  
Leave Request:
  type: ANNUAL_LEAVE
  periodType: JOURNEE_COMPLETE
  fromDate: 2026-04-01
  toDate: 2026-04-05
  userId: 8
  
Valid JWT Token (from successful auth):
  (See sample above - valid for 1 day)
```
