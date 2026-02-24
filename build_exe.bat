@echo off
cd /d "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine"

echo === PyInstaller Version ===
"C:\Users\Ricky's PC\AppData\Local\Programs\Python\Python311\python.exe" -m PyInstaller --version

echo === Building EXE ===
"C:\Users\Ricky's PC\AppData\Local\Programs\Python\Python311\python.exe" -m PyInstaller --clean --noconfirm shokker-server.spec

echo === Build Exit Code: %ERRORLEVEL% ===

if exist "dist\shokker-server.exe" (
    echo === EXE Built Successfully ===
    dir "dist\shokker-server.exe"
    
    echo === Deploying to electron-app\server ===
    copy /Y "dist\shokker-server.exe" "electron-app\server\shokker-server.exe"
    copy /Y "paint-booth-v2.html" "electron-app\server\paint-booth-v2.html"
    echo === Deploy Complete ===
) else (
    echo === ERROR: EXE not found in dist\ ===
)

echo === DONE ===
