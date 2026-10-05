@echo off
setlocal
title SPB Live Server Logs

cd /d "%~dp0"
set "SPB_PYTHON=C:\Python313\python.exe"
if not exist "%SPB_PYTHON%" set "SPB_PYTHON=python"

"%SPB_PYTHON%" -u "%~dp0spb_server_supervisor.py" logs
set "SPB_RC=%ERRORLEVEL%"

if not "%SPB_RC%"=="0" (
    echo.
    echo [ERROR] SPB log viewer failed with exit code %SPB_RC%.
    pause
)

endlocal & exit /b %SPB_RC%
