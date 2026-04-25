# SPB 2-Hour Regression Sweep — Final Summary

> ## 🛈 UPDATE (2026-04-21) — this document is now HISTORICAL
>
> The 2h audit on 2026-04-20 surfaced 6 pre-existing bugs and documented
> them as "not HARDMODE regressions" + filed 2 `spawn_task` chips. On
> 2026-04-21 01:07 a HEENAN FAMILY overnight repair loop ran (see
> `HEENAN_FAMILY_5H_OVERNIGHT_WORKLOG.md` / `..._FINAL_SUMMARY.md`) and
> **fixed several of the items this document describes as unresolved**.
>
> Current state (post-overnight):
> - **Issue #3 (spec-pattern channel default `channels="MR"`)**: FIXED
>   in iter 2 of the overnight loop. `engine/compose.py` now resolves
>   defaults from the pattern's docstring (`Targets R=Metallic → M`,
>   `G=Roughness → R`, `B=Clearcoat → C`). `abstract_rothko_field` now
>   applies its clearcoat-depth effect. 14 behavioral tests verify.
> - **Issue #4 (duplicate `applyPreset` + preset-path `||` vs `??`)**:
>   FIXED in iter 1 of the overnight loop. Polymorphic dispatcher
>   replaces the two silently-dueling definitions. Gallery clicks work
>   again. Falsy values (tolerance=0, wear=0, muted=false) round-trip.
>   11 behavioral V8-harness tests verify.
> - **Issue #6 (31 unrenderable JS pattern IDs)**: FIXED in iter 3.
>   19 aliased (10 cross-registry renames + 6 family-semantic + 3
>   broken-fallback repairs). 12 de-exposed from PATTERN_GROUPS so
>   the picker no longer shows dead entries. Net: 0 picker-visible
>   silent-no-render paths.
> - **Issue #2 (GPU/CPU color-pick metric divergence)**: FIXED in
>   iter 5. GPU branch now applies BT.601 perceptual weights matching
>   the CPU branch's documented intent. `max(|mask_cpu - mask_gpu|) = 0.0`
>   on identical input. Cross-platform preset sharing now consistent.
> - **Issue #5 (Soft-falloff by design)**: unchanged; still documented
>   as intentional, not a bug.
>
> The two `spawn_task` chips filed by this audit are now OBSOLETE —
> both underlying bugs were fixed by the overnight loop. Don't
> dispatch them.
>
> Refer to the overnight worklog for the behavioral-test coverage
> evidence and the exact code changes landed. This document remains
> accurate AS OF 2026-04-20 17:52.

---

**Audit window:** 2026-04-20 16:29:08 → 17:52 local (completed ~37 min early of the 18:29 ceiling)
**Scope:** Prove the HARDMODE autonomous loop (29 shipped finish tunings, 276+ parameterised assertions added) did not cause collateral damage elsewhere in the engine, persistence, UI, or registry paths.
**Mode:** Audit-first. No feature work, no speculative refactor, no ID renames. Measured evidence before claim.

---

## Headline

**Scoped to the 10-item HARDMODE-adjacent checklist: no new regressions from the HARDMODE loop were detected.** Every HARDMODE-touched surface (foundation neutrality, spec purity, layer mask apply, base-write gating, FINISH_REGISTRY) was probed with code-level evidence and is now pinned by a regression test.

**Caveats on this claim:**
- This audit is narrow. It did not re-render every painter scenario; it probed the specific invariants that the HARDMODE tuning pass could plausibly have touched.
- Six pre-existing issues surfaced during the sweep. They are all confirmed older than HARDMODE by timeline or structural independence. They are documented and some have follow-up `spawn_task` chips, but **several are painter-facing defects** (see "Pre-existing issues" below) — "no HARDMODE regression" does not mean "no painter-facing bugs in shipped build."
- Three of the new regression tests are **ratchets on broken behavior**, not proofs of correctness. They prevent the known bugs from worsening; they do not prove the bugs are absent. Each ratchet has an `xfail`-on-fix companion that silently greens when the fix lands, signaling the test can be deleted.

## Post-audit review by Codex

