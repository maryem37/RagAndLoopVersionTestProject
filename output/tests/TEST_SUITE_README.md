# Comprehensive Test Suite Documentation

## Overview
This directory contains a comprehensive test suite for the Leave Request Management System with unit tests, integration tests, and contract tests.

## Test Structure

### 1. Unit Tests

#### AuthServiceTest
- **Location**: `src/test/java/com/example/auth/service/AuthServiceTest.java`
- **Purpose**: Tests the business logic of the AuthService class
- **Test Cases**:
  - `testLoginWithValidCredentials()` - Verifies successful login with valid credentials
  - `testLoginWithInvalidPassword()` - Validates exception thrown for wrong password
  - `testLoginWithNonExistentUser()` - Checks handling of non-existent users
  - `testRegisterNewUser()` - Tests new user registration
  - `testRegisterDuplicateEmail()` - Validates duplicate email handling
  - `testValidateValidToken()` - Confirms JWT token validation
  - `testValidateInvalidToken()` - Tests invalid token handling
  - `testGetEmailFromToken()` - Verifies email extraction from JWT
  - `testChangePassword()` - Tests password change functionality

**Key Features**:
- Uses Mockito for dependency injection and mocking
- Tests error scenarios and edge cases
- Validates all method interactions

#### LeaveRequestServiceTest
- **Location**: `src/test/java/com/example/leave/service/LeaveRequestServiceTest.java`
- **Purpose**: Tests the business logic of the LeaveRequestService class
- **Test Cases**:
  - `testCreateLeaveRequest()` - Tests leave request creation
  - `testGetLeaveRequestById()` - Retrieves specific leave requests
  - `testGetLeaveRequestByIdNotFound()` - Handles non-existent requests
  - `testGetLeaveRequestsByEmployeeId()` - Retrieves employee's leave requests
  - `testApproveLeaveRequest()` - Tests approval workflow
  - `testRejectLeaveRequest()` - Tests rejection workflow
  - `testCancelLeaveRequest()` - Tests cancellation workflow
  - `testGetPendingLeaveRequests()` - Filters pending requests
  - `testCheckLeaveBalance()` - Calculates available leave days
  - `testDeleteLeaveRequest()` - Tests deletion functionality
  - `testValidateLeaveDatesOverlapping()` - Rejects overlapping dates
  - `testValidateLeaveDatesNonOverlapping()` - Accepts valid dates

**Key Features**:
- Comprehensive workflow testing
- Date validation scenarios
- Leave balance calculations

### 2. Integration Tests

#### AuthControllerIntegrationTest
- **Location**: `src/test/java/com/example/auth/integration/AuthControllerIntegrationTest.java`
- **Purpose**: Tests HTTP API endpoints with actual server
- **Prerequisites**: Server running on `http://localhost:9000`
- **Test Cases**:
  - `testLoginInvalidCredentials()` - Tests login with wrong credentials
  - `testLoginValidCredentials()` - Tests successful login
  - `testRegisterNewUser()` - Tests user registration via API
  - `testGetUserWithoutJWT()` - Tests authorization validation
  - `testChangePassword()` - Tests password change endpoint

**Key Features**:
- Uses RestAssured for HTTP testing
- Tests complete request/response cycles
- Validates HTTP status codes and response bodies
- Flexible status code matching for different implementations

#### LeaveControllerIntegrationTest
- **Location**: `src/test/java/com/example/leave/integration/LeaveControllerIntegrationTest.java`
- **Purpose**: Tests Leave API endpoints
- **Prerequisites**: Server running on `http://localhost:8080`
- **Test Cases**:
  - `testGetAllLeaveRequests()` - Retrieves all leave requests
  - `testGetLeaveRequestById()` - Gets specific leave request
  - `testCreateLeaveRequest()` - Creates new leave request
  - `testUpdateLeaveRequestStatus()` - Updates request status
  - `testDeleteLeaveRequest()` - Deletes leave request

