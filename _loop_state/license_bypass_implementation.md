# Developer Bypass Backdoor — Implementation Notes

Date: 2026-05-27
Author: Claude dev agent
Status: Implemented + smoke-tested. NOT committed (owner will review).

## Current flow (from investigation)

The PayHip license system is alive and well in the Electron front door. Key
files:

- `electron-app/main.js` — owns the entire flow:
  - `APP_DATA_DIR` = `%APPDATA%/ShokkerPaintBooth` (line ~128)
  - `LICENSE_FILE` = `%APPDATA%/ShokkerPaintBooth/license.dat` (AES-256-CBC
    encrypted blob containing licenseKey, email, machineId, activatedAt,
    lastVerified, offlineActivated flags)
  - `verifyWithPayhip(key)` — hits `https://payhip.com/api/v2/license/verify`
    via node:https + electron:net fallback
  - `showLicenseDialog()` — opens a 520x420 `BrowserWindow` that loads
    `license.html` with `license-preload.js` (contextIsolation ON, sandbox
    OFF). Handles `license-submit`, `license-buy`, `license-quit` IPC.
  - `checkLicenseAndActivate()` — entry point, called from `app.whenReady`
    (line ~2519). Order: contributor-test-build short-circuit → local
    license decrypt + machine-ID match → 7-day re-verify if stale → 72h
    activation grace → showLicenseDialog. If it returns anything other
    than `true` or `'grace'`, the app quits.

- `electron-app/license.html` — the dialog UI itself (vanilla HTML; key
  input + Activate/Buy/Exit buttons).
- `electron-app/license-preload.js` — minimal contextBridge exposing a
  whitelisted `electronLicense.ipcRenderer` to the renderer.

There is no Python-side license check — server.py and friends have no
`/api/license*` route. The gate is 100% Electron.

The "license system removed for the last dev shipment" comment in the
task description does NOT match what's on disk right now — PayHip is
fully wired up here.

## Integration point chosen

**Electron front door, in `electron-app/main.js` + `electron-app/license.html`.**

Why: the only license gate is here. Server has no opinion. Putting the
bypass in JS keeps it local to where the gate is, avoids a new HTTP
endpoint, and means the bypass works whether or not the embedded Python
server ever starts.

