# 🎯 How to Run Complete Pipeline for Backend Testing

## TL;DR - Just Run This

```powershell
cd C:\Bureau\Bureau\project_test
powershell -ExecutionPolicy Bypass -File .\run_complete_pipeline.ps1
```

**Done!** Your backend will be tested with all agents in ~20-30 minutes.

---

## What You Get

✅ **41+ Test Methods** across 7 test classes  
✅ **Python Agents** generate and validate tests  
✅ **Gherkin Features** from your user stories  
✅ **JaCoCo Coverage** reports  
✅ **Complete Results** summary  

---

## 4 Ways to Run

### **1. Full Pipeline (Recommended)**
```powershell
.\run_complete_pipeline.ps1
# Runs: Setup → Python Agents → Maven Tests → Results
```

### **2. Python Agents Only**
```powershell
.\run_complete_pipeline.ps1 -Phase python
```

### **3. Maven Tests Only**
```powershell
.\run_complete_pipeline.ps1 -Phase maven
```

### **4. Test Specific Service**
```powershell
.\run_complete_pipeline.ps1 -Service auth
.\run_complete_pipeline.ps1 -Service leave
```

---

## What Each Phase Does

### Phase 1: Setup (1 min)
Prepares environment:
- Activates Python venv
- Installs dependencies

### Phase 2: Python Agents (5-10 min)
Agents do the work:
- **GherkinGenerator** → Creates test feature files
- **GherkinValidator** → Validates syntax
- **TestWriter** → Generates test code
- **TestExecutor** → Runs generated tests
- **CoverageAnalyst** → Analyzes coverage

### Phase 3: Maven Tests (5-15 min)
Java tests run:
- **Unit Tests** (21 methods) - Business logic
- **Integration Tests** (10 methods) - HTTP endpoints
- **E2E Tests** (4 methods) - Complete workflows
- **Contract Tests** (6 methods) - API compliance
- **JaCoCo Coverage** - Code coverage metrics

### Phase 4: Results (1 min)
Shows summary:
- File counts
- Output locations
- Next steps

---

## Output Locations

| Output | Path |
|--------|------|
| **Gherkin Features** | `output/features/` |
| **Test Reports** | `output/reports/` |
| **Coverage Data** | `output/jacoco/` |
| **Maven Tests** | `output/tests/target/` |
| **Coverage Report** | `output/tests/target/site/jacoco/index.html` |

---

## View Results After Running

### 1. Coverage Report
```powershell
start output/tests/target/site/jacoco/index.html
```

### 2. Feature Files
```powershell
Get-ChildItem output/features -Filter *.feature | Select Name
```

### 3. Test Reports
```powershell
Get-ChildItem output/reports -Filter *.yaml | Select Name
```

### 4. Maven Test Results
```powershell
Get-ChildItem output/tests/target/surefire-reports -Filter *.txt
```

---

## Manual Commands (if needed)

### **Run Python Pipeline Directly**
```powershell
cd C:\Bureau\Bureau\project_test
python run_pipeline.py
python run_pipeline.py --services auth
python run_pipeline.py --list
```

### **Run Maven Tests Directly**
```powershell
cd C:\Bureau\Bureau\project_test\output\tests
mvn clean test jacoco:report
mvn test -Dtest=*Auth*
mvn test -Dtest=*Leave*
```

### **With Custom Service URLs**
```powershell
mvn clean test `
  -DAUTH_BASE_URL="http://127.0.0.1:9000" `
  -DLEAVE_BASE_URL="http://127.0.0.1:9001"
```

---

## Troubleshooting

### Issue: Script won't run
**Solution:** Allow script execution
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Python modules not found
**Solution:** Install dependencies
```powershell
pip install -r requirements.txt
```

### Issue: Maven tests fail
**Solution:** Check if services are needed and running
- Auth service: `http://localhost:9000`
- Leave service: `http://localhost:8080`

Or provide custom URLs:
```powershell
mvn test -DAUTH_BASE_URL="http://127.0.0.1:9000"
```

### Issue: Coverage report won't open
**Solution:** Navigate manually
```powershell
cd output/tests/target/site/jacoco
start index.html
```

---

## Time Estimates

| Component | Time |
|-----------|------|
| Setup | 1-2 min |
| Python Pipeline | 5-10 min |
| Maven Tests | 5-15 min |
| Report Generation | 2 min |
| **Total** | **15-30 min** |

---

## File Locations

### Scripts
- **Main Script**: `run_complete_pipeline.ps1` ← Use this!
- **Full Docs**: `RUN_COMPLETE_PIPELINE.md`
- **Quick Ref**: `QUICK_START_PIPELINE.md`

### Python Project
- **Run Pipeline**: `run_pipeline.py`
- **Agents**: `agents/`
- **Config**: `config/`
- **Tools**: `tools/`

### Test Suite
- **Tests**: `output/tests/src/test/java/`
- **pom.xml**: `output/tests/pom.xml`
- **Docs**: `output/tests/TEST_SUITE_README.md`

---

## Next Steps After Running

1. **Review Coverage**
   ```powershell
   start output/tests/target/site/jacoco/index.html
   ```

2. **Check Generated Features**
   ```powershell
   Get-ChildItem output/features -Filter *.feature
   ```

3. **View Test Summary**
   ```powershell
   Get-ChildItem output/reports
   ```

4. **Check Test Results**
   ```powershell
   Get-ChildItem output/tests/target/surefire-reports
   ```

---

## Success Indicators ✅

After the pipeline completes, you should see:
- ✅ Features generated: `output/features/*.feature`
- ✅ Reports created: `output/reports/*.yaml`
- ✅ Tests compiled: `output/tests/target/test-classes/`
- ✅ Coverage report: `output/tests/target/site/jacoco/index.html`
- ✅ Test results: `output/tests/target/surefire-reports/`

---

## Quick Command Reference

```powershell
# Run everything
.\run_complete_pipeline.ps1

# Specific phase
.\run_complete_pipeline.ps1 -Phase python
.\run_complete_pipeline.ps1 -Phase maven

# Specific service
.\run_complete_pipeline.ps1 -Service auth
.\run_complete_pipeline.ps1 -Service leave

# View results
start output/tests/target/site/jacoco/index.html
Get-ChildItem output/features -Filter *.feature
Get-ChildItem output/reports
```

---

## Summary

| What | How Long | Command |
|------|----------|---------|
| Full Pipeline | 20-30 min | `.\run_complete_pipeline.ps1` |
| Python Only | 5-10 min | `.\run_complete_pipeline.ps1 -Phase python` |
| Tests Only | 5-15 min | `.\run_complete_pipeline.ps1 -Phase maven` |
| Specific Service | 10-20 min | `.\run_complete_pipeline.ps1 -Service auth` |

---

**Ready to test your backend?**

```powershell
.\run_complete_pipeline.ps1
```

See full documentation: [RUN_COMPLETE_PIPELINE.md](./RUN_COMPLETE_PIPELINE.md)