**Key Features**:
- Comprehensive CRUD operations testing
- Status code validation
- Response body assertions

### 3. E2E Tests

#### LeaveRequestE2ETest
- **Location**: `src/test/java/com/example/leave/e2e/LeaveRequestE2ETest.java`
- **Purpose**: Tests complete workflows from authentication through leave management
- **Test Scenarios**:
  - User login → Create leave request → Approval workflow
  - Error handling for invalid data
  - Multi-step workflows with state transitions

**Key Features**:
- Tests complete business scenarios
- Validates state consistency
- Tests error recovery

### 4. Contract Tests

#### AuthServiceContractTest
- **Location**: `src/test/java/com/example/auth/contract/AuthServiceContractTest.java`
- **Purpose**: Ensures compatibility with external services
- **Key Aspects**:
  - Validates API contract compliance
  - Tests request/response formats
  - Ensures backward compatibility

#### LeaveServiceContractTest
- **Location**: `src/test/java/com/example/leave/contract/LeaveServiceContractTest.java`
- **Purpose**: Validates internal service contracts

## Running the Tests

### Run All Tests
```bash
mvn test
```

### Run Specific Test Class
```bash
mvn test -Dtest=AuthServiceTest
```

### Run Specific Test Method
```bash
mvn test -Dtest=AuthServiceTest#testLoginWithValidCredentials
```

### Run with Code Coverage
```bash
mvn clean test jacoco:report
```

### Run Integration Tests Only
```bash
mvn test -Dtest=*IntegrationTest
```

### Run E2E Tests Only
```bash
mvn test -Dtest=*E2ETest
```

## Test Configuration

### Properties Files
- **Test Configuration**: `src/test/resources/application-test.properties`
- **Integration Test Config**: `src/test/resources/application-integration.properties`

### Database Setup
- Tests use in-memory H2 database for speed
- Automatically initialized with test data

## Test Reports

### Coverage Reports
After running tests with coverage:
```bash
open target/site/jacoco/index.html
```

### Surefire Reports
```bash
open target/site/surefire-report.html
```

## Best Practices Implemented

### Unit Tests
✓ Uses Mockito for dependency isolation
✓ Tests single responsibility
✓ Clear test method names
✓ Proper setup and teardown

### Integration Tests
✓ Tests real HTTP communication
✓ Uses RestAssured fluent API
✓ Flexible assertion matching
✓ Handles multiple response scenarios

### Test Data
✓ Consistent test fixtures
✓ Realistic test scenarios
✓ Proper date handling
✓ Edge case coverage

### Documentation
✓ Clear test class purpose
✓ Descriptive @DisplayName annotations
✓ Well-commented test logic
✓ README with usage instructions

## Dependencies

### Testing Libraries
- JUnit 5 (Jupiter)
- Mockito 4.x
- RestAssured 5.x
- Hamcrest Matchers

### Required for Running Tests
- JDK 11+
- Maven 3.6+
- Running microservices for integration tests

## Common Issues & Solutions

### Issue: Integration tests fail with connection refused
**Solution**: Ensure services are running on required ports:
- Auth Service: `http://localhost:9000`
- Leave Service: `http://localhost:8080`

### Issue: JWT token tests fail
**Solution**: Verify JWT secret configuration in test properties

### Issue: Date-based tests fail in different timezones
**Solution**: Tests use LocalDate (timezone-independent)

## Future Enhancements

- [ ] Add performance testing with JMH
- [ ] Add security testing with OWASP ZAP
- [ ] Add mutation testing with PIT
- [ ] Add load testing with JMeter
- [ ] Add API documentation tests with Springdoc
- [ ] Add accessibility testing

## Contact & Support

For issues or questions about the test suite:
1. Check this documentation
2. Review test class comments
3. Check test failure output for details
4. Consult team documentation

---

**Last Updated**: 2025-03-21
**Version**: 1.0.0
