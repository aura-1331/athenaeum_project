import subprocess
import time
import requests # type: ignore
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEV_PATH = os.path.join(BASE_DIR, "dev.py")

print("Launching backend...")

proc = subprocess.Popen(
    [sys.executable, DEV_PATH],
    cwd=BASE_DIR
)

# wait until backend is ready
for i in range(20):
    try:
        requests.get("http://127.0.0.1:8000/docs")
        print("Backend ready")
        break
    except Exception:
        time.sleep(0.5)
else:
    print("Backend failed to start")