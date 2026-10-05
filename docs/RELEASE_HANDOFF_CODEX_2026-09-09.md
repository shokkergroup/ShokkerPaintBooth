# RELEASE HANDOFF — how a Shokker Paint Booth update actually gets to customers

Written 2026-09-09 by Claude for Codex, at the owner's request, after shipping 10.0.1 (2026-09-05) and
10.0.2 (2026-09-09) through the release contract end to end. Everything below was executed, not
theorized. Where a step bit us, the bite is written next to it.

Repo: `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum`, branch `codex/JuneAlphaPolish`.
Live right now: **10.0.2** (HEAD `e0cd8b3f` bookkeeping on top of candidate `7810813e`).
Evidence trail for both releases: `_release_evidence/10.0.1/` and `_release_evidence/10.0.2/` (gitignored by design).

---

## 0. The mess to fix first (Codex, this is yours)

On **2026-09-09 at 16:51:29** — after the 10.0.2 candidate was snapshotted (01:12) and staged (01:45) —
six files in the shared working tree were overwritten, all in the same second, with **older** copies:

```
paint-booth-v2.html                     (dropped the 7 script tags for js/canvas/tool-menus.js, js/spec-overlays/*, js/canvas/zone/spec-png-pixels.js;
                                         rolled ?v= cache tokens back to August)
server.py                               (247-line delta vs HEAD)
server_routes/user_import_routes.py     (REMOVED the community-drop routes: /api/user-imports/community-drop/<id>, /install-community-drop)
js/finishes/user-import-gallery.js      (REMOVED the ADD TO SPB deep-link handling + install calls)
engine/paint_v2/user_imports_ingest.py  (126 lines removed)
scripts/runtime-sync-manifest.json      (~300 entries removed)
```

Effect on the owner's LOCAL app: `paint-booth-3-canvas.js` died at line 27149 (`createQueue` of a module the
old HTML no longer loads), so `const _dispatchOwnsToolbarMode` never initialized and boot failed with
"Initialization failed — Cannot access '_dispatchOwnsToolbarMode' before initialization" plus the
"Auto-save is incomplete" banner. The electron-app/server mirror had the same stale copies (241 files).

What was done about it: the six files were restored to HEAD (= the shipped 10.0.2 content), the mirror was
resynced, the dev server refreshed. **Your overwritten versions were saved, not deleted:**
`_release_evidence/10.0.2/lane_wip_2026-09-09_overwrite/` (the six files + `wip_vs_HEAD.diff`; gitignored, on disk). If any of it was real
work, re-apply it ON TOP of HEAD `e0cd8b3f`; do not copy files from an older checkout, a different
worktree, or a stale editor buffer over the shared tree again. The SHOKK DROPS deep-link/install code
is IN 10.0.2 and verified working against the live site (a real Lyons Designs drop installed through the
packaged server); removing those routes would break ADD TO SPB in the next release.

Rules that follow from this:
1. **Work from HEAD.** `git status` before you start; if the tree is dirty with files you did not touch, stop and ask.
2. **Never bulk-write runtime files from a stale copy.** If an editor shows a file older than HEAD, reload it.
3. **During a release window (from the snapshot commit until `-Phase activate` returns), nobody edits the tree.**
   The proof binds Git HEAD and the byte hashes of 44 runtime files; any edit — even a line-ending flip —
   invalidates it and costs a 13-minute re-run. Two proofs were lost to this on 10.0.2 alone.

**Tree state when this was written (2026-09-09, evening):** HEAD `e0cd8b3f`, plus an UNCOMMITTED base-color-mode
hotfix lane in the working tree — `docs/BASE_COLOR_MODE_HOTFIX_2026-09-09.md`, `tests/base_color_mode_transport.cjs`,
and edits to `server.py`, `paint-booth-v2.html`, `paint-booth-2-state-zones.js`, `paint-booth-3-canvas.js`,
`paint-booth-5-api-render.js`, `js/zones/zone-base-color-controls.js`, `js/zones/zone-config-zone-map-controls.js`,
`server_routes/psd_layer_export_routes.py` (and their mirror copies); that lane refreshed the dev server to generation 3.
Its own doc says the shipped 10.0.2 bytes carry the preview-transport gap, so **that work is the 10.0.3 candidate**:
finish it, run its tests, commit it (Step 2 below), and take it through Steps 1–10. Do not fold unrelated work into
the same candidate, and do not touch the tree between the candidate commit and activation.

---

## 1. The shape of a release (what the owner sees vs what runs)

