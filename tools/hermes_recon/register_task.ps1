$ErrorActionPreference = "Stop"

$taskName = "SPB HERMES Recon"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$runner = Join-Path $repoRoot "HERMES_RECON_TASK_RUN.bat"

$action = New-ScheduledTaskAction `
  -Execute "cmd.exe" `
  -Argument ("/c `"$runner`"") `
  -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger `
  -Once `
  -At (Get-Date).AddMinutes(1) `
  -RepetitionInterval (New-TimeSpan -Minutes 15) `
  -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -MultipleInstances IgnoreNew

Register-ScheduledTask `
  -TaskName $taskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Runs HERMES Recon for Shokker Paint Booth every 15 minutes." `
  -Force | Out-Null

Start-ScheduledTask -TaskName $taskName

Write-Host "Registered and started: $taskName"
Write-Host "Runner: $runner"
Write-Host "Cadence: every 15 minutes"
