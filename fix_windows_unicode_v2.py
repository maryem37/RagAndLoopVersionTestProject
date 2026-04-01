#!/usr/bin/env python3
"""
Windows Console Encoding Fix - Comprehensive Solution v2

This script removes problematic Unicode characters from all Python files.
It processes the source code to replace Unicode with ASCII equivalents.

Usage:
  python fix_windows_unicode_v2.py
"""

import sys
import re
from pathlib import Path

def remove_box_drawing_lines(content):
    """
    Remove box drawing lines that cause rendering issues on Windows.
    Replace them with simple ASCII lines.
    """
    # Replace various box drawing sequences with simple lines
    patterns = {
        # Box drawing lines
        r'[═]{3,}': '=' * 30,
        r'[─]{3,}': '-' * 30,
        r'[\║]{1,}': '|',
        r'[║]{1,}': '|',
        # Unicode line patterns
        r'[Ôö]+[Ç]+': '=',
        r'ÔöÇ': '=',
        r'Ô£': '[',
        r'Ôù': ']',
        r'Ô£ô': '[OK]',
        r'Ô£ù': '[FAIL]',
        r'ƒôä': '[FILE]',
        r'ƒôè': '[CHART]',
        r'ƒôü': '[FOLDER]',
        r'ƒôï': '[LIST]',
        r'Ô£à': '[DONE]',
        r'ÔØî': '[ERROR]',
        r'ÔåÆ': '->',
    }
    
    for pattern, replacement in patterns.items():
        content = re.sub(pattern, replacement, content)
    
    return content

def clean_file(filepath):
    """Remove problematic Unicode from file"""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        original = content
        
        # Remove box drawing lines
        content = remove_box_drawing_lines(content)
        
        # Basic Unicode replacement
        basic_replacements = {
            '✓': '[OK]',
            '✗': '[FAIL]',
            '✔': '[OK]',
            '❌': '[ERROR]',
            '⚠': '[WARN]',
            '📋': '[LIST]',
            '🚀': '[START]',
            '🔍': '[DEBUG]',
            '📊': '[CHART]',
            '📈': '[TREND]',
            '💾': '[SAVE]',
            '📁': '[FILE]',
            '📂': '[FOLDER]',
            '→': '->',
            '▶': '->',
        }
        
        for uni_char, ascii_char in basic_replacements.items():
            content = content.replace(uni_char, ascii_char)
        
        if content != original:
            filepath.write_text(content, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"Error: {filepath}: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("Windows Console Unicode Fix v2")
    print("="*80)
    
    project_root = Path(__file__).parent
    python_files = list(project_root.glob("agents/*.py")) + \
                   list(project_root.glob("graph/*.py")) + \
                   list(project_root.glob("config/*.py")) + \
                   list(project_root.glob("tools/*.py"))
    
    fixed_count = 0
    for py_file in python_files:
        if clean_file(py_file):
            print(f"[FIXED] {py_file.relative_to(project_root)}")
            fixed_count += 1
    
    print(f"\n[OK] Fixed {fixed_count} files")
    print("="*80 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
