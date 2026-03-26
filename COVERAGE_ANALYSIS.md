# Code Coverage Analysis & Improvement Plan

**Status**: March 24, 2026 | **Current Baseline**: 17.92% | **Target**: 60%+

---

## Executive Summary

**Coverage Baseline (March 21, 2026):**
- **Line Coverage**: 43/240 lines (17.92%)
- **Branch Coverage**: 1/358 branches (0.28%)
- **Method Coverage**: 23/157 methods (14.65%)
- **Tests Executed**: 16 tests (0 failures)
- **Quality Gate**: ❌ FAILED (all thresholds below requirements)

**Gap to Target**:
- Line Coverage: 17.92% → 60% = **+42.08% needed**
- Branch Coverage: 0.28% → 50% = **+49.72% needed**
- Method Coverage: 14.65% → 70% = **+55.35% needed**

---

## Coverage by Package (Baseline Analysis)

### ✅ Fully Covered (100%)
| Package | Lines | Methods | File |
|---------|-------|---------|------|
| `tn.enis.conge` | 3/3 (100%) | 2/2 (100%) | CongeeApplication.java |
| `tn.enis.conge.configuration` | 24/42 (57%) | 9/11 (82%) | WebSecurityConfiguration.java |

### ⚠️ Partially Covered
| Package | Lines | Methods | Issue |
|---------|-------|---------|-------|
| `tn.enis.conge.controller` | 4/62 (6.45%) | 4/14 (28%) | Controllers not tested |
| `tn.enis.conge.services` | 12/56 (21%) | 8/28 (29%) | Business logic untested |
| `tn.enis.conge.dto` | 0/18 (0%) | - | No mapping tests |

### ❌ Uncovered (0%)
| Package | Classes | Issue |
|----------|---------|-------|
| `tn.enis.conge.entity` | 8 classes | No entity tests |
| `tn.enis.conge.utils` | 3 classes | No utility tests |
| `tn.enis.conge.repository` | 2 classes | No repository tests |

---

## Root Causes of Low Coverage

### 1. **Missing Unit Tests for Business Logic**
- Controllers have only 6.45% coverage (4/62 lines)
- Services have only 21% coverage (12/56 lines)
- DTO mappers have 0% coverage

**Impact**: No validation of request handling, validation logic, or error cases

### 2. **HTTP Integration Tests Only**
- Current test pipeline creates HTTP endpoint tests
- These test response codes, not business logic
- HTTP tests don't execute internal service methods
- JaCoCo can't monitor code execution through HTTP proxies

**Impact**: Even with working HTTP tests, no bytecode coverage collected

### 3. **Missing Database/Repository Tests**
- `JpaRepository` classes not tested (0%)
- No tests for data persistence layer
- Query methods not validated

**Impact**: 40% of codebase untouched

### 4. **No Exception Handling Tests**
- Error paths not covered
- Validation errors not tested
- Edge cases missing

**Impact**: Error handling code unmeasured

---

## Recommended Improvement Strategy

### Phase 1: Quick Wins (Target: 25-30% coverage)
**Effort**: 2-3 hours | **Expected Gain**: +10%

1. **Write Service Layer Unit Tests**
   - Test `LeaveService` core methods
   - Mock database/repository
   - Use Mockito for dependencies
   - Target: Service classes 50%+ coverage

2. **Write Controller Tests**
   - Test `LeaveController` endpoints
   - Mock `LeaveService`
   - Test valid/invalid inputs
   - Test response codes and content

3. **Add DTO/Mapper Tests**
   - Test object conversions
   - Test null handling
   - Quick-win classes (100% easy)

**Files to Create**:
```
output/tests/src/test/java/tn/enis/conge/
  └── services/
      └── LeaveServiceTest.java
  └── controller/
      └── LeaveControllerTest.java
  └── dto/
      └── LeaveRequestMapperTest.java
```

### Phase 2: Core Logic Coverage (Target: 45-50%)
**Effort**: 4-5 hours | **Expected Gain**: +15-20%

1. **Comprehensive Service Tests**
   - Leave balance validation
   - Request status transitions
   - Date range validation
   - Conflict detection

