# SNAKESKIN CANDIDATES (2026-10-04) - real snakeskin spec textures for the copilot (OWNER LOOK REQUIRED - candidates only, nothing wired)

Lane: Claude (Opus), no sub-agents. Work dir `_snakeskin_work/`. Status: DONE - candidates built, gated, sheets looked at; awaiting the owner's pick. Nothing wired into the catalogue or the copilot.

## 1. Why the current one reads as a grid

- Copilot map: `js/spb-pro-edit.js` `TEXTURES[0]` (id `snake`) -> spec `snake_scale_diamond` ("Snake Scale Diamond", opacity 85, scale 1), alt `spec_snake_scales`, paint pattern `snake_skin`. Applied as `zone.spec_patterns = [{id, opacity:85, scale:1}]` (offline compile L1085, online refinish L926).
- The id is bound many times; the binding that is LIVE in the booted engine (verified: `PATTERN_CATALOG["snake_scale_diamond"].__module__` = `engine.spec_pattern_families.overhaul_2026`, `overhaul_snake_scale_diamond`, legacy v1 overlay) comes from the 2026-07-13 spec-overlay overhaul, whose semantic field is `engine/spec_pattern_families/semantic_overlays_2026.py:565`:
  `a = max(_line(u+v, s*1.55), _line(u-v, s*1.55)); keel = _line(u, s*.78)` -> two families of straight parallel lines crossed at 90 deg plus a straight keel line. That is literally a lattice: one period, no jitter, no size change, no row curvature, no overlap, no per-scale material. (The older `rescue_snake_scale_diamond` rotated-square tessellation is shadowed and never runs.)
- At 1:1 it is a perfectly regular square/diamond grid (`_snakeskin_work/sheets/compare_1to1.png`, left column; `OLD_snake_scale_diamond_1to1.png`). Its G (roughness) channel is nearly flat, so the whole look lives in B.

## 2. The three candidates (new math) - `engine/spec_pattern_families/snakeskin_candidates_2026_10_04.py`

Shared NEW primitive `_Lattice` (imbricate scale lattice): seeds on a half-offset, per-row-jittered lattice in a smoothly WARPED + rotated frame (two warp octaves -> curved rows, no period anywhere); each seed = rounded lozenge (L2->L1 blend) with its own size (+-12-15%) and a pointed free tip. Pixels resolve by ROOF-TILE PRIORITY (front row covers the base of the row behind -> real overlap, a cast shadow under every free edge, skin showing in gaps). Macro markings are sampled at each scale's SEED, so pigment snaps to scale boundaries like a real snake. Spec only: paint untouched (colour-preserving SHINE texture), same contract as every legacy spec overlay (`fn(shape, seed, sm) -> HxWx3 [0,1]`). Every scale: glossy crown, rough dull rim.

| id | look | math |
|---|---|---|
| `snakeskin_cand_python` | ball python / boa | 17x~24 px rounded lozenges, rot 0.38, warp 30 px @420 px; macro saddles = smooth field (170+70 px) thresholded per scale into 3 tiers: saddle = dark metal mirror (M .92 R .24), one-scale halo = bare colour under clear (M .04), ground = satin metal; light flecks inside saddles; crest highlight on the free half; growth lines `cos(9 dv)` |
| `snakeskin_cand_viper` | diamondback / rattlesnake | narrow lanceolate 15x~29 px scales, pointed tips (tip .38), KEEL ridge `exp(-(du/.17)^2)` (gloss+metal up, roughness down) with one lit flank; macro jittered diamond chain (150x190 px, per-diamond centre/size/aspect jitter, 15% missing, noise-broken edges) quantised per scale: dark metal body, one-scale bright clear border, lighter core, satin ground with darker speckle scales |
| `snakeskin_cand_sunbeam` | sunbeam snake (iridescent) | tiny 13x~15 px smooth imbricate scales, rot 0.95; each scale ONE phase `phi` of a cycling (M, R, Cc) triple at 0/120/240 deg; phi = sweeping sheen waves (300+110 px field + diagonal band) + per-scale jitter + slide across the scale -> neighbouring scales are different materials, sheen rolls as the car turns |

Perf: canvas resolved in 64-row strips on a thread pool, only the 6 lattice cells that can own a pixel are tested.

