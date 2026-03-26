# Coverage is Low: Root Cause Analysis

## Current Status
- **Line Coverage: 17.92%** (43 out of 240 lines executed)
- **Tests Running: 28 total**
- **Tests Passing: 13** (46%)
- **Tests Failing: 15** (54%)

## Root Causes of Low Coverage

### Problem 1: Gherkin Steps Don't Match Java Annotations

The feature file is generated with step text like:
```gherkin
Given the employee has sufficient leave balance
When the employee submits a leave request
Then the system displays the message "Added successfully"
```

But the Java test code generates annotations like:
```java
@Given("the employee has sufficient annual leave balance")  // ← "annual" was added!
@When("the employee submits an annual leave request")      // ← "annual" was added!
@Then("the system displays the message \"Added successfully\"")
```

**Result**: Cucumber can't match steps → Tests fail with "undefined step"

### Problem 2: Feature File Text is Generated Incorrectly

The `gherkin_generator.py` is creating feature text that doesn't match what `test_writer.py` expects.

Looking at the feature file:
```gherkin
Scenario: Employee submits a valid annual leave request
  Given the employee has sufficient annual leave balance
  When the employee submits an annual leave request
  Then the leave request status is "Pending"
```

But other scenarios use DIFFERENT text:
```gherkin
Scenario: Employee submits a leave request with invalid leave type
  Given the employee has sufficient leave balance
  When the employee submits a leave request with an invalid leave type
```

**Notice**: "sufficient leave balance" vs "sufficient annual leave balance"
**Notice**: "submits a leave request" vs "submits an annual leave request"

### Problem 3: The test_writer Handlers Don't Generate Correct Annotations

In `test_writer.py`, the `_step_to_annotation()` function is generating step text, but the underlying feature generation is using DIFFERENT step texts.

Example:
- Feature line: `the employee submits a leave request with past dates`
- Generated annotation might become: `the employee submits a leave request with past dates` ✅
- But feature file probably also generates: `the employee has sufficient leave balance` without "annual"
- Generated annotation would be: `the employee has sufficient leave balance` ✅
- **But they still don't match because of inconsistencies in gherkin_generator.py**

## Why Coverage Stays at 17.92%

1. **Undefined steps → Test failures**
   - 15 out of 28 tests are failing with "undefined step" errors
   - These tests NEVER execute service code
   - JaCoCo only measures lines executed during passing tests
   - So coverage stays stuck at whatever the 13 passing tests exercise

2. **Only 13 tests can pass**
   - Even if all 28 tests passed, they're testing the same code paths
   - Need to add NEW feature scenarios to exercise untested code
   - Current features only test "create" endpoint
   - Need to add features for: approve, reject, cancel, balance checks, etc.

## Evidence: Test Failure Logs

```
[ERROR] Leave Request Lifecycle.Employee submits a leave request with invalid leave type
  Run 1: PASS
  Run 2: The step 'the employee has sufficient leave balance' and 1 other step(s) are undefined.
    @Given("the employee has sufficient leave balance")
    public void the_employee_has_sufficient_leave_balance() {
        throw new io.cucumber.java.PendingException();
    }
```

**Interpretation**: 
- Run 1 = First execution (some steps matched, test passed)
- Run 2 = Re-run (now the step is undefined) - THIS IS THE PROBLEM!

The test framework is trying to handle VARIABLE step text, but the Gherkin generator and test writer are out of sync.

## Quick Fix Strategy

1. **Option A (Recommended)**: Align gherkin_generator.py to use CONSISTENT step text
   - All balance checks should be: "the employee has sufficient leave balance" (no "annual")
   - All submits should be: "the employee submits a leave request" (no "annual")
   - This way test_writer handlers will match

2. **Option B**: Expand test_writer handlers to handle ALL variations
   - Add handlers for: "sufficient leave balance", "sufficient annual leave balance", "has balance", etc.
   - Currently only handles "sufficient" + "balance" + "annual" together

3. **Option C**: Fix the matching in test_writer
   - The `_step_to_annotation()` function should generate step annotations that exactly match feature text
   - Currently it's transforming step text in ways that don't match the original feature

## Immediate Action Items

1. **Generate feature file**: Run gherkin_generator to create feature file (already done)
2. **Check feature text**: Verify the exact step text in the feature file
3. **Match annotations**: Ensure test_writer generates `@Given/@When/@Then` annotations that EXACTLY match the feature step text
4. **Run tests**: Tests should now pass, coverage should increase

## Expected Outcome After Fix

- If all 28 tests pass: Coverage will improve to ~25-30% (more code paths executed)
- To reach 60% coverage target: Need to add 10-15 more feature scenarios:
  - Approve leave request
  - Reject leave request
  - Cancel leave request
  - Overlapping date validation
  - Balance deduction verification
  - etc.
