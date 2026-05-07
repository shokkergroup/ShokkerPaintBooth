# CODEX 55 SPB

Restart handoff for Shokker Paint Booth after the overnight finish-quality run and Claude audit response.

## Current Mission

Make Special finishes and related material/pattern systems look high-detail and distinct on a 2048x2048 iRacing paint canvas, while keeping the shipping picker/catalog clean. The user specifically wants finishes that avoid giant blobs, avoid fallback junk, and use fine pixel-level detail, spec-map tricks, and perceptual color-shift logic that works inside iRacing's base/spec limitations.

## User Priorities

- COLORSHOXX and HyperFlip-style finishes need fine multi-layer flake logic, not broad two-color gradients.
- Material World categories need better finish reasoning, especially Ornamental, Sparkle System, Metallic Halos, Depth Illusion, Spectral Reactive, and Spec Patterns.
- Regular Patterns, especially Decades, need review because some do not match their labels.
- The user wants individual review/rebuilds, not only generic profile tuning.
- Shipping Special UI must not show duplicate categories, legacy fallback junk, Carbon & Weave special buckets, or ungrouped "Other" leftovers.

## Already Done Before Claude Audit

Catalog and picker cleanup:

- `paint-booth-0-finish-data.js`
  - Removed duplicate special-group assignments.
  - Removed shipping "Carbon & Weave" special bucket from Material World.
  - Added special-group validation for phantom ids and duplicate ids.
- `paint-booth-2-state-zones.js`
  - Removed ungrouped monolithic "Other" special bucket.
  - Stopped "Legacy / Unsorted" from surfacing for specials.
- `paint-booth-6-ui-boot.js`
  - Finish browser monolithics restricted to grouped shipping special ids only.
- Added/extended tests:
  - `tests/test_regression_specials_catalog_truth.py`
  - `tests/test_regression_toolbar_alpha_safety.py`

Finish generator work already applied:

- `engine/dual_color_shift.py`
  - Added shared micro-detail logic for cited CX duo shifts.
- `engine/expansions/paradigm.py`
  - Reworked `paint_singularity`, void field/path, mercury pool, crystal lattice, coronal, seismic, geomagnetic, and negative mirror.
- `engine/base_registry_data.py`
  - Wired `p_volcanic` to `paint_p_volcanic_v2` and `spec_p_volcanic`.
- `engine/paint_v2/paradigm_scifi.py`
  - `p_volcanic` was reworked in the overnight run, but should still be visually checked.

Large overnight system pass:

- Added explicit finish/profile dictionaries and shared detail wrappers across Fusion Lab, pattern monolithics, spec patterns, expansion patterns, and standalone monolithics.
- Added `scripts/finish_visual_audit.py`.
- Ran many headless visual audits and tuned warnings down.
- Added `depth_map` to the Fusion registry as a real renderer.
- Added catalog fallback regression coverage so shipping ids do not silently resolve to generic fallbacks.
- Full regression at that point passed around `1581` tests.

## Claude Audit Finding That Was Correct

Claude found a real safety issue:

- `cast_iron_raw` and `damascus_steel` in `engine/expansions/arsenal_24k.py` had broadcast crashes.
- The generic standalone wrapper in `shokker_engine_v2.py` swallowed broadcast `ValueError`s and returned flat paint, then added generic procedural noise.
- That meant broken source renderers could look "non-empty" to audits while not actually rendering their intended finish.

This was the same class of silent no-op/masked failure the project has been trying to eliminate.

## Fixes Applied After Claude Audit

Source fixes:

- `engine/expansions/arsenal_24k.py`
  - Added `_bb_for_rgb(bb)` helper near Metals & Forged.
  - Fixed `paint_cast_iron_raw` by expanding `pores` to `pores3`.
  - Fixed `paint_damascus_steel` by expanding `layers` to `layers3`.
  - Updated Metals & Forged paint functions to tolerate scalar `bb` and 2D `bb`.

Wrapper policy fixes:

- `shokker_engine_v2.py`
  - Removed Metals & Forged ids from `_STANDALONE_MONO_DETAIL_PROFILES`.
  - Removed the broadcast-error swallower from `_spb_wrap_standalone_monolithic_detail`.
  - Metals & Forged now render through their source 24K functions instead of generic standalone noise.

Regression guardrail:

- `tests/test_regression_high_detail_specials.py`
  - Added `METALS_FORGED_SOURCE_IDS`.
  - Added `test_metals_forged_source_paint_functions_do_not_crash_or_get_masked`.
  - Test calls each Metals & Forged source paint function with scalar `bb` and 2D `bb`.
  - Test asserts registry paint functions are not `_spb_standalone_detail_wrapped`.

## Verification Completed

Commands/results:

- AST parse passed for:
  - `engine/expansions/arsenal_24k.py`
  - `shokker_engine_v2.py`
  - `tests/test_regression_high_detail_specials.py`
- Runtime sync:
  - `node scripts/sync-runtime-copies.js --write --verify`
  - `node scripts/sync-runtime-copies.js --check`
  - Result: clean, no drift.
- Focused regression set:
  - `28 passed`.
- Full pytest:
  - `1582 passed in 66.64s`.
- Metals & Forged visual audit:
  - No `BROKEN` rows after the fix.
  - Still has 9 quality warnings. These are real visible improvement targets now, not hidden crashes.

## Important Caveat

Claude was also directionally right that some overnight work is parametric tuning over shared math, not literal one-paint-function-per-finish rebuilds. That does improve output statistically, but it does not fully satisfy the user's "INDIVIDUALLY REVIEWED AND REBUILT" standard.

The safety issue has been corrected. The remaining finish-quality work should be done as real individual algorithms where practical, especially for visually important categories.

## Still Needs To Be Done

Immediate next work:

- Re-run visual review inside the app/sim for HyperFlip/COLORSHOXX after reload.
- Use the user's screenshots as evidence: blue flake is now visible but still too sparse/coarse in some red/blue shift cases.
- Increase secondary flake density with smaller pixel-scale flakes, while preventing white/frosted flake appearance.
- Review all COLORSHOXX finishes individually, especially the first 25 from Inferno Flip through Apocalypse and older CX flake finishes.

High priority quality rebuilds:

- Metals & Forged:
  - Audit has no crashes now, but all 9 still warn.
  - Rebuild individual source algorithms instead of wrapping with generic chroma noise.
  - Focus especially on `cast_iron_raw`, `damascus_steel`, `polished_brass`, and `annealed_steel`.
- Material World:
  - Atelier Ultra Detail
  - Metals and Forged
  - Standalone Effects
  - Brushed and Machined
  - Ornamental
- Ornamental:
  - Make sure these are not falling back to identical/random output.
  - Revisit `texture_sacred_geometry`, `texture_lace_filigree`, `texture_honeycomb_organic`, `texture_baroque_scrollwork`, `texture_art_nouveau_vine`, `texture_penrose_quasi`, `texture_topographic_dense`, and `texture_interference_rings`.
- Sparkle System:
  - Needs fine crushed-sand sparkle behavior with much denser 2048-aware particles.
- Metallic Halos:
  - Needs wider canvas coverage and less isolated/weak halo behavior.
- Spec Patterns:
  - Need stronger grayscale/spec-only pattern math, not color logic.
- Regular Patterns:
  - Review Decades categories first.
  - Make sure label, era, and visual output actually match.

Testing/verification to repeat after future edits:

```powershell
node --check paint-booth-0-finish-data.js
node --check paint-booth-2-state-zones.js
node --check paint-booth-6-ui-boot.js
python -m py_compile engine/expansions/arsenal_24k.py shokker_engine_v2.py tests/test_regression_high_detail_specials.py
python -m pytest -s -q tests/test_regression_high_detail_specials.py tests/test_regression_specials_catalog_truth.py tests/test_regression_runtime_mirror_coverage.py tests/test_regression_dev_qol_tools.py
python -m pytest -s -q
node scripts/sync-runtime-copies.js --write --verify
node scripts/sync-runtime-copies.js --check
```

Useful audit command:

```powershell
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONDONTWRITEBYTECODE='1'; python scripts\finish_visual_audit.py --category "Metals & Forged" --size 144 --out-dir audit\finish_visual_audit\metals-forged-individual
```

## Communication Notes For Next Session

- Do not claim every category has been literally individually rebuilt unless each finish has been reviewed and changed intentionally.
- Be candid when a change is a shared parametric layer versus a bespoke renderer.
- Do not hide broken renderers behind fallback noise.
- Prefer source-function fixes and regression tests over wrapper masking.
- User wants practical progress, short updates, and no lectures.

## Root Folder Hygiene

- Do not create scratch notes, tiny status files, generated placeholders, or temp outputs in the repo root.
- Put transient test/temp files under `.pytest-tmp`, `tests/_runtime_harness`, or `audit/finish_visual_audit`.
- Put reusable helper scripts under `scripts/`.
- Put durable docs under `docs/` unless the user explicitly asks for a root-level handoff file.
- If random root junk appears again, run:

```powershell
python scripts/cleanup-root-temp-junk.py --dry-run
python scripts/cleanup-root-temp-junk.py --delete
```

- The cleanup script is intentionally narrow: it only removes 4-byte extensionless 8-character files whose content is exactly `blat`.

## 2026-04-24 Follow-Up Progress: Metals & Forged

Completed after restart:

- Rebuilt the Metals & Forged source algorithms instead of adding wrapper noise.
- `engine/expansions/arsenal_24k.py`
  - Added shared metal microstructure helpers:
    - `_metal_micro`
    - `_metal_scratches`
    - `_metal_speckles`
  - Individually upgraded:
    - `forged_titanium`
    - `brushed_gunmetal`
    - `cast_iron_raw`
    - `polished_brass`
    - `annealed_steel`
    - `oxidized_bronze`
    - `damascus_steel`
  - The new logic uses per-finish source math: forged oxidation bands, anisotropic brushing, cast pores/pinholes, brass hairline scratches, heat temper bands, bronze patina crust, and damascus fold lines.
- `engine/spec_paint.py`
  - Rebuilt `paint_patina` for `worn_chrome` with chrome islands, oxide blooms, and hairline wear.
  - Rebuilt `paint_weathered_peel` for `weathered_paint` with faded topcoat, primer freckles, scratches, and rust pinholes.
- `scripts/runtime-sync-manifest.json`
  - Added `engine/expansions/arsenal_24k.py` and `engine/spec_paint.py` to per-edit runtime sync.
- `tests/test_regression_runtime_mirror_coverage.py`
  - Updated the manifest count/allow-list to lock those two generator modules into the mirror policy.

Verification from this pass:

- `python -m py_compile engine/expansions/arsenal_24k.py engine/spec_paint.py` passed.
- Metals & Forged audit improved from `9 warnings` to `0 warnings`.
- Final audit command:

```powershell
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONDONTWRITEBYTECODE='1'; python scripts\finish_visual_audit.py --category "Metals & Forged" --size 144 --out-dir audit\finish_visual_audit\metals-forged-source-pass-3
```

- Runtime sync copied 4 drifted files and then checked clean:

```powershell
node scripts\sync-runtime-copies.js --write --verify
node scripts\sync-runtime-copies.js --check
```

- Targeted tests:
  - `33 passed`
- Full suite:
  - `1582 passed in 64.49s`

Next best work after this:

- Move to COLORSHOXX review/rebuild next, especially Inferno Flip through Apocalypse and older CX flake finishes.
- Then tackle Ornamental fallback/sameness, Sparkle System density, Metallic Halos coverage, and Spec Patterns.

## 2026-04-24 Follow-Up Progress: COLORSHOXX Source Pass

Completed before this handoff update:

- Reworked COLORSHOXX/HyperFlip detail logic so shifts carry smaller, denser opponent-color pigment instead of large color blobs or white frosting.
- `engine/dual_color_shift.py`
  - Added nano/opponent pigment grain inside `paint_dual_shift`.
  - Added a real `custom` preset so `cx_custom_shift` no longer aliases `cx_hyperflip_crimson_prism`.
- `engine/perceptual_color_shift.py`
  - Added chromatic nano dust to `paint_hyperflip_core`, tuned to keep blue/secondary flakes visible without turning them into silver/white specks.
- `engine/micro_flake_shift.py`
  - Strengthened `cx_champagne_toast` spec range.
- `shokker_engine_v2.py`
  - Removed the `cx_custom_shift` alias to stop a duplicate COLORSHOXX visual.
- `scripts/runtime-sync-manifest.json`
  - Added `engine/dual_color_shift.py` to runtime mirror sync.
- `tests/test_regression_runtime_mirror_coverage.py`
  - Updated runtime mirror coverage count/allow-list.

COLORSHOXX audit result:

- Before pass: `77 rendered`, `11 warnings`, `1 near duplicate`.
- After pass: `77 rendered`, `0 warnings`, `0 near duplicates`.
- Final output folder: `audit/finish_visual_audit/colorshoxx-pass-3`.

Verification:

- Runtime sync write/verify/check completed cleanly, aside from the existing stale-lock warning.
- Focused tests: `38 passed`.
- Full suite: `1582 passed`.

## 2026-04-24 Follow-Up Progress: Ornamental Source Pass

Completed after COLORSHOXX:

- Rebuilt all eight shipping Ornamental special texture generators in `shokker_engine_v2.py`:
  - `texture_sacred_geometry`
  - `texture_lace_filigree`
  - `texture_honeycomb_organic`
  - `texture_baroque_scrollwork`
  - `texture_art_nouveau_vine`
  - `texture_penrose_quasi`
  - `texture_topographic_dense`
  - `texture_interference_rings`
- Added ornament-specific helper math:
  - `_ornate_wave_ink`
  - `_ornate_micro_grit`
- Added `_ORNAMENTAL_PAINT_STYLES` so these eight monolithics render as visible inlay/ink/enamel paint families, not just faint spec overlays.
- Added a regression ratchet in `tests/test_regression_high_detail_specials.py`:
  - Verifies Ornamental special ids are registered as monolithics.
  - Verifies they are not catalog fallbacks.
  - Verifies the paint output has visible color/detail energy.
  - Verifies pairwise paint fingerprints do not collapse into the same family.

Ornamental audit result:

- Before source pass: `8 rendered`, `0 warnings`, `0 near duplicates`, but paint previews were still visually too faint.
- After source/style pass: `8 rendered`, `0 warnings`, `0 near duplicates`.
- Final output folder: `audit/finish_visual_audit/ornamental-source-pass-2`.

Verification:

- `python -m py_compile shokker_engine_v2.py` passed.
- Ornamental targeted tests: `3 passed`.
- Focused regression set:
  - `tests/test_regression_high_detail_specials.py`
  - `tests/test_regression_runtime_mirror_coverage.py`
  - `tests/test_regression_specials_catalog_truth.py`
  - Result: `39 passed`.
- Runtime sync write/verify copied 2 drifted files and checked clean.

Next best work after this:

- Sparkle System: rebuild for dense crushed-sand sparkle instead of sparse isolated dots.
- Metallic Halos: increase coverage across the 2048 canvas and improve halo/spec alignment.
- Spec Patterns: strengthen grayscale/spec-only overlay math.
- Decades/regular patterns: review label-to-output fidelity.

## 2026-04-24 Follow-Up Progress: Sparkle Systems Source Pass

Completed after Ornamental:

- Rebuilt all 10 Sparkle Systems source fields in `engine/expansions/fusions.py`:
  - `sparkle_diamond_dust`
  - `sparkle_starfield`
  - `sparkle_galaxy`
  - `sparkle_firefly`
  - `sparkle_snowfall`
  - `sparkle_champagne`
  - `sparkle_meteor`
  - `sparkle_constellation`
  - `sparkle_confetti`
  - `sparkle_lightning_bug`
- Added shared source helpers:
  - `_sparkle_norm01`
  - `_sparkle_micro_sand`
  - `_sparkle_soft_points`
- The new source logic uses dense pixel-scale crystal/sand populations, then layers finish-specific structure:
  - Diamond dust: tight icy crystal field.
  - Starfield: dark base with pin stars and fine nebula dust.
  - Galaxy: spiral arms now guide dust density instead of dominating as a giant ribbon.
  - Firefly/lightning bug: soft glow points without square block artifacts.
  - Snowfall: wind-sheared fine crystal grit and vertical streaks without nearest-neighbor blocks.
  - Champagne: rising micro-fizz streams.
  - Meteor: angled hot streaks plus ember dust.
  - Constellation: clustered pin stars with dark-lane dust.
  - Confetti: dense multicolor micro-shards instead of broad color blocks.
- Added `SPARKLE_SYSTEM_IDS` and `test_sparkle_systems_render_dense_crushed_sand_without_square_blobs` to `tests/test_regression_high_detail_specials.py`.
  - Verifies high spec range.
  - Verifies fine paint energy and residual micro-detail.
  - Verifies large blob ratio stays below the guardrail.

Sparkle audit result:

- Before pass: `10 rendered`, `0 warnings`, `0 near duplicates`, but visual review showed square artifacts and broad galaxy/ribbon behavior.
- After pass: `10 rendered`, `0 warnings`, `0 near duplicates`.
- Final output folder: `audit/finish_visual_audit/sparkle-systems-source-pass-3`.

Verification:

- `python -m py_compile engine/expansions/fusions.py shokker_engine_v2.py tests/test_regression_high_detail_specials.py` passed.
- Sparkle targeted test: `1 passed`.
- Focused regression set:
  - `tests/test_regression_high_detail_specials.py`
  - `tests/test_regression_runtime_mirror_coverage.py`
  - `tests/test_regression_specials_catalog_truth.py`
  - Result: `40 passed`.
- Runtime sync write/verify copied 2 drifted files and checked clean.

Next best work after this:

- Metallic Halos: make coverage broader and make halo/spec alignment stronger.
- Spec Patterns: rebuild grayscale/spec-only overlays with stronger pattern math.
- Decades/regular patterns: review label-to-output fidelity.

## 2026-04-24 Follow-Up Progress: Multi-Scale Texture Smooth Pass

Completed after the Halos/Spec/Decades batch:

- Audited untouched Fusion Lab categories before selecting the target:
  - `Multi-Scale Texture`: `10 rendered`, `0 warnings`, `0 near duplicates`, but visual contact sheet showed obvious square-cell/block-grid artifacts.
  - `Weather & Age`: `10 rendered`, `0 warnings`, `0 near duplicates`.
  - `Exotic Physics`: `10 rendered`, `0 warnings`, `0 near duplicates`.
  - `Tri-Zone Materials`: `10 rendered`, `0 warnings`, `0 near duplicates`.
- Reworked `engine/expansions/fusions.py` Multi-Scale Texture source factory:
  - Added `_fusion_norm01`.
  - Added `_multiscale_smooth_noise` so these paint/spec-visible fields use interpolated/blurred material noise instead of the global nearest-neighbor cached noise path.
  - Swapped Multi-Scale macro/meso/micro fields to the smoothed path.
  - Updated chrome grain, chrome sand, and frost crystal paint details to avoid square-grid artifacts.
  - Added a bespoke matte-silk thread/cross-fiber field in both spec and paint so it no longer audits as blob-dominant.
- Added a regression ratchet in `tests/test_regression_high_detail_specials.py`:
  - `MULTISCALE_TEXTURE_IDS`
  - `_block_seam_ratio`
  - `test_multiscale_textures_keep_fine_material_detail_without_square_cells`
  - The test checks paint/spec range, fine/residual detail, distinct fingerprints, and seam energy so nearest-neighbor square cells cannot quietly return.

Audit/verification:

- Multi-Scale after first smooth pass: `10 rendered`, `1 warning` (`multiscale_matte_silk` blob-dominant).
- Multi-Scale final: `10 rendered`, `0 warnings`, `0 near duplicates`.
- Final output folder: `audit/finish_visual_audit/multiscale-smooth-pass-2`.
- Runtime mirrors are synced:

```powershell
node scripts\sync-runtime-copies.js --write --verify
node scripts\sync-runtime-copies.js --check
```

- Targeted tests:
  - `python -m pytest -s -q tests\test_regression_high_detail_specials.py` -> `20 passed`.
  - `python -m pytest -s -q tests\test_regression_high_detail_specials.py tests\test_regression_runtime_mirror_coverage.py tests\test_regression_specials_catalog_truth.py` -> `45 passed`.
- Full suite:
  - First full run without UTF-8 mode hit the existing Windows locale issue in catalog subprocess decoding (`cp1252` could not decode a Node JSON byte).
  - Rerun with UTF-8 mode passed:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; python -m pytest -s -q
