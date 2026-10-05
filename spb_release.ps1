# =====================================================================================
#  SPB RELEASE - one reusable script for EVERY release. Replaces hand-writing a new
#  spb_deploy_<version>.ps1 each time (spb_deploy_final.ps1 = 8.0.4, spb_deploy_805.ps1
#  = 8.0.5). Version comes from electron-app/package.json, so there is nothing to edit.
#
#  Created 2026-08-09 on owner request ("I NEED to automate this... it's becoming too much
#  for me to handle"). Keeps every safety property the 8.0.4/8.0.5 scripts earned:
#    * keys are pasted by YOU, once, and live only in this process's environment
#    * --hold-latest stages the payload WITHOUT flipping the update feed
#    * a payload SIZE GATE, because the first 8.0.5 build silently shipped 1.76 GB light
#      (SPB_BUNDLE_ALL unset) and nothing in the build failed loudly
#    * nothing goes live until you type GO
#
#  PHASES - the whole point of the split:
#    build   NO CREDENTIALS. Preflight + build + size gate + PayHip kit + sandbox prep.
#            This is the multi-hour part and can run completely unattended.
#    stage   Existing evidence-bound artifacts -> R2, with latest.yml held.
#    deploy  Explicit combined stage -> human boundary -> GO -> activate (never builds).
#    activate Recheck evidence/R2 hashes -> GO -> publish exact latest.yml (never builds).
#    all     RETIRED: aborts across the build/human-smoke boundary.
#    verify  NO CREDENTIALS. Just read the public feed and report what is live.
#
#  USAGE
#    .\spb_release.ps1 -Phase build        # unattended: gates + build + kits
#    .\spb_release.ps1 -Phase stage        # upload exact artifacts; feed untouched
#    .\spb_release.ps1 -Phase activate     # GO + exact feed publication
#    .\spb_release.ps1 -Phase deploy       # explicit combined stage/activate flow
#    .\spb_release.ps1 -Phase verify       # what is live right now?
#    .\spb_release.ps1 -MinPayloadGB 4.8   # override the size floor
#    .\spb_release.ps1 -SaveKey            # ONE TIME: store the R2 token (encrypted)
#    .\spb_release.ps1 -TestKey            # is my stored token still good? (read-only)
# =====================================================================================

[CmdletBinding()]
param(
    [ValidateSet("all", "build", "deploy", "stage", "activate", "verify")]
    [string]$Phase = "all",
    [switch]$SkipBuild,
    # DECIMAL GB (1e9 bytes), matching the proven 8.0.5 gate which compared against
    # 4800000000 bytes. Do NOT switch this to PowerShell's 1GB constant: that is BINARY
    # (GiB, 1073741824), which silently makes the floor ~354 MB stricter and rejects a
    # perfectly complete payload. That exact mistake failed the first 10.0.0 build.
    [double]$MinPayloadGB = 4.8,
    [string]$Version = "",
    # One-time: prompt for the R2 keys and store them DPAPI-encrypted (see Save-R2Key).
    [switch]$SaveKey,
    # Use the stored keys instead of prompting. Lets the deploy run unattended.
    [switch]$UseStoredKey,
    # Read-only check that the stored key still works (no upload, changes nothing).
    [switch]$TestKey,
    # Non-interactive activation. Must EXACTLY equal the version being published, so it
    # can never fire by accident or be copy-pasted from an older release. Exists so the
    # owner can delegate the go-live ("activate 10.0.0") without sitting at the prompt.
    [string]$IUnderstandThisGoesLive = ""
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$FEED = "https://pub-9969ab01838a4d69bb55822f42553904.r2.dev"
$R2_ENDPOINT = "https://dcdedf1b696ea520d672ffcc49dcf26f.r2.cloudflarestorage.com"
$R2_BUCKET = "shokkerpaintbooth"

function Say($msg, $color) {
    if (-not $color) { $color = "Gray" }
    Write-Host $msg -ForegroundColor $color
}
function Head($msg) {
    Write-Host ""
    Say ("=" * 78) "Cyan"
    Say ("  " + $msg) "Cyan"
    Say ("=" * 78) "Cyan"
    Write-Host ""
}
function Die($msg) {
    Write-Host ""
    Say ("ABORT: " + $msg) "Red"
    exit 1
}

# PowerShell 5.1 turns ANY stderr output from a native exe into a NativeCommandError
# ErrorRecord, and with $ErrorActionPreference="Stop" that is TERMINATING - even when the
# exe exited 0. sync-runtime-copies.js writes a benign "stale lock reused" warning to
# stderr, which aborted this script mid-preflight. Run native tools through here: stderr
# is captured as text, and the caller decides using the real exit code.
function Invoke-Native {
    # NOTE: the parameter is ArgList, NOT Args - $Args is a PowerShell AUTOMATIC
    # variable, so naming it $Args makes the splat silently expand to nothing and the
    # command runs with no arguments (which read as "drift detected" here).
    param([string]$Exe, [string[]]$ArgList)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & $Exe @ArgList 2>&1 | Out-String
        $script:NativeExit = $LASTEXITCODE
        return $out
    } finally {
        $ErrorActionPreference = $prev
    }
}

