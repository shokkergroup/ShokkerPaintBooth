param([string]$AppUrl = 'http://localhost:59876/', [int]$Port = 59890)
$ErrorActionPreference = 'Stop'
$spbMcpRoot = $PSScriptRoot
$spbMcpPython = Join-Path $spbMcpRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $spbMcpPython)) { $spbMcpPython = (Get-Command python).Source }
$spbMcpData = Join-Path $spbMcpRoot 'data'
New-Item -ItemType Directory -Force -Path $spbMcpData | Out-Null
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port is already in use; an existing service has not been restarted."
}
$spbMcpScript = Join-Path $spbMcpRoot 'spb_mcp_server.py'
# Start-Process joins ArgumentList on Windows; quote the absolute script path.
$spbMcpArgs = @(('"{0}"' -f $spbMcpScript), '--transport', 'streamable-http', '--port', $Port, '--url', ('"{0}"' -f $AppUrl))
$spbMcpProcess = Start-Process -FilePath $spbMcpPython -ArgumentList $spbMcpArgs -WindowStyle Hidden -PassThru `
    -WorkingDirectory $spbMcpRoot -RedirectStandardOutput (Join-Path $spbMcpData 'http-stdout.log') `
    -RedirectStandardError (Join-Path $spbMcpData 'http-stderr.log')
$spbMcpProcess.Id | Set-Content -LiteralPath (Join-Path $spbMcpData 'http.pid')
Write-Host "Starting SPB MCP in the background: http://127.0.0.1:$Port/mcp"
Write-Host "Bearer token: $spbMcpData\http-token.txt (created on startup)"
