@echo off
setlocal
cd /d "%~dp0"

echo.
echo Shokker Paint Booth - root temp junk preview
echo ============================================
echo This lists only the known accidental root junk signature:
echo   - extensionless 8-character random-looking filename
echo   - exactly 4 bytes
echo   - content exactly "blat"
echo.

python scripts\cleanup-root-temp-junk.py --dry-run

echo.
pause
