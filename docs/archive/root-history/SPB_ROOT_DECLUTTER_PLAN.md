I have all the classification data I need. This is a pure data-consolidation task — no repo exploration required since the classification is provided inline. Let me produce the declutter plan.

First, let me extract the `archive` files precisely. The files with `recommended_action == 'archive'` are:

1. `CODEX 55 SPB.md` → `docs/archive/handoffs/`
2. `MORNING_BRIEF_2026-05-27.md` → `docs/archive/overnight-runs/`
3. `LOOKS_THEMING_SPRINT.md` → `docs/archive/sprints/`
4. `UI_UX_OVERNIGHT_SPRINT.md` → `docs/archive/sprints/`
5. `patch_light_optics_scorecard.py` → `scripts/archive/oneoff/`
6. `retool_fusions.py` → `scripts/archive/oneoff/`
7. `_id_audit.py` → `scripts/archive/oneoff/`
8. `_id_audit2.py` → `scripts/archive/oneoff/`
9. `_route_audit.py` → `scripts/archive/oneoff/`
10. `shokker-material-report-grad_aqua_drift-sphere.json` → `docs/archive/material-reports/`
11. `shokker-material-report-mc_neon_camo-sphere.json` → `docs/archive/material-reports/`
12. `shokker-material-report-rs_bell_of_damned-sphere.json` → `docs/archive/material-reports/`
13. `_handler_names.txt` → `docs/archive/audits/`
14. `nul` → `scripts/archive/oneoff/`

(The three material-report files appear twice in the data — once as `uncertain`/`do_not_move` and once as `archive_safe`/`archive`. The `archive` verdict is the final/authoritative entry, so they go in the move plan.)

# SPB Root-Folder Declutter Plan

## 1. Headline

- **Root files reviewed:** 124 classification entries covering ~120 distinct root files (3 material-report JSONs appear twice; one duplicate-safety note on `SPB_SPEC_OVERLAY_PURGE.json`).
- **Archive-safe (recommended `archive`):** **14 files** — every one has **zero live code/build/test references** and is a dated one-off, scratch script, or stray export.
- **The rest (~106) stay put:** load-bearing code/data/entrypoints, live Flask-served HTML, generated rate-portals/workbenches, protected OSS + repo docs, and a handful of `uncertain` files awaiting your call.
- **"What to actually read" canonical set:** after archiving, your day-to-day reading collapses to **~9 docs** — `SPB_ALPHA_AUDIT.md`, `PRIORITIES.md`, `README.md`, `CLAUDE.md` / `AGENTS.md`, `CHANGELOG.md`, `OPEN_ISSUES.md`, `SPB_GOAL_OPERATING_BRIEF.md`, and `SPB_CANONICAL_WORKSPACE.md`. Everything else is either reference-on-demand or machine-owned.

## 2. Move plan (archive-only)

git mv-friendly relative paths, grouped by destination.

| Dest folder | Files moving there | One-line reason |
|---|---|---|
| `docs/archive/handoffs/` | `CODEX 55 SPB.md` | Old Codex restart/handoff doc; zero live code refs; staged archive_proposal flagged it. |
| `docs/archive/overnight-runs/` | `MORNING_BRIEF_2026-05-27.md` | Dated one-loop summary; no code/build refs; nothing points back at it. |
| `docs/archive/sprints/` | `LOOKS_THEMING_SPRINT.md`, `UI_UX_OVERNIGHT_SPRINT.md` | Dated (2026-05-19 / 05-18) sprint logs; self-refs only — **confirm with owner (archive_proposal listed as keep)**. |
| `docs/archive/material-reports/` | `shokker-material-report-grad_aqua_drift-sphere.json`, `shokker-material-report-mc_neon_camo-sphere.json`, `shokker-material-report-rs_bell_of_damned-sphere.json` | One-off finish-viewer download exports; only match the `a.download` filename pattern, never read by code. |
| `docs/archive/audits/` | `_handler_names.txt` | One-off dump of extracted JS handler names; not read by any code. |
| `scripts/archive/oneoff/` | `patch_light_optics_scorecard.py`, `retool_fusions.py`, `_id_audit.py`, `_id_audit2.py`, `_route_audit.py`, `nul` | Superseded one-shot patch/scratch scripts (not imported, not in build/pytest) + the spurious zero-byte `nul` Windows artifact. |

