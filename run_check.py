#!/usr/bin/env python3
import subprocess
import sys

# Run the check script
result = subprocess.run([sys.executable, r"c:\Bureau\Bureau\project_test\check_demandeconge_files.py"], capture_output=True, text=True)

# Read the output file
try:
    with open(r"C:\Bureau\Bureau\project_test\file_check_results.txt", 'r') as f:
        content = f.read()
    print(content)
except:
    print("Could not read results file")
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
