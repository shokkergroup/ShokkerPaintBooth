@echo off
setlocal
cd /d "%~dp0"

echo.
echo Shokker Paint Booth - root temp junk cleanup
echo ============================================
echo This deletes only the known accidental root junk signature:
echo   - extensionless 8-character random-looking filename
echo   - exactly 4 bytes
echo   - content exactly "blat"
echo.
echo Preview:
python scripts\cleanup-root-temp-junk.py --dry-run
echo.

choice /C YN /N /M "Delete these matching files? [Y/N] "
if errorlevel 2 (
  echo.
  echo Cleanup cancelled.
  pause
  exit /b 0
)

echo.
python scripts\cleanup-root-temp-junk.py --delete

echo.
pause
