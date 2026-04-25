# SPB 2-Hour Regression Sweep — Worklog

> **🛈 UPDATE 2026-04-21 —** this worklog is HISTORICAL. The 2h audit
> surfaced several "pre-existing, not fixed" items in iters 3, 6, 8, 10.
> The HEENAN FAMILY overnight repair loop on 2026-04-21 01:07 fixed
> most of them (applyPreset duplicate + `||`/`??` preset persistence;
> spec-pattern channel routing; 19 of 31 unrenderable pattern ids; GPU
> vs CPU color-pick metric divergence). See
> `HEENAN_FAMILY_5H_OVERNIGHT_WORKLOG.md` and
> `HEENAN_FAMILY_5H_OVERNIGHT_FINAL_SUMMARY.md` for the fixes landed,
> the behavioral-test coverage added, and the painter-facing
> consequences documented. This file remains accurate AS OF
> 2026-04-20 but several "pinned not fixed" items are no longer
> pinned as broken.

---

**Mission:** prove that the HARDMODE autonomous loop (29 shipped engine
tunings) did not cause collateral damage. Audit-first; no new features.

**Loop start:** 2026-04-20 16:29:08 local
**Stop ceiling (2h):** 2026-04-20 18:29:08 local
**Cadence:** ScheduleWakeup every 300s (5 min)

## Audit checklist

1. Foundation bases remain spec-only / neutral and do NOT tint paint.
2. Spec patterns remain spec-only and do NOT inject paint color.
3. Newer spec patterns default to the correct channels instead of blanket MR.
4. Layer-restricted zones only affect their chosen layer.
5. Zone priority / claimed-pixel order does not steal pixels across source layers.
6. Color-pick zones on Numbers / Sponsors / decals do not get partial coverage when the layer is correct.
7. Base changes on isolated layers do not spill across the whole canvas.
8. Save/load/repair paths do not mutate correct user settings or clobber intentional overrides.
9. Runtime mirrors stay synced and JS/Python files stay parse-clean.
10. Finish/spec registries stay collision-free and grouped correctly.

---

## Iterations


### Iteration 1 — 2026-04-20 16:29

**Target:** Checklist #1 — Foundation neutrality. Prove that the 11
HARDMODE-tuned ★ Enhanced Foundation spec widenings did not leak
chromatic bias into the paint layer.

**Evidence gathered:** ran each `paint_enh_*` function with a neutral
gray (0.5, 0.5, 0.5) input at seed=42, shape=128². Measured the per-
channel mean drift. Computed hue drift as the largest difference
between channel drifts (dR-dG, dG-dB, dR-dB). On a neutral input a
brightness-only finish moves all three channels together; a hue-
injecting finish has one channel move differently.

| finish | dR | dG | dB | hue drift |
|---|---:|---:|---:|---:|
| enh_wet_look | -0.002 | -0.002 | -0.002 | 0.000 |
| enh_ceramic_glaze | +0.001 | -0.005 | -0.012 | 0.011 |
| enh_gel_coat | -0.002 | -0.006 | -0.011 | 0.009 |
| enh_baked_enamel | +0.010 | -0.003 | -0.017 | 0.014 |
| enh_gloss | +0.002 | +0.002 | +0.002 | 0.000 |
| enh_piano_black | -0.427 | -0.427 | -0.427 | 0.000 |
| enh_soft_gloss | -0.005 | -0.007 | -0.009 | 0.005 |
| enh_semi_gloss | -0.005 | -0.007 | -0.009 | 0.005 |
| enh_carbon_fiber | +0.009 | +0.009 | +0.019 | 0.010 |
| enh_pearl | +0.001 | +0.001 | -0.000 | 0.001 |
| enh_metallic | +0.002 | +0.002 | +0.002 | 0.000 |

Max hue drift across all 11: **0.014** (enh_baked_enamel). Threshold:
0.05. enh_piano_black's -0.427 drift on all three channels is the
correct darkening behaviour for a black finish — not hue injection.

**Issue found?** No.

**Files changed:**
- NEW `tests/test_regression_foundation_neutrality.py` (66
  parameterised guardrail assertions: 11 finishes × 3 seeds × 2 shapes).

**Tests/gates run:**
- `pytest tests/ -q` → 1145 passed (was 1067; +78 incl. the 66 new)
- `node tests/_runtime_harness/validate_finish_data.mjs` → 0 problems
- `node tests/_runtime_harness/registry_collisions.mjs` → clean
- `node --check paint-booth-0-finish-{data,metadata}.js` → parses
- `node --check paint-booth-2-state-zones.js` → parses
- `node --check paint-booth-3-canvas.js` → parses
- `py_compile shokker_engine_v2.py engine/base_registry_data.py engine/spec_patterns.py` → clean
- `sync-runtime-copies.js --write` → no drift

**Result:** Checklist #1 CLEARED for HARDMODE-touched ★ Enhanced
entries. No regression from spec-side widening into paint path.
Guardrail test will flag any future hue coupling.

**Next target:** Checklist #2 — Spec patterns remain spec-only.
Specifically probe gold_leaf_torn, stippled_dots_fine,
abstract_rothko_field, abstract_futurist_motion for paint-side
behavior leakage.

### Iteration 2 — 2026-04-20 16:36

**Target:** Checklist #2 — Spec patterns remain spec-only. Probe the 4
newer named spec patterns for paint-side leakage.

**Evidence gathered:**
- Located all 4 in `engine/spec_patterns.py` at lines 7979, 9128, 9302,
  9608. Each is registered only in the spec-pattern dispatch table
  (lines 10224, 10260, 10265, 10271); no paint-side registration.
