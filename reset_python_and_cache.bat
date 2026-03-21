@echo off
REM Reset Python: kill stuck processes and clear __pycache__ in this project.
REM Double-click to run, or run from CMD/PowerShell. Safe to run anytime.

echo.
echo [1/2] Stopping all Python processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM pythonw.exe 2>nul
if %errorlevel% equ 0 (echo       Some Python processes were stopped.) else (echo       No Python processes were running.)
echo.

echo [2/2] Removing __pycache__ folders in this project...
set "v5=%~dp0"
set "count=0"
for /d /r "%v5%" %%d in (__pycache__) do (
  if exist "%%d" (
    rd /s /q "%%d" 2>nul
    set /a count+=1
  )
)
echo       Done. Cleared cache.
echo.
echo Reset complete. Close this window, open a NEW terminal, then run:
echo   cd /d "%v5%"
echo   python server_v5.py
echo.
pause