# R2 serves latest.yml as application/yaml, and Invoke-WebRequest hands back
# Content as a Byte[] for any non-text content type - so a naive regex on
# .Content silently matches nothing and the version reads blank. Always decode.
function Get-FeedVersion($url) {
    $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30
    if ($resp.Content -is [byte[]]) {
        $text = [System.Text.Encoding]::UTF8.GetString($resp.Content)
    } else {
        $text = [string]$resp.Content
    }
    $match = [regex]::Match($text, '(?m)^version:\s*(\S+)\s*$')
    if (-not $match.Success) { throw "Feed latest.yml has no parseable top-level version." }
    return $match.Groups[1].Value
}

# ---------------------------------------------------------------- credentials
# The keys are stored with ConvertFrom-SecureString, i.e. Windows DPAPI: the ciphertext
# is bound to THIS Windows user on THIS machine and is useless if copied elsewhere. The
# plaintext is typed by the owner and never written to disk, never printed, and never
# passed on a command line. Delete the file (or rotate the token in Cloudflare) to revoke.
$CredFile = Join-Path $PSScriptRoot ".r2_credentials.xml"

function Save-R2Key {
    Head "STORE R2 KEYS (one time)"
    Say "Paste the two values from Cloudflare -> R2 -> Manage R2 API Tokens." "Yellow"
    Say "They are encrypted to your Windows account (DPAPI) - not readable by anyone else," "DarkGray"
    Say "not portable to another machine, and never shown again." "DarkGray"
    Write-Host ""
    $id = (Read-Host "R2 Access Key ID").Trim()
    $secure = Read-Host "R2 Secret Access Key" -AsSecureString
    if ((-not $id) -or (-not $secure) -or ($secure.Length -eq 0)) {
        Die "A value was blank - nothing stored."
    }
    # Catch a truncated / doubled / non-hex paste NOW, while Cloudflare still has the
    # secret on screen. Finding out at deploy time means going back for a new token.
    $problems = @()
    if ($id.Length -ne 32) { $problems += ("Access Key ID is " + $id.Length + " characters; R2 IDs are exactly 32") }
    if ($id -notmatch '^[0-9a-fA-F]+$') { $problems += "Access Key ID contains non-hex characters" }
    if ($secure.Length -ne 64) { $problems += ("Secret Access Key is " + $secure.Length + " characters; R2 secrets are exactly 64") }
    if ($problems.Count -gt 0) {
        Say "That does not look like an R2 key pair:" "Red"
        $problems | ForEach-Object { Say ("   - " + $_) "Red" }
        Write-Host ""
        Say "Nothing was stored. Re-copy BOTH values and run -SaveKey again." "Yellow"
        Say "The secret is shown only once - if it is gone, delete that token and make a new one." "Yellow"
        Say "Step-by-step: docs\R2_TOKEN_SETUP.md" "Cyan"
        exit 1
    }
    [pscustomobject]@{
        AccessKeyId = $id
        SecretCipher = ($secure | ConvertFrom-SecureString)
        Stored = (Get-Date).ToString("s")
    } | Export-Clixml -Path $CredFile
    Say ("Stored -> " + (Split-Path $CredFile -Leaf) + "  (gitignored, DPAPI-encrypted)") "Green"
    Write-Host ""
    Say "Checking the key against R2 (read-only)..." "DarkGray"
    Load-R2Key
    $t = Invoke-Native "py" @("-3", "scripts/r2_test_key.py")
    Write-Host $t
    if ($script:NativeExit -ne 0) {
        Say "The key was stored but R2 would not accept it - see above." "Red"
        Say "Fix it with another -SaveKey; the stored value is not usable yet." "Yellow"
        exit 1
    }
    Say "From now on:  .\spb_release.ps1 -Phase stage -UseStoredKey" "Cyan"
    Say "To revoke: delete that file AND delete the token in Cloudflare." "Cyan"
}

