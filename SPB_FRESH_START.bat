@echo off
setlocal
title SPB Fresh Start

cd /d "%~dp0"

echo ============================================================
echo   SPB FRESH START
echo   Refresh the managed backend, or start it if it is stopped.
echo   This window remains open with LIVE server + restart logs.
echo   Closing it detaches logs only; SPB keeps running in the background.
echo ============================================================
echo.

set "SPB_PYTHON=C:\Python313\python.exe"
if not exist "%SPB_PYTHON%" set "SPB_PYTHON=python"

echo [Launcher] Running canonical file: %~f0
echo [Launcher] Opening live server and automatic-restart output...
echo.

"%SPB_PYTHON%" -u "%~dp0spb_server_supervisor.py" refresh --follow
set "SPB_RC=%ERRORLEVEL%"

if not "%SPB_RC%"=="0" (
    echo.
    echo [ERROR] SPB fresh start failed with exit code %SPB_RC%.
    echo         See .spb_supervisor\lifecycle.log for details.
    echo.
    pause
)

endlocal & exit /b %SPB_RC%
