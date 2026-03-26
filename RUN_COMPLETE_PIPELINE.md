# 🚀 Complete Pipeline Execution Guide

## Quick Start - Run Everything

### **Option 1: Run Full Pipeline (Recommended)**
```powershell
# Navigate to project directory
cd C:\Bureau\Bureau\project_test

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run complete pipeline
python run_pipeline.py
```

### **Option 2: Run Specific Services**
```powershell
# Run only auth service
python run_pipeline.py --services auth

# Run multiple services
python run_pipeline.py --services auth,leave

# List available services
python run_pipeline.py --list

# Show execution order
python run_pipeline.py --order
```

---

## 📋 Full Pipeline Steps

### **Step 1: Setup Environment**
```powershell
# Navigate to project
cd C:\Bureau\Bureau\project_test

# Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# Install/upgrade dependencies
pip install -r requirements.txt -q
```

### **Step 2: Run Python Pipeline**
```powershell
# This runs all agents:
python run_pipeline.py

# Or with specific service:
python run_pipeline.py --services leave
```

**What this does:**
- ✅ Reads user stories
- ✅ Generates Gherkin feature files
- ✅ Validates Gherkin syntax
- ✅ Generates test cases
- ✅ Executes tests
- ✅ Generates coverage reports

### **Step 3: Run Maven Tests (Integration Tests)**
```powershell
# Navigate to tests directory
cd output/tests

# Run all tests with coverage
mvn clean test jacoco:report

# Or run specific tests
mvn test -Dtest=*Integration*Test
```

### **Step 4: View Results**
```powershell
# Python agents output
# Check: output/features/
# Check: output/reports/

# Java tests output
# Check: output/tests/target/site/jacoco/index.html
```

---

## 🔧 Complete End-to-End Execution

### **All-in-One Script** (Recommended)
Create a file named `run_all_tests.ps1`:

```powershell
# run_all_tests.ps1

Write-Host "🚀 Starting Complete Test Pipeline" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green

# Navigate to project root
cd C:\Bureau\Bureau\project_test

# Step 1: Activate environment
Write-Host "`n📦 Activating Python environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

# Step 2: Run Python pipeline
Write-Host "`n🤖 Running Python agents..." -ForegroundColor Yellow
python run_pipeline.py

# Step 3: Run Maven tests
Write-Host "`n✅ Running Maven tests..." -ForegroundColor Yellow
cd output/tests
mvn clean test jacoco:report

