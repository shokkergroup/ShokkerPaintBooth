$ErrorActionPreference = "Continue"
$pyExe = "C:\Users\Ricky's PC\AppData\Local\Programs\Python\Python311\python.exe"
$workDir = "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine"
$logFile = Join-Path $workDir "build_log.txt"

Set-Location $workDir

"=== PyInstaller Version ===" | Out-File $logFile
& $pyExe -m PyInstaller --version 2>&1 | Out-File $logFile -Append

"=== Building EXE ===" | Out-File $logFile -Append
& $pyExe -m PyInstaller --clean --noconfirm shokker-server.spec 2>&1 | Out-File $logFile -Append

$exePath = Join-Path $workDir "dist\shokker-server.exe"
if (Test-Path $exePath) {
    "=== EXE Built Successfully ===" | Out-File $logFile -Append
    (Get-Item $exePath).Length | ForEach-Object { "Size: $_ bytes" } | Out-File $logFile -Append
    
    "=== Deploying ===" | Out-File $logFile -Append
    $deployDir = Join-Path $workDir "electron-app\server"
    Copy-Item $exePath (Join-Path $deployDir "shokker-server.exe") -Force
    Copy-Item (Join-Path $workDir "paint-booth-v2.html") (Join-Path $deployDir "paint-booth-v2.html") -Force
    "=== Deploy Complete ===" | Out-File $logFile -Append
} else {
    "=== ERROR: EXE not found ===" | Out-File $logFile -Append
}

"=== DONE ===" | Out-File $logFile -Append
