# SPB Alpha smoke test v2 — installs, probes payhip reachability, then DRIVES the license
# dialog (types the key + Activate) and proves the booth loads. Runs INSIDE Windows Sandbox.
# Mapped: C:\Installers (ro: installer+package+key), C:\QA (rw: results out).
$ErrorActionPreference = 'Continue'
# Heartbeat FIRST — proves the LogonCommand fired and C:\QA is writable, before anything can fail.
try { New-Item -ItemType Directory -Force 'C:\QA' | Out-Null; Set-Content -Path 'C:\QA\STARTED.txt' -Value "logon fired $(Get-Date -Format 'HH:mm:ss')" } catch {}
trap { try { Add-Content -Path 'C:\QA\RESULT.txt' -Value "TRAP (fatal): $($_.Exception.Message)" } catch {}; continue }
$qa = 'C:\QA'
$log = Join-Path $qa 'RESULT.txt'
function Say($m) { $line = "$(Get-Date -Format 'HH:mm:ss')  $m"; Add-Content -Path $log -Value $line; Write-Host $line }
function Shot($name) {
  try {
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    $b = [Windows.Forms.SystemInformation]::VirtualScreen
    $bmp = New-Object Drawing.Bitmap $b.Width, $b.Height
    $g = [Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [Drawing.Point]::Empty, $b.Size)
    $bmp.Save((Join-Path $qa $name), [Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose(); Say "  shot: $name"
  } catch { Say "  shot FAIL ($name): $($_.Exception.Message)" }
}

New-Item -ItemType Directory -Force $qa | Out-Null
Set-Content -Path $log -Value "SPB SANDBOX SMOKE TEST v2  $(Get-Date)"

# --- connectivity probe (does THIS sandbox reach payhip?) ---
Say 'Probing payhip.com reachability from sandbox...'
$payhipOk = $false
try { $r = Invoke-WebRequest 'https://payhip.com/' -UseBasicParsing -TimeoutSec 6; Say "  payhip HTTP $($r.StatusCode) — REACHABLE"; $payhipOk = $true }
catch { if ($_.Exception.Response) { Say "  payhip HTTP $([int]$_.Exception.Response.StatusCode) — REACHABLE"; $payhipOk = $true } else { Say "  payhip UNREACHABLE: $($_.Exception.Message)" } }

# --- install ---
$setup = Get-ChildItem 'C:\Installers' -Filter '*Web-Setup.exe' | Select-Object -First 1
if (-not $setup) { Say 'FAIL: no installer'; exit 1 }
Say "Installing $($setup.Name) silently..."
$p = Start-Process $setup.FullName -ArgumentList '/S' -PassThru; $p.WaitForExit()
Say "Installer exit=$($p.ExitCode)"

$appExe = Get-ChildItem "$env:LOCALAPPDATA\Programs" -Directory -ErrorAction SilentlyContinue |
  Where-Object Name -match 'shokker' |
  ForEach-Object { Get-ChildItem $_.FullName -Filter '*.exe' } |
  Where-Object { $_.Name -notmatch 'unins' } | Select-Object -First 1
if (-not $appExe) { Say 'FAIL: app exe not found'; exit 1 }
Say "Installed: $($appExe.Name)"

# --- launch + wait for license window ---
Say 'Launching app...'
Start-Process $appExe.FullName
Start-Sleep -Seconds 18
Shot 'v2-1-license-gate.png'

$key = ''
try { $key = (Get-Content 'C:\Installers\testkey.txt' -Raw).Trim() } catch {}
if (-not $key) { Say 'FAIL: no testkey.txt'; exit 1 }
Say "Driving license dialog with key $($key.Substring(0,5))-..."

# Bring the Activate window to foreground and type the key.
Add-Type -AssemblyName Microsoft.VisualBasic
$proc = Get-Process | Where-Object { $_.MainWindowTitle -match 'Activate|Shokker' -and $_.Name -match 'shokker' } | Select-Object -First 1
if ($proc) {
  try { [Microsoft.VisualBasic.Interaction]::AppActivate($proc.Id); Start-Sleep -Milliseconds 800 } catch { Say "  AppActivate warn: $($_.Exception.Message)" }
}
Add-Type -AssemblyName System.Windows.Forms
# Click into the field area is auto-focused on the input in license.html; type key then activate.
[System.Windows.Forms.SendKeys]::SendWait($key)
Start-Sleep -Milliseconds 600
Shot 'v2-2-key-typed.png'
# Tab to the Activate button and press it (Enter also submits in most forms).
[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait('{TAB}{ENTER}')
Say 'Submitted. Waiting for verify + server boot...'

# --- success signal: server answers on default ports (only starts AFTER activation) ---
$ports = 59876,59877,59878,59879,60876
$alive = $null
$deadline = (Get-Date).AddMinutes(3)
while (-not $alive -and (Get-Date) -lt $deadline) {
  foreach ($pt in $ports) { try { if ((Invoke-WebRequest "http://127.0.0.1:$pt/" -UseBasicParsing -TimeoutSec 4).StatusCode -eq 200) { $alive = $pt; break } } catch {} }
  if (-not $alive) { Start-Sleep -Seconds 5 }
}
Start-Sleep -Seconds 3
Shot 'v2-3-after-activate.png'

if ($alive) {
  Say "PASS: server answering on 127.0.0.1:$alive — ACTIVATION SUCCEEDED, booth loading"
  try { $html = (Invoke-WebRequest "http://127.0.0.1:$alive/" -UseBasicParsing -TimeoutSec 8).Content; if ($html -match 'SHOKKER') { Say 'PASS: booth HTML served' } } catch {}
} else {
  # Distinguish fixed-offline-activation from a still-broken hang.
  Say "NOTE: server not up in 3min. payhipReachable=$payhipOk — if false, expected path is offline-activation (check shot v2-3 for booth or offline message); if app window still says 'Verifying...' the hang is NOT fixed."
}

# copy logs
$ld = "$env:APPDATA\ShokkerPaintBooth\logs"
if (Test-Path $ld) { Copy-Item $ld (Join-Path $qa 'app-logs') -Recurse -Force; Say 'app logs copied' }
Say 'SMOKE TEST v2 DONE.'
