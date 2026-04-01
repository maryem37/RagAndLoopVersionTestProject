#!/usr/bin/env python3
import re

file_path = r'C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    content = ''.join(lines)

# Check lines with errors
print("Lines with issues:")
for line_num in [139, 625, 629, 764, 789]:
    if line_num <= len(lines):
        line = lines[line_num-1].strip()
        print(f"Line {line_num}: {line[:120]}")

# Count references
user_role = len(re.findall(r'\bUserRole\b', content))
employer = len(re.findall(r'\bEmployer\b', content))
team_leader = len(re.findall(r'\bTeamLeader\b', content))
admin = len(re.findall(r'\bAdministration\b', content))

print(f"\nRemaining references:")
print(f"  UserRole: {user_role}")
print(f"  Employer: {employer}")
print(f"  TeamLeader: {team_leader}")
print(f"  Administration: {admin}")

# Show first occurrence of each
if employer > 0:
    m = re.search(r'\bEmployer\b', content)
    if m:
        line_num = content[:m.start()].count('\n') + 1
        print(f"\nEmployer first occurs at line {line_num}")

if team_leader > 0:
    m = re.search(r'\bTeamLeader\b', content)
    if m:
        line_num = content[:m.start()].count('\n') + 1
        print(f"TeamLeader first occurs at line {line_num}")

if admin > 0:
    m = re.search(r'\bAdministration\b', content)
    if m:
        line_num = content[:m.start()].count('\n') + 1
        print(f"Administration first occurs at line {line_num}")
