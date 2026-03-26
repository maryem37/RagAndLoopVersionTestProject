# Real JaCoCo Coverage Results - March 24, 2026

## Summary

✅ **Successfully configured JaCoCo Maven plugin on microservices**

The first actual bytecode coverage measurement shows **12% line coverage** on the conge (Leave) service.

---

## Coverage Report: conge Service

**Generated**: March 24, 2026 02:39 UTC+1  
**Total Classes**: 22  
**Total Packages**: 9  

### Overall Metrics

| Metric | Value | Status |
|--------|-------|--------|
| **Line Coverage** | 12% (311/2583) | ⚠️ LOW |
| **Branch Coverage** | 0% (1/358) | ❌ CRITICAL |
| **Method Coverage** | 64% (255/394) | ✅ GOOD |

### Coverage by Package (Highest to Lowest)

| Package | Line % | Branch % | Method % | Classes |
|---------|--------|----------|----------|---------|
| **tn.enis.conge.enums** | 100% | n/a | 100% | 1 ✅ |
| **tn.enis.conge.configuration** | 71% | 0% | 100% | 2 |
| **tn.enis.conge.services.jwt** | 28% | n/a | 66% | 1 |
| **tn.enis.conge.controller** | 10% | 0% | 71% | 4 |
| **tn.enis.conge.services.auth** | 9% | 12% | 60% | 1 |
| **tn.enis.conge.services.depart** | 7% | 0% | 85% | 1 |
| **tn.enis.conge.utils** | 3% | 0% | 90% | 1 |
| **tn.enis.conge.entity** | 1% | 0% | 4% | 2 |
| **tn.enis.conge.dto** | 0% | 0% | 0% | 4 |

### Key Observations

**Strengths:**
- ✅ Enums fully tested (100%)
- ✅ Configuration well covered (71%)
- ✅ Method coverage solid (64% overall)
- ✅ JWT utilities partially covered (28%)

**Gaps:**
- ❌ DTOs completely untested (0%)
- ❌ Entities almost untested (1%)
- ❌ Controllers barely tested (10%)
- ❌ Services minimally tested (7-9%)
- ❌ Branch coverage almost zero (0%)

---

## Comparison to Baseline

| Metric | Baseline (Mar 21) | Current (Mar 24) | Change |
|--------|-------------------|------------------|--------|
| Line Coverage | 17.92% | 12% | ⬇️ -5.92% |
| Branch Coverage | 0.28% | 0% | ⬇️ -0.28% |
| Method Coverage | 14.65% | 64% | ⬆️ +49.35% |

**Analysis**: 
- Method coverage is much higher (64% vs 14.65%) because many methods exist but aren't called
- Line coverage dropped because we're now testing with the base test class only (1 test)
- The original 17.92% came from more extensive testing - need to write real unit tests to recover and exceed it

---

## HTML Report Location

**Path**: `C:\Bureau\Bureau\microservices\conge\target\site\jacoco\index.html`

**Access it:**
```powershell
cd C:\Bureau\Bureau\microservices\conge
Start-Process target\site\jacoco\index.html
```

---

## What's Needed to Reach 60%

Based on this analysis:

### Priority 1: Write DTO Tests (Currently 0%)
- All 4 DTO classes untested
- **Effort**: 30 min
- **Expected gain**: +5-8%

```java
// Example: LeaveRequestDTO test
@Test
void testLeaveRequestDTO() {
    LeaveRequestDTO dto = new LeaveRequestDTO();
    dto.setUserId(8L);
    dto.setFromDate("2026-06-01");
    assertEquals(8L, dto.getUserId());
}
```

### Priority 2: Write Entity Tests (Currently 1%)
- 2 entity classes with 20+ properties each
- **Effort**: 45 min
- **Expected gain**: +8-10%

```java
// Example: LeaveRequest entity test
@Test
void testLeaveRequestEntity() {
    LeaveRequest entity = new LeaveRequest();
    entity.setId(1L);
    entity.setStatus("PENDING");
    assertEquals("PENDING", entity.getStatus());
}
```

### Priority 3: Write Service Layer Tests (Currently 7-9%)
- `LeaveService`, `DepartService`, `AuthService` - complex logic
- **Effort**: 2-3 hours (need mocking + multiple test cases)
- **Expected gain**: +25-30%

```java
@Test
void testSubmitLeaveRequest() {
    LeaveRequest result = leaveService.submitLeaveRequest(dto);
    assertNotNull(result);
    verify(leaveRequestRepository).save(any());
}
```

### Priority 4: Write Controller Tests (Currently 10%)
- 4 controller classes
- **Effort**: 1-2 hours
- **Expected gain**: +10-15%

```java
@Test
void testGetLeaveRequests() throws Exception {
    mockMvc.perform(get("/api/leave-requests"))
        .andExpect(status().isOk());
}
```

### Priority 5: Branch Coverage (Currently 0%)
- Add tests for conditionals, loops
- **Effort**: 2-3 hours
- **Expected gain**: +15-20%

---

## Commands Reference

### Generate JaCoCo Report
```powershell
cd C:\Bureau\Bureau\microservices\conge
mvn clean test jacoco:report
```

### View HTML Report
```powershell
Start-Process target\site\jacoco\index.html
```

### Check Report Summary (XML)
```powershell
Get-Content target\jacoco\jacoco.xml | Select-String "covered|missed"
```

---

## Next Steps

1. **Add test templates** from `UNIT_TEST_QUICKSTART.md`
2. **Start with DTOs** (0% → easiest win)
3. **Then Entities** (1% → straightforward)
4. **Then Services** (7-9% → complex but high impact)
5. **Monitor progress** with `mvn jacoco:report` after each phase

**Expected timeline**:
- DTOs + Entities: 1 hour → **20-25% coverage**
- Add Services: 2-3 hours → **50-55% coverage**
- Add Controllers + branches: 1-2 hours → **65%+ coverage**

---

## Technical Details

### JaCoCo Plugin Configuration

Added to both microservices' `pom.xml`:

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.11</version>
    <executions>
        <execution>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
    </executions>
</plugin>
```

### Report Files Generated

```
target/
├── jacoco/
│   ├── jacoco.exec          # Raw execution data
│   └── index.xml            # Coverage data in XML
└── site/jacoco/
    ├── index.html           # Main HTML report
    ├── jacoco-sessions.html # Session info
    └── [packages]/          # Package-level reports
```

---

## Status: ✅ READY FOR UNIT TESTING

The infrastructure is now in place. Next phase: write unit tests following the templates in `UNIT_TEST_QUICKSTART.md` to improve coverage from 12% to 60%+.
