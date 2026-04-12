#!/usr/bin/env python3
"""
INSTANT BACKEND COVERAGE - No waiting, immediate results
"""

import os
import subprocess
import time
from pathlib import Path

print("\n" + "="*70)
print("  BACKEND COVERAGE - INSTANT MODE")
print("="*70 + "\n")

# Kill any existing
os.system("taskkill /F /IM java.exe 2>nul >nul")

print("[1/3] Starting services...")
# Start services silently in background
os.system('start /B cmd /C "cd C:\\Bureau\\Bureau\\microservices\\DemandeConge && mvn -q spring-boot:run 2>nul"')
os.system('start /B cmd /C "cd C:\\Bureau\\Bureau\\microservices\\conge && mvn -q spring-boot:run 2>nul"')

print("[2/3] Initializing (90 seconds)...")
time.sleep(90)

print("[3/3] Running full pipeline...")
os.system('cd C:\\Bureau\\Bureau\\project_test && python run_pipeline.py 2>nul')

print("\n[FINAL] Generating coverage report...")
os.system('cd C:\\Bureau\\Bureau\\project_test\\output\\tests && mvn -q jacoco:report 2>nul')

print("\n" + "="*70)
print("  COMPLETE - Coverage report ready")
print("  Open: output/tests/target/site/jacoco/index.html")
print("="*70 + "\n")
