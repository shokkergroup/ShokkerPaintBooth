# GOLDEN_NET_TRIAGE — the 42 changed + 1 removed from ENGINE_ZONE_COST (2026-10-06)

Trigger: `docs/handoff_reports/ENGINE_ZONE_COST.md:82`. The zone-cost lane's golden check showed 388 same, 42 changed and 1 removed. The same set appeared with `SPB_ZONE_BBOX=0` and with HEAD's `compose.py` + `shokker_engine_v2.py` loaded, so the deltas were already in committed code.

**Verdict: 0 look regressions in the golden set.** All 42 changes are declared owner changes. The 1 removal is an owner retirement. I looked at all 43 at 1:1 (sheets in `golden_net_triage/`), then re-baked them.
**The net is green again on the working tree:** `GOLDEN NET: 430 same, 0 changed, 0 removed, 0 added, 0 error (2 absent)`.

The triage did surface 4 other problems (§5 R1–R4). The two big ones:
- **R4 is a real production bug.** `engine/paint_v2/cultural_viva_mexico.py:162` keys a memo cache on `id(array)`. Freed ids get reused, so finishes in the Viva / Union Jacked / Rising Sun / Mortal Shokk / guest-designer / SHOKK DROP / Spec Sculpt paths can silently receive another texture's edge map. Repro 50/50; a fix is validated in scratch.
- **R1:** the committed snapshot cannot boot from a clean checkout.

Nothing was committed, no engine code was edited, and no server was touched.

---

## 1. How the check was rerun

- **Script:** `python scripts/spb_golden_net.py` (`--check` by default). Manifest: `scripts/golden_manifest.json` (432 ids, 512², seed 51). Refs: `_golden/refs/` (gitignored).
- **HEAD (aa73b9f8e) vs the working tree.**
  - The main tree has other lanes' uncommitted engine edits: `engine/compose.py` (zone-cost), `shokker_engine_v2.py` (zone-cost + texture-anchor) and `engine/paint_v2/flames_2026.py` (flames).
  - To isolate committed code, `golden_net_triage/gn_wrap_head.py` loads the **HEAD source of those 3 files under their real paths** through an import hook. A marker check confirms the HEAD code ran. The run writes `last_check.json` and the diffs to scratch, and a guard refuses any repo write.
- **HEAD result:** the same 42 changed + `hou_veiled_skull` removed as the lane. The one extra is `flame_hotrod`, which is expected: the flames lane already accepted its uncommitted rebuild into the dirty manifest on 10-06 09:26.
- **Working-tree result:** the identical 42 + 1. All **103/103 diff PNGs are byte-identical** between HEAD and the working tree, so a re-bake from the working tree records exactly the committed look.
- **Trap to remember.** `importlib.util.spec_from_file_location()` on a *copied* HEAD file changes `__file__`. `shokker_engine_v2` then loses its `__file__`-relative loads: 30 monolithics vanish, and `aurora_borealis` falsely shows as REMOVED. The wrapper loads HEAD bytes under the real path instead. The lane's 43-id result was unaffected.
- **A clean `git archive HEAD` checkout does not boot at all** (see §5 R1).

## 2. Attribution: why `git bisect` can't split these

`git log -- engine shokker_engine_v2.py` goes straight from `4617dc28a` (2026-04-26) to `638f65103` ("Beta build-out snapshot 2026-10-05 (1/6)"). Every committed delta below therefore lands in **one snapshot commit**, and bisect has nothing to split.

Attribution instead comes from:
- the dated owner headers inside each changed module;
- the family files' mtimes, checked so that nothing changed after the declared rebuild except where documented;
- the lane reports in `docs/finish_audits/`;
- the 09-05 golden logs (`_golden/check_after_staging.log`).

## 3. Per-finish classification (all LOOKED at 1:1: old | new)