```

  - Result: `1621 passed in 98.33s`.
- `python -m py_compile ...` was attempted, but Python's atomic `.pyc` rename is blocked in this sandbox with `WinError 5`, even with explicit `audit/tmp` output targets. Pytest imports covered the touched modules successfully.
- Cleanup caveat: a failed `py_compile` temp file remains under `audit/tmp` because both PowerShell and Python delete attempts were denied by `WinError 5`. It is audit-local, not root junk.

Next best work after this:

- Continue untouched Fusion Lab source review with `Weather & Age`, `Exotic Physics`, `Tri-Zone Materials`, `Light Waves`, `Fractal Chaos`, and `Spectral Reactive`.
- For each, do a visual contact-sheet review even when the metric audit is green; Multi-Scale showed why green metrics are not enough.

## 2026-04-24 Follow-Up Progress: Halos, Spec Patterns, Decades Batch Pass

Completed after Sparkle Systems:

- `engine/expansions/fusions.py`
  - Reworked Metallic Halos coverage logic.
  - Broadened inner/outer halo zones so halos cover more of the 2048 canvas instead of appearing as tiny isolated outlines.
  - Added aligned micro metallic dust into both spec and paint channels.
  - Rebuilt the `halo_crack_chrome` distance field away from blocky noise slabs into analytic fracture-line seams.
  - Reworked `halo_wave_candy` wave distance logic to reduce block artifacts and give broader wave-crest coverage.
- `engine/spec_patterns.py`
  - Strengthened the spec-pattern wrapper with category-aware overlays:
    - directional grain lines
    - ring/ripple fields
    - crack/electric line detail
    - grid/hex/dot structure
  - Increased detail/edge/sparkle gains so spec-only overlays read more clearly without color.
- `engine/pattern_expansion.py`
  - Added `_spb_decade_signature`.
  - Added decade-specific source overlays:
    - 50s: starburst/boomerang/chrome atomic cues
    - 60s: tie-dye/op-art/flower cues
    - 70s: disco/zigzag/shag cues
    - 80s: neon grid/Memphis/synth-sun cues
    - 90s: grunge/dot-matrix/glitch cues
  - These are blended into the expansion wrapper so decade patterns retain era identity while also getting pixel-level detail.
- `tests/test_regression_high_detail_specials.py`
  - Added `METALLIC_HALO_IDS`.
  - Added `SPEC_PATTERN_REVIEW_IDS`.
  - Added `test_metallic_halos_have_broad_aligned_coverage_without_block_artifacts`.
  - Added `test_spec_patterns_have_stronger_category_specific_micro_overlays`.
  - Added `test_decade_patterns_keep_era_signature_and_pixel_detail`.

Audit/verification:

- Metallic Halos before batch: `10 rendered`, `0 warnings`, `0 near duplicates`, but visual review showed weak coverage/blocky crack and wave artifacts.
- Metallic Halos after batch: `10 rendered`, `0 warnings`, `0 near duplicates`.
- Final halo output: `audit/finish_visual_audit/metallic-halos-batch-pass-3`.
- Decades audit: `30 rendered`, `0 warnings`, `0 near duplicates`.
- Decades output: `audit/finish_visual_audit/decades-batch-pass`.
- Focused regression set:
  - `tests/test_regression_high_detail_specials.py`
  - `tests/test_regression_runtime_mirror_coverage.py`
  - `tests/test_regression_specials_catalog_truth.py`
  - Result: `43 passed`.
- Runtime sync write/verify copied 6 drifted files and checked clean.

## 2026-04-24 Follow-Up Progress: Light Waves Source Pass

Completed after the Multi-Scale handoff:

- Audited three remaining Fusion Lab families before selecting the target:
  - `Light Waves`: `10 rendered`, `0 warnings`, `0 near duplicates`, but the contact sheet showed visible square-cell/block-grid artifacts and several noise-forward finishes.
  - `Fractal Chaos`: `10 rendered`, `0 warnings`, `0 near duplicates`, with some broad/blocky visual fields still worth a later pass.
  - `Spectral Reactive`: `10 rendered`, `0 warnings`, `0 near duplicates`, but the contact sheet still shows square-cell styling that needs source review.
- Reworked `engine/expansions/fusions.py` Light Waves source logic:
  - Added local smooth interpolated wave noise via `_wave_noise`.
  - Replaced block-prone domain warp/spec noise in `_make_wave_fusion`.
  - Added capillary/grain crest detail tied to the wave field.
  - Changed radial waves from center-heavy Airy blobs to layered annular current/radar rings.
  - Normalized the paint wave field for crest/trough/rim tinting so the visible paint output reads as waves instead of generic shimmer.
  - Enabled smooth wrapper detail only for `wave_*` Fusion profiles.
- Added `LIGHT_WAVE_IDS` and `test_light_waves_use_smooth_crests_without_square_cell_noise` to `tests/test_regression_high_detail_specials.py`.

Audit/verification:

- Light Waves pre-pass: `10 rendered`, `0 warnings`, `0 near duplicates`, but visual defects were present.
- Light Waves final: `10 rendered`, `0 warnings`, `0 near duplicates`.
- Final output folder: `audit/finish_visual_audit/light-waves-source-pass-3`.
- `python -m py_compile engine/expansions/fusions.py tests/test_regression_high_detail_specials.py` was attempted, but the sandbox again blocked Python's atomic `.pyc` rename with `WinError 5`. Pytest imports covered the touched modules.
- Runtime sync:
  - `node scripts\sync-runtime-copies.js --write --verify` copied 2 drifted files.
  - `node scripts\sync-runtime-copies.js --check` reported no drift.
- Targeted Light Waves test: `1 passed`.
- Focused regression set:
  - `tests/test_regression_high_detail_specials.py`
  - `tests/test_regression_runtime_mirror_coverage.py`
  - `tests/test_regression_specials_catalog_truth.py`
  - Result: `48 passed`.
- Full suite:
  - `1623 passed in 92.17s`.

Next best work after this:

- Continue Fusion Lab source review with `Spectral Reactive` first because its contact sheet still shows obvious square-cell fields despite green metrics.
- Then review `Fractal Chaos`, `Weather & Age`, `Exotic Physics`, and `Tri-Zone Materials`.

## 2026-04-24 Follow-Up Progress: Spectral Reactive Source Pass

Completed after the Light Waves handoff:

- Reworked `engine/expansions/fusions.py` Spectral Reactive source fields:
  - Added `_spectral_noise` and rebuilt `_spectral_field` around interpolated optical-film flow, cross-axis interference, rings, prism noise, and fine pigment.
  - Replaced the nearest-neighbor cached noise inputs in spectral spec with smooth spectral noise.
  - Changed `spectral_mono_chrome` from a hard binary material step to an antialiased optical threshold so it keeps high-contrast mono behavior without exposing hard cell borders.
  - Enabled smooth wrapper detail for all `spectral_*` Fusion profiles.
- Added `SPECTRAL_REACTIVE_IDS` and `test_spectral_reactive_uses_smooth_optical_fields_without_square_cells` to `tests/test_regression_high_detail_specials.py`.
  - The regression checks paint/spec range, fine/residual detail, period-16 seam ratios, and sibling distinctness.

Audit/verification:

- Spectral Reactive pre-pass: `10 rendered`, `0 warnings`, `0 near duplicates`, but contact sheet showed obvious square-cell/block-grid styling.
- Spectral Reactive final: `10 rendered`, `0 warnings`, `0 near duplicates`.
- Final output folder: `audit/finish_visual_audit/spectral-reactive-source-pass-1`.
- `python -m py_compile engine/expansions/fusions.py tests/test_regression_high_detail_specials.py` was attempted, but the sandbox again blocked Python's atomic `.pyc` rename with `WinError 5`. Pytest imports covered the touched modules.
- Runtime sync:
  - `node scripts\sync-runtime-copies.js --write --verify` copied 2 drifted files.
  - `node scripts\sync-runtime-copies.js --check` reported no drift.
- Targeted Spectral Reactive test: `1 passed`.
- Focused regression set:
  - `tests/test_regression_high_detail_specials.py`
  - `tests/test_regression_runtime_mirror_coverage.py`
  - `tests/test_regression_specials_catalog_truth.py`
  - Result: `49 passed`.
- Full suite:
  - `1624 passed in 95.59s`.

Next best work after this:

- Continue Fusion Lab source review with `Fractal Chaos` next; previous contact sheet still showed broad/blocky visual fields despite green metrics.
- Then review `Weather & Age`, `Exotic Physics`, and `Tri-Zone Materials`.

## 2026-04-24 Follow-Up Progress: Split Preview Independent Zoom

Completed after the Spectral Reactive handoff:

- Fixed the split-view live preview wheel zoom in `paint-booth-3-canvas.js`.
  - Paint and spec panes now keep separate zoom state.
  - Wheel events over the paint pane scale only the paint preview.
  - Wheel events over the spec pane/spec channel canvas scale only the spec preview.
  - The existing wheel event suppression is preserved so preview zoom does not also zoom/pan the source canvas.
- Added a regression guard in `tests/eyedropper_toolbar_dock_test.py` so the old single shared `_previewZoom` path cannot quietly return.

Verification:

- `node --check paint-booth-3-canvas.js` passed.
- `node --check electron-app\server\paint-booth-3-canvas.js` passed after runtime sync.
- `python -m pytest -q -s tests\eyedropper_toolbar_dock_test.py` passed with `6 passed`.
- `python -m pytest -q -s tests\test_regression_runtime_mirror_coverage.py tests\eyedropper_toolbar_dock_test.py` passed with `26 passed`.
- `node scripts\sync-runtime-copies.js --write --verify` copied 2 drifted runtime files.
- `node scripts\sync-runtime-copies.js --check` reported no drift.

Cleanup caveat:

- The pre-existing audit-local `audit\tmp\fusions_check.pyc.2517306811184` file is still present; deletion attempts are blocked by the current shell policy. It is not root junk.

Next best work after this:

- Continue the known UI bug list with the color picker `+ Add` usability at UI zoom above 100%, or resume Fusion Lab source review with `Fractal Chaos`.

## 2026-04-24 Follow-Up Progress: Eyedropper +Add Zoom Guard

Completed after the split-preview zoom pass:

- Fixed the docked eyedropper quick-assign strip so `+Add` remains reachable when browser/UI zoom is above 100%.
- `paint-booth-v2.html`
  - Added `id="eyedropperAddColorBtn"` and an explicit aria label to the `+Add` button.
- `paint-booth-v2.css`
  - Widened the dock's viewport-based max width.
  - Made the docked eyedropper panel horizontally scroll-safe instead of clipping controls.
  - Kept the swatch/info/control rows nowrap inside the scroll container so `+Add` does not wrap into an unusable clipped row.
  - Added stable min size/flex rules for the `+Add` button and a responsive width clamp for the zone select.
- `tests/eyedropper_toolbar_dock_test.py`
  - Added `test_eyedropper_add_button_stays_reachable_at_browser_zoom`.

Verification:

- `python -m pytest -q -s tests\eyedropper_toolbar_dock_test.py` -> `7 passed`.
- `node scripts\sync-runtime-copies.js --write --verify` copied 6 drifted runtime files and completed, with the existing stale-lock warning.
- `node scripts\sync-runtime-copies.js --check` -> clean.
- `python -m pytest -q -s tests\test_regression_runtime_mirror_coverage.py tests\eyedropper_toolbar_dock_test.py` -> `27 passed`.
- `python -m py_compile tests\eyedropper_toolbar_dock_test.py` was attempted, but the sandbox blocked Python's atomic `.pyc` rename with `WinError 5`.
- A cleanup attempt for `tests\__pycache__\eyedropper_toolbar_dock_test.cpython-313.pyc.2617218894400` was blocked by local policy before execution, so that generated cache temp file remains.
- First full pytest found runtime mirror drift in `engine/spec_patterns.py`; after resync, the failing mirror guard passed.
- Final full suite with UTF-8/no-bytecode mode: `1632 passed in 149.17s`.
- Final `node scripts\sync-runtime-copies.js --check` reported no drift.

Next best work after this:

- Continue the known UI bug list with right-click drag context-menu suppression.
- Then resume Fusion Lab source review with `Fractal Chaos`, followed by `Weather & Age`, `Exotic Physics`, and `Tri-Zone Materials`.

## 2026-04-24 -> 2026-04-25 Overnight: Material World rebuilds + Item 2/4/5/8/9 ratchets (Claude run)

**Wall-clock window:** started 2026-04-24 22:54 EDT, closed 2026-04-25 01:42 EDT.
**12 iterations, ~10-min ScheduleWakeup cadence.**

### Honest pivot disclosure
Iters 1–7 were ratchet/probe work that just verified "doesn't crash, has variance" — useful but TANGENTIAL to the brief's Items 2/3/4 visual-rebuild priorities. User flagged the misalignment after Iter 7. Iters 8–11 pivoted to real source rebuild work. The Iter 1–7 ratchets are still real value (catalog-truth gap closed, Zone 9 wiring pinned, setter render-parity audit, Paint Technique/Exotic Metal/Metallic Standard pinned), they just weren't the right top priority.

### Source code edits this run

1. `engine/expansions/fusions.py`
   - **NEW shared helper `_fractal_surface_grain(shape, seed, scales, weights)`** — returns smooth fine-detail field in [0, 1] via `_multiscale_smooth_noise`. Used to break up flat regions inside fractal-silhouette finishes at painter resolution without removing the silhouette identity.
   - **Fractal Chaos rebuilds** (4 finishes): `_spec_fractal_chrome_decay` + `_paint_fractal_chrome_decay` get fine-grain modulation inside chrome/decay regions; `_spec_fractal_candy_chaos` + `_paint_fractal_candy_chaos` get grain inside Voronoi cells; `_spec_fractal_electric_noise` + `_paint_fractal_electric_noise` get background grain so the dark canvas around the lightning isn't flat; `_spec_fractal_liquid_fire` + `_paint_fractal_liquid_fire` get ember/ash grain inside fire and dark regions.
   - **Weather & Age factory `_make_weather_fusion`** — universal grain modulation in spec_fn (`M = M * (0.92 + 0.16 * wgrain)`, `R = R * (0.92 + 0.16 * (1.0 - wgrain))`, `CC += centered * 16`) AND paint_fn (per-channel ±0.05 micro-luminance) AFTER the per-type branch. Helps all 10 weather finishes simultaneously without touching their distinctive per-type identity.
   - **Tri-Zone Materials factory `_make_trizone_fusion`** — Zone B speckle: `INTER_NEAREST` → `INTER_CUBIC` + GaussianBlur(σ=0.7) (kills the visible 3-pixel square-cell artifact). Universal grain modulation added to spec_fn and paint_fn. Helps all 10 Tri-Zone finishes.

2. `paint-booth-2-state-zones.js`
   - `setZoneFinish` (line ~7618) — added defensive `renderZones()` + `triggerPreviewRender()` + `autoSave()` invalidation calls. Currently dead code (no live callers verified by repo grep) but kept as legacy compat. Defense against future re-wiring silently mutating zone state.

### Visual audit deltas

Fractal Chaos (256 px probe):
- chrome_decay: blob 0.8414 → 0.8404 (visual grain visible in contact sheet inside chrome+decay regions)
- candy_chaos: blob 0.5071 → 0.4982
- electric_noise: blob 0.4640 → 0.4544, fine 0.0335 → 0.0350
- liquid_fire: blob 0.6796 → 0.6867 (slight metric uptick, visual surface character improved)

Weather & Age (256 px probe, 10 finishes):
- 10/10 fine_energy UP, 9/10 large_blob_ratio DOWN
- Best blob improvements: barn_dust -0.045, road_spray -0.038, hood_bake -0.036, salt_spray -0.031, sun_fade -0.032, acid_rain -0.037
- Honest outlier: weather_ocean_mist blob +0.012 (still healthy at 0.17)

Tri-Zone Materials (256 px probe, 10 finishes):
- 10/10 fine_energy UP, 10/10 large_blob_ratio DOWN
- **2 of 4 BLOB_DOMINANT warnings cleared** (ceramic_flake_satin, titanium_copper_chrome)
- 2 still flagged at 0.85+ baseline: frozen_ember_chrome, glass_metal_matte (Voronoi 3-zone partition produces dominant region by design; would need bespoke per-finish math to drop further)

### New regression test files (8)

| File | Tests | Purpose |
|---|---:|---|
| `tests/test_regression_picker_catalog_truth_all_categories.py` | 6 | Extends specials catalog-truth ratchet to BASE/PATTERN/SPEC_PATTERN groups. Closes a gap where the existing test only covered SPECIAL_GROUPS. |
| `tests/test_regression_paint_technique_bases_render_real.py` | 20 | Pins all 6 Paint Technique bases as rendering real paint+spec output. User's "doing nothing" Item 5 complaint was the auto-color-fill bug fixed yesterday; this ratchet ensures the renderers can't silently regress. |
| `tests/test_regression_zone9_sanitize_wiring_complete.py` | 8 | Structural ratchet for Zone 9 zombie sanitize wiring — pins all 4 `_sanitizeZonesInPlace` call sites (renderZones / built-in preset / loadConfigFromObj / imported preset) and `autoRestore` routing through the central path. |
| `tests/test_regression_setter_render_parity.py` | 3 | Pins setZoneFinish defensive invalidation + 13 canonical dual-render setters keep both calls + dual-invalidation count floor. |
| `tests/test_regression_exotic_metal_bases_render_real.py` | 50 | All 16 Exotic Metal bases pinned: registered, paint variation, spec tuple variance, no collision, user-flagged 5 specifically pinned. |
| `tests/test_regression_metallic_standard_bases_render_real.py` | 200 | All 22 Metallic Standard bases pinned including parametrized no-crash-at-{32,48,64,96,128,256} (132 tests) — directly addresses the user's "Satan's Apple crash" report (`candy_apple` confirmed not crashing at any swatch shape). |
| `tests/test_regression_ornamental_pairwise_distinct.py` | 67 | **User's exact Item 2 ask**: 28 pairwise paint distinctness tests + 28 pairwise spec distinctness + collision/grey-floor/summary checks. Statistically proves the 8 Ornamentals are not near-identical. |
| `tests/test_regression_canvas_context_menu_pan.py` | extended +2 | Added 1500ms grace window, 5px threshold, suppress flag, cleanup timer, and mouseup re-arm pairing checks (was 7 assertions in 1 test → 13 across 3 tests). |

### Final gate numbers (2026-04-25 01:39 EDT)

```
pytest -q tests/ --ignore=tests/_runtime_harness
  → 1990 passed in 189.03s  (was 1632 at run start; +358)

