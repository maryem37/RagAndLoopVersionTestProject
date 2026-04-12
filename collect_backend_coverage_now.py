#!/usr/bin/env python3
"""
REAL BACKEND COVERAGE - Direct Solution
Starts services, runs pipeline, collects backend coverage
"""
import subprocess
import time
import os
import sys
import shutil

def run_cmd(cmd, shell=True, cwd=None, background=False):
    """Run shell command"""
    try:
        if background:
            subprocess.Popen(cmd, shell=shell, cwd=cwd, 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            return None
        else:
            result = subprocess.run(cmd, shell=shell, cwd=cwd, 
                                  capture_output=True, text=True, timeout=120)
            return result
    except subprocess.TimeoutExpired:
        return None

PROJECT = r"C:\Bureau\Bureau\project_test"
MICROSERVICES = r"C:\Bureau\Bureau\microservices"

print("🚀 REAL BACKEND COVERAGE - STARTING")
print("=" * 70)

# Kill any existing processes
print("\n[1/8] Stopping any running services...")
run_cmd("taskkill /F /IM java.exe", cwd=PROJECT)
time.sleep(2)

# Start Auth service
print("\n[2/8] Starting Auth Service (DemandeConge) on port 9000...")
auth_service = os.path.join(MICROSERVICES, "DemandeConge")
auth_cmd = f'cd /d "{auth_service}" && mvn spring-boot:run -DskipTests -q'
run_cmd(auth_cmd, background=True)

# Wait for it
time.sleep(60)
print("     ✅ Auth service started (waiting for DB connection)")

# Start Leave service
print("\n[3/8] Starting Leave Service (conge) on port 9001...")
leave_service = os.path.join(MICROSERVICES, "conge")
leave_cmd = f'cd /d "{leave_service}" && mvn spring-boot:run -DskipTests -q'
run_cmd(leave_cmd, background=True)

# Wait
time.sleep(60)
print("     ✅ Leave service started (waiting for DB connection)")

# Check services
print("\n[4/8] Verifying services are responding...")
import socket
def port_open(host, port):
    try:
        s = socket.socket()
        s.settimeout(1)
        r = s.connect_ex((host, port))
        s.close()
        return r == 0
    except:
        return False

if port_open("127.0.0.1", 9000):
    print("     ✅ Auth service responding on port 9000")
else:
    print("     ⚠️  Auth service NOT responding - may still be initializing")

if port_open("127.0.0.1", 9001):
    print("     ✅ Leave service responding on port 9001")
else:
    print("     ⚠️  Leave service NOT responding - may still be initializing")

# Run pipeline
print("\n[5/8] Running pipeline tests against services...")
os.chdir(PROJECT)
result = subprocess.run(
    ["python", "run_pipeline.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Check for pass rate
output = result.stdout
if "Tests passed" in output:
    for line in output.split('\n'):
        if "Tests passed" in line or "pass rate" in line:
            print(f"     {line.strip()}")

print("     ✅ Pipeline completed")

# Stop services to flush coverage
print("\n[6/8] Stopping services to flush coverage data...")
run_cmd("taskkill /F /IM java.exe")
time.sleep(3)
print("     ✅ Services stopped")

# Check for coverage files
print("\n[7/8] Checking for backend coverage files...")
tests_dir = os.path.join(PROJECT, "output", "tests")
for root, dirs, files in os.walk(tests_dir):
    for f in files:
        if f.endswith(".exec"):
            print(f"     Found: {os.path.join(root, f)}")

# Generate report
print("\n[8/8] Generating coverage report...")
os.chdir(tests_dir)
report_cmd = f'"{os.path.expandvars("%MAVEN_HOME%/bin/mvn")}" jacoco:report -DskipTests -q'
if os.name == 'nt':
    # Windows
    maven_path = r"C:\Users\MSI\Downloads\apache-maven-3.9.10-bin\apache-maven-3.9.10\bin\mvn.cmd"
    if os.path.exists(maven_path):
        report_cmd = f'"{maven_path}" clean jacoco:report -DskipTests'
    
result = subprocess.run(report_cmd, shell=True, cwd=tests_dir,
                       capture_output=True, text=True)

# Check report
report_file = os.path.join(tests_dir, "target", "site", "jacoco", "index.html")
if os.path.exists(report_file):
    print(f"     ✅ Report generated: {report_file}")
else:
    print(f"     ⚠️  Report not found yet")

# Check latest coverage report
print("\n" + "=" * 70)
print("Coverage collection complete!")
reports_dir = os.path.join(PROJECT, "output", "reports")
if os.path.exists(reports_dir):
    latest = max([os.path.join(reports_dir, f) for f in os.listdir(reports_dir) 
                  if f.startswith("coverage_report") and f.endswith(".yaml")],
                 key=os.path.getctime, default=None)
    if latest:
        print(f"Latest report: {os.path.basename(latest)}")
        # Show coverage metrics
        with open(latest, 'r') as f:
            content = f.read()
            for line in content.split('\n')[:30]:
                if 'rate_%' in line or 'Lines' in line or 'Branches' in line:
                    print(f"  {line}")

print("\nTo view detailed report:")
print(f"  start \"{report_file}\"")
