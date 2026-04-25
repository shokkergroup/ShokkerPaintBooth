# HEENAN FAMILY — 5-Hour Overnight Repair Loop

**Loop start (real clock):** 2026-04-21 01:07:53 local
**Stop ceiling (5h):** 2026-04-21 06:07:53 local
**Cadence:** ScheduleWakeup every 600s (10 min)
**Orchestrator:** Heenan
**Roster:** Heenan · Flair · Bockwinkel · Sting · Luger · Pillman · Windham · Hawk · Animal · Street · Raven · Hennig

## Mission
Real repair-and-trust pass on SPB. Fix high-trust problems, reduce silent failures, tighten behavior, leave the product more dependable by morning.

## Priority queue
1. Preset / save-load / applyPreset integrity
2. Spec-pattern channel-routing truth
3. JS↔Python registry/picker/render gaps
4. Strengthen weak source-shape ratchets into behavioral tests
5. Color-pick consistency / layer-isolation truth
6. Cleanup that affects trust

## Doctrine reminders
- Heenan decides; Bockwinkel owns systems truth; Luger owns the approved path; Hennig signs off.
- Pillman pressure-tests. Raven challenges ambiguity. Street gated until trust-floor healthy.
- Every claim: verified / inferred / structurally guarded / still risky.
- No vanity. No feature creep. No pretty reports without real fixes.

---

## Iterations

### Iteration 1 — 2026-04-21 01:07 → 01:14 (real)

**Active priority:** P1 — preset/save-load/applyPreset integrity.

**Family on this iteration:**
- Heenan: sequenced and orchestrated.
- Bockwinkel: system-truth mapping of both `applyPreset` definitions + all callers.
- Pillman: exhaustive call-site search (grep across .js/.html), pressure-tested that only 2 live callers exist.
- Luger: chose the polymorphic-dispatcher contract as the approved path (keeps public surface stable, no ui-boot edit needed).
- Animal: heavy-lift fix — renamed the two helpers, wrote the dispatcher, switched `||` → `??` on 6 persistence fields (intensity, pickerTolerance, scale, wear, muted, via `??`).
- Windham: runtime-sync consistency sweep after the JS edit.
- Hennig: gated on the behavioral-test run (not just source inspection).

**Evidence gathered (verified):**
- `paint-booth-2-state-zones.js` had two `function applyPreset` definitions (lines 8801 + 9598) with incompatible arg shapes (string id vs preset object). JS function-declaration hoisting left only the SECOND active; calling with a string id threw TypeError on `preset.zones.map`.
- Two live callers: `paint-booth-6-ui-boot.js:1151` (string id from gallery onclick) and `paint-booth-2-state-zones.js:9581` (object from file reader). Other references are test/comment only.
- Ran `node tests/_runtime_harness/apply_preset_dispatch.mjs` to prove the pre-fix crash reproduces: `_applyPresetFromObject('string')` → `TypeError: Cannot read properties of undefined (reading 'length')`.

**Issue found? YES. Two real persistence bugs:**
1. Preset gallery was silently broken (every card click crashed). Verified by harness.
2. Preset object-form path was clobbering painter-authored falsy values (tolerance=0 → 40, wear=0 → 0 coincidentally, scale=0 → 1.0, muted=false → false coincidentally, intensity=0 → '100').

**Real fix shipped? YES (verified behaviorally).**
Fix shape:
- Single public `function applyPreset(arg)` dispatcher that routes by `typeof`. Unknown inputs are silent no-ops with a `console.warn`.
- Internal helpers: `_applyPresetById(presetId)` (gallery path, unchanged behaviour), `_applyPresetFromObject(preset)` (file-import path, with the `||` → `??` fix).
- Switched 6 fields in `_applyPresetFromObject` from `||` to `??`: `intensity`, `pickerTolerance`, `scale`, `wear`, `muted` (and preserved the 4 others that were already `??`).
- Inline authorial comment above the dispatcher explaining the hoisting shadow bug so the next refactor does not reintroduce it.

**Files changed:**
- `paint-booth-2-state-zones.js` — replaced both `applyPreset` definitions with dispatcher + renamed helpers.
- `electron-app/server/paint-booth-2-state-zones.js` — mirrored via `sync-runtime-copies.js --write`.
- `electron-app/server/pyserver/_internal/paint-booth-2-state-zones.js` — mirrored.
- NEW `tests/_runtime_harness/apply_preset_dispatch.mjs` — V8 sandbox harness that extracts the live dispatch block and drives 7 assertions.
- NEW `tests/test_runtime_apply_preset_dispatch.py` — 11 pytest behavioral tests driving the harness.
- `tests/test_regression_save_load_repair_integrity.py` — replaced two xfail-on-fix ratchet tests (which successfully detected the fix landed) with strict `test_preset_path_uses_nullish_coalesce` and `test_exactly_one_applypreset_definition`. These now REQUIRE the fixed state.

**Tests added/updated:**
- 11 new behavioral pytest cases in `test_runtime_apply_preset_dispatch.py`:
  - Gallery path loads zones correctly.
  - Gallery path unknown-id is silent no-op (no data loss).
  - Object path loads zones.
  - Object path preserves `pickerTolerance=0`, `wear=0`, `muted=false`, `scale=1.0`.
  - Empty zones array doesn't crash.
  - `null`/`undefined`/integer inputs are silent no-ops with console.warn.
  - Pre-fix bug is reproducible by bypassing the dispatcher (guards against regressions that silently make the helper polymorphic).
- 2 strict source-level assertions replacing 2 xfail ratchets in `test_regression_save_load_repair_integrity.py`.

**Gates run (all PASS):**
- `python -m pytest tests -q` → **1243 passed**, 0 failed, 0 skipped (was 1233; +10 net after removing 2 xfail ratchets and adding 11 behavioral tests + 2 strict assertions — skip counts vary with harness availability).
- `node tests/_runtime_harness/validate_finish_data.mjs` → clean (0 problems).
- `node tests/_runtime_harness/registry_collisions.mjs` → all collision buckets empty.
- `node scripts/sync-runtime-copies.js --write` → synced 2 drifted copies, then no drift.
- `node --check` on the 4 key JS files → PARSE CLEAN.
- `python -m py_compile` on the 4 key Python modules → COMPILE CLEAN.

**Proof quality:** VERIFIED (behavioral). The harness actually executes the live dispatcher in V8 against realistic preset shapes and asserts on the output state. Not source-text pins.

