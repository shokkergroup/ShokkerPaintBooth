@echo off
cd /d "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine"
echo === Checking Python and PyInstaller ===
C:\Windows\py.exe -3.11 -c "import PyInstaller; print('PyInstaller', PyInstaller.__version__)"
if errorlevel 1 (
    echo PyInstaller not found on Python 3.11, trying default python...
    C:\Windows\py.exe -c "import PyInstaller; print('PyInstaller', PyInstaller.__version__)"
)
echo.
echo === Building shokker-server.exe ===
C:\Windows\py.exe -3.11 -m PyInstaller --noconfirm shokker-server.spec
if errorlevel 1 (
    echo Build with 3.11 failed, trying default...
    C:\Windows\py.exe -m PyInstaller --noconfirm shokker-server.spec
)
echo.
echo === Build complete ===
dir dist\shokker-server.exe 2>nul
if errorlevel 1 echo ERROR: shokker-server.exe not found in dist!
