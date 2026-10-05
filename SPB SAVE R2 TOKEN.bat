@echo off
title SPB - store R2 token (one time)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0spb_release.ps1" -SaveKey
echo.
pause