| # | ids | channels | cause (file:line) | when | class | action |
|---|---|---|---|---|---|---|
| 7 | `eggshell flat_black gloss matte primer satin wet_look` | spec R + CC only | `engine/base_registry_data.py:1559` `_spec_foundation_pure_bound` via `_upgrade_foundation_material_spec` (:1563) | 09-30 | **INTENDED**: owner mandate 2026-09-30, "REGULAR foundations SHOULD BE PURE" (memory `feedback_foundation_bases_pure`) | re-baked |
| 1 | `at_beige_box` | all | `engine/paint_v2/all_that_image_2026/at_beige_box.py:1` (AT-R2) | 09-16 | **INTENDED** rebuild, `docs/finish_audits/all_that_2026-09-16/` | re-baked |
| 2 | `cbp_acid_rain rad_amber_terminal` | all | `engine/paint_v2/era_image_2026/<id>.py:1` (ERA120 tick2, owner "DO what they say") | 09-17 | **INTENDED** rebuild, `docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md` | re-baked |
| 1 | `fl_penetrant_bleed` | all | `engine/paint_v2/flaw_lab_rebuild_2026/__init__.py:1` (FLAW LAB21; fn moved from `flaw_lab_2026`) | 09-18 | **INTENDED** rebuild, `docs/finish_audits/FLAW_LAB_REBUILD_2026-09-18.md` | re-baked |
| 5 | `bth_fisheye lsk_return_stroke mul_erlkonig_swirl slt_reticulated wrap_panel_seam` | all | `engine/paint_v2/core_works_2026/finishes/<id>.py:1` (SHOKK WORKS, owner "rebuild with jaw-dropping fine detail"); fn moved from the old `*_2026.py` | 09-30 | **INTENDED** rebuild, `docs/finish_audits/CORE_WORKS_REBUILD_2026-09-30.md` (`wrap_panel_seam` renamed "Panel Step Inlay") | re-baked |
| 1 | `astra_event_horizon` | all | `engine/expansions/astra/event_horizon.py:1` → `originals.py::event_horizon` (ASTRA R2); 09-29 `kit.py` owner-feedback pass | 09-27/29 | **INTENDED** R1→R2 rebuild, `docs/finish_audits/ASTRA_R2_2026-09-27.md`. The owner's overall R2 verdict is still open (memory `project_astra_r2_rebuild`); if R2 is rejected, re-accept again. | re-baked |
| 25 | `mc_*` (retired, hidden since 06-03) | paint+spec (`mc_neon_camo` paint only) | `_staging/monolithic_upgrades/color_mono_factories_v2.py` (**gitignored**, not in any commit) | **pre-dates the snapshot.** Already in `_golden/check_after_staging.log` (09-05, 25 changed) | **INTENDED / restoration.** The 09-05 bake ran while `_staging/` was archived (v1 fallback); the restore brought back the live v2 factories (memory `project_codebase_health_overnight`: "awaiting --accept") | re-baked |
| 1 | `hou_veiled_skull` | REMOVED | `engine/registry.py:678-682`: "owner09-18 replaces HOUDINI with twenty original spectral materials". The install now imports `fractured_shokk_2026` (aliased `_install_houdini`), so all 30 `hou_*` ids are unregistered | 09-18 | **INTENTIONAL RETIREMENT** (see §4) | `--accept` → recorded **ABSENT** (a resurrection now reports ADDED) |

What I saw at 1:1 (all of these are in `golden_net_triage/`, one PNG per id; `mc_0..6.png` are 256-px 1:1 crops):

- **Foundations** (`_foundations.png`, 8× contrast stretch): the old references carry ±5-level roughness grain and clearcoat clouds. The new ones are perfectly flat at the same means: gloss R30/CC16, matte 200/160, satin 95/70, primer 215/200, flat_black 250/255, eggshell 140/95, wet_look 15/16. This is exactly the grit the owner rejected.
- **Rebuilds**: every one is a wholesale redesign, not a drift-sized change, and most old references were visibly weak.
  - The old `bth_fisheye` had cell-clipped circles (seams at cell borders).
  - The old `astra_event_horizon` was a uniform 8 px dot lattice (R1).
  - The old `cbp_acid_rain` and `rad_amber_terminal` specs were noise.
