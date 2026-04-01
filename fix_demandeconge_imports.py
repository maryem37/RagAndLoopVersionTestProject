#!/usr/bin/env python3
"""
Fix DemandeConge compilation errors by:
1. Removing tn.enis.conge package imports
2. Replacing UserRole enum references with String literals
"""

import re
import sys

def fix_user_service_employer():
    """Remove tn.enis.conge imports from UserServiceEmployer.java"""
    file_path = r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\user\UserServiceEmployer.java"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove the conge imports
        content = re.sub(r'import tn\.enis\.conge\.entity\.*;?\n', '', content)
        content = re.sub(r'import tn\.enis\.conge\.repository\.*;?\n', '', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Fixed UserServiceEmployer.java - removed conge imports")
            return True
        else:
            print(f"- UserServiceEmployer.java already correct")
            return True
    except Exception as e:
        print(f"✗ Error fixing UserServiceEmployer.java: {e}")
        return False

def fix_balance():
    """Remove tn.enis.conge import from Balance.java"""
    file_path = r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\entity\Balance.java"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove the conge import
        content = re.sub(r'import tn\.enis\.conge\.entity\.*;?\n', '', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Fixed Balance.java - removed conge import")
            return True
        else:
            print(f"- Balance.java already correct")
            return True
    except Exception as e:
        print(f"✗ Error fixing Balance.java: {e}")
        return False

def fix_leave_request_service_impl():
    """Replace UserRole enum references with String literals in LeaveRequestServiceImpl.java"""
    file_path = r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace enum references
        replacements = [
            (r'UserRole\.EMPLOYER\b', '"EMPLOYER"'),
            (r'UserRole\.TEAM_LEADER\b', '"TEAM_LEADER"'),
            (r'UserRole\.ADMINISTRATION\b', '"ADMINISTRATION"'),
            # Also handle cases where they might appear as Employer, TeamLeader, Administration
            # But be careful about method calls like getEmployer()
            (r'\bEmployer\b(?!\.|\()', '"EMPLOYER"'),
            (r'\bTeamLeader\b(?!\.|\()', '"TEAM_LEADER"'),
            (r'\bAdministration\b(?!\.|\()', '"ADMINISTRATION"'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Fixed LeaveRequestServiceImpl.java - replaced UserRole enum references")
            return True
        else:
            print(f"- LeaveRequestServiceImpl.java already correct")
            return True
    except Exception as e:
        print(f"✗ Error fixing LeaveRequestServiceImpl.java: {e}")
        return False

if __name__ == "__main__":
    print("Fixing DemandeConge compilation errors...\n")
    
    results = [
        fix_user_service_employer(),
        fix_balance(),
        fix_leave_request_service_impl(),
    ]
    
    if all(results):
        print("\n✓ All fixes applied successfully")
        sys.exit(0)
    else:
        print("\n✗ Some fixes failed")
        sys.exit(1)