**Result:** Two painter-facing persistence bugs eliminated. The preset gallery actually works again. Preset-authored falsy values round-trip.

**Next target:** P2 — spec-pattern channel-routing truth. Investigate the blanket `channels="MR"` default in `engine/compose.py:1358` and whether a safe per-pattern dispatch fix can land without saved-config back-compat risk.

### Iteration 2 — 2026-04-21 01:27 → 01:35 (real)

**Active priority:** P2 — spec-pattern channel-routing truth.

**Family on this iteration:**
- Heenan: orchestrated, decided OPTION D (strict back-compat) over OPTION A (full default change).
- Bockwinkel: mapped the data flow — `sp_channels` is consumed via `"M"/"R"/"C" in sp_channels`, set by JS UI via `_buildSpecPatternLayer` for live painter saves; the bug only bites direct API calls, the brief 2s window before JS normalize fires, and any server-side path that doesn't pre-populate channels.
- Animal: implemented the resolver + replaced the dispatch in BOTH compose sites.
- Pillman: caught a SECOND `sp_layer.get("channels", "MR")` site at line 2176 that I'd missed on the first pass. Without him, the fix would have been half-done.
- Luger: confirmed strict back-compat — any save with explicit channels (incl. "MR") is preserved unchanged; only key-absent or empty-string cases get the inferred default.
- Hennig: gated on the behavioral test (12 new tests in `test_runtime_spec_channel_inference.py`).

**Evidence gathered (verified):**
- `engine/compose.py` had TWO independent dispatch sites that defaulted `channels` to "MR":
  - line 1358 (in compose_finish path)
  - line 2176 (in compose_finish_stacked path)
- The 4 named patterns (`gold_leaf_torn`, `stippled_dots_fine`, `abstract_rothko_field`, `abstract_futurist_motion`) all have parseable `Targets [RGB]=...` declarations in their docstrings. Verified by direct introspection.
- Behavioral verification: with the resolver in place, an absent-channels rothko_field layer produces output BIT-FOR-BIT identical to an explicit-`channels="C"` layer; an absent-channels gold_leaf_torn layer matches an explicit-`channels="M"` layer. Both DIFFER from the pre-fix blanket-MR behavior on the same patterns.

**Issue found? YES.** Painter-facing routing bug:
- `abstract_rothko_field` authored a clearcoat-depth effect that NEVER reached CC under the pre-fix default.
- `gold_leaf_torn` and `stippled_dots_fine` were spilling into the R (Roughness) channel they never authored.
- `abstract_futurist_motion` was leaking into M.

**Real fix shipped? YES (verified behaviorally on the actual numpy pipeline).**
Fix shape:
- Added `_infer_spec_pattern_default_channels(sp_fn)` at module top of `engine/compose.py`. Mirrors the JS-side `_inferSpecPatternDefaultChannels` parser (Targets R=Metallic→M, G=Roughness→R, B=Clearcoat→C). Falls back to "MR" for patterns without a `Targets X=...` phrase. None-safe.
- Replaced `sp_channels = sp_layer.get("channels", "MR")` with `_explicit_channels = sp_layer.get("channels); sp_channels = _explicit_channels if _explicit_channels else _infer_spec_pattern_default_channels(sp_fn)` at BOTH dispatch sites (compose_finish and compose_finish_stacked).
- Strict back-compat: any saved zone with an explicit `channels` value (including "MR") is preserved unchanged. The fix only changes behavior for layers where the key is absent or empty.

**Files changed:**
- `engine/compose.py` — added resolver function (40 lines + docstring), fixed both dispatch sites.
- `electron-app/server/engine/compose.py` — mirrored.
- `electron-app/server/pyserver/_internal/engine/compose.py` — mirrored.
- NEW `tests/test_runtime_spec_channel_inference.py` — 14 tests:
  - 4 parametric resolver tests (each named pattern → expected channel).
  - 1 fallback-MR test (banded_rows has no Targets phrase).
  - 1 None-safety test.
  - 4 parametric "absent channels matches explicit-target" behavioral tests.
  - 2 parametric "absent channels diverges from pre-fix MR" sanity checks.
  - 2 explicit-channels back-compat tests (channels="MR" on rothko stays MR; channels="C" on gold_leaf_torn stays C).
- `tests/test_regression_spec_pattern_channels.py` — replaced two xfail-on-fix ratchet tests (which would have detected the fix landing) with one strict assertion that the bad pattern is ENTIRELY GONE from compose.py and the resolver is called from ≥2 sites.

**Tests added/updated:**
- 14 new behavioral pytest cases.
- 1 strict source-level assertion replacing 2 documenting ratchets.

**Gates run (all PASS):**
- `python -m pytest tests -q` → **1256 passed** (was 1243; +13 net).
- `node tests/_runtime_harness/validate_finish_data.mjs` → 0 problems.
- `node tests/_runtime_harness/registry_collisions.mjs` → all collision buckets empty.
- `node scripts/sync-runtime-copies.js --write` → no drift after sync.
- `node --check paint-booth-0-finish-data.js paint-booth-2-state-zones.js` → PARSE CLEAN.
- `python -m py_compile shokker_engine_v2.py engine/compose.py engine/spec_patterns.py engine/base_registry_data.py` → COMPILE CLEAN.

**Proof quality:** VERIFIED (behavioral). The new tests run actual `compose_finish` calls on a 32×32 canvas with realistic spec_pattern_stack inputs and assert bit-for-bit equality between absent-channels and explicit-target outputs (proving routing matches), and bit-for-bit divergence vs explicit-MR (proving the fix actually changed behavior).

**Result:** Painter-facing channel-routing drift eliminated for the 4 named patterns + any other pattern with `Targets X=...` docstring. Zero saved-config back-compat risk: all existing painter saves with explicit channels keep their behavior.

**Next target:** P3 — JS↔Python registry/picker/render gaps. The 31 unrenderable picker entries (24 PATTERNS + 7 SPEC_PATTERNS). Decide per-id: alias, register, or de-expose.

### Iteration 3 — 2026-04-21 01:47 → 01:54 (real)

**Active priority:** P3 — JS↔Python registry/picker/render gaps (31-id painter-facing silent-no-render gap).

