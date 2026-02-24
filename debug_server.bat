@echo off
echo === Running shokker-server.exe directly to capture crash output ===
echo.
set SHOKKER_PORT=59876
"C:\Users\Ricky's PC\AppData\Local\Programs\shokker-paint-booth\resources\server\shokker-server.exe" 2>&1
echo.
echo === Exit code: %errorlevel% ===
echo.
pause