# ENGINE_TEXTURE_ANCHOR (engine lane, 2026-10-06)

Goal: opt-in per-zone flag so a part-limited copy of a whole-car zone renders the SAME texture
pixels inside that part as the original. Zones without the flag stay bit-exact.

## Root cause (found 2026-10-06)

- `shokker_engine_v2.py` has a **visible-crop fast path** for base-only zones that cover <= 18% of the
  canvas (`_bbox_noise_fast_path_reject_reason` -> `_compose_bbox_noise_base_spec` /
  `_compose_bbox_finish_spec_stack` / `_apply_bbox_compose_paint_mod`). It calls the base's
  `base_spec_fn(crop_shape, ...)` / `compose_finish(..., crop_shape, ...)` on each bbox crop, so the
  noise field is generated at CROP size: a different, finer grain than the full-canvas render.
- A roof copy (12.4% of the canvas) takes this path; the whole-car original (> 18%) takes the full
  path. Same story for the original zone when an everything-but-the-roof zone sits above it: its
  visible mask shrinks to the roof and it drops into the crop path (`_seedtest.py`, 58%).
- Second, independent cause: the zone seed is `seed + 13 * render_seed_index` (or `seed + 13*i`).
  `js/spb-pro-zone-kit.js` COPY_SKIP_RE drops `renderSeedIndex` on copies, so a copy gets a new seed.

## Log

### 2026-10-06 step 1-2: flag + pass-through
- Engine: `_zone_texture_anchor_canvas(zone)` + one gate at the top of `_bbox_noise_fast_path_reject_reason`
  (shokker_engine_v2.py, shared by car / helmet / suit loops) -> an anchored zone never takes the crop
  spec/paint paths; it uses full-canvas `compose_finish` (+ the bit-exact gathered paint path, unchanged).
  Kill switch `SPB_TEXTURE_ANCHOR=0`.
- Field: `zone["texture_anchor"] = "canvas"` in the payload; client zone object `textureAnchor: 'canvas'`.
  Pass-through: paint-booth-5-api-render.js (serializer), server.py preview endpoint (field-by-field
  rebuild), paint-booth-2-state-zones.js getConfig/loadConfigFromObj (save/load). /render passes zones as-is.
- Seed: copies must ALSO carry the original's `renderSeedIndex` (zone seed = seed + 13*index).
- Harness: `scripts/spb_texture_anchor_check.py` (baseline sha of the 15 bench payloads x bbox on/off,
  taken BEFORE the edit: `_zone_cost_bench/texture_anchor_baseline.json`).
- Before-fix roof rows (copy vs whole-car original, inside the roof): every finish DIFF except none;
  e.g. metallic spec 100% px, pearl 99%, electric_ice 100%, patina 65%. Full table `_zone_cost_bench/ta_before.txt`
  (that run compared against a colour-'everything' original, whose mask misses 6.1% of the roof; fixed to a
  full-canvas region original for the after-run).

### 2026-10-06 step 3: harness round 1 -> two more mask-relative inputs found
- Round 1 (crop gate only): base finishes all BIT-EXACT (f_pearl, f_chrome, metallic, pearl, candy, chrome,
  chalky_base, electric_ice, patina_bronze), incl. the `_seedtest.py` "under" scenario. Still DIFF:
  - pattern (carbon_fiber) paint max 131 on 100% of the roof: PATH 1 `auto_scale = _compute_zone_auto_scale(zone_mask)`
    densifies patterns by the zone bbox area (< 0.6 of canvas). Anchored -> auto_scale 1.0 (= a whole-car zone).
  - monolithic ff_truchet_glass spec max 23 on 3.6%: FRACTURED `fracture_spec(art, mask)` reacts to the mask edge.
    Anchored -> the monolithic spec_fn gets a full-canvas mask (combine step still applies the zone mask);
    the zone-layer cache key gets ("texture_anchor","canvas") appended only for anchored zones.
- No-flag regression note: the pre-edit baseline vs round 1 showed S09 CHANGED (both bbox modes). Cause is
  pre-existing, not this change: `abs(hash(base_id))` seeds the crop/base noise and Python randomises str
  hashes per process unless PYTHONHASHSEED=0 (the app sets 0 in main.js / supervisor / START_SERVER.bat).
  The harness now warns without PYTHONHASHSEED=0, and the baseline is baked with the flag gate patched to
  False in the same process (`--baseline --old`; every change routes through `_zone_texture_anchor_canvas`).

### 2026-10-06 step 3 result: roof-copy harness (PYTHONHASHSEED=0, one process)
`python scripts/spb_texture_anchor_check.py --baseline --old --check --noop` -> `_zone_cost_bench/ta_after3.txt`.
Original = one full-canvas zone; copy = same zone on the roof rect (12.4% of the canvas) with
`texture_anchor:"canvas"` and the same `render_seed_index`. Compared inside the roof.

