# SPB Alpha installer smoke test — runs INSIDE Windows Sandbox as LogonCommand.
# Mapped: C:\Installers (read-only: installer + package + this script), C:\QA (writable: results out).
$ErrorActionPreference = 'Continue'
$qa = 'C:\QA'
$log = Join-Path $qa 'RESULT.txt'
function Say($m) { $line = "$(Get-Date -Format 'HH:mm:ss')  $m"; Add-Content -Path $log -Value $line; Write-Host $line }

New-Item -ItemType Directory -Force $qa | Out-Null
Set-Content -Path $log -Value "SPB SANDBOX SMOKE TEST  $(Get-Date)"
Say "Sandbox up. Looking for installer..."

$setup = Get-ChildItem 'C:\Installers' -Filter '*Web-Setup.exe' | Select-Object -First 1
if (-not $setup) { $setup = Get-ChildItem 'C:\Installers' -Filter '*Setup.exe' | Select-Object -First 1 }
if (-not $setup) { Say 'FAIL: no installer found in C:\Installers'; exit 1 }
Say "Installer: $($setup.Name) ($([math]::Round($setup.Length/1MB,1)) MB)"

# NSIS web stub uses the .nsis.7z package sitting beside it instead of downloading — both are mapped in.
Say 'Running silent install (/S)...'
$sw = [Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $setup.FullName -ArgumentList '/S' -PassThru
$proc.WaitForExit()
Say "Installer exited code=$($proc.ExitCode) after $([math]::Round($sw.Elapsed.TotalSeconds,0))s"

# Find the installed app exe (per-user first, then per-machine).
$roots = @("$env:LOCALAPPDATA\Programs", "$env:ProgramFiles", "${env:ProgramFiles(x86)}")
$appExe = $null
foreach ($r in $roots) {
  if (-not (Test-Path $r)) { continue }
  $appExe = Get-ChildItem $r -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'shokker' } |
    ForEach-Object { Get-ChildItem $_.FullName -Filter '*.exe' -ErrorAction SilentlyContinue } |
    Where-Object { $_.Name -notmatch 'unins' } | Select-Object -First 1
  if ($appExe) { break }
}
if (-not $appExe) { Say 'FAIL: installed app exe not found under Programs dirs'; Get-ChildItem "$env:LOCALAPPDATA\Programs" -ErrorAction SilentlyContinue | ForEach-Object { Say "  saw: $($_.Name)" }; exit 1 }
Say "PASS: app installed -> $($appExe.FullName)"

Say 'Launching app...'
Start-Process -FilePath $appExe.FullName
Start-Sleep -Seconds 20

# Poll the local server on the default port scan (59876..59879, 60876..) for up to 4 minutes.
$ports = 59876,59877,59878,59879,60876,60877
$alive = $null
$deadline = (Get-Date).AddMinutes(4)
while (-not $alive -and (Get-Date) -lt $deadline) {
  foreach ($pt in $ports) {
    try {
      $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$pt/" -UseBasicParsing -TimeoutSec 5
      if ($resp.StatusCode -eq 200) { $alive = $pt; break }
    } catch {}
  }
  if (-not $alive) { Start-Sleep -Seconds 6 }
}
if ($alive) {
  Say "PASS: SPB server answering HTTP 200 on 127.0.0.1:$alive"
  try {
    $html = (Invoke-WebRequest -Uri "http://127.0.0.1:$alive/" -UseBasicParsing -TimeoutSec 10).Content
    if ($html -match 'SHOKKER|Shokker') { Say 'PASS: booth HTML served (SHOKKER marker found)' } else { Say 'WARN: HTML served but no SHOKKER marker' }
  } catch { Say "WARN: second fetch failed: $($_.Exception.Message)" }
} else {
  Say 'FAIL: server never answered on default ports within 4 minutes'
}

# Is the app process alive?
Start-Sleep -Seconds 10
$alive2 = Get-Process | Where-Object { $_.Name -match 'shokker' -or $_.Path -eq $appExe.FullName } | Select-Object -First 3
if ($alive2) { $alive2 | ForEach-Object { Say "PASS: process running: $($_.Name) (pid $($_.Id))" } } else { Say 'FAIL: no shokker process running' }

# Screenshot the desktop for visual proof.
try {
  Add-Type -AssemblyName System.Windows.Forms, System.Drawing
  $b = [Windows.Forms.SystemInformation]::VirtualScreen
  $bmp = New-Object Drawing.Bitmap $b.Width, $b.Height
  $g = [Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($b.Location, [Drawing.Point]::Empty, $b.Size)
  $bmp.Save((Join-Path $qa 'sandbox-screenshot.png'), [Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
  Say 'PASS: screenshot captured'
} catch { Say "WARN: screenshot failed: $($_.Exception.Message)" }

# Copy app logs out.
$logDir = "$env:APPDATA\ShokkerPaintBooth\logs"
if (Test-Path $logDir) { Copy-Item $logDir (Join-Path $qa 'app-logs') -Recurse -Force; Say 'PASS: app logs copied to QA share' }
else { Say "NOTE: no log dir at $logDir (listing APPDATA)"; Get-ChildItem $env:APPDATA -Directory -ErrorAction SilentlyContinue | Where-Object Name -match 'shokker' | ForEach-Object { Say "  appdata: $($_.Name)"; Copy-Item $_.FullName (Join-Path $qa $_.Name) -Recurse -Force -ErrorAction SilentlyContinue } }

Say 'SMOKE TEST DONE.'
