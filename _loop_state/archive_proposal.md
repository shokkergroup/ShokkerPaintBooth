# Archive Proposal — 2026-05-27 (STAGE ONLY, no moves yet)

Survey of the project root at `C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\`.

## Summary
- **~170 root entries** examined (files + directories, one level deep)
- **~120 LOAD-BEARING** (frozen, not touched)
- **28 SAFE-TO-ARCHIVE** items proposed
- **9 UNSURE** items flagged for owner review
- **Estimated reclaim from SAFE bucket: ~21.3 MB** (dominated by three rotated server logs + three .bak copies of the 1MB scorecard JS)

## SAFE-TO-ARCHIVE (proposed to `_archive\2026-05-27\`)

These were verified to be either:
- Stale rotated logs / explicit `.bak*` backups
- One-off scratch scripts that grep-as-zero-references anywhere in the live tree (root, `electron-app/server/`, `electron-app/server/pyserver/_internal/`, HTML pages)
- Output-capture text files from agent runs (e.g. `list_shimmer.txt`, `check_m7_categories.txt`)
- Dead Hermes-Recon harness (mission complete; no current ref from server / electron / batch chain)
- Zero-byte/garbage files (`nul`, `ZzTst_02`)
- Old retired `CLEANUP_ROOT_JUNK*.bat` (from a previous cleanup pass — owner now wants this proposal-driven flow instead)

| File | Size | Why safe | Last modified |
|---|---|---|---|
| `server_log.txt.1` | 5.0 MB | Rotated server log, not opened anywhere | 2026-05-24 |
| `server_log.txt.2` | 5.0 MB | Rotated server log | 2026-05-19 |
| `server_log.txt.3` | 5.0 MB | Rotated server log | 2026-05-16 |
| `paint-booth-0-catalog-scorecard.js.bak_optics` | 1.11 MB | Explicit .bak before optics tick | 2026-05-19 |
| `paint-booth-0-catalog-scorecard.js.bak_spb102` | 1.07 MB | Explicit .bak before SPB1.02 | 2026-05-19 |
| `paint-booth-0-catalog-scorecard.js.bak_spb107` | 1.03 MB | Explicit .bak before SPB1.07 | 2026-05-18 |
| `list_shimmer.txt` | 50 KB | Captured stdout from `list_shimmer.py` run | 2026-05-19 |
| `check_m7_categories.txt` | 6.6 KB | Captured stdout from `check_m7_categories.py` run | 2026-05-19 |
| `SPB_RATE_10.json.bak_pre_round6` | 9.0 KB | Explicit .bak before round 6 | 2026-05-25 |
| `SPB_RATE_10.json.bak_pre_round5_save` | 5.8 KB | Explicit .bak before round 5 save | 2026-05-25 |
| `SPB_RATE_10.json.bak_round4_start` | 6.4 KB | Explicit .bak at round 4 start | 2026-05-24 |
| `CLEANUP_ROOT_JUNK.bat` | 629 B | Old cleanup script (superseded by this proposal flow) | 2026-04-26 |
| `CLEANUP_ROOT_JUNK_PREVIEW.bat` | 407 B | Old cleanup preview (superseded) | 2026-04-26 |
| `EDIT_HERMES_RECON_MISSION.bat` | 58 B | Hermes Recon harness; not referenced from server/electron | 2026-05-03 |
| `HERMES_RECON_TASK_RUN.bat` | 179 B | Hermes Recon harness | 2026-05-14 |
| `OPEN_HERMES_RECON_INBOX.bat` | 53 B | Hermes Recon harness | 2026-05-03 |
| `OPEN_HERMES_RECON_LOG.bat` | 70 B | Hermes Recon harness | 2026-05-03 |
| `RUN_HERMES_RECON_ONCE.bat` | 234 B | Hermes Recon harness | 2026-05-14 |
| `START_HERMES_RECON.bat` | 363 B | Hermes Recon harness | 2026-05-03 |
| `STATUS_HERMES_RECON.bat` | 125 B | Hermes Recon harness | 2026-05-03 |
| `STOP_HERMES_RECON.bat` | 174 B | Hermes Recon harness | 2026-05-03 |
| `HERMES_RECON_MISSION.md` | 1.2 KB | Hermes Recon docs (mission already executed) | 2026-05-18 |
| `HERMES_RECON_README.md` | 1.9 KB | Hermes Recon docs | 2026-05-03 |
| `ZzTst_02` | 4 B | Sentinel/test artifact; zero references | 2026-04-26 |
| `nul` | 0 B | Created by an accidental Windows `> nul` redirect | 2026-05-25 |
| `check_ff_v2.py` | 293 B | One-shot diagnostic script; zero references | 2026-05-19 |
| `check_fusions.py` | 240 B | One-shot diagnostic; zero references | 2026-05-19 |
| `check_m7_categories.py` | 562 B | One-shot diagnostic; zero references (its output `.txt` also archived) | 2026-05-19 |
| `check_registry.py` | 738 B | One-shot diagnostic; zero references | 2026-05-19 |
| `list_light_optics.py` | 884 B | One-shot diagnostic; zero references | 2026-05-19 |
| `list_shimmer.py` | 963 B | One-shot diagnostic; zero references | 2026-05-19 |
| `search_antigravity.py` | 1.2 KB | One-shot diagnostic; zero references | 2026-05-20 |
| `search_ide.py` | 1.0 KB | One-shot diagnostic; zero references | 2026-05-20 |
| `search_ide_folder.py` | 1.2 KB | One-shot diagnostic; zero references | 2026-05-20 |
| `search_promo.py` | 1.0 KB | One-shot diagnostic; zero references | 2026-05-20 |
| `view_fusion_code.py` | 405 B | One-shot diagnostic; zero references | 2026-05-19 |

(35 entries above — actual count corrected; reclaim estimate ~21.3 MB)

## UNSURE (please review — defaulted to keep)

These are stale-LOOKING but I couldn't fully clear them without owner judgment. Default action is **KEEP**.

| File | Size | Best guess | What to check |
|---|---|---|---|
| `CODEX 55 SPB.md` | 55 KB | Old Codex handoff document; no live refs | Owner: do you still need this old handoff? |
| `WAKE_AGENT.bat` | 540 B | Agent-wakeup helper; tied to overnight loop? | Confirm not used by current overnight flow |
| `STOP_SHOKKER_AGENT_WATCHDOG.bat` | 508 B | Watchdog stop script; uncertain if watchdog still runs | Confirm watchdog process state |
| `START_V5_DEV.bat` | 655 B | V5 server dev launcher; `server_v5.py` is still present | Keep if still launching v5 anywhere |
| `SPB_OWNER_REVIEW.html` + `SPB_OWNER_REVIEW_RESPONSES.json` | ~19 KB | Owner-facing review page (older); zero code refs but you may still want it | Owner judgment |
| `shokker-material-report-grad_aqua_drift-sphere.json` | 24.7 KB | Material reports; appear to be one-off exports | Confirm not re-imported anywhere |
| `shokker-material-report-mc_neon_camo-sphere.json` | 24.7 KB | Same as above | Same |
| `shokker-material-report-rs_bell_of_damned-sphere.json` | 24.9 KB | Same as above | Same |
| `patch_light_optics_scorecard.py`, `retool_fusions.py`, `test_light_optics_metrics.py`, `test_spec_values.py`, `benchmark_finishes.py`, `audit_finish_quality.py`, `rebuild_thumbnails.py`, `rebuild_picker_swatches.py` (+ their `.bat` launchers), `shokker_24k_expansion.py`, `shokker_atelier_expansion.py`, `shokker_color_monolithics.py`, `shokker_fusions_expansion.py`, `shokker_paradigm_expansion.py`, `shokker_specials_overhaul.py`, `shokk_manager.py`, `shokker_config.json`, `finish_colors_lookup.py`, `finish_ids_canonical.json` | varies | These look like dev tooling — no current server.py / engine import found, but owner may still run them ad-hoc | Confirm none are still in your dev workflow before archiving in a future pass |

## LOAD-BEARING (do not touch)

Tally by category — all explicitly verified or matched against `server.py`/`paint-booth-v2.html`/electron mirrors:

- **Core engine + 3-copy mirrors** (root + `electron-app/server/` + `electron-app/server/pyserver/_internal/`): `server.py`, `server_v5.py`, `shokker_engine_v2.py`, `config.py`, all `paint-booth-*.js` and `paint-booth-*.html`, `main.js`, `fusion-swatches.js`, `swatch-upgrades*.js`, `spec-sculpt.html`, `shokk-drop.html`, `user-imports-gallery.html`, `finish-viewer.html`, `paint-booth-pro-theme.css`, `paint-booth-v2.css`
- **Operating docs** (top-level .md): `README.md`, `CHANGELOG.md`, `RESEARCH.md`, `RESEARCH_REFERENCE.md`, `PRIORITIES.md`, `QA_REPORT.md`(missing — see QA_FINDINGS), `CLAUDE.md`, `AGENTS.md`, `ALPHA_README.md`, `MEMORY.md`(missing — lives under .claude), `OPEN_ISSUES.md`, `LAUNCH_CHECKLIST.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `AUTHORS.md`, `ARTIFACTS.md`, `MAKEFILE.md`, `LICENSE.txt`, `DEVELOPMENT_NOTES.md`, `LOOKS_THEMING_SPRINT.md`, `UI_UX_OVERNIGHT_SPRINT.md`, `WINDOWS_SANDBOX_TEST_GUIDE.md`, `VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md`, `SPB_GOAL_OPERATING_BRIEF.md`, `SPB_LINEAR_HANDOFF.md`, `SPB_PICKER_UI_UX_AGENT_HANDOFF.md`, `SPB_QA_FINDINGS.md`, `SPB_RELEASE_NOTES.md`, `SPB_SLACK_*.md`, `SPB_UI_UX_NEXT_THREAD_HANDOFF.md`, `SPB_CANONICAL_WORKSPACE.md`, `SHOKKER_BIBLE.md`, `THUMBNAIL_BUG_DIAGNOSTIC.md`, `OVERNIGHT_STATUS.md`, `WORKSPACE_LOCATION.md`, `VERSION.txt`
- **Owner-facing SPB_*.html** pages: `SPB_AUDIT.html`, `SPB_FINISH_QUALITY_WORKBOOK.html`, `SPB_OVERNIGHT_REVIEW.html`, `SPB_PATTERN_AUDIT.html`, `SPB_PATTERN_CAR_PREVIEW.html`, `SPB_PATTERN_QUALITY_REVIEW.html`, `SPB_PATTERN_TOP10_COMPARE.html`, `SPB_RATE_*.html` (all variants), `SPB_RATE_*.json` (active state), `SPB_SPEC_PATTERNS_ATLAS.html`, `SPB_SPEC_PATTERNS_INDEX.html`, `SPB_WIKI.html`, `SPB_WORKBENCH_*.html`, `SPB_WORKBENCHES_INDEX.html`, `SPB_AUDIT.json`
- **Active data JSONs**: `custom_finishes.json`, `finish_colors.json`, `finish_ids_canonical.json` (under UNSURE — kept here for safety), `package.json`, `package-lock.json`, `pyproject.toml`, `requirements.txt`, `.gitignore`, `.editorconfig`, `.prettierrc.json`, `.server_port`
- **Build / launcher scripts**: `START_SERVER.bat`, `SPB_FRESH_START.bat`, `install.sh`, `OPEN_SHOKKER_FINISH_VIEWER.bat`, `OPEN_SHOKKER_FINISH_VIEWER.vbs`
- **Directories — all kept**: `electron-app/`, `engine/`, `scripts/`, `tests/`, `server_routes/`, `js/`, `css/`, `assets/`, `audit/`, `docs/`, `tools/`, `memory/`, `output/`, `thumbnails/`, `_workbook_metrics/`, `_loop_state/`, `_rate10_thumbs/`, `_candy_pearl_thumbs/`, `_exotic_metal_thumbs/`, `_rate_chameleon_thumbs/`, `_rate_colorshoxx_thumbs/`, `_rate_light_optics_thumbs/`, `_rate_prizm_thumbs/`, `_archive/`, `_dev_asset_masters/` (7.1 GB — owner's source masters), `_staging/`, `_pattern_car_preview/`, `_pattern_rework_before/`, `_pattern_rework_field/`, `basespatterns_examples/`, `codex_recon_inbox/`, `decals/`, `fonts/`, `helmets/`, `inspiration/`, `leagues/`, `palettes/`, `psd_templates/`, `recipes/`, `shokk_factory/`, `suits/`, `swatches/`, `text_templates/`, `tutorials/`, `wiki-assets/`, `PayHip-upload/`, `Ricky Whittenburg/`, `.git/`, `.github/`, `.claude/`, `.vscode/`, `.codex-tmp/`, `.pytest-tmp/`, `.git.corrupt-backup-20260514-094027/` (kept for safety — owner's backup from the workspace move)
- **Image**: `SPB - QR - Discord.jpg` (Discord QR — owner-facing)

