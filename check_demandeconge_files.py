import os
import re
import subprocess

# Define file paths
files_info = {
    "UserServiceEmployer.java": r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\user\UserServiceEmployer.java",
    "Balance.java": r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\entity\Balance.java",
    "LeaveRequestServiceImpl.java": r"C:\Bureau\Bureau\microservices\DemandeConge\src\main\java\tn\enis\DemandeConge\service\LeaveRequest\LeaveRequestServiceImpl.java",
}

# Check which files exist
results = []
for name, path in files_info.items():
    exists = os.path.exists(path)
    results.append(f"{name}: {'EXISTS' if exists else 'NOT FOUND'}")

# Write results to file
output_file = r"C:\Bureau\Bureau\project_test\file_check_results.txt"
with open(output_file, 'w') as f:
    for line in results:
        f.write(line + '\n')

# Try to find these files
search_results = []
try:
    for root, dirs, files in os.walk(r"C:\Bureau\Bureau\microservices"):
        for file in files:
            if file in ["UserServiceEmployer.java", "Balance.java", "LeaveRequestServiceImpl.java"]:
                search_results.append(os.path.join(root, file))
        # Limit depth
        if root.count(os.sep) - r"C:\Bureau\Bureau\microservices".count(os.sep) > 6:
            del dirs[:]
except Exception as e:
    search_results.append(f"Error during search: {e}")

with open(output_file, 'a') as f:
    f.write('\n=== Search Results ===\n')
    for line in search_results:
        f.write(line + '\n')

print("Results written to:", output_file)
