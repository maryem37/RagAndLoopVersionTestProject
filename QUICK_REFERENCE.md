# ⚡ Quick Reference: Generalized Microservices Testing

## Adding a New Service (2 Steps)

### Step 1: Edit `config/services_matrix.yaml`
```yaml
  your_service:
    enabled: true
    port: 9002
    db:
      type: "postgres"
      port: 5433
    java_package: "com.example.your_service"
    test_runner_class: "com.example.your_service.TestRunner"
    pom_location: "output/tests"
    dependencies: ["service_it_depends_on"]
```

### Step 2: Create Swagger (optional)
Create file: `examples/sample_your_service_swagger.json`

### That's it! ✅

---

## Run Commands

| Command | Effect |
|---------|--------|
| `python run_pipeline.py` | Test all enabled services |
| `python run_pipeline.py --services auth` | Test only auth |
| `python run_pipeline.py --services auth,leave` | Test multiple |
| `python run_pipeline.py --list` | Show available services |
| `python run_pipeline.py --order` | Show execution order |

---

## Configuration Template

```yaml
services:
  # SERVICE 1
  service1:
    enabled: true
    port: 9000
    db: {type: "postgres", port: 5432}
    java_package: "com.example.service1"
    test_runner_class: "com.example.service1.TestRunner"
    pom_location: "output/tests"
    dependencies: []

  # SERVICE 2 (depends on SERVICE 1)
  service2:
    enabled: true
    port: 9001
    db: {type: "mysql", port: 3306}
    java_package: "com.example.service2"
    test_runner_class: "com.example.service2.TestRunner"
    pom_location: "output/tests"
    dependencies: ["service1"]

  # SERVICE 3 (depends on SERVICE 1 and 2)
  service3:
    enabled: false  # Change to true to enable
    port: 9002
    db: {type: "postgres", port: 5433}
    java_package: "com.example.service3"
    test_runner_class: "com.example.service3.TestRunner"
    pom_location: "output/tests"
    dependencies: ["service1", "service2"]
```

---

## How to Use in Your Code

```python
# Get the service registry
from tools.service_registry import get_service_registry
registry = get_service_registry()

# List all enabled services
for service in registry.get_enabled_services():
    print(f"{service.name}: {service.get_base_url()}")

# Get execution order
order = registry.get_execution_order()  # Respects dependencies

# Check dependencies
deps = registry.get_service_dependencies("service2")  # Returns ["service1"]

# Get impact of changes
impact = registry.get_impact_scope("service1")  # All services affected by service1
```

---

## File Locations

| Purpose | File |
|---------|------|
| **Configuration** | `config/services_matrix.yaml` |
| **Service Registry** | `tools/service_registry.py` |
| **Entry Point** | `run_pipeline.py` |
| **Detailed Guide** | `GENERALIZATION_GUIDE.md` |

---

## Examples

### 2 Services (Auth + Leave)
```yaml
services:
  auth:
    enabled: true
    port: 9000
    dependencies: []
  leave:
    enabled: true
    port: 9001
    dependencies: ["auth"]
```

### 3+ Services (Linear Chain)
```yaml
services:
  auth: {enabled: true, port: 9000, dependencies: []}
  leave: {enabled: true, port: 9001, dependencies: ["auth"]}
  payment: {enabled: true, port: 9002, dependencies: ["auth", "leave"]}
```

### Complex Dependencies
```yaml
services:
  auth: {enabled: true, port: 9000, dependencies: []}
  leave: {enabled: true, port: 9001, dependencies: ["auth"]}
  payment: {enabled: true, port: 9002, dependencies: ["auth"]}
  notification: {enabled: true, port: 9003, dependencies: ["auth", "leave", "payment"]}
```

---

## Status

✅ System is now **completely generalized**
✅ Works for **any number of services**
✅ **Zero hardcoding** of service names/ports
✅ **Configuration-driven** via `services_matrix.yaml`
✅ Ready to scale from 2 to 100+ microservices