- **mc_\***: the same v1→v2 change across the family. Hard-edged 3–4-colour blobs on a flat spec became soft blended fields on a lightly textured spec.

## 4. The 1 removed finish: `hou_veiled_skull`

- **Retired on purpose.** The owner replaced FRACTURED HOUDINI (30 `hou_*`) with FRACTURED SHOKK on 2026-09-18 (`engine/registry.py:678`). The old module `engine/expansions/fractured_houdini_reveal_2026.py` is still in the tree but nothing imports it.
- **No picker/data leak.**
  - No JS, data or server file references any `hou_*` id.
  - `paint-booth-0-finish-data.js` has 0.
  - `python scripts/spb_retired_gate.py` gives `RETIRED GATE: 0 hit(s) -> PASS`.
- **But the retired gate does not know about it.** None of the 30 `hou_*` ids are in `scripts/retired_catalog.json`. The gate only protects what the ledger lists, so re-adding the old install line would pass the gate silently. The golden net now records the id ABSENT, which catches only this one id. See R2.

## 5. Regressions / defects found (none are golden-look regressions)

**R1. The committed snapshot cannot boot from a clean checkout. HIGH (repo integrity; the installer is not affected because it builds from the working tree).**
- `.gitignore:182` `_*.py` (the "temp/debug scripts" rule) also matches every `__init__.py` and real runtime modules.
- Untracked as a result:
  - 21 `__init__.py` under `engine/` (e.g. `engine/paint_v2/__init__.py`, `engine/expansions/__init__.py`);
  - `engine/paint_v2/_finish_kit_2026.py`;
  - `engine/paint_v2/_variant_params.py`;
  - `engine/spec_pattern_families/_v2_palette_fix.py`.
- `git archive HEAD` then fails at import: `engine/paint_v2/military_tactical.py:7` raises `ImportError: cannot import name 'ensure_bb_2d' from 'engine.paint_v2'`.
- `.gitignore:130` `*.png` also hides **~430 MB of runtime baked maps (414 PNGs)** in:
  - `engine/paint_v2/era_image_2026/assets` (240)
  - `all_that_image_2026/assets` (118)
  - `flaw_lab_rebuild_2026/assets` (42)
  - `engine/expansions/fractured_shokk_assets` (40)
  - `all_that_pilot/assets` (14)
- So `at_*`, `cbp_*`/`rad_*`, `fl_*` and `fsh_*` cannot render from git.
- `_staging/` (`.gitignore:177`) is runtime-loaded too; that's the known open owner decision.
- **Proposed fix:** add after line 185:
  ```
  !**/__init__.py
  !engine/**/_*.py
  ```
  Then `git add` those 24 files. For the PNGs, the owner picks: commit `!engine/**/assets/*.png` (+430 MB to the repo), or Git LFS, or leave them out and document that git is not a restorable snapshot. This is the open "git snapshot" decision from 09-05.

**R2. Retired-ledger gap for FRACTURED HOUDINI. MEDIUM.**
- `scripts/retired_catalog.json` has 0 of the 30 `hou_*` ids.
- **Fix:** add a SOURCES row in `scripts/build_retired_catalog.py`. Ids come from the `HOUDINI` keys in `engine/expansions/fractured_houdini_reveal_2026.py:186`; since 2026-09-18; basis `engine/registry.py:678`. Then regenerate (the script also writes `js/spb-retired-catalog.js`) and run `python scripts/spb_retired_gate.py`.
- I didn't do this: it changes the shipped JS ledger, so it's the owner's call.

