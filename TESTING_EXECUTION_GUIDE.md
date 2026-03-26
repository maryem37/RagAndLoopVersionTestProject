# Testing Your Microservice App - Step by Step

## QUICK ANSWER: Where to Put Parameters

```
Your microservice app parameters go in 3 places:

1. services_matrix.yaml    ← Service config (ports, packages, etc.)
2. .env file               ← Secrets & credentials (JWT, API keys)
3. CLI flags               ← Runtime options (--services, --order, etc.)
```

---

## STEP 1: Configure Your Services

### Edit `config/services_matrix.yaml`

```yaml
services:
  auth:                          # ← Your 1st service name
    enabled: true
    port: 9000                   # ← What port it runs on
    db_type: mysql               # ← Database type
    java_package: "com.enis.conge.services.auth"  # ← Java package
    test_runner_class: "com.example.auth.AuthTestRunner"  # ← Test runner
    pom_location: "output/tests/pom.xml"  # ← Where is pom.xml?
    dependencies: []             # ← Depends on nothing
    
  leave:                         # ← Your 2nd service name
    enabled: true
    port: 9001
    db_type: mysql
    java_package: "tn.enis.conge"
    test_runner_class: "com.example.leave.LeaveTestRunner"
    pom_location: "output/tests/pom.xml"
    dependencies: ["auth"]       # ← Depends on auth service

  payment:                       # ← Optional 3rd service
    enabled: false               # ← Disable if not ready
    port: 9002
    db_type: postgres
    java_package: "com.example.payment"
    test_runner_class: "com.example.payment.PaymentTestRunner"
    pom_location: "output/tests/pom.xml"
    dependencies: ["auth", "leave"]

test_credentials:                # ← Authentication config
  jwt_token: "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImlhdCI6MTcxMTA1NjAwMCwiZXhwIjoxNzQyNjc2MDAwfQ.fake_signature"
  test_users:
    admin:
      email: "admin@test.com"
      password: "admin123"
    employee:
      email: "employee@test.com"
      password: "employee123"
```

---

## STEP 2: Configure Secrets

### Create/Edit `.env` file

```bash
# API Keys & Secrets
HUGGINGFACE_API_TOKEN=your_huggingface_token_here
OPENAI_API_KEY=your_openai_key_here

# Test Credentials
TEST_JWT_TOKEN=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImlhdCI6MTcxMTA1NjAwMCwiZXhwIjoxNzQyNjc2MDAwfQ.fake_signature
TEST_USER_EMAIL=admin@test.com
TEST_USER_PASSWORD=admin123

# LLM Settings
DEFAULT_LLM_MODEL=mistral7b
COVERAGE_THRESHOLD=70

# Swagger/API Specs
AUTH_SWAGGER_SPEC=examples/sample_swagger1.json
LEAVE_SWAGGER_SPEC=examples/sample_swagger2.json
```

---

## STEP 3: Run Your Tests

### Option A: Test ALL Services (In Order)

```bash
# Windows PowerShell
python run_pipeline.py

# or explicitly
python run_pipeline.py --services auth,leave
```

**What happens:**
1. Loads services_matrix.yaml
2. Checks dependencies (auth first, then leave)
3. Generates tests from Swagger specs
4. Writes test code for both services
5. Executes Maven tests for both
6. Collects JaCoCo coverage
7. Analyzes coverage reports

---

### Option B: Test SPECIFIC Service Only

```bash
# Test only auth service
python run_pipeline.py --services auth

# Test only leave service  
python run_pipeline.py --services leave

# Test auth, then leave (respects dependencies)
python run_pipeline.py --services auth,leave
```

---

### Option C: See Service Execution Order

```bash
# Check what order services will run in
python run_pipeline.py --order

# Output should show:
# Service Execution Order:
# 1. auth (no dependencies)
# 2. leave (depends on auth)
```

---

### Option D: List Available Services

