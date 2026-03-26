# Generalized Microservices Test Automation Guide

## Overview

Your test automation system is now **completely generalized** to work with **any number of microservices** (2, 3, 5, 10+).

Instead of hardcoding service names and ports, everything now uses a **ServiceRegistry** pattern loaded from `services_matrix.yaml`.

---

## Quick Start: Adding a New Service

### **Step 1: Edit `config/services_matrix.yaml`**

Add your service to the `services` section:

```yaml
services:
  auth:
    enabled: true
    port: 9000
    db:
      type: "postgres"
      port: 5432
    java_package: "com.example.auth"
    test_runner_class: "com.example.auth.AuthTestRunner"
    pom_location: "output/tests"
    dependencies: []

  leave:
    enabled: true
    port: 9001
    db:
      type: "mysql"
      port: 3306
    java_package: "com.example.leave"
    test_runner_class: "com.example.leave.LeaveTestRunner"
    pom_location: "output/tests"
    dependencies: ["auth"]

  # ADD YOUR NEW SERVICE HERE
  payment:
    enabled: true  # Set to false to disable testing
    port: 9002
    db:
      type: "postgres"
      port: 5433
    java_package: "com.example.payment"
    test_runner_class: "com.example.payment.PaymentTestRunner"
    pom_location: "output/tests"
    dependencies: ["auth", "leave"]
```

### **Step 2: Create Swagger Spec** (Optional but recommended)

Add file: `examples/sample_payment_swagger.json`

The pipeline will automatically discover and load it.

### **Step 3: Run Pipeline**

```bash
# Run ALL enabled services (respecting dependency order)
python run_pipeline.py

# Run specific service
python run_pipeline.py --services payment

# Run multiple services
python run_pipeline.py --services auth,leave,payment

# List available services
python run_pipeline.py --list

# Show execution order
python run_pipeline.py --order
```

---

## Architecture: How It Works

### **ServiceRegistry Pattern**

```
services_matrix.yaml
        ↓
   ServiceRegistry (tools/service_registry.py)
        ↓
   get_service_registry()  [global singleton]
        ↓
   Used by:
   • settings.py → Loads services dynamically
   • run_pipeline.py → Processes any services
   • test_executor.py → Builds Maven commands with all service URLs
   • workflow.py → Orchestrates testing
```

### **Key Components**

#### **1. ServiceRegistry** (`tools/service_registry.py`)
```python
from tools.service_registry import get_service_registry

registry = get_service_registry()

# Get all enabled services
enabled = registry.get_enabled_services()

# Get execution order (respects dependencies)
order = registry.get_execution_order()  # Returns: [auth, leave, payment]

# Check if services can run in parallel
can_parallel = registry.can_run_parallel("leave", "payment")  # True if no mutual deps

# Get service configuration
config = registry.get_service_config("payment")
# Returns: {port: 9002, base_url: http://127.0.0.1:9002, ...}
```

#### **2. Configuration** (`config/services_matrix.yaml`)

```yaml
services:
  <service_name>:
    enabled: bool                    # Enable/disable service
    port: int                        # Service port
    db:
      type: string                   # postgres, mysql, mongodb, etc.
      port: int                      # Database port
    java_package: string             # Base Java package (e.g., com.example.payment)
    test_runner_class: string        # Cucumber runner class
    pom_location: string             # Path to pom.xml
    dependencies: [list of strings]  # Other services this depends on
```

#### **3. Settings Integration** (`config/settings.py`)

```python
from config.settings import get_settings

settings = get_settings()
registry = settings.service_registry

# Now all code uses dynamic configuration
for service in registry.get_enabled_services():
    print(f"Service: {service.name}, Port: {service.port}")
```

---

## Examples: Different Scenarios

### **Scenario 1: 2 Services (Current)**
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

