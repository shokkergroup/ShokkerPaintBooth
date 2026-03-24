@echo off
title Shokker Paint Booth V5 Server

echo ============================================================
echo   SHOKKER PAINT BOOTH V5 — LIVE SERVER
echo   Double-click to run! Keeping terminal open to read errors.
echo ============================================================

cd /d "%~dp0"
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
