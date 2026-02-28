@echo off
echo === 1. Building PyInstaller ===
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__
py -3.11 -m PyInstaller shokker-server-ag.spec --clean --noconfirm > build_log.txt 2>&1
if errorlevel 1 goto error

echo === 2. Copying Backend ===
copy /Y dist\shokker-paint-booth-ag.exe electron-app\server\shokker-paint-booth-ag.exe
if errorlevel 1 goto error

echo === 3. Building Electron App ===
taskkill /F /IM "Shokker Paint Booth AG.exe" /T >nul 2>&1
taskkill /F /IM "shokker-paint-booth-ag.exe" /T >nul 2>&1
cd electron-app
call npm run build > npm_build_log.txt 2>&1
if errorlevel 1 goto error

echo === 4. Finalizing ===
cd ..
copy /Y "electron-app\dist\Shokker Paint Booth AG Setup 0.3.0.exe" ShokkerPaintBoothAG-0.3.0-Setup.exe
copy /Y "electron-app\dist\ShokkerPaintBoothAG-0.3.0-Setup.exe" ShokkerPaintBoothAG-0.3.0-Setup.exe
echo Pipeline Success! > pipeline_done.txt
exit /b 0

:error
echo Pipeline Failed! > pipeline_done.txt
exit /b 1