- Customers run the Electron app installed by `ShokkerPaintBoothV10-<ver>-Web-Setup.exe` (a 700 KB NSIS web
  stub). The stub downloads `shokker-paint-booth-v6-<ver>-x64.nsis.7z` (the payload, ~4.1 GB) from the public
  R2 bucket and installs/upgrades in place. Installed apps auto-update by reading `latest.yml` from the same
  bucket (electron-updater, generic provider). Publish URL: `https://pub-9969ab01838a4d69bb55822f42553904.r2.dev/`.
- **A version, once published, is never reused.** Hotfixes are the next patch number (10.0.2 → 10.0.3).
  electron-updater only moves customers to a HIGHER version.
- **Publishing `latest.yml` is the irreversible step.** Rollback does not un-update people who already took it.
  Payload + stub upload ("stage") is safe and reversible; the feed ("activate") is not.
- **Only the owner activates.** He types GO in chat (or runs the activate command himself). An agent never
  decides to publish.
- **The R2 credentials are never read, typed, or pasted by an agent.** The owner ran `.\spb_release.ps1 -SaveKey`
  once (DPAPI-encrypted `.r2_credentials.xml`, gitignored); every command below uses `-UseStoredKey`.
  If a key ever shows up in chat, say it must be rotated.

The whole thing is driven by `spb_release.ps1` (root) plus `deploy_r2.py`, gated by
`scripts/spb_release_preflight.js` → `scripts/spb_release_evidence_gate.js` + `scripts/spb_release_contract.js`.
Read `docs/RELEASE_PROCESS.md` (contract, "Lessons from 10.0.1", scope-outs) and `docs/SPB_RELEASE_GAUNTLET.md`
(the gate table A–H with the two dated run logs) once before your first release.

---

## 2. The exact sequence (10.0.2 took ~2.5 h wall-clock with two lost proofs; a clean run is ~1 h)

All commands from the repo root. PowerShell for `spb_release.ps1`; the rest run from bash or PowerShell alike.

### Step 1 — version bump (four sources must agree)
```
VERSION.txt                                10.0.3
electron-app/package.json  "version":     "10.0.3"
config.py   VERSION: str = "10.0.3-beta"   BUILD_TAG: str = "10.0.3"
paint-booth-5-api-render.js  const CLIENT_VERSION = '10.0.3-beta';
```
```bash
node scripts/sync-runtime-copies.js --write          # root -> electron-app/server for the manifest files
node scripts/sync-runtime-copies.js --check          # must print "no drift detected"
node scripts/spb_current_state.js --check-version    # must print one consistent identity line
```
Trap: `engine/` is check-only in the manifest. Drift there ("report-only") still fails the gate; converge it by
copying root → mirror for the listed files (root is the source of truth), then `--check` again.

### Step 2 — make the candidate tree clean and commit it
The evidence gate demands **zero rows** from `git status --porcelain=v1 --untracked-files=all` (ignored files are
fine). The tree usually carries gigabytes of lane scratch; those get **gitignored, never committed**
(`/_hype_video_work/`, `/_dlm_rebuild_work/`, `/_arca_forge_work/`, `/_website_work/` … see `.gitignore` bottom).
Runtime additions (new js/css modules referenced by `paint-booth-v2.html`, engine files, tests, docs) DO get committed.
```bash
python - <<'EOF'        # size what a commit would add; anything >20 MB or in a *_work dir gets an ignore rule
import os,subprocess;f=[x for x in subprocess.run(['git','ls-files','--others','--exclude-standard','-z'],capture_output=True).stdout.decode().split('\0') if x]
print(len(f),'files',sum(os.path.getsize(x) for x in f if os.path.exists(x))/1e6,'MB');print([x for x in f if os.path.exists(x) and os.path.getsize(x)>20e6][:10])
EOF
git add -A && git commit -m "<ver> candidate: <what it carries>"      # Co-Authored-By trailer per the session rules
git status --porcelain=v1 --untracked-files=all | wc -l                  # 0
```
Traps: `_audit/last_render_trace.json` + `render_trace_history.jsonl` are written by the server on every render —
they are gitignored now; do not re-track them. Never `git add -A` right after a BUILD (see Step 4).

### Step 3 — the cheap gates (run them before the build, fix what's red)
```bash
node scripts/spb_file_budget.js --enforce           # line-count ceilings per file (scripts/spb_file_budget.js)
node scripts/spb_generated_drift_guard.js --enforce # engine/spec_patterns.py + scorecard line baselines
node scripts/spb_context_target_lint.js             # scripts/spb_context_targets.json paths must exist
node scripts/spb_easy_regression.js --verify-plan   # plan bytes + pinned totals
node scripts/spb_layer_regression.js --verify-plan
node scripts/spb_release_preflight.js --mode=prebuild   # runs all of the above + mirror + evidence (evidence red until Step 7)
```
Owner policy 2026-09-05: if a file grew past its ceiling, raise the ceiling to current size + ~5 % WITH a dated
note in the script, and say so in the CHANGELOG. Never delete a gate.

