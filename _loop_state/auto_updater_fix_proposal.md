# SPB Electron Auto-Updater — Diagnostic Report

**Date:** 2026-05-27
**Mode:** Diagnostic only — no code edits applied.

---

## 1. Current state (what is wired, what is missing)

### Wired correctly
- **electron-updater installed**: `electron-app/package.json:61` — `"electron-updater": "^6.8.3"`.
- **electron-builder installed**: `electron-app/package.json:21` — `"electron-builder": "^25.1.8"`.
- **Publish provider set to GitHub**: `electron-app/package.json:54-58`
  ```
  "publish": { "provider": "github", "owner": "ShokkerGroup", "repo": "ShokkerPaintBooth" }
  ```
- **Repo is public** (verified via GitHub API: `shokkergroup/ShokkerPaintBooth`, private=false, default branch=main).
- **Updater code present** in `electron-app/main.js:19, 2610-2633`:
  - `autoUpdater.autoDownload = true` (line 2614)
  - `autoUpdater.autoInstallOnAppQuit = true` (line 2615)
  - `autoUpdater.allowPrerelease = true` (line 2616)
  - `update-available`, `update-not-available`, `update-downloaded`, `error` handlers all present
  - `autoUpdater.checkForUpdates()` fires 5 seconds after `whenReady()` (line 2632)
- **`latest.yml` IS uploaded** to every release on GitHub (verified — 367 bytes each, valid YAML with version, sha512, size, path).
- **`publish` npm script exists**: `electron-app/package.json:17` → `electron-builder --win --x64 --publish always`.

### Missing / broken
- **NO code signing.** `electron-app/_build_full_log.txt:8-45` shows for every `.exe` in the build:
  ```
  no signing info identified, signing is skipped  signHook=false cscInfo=null
  ```
  No `certificateFile`, `certificateSubjectName`, `signtoolOptions`, or `CSC_LINK` anywhere in `package.json` or build scripts.
- **NO `.exe.blockmap` on most releases.** Only v6.2.0 and v5.9.x have blockmaps. v6.0.0, v6.0.1, v6.0.2, v6.1.0, v6.1.1 are missing blockmaps entirely. Without a blockmap, differential updates cannot occur — only full re-downloads, which on ~870 MB installers are slow and fragile.
- **Local `package.json` version (6.3.0) is ahead of every published GitHub release** (highest is v6.2.0). Whatever 6.3.0 work exists has never been pushed as a release, so no installed user can pull it.
- **No CI workflow that publishes releases.** `.github/workflows/ci.yml` only runs Python regression + a sync drift check. There is no `electron-builder --publish` step on tag push. All releases are manually built on the dev machine and (presumably) uploaded by hand via the GitHub web UI.
- **`allowPrerelease = true` with no `channel` set.** Several recent releases (v6.0.x, v6.1.0, v6.1.1) are flagged `prerelease=true` on GitHub. v6.2.0 is the only recent **stable** release. Without a `channel` override, electron-updater defaults to the `latest` channel and only consumes non-prerelease tags. `allowPrerelease=true` alone doesn't change channel; it allows a prerelease to be considered when explicitly fetched, but the default `latest.yml` lookup still resolves to the highest stable. This is a subtle confuser — see "Other factors."
- **Build batch file targets a stale path.** `electron-app/_build_now.bat:4` still points to `D:\Cursor - Shokker Paint Booth GOLD\Shokker Paint Booth V5\electron-app` — predates the May 2026 workspace move. Probably unused now, but suggests the build path is muddled.
- **No `dev-app-update.yml`** anywhere in the tree (not necessarily a problem; only relevant during dev testing).
- **`setFeedURL` never called** — relying entirely on `publish` config in `package.json`. That's fine *if* `app-update.yml` ends up packaged inside the asar, which electron-builder normally does. Verifiable only by inspecting a shipped build.

---

## 2. The most likely root cause

**Windows code-signing is missing.** Every binary in the build log shows `signHook=false cscInfo=null`.

electron-updater on Windows performs a publisher-name match on the **currently running executable** and the **downloaded update**: the update's signed publisher must match the installed app's signed publisher. If both are unsigned, electron-updater allows the swap **only when explicitly told** via `verifyUpdateCodeSignature: false` (or the modern equivalent `disableWebInstaller`/publisherName workarounds). The default behavior with an unsigned installed app + unsigned downloaded update is that the integrity check on Windows still attempts a publisher-name match and finds **nothing to match against**, which electron-updater logs as `"New version ... is not signed by the application owner"` and aborts the install silently — exactly the "didn't auto-update" symptom users report.