**R3. Stale identity-contract reference. LOW.**
- `engine/expansions/fractured_shokk_2026.py:267` lists `hou_veiled_skull` as a `nearest_neighbors` entry, but that finish is no longer registered.
- **Fix:** point it at a live `fsh_*` sibling or drop the entry.

**R4. REAL BUG: `id()`-keyed memo cache returns another texture's luma/edge map. HIGH (silent wrong renders in production). Found through a golden flake on `gd_lyons_black_rainbow_holo_x`.**
- **Symptom.** In full golden runs on HEAD code (2 of the 2 post-rebake HEAD runs), the spec came back CHANGED: mad 16, 93% of pixels moved, mean 142→133.
  - The output was the correct Lyons holo spec **plus a Truchet quarter-circle line grid**: another finish's edges (`golden_net_triage/gd_lyons_black_rainbow_holo_x__flake_spec.png`: baseline | bad | diff).
  - The bad output was byte-identical across both runs.
  - It never shows when the id renders alone (6/6), with only its sorted prefix (2/2), or after a 180 s idle (1/1). It depends on memory layout, not on code changes.
- **Root cause: `engine/paint_v2/cultural_viva_mexico.py:162`.**
  ```
  _viva_cache_key = (id(tex), h, w, id(mask), h)
  ```
  This keys the 4-entry `_VIVA_LUMA_CACHE` / `_VIVA_CREST_CACHE` (lines 157–159; "SPB-92 tick 61" per-render memo). CPython reuses an `id()` as soon as the array is freed. So a *new* texture of the same shape at the same address gets the *previous* texture's `(gray, edge_n)`.
  - In `guest_designers.py:174-181` that feeds `Cc = ... + edge_n*42` and the dark-mask, which is exactly the overlaid line grid.
  - **Repro:** a random texture, then `del`, then a flat-black texture of the same shape → the flat-black call returns the random texture's luma map **50/50 times**.
- **Blast radius.** Every caller of `_viva_mexico_paint_luma_edge` / `_viva_mexico_highlight_crest` / `_post_adjust_viva_mexico_spec`:
  - `cultural_viva_mexico`, `cultural_union_jacked`, `cultural_rising_sun`, `cultural_mortal_shokk`, `cultural_colorshoxx_ai`, `cultural_grunge_fun`;
  - `guest_designers`;
  - `user_imports` + `user_imports_spec_dna` (SHOKK DROP);
  - `engine/spec_sculpt/generate.py` + `paint_trace.py` (Spec Sculpt).
  On the live server nearly every render is 2048², so same-shape id reuse across zones and jobs is likely. A car can silently get a *different* finish's (or a different car's) edge-driven clearcoat/roughness.
- **Proposed fix (validated in scratch, engine untouched):**
  - Store weak references alongside the cached value and verify identity on a hit:
    - `_viva_lru_put` stores `(weakref.ref(tex), weakref.ref(mask), value)`.
    - `_viva_lru_get(cache, key, tex, mask)` returns the value only if `tref() is tex and mref() is mask`; otherwise it pops the entry and misses.
  - Pass `tex_rgb_hwc, mask_hw` through at the 2 get sites (`_viva_mexico_paint_luma_edge`, `_viva_mexico_highlight_crest`). ndarray views support weakrefs.
  - Scratch result: **0/50 stale hits**, and the same-object dedup still computes once per 3 calls, so the tick-61 speed win stays.
  - Rejected alternative: holding strong refs would also stop the id reuse, but pins up to 4 × 48 MB at 2048.
  - Gates after the fix: golden net full check (HEAD and working tree), `spb-spec-sculpt-qa`, and a server restart (engine change).
