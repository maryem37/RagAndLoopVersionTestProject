#!/usr/bin/env python3
"""
Complete fix for DemandeConge compilation errors with verification
"""

import os
import re
import subprocess
import sys

def verify_file_exists(path):
    """Verify a file exists"""
    return os.path.exists(path)

def fix_user_service_employer():
    """Remove tn.enis.conge imports from UserServiceEmployer.java"""
    file_path = r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\user\UserServiceEmployer.java"
    
    if not verify_file_exists(file_path):
        return False, f"File not found: {file_path}"
    
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
            return True, "Removed conge imports"
        else:
            return True, "Already correct"
    except Exception as e:
        return False, str(e)

def fix_balance():
    """Remove tn.enis.conge import from Balance.java"""
    file_path = r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\entity\Balance.java"
    
    if not verify_file_exists(file_path):
        return False, f"File not found: {file_path}"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove the conge import
        content = re.sub(r'import tn\.enis\.conge\.entity\.*;?\n', '', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Removed conge import"
        else:
            return True, "Already correct"
    except Exception as e:
        return False, str(e)

def fix_leave_request_service_impl():
    """Replace UserRole enum references with String literals in LeaveRequestServiceImpl.java"""
    file_path = r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java"
    
    if not verify_file_exists(file_path):
        return False, f"File not found: {file_path}"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace enum references
        replacements = [
            (r'UserRole\.EMPLOYER\b', '"EMPLOYER"'),
            (r'UserRole\.TEAM_LEADER\b', '"TEAM_LEADER"'),
            (r'UserRole\.ADMINISTRATION\b', '"ADMINISTRATION"'),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Replaced UserRole enum references"
        else:
            return True, "Already correct"
    except Exception as e:
        return False, str(e)

def compile_demandeconge():
    """Compile DemandeConge microservice"""
    workdir = r"C:\Bureau\Bureau\microservices\DemandeConge"
    try:
        result = subprocess.run(
            ['mvn', 'clean', 'compile'],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

if __name__ == "__main__":
    print("=== DemandeConge Compilation Fix ===\n")
    
    fixes = [
        ("UserServiceEmployer.java", fix_user_service_employer),
        ("Balance.java", fix_balance),
        ("LeaveRequestServiceImpl.java", fix_leave_request_service_impl),
    ]
    
    all_success = True
    for name, fix_func in fixes:
        success, message = fix_func()
        status = "✓" if success else "✗"
        print(f"{status} {name}: {message}")
        if not success:
            all_success = False
    
    if all_success:
        print("\n=== Attempting Compilation ===\n")
        success, stdout, stderr = compile_demandeconge()
        
        # Write detailed output to file
        with open(r"C:\Bureau\Bureau\project_test\demandeconge_compile_result.txt", 'w') as f:
            f.write("=== Compilation Result ===\n")
            f.write(f"Success: {success}\n\n")
            f.write("=== STDOUT ===\n")
            f.write(stdout)
            f.write("\n\n=== STDERR ===\n")
            f.write(stderr)
        
        if success:
            print("✓ Compilation successful!")
            sys.exit(0)
        else:
            print("✗ Compilation failed. Details saved to demandeconge_compile_result.txt")
            # Show last 30 lines of output
            lines = (stdout + stderr).split('\n')
            print("\nLast 30 lines of compilation output:")
            for line in lines[-30:]:
                print(line)
            sys.exit(1)
    else:
        print("\n✗ File fixes failed")
        sys.exit(1)