| finish | anchored copy | no-flag copy (today) | original under an everything-but-roof zone, anchored |
|---|---|---|---|
| f_pearl (Foundation, source) | BIT-EXACT | BIT-EXACT | BIT-EXACT |
| f_chrome (Foundation, source) | BIT-EXACT | BIT-EXACT | BIT-EXACT |
| metallic | BIT-EXACT | spec 100% px (max 52), paint 98.6% (max 39) | BIT-EXACT |
| pearl | BIT-EXACT | spec 98.9% (152), paint 100% (157) | BIT-EXACT |
| candy (solid colour) | BIT-EXACT | spec 100% (119) | BIT-EXACT |
| chrome | BIT-EXACT | spec 96.8% (25), paint 98.1% (255) | BIT-EXACT |
| chalky_base | BIT-EXACT | spec 99.7% (220), paint 97.1% (153) | BIT-EXACT |
| electric_ice (noise) | BIT-EXACT | spec 100% (252), paint 100% (255) | BIT-EXACT |
| patina_bronze (noise) | BIT-EXACT | spec 62.5% (1), paint 100% (70) | BIT-EXACT |
| gloss + carbon_fiber pattern | BIT-EXACT | paint 100% (131) | BIT-EXACT |
| ff_truchet_glass (monolithic, PROTECTED - fn untouched) | BIT-EXACT | spec 3.6% (23) | BIT-EXACT |

ROOF SUMMARY 22/22 anchored rows bit-exact. No-flag regression: 13 bench payloads (11 synthetic + the 2
captured job_render_* payloads present today, not 15) x SPB_ZONE_BBOX on/off = **26/26 bit-exact** vs the
pre-change engine.

Foundation colour-source copies were already exact (flat spec): the visible S5 roof change came from
the noisy/chalk/chrome looks of the owner's zones, and from the copy's new seed.

### 2026-10-06 step 4: Foundation F-zone cost
- Engine profile of the S5 F zone (f_pearl, colour source, everything but the roof, also with a
  body-layer `source_layer_mask` proxy at 87% coverage): CPU ~1.1 s for the whole preview_render of that
  one zone, ~0.8 s of it fixed per-render overhead (rem-only render = 0.8 s CPU). The zone itself: compose_finish
  0.27 s isolated + gathered paint 0.24 s + combine np.where/astype 0.23 s. **The engine does not spend
  2.9-3.8 s on this zone**; S5's 3.78 s is client wall-clock on a shared, loaded machine (this session saw
  4-6 s wall for a 0.8 s-CPU render while other lanes rendered) plus client mask/RLE + transfer.
- Bit-exact saving landed anyway: every Foundation `f_*` (PURE constant spec fn) is a paint-noop base that
  the flat plate declined, so it ran the thread-overlapped spec+paint pair. Now: spec-only full-path
  `compose_finish` (same call), paint untouched. Proof: `--noop` = 16 bases (6 Foundation + 10 other
  paint-noop noisy-spec bases out of 74) x 4 masks x alone/+catch-all = **128/128 bit-exact**. CPU
  F + catch-all 1.84 -> 1.39 s, F with layer mask 1.05 -> 0.86 s; F alone unchanged within noise.
  Kill switch `SPB_NOOP_PAINT_SKIP=0`. Car loop only (helmet/suit loops untouched).
- Anchor cost: an anchored copy takes the full-canvas spec path instead of the crop path. Wall, same
  run: electric_ice +0.4 s, truchet +0.3 s, candy +0.2 s, Foundation +0 s. The base spec plate is cached
  by (base, seed, shape), so a copy that shares the original's seed reuses the original's plate.

### 2026-10-06 gates (final)
- `scripts/spb_texture_anchor_check.py --baseline --old --check --noop` (PYTHONHASHSEED=0): NOFLAG 26/26, ROOF 22/22, NOOP 128/128.
- `scripts/spb_zone_cost_bench.py --check`: 13/13 BIT-EXACT (gathered fast path unaffected).
- Golden net: 43 changed + 1 removed before, 44 + 1 after; the one new id is `flame_hotrod`, whose
  `engine/paint_v2/flames_2026.py` the FLAMES lane saved at 02:54, during the run. The golden net calls
  registered finish functions directly, and this lane changed none of them. Otherwise the set is unchanged.
- Two-copy: the 4 files copied to electron-app/server/ (diffs were mine only); `sync-runtime-copies --check`
  shows drift only in other lanes' files (thumbnails manifest, flames_2026.py, snakeskin candidates).
  Cache tokens bumped in both paint-booth-v2.html copies (state-zones + api-render).
- **The server needs a restart** for the engine/server.py changes (not restarted by this lane).

## Contract for the helper planner (js/spb-intent-plan.js, not edited here)
On every part-limited copy of an existing zone's look:
```js
copy.textureAnchor = 'canvas';                       // -> payload zone.texture_anchor = "canvas"
copy.renderSeedIndex = original.renderSeedIndex;     // same seed; zone-kit copyLook() deliberately skips it
```
To keep the ORIGINAL zone stable when another zone later covers most of it (the `_seedtest.py` 58% case),
set `textureAnchor:'canvas'` on the original as well. A whole-car original already renders on the full
path, so its pixels do not change.
Caveat: the copy matches the original only where the original's own texture does not depend on its mask.
For base, noise, pattern and Foundation looks, and for FRACTURED monolithics checked against a full-canvas
original, the match is exact. A monolithic whose spec_fn reacts to the original's mask EDGE (FRACTURED
`fracture_spec`) can still differ within that fn's edge radius of the original's mask boundary.