function Load-R2Key {
    if (-not (Test-Path $CredFile)) {
        Die "No stored keys. Run:  .\spb_release.ps1 -SaveKey"
    }
    $c = Import-Clixml -Path $CredFile
    $sec = $c.SecretCipher | ConvertTo-SecureString
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    $env:R2_ACCESS_KEY_ID = $c.AccessKeyId
    $env:R2_SECRET_ACCESS_KEY = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    $env:R2_ENDPOINT = $R2_ENDPOINT
    $env:R2_BUCKET = $R2_BUCKET
    Say ("Using stored key (id ends ..." + $c.AccessKeyId.Substring([Math]::Max(0, $c.AccessKeyId.Length - 4)) + ", saved " + $c.Stored + ")") "Green"
}

# ---------------------------------------------------------------- version discovery
if ($Version) {
    $ver = $Version
} else {
    $pkgPath = Join-Path $PSScriptRoot "electron-app\package.json"
    if (-not (Test-Path $pkgPath)) { Die "electron-app\package.json not found." }
    $ver = (Get-Content $pkgPath -Raw | ConvertFrom-Json).version
}
if (-not $ver) { Die "Could not determine the version." }
$packageVersion = (Get-Content (Join-Path $PSScriptRoot "electron-app\package.json") -Raw | ConvertFrom-Json).version
if ($ver -ne $packageVersion) { Die ("Requested version " + $ver + " does not match package.json " + $packageVersion + ".") }

# Brand prefix for the PayHip zip is DERIVED from build.win.artifactName
# ("ShokkerPaintBoothV10-${version}-Web-Setup.${ext}" -> "ShokkerPaintBoothV10"), so a
# rename like V8 -> V10 can never leave the kit named after the old brand.
$brand = "ShokkerPaintBooth"
try {
    $pkgJson = Get-Content (Join-Path $PSScriptRoot "electron-app\package.json") -Raw | ConvertFrom-Json
    $artPattern = $pkgJson.build.win.artifactName
    if ($artPattern) {
        $m = [regex]::Match($artPattern, '^([A-Za-z0-9]+?)-\$\{version\}')
        if ($m.Success) { $brand = $m.Groups[1].Value }
    }
} catch { }

if ($SaveKey) { Save-R2Key; exit 0 }

if ($TestKey) {
    Head "TEST STORED R2 KEY (read-only - uploads nothing, changes nothing)"
    Load-R2Key
    $t = Invoke-Native "py" @("-3", "scripts/r2_test_key.py")
    Write-Host $t
    if ($script:NativeExit -ne 0) {
        Say "Key is NOT usable. See the message above." "Red"
        exit 1
    }
    Say "Your stored key is good - no action needed." "Green"
    exit 0
}

Head ("SHOKKER PAINT BOOTH  " + $ver + "   [phase: " + $Phase + "]")