```bash
# See all configured services
python run_pipeline.py --list

# Output:
# Available Services:
# ✓ auth (enabled, port 9000)
# ✓ leave (enabled, port 9001)
# ✗ payment (disabled, port 9002)
```

---

## STEP 4: Monitor Test Execution

### Console Output During Testing

```
[2026-03-23 10:15:23] Loading ServiceRegistry...
[2026-03-23 10:15:24] Found 2 services: auth, leave
[2026-03-23 10:15:25] Dependency order: auth → leave
[2026-03-23 10:15:26] Loading Swagger specs...
[2026-03-23 10:15:27] Generating Gherkin features...
[2026-03-23 10:15:30] Writing test code...
[2026-03-23 10:15:35] Executing Maven tests for auth...
[2026-03-23 10:15:45] ✓ Auth tests passed (28 tests)
[2026-03-23 10:15:46] Executing Maven tests for leave...
[2026-03-23 10:16:05] ✓ Leave tests passed (35 tests)
[2026-03-23 10:16:06] Collecting JaCoCo coverage...
[2026-03-23 10:16:08] Analyzing coverage...
[2026-03-23 10:16:10] Coverage report saved to output/reports/
```

---

## STEP 5: Check Test Results

### Where to Find Results

```
output/
├── features/
│   └── *.feature          ← Generated Gherkin scenarios
├── tests/
│   └── target/
│       ├── surefire-reports/     ← Test results (JUnit XML)
│       └── jacoco.exec           ← Coverage data
└── reports/
    ├── jacoco.xml         ← Coverage XML
    └── coverage_report_*.json    ← Coverage JSON
```

### View HTML Coverage Report

```bash
# Windows
start output/jacoco/report/html/index.html

# Or open file directly in browser
# C:\Bureau\Bureau\project_test\output\jacoco\report\html\index.html
```

---

## STEP 6: Interpret Results

### Success Indicators ✓

```
✓ All tests passed
✓ Coverage >= 70% (or your threshold)
✓ No broken dependencies
✓ All services tested in order
```

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| **Port already in use** | Service still running | Stop service on port 9000/9001 |
| **Maven not found** | PATH issue | Activate venv: `Activate.ps1` |
| **Swagger spec not found** | Wrong path in matrix | Fix `pom_location` in services_matrix.yaml |
| **JWT expired** | Old token in .env | Update TEST_JWT_TOKEN |
| **Test failed** | Logic error in service | Check test output in surefire-reports |

---

## COMPLETE EXAMPLE: Test from Start to Finish

### 1. Prepare Configuration

```yaml
# services_matrix.yaml - EXACT config for YOUR services
services:
  auth:
    enabled: true
    port: 9000
    db_type: mysql
    java_package: "com.enis.conge.services.auth"
    test_runner_class: "com.example.auth.AuthTestRunner"
    pom_location: "output/tests/pom.xml"
    dependencies: []
    
  leave:
    enabled: true
    port: 9001
    db_type: mysql
    java_package: "tn.enis.conge"
    test_runner_class: "com.example.leave.LeaveTestRunner"
    pom_location: "output/tests/pom.xml"
    dependencies: ["auth"]

test_credentials:
  jwt_token: "eyJhbGciOiJIUzI1NiJ9..."
  test_users:
    admin:
      email: "admin@test.com"
      password: "admin123"
```

### 2. Prepare .env

```bash
HUGGINGFACE_API_TOKEN=hf_xxxxxxxxxxxx
TEST_JWT_TOKEN=eyJhbGciOiJIUzI1NiJ9...
TEST_USER_EMAIL=admin@test.com
TEST_USER_PASSWORD=admin123
```

### 3. Run Tests

```bash
# In PowerShell (with venv activated)
python run_pipeline.py --services auth,leave
```

### 4. Wait for Completion