```json
[
  {"from": "CODEX 55 SPB.md", "to": "docs/archive/handoffs/CODEX 55 SPB.md"},
  {"from": "MORNING_BRIEF_2026-05-27.md", "to": "docs/archive/overnight-runs/MORNING_BRIEF_2026-05-27.md"},
  {"from": "LOOKS_THEMING_SPRINT.md", "to": "docs/archive/sprints/LOOKS_THEMING_SPRINT.md"},
  {"from": "UI_UX_OVERNIGHT_SPRINT.md", "to": "docs/archive/sprints/UI_UX_OVERNIGHT_SPRINT.md"},
  {"from": "shokker-material-report-grad_aqua_drift-sphere.json", "to": "docs/archive/material-reports/shokker-material-report-grad_aqua_drift-sphere.json"},
  {"from": "shokker-material-report-mc_neon_camo-sphere.json", "to": "docs/archive/material-reports/shokker-material-report-mc_neon_camo-sphere.json"},
  {"from": "shokker-material-report-rs_bell_of_damned-sphere.json", "to": "docs/archive/material-reports/shokker-material-report-rs_bell_of_damned-sphere.json"},
  {"from": "_handler_names.txt", "to": "docs/archive/audits/_handler_names.txt"},
  {"from": "patch_light_optics_scorecard.py", "to": "scripts/archive/oneoff/patch_light_optics_scorecard.py"},
  {"from": "retool_fusions.py", "to": "scripts/archive/oneoff/retool_fusions.py"},
  {"from": "_id_audit.py", "to": "scripts/archive/oneoff/_id_audit.py"},
  {"from": "_id_audit2.py", "to": "scripts/archive/oneoff/_id_audit2.py"},
  {"from": "_route_audit.py", "to": "scripts/archive/oneoff/_route_audit.py"},
  {"from": "nul", "to": "scripts/archive/oneoff/nul"}
]
```

> Apply with e.g. `git mv "CODEX 55 SPB.md" "docs/archive/handoffs/CODEX 55 SPB.md"` (create the dest folders first). Note `nul` is a reserved Windows device name — `git mv` works, but a plain shell `mv`/`del` may not; prefer `git mv -- nul scripts/archive/oneoff/nul` or delete via the repo's git tooling.

## 3. Canonical keepers (stay in root)

The short list you actually read/maintain:

| File | What it's for |
|---|---|
| `SPB_ALPHA_AUDIT.md` | Today's active audit driving this declutter; never-archive. |
| `PRIORITIES.md` | Core planning doc, cited across docs. |
| `README.md` | Repo entrypoint; never-archive. |
| `CLAUDE.md` / `AGENTS.md` | Agent operating docs, updated today; protected. |
| `CHANGELOG.md` | Standard changelog, actively maintained. |
| `OPEN_ISSUES.md` | Issue-tracking doc; protected. |
| `SPB_GOAL_OPERATING_BRIEF.md` | Durable memory for `/goal` work; cited by CLAUDE/AGENTS/README. |
| `SPB_CANONICAL_WORKSPACE.md` / `WORKSPACE_LOCATION.md` | Workspace-location tie-breaker pointers; never-archive. |
| `SPB_RELEASE_NOTES.md` | Release notes pasted into GitHub Releases. |
| `ARTIFACTS.md` | The repo's own root-artifact registry — the canonical place to track dispositions. |
| `MAKEFILE.md` | Windows command cheat sheet. |
| `RESEARCH.md` / `RESEARCH_REFERENCE.md` | Active research-steering + pointer docs. |
| `SPB_TEST_TRIAGE.md` | Active pytest-greening triage; never-archive. |
| Standard OSS set: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `AUTHORS.md` | Protected community/policy docs. |
| Release content: `ALPHA_README.md`, `LAUNCH_CHECKLIST.md`, `WINDOWS_SANDBOX_TEST_GUIDE.md` | Shipped/release walkthrough docs. |
| Build config: `package.json`, `package-lock.json` | Node/Electron manifest + lockfile. |

## 4. Active tools / uncertain — owner decides

These have no clean automated verdict. Nothing moves until you rule.

**Sprints flagged for archive but conservatively kept by the prior loop (verify before moving):**
- `LOOKS_THEMING_SPRINT.md`, `UI_UX_OVERNIGHT_SPRINT.md` — in the move plan above, but `archive_proposal.md` listed them as "operating-docs keep." Confirm they're finished.

**Uncertain docs (no code/server ref; "when in doubt, keep"):**
- `SPB_PICKER_UI_UX_AGENT_HANDOFF.md` — launch doc for still-active picker UX (SPB-70).
- `SPB_SLACK_FIRST_RUN_CHECKLIST.md`, `SPB_SLACK_INTEGRATION_PLAYBOOK.md`, `SPB_SLACK_OPERATING_SYSTEM.md` — live Slack-ops operating docs (only cross-reference each other).
- `DEVELOPMENT_NOTES.md` — ARTIFACTS flags REVIEW (predates `docs/DEVELOPMENT.md`); migrate-then-delete candidate.
- `SPB_UPDATE_SYSTEM.html` — standalone reference page, no generator/route. If archived → `docs/archive/handoffs/`.
- `SPB_RATE_FINISH.html` — early standalone rater (SPB-89), superseded by the portal system. If archived → `docs/archive/rate-sessions/`.
- `SPB_OWNER_REVIEW.html` + `SPB_OWNER_REVIEW_RESPONSES.json` — owner questionnaire + saved real owner answers (2026-05-15). If archived → `docs/archive/owner-reviews/`.

