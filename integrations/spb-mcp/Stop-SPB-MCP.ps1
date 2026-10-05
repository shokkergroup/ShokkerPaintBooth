$ErrorActionPreference = 'Stop'
$spbMcpPidFile = Join-Path $PSScriptRoot 'data\http.pid'
if (-not (Test-Path -LiteralPath $spbMcpPidFile)) { Write-Host 'No recorded SPB MCP process.'; return }
$spbMcpPid = [int](Get-Content -LiteralPath $spbMcpPidFile -Raw)
$spbMcpProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$spbMcpPid"
if ($spbMcpProcess) {
    $spbMcpScript = Join-Path $PSScriptRoot 'spb_mcp_server.py'
    if ($spbMcpProcess.CommandLine -notmatch [regex]::Escape($spbMcpScript)) {
        throw 'Recorded PID belongs to another process; it was not stopped.'
    }
    Stop-Process -Id $spbMcpPid
}
Remove-Item -LiteralPath $spbMcpPidFile
Write-Host 'SPB MCP HTTP process stopped. Save/close active MCP documents before using this command.'
