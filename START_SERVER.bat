@echo off
title Shokker Paint Booth V5 Server

echo ============================================================
echo   SHOKKER PAINT BOOTH V5 — LIVE SERVER
echo   Double-click to run! Keeping terminal open to read errors.
echo ============================================================

cd /d "%~dp0"
echo [Startup] Stopping any existing SPB server processes from this folder...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $root=(Resolve-Path '.').Path; $rootRe=[regex]::Escape($root); $targets=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'python' -and $_.CommandLine -match 'server(_v5)?\.py' -and $_.CommandLine -match $rootRe }; foreach ($p in $targets) { Write-Host ('[Startup] Stopping SPB server PID ' + $p.ProcessId + ' from this folder'); Stop-Process -Id $p.ProcessId -Force }; $cons=Get-NetTCPConnection -LocalPort 59876 -State Listen; foreach ($c in $cons) { $p=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $c.OwningProcess); if ($p -and $p.CommandLine -match 'server(_v5)?\.py') { Write-Host ('[Startup] Stopping stale SPB listener PID ' + $p.ProcessId + ' on port 59876'); Stop-Process -Id $p.ProcessId -Force } elseif ($p) { Write-Host ('[Startup] Port 59876 is owned by non-SPB process PID ' + $p.ProcessId + ': ' + $p.Name) } }"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $ports=@(59876,59877,59878,59879,60876,60877,60878,60879,61876,62876); foreach ($port in $ports) { $cons=Get-NetTCPConnection -LocalPort $port -State Listen; foreach ($c in $cons) { $p=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $c.OwningProcess); if ($p -and ($p.CommandLine -match 'server(_v5)?\.py' -or $p.CommandLine -match 'paint-booth|pyserver|Shokker Paint Booth')) { Write-Host ('[Startup] Stopping stale SPB listener PID ' + $p.ProcessId + ' on port ' + $port); Stop-Process -Id $p.ProcessId -Force } } }"

set SHOKKER_PORT=59876

:: Use Python 3.13 for GPU acceleration (CuPy requires 3.13+)
:: Falls back to system python if 3.13 not found
if exist "C:\Python313\python.exe" (
    C:\Python313\python.exe server_v5.py
) else (
    python server_v5.py
)

echo.
echo Server has closed, hit an error, or the port was already in use!
pause
