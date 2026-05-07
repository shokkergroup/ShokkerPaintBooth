@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\hermes_recon\status_task.ps1"
echo.
pause
