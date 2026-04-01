#!/usr/bin/env python3
import re

file_path = r'C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Replace valueOf() calls with direct assignment
# valueOf(userDto.getUserRole()) -> userDto.getUserRole()
content = re.sub(r'valueOf\s*\(\s*(\w+\.get\w+\(\))\s*\)', r'\1', content)
content = re.sub(r'valueOf\s*\(\s*(\w+)\s*\)', r'\1', content)

# Fix 2: Remove .name() calls on strings
# "EMPLOYER".name() -> "EMPLOYER"
content = re.sub(r'"([^"]+)"\s*\.\s*name\s*\(\)', r'"\1"', content)
# userRole.name() -> userRole (when userRole is already a String)
content = re.sub(r'(\w+)\s*\.\s*name\s*\(\)\s*\.equals', r'\1.equals', content)

# Fix 3: Direct comparison without .name()
# .equals("EMPLOYER".name() -> .equals("EMPLOYER"
content = re.sub(r'\.equals\s*\(\s*"([^"]+)"\s*\.\s*name\s*\(\)', r'.equals("\1"', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed valueOf() and .name() calls")

# Verify the fixes
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("\nVerification - lines with issues:")
for line_num in [139, 625, 629, 764, 789]:
    if line_num <= len(lines):
        line = lines[line_num-1].strip()
        print(f"Line {line_num}: {line[:120]}")
