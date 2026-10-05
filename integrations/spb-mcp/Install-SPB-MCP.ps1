param([string]$AppUrl = 'http://localhost:59876/')
$ErrorActionPreference = 'Stop'
$spbMcpRoot = $PSScriptRoot
$spbMcpPython = Join-Path $spbMcpRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $spbMcpPython)) {
    python -m venv (Join-Path $spbMcpRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed.' }
}
& $spbMcpPython -m pip install -r (Join-Path $spbMcpRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'MCP dependency installation failed.' }
$spbMcpData = Join-Path $spbMcpRoot 'data'
New-Item -ItemType Directory -Force -Path $spbMcpData | Out-Null
$spbMcpConfig = Join-Path $spbMcpData 'client-config.json'
& $spbMcpPython (Join-Path $spbMcpRoot 'spb_mcp_server.py') --url $AppUrl --print-config |
    Set-Content -LiteralPath $spbMcpConfig -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw 'MCP configuration generation failed.' }
Write-Host "SPB MCP installed. Client connection settings: $spbMcpConfig"
Write-Host 'No AI client configuration was overwritten. The AI client starts the stdio server on demand.'
