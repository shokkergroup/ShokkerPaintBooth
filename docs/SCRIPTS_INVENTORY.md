# scripts/ Inventory

WIN #43 — read-only inventory of `scripts/` to help the owner declutter later.

DOC ONLY. Nothing in this file has been moved, deleted, or modified. Every
RECOMMEND-ARCHIVE marker below is a recommendation only.

## Method and honesty note

`scripts/` is large (~240 entries). I did NOT read all ~240 docstrings; doing so
reliably is not feasible on this network-mounted checkout (Read/Grep intermittently
serve stale/garbled output). Classification is grounded in authoritative sources:

- root `package.json` `scripts` block (verified read)
- `electron-app/package.json` `scripts` block (verified read)
- `.github/workflows/ci.yml` (verified read)
- `scripts/README.md`, `scripts/README_AUDITS.md`, `scripts/RUNTIME_SYNC.md`
  (the directory's own self-description, verified read)
- spot-read docstrings (`spb_doctor.py`, `spb_guard_zone_base_overlay.js`,
  `spb_release_gate_status.js`) and filename-convention families

Where a classification is by convention/family rather than a per-file docstring
read it is marked (by family) and should be confirmed before any file is moved.
This is a declutter starting point, not a delete list.

Classification key:

- live-tool: invoked by CI or an npm script, or part of a coherent
  actively-maintained tooling family (sync, guards, doctor, audit toolchain).
- one-shot-historical: per `scripts/README.md` / `README_AUDITS.md`, a one-shot
  from a specific catalog/pattern rebuild effort; kept for reference, not in any
  automated pipeline.
- unknown: not wired and not clearly historical; needs an owner glance.

## Authoritative wiring (ground truth)

### root package.json -> scripts/

Only ONE `scripts/` file is referenced by the root `package.json`:

- `sync-runtime` -> `node scripts/sync-runtime-copies.js --write`
- `check-runtime-sync` -> `node scripts/sync-runtime-copies.js --check`

(Other root scripts do not call into `scripts/`: `check:catalog` ->
`tests/_runtime_harness/validate_finish_data.mjs`; `check:js` -> inline
`node --check paint-booth-*.js`; `export:dna-bible` -> `tools/...`;
`test*` -> pytest. None of those live in `scripts/`.)

### electron-app/package.json -> scripts/

- `sync-runtime` -> `node ../scripts/sync-runtime-copies.js --write`
- `check-runtime-sync` -> `node ../scripts/sync-runtime-copies.js --check`

(`copy-server` -> `copy-server-assets.js`, which per RUNTIME_SYNC.md programmatically
calls `sync-runtime-copies.js` before packaging.)

### ci.yml -> scripts/

CI (verified earlier full read) runs `node scripts/sync-runtime-copies.js --check`
(runtime mirror drift), plus `npm run check:js`, the report-only
`node scripts/check-js-lint.mjs`, and `npm run check:catalog`. The only hard
dependency on a `scripts/` file is `sync-runtime-copies.js`; `check-js-lint.mjs`
is report-only (continue-on-error).

> Correction note: an earlier draft of this file invented npm scripts
> (`sync`, `check:sync`, `lint:js`, `format:check`) and Python scripts
> (`deploy_check.py`, `audit_catalog.py`, `generate_catalog_from_spec.py`,
> `build_full_catalog.py`, `apply_full_catalog.py`, `migrate_specs.py`,
> `seed_examples.py`, etc.) that do NOT exist. The wiring above is the real,
> verified wiring; those invented entries have been removed.

## live-tool — directly wired (keep)

| Script | Purpose | Wired by |
|---|---|---|
| `sync-runtime-copies.js` | THE runtime 3-copy mirror sync/check (root UI/runtime files -> `electron-app/server/` and `.../pyserver/_internal/`). Driven by `runtime-sync-manifest.json`. Do not run `--write` by hand; orchestrator/build owns it. | ci.yml, root + electron-app package.json |
| `runtime-sync-manifest.json` | Declarative manifest (managed files + target dirs) consumed by the sync script. | sync-runtime-copies.js |
| `check-js-lint.mjs` | JS lint runner (degrades gracefully if eslint absent). | ci.yml (report-only) |

## live-tool — coherent maintained families (keep; run manually / by other tooling)

| Family (approx count) | Purpose | Evidence |
|---|---|---|
| `spb_guard_zone_*.js`, `spb_guard_swatch_popup_*.js`, `spb_guard_server_*.js`, `spb_guard_*.js` (~110 files) | Extraction-safety contract guards: each asserts a control block in a `paint-booth-*.js` / `paint-booth-v2.html` / `server.py` still exposes its public contract after refactor; exits non-zero on drift. | docstring of `spb_guard_zone_base_overlay.js` reads root UI files + builds a `failures[]` list. (by family) |
| `spb_doctor.py` | One-command read-only checkout health report (py + deps, engine import + registry counts, runtime-sync drift via `--check` only, catalog integrity). Contributor preflight. | docstring read. |
| `spb_file_budget.js`, `spb_line_count.js`, `spb_guard_line_count.js`, `spb_release_gate_status.js` | File-size / line-count budgets + release-gate status (`spb_release_gate_status.js` invokes `spb_file_budget.js`). | `spb_release_gate_status.js` line 21 read; rest (by family). |
| `spb_context.js`, `spb_context_targets.json`, `spb93_context.js` | Context/target data + helper for the guard/budget tooling. | filenames + family. (by family) |
| `spb_check_stylesheet_links.js`, `spb_generated_drift_guard.js`, `check-format.mjs`, `spb_extract_css_block.js` | JS/CSS structural checks + extraction helpers. NOTE: not found in the current root package.json scripts; likely run ad hoc or by an outer harness. | filenames. (by family) |
| `spb_smoke_server_routes.py`, `spb_smoke_zone_boot_http.js`, `_mshcb_smoke.py` | Smoke checks (server routes / zone boot / money-shokk). | filenames. (by family) |

## live-tool — audit/quality toolchain (keep; run manually per README_AUDITS.md)

`README_AUDITS.md` documents these as the manual quality toolchain (mirrored by
pytest regression tests in CI, not run directly in CI):

- Doctrine audits: `audit_spec_driven_paint_neutrality.py`,
  `audit_spec_driven_spec_richness.py`,
  `audit_pattern_design_paint_richness.py`, `audit_pattern_image_chroma.py`,
  `audit_registry_placeholders.py`
- Perf: `audit_render_perf.py`
- Owner-gated patches (default dry-run; `--apply` to commit):
  `spb77_apply_ungrouped_remap.py`, `spb94_apply_pattern_image_remap.py`,
  `spb79_apply_gradient_split.py`
- Status/dashboards: `spb_compliance_status.py`, `spb86_micro_preview_sheet.py`
- M-metric pipeline: `spb_workbook_compute_m1.py` .. `m8.py` (+ `m9.py`)
- Other scorers/reports: `spb_spm7/8/10_score.py`, `spm9_score.py`,
  `spb_catalog_report.py`, `spb_catalog_scorecard.py`, `spb_visual_diff.py`,
  `spb_scorecard_drift_summary.py`, `audit_pattern_quality.py`,
  `audit_spec_pattern_quality.py`, `audit_pattern_paint_chroma.py`,
  `audit_pattern_image_chroma.py`

Keep all of these. But see "version-churn candidates" — the versioned scorers
and M-passes accumulate and are the cleanest archive opportunity.

## one-shot-historical — RECOMMEND-ARCHIVE (by README + filename family)

`scripts/README.md`: "Most `.py` files in this folder are one-shot
generators/auditors run by hand during engine refactors." None of the following
are referenced by CI or any package.json. (by family — confirm the top-of-file
before moving any specific one.)

- Cultural/themed one-shots: `build_cultural_forbidden_dragon.py`,
  `build_cultural_grunge_fun.py`, `build_cultural_viva_mexico.py`,
  `move_grunge_fun_category.py`, `refresh_grunge_fun_manifest_names.py`,
  `repair_cultural_finishes_js.py`, `bake_cultural_jpg_runtime.py`,
  `rebuild_rising_sun_specs.py`, `bake_union_jacked_specs.py`,
  `bake_union_jacked_jpg_runtime.py`, `union_jacked_footer_ocr.py`,
  `process_union_jacked_assets.py`, `sync_union_jacked_finish_data.py`,
  `build_finish_tags.py`.
- Round/sweep trackers + numbered patches: `build_round5_targeted_tracker.py`,
  `extend_round5_full_sweep.py`, `extend_round5_tracker.py`,
  `verify_round4_rebuilds.py`, `spb86_gain_sweep.py`,
  `spb86_micro_preview_sheet.py`, `spb86_probe_real_weak_clusters.py`,
  `spb77_apply_ungrouped_remap.py`, `spb79_apply_gradient_split.py`,
  `spb94_apply_pattern_image_remap.py` (the apply_* are owner-gated tools per
  README_AUDITS — keep if the remaps may be re-run; otherwise historical).
- Rate-portal/reference one-shots: `bootstrap_rate_portals.py`,
  `generate_rate_portal_queue.py`, `render_rate_portal_thumbs.py`,
  `render_rate10_thumbs.py`, `retire_rate10_visible_for_reference_rebuild.py`,
  `build_colorshoxx_ai_reference_batch.py`,
  `build_ricky_reference_spec_overlays.py`,
  `build_ricky_reference_batch2_spec_overlays.py`,
  `verify_ricky_reference_batch2.py`, `patch_ricky_reference_finish_data.py`,
  `colorshoxx_desc_audit.py`, `demo_user_import_dna.py`.
- Spec-overlay regroup/purge one-shots:
  `generate_spec_overlay_definitive_catalog.py`,
  `generate_spec_overlay_purge_catalog.py`,
  `render_spec_overlay_definitive_thumbs.py`,
  `render_spec_overlay_purge_thumbs.py`,
  `patch_definitive_spec_finish_data.py`,
  `consolidate_spec_pattern_categories.py`.
- Candy/exotic/money-shokk one-shots: `render_candy_pearl_thumbs.py`,
  `render_exotic_metal_thumbs.py`, `generate_candy_pearl_audit_queue.py`,
  `generate_exotic_metal_audit_queue.py`, `spb_read_candy_pearl_notes.py`,
  `spb_read_exotic_metal_notes.py`, `spb_read_rate_portal_notes.py`,
  `archive_money_shokk_v1_thumbs.py`.
- Early catalog one-shots (per README "Python helpers"):
  `export_finish_ids.py`, `extract_finish_colors.py`, `extract_spec_paint.py`,
  `generate_smilexx_upgraded.py`, `import_abstract_experimental_patterns.py`,
  `remove_cs_block.py`, `remove_spec_paint_block.py`, `split_engine.py`,
  `build_special_groups.py` (+ generated output `special_groups_output.js`),
  `list_patterns_by_category.py`, `mono_ids_backend.txt`,
  `bake_pattern_thumbnails.sh`, `bake_pattern_thumbnails.bat`.
- Misc rebake/patch/diagnose one-shots: `rebake_directional_grain.py`,
  `rebake_ghost_depth_thumbnails.py`, `rebake_spectrum_shift_all.py`,
  `rebake_tick94_categories.py`, `patch_spectrum_js_data.py`,
  `spb_wire_spectrum_prism_ui.py`, `cleanup-root-temp-junk.py`,
  `diagnose_iracing_spec_package.py`, `optimize_spec_for_trading_paints.py`,
  `bake_efx_spec_previews.py`, `bake_spec_driven_thumbnails.py`,
  `skate_surf_contact_sheet.py`, `pattern_inventory.py`, `finish_visual_audit.py`,
  `audit_renderer_performance.py` (older twin of `audit_render_perf.py`),
  `mark_audit_addressed.py`, `generate_audit_queue.py`, `build_audit_workbook.py`,
  `build_overnight_review.py`, `build_reference_pattern_plates.py`,
  `build_category_workbench.py`, `spb_pattern_audit.py`,
  `spb_pattern_car_preview.py`, `spb_pattern_quality_metric.py`,
  `spb_pattern_top10_compare.py`, `spb_pattern_weakness_rollup.py`,
  `spb_visual_workbench.py`, `spb_rebuild_triage.py`, `spb_probe_catalog_drift.py`,
  `spb_watch_catalog_files.py`, `generate_spec_pattern_atlas.py`.
- Overnight loop helpers: `overnight_finish_worker.py`, `overnight_loop.sh`,
  `shokk_drop_loop_arm.sh`, `shokk_drop_loop_arm.ps1` — keep only if the overnight
  loop is still used; otherwise archive.
- Generated/output + scratch artifacts (safe to archive — pure outputs):
  `special_groups_output.js`, `mono_ids_backend.txt`, `_mshcb_smoke_result.txt`,
  and any `_mshc_*.png` / `_fd_*.png` smoke montages living in `scripts/`.

## version-churn candidates (keep latest, archive older — owner call)

- Scorers: `spb_spm7_score.py`, `spb_spm8_score.py`, `spb_spm10_score.py`,
  `spm9_score.py` — likely only the newest is current.
- Workbook passes: `spb_workbook_compute_m1.py` .. `m9.py` — confirm which the
  current workbook build uses.
- Scorecard patches: `spb102_patch_spectrum_scorecard.py`,
  `spb107_patch_v3_seeds_scorecard.py`, `spb109_patch_spec_pattern_scorecard.py`.
- Audit twins: `audit_render_perf.py` vs `audit_renderer_performance.py`;
  `audit_pattern_design_paint_richness.py` vs `audit_spec_driven_spec_richness.py`.

## unknown (needs an owner glance)

- `audit_server.py`, `review_server.py` — server-audit helpers; not wired;
  unclear if superseded by the `spb_guard_server_*.js` family.
- `rate_portals_config.py`, `spb_rate_portal_lib.py` — config/lib; live only if
  the rate-portal flow is still active (imported by the rate-portal one-shots).
- `spb102/107/109_patch_*scorecard.py` — see version-churn.

## Already-archived destination

`scripts/archive/` already exists — the owner has a destination for the
RECOMMEND-ARCHIVE items above. This doc does not move anything into it.

## Notes

1. No action was taken. This document is the deliverable.
2. "(by family)" classifications are inferred from filename + the directory's own
   READMEs, not a per-file docstring read; confirm the top-of-file before moving
   any specific script.
3. Safest concrete first declutter: the version-churn group plus the pure
   generated/output artifacts (`special_groups_output.js`, `*_smoke_result.txt`,
   `_mshc_*`/`_fd_*` PNGs), since those carry no logic.
