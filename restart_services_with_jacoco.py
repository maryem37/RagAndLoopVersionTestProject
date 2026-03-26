#!/usr/bin/env python3
"""
Script to restart Java microservices with JaCoCo agent monitoring enabled.
This collects code coverage data during test execution.
"""

import subprocess
import time
import sys
import os
from pathlib import Path

# Configuration
JAVA_HOME = r"C:\Program Files\Java\jdk-17"
JAVA_EXE = os.path.join(JAVA_HOME, "bin", "java.exe")
CONGE_PATH = r"C:\Bureau\Bureau\microservices\conge\target\classes"
DEMANDE_CONGE_PATH = r"C:\Bureau\Bureau\microservices\DemandeConge\target\classes"
JACOCO_AGENT = os.path.expanduser(r"~\.m2\repository\org\jacoco\org.jacoco.agent\0.8.11\org.jacoco.agent-0.8.11-runtime.jar")
OUTPUT_DIR = r"C:\Bureau\Bureau\project_test\output\jacoco"
MAVEN_REPO = os.path.expanduser(r"~\.m2\repository")

def ensure_output_dir():
    """Create output directory if it doesn't exist"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    print(f"✓ Output directory ready: {OUTPUT_DIR}")

def stop_services():
    """Stop running Java services"""
    print("\n[Step 1] Stopping existing services...")
    
    # Kill processes by port using netstat
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        for line in result.stdout.split('\n'):
            if ':9000' in line or ':9001' in line:
                parts = line.split()
                if parts and parts[-1].isdigit():
                    pid = parts[-1]
                    port = ':9000' if ':9000' in line else ':9001'
                    print(f"  Killing process on port {port} (PID: {pid})...")
                    subprocess.run(["taskkill", "/PID", pid, "/F"], 
                                 stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"  ⚠ Could not identify services by port: {e}")
        print("  Attempting to kill java processes with known classnames...")
        subprocess.run(["taskkill", "/F", "/IM", "java.exe"], 
                      stderr=subprocess.DEVNULL)
    
    time.sleep(3)
    print("  ✓ Services stopped")

def get_maven_classpath(module_path):
    """Generate classpath using Maven dependency plugin"""
    print(f"\n[Step 2] Building classpath for {module_path}...")
    
    try:
        result = subprocess.run(
            [
                "mvn",
                "-f", os.path.join(module_path, "pom.xml"),
                "dependency:build-classpath",
                "-Dmdep.outputFile=.classpath.txt",
                "-q"
            ],
            cwd=module_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        classpath_file = os.path.join(module_path, ".classpath.txt")
        if os.path.exists(classpath_file):
            with open(classpath_file, 'r') as f:
                classpath = f.read().strip()
            # Add the module's target/classes to the beginning
            classes_dir = os.path.join(module_path, "target", "classes")
            full_classpath = f"{classes_dir};{classpath}"
            os.remove(classpath_file)
            return full_classpath
        else:
            print(f"  ⚠ Could not generate classpath, using fallback")
            return None
    except Exception as e:
        print(f"  ⚠ Maven classpath generation failed: {e}")
        return None

def start_service(name, port, main_class, module_path):
    """Start a microservice with JaCoCo agent"""
    print(f"\n[Step 3] Starting {name} Service on port {port}...")
    
    # Get classpath
    classpath = get_maven_classpath(module_path)
    
    if not classpath:
        print(f"  ❌ Could not determine classpath for {name}")
        return None
    
    # Prepare JaCoCo agent argument
    exec_file = os.path.join(OUTPUT_DIR, f"{name.lower()}.exec")
    jacoco_opts = f"-javaagent:{JACOCO_AGENT}=destfile={exec_file},append=false"
    
    # Build command
    cmd = [
        JAVA_EXE,
        jacoco_opts,
        "-Dfile.encoding=UTF-8",
        "-cp", classpath,
        f"-Dserver.port={port}",
        main_class
    ]
    
    try:
        print(f"  Starting process...")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"  ✓ {name} Service started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"  ❌ Failed to start {name} Service: {e}")
        return None

def verify_service(port, name):
    """Verify service is responding"""
    for attempt in range(5):
        try:
            import urllib.request
            response = urllib.request.urlopen(
                f"http://localhost:{port}/api/health",
                timeout=2
            )
            print(f"  ✓ {name} Service is responding on port {port}")
            return True
        except Exception:
            if attempt < 4:
                print(f"  ⏳ Waiting for {name} Service to start (attempt {attempt + 1}/5)...")
                time.sleep(2)
    
    print(f"  ⚠ {name} Service may still be starting, check logs")
    return False

def main():
    """Main execution"""
    print("=" * 60)
    print("Microservices Restart with JaCoCo Monitoring")
    print("=" * 60)
    
    # Verify Java
    if not os.path.exists(JAVA_EXE):
        print(f"❌ Java not found at: {JAVA_EXE}")
        sys.exit(1)
    
    # Verify JaCoCo agent
    if not os.path.exists(JACOCO_AGENT):
        print(f"❌ JaCoCo agent not found at: {JACOCO_AGENT}")
        sys.exit(1)
    
    # Prepare
    ensure_output_dir()
    stop_services()
    time.sleep(2)
    
    # Start services
    conge_process = start_service(
        "Conge",
        9000,
        "tn.enis.conge.CongeeApplication",
        r"C:\Bureau\Bureau\microservices\conge"
    )
    
    time.sleep(5)
    
    demande_process = start_service(
        "DemandeConge",
        9001,
        "tn.enis.DemandeConge.DemandeCongeApplication",
        r"C:\Bureau\Bureau\microservices\DemandeConge"
    )
    
    time.sleep(5)
    
    # Verify services
    print("\n[Step 4] Verifying services...")
    verify_service(9000, "Leave (Conge)")
    verify_service(9001, "Auth (DemandeConge)")
    
    # Summary
    print("\n" + "=" * 60)
    print("Services Ready for Testing!")
    print("=" * 60)
    if conge_process:
        print(f"Leave Service (conge):        PORT 9000, PID {conge_process.pid}")
    if demande_process:
        print(f"Auth Service (DemandeConge): PORT 9001, PID {demande_process.pid}")
    print(f"JaCoCo Coverage Output:      {OUTPUT_DIR}")
    print("\nNext: Run the test pipeline to collect coverage")
    print("  python run_pipeline.py --services auth")
    print("=" * 60)

if __name__ == "__main__":
    main()
