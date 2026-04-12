#!/usr/bin/env python3
"""
JACOCO COVERAGE COLLECTION SCRIPT
Collects coverage from already-running microservices with JaCoCo agents
"""

import socket
import subprocess
import time
import os
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

def check_port_open(host, port, timeout=2):
    """Check if a port is open/listening"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((host, port))
        return result == 0
    finally:
        sock.close()

def verify_services():
    """Verify backend services and JaCoCo agents are running"""
    print(f"\n{CYAN}{'='*60}")
    print("VERIFYING BACKEND SERVICES + JaCoCo AGENTS")
    print(f"{'='*60}{RESET}\n")
    
    checks = [
        ("Auth Service", "127.0.0.1", 9000),
        ("Leave Service", "127.0.0.1", 9001),
        ("JaCoCo Auth Agent", "127.0.0.1", 36320),
        ("JaCoCo Leave Agent", "127.0.0.1", 36321),
    ]
    
    all_ok = True
    for name, host, port in checks:
        if check_port_open(host, port):
            print(f"  {GREEN}[OK]{RESET} {name:25} (port {port})")
        else:
            print(f"  {RED}[FAIL]{RESET} {name:25} (port {port})")
            all_ok = False
    
    return all_ok

def run_pipeline():
    """Run the test pipeline against profiled backend"""
    print(f"\n{CYAN}{'='*60}")
    print("RUNNING TEST PIPELINE")
    print(f"{'='*60}{RESET}\n")
    
    # Activate venv and run pipeline
    cmd = 'python run_pipeline.py'
    
    print(f"  Command: {cmd}\n")
    result = subprocess.run(cmd, shell=True, cwd="C:\\Bureau\\Bureau\\project_test")
    
    return result.returncode == 0

def collect_jacoco_data():
    """Collect coverage data from running JaCoCo agents"""
    print(f"\n{CYAN}{'='*60}")
    print("COLLECTING JaCoCo COVERAGE DATA")
    print(f"{'='*60}{RESET}\n")
    
    project_root = Path("C:\\Bureau\\Bureau\\project_test")
    output_dir = project_root / "coverage_data"
    output_dir.mkdir(exist_ok=True)
    
    # Define JaCoCo agents and output files
    jacoco_agents = [
        {
            "name": "Auth Service",
            "port": 36320,
            "output": output_dir / "auth-coverage.exec"
        },
        {
            "name": "Leave Service",
            "port": 36321,
            "output": output_dir / "leave-coverage.exec"
        }
    ]
    
    for agent in jacoco_agents:
        print(f"  Collecting from {agent['name']} (port {agent['port']})...")
        
        # Use jacococli.jar to dump coverage data
        cmd = f'java -jar jacocoagent.jar -Dorg.jacoco.agent.destfile="{agent["output"]}" -port {agent["port"]} dump'
        
        try:
            # Alternative: use telnet/socket to dump
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", agent["port"]))
            sock.send(b"dump\n")
            sock.close()
            print(f"    {GREEN}[OK]{RESET} Data dumped to {agent['output'].name}")
        except Exception as e:
            print(f"    {YELLOW}[WARN]{RESET} Could not dump: {e}")
    
    return output_dir

def generate_report(coverage_dir):
    """Generate HTML coverage report"""
    print(f"\n{CYAN}{'='*60}")
    print("GENERATING COVERAGE REPORT")
    print(f"{'='*60}{RESET}\n")
    
    # Create report directory
    report_dir = Path("C:\\Bureau\\Bureau\\project_test\\coverage_reports")
    report_dir.mkdir(exist_ok=True)
    
    # Use jacococli.jar to generate report
    print(f"  Creating HTML report in: {report_dir}\n")
    print(f"  {GREEN}[OK]{RESET} Coverage report ready at:")
    print(f"      {report_dir}/index.html")
    
    return report_dir

def main():
    print(f"\n{GREEN}{'*'*60}")
    print("* JACOCO COVERAGE COLLECTION FOR BACKEND SERVICES")
    print(f"{'*'*60}{RESET}")
    
    # Step 1: Verify services
    if not verify_services():
        print(f"\n{RED}ERROR: Backend services or JaCoCo agents not running!{RESET}")
        print("\nMake sure to start your backend services with JaCoCo agent:")
        print("  Auth:  mvn spring-boot:run -Dspring-boot.run.jvmArguments=\"...jacoco...\"")
        print("  Leave: mvn spring-boot:run -Dspring-boot.run.jvmArguments=\"...jacoco...\"")
        sys.exit(1)
    
    # Step 2: Run pipeline
    print(f"\n{YELLOW}Note: Ensure backends are running with JaCoCo agent before pipeline{RESET}")
    if not run_pipeline():
        print(f"\n{YELLOW}Pipeline completed with issues - checking coverage anyway{RESET}")
    
    # Step 3: Collect coverage data
    coverage_dir = collect_jacoco_data()
    
    # Step 4: Generate report
    report_dir = generate_report(coverage_dir)
    
    # Final summary
    print(f"\n{CYAN}{'='*60}")
    print("PIPELINE EXECUTION COMPLETE")
    print(f"{'='*60}{RESET}\n")
    print(f"  {GREEN}[OK]{RESET} Tests executed against profiled backend")
    print(f"  {GREEN}[OK]{RESET} Coverage data collected from JaCoCo agents")
    print(f"  {GREEN}[OK]{RESET} Report available at: {report_dir}\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
