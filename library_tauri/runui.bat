@echo off

echo Checking backend...

powershell -Command "try { Invoke-WebRequest http://127.0.0.1:8000/docs -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }"

if %errorlevel%==0 (
    echo Backend already running
) else (
    echo Starting backend...
    start /b "" D:\Athenaeum_Project\library_api\venv312\Scripts\python.exe D:\Athenaeum_Project\library_api\start_backend.py
)

echo Starting frontend...

cd /d D:\Athenaeum_Project\library_tauri
npm run tauri:dev