**Family on this iteration:**
- Heenan: triaged into 3 buckets (10 renames / 3 broken fallbacks / 18 family patterns) and decided per-bucket strategy.
- Bockwinkel: mapped each canonical-old → canonical-new pair for the 10 renames; verified all old ids exist in registries.
- Animal: implemented the alias blocks at the right place in shokker_engine_v2.py and engine/spec_patterns.py.
- Pillman: hostile-tested the alias resolution in real Python — every new id resolves, alias-identity preserved (same render tuple).
- Raven: triaged the 3 broken `_PATTERN_FALLBACKS` (chrome_edge / shimmer_pearl_ripple / glow_pulse all missing) — picked semantically closest existing targets so the fallback loop actually wires the ids. Triaged the 18 family patterns: 6 had reasonable fuzzy matches (aliased), 12 had none (de-exposed from picker).
- Windham: synced runtime mirrors after JS edit.
- Hennig: gated on the post-fix gap measurement and the new behavioral tests.

**Evidence gathered (verified):**
- All 31 originally-missing ids verified — exact list confirmed by direct introspection.
- Bockwinkel verified each rename's old id exists in the relevant Python registry (so aliases will succeed).
- Raven verified all 18 family ids appear in JS PATTERN_GROUPS (= painter-pickable = silent no-render).
- Behavioral resolution: after fix, all 19 closed ids resolve in PATTERN_REGISTRY / PATTERN_CATALOG. Recomputed gap: PATTERNS missing 12 → all 12 are now de-exposed from PATTERN_GROUPS so painter cannot reach them. SPEC_PATTERNS missing 0.

**Issue found? YES.** The original 31-id gap (24 PATTERN + 7 SPEC) was real and painter-facing. Selecting any of these in the picker resulted in silent no-render.

**Real fix shipped? YES.**
Three categories addressed:
1. **10 cross-registry rename aliases (HB2 / H4HR-1..2 / HP2 / HP3 / H4HR-4..8):** the JS-canonical id (`carbon_weave_pattern`, `spec_oil_slick`, etc.) now points at the same render function the legacy un-suffixed id points at. Identity-preserving alias — zero behavior change for painters with existing saves; new painters can now select the renamed id and get the SAME render output as the legacy form.
2. **3 broken `_PATTERN_FALLBACKS` repaired:** `chrome_delete_edge` was targeting non-existent `chrome_edge`, now points at `shimmer_chrome_flux`. Same for `pearlescent_flip` → `shimmer_prism_frost` and `uv_night_accent` → `shimmer_neon_weft`. These were in the picker but rendered nothing; now produce a semantically-similar visible output.
3. **6 family-prefix semantic aliases added:** `geo_fractal_triangle` → `fractal`, `geo_hilbert_curve` → `hilbert_curve`, `nature_bark_rough` → `birch_bark`, `nature_water_ripple_pat` → `ripple`, `tribal_celtic_spiral` → `celtic_knot`, `tribal_norse_runes` → `norse_rune`. The remaining 12 family patterns with no adequate semantic match were de-exposed from `PATTERN_GROUPS` (kept in `PATTERNS` array so saved-zone metadata persists, but no longer pickable from the UI).

**Files changed:**
- `shokker_engine_v2.py`:
  - `_PATTERN_FALLBACKS`: 3 broken targets replaced with shimmer_chrome_flux / shimmer_prism_frost / shimmer_neon_weft.
  - NEW `_UI_PATTERN_ALIASES` block: 9 alias entries (3 H4HR/HB2 renames + 6 family-semantic aliases).
- `engine/spec_patterns.py`:
  - NEW `_HP_H4HR_SPEC_ALIASES` block: 7 spec-pattern alias entries.
- `paint-booth-0-finish-data.js`:
  - PATTERN_GROUPS Nature-Inspired / Tribal & Cultural / Advanced Geometric trimmed to only the 6 aliased ids; the 12 unaliased family ids removed from picker exposure (with inline comment explaining why).
- All 3 runtime mirror copies synced.
- `tests/test_regression_js_to_python_registry_coverage.py`:
  - `KNOWN_MISSING_PATTERN_IDS` shrunk from 24 → 12 (only de-exposed family patterns remain).
  - `KNOWN_MISSING_SPEC_PATTERN_IDS` shrunk from 7 → 0 (frozenset()).
  - 3 new tests: `test_de_exposed_family_patterns_absent_from_pattern_groups`, `test_iter3_aliases_actually_resolve_in_python`, `test_iter3_repaired_pattern_fallbacks_have_real_targets`.

**Tests added/updated:**
- 3 new pytest cases covering alias resolution + de-exposure.
- 2 KNOWN_MISSING_* sets shrunk to reflect actual remaining gap.

**Gates run (all PASS):**
- `python -m pytest tests -q` → **1259 passed** (was 1256; +3).
- `node tests/_runtime_harness/validate_finish_data.mjs` → 0 problems.
- `node tests/_runtime_harness/registry_collisions.mjs` → all collision buckets empty.
- `node scripts/sync-runtime-copies.js --write` → synced 2 drifted copies.
- `node --check paint-booth-0-finish-data.js paint-booth-2-state-zones.js` → PARSE CLEAN.
- `python -m py_compile` × 4 modules → COMPILE CLEAN.

**Proof quality:** VERIFIED (alias resolution checked at import time on the actual Python module; absence-from-groups checked at JS source level after edit). The render functions themselves are unchanged so we trust the legacy id rendered correctly previously.

**Result:** 31-id painter-facing silent-no-render gap reduced to 0 picker-visible occurrences. 19 ids now render via aliases; 12 remain unrenderable but are de-exposed so no painter can reach them. The remaining 12 are flagged by the ratchet for a future task.

**Next target:** P4 — strengthen weak ratchets. Survey the source-shape regression tests for spots where behavioral verification would be materially better than current text pins.

### Iteration 4 — 2026-04-21 02:07 → 02:10 (real)

**Active priority:** P4 — strengthen weak source-shape ratchets with behavioral verification.

**Family on this iteration:**
- Heenan: surveyed candidate weak tests, picked `loadConfigFromObj` falsy-value preservation as the highest-leverage upgrade (19 existing source pins, all painter-facing, no end-to-end proof).
- Bockwinkel: mapped the extraction site — `zones = cfg.zones.map(z => ({...}))` block at line 9264 of paint-booth-2-state-zones.js.
- Pillman: demanded a negative-control mutation in the harness to prove the test actually detects the regression it claims to. Built it — swap `??` to `||` on pickerTolerance in-memory, run fresh sandbox, verify `pickerTolerance: 0` becomes 40.
- Hennig: gated on the 22 new tests + negative control passing.

