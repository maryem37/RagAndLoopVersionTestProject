# Test Execution Guide

## Quick Start

### Prerequisites
1. JDK 11 or higher installed
2. Maven 3.6 or higher
3. For integration tests: Services running on required ports

### Basic Test Execution

```bash
# Navigate to test directory
cd output/tests

# Run all tests
mvn clean test

# Run tests with coverage report
mvn clean test jacoco:report

# View coverage report
# Windows
start target/site/jacoco/index.html

# macOS
open target/site/jacoco/index.html

# Linux
xdg-open target/site/jacoco/index.html
```

## Test Categories

### Unit Tests (Fast - ~5 seconds)
```bash
mvn test -Dtest=*Service*Test
```

### Integration Tests (Medium - ~30 seconds)
```bash
mvn test -Dtest=*Integration*Test
```

**Required before running**:
```bash
# Terminal 1: Start Auth Service
java -jar auth-service.jar --server.port=9000

# Terminal 2: Start Leave Service
java -jar leave-service.jar --server.port=8080

# Terminal 3: Run tests
mvn test -Dtest=*Integration*Test
```

### E2E Tests (Slow - ~1 minute)
```bash
mvn test -Dtest=*E2E*Test
```

### Contract Tests
```bash
mvn test -Dtest=*Contract*Test
```

## Advanced Test Execution

### Run Single Test Class
```bash
mvn test -Dtest=AuthServiceTest
```

### Run Single Test Method
```bash
mvn test -Dtest=AuthServiceTest#testLoginWithValidCredentials
```

### Run Tests Matching Pattern
```bash
# All tests with "Login" in name
mvn test -Dtest=*Test -Dgroups="login"

# All tests containing "Auth"
mvn test -Dtest=Auth*
```

### Run Tests in Parallel
```bash
mvn test -Dparallelism=4
```

### Skip Tests During Build
```bash
mvn clean package -DskipTests
```

## Coverage Reports

### Generate Coverage Report
```bash
mvn clean test jacoco:report
```

### View Report
- File: `target/site/jacoco/index.html`
- Shows line and branch coverage
- Identifies untested code

### Coverage Targets
- **Line Coverage**: 80%+ target
- **Branch Coverage**: 75%+ target
- **Critical Code**: 90%+ target

## Test Reports

### View Surefire Report
```bash
# Generate and open
mvn surefire-report:report
open target/site/surefire-report.html
```

### Test Results Summary
- Location: `target/surefire-reports/`
- Formats: TXT, XML
- Contains test execution times and failures

## Debugging Tests

### Run with Debug Output
```bash
mvn test -X
```

### Run Single Test with Debugging
```bash
mvn -Dmaven.surefire.debug test -Dtest=AuthServiceTest#testLoginWithValidCredentials
```

### Enable Test Logging
Set in `application-test.properties`:
```properties
logging.level.root=DEBUG
logging.level.com.example=DEBUG
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up JDK
        uses: actions/setup-java@v2
        with:
          java-version: '11'
      - name: Run tests
        run: mvn clean test jacoco:report
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v2
```

### Jenkins Pipeline Example
```groovy
pipeline {
    stages {
        stage('Test') {
            steps {
                sh 'mvn clean test jacoco:report'
            }
        }
        stage('Coverage Report') {
            steps {
                publishHTML([
                    reportDir: 'target/site/jacoco',
                    reportFiles: 'index.html',
                    reportName: 'Code Coverage'
                ])
            }
        }
    }
}
```

## Troubleshooting

### Build Failures

#### Issue: `No tests found`
```bash
# Verify Maven Surefire configuration
mvn help:active-profiles
mvn test -DskipTests=false -Dtest=AuthServiceTest
```

#### Issue: `Port already in use` (Integration tests)
```bash
# Kill process on port 9000 (Windows)
netstat -ano | findstr :9000
taskkill /PID <PID> /F

# Kill process on port 9000 (Unix)
lsof -ti :9000 | xargs kill -9
```

#### Issue: `OutOfMemoryError`
```bash
# Increase heap memory
export MAVEN_OPTS="-Xmx1024m"
mvn clean test
```

### Test Failures

#### Issue: Flaky tests (intermittent failures)
- Check for time-dependent assertions
- Verify thread safety in tests
- Add `@Timeout` annotations

#### Issue: Database lock errors
- Ensure H2 test database cleanup
- Check transaction isolation levels
- Review test order dependencies

#### Issue: JWT token expiration in tests
- Use mock time in tests
- Generate fresh tokens per test
- Check token TTL configuration

## Performance Optimization

### Test Execution Time
```bash
# Show slowest tests
mvn test -DshowSuccess=false

# Run tests in parallel (requires JUnit 5)
mvn test -Dparallelism=4 -Dparallel=methods
```

### Best Practices
1. Use unit tests for fast feedback
2. Mock external dependencies
3. Use in-memory database (H2)
4. Minimize fixture setup
5. Avoid sleep/wait in tests

## Test Data Management

### Reset Test Data
```bash
# H2 database is recreated for each test run
mvn clean test
```

### Use Custom Test Data
Edit `application-test.properties`:
```properties
spring.datasource.url=jdbc:h2:mem:testdb
spring.jpa.hibernate.ddl-auto=create-drop
```

## Continuous Monitoring

### Watch Tests During Development
```bash
# Install watch tool
npm install -g watch

# Run tests on file changes
watch 'mvn test' src
```

## Test Checklist

Before committing code:
- [ ] All unit tests pass
- [ ] Code coverage meets 80% minimum
- [ ] No new compiler warnings
- [ ] Integration tests pass (with services)
- [ ] No hardcoded test data
- [ ] Descriptive test method names
- [ ] Comments on complex test logic

---

**Last Updated**: 2025-03-21
**Version**: 1.0.0