`electron-app/` is NOT in the 3-copy mirror set (which is for paint-booth-*.js,
server.py, engine/*.py). main.js, license.html, license-preload.js live
only under `electron-app/` so they were edited once.

## Files touched

| File | md5 |
|------|-----|
| `electron-app/main.js` | `506b3724c687420681eb83ea91019b67` |
| `electron-app/license.html` | `a57a973328e992e20e2f53a9fa4edbb6` |
| `electron-app/license-preload.js` | `a4e2e2b7667896951a6aad322db363d0` |
| `_loop_state/license_bypass_smoke_test.js` | `9550f2202239e31194fd397f400b7d3f` |

### What was added

**`electron-app/main.js`** (~60 new lines, just below `isContributorTestBuild`):
- `BYPASS_HASH` constant (SHA-256 hex only — plaintext passphrase never
  appears in source)
- `getBypassFlagDir()` — cross-platform: `%APPDATA%/shokker-paint-booth` on
  Windows, `~/Library/Application Support/shokker-paint-booth` on macOS,
  `~/.config/shokker-paint-booth` on Linux
- `getBypassFlagFile()` — `<dir>/bypass.json`
- `verifyBypassCode(code)` — SHA-256 hex compare, no trim (consistent with
  smoke test expectation that trailing space fails)
- `writeBypassFlag()` — mkdir -p + writes `{enabled: true, activated_at:
  <ISO>, version: 1}`
- `hasBypassFlag()` — reads + JSON.parse + checks `enabled === true`

In `showLicenseDialog`, a `bypass-result` IPC sender wired up. The
`license-bypass-submit` handler re-arms itself on failure (same pattern
as `license-submit`), and on success calls `safeResolve(true)` + closes
the window. The window's `closed` listener was updated to also
`removeAllListeners('license-bypass-submit')` on close.

In `checkLicenseAndActivate`, a `hasBypassFlag()` check is the FIRST thing
that runs — even before the contributor-build short-circuit — so once
the flag is on disk, the license dialog never appears again on that
machine for any future launch.

**`electron-app/license.html`**:
- New styles for `.bypass-link`, `#bypassPanel`, `#bypassInput`,
  `#bypassSubmit`, `#bypassStatus` (subtle dark gray, dotted underline,
  hidden by default)
- New DOM under the status div: a dimmed "Have a developer/contributor
  code?" link that toggles a hidden panel containing an input + Submit
  button + inline status
- JS: `toggleBypass()`, `doBypass()`, Enter-key handler on the input,
  and a `bypass-result` IPC listener that shows "Activated." or
  "Invalid code" (and clears the input on failure — no proximity hint)

**`electron-app/license-preload.js`**:
- Added `license-bypass-submit` to the renderer→main allowed-send list
- Added `bypass-result` to the main→renderer allowed-on list

## Smoke test results

`node _loop_state/license_bypass_smoke_test.js` — exit 0, 13/13 passed.

```
PASS  verify("SHOKKER-DEVELOPER-FRIEND-SPECIAL-55") returns true  (got true)
PASS  verify("wrong-code") returns false  (got false)
PASS  verify("") returns false  (got false)
PASS  verify("SHOKKER-DEVELOPER-FRIEND-SPECIAL-55 ") (trailing space) returns false (no trim)  (got false)
PASS  verify(null) returns false (non-string)  (got false)
PASS  verify(12345) returns false (non-string)  (got false)
PASS  flag file path ends with shokker-paint-booth\bypass.json  (got true)
PASS  writeBypassFlag wrote to expected path  (got "C:\\Users\\Ricky's PC\\AppData\\Roaming\\shokker-paint-booth\\bypass.json")
PASS  payload.enabled === true  (got true)
PASS  payload.version === 1  (got 1)
PASS  payload.activated_at is ISO-ish string  (got true)
PASS  mkdir called with recursive true  (got true)
PASS  win32 dir contains Roaming or APPDATA root  (got true)

--- Summary: 13 passed, 0 failed ---
```

Full stdout saved to `_loop_state/license_bypass_smoke_test.log`.

The smoke test does NOT write to real AppData — `fs` is mocked, so no
`bypass.json` is created on the dev machine by running the test.

## UI description

On the license activation dialog, below the `Verifying...`/error status
line and above the `Exit` button, there is a small dimmed-gray text
link that reads `Have a developer/contributor code?` (font-size 11px,
color `#555`, dotted underline). Hovering it brightens to `#888`.
Clicking it reveals a panel directly below containing:

1. A narrow centered monospace text input (`#bypassInput`, dark `#141414`
   background, gray border) with placeholder "Enter code".
2. A subdued Submit button below it (dark `#1a1a1a`, gray text).
3. A small inline status line beneath that — shows "Checking...",
   then "Activated." (info color) or "Invalid code" (error color).

On a successful submit the input field clears, the bypass flag is
written, the renderer receives a `bypass-result` event with `{ok: true}`,
and the dialog closes — the app proceeds to the main UI immediately.
Every subsequent launch sees the flag and skips the license dialog
entirely.

On a failed submit the input is cleared, "Invalid code" is shown, and
the handler re-arms so the user can try again without reopening the
panel.

## Owner instructions

To enable bypass on a machine:
1. Launch SPB.
2. On the license dialog, click the dimmed link `Have a developer/contributor code?` near the bottom.
3. Paste this code into the field that appears:
   `SHOKKER-DEVELOPER-FRIEND-SPECIAL-55`
4. Click Submit (or hit Enter). Dialog closes, app starts.
5. From now on, on this machine, the license dialog will not appear
   again. To revoke, delete:
   - Windows: `%APPDATA%\shokker-paint-booth\bypass.json`
   - macOS: `~/Library/Application Support/shokker-paint-booth/bypass.json`
   - Linux: `~/.config/shokker-paint-booth/bypass.json`

Note: the flag lives in a different folder than the normal license
storage (`%APPDATA%\ShokkerPaintBooth\license.dat`) — by design, so
revoking one doesn't disturb the other.

## Security notes

- Plaintext passphrase is never in source. Only the SHA-256 hex digest
  is hardcoded.
- The bypass file is per-machine; copying it to another machine WILL
  let that machine bypass too (no machine-ID binding here, on purpose
  since the owner wants dev/contributor handouts to be portable). If
  the owner ever wants to scope it to a single machine, the `version: 1`
  in the JSON gives us a forward-compatible upgrade path.
- The dotted-underline visual is intentionally low-contrast so casual
  users won't notice it; owner's stated policy is "it's for devs only."
