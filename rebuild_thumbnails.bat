@echo off
cd /d "%~dp0"
python rebuild_thumbnails.py %*
echo.
pause
