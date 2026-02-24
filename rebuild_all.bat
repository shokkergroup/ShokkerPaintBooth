@echo off
echo ============================================
echo  ShokkerPaintBooth - Full Rebuild
echo ============================================
echo.

cd /d "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine"

echo [0/3] Cleaning stale PyInstaller cache...
if exist build_temp rmdir /s /q build_temp
if exist dist\shokker-server.exe del /q dist\shokker-server.exe
echo Done.
echo.

echo [1/3] Building shokker-server.exe via PyInstaller...
echo.
py -3.11 -m PyInstaller --noconfirm --clean shokker-server.spec
if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)
echo.
echo [1/3] DONE - shokker-server.exe built.
echo.

echo [2/3] Copying files to electron-app\server...
copy /Y "dist\shokker-server.exe" "electron-app\server\shokker-server.exe"
if errorlevel 1 (
    echo ERROR: Failed to copy shokker-server.exe!
    pause
    exit /b 1
)
echo.
echo [2/3] DONE - Files copied.
echo.

echo [3/3] Building installer via electron-builder...
cd electron-app
call npm run build
if errorlevel 1 (
    echo.
    echo ERROR: electron-builder failed!
    pause
    exit /b 1
)
echo.
echo ============================================
echo  BUILD COMPLETE!
echo  Installer: electron-app\dist\ShokkerPaintBooth-0.1.0-alpha-Setup.exe
echo ============================================
echo.
pause