@echo off
setlocal
echo Stopping HERMES Recon scheduled task...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\hermes_recon\unregister_task.ps1"
echo.
pause
