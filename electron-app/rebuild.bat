@echo off
setlocal
set "PATH=C:\Program Files\nodejs;C:\Program Files\nodejs\node_modules\npm\bin;%USERPROFILE%\AppData\Roaming\npm;%PATH%"
cd /d "%~dp0"
echo Current dir: %CD% > rebuild_log.txt 2>&1
echo Node version: >> rebuild_log.txt 2>&1
node --version >> rebuild_log.txt 2>&1
echo NPM version: >> rebuild_log.txt 2>&1
npm --version >> rebuild_log.txt 2>&1
echo. >> rebuild_log.txt 2>&1
echo === Running copy-server === >> rebuild_log.txt 2>&1
call node copy-server-assets.js >> rebuild_log.txt 2>&1
echo copy-server exit: %errorlevel% >> rebuild_log.txt 2>&1
echo. >> rebuild_log.txt 2>&1
echo === Running electron-builder === >> rebuild_log.txt 2>&1
call npx electron-builder --win --x64 >> rebuild_log.txt 2>&1
echo builder exit: %errorlevel% >> rebuild_log.txt 2>&1
endlocal
