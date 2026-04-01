#!/usr/bin/env python3
import os

files_to_check = [
    r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\user\UserServiceEmployer.java",
    r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\entity\Balance.java",
    r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java",
]

for f in files_to_check:
    exists = os.path.exists(f)
    print(f"{f}: {exists}")
    if exists:
        size = os.path.getsize(f)
        print(f"  Size: {size} bytes")