A Codex review of the loop-added test files flagged that the first versions of three regression tests pinned buggy state as required (turning correct fixes into false-positive regressions). Those tests were rewritten post-audit to use `pytest.xfail` on the fix-detected state — they now accept either the known-bug state or the fixed state, failing only on DIFFERENT regression directions. The rewritten forms are:
- `test_spec_pattern_channel_default_state_is_documented` + `test_spec_pattern_default_is_still_the_bug`
- `test_preset_path_must_not_regress_main_path` + `test_preset_path_divergence_still_exists_documented` + `test_duplicate_applypreset_still_exists_documented`
- `test_pattern_registry_coverage_ratchet_count` (xfail on shrink) + `test_spec_pattern_catalog_coverage_ratchet_count` (xfail on shrink)

---

## Checklist results

| # | Item | Result | Evidence type | Guardrails added |
|---|------|--------|---------------|------------------|
| 1 | Foundation bases stay neutral (no paint tint) | **CLEARED** | Behavioural: per-channel hue drift on neutral gray, max 0.014 (threshold 0.05) across 11 tuned enh_* finishes | 66 |
| 2 | Spec patterns remain spec-only (no paint injection) | **CLEARED** | Signature + output-type probe across 4 newer patterns | 20 |
| 3 | Spec pattern channel defaults match docstring intent | **PRE-EXISTING BUG pinned** | `engine/compose.py:1358` uses blanket `channels="MR"` default; 3 patterns author a different channel in docstring | 5 |
| 4 | Layer-restricted zones only affect their chosen layer | **CLEARED** | Source-level pin: `mask * _source_layer_mask` precedes `mask - claimed * 0.8` | 2 |
| 5 | Zone priority doesn't steal pixels across source layers | **CLEARED (gap closed)** | Behavioural: partial-overlap arbitration (missing before, existing test only covered disjoint case) | 2 |
| 6 | Color-pick zones don't get partial coverage on correct layer | **2 PRE-EXISTING issues pinned** | (a) Soft-falloff is by design (linear `1 - dist/tol`); (b) GPU unweighted Euclidean vs CPU BT.601-weighted — cross-platform metric divergence predates HARDMODE | 3 |
| 7 | Base changes on isolated layers don't spill across canvas | **CLEARED** | Source-level pin: paint writes use `paint * (1 - mask) + effect * mask`; spec writes use `np.where(mask3d > 0.01, zone, combined)` at all 10+ sampled sites | 3 |
| 8 | Save/load/repair paths don't clobber user settings | **MAIN PATH CLEARED + 2 pre-existing pins** | `loadConfigFromObj` correctly uses `??` for falsy-legitimate fields. Found: **duplicate `applyPreset` definitions** + **preset-load path uses `\|\|` where `??` is correct** — both pre-existing | 25 |
| 9 | Runtime mirrors stay synced, JS/Python parse-clean | **CLEARED** | Front-end sync: 17 files × 2 targets, no drift. Python mirrors stale between builds by design (documented separation). All 3 copies × 9 Python + 6 JS files parse-clean | 19 |
| 10 | Registries stay collision-free | **AUDITED — 1 new pre-existing gap ratcheted** | Existing coverage confirmed clean. New finding: **31 JS pattern IDs have no Python render function** (24 PATTERNS + 7 SPEC_PATTERNS) — predates HARDMODE | 6 |
| — | Full test suite | ✅ 1230 pass, 0 fail | — | — |
| — | Runtime sync gate | ✅ No drift | — | — |

---

## Pre-existing issues (NOT HARDMODE regressions — documented)

Every issue below was verified against timeline or code structure to be older than the HARDMODE loop.

1. **`engine/compose.py:1358` blanket `channels="MR"` default** — ignores per-pattern docstring intent. Affects 3 spec patterns whose authored intent is M-only, C-only, or R-only. Fixing is a saved-config back-compat decision (painter-facing render change), out of scope for an audit loop. *Pinned by `test_regression_spec_pattern_channels.py`.*

