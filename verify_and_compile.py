#!/usr/bin/env python3
"""Verify and fix enum references, then compile."""
import subprocess
import re
import os

os.chdir(r'C:\Bureau\Bureau\microservices\DemandeConge')

# The file path
impl_file = r'C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java'

print("Reading file...")
with open(impl_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Count remaining issues
issue_count_before = len(re.findall(r'\b(TeamLeader|Administration|Employer)\b', content))
print(f"Found {issue_count_before} unreplaced enum references")

if issue_count_before > 0:
    print("\nApplying fixes...")
    # Replace enum values
    content = re.sub(r'\bTeamLeader\b', '"TEAM_LEADER"', content)
    content = re.sub(r'\bAdministration\b', '"ADMINISTRATION"', content)
    content = re.sub(r'\bEmployer\b', '"EMPLOYER"', content)
    
    with open(impl_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Fixes applied")

# Verify
with open(impl_file, 'r', encoding='utf-8') as f:
    content2 = f.read()
    
issue_count_after = len(re.findall(r'\b(TeamLeader|Administration|Employer)\b', content2))
print(f"After fix: {issue_count_after} unreplaced enum references")

# Try to compile
print("\nCompiling...")
result = subprocess.run(['mvn', 'clean', 'compile', '-q'], capture_output=True, text=True)

if result.returncode == 0:
    print("✅ COMPILATION SUCCESS!")
    exit(0)
else:
    print("❌ Compilation failed")
    # Show errors
    for line in result.stderr.split('\n'):
        if 'ERROR' in line:
            print(line)
    exit(1)