$distDir = Join-Path $PSScriptRoot "electron-app\dist"
$webDir = Join-Path $distDir "nsis-web"
$shareDir = Join-Path $PSScriptRoot "_sandbox_share"
$verCore = $ver
$evidencePath = Join-Path $PSScriptRoot ("_release_evidence\" + $verCore + "\release-evidence.json")

if ($Phase -eq "all") {
    Die "-Phase all is retired: build and human smoke are an explicit release boundary. Run build, record clean-machine evidence, then stage and activate separately."
}
if ($SkipBuild) {
    Die "-SkipBuild is retired. Stage/deploy/activate already consume existing artifacts and never rebuild; choose the explicit phase."
}

# =====================================================================================
#  VERIFY-ONLY - no credentials, safe any time
# =====================================================================================
if ($Phase -eq "verify") {
    Head "LIVE FEED"
    try {
        $liveVer = Get-FeedVersion ($FEED + "/latest.yml")
        Say ("Public feed is serving: " + $liveVer) "Green"
        if ($liveVer -eq $ver) {
            Say ("This matches the local build (" + $ver + ") - " + $ver + " is LIVE.") "Green"
        } else {
            Say ("Local build is " + $ver + " - NOT yet live.") "Yellow"
            exit 1
        }
    } catch {
        Say ("Could not read the feed: " + $_.Exception.Message) "Red"
        Say "(r2.dev can 403 for ~a minute after changes - retry.)" "DarkGray"
        exit 1
    }
    exit 0
}

function Invoke-ReleasePreflight([string]$Mode) {
    Head ("PREFLIGHT - " + $Mode + " release contract")
    $out = Invoke-Native "node" @("scripts\spb_release_preflight.js", ("--mode=" + $Mode), ("--manifest=" + $evidencePath))
    Write-Host $out
    if ($script:NativeExit -ne 0) {
        Die ("Release " + $Mode + " preflight failed. No build, upload, or activation was attempted.")
    }
}

function Acquire-R2Credentials {
    if ($UseStoredKey) { Load-R2Key } else {
        $env:R2_ENDPOINT = $R2_ENDPOINT
        $env:R2_BUCKET = $R2_BUCKET
        $env:R2_ACCESS_KEY_ID = (Read-Host "Paste R2 Access Key ID").Trim()
        $secret = Read-Host "Paste R2 Secret Access Key" -AsSecureString
        $secretPtr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
        try { $env:R2_SECRET_ACCESS_KEY = ([System.Runtime.InteropServices.Marshal]::PtrToStringAuto($secretPtr)).Trim() }
        finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPtr) }
    }
    if ((-not $env:R2_ACCESS_KEY_ID) -or (-not $env:R2_SECRET_ACCESS_KEY)) { Die "An R2 key was blank. Nothing was uploaded." }
}

function Invoke-R2ReleasePhase([string]$Flag) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & py -3 deploy_r2.py "electron-app\dist" $Flag ("--evidence=" + $evidencePath)
        $script:NativeExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    if ($script:NativeExit -ne 0) { Die ("R2 " + $Flag + " failed. The release boundary remains closed.") }
}