### Step 4 — build
```bash
cd electron-app && SPB_BUNDLE_ALL=1 npm run build && cd ..     # ~6 min on the owner's box
```
`SPB_BUNDLE_ALL=1` is mandatory (without it the premium texture packs are silently omitted; look for the
`bundle-all …` lines in the log). `electron-app/package.json` must have NO `"compression"` key (an uncommitted
`"store"` once shipped a 7.0 GB payload; default LZMA gives ~4.1 GB) and must keep `!thumbnails/audit/**` excluded.
Then **undo what the build did to the mirror** — copy-server-assets writes ~160 untracked scripts, a
`_copy-manifest.json`, and 2048-only texture variants into `electron-app/server/`:
```bash
git checkout -- electron-app/server/scripts electron-app/server/_copy-manifest.json electron-app/server/assets 2>/dev/null
git clean -fdq -- electron-app/server/scripts
node scripts/sync-runtime-copies.js --write && node scripts/sync-runtime-copies.js --check   # "no drift detected"
git status --porcelain=v1 --untracked-files=all | wc -l                                       # 0 again
python scripts/release/spb_make_kits.py --version 10.0.3     # packaged-copy checks + _sandbox_share + PayHip zip + .wsb
```
`spb_make_kits.py` fails loudly if the packaged copy under `electron-app/dist/win-unpacked/resources/server/`
does not report the new version, is missing a module the HTML references, packages `thumbnails/audit`, or the
payload is suspiciously small. Fix, rebuild, re-run.

### Step 5 — the isolated proof (13 min, tree must be clean and must not be touched while it runs)
```bash
node scripts/spb_isolated_verify.js --suite all > _release_evidence/isolated-<ver>.log 2>&1
```
Boots a disposable server on a free port with external writes disabled, runs the Layer suite (95 checks; must be
95/95) and the Easy suite with fresh Chrome profiles, records the security smoke, Git HEAD, candidateClean and the
harness hashes into `_release_evidence/<config-version>/isolated-<ts>/isolated-proof.json`.
Traps: (a) the Easy runner pins the plan's exact bytes — if `scripts/shotplans/easy-mode-regression.json` was ever
re-checked-out with CRLF the runner aborts with 0 screenshots; restore the LF blob (`git show HEAD:… > file`) and
`git add` it; (b) never run it while a build or another proof is hogging CPU (0 screenshots = gate fail);
(c) never `sync --write` or edit anything while it runs.
The Easy suite has been red since the owner's 2026-09-02 first-run change (its 19 steps assume the July shell).
It is currently **scoped out** with an owner-approved, dated reason recorded in the manifest (`scopeOuts.easySuite`);
the gate prints `SCOPE-OUT` every time. Modernizing that plan is open work (WIP diff preserved at `_release_evidence/easy_plan_agent_wip_2026-09-05.diff`).

### Step 6 — the gauntlet record
The gate wants a dated five-zone gauntlet PASS on fixture `spb-chevy-truck-2048-v1` with a hashed record file.
For a FULL release, run Gates A–F of `docs/SPB_RELEASE_GAUNTLET.md` in the live app (10.0.1's record shows how each
row was verified with pixel-level checks). For a HOTFIX, write `_release_evidence/<ver>/gauntlet-record-<date>.md`
that cites the last full A–F run, lists the delta, and records the gates re-run on the new HEAD (10.0.2's record is
the template). Every edit to this file changes its hash → re-run Step 7.

### Step 7 — evidence manifest + prebuild/prestage gates
```bash
python scripts/release/spb_write_evidence.py --version 10.0.3 --proof "<isolated-proof.json path>" \
       --scope-out-easy "<owner-approved reason, >= 40 chars>"        # omit the flag once the Easy suite is green
python scripts/release/spb_add_built_evidence.py --version 10.0.3     # distributables + latest.yml (needs the PayHip zip)
node scripts/spb_release_evidence_gate.js --mode=prestage             # PASS
node scripts/spb_release_preflight.js --mode=prestage                 # all PASS
py -3 deploy_r2.py "electron-app\dist" --hold-latest --check-release-contract "--evidence=_release_evidence\10.0.3\release-evidence.json"
```
`spb_write_evidence.py` rebuilds the manifest from scratch (gitHead, sourceHash from `scripts/spb_runtime_identity`,
proof + record hashes). Run it again after ANY record edit, then `spb_add_built_evidence.py` again.