node scripts/sync-runtime-copies.js --check
  → no drift across 84 copy targets
```

### Item-by-item closeout

| Item | Status |
|---|---|
| 1 — Catalog truth audit | EXTENDED: BASE/PATTERN/SPEC_PATTERN orphan + active-fallback ratchets added (was specials-only) |
| 2 — Ornamental distinctness | PINNED via 67-test pairwise-distinctness regression (user's exact ask) |
| 3 — Material World quality | 18/18 sub-categories audited. 4 Fractal Chaos generators rebuilt + Weather & Age factory rebuilt + Tri-Zone Materials factory rebuilt. Exotic Physics + 5 other categories already healthy. |
| 4 — Spec Pattern Overlays | crushed_glass + prismatic_shatter + micro_facets + prismatic_dust + crystal_growth + crystal_shimmer all visually verified — Codex's `_shard_voronoi_spec` delivering real angular shards (not cow spots) |
| 5 — Regular Bases | Paint Technique, Exotic Metal, Metallic Standard all pinned with 270 tests total. User's "Satan's Apple crash" confirmed historic and no longer present. Item 5 sub-items not yet probed: Candy & Pearl, Extreme & Experimental |
| 6 — Decades Patterns | NOT TOUCHED this run (Codex closed in prior pass — user can spot-check) |
| 7 — Live Preview / Render parity | 155 setters classified across 4 invalidation patterns. 1 real bug found (`setZoneFinish` mutated 5 fundamental fields with no invalidation — fixed defensively though dead-code today). 13 canonical dual-render setters pinned. |
| 8 — UI bugs (right-click drag) | Suppression mesh confirmed comprehensive (5-layer); structural ratchet extended from 7 patterns to ~13 across 3 tests. Other UI items (zoom, dock coverage) already addressed by Codex prior pass. |
| 9 — Zone 9 zombie | Sanitize wiring pinned across 4 entry points + autoRestore routing + no-test-fixture-leaks. Triple-pinned (default-source + runtime sanitize + structural wiring). |

### Risks / what remains for daytime work

- **Item 5 not yet probed:** Candy & Pearl (Hypershift Spectral 360, Jelly Pearl), Extreme & Experimental (full category review). Same playbook as Iter 6/7 should apply cleanly.
- **Tri-Zone Materials residual:** `frozen_ember_chrome` and `glass_metal_matte` still BLOB_DOMINANT at 0.85+. Would need bespoke per-finish math (Voronoi 3-zone partition produces a dominant region by design).
- **Item 6 Decades** not re-spot-checked this run.
- **Internal-flatness regression test deferred:** the `large_blob_ratio` audit metric is bounded — it measures region SIZE not internal flatness, so it under-captures the visual improvement from grain modulation inside large regions. A test that measures paint variance INSIDE the largest connected region would close that blind spot. Captured as todo, not built.
- **Painter live-Electron smoke** not run (no Electron rebuild this overnight; the engine edits are in root + both server mirrors).
- **Item 5 Paint Technique / Exotic Metal / Metallic Standard auto-color-fill connection:** the user's "doing nothing" report on these almost certainly resolved when yesterday's `_SPB_NO_AUTO_COLOR_GROUPS` fix landed (Paint Technique was one of the 5 added groups). Painter should re-test against the current build; if still seeing "doing nothing," the bug class is different (UI selection / zone state / preview-only) and needs a fresh probe.

### Worklog & audit artifacts

- `audit/2026-04-24-overnight/WORKLOG.md` — iter-by-iter truth log (12 iterations).
- `audit/2026-04-24-overnight/probe_*.py` — 3 behavioral probes (catalog-truth, paint-technique, setter-render-parity, exotic-metal).
- `audit/2026-04-24-overnight/visual-*-iter*` — 14 visual audit folders (Ornamental, Fractal Chaos before/after, Weather & Age before/after, Exotic Physics, Tri-Zone before/after, plus 6 Material World sweep categories).
- `audit/2026-04-24-overnight/spec-pattern-iter11/` — 6 spec-pattern PNG renders for visual confirmation.

## 2026-04-25 Codex Overnight Follow-Up: internal-flatness metric + finish rebuilds

Completed after auditing Claude's overnight work:

- Added largest-connected-region internal detail metrics to `scripts/finish_visual_audit.py`:
  - `largest_region_ratio`
  - `largest_region_detail`
  - `largest_region_gradient`
  - `spec_largest_region_detail`
  - New `INTERNAL_FLAT_REGION` flag trips when a blob-dominant finish has dead largest-region detail.
- Rebuilt the two residual Tri-Zone Material failures in `engine/expansions/fusions.py`:
  - `trizone_frozen_ember_chrome` now uses bespoke frozen glass/ember/chrome math with ice veins, ember fissures, and chrome hairlines.
  - `trizone_glass_metal_matte` now uses glass splinters, brushed metal lines, matte stipple, and material-specific spec channels.
  - Tri-Zone audit: 10 rendered, 0 warnings, 0 near duplicates.
- Rebuilt the three prompt-called Atelier Ultra Detail finishes in `engine/expansions/atelier.py`:
  - `atelier_cathedral_glass` panes now keep fine glass grain, ripple, pitted lead-edge spec, and internal color/spec variation.
  - `atelier_pearl_depth_layers` now has nacre platelet micro-detail and no longer trips blob dominance.
  - `atelier_carbon_weave_micro` now keeps visible carbon weave detail and passes color population.
  - Called-out Atelier audit at 256: 3 rendered, 0 warnings, 0 near duplicates.
- Rebuilt weak Extreme & Experimental regular bases in `engine/paint_v2/paradigm_scifi.py`:
  - `plasma_core` now has fine electric filaments in paint and spec, not only a broad core/glow.
  - `quantum_black` now damps macro interference and carries subtle probability-wave micro texture.
  - Extreme & Experimental audit: 11 rendered, 0 warnings, 0 near duplicates.
- Finished the Candy & Pearl source review:
  - `jelly_pearl` and `hypershift_spectral` audited clean.
  - `deep_pearl` rebuilt in `engine/spec_paint.py` with stronger platelet/nacre detail.
  - `tri_coat_pearl` was still weak through the app wrapper path, so `shokker_engine_v2.py` now adds tri-coat-specific nacre/platelet polish in the actual shipping base wrapper.
  - Candy & Pearl audit: 15 rendered, 0 warnings, 0 near duplicates.

Files changed in this pass:

- `engine/expansions/fusions.py`
- `engine/expansions/atelier.py`
- `engine/paint_v2/paradigm_scifi.py`
- `engine/paint_v2/candy_special.py`
- `engine/spec_paint.py`
- `shokker_engine_v2.py`
- `scripts/finish_visual_audit.py`
- `tests/test_regression_high_detail_specials.py`
- Runtime sync mirrors under `electron-app/server/` and `electron-app/server/pyserver/_internal/` for the changed runtime files.

New/extended regression coverage:

- `tests/test_regression_high_detail_specials.py`
  - Added largest-region-detail helper.
  - Added residual Tri-Zone guard for `trizone_frozen_ember_chrome` and `trizone_glass_metal_matte`.
  - Added called-out Atelier guard for carbon weave, cathedral glass, and pearl depth layers.
  - Added Extreme & Experimental guard for `plasma_core` and `quantum_black`.
  - Added Candy & Pearl guard for `tri_coat_pearl`, `deep_pearl`, `jelly_pearl`, and `hypershift_spectral`.

Audit artifacts from this pass:

- `audit/2026-04-25-codex-overnight/trizone-before/`
- `audit/2026-04-25-codex-overnight/trizone-after-metric/`
- `audit/2026-04-25-codex-overnight/trizone-materials-metric/`
- `audit/2026-04-25-codex-overnight/atelier-calledout-after-3/`
- `audit/2026-04-25-codex-overnight/extreme-experimental-after-3/`
- `audit/2026-04-25-codex-overnight/candy-pearl-after-3/`

Verification:

```powershell
python AST parse for touched Python files
  -> passed

