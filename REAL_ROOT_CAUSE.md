# REAL ROOT CAUSE OF LOW COVERAGE

## The Problem

**Feature file says:**
```gherkin
Given the employee has sufficient leave balance
When the employee submits an annual leave request
```

**LeaveSteps.java generates:**
```java
@Given("the employee has sufficient annual leave balance")
@When("the employee submits an annual leave request")
```

**Result**: Cucumber can't find a matching step for "the employee has sufficient leave balance" → Undefined step → Test fails

## Why This Happens

The `gherkin_generator` is creating feature files with INCONSISTENT step text. There are TWO different feature files:

1. **output/features/auth_01_leave-request-lifecycle_....feature** 
   - Has: `Given the employee has sufficient leave balance` (NO "annual")

2. **What test_writer processes internally**
   - Has: Somehow getting "the employee has sufficient **annual** leave balance"

The test_writer is NOT generating from the same feature file that gherkin_generator saved to disk!

## Evidence

When test_writer runs, it calls:
```python
svc_gherkin, svc_files = self._gherkin_for_service(svc, state)
```

This reads `state.gherkin_files` and `state.gherkin_content` from the gherkin_generator output. 

The gherkin_generator might be:
- Generating ONE version of the Gherkin for saving to disk
- And a DIFFERENT version for passing to test_writer in `state.gherkin_content`

OR

- The test_writer is running BEFORE the feature files are saved
- And reading OLD feature files that had "annual"

## Quick Verification

Check the `state.gherkin_content` variable that's passed from gherkin_generator to test_writer. It probably contains "annual" in the steps, while the saved feature files don't.

## How to Fix

1. **Option A**: Make gherkin_generator save the EXACT same feature file text that it passes to test_writer
2. **Option B**: Make test_writer add handlers for BOTH variations ("sufficient balance" AND "sufficient annual balance")
3. **Option C**: Make test_writer skip generating duplicate annotations for steps that differ only in optional words like "annual"

## Immediate Action

Add a fallback handler in test_writer that matches variations:
- "the employee has sufficient leave balance" → Generate `@Given("the employee has sufficient leave balance")`
- "the employee has sufficient annual leave balance" → Generate `@Given("the employee has sufficient annual leave balance")`

But currently test_writer only recognizes ONE version based on what the gherkin_generator gives it internally, and the saved feature file has a different version!