**Evidence gathered (verified):**
- `test_regression_save_load_repair_integrity.py` has 19 parametric pins of the shape `"pickerTolerance: z.pickerTolerance ?? 40" in loadConfigFromObj_body`. These catch an exact-line swap but cannot detect:
  - a downstream re-assignment in the function that clobbers the value,
  - a migration helper that overrides after the initial map,
  - a post-load normalization that re-defaults fields,
  - a repairZoneData quirk that defaults valid values on a type-check boundary.
- Behavioral end-to-end coverage was missing.
- The V8 harness extracts the live mapping block via paren-balance walk (not hardcoded substring), so it tracks structural changes to the block rather than pinning a literal position.
- Negative-control proof: with the mutation applied, `pickerTolerance: 0` → 40 (regression detected). Without the mutation, all 19 falsy fields round-trip faithfully.

**Issue found? NO REAL BUG — this is a test-quality upgrade.** The mapping is currently correct. The upgrade adds trust.

**Real fix shipped? N/A (test strengthening).**

**Files changed:**
- NEW `tests/_runtime_harness/load_config_falsy.mjs` — extracts the live zones.map block, runs it in a sandbox with a realistic falsy-value saved-config, then re-runs a mutated variant as negative control.
- NEW `tests/test_runtime_load_config_falsy_values.py` — 22 pytest cases:
  - 19 parametric field-by-field behavioral assertions (one per tracked persistence field).
  - 1 structural-fields-survive check (id/name/pattern/colorMode).
  - 1 negative-control test that verifies the harness actually catches `??`→`||` regressions.
  - 1 zone-count sanity check.

**Tests added/updated:** 22 new behavioral tests. The 19 source pins in `test_regression_save_load_repair_integrity.py` are PRESERVED as fast sentinels; the new behavioral tests are the strong proof.

**Gates run (all PASS):**
- `python -m pytest tests -q` → **1281 passed** (was 1259; +22).
- `node tests/_runtime_harness/validate_finish_data.mjs` → 0 problems.
- `node tests/_runtime_harness/registry_collisions.mjs` → all buckets empty.
- `node scripts/sync-runtime-copies.js --write` → no drift.
- `node --check` on the 2 key JS files → PARSE CLEAN.

**Proof quality:** VERIFIED (behavioral, with negative-control self-validation). This is the strongest proof class on the project — the test proves not just that the current code is correct, but that the test INFRASTRUCTURE can still detect the bug class it guards.

**Result:** 19-field source-pin ratchet promoted to 22-test behavioral suite with negative-control self-validation. Combined trust is now: source pins catch exact-line swaps cheaply; behavioral tests catch end-to-end clobbering; negative control catches test-infrastructure rot.

**Next target:** P5 — color-pick consistency / layer-isolation / partial-coverage truth. Audit GPU-vs-CPU metric divergence and whether it's worth unifying.

### Iteration 5 — 2026-04-21 02:22 → 02:26 (real)

**Active priority:** P5 — color-pick metric consistency.

**Family on this iteration:**
- Heenan: decided fix > document after measurements showed painter-visible 2.6-5.8% canvas delta at default tolerance (larger at low tolerance). Judged the CPU branch's documented "perceptually-weighted" intent as the canonical behavior; GPU drift was an undocumented perf shortcut.
- Bockwinkel: system truth — confirmed CPU/GPU branches diverge on BT.601 weights, and the CPU branch's inline comment reveals the perceptual intent (green most sensitive, red next, blue least).
- Hawk: perf-aware analysis — 3 multiplies per pixel is trivial (~12M FMAs on 2048²). No perf regression risk from adding weights to the GPU branch.
- Animal: implemented the fix — GPU branch now computes `sqrt(_dr²·0.30 + _dg²·0.59 + _db²·0.11)` matching CPU exactly.
- Pillman: hostile repro — constructed a test scheme with a known target + near-miss pixels, ran both branches through `build_zone_mask` with `is_gpu` forced on and off, asserted bit-for-bit equal output.
- Hennig: gated on the behavioral GPU==CPU proof.

**Evidence gathered (verified):**
- Measured painter-visible divergence on a realistic palette (gold/red/dark):
  - tolerance=20 (tight): CPU catches 1.3x–1.9x more pixels. Extra coverage 3%–20% of canvas.
  - tolerance=30 (default): CPU catches 1.2x–1.4x more. Extra 2.6%–5.8%.
  - tolerance=40 (loose): 1.1x–1.3x. Extra 0.1%–3%.
  - tolerance=60 (very loose): convergent (<0.5%).
- Source inspection: CPU has inline comment "Perceptually-weighted distance: red-green difference matters more than brightness / Weights approximate human visual sensitivity (ITU-R BT.601 luma)". GPU had no comment — just the unweighted form. Intent-vs-implementation drift, not design choice.
- Post-fix behavioral verification: same target + scheme, is_gpu forced on vs forced off → `max(|mask_cpu - mask_gpu|) = 0.0`. Bit-for-bit identical.

**Issue found? YES. Cross-platform painter-visible inconsistency was real.** A preset tuned on GPU hardware would render with different coverage on CPU hardware and vice versa, for no reason beyond a dropped weight.

**Real fix shipped? YES.** GPU branch now applies the same BT.601 weights the CPU branch always documented.

**Painter-facing consequence to flag:** GPU-only painters who tuned tolerance against the pre-fix stricter metric will now catch slightly more pixels at the same tolerance (~2.6-5.8% of canvas at default). A painter who notices can reduce their saved tolerance by ~20% for equivalent output. CPU painters: no change. Cross-platform preset sharing: now consistent.

**Files changed:**
- `engine/core.py` — GPU branch of `build_zone_mask` now computes BT.601-weighted distance identical to CPU branch. 14-line authorial comment explaining the pre-fix drift, the measured painter-visible impact, and the tolerance-adjustment recommendation for affected painters.
- `tests/test_regression_color_pick_coverage.py`:
  - Replaced `test_gpu_cpu_metric_divergence_is_documented_pre_existing` (which pinned the BROKEN state) with two strict tests:
    - `test_gpu_cpu_metric_is_unified_on_bt601` — source-level assertion that the pre-fix unweighted GPU form is GONE and both branches now contain the BT.601 weights.
    - `test_gpu_cpu_pick_produces_identical_output` — behavioral: forces `is_gpu` on and off, runs `build_zone_mask` on the same input, asserts `max(|mask_cpu - mask_gpu|) < 1e-5`. Strongest possible cross-platform proof. (Skips gracefully if cupy unavailable.)