2. **GPU vs CPU color-pick metric divergence** — GPU uses unweighted Euclidean; CPU uses BT.601-weighted. Same `tolerance=T` catches more pixels on CPU than GPU. Cross-platform consistency issue. Fix is also saved-config back-compat. *Pinned by `test_regression_color_pick_coverage.py`.*

3. **Color-pick soft falloff** — `1 - dist/tolerance` is intentional (no hard seam at tolerance boundary). Not a bug; pinned so a switch to hard-edge/squared falloff is visible in test output. *Pinned by same test as #2.*

4. **Duplicate `applyPreset` function definition** in `paint-booth-2-state-zones.js` — one at line 8801, one at line 9598. The second hoists over the first, silently deadening the UI's ID-form path. *Filed as spawn_task ("Resolve duplicate applyPreset definition") with bundled fix for issue #5.*

5. **Preset-load path uses `\|\|` instead of `??`** in the active `applyPreset(preset)` — numeric/boolean persistence fields like `pickerTolerance: z.pickerTolerance \|\| 40` replace legitimate falsy user values (tolerance=0 → 40). The main `loadConfigFromObj` path correctly uses `??`. *Pinned; bundled into the same spawn_task as #4.*

6. **31 unrenderable JS pattern IDs** (24 PATTERNS + 7 SPEC_PATTERNS) — JS picker shows them but Python can't dispatch. Breakdown: 10 HP/H4HR/HB2 renames where Python still registers old IDs, 3 broken _PATTERN_FALLBACKS, 18 geo/nature/tribal family patterns that were never authored Python-side. *Filed as spawn_task ("Fix 31 unrenderable patterns").* Ratcheted so the gap cannot grow.

---

## Test count impact

| Milestone | Total tests |
|-----------|-------------|
| Before loop | 1079 |
| After iter 1 (Foundation neutrality) | 1145 (+66) |
| After iter 2 (Spec-pattern purity) | 1165 (+20) |
| After iter 3 (Channel defaults) | 1170 (+5) |
| After iter 4 (Layer-mask ordering) | 1172 (+2) |
| After iter 5 (Cross-layer overlap) | 1174 (+2) |
| After iter 6 (Color-pick coverage) | 1177 (+3) |
| After iter 7 (Base-on-layer spill) | 1180 (+3) |
| After iter 8 (Save/load/repair) | 1205 (+25) |
| After iter 9 (Runtime mirror sync) | 1224 (+19) |
| After iter 10 (Registry coverage) | 1230 (+6) |
| **Net added by this audit** | **+151 guardrails** |

Every guardrail is designed as either (a) a behavioural probe of the invariant, (b) a source-level pin of the structural form that preserves the invariant, or (c) a ratchet that rejects silent worsening of a pre-existing gap.

---

## Follow-ups filed

Two `spawn_task` chips are ready for the user to dispatch into fresh sessions:

1. **"Resolve duplicate applyPreset definition"** — Bundles the duplicate-function fix and the preset-path `\|\|`→`??` fix. ~1h budget.

2. **"Fix 31 unrenderable patterns"** — Map out the 31 JS→Python gaps, add Python-side aliases for the 10 renames, triage the 18 unregistered family patterns (register or remove from UI), fix the 3 broken fallbacks. ~3-6h budget.

Neither is a HARDMODE regression. Both are pre-existing, painter-facing, worth fixing but not under audit conditions.

---

## Confidence statement

**Narrow scope — HARDMODE-specific invariants:** the 29 finish tunings did not break the invariants probed in this 10-item checklist. Foundation neutrality, spec-pattern purity, layer isolation, mask application, base-write gating, and FINISH_REGISTRY integrity all verified safe with behavioural or source-level evidence, now pinned by regression tests.

**Wider view — painter-facing state:** the audit surfaced 6 pre-existing issues, 3 of which are painter-visible:
- Spec patterns (`gold_leaf_torn`, `stippled_dots_fine`, `abstract_rothko_field`, `abstract_futurist_motion`) render to the wrong channels because of the blanket `channels="MR"` default in `engine/compose.py:1358`. Painter-facing impact varies by pattern; `abstract_rothko_field`'s authored clearcoat-depth effect never applies at all.
- Presets authored with explicit `pickerTolerance: 0`, `scale: 0`, or other falsy values lose fidelity on import because the preset-load path uses `||` instead of `??`.
- 31 picker-visible pattern IDs (24 regular + 7 spec) have no Python render function and silently produce no output when selected.

