# Coverage Low 17.92% - Executive Summary

## The Problem in 3 Sentences

1. **Only 13 out of 28 tests are passing** (46% pass rate)
2. **JaCoCo coverage only measures code executed during PASSING tests**
3. **With 15 failing tests, only 43 out of 240 lines execute** → 17.92% coverage

## Why Tests Are Failing

The **Gherkin feature files** and **Java test code** don't match:

| Feature File Says | Generated Java Has | Result |
|---|---|---|
| `Given the employee has sufficient leave balance` | `@Given("the employee has sufficient **annual** leave balance")` | ❌ Step not found |
| `When the employee submits a leave request with past dates` | NO HANDLER | ❌ No implementation |

**Result**: Cucumber says "undefined step" → Test fails before any code runs

## Coverage Calculation

```
Total lines of service code:          240
Lines executed (13 passing tests):     43
Uncovered lines (15 failing tests):   197

Coverage = 43 / 240 = 17.92%
```

## How to Improve Coverage

### Step 1: Fix Undefined Steps (Required to get from 46% to 75%+ test pass rate)
- Make Gherkin step text match Java annotations exactly
- Add missing step handlers to test_writer.py

### Step 2: Add More Test Scenarios (Required to get from 25% to 60% code coverage)
- Current 28 test scenarios only test "create" endpoint
- Add scenarios for: approve, reject, cancel, balance checks, date validation
- Need ~50 total scenarios to reach 60% coverage target

## What's Blocking Progress

**HuggingFace API Credits**: The Gherkin generator uses an LLM API that ran out of credits. Can't generate new features until credits are restored or API switched to local/free alternative.

**Current mitigation**: Use previously generated feature files (already on disk from last successful run)
