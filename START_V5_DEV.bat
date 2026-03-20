@echo off
REM Shokker Paint Booth V5 — DEV MODE LAUNCH
REM SHOKKER_DEV=1 enables hot reload. Every Python file save auto-restarts the server.

title Shokker V5 DEV MODE

echo ============================================================
echo   SHOKKER PAINT BOOTH V5 — DEV MODE
echo   HOT RELOAD ON: Edit any .py file and save to auto-restart
echo   Port: 59877 (dev) — use START_V5_PRIMARY or server_v5.py for port 59876
echo ============================================================

cd /d "%~dp0"
set SHOKKER_DEV=1
set SHOKKER_PORT=59877
REM Default (no env) = 59876; this bat forces 59877 for dev
python server_v5.py

pause
