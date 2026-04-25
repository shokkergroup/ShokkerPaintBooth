# Developer Troubleshooting — SPB

This is the **developer-side** troubleshooting guide. If you're a user, see `SPB_TROUBLESHOOTING.md` in the repo root — that one is written for people who don't want to read Python stack traces. This one assumes you have a terminal open and you're unafraid of `grep`.

Grouped by category. Each entry: symptom, likely cause, and the shortest path back to a working state.

---

## 1. Three-Copy Sync Failures

SPB keeps three copies of several critical files (`base_registry_data.py`, `paint-booth-0-finish-data.js`, etc.) — one at the repo root, one in `electron-app/server/`, and one in `electron-app/server/pyserver/_internal/`. Most dev-side weirdness comes from these drifting.

### Symptom: New finish works in dev, missing in packaged build

- **Cause:** You updated the root copy of `base_registry_data.py` but not the `pyserver/_internal/` copy. The Electron build ships the `_internal` one.
- **Fix:** Diff all three copies. Sync. Rebuild. See `CONVENTIONS.md` for the diff helper.

### Symptom: Pattern ID renders magenta / nothing in dev but the picker shows it

- **Cause:** `PATTERNS` and `PATTERN_GROUPS` are defined (JS side sees it) but `PATTERN_REGISTRY` (Python side) is missing the entry. The renderer silently skips unknown IDs.
- **Fix:** Add the entry to `PATTERN_REGISTRY` in `engine/patterns.py`. Sync all three copies.

### Symptom: Picker is missing a pattern you just added

- **Cause:** You added to `PATTERNS` but didn't add to `PATTERN_GROUPS`. Un-grouped IDs get removed from the picker at boot.
- **Fix:** Add the ID to the relevant group in `PATTERN_GROUPS`.

---

## 2. Python Server

### Symptom: `python.exe` hangs around after SPB closes

- **Cause:** Flask server didn't shut down cleanly — usually a long-running render thread ignoring the shutdown signal.
- **Fix:** `taskkill /F /IM python.exe` (dev only — this is brutal). Longer fix: check the shutdown handler in `server.py` around the route cleanup.

### Symptom: "Address already in use" on launch

- **Cause:** A prior `python.exe` didn't release the port.
- **Fix:** Same as above, or change the dev port in `config.py`. Don't check that change in.

### Symptom: First request after launch takes 10+ seconds

- **Cause:** Cold engine init. Normal on first render. If it happens on every request, the engine is re-initializing — look for a stray `Engine()` call inside a request handler.

### Symptom: `ModuleNotFoundError` on packaged build only

- **Cause:** A new Python dependency isn't in the bundled `pyserver/_internal/` zip.
- **Fix:** Rebuild the bundled interpreter. Ask the Release Captain which script owns it for your build — it's usually under `scripts/`.

---

## 3. Electron / Frontend

### Symptom: UI loads but renders never come back

- **Cause:** The Electron side isn't reaching the Python server. Check the devtools console for the port and verify `curl http://127.0.0.1:<port>/health`.
- **Fix:** If the port is unreachable, the Python server didn't start. Check its stdout — it's usually piped to a log in `%APPDATA%\ShokkerPaintBooth\logs\`.

### Symptom: DevTools won't open in packaged build

- **Cause:** DevTools are gated off in production. That's intentional.
- **Fix:** For debugging, run from source (`npm run dev` in `electron-app/`) or flip the dev flag documented in `docs/DEBUGGING.md`.

### Symptom: `renderZones()` is slow

- **Known issue.** DOM rebuild inefficiency, on the backlog as of 6.2.0. See `MEMORY.md` / `PRIORITIES.md`. Workaround: fewer zones.

---

## 4. Engine / Rendering

### Symptom: Chrome looks matte

- **Cause:** Spec map channels inverted. R should be 255, G should be 0, B should be 16 (not 0 — B uses an inverted scale where 16 is max gloss).
- **Fix:** Review the spec values. See `GLOSSARY.md` for the R/G/B conventions.

### Symptom: Highlights are blown out

- **Cause:** GGX floor bug. Fixed in 6.2.0 (WARN-GGX-001 through 006). If you're on an older engine, pull fixes or update.

### Symptom: `_engine_rot_debug()` output is missing

- **Cause:** That debug hook lives at `shokker_engine_v2.py` ~line 84 and is gated on an env var. Check that it's set.

---

## 5. Build & Packaging

### Symptom: Installer runs but app won't launch on a fresh Windows Sandbox

- **Cause:** Installer didn't bundle `pyserver/_internal/`. Reject the build.
- **Fix:** Look at `electron-app/copy-server-assets.js` — that's the script that stages bundled assets. Runs as part of the build; if it failed silently you'll see missing files in the staging dir.

### Symptom: App starts, splash shows old version

- **Cause:** Version string not bumped in one of several places. See `LAUNCH_CHECKLIST.md` section 5 for the full list.
- **Fix:** Grep for the old version string across the whole repo, update every hit that belongs to the current release.

### Symptom: Installer is suddenly 2x bigger

- **Cause:** Most likely something got bundled that shouldn't be — test data, golden images, a stray `node_modules`.
- **Fix:** Compare the installer's file tree to the previous release. `7z l ShokkerPaintBooth-*-Setup.exe` and diff.

---

## 6. Data / Saves

### Symptom: Shokk saved in dev won't open in packaged build

- **Cause:** Version skew in the save format. If you bumped the format mid-cycle, older parsers reject it.
- **Fix:** Guard with a version field in the save file and a migration on load. Never break format silently.

### Symptom: Shokk saved in previous version won't open in current

- **This is a release-blocker.** Do not ship. Fix the migration or rev the format header explicitly and ship a converter.

---

## 7. Environment Quirks

### Symptom: Bash commands fail in Ricky's Windows environment

- **Cause:** The path `C:\Users\Ricky's PC\` contains an apostrophe, which breaks a lot of shell tooling that doesn't quote properly.
- **Fix:** Always double-quote paths. Use forward slashes. Consider `set -u` to catch unquoted expansions.

### Symptom: Paperclip API env vars not present

- **Cause:** They're not injected in manual dev sessions.
- **Fix:** Set them locally for that session. Don't commit them.

---

## 8. When All Else Fails

1. `git status` — make sure your tree is what you think it is.
2. `git diff HEAD~5 -- engine/ electron-app/server/` — did something change under you?
3. Clean build. Delete `electron-app/node_modules/`, `electron-app/dist/`, `electron-app/server/__pycache__/`, and rebuild.
4. Run SPB in a clean Windows Sandbox (see `WINDOWS_SANDBOX_TEST_GUIDE.md`). If it works there, it's your local environment. If it fails there, it's the build.
5. Ask in `#spb-dev`. Attach logs. The answer is usually a three-copy sync issue.

---

*Last updated for 6.2.0-alpha. When you fix a recurring problem, add it here.*
