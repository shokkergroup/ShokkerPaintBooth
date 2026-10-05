@echo off
setlocal
title SPB Server (temporary port 60876)

cd /d "%~dp0"

echo ============================================================
echo   SPB SERVER  -  TEMPORARY PORT 60876
echo ============================================================
echo.
echo   Why this file exists:
echo     Windows' Hyper-V stack (Docker Desktop / WSL / BlueStacks)
echo     reserved the block 59813-59912 this boot, which swallowed
echo     the usual port 59876. Nothing is listening there - Windows
echo     just refuses the bind, so killing SPB processes cannot help.
echo.
echo   Use this until the permanent fix is applied:
echo     1. Admin PowerShell:
echo          netsh int ipv4 set dynamicport tcp start=49152 num=10000
echo     2. Reboot
echo     3. Admin PowerShell:
echo          netsh int ipv4 add excludedportrange protocol=tcp startport=59876 numberofports=1 store=persistent
echo     After that, go back to SPB_FRESH_START.bat and 59876 is yours for good.
echo.
echo ------------------------------------------------------------
echo   OPEN THE APP AT:   http://localhost:60876/
echo   Leave this window OPEN while you paint.
echo ------------------------------------------------------------
echo.

echo [1/2] Clearing any stale SPB python from this folder...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='SilentlyContinue';" ^
  "$root=(Resolve-Path '.').Path; $rootRe=[regex]::Escape($root);" ^
  "$t=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'python' -and $_.CommandLine -match 'server(_v5)?\.py' -and $_.CommandLine -match $rootRe -and $_.CommandLine -notmatch 'review_server\.py' };" ^
  "foreach ($p in $t) { Write-Host ('  stopping PID ' + $p.ProcessId); & taskkill.exe /F /T /PID $($p.ProcessId) | Out-Null }"

echo [2/2] Starting server on 60876...
echo.

set SHOKKER_PORT=60876
set PYTHONHASHSEED=0
set SPB_NO_BOOT_SWATCH_WARM=1

if exist "C:\Python313\python.exe" (
    C:\Python313\python.exe server_v5.py
) else (
    python server_v5.py
)

echo.
if errorlevel 1 (
    echo [ERROR] Server exited with an error. Scroll up for the traceback.
    echo         If it says WinError 10013, Hyper-V took 60876 too -
    echo         SPB will now auto-fall-back; check the port it printed above.
) else (
    echo [INFO] Server stopped.
)
pause
