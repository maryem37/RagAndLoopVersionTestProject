#!/usr/bin/env python3
"""
Windows Console Encoding Fix - Comprehensive Solution

This script strips Unicode characters from all Python files in the project
that use loguru, making them Windows-compatible.

Usage:
  python fix_windows_unicode.py
"""

import sys
import re
from pathlib import Path

# Unicode characters and their ASCII replacements
UNICODE_REPLACEMENTS = {
    '✓': '[OK]',
    '✗': '[FAIL]',
    '✔': '[OK]',
    '✗': '[FAIL]',
    '❌': '[ERROR]',
    '⚠': '[WARN]',
    '📋': '[LIST]',
    '🚀': '[START]',
    '🔍': '[DEBUG]',
    '📊': '[CHART]',
    '📈': '[TREND]',
    '💾': '[SAVE]',
    '📁': '[FILE]',
    '→': '->',
    '▶': '->',
    '█': '#',
    '═': '=',
    '║': '|',
    '╔': '+',
    '╚': '+',
    '╝': '+',
    '╗': '+',
}

def clean_unicode_from_file(filepath):
    """Remove unicode characters from a file"""
    try:
        content = filepath.read_text(encoding='utf-8')
        original_length = len(content)
        
        # Replace unicode characters
        for unicode_char, ascii_char in UNICODE_REPLACEMENTS.items():
            content = content.replace(unicode_char, ascii_char)
        
        if len(content) != original_length:
            filepath.write_text(content, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("Windows Console Unicode Fix")
    print("="*80)
    
    project_root = Path(__file__).parent
    python_files = list(project_root.glob("agents/*.py")) + \
                   list(project_root.glob("graph/*.py")) + \
                   list(project_root.glob("config/*.py"))
    
    fixed_count = 0
    for py_file in python_files:
        if clean_unicode_from_file(py_file):
            print(f"[FIXED] {py_file.relative_to(project_root)}")
            fixed_count += 1
    
    print(f"\n[OK] Fixed {fixed_count} files")
    print("="*80 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
