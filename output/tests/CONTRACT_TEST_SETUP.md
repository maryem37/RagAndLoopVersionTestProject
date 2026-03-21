# Contract Test Setup

```bash
export TEST_JWT_TOKEN=<token>

# Run tests AND generate JaCoCo coverage report:
mvn clean verify -Dservice.name=leave-request-service

# Coverage report will be written to:
# tests/target/site/jacoco/jacoco.xml
```
