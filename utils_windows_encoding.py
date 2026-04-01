"""
Windows Console UTF-8 Encoding Fix

This module ensures that the Python environment uses UTF-8 encoding
for console output on Windows, preventing UnicodeEncodeError when
loguru tries to print emoji characters.
"""

import sys
import os


def fix_windows_utf8_encoding():
    """
    Fix Windows console encoding to support UTF-8 output.
    Call this at the very start of your script before any logging.
    """
    if sys.platform == "win32":
        try:
            # For Python 3.7+ on Windows
            import ctypes
            import msvcrt
            
            # Enable UTF-8 mode
            os.environ["PYTHONIOENCODING"] = "utf-8"
            
            # Force UTF-8 for stdout and stderr
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            
            return True
        except Exception as e:
            # Fallback: at least set the environment variable
            os.environ["PYTHONIOENCODING"] = "utf-8"
            return False
    return None


if __name__ == "__main__":
    fix_windows_utf8_encoding()
    print("UTF-8 encoding configured for Windows console")