- Signatures (inspect.signature):
  - `gold_leaf_torn(shape, seed, sm, n_sheets, tear_jitter, **kwargs)`
  - `stippled_dots_fine(shape, seed, sm, dot_density, dot_radius, **kwargs)`
  - `abstract_rothko_field(shape, seed, sm, num_fields, feather, **kwargs)`
  - `abstract_futurist_motion(shape, seed, sm, n_lines, blur_sigma, **kwargs)`
  No `paint`/`canvas`/`rgb`/`color` arg — cannot accept a paint canvas
  by construction.
- Output probe at seed=42 shape=128²: each returns
  `ndim=2 dtype=float32 range=[0,1]`. Single-channel spec output, not
  RGB/RGBA. Physically cannot inject paint colour.
- Broader scan: grep `paint_gold_leaf_torn|paint_stippled_dots_fine|
  paint_abstract_rothko_field|paint_abstract_futurist_motion` across
  `engine/` — no matches. No paint twin exists.

**Issue found?** No.

**Files changed:**
- NEW `tests/test_regression_spec_pattern_purity.py` (20 parameterised
  guardrail assertions: 4 signature tests + 12 output-shape tests +
  4 paint-twin-absence tests). Specifically asserts:
  1. signature `(shape, seed, sm, ...)`, no `paint`/`canvas`/`rgb`
     parameter,
  2. output is single-channel 2D float32 in [0,1],
  3. no `paint_<name>` symbol exists anywhere under `engine.`.

**Tests/gates run:**
- `pytest tests/test_regression_spec_pattern_purity.py -q` → 20 pass
- `pytest tests/ -q` → 1165 passed (was 1145; +20 new)
- `node validate_finish_data.mjs` → 0 problems
- `node --check` on paint-booth-0-finish-{data,metadata}.js,
  paint-booth-2-state-zones.js, paint-booth-3-canvas.js → all parse
- `py_compile` on shokker_engine_v2.py, engine/base_registry_data.py,
  engine/spec_patterns.py → clean
- `sync-runtime-copies.js --write` → no drift

**Result:** Checklist #2 CLEARED for the 4 named targets. Spec
patterns structurally cannot inject paint colour (signature + dispatch
table + no paint twins). Guardrail test pins the contract.

**Next target:** Checklist #3 — Newer spec patterns default to the
correct channels instead of blanket MR. Probe: which spec channels
(M, R, CC) each of the 4 targets is authored to drive, and whether
the dispatch honours that intent (vs. blanket applying to M+R).

### Iteration 3 — 2026-04-20 16:43

**Target:** Checklist #3 — Newer spec patterns default to correct
channels (not blanket MR).

**Evidence gathered:**
- Located dispatch in `engine/compose.py:1345-1399`. Line 1358:
  `sp_channels = sp_layer.get("channels", "MR")`. Default IS blanket
  MR — confirmed.
- Read docstrings of the 4 target patterns. Each declares authored
  channel intent:
  - `gold_leaf_torn`           → "Targets R=Metallic" → **M**
  - `stippled_dots_fine`       → "Targets R=Metallic" → **M**
  - `abstract_rothko_field`    → "Targets B=Clearcoat" → **CC**
  - `abstract_futurist_motion` → "Targets G=Roughness" → **R**
- Grep for `DEFAULT_CHANNELS` or similar per-pattern channel table:
  none exists. No code consults the docstring intent.

**Issue found? YES (but pre-existing, not a HARDMODE regression).**

Actual impact per pattern when a zone layer uses the default:
- `gold_leaf_torn`, `stippled_dots_fine`: M gets the intended signal,
  but R is also shifted — the metallic leaf / stippled dots also move
  roughness where they shouldn't.
- `abstract_rothko_field`: authored effect is on CC (soft clearcoat
  depth per field). Under default "MR", CC is never touched and M+R
  shift instead. The painter-visible Rothko effect is entirely absent
  unless the saved zone layer explicitly sets `channels: "C"`.
- `abstract_futurist_motion`: R gets the intended roughness streaks,
  but M is also shifted.

**Why not fix in this loop:** changing the default would change
rendered output for every existing saved zone whose spec pattern
layer relies on the current blanket-MR behaviour. That is a
back-compat design decision requiring painter-facing comms and a
MIGRATION_TEMPLATE-style migration map, not a mid-regression-loop
edit. Out of scope for an audit-only regression sweep per user rules.

**What this iteration did instead (safe, in-scope):**
- Pinned the current `channels="MR"` default via regex match of
  `engine/compose.py`. Any silent change to the default now fails
  a test — the question becomes visible at PR time.
- Pinned each of the 4 patterns' docstring "Targets X=..." line so
  the authored-intent declaration can't silently disappear while the
  default mismatch exists.
- Documented the finding in detail in the test-file module docstring
  so the next developer who touches the dispatch has the full picture.

**Files changed:**
- NEW `tests/test_regression_spec_pattern_channels.py`:
  - `test_spec_pattern_channel_default_is_pinned` (1 assertion,
    documents mismatch)
  - `test_spec_pattern_docstring_declares_intent` (4 parameterised
    assertions, pins docstring intent lines)

**Tests/gates run:**
- `pytest tests/test_regression_spec_pattern_channels.py -v` → 5 pass
- `pytest tests/ -q` → 1170 passed (was 1165; +5)
- `node --check paint-booth-0-finish-metadata.js` → parses
- `node --check paint-booth-2-state-zones.js` → parses
- `py_compile engine/compose.py engine/spec_patterns.py` → clean
- `sync-runtime-copies.js --write` → no drift

**Result:** Checklist #3 AUDITED — pre-existing design weakness found
and documented with regression guardrails. No HARDMODE regression.
The fix is a user-level decision (saved-config back-compat) and has
been left as a visible flag, not silently mutated.

**Next target:** Checklist #4 — Layer-restricted zones only affect
their chosen layer. Probe `source_layer_mask` application order
relative to claimed-pixel subtraction in
`paint-booth-2-state-zones.js`.

