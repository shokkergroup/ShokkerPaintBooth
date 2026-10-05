@echo off
setlocal
title SPB Server Status

cd /d "%~dp0"
set "SPB_PYTHON=C:\Python313\python.exe"
if not exist "%SPB_PYTHON%" set "SPB_PYTHON=python"

"%SPB_PYTHON%" "%~dp0spb_server_supervisor.py" status
set "SPB_RC=%ERRORLEVEL%"
echo.
pause

endlocal & exit /b %SPB_RC%
