# 🚀 How to Run Your Workflow

## Prerequisites
✅ Both microservices now compile successfully:
- conge (Port 9000) - Auth & User Management
- DemandeConge (Port 9001) - Leave Requests

## Quick Start

### 1️⃣ **Option A: Run All Services (E2E Consolidated Test)**
```powershell
cd C:\Bureau\Bureau\project_test
python run_pipeline_windows.py
```

### 2️⃣ **Option B: Run Specific Service**
```powershell
# Test only the auth/conge service
python run_pipeline_windows.py --services auth

# Test only the leave request service
python run_pipeline_windows.py --services leave

# Test multiple services
python run_pipeline_windows.py --services auth,leave
```

### 3️⃣ **Option C: List Available Services**
```powershell
python run_pipeline_windows.py --list
```

### 4️⃣ **Option D: Show Execution Order**
```powershell
python run_pipeline_windows.py --order
```

## What the Pipeline Does

The workflow automates the complete test lifecycle:

1. **User Story → Gherkin** (gherkin_generator.py)
   - Reads your Swagger specs and user story
   - Generates .feature files

2. **Validate Gherkin** (gherkin_validator.py)
   - Checks syntax and completeness

3. **Generate Tests** (test_writer.py)
   - Creates executable Java tests from Gherkin

4. **Execute Tests** (test_executor.py)
   - Runs Maven tests
   - Captures results

5. **Measure Coverage** (coverage_analyst.py)
   - JaCoCo coverage analysis

6. **Self-Healing** (self_healing.py)
   - Auto-fixes failing tests

## Configuration

Edit `config/services_matrix.yaml` to:
- Enable/disable services
- Set ports (9000 for conge, 9001 for DemandeConge)
- Configure Swagger specs

## Output

Results are saved to `output/`:
- `features/` - Generated .feature files
- `tests/` - Generated Java test files
- `reports/` - Test execution reports
- `jacoco/` - Coverage reports

## Troubleshooting

If the pipeline fails:
1. Check both microservices are running:
   ```powershell
   # Start conge
   cd C:\Bureau\Bureau\microservices\conge
   mvn spring-boot:run
   
   # In another terminal, start DemandeConge
   cd C:\Bureau\Bureau\microservices\DemandeConge
   mvn spring-boot:run
   ```

2. Verify database is running (MySQL on localhost:3306)

3. Check `config/services_matrix.yaml` for correct configuration

## Success Indicators

✅ Pipeline completes without errors
✅ Generated Gherkin files in `output/features/`
✅ Generated Java tests in `output/tests/`
✅ Test execution reports in `output/reports/`
✅ Coverage report in `output/jacoco/`