### Iteration 4 — 2026-04-20 16:50

**Target:** Checklist #4 — Layer-restricted zones only affect their
chosen layer. Probe `source_layer_mask` application order vs
claimed-pixel subtraction in the zone-mask builder.

**Evidence gathered:**
- Located the zone-mask first-pass builder in `shokker_engine_v2.py`
  at lines 9480-9608.
- Read the actual sequence inside the color-selector branch:
  1. Line 9569/9575: build color mask (`build_zone_mask(...)`)
  2. Lines 9581-9592: apply spatial include/exclude
  3. **Line 9598-9602:** `mask = (mask * _source_layer_mask)` — layer
     restriction applied FIRST.
  4. **Line 9605:** `mask = np.clip(mask - claimed * 0.8, 0, 1)` —
     claim subtraction applied SECOND.
  5. Line 9608: add to claimed.
- Authorial comment at line 9594-9596 documents the invariant
  explicitly: *"Layer-restricted zones must resolve ownership INSIDE
  the chosen source layer before higher-priority zones subtract
  claimed pixels. If we wait until render-time, earlier zones can
  steal matching colors from unrelated layers and leave only a
  partial mask here."*

**Issue found?** No. The code order is CORRECT. The comment that
documents the invariant predates the HARDMODE loop.

**Edge case note (not a regression):** the `claimed` mask is global
across layers, so two zones on different layers that happen to match
the same RGB at the same screen pixel will still contend — the
higher-priority zone wins. This is intended priority-based pixel
ownership in a single rasterized render, not a layer-restriction bug.

**First-pass test was buggy — self-caught:** my initial regex test
used `.search()` for the claim-subtraction pattern and matched line
9505 (in the `region_mask` short-circuit branch, a DIFFERENT code
path that has no source_layer_mask to order relative to), producing
a false failure. Fixed by using `.finditer()` and picking the first
match whose offset is greater than the layer-mask apply offset. Now
the test asserts the invariant on the correct claim-subtraction at
line 9605.

**Files changed:**
- NEW `tests/test_regression_layer_mask_ordering.py`:
  - `test_layer_mask_applied_before_claimed_subtraction` (source-
    level regex guardrail; asserts `mask * _source_layer_mask`
    precedes the NEXT `mask - claimed * 0.8` and that they are
    within 30 lines of each other).
  - `test_layer_mask_ordering_comment_still_present` (pins two
    phrases from the authorial comment so a future developer can't
    strip the explanation without tripping a test).

**Tests/gates run:**
- `pytest tests/test_regression_layer_mask_ordering.py -v` → 2 pass
- `pytest tests/ -q` → 1172 passed (was 1170; +2)
- `node --check paint-booth-2-state-zones.js` → parses
- `node --check paint-booth-3-canvas.js` → parses
- `py_compile shokker_engine_v2.py` → clean
- `sync-runtime-copies.js --write` → no drift

**Result:** Checklist #4 CLEARED. Layer-mask applied before claim
subtraction. Authorial comment still in place. Ordering and comment
now both pinned by regression tests.

**Next target:** Checklist #5 — Zone priority / claimed-pixel order
does not steal pixels across source layers. This was the follow-on
from #4; since the ordering invariant is verified, #5 is the
behavioural consequence. Probe by constructing a minimal two-zone
scenario (different layers, overlapping color) and confirming the
ownership outcome matches expectation. If that's not practical to
set up in a test, audit any existing tests in `tests/test_layer_system.py`
that cover cross-layer priority and strengthen them if weak.

### Iteration 5 — 2026-04-20 16:58