### Step 8 — stage (upload; feed untouched)
```powershell
.\spb_release.ps1 -Phase stage -UseStoredKey        # re-runs prestage preflight, uploads payload + stub with spb-sha256 metadata, HEAD-verifies
```
~20 min for 4.1 GB. Same keys are overwritten on a restage. Check room first with `.\spb_release.ps1 -TestKey`
(the owner enabled R2 billing; the bucket keeps the live payload as rollback plus the staged one).
Public check: `curl -sI https://pub-9969ab01838a4d69bb55822f42553904.r2.dev/<file>` sizes must equal the manifest.

### Step 9 — owner install test (clean machine)
Hand the owner `SPB_<ver>_sandbox.wsb` (Windows Sandbox, mapped `_sandbox_share/`, **24 GB + vGPU** or the engine
MemoryErrors) and `RELEASE_GATE_<ver>.txt`-style must-pass list. He replies PASS (or what broke). Then:
```bash
python scripts/release/spb_record_packaged_smoke.py --version 10.0.3 --summary "Owner <date>: <his words> PASS"
node scripts/spb_release_evidence_gate.js --mode=activate      # PASS
node scripts/spb_release_preflight.js --mode=activate          # all PASS
```
If the tree got dirtied meanwhile by someone else's edits: `git stash push -m "<ver> activate: parked" -- <files>`,
run the gates, activate, `git stash pop` afterwards. If the parked files are among the 44 identity files, the
stash round-trip can flip line endings and break the proof's hash even though `git status` is clean — then
`git checkout --` those files (root AND mirror), `sync --check`, and re-run Step 5. Yes, really.

### Step 10 — activate (owner's GO only), verify, bookkeeping
```powershell
.\spb_release.ps1 -Phase activate -UseStoredKey -IUnderstandThisGoesLive 10.0.3   # non-interactive form; owner said GO in chat
.\spb_release.ps1 -Phase verify                                                    # reads the public feed cold
```
Then one bookkeeping commit: CHANGELOG entry, Living Wiki (compress the board row into Recently Shipped + ONE daily
log entry), `docs/SPB_RELEASE_GAUNTLET.md` run log, and hand the owner `ShokkerPaintBooth-<ver>-Payhip.zip` +
`RELEASE_NOTES_<ver>.md` for the PayHip page (he also swaps the manual-download link at the bottom of that page
to the new stub URL).

---

## 3. Things that are NOT obvious from the scripts

- `spb_release.ps1 -Phase build` runs the prebuild preflight FIRST, and that preflight needs the evidence manifest,
  which needs the proof, which needs the clean tree — so in practice you build with `npm run build` (Step 4) and let
  the ps1 handle stage/activate/verify. Kits come from `scripts/release/spb_make_kits.py`.
- `-Phase all` is retired on purpose, and `-Phase deploy` (stage + activate in one go) exists but is not how this
  project ships: stage, then the owner's clean-machine PASS, then his GO, then activate. Three separate moments.
- The dev server at :59876 serves the working tree; the installed app serves the packaged mirror. Changing
  `server.py`/`server_v5.py` needs `python spb_server_supervisor.py refresh`. JS/CSS changes need a fresh `?v=` token
  in `paint-booth-v2.html` or Electron keeps the cached file (memory: cache-token discipline).
- The swatch warm-up worker is launched with `CREATE_NO_WINDOW` (server_v5.py + rebuild_picker_swatches.py). Do not
  put `DETACHED_PROCESS` back: it made a python console pop over the customer's app 25 s after launch.
- Windows Sandbox: `<MemoryInMB>24576</MemoryInMB>` + `<vGpu>Enable</vGpu>` or the first render MemoryErrors.
- Python's own TLS store on this box is stale (`urllib` says the r2.dev cert expired); use `curl` for public checks.
- Concurrent lanes editing `SPB_WIKI.html` are normal; park those two files during the gate window and pop after.
- An ancient `stash@{0}: WIP on main: c19df28 v6.1.1` exists. Do not pop it (it merge-conflicts four engine files).

## 4. Where the record of all this lives

`docs/RELEASE_PROCESS.md` (contract + lessons) · `docs/SPB_RELEASE_GAUNTLET.md` (gates + run logs) ·
`CHANGELOG.md` 2026-09-05 / 2026-09-09 · Living Wiki daily log those dates · `_release_evidence/10.0.1/` and
`_release_evidence/10.0.2/` (manifests, gauntlet records, packaged-smoke records, stage/activate logs) ·
`scripts/release/` (the four helpers above).