```
Testing auth service...
[✓] Tests passed: 28/28
[✓] Coverage: 78%

Testing leave service...
[✓] Tests passed: 35/35
[✓] Coverage: 82%

Overall: 63 tests passed, 80% coverage
```

### 5. Review Results

```bash
# Open HTML report
start output/jacoco/report/html/index.html
```

---

## Parameter Reference: What Goes Where?

### `services_matrix.yaml` (Microservice Configuration)

```yaml
services:
  SERVICE_NAME:                    # Your microservice name
    enabled: true/false            # Enable/disable service
    port: 9000                     # Service port
    db_type: mysql/postgres        # Database type
    java_package: "com.example"    # Java package name
    test_runner_class: "TestClass" # JUnit test runner
    pom_location: "path/pom.xml"   # Maven POM file location
    dependencies: []               # Services it depends on
```

### `.env` (Secrets & Credentials)

```bash
# API Tokens
HUGGINGFACE_API_TOKEN=...
OPENAI_API_KEY=...

# Test Credentials  
TEST_JWT_TOKEN=...
TEST_USER_EMAIL=...
TEST_USER_PASSWORD=...

# Service URLs (Optional - auto-generated from services_matrix.yaml)
AUTH_BASE_URL=http://localhost:9000
LEAVE_BASE_URL=http://localhost:9001
```

### CLI Flags (Runtime Options)

```bash
python run_pipeline.py [OPTIONS]

--services SERVICE1,SERVICE2    # Which services to test (default: all enabled)
--list                          # Show available services
--order                         # Show execution order
--skip-generation               # Skip Gherkin generation
--skip-execution                # Skip Maven execution (just generate)
--coverage-threshold 75         # Minimum coverage % (default: 70)
```

---

## FAQ: Common Questions

**Q: My service runs on port 9000, where do I put it?**  
A: In `services_matrix.yaml` under your service's `port: 9000`

**Q: Where does my JWT token go?**  
A: Both places - `.env` (for quick loading) AND `services_matrix.yaml` (for persistence)

**Q: How many services can I test?**  
A: As many as you want! Just add them to `services_matrix.yaml`

**Q: Can I test services in parallel?**  
A: ServiceRegistry supports it - just set `can_run_parallel: true` for independent services

**Q: What if I don't have Swagger specs?**  
A: Manually write `.feature` files in `output/features/`

**Q: How do I skip a service?**  
A: Set `enabled: false` in `services_matrix.yaml`

**Q: Can I use different databases per service?**  
A: Yes! Set `db_type: mysql` or `db_type: postgres` per service

---

## Testing Checklist

- [ ] `services_matrix.yaml` configured with your services
- [ ] `.env` file has JWT token and credentials
- [ ] Microservices are running (or tests will start them)
- [ ] Swagger specs point to right files
- [ ] Java package names match your code
- [ ] Test runner classes exist in your Maven project
- [ ] Run `python run_pipeline.py --list` to verify config
- [ ] Run `python run_pipeline.py --services auth,leave` to test
- [ ] Check `output/reports/` for results
- [ ] Open HTML coverage report in browser

---

## Quick Command Reference

```bash
# Show all available services
python run_pipeline.py --list

# Show execution order (dependencies)
python run_pipeline.py --order

# Test specific services
python run_pipeline.py --services auth,leave

# Test one service only
python run_pipeline.py --services auth

# Test all enabled services
python run_pipeline.py

# Test without generating new features
python run_pipeline.py --skip-generation

# Test without running Maven (just generate code)
python run_pipeline.py --skip-execution
```

---

## YOU ARE HERE 👇

```
Step 1: Configure services_matrix.yaml     ← DO THIS FIRST
        (Put your service names & ports)

Step 2: Configure .env                     ← DO THIS SECOND
        (Put JWT token & credentials)

Step 3: Run pipeline                       ← DO THIS THIRD
        python run_pipeline.py

Step 4: Check results                      ← DONE!
        (View coverage reports)
```

**Start with Step 1 now!** ⬇️
