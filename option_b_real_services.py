#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPTION B: Test Real Microservices with Coverage Measurement
Builds, starts, and tests real microservices with JaCoCo enabled
"""

import subprocess
import time
import sys
import os
import requests
from pathlib import Path
from typing import Optional

# Configuration
JAVA_HOME = r"C:\Program Files\Java\jdk-17"
JAVA_EXE = os.path.join(JAVA_HOME, "bin", "java.exe")
JACOCO_AGENT = os.path.expanduser(r"~\.m2\repository\org\jacoco\org.jacoco.agent\0.8.11\org.jacoco.agent-0.8.11-runtime.jar")
MAVEN_HOME = r"C:\Users\MSI\Downloads\apache-maven-3.9.10-bin\apache-maven-3.9.10"
MAVEN_EXE = os.path.join(MAVEN_HOME, "bin", "mvn.cmd")
TEST_PROJECT_PATH = r"C:\Bureau\Bureau\project_test\output\tests"

# Real microservices
SERVICES = {
    "auth": {
        "name": "conge",
        "port": 9000,
        "path": r"C:\Bureau\Bureau\microservices\conge",
        "main_class": "tn.enis.conge.CongeApplication",
    },
    "leave": {
        "name": "DemandeConge",
        "port": 9001,
        "path": r"C:\Bureau\Bureau\microservices\DemandeConge",
        "main_class": "tn.enis.conge.DemandeCongeApplication",
    }
}

OUTPUT_DIR = r"C:\Bureau\Bureau\project_test\output\jacoco"

# ============================================================================
def stop_services():
    """Stop any running Java services"""
    print("\n" + "="*80)
    print("STOPPING EXISTING SERVICES")
    print("="*80)
    
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        killed_count = 0
        for line in result.stdout.split('\n'):
            for port in ['9000', '9001']:
                if f':{port}' in line:
                    parts = line.split()
                    if parts and len(parts) > 0:
                        pid = parts[-1]
                        if pid.isdigit():
                            print(f"  Killing process on port {port} (PID: {pid})...")
                            subprocess.run(
                                ["taskkill", "/PID", pid, "/F"],
                                stderr=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL
                            )
                            killed_count += 1
        
        if killed_count > 0:
            print(f"OK - Killed {killed_count} process(es)")
            time.sleep(2)
        else:
            print("OK - No existing services found")
    except Exception as e:
        print(f"Warning: {e}")

def build_microservice(service_key: str, service_config: dict) -> bool:
    """Build a microservice with Maven"""
    service_path = service_config["path"]
    service_name = service_config["name"]
    
    print(f"\n[Building {service_name}]")
    
    if not os.path.exists(service_path):
        print(f"ERROR: Path not found: {service_path}")
        return False
    
    try:
        result = subprocess.run(
            [MAVEN_EXE, "clean", "package", "-DskipTests", "-q"],
            cwd=service_path,
            timeout=300,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"OK - {service_name} built successfully")
            return True
        else:
            print(f"ERROR - {service_name} build failed")
            return False
    except subprocess.TimeoutExpired:
        print(f"ERROR - {service_name} build timed out")
        return False
    except Exception as e:
        print(f"ERROR - {service_name} build: {e}")
        return False

def build_all_services() -> bool:
    """Build all enabled services"""
    print("\n" + "="*80)
    print("BUILDING MICROSERVICES")
    print("="*80)
    
    for key, config in SERVICES.items():
        if not build_microservice(key, config):
            return False
    
    return True

def wait_for_service(port: int, service_name: str, max_retries: int = 20) -> bool:
    """Wait for service to be ready"""
    print(f"  Waiting for {service_name} on port {port}...")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"http://localhost:{port}/api/health",
                timeout=2
            )
            if response.status_code in [200, 500]:
                print(f"  OK - {service_name} is responding")
                return True
        except:
            if attempt < max_retries - 1:
                print(f"    Attempt {attempt + 1}/{max_retries}...")
                time.sleep(2)
    
    print(f"  ERROR - {service_name} did not respond")
    return False

def start_all_services() -> dict:
    """Start all enabled services with JaCoCo"""
    print("\n" + "="*80)
    print("STARTING MICROSERVICES WITH JACOCO")
    print("="*80)
    
    processes = {}
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    for key, config in SERVICES.items():
        port = config["port"]
        path = config["path"]
        name = config["name"]
        main_class = config["main_class"]
        
        print(f"\n[Starting {name}]")
        
        # Build classpath
        classpath = os.path.join(path, "target", "classes") + ";"
        target_lib = os.path.join(path, "target", "lib")
        if os.path.exists(target_lib):
            for jar in os.listdir(target_lib):
                if jar.endswith(".jar"):
                    classpath += os.path.join(target_lib, jar) + ";"
        
        # JaCoCo configuration
        jacoco_output = os.path.join(OUTPUT_DIR, f"{name}.exec")
        jacoco_arg = (
            f"-javaagent:{JACOCO_AGENT}="
            f"destfile={jacoco_output},"
            f"port={port + 2},"
            f"address=localhost,"
            f"append=false"
        )
        
        # Start service
        cmd = [
            JAVA_EXE,
            jacoco_arg,
            "-Dserver.port=" + str(port),
            "-Dspring.jpa.hibernate.ddl-auto=update",
            "-Dspring.datasource.url=jdbc:mysql://localhost:3306/conge?useSSL=false&serverTimezone=UTC&createDatabaseIfNotExist=true",
            "-Dspring.datasource.username=root",
            "-Dspring.datasource.password=root",
            "-cp", classpath,
            main_class
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(f"OK - {name} started (PID: {process.pid})")
            
            # Wait for service to be ready
            if wait_for_service(port, name):
                processes[key] = process
                time.sleep(2)
            else:
                process.terminate()
                print(f"ERROR - {name} failed health check")
        except Exception as e:
            print(f"ERROR - Failed to start {name}: {e}")
    
    if len(processes) == len(SERVICES):
        print(f"\nOK - All {len(SERVICES)} services started with JaCoCo")
        return processes
    else:
        print(f"\nWARNING - Only {len(processes)}/{len(SERVICES)} services started")
        return processes

def run_tests() -> bool:
    """Run test suite against real services"""
    print("\n" + "="*80)
    print("RUNNING TESTS AGAINST REAL SERVICES")
    print("="*80)
    
    print(f"Test project: {TEST_PROJECT_PATH}")
    
    try:
        result = subprocess.run(
            [MAVEN_EXE, "clean", "package", "-DskipTests=false"],
            cwd=TEST_PROJECT_PATH,
            timeout=600,
            capture_output=True,
            text=True
        )
        
        output = result.stdout + result.stderr
        
        # Extract test results
        for line in output.split('\n'):
            if "Tests run:" in line or "Errors:" in line or "Failures:" in line:
                print(f"  {line.strip()}")
        
        if "Tests run:" in output:
            print("\nOK - Tests executed")
            return True
        else:
            print("\nERROR - Tests did not run")
            return False
    except subprocess.TimeoutExpired:
        print("ERROR - Tests timed out")
        return False
    except Exception as e:
        print(f"ERROR - {e}")
        return False

def collect_coverage() -> bool:
    """Collect coverage data from services"""
    print("\n" + "="*80)
    print("COLLECTING COVERAGE DATA FROM REAL SERVICES")
    print("="*80)
    
    for key, config in SERVICES.items():
        name = config["name"]
        port = config["port"]
        
        print(f"\n[Collecting {name} coverage]")
        
        dump_url = f"http://localhost:{port}/jacoco-api/dump"
        jacoco_output = os.path.join(OUTPUT_DIR, f"{name}.exec")
        
        try:
            response = requests.get(dump_url, timeout=5)
            if response.status_code == 200:
                Path(jacoco_output).parent.mkdir(parents=True, exist_ok=True)
                with open(jacoco_output, 'wb') as f:
                    f.write(response.content)
                print(f"OK - Coverage saved to {jacoco_output}")
                print(f"    File size: {len(response.content)} bytes")
            else:
                print(f"WARNING - JaCoCo returned {response.status_code}")
        except Exception as e:
            print(f"WARNING - Could not collect: {e}")
    
    return True

def stop_all_services(processes: dict):
    """Stop all running services"""
    print("\n" + "="*80)
    print("STOPPING SERVICES")
    print("="*80)
    
    for key, process in processes.items():
        if process:
            name = SERVICES[key]['name']
            print(f"Stopping {name}...")
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"OK - {name} stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"OK - {name} killed")
            except Exception as e:
                print(f"WARNING - {e}")

def main():
    """Execute the complete Option B pipeline"""
    print("\n" + "="*80)
    print("OPTION B: TESTING REAL MICROSERVICES WITH COVERAGE")
    print("="*80)
    print("\nPipeline:")
    print("  1. Stop existing services")
    print("  2. Build microservices")
    print("  3. Start with JaCoCo agent")
    print("  4. Run tests against real services")
    print("  5. Collect coverage data")
    print("  6. Stop services")
    print("\nExpected improvement: 2.58% -> 30-70% coverage")
    print("="*80)
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    stop_services()
    
    if not build_all_services():
        print("\nERROR: Failed to build microservices")
        return False
    
    processes = start_all_services()
    
    if not processes:
        print("\nERROR: Failed to start microservices")
        return False
    
    try:
        run_tests()
        collect_coverage()
    finally:
        stop_all_services(processes)
    
    print("\n" + "="*80)
    print("COVERAGE COLLECTION COMPLETE")
    print("="*80)
    print(f"\nCoverage data location: {OUTPUT_DIR}")
    print("\nNext steps:")
    print("  cd C:\\Bureau\\Bureau\\project_test\\output\\tests")
    print("  mvn jacoco:report")
    print("  open target/site/jacoco/index.html")
    print("\nExpected improvement:")
    print("  Before: 2.58% (test harness only)")
    print("  After: 30-70% (real business logic)")
    print("="*80)
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