## 3. Gate results (one engine boot; `python _snakeskin_work/snake_harness.py --gates`; raw numbers `_snakeskin_work/results.json`)

How gated: spec overlays are not picker finishes, so `spb_finish_law.py --group` cannot enumerate them. The harness imports the law's OWN axis functions (`scale_axis`, `coverage_axis`, `richness_*`, `story_signature`, `texture_signature`, `audit_group`, `verdict`) and feeds them paint = the customer's flat colour + spec = Foundation base composed with the overlay exactly as the zone does it (same SPEC-DRIVEN FOLLOW exemption the law already grants Foundation). Group = 3 candidates + OLD + the 4 other reptile overlays the copilot uses (spec_snake_scales, croc_delta_armor, dragon_scale_macro, spec_fish_scales). Uniqueness = `spb_catalog_fingerprint.fingerprint` + `spb_uniqueness_gate._cand_sim` against the whole finish index AND all 330 fingerprintable spec overlays (cache `_snakeskin_work/spec_fp_cache.npz`).

| id | LAW f_metallic | LAW f_soft_gloss | fine (>=0.20) | eff materials (adv.) | twin (ADVISORY) | uniqueness nearest (fail >=80%) | pattern / +compose @2048 |
|---|---|---|---|---|---|---|---|
| OLD snake_scale_diamond | PASS | PASS | 0.41 / 0.51 | 5.3 / 2.7 | 0.95-0.98 | 36% spec_sharkskin_riblet | 0.17 / 0.36 s |
| snakeskin_cand_python | PASS | PASS | 0.48 / 0.53 | 12.6 / 8.1 | 0.99 -> viper | 35% spov2_trabecular_pores; finish 33%; sibling 29% | 0.74 / 1.04 s |
| snakeskin_cand_viper | PASS | PASS | 0.46 / 0.48 | 12.1 / 5.6 | 0.99 -> python | 35% carbon_weave; finish 31%; sibling 30% | 0.99 / 1.15 s |
| snakeskin_cand_sunbeam | PASS | PASS | 0.23 / 0.23 | 12.6 / 4.6 | 0.96-0.97 | 38% astra_chronograph_gold; spec 35%; sibling 29% | 0.77 / 1.17 s |

- STORY: f_metallic 8/8 distinct (1.00); f_soft_gloss 7/8 (0.88) - the shared pair is two EXISTING overlays (spec_snake_scales = croc_delta_armor), not a candidate. Every candidate owns its material story on both bases.
- COVERAGE dead 0.00 (paint untouched); FOLLOW N/A (spec-driven, the customer's paint is the artwork).
- TWIN is advisory by the law's own calibration (the owner's gold standards sit 0.82-0.92). python<->viper 0.99 is the shared scale-lattice spectrum; the existing reptile overlays sit 0.96-0.98 with each other. The structural uniqueness metric separates the siblings cleanly (29-30%).
- Render budget: all well inside 3 s (pattern alone 0.74-0.99 s; with the spec compose 1.04-1.17 s). Strip-threaded, numpy + cv2 only.
- Protected finishes: untouched (no renderer, recipe, palette or deck edited; the only engine change is the NEW untracked module above, not registered anywhere).
- Visual (looked at every sheet at 1:1 and whole-car): OLD = square grid. python = unmistakable overlapping python scales + saddles on pink/purple/yellow; viper = keeled lanceolate scales + diamondback chain (diamonds are subtler at whole-car scale than python saddles); sunbeam = fine imbricate scales with rolling iridescent bands (reads as sheen/leather at whole-car, snake scales at 1:1). On BLACK soft-gloss all three are visible only inside highlights (black paint has no diffuse to modulate; physics, not a bug) - still clearly more than OLD.

## 4. Contact sheets (`_snakeskin_work/sheets/`)

- `compare_1to1.png` - OLD vs 3 candidates, 1:1 lit on purple + spec G + spec B.
- `<id>_car.png` - whole car (Next Gen City livery, body = its green/yellow, other parts untouched) on pink + purple (f_metallic) and black + yellow (f_soft_gloss), studio-lit approximation.
- `<id>_1to1.png` - 1:1 lit crops on the four paints + spec G/B for f_metallic and f_soft_gloss.
- Harness: `python _snakeskin_work/snake_harness.py --sheets --gates` (one engine boot). The lit view is an approximate studio shader, not the iRacing sim.