function Confirm-LiveFeedHash {
    $localFeed = Join-Path $webDir "latest.yml"
    if (-not (Test-Path -LiteralPath $localFeed)) { Die "Local latest.yml disappeared before confirmation." }
    $localHash = (Get-FileHash -LiteralPath $localFeed -Algorithm SHA256).Hash.ToLowerInvariant()
    for ($attempt = 1; $attempt -le 6; $attempt++) {
        $tempFeed = [System.IO.Path]::GetTempFileName()
        try {
            Invoke-WebRequest -Uri ($FEED + "/latest.yml?spb_verify=" + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()) -OutFile $tempFeed -UseBasicParsing -TimeoutSec 30 | Out-Null
            $remoteHash = (Get-FileHash -LiteralPath $tempFeed -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($remoteHash -eq $localHash) { Say ("LIVE: public latest.yml SHA-256 matches " + $localHash) "Green"; return }
            Say ("Public latest.yml is different - retry " + $attempt + "/6...") "DarkGray"
        } catch { Say ("Feed read failed - retry " + $attempt + "/6...") "DarkGray" }
        finally { Remove-Item -LiteralPath $tempFeed -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 10
    }
    Die "Activation upload returned, but the public latest.yml never matched the exact local SHA-256. Treat go-live as unconfirmed."
}

# Stage/deploy/activate consume the exact already-built candidate. They return before
# the build implementation below, so no upload-capable phase can rebuild artifacts.
if ($Phase -eq "stage" -or $Phase -eq "deploy") {
    Invoke-ReleasePreflight "prestage"
    Acquire-R2Credentials
    Head "STAGE - exact payload + web installer (latest.yml held)"
    Invoke-R2ReleasePhase "--hold-latest"
    Say "STAGED and authenticated SHA-verified. The live feed is unchanged." "Green"
    if ($Phase -eq "stage") {
        Say "Next: clean-machine test this staged installer, hash the smoke record into packagedSmoke, then:" "Yellow"
        Say ".\spb_release.ps1 -Phase activate -UseStoredKey" "Cyan"
        exit 0
    }

    Head "HUMAN BOUNDARY - confirm the staged installer"
    Say "Run the staged web installer on the clean machine, complete Gates A-F, and add the hashed packagedSmoke record." "Yellow"
    Read-Host "Press ENTER only after the human smoke boundary and evidence update are complete" | Out-Null
    Invoke-ReleasePreflight "activate"
    if ($IUnderstandThisGoesLive) {
        if ($IUnderstandThisGoesLive -ne $ver) { Die ("-IUnderstandThisGoesLive must be exactly '" + $ver + "'.") }
    } else {
        $go = Read-Host ("Type GO (capital) to publish " + $verCore + " - anything else cancels")
        if ($go -ne "GO") { Say "Cancelled. Feed unchanged; staged objects remain." "Yellow"; exit 0 }
    }
    Head ("ACTIVATE - exact latest.yml for " + $verCore)
    Invoke-R2ReleasePhase "--only-latest"
    Confirm-LiveFeedHash
    exit 0
}

if ($Phase -eq "activate") {
    Acquire-R2Credentials
    Invoke-ReleasePreflight "activate"
    Head ("ACTIVATE " + $ver + " - users will auto-update")
    if ($IUnderstandThisGoesLive) {
        if ($IUnderstandThisGoesLive -ne $ver) { Die ("-IUnderstandThisGoesLive must be exactly '" + $ver + "'.") }
    } else {
        $go = Read-Host "Type GO (capital) to publish the exact evidence-listed latest.yml - anything else cancels"
        if ($go -ne "GO") { Say "Cancelled. Feed unchanged." "Yellow"; exit 0 }
    }
    Invoke-R2ReleasePhase "--only-latest"
    Confirm-LiveFeedHash
    exit 0
}

# =====================================================================================
#  PHASE: BUILD  - NO CREDENTIALS NEEDED. Runs unattended.
# =====================================================================================
if ($Phase -eq "build") {

    Head "PREFLIGHT - version consistency"

    # config.py VERSION is what the APP DISPLAYS. It was left at 8.0.4-beta through the
    # whole 8.0.5 release, so the app under-reported itself to every user. Never again:
    # this gate fails the release if it disagrees with package.json.
    $cfg = Get-Content (Join-Path $PSScriptRoot "config.py") -Raw
    $cfgVer = ([regex]::Match($cfg, '(?m)^\s{4}VERSION:\s*str\s*=\s*"([^"]+)"')).Groups[1].Value
    $verCore = $ver
    $cfgCore = $cfgVer -replace '-beta$', '' -replace '-rc\d*$', ''
    Say ("package.json : " + $ver)
    Say ("config.py    : " + $cfgVer + "   (what the title bar shows)")
    if ($cfgCore -ne $verCore) {
        Die ("config.py VERSION (" + $cfgVer + ") does not match package.json (" + $ver + ").`n" +
             "       Fix config.py first - otherwise the app ships reporting the wrong version.")
    }
    Say "Version sources agree." "Green"

    $vtxtPath = Join-Path $PSScriptRoot "VERSION.txt"
    if (Test-Path $vtxtPath) {
        $vtxt = (Get-Content $vtxtPath -Raw).Trim()
        if ($vtxt -notlike ($verCore + "*")) {
            Say ("NOTE: VERSION.txt says '" + $vtxt + "' - cosmetic, not a blocker.") "Yellow"
        }
    }

    Head "PREFLIGHT - non-mutating trust gates"
    $preflight = Invoke-Native "node" @("scripts\spb_release_preflight.js", "--mode=prebuild", ("--manifest=" + $evidencePath))
    Write-Host $preflight
    if ($script:NativeExit -ne 0) {
        Die "Release trust gates failed. Fix the candidate tree; the release command will not rewrite or re-baseline it."
    }
    Say "Trust gates passed." "Green"

    Head "PREFLIGHT - two-copy sync (check only)"
    $chk = Invoke-Native "node" @("scripts\sync-runtime-copies.js", "--check")
    if ($script:NativeExit -ne 0) {
        Say $chk "Red"
        Die "Mirror sync check failed. Run sync deliberately before release, review it, then retry."
    }
    if ($chk -notmatch "no drift detected") {
        Say $chk "Red"
        Die "Mirror drift. The installer ships electron-app/server - a drift here ships stale code."
    }
    Say "No drift." "Green"

    # Release notes are a soft gate: warn, never block.
    $notes = Join-Path $PSScriptRoot ("RELEASE_NOTES_" + $verCore + ".md")
    if (Test-Path $notes) {
        Say ("Release notes present: RELEASE_NOTES_" + $verCore + ".md") "Green"
    } else {
        Say ("NOTE: no RELEASE_NOTES_" + $verCore + ".md - PayHip changelog will need writing.") "Yellow"
    }

    Head "BUILD - all-in-one bundle (SPB_BUNDLE_ALL=1)"
    Say "SPB_BUNDLE_ALL=1 is FORCED here. Without it the build silently omits the" "DarkGray"
    Say "premium finish packs (~1.76 GB) and nothing fails loudly. That shipped once." "DarkGray"
    Say "This takes a long while. Leave it running." "DarkGray"
    Write-Host ""
    Push-Location (Join-Path $PSScriptRoot "electron-app")
    $env:SPB_BUNDLE_ALL = "1"
    $buildOut = Invoke-Native "npm" @("run", "build")
    Write-Host $buildOut
    $buildCode = $script:NativeExit
    Pop-Location
    if ($buildCode -ne 0) { Die "npm run build failed (exit $buildCode). Nothing uploaded." }
    Say "Build finished." "Green"

    Head "GATE - payload size"
    if (-not (Test-Path $webDir)) { Die "$webDir not found - the build did not produce nsis-web artifacts." }
    $payload = Get-ChildItem (Join-Path $webDir "*.nsis.7z") -ErrorAction SilentlyContinue |
               Where-Object { $_.Name -like ("*" + $verCore + "*") } | Select-Object -First 1
    if (-not $payload) { Die ("No *" + $verCore + "*.nsis.7z payload in " + $webDir) }
    # Report BOTH units - the GB/GiB ambiguity is exactly what made this gate misfire.
    $gbDec = [math]::Round($payload.Length / 1e9, 2)
    $giB = [math]::Round($payload.Length / 1GB, 2)
    $floorBytes = $MinPayloadGB * 1e9
    Say ("Payload: " + $payload.Name)
    Say ("Size   : " + $gbDec + " GB (" + $giB + " GiB)   floor " + $MinPayloadGB + " GB")
    if ($payload.Length -lt $floorBytes) {
        Die ("Payload is only " + $gbDec + " GB - the finish packs are probably missing.`n" +
             "       Rebuild with:  cd electron-app; `$env:SPB_BUNDLE_ALL=`"1`"; npm run build")
    }
    Say "Size gate PASSED." "Green"

    $stub = Get-ChildItem (Join-Path $webDir "*Web-Setup.exe") -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like ("*" + $verCore + "*") } | Select-Object -First 1
    if (-not $stub) { Die "No *Web-Setup.exe stub found - cannot prep the installer kits." }
    Say ("Stub   : " + $stub.Name + "  (" + [math]::Round($stub.Length / 1MB, 1) + " MB)")

    Head "PREP - sandbox share + .wsb"
    if (-not (Test-Path $shareDir)) { New-Item -ItemType Directory -Path $shareDir | Out-Null }
    Copy-Item $stub.FullName -Destination $shareDir -Force
    Say ("Stub copied to _sandbox_share\" + $stub.Name) "Green"

    $wsb = Join-Path $PSScriptRoot ("SPB_" + $verCore + "_sandbox.wsb")
    if (-not (Test-Path $wsb)) {
        # vGPU disabled: avoids the "sandbox forcibly closed by host" quirk on this machine.
        $wsbBody = @"
<Configuration>
  <VGpu>Disable</VGpu>
  <MemoryInMB>8192</MemoryInMB>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>$PSScriptRoot\_sandbox_share</HostFolder>
      <SandboxFolder>C:\Users\WDAGUtilityAccount\Desktop\SPB-$verCore-Installer</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>explorer.exe C:\Users\WDAGUtilityAccount\Desktop\SPB-$verCore-Installer</Command>
  </LogonCommand>
</Configuration>
"@
        Set-Content -Path $wsb -Value $wsbBody -Encoding UTF8
        Say ("Created SPB_" + $verCore + "_sandbox.wsb") "Green"
    } else {
        Say ("SPB_" + $verCore + "_sandbox.wsb already exists.") "Green"
    }

    Head "PREP - PayHip kit"
    $payDir = Join-Path $PSScriptRoot ("_payhip_" + $verCore)
    if (-not (Test-Path $payDir)) { New-Item -ItemType Directory -Path $payDir | Out-Null }
    Copy-Item $stub.FullName -Destination $payDir -Force

    # Carry forward the most recent READ ME as the template, swapping version strings.
    $readmeOut = Join-Path $payDir "READ ME FIRST.txt"
    if (-not (Test-Path $readmeOut)) {
        $prev = Get-ChildItem (Join-Path $PSScriptRoot "_payhip_*") -Directory |
                Where-Object { Test-Path (Join-Path $_.FullName "READ ME FIRST.txt") } |
                Sort-Object Name -Descending | Select-Object -First 1
        if ($prev) {
            $tpl = Get-Content (Join-Path $prev.FullName "READ ME FIRST.txt") -Raw
            $prevVer = $prev.Name -replace '^_payhip_', ''
            $tpl = $tpl -replace [regex]::Escape($prevVer), $verCore
            Set-Content -Path $readmeOut -Value $tpl -Encoding UTF8
            Say ("READ ME built from _payhip_" + $prevVer + " (version strings swapped).") "Green"
            Say "  -> Review the WHAT'S NEW section before uploading; it still describes the old release." "Yellow"
        } else {
            Say "No previous READ ME to template from - write one before uploading." "Yellow"
        }
    } else {
        Say "READ ME already present." "Green"
    }

    $zipOut = Join-Path $PSScriptRoot ($brand + "-" + $verCore + "-Payhip.zip")
    if (Test-Path $zipOut) { Remove-Item $zipOut -Force }
    Compress-Archive -Path (Join-Path $payDir "*") -DestinationPath $zipOut -Force
    Say ("PayHip zip: " + (Split-Path $zipOut -Leaf) + "  (" +
         [math]::Round((Get-Item $zipOut).Length / 1MB, 1) + " MB)") "Green"

    Head "BUILD PHASE COMPLETE - nothing uploaded, nothing live"
    Say ("Payload  : " + $payload.Name + "  " + $gbDec + " GB") "Green"
    Say ("Stub     : " + $stub.Name) "Green"
    Say ("PayHip   : " + (Split-Path $zipOut -Leaf)) "Green"
    Say ("Sandbox  : SPB_" + $verCore + "_sandbox.wsb") "Green"
    Write-Host ""
    Say "Next:  .\spb_release.ps1 -Phase stage -UseStoredKey    (upload exact artifacts, feed untouched)" "Cyan"
    exit 0
}
