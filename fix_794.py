#!/usr/bin/env python3
import re

file_path = r'C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace MapJoin<..., UserRole, ...> with MapJoin<..., String, ...>
content = re.sub(r'MapJoin<([^,]+),\s*UserRole\s*,', r'MapJoin<\1, String,', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed MapJoin UserRole reference")

# Verify
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"\nLine 794 after fix: {lines[793].strip()[:120]}")

# Double check - count remaining UserRole
with open(file_path, 'r', encoding='utf-8') as f:
    content2 = f.read()

remaining = len(re.findall(r'\bUserRole\b', content2))
print(f"Remaining UserRole references: {remaining}")
