import os
import subprocess

# Use tasklist/taskkill on Windows or pkill on Linux/Mac to find and stop uvicorn
cmd = ["pkill", "-9", "-f", "uvicorn"] if os.name != "nt" else ["taskkill", "/F", "/IM", "python.exe", "/T"]
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0:
    print("All uvicorn/python processes terminated")

else:
    print(f"Command failed with exit code {result.returncode}")
    if result.stderr:
        print(f"error: {result.stderr}")
