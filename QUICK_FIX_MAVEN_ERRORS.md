# Quick Fix: Maven Compilation Errors

## Problem
Generated tests reference backend classes that don't exist. Maven can't compile.

## Fastest Fix (2 minutes)

### Option 1: Skip Unit Tests (RECOMMENDED)
Keep contract/integration tests, skip unit tests:

```bash
# Edit output/tests/pom.xml
# Find <build> section and add:

<build>
    <plugins>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>3.0.0-M9</version>
            <configuration>
                <excludes>
                    <exclude>**/service/*Test.java</exclude>
                </excludes>
            </configuration>
        </plugin>
    </plugins>
</build>
```

Then run:
```bash
cd output/tests
mvn clean test
```

This will skip `AuthServiceTest.java` and `LeaveRequestServiceTest.java` but run contract tests.

---

### Option 2: Delete Unit Test Files
Fastest workaround:

```bash
# Delete files that are failing
rm output/tests/src/test/java/com/example/auth/service/*Test.java
rm output/tests/src/test/java/com/example/leave/service/*Test.java

# Rebuild
cd output/tests
mvn clean test
```

---

### Option 3: Remove Generated Unit Tests from Test Writer
Prevent re-generation:

Edit `agents/test_writer.py` line ~1850:

**Before**:
```python
# Both unit tests AND step definitions
test_writer.generate_for_service(service)  # Creates ServiceTest.java + Steps.java
```

**After**:
```python
# Only step definitions and Cucumber runners (no unit tests)
# Comment out: AuthServiceTest, LeaveRequestServiceTest generation
# Keep: AuthSteps, LeaveSteps, AuthTestRunner, LeaveTestRunner
```

---

## Why This Happens

✗ **Generated tests** try to test backend services  
✗ **Backe code** doesn't exist in this test project  
✗ **Maven** can't find the imports  

```
AuthServiceTest.java imports:
  ├─ com.example.auth.dto.UserDTO       ❌ NOT FOUND
  ├─ com.example.auth.entity.User       ❌ NOT FOUND
  ├─ com.example.auth.service.AuthService ❌ NOT FOUND
  └─ ...
```

---

## Once Fixed

After applying one of the above:

```bash
# Run contract/integration tests
cd output/tests
mvn clean verify -DAUTH_BASE_URL=http://127.0.0.1:9000 -DLEAVE_BASE_URL=http://127.0.0.1:9001

# Check coverage
open target/site/jacoco/index.html
```

---

## Best Long-Term Solution

**Get backend source code in classpath:**

```bash
# If you have backend JARs:
mvn install:install-file \
  -Dfile=../auth-service/target/auth-service.jar \
  -DgroupId=com.example \
  -DartifactId=auth-service \
  -Dversion=1.0.0 \
  -Dpackaging=jar

# Add to pom.xml:
<dependency>
    <groupId>com.example</groupId>
    <artifactId>auth-service</artifactId>
    <version>1.0.0</version>
</dependency>
```

Then unit tests will compile and run!

---

**Choose your fix above and run it. Report back with results!**
