# ENGINE_ZONE_COST — make a zone's render cost proportional to its area (2026-10-05)

Lane: engine performance, OPTIMIZE mode (same pixels). Owner law: ≤ 3 s at 2048.
Trigger: flames lane measured ~0.6 s of server time per extra zone, whatever its size.

Kill switch: **`SPB_ZONE_BBOX=0`** (also `false/off/no`) restores the old full-canvas paths exactly.
It is read per call, so one process can A/B. Server/engine change → **needs a server restart** to go live.

Harness: `scripts/spb_zone_cost_bench.py` (one engine boot, one verdict line per item; log spam → `_zone_cost_bench/engine.log`).

```
python scripts/spb_zone_cost_bench.py --check          # old vs new per payload, uint8 paint+spec
python scripts/spb_zone_cost_bench.py --unit           # float-level compose_paint_mod full vs gathered
python scripts/spb_zone_cost_bench.py --time --runs 3  # timing table, cold zone cache every run
python scripts/spb_zone_cost_bench.py --lines S04      # line-level cumulative timer of build_multi_zone
```

## 1. Where the time goes (step 1)

Entry: `server.py /preview-render` → `shokker_engine_v2.preview_render` → `build_multi_zone(preview_mode=True)`; the zone loop is `for i, zone in enumerate(zones)` (~L18555), base path ~L19449-19520.

cProfile is misleading here (the spec runs in `_shared_spec_pool`, a second thread, and the attribution lands in `logging`). The line timer on `build_multi_zone`'s own frame (S04: 4 small zones + Everything Else, cold cache) gave:

| cost | line | what |
|---|---|---|
| 1.37 s | L19498 | `compose_paint_mod` FULL canvas for 3 solid/gradient zones of 3-4% (spec already on the crop path; paint rejected with "base color mode is adjusted") |
| 0.55 s | L19512 | waiting for the spec thread (Everything Else, full) |
| 0.14 s | L19510 | Everything Else paint |
| ~0.1 s each | L19449/19452/19469, L18673-18675, L20293, L20367, L18399/18400, L18594 | per-zone bookkeeping: `_mask_active_regions` called ~5x per zone (10 ms each), reject-reason `np.mean`s, zone-cache key digest of the full mask, prior-claim multiply, ownership hardening |

Inside `compose_paint_mod` for a paint_none base + solid colour: 2 full paint copies, a full-size colour source, `np.clip` of it twice, a full-size blend — ~0.25-0.45 s for a 3% zone.

## 2. Change 1 — gathered (area-proportional) paint for per-pixel zones