- **End-to-end confirmation:** the bug itself is proven: 50/50 unit repro, and the code path matches the symptom (`guest_designers.py:174` feeds `edge_n` straight into Cc). Attribution of the *golden flake* to it is **strongly indicated but not proven end-to-end**. The flake hit 2 of 4 post-rebake HEAD full runs. The 2 follow-up runs were both clean: cache disabled (expected) and also the cache-enabled control, because whether a freed id is reused depends on allocation timing. To close it: apply the fix, then do repeated full runs with 0 flakes.
- The golden reference for `gd_lyons_black_rainbow_holo_x` was **not** touched; the 09-05 bake is the correct look.
- **Golden-net hardening (separate, small):** make `--check` re-render a CHANGED id once in a fresh call and flag `UNSTABLE` when the two renders differ. Then this class of bug shows up as a named defect instead of a lane-blocking "change".

**Quality notes on the accepted rebuilds (not drift; for the owner's audit):**
- `mul_erlkonig_swirl` and `slt_reticulated` are already flagged for seams in `docs/CATALOGUE_QA_2026-10-03.md:1006/1018`. At 1:1 the new erlkonig spec shows square-block discontinuities.
- `cbp_acid_rain`'s new spec has a frame on all four edges: R about 35 lower and CC 45–64 higher in the outer 16/512 px (`era_image_2026/__init__.py:34` stretches the map to the canvas, so that's a ~64 px border on the 2048 sheet, not a tile grid).
- v2 `mc_woodland_camo` has lost almost all of its green (retired, hidden).

## 6. Re-bake performed (main tree, no commit)

```
python scripts/spb_golden_net.py --accept eggshell,flat_black,gloss,matte,primer,satin,wet_look --reason "GOLDEN_NET_TRIAGE 2026-10-06: ... PURE foundations ..."
python scripts/spb_golden_net.py --accept astra_event_horizon,at_beige_box,bth_fisheye,cbp_acid_rain,fl_penetrant_bleed,lsk_return_stroke,mul_erlkonig_swirl,rad_amber_terminal,slt_reticulated,wrap_panel_seam --reason "GOLDEN_NET_TRIAGE 2026-10-06: declared owner rebuilds ..."
python scripts/spb_golden_net.py --accept <25 mc_* ids> --reason "GOLDEN_NET_TRIAGE 2026-10-06: RETIRED mc_* ... v2 factories ..."
python scripts/spb_golden_net.py --accept hou_veiled_skull --reason "GOLDEN_NET_TRIAGE 2026-10-06: owner 09-18 replaced FRACTURED HOUDINI ..."
```

- No protected ids were involved (none of the 43 are in `scripts/protected_finishes.json`).
- The manifest diff vs the pre-triage copy is exactly the **43** entries, each carrying a `GOLDEN_NET_TRIAGE` `accept_reason`. The flames lane's `flame_hotrod` entry is untouched.
- `meta.registry` now records the working-tree counts (monolithics 3035).
- `scripts/golden_manifest.json` was already dirty from the flames lane, so commit both together, or after the flames lane lands.

**After the re-bake:**
- Working tree: `GOLDEN NET: 430 same, 0 changed, 0 removed, 0 added, 0 error (2 absent)` → **PASS** (`golden_net_triage/check_after_rebake_2026-10-06.log`).
- HEAD hook: `flame_hotrod`, which is expected until the flames lane commits, plus `gd_lyons_black_rainbow_holo_x` in 2/2 post-rebake runs. That one is the R4 bug, not a look change.

## 7. Files

- New: `docs/handoff_reports/GOLDEN_NET_TRIAGE.md`.
- Local evidence in `docs/handoff_reports/golden_net_triage/`. The PNGs are gitignored by `*.png`.
  - Per-id 1:1 sheets
  - `_foundations.png`
  - `mc_0..6.png`
  - the flake image
  - both check logs
  - `gn_wrap_head.py`: the HEAD-overlay check wrapper. It expects `overlay/{compose,shokker_engine_v2,flames_2026}.py` from `git show HEAD:<path>` next to it.
- Changed: `scripts/golden_manifest.json` (43 entries); `_golden/refs/` (re-baked refs, gitignored).
- Untouched: all engine code, the protected finishes, servers 59876/59879, git history.