2. **Repository/JPA Tests**
   - Persistence tests with H2 test database
   - Query validation
   - Update/delete operations

3. **Utility Method Tests**
   - Date utilities
   - String formatters
   - Helper methods

### Phase 3: Edge Cases & Error Paths (Target: 60%+)
**Effort**: 3-4 hours | **Expected Gain**: +10-15%

1. **Exception Handling**
   - Invalid leave types
   - Past date requests
   - Balance insufficiency
   - Authorization failures

2. **Boundary Conditions**
   - Zero-day requests
   - Overlapping leave periods
   - Maximum continuous days
   - Notice period violations

3. **Integration Scenarios**
   - Multi-step approval workflows
   - Concurrent requests
   - Balance updates

---

## Implementation Instructions

### Add JUnit5 + Mockito Dependencies to Microservice POM

```xml
<!-- Add to C:\Bureau\Bureau\microservices\conge\pom.xml <dependencies> -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.mockito</groupId>
    <artifactId>mockito-core</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>com.h2database</groupId>
    <artifactId>h2</artifactId>
    <scope>test</scope>
</dependency>
```

### Add JaCoCo Plugin to Microservice POM

```xml
<!-- Add to <build><plugins> -->
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.11</version>
    <executions>
        <execution>
            <goals><goal>prepare-agent</goal></goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>verify</phase>
            <goals><goal>report</goal></goals>
        </execution>
    </executions>
</plugin>
```

### Generate Coverage Report

```powershell
cd C:\Bureau\Bureau\microservices\conge
mvn clean test jacoco:report
# Report will be at: target/site/jacoco/index.html
```

---

## Current Setup Status

✅ **Completed**:
- Services running with JaCoCo agent instrumentation
- Test pipeline configured (run_pipeline.py)
- Baseline coverage documented (17.92%)
- 86 BDD test steps defined
- 14 passing integration tests

⚠️ **In Progress**:
- Unit test implementation
- Service layer testing
- JaCoCo report integration

❌ **Not Yet Started**:
- Controller unit tests
- Repository tests
- Exception handling tests
- Edge case coverage

---

## Running Coverage

**Quick Coverage Check**:
```powershell
cd C:\Bureau\Bureau\project_test
python run_pipeline.py --services auth
# Generates: output/reports/coverage_report_auth_*.yaml
```

**Full Microservice Coverage**:
```powershell
cd C:\Bureau\Bureau\microservices\conge
mvn clean test jacoco:report
# Generates: target/site/jacoco/index.html
```

**View HTML Report**:
```powershell
Start-Process "C:\Bureau\Bureau\microservices\conge\target\site\jacoco\index.html"
```

---

## Progress Tracking

| Phase | Status | Coverage | Tests | Est. Time |
|-------|--------|----------|-------|-----------|
| Baseline | ✅ Complete | 17.92% | 16 | - |
| Phase 1: Quick Wins | ⏳ Ready | Target: 25-30% | 40+ | 2-3h |
| Phase 2: Core Logic | ⏳ Planned | Target: 45-50% | 60+ | 4-5h |
| Phase 3: Edge Cases | ⏳ Planned | Target: 60%+ | 80+ | 3-4h |

---

## Key Metrics for Success

✅ **Goal**: Reach 60% line coverage
- [ ] Service tests: 50%+ coverage
- [ ] Controller tests: 40%+ coverage  
- [ ] DTO/Utility tests: 80%+ coverage
- [ ] Exception handling: All paths covered
- [ ] Quality gates: All passing

---

## Resources

- [JaCoCo Maven Plugin](https://www.jacoco.org/jacoco/trunk/doc/maven.html)
- [JUnit5 Documentation](https://junit.org/junit5/docs/current/user-guide/)
- [Mockito Documentation](https://javadoc.io/doc/org.mockito/mockito-core/latest/org/mockito/Mockito.html)
- [Spring Test Guide](https://spring.io/guides/gs/testing-web/)

---

**Last Updated**: March 24, 2026  
**Baseline Report**: `output/reports/coverage_report_BASELINE_17.92percent.yaml`
