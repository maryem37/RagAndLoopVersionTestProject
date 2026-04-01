#!/usr/bin/env python3
"""
Comprehensive fix script for DemandeConge microservice
Writes all output to file to work around terminal issues
"""

import os
import re
import subprocess
import sys
from pathlib import Path

def main():
    output_lines = []
    
    # Define file paths
    files_to_fix = {
        "UserServiceEmployer.java": r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\user\UserServiceEmployer.java",
        "Balance.java": r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\entity\Balance.java",
        "LeaveRequestServiceImpl.java": r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java",
    }
    
    output_lines.append("=== DemandeConge Compilation Fix ===\n")
    
    # Check which files exist
    output_lines.append("Checking for files...")
    existing_files = {}
    for name, path in files_to_fix.items():
        exists = os.path.exists(path)
        output_lines.append(f"{name}: {'FOUND' if exists else 'NOT FOUND at ' + path}")
        if exists:
            existing_files[name] = path
    
    if not existing_files:
        output_lines.append("\n✗ FAILURE: None of the target files found!")
        output_lines.append("Searching for files in microservices directory...")
        
        # Try to find them
        try:
            for root, dirs, files in os.walk(r"C:\Bureau\Bureau\microservices"):
                for file in files:
                    if file in files_to_fix.keys():
                        full_path = os.path.join(root, file)
                        output_lines.append(f"  Found: {full_path}")
                # Limit depth
                if root.count(os.sep) - r"C:\Bureau\Bureau\microservices".count(os.sep) > 5:
                    del dirs[:]
        except Exception as e:
            output_lines.append(f"  Search error: {e}")
        
        # Write output and exit
        output_file = r"C:\Bureau\Bureau\project_test\demandeconge_fix_results.txt"
        with open(output_file, 'w') as f:
            f.write('\n'.join(output_lines))
        return 1
    
    output_lines.append(f"\nFound {len(existing_files)} files to fix\n")
    
    # Fix UserServiceEmployer.java
    if "UserServiceEmployer.java" in existing_files:
        output_lines.append("--- Fixing UserServiceEmployer.java ---")
        try:
            path = existing_files["UserServiceEmployer.java"]
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            # Remove conge imports
            content = re.sub(r'import tn\.enis\.conge\.entity\.*;?\n', '', content)
            content = re.sub(r'import tn\.enis\.conge\.repository\.*;?\n', '', content)
            
            if content != original:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                output_lines.append("✓ Removed conge imports")
            else:
                output_lines.append("- No changes needed")
        except Exception as e:
            output_lines.append(f"✗ Error: {e}")
    
    # Fix Balance.java
    if "Balance.java" in existing_files:
        output_lines.append("--- Fixing Balance.java ---")
        try:
            path = existing_files["Balance.java"]
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            # Remove conge import
            content = re.sub(r'import tn\.enis\.conge\.entity\.*;?\n', '', content)
            
            if content != original:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                output_lines.append("✓ Removed conge import")
            else:
                output_lines.append("- No changes needed")
        except Exception as e:
            output_lines.append(f"✗ Error: {e}")
    
    # Fix LeaveRequestServiceImpl.java
    if "LeaveRequestServiceImpl.java" in existing_files:
        output_lines.append("--- Fixing LeaveRequestServiceImpl.java ---")
        try:
            path = existing_files["LeaveRequestServiceImpl.java"]
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original = content
            # Replace UserRole enum references
            replacements = [
                (r'UserRole\.EMPLOYER\b', '"EMPLOYER"'),
                (r'UserRole\.TEAM_LEADER\b', '"TEAM_LEADER"'),
                (r'UserRole\.ADMINISTRATION\b', '"ADMINISTRATION"'),
            ]
            
            for pattern, replacement in replacements:
                content = re.sub(pattern, replacement, content)
            
            if content != original:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                output_lines.append("✓ Replaced UserRole enum references")
            else:
                output_lines.append("- No changes needed")
        except Exception as e:
            output_lines.append(f"✗ Error: {e}")
    
    # Try compilation
    output_lines.append("\n--- Running Compilation ---")
    try:
        workdir = r"C:\Bureau\Bureau\microservices\DemandeConge"
        output_lines.append(f"Working directory: {workdir}")
        
        if os.path.exists(workdir):
            result = subprocess.run(
                ['mvn', 'clean', 'compile'],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                output_lines.append("✓ Compilation SUCCESSFUL!")
            else:
                output_lines.append("✗ Compilation FAILED")
                output_lines.append("\n--- Last 50 lines of output ---")
                all_output = result.stdout + result.stderr
                lines = all_output.split('\n')
                output_lines.extend(lines[-50:])
        else:
            output_lines.append(f"✗ Work directory not found: {workdir}")
    except subprocess.TimeoutExpired:
        output_lines.append("✗ Compilation timed out after 300 seconds")
    except Exception as e:
        output_lines.append(f"✗ Compilation error: {e}")
    
    # Write final output
    output_file = r"C:\Bureau\Bureau\project_test\demandeconge_fix_results.txt"
    with open(output_file, 'w') as f:
        f.write('\n'.join(output_lines))
    
    print(f"Results written to: {output_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
