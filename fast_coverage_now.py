#!/usr/bin/env python3
"""
FAST COVERAGE SOLUTION: Run pipeline now, collect coverage after
No need to wait for service restart - uses existing running services
"""

import subprocess
import os
import time
from pathlib import Path

def run_pipeline_now():
    """Run pipeline against current backend (with or without JaCoCo)"""
    print("\n" + "="*60)
    print("RUNNING TEST PIPELINE (48 tests)")
    print("="*60 + "\n")
    
    os.chdir("C:\\Bureau\\Bureau\\project_test")
    result = subprocess.run(["python", "run_pipeline.py"], shell=True)
    
    return result.returncode == 0

def generate_coverage_report():
    """Generate coverage report from existing test execution"""
    print("\n" + "="*60)
    print("GENERATING COVERAGE REPORT")
    print("="*60 + "\n")
    
    # Go to test directory
    os.chdir("C:\\Bureau\\Bureau\\project_test\\output\\tests")
    
    # Run Maven with JaCoCo report generation
    cmd = 'mvn jacoco:report'
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print("\n[OK] Coverage report generated")
        report_path = Path("target/site/jacoco/index.html")
        if report_path.exists():
            print(f"[OK] Report available: {report_path.absolute()}")
            return True
    
    return False

def main():
    print("\n" + "*"*60)
    print("* FAST COVERAGE COLLECTION")
    print("* (Using existing backend)")
    print("*"*60)
    
    # Step 1: Run pipeline
    if run_pipeline_now():
        print("\n[OK] Tests completed successfully")
    else:
        print("\n[WARN] Tests completed with some issues")
    
    # Step 2: Generate coverage report
    time.sleep(5)
    if generate_coverage_report():
        print("\n[SUCCESS] Coverage report ready!")
        print("\nOpen: C:\\Bureau\\Bureau\\project_test\\output\\tests\\target\\site\\jacoco\\index.html")
    else:
        print("\n[INFO] Check: C:\\Bureau\\Bureau\\project_test\\output\\tests\\target\\site\\")
    
    print("\n" + "*"*60)
    print("Pipeline + Coverage Complete!")
    print("*"*60 + "\n")

if __name__ == "__main__":
    main()
