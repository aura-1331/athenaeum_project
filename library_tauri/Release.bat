@echo off
title Athenaeum Release
cd /d "%~dp0"

echo.
echo ========================================
echo        ATHENAEUM RELEASE
echo ========================================
echo.
echo  [1] Patch
echo  [2] Minor
echo  [3] Major
echo  [Q] Cancel
echo.

choice /C 123Q /N /M "Select release type: "

if errorlevel 4 exit /b
if errorlevel 3 npm run release:major
if errorlevel 2 npm run release:minor
if errorlevel 1 npm run release:patch

echo.
pause
