[CmdletBinding()]
param(
    [string]$Root = '',
    [int]$IntervalSeconds = 30,
    [double]$WarnPrivateGB = 8,
    [double]$WarnTotalPrivateGB = 20,
    [switch]$AutoRestart,
    [double]$RestartPrivateGB = 18,
    [double]$RestartTotalPrivateGB = 36,
    [int]$RestartCooldownMinutes = 10,
    [switch]$Once
)

$ErrorActionPreference = 'Continue'
$ScriptRoot = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ScriptRoot)) {
    $ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..')).Path
}
else {
    $Root = (Resolve-Path -LiteralPath $Root).Path
}
$LogDir = Join-Path $Root '_perf'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$CsvPath = Join-Path $LogDir "spb-python-guardian-$Stamp.csv"
$EventPath = Join-Path $LogDir "spb-python-guardian-$Stamp.events.jsonl"
$Header = 'Time,Pid,Name,IsSpb,Reason,PrivateGB,WorkingGB,CpuSeconds,Path,CommandLine'
Set-Content -LiteralPath $CsvPath -Value $Header -Encoding UTF8

function ConvertTo-CsvField {
    param([object]$Value)
    if ($null -eq $Value) {
        return '""'
    }
    $Text = [string]$Value
    return '"' + $Text.Replace('"', '""') + '"'
}

function Write-GuardianEvent {
    param(
        [string]$Level,
        [string]$Message,
        [object]$Data = $null
    )
    $Event = [ordered]@{
        time = (Get-Date).ToString('o')
        level = $Level
        message = $Message
        data = $Data
    }
    ($Event | ConvertTo-Json -Compress -Depth 6) | Add-Content -LiteralPath $EventPath -Encoding UTF8
}

function Get-SpbPorts {
    $Ports = New-Object System.Collections.Generic.List[int]
    $ServerPortPath = Join-Path $Root '.server_port'
    if (Test-Path -LiteralPath $ServerPortPath) {
        $PortText = (Get-Content -LiteralPath $ServerPortPath -Raw -ErrorAction SilentlyContinue).Trim()
        $Parsed = 0
        if ([int]::TryParse($PortText, [ref]$Parsed)) {
            [void]$Ports.Add($Parsed)
        }
    }

    foreach ($Port in @(59876, 59877, 59878, 59879, 59880, 60876, 60877, 60878, 60879, 60880, 61876, 62876)) {
        if (-not $Ports.Contains($Port)) {
            [void]$Ports.Add($Port)
        }
    }

    return @($Ports | Sort-Object -Unique)
}

function Get-PortOwnerMap {
    param([int[]]$Ports)
    $Map = @{}
    try {
        $Connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $Ports -contains [int]$_.LocalPort }
        foreach ($Connection in $Connections) {
            $Map[[int]$Connection.OwningProcess] = [int]$Connection.LocalPort
        }
    }
    catch {
        Write-GuardianEvent -Level 'WARN' -Message 'Could not read listening TCP connections.' -Data $_.Exception.Message
    }
    return $Map
}

function Get-PythonSamples {
    param(
        [hashtable]$PortOwners,
        [string]$RootPath
    )

    $Samples = @()
    $EscapedRoot = [regex]::Escape($RootPath)
    $PythonProcesses = Get-CimInstance Win32_Process -Filter "(Name='python.exe' OR Name='pythonw.exe' OR Name='py.exe')" -ErrorAction SilentlyContinue

    foreach ($CimProcess in $PythonProcesses) {
        $ProcessId = [int]$CimProcess.ProcessId
        $CommandLine = [string]$CimProcess.CommandLine
        $ExecutablePath = [string]$CimProcess.ExecutablePath
        $Reasons = @()

        if ($PortOwners.ContainsKey($ProcessId)) {
            $Reasons += "listening-port:$($PortOwners[$ProcessId])"
        }
        if ($CommandLine -match $EscapedRoot -or $ExecutablePath -match $EscapedRoot) {
            $Reasons += 'spb-root-path'
        }
        if ($CommandLine -match '(?i)(server_v5\.py|spec[_-]sculpt|shokker|paint[- ]booth)') {
            $Reasons += 'spb-command-marker'
        }

        $LiveProcess = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        $PrivateGB = 0
        $WorkingGB = 0
        $CpuSeconds = 0
        if ($LiveProcess) {
            $PrivateGB = [math]::Round($LiveProcess.PrivateMemorySize64 / 1GB, 3)
            $WorkingGB = [math]::Round($LiveProcess.WorkingSet64 / 1GB, 3)
            if ($null -ne $LiveProcess.CPU) {
                $CpuSeconds = [math]::Round($LiveProcess.CPU, 2)
            }
        }

        $Samples += [pscustomobject]@{
            Time = (Get-Date).ToString('o')
            Pid = $ProcessId
            Name = [string]$CimProcess.Name
            IsSpb = ($Reasons.Count -gt 0)
            Reason = ($Reasons -join ';')
            PrivateGB = $PrivateGB
            WorkingGB = $WorkingGB
            CpuSeconds = $CpuSeconds
            Path = $ExecutablePath
            CommandLine = $CommandLine
        }
    }

    return $Samples
}