# Run: python run_pipeline.py
# Result: Tests auth → then tests leave (auth must pass first)
```

### **Scenario 2: 3+ Services with Complex Dependencies**
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
  
  payment:
    enabled: true
    port: 9002
    dependencies: ["auth", "leave"]
  
  notification:
    enabled: true
    port: 9003
    dependencies: ["auth"]

# Execution order: auth → [leave, notification] (parallel) → payment
```

### **Scenario 3: Selective Testing**
```bash
# Only test auth
python run_pipeline.py --services auth

# Only test leave and payment (auth will also run since leave depends on it)
python run_pipeline.py --services leave,payment

# Disable a service temporarily
# In services_matrix.yaml: set payment.enabled: false
python run_pipeline.py  # Payment won't be tested
```

### **Scenario 4: Change Impact Analysis**
```python
from tools.service_registry import get_service_registry

registry = get_service_registry()

# If auth service changed, what needs retesting?
impact = registry.get_impact_scope("auth")
# Returns: ["auth", "leave", "payment", "notification"]
# (All services that directly or indirectly depend on auth)
```

---

## How Code Uses ServiceRegistry

### **Before (Hardcoded)**
```python
# Old: Hardcoded service names and ports
auth_url = "http://localhost:9000"
leave_url = "http://localhost:9001"
```

### **After (Dynamic)**
```python
# New: Dynamic from registry
from tools.service_registry import get_service_registry

registry = get_service_registry()

# Works for ANY number of services
for service in registry.get_enabled_services():
    service_url = service.get_base_url()  # Automatically http://127.0.0.1:<port>
```

---

## Key Files Changed

| File | Changes |
|------|---------|
| `config/services_matrix.yaml` | **NEW** - Central configuration |
| `tools/service_registry.py` | **NEW** - Service management |
| `config/settings.py` | Updated to load from registry |
| `run_pipeline.py` | Updated to be service-agnostic with CLI |
| `agents/test_executor.py` | Updated to build Maven commands dynamically |

---

## Testing Your Changes

### **Verify Configuration Loads**
```bash
python -c "from tools.service_registry import get_service_registry; r = get_service_registry(); r.print_summary()"
```

### **Test Service Discovery**
```bash
python run_pipeline.py --list
```

### **Test Execution Order**
```bash
python run_pipeline.py --order
```

### **Run Full Pipeline**
```bash
python run_pipeline.py
```

---

## Scaling Examples

### **2 Services** (Your current setup)
```bash
python run_pipeline.py --services auth,leave
# Time: ~5 min
```

### **5 Services**
```bash
python run_pipeline.py
# Runs: auth → [leave, payment, notification] → analytics
# Time: ~15 min (with parallelization)
```

### **10+ Services**
```bash
# In services_matrix.yaml, enable up to 10 services
python run_pipeline.py
# ServiceRegistry handles all coordination automatically
# Time: Depends on dependencies and parallelization
```

---

## Advanced: Enable Parallelization

**Coming soon:** Modify `workflow.py` to run independent services in parallel.

For now, services run sequentially in dependency order. Example:

```
Current: auth → leave → payment → notification (sequential)
Future:  auth → [leave, notification] → payment (parallel where possible)
```

---

## Troubleshooting

### **"Unknown service" Error**
```bash
# Check service is defined in services_matrix.yaml
python run_pipeline.py --list
```

### **"Port conflict" Error**
```bash
# Two services configured on same port
# Fix: In services_matrix.yaml, use unique ports (9000, 9001, 9002, etc.)
```

### **"Circular dependency" Error**
```bash
# Service A depends on B, but B depends on A
# Fix: Remove circular dependency in services_matrix.yaml
```

### **Service not tested**
```bash
# Check if service is enabled
# In services_matrix.yaml: set enabled: true
```

---

## Summary

✅ **One configuration file** (`services_matrix.yaml`) controls everything
✅ **Add new services** - Just add a block, no code changes
✅ **Remove services** - Set `enabled: false`
✅ **Scale to 2, 3, 10+ services** - No code refactoring needed
✅ **Automatic dependency management** - Services test in correct order
✅ **CLI support** - Select which services to test

**Your system now adapts to ANY microservice architecture!**
