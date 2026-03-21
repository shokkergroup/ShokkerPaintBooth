# Build double-clickable EXE for a friend (no Python/terminal needed).
# Run from: "Shokker Paint Booth V5" folder.
# Steps: 1) PyInstaller server EXE  2) Copy to electron-app  3) Electron build  4) Optional portable zip.

$ErrorActionPreference = "Stop"
$v5Root = $PSScriptRoot
$dateStr = Get-Date -Format "yyyy-MM-dd"

Write-Host "=== Step 1: Build server EXE (PyInstaller) ===" -ForegroundColor Cyan
Set-Location $v5Root
& python -m PyInstaller --noconfirm shokker-server-v5.spec
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed." }

$serverExe = Join-Path $v5Root "dist\shokker-paint-booth-v5.exe"
if (-not (Test-Path $serverExe)) {
    Write-Error "Expected EXE not found: $serverExe"
}

$electronServer = Join-Path $v5Root "electron-app\server"
Write-Host "`n=== Step 2: Copy server EXE into electron-app/server ===" -ForegroundColor Cyan
Copy-Item $serverExe -Destination $electronServer -Force
Write-Host "Copied to $electronServer"

Write-Host "`n=== Step 3: Sync V5 assets and build Electron app ===" -ForegroundColor Cyan
Set-Location (Join-Path $v5Root "electron-app")
& npm run copy-server
if ($LASTEXITCODE -ne 0) { Write-Error "copy-server failed." }
# Copy EXE again (copy-server doesn't create it)
Copy-Item $serverExe -Destination $electronServer -Force
& npm run build
if ($LASTEXITCODE -ne 0) { Write-Error "Electron build failed." }

$winUnpacked = Join-Path $v5Root "electron-app\dist\win-unpacked"
$setupExe = Join-Path $v5Root "electron-app\dist\*.Setup.exe"
$parentDir = Split-Path -Parent $v5Root
$portableZip = Join-Path $parentDir "ShokkerPaintBooth-V5-DEV-Portable-$dateStr.zip"

Write-Host "`n=== Step 4: Create portable zip for your friend ===" -ForegroundColor Cyan
if (Test-Path $portableZip) { Remove-Item $portableZip -Force }
Compress-Archive -Path (Join-Path $winUnpacked "*") -DestinationPath $portableZip -CompressionLevel Optimal

Write-Host "`n=== Done ===" -ForegroundColor Green
Write-Host "Installer (one-click install + desktop shortcut):"
Get-ChildItem (Join-Path $v5Root "electron-app\dist") -Filter "*.Setup.exe" | ForEach-Object { Write-Host "  $($_.FullName)" }
Write-Host "`nPortable zip (unzip and double-click the app):"
Write-Host "  $portableZip"
Write-Host "`nSend the portable zip to your friend. He unzips it and double-clicks 'Shokker Paint Booth V5.exe' - no install, no Python."
Set-Location $v5Root
