#!/usr/bin/env python3
"""Check the remaining errors in LeaveRequestServiceImpl."""
import subprocess
import re

# Run Maven compile
result = subprocess.run(
    ['mvn', 'compile'],
    cwd=r'C:\Bureau\Bureau\microservices\DemandeConge',
    capture_output=True,
    text=True
)

# Extract errors for LeaveRequestServiceImpl
errors = re.findall(
    r'\[ERROR\].*?LeaveRequestServiceImpl\.java:\[(\d+),\d+\].*?(?=\[ERROR\]|$)',
    result.stderr,
    re.DOTALL
)

print("Errors in LeaveRequestServiceImpl.java at lines:")
for match in re.finditer(r'LeaveRequestServiceImpl\.java:\[(\d+),(\d+)\]', result.stderr):
    line_num = match.group(1)
    col = match.group(2)
    print(f"  Line {line_num}, Col {col}")

# Also check what the file looks like at those lines
file_path = r'C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("\nContent at error lines:")
for line_num in [139, 625, 629, 764, 789]:
    if line_num <= len(lines):
        print(f"  Line {line_num}: {lines[line_num-1].strip()[:100]}")

# Count remaining UserRole references
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

user_role_count = len(re.findall(r'\bUserRole\b', content))
employer_count = len(re.findall(r'\bEmployer\b', content))
team_leader_count = len(re.findall(r'\bTeamLeader\b', content))
administration_count = len(re.findall(r'\bAdministration\b', content))

print(f"\nRemaining references:")
print(f"  UserRole: {user_role_count}")
print(f"  Employer: {employer_count}")
print(f"  TeamLeader: {team_leader_count}")
print(f"  Administration: {administration_count}")
