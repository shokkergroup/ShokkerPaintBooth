[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$targetPort = 59876
$rangeStart = 59842
$rangeCount = 100
$logPath = Join-Path $PSScriptRoot '..\_spb_port_59876_host_fix.log'

function Log([string]$Message) {
    $line = ('{0:yyyy-MM-dd HH:mm:ss} {1}' -f (Get-Date), $Message)
    $line | Tee-Object -FilePath $logPath -Append
}

function Test-TcpBind([string]$Address, [int]$Port) {
    $listener = $null
    try {
        $ip = [System.Net.IPAddress]::Parse($Address)
        $listener = [System.Net.Sockets.TcpListener]::new($ip, $Port)
        $listener.Start()
        return $true
    }
    catch {
        Log "Bind failed on ${Address}:${Port}: $($_.Exception.Message)"
        return $false
    }
    finally {
        if ($null -ne $listener) {
            try { $listener.Stop() } catch {}
        }
    }
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'This repair must run elevated.'
}

Log 'Starting narrow SPB port 59876 host-network repair.'
Log 'Stopping WSL instances so inactive Docker/WSL networking cannot retain the HNS allocation.'
& wsl.exe --shutdown 2>&1 | ForEach-Object { Log "wsl: $_" }

$hnsWasRunning = (Get-Service hns).Status -eq 'Running'
$winNatWasRunning = (Get-Service winnat).Status -eq 'Running'

try {
    if ($hnsWasRunning) {
        Log 'Stopping Host Network Service (HNS).'
        Stop-Service hns -Force
    }
    if ($winNatWasRunning) {
        Log 'Stopping WinNAT.'
        Stop-Service winnat -Force
    }

    Log "Deleting active IPv4 TCP exclusion ${rangeStart}-$($rangeStart + $rangeCount - 1)."
    & netsh.exe interface ipv4 delete excludedportrange protocol=tcp startport=$rangeStart numberofports=$rangeCount store=active 2>&1 |
        ForEach-Object { Log "netsh ipv4: $_" }

    Log "Deleting active IPv6 TCP exclusion ${rangeStart}-$($rangeStart + $rangeCount - 1)."
    & netsh.exe interface ipv6 delete excludedportrange protocol=tcp startport=$rangeStart numberofports=$rangeCount store=active 2>&1 |
        ForEach-Object { Log "netsh ipv6: $_" }
}
finally {
    if ($winNatWasRunning) {
        Log 'Restarting WinNAT.'
        Start-Service winnat
    }
    if ($hnsWasRunning) {
        Log 'Restarting Host Network Service (HNS).'
        Start-Service hns
    }
}

$loopbackOk = Test-TcpBind '127.0.0.1' $targetPort
$wildcardOk = Test-TcpBind '0.0.0.0' $targetPort
Log "RESULT loopback_bind=$loopbackOk wildcard_bind=$wildcardOk"

if (-not ($loopbackOk -and $wildcardOk)) {
    Log 'Narrow repair did not release 59876; no dynamic-port-range settings were changed.'
    exit 2
}

Log 'SUCCESS: TCP 59876 is bindable again.'
