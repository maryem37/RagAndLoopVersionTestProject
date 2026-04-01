# 🔍 DEBUG GUIDE - Project Not Working

## Root Cause Identified

**Current Issue**: Test Writer fails because Swagger specs are not passed to the workflow state.

```
Error: ValueError("No Swagger spec found in state.")
Location: agents/test_writer.py line 2262
```

### The Problem Flow

```
run_pipeline.py loads Swagger specs
    ↓
Passes them to workflow.run()
    ↓
But workflow doesn't put them into state
    ↓
test_writer expects specs in state
    ↓
❌ FAILURE: "No Swagger spec found"
```

---

## Root Cause Analysis

### What's Happening:

1. **run_pipeline.py** successfully loads Swagger specs from files:
   - `examples/sample_swagger1.json` (auth service)
   - `examples/sample_swagger2.json` (leave service)

2. **run_pipeline.py** calls: `workflow.run(swagger_spec=all_swagger_specs, swagger_specs=all_swagger_specs, ...)`

3. **But graph/workflow.py** does NOT initialize these values in the state!

### Evidence:

File: `graph/state.py` - Check if `swagger_spec` and `swagger_specs` are initialized in `TestAutomationState`

---

##  Step 1: Check State Initialization

### Read this file:
```
graph/state.py
```

### Look for:
- Does `TestAutomationState` have `swagger_spec` field?
- Does `TestAutomationState` have `swagger_specs` field?

### Expected:
```python
@dataclass
class TestAutomationState:
    swagger_spec: dict = None  # ← SHOULD EXIST
    swagger_specs: dict = None # ← SHOULD EXIST
    # ... other fields
```

---

## Step 2: Check Workflow Initialization

### Read this file:
```
graph/workflow.py
```

### Look for the `run()` method (around line 100-130)

### It should do:
```python
def run(self, user_story, service_name, swagger_spec=None, swagger_specs=None, ...):
    state = TestAutomationState(
        user_story=user_story,
        service_name=service_name,
        swagger_spec=swagger_spec or {},      # ← PASS TO STATE
        swagger_specs=swagger_specs or {},    # ← PASS TO STATE
        # ... other fields
    )
```

---

## Why This Matters

The gherkin_generator and gherkin_validator complete successfully, but then test_writer can't run because:

1. **State is missing Swagger data**
2. Test writer needs Swagger to understand API endpoints
3. Without endpoints, it can't generate proper test steps

---

## Solution

### Option 1: Ensure Swagger flows to state (RECOMMENDED)

**File**: `graph/state.py`
- Make sure `swagger_spec` and `swagger_specs` fields exist in `TestAutomationState`

**File**: `graph/workflow.py` → `run()` method
- Make sure swagger parameters are passed into initial state

### Option 2: Provide default Swagger

If no Swagger files provided, load default ones:

```python
if not swagger_spec or not swagger_specs:
    swagger_spec = load_default_swagger()  # from examples/
```

---

## Quick Fix Commands

### Step 1: Inspect state.py
```powershell
cd C:\Bureau\Bureau\project_test
grep -n "class TestAutomationState" graph/state.py
grep -n "swagger" graph/state.py
```

### Step 2: Inspect workflow.py
```powershell
grep -n "def run" graph/workflow.py
grep -n "TestAutomationState(" graph/workflow.py
```

### Step 3: Run with debug
```powershell
python run_pipeline.py --services auth 2>&1 | Tee-Object -Variable output
# Check for "No Swagger spec found"
```

---

## What You Need to Do Now

1. **Read** `graph/state.py` and check if swagger fields exist
2. **Read** `graph/workflow.py` `run()` method and check if swagger is passed to state
3. **If missing**: Add the fields and pass the parameters
4. **Test**: Run `python run_pipeline.py --services auth` and check if it passes test_writer

---

## Success Indicators

When fixed, you should see:

```
✓ gherkin_generator  [974ms]
✓ gherkin_validator  [1684ms]
✓ test_writer        [3200ms]   ← This should NOT show ✗ anymore
✓ test_executor      [...]
✓ coverage_analyst   [...]
```

---

## Questions to Ask Yourself

- [ ] Does `TestAutomationState` have `swagger_spec` field?
- [ ] Does `TestAutomationState` have `swagger_specs` field?
- [ ] Does `workflow.run()` pass swagger parameters to initial state?
- [ ] Are the Swagger files actually being loaded in `run_pipeline.py`?
- [ ] Is `run_pipeline.py` calling `workflow.run()` with those parameters?

