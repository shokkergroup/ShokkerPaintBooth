# Disable + unregister the Windows "Shokker Agent Watchdog" task (E:\Koda\watchdog.bat, ~10 min).
# That task restarts Koda/Claude/Codex proxies and spawns new cmd windows — often mistaken for SPB resetting.
$ErrorActionPreference = 'Stop'
$taskName = 'Shokker Agent Watchdog'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "Task not found: $taskName (already removed?)"
    exit 0
}
Write-Host "Found: $taskName (State: $($task.State))"
Disable-ScheduledTask -TaskName $taskName | Out-Null
Write-Host "Disabled: $taskName"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Host "Unregistered: $taskName"
Write-Host "Done. Koda stack will no longer auto-restart every 10 minutes."