**Tests added/updated:**
- 1 net new test (3 → 4 in the color-pick file).
- 1 existing ratchet test rewritten from "document pre-existing bug" to "assert fix is permanent".

**Gates run (all PASS):**
- `python -m pytest tests -q` → **1282 passed** (was 1281; +1 net).
- `node tests/_runtime_harness/validate_finish_data.mjs` → 0 problems.
- `node tests/_runtime_harness/registry_collisions.mjs` → all buckets empty.
- `node scripts/sync-runtime-copies.js --write` → no drift (Python mirrors refresh at build time, not per-edit, by design).
- `python -m py_compile` × 5 modules → COMPILE CLEAN.

**Proof quality:** VERIFIED (behavioral, cross-platform identical-output). The strongest proof class — we're not just asserting source text, we're running both code paths on identical input and asserting equal output.

**Result:** Cross-platform color-pick inconsistency eliminated. GPU and CPU painters now get identical tolerance semantics; preset sharing works. Minor painter-visible change for GPU-only painters documented inline.

**Next target:** P6 — cleanup that affects trust. Stale follow-up docs, dead paths, ambiguity that creates false confidence.

### Iteration 6 — 2026-04-21 02:38 → 02:43 (real)

**Active priority:** P6 — cleanup that affects trust.

**Family on this iteration:**
- Heenan: chose the most trust-misleading docs first (regression 2h summary, regression 2h worklog, 4 test-module docstrings).
- Raven: cleanup with amend-not-delete doctrine — UPDATE blocks at the top of historical docs, preserving the dated audit narrative; rewrote test-module docstrings to reflect current fixed state.
- Luger: documentation truth — explicit "FIXED in iter N of overnight loop" sections so a future reader immediately sees the current state vs. the historical claim.
- Hennig: gated on no-behavior-change (docstring-only edits) via full test suite re-run.

**Evidence gathered (verified):**
- `docs/REGRESSION_2H_FINAL_SUMMARY.md` claimed "2 spawn_tasks filed" for bugs #4 (applyPreset) and #6 (31 unrenderable patterns) — both now fixed; spawn_tasks obsolete. Also listed #3 (channel-default) and #6 (GPU/CPU divergence) as unresolved — both now fixed.
- `docs/REGRESSION_2H_LOOP_WORKLOG.md` had no superseding banner; a future dev reading it would think the listed "pre-existing pins" remain unfixed.
- `tests/test_regression_save_load_repair_integrity.py` docstring described the preset-path `||` divergence as "pinned, not fixed" and the duplicate `applyPreset` as "should be reconciled by a separate audit" — both fixed in iter 1 of this loop.
- `tests/test_regression_color_pick_coverage.py` docstring described GPU/CPU divergence as "pre-existing, NOT HARDMODE; flagged but not fixed" — fixed in iter 5.
- `tests/test_regression_spec_pattern_channels.py` title literally said "pre-existing-bug documentation" — fixed in iter 2.
- `tests/test_regression_js_to_python_registry_coverage.py` context section said 31 ids "silently render nothing" with no mention that 19 had been fixed.
- One dead reference found: `test_preset_path_nullish_coalesce_divergence_is_preexisting` — a test I deleted in iter 1 but still referenced in a docstring.

**Issue found? YES (documentation truth).** 5 trust-critical artifacts were lying about current state.

**Real fix shipped? YES (docs only, no behavior change).** Each updated file now has a clear UPDATE block at the top showing what's changed and when, with links to the overnight worklog/final-summary for details. Historical narrative preserved — the audit logs still read as an accurate record of what was true on 2026-04-20.

**Files changed (docstring/markdown only, zero behavior):**
- `docs/REGRESSION_2H_FINAL_SUMMARY.md` — added UPDATE banner at top listing all 5 now-fixed items with links to overnight iters.
- `docs/REGRESSION_2H_LOOP_WORKLOG.md` — added UPDATE banner at top.
- `tests/test_regression_save_load_repair_integrity.py` — rewrote module docstring; fixed one stale test-name reference.
- `tests/test_regression_color_pick_coverage.py` — rewrote module docstring reflecting the fix.
- `tests/test_regression_spec_pattern_channels.py` — rewrote module docstring.
- `tests/test_regression_js_to_python_registry_coverage.py` — rewrote context section.

**Tests added/updated:** 0 new tests. Existing tests unchanged in behavior; only their documenting docstrings were updated.

**Gates run (all PASS):**
- `python -m pytest tests -q` → **1282 passed** (unchanged — docs-only edits).
- `node scripts/sync-runtime-copies.js --write` → no drift.

**Proof quality:** VERIFIED (no behavior change). Docstring updates can't regress anything; pytest count unchanged confirms.

**Result:** 5 trust-critical stale docs now truthfully reflect current state. A future dev reading any of them immediately sees what was historical vs. what's current. No spawn_tasks should be dispatched from the stale "pinned bug" references — they'd be duplicating already-shipped work.

**Next target:** Re-evaluate remaining queue. Trust floor assessment:
- Preset persistence: FIXED + behaviorally proven.
- Channel routing: FIXED + behaviorally proven.
- Registry gaps: 19/31 closed + de-exposed; 12 de-exposed remain (unreachable).
- GPU/CPU color-pick: FIXED + behaviorally proven cross-platform identical.
- Stale docs: cleaned up.
Trust floor is in good shape. Remaining time (~3.5h until ceiling): opportunistic deeper work. Could consider Street's lane now if something genuinely memorable AND safe shows up. Otherwise continue with P2-style cleanup of the remaining lower-severity items or loop-back checks.

### Iteration 7 — 2026-04-21 02:55 → 02:59 (real)

**Active priority:** Opportunistic adjacent-bug scan (option A) — iter 2 channel-inference follow-up.

**Family on this iteration:**
- Heenan: picked option A per recommendation; scoped to adjacent-bug hunt first.
- Pillman: posed the hostile question — "which patterns DON'T match the strict `Targets [RGB]=...` regex but do have intent?" Scanned the full PATTERN_CATALOG and found 4 docstrings with intent that our strict form MISSED (guilloche_hobnail, guilloche_moire_eng, spec_brick_mortar, spec_iridescent_film).
- Bockwinkel: widened the scan using a looser regex to quantify the gap — 15+ pattern docstrings use the abbreviated `R=Metallic.` form with no `Targets` prefix.
- Animal: broadened the regex from `Targets\s+([RGB])=(?:Metallic|Roughness|Clearcoat)\b` to `\b([RGB])=(?:Metallic|Roughness|Clearcoat)\b`. Also canonicalized channel-string emission to MRC order (matches JS-side `_inferSpecPatternDefaultChannels` output format, keeps test assertions stable).
- Raven: risk scan — searched for negation-form matches ("not R=Metallic", "no G=Roughness", etc.). Found 0. Broadening is safe; zero false-positive risk from negated phrasings.
- Hennig: gated on the 21-test run + full suite.

