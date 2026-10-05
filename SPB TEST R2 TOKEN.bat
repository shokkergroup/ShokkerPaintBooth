@echo off
title SPB - is my R2 token still good?
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0spb_release.ps1" -TestKey
echo.
pause
