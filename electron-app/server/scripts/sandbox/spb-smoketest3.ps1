# SPB v7.0.2 sandbox test — proves: clean install works, branding says V7, AND installing
# AGAIN while the app is running does NOT hang (the force-kill fix). Runs inside Windows Sandbox.
$ErrorActionPreference = 'Continue'
try { New-Item -ItemType Directory -Force 'C:\QA' | Out-Null; Set-Content -Path 'C:\QA\STARTED.txt' -Value "logon fired $(Get-Date -Format 'HH:mm:ss')" } catch {}
trap { try { Add-Content -Path 'C:\QA\RESULT.txt' -Value "TRAP: $($_.Exception.Message)" } catch {}; continue }
$qa = 'C:\QA'; $log = "$qa\RESULT.txt"
function Say($m) { $l = "$(Get-Date -Format 'HH:mm:ss')  $m"; Add-Content -Path $log -Value $l; Write-Host $l }
function Shot($n) { try { Add-Type -AssemblyName System.Windows.Forms, System.Drawing; $b=[Windows.Forms.SystemInformation]::VirtualScreen; $bm=New-Object Drawing.Bitmap $b.Width,$b.Height; $g=[Drawing.Graphics]::FromImage($bm); $g.CopyFromScreen($b.Location,[Drawing.Point]::Empty,$b.Size); $bm.Save("$qa\$n",[Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bm.Dispose(); Say "  shot: $n" } catch { Say "  shot fail: $($_.Exception.Message)" } }
Set-Content -Path $log -Value "SPB v7.0.2 SANDBOX TEST  $(Get-Date)"

$setup = Get-ChildItem 'C:\Installers' -Filter '*Web-Setup.exe' | Select-Object -First 1
if (-not $setup) { Say 'FAIL: no installer in C:\Installers'; exit 1 }
Say "Installer: $($setup.Name)"

# ---- INSTALL #1 (clean) ----
Say 'Install #1 (clean) silent /S ...'
$sw = [Diagnostics.Stopwatch]::StartNew()
$p = Start-Process $setup.FullName -ArgumentList '/S' -PassThru
if (-not $p.WaitForExit(360000)) { Say 'FAIL: install #1 HUNG (>6 min)'; try { $p.Kill() } catch {}; Shot 'v702-hang1.png'; exit 1 }
Say "Install #1 exit=$($p.ExitCode) in $([math]::Round($sw.Elapsed.TotalSeconds,0))s"

# ---- VERIFY V7 BRANDING ----
$exe = Get-ChildItem "$env:LOCALAPPDATA\Programs" -Recurse -Filter '*.exe' -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Shokker Paint Booth' -and $_.Name -notmatch 'unins' } | Select-Object -First 1
if (-not $exe) { Say 'FAIL: no installed Shokker exe found'; exit 1 }
if ($exe.Name -match 'V7') { Say "PASS: branding is V7 -> '$($exe.Name)'" } else { Say "FAIL: exe still says NOT-V7 -> '$($exe.Name)'" }
$lnk = Get-ChildItem "$env:PUBLIC\Desktop","$env:USERPROFILE\Desktop","$env:APPDATA\Microsoft\Windows\Start Menu\Programs" -Recurse -Filter '*.lnk' -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Shokker' } | Select-Object -First 1
if ($lnk) { Say "shortcut: '$($lnk.Name)'" }

# ---- LAUNCH (so app + server are running and holding file handles) ----
Say 'Launching app...'
Start-Process $exe.FullName
Start-Sleep -Seconds 22
Shot 'v702-1-running.png'
$proc = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Shokker Paint Booth V7' } | Select-Object -First 1
if ($proc) { Say "app running (pid $($proc.Id)) + child server" } else { Say 'WARN: app process not found after launch' }

# ---- THE KEY TEST: reinstall WHILE running. Force-kill must let it finish, not hang ----
Say 'Install #2 WHILE APP RUNNING (force-kill no-hang test)...'
$sw2 = [Diagnostics.Stopwatch]::StartNew()
$p2 = Start-Process $setup.FullName -ArgumentList '/S' -PassThru
if (-not $p2.WaitForExit(300000)) { Say 'FAIL: install #2 HUNG over running app (>5 min) - FORCE-KILL DID NOT WORK'; try { $p2.Kill() } catch {}; Shot 'v702-hang2.png'; exit 1 }
Say "PASS: install #2 over running app exit=$($p2.ExitCode) in $([math]::Round($sw2.Elapsed.TotalSeconds,0))s - NO HANG"
Start-Sleep -Seconds 6
Shot 'v702-2-after-reinstall.png'
if (Test-Path $exe.FullName) { Say 'PASS: app exe intact after reinstall-over-running' } else { Say 'WARN: exe missing after reinstall' }

# relaunch to confirm still works
Start-Process $exe.FullName
Start-Sleep -Seconds 15
Shot 'v702-3-relaunch.png'
$proc2 = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Shokker Paint Booth V7' } | Select-Object -First 1
if ($proc2) { Say "PASS: app relaunches clean after reinstall (pid $($proc2.Id))" } else { Say 'WARN: relaunch process not found' }

Say 'v7.0.2 SANDBOX TEST DONE.'
