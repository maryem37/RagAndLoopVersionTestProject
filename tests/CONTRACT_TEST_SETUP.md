# Contract-Level E2E Test Setup for leave-request-service

## 🎯 **Test Type: CONTRACT-LEVEL E2E**

These tests validate:
✅ API endpoints exist and respond
✅ Request/response structure compatibility
✅ Service-to-service communication

These tests DO NOT validate:
❌ Business logic (e.g., balance checks, approval rules)
❌ Authentication/Authorization (assumes pre-configured tokens)
❌ Test data creation (assumes data exists or uses stubs)

## 📦 Required Dependencies

Add these to your microservice `pom.xml`:
```xml
<!-- ============================================ -->
<!-- Contract-Level E2E Test Dependencies -->
<!-- Add these to your existing <dependencies> section -->
<!-- ============================================ -->

<!-- Cucumber -->
<dependency>
    <groupId>io.cucumber</groupId>
    <artifactId>cucumber-java</artifactId>
    <version>7.14.0</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>io.cucumber</groupId>
    <artifactId>cucumber-junit</artifactId>
    <version>7.14.0</version>
    <scope>test</scope>
</dependency>

<!-- RestAssured for API Testing -->
<dependency>
    <groupId>io.rest-assured</groupId>
    <artifactId>rest-assured</artifactId>
    <version>5.3.2</version>
    <scope>test</scope>
</dependency>

<!-- AssertJ for Fluent Assertions -->
<dependency>
    <groupId>org.assertj</groupId>
    <artifactId>assertj-core</artifactId>
    <version>3.24.2</version>
    <scope>test</scope>
</dependency>

<!-- SLF4J for Logging -->
<dependency>
    <groupId>org.slf4j</groupId>
    <artifactId>slf4j-api</artifactId>
    <version>2.0.9</version>
    <scope>test</scope>
</dependency>

<!-- JUnit 4 (if not already present) -->
<dependency>
    <groupId>junit</groupId>
    <artifactId>junit</artifactId>
    <version>4.13.2</version>
    <scope>test</scope>
</dependency>

```

## 🔐 Authentication Setup

Contract tests require a pre-configured JWT token:
```bash
# Set environment variable before running tests
export TEST_JWT_TOKEN="your-valid-jwt-token-here"

# Or in CI/CD (GitHub Actions example)
env:
  TEST_JWT_TOKEN: ${{ secrets.TEST_JWT_TOKEN }}
```

## 🚀 Running Tests
```bash
# With token
export TEST_JWT_TOKEN="valid-token"
mvn test -Dtest=ContractTestRunner

# Or run all contract tests
mvn test -Dcucumber.filter.tags="@contract"
```

## 📝 Important Notes

1. **Test Data**: These tests assume data exists. Pre-seed your test environment.
2. **Authentication**: Tokens must be valid. Use a dedicated test user.
3. **Environment**: Point to test/staging environment, NOT production.
4. **CI/CD**: Store JWT token as secret, inject via environment variable.

## 🏗️ Test Philosophy

> "The TestWriter agent generates contract-level end-to-end API tests, 
> validating service interoperability and API compatibility rather than 
> business rules, data correctness, or authorization semantics."

## ⚠️ What These Tests Do NOT Cover

- Business rule validation (use unit/integration tests)
- Authorization logic (use security-focused tests)
- Data correctness (use business logic tests)
- Performance/load (use dedicated performance tests)

## 📁 Generated Files

- **Step Definitions**: `src\test\java\com\example\leaverequestservice\steps\LeaveRequestServiceSteps.java`
- **Test Runner**: `src\test\java\com\example\leaverequestservice\ContractTestRunner.java`
