$ErrorActionPreference = "Stop"
echo "=== 1. Building PyInstaller ==="
Remove-Item -Recurse -Force "dist\*" -ErrorAction SilentlyContinue 
Remove-Item -Recurse -Force "build\*" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "__pycache__*" -ErrorAction SilentlyContinue
pyinstaller shokker-server-ag.spec --clean --noconfirm *>&1 | Out-File "build_log.txt" -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

echo "=== 2. Copying Backend ==="
Copy-Item "dist\shokker-paint-booth-ag.exe" "electron-app\server\shokker-paint-booth-ag.exe" -Force

echo "=== 3. Building Electron App ==="
Set-Location "electron-app"
npm run build *>&1 | Out-File "npm_build_log.txt" -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "npm build failed" }

echo "=== 4. Finalizing ==="
Set-Location ".."
Copy-Item "electron-app\dist\Shokker Paint Booth Setup 0.2.3.exe" "ShokkerPaintBoothAG-0.2.3-Setup.exe" -Force -ErrorAction SilentlyContinue
Copy-Item "electron-app\dist\ShokkerPaintBoothAG-0.2.3-Setup.exe" "ShokkerPaintBoothAG-0.2.3-Setup.exe" -Force -ErrorAction SilentlyContinue
echo "Pipeline Success!" > pipeline_done.txt