**Uncertain root tests (NOT collected by pytest `testpaths=['tests']`):**
- `test_spec_values.py` — `SPB_ALPHA_AUDIT.md` (TEST-05) flags its iron-rule invariants to be ported into `tests/`; **keep until ported.**
- `test_light_optics_metrics.py` — captures Light Optics invariants worth porting (TEST-05 family); triage to `tests/`.

**Active rate portals / workbenches (live tooling, do not move) — listed so you can prune any you've retired:**
- Portal raters wired into `scripts/rate_portals_config.py`: `SPB_RATE_LIGHT_OPTICS`, `SPB_RATE_PRIZM`, `SPB_RATE_CHAMELEON`, `SPB_RATE_COLORSHOXX`, `SPB_RATE_FORBIDDEN_DRAGON`, `SPB_RATE_MONEY_SHOKK` (each `.html` + `.json`) plus `SPB_RATE_PORTALS_INDEX.html`.
- Off-config but still script-referenced: `SPB_RATE_EXOTIC_METAL.*`, `SPB_RATE_CANDY_PEARL.*` (render/notes scripts).
- Generated workbenches from `scripts/build_category_workbench.py`: `SPB_WORKBENCHES_INDEX.html`, `SPB_FINISH_QUALITY_WORKBOOK.html`, and all 28 `SPB_WORKBENCH_*.html` category files (incl. near-duplicate-looking but distinct categories: `RACE_HERITAGE` vs `RACING_HERITAGE`, `SPARKLE` vs `SPARKLE_SYSTEMS`, `WEATHER_AGE` vs `WEATHERED_AGED`).
- Other generated surfaces: `SPB_PATTERN_CAR_PREVIEW.html`, `SPB_PATTERN_TOP10_COMPARE.html`, `SPB_OVERNIGHT_REVIEW.html` (regeneratable — prune the stale copy only if you want).
- Active QA/build scripts kept in root: `audit_finish_quality.py`, `benchmark_finishes.py`, `rebuild_thumbnails.py`, `rebuild_picker_swatches.py` (+ their `.bat` wrappers), launchers `START_SERVER.bat`, `SPB_FRESH_START.bat`, `START_V5_DEV.bat` (keep until V5 confirmed retired), `OPEN_SHOKKER_FINISH_VIEWER.bat/.vbs`, `WAKE_AGENT.bat`, `STOP_SHOKKER_AGENT_WATCHDOG.bat`, and the `SPB - QR - Discord.jpg` asset.

## 5. Do-not-move (load-bearing) — a future cleanup MUST NOT touch these

- **App entrypoint HTML served by Flask + Electron:** `paint-booth-v2.html` (served at `/`), `finish-viewer.html`, `spec-sculpt.html`, `shokk-drop.html`, `SHOKK_DROP_BIBLE.html`, `user-imports-gallery.html`, `SPB_PATTERN_AUDIT.html`, `SPB_PATTERN_QUALITY_REVIEW.html`, `SPB_AUDIT.html`, `SPB_SPEC_PATTERNS_ATLAS.html`, `SPB_SPEC_PATTERNS_INDEX.html`, `SPEC_OVERLAY_PURGE.html`, `SPB_RATE_10.html`.
- **Live state JSON read/written by servers:** `SPB_AUDIT.json`, `SPB_RATE_10.json`, `SPB_SPEC_OVERLAY_PURGE.json`.
- **`SPB_WIKI.html`** — read and asserted against by the regression test suite (`tests/test_regression_toolbar_alpha_safety.py`); archiving breaks tests.
- **Runtime-imported engine shims (code beats docs/.gitignore that say "ARCHIVE"):** `shokker_24k_expansion.py`, `shokker_atelier_expansion.py`, `shokker_fusions_expansion.py`, `shokker_paradigm_expansion.py`, `shokker_color_monolithics.py`, `shokker_specials_overhaul.py` — imported by `shokker_engine_v2.py`, engine/routes, in the Electron build manifest, and asserted by `tests/test_regression_runtime_mirror_coverage.py`.
- **Core module:** `finish_colors_lookup.py` (`get_finish_colors` imported all over `server.py` + routes; in the build manifest).
- **Protected data/config JSON:** `custom_finishes.json`, `finish_colors.json`, `finish_ids_canonical.json`, `shokker_config.json`.
- **Code-referenced doctrine docs:** `SHOKKER_BIBLE.md` (ID-contract source in shipped JS), `VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md` (referenced by engine source), `THUMBNAIL_BUG_DIAGNOSTIC.md` (named in `server.py`), `OVERNIGHT_STATUS.md` (written by `scripts/overnight_finish_worker.py`).
- **Runtime-sliced handoff:** `SPB_LINEAR_HANDOFF.md` — read by `scripts/spb_context.js` via `spb_context_targets.json` (slice entries at lines 1720/1752); moving it without editing the manifest breaks that tool.