# Step 4: Display results
Write-Host "`n📊 Pipeline Complete!" -ForegroundColor Green
Write-Host "`nResults locations:" -ForegroundColor Cyan
Write-Host "  - Python outputs: output/reports/" -ForegroundColor Gray
Write-Host "  - Java coverage: output/tests/target/site/jacoco/index.html" -ForegroundColor Gray
Write-Host "  - Features: output/features/" -ForegroundColor Gray
```

**Run it:**
```powershell
.\run_all_tests.ps1
```

---

## 📊 What Each Component Does

### **Python Agents (Workflow)**

| Agent | Purpose |
|-------|---------|
| **GherkinGenerator** | Converts user stories to Gherkin feature files |
| **GherkinValidator** | Validates Gherkin syntax |
| **TestWriter** | Generates test code from features |
| **TestExecutor** | Runs the tests |
| **CoverageAnalyst** | Analyzes test coverage |
| **SelfHealing** | Auto-fixes failing tests |

### **Java/Maven Tests**

| Test Type | Purpose |
|-----------|---------|
| **Unit Tests** | Test service logic |
| **Integration Tests** | Test API endpoints |
| **E2E Tests** | Test complete workflows |
| **Contract Tests** | Validate API contracts |

---

## 🔍 Detailed Step-by-Step

### **Phase 1: Setup (2 min)**
```powershell
cd C:\Bureau\Bureau\project_test
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -q
```

### **Phase 2: Generate Test Artifacts (5 min)**
```powershell
python run_pipeline.py
```
Output files:
- `output/features/*.feature` - Gherkin files
- `output/reports/*.json` - Coverage reports
- `output/reports/*.yaml` - Test results

### **Phase 3: Run Java Tests (10 min)**
```powershell
cd output/tests
mvn clean test jacoco:report
```
Output files:
- `target/test-classes/` - Compiled tests
- `target/surefire-reports/` - Test results
- `target/site/jacoco/` - Coverage reports

### **Phase 4: Review Results (5 min)**
```powershell
# View coverage
start output/tests/target/site/jacoco/index.html

# Check feature files
Get-ChildItem output/features -Filter *.feature

# Check reports
Get-ChildItem output/reports -Filter *.yaml | Select-Object -First 5
```

---

## 🎯 Run Specific Scenarios

### **Test Only Auth Service**
```powershell
cd C:\Bureau\Bureau\project_test
.\.venv\Scripts\Activate.ps1
python run_pipeline.py --services auth
cd output/tests
mvn test -Dtest=*Auth*
```

### **Test Only Leave Service**
```powershell
cd C:\Bureau\Bureau\project_test
.\.venv\Scripts\Activate.ps1
python run_pipeline.py --services leave
cd output/tests
mvn test -Dtest=*Leave*
```

### **Generate Features Only (No Execution)**
```powershell
cd C:\Bureau\Bureau\project_test
.\.venv\Scripts\Activate.ps1
python -c "from agents.gherkin_generator import GherkinGeneratorAgent; GherkinGeneratorAgent().generate()"
```

### **Test with Custom Backend URL**
```powershell
cd C:\Bureau\Bureau\project_test\output\tests
mvn clean test `
  -DAUTH_BASE_URL="http://127.0.0.1:9000" `
  -DLEAVE_BASE_URL="http://127.0.0.1:9001"
```

---

## 📁 Output Locations

| Output | Location | Purpose |
|--------|----------|---------|
| **Feature Files** | `output/features/` | Gherkin test scenarios |
| **Test Results** | `output/reports/` | JSON/YAML test reports |
| **Coverage Data** | `output/jacoco/` | Code coverage metrics |
| **Maven Tests** | `output/tests/target/` | Java test outputs |
| **Test Classes** | `output/tests/src/test/java/` | Test source code |

---

## ✅ Verification Checklist

After running the pipeline, verify:

```powershell
# ✅ Check Python agents ran
Get-ChildItem output/features -Filter *.feature -ErrorAction SilentlyContinue

# ✅ Check reports generated
Get-ChildItem output/reports -Filter *.yaml -ErrorAction SilentlyContinue

# ✅ Check Maven tests ran
Get-ChildItem output/tests/target/surefire-reports/ -Filter *.txt

# ✅ Check coverage report exists
Test-Path output/tests/target/site/jacoco/index.html

# ✅ Check test classes compiled
Get-ChildItem output/tests/target/test-classes -Filter *.class | Measure-Object
```

---

## 🐛 Troubleshooting

### **Issue: Python modules not found**
```powershell
# Solution: Install dependencies
pip install -r requirements.txt
```

### **Issue: Maven tests fail**
```powershell
# Check if services are running
# Or set custom URLs:
mvn test -DAUTH_BASE_URL="http://localhost:9000" -DLEAVE_BASE_URL="http://localhost:9001"
```

### **Issue: Features not generated**
```powershell
# Check if example files exist
Test-Path examples/comprehensive_user_story.md

# Run with debug output
python run_pipeline.py 2>&1
```

### **Issue: Coverage report not opening**
```powershell
# Navigate manually
cd output/tests/target/site/jacoco
start index.html
```

---

## ⏱️ Execution Time Estimates

| Phase | Time |
|-------|------|
| Environment setup | 2 min |
| Python pipeline | 5-10 min |
| Maven tests | 5-15 min |
| Report generation | 2 min |
| **Total** | **15-40 min** |

---

## 🎊 Success Indicators

✅ **All phases completed successfully:**
- Python agents generated Gherkin files
- Tests were created and executed
- Coverage reports were generated
- Maven tests passed
- Reports are viewable

**Next:** Check `output/reports/` and `target/site/jacoco/` for results!

---

## 📚 Related Documentation

- [Python Pipeline Details](../run_pipeline.py)
- [Test Suite Guide](output/tests/TEST_SUITE_README.md)
- [Execution Guide](output/tests/TEST_EXECUTION_GUIDE.md)

---

**Ready to run the full pipeline?** Use the **All-in-One Script** above! 🚀