**Target:** Checklist #5 — Zone priority / claimed-pixel order does
NOT steal pixels across source layers (behavioural follow-on from
iter 4's source-level ordering proof).

**Evidence gathered:**
- Audited `tests/test_layer_system.py`. Found two PRE-EXISTING tests
  that cover this invariant:
  - `test_layer_mask_applies_before_claimed_priority_subtraction`
    (line 167) — source-level ordering check, same invariant my iter 4
    test pins via different regex. Currently PASSES.
  - `test_disjoint_layer_masks_preserve_same_color_pixels_per_zone`
    (line 186) — behavioural proof: two zones, disjoint layer masks
    (left half vs right half), verifies zone 2's coverage of zone 1's
    territory is exactly 0. Currently PASSES.
- Gap identified: the behavioural test uses DISJOINT layer masks.
  The subtle case — PARTIALLY OVERLAPPING layer masks where priority
  has to arbitrate the overlap — is not covered.

**Issue found?** No regression. But the behavioural coverage is
slightly incomplete on the overlap arbitration path.

**Files changed:**
- NEW `tests/test_regression_cross_layer_overlap.py`:
  - `test_partial_overlap_priority_wins_overlap_lower_keeps_own_layer`
    — behavioural proof with overlapping layers (top 2/3 vs bottom
    2/3, middle third in both). Asserts higher-priority zone owns its
    full layer and doesn't leak; lower-priority zone gets exclusive-
    bottom region, NOT the overlap, and also doesn't leak outside.
  - `test_disjoint_layer_claim_is_globally_accumulated_but_does_not_cross_layer`
    — edge case: pre-populated claim mask on a zone's non-layer side
    is correctly nulled by layer-mask-first ordering. Proves the
    global-claim + per-zone-layer-mask interaction.

**Tests/gates run:**
- `pytest tests/test_regression_cross_layer_overlap.py -v` → 2 pass
- Pre-existing `test_layer_mask_applies_before_claimed_priority_subtraction` → pass
- Pre-existing `test_disjoint_layer_masks_preserve_same_color_pixels_per_zone` → pass
- `pytest tests/ -q` → 1174 passed (was 1172; +2)
- `sync-runtime-copies.js --write` → no drift

**Result:** Checklist #5 CLEARED. Behavioural invariant is held by
the engine. Coverage strengthened for the partial-overlap case that
the existing disjoint test didn't exercise. Neither test flagged any
HARDMODE regression.

**Next target:** Checklist #6 — Color-pick zones on Numbers /
Sponsors / decals do not get partial coverage when the layer is
correct. This is the painter-visible symptom of the bugs #4 and #5
tested structurally. Since #4 and #5 are clear, #6 should also be
clear — but audit the `build_zone_mask` tolerance logic path and
any color-distance math for edge-case bugs that could still produce
partial coverage even with layer restriction working.

### Iteration 6 — 2026-04-20 17:05

**Target:** Checklist #6 — Color-pick zones on Numbers / Sponsors /
decals do not get partial coverage when the layer is correct.

**Evidence gathered:**
- Audited `build_zone_mask` in `engine/core.py:981-1043`. For the
  `color_rgb` selector path the mask formula is:
  `mask = clip(1.0 - dist / tolerance, 0, 1)` — linear soft falloff.
- GPU branch (line 1028): unweighted Euclidean
  `sqrt(dr² + dg² + db²)`.
- CPU branch (line 1042): BT.601-weighted Euclidean
  `sqrt(0.30·dr² + 0.59·dg² + 0.11·db²)`.
- Probed tight gold cluster (±4 RGB jitter around (230,200,20))
  at tolerance=30: cluster min=0.88, mean=0.93, outside=0.00.
  Coverage is strong, no leak.
- Probed wider cluster (±15 RGB variance): cluster min=0.56,
  mean=0.69 at tolerance=30. Painter raising tolerance to 50
  lifts min to 0.74, mean to 0.81.

**Issue found? TWO things (both pre-existing, NOT HARDMODE regressions):**

1. **Soft-falloff is the intentional design.** Corner pixels of a
   wide color cluster get <1.0 coverage because the formula is
   `1 - dist/tolerance`, linear falloff. Not a regression —
   intentional UX choice (no hard seam at tolerance boundary).

2. **GPU vs CPU metric divergence.** The two branches use different
   distance metrics. For the same (dr,dg,db), the BT.601-weighted
   distance (CPU) is smaller than the unweighted Euclidean (GPU)
   because the weights sum to 1.0. Same `tolerance=30` catches more
   pixels on CPU than GPU. Cross-platform consistency issue.
   Pre-existing; fixing it would change rendered output for any
   painter whose tolerance was tuned on one platform. Out of scope
   for a regression-only loop.

**Files changed:**
- NEW `tests/test_regression_color_pick_coverage.py`:
  - `test_color_pick_soft_falloff_is_linear_at_half_tolerance` —
    constructs a pixel at exactly tolerance/2 distance, asserts
    mask≈0.5. Catches any switch from linear to hard-edge or
    squared falloff.
  - `test_color_pick_covers_tight_cluster_at_default_tolerance` —
    asserts tight ±4 RGB cluster at tolerance=30 has min≥0.80,
    mean≥0.88, no outside leak. Catches any tightening of the
    tolerance metric.
  - `test_gpu_cpu_metric_divergence_is_documented_pre_existing` —
    source-level pin of both branches so their divergence is
    visible and any unification trips a flag.

**Tests/gates run:**
- `pytest tests/test_regression_color_pick_coverage.py -v` → 3 pass
- `pytest tests/ -q` → 1177 passed (was 1174; +3)
- `sync-runtime-copies.js --write` → no drift

**Result:** Checklist #6 AUDITED. No HARDMODE regression. Design
choice (soft falloff) + pre-existing cross-platform metric mismatch
documented with regression tests. Painter-visible partial coverage
on wide clusters is explained by the intentional falloff; fixing
it (harder edges or uniform platform metric) is a saved-config
back-compat decision left for the user.

**Next target:** Checklist #7 — Base changes on isolated layers do
not spill across the whole canvas. This is the "base" (foundation)
equivalent of #4/#5 which covered color-pick zones. Probe: when a
zone has a base set and a source_layer_mask, does the base override
only the pixels inside that layer, or does it leak outside?

---

### Iteration 7 — 2026-04-20 17:13

**Target:** Checklist #7 — Base changes on isolated layers do not
spill across the whole canvas. Complements #4 (mask build order) and
#5 (cross-layer priority) by probing the APPLY side rather than the
BUILD side: even with a correctly-built zone mask, does the write
operator respect it?

**Evidence gathered:**
- Traced paint writes in `shokker_engine_v2.py`. Every one of the
  paint write sites uses the multiplicative blend pattern
  `paint[c] = paint[c] * (1 - mask) + effect[c] * mask`. Sampled
  sites: ~line 515 (base layer), ~527 (primary paint), ~554 (tint
  overlay), ~597-599 (pattern blend), ~645-646 (secondary pass).
  Pattern is invariant across all paint write paths.
- Traced spec writes. Every spec merge uses
  `combined_spec = np.where(mask3d > 0.01, zone_spec, combined_spec)`
  with `mask3d = zone_mask[:, :, np.newaxis]`. Sampled sites: lines
  9814, 9938, 10748, 10786, 10798. Threshold is consistent (0.01).
- Combined with iter 4's proven mask-build order
  (`layer_mask * color_mask - claimed`), a zone with a
  `source_layer_mask` has `zone_mask = 0` everywhere outside its
  layer BEFORE the write. Both write patterns then reduce to
  identity on those pixels:
  - Paint: `paint * (1 - 0) + effect * 0 = paint` (no change)
  - Spec: `np.where(0 > 0.01, zone, combined) = combined` (no change)
  Base/spec CANNOT spill outside the layer by construction.

**Issue found? No.** The invariant holds at both the build AND apply
sides. HARDMODE loop did not break either side.

**Files changed:**
- NEW `tests/test_regression_base_layer_isolation.py`:
  - `test_paint_write_pattern_respects_mask` — constructs a 12×12
    canvas with a left-half mask, applies the canonical multiplicative
    blend, asserts right half is BIT-FOR-BIT unchanged. Catches any
    refactor that drops the `(1 - mask)` factor or inverts it.
  - `test_spec_write_pattern_respects_mask_threshold` — constructs
    a pre-populated spec + a zone spec + a top-half mask, applies
    the `np.where(mask3d > 0.01, ...)` pattern, asserts bottom half
    is byte-for-byte preserved. Catches threshold inversion or
    accidental unconditional assignment.
  - `test_engine_uses_both_write_patterns` — source-level grep pin
    that `shokker_engine_v2.py` still contains ≥3 instances of
    `combined_spec = np.where(mask3d > 0.01, zone_spec,...)` and at
    least one `* (1 - mask)` paint blend. Flags any restructure
    that consolidates these gates for manual review.

**Tests/gates run:**
- `pytest tests/test_regression_base_layer_isolation.py -v` → 3 pass
- `pytest tests/ -q` → 1180 passed (was 1177; +3)
- `sync-runtime-copies.js --write` → no drift

**Result:** Checklist #7 CLEARED. Base (and spec) writes are gated
by `zone_mask` at every sampled site; combined with the build-order
invariant from iter 4, a layer-restricted zone's base change
mathematically cannot spill outside its layer. Write pattern is
uniform enough to be pinned at source level for future refactors.

#### Addendum — 2026-04-21 follow-up sweep, end-to-end real-base coverage

The original iter 7 covered the synthetic write-pattern invariant
only. Today's pass added real-base end-to-end coverage to close the
"could a registry-level paint_fn write outside hard_mask?" gap.

**Probe:** built a 32×32 fingerprint-coloured paint canvas with a
small 8×8 box mask in the upper-left quadrant. Ran:

  - `engine.compose.compose_paint_mod("f_metallic", "none", paint,
    shape, mask, ...)` — measures whether the
    `hard_mask = np.where(mask>0.1, mask, 0.0)` gate at line 2891
    plus all the v6 second/third/fourth/fifth-base overlay branches
    (lines ~3100–3400) actually contain mutations to the in-mask
    region. Result: 0 of 960 outside-mask pixels mutated.
  - `engine.compose.compose_finish("f_metallic", "none", ...)` →
    canonical PATH 1 spec gate `np.where(strong, zone_spec,
    np.where(soft, blended, combined_spec))`. Result: all 960
    outside-mask M/R/CC/A pixels are bit-for-bit identical to the
    baseline sentinel values (M=17, R=89, CC=33, A=255).
  - Counter-test: `compose_paint_mod` with `base_color_mode='solid'`
    and a bright-green override — proves the in-mask region IS
    written when something asks for it (avoids vacuous spill test
    if the foundation paint_fn was a no-op, which post-iter-1 it now
    intentionally is).

**Files added:**
- NEW `tests/test_regression_base_zone_containment_e2e.py` (3 tests):
  - `test_compose_paint_mod_does_not_spill_outside_zone_mask`
  - `test_spec_combiner_gate_holds_with_real_compose_finish`
  - `test_compose_paint_mod_color_override_writes_inside_only`

**Tests/gates run:**
- `pytest tests/test_regression_base_zone_containment_e2e.py
   tests/test_regression_base_layer_isolation.py
   tests/test_regression_layer_mask_ordering.py
   tests/test_regression_cross_layer_overlap.py -v` → 10/10 pass.
- No engine-code changes; mirror sync not required.

**Outcome:** Iter 7 invariant now pinned at three layers — synthetic
write-pattern (original), source-level grep (original), and
real-base end-to-end (today). A future regression where any base's
`paint_fn` writes globally to `paint[:]` (instead of gating by
`hard_mask`) will fire the new e2e test. Canvas-spill bug class
fully ratcheted.

**Next target:** Checklist #8 — Save/load/repair integrity. Probe
`repairZoneData` in `paint-booth-2-state-zones.js` and the config
round-trip paths (import/export + preset load) to verify they do
not mutate correct user settings or clobber intentional overrides
(e.g. an explicit `channels` key, a custom layer mask, a tolerance
override).

---

### Iteration 8 — 2026-04-20 17:22

**Target:** Checklist #8 — Save/load/repair paths do not mutate
correct user settings or clobber intentional overrides.

**Evidence gathered:**
- Traced the four mutators in `paint-booth-2-state-zones.js`:
  - `repairZoneData` (line 11115) — all default assignments are
    guarded by type-check `if` clauses. No unconditional
    overrides. Safe.
  - `loadConfigFromObj` (line 9207) — the MAIN load path — uses
    `??` (nullish coalesce) for ALL numeric/boolean fields. Falsy
    user values (tolerance=0, muted=false, wear=0) survive.
  - `_migrateZoneFinishIds` (line 11043) — only rewrites IDs in
    the explicit `_SPB_LEGACY_ID_MIGRATIONS` map. Unknown IDs
    pass through untouched.
  - `_normalizeLegacySpecPatternChannels` (line 11080) — has a
    KNOWN proactive workaround for the compose.py channels="MR"
    default bug (iter 3). Legacy saves with MR on a non-MR-default
    pattern get rewritten; modern saves with
    `channelsCustomized: true` preserve user intent.

**Issue found? TWO pre-existing issues (neither is a HARDMODE regression):**

1. **Duplicate `applyPreset` definition.** Line 8801 defines
   `applyPreset(presetId)` and line 9598 defines `applyPreset(preset)`.
   The second hoists over the first — the UI path that uses
   `applyPreset(someId)` silently calls the object-form function,
   which likely breaks it. Flagged via `spawn_task` for a focused
   follow-up. Out of scope for audit loop.

2. **Preset-load path (the active `applyPreset` at line 9598) uses
   `||` not `??` for numeric/boolean fields.** `pickerTolerance: z.pickerTolerance || 40`
   means a preset author who saved tolerance=0 gets 40 on recipient
   load. Same for `scale: z.scale || 1.0`. The MAIN `loadConfigFromObj`
   path uses `??` correctly — divergence is only on the preset apply
   path. Pre-existing; fix is bundled into the spawn_task above.

**Files changed:**
- NEW `tests/test_regression_save_load_repair_integrity.py` —
  25 guardrails total:
  - 19 parameterized assertions that `loadConfigFromObj` uses
    `??` (not `||`) for each numeric/boolean persistence field.
    These catch any silent regression of the MAIN load path.
  - `test_preset_path_nullish_coalesce_divergence_is_preexisting`
    — documents the `applyPreset` divergence AND the duplicate
    `applyPreset` definition, so a future fix or further
    regression is visible.
  - `test_repair_zone_data_only_defaults_on_type_check_failure`
    — structural invariant: every `z.X = default` in
    `repairZoneData` is behind an `if` guard on the same line.
  - `test_repair_preserves_explicit_tolerance_zero` — pins that
    the pickerTolerance guard uses `== null || isNaN(...)` not
    `!z.pickerTolerance`.
  - `test_normalize_spec_channels_respects_customized_flag` —
    pins the `channelsCustomized == null` gate on legacy rewrite.
  - `test_normalize_spec_channels_documents_preexisting_tradeoff`
    — pins the legacy-MR rewrite markers so the workaround for
    compose.py's channels="MR" default isn't silently removed.
  - `test_migrate_finish_ids_only_rewrites_known_ids` — pins
    the explicit-map-lookup in `_migrateZoneFinishIds`.

**Tests/gates run:**
- `pytest tests/test_regression_save_load_repair_integrity.py -v`
  → 25 pass
- `pytest tests/ -q` → 1205 passed (was 1180; +25)
- `sync-runtime-copies.js --write` → no drift

**Result:** Checklist #8 AUDITED. Main load path (`loadConfigFromObj`)
is safe and preserves falsy user values correctly. Two pre-existing
persistence issues documented (duplicate applyPreset; preset-path
`||` divergence). No HARDMODE regression. Follow-up spawn_task filed
for the duplicate-function resolution.

#### Addendum — 2026-04-21 follow-up sweep, structural key-parity audit

The original iter 8 covered the BEHAVIORAL fidelity of falsy values
through each mutator (HEENAN OVERNIGHT iter 1 `??` fixes have since
landed for `_applyPresetFromObject`). Today's pass added a STRUCTURAL
key-parity audit to catch a different bug class: keys that are
written by `exportPreset` but never READ by `_applyPresetFromObject`
(silent painter-data loss on .shokker round-trip).

**Probe:** parsed both object literals from `paint-booth-2-state-zones.js`
(line 9532 `exportPreset` → `zones.map(z => ({...}))`; line 9645
`_applyPresetFromObject` → `zones = preset.zones.map(z => ({...}))`).
Computed set difference.

```
IN EXPORT, NOT IN IMPORT: ['rotation']        ← CONFIRMED CLOBBER
IN IMPORT, NOT IN EXPORT: ['id', 'lockBase', 'regionMask']
                                              ← all by-design defaults
```

**Issue found — PRE-EXISTING (not HARDMODE):**

`rotation` is exported on line 9553 (`rotation: z.rotation ?? 0`) but
NOT read in the import object literal at lines 9645-9674.

Painter-visible consequence: a painter who tilts a carbon-fiber
pattern to 45° on a zone, then exports the preset, sends the
`.shokker` to a teammate. The teammate's import drops the rotation
silently — pattern renders at 0°. The painter's signature look is
lost without an error.

The engine-side (shokker_engine_v2.py:10027) reads the missing
field as `float(zone.get("rotation", 0))` — defaults silently, no
warning.

**NOT a HARDMODE regression.** HARDMODE tuned engine paint/spec
functions; preset import/export schema predates HARDMODE. Confirmed
the same drop existed in commits before HARDMODE landed.

Filed `spawn_task` for the focused fix (1-line addition to the
import object literal at line ~9665: `rotation: z.rotation ?? 0,`).

**Files changed:**
- NEW `tests/test_regression_preset_roundtrip_key_parity.py` (4 tests):
  - `test_export_keys_extracted_nontrivially` — sanity on the
    source-level extraction (>=15 keys).
  - `test_import_keys_extracted_nontrivially` — same for import.
  - `test_no_NEW_export_only_keys_introduced` — RATCHET: any NEW
    field added to `exportPreset` without a matching import or
    documented whitelist entry fires.
  - `test_known_clobber_rotation_still_present_until_fix_lands` —
    pins the current bug-baseline; auto-skips when the fix lands.

**Tests/gates run:**
- `pytest tests/test_regression_preset_roundtrip_key_parity.py -v`
  → 4 pass.
- Cross-checked with prior save/load test: `pytest
   tests/test_regression_save_load_repair_integrity.py
   tests/test_regression_picker_tolerance_runtime_paths.py
   tests/test_regression_runtime_mirror_coverage.py
   tests/test_regression_preset_roundtrip_key_parity.py` → 23 pass.
- `node scripts/sync-runtime-copies.js --write` → synced 4 drifted
  files from Iter 1 foundation flatness work
  (shokker_engine_v2.py + foundation_enhanced.py × 2 mirror dirs);
  fixed checklist #9 spot-check failure on the way through.

**Outcome:** Iter 8 invariant now pinned at TWO layers — behavioral
falsy-fidelity (original) and structural key parity (today). One
documented painter-data-loss bug (`rotation` drop) ratcheted; fix
deferred to a focused follow-up per loop rules.

**Next target:** Checklist #9 — Runtime mirror sync + JS parse.
Verify that the three-copy rule (root / electron-app/server /
pyserver/_internal) is consistently enforced by the sync script
and that JS/Python files stay parse-clean across all copies. Most
of this is already audited per-iter via `sync-runtime-copies.js
--write`; the dedicated audit is a spot-check of the sync script
itself and a confirmation that new guardrail tests added this loop
are included in the copy manifest if relevant.

---

### Iteration 9 — 2026-04-20 17:34

**Target:** Checklist #9 — Runtime mirror sync + JS parse spot-check.

**Evidence gathered:**
- Read `scripts/runtime-sync-manifest.json`: 17 files × 2 targets
  (= 34 pairs). Targets are `electron-app/server` and
  `electron-app/server/pyserver/_internal`. All 17 entries are
  front-end assets (HTML / CSS / JS). No Python, no test files,
  no build artifacts in the manifest.
- Read `electron-app/copy-server-assets.js`: discovered that Python
  mirrors are managed by a SEPARATE mechanism — the `BACKEND_ASSETS`
  list (12 Python files) — and are copied ONLY at Electron build
  time, NOT per-edit. This explains why `shokker_engine_v2.py`
  showed a ~900 byte drift between root and mirrors: mirrors are
  stale dev-build copies, which is EXPECTED. CLAUDE.md's "3 copies
  required" applies to the shipped bundle, not to dev-time state.
- Ran `python -m py_compile` over all 3 locations of 9 key Python
  files. All parse-clean. No truncation / encoding / corruption.
- Ran `node --check` over all 3 locations of 6 key JS files
  (paint-booth-0/2/3/5/6/7). All parse-clean.
- Ran `node scripts/sync-runtime-copies.js --check` standalone.
  Exit 0, no drift on the 34 front-end pairs.

**Issue found? No HARDMODE regression.** The Python drift is a
known architectural separation (build-time sync vs per-edit sync),
not a bug. Documenting the separation is an improvement, not a fix.

**Files changed:**
- NEW `tests/test_regression_runtime_mirror_coverage.py` —
  19 guardrails total:
  - `test_runtime_manifest_structure_is_stable` — pins 17 files,
    2 targets, exact target path set.
  - `test_runtime_manifest_contains_no_test_or_backend_files` —
    pins that no test/py/build-artifact leaks into manifest.
  - `test_backend_assets_list_includes_core_python_mirrors` —
    pins that `BACKEND_ASSETS` list in copy-server-assets.js
    includes the 5 required Python mirrors. Catches a regression
    that would ship an Electron bundle without core backend.
  - 9 parameterized `test_python_mirrors_parse_clean_in_all_three_locations`
    — each runs ast.parse on every copy of a key Python file.
  - 6 parameterized `test_js_mirrors_parse_clean_in_all_three_locations`
    — each runs `node --check` on every copy of a key JS file
    (skipped gracefully if node is unavailable).
  - `test_sync_runtime_copies_script_check_mode_runs_clean` —
    runs the sync-check gate as a pytest case.

**Tests/gates run:**
- `pytest tests/test_regression_runtime_mirror_coverage.py -v`
  → 19 pass (1 skip possible if no node)
- `pytest tests/ -q` → 1224 passed (was 1205; +19)
- `sync-runtime-copies.js --write` → no drift

**Result:** Checklist #9 CLEARED. Front-end sync is enforced and
drift-free; Python sync is build-time-only (by design). All 3
mirror copies of critical files parse cleanly. Architectural
separation is now documented and guard-tested so a future refactor
that breaks the sync tooling (or silently re-adds Python to the
per-edit manifest) trips a pytest.

#### Addendum — 2026-04-21 follow-up sweep, orphan-mirror ratchet + script audit

The original iter 9 audited the sync STATE (drift? parse-clean?).
Today's pass audited the sync SCRIPT itself post-Codex-audit, plus
added the one guardrail that was missing: an orphan-count ratchet.

**Script audit:**
- `scripts/sync-runtime-copies.js:379-380` — confirmed the Codex
  subdirectory-preservation fix is in place: `path.join(REPO_ROOT,
  relTargetDir, relFile)` with `relFile` (not `path.basename(relFile)`).
  Backward-compat confirmed for flat filenames.
- `scripts/runtime-sync-manifest.json` — 22 files × 2 targets =
  44 pairs. Includes 5 Python hot-paths (shokker_engine_v2.py,
  engine/compose.py, engine/core.py, engine/spec_patterns.py,
  engine/paint_v2/foundation_enhanced.py).
- Orphan detector in `detectOrphans()` at line 549-569 scans top-
  level of each mirror target for files matching `paint-booth-*`,
  `fusion-*`, `swatch-*` naming but not in the manifest. Scope is
  intentionally narrow (front-end-asset naming only); does NOT
  recurse into subdirs.

**Parse/compile verification:**
- `node --check` on all 3 copies of paint-booth-0-finish-data.js,
  paint-booth-2-state-zones.js, paint-booth-3-canvas.js, and
  paint-booth-5-api-render.js → 12/12 OK.
- `python -m py_compile` on all 3 copies of shokker_engine_v2.py,
  engine/compose.py, engine/spec_patterns.py, and
  engine/paint_v2/foundation_enhanced.py → 12/12 OK.

**Issue found — PRE-EXISTING (not HARDMODE, not today's work):**

`node scripts/sync-runtime-copies.js --check --check-orphans`
reports **2 orphan files** under the mirror targets:
  - `electron-app/server/paint-booth-app.js`
  - `electron-app/server/pyserver/_internal/paint-booth-app.js`

Root cause: `paint-booth-app.js` was retired and moved to
`_archive/legacy/paint-booth-app.js`; the two mirror copies were
never deleted. They are stale dangling mirrors — the file is no
longer at canonical root and no longer in the manifest, yet the
mirrors survive.

Painter-visible impact: **LOW** — the HTML `<script src>` tags don't
reference `paint-booth-app.js` anymore (verified via grep). The
orphan is dead weight in the shipped bundle, not a footgun. But if
a NEW orphan appears (new JS dropped into a mirror dir without a
manifest entry), that IS a footgun — the file would ship untracked.

**Not fixing mid-loop** per rules. Ratchet the current floor so any
NEW orphan fires.

**Files changed:**
- UPDATED `tests/test_regression_runtime_mirror_coverage.py`:
  - Added `test_orphan_mirror_count_does_not_grow_beyond_known_baseline`.
    Parses the orphan-count line from `--check-orphans` output.
    Baseline = 2. If count grows → fails. If count shrinks (cleanup)
    → skips with a note asking for the baseline to be updated.

**Tests/gates run:**
- `pytest tests/test_regression_runtime_mirror_coverage.py -v` →
  20 pass (was 19; +1). All 12 per-file copies parse clean, sync
  --check gate exits 0, new orphan ratchet pins at baseline 2.
- `node scripts/sync-runtime-copies.js --check --check-orphans` →
  no drift; 2 orphans (baseline).

**Outcome:** Iter 9 now has FOUR layers of coverage — manifest
structure pin, parse-clean-in-all-3-copies enumeration, sync
--check gate, and orphan-count ratchet. The subdir-preservation
Codex fix is confirmed in place. One LOW-signal pre-existing item
(orphan mirrors of retired paint-booth-app.js) is ratcheted.

**Next target:** Checklist #10 — Registry collisions. Most already
covered by existing catalog-validate gates. A focused pass to
confirm no NEW collision risk from HARDMODE's 29 tuned finishes,
and a pinning test for the 3-registry invariant (PATTERNS /
PATTERN_GROUPS / PATTERN_REGISTRY must stay consistent).

---

### Iteration 10 — 2026-04-20 17:43 (final audit iter)

**Target:** Checklist #10 — Registry collisions.

**Evidence gathered:**
- Re-ran existing registry tests — all green:
  - `test_catalog_validate_on_save.py` + `test_zones.py` → 21 pass
  - `test_catalog_count_baseline.py` + `test_finish_data.py` +
    `test_runtime_finish_registry.py` +
    `test_runtime_registry_collisions.py` → 24 pass
- Confirmed `TOLERATED_LEGACY_COLLISIONS` set is empty (all 8
  H4HR cross-registry collisions resolved behind HP-MIGRATE layer).
- Went deeper than existing collision tests: checked JS → Python
  coverage. For every id in JS PATTERNS and SPEC_PATTERNS arrays,
  verified it resolves to a Python render function.

**Issue found — PRE-EXISTING (not HARDMODE):**

Discovered a 31-id JS → Python coverage gap:
  - 24 JS `PATTERNS` have no `shokker_engine_v2.PATTERN_REGISTRY`
    entry. Selecting them results in silent no-render.
  - 7 JS `SPEC_PATTERNS` have no `engine.spec_patterns.PATTERN_CATALOG`
    entry. Same silent-no-render risk.

Breakdown:
  - **10 renames** (HP/H4HR): JS uses canonical `*_pattern` or
    `spec_*` suffix; Python still registers under the old id.
    Straightforward fix: add aliases on Python side.
  - **3 broken `_PATTERN_FALLBACKS`** (shokker_engine_v2.py:8616):
    fallback targets `chrome_edge`, `shimmer_pearl_ripple`,
    `glow_pulse` don't actually exist in PATTERN_REGISTRY.
  - **18 geo/nature/tribal family patterns**: listed in JS UI but
    never had Python render functions authored.

**NOT a HARDMODE regression.** HARDMODE tuned finishes (29
MONOLITHIC/paint functions), not patterns. The H4HR renames
landed 2026-04-19 (one day before HARDMODE); geo/nature/tribal
family gaps predate both.

Filed `spawn_task` for the fix (budget ~3-6h). Ratchet in place
to prevent the gap from growing.

**Files changed:**
- NEW `tests/test_regression_js_to_python_registry_coverage.py`
  (6 tests, ratchet form):
  - `test_pattern_registry_coverage_gap_does_not_grow` — set-
    inclusion check; any NEW id missing fires.
  - `test_spec_pattern_catalog_coverage_gap_does_not_grow` —
    same for spec patterns.
  - `test_pattern_registry_coverage_ratchet_count` — count cap;
    shrinking triggers a skip-with-note for test update.
  - `test_spec_pattern_catalog_coverage_ratchet_count` — spec
    count cap.
  - `test_js_patterns_in_groups_are_also_in_patterns_array` —
    PATTERN_GROUPS references only valid PATTERNS ids.
  - `test_finish_data_js_passes_self_validation` — the in-source
    `validateFinishData` function remains.

**Tests/gates run:**
- `pytest tests/test_regression_js_to_python_registry_coverage.py -v`
  → 6 pass
- `pytest tests/test_catalog_* tests/test_runtime_registry_* tests/test_runtime_finish_registry.py tests/test_zones.py tests/test_finish_data.py -q`
  → 45 pass (existing coverage confirmed clean)
- `pytest tests/ -q` → 1230 passed (was 1224; +6)
- `sync-runtime-copies.js --write` → no drift

**Result:** Checklist #10 AUDITED. Existing collision coverage
confirmed clean. One new pre-existing gap documented + ratcheted
+ spawn_task filed. No HARDMODE regression.

**Final summary** is next: `docs/REGRESSION_2H_FINAL_SUMMARY.md`.