## 5. Catalogue "Snakeskin" swatch renders nearly black - cause (NOT fixed: not a bake problem)

- The builder tile is `fc_snakeskin` (FRACTURED WILDS / cryptid). `js/spb-offline-builder.js thumbFor()` asks for the LIVE swatch `/api/swatch/monolithic/fc_snakeskin?size=200&color=<hex>`.
- Live app (port 59879) answers **HTTP 500** `quality review manifest missing: _wilds_rejection_work/release_quality/wilds_110_owner_review_manifest.json; owner accepted 0/110`. `server_routes/swatch_routes.py:532` calls `quality_write_guard` (server.py `_require_wilds_picker_write_quality`) for every monolithic, and the Wilds 110 release lock (`scripts/spb_wilds_quality_release_lock.py`, fail-closed by design: "never infers acceptance from M7 ... or any other mechanical metric") refuses. The manifest exists nowhere (not even `_archive/`). The `<img>` `onerror` hides the image -> the tile shows its dark empty background = "nearly black".
- The only fallback picture (`prefer=static` -> `thumbnails/monolithic/fc_snakeskin.png`, 2026-08-23) is ALSO stale: it is a superseded rebuild (green arrow dots on black, mean RGB [20,48,22]); the current finish renders violet/olive blotches, paint luma mean 0.20 (dark-ground design, base (8,9,6), dead 0.10). Side by side: `_snakeskin_work/fc_snakeskin_probe_vs_thumb.png` (current | stale thumb | what prefer=static serves).
- Why not fixed: a rebake would not change what the builder shows (its live request is refused by an owner quality lock, not by a missing bake), and opening that lock is the owner's call. Two options for whoever owns lane S / the builder: (a) the builder skips release-locked Wilds ids in its WHICH LOOK search (the second hit `fsk_snakeskin` "Snakeskin" from FRACTURED OPALFIRE renders fine: HTTP 200, luma 0.41), or (b) the owner completes / waives the Wilds review manifest, then rebake `fc_snakeskin` (it is in `INDEPENDENT_OVERRIDES`, so `SPB_ALLOW_EXPERIMENTAL_WILDS_THUMBNAILS=1` one-shot CLI bake is already owner-permitted for the static file).

## 6. Recommendation

**`snakeskin_cand_python` as the default for the copilot's "snakeskin / snake scales / reptile" row.** It is the one that reads as snakeskin instantly at 1:1 AND on the whole car on every paint (overlapping scales + python saddles carry at car distance; viper's diamonds and sunbeam's sheen are subtler there), it has the richest spec (12.6 effective materials vs OLD 5.3), and it is the fastest of the three (0.74 s). Viper is the natural pick for "rattlesnake / viper / diamondback" words and sunbeam for "holographic / iridescent snakeskin" (FIRSTTEST2's ask) if the owner wants per-word mapping later - that is a TEXTURES row split, not more math.

## 7. Exact change once the owner picks (example: python; swap the id for viper/sunbeam)

1. `engine/spec_patterns.py` - append one line at the very end (after the v2 `PATTERN_CATALOG.update(...)`, so nothing re-binds it):
   `from .spec_pattern_families.snakeskin_candidates_2026_10_04 import CANDIDATES as _SNAKESKIN; PATTERN_CATALOG["snakeskin_python"] = _SNAKESKIN["snakeskin_cand_python"]`
2. `js/spb-pro-edit.js` L298 (TEXTURES, id `snake`): `spec: 'snake_scale_diamond', specName: 'Snake Scale Diamond'` -> `spec: 'snakeskin_python', specName: 'Python Snakeskin'`.

Ship housekeeping that goes with it (not extra design): add a `SPEC_PATTERNS` row + the "Predator Skins" group entry in `paint-booth-0-finish-data.js` so the zone UI names it; `node scripts/sync-runtime-copies.js --write` (the new module + spec_patterns.py to `electron-app/server/`); bump the `?v=` of every changed JS; bake its builder thumb with `scripts/bake_offline_tex_thumbs.py` (TEX_BAKED). Keeping `snake_scale_diamond` untouched means saved projects that used it do not change.