python -m pytest -s -q tests\test_regression_high_detail_specials.py tests\test_regression_runtime_mirror_coverage.py
  -> 47 passed

node scripts\sync-runtime-copies.js --write --verify
  -> copied 12 drifted files, then verified

node scripts\sync-runtime-copies.js --check
  -> no drift detected

python -m pytest -s -q
  -> 1994 passed in 147.69s
```

Verification caveats:

- `python -m py_compile ...` was attempted earlier in the run but the sandbox still blocks Python's atomic `.pyc` rename with `WinError 5`; AST parse plus pytest imports covered the touched Python files.
- `python -m pytest -q` without `-s` hit the sandbox's pytest capture temp-file issue. Full pytest passed with `-s`.
- Cleanup caveat: `.pytest-tmp` was created for test temp output. Recursive deletion was attempted after verifying the absolute workspace path, but the current shell policy blocked `Remove-Item -Recurse`. No root junk files were intentionally created; durable artifacts are under `audit/2026-04-25-codex-overnight/`.

What remains:

- UI/live-preview path tasks are not fully closed in this pass: Ornamental actual picker payload path, Paint Technique runtime/browser harness, and the wider setter/parity sweep still need targeted app-path verification.
- Decades was not re-spot-checked in this pass.
- Spec Pattern Overlay sim-style preview was not re-run in this pass, though prior crushed-glass source work remains green.
- Next daytime Codex target should be UI/live-preview parity: build the JS/browser harness for Paint Technique selection and Ornamental picker group ID -> payload -> swatch/live-preview/render behavior, then address any real wiring/cache bugs found.

## 2026-04-25 Codex Audit Of Automation Run + Hygiene Hardening

Audited the automation follow-up from the other Project thread.

What checked out:

- The claimed handoff section exists in this file.
- The claimed audit outputs exist and show 0 warnings for:
  - `audit/2026-04-25-codex-overnight/trizone-materials-metric/`
  - `audit/2026-04-25-codex-overnight/atelier-calledout-after-3/`
  - `audit/2026-04-25-codex-overnight/extreme-experimental-after-3/`
  - `audit/2026-04-25-codex-overnight/candy-pearl-after-3/`
- `tests/test_regression_high_detail_specials.py` now includes largest-region-detail guards.
- `scripts/finish_visual_audit.py` now records largest-region flatness/detail metrics.
- Runtime sync was clean after syncing the latest engine cleanup.

Extra hardening done in this audit:

- `tests/conftest.py`
  - Added pytest session-start/session-finish cleanup for only the known root temp artifact signature: extensionless 8-character file, exactly 4 bytes, content exactly `blat`.
  - Also clears disposable files from `tests/_runtime_harness/temp_files`.
- `tests/test_regression_dev_qol_tools.py`
  - Added a regression proving `scripts/cleanup-root-temp-junk.py --delete` removes only that exact root junk signature and does not delete near misses.
- `engine/paint_v2/candy_special.py`
  - Removed Python's implicit "last definition wins" risk for Jelly Pearl by renaming the old implementation to legacy helper names.
  - The active shipping functions are now the micro-detail rebuilds:
    - `paint_jelly_pearl_v2`
    - `spec_jelly_pearl`
  - Synced to both runtime mirrors.

Verification from this audit:

```powershell
python AST parse for tests/conftest.py, tests/test_regression_dev_qol_tools.py, engine/paint_v2/candy_special.py
  -> passed

