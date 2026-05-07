$taskName = "SPB HERMES Recon"

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
  Write-Host "Windows scheduled task: not installed"
} else {
  $info = Get-ScheduledTaskInfo -TaskName $taskName
  Write-Host "Windows scheduled task: installed"
  Write-Host "State: $($task.State)"
  Write-Host "Last run: $($info.LastRunTime)"
  Write-Host "Next run: $($info.NextRunTime)"
  Write-Host "Last result: $($info.LastTaskResult)"
}

Write-Host ""
wsl -d Ubuntu-24.04 -u ricky -- bash -lc "cd '/mnt/e/Koda/Shokker Paint Booth Gold to Platinum' && python3 tools/hermes_recon/hermes_recon.py --status"
