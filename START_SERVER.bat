@echo off
title Shokker Paint Booth V5 Server

echo ============================================================
echo   SHOKKER PAINT BOOTH V5 — LIVE SERVER
echo   Double-click to run! Keeping terminal open to read errors.
echo ============================================================

cd /d "%~dp0"
python server_v5.py

echo.
echo Server has closed, hit an error, or the port was already in use!
pause