python -m pytest -s -q tests/test_regression_dev_qol_tools.py tests/test_regression_high_detail_specials.py tests/test_regression_runtime_mirror_coverage.py
  -> 50 passed

node scripts/sync-runtime-copies.js --write --verify
  -> synced 2 drifted Candy/Pearl runtime copies

node scripts/sync-runtime-copies.js --check
  -> no drift detected
```

Cleanup status:

- Root 8-character `blat` junk files: `0`
- `tests/_runtime_harness/temp_files`: `0` disposable files

## 2026-04-25 Regular Pattern Category Audit + Rebuild Gate

Completed the regular Pattern Categories pass requested after the Spec Pattern audit.

New audit tool:

- `scripts/audit_pattern_quality.py`
  - Grades all UI-shipping regular `PATTERN_GROUPS` entries.
  - Writes ranked contact sheets plus `report.json` and `report.md`.
  - Scores total quality from intent, originality, wow factor, 2048-scale detail, and canvas coverage.
  - Uses threshold `88.0`.
  - Image-backed/user-art patterns are graded as review-only instead of being auto-rebuilt.

Baseline and final:

- Baseline image-aware audit found `79` procedural rebuild-required patterns.
- Final audit is clean:
  - `307` patterns graded.
  - `0` procedural rebuild-required.
  - `2` image review-only rows remain: `rune_symbols` and `tribal_norse_runes` are image-backed and intentionally not auto-rewritten.
- Final artifacts:
  - `audit/2026-04-25-pattern-quality/final-catalog2/report.md`
  - `audit/2026-04-25-pattern-quality/final-catalog2/report.json`
  - `audit/2026-04-25-pattern-quality/final-catalog2/ranked_worst_first.png`
  - `audit/2026-04-25-pattern-quality/final-catalog2/ranked_best_first.png`

Source rebuild work:

- `shokker_engine_v2.py`
  - Added source-level high-detail regular pattern rebuilds for weak families.
  - Rebuilt/overrode procedural renderers for Tech & Circuit, World Geometry, Natural Textures, Surface Accent, Art Deco/Geometric/Textile, Op-Art, Mathematical/Fractal, Weather, Abstract, PARADIGM, selected Decades, selected Gothic, selected Animal, selected Metal/Carbon, and Pixel Grid.
  - Preserved user image-backed patterns like Biomechanical, Art Deco Classic, Snake Skin, Skate & Surf image art, and decade image imports.

Catalog cleanup:

- `paint-booth-0-finish-data.js`
  - Combined `PARADIGM - Digital Reality` and `PARADIGM - Physics Exploits` into one `PARADIGM` pattern group.
  - Removed picker junk categories: `Final Collection`, `Nature-Inspired`, `Tribal & Cultural`, and `Advanced Geometric`.
  - Moved surviving renderable IDs into stronger parent groups:
    - Final/Advanced IDs moved into Mathematical & Fractal.
    - Nature IDs moved into Natural Textures.
    - Tribal IDs moved into Artistic & Cultural.

Regression coverage:

- `tests/test_regression_dev_qol_tools.py`
  - Added `test_regular_pattern_quality_gate_clears_shipping_catalog`.
  - Added `test_regular_pattern_picker_categories_are_curated`.
- `.gitignore`
  - Explicitly unignored `scripts/audit_pattern_quality.py`.

Verification:

```powershell
node --check paint-booth-0-finish-data.js
  -> passed

