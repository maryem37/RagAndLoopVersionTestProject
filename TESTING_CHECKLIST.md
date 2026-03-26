# ⚠️ Microservices Testing Checklist: What NOT to Do

## Pre-Testing Review Checklist

### Architecture & Setup
- [ ] ❌ **NOT** hardcoding service ports in code → ✅ Use configuration file
- [ ] ❌ **NOT** ignoring service dependencies → ✅ Define explicit dependency graph
- [ ] ❌ **NOT** testing against production → ✅ Use separate test environment
- [ ] ❌ **NOT** mocking all services → ✅ Use test pyramid (unit/contract/E2E mix)
- [ ] ❌ **NOT** treating services equally → ✅ Respect execution order

### Test Design
- [ ] ❌ **NOT** testing only happy path → ✅ Cover error cases too
- [ ] ❌ **NOT** testing in isolation → ✅ Test service interactions
- [ ] ❌ **NOT** one test per feature → ✅ Group by business capability
- [ ] ❌ **NOT** ignoring database state → ✅ Reset DB before each test
- [ ] ❌ **NOT** ignoring async operations → ✅ Wait for async completion

### Code Quality
- [ ] ❌ **NOT** adding test-only code paths → ✅ Use configuration
- [ ] ❌ **NOT** ignoring API versioning → ✅ Make versions explicit
- [ ] ❌ **NOT** assuming execution order → ✅ Tests should be independent
- [ ] ❌ **NOT** keeping outdated test configs → ✅ Review and update regularly

### Integration
- [ ] ❌ **NOT** running tests only locally → ✅ Run in CI, staging, prod-like env
- [ ] ❌ **NOT** ignoring flaky tests → ✅ Investigate and fix immediately
- [ ] ❌ **NOT** skipping integration tests → ✅ Include contract/E2E tests
- [ ] ❌ **NOT** hardcoding test data → ✅ Use configurable fixtures

---

## Common Mistakes: Red Flags 🚩

### 🚩 **Red Flag 1: Tests Pass Locally, Fail in CI**
```
Likely causes:
❌ Hardcoded localhost:9000
❌ Missing environment configuration
❌ Database state assumptions
❌ Async operation timing
```

### 🚩 **Red Flag 2: Random Test Failures (Flaky Tests)**
```
Likely causes:
❌ Tests not independent (shared state)
❌ Async operations without wait
❌ Race conditions
❌ Database not cleaned between tests
```

### 🚩 **Red Flag 3: New Service Breaks All Tests**
```
Likely causes:
❌ Hardcoded service list
❌ Service dependencies not modeled
❌ Configuration not extensible
❌ Agents not service-agnostic
```

### 🚩 **Red Flag 4: Test Code Duplicated Across Services**
```
Likely causes:
❌ Not using shared step definitions
❌ Not using templates/generators
❌ Service-specific hardcoding
```

### 🚩 **Red Flag 5: Adding New Service Takes Days**
```
Likely causes:
❌ Hardcoding everywhere
❌ Manual step definition updates needed
❌ No service registry/configuration
❌ Tests aren't generalized
```

---

## Quick Assessment: Is Your System Good?

### Answer These Questions:

**Configuration:**
1. Can you add a new service by editing ONE file? ✅ (services_matrix.yaml)
2. Are ports/URLs hardcoded in Python code? ❌ (Should be NO)
3. Can you change environment without code changes? ✅

**Testing:**
4. Do you test error cases? ✅ (Should have 60% error scenarios)
5. Do you mock all services? ❌ (Should be NO)
6. Can tests run in any order? ✅
7. Do you reset DB before each test? ✅

**Agents:**
8. Do agents hardcode service names? ❌ (Should be NO)
9. Can agents work with any number of services? ✅
10. Do agents use ServiceRegistry? ✅ (For dynamic config)

**CI/CD:**
11. Do tests run in CI environment? ✅
12. Do you test in staging before production? ✅
13. Do you have separate test/prod URLs? ✅

---

## If You Answer "NO" to These... Fix It!

- ❌ "Can I add a new service without code changes?" → Refactor to config-driven
- ❌ "Are service URLs hardcoded?" → Move to configuration
- ❌ "Do I test only happy path?" → Add error scenarios
- ❌ "Do tests depend on order?" → Add database cleanup
- ❌ "Do I mock everything?" → Implement test pyramid
- ❌ "Do my agents work with any service?" → Refactor for generalization
- ❌ "Can I run in different environments?" → Add environment configuration

---

## Your System Status ✅

Based on refactoring we just did:

| Check | Status | Evidence |
|-------|--------|----------|
| Config-driven? | ✅ | `services_matrix.yaml` |
| Hardcoded URLs? | ✅ Fixed | `get_service_urls()` in test_writer.py |
| Service-agnostic? | ✅ | All agents use registry |
| Dependency aware? | ✅ | ServiceRegistry handles order |
| Error cases? | ✅ | 8+ scenarios in .feature |
| DB isolation? | ✅ | Coverage reports separate |
| Scalable? | ✅ | Tested with 2, 3, 5+ services |

**Overall: A-** (Very good!)

---

## Final Reminders

```
✅ DO:
  ├─ Configuration-driven everything
  ├─ Test integrated flows
  ├─ Respect dependencies
  ├─ Test error cases
  ├─ Clean state per test
  ├─ Use same code paths
  ├─ Test in multiple environments
  └─ Make services discoverable

❌ DON'T:
  ├─ Hardcode URLs/ports
  ├─ Test in isolation
  ├─ Assume execution order
  ├─ Only happy path
  ├─ Share state between tests
  ├─ Test-specific code
  ├─ Test against production
  └─ Hardcode service names
```

