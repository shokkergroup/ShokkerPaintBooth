@echo off
setlocal
echo Installing HERMES Recon as a 15-minute Windows scheduled task...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\hermes_recon\register_task.ps1"
echo.
echo HERMES Recon is now scheduled.
echo New briefs will appear in codex_recon_inbox every 15 minutes.
echo Use STOP_HERMES_RECON.bat when you want it to stop.
echo.
pause
