# 🚀 Quick Start - Run Complete Pipeline

## 2-Minute Setup

### **Quick Command - Run Everything**
```powershell
cd C:\Bureau\Bureau\project_test
powershell -ExecutionPolicy Bypass -File .\run_complete_pipeline.ps1
```

That's it! This runs:
1. ✅ Python agents (Gherkin, test generation, validation)
2. ✅ Maven tests (unit, integration, E2E tests)
3. ✅ Coverage reports (JaCoCo)

---

## Alternative: Run Specific Phases

### **Setup Only**
```powershell
.\run_complete_pipeline.ps1 -Phase setup
```

### **Python Agents Only**
```powershell
.\run_complete_pipeline.ps1 -Phase python
```

### **Maven Tests Only**
```powershell
.\run_complete_pipeline.ps1 -Phase maven
```

### **Test Specific Service**
```powershell
.\run_complete_pipeline.ps1 -Service auth
.\run_complete_pipeline.ps1 -Service leave
```

---

## What It Does

### Phase 1: Setup (1 min)
- Activates Python environment
- Installs dependencies

### Phase 2: Python Agents (5 min)
- Generates Gherkin features from user stories
- Validates feature syntax
- Generates test code
- Executes tests
- Analyzes coverage

### Phase 3: Maven Tests (10 min)
- Unit tests (21 methods)
- Integration tests (10 methods)
- E2E tests (4 methods)
- Contract tests (6 methods)
- Generates JaCoCo coverage report

### Phase 4: Results
- Shows summary of all outputs
- Displays output locations

---

## View Results

### Coverage Report
```powershell
start output/tests/target/site/jacoco/index.html
```

### Feature Files
```powershell
Get-ChildItem output/features -Filter *.feature
```

### Test Reports
```powershell
Get-ChildItem output/reports -Filter *.yaml
```

### Maven Test Results
```powershell
Get-ChildItem output/tests/target/surefire-reports -Filter *.txt
```

---

## Total Time
- **Full pipeline**: ~15-30 minutes
- **Python only**: ~5-10 minutes
- **Maven only**: ~5-15 minutes

---

## Need Help?

See full documentation: [RUN_COMPLETE_PIPELINE.md](./RUN_COMPLETE_PIPELINE.md)

---

**Start now:**
```powershell
.\run_complete_pipeline.ps1
```
