#!/usr/bin/env python3
import re

file_path = r'C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\entity\LeaveRequest.java'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find all @Enumerated annotations followed by String fields
pattern = r'@Enumerated\(EnumType\.STRING\)\s+private String (\w+);'
matches = re.findall(pattern, content)

print(f"Found {len(matches)} @Enumerated annotations on String fields:")
for match in matches:
    print(f"  - {match}")

# Remove @Enumerated annotations from String fields
content = re.sub(
    r'@Enumerated\(EnumType\.STRING\)\s+\n\s+private String',
    'private String',
    content
)

# Also try without the newline
content = re.sub(
    r'@Enumerated\(EnumType\.STRING\)\s+private String',
    'private String',
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ Removed @Enumerated annotations from String fields")

# Verify
with open(file_path, 'r', encoding='utf-8') as f:
    content2 = f.read()

remaining = len(re.findall(r'@Enumerated.*String', content2))
print(f"Remaining issues: {remaining}")
