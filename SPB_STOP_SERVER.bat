@echo off
setlocal
title SPB Server Stop

cd /d "%~dp0"
set "SPB_PYTHON=C:\Python313\python.exe"
if not exist "%SPB_PYTHON%" set "SPB_PYTHON=python"

echo Stopping the supervised SPB backend and setting manual-stop state...
"%SPB_PYTHON%" "%~dp0spb_server_supervisor.py" stop
set "SPB_RC=%ERRORLEVEL%"

if not "%SPB_RC%"=="0" (
    echo.
    echo [ERROR] SPB stop failed with exit code %SPB_RC%.
    echo         See .spb_supervisor\lifecycle.log for details.
    pause
)

endlocal & exit /b %SPB_RC%
