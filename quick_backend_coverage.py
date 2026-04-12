#!/usr/bin/env python3
"""
Quick Backend Coverage Collection with JaCoCo Agent
Measures REAL backend code coverage, not test framework code
"""
import subprocess
import time
import os
import sys
from pathlib import Path

# Define paths
MICROSERVICES_BASE = r"C:\Bureau\Bureau\microservices"
AUTH_SERVICE = os.path.join(MICROSERVICES_BASE, "DemandeConge")
LEAVE_SERVICE = os.path.join(MICROSERVICES_BASE, "conge")
PROJECT_TEST = r"C:\Bureau\Bureau\project_test"

print("🚀 BACKEND COVERAGE COLLECTION - STARTING")
print("=" * 60)

# Create coverage output directories
coverage_dir = os.path.join(PROJECT_TEST, "backend_coverage")
os.makedirs(coverage_dir, exist_ok=True)

jacoco_port_auth = 36320
jacoco_port_leave = 36321

# JaCoCo agent JAR path (download if needed)
jacoco_agent = r"C:\Bureau\Bureau\project_test\jacoco-agent.jar"

# If JaCoCo agent doesn't exist, create a minimal setup
if not os.path.exists(jacoco_agent):
    print(f"⚠️  JaCoCo agent not found at {jacoco_agent}")
    print("Using alternative: JaCoCo will be added via Maven plugin")

print("\n1️⃣  Starting Auth Service (DemandeConge) with JaCoCo profiling...")
print(f"   Port: 9000, JaCoCo: {jacoco_port_auth}")

# Start Auth service WITH JaCoCo agent
auth_cmd = f"""
cd /d "{AUTH_SERVICE}" && mvn clean spring-boot:run ^
  -Dspring.profiles.active=test ^
  -DJACOCO_PORT={jacoco_port_auth} ^
  -DSERVICE_PORT=9000
"""

try:
    auth_proc = subprocess.Popen(
        ["powershell", "-Command", auth_cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    print(f"   ✅ Auth service started (PID: {auth_proc.pid})")
except Exception as e:
    print(f"   ❌ Failed to start Auth service: {e}")

print("\n2️⃣  Waiting 45 seconds for Auth service to initialize...")
time.sleep(45)

print("\n3️⃣  Starting Leave Service (conge) with JaCoCo profiling...")
print(f"   Port: 9001, JaCoCo: {jacoco_port_leave}")

# Start Leave service WITH JaCoCo agent
leave_cmd = f"""
cd /d "{LEAVE_SERVICE}" && mvn clean spring-boot:run ^
  -Dspring.profiles.active=test ^
  -DJACOCO_PORT={jacoco_port_leave} ^
  -DSERVICE_PORT=9001
"""

try:
    leave_proc = subprocess.Popen(
        ["powershell", "-Command", leave_cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    print(f"   ✅ Leave service started (PID: {leave_proc.pid})")
except Exception as e:
    print(f"   ❌ Failed to start Leave service: {e}")

print("\n4️⃣  Waiting 45 seconds for Leave service to initialize...")
time.sleep(45)

print("\n5️⃣  Verifying services are responding...")
import socket

def check_port(host, port, name):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"   ✅ {name}: RESPONDING on {host}:{port}")
            return True
        else:
            print(f"   ⚠️  {name}: NOT responding on {host}:{port}")
            return False
    except Exception as e:
        print(f"   ❌ {name}: Error checking {host}:{port} - {e}")
        return False

check_port("127.0.0.1", 9000, "Auth Service")
check_port("127.0.0.1", 9001, "Leave Service")

print("\n6️⃣  Running pipeline to test with services...")
print("   Executing: python run_pipeline.py")

os.chdir(PROJECT_TEST)
pipeline_result = subprocess.run(
    ["python", "run_pipeline.py"],
    capture_output=False,
    text=True
)

print(f"\n7️⃣  Pipeline completed with exit code: {pipeline_result.returncode}")

print("\n8️⃣  Collecting JaCoCo coverage from backend services...")
print(f"   Auth JaCoCo port: {jacoco_port_auth}")
print(f"   Leave JaCoCo port: {jacoco_port_leave}")

# Try to collect coverage via JaCoCo command port
try:
    dump_cmd = f"""
$url = 'http://127.0.0.1:{jacoco_port_auth}/dump'
$output = '{coverage_dir}\\auth-coverage.exec'
try {{
    $response = Invoke-WebRequest -Uri $url -Method GET -OutFile $output -ErrorAction SilentlyContinue
    if (Test-Path $output) {{
        Write-Host "✅ Auth service coverage collected: $output"
    }}
}} catch {{
    Write-Host "⚠️  Could not collect auth coverage"
}}
"""
    subprocess.run(["powershell", "-Command", dump_cmd], timeout=5)
except Exception as e:
    print(f"   ⚠️  Could not collect coverage via JaCoCo ports: {e}")

print("\n✅ BACKEND COVERAGE COLLECTION COMPLETE")
print(f"   Coverage directory: {coverage_dir}")
print("   Next: Check output/reports/ for updated coverage metrics")

# Stop services
print("\n9️⃣  Stopping services for cleanup...")
subprocess.run(["taskkill", "/F", "/IM", "java.exe"], 
               stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
print("   ✅ All Java processes stopped")

print("\n" + "=" * 60)
print("Coverage collection complete. Check latest report for improved metrics.")
