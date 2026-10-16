# 11.0.0 beta readiness (2026-10-13) — status after the Claude fix pass

Audit by S21 below (verbatim, taken before the fixes). **Fixed since (Claude, 2026-10-13):**
- Version identity PASS: VERSION.txt `11.0.0`, config `VERSION="11.0.0-beta"` / `BUILD_TAG="11.0.0"`, `CLIENT_VERSION='11.0.0-beta'`. Also removes the startup toast "the app is v11.00 but this window is v10.0.3-beta". Header badge now reads V11.0.0, title "Shokker Paint Booth v11.0.0-beta".
- Claude connector: new gate `scripts/spb_mcpb_release_gate.py` (in every preflight mode) PASSES: 38 tools == server, version 11.0.0 == app, archive == `electron-app/server`, extracted copy starts. `.mcpb` rebuilt (sha256 b8bd7ae19df73347...).
- Claude setup (plan A/C/E, S22): 3-state setup card + update banner (detects Microsoft Store Claude Desktop), connector starts SPB when it is closed (survives Claude closing), help text updated, `GETTING_STARTED.html` now shipped + served (Guide links 404'd before).
- Mirror sync: no drift. File budget: 3 ceilings raised (owner 09-05 precedent) -> PASS. `.gitignore`: scratch dirs + `*.bak_*`.
- Tests: coexistence token test made token-agnostic; `wx_` added to the all-sizes test; golden net +7 cz_/wx_ pinned (439).
**Still open (owner):** freeze lanes + commit plan; Easy scope-out yes/no; evidence cycle; build + stage; clean-PC Sandbox smoke (incl. Claude flow); activation "go". Known-red, not release gates: 10 smart_tga fixture tests, 1 OCR test, 1 Wilds chunk-worker test, Wilds quality lock (owner review manifest).

---

# Beta readiness audit (S21, 2026-10-13)
Audit only: nothing committed/staged/built/bumped/uploaded; :59876 untouched. Evidence beside this file (`preflight_prebuild.txt`, `gate_status.txt`, `tests_v2_full.txt`, `golden_check.txt`, `all_sizes.txt`, `sync_check.txt`, `wilds_sync_report.json`).

| # | Check | Result | Command / reason |
|---|-------|--------|------------------|
| 1 | Version identity | FAIL | `node scripts/spb_current_state.js --check-version`: VERSION.txt=10.0.3, package.json=11.0.0, config VERSION+BUILD_TAG="11.00" (not SemVer), CLIENT_VERSION='10.0.3-beta'. All must agree. |
| 1b | 11.0.0 already released/staged? | NO | Live feed latest.yml = 10.0.3 (activated 09-09). `_release_evidence/` has no 11.0.0 dir (only `11.00-baseline`: local build, "public distribution not performed"). Public HEAD of `ShokkerPaintBoothV11-11.0.0-Web-Setup.exe` and the `.nsis.7z` = 404. **11.0.0 is unused: use it.** |
| 2 | `release_preflight --mode=prebuild` | FAIL (6 gate lines) | PASS: context, Layer+Easy manifests, Easy featured, fixture, generated-drift. FAIL: version identity, mirror sync, file-budget, source evidence, gitHead/sourceHash/isolated-proof hashes (all stale 10.0.3 evidence), dirty tree. See below. |
| 3 | `spb_release_gate_status.js` | FAIL | Read-only (wraps preflight status). build/stage/deploy/activate all BLOCKED; adds: no prestage artifact evidence, no packaged-smoke evidence. |
| 4a | Wilds delivery two-copy | PASS | `python scripts/spb_verify_wilds_release_sync.py --json`: 239/239 pairs. Censuses only the OLD 110 (cryptid 20/morpho 50/bloom 20/petri 20 = FIRST SET); wx_/cz_ are invisible to it, so the FIRST SET regrouping broke nothing. |
| 4b | Wilds quality lock | FAIL (old) | `python scripts/spb_wilds_quality_release_lock.py`: owner review manifest `_wilds_rejection_work/release_quality/wilds_110_owner_review_manifest.json` not on disk, 0/110 accepted. Not called by preflight or `spb_release.ps1` (only the Wilds bake + verifier): not a release gate. Re-pin = owner reviews, then writes that manifest. |
| 4c | `spb_wilds_release_gate.py` | n/a | Library, no CLI; covered by `tests/test_wilds_*` (5c). |
| 4d | Golden net (pinned hashes) | PASS | `python scripts/spb_golden_net.py --check`: 430 same, 0 changed/removed/error; advisory registry drift +170 monolithics = wx_/cz_ (unpinned). Only cos_saucer_alloy + fc_antler_bone are pinned from Wilds/Cosmos. |
| 5a | `tests_v2` | 12 red / 3692 pass | `pytest tests_v2/ -o addopts= -o filterwarnings= -p no:cacheprovider -q`, 17m19s. None from Cosmos/Wilds: 10x smart_tga "real_dlm" (missing `_smart_tga_runs` fixtures), 1x gpu_worker OCR (`_separate_image.py` absent), 1x `test_iracing_coexistence_mode_is_loaded_last_and_default_on` (pins css token `...20260824a`; HEAD already has `spb-fxkill-20260830a`: stale at HEAD). |
| 5b | all-sizes render (cos_, cz_, wx_) | PASS | Stock `tests/regression_new_categories_all_sizes_test.py` sweeps ~800 ids (alphabetical, cos_/cz_ first) and was aborted at ~37 min with no FAIL lines. Focused re-run via `_beta_prep/wx_sizes_check.py` (same `_render_once`, 5 sizes 48-2048): cos_ 60, cz_ 60, wx_ 110 ids: 0 broken, 0 over 3 s at 2048. **wx_ is not in the stock test's PREFIXES.** Needs PYTHONUTF8=1 when redirected, else emoji prints break expansion installs. |
| 5c | `tests/test_wilds_*` (3 files) | 64 pass / 1 red | `test_chunk_workers_receive_the_selected_quality_manifest`: fake worker rejects `creationflags`. Test and bake script unchanged since the 10-05 commit: pre-existing. |
| 6 | Two-copy sync | FAIL | `node scripts/sync-runtime-copies.js --check`: 2 of 16,999 differ, both live MCP-lane edits: `mcp/server/index.js` (touched 00:17 today) and `mcp/shokker-paint-booth.mcpb`. Cosmos/Wilds R2 packages and finish-data JS are in sync. |
| 7 | Claude connector `.mcpb` | FAIL | Three different builds, manifest 11.0.0 in all (= package.json, != config "11.00"): root 7,118,443 B sha 104130eb (10-12 23:58, 424 members); mirror 7,095,040 B b7f0f8f1 (10-12 20:17, 422); last win-unpacked 6,933,637 B a7dcb2b0 (10-11). Stray `*.mcpb-builder-repair-v3.backup` exists in win-unpacked only (not in source or mirror; a rebuild drops it). No build-time .mcpb gate exists (beta plan item B). |
| 8 | Git state | FAIL | Branch `codex/JuneAlphaPolish` = main + 10 commits, 0 behind (fast-forwardable); origin copy == HEAD. 736 tracked-modified + 22,570 untracked non-ignored (0.88 GB, no file over 50 MB). Gate needs 0 rows. |
| 9 | Clean-machine smoke | UNKNOWN | `WindowsSandbox.exe` is installed and 10.0.1-10.0.3 used it (`SPB_10.0.3_sandbox.wsb`); `Get-WindowsOptionalFeature` needs admin. 128 GB RAM, so the 24 GB + vGPU .wsb is fine. Needs the owner: `scripts/release/spb_record_packaged_smoke.py --version 11.0.0 --summary "..."` after stage. |
| 10 | Build prerequisites | PASS / UNKNOWN | electron-builder 25.1.8, electron 33.4.11; no `compression:"store"`; no signing config (fits "no code signing"). Free: C: 437 GB, D: 1.5 TB (last unpacked build 17.9 GB). `.r2_credentials.xml` PRESENT (DPAPI, 08-10, gitignored); env vars absent (loaded at run). R2 headroom UNKNOWN (10 GB tier; 10.0.3 payload alone is 4.16 GB). |
| 11 | Scope-outs / blockers | see below | `easySuite` scope-out lives in the 10.0.3 manifest only; it does not carry to 11.0.0. Gauntlet watchlist W1-W3 (P0) still read "In progress" (stale or real: confirm). `PRIORITIES.md` STOP-SHIP section (08-22) still says "freeze new finishes/catalog expansion"; today's +170 finishes contradict it: refresh the text or get the owner's nod. |

## Fixes for the preflight failures
- **Version identity**: VERSION.txt `11.0.0`; config `VERSION="11.0.0-beta"`, `BUILD_TAG="11.0.0"` (10.0.3 convention); CLIENT_VERSION `'11.0.0-beta'`. Decide how "11.00" shows in the UI.
- **Mirror sync**: wait for the MCP lane to stop, rebuild the .mcpb, `node scripts/sync-runtime-copies.js --write`, then `--check`.
- **File budget**: `js/features/spb-projects.js` 1202/1100, `js/zones/zone-keyboard-controls.js` 247/120, `server_routes/psd_import_routes.py` 501/280 (11.00 adoption growth). Raise the ceilings in `scripts/spb_context_targets.json` (owner OK; 09-05 precedent) or split.
- **Evidence / gitHead / sourceHash / isolated proof**: only after a clean commit: `node scripts/spb_isolated_verify.js --suite all` (~13 min), five-zone gauntlet record, `scripts/release/spb_write_evidence.py`. Easy will probably fail again: needs a fresh owner `scopeOuts.easySuite`.
- **Git hygiene**: not ignored today: `_spb_marketing_work` (12,985 files, 196 MB), `_ui_polish_2026-10-12` (1,227, 110 MB), `_wilds_r2` (151), `_cosmos_r2` (66), `_zone_cost_bench`, `_beta_prep`, `*.bak_lo3/_sculpt2/_iq3/_w3*`, `bash.exe.stackdump`, `_groups.json.stale-*`. Add ignore rules. `electron-app/server` carries ~2,700 untracked + 158 modified files from the 10-11 local build (copy-server-assets byproducts, incl. `mcp/chatgpt` audit dirs such as encyclopedia-24h, 1,116 files): revert them and `sync --write` (10.0.1 lesson).
- **Commit plan (6-8)**: (1) .gitignore; (2) version identity; (3) engine: Wilds R2, Cosmos R2, flames_v2, rev_*, registry, finish-data JS, `_groups.json`, canonical ids, golden manifest; (4) 11.00 UI/runtime (js, css, html, server_routes, scripts); (5) data/encyclopedia, docs/ai_knowledge, tutorials (Codex); (6) mcp/ shipping subset + .mcpb; (7) electron-app (package.json, copy-server-assets.js, installer.nsh), mirror last after `sync --write`; (8) wiki/CHANGELOG only AFTER activation.

## Blockers in order (fix / owner / effort)
1. **Freeze the lanes** (Codex MCP, marketing, wiki writers, S22) from commit to activation. Owner/Claude. 10 min to arrange, ~3 h frozen.
2. **Settle the .mcpb + mirror**, add the build-time .mcpb gate (plan item B). Codex finishes, Claude gate. 1-2 h.
3. **Version bump to 11.0.0**. Claude. 15 min, then sync.
4. **Raise the 3 file-budget ceilings** (owner OK first). Claude. 10 min.
5. **Ignore rules, dirty-tree cleanup, 6-8 commits**. Claude; Codex says which `mcp/chatgpt/**` dirs ship. 1-1.5 h.
6. **Evidence cycle**: isolated run, gauntlet record, manifest, Easy scope-out yes/no. Claude + owner. 1.5-2 h.
7. **Build, R2 headroom check, stage** (`spb_release.ps1 -Phase build` then `stage`). Claude. ~1.5 h plus upload. Confirm the package holds `thumbnails/picker_split/monolithic` = 3,325 files (mirror has 3,155: the 170 wx_/cz_ swatches arrive via copy-server-assets).
8. **Clean-PC smoke** in Sandbox incl. Claude Desktop connector flow (plan item F) and a 10.0.3 -> 11.0.0 auto-update (shortcut renamed to V11). Owner. 45 min.
9. **Activate** on the owner's explicit "go". Claude. 15 min.
Non-gating but promised in the beta plan: guided Claude card (A), "Claude can open SPB" (C), help-text refresh (E), all Codex; signing (D) dropped by owner. Cheap wins: add `wx_` to the all-sizes PREFIXES; pin a few wx_/cz_ in the golden net (`--add`, `--bake`).
