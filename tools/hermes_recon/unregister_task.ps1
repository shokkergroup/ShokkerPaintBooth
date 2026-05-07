$taskName = "SPB HERMES Recon"

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
  Write-Host "Windows scheduled task is not installed."
} else {
  Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
  Write-Host "Stopped and removed: $taskName"
}

wsl -d Ubuntu-24.04 -u ricky -- bash -lc "cd '/mnt/e/Koda/Shokker Paint Booth Gold to Platinum' && python3 tools/hermes_recon/hermes_recon.py --stop"
