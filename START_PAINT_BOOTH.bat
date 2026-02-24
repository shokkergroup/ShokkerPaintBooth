@echo off
title Shokker Paint Booth Server
echo ========================================
echo   SHOKKER PAINT BOOTH - Starting...
echo ========================================
echo.

:: Use script's own directory (works on ANY machine)
cd /d "%~dp0"

:: Find Python — check common locations
set PYTHON=
where python >nul 2>&1 && set PYTHON=python
if not defined PYTHON (
    where python3 >nul 2>&1 && set PYTHON=python3
)
if not defined PYTHON (
    if exist "C:\Python313\python.exe" set PYTHON=C:\Python313\python.exe
)
if not defined PYTHON (
    if exist "C:\Python312\python.exe" set PYTHON=C:\Python312\python.exe
)
if not defined PYTHON (
    if exist "C:\Python311\python.exe" set PYTHON=C:\Python311\python.exe
)
if not defined PYTHON (
    echo ERROR: Python not found. Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

echo   Python: %PYTHON%
echo   Directory: %cd%
echo   Starting server...
echo ========================================

:: Start server in background, open browser after short delay
start "" %PYTHON% start_server.py
echo   Waiting for server to start...
timeout /t 3 /nobreak >nul

:: Open Paint Booth in default browser
start http://localhost:5000
echo   Browser opened. Server running in background.
echo   Close this window to stop the server.
echo ========================================
pause
