@echo off
setlocal
cd /d "%~dp0electron-app"

if exist "node_modules\.bin\electron.cmd" (
  call "node_modules\.bin\electron.cmd" . --open-finish-viewer
) else (
  npm start -- --open-finish-viewer
)
