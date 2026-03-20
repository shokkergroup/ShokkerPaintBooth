@echo off
REM ============================================================
REM  GLOBAL: Kill ALL Python processes anywhere on the system
REM  Use when Python is stuck, crashing, or won't start anywhere.
REM  Safe to run anytime. Run as Administrator if some PIDs resist.
REM ============================================================

echo.
echo Killing ALL Python processes system-wide...
echo.

taskkill /F /IM python.exe   2>nul
taskkill /F /IM pythonw.exe  2>nul
taskkill /F /IM python3.exe  2>nul

echo.
echo Done. All python.exe / pythonw.exe / python3.exe have been stopped.
echo Open a NEW terminal before starting any Python app again.
echo.
pause
