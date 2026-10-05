# archive_apply.ps1
# Generated 2026-05-27 by stage-only archive proposal pass.
# Run: PowerShell -ExecutionPolicy Bypass -File "_loop_state\archive_apply.ps1"
# Idempotent: skips files already moved. Touches ONLY items classified SAFE-TO-ARCHIVE.
# UNSURE items are intentionally NOT included.

$ErrorActionPreference = 'Stop'

# Resolve project root = parent of _loop_state directory containing this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -LiteralPath $ProjectRoot

$ArchiveDate = '2026-05-27'
$ArchiveDir = Join-Path -Path $ProjectRoot -ChildPath "_archive\$ArchiveDate"

if (-not (Test-Path -LiteralPath $ArchiveDir)) {
    New-Item -ItemType Directory -Path $ArchiveDir -Force | Out-Null
    Write-Host "Created $ArchiveDir"
} else {
    Write-Host "Archive dir already exists: $ArchiveDir"
}

# SAFE-TO-ARCHIVE list (verified zero references in live tree, see archive_proposal.md)
$SafeList = @(
    # Rotated server logs
    'server_log.txt.1',
    'server_log.txt.2',
    'server_log.txt.3',

    # Explicit .bak* backups
    'paint-booth-0-catalog-scorecard.js.bak_optics',
    'paint-booth-0-catalog-scorecard.js.bak_spb102',
    'paint-booth-0-catalog-scorecard.js.bak_spb107',
    'SPB_RATE_10.json.bak_pre_round5_save',
    'SPB_RATE_10.json.bak_pre_round6',
    'SPB_RATE_10.json.bak_round4_start',

    # Captured stdout text dumps
    'list_shimmer.txt',
    'check_m7_categories.txt',

    # Superseded cleanup bats
    'CLEANUP_ROOT_JUNK.bat',
    'CLEANUP_ROOT_JUNK_PREVIEW.bat',

    # Hermes Recon harness (mission complete, no live refs)
    'EDIT_HERMES_RECON_MISSION.bat',
    'HERMES_RECON_TASK_RUN.bat',
    'OPEN_HERMES_RECON_INBOX.bat',
    'OPEN_HERMES_RECON_LOG.bat',
    'RUN_HERMES_RECON_ONCE.bat',
    'START_HERMES_RECON.bat',
    'STATUS_HERMES_RECON.bat',
    'STOP_HERMES_RECON.bat',
    'HERMES_RECON_MISSION.md',
    'HERMES_RECON_README.md',

    # Sentinel / garbage
    'ZzTst_02',
    'nul',

    # One-shot diagnostic scripts (zero references anywhere)
    'check_ff_v2.py',
    'check_fusions.py',
    'check_m7_categories.py',
    'check_registry.py',
    'list_light_optics.py',
    'list_shimmer.py',
    'search_antigravity.py',
    'search_ide.py',
    'search_ide_folder.py',
    'search_promo.py',
    'view_fusion_code.py'
)

$moved   = New-Object System.Collections.Generic.List[string]
$skipped = New-Object System.Collections.Generic.List[string]
$missing = New-Object System.Collections.Generic.List[string]
$failed  = New-Object System.Collections.Generic.List[string]

foreach ($name in $SafeList) {
    $src = Join-Path -Path $ProjectRoot -ChildPath $name
    $dst = Join-Path -Path $ArchiveDir  -ChildPath $name

    if (Test-Path -LiteralPath $dst) {
        $skipped.Add($name) | Out-Null
        continue
    }
    if (-not (Test-Path -LiteralPath $src)) {
        $missing.Add($name) | Out-Null
        continue
    }
    try {
        Move-Item -LiteralPath $src -Destination $dst -ErrorAction Stop
        $moved.Add($name) | Out-Null
    } catch {
        $failed.Add("$name : $($_.Exception.Message)") | Out-Null
    }
}

Write-Host ""
Write-Host "================ Archive Summary ================"
Write-Host "Archive dir : $ArchiveDir"
Write-Host "Moved       : $($moved.Count)"
Write-Host "Skipped     : $($skipped.Count) (already in archive)"
Write-Host "Missing     : $($missing.Count) (not at root)"
Write-Host "Failed      : $($failed.Count)"
Write-Host "-------------------------------------------------"

if ($moved.Count -gt 0)   { Write-Host ""; Write-Host "MOVED:";   foreach ($n in $moved)   { Write-Host "  + $n" } }
if ($skipped.Count -gt 0) { Write-Host ""; Write-Host "SKIPPED:"; foreach ($n in $skipped) { Write-Host "  = $n" } }
if ($missing.Count -gt 0) { Write-Host ""; Write-Host "MISSING:"; foreach ($n in $missing) { Write-Host "  ? $n" } }
if ($failed.Count -gt 0)  { Write-Host ""; Write-Host "FAILED:";  foreach ($n in $failed)  { Write-Host "  ! $n" } }

Write-Host ""
Write-Host "Done. To undo any single file: Move-Item `"_archive\$ArchiveDate\<file>`" .\<file>"
