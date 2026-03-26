# Why Coverage is Low (17.92%) - Final Analysis

## Summary

**Coverage is low because only 13 out of 28 tests pass (46% pass rate).** JaCoCo only measures code executed during PASSING tests. With 15 failing tests, only ~43 lines out of 240 get executed, leaving coverage at 17.92%.

## Three Layers of Problems

### Layer 1: Undefined Steps (Primary Blocker)
**Problem**: 15 tests fail with "undefined step" errors
- Gherkin features say: `Given the employee has sufficient leave balance`  
- Generated Java has: `@Given("the employee has sufficient **annual** leave balance")`
- **Cucumber can't match them** → Step is "undefined" → Test fails

**Root Cause**: Gherkin generator and test_writer are out of sync
- Gherkin generator creates feature files with variant step text
- Test writer generates Java annotations with different text
- Example: "sufficient leave balance" vs "sufficient **annual** leave balance"

### Layer 2: Missing Step Handlers (Secondary Blocker)
**Problem**: test_writer.py doesn't have handlers for all step variations
- Feature says: `When the employee submits a leave request with past dates`
- No handler exists for this specific text pattern
- Falls back to generic logging-only handler
- **HTTP calls are never made** → Service code isn't exercised

### Layer 3: Low Test Scenario Count (Tertiary Issue)
**Problem**: Even if all 28 tests passed, they'd still only cover 25-30% of code
- Current scenarios only test "create" endpoint
- Missing scenarios:
  - Approve leave request
  - Reject leave request
  - Cancel leave request
  - Balance validation
  - Date validation
  - etc.

**Estimate**: Need 40-50 test scenarios total to reach 60% coverage

## Evidence

### Test Execution Summary (Last Successful Run)
```
Tests total:  28
Tests passed: 13 (46%)
Tests failed: 15 (54%)
Coverage:     17.92% (43/240 lines)
```

### Sample Undefined Steps
```
[ERROR] The step 'the employee has sufficient leave balance' is undefined.
  You can implement this step using the snippet(s) below:
  
  @Given("the employee has sufficient leave balance")
  public void the_employee_has_sufficient_leave_balance() {
    throw new io.cucumber.java.PendingException();
  }
```

### Actual Generated Annotation
```java
@Given("the employee has sufficient annual leave balance")  // ← "annual" was added!
public void theEmployeeHasSufficientAnnualLeaveBalance() {
    logger.info("Precondition: the employee has sufficient annual leave balance");
}
```

## How to Fix

### Fix #1: Align Gherkin Generator & Test Writer
- **Option A**: Modify gherkin_generator to always use consistent step text  
  - All balance checks: "the employee has sufficient leave balance" (no "annual")
  - All submits: "the employee submits a leave request" (no "annual")
  
- **Option B**: Modify test_writer to handle all variations
  - Add handlers that match both "sufficient balance" AND "sufficient annual balance"
  - Current status: Partially done (added 1 handler)

### Fix #2: Add Missing Step Handlers  
For each unique step pattern in the feature file, ensure test_writer.py has a handler.

Missing handlers (samples):
```python
if "submits a leave request with past dates" in tl:
    return _j([...code to set fromDate in past...])

if "submits a leave request with an invalid leave type" in tl:
    return _j([...code to set invalid type...])

if "submits a leave request with empty/null fields" in tl:
    return _j([...code to omit required fields...])
```

### Fix #3: Generate Additional Test Scenarios
Once Fixes #1-2 are working and all 28 tests pass:
- Generate features for: approve, reject, cancel, overlap detection, balance limits
- **Expected result**: Coverage increases to 30-40%
- **Then add more**: Additional edge cases, different user roles, etc.
- **Target**: 50+ scenarios total for 60%+ coverage

## Implementation Status

**Done:**
- ✅ Identified root causes (3 layers)
- ✅ Added some step handlers to test_writer.py
- ✅ Documented the problem

**In Progress:**
- ⏳ Align gherkin generator and test writer step text
- ⏳ Add remaining step handlers for all feature scenarios

**Not Started:**
- ❌ Generate additional feature scenarios (approve, reject, cancel, etc.)
- ❌ Run tests with all handlers in place
- ❌ Measure coverage improvement

## Next Immediate Steps

1. **Fix Gherkin/test_writer mismatch**
   - Either: Remove "annual" from gherkin features
   - Or: Add handlers for both "balance" and "annual balance"

2. **Add all missing step handlers**
   - Scan feature file for all unique "Given/When/Then" patterns
   - Ensure test_writer has a handler for each pattern
   - Handler should call actual HTTP endpoints, not just log

3. **Re-run pipeline and measure**
   - Run: `python run_pipeline.py --services auth`
   - Check: Test pass rate should improve to 75%+
   - Measure: Coverage should jump to 25-30%

4. **Add new features**
   - Create approve/reject/cancel scenarios
   - Target: 40-50 total scenarios
   - Expected coverage: 50-60%

## Why HuggingFace Credits Ran Out

The gherkin_generator uses an LLM (Qwen2.5-Coder-32B) to generate Gherkin features. Each API call costs HuggingFace credits. With multiple runs of the pipeline, credits were depleted.

**Workaround**: Use cached/existing feature files instead of regenerating
