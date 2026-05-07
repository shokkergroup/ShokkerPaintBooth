@echo off
setlocal
title SPB Fresh Start

cd /d "%~dp0"

echo ============================================================
echo   SPB FRESH START
echo   Force-kill stale SPB processes, then start clean.
echo ============================================================
echo.
echo [1/3] Killing SPB/Electron/pyserver processes from this repo...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='SilentlyContinue';" ^
  "$root=(Resolve-Path '.').Path;" ^
  "$rootRe=[regex]::Escape($root);" ^
  "$spbRe='server_v5\.py|server\.py|paint-booth-v2\.html|paint-booth-5-api-render\.js|pyserver|Shokker Paint Booth|SPB';" ^
  "$candidates=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and (($_.CommandLine -match $rootRe) -or ($_.CommandLine -match $spbRe)) -and ($_.Name -match 'python|node|electron') };" ^
  "foreach ($p in $candidates) { Write-Host ('[Kill] PID ' + $p.ProcessId + ' :: ' + $p.Name); Stop-Process -Id $p.ProcessId -Force };" ^
  "$ports=@(59876,59877,59878,59879,60876,60877,60878,60879,61876,62876);" ^
  "foreach ($port in $ports) {" ^
  "  $cons=Get-NetTCPConnection -LocalPort $port -State Listen;" ^
  "  foreach ($c in $cons) {" ^
  "    try {" ^
  "      $pp=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $c.OwningProcess);" ^
  "      if ($pp) {" ^
  "        if ($pp.CommandLine -match $rootRe -or $pp.CommandLine -match 'server_v5\.py|server\.py|pyserver|paint-booth') {" ^
  "          Write-Host ('[Kill] Port ' + $port + ' listener PID ' + $pp.ProcessId);" ^
  "          Stop-Process -Id $pp.ProcessId -Force" ^
  "        } else {" ^
  "          Write-Host ('[Info] Port ' + $port + ' owned by non-SPB process PID ' + $pp.ProcessId + ' (' + $pp.Name + ')')" ^
  "        }" ^
  "      }" ^
  "    } catch {}" ^
  "  }" ^
  "}"

echo [2/3] Clearing stale local lock/pid markers...
if exist "scripts\.runtime-sync.lock" del /f /q "scripts\.runtime-sync.lock" >nul 2>&1
if exist "electron-app\server\.runtime-sync.lock" del /f /q "electron-app\server\.runtime-sync.lock" >nul 2>&1
if exist ".spb_server.pid" del /f /q ".spb_server.pid" >nul 2>&1
if exist "electron-app\server\.spb_server.pid" del /f /q "electron-app\server\.spb_server.pid" >nul 2>&1

echo [3/3] Starting SPB server clean...
call "%~dp0START_SERVER.bat"

endlocal
