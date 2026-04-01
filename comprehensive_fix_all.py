#!/usr/bin/env python3
"""Comprehensive fix for all remaining UserRole references in DemandeConge."""
import re
import os
import glob

base_dir = r'C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge'

# Pattern to find all Java files
java_files = glob.glob(os.path.join(base_dir, '**/*.java'), recursive=True)

print(f"Found {len(java_files)} Java files")

for file_path in java_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Fix 1: Remove import statements for UserRole and conge packages
    content = re.sub(r'import tn\.enis\.conge\..*?\n', '', content)
    
    # Fix 2: Replace UserRole type references with String
    # This must be done before enum value replacements
    content = re.sub(r'<UserRole,', '<String,', content)
    content = re.sub(r'<UserRole\s*>', '<String>', content)
    content = re.sub(r'UserRole\s+(\w+)\s*=', r'String \1 =', content)
    content = re.sub(r'UserRole\s+(\w+)\s*;', r'String \1;', content)
    content = re.sub(r'\(UserRole\s+', r'(String ', content)
    content = re.sub(r'return\s+UserRole', 'return String', content)
    
    # Fix 3: Replace enum value references with strings
    content = re.sub(r'UserRole\.EMPLOYER\b', '"EMPLOYER"', content)
    content = re.sub(r'UserRole\.TEAM_LEADER\b', '"TEAM_LEADER"', content)
    content = re.sub(r'UserRole\.ADMINISTRATION\b', '"ADMINISTRATION"', content)
    
    # Fix 4: Replace remaining UserRole references
    content = re.sub(r'UserRole\s*\.\s*Employer\b', '"EMPLOYER"', content)
    content = re.sub(r'UserRole\s*\.\s*TeamLeader\b', '"TEAM_LEADER"', content)
    content = re.sub(r'UserRole\s*\.\s*Administration\b', '"ADMINISTRATION"', content)
    
    # Fix 5: Replace bare enum values (when not qualified)
    content = re.sub(r'\bEmployer\b', '"EMPLOYER"', content)
    content = re.sub(r'\bTeamLeader\b', '"TEAM_LEADER"', content)
    content = re.sub(r'\bAdministration\b', '"ADMINISTRATION"', content)
    
    # Fix 6: Remove any remaining UserRole class references
    content = re.sub(r'<\s*UserRole\s*>', '<String>', content)
    content = re.sub(r'UserRole\s*userRole', 'String userRole', content)
    content = re.sub(r'new\s+UserRole', 'new String', content)
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Fixed: {os.path.basename(file_path)}")
    
print("\n✓ All files fixed!")
