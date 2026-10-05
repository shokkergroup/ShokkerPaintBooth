@echo off
setlocal
title SPB Server Refresh

cd /d "%~dp0"
set "SPB_PYTHON=C:\Python313\python.exe"
if not exist "%SPB_PYTHON%" set "SPB_PYTHON=python"

echo Refreshing SPB. This window will remain open with live logs.
echo Closing it later detaches the viewer only; the server keeps running.
echo.

"%SPB_PYTHON%" -u "%~dp0spb_server_supervisor.py" refresh --follow
set "SPB_RC=%ERRORLEVEL%"

if not "%SPB_RC%"=="0" (
    echo.
    echo [ERROR] SPB refresh failed with exit code %SPB_RC%.
    echo         See .spb_supervisor\lifecycle.log for details.
    echo.
    pause
)

endlocal & exit /b %SPB_RC%
