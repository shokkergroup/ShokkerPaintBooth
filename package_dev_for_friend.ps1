# Package current DEV build for a friend (no license key needed - Alpha build).
# Run from: "Shokker Paint Booth V5" folder or from repo root.
# Output: One zip next to this script (or in repo root) named with date.

$ErrorActionPreference = "Stop"
$v5Name = "Shokker Paint Booth V5"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# If we're inside V5, source is scriptDir; else assume script is in V5
if ((Split-Path -Leaf $scriptDir) -eq $v5Name) {
    $sourceDir = $scriptDir
} else {
    $sourceDir = Join-Path $scriptDir $v5Name
}
if (-not (Test-Path $sourceDir)) {
    Write-Error "V5 folder not found: $sourceDir"
}
$dateStr = Get-Date -Format "yyyy-MM-dd"
$zipName = "ShokkerPaintBooth-V5-DEV-$dateStr.zip"
$parentDir = Split-Path -Parent $sourceDir
$zipPath = Join-Path $parentDir $zipName

# Temp copy with exclusions (so we don't zip cache/build/license)
$tempRoot = Join-Path $env:TEMP "ShokkerPackage_$(Get-Date -Format 'yyyyMMddHHmmss')"
$tempV5 = Join-Path $tempRoot $v5Name
New-Item -ItemType Directory -Path $tempV5 -Force | Out-Null

$excludeDirs = @(
    ".git", "__pycache__", "node_modules", "venv", ".venv",
    "dist", "build", "server.build", "server.onefile-build",
    "_archive", "_staging", "output", "PayHip-upload"
)
$excludeFiles = @("*.pyc", "shokker_license.json")
$robocopyExclude = ($excludeDirs | ForEach-Object { "/XD", $_ }) -join " "
$xf = ($excludeFiles | ForEach-Object { "/XF", $_ }) -join " "

Write-Host "Copying V5 to temp (excluding cache/build/license)..."
& robocopy $sourceDir $tempV5 /E /NFL /NDL /NJH /NJS /NC /NS /NP /XD $excludeDirs /XF $excludeFiles | Out-Null
if ($LASTEXITCODE -ge 8) {
    Write-Error "Robocopy failed with exit $LASTEXITCODE"
}

# Add a short README for your friend
$readme = @"
Shokker Paint Booth V5 — DEV build ($dateStr)
============================================
Your friend sent you this build. No license key needed for this Alpha build.

How to run:
1. Install Python 3 (if not already): https://www.python.org/downloads/
2. Open a terminal in this folder (e.g. right-click -> Open in Terminal).
3. Run:  python server_v5.py
4. Open a browser to:  http://localhost:59876

Optional: Double-click reset_python_and_cache.bat if anything gets stuck, then run server_v5.py again.
"@
Set-Content -Path (Join-Path $tempV5 "RUN_FIRST.txt") -Value $readme -Encoding UTF8

Write-Host "Creating zip: $zipPath"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $tempRoot "*") -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Done. Package: $zipPath"
Write-Host "Send that file to your friend; they unzip and run python server_v5.py from the folder."