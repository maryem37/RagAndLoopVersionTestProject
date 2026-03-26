# JaCoCo Configuration & Services Restart - Setup Complete

## ✅ What Was Accomplished

### 1. **Identified Running Services**
Located two microservices running WITHOUT JaCoCo agent monitoring:
- **Leave Service (conge)**: Port 9000, Main class: `tn.enis.conge.CongeeApplication`
  - Location: `C:\Bureau\Bureau\microservices\conge\target\classes`
- **Auth Service (DemandeConge)**: Port 9001, Main class: `tn.enis.DemandeConge.DemandeCongeApplication`
  - Location: `C:\Bureau\Bureau\microservices\DemandeConge\target\classes`

**Problem Identified**: Services were running with IntelliJ IDEA's debug agent only (`idea_rt.jar`), NOT with JaCoCo agent. This prevented coverage data collection.

### 2. **Located JaCoCo Agent**
Found JaCoCo agent in Maven repository:
```
C:\Users\MSI\.m2\repository\org\jacoco\org.jacoco.agent\0.8.11\org.jacoco.agent-0.8.11-runtime.jar
```

### 3. **Created Restart Script**
Generated PowerShell script: `restart-services-jacoco.ps1`
- Stops existing Java processes
- Restarts both services with JaCoCo agent parameters:
  ```
  -javaagent:...org.jacoco.agent-0.8.11-runtime.jar=destfile=<output_dir>\<service>.exec,append=false
  ```
- Services automatically instrument code during startup
- Coverage data will be written to `.exec` files

### 4. **Successfully Restarted Services**
Both services now running WITH JaCoCo monitoring:
- **Leave Service**: PID 25976, Port 9000
  - JaCoCo output: `C:\Bureau\Bureau\project_test\output\jacoco\conge.exec`
- **Auth Service**: PID 14964, Port 9001
  - JaCoCo output: `C:\Bureau\Bureau\project_test\output\jacoco\auth.exec`

## 📋 How JaCoCo Agent Works

The JaCoCo agent configuration added to the service startup:
```
-javaagent:path\to\org.jacoco.agent-0.8.11-runtime.jar=destfile=output\path\<service>.exec,append=false
```

**Key parameters:**
- `destfile`: Where to save coverage data (the `.exec` file)
- `append=false`: Create new file instead of appending (ensures fresh coverage data)

**What this does:**
- Instruments all Java bytecode at runtime as classes are loaded
- Tracks line coverage, branch coverage, method coverage
- Writes coverage data to `.exec` file when service shuts down or crashes
- Zero-impact on service functionality (transparent monitoring)

## 🚀 Next Steps to Collect Coverage

1. **Run the test pipeline** to exercise the services:
   ```bash
   python run_pipeline.py --services auth
   ```
   
2. **Expected result**:
   - Tests will hit the APIs on ports 9000 and 9001
   - JaCoCo will record which lines, branches, and methods were exercised
   - Coverage data gets saved to:
     - `C:\Bureau\Bureau\project_test\output\jacoco\conge.exec`
     - `C:\Bureau\Bureau\project_test\output\jacoco\auth.exec`

3. **Generate coverage reports**:
   ```bash
   python test_coverage_analyst.py
   ```
   - This will read the `.exec` files
   - Generate HTML reports in `C:\Bureau\Bureau\project_test\output\jacoco\report\`
   - Coverage metrics will increase from current 17.92%

## 📊 Current Status

| Metric | Before | After |
|--------|--------|-------|
| **JaCoCo Agent** | ❌ Not running | ✅ Active (runtime instrumentation) |
| **Leave Service** | Running (no monitoring) | ✅ Running with monitoring (PID 25976) |
| **Auth Service** | Running (no monitoring) | ✅ Running with monitoring (PID 14964) |
| **Coverage Data** | Stale (2 days old) | ⏳ Ready to collect fresh data |

## 🔧 Scripts Created

1. **restart-services-jacoco.ps1** - Main PowerShell script
   - Stops existing services
   - Builds complete classpath for each service
   - Starts services with JaCoCo agent parameters
   - Verifies startup was successful

2. **restart_services_with_jacoco.py** - Python alternative (not fully executed due to Maven not in PATH)

## ⚙️ Configuration Details

### Leave Service (Conge) - Port 9000
**JaCoCo Config:**
```
-javaagent:C:\Users\MSI\.m2\repository\org\jacoco\org.jacoco.agent\0.8.11\org.jacoco.agent-0.8.11-runtime.jar=destfile=C:\Bureau\Bureau\project_test\output\jacoco\conge.exec,append=false
-Dserver.port=9000
```

### Auth Service (DemandeConge) - Port 9001  
**JaCoCo Config:**
```
-javaagent:C:\Users\MSI\.m2\repository\org\jacoco\org.jacoco.agent\0.8.11\org.jacoco.agent-0.8.11-runtime.jar=destfile=C:\Bureau\Bureau\project_test\output\jacoco\auth.exec,append=false
-Dserver.port=9001
```

## 📝 IntelliJ Integration Note

These services were launched from IntelliJ IDEA. To make this restart automatic:

**Option 1: Update IntelliJ Run Configurations**
1. Open IntelliJ project for each microservice
2. Edit Run Configuration (Run → Edit Configurations)
3. Add VM options:
   ```
   -javaagent:C:\Users\MSI\.m2\repository\org\jacoco\org.jacoco.agent\0.8.11\org.jacoco.agent-0.8.11-runtime.jar=destfile=C:\Bureau\Bureau\project_test\output\jacoco\<service>.exec,append=false
   ```
4. Save configuration
5. Next time you run from IntelliJ, JaCoCo will be active automatically

**Option 2: Use PowerShell Script** (Current approach)
- Execute `restart-services-jacoco.ps1` whenever you need fresh coverage monitoring
- Services run independently from IntelliJ
- Better for automated testing pipelines

## 🎯 Success Indicators

Once test pipeline runs and completes:
- ✅ `conge.exec` file will grow in size (from 0 to N KB)
- ✅ `auth.exec` file will grow in size (from 0 to N KB)
- ✅ Coverage metrics will increase above 17.92%
- ✅ New HTML reports will be generated with detailed coverage breakdown

## 🔍 Troubleshooting

If services don't start:
1. Check port availability: `netstat -ano | findstr :9000`
2. Check Java path: `where java`
3. Verify JaCoCo agent exists: `Test-Path "C:\Users\MSI\.m2\repository\org\jacoco\org.jacoco.agent\0.8.11\org.jacoco.agent-0.8.11-runtime.jar"`
4. Check for Java errors in terminal output

If coverage not collecting:
1. Verify `.exec` files exist and grow in size during test execution
2. Confirm services are actually being hit by tests
3. Check that test APIs are targeting correct ports (9000, 9001)

---

**Created**: March 24, 2026
**JaCoCo Version**: 0.8.11
**Java Version**: 17.0.12
**Spring Boot Version**: 3.2.3
