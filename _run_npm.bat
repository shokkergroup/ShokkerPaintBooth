@echo off
set "PATH=C:\Program Files\nodejs;C:\Windows\system32;%PATH%"
cd /d "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\electron-app"
echo Current dir: %CD%
echo Node version:
node --version
echo NPM version:
npm --version
echo.
echo Running npm install...
npm install --include=dev 2>&1
echo.
echo Exit code: %ERRORLEVEL%
echo.
echo Checking key files...
if exist "node_modules\electron\cli.js" (echo electron/cli.js: EXISTS) else (echo electron/cli.js: MISSING)
if exist "node_modules\electron\dist\electron.exe" (echo electron/dist/electron.exe: EXISTS) else (echo electron/dist/electron.exe: MISSING)
if exist "node_modules\electron-builder\out\cli\cli.js" (echo electron-builder cli.js: EXISTS) else (echo electron-builder cli.js: MISSING)
