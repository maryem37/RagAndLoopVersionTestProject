#!/usr/bin/env python3
"""
Dump JaCoCo coverage data from running microservices.

This script attempts to extract JaCoCo coverage from running Java services
by making HTTP requests to potential JaCoCo endpoints.
"""

import requests
import subprocess
from pathlib import Path
import sys

def dump_coverage(service_name: str, port: int, output_file: str):
    """Try to dump coverage from a running service."""
    
    # Common JaCoCo endpoints
    endpoints = [
        f"http://localhost:{port}/jacoco-api/dump",
        f"http://localhost:{port}/api/coverage/dump",
        f"http://localhost:{port}/coverage/exec",
        f"http://localhost:{port}/.jacoco",
    ]
    
    for endpoint in endpoints:
        print(f"  Trying {endpoint}...")
        try:
            response = requests.get(endpoint, timeout=2)
            if response.status_code == 200 and response.content:
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Successfully dumped coverage to {output_file}")
                return True
        except Exception as e:
            print(f"    Failed: {e}")
    
    return False

def main():
    # Try to dump coverage from running services
    print("Attempting to dump JaCoCo coverage from running services...")
    
    auth_dumped = dump_coverage("Auth", 9000, "output/jacoco/auth_fresh.exec")
    leave_dumped = dump_coverage("Leave", 9001, "output/jacoco/leave_fresh.exec")
    
    if not auth_dumped and not leave_dumped:
        print("\n❌ Could not dump coverage from services.")
        print("\nThe services are running but don't expose JaCoCo dump endpoints.")
        print("\nTo enable coverage collection, restart services with JaCoCo agent:")
        print("""
  java -javaagent:/path/to/jacocoagent.jar=destfile=output/jacoco/auth.exec \\
       -jar auth-service.jar
        """)
        return 1
    
    print("\n✅ Coverage dump successful!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
