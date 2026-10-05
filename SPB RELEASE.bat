@echo off
title SPB RELEASE - build, stage, test, go live
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0spb_release.ps1" %*
echo.
echo (You can close this window now.)
pause
