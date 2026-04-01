# Windows Quick Start - After Encoding Fix

## TL;DR - Just Run This

```powershell
cd c:\Bureau\Bureau\project_test
python run_pipeline_windows.py
```

That's it! The encoding is handled automatically.

---

## Your Options

### Option A: Python (Easiest)
```powershell
python run_pipeline_windows.py --services auth
```

### Option B: Batch File
```cmd
run_pipeline_windows.bat auth
```

### Option C: PowerShell
```powershell
.\run_pipeline_utf8.ps1 -Services auth
```

### Option D: Manual Encoding (Old Way)
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
python run_pipeline.py --services auth
```

---

## What Was Fixed

✅ Windows console encoding errors - SOLVED
✅ Unicode emoji replaced with ASCII text
✅ Pipeline runs cleanly
✅ No more UnicodeEncodeError crashes

---

## Current Status

**Pipeline Status**: WORKING ✓

```
[OK] gherkin_generator     - Converts user stories to BDD scenarios
[OK] gherkin_validator     - Validates feature files syntax
[OK] test_writer          - Generates Java test classes
[FAIL] test_executor      - Tests running but failing (backend issue)
[OK] coverage_analyst     - Measures code coverage
```

The test_executor failures are NOT encoding issues.
They're backend connectivity/authentication issues.

---

## Next Steps

1. ✅ Encoding fix complete - you can run the pipeline
2. ⏭ Fix backend test failures - see BACKEND_RUNNING_STATUS.md
3. ⏭ Improve test coverage to 60%+ (currently 34.92%)

---

## Support

If you see garbled output again:
1. Use `run_pipeline_windows.bat` directly
2. Or run: `python run_pipeline_windows.py --services auth 2>&1 | Out-File -FilePath output.log -Encoding UTF8`

