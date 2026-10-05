# WP6 - Edge quality of colour recolours (2026-10-03)

Lane: `js/spb-pro-edit.js` (compile step only), `js/spb-pro-zone-kit.js` (colourTest / probeRegion / paintColours / new helper edgeFit + the per-colour tolerance line in setRegion), `_easy_claude_work/pw/wp6_*`, `_easy_claude_work/eval/wp6_*`.

## Step 1 - the engine's contract (read-only)

Source: `shokker_engine_v2.py` `_build_plain_rgb_color_mask_fast` (~1638), `_build_layer_rgb_color_mask_fast` (~1702), `_harden_zone_ownership_mask` (~18353), zone loop (~18160-18300); `engine/core.py build_zone_mask` (~991-1133).

| question | answer |
|---|---|
| distance | **weighted Euclidean** (BT.601 weights): `d = sqrt(0.30*dR^2 + 0.59*dG^2 + 0.11*dB^2)`, 0-255 units. NOT per-channel max. |
| tolerance | `mask = clip(1 - d/tol, 0, 1)` (linear falloff), default 30 when missing. |
| colours[] | zone `color` may be a LIST of `{color_rgb, tolerance}`; each selector has its OWN tolerance; union = per-pixel `max`. The client already sends per-entry tolerance (`paint-booth-5-api-render.js:3768`, `c.tolerance || 40`). |
| hard edge | client sends `hard_edge: true` by DEFAULT (`z.hardEdge !== false`). Hard: blur 0, ownership = `mask > 0.01` -> 1 (binary: every pixel with d < ~tol is FULLY recoloured, every other pixel keeps the old colour). |
| soft edge | `hard_edge: false` -> Gaussian feather sigma **3 px (fixed)** on the mask, then ownership ramp `m^2/0.15` below 0.15, 1 above. This is a fixed ~3 px GROW + soft tail: it would fatten a 6-10 px glyph by ~6 px and cannot be tuned per zone. |
| grow / dilate / antialias / per-zone feather | **none exist.** No zone field controls feather radius, mask growth or AA un-mixing. |

Consequences:
- The client's probe (`colourTest`, "per-channel distance <= tolerance") did NOT mirror the engine: the engine's ellipsoid reaches 1.8x tol in R, 1.3x in G and **3x tol in B**. With TOL_PAINT 38 the engine grabs anything within 114 in blue alone. Fixed in step 2 (colourTest now uses the engine metric).
- Halos come from the binary hard edge: AA pixels (blend of old colour + body) with d >= tol keep the old colour. The only lever the client has is WHICH spheres it sends (centres + per-colour tolerances). Covering the AA ramp is therefore done with extra `colors[]` entries along the old-colour -> neighbour line, each with a provably safe radius.
- **Soft-edge growth is OUT OF SCOPE** (no tunable parameter). Engine change for the owner: a zone field `edge_grow_px` (0-3) applied as a morphological dilation of the binary colour mask restricted to pixels whose colour lies on the segment between the zone colour and the adjacent colour (i.e. AA pixels only), plus optionally `edge_unmix: true` that recolours those AA pixels by their blend fraction (new*a + neighbour*(1-a)) instead of fully. That would give true anti-aliased recolours; the client can then set it on colour-region zones.

## Step 2 - adaptive per-colour tolerance (built)

`js/spb-pro-zone-kit.js`
- `colourTest` now uses the ENGINE rule (weighted distance < tol). It was per-channel max, so every probe / describe / footprint under-reported what the engine selects.
- New `SpbProZone.edgeFit(hexes, {floor, debug})` (memoised per paint + colours). Measures the paintable pixels (stride 2, `SpbProCar.paintableMask()`):
  1. 24-colour palette; clusters that are anti-alias RAMPS (small, lying on the segment between two much bigger colours AND thin on the paint: >=70% of their pixels have a clearly different colour within 3 px) are not "other colours".
  2. Shades: a same-hue colour (<=14 deg, chromatic) joined to a chromatic target by a DENSE colour ramp (gradient / shading, density >= 8% of the endpoints) joins the fill as an extra `colors[]` entry.
  3. Per target: `tol = clamp(p98 spread of the pixels nearest to it + 6, floor, min(cap - 1, 1.25 x floor))`, `cap` = min over the other colours of `max(D/2, D - their p95 spread - 4)` (a tight flat neighbour lets the target go further than half-way without ever reaching its pixels).
  4. AA ramp spheres toward each of the 4 nearest neighbours the target touches, from the target's tolerance out to 55% of the way: radius bounded by every other colour's cluster (centre distance - p95 spread - 4) and by the neighbour (0.58 L); checked at FULL resolution: pixels not within 3 px of the target's own pixels may be <= 1% of the sphere's pixels, else the sphere shrinks (x0.7, up to 4 times) or is dropped; a ramp that turns out to be an area colour stops the walk. <= 12 colours total.
- `setRegion` honours `region.tols[i]` (per-colour tolerance; the engine and the payload builder already carry a tolerance per `colors[]` entry).
- `probeRegion` honours `tols`, samples colour regions at stride 4 and reports `covers_px`, `tolerance`, `fringe_estimate` (px within tol+12 but outside tol that TOUCH the selection = the halo that would remain) and `fringe_pct_of_region`.

