@echo off
echo ============================================
echo   SHOKKER CLEAN START - Nuclear Reset
echo ============================================

echo.
echo [1/4] Killing ALL Python processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM pythonw.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2/4] Clearing __pycache__...
if exist "__pycache__" rmdir /s /q "__pycache__"

echo [3/4] Clearing stale ORIGINAL_ backups from iRacing paint folders...
for /r "%USERPROFILE%\Documents\iRacing\paint" %%f in (ORIGINAL_*) do (
    echo   Deleting: %%f
    del /f "%%f" 2>nul
)

echo [4/4] Starting fresh server...
echo.
echo ============================================
echo   SERVER IS RUNNING ON http://localhost:5000
echo   Output goes to server_log.txt
echo   DO NOT CLOSE THIS WINDOW
echo   Press Ctrl+C to stop the server
echo ============================================
echo.
echo Open your browser to: http://localhost:5000
echo.
start http://localhost:5000
python start_server.py
pause
