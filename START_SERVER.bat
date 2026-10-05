@echo off
setlocal
title Shokker Paint Booth Server Control

cd /d "%~dp0"

echo ============================================================
echo   SHOKKER PAINT BOOTH - SUPERVISED BACKEND
echo ============================================================
echo   Action: start or confirm the managed backend
echo   This window stays open and shows LIVE server + restart logs.
echo   Closing this window detaches logs only; the backend keeps running.
echo   Unexpected exits restart automatically.
echo.
echo   Manual stop: SPB_STOP_SERVER.bat
echo   Clean refresh: SPB_REFRESH_SERVER.bat
echo   Status:        SPB_SERVER_STATUS.bat
echo   Logs only:     SPB_SERVER_LOGS.bat
echo ============================================================
echo.

set "SPB_PYTHON=C:\Python313\python.exe"
if not exist "%SPB_PYTHON%" set "SPB_PYTHON=python"
set PYTHONHASHSEED=0
set SPB_NO_BOOT_SWATCH_WARM=1

"%SPB_PYTHON%" "%~dp0spb_server_supervisor.py" start --follow
set "SPB_RC=%ERRORLEVEL%"

if not "%SPB_RC%"=="0" (
    echo.
    echo [ERROR] SPB server control failed with exit code %SPB_RC%.
    echo         See .spb_supervisor\lifecycle.log for details.
    echo.
    pause
)

endlocal & exit /b %SPB_RC%
