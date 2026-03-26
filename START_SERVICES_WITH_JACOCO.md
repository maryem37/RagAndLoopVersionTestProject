# Starting Microservices with JaCoCo Coverage Monitoring

To collect code coverage from the running microservices, restart them with JaCoCo agent enabled.

## Prerequisites

1. Download JaCoCo agent JAR if you don't have it:
   ```
   Version: 0.8.11 (used in pom.xml)
   Download from: https://repo.maven.apache.org/maven2/org/jacoco/org.jacoco.agent/0.8.11/org.jacoco.agent-0.8.11-runtime.jar
   Save to: C:\Bureau\Bureau\project_test\lib\jacocoagent.jar
   ```

2. Or use Maven to download it:
   ```
   mvn org.apache.maven.plugins:maven-dependency-plugin:3.6.0:get -Dartifact=org.jacoco:org.jacoco.agent:0.8.11:jar -DrepoUrl=https://repo.maven.apache.org/maven2/
   ```

## Auth Service (Port 9000)

**Current startup command** (unknown - adjust based on how it's started):
```bash
java -jar auth-service.jar --server.port=9000
```

**With JaCoCo enabled:**
```bash
java -javaagent:C:\Bureau\Bureau\project_test\output\jacoco\auth.exec=destfile=C:\Bureau\Bureau\project_test\output\jacoco\auth.exec ^
     -jar auth-service.jar --server.port=9000
```

Wait, fix that - the destfile should be the exec file location:

```bash
java -javaagent:C:\path\to\jacocoagent.jar=destfile=C:\Bureau\Bureau\project_test\output\jacoco\auth.exec ^
     -jar auth-service.jar --server.port=9000
```

## Leave Service (Port 9001)

**With JaCoCo enabled:**
```bash
java -javaagent:C:\path\to\jacocoagent.jar=destfile=C:\Bureau\Bureau\project_test\output\jacoco\leave.exec ^
     -jar leave-service.jar --server.port=9001
```

## Key Points

- The `-javaagent` argument MUST come before `-jar`
- `destfile=` specifies where to write the `.exec` coverage file
- Use separate `.exec` files for each service:
  - `auth.exec` for Auth service
  - `leave.exec` (or `conge.exec`) for Leave service
- The `jacocoagent.jar` file path must match where you saved it

## After Restarting with JaCoCo

1. Services will be running with coverage monitoring
2. Run the test pipeline: `python run_pipeline.py --services auth`
3. After tests complete, the `.exec` files will be updated with coverage data
4. JaCoCo report will show actual microservice code coverage (not just test code)

## Finding Your Services' Startup Command

If you don't know the current startup command:

1. **If running in PowerShell**: Use `Get-Process` to find Java processes
   ```powershell
   Get-Process java | Select-Object CommandLine
   ```

2. **If running in Docker**: Check docker ps and inspect the container
   ```
   docker ps
   docker inspect <container_id>
   ```

3. **If running as Windows Service**: Check Services or the startup command in service properties

## Stopping Services Before Restart

```powershell
# Find Java processes on ports 9000 and 9001
Get-NetTCPConnection | Where-Object LocalPort -in (9000, 9001)

# Kill the process
Stop-Process -Id <PID> -Force
```

---

**Once you restart the services with JaCoCo, run this command to verify coverage data collection:**
```powershell
python run_pipeline.py --services auth
```

The coverage percentage should then increase from 17.92% to reflect actual microservice code execution.