Even when the swap is attempted, Windows SmartScreen blocks an unsigned NSIS swap during `autoInstallOnAppQuit`, and the user sees nothing because the swap happens **after the app has already quit** — there's no UI to present the prompt to, and the new installer just sits in the AppData cache. Next launch boots the OLD version with no error visible to the user.

This explains the exact symptom: download appears to succeed (you see no error), but the install never completes.

---

## 3. Other contributing factors (compounding)

1. **Missing blockmaps on v6.0.x and v6.1.x.** Forces a full ~870 MB re-download on every update from those versions. Users on flaky home connections may never complete the download in one app session. electron-updater stores progress in AppData but a full restart with a partial cache often re-starts from zero.
2. **Manual release uploads.** No CI publish step means releases get uploaded by hand. Easy to forget the blockmap or `latest.yml` — and historically you DID forget blockmaps 5 releases in a row. (Auto-builder's `--publish always` generates and uploads both. The `_build_now.bat` script does NOT pass `--publish`.)
3. **Prerelease tag flag.** v6.1.0 and v6.1.1 are marked prerelease on GitHub. A user on v6.0.2 (stable) currently sees v6.2.0 as the latest. A user on v6.1.0 (prerelease) might bounce between channels in confusing ways depending on the `latest.yml` actually present at release time.
4. **Local version 6.3.0 not released.** Any owner expectation that "6.3 is out there" is wrong; nothing on GitHub is 6.3 yet. So any owner test of "will 6.2 users get 6.3?" cannot succeed because 6.3 doesn't exist on the release feed.
5. **Logger output goes to `debugLog`** (main.js:2613). If that's only console-stderr and not written to disk in the packaged build, every update failure for the last several months has been invisible. (Worth confirming where `debugLog` actually writes in production.)
6. **`oneClick: true` NSIS installer** (`package.json:35`). One-click NSIS uses per-user install in `%LocalAppData%\Programs\...` which is the correct mode for non-admin auto-updates — that part is fine. Not a problem; mentioning so you know it isn't.

---

## 4. The single biggest fix

**Add Windows code signing to the build.** Sign every release with a real OV/EV code-signing certificate, then re-publish v6.2.0 (or skip directly to v6.3.0). All future users installing the signed v6.2.0+ will then be able to auto-update to subsequent signed releases.

### Suggested edits (NOT applied)

**File: `electron-app/package.json`** — add to `"build"` block:
```json
"win": {
  "target": "nsis",
  "icon": "icon.ico",
  "artifactName": "ShokkerPaintBoothV6-${version}-Setup.${ext}",
  "certificateFile": "${env.CSC_LINK}",
  "certificatePassword": "${env.CSC_KEY_PASSWORD}",
  "signingHashAlgorithms": ["sha256"],
  "publisherName": "Shokker Group LLC",
  "verifyUpdateCodeSignature": true
}
```

Then before building, set env vars:
```
set CSC_LINK=C:\path\to\shokker-codesign.pfx
set CSC_KEY_PASSWORD=<pfx password>
```

**Cost reality:** an OV code-signing cert is roughly $90-$200/yr (SSL.com, Sectigo, Certum). EV is $300-$600/yr but eliminates SmartScreen warnings instantly. For SPB's audience (paying iRacing customers), **OV is sufficient** — SmartScreen reputation builds after a few hundred downloads and warnings stop.

### Cheaper interim fix (if cert money isn't ready today)
In `electron-app/main.js:2613`, replace the existing `autoUpdater.on('error', ...)` with code that **shows a dialog** to the user with the error and a "Download manually from GitHub" button. This won't fix the update mechanism but will stop the silent failures so users at least know they need to grab the new installer. Combined with the cert, this becomes belt-and-suspenders.

### Second-biggest fix (cheap, immediate)
**Switch the build command to publish automatically with blockmaps**. Add a GitHub Actions workflow `.github/workflows/release.yml` that runs on tag push:
```yaml
name: Release
on:
  push:
    tags: ['v*']
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd electron-app && npm ci
      - run: cd electron-app && npm run publish
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          CSC_LINK: ${{ secrets.WIN_CSC_LINK }}
          CSC_KEY_PASSWORD: ${{ secrets.WIN_CSC_KEY_PASSWORD }}
```
This guarantees blockmaps + `latest.yml` are always uploaded together, signed.

---

## 5. The "just rebuild and reship via PayHip" alternative

### Cost / benefit, honestly

**The current PayHip-reupload workaround is fine for an early-access tool with a small user base.** Realistic estimate of how often this is needed:
- Owner shipping pace: ~1 release every 2-4 weeks based on tag history (v6.0.0 → v6.2.0 in ~3 months).
- Each PayHip reupload takes the owner maybe 10-20 minutes (export, upload ~900 MB, post a Discord message).
- Users grumble but eventually click the new download link.

**Total cost of workaround per year:** ~25-40 hours of owner time + customer support friction.

**Cost of fixing auto-updater "properly":**
- Code-signing cert: ~$150/yr (OV)
- One-time setup: ~4-6 hours (cert provisioning, CI workflow, test cycle)
- Ongoing: zero — auto-updates just work

**Verdict: Fix it.** The break-even is ~1 year of dev time. But the bigger wins are:
1. **Customer experience.** Auto-update is a tier-1 expectation. "You have to redownload the whole 900 MB installer every two weeks" is a real PayHip-review-tanking complaint.
2. **Hot-fix capability.** Right now if a critical bug ships at 9pm on a Friday, every user is broken until you manually re-upload to PayHip AND every user redownloads. With working auto-update, a Saturday morning hotfix lands silently overnight.
3. **Removes a per-release foot-gun.** No more "did I remember to upload the blockmap?" — CI handles it.

**The PayHip workaround is acceptable as a stopgap for a couple weeks while the cert is being issued, but not as a long-term strategy.**

One caveat: if the owner is allergic to recurring costs and the user base is < 50 active customers, the PayHip-reupload approach is genuinely defensible. The math flips when the user base grows or release cadence increases.

---

## 6. Test plan (verify the fix on a test machine before going live)

1. **Pre-flight on dev box.**
   - Build a signed v6.3.0 with `CSC_LINK` env var set. Confirm the build log shows `signing with signtool.exe ... success` (NOT `signHook=false`).
   - Inspect the resulting `Setup.exe` with `signtool verify /pa /v dist\ShokkerPaintBoothV6-6.3.0-Setup.exe`. Should print `Successfully verified` and show "Shokker Group LLC" as the publisher.
   - Confirm `dist\latest.yml` and `dist\ShokkerPaintBoothV6-6.3.0-Setup.exe.blockmap` both exist.

2. **Staging release.**
   - Tag a **draft** release on GitHub: `v6.3.0-test`, marked as **prerelease**.
   - Upload `Setup.exe`, `latest.yml`, `.exe.blockmap`.
   - On main.js temporarily flip `allowPrerelease = true` to ensure the test box can see it (already true in current code — good).

3. **Clean-room test machine.**
   - Use a VM or spare laptop with no SPB installed.
   - Install **signed v6.2.0 first** (you'll need to rebuild and re-sign v6.2.0 to match — see step 4). Run it once, close it.
   - Promote v6.3.0-test from prerelease → release (untick the prerelease box) so the `latest` channel picks it up.
   - Launch v6.2.0. Wait ~10 seconds (5s update check + 5s buffer).
   - **Expected:** dialog appears "Version 6.3.0 is available and downloading in the background."
   - Wait for download to complete. Confirm in `%LocalAppData%\shokker-paint-booth-v6-updater\pending\` that the new `.exe` is present.
   - Quit the app. **Expected:** NSIS installer auto-runs silently, no SmartScreen prompt (because signed), app updates.
   - Relaunch. **Expected:** new version 6.3.0 boots, `[Updater] No updates available - running latest version` in the log.

4. **The chicken-and-egg problem.**
   - Existing installed v6.0–v6.2 users have **unsigned** installs. After you ship a signed v6.3.0, the updater will refuse to swap unsigned→signed (different publisher = "untrusted"). **Those users will need ONE more manual re-download from PayHip to land on the signed v6.2.x or v6.3.x baseline.** After that, every subsequent update is automatic. Communicate this in the release notes: *"One-time manual reinstall required for this version — auto-updates will work from now on."*

5. **Add a debug command** (temporary) to the running app: a hidden keystroke (e.g., Ctrl+Shift+U) that triggers `autoUpdater.checkForUpdates()` and shows a dialog with the result. Lets the owner force-test on any installed machine without waiting for the 5s startup timer.

6. **Watch the logs.** Make sure `debugLog` in production writes to a file (e.g., `%AppData%\Shokker Paint Booth V6\logs\main.log`). If it doesn't, fix that **before** the cert work — you need visibility into update errors going forward.

---

## TL;DR

- Auto-updater code is **wired correctly**. `latest.yml` is published. The repo is public.
- Builds are **unsigned**. That's the killshot — electron-updater on Windows silently refuses to swap an unsigned update.
- Missing `.exe.blockmap` files on most releases compound the issue by forcing 900 MB full re-downloads.
- **Fix:** buy an OV code-signing cert (~$150/yr), add `certificateFile` to `package.json`, add a `release.yml` GitHub Action that runs `npm run publish` on tag push. One existing-user re-install is required to bridge to the signed baseline; after that, auto-updates work forever.
- **Worth it?** Yes. Break-even vs. PayHip reuploads is under one year of owner time, and user experience improves immediately.
