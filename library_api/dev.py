import subprocess
import sys
from watchfiles import run_process

def start():
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--loop", "asyncio"]
    )

if __name__ == "__main__":
    run_process(".", target=start)