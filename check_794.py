#!/usr/bin/env python3
import re

file_path = r'C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Show line 794 and surrounding lines
print("Content around line 794:")
for i in range(790, min(798, len(lines))):
    print(f"{i+1}: {lines[i].rstrip()}")

# Search for any UserRole references
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

matches = list(re.finditer(r'\bUserRole\b', content))
print(f"\n\nUserRole references found: {len(matches)}")
for i, match in enumerate(matches):
    line_num = content[:match.start()].count('\n') + 1
    line_content = lines[line_num - 1].strip()
    print(f"  {i+1}. Line {line_num}: {line_content[:100]}")