function Add-SamplesToCsv {
    param([object[]]$Samples)
    foreach ($Sample in $Samples) {
        $Line = @(
            ConvertTo-CsvField $Sample.Time
            ConvertTo-CsvField $Sample.Pid
            ConvertTo-CsvField $Sample.Name
            ConvertTo-CsvField $Sample.IsSpb
            ConvertTo-CsvField $Sample.Reason
            ConvertTo-CsvField $Sample.PrivateGB
            ConvertTo-CsvField $Sample.WorkingGB
            ConvertTo-CsvField $Sample.CpuSeconds
            ConvertTo-CsvField $Sample.Path
            ConvertTo-CsvField $Sample.CommandLine
        ) -join ','
        Add-Content -LiteralPath $CsvPath -Value $Line -Encoding UTF8
    }
}

function Restart-SpbPythonServer {
    param(
        [object[]]$SpbSamples,
        [int]$Port
    )

    $UniquePids = @($SpbSamples | Select-Object -ExpandProperty Pid -Unique)
    foreach ($Pid in $UniquePids) {
        Stop-Process -Id $Pid -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds 2

    $PythonExe = 'C:\Python313\python.exe'
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        $PythonExe = 'python.exe'
    }

    $PreviousPort = $env:SHOKKER_PORT
    $PreviousHashSeed = $env:PYTHONHASHSEED
    try {
        $env:SHOKKER_PORT = [string]$Port
        $env:PYTHONHASHSEED = '0'
        Start-Process -FilePath $PythonExe -ArgumentList @('server_v5.py') -WorkingDirectory $Root -WindowStyle Hidden | Out-Null
    }
    finally {
        $env:SHOKKER_PORT = $PreviousPort
        $env:PYTHONHASHSEED = $PreviousHashSeed
    }
}

Write-Host "SPB Python guardian started."
Write-Host "Root: $Root"
Write-Host "CSV: $CsvPath"
Write-Host "Events: $EventPath"
if ($AutoRestart) {
    Write-Host "AutoRestart is ON. Only Python processes identified as SPB-related can be restarted."
}
else {
    Write-Host "AutoRestart is OFF. This run only records Python memory and command lines."
}

Write-GuardianEvent -Level 'INFO' -Message 'SPB Python guardian started.' -Data @{
    root = $Root
    intervalSeconds = $IntervalSeconds
    warnPrivateGB = $WarnPrivateGB
    warnTotalPrivateGB = $WarnTotalPrivateGB
    autoRestart = [bool]$AutoRestart
}

$LastRestart = [datetime]::MinValue

while ($true) {
    $Ports = Get-SpbPorts
    $PortOwners = Get-PortOwnerMap -Ports $Ports
    $Samples = @(Get-PythonSamples -PortOwners $PortOwners -RootPath $Root)
    Add-SamplesToCsv -Samples $Samples

    $SpbSamples = @($Samples | Where-Object { $_.IsSpb })
    $TotalPrivateGB = [math]::Round((($SpbSamples | Measure-Object -Property PrivateGB -Sum).Sum), 3)
    $HeavySamples = @($SpbSamples | Where-Object { $_.PrivateGB -ge $WarnPrivateGB })

    if ($SpbSamples.Count -gt 0) {
        $Top = @($SpbSamples | Sort-Object PrivateGB -Descending | Select-Object -First 3)
        Write-Host ("{0} SPB Python count={1} totalPrivateGB={2} top={3}GB pid={4}" -f (Get-Date -Format 'HH:mm:ss'), $SpbSamples.Count, $TotalPrivateGB, $Top[0].PrivateGB, $Top[0].Pid)
    }
    else {
        Write-Host ("{0} no SPB Python process detected" -f (Get-Date -Format 'HH:mm:ss'))
    }

    if ($HeavySamples.Count -gt 0 -or $TotalPrivateGB -ge $WarnTotalPrivateGB) {
        Write-GuardianEvent -Level 'WARN' -Message 'SPB Python memory warning.' -Data @{
            totalPrivateGB = $TotalPrivateGB
            heavy = @($HeavySamples | Select-Object Pid, PrivateGB, WorkingGB, Reason, CommandLine)
            allSpb = @($SpbSamples | Select-Object Pid, PrivateGB, WorkingGB, Reason, CommandLine)
        }
    }

    $RestartReasons = @()
    if ($AutoRestart -and $SpbSamples.Count -gt 0) {
        $OverProcessLimit = @($SpbSamples | Where-Object { $_.PrivateGB -ge $RestartPrivateGB })
        if ($OverProcessLimit.Count -gt 0) {
            $RestartReasons += "process-private-gb>=$RestartPrivateGB"
        }
        if ($TotalPrivateGB -ge $RestartTotalPrivateGB) {
            $RestartReasons += "total-private-gb>=$RestartTotalPrivateGB"
        }
    }

    if ($RestartReasons.Count -gt 0) {
        $MinutesSinceRestart = ((Get-Date) - $LastRestart).TotalMinutes
        if ($MinutesSinceRestart -ge $RestartCooldownMinutes) {
            Write-GuardianEvent -Level 'ACTION' -Message 'Restarting SPB Python server due to memory threshold.' -Data @{
                reasons = $RestartReasons
                totalPrivateGB = $TotalPrivateGB
                samples = @($SpbSamples | Select-Object Pid, PrivateGB, WorkingGB, Reason, CommandLine)
            }
            Restart-SpbPythonServer -SpbSamples $SpbSamples -Port $Ports[0]
            $LastRestart = Get-Date
        }
        else {
            Write-GuardianEvent -Level 'WARN' -Message 'Restart threshold hit but cooldown is active.' -Data @{
                reasons = $RestartReasons
                minutesSinceRestart = [math]::Round($MinutesSinceRestart, 2)
                cooldownMinutes = $RestartCooldownMinutes
            }
        }
    }

    if ($Once) {
        break
    }
    Start-Sleep -Seconds $IntervalSeconds
}