These predate HARDMODE by timeline or structural independence (HARDMODE touched finishes, not compose.py channel dispatch, not preset loading, not pattern registration). They are **not new regressions** — but they also **aren't cleared by this audit.** The follow-up `spawn_task` chips are real bug fixes, not polish.

**Runtime gate status at audit close:**
- `pytest tests/ -q` → **1233 passed, 0 failed, 0 skipped**
- `node scripts/sync-runtime-copies.js --check` → **no drift**
- `node --check` across key JS × 3 mirror copies → **all parse-clean**
- `ast.parse` across key Python × 3 mirror copies → **all parse-clean**

**Recommendation:** HARDMODE itself is clear to ship as far as this audit can see. The two `spawn_task` chips should be treated as real painter-facing bug fixes, not nice-to-haves, and prioritized accordingly.

---

*Worklog detail:* [REGRESSION_2H_LOOP_WORKLOG.md](./REGRESSION_2H_LOOP_WORKLOG.md)
*Ran by:* regression-audit agent
*Model:* Sonnet 4.7 (1M context)
*Generated:* 2026-04-20

---

# 2026-04-21 Follow-up sweep — Appendix

A second pass of the same 10-item checklist ran on 2026-04-21 to:
- verify the HEENAN overnight fixes held and that the existing
  ratchets still matched the floor,
- add missing coverage where the original sweep had gaps,
- clear any accumulated mirror drift before final sign-off.

## Checklist delta (what this sweep added)

| # | Original sweep result | 2026-04-21 follow-up result | What today added |
|---|------------------------|-----------------------------|------------------|
| 1 | CLEARED (66 guardrails) | Re-confirmed CLEARED. Also verified Foundation Base spec-flatness work (Iter 1 of an earlier focused session) holds: `tests/test_regression_foundation_spec_flatness.py` 11/11. | — |
| 2 | CLEARED (20 guardrails) | Re-confirmed CLEARED. | — |
| 3 | Pre-existing BUG pinned | Confirmed FIXED by HEENAN overnight iter 2 (per existing Update box at top of this doc). Behavioral tests now green. | — |
| 4 | CLEARED | Re-confirmed CLEARED. | — |
| 5 | CLEARED (gap closed) | Re-confirmed CLEARED. | — |
| 6 | 2 pre-existing pins | Confirmed Issue #2 FIXED by HEENAN overnight iter 5; Issue #1 (soft-falloff) remains by-design. | — |
| 7 | CLEARED (source-level + synthetic) | CLEARED with **new end-to-end supplement** — real-base e2e coverage through `compose_paint_mod` and the spec combiner gate. | `tests/test_regression_base_zone_containment_e2e.py` (3 tests): proves `f_metallic` (and the v6 base-overlay branches at compose.py:3100-3400) do not spill outside the zone mask at either the paint or spec layer. |
| 8 | AUDITED + 2 pre-existing pins (both FIXED overnight) | **New clobber found & ratcheted** — structural key-parity audit revealed `rotation` is exported by `exportPreset` but NOT read by `_applyPresetFromObject`. Painter sharing a .shokker preset with rotated patterns loses the rotation silently on recipient import. | `tests/test_regression_preset_roundtrip_key_parity.py` (4 tests): ratchets the current 1-key drop; any NEW export-only key (another silent preset-loss bug) fires. `spawn_task` filed for the 1-line fix. |
| 9 | CLEARED (19 guardrails) | CLEARED + **script audit** + **orphan-count ratchet**. `sync-runtime-copies.js:379-380` subdir-preservation Codex fix confirmed in place. 12/12 JS + 12/12 Python × 3 mirror copies parse clean. Found 2 orphan mirrors (stale legacy `paint-booth-app.js` copies; low-signal). | `test_orphan_mirror_count_does_not_grow_beyond_known_baseline` in `test_regression_runtime_mirror_coverage.py`: baseline 2, fires on growth, auto-skips on shrink. Mirror drift from earlier work cleared via `--write`. |
| 10 | AUDITED + 31-id gap ratcheted (10 renames + 3 broken fallbacks + 18 unregistered) | VERIFIED — HEENAN overnight iter 3 closed 19 of 31 (10 aliases + 3 repaired fallbacks + 6 family-semantic aliases); 12 remaining de-exposed from PATTERN_GROUPS. Existing ratchet already correctly tightened to 12. Registry-collision tests 45/45 green. | — (existing test file already reflects the correct post-HEENAN floor). |