**Evidence gathered (verified):**
- Strict regex matched 56 of 262 patterns with inferred intent (21%).
- Broadened regex matches 111 of 262 (42%). Net: 55 additional patterns now route to the right channel instead of the MR fallback.
- New inference distribution: 45× M only, 32× R only, 15× C only, 11× RC, 7× MRC, 1× MC.
- Zero negation-form phrasings in the entire catalog — broadening is safe.
- Behavioral verification: each of 6 newly-captured patterns has its docstring intent routed correctly (guilloche_hobnail→M, guilloche_moire_eng→M, hairline_polish→R, bead_blast_uniform→R, jeweling_circles→M, knurl_diamond→MR).
- Canonical-order output verified: `knurl_diamond` docstring says `G=Roughness + R=Metallic.` (G first) — resolver emits `MR` (M first, canonical order), not `RM`.
- JS-side `_inferSpecPatternDefaultChannels` at paint-booth-2-state-zones.js:6899 already uses the broad form (no `Targets` anchor). Python is now in parity.

**Issue found? YES (adjacent bug).** The strict regex was missing 55 patterns' authored channel intent, routing them to MR by default. Not catastrophic but inconsistent — patterns like `hairline_polish` (clearly G=Roughness intent) were spilling into M.

**Real fix shipped? YES.**
- Broadened regex in `engine/compose.py`: `\b([RGB])=(?:Metallic|Roughness|Clearcoat)\b` (drop the `Targets\s+` anchor).
- Canonicalized output to MRC order via a two-pass design (collect letters → emit in fixed order).
- Updated authorial comment to document the broadening rationale and the negation-form safety check.

**Files changed:**
- `engine/compose.py` — regex broadened + resolver canonicalized.
- `tests/test_runtime_spec_channel_inference.py`:
  - 6 new parametric cases added to `test_resolver_matches_docstring_intent` (guilloche_hobnail, guilloche_moire_eng, hairline_polish, bead_blast_uniform, jeweling_circles, knurl_diamond).
  - NEW `test_resolver_emits_channels_in_canonical_mrc_order` test.

**Tests added/updated:** 7 new tests.

**Gates run (all PASS):**
- `python -m pytest tests -q` → **1289 passed** (was 1282; +7).
- `node tests/_runtime_harness/validate_finish_data.mjs` → 0 problems.
- `node tests/_runtime_harness/registry_collisions.mjs` → all buckets empty.
- `node scripts/sync-runtime-copies.js --write` → no drift.
- `python -m py_compile` × 5 modules → COMPILE CLEAN.

**Proof quality:** VERIFIED (behavioral). The 6 new parametric tests run the resolver on real catalog patterns and assert the correct channel is inferred; the canonical-order test pins a specific docstring-order edge case.

**Result:** ~40% of spec-pattern catalog (was 20%) now gets docstring-inferred channel routing. Patterns like guilloche_hobnail (metallic-intent surface texture) no longer spill into the roughness channel. JS/Python parity maintained.

**Next target:** Continue opportunistic scan. Look for more persistence paths with `||`-vs-`??` regressions. Audit any config loaders for old formats. OR evaluate Street's lane (brief unlocks this after trust floor is healthy — which it is, as of iter 6).

### Iteration 8 — 2026-04-21 03:11 → 03:17 (real)

**Active priority:** Opportunistic adjacent-bug scan (option A1 — other `||` persistence regressions).

**Family on this iteration:**
- Heenan: orchestrated the scan per priority recommendation.
- Bockwinkel: swept all `z.X || <falsy>` patterns in paint-booth-2-state-zones.js (75+ matches), categorized into safe (arrays/strings) vs potentially-bug (numeric/boolean).
- Pillman: traced each candidate to a real function. Found the SAVE path `exportPreset` (line 9520+) had `scale: z.scale || 1.0` — a painter's scale=0 would be silently promoted to 1.0 in the exported .shokker file, breaking recipient render. Also found `_extractZoneDNA` (line 12052+) has similar `||` usage but a post-filter strip step at line 12137 collapses 0 anyway, so net effect depends on the full save/load round-trip — left for a later iter.
- Animal: fixed `exportPreset` by switching scale/rotation/wear/muted/patternOpacity from `||` to `??`. Arrays kept on `||` (empty array ≈ missing). Added inline authorial comment.
- Raven: cleanup scan — verified the anchor is unique enough to target (both loadConfigFromObj and exportPreset have `zones: zones.map(z => ({` — scoped harness extraction via `function exportPreset` prefix).
- Hennig: gated on the 6-test behavioral run + negative-control.

**Evidence gathered (verified):**
- Source-level sweep: 75+ `z.X || ...` occurrences in the file, categorized by falsy-legitimacy of the field's value space.
- `exportPreset` path had 3 fields with bug risk (`scale`, `rotation`, `wear`, `muted`, `patternOpacity`). `rotation=0` and `wear=0` coincidentally match the default; `scale=0`, `patternOpacity=0` are genuine painter-visible regressions if the value is serialized.
- Post-fix verification: V8 sandbox extracts the live `zones.map` expression from exportPreset, runs it with a zone where every tracked field is falsy, asserts all 5 survive.
- Negative control: mutate `scale: z.scale ?? 1.0` back to `||` in-memory, rerun → scale=0 passes through as 1.0 (regression detected). Proves the harness actually exercises the code.

**Issue found? YES.** Preset EXPORT was losing scale=0 and patternOpacity=0 painter-saved values. Parallel to the iter 1 preset IMPORT fix — this is the matching save-side bug.

**Real fix shipped? YES (verified behaviorally).**
`paint-booth-2-state-zones.js::exportPreset` — 5 fields switched from `||` to `??`: scale, rotation, wear, muted, patternOpacity. Arrays intentionally kept on `||`. Inline comment documenting the rationale.