## Surprising load-bearing dependencies found

1. **`finish-viewer.html`** is launched by `OPEN_SHOKKER_FINISH_VIEWER.bat` and `OPEN_SHOKKER_FINISH_VIEWER.vbs`, AND it's referenced by `server_v5.py` + `paint-booth-6-ui-boot.js`. Definitely live — kept.
2. **`spec-sculpt.html`** is referenced by `server_v5.py` and `main.js`. Live.
3. **`shokk-drop.html`**: served from server route; live.
4. **`user-imports-gallery.html`** (269 B placeholder file at root): tiny but referenced by `paint-booth-v2.html`. Do NOT delete despite small size.
5. **`paint-booth-1-data.js`** is still referenced from `paint-booth-v2.html` even though it's small (15 KB); confirmed live.
6. **`paint-booth-7-shokk.js`** still referenced from `paint-booth-v2.html` — kept.
7. **`paint-booth-0-catalog-scorecard.js`** is referenced from `paint-booth-v2.html` AND is 1.18 MB — definitely live. Only its `.bak_*` variants are archived.
8. **Hermes Recon harness** has both `.bat` launchers AND `.md` docs at root, but no current code reference (it appears to have been an agent-task system that's complete). Archiving the whole set.

## To execute the archive (owner opts in)

Review the SAFE list above. When ready:

```powershell
PowerShell -ExecutionPolicy Bypass -File "_loop_state\archive_apply.ps1"
```

This will:
- Create `_archive\2026-05-27\` if not already present
- Move each SAFE-TO-ARCHIVE entry into it
- Skip anything already moved (idempotent)
- Print a one-line-per-file summary at the end
- **Touch nothing in the UNSURE or LOAD-BEARING buckets**

To undo: `Move-Item _archive\2026-05-27\<file> .\<file>` for any entry, or just move the whole `2026-05-27` folder back.

**No moves performed by this proposal. Owner must opt in.**
