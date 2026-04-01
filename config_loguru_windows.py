"""
Loguru Windows UTF-8 Configuration

Configures loguru to properly handle UTF-8 on Windows without emoji/unicode errors.
This removes the problematic emoji characters from log output on Windows.
"""

import sys
import os
from loguru import logger

# Remove default handler
logger.remove()

def configure_logger_for_windows():
    """
    Configure loguru to work properly on Windows.
    Removes emoji characters and uses plain ASCII-compatible output.
    """
    if sys.platform == "win32":
        # Use a format without emoji and with ASCII-only characters
        log_format = (
            "<level>{level: <8}</level> | "
            "{name:30} | "
            "{message}"
        )
    else:
        # On Unix/Linux, use the nice format with emoji
        log_format = (
            "<level>{level: <8}</level> | "
            "<cyan>{name:30}</cyan> | "
            "<level>{message}</level>"
        )
    
    logger.add(
        sys.stderr,
        format=log_format,
        level="INFO",
        colorize=sys.platform != "win32",
        backtrace=True,
        diagnose=True,
    )
    
    return logger


if __name__ == "__main__":
    logger = configure_logger_for_windows()
    logger.info("Logger configured for Windows")
    logger.success("This is a success message")
    logger.warning("This is a warning message")