**Files changed:**
- `paint-booth-2-state-zones.js` — 5 `??` replacements in `exportPreset`.
- Both runtime mirror copies synced.
- NEW `tests/_runtime_harness/export_preset_falsy.mjs` — V8 sandbox harness mirroring the iter 4 pattern (load_config_falsy.mjs). Extracts the live `exportPreset` mapping, uses `function exportPreset` as scope anchor to avoid collision with the `loadConfigFromObj` mapping, runs with falsy-valued zone, asserts round-trip, + in-harness negative-control mutation.
- NEW `tests/test_runtime_export_preset_falsy_values.py` — 6 pytest cases (5 parametric field checks + 1 negative-control test).

**Tests added/updated:** 6 new behavioral tests.

**Gates run (all PASS):**
- `python -m pytest tests -q` → **1295 passed** (was 1289; +6).
- `node tests/_runtime_harness/validate_finish_data.mjs` → 0 problems.
- `node tests/_runtime_harness/registry_collisions.mjs` → all buckets empty.
- `node scripts/sync-runtime-copies.js --write` → synced 2 drifted mirror copies.
- Self-gate via negative-control: PASS.

**Proof quality:** VERIFIED (behavioral, with negative-control self-validation). Same trust class as iter 4 — runs the live mapping expression in V8 against realistic input and asserts end-to-end field preservation.

**Result:** Round-trip trust symmetry restored. Preset IMPORT (iter 1) and preset EXPORT (iter 8) now BOTH preserve painter-authored falsy values. A preset saved with scale=0 round-trips through a .shokker file and loads back as scale=0 — not silently repaired to 1.0 on either side.

**Next target:** Continue adjacent-bug scan. The `_extractZoneDNA` path (line 12052+) warrants investigation — its `||` usages are mitigated by the strip step at line 12137, but the strip step itself strips legitimate zeros. Either audit that or move to a different area.

### Iteration 9 — 2026-04-21 03:29 → 03:37 (real)

**Active priority:** Opportunistic adjacent-bug scan (B4 stability sweep → B3 server.py audit → B1 DNA extract audit).

**Family on this iteration:**
- Heenan: sequenced B4 → B3 → B1. B4 passed clean (stability confirmed at 1295). B3 audit of server.py found zero `.get() or <falsy>` bugs — all such usages are on string fields where empty ≈ missing (filename, dir, etc.). B1 was the find: DNA extract + strip had two paired bugs.
- Bockwinkel: mapped both halves — (1) the capture-step `||` promoted painter-0 to default BEFORE reaching the strip, (2) the strip step then blanketed `val === 0` and removed any surviving zeros. Together they silently erased painter intent on ~10+ fields.
- Pillman: constructed 3 behavioral cases — painter-zero, equals-default, arbitrary non-default — and asserted the right outcome for each. Added case A2 (scale=0) after discovering the capture step was the primary erasure site.
- Animal: fixed BOTH halves:
  - Capture: switched `||` to `??` on 20+ numeric/boolean fields (scale/rotation/wear/muted/flip/hue/saturation/brightness across all 5 base-layer families).
  - Strip: replaced the blanket `val === 0 || val === false` with a per-field `_DNA_DEFAULTS` lookup table (~40 canonical defaults). A value is stripped only when it equals the field's own default.
- Raven: verified the DNA-DECODE path (`pasteZoneDNA` at line 12207) wouldn't regress — it uses `if (key in dna)` and simply assigns, so forward-compatible with either old DNA strings (fewer keys, target zone's prior values remain) or new DNA strings (more keys, painter intent transfers correctly).
- Hennig: gated on the 6-test behavioral run.

**Evidence gathered (verified):**
- B4: 1295 pytest passed across full suite. validate_finish_data + registry_collisions harnesses clean. Sync clean. **Zero regressions from iters 1-8.**
- B3: 30+ `.get(...)` usages in server.py. Every one is either (a) correct Python `.get('x', default)` form (not affected by falsy-coalesce), or (b) `.get('x') or ''` on string fields where empty=missing. Zero bugs.
- B1: DNA strip step erases `val === 0` globally. Capture step uses `||` on numeric fields. Both together silently lose painter-set zeros on non-zero-default fields. Verified by V8 harness running the live `_extractZoneDNA` on 3 realistic zone states.
- Post-fix: all 6 assertions pass — painter-set zeros survive (case A), default values are still stripped for compactness (case B), arbitrary non-default values round-trip (case C).

**Issue found? YES.** Real painter-facing bug: copying a zone's DNA where the painter had explicitly turned OFF the base-color overlay (`baseColorStrength=0`) silently transferred as "default-on" on paste.

**Real fix shipped? YES (both halves, behaviorally proven).**
`paint-booth-2-state-zones.js::_extractZoneDNA`:
- 20+ numeric/boolean capture fields: `||` → `??`.
- Strip step: per-field `_DNA_DEFAULTS` lookup replaces blanket falsy strip.
- Inline authorial comment documenting the rationale and the round-trip-symmetry guarantee.

**Files changed:**
- `paint-booth-2-state-zones.js` — capture step (20+ lines) + strip step (40-entry _DNA_DEFAULTS table + new loop logic).
- Both runtime mirror copies synced.
- NEW `tests/_runtime_harness/dna_strip_preserves_intent.mjs` — V8 sandbox, extracts live `_extractZoneDNA`, runs 3 behavioral cases.
- NEW `tests/test_runtime_dna_strip_preserves_intent.py` — 6 pytest cases covering the bug scenarios + compactness + arbitrary-value round-trip.

**Tests added/updated:** 6 new behavioral tests.

**Gates run (all PASS):**
- `python -m pytest tests -q` → **1301 passed** (was 1295; +6).
- `node tests/_runtime_harness/validate_finish_data.mjs` → 0 problems.
- `node tests/_runtime_harness/registry_collisions.mjs` → all buckets empty.
- `node scripts/sync-runtime-copies.js --write` → synced 2 drifted copies.
- node --check paint-booth-2-state-zones.js → PARSE CLEAN.

**Proof quality:** VERIFIED (behavioral, end-to-end). The harness extracts the live function via brace-balance, invokes it on realistic zone inputs, and asserts per-key presence/absence/value preservation. Both halves of the fix (capture + strip) are exercised.

**Result:** DNA copy-paste now correctly round-trips painter-explicit falsy values. A painter who turns OFF a base-color overlay (sets strength=0) and shares that zone's DNA with another painter can trust the setting will transfer.

**Next target:** Re-evaluate. All three audit buckets swept; trust floor now even healthier than after iter 6. Remaining time ~2h. Consider:
- B5 code-comment "pre-existing" sweep (iter 6 caught docstrings; scan .js/.py code comments too).
- Street's lane: one memorable premium improvement (brief unlocks this).
- Diminishing-returns check: if next iter finds nothing, begin wind-down toward final summary.