## New tests added by this follow-up

| File | Tests | Purpose |
|---|---:|---|
| `tests/test_regression_base_zone_containment_e2e.py` | 3 | Iter 7 real-base end-to-end containment pin. |
| `tests/test_regression_preset_roundtrip_key_parity.py` | 4 | Iter 8 structural key-parity ratchet for `.shokker` preset round-trip. |
| `tests/test_regression_runtime_mirror_coverage.py` *(extended)* | +1 | Iter 9 orphan-mirror count ratchet. |

**Net guardrails added by this follow-up sweep: +8**
(cumulative +159 across both sweeps: +151 original + +8 follow-up).

## Housekeeping performed during the follow-up

- **Mirror sync:** 4 Python files (`shokker_engine_v2.py` ×2 mirror dirs, `engine/paint_v2/foundation_enhanced.py` ×2) had drifted due to Foundation Base spec-flatness fixes from a prior focused session. Synced via `node scripts/sync-runtime-copies.js --write` during iter 8. Post-sync `--check` exits 0.

## New painter-facing issue found today (1 clobber)

**`rotation` is dropped on `.shokker` preset import.**
- *Location:* `paint-booth-2-state-zones.js` — `exportPreset` (line ~9553) writes `rotation: z.rotation ?? 0`; `_applyPresetFromObject` (lines 9645-9674) omits it.
- *Symptom:* Painter rotates a pattern to 45°, exports preset, teammate imports — pattern renders at 0°.
- *Status:* NOT HARDMODE. Predates the overnight repair loop as well. `spawn_task` filed with a 1-line fix plan.
- *Guardrail:* `test_known_clobber_rotation_still_present_until_fix_lands` ratchet auto-signals when the fix lands.

## Follow-up `spawn_task` chips filed by this sweep

1. **"Fix preset rotation drop in _applyPresetFromObject"** — 1-line fix on the import side, remove `"rotation"` from whitelist, delete the companion xfail-on-fix test. ~15 min budget.

(The two chips filed by the original 2026-04-20 sweep were OBSOLETED by the HEENAN overnight loop per the Update box at the top — do not dispatch them.)

## Runtime gate status at follow-up close

- `pytest tests/test_regression_*.py` → regression layer all green.
- Registry collisions: 45/45 existing tests pass; no new cross-registry collisions from HARDMODE's 29 tuned finishes.
- `node scripts/sync-runtime-copies.js --check` → no drift.
- `node scripts/sync-runtime-copies.js --check --check-orphans` → 2 orphans (baseline — ratcheted).
- All 3 mirror copies of hot Python files compile; all 3 mirror copies of key JS files parse.

## Confidence statement (follow-up)

**The 10-item checklist's HARDMODE-safety conclusion from 2026-04-20 still holds.** HARDMODE has not introduced regressions. The HEENAN overnight loop genuinely resolved 4 of the 6 pre-existing issues surfaced by the original sweep. The 2026-04-21 follow-up sweep added 3 new ratchet layers — end-to-end base containment, preset structural key-parity, and mirror orphan count — each catching a distinct bug class that the original sweep did not cover.

**One additional painter-facing clobber was found** (preset `rotation` drop). It is pre-existing, it is pinned, and it has a focused one-line fix queued behind a `spawn_task` chip.

*Follow-up generated:* 2026-04-21
*Ran by:* regression-audit agent (continuation)
*Model:* Sonnet 4.7 (1M context)