`engine/compose.py`:
- `compose_paint_mod_gathered()` + `paint_mod_gather_reject_reason()` (after `compose_paint_mod`): gathers the pixels the zone can change (`mask > 0.1`, exactly `hard_mask`'s support), runs the UNCHANGED `compose_paint_mod` on a (1, N) strip, scatters back. Eligible only when every step is elementwise: base `paint_fn is paint_none`, no pattern, no blend/2nd-5th overlay, colour mode source/solid/gradient, no Color Lab depth, no base/colour placement transform (fit-zone IS supported since round 2, see §3), gradient not angular/rotated, paint (H,W,3) float32 contiguous, coverage ≤ 60%.
- `generate_custom_gradient(..., coords=None)`: gathered-coordinate branch — the same float32 expressions evaluated at (row, col) pairs.
- `_apply_base_color_override(..., _color_src_coords=None)` and `compose_paint_mod(..., _color_src_coords=None)` forward it. `None` = old code path, untouched.

`shokker_engine_v2.py`: `_zone_bbox_enabled()` + `_zone_gathered_paint_mod()` (before `_log_bbox_fast_path_skip`), called at the two `compose_paint_mod` full-path sites of the base path (visible-crop spec + full paint; and full spec + full paint).

Verdicts (first round): `--unit` 44/44 FLOAT-EXACT (4 masks incl. soft/noisy × solid, solid@0.55, source+HSB, base_strength 0.4, 6 gradient directions); `--check` 15/15 BIT-EXACT.

## 3. Round 2: fit-zone gradients and the HSB tail fix

- **Fit-zone ("Fit gradient to zone"):** the fitted source depends on the whole canvas (cv2 resize of the full-size source into the mask bbox). The gathered path therefore builds the source at full canvas shape exactly as the full path does. It takes the bbox from the gathered `hard_mask > 0.05` pixels, which is the same set the full path scans, then gathers the fitted source at the zone's pixels (`_fit_full` in `_apply_base_color_override`). Only the colour source is full-size. Every blend step still runs on the strip.
- **HSB 1-ulp tail fix:** cv2 `COLOR_RGB2HSV` uses SIMD over the vector body and scalar code over the tail, and the two can differ by 1 ulp. A gathered strip whose length is not a multiple of the vector width put a pixel in the tail that sits in the body on the full canvas: one pixel was off by 5.96e-08 in soft_ellipse + radial + fit + hue. Fix: the strip is padded to a multiple of 64 with zero paint/mask dummies, which the blend leaves alone and which are dropped on scatter. HSB zones are rejected (full path) when `H*W` or `W` is not a multiple of 64; 2048 and every preview scale are multiples.
- Verdict: `--unit` **108/108 FLOAT-EXACT** (4 masks × solid / strength / source+HSB / base_strength / 6 gradient directions / fit-zone solid+gradient / gradient+HSB / fit+bri+strength). `--check` **15/15 BIT-EXACT**.

**Not done, on purpose: a gathered spec (`compose_finish`).** Spec is now the main per-zone cost for large or multi-part zones; flames fill regions are None, so the full `compose_finish` takes ~0.35 s. It was not gathered for three reasons:
- The dither planes come from `RandomState(seed).uniform((H, W))`, which depends on the canvas shape.
- `base_color_fit_zone` resizes the spec into the bbox, a whole-canvas operation.
- The spec values *outside* the mask still reach the output through the soft combine (>0.05), the zone-cache crops and the `_apply_zone_spec_*` post-passes.

An exact version would have to compute the full dithered plane anyway, so the saving is small and the risk is real. Next candidate if more speed is needed: exact memoisation of the per-zone bookkeeping (`_mask_active_regions` is called ~5x per zone, plus the reject-reason `np.mean`s and the cache-key digest), ~0.1 s per zone.

## 4. Final round: one process, `--unit --check --time --runs 3`, cold zone cache every run

Paint source is the latest real `ORIGINAL_paint_with_decals.png` at 2048, seed 51, preview_scale 1.0. Old = `SPB_ZONE_BBOX=0`. The timings are medians of 3 on a shared, noisy machine (other agents running), so rows within ±0.3 s are noise.

| payload | zones | verdict (paint / spec uint8) | old s | new s |
|---|---|---|---|---|
| S01 body_only | 1 | BIT-EXACT 0/0 | 0.80 | 0.90 |
| S02 +1 solid 3% | 2 | BIT-EXACT 0/0 | 1.24 | 1.04 |
| S03 +2 solid+grad | 3 | BIT-EXACT 0/0 | 1.85 | 1.26 |
| S04 +4 mixed | 5 | BIT-EXACT 0/0 | 2.89 | 1.78 |
| S05 flames hot rod | 3 | BIT-EXACT 0/0 | 2.50 | 2.05 |
| S06 true fire 3 layers (fit-zone) | 4 | BIT-EXACT 0/0 | 3.99 | 3.30 |
| S07 Foundation spec-only parts | 4 | BIT-EXACT 0/0 | 3.40 | 3.62 (noise: spread 2.84-4.48) |
| S08 soft edge + strength | 3 | BIT-EXACT 0/0 | 2.90 | 2.65 |
| S09 pattern + noise base (not eligible) | 3 | BIT-EXACT 0/0 | 5.15 | 4.32 (noise) |
| S10 monolithic region | 3 | BIT-EXACT 0/0 | 1.53 | 1.32 |
| S11 HSB + colour match | 3 | BIT-EXACT 0/0 | 2.12 | 1.44 |
| C_d547e73ede4b (real) | 2 | BIT-EXACT 0/0 | 2.71 | 2.00 |
| C_2d81e98b608b (real) | 2 | BIT-EXACT 0/0 | 2.49 | 2.13 |
| C_8738dc2ea9f0 (real) | 4 | BIT-EXACT 0/0 | 2.93 | 3.27 (noise: spread 2.31-3.37) |
| C_d40d685aa314 (real) | 4 | BIT-EXACT 0/0 | 3.18 | 3.10 |

Per small solid/gradient zone, the paint cost dropped from ~0.45 s to ~0.05 s. The S04 slope went from ~0.5 s per zone to ~0.25 s per zone; what remains is the spec and per-zone bookkeeping (§3).

Other gates:
- **Golden net:** 388 same, 42 changed, 1 removed. The **identical set** reproduces with `SPB_ZONE_BBOX=0` and with the **HEAD versions** of both of my files loaded through an import hook (hook verified: `compose_paint_mod_gathered` absent). These deltas already exist in the committed snapshot and are not from this lane; another lane's owner should re-bake or accept them.
- **Retired gate:** 0 hits, PASS.
- **`audit_render_perf.py --trials 3`:** not applicable. It times each finish's own `spec_fn`/`paint_fn` at 512 and never reaches `build_multi_zone` or `compose_paint_mod`, which is all this lane changed. It was started, then stopped to spare the shared machine. The budget evidence for this change is the §4 table, timed at full 2048 through the real `preview_render`.
- **Two-copy:** only my two files were copied to `electron-app/server/` (the electron copies differed only by this lane's hunks). `--check` now lists only `thumbnails/_manifest.json` and `snakeskin_candidates_2026_10_04.py` (report-only), which belong to other lanes and were left alone.

## 5. Files changed

- `engine/compose.py`:
  - L1861 `generate_custom_gradient(..., coords=None)`; gathered branch at L1909
  - L2256 `_apply_base_color_override(..., _color_src_coords=None)`; `_fit_full` at L2287-2291; gathered gradient at L2481
  - L5101 `compose_paint_mod(..., _color_src_coords=None)`; forwarded at L5306
  - L5950-6100: header, `_GATHER_COLOR_MODES`, `paint_mod_gather_reject_reason` (L5967), `compose_paint_mod_gathered` (L6032)
- `shokker_engine_v2.py`:
  - L918 `_zone_bbox_enabled()`
  - L927 `_zone_gathered_paint_mod()`
  - call sites L19531 and L19548, which fall back to the untouched `compose_paint_mod` call
- Mirrors: `electron-app/server/engine/compose.py` and `electron-app/server/shokker_engine_v2.py` (byte copies).
- New: `scripts/spb_zone_cost_bench.py` (harness). Outputs are in `_zone_cost_bench/` (`final_round.txt`, `timing.json`, `golden*.txt`).

**Kill switch:** `SPB_ZONE_BBOX=0` (or false/off/no) in the server environment restores the old full-canvas paint calls exactly. It is read on every call.
**Deploy:** this is an engine change, so the server needs a **restart** (59876 and 59879) to pick it up. The lane did not restart anything.