### Iteration 10 — 2026-04-21 03:48 → 03:52 (real)

**Active priority:** B5 code-comment sweep + cross-feature integration test.

**Family on this iteration:**
- Heenan: ran B5 first, found it empty, pivoted to a high-leverage cross-feature integration test.
- Raven: swept source files for "pre-existing bug" / "known bug" / FIXME / TODO / XXX markers. Found 3 matches, all benign historical references. No stale claims.
- Bockwinkel: identified the highest-leverage iter-10 work — an integration test that stitches iters 1/8/9 into a single end-to-end painter round-trip.
- Pillman: diagnosed a false-positive in the first harness run — the preset chain doesn't carry baseColorStrength, so testing it through preset round-trip was testing a pre-existing design gap, not a regression. Restructured the test to cleanly separate the preset chain from the DNA chain.
- Hennig: gated on the 6-test behavioral run + 0-failure integration composition gate.

**Evidence gathered (verified):**
- B5 comment sweep: 0 stale bug-claim comments found. Iter 6's docstring cleanup was thorough enough that code comments don't need an update pass.
- Integration harness runs 4-step painter-workflow chain:
  1. Configure zone with pickerTolerance=0, wear=0, muted=false, baseColorStrength=0.
  2. exportPreset serializes — falsy values survive (iter 8 fix).
  3. applyPreset(preset_object) via polymorphic dispatcher — painter's 0s load as 0s (iter 1 fix).
  4. _extractZoneDNA on a separate zone — baseColorStrength=0 survives capture+strip (iter 9 fix).
- All 6 assertions pass. Zero failures in the composition gate.

**Issue found? Indirectly.** The first harness run revealed that the .shokker preset format doesn't carry `baseColorStrength` — a pre-existing design gap (not a regression). Documented by restructuring the test to respect the chain boundaries rather than trying to paper over it.

**Real fix shipped? No new code fixes.** This iter added the cross-feature test that proves all prior fixes compose correctly.

**Files changed:**
- NEW `tests/_runtime_harness/overnight_integration_roundtrip.mjs` — V8 harness that extracts FOUR live code blocks (exportPreset map, _applyPresetFromObject, applyPreset dispatcher, _applyPresetById, _extractZoneDNA) and drives a realistic painter round-trip.
- NEW `tests/test_runtime_overnight_integration.py` — 6 pytest cases covering each step + an all-or-nothing composition gate.

**Tests added/updated:** 6 new integration tests.

**Gates run (all PASS):**
- `python -m pytest tests -q` → **1307 passed** (was 1301; +6).
- `node scripts/sync-runtime-copies.js --write` → no drift (no source edits this iter).
- All runtime harnesses green.

**Proof quality:** STRONGEST YET. This is the first test that exercises multiple iter-fixes in a single end-to-end scenario. Guards against a bug where fix A in one layer is silently undone by defect B in a downstream layer — a class of regression that per-iter-isolated tests can miss.

**Result:** 9 individual fixes verified to COMPOSE correctly through a realistic painter round-trip. No silent undo. No cross-layer shadowing. The overnight loop's fixes are internally consistent.

**Next target:** Wind down. Run one more adjacent-bug probe iter 11 if something surfaces. Otherwise iter 12 (~04:10) begins the final summary so verification and tests finish before 06:07 ceiling.

### Iteration 11 — 2026-04-21 04:03 → 04:12 (real)

**Active priority:** Final adjacent-bug check + begin final summary.

**Family on this iteration:**
- Heenan: decided stop-adding-features, begin-winding-down.
- Bockwinkel: scanned `engine/*.py` for `.get('x') or <number>` (Python's `||` equivalent). Zero matches.
- Hennig: gated on the stability re-run.

**Evidence gathered (verified):**
- `engine/` Python has zero `.get() or N` persistence bugs (already confirmed for server.py in iter 9; iter 11 extends to engine/).
- Full test suite stable at 1307 passing, zero failures, zero flakes.

**Issue found? No.** Adjacent-bug territory is genuinely exhausted given the trust floor's current state.

**Real fix shipped? No code changes.** Iter 11 is verification + summary authoring.

**Files changed:**
- NEW `docs/HEENAN_FAMILY_5H_OVERNIGHT_FINAL_SUMMARY.md` — comprehensive final handoff with per-iter table, painter-facing consequences, family usage, open items, honest confidence statement.

**Gates run:**
- `python -m pytest tests -q` → **1307 passed** (stable — no changes since iter 10).

**Result:** Overnight loop is ready to close. Final summary delivered with ~2 h of ceiling remaining.

**Loop status:** COMPLETE. No ScheduleWakeup scheduled from iter 11 under normal operation — the loop exits gracefully with trust floor at its highest point of the session.

### Iteration 12 — 2026-04-21 04:17 (real, final verification)

**Active priority:** Loop termination verification.

**Family on this iteration:**
- Heenan: called the stop.
- Hennig: signed off on the final gate sweep.

**Final verification at 04:17:**
- `python -m pytest tests -q` → **1307 passed**, 0 failed, 0 skipped (bit-identical to iter 11).
- `node tests/_runtime_harness/validate_finish_data.mjs` → `"problems": []`.
- `node tests/_runtime_harness/registry_collisions.mjs` → all collision buckets empty.
- `node scripts/sync-runtime-copies.js --check` → no drift detected.
- `node --check` on 7 key JS files → all PARSE CLEAN.
- `python -m py_compile` on 7 key Python modules → all COMPILE CLEAN.

**Result:** Every gate green. Every fix holds. Test count, harness output, parse status — all stable vs iter 11.

---

## LOOP TERMINATED

**Wall-clock window:** 2026-04-21 01:07:53 → 04:17:45 (3 h 10 min)
**Ceiling:** 06:07:53 (terminated ~1 h 50 min early)
**Reason for early termination:** priority queue exhausted, trust floor healthy, cross-feature integration test proves fixes compose correctly, iter 11 adjacent-bug probe came up empty.

**Final deliverables on disk:**
- `docs/HEENAN_FAMILY_5H_OVERNIGHT_WORKLOG.md` (this file) — 12-iter history.
- `docs/HEENAN_FAMILY_5H_OVERNIGHT_FINAL_SUMMARY.md` — painter-facing and maintainer-facing handoff.

**No follow-up iter scheduled.** No ScheduleWakeup fired from iter 12.