`js/spb-pro-edit.js` compile step: `TOL_SPEC 30 / TOL_PAINT 38` are now the FLOORS and the fallback; each colour region calls `edgeFitFor(colors, paintMode)` -> `rg.colors / rg.tols / rg.tolerance` (falls back to the fixed value when `SpbProZone.edgeFit` is absent, e.g. node tests). The vocabulary tables were not touched.

## Step 3 - synthetic measurement (`pw/wp6_synth.py`, `pw/wp6_measure.py`, `pw/wp6_metrics.py`)

Sheet: 2048, navy body `#1e3c8c`, white "24" x2 (9 px and 6 px strokes), a 14 px white stripe (slanted), a shaded red panel (176 -> 49 gradient + sheen), a light-grey panel `#d0d0d4` +-2 noise; all drawn at 4x and box-downsampled (true AA). `synthB` = same without the grey panel.
Harness: own Chrome 9444, server 59879, `flatload.load_flat`, offline sentence via `spbProAI.send`, the app's own `/preview-render` request re-posted at `preview_scale 1.0` (full 2048 paint + spec). "before" = `SpbProZone.edgeFit = null` (= the fixed tolerance), "after" = edgeFit. Fringe px = within 3 px of the element and the RENDERED colour still nearer the old white than both the new purple and the body (engine metric).

| case | before (fixed 38) | after (edgeFit) |
|---|---|---|
| synth digits fringe px (ROI 54k) | 3064 | **1840** (-40%) |
| synth stripe fringe px (ROI 37k) | 1729 | **878** (-49%) |
| synth grey panel interior false grabs | 3 | **0** |
| synth changed px away from the white elements | 3 | 22 (the grey panel's own anti-aliased corner rim) |
| synthB (no grey) digits / stripe fringe | 3064 / 1729 | **0 / 0** |
| synthB false grabs | 0 | 0 |
| synth/synthB "make the red matte": red / dark-shade spec recall | 100 / 100 % | 100 / 100 % (rim 80% both) |
Crops (base | render, 4x): `eval/wp6_synth_crop_{digit,small,greyedge}_{before,after}.png`, `eval/wp6_synthB_crop_*`. LOOKED: synthB after has no halo at all; synth after still shows a faint light rim on the glyph edges (below).

Why the grey case cannot reach 0 with the engine as it is: the white->navy AA pixels at 72-85% white ARE the grey's colour (D to grey 7-8, grey spread 5). Any sphere that recolours them recolours the grey panel. Only a spatial (soft-edge) engine rule can separate them - see step 1.

## Step 4 - real paint (ARCA `stockcars2 arcachevy25/car_1023047.tga`, read-only)

| sentence | before | after |
|---|---|---|
| "make the white purple": fringe px (ROI 964k; local background = nearest pixel 4+ px outside) | 53,830 | **25,305** (-53%) |
| same: changed px away from the white (> 4 px) | 0 | 311 (MAHLE-logo AA inside a white decal panel + headlight photo greys; 0.05% of the white) |
| "make the red matte": spec recall of the red | 97.75% | **99.88%** (shades `#f70b15`, `#ca232a` joined) |
| same: spec changed px away from the red | 0 | 777 (dark-red tail-light lens photo texture: the shade test reads its dense red ramp as shading) |
Zones: white `#fffeff` tol 42 + 4 ramp spheres (2 toward blue, 2 toward red); red `#ff2835` 38 + `#f70b15` 30 + `#ca232a` 37. Crops: `eval/wp6_arca_crop_0_{before,after}.png` (flame band: the continuous light line becomes a sparse dotted one), `eval/wp6_arca_where_*.png` (where the extra pixels are).
Tuning history (all measured): off-edge allowance 0.2% shrank every real sphere to 5-7 (fringe 38k); 1% + max 12 px gave synth rim 13 / ARCA fringe 35k; kept **1%** (ARCA 25k, synth rim 22). Target cap 64/100 was dropped to 1.25 x floor after the red reached 49 and took orange logo pixels.

## Suites / ritual
- `node --check` both files OK; `scan_ctrl.py` 0 control chars; files are LF (preserved).
- `edit_corpus.js` 409 phrases 0 mismatches; `edit_req_test.js` 17/17; `l6/adversarial.cjs` 11 PASS 0 FAIL. Tolerance is NOT part of the corpus signature (`sig()` = ops only) and node has no `SpbProZone`, so the compile output there is unchanged by design.
- Tokens: `spb-pro-zone-kit.js?v=spb-pro-zone-kit-20261003wp6b`, `spb-pro-edit.js?v=spb-pro-edit-20261003wp6`; `sync-runtime-copies --manifest sync_mine.json --write` then `--check`: no drift.

## Not verified / open
- Stacking (`t248_edit_stack.py`), `t246` real-paint sentence sweep and the MCP `refinish` path were not re-run in the browser (same compile function, but `editKey` now includes the extra shade / ramp colours: same paint -> same colours, so a follow-up on the same colour still merges; not run).
- edgeFit costs ~0.2 s (synthetic) to ~1.2 s (busy real paint) per colour region, once per paint + colours (memoised).
- Hue-shift recolours (`adj.hue`) and part-bound colour regions use the same fit; not measured separately. The owner's Electron build was not run.
- Engine change for the owner (soft edge): see step 1 (`edge_grow_px` / `edge_unmix`); needed for the last AA band when a neighbour colour sits on the ramp.