## 6. Draft: `docs/archive/INDEX.md`

```markdown
# Archive Index

This folder holds root-level files that were **archived during the 2026-05-29 declutter**
(driven by `SPB_ALPHA_AUDIT.md`). Everything here is dated, one-off, or stray output with
**zero live code/build/test references** at the time of archival. Nothing here is loaded by
the app, the engine, the servers, or the test suite.

> If you are looking for the current canonical docs, **do NOT read this archive.**
> See "Read these, ignore the archive" at the bottom.

## What moved (from -> to)

| From (repo root) | To | Why archived |
|---|---|---|
| `CODEX 55 SPB.md` | `docs/archive/handoffs/CODEX 55 SPB.md` | Old Codex restart/handoff doc; no live refs. |
| `SPB_UPDATE_SYSTEM.html` *(if owner confirms)* | `docs/archive/handoffs/SPB_UPDATE_SYSTEM.html` | Standalone reference page; no generator/route. |
| `MORNING_BRIEF_2026-05-27.md` | `docs/archive/overnight-runs/MORNING_BRIEF_2026-05-27.md` | Dated one-loop summary; nothing references it. |
| `LOOKS_THEMING_SPRINT.md` | `docs/archive/sprints/LOOKS_THEMING_SPRINT.md` | Dated 2026-05-19 sprint log; self-refs only. |
| `UI_UX_OVERNIGHT_SPRINT.md` | `docs/archive/sprints/UI_UX_OVERNIGHT_SPRINT.md` | Dated 2026-05-18 sprint log; self-refs only. |
| `shokker-material-report-grad_aqua_drift-sphere.json` | `docs/archive/material-reports/…` | One-off finish-viewer export; never read by code. |
| `shokker-material-report-mc_neon_camo-sphere.json` | `docs/archive/material-reports/…` | One-off finish-viewer export; never read by code. |
| `shokker-material-report-rs_bell_of_damned-sphere.json` | `docs/archive/material-reports/…` | One-off finish-viewer export; never read by code. |
| `SPB_OWNER_REVIEW_RESPONSES.json` *(if owner confirms)* | `docs/archive/owner-reviews/…` | Saved owner answers (2026-05-15); no live ref. |
| `SPB_RATE_FINISH.html` *(if owner confirms)* | `docs/archive/rate-sessions/…` | Early rater (SPB-89) superseded by portal system. |
| `_handler_names.txt` | `docs/archive/audits/_handler_names.txt` | One-off dump of extracted JS handler names. |
| `patch_light_optics_scorecard.py` | `scripts/archive/oneoff/…` | One-shot scorecard patch (May 19); not imported. |
| `retool_fusions.py` | `scripts/archive/oneoff/…` | One-shot fusions retool (May 19); no refs. |
| `_id_audit.py` | `scripts/archive/oneoff/…` | Throwaway getElementById diff scratch (May 27). |
| `_id_audit2.py` | `scripts/archive/oneoff/…` | Throwaway variant of `_id_audit.py`. |
| `_route_audit.py` | `scripts/archive/oneoff/…` | Throwaway UI-fetch-vs-route check (May 27). |
| `nul` | `scripts/archive/oneoff/nul` | Spurious zero-byte Windows `>nul` artifact (junk). |

*(Rows marked "if owner confirms" are owner-decision items, not part of the automatic move set.)*

## Restoring something

Everything was moved with `git mv`, so history is intact:
`git log --follow docs/archive/<path>` and `git mv` it back to root if it turns out to be needed.

## Read these N docs, ignore the archive

For current work, the canonical reading set is **9 docs** (all in repo root):

1. `SPB_ALPHA_AUDIT.md` — active audit / current priorities.
2. `PRIORITIES.md` — planning.
3. `README.md` — repo entrypoint.
4. `CLAUDE.md` + `AGENTS.md` — agent operating docs.
5. `CHANGELOG.md` — what shipped.
6. `OPEN_ISSUES.md` — open work.
7. `SPB_GOAL_OPERATING_BRIEF.md` — durable `/goal` memory.
8. `SPB_CANONICAL_WORKSPACE.md` (+ `WORKSPACE_LOCATION.md`) — where the real workspace lives.
9. `ARTIFACTS.md` — the live registry of every root artifact and its disposition.

Reference-on-demand (not daily): `SHOKKER_BIBLE.md`, `VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md`,
`MAKEFILE.md`, `RESEARCH.md`. Everything under `docs/archive/` is historical — skip it unless
you are specifically chasing the history of one of the items listed above.
```