# In-App Update Banner — Implementation Notes

**Date:** 2026-05-27
**Branch:** claude/interesting-austin-f9e56a (worktree)
**Mode:** Staged. No git operations performed.

This ticket adds a "manual-but-prompted" update flow on top of the existing
electron-updater wiring (which silently fails because builds are unsigned —
see `_loop_state/auto_updater_fix_proposal.md`). The banner runs IN ADDITION
to electron-updater. The owner can yank electron-updater later if desired.

---

## Files touched (with md5s)

| File | md5 | Status |
|---|---|---|
| `electron-app/update-check.js`                                       | `a317cf7557171153fcc2820a59a5bb82` | new |
| `electron-app/main.js`                                               | `8a1629fc0e8b6b0c3eff5a6e688d610a` | modified |
| `electron-app/preload.js`                                            | `d3ded30d413abeb0349a5ed46dc61f1e` | modified |
| `electron-app/package.json`                                          | `e2cf4e6f6f08a71f7134cb8fbf1a0989` | modified |
| `paint-booth-v2.html`                                                | `9d4dba247a734318dd114d5c58b086f3` | modified |
| `electron-app/server/paint-booth-v2.html`                            | `9d4dba247a734318dd114d5c58b086f3` | modified (mirror) |
| `electron-app/server/pyserver/_internal/paint-booth-v2.html`         | `9d4dba247a734318dd114d5c58b086f3` | modified (mirror) |
| `.github/workflows/release.yml`                                      | `ee78b6a873e81937d63e5faa64a2a9ec` | new |
| `_loop_state/in_app_updater_smoke_test.js`                           | `7974b79717455bf230838853733635e6` | new |
| `_loop_state/in_app_updater_smoke_test.log`                          | `249a14d64c49cf6f1dea0c03f4c123ee` | new |

The three `paint-booth-v2.html` copies are bit-identical (same md5) — 3-copy
mirror invariant preserved.

---

## Integration architecture

```
┌─ Main process (electron-app/main.js) ─────────────────────────────────────┐
│                                                                            │
│  const updateCheck = require('./update-check.js');                        │
│                                                                            │
│  Boot sequence (after window did-finish-load):                             │
│  ┌─────────────────────────────────────────┐                              │
│  │ setTimeout(checkForUpdate, 3000)        │  ← non-blocking, fires 3s    │
│  │   → GET api.github.com/.../releases/latest                              │
│  │   → compareVersions(remote, app.getVersion())                           │
│  │   → if update available:                                                │
│  │       mainWindow.webContents.send('update-banner', {...})               │
│  └─────────────────────────────────────────┘                              │
│                                                                            │
│  Existing electron-updater code (line ~2685) UNCHANGED.                    │
│  Fires 5s after window load. Still runs, still silently fails on          │
│  unsigned builds. Banner does NOT depend on it.                            │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                              │
                              │  'update-banner' channel
                              ▼
┌─ Preload (electron-app/preload.js) ───────────────────────────────────────┐
│  ON_CHANNELS += 'update-banner'                                            │
│  Exposed via contextBridge as window.electronAPI.on('update-banner', …)   │
└────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─ Renderer (paint-booth-v2.html, top of <body>) ───────────────────────────┐
│  <div id="spbUpdateBanner" style="display:none"> ... </div>                │
│  <script>                                                                  │
│    window.electronAPI.on('update-banner', showBanner);                     │
│    // showBanner respects localStorage[spb_update_snooze_until]            │
│    // "Download Update" → electronAPI.openExternal(releaseUrl)             │
│    // "Remind Me Later" → setSnooze(24h)                                   │
│  </script>                                                                 │
└────────────────────────────────────────────────────────────────────────────┘
```

**Layout choice:** banner is `position: static` (push-down, not overlay).
It pushes the existing `<nav class="header">` down by ~40px when visible.
When hidden (default), it occupies zero vertical space. No existing UI is
covered.

**Snooze:** stored in renderer localStorage as ISO 8601 string under key
`spb_update_snooze_until`. Both the renderer banner script and the
update-check module check the same key (the module accepts an injectable
`storage` object for testing). When snoozed, the renderer suppresses the
banner display even if main pushes another event. The main-process call
itself does NOT have access to renderer localStorage, so the banner-side
snooze is the source of truth for what the user sees; the module-level
snooze is for unit tests and potential future main-process polling.

**Download Update flow:** opens GitHub releases page in the user's default
browser via the existing `open-external` IPC handler (already in the
preload allowlist). Sets a 1-hour snooze so the banner does not immediately
reappear after the user opens the tab.

---

## Smoke test results

```
node _loop_state/in_app_updater_smoke_test.js

[1] compareVersions semver correctness                  9/9   PASS
[2] snooze behavior                                     4/4   PASS
[3] checkForUpdate snooze gate                          2/2   PASS
[4] network failure handled silently                    3/3   PASS
[5] happy path — newer remote                           3/3   PASS
[6] equal/older remote                                  2/2   PASS
[7] malformed remote responses                          2/2   PASS

RESULT  pass=25  fail=0
```

Full log: `_loop_state/in_app_updater_smoke_test.log`.

Coverage:
- Numeric semver ordering (`6.3.10 > 6.3.9`, `6.2.9 < 6.3.0`, major bump).
- v-prefix stripping (`v6.3.0` == `6.3.0`).
- Prerelease tag ordering (`6.3.0-beta < 6.3.0`).
- Garbage input tolerated → comparator returns 0 (safer than throwing).
- Snooze: future timestamp suppresses banner; past timestamp allows it.
- `setSnooze(24)` writes an ISO timestamp ~24h ahead (verified within
  ±1h window to avoid clock-jitter flakes).
- Network failure: `fetchImpl` rejecting or synchronously throwing both
  resolve to `{updateAvailable: false, reason: 'network'}`.
- Happy path with mocked fetch returning `{tag_name: 'v6.3.1', ...}`.
- Malformed responses (`null`, `{}`) handled silently.

---

## Four config fixes

### (a) Blockmap publishing
Added `"differentialPackage": true` under `build.nsis` in
`electron-app/package.json`. electron-builder generates `.exe.blockmap`
files by default; the differentialPackage flag ensures they are treated as
publishable artifacts. Combined with `--publish always` in the new
workflow, blockmaps will land on every future release.

### (b) CI publish workflow
Created `.github/workflows/release.yml`. See contents at the bottom of
this doc. Triggers on `v*.*.*` tag push or manual dispatch. Uses
`windows-latest`, Node 20, installs `electron-app/` deps, runs
`copy-server`, then `npx electron-builder --win --x64 --publish always`.
The auto-provided `GITHUB_TOKEN` is mapped to `GH_TOKEN` (electron-builder
convention).

### (c) Version state
`electron-app/package.json` still shows version `6.3.0` (unchanged). The
latest stable GitHub release is `v6.2.0`. This is consistent with owner's
intent to tag 6.3.0 when ready; no bump was applied here. Owner action:
when ready to ship, run `git tag v6.3.0 && git push --tags` to fire the
release workflow.

### (d) v6.1.0 / v6.1.1 prerelease flag
**Not a code change** — these are GitHub release metadata. Owner action
item below.

---

## Owner manual action items

1. **Edit GitHub releases v6.1.0 and v6.1.1 to remove the prerelease flag
   (or delete them).** Both are currently marked `prerelease=true`,
   confusing electron-updater's channel resolution. Either:
   - In the GitHub web UI: open each release, click "Edit", uncheck
     "Set as a pre-release", save. (Recommended — preserves history.)
   - Or delete them entirely if 6.1.x was never the intended public path.

2. **GITHUB_TOKEN secret.** The workflow uses `secrets.GITHUB_TOKEN`,
   which Actions provides automatically. No action needed unless you want
   to use a PAT for cross-repo publishing — which you don't. Skip.

3. **Tag and push to test the workflow.** When ready to ship 6.3.0:
   ```
   git tag v6.3.0
   git push origin v6.3.0
   ```
   Watch the Actions tab. First run will be slow (cold npm install). On
   success, the release will appear at
   `https://github.com/shokkergroup/ShokkerPaintBooth/releases/tag/v6.3.0`
   with `Setup.exe`, `Setup.exe.blockmap`, and `latest.yml` attached.

4. **(Recommended later)** Buy an OV code-signing cert (~$90–200/yr) so
   electron-updater's silent path works again. Once signed, you can yank
   this in-app banner and let electron-updater do its job. Until then,
   the banner is the user-visible update path.

---

## release.yml contents (for quick review)

```yaml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build:
    name: Build & Publish (Windows)
    runs-on: windows-latest
    timeout-minutes: 60
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 1
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies (electron-app)
        working-directory: electron-app
        run: npm install --no-audit --no-fund
      - name: Copy server assets
        working-directory: electron-app
        run: npm run copy-server
      - name: Build & publish via electron-builder
        working-directory: electron-app
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: npx electron-builder --win --x64 --publish always
      - name: Upload build artifacts (debug / fallback)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: spb-windows-dist
          path: |
            electron-app/dist/*.exe
            electron-app/dist/*.exe.blockmap
            electron-app/dist/latest.yml
          if-no-files-found: warn
          retention-days: 7
```

---

## Honest UX prediction

**Will users click "Download Update"?**

My honest read: **~25–40% conversion within the first 2 weeks** of seeing
the banner.

Why moderate, not high:
- The banner is a friction step. It opens a browser, lands on the GitHub
  release page (which a non-dev user finds intimidating — assets, source
  zips, prerelease tags), and then asks them to re-download an 800+ MB
  installer and re-run it.
- "Remind Me Later" is right there. Some users will hit it forever.
- iRacing painters skew toward "if it works, don't break it." Many will
  ignore the prompt until something stops working.

Why not lower:
- The audience is paying customers (PayHip). They already overcame the
  payment + install hurdle once — they'll do it again for features.
- The release page IS the cleanest UX you can ship without code signing.
- Snooze means the banner doesn't enrage them; it just resurfaces daily.

**To push conversion to 60–80%** you would need either:
- Code signing → real silent auto-update (the actual fix).
- An in-app downloader that grabs the installer and `shell.openPath()`s
  it — bypasses the GitHub UI but still requires the user to click
  through the unsigned NSIS warning.

For ~60 users, this manual-but-prompted flow is the right tradeoff. You'll
see the bulk migrate within 2-3 release cycles. The stragglers will
upgrade only when a feature they need lands.