python -m py_compile shokker_engine_v2.py scripts/audit_pattern_quality.py tests/test_regression_dev_qol_tools.py tests/test_regression_regular_patterns_quality.py
  -> passed

python -m pytest -q tests/test_regression_dev_qol_tools.py tests/test_regression_regular_patterns_quality.py
  -> 8 passed

python scripts/audit_pattern_quality.py --size 160 --threshold 88 --out-dir audit/2026-04-25-pattern-quality/final-catalog2
  -> 307 graded, 0 rebuild-required

node scripts/sync-runtime-copies.js --write --verify
  -> synced 4 drifted runtime copies

node scripts/sync-runtime-copies.js --check
  -> no drift detected
```
- `.pytest-tmp` still exists because `tests/test_regression_dev_qol_tools.py` intentionally writes the visual-audit smoke report there; it is ignored by git.

Remaining Alpha targets after this audit:

- UI/live-preview parity remains the highest-risk packaging target.
- Verify Ornamental actual picker path, not just renderer distinctness tests.
- Verify Paint Technique through picker -> payload -> preview -> render, because source render tests alone do not prove the UI path.
- Re-run sim-style spot checks for Spec Pattern Overlays that users called visually weak, especially crushed glass.

## 2026-04-25 Spec Pattern Overlay Grading + Rebuild Gate

Completed a full thumbnail-quality pass for the shipping Spec Pattern Overlay catalog.

New audit tool:

- `scripts/audit_spec_pattern_quality.py`
  - Renders every UI-shipping `SPEC_PATTERNS` id.
  - Produces ranked thumbnail sheets and machine-readable scores.
  - Scores each pattern from 1-100 using:
    - intent: 24%
    - originality: 16%
    - wow factor: 20%
    - detail: 24%
    - canvas coverage: 16%
  - Uses a strict Alpha rebuild threshold of `96.0`.
  - Hard-flags low coverage, low detail, low intent, or blob/flat largest-region behavior.

Audit artifacts:

- `audit/2026-04-25-spec-pattern-quality/baseline-threshold96/`
  - Baseline strict run: 35 of 255 patterns fell below the 96 threshold.
- `audit/2026-04-25-spec-pattern-quality/final-verify/`
  - Final verification run: 255 graded, 0 rebuild-required.
  - Main files:
    - `ranked_worst_first.png`
    - `ranked_best_first.png`
    - `rebuild_required.png`
    - `report.json`
    - `report.md`

Source rebuild work:

- `engine/spec_patterns.py`
  - Added ID-gated concept rebuild layers for the 35 below-threshold spec overlays.
  - Rebuild modes include: depth pooling, ink wash, clearcoat bubbles/fish-eyes, drip runs, tape residue, ghost race-number geometry, wax resist, exhaust scorch, battle scratches, electric branches, undercarriage spray, smoke streaks, hard-edge abstract forms, cloud wisps, tarmac grit, cast pits, expressionist splatter, chromatic fringe, sponsor deboss/emboss, pinstripes, rain beads, confetti, caustics, leaf veins, moire rebuild, oil grime, brush bristles, and Kandinsky-style shape geometry.
  - The rebuild hook is ID-gated through `_SPB_SPEC_REBUILD_MODES`, so the rest of the 255-pattern catalog is not churned.
  - Synced to both runtime mirrors.

Regression coverage:

- `tests/test_regression_dev_qol_tools.py`
  - Added `test_spec_pattern_quality_gate_clears_shipping_catalog`.
  - It runs the grader at size 160 with threshold 96 and asserts all shipping spec patterns clear the gate.

Verification:

```powershell
python -m pytest -s -q tests/test_regression_dev_qol_tools.py tests/test_regression_spec_pattern_channel_coverage.py tests/test_regression_spec_pattern_purity.py tests/test_regression_spec_pattern_sm_robustness.py
  -> 42 passed

python -m pytest -s -q tests/test_regression_runtime_mirror_coverage.py tests/test_regression_dev_qol_tools.py
  -> 24 passed

python scripts/audit_spec_pattern_quality.py --size 160 --threshold 96 --out-dir audit/2026-04-25-spec-pattern-quality/final-verify
  -> 255 graded, 0 rebuild-required

node scripts/sync-runtime-copies.js --write --verify
  -> synced 2 spec_patterns runtime mirrors

node scripts/sync-runtime-copies.js --check
  -> no drift detected
```

Cleanup status:

- Root 8-character `blat` junk files: `0`
- `tests/_runtime_harness/temp_files`: `0` disposable files
