# PART_MASKS (2026-10-06) - jagged part edges ("make the hood orange" ring)

STATUS: fix built and verified on test server 59880 through a Playwright route override. NOT landed: nothing under js/, engine/, server_routes/ or the HTML was written (coordinator hold while S6 runs on 59879).

## Cause
`js/spb-pro-carmap.js` builds every named part from the 256x256 island grid (1 cell = 8 px of the 2048 sheet): the Mask layer is read at 256, split by Wire outlines thickened one cell, labels grown back only 3-4 cells (`label()`), then `maskOne()` blows the cells up to 2048 (bilinear >= 0.35). Consequences on the owner's ARCA Chevy SS hood:
- the rim is a staircase that ignores the real panel edge (the template Mask layer is full resolution);
- bands up to ~60 px just inside / outside the outline were never labelled, giving the stubs and notches on the left/top/bottom of the ring;
- the part leaked ~0.2% of its pixels outside the paintable area.
Not the cause: the visible-ownership taper, colour tolerance or polygon point count (parts are grid cells, not polygons). The orange ring = body-layer pixels inside this mask, so the ring edge IS the mask edge.

## Fix (scratch, hunk-ready): `_easy_claude_work/part_masks/scratch/spb-pro-carmap.landable.js`, diff `docs/handoff_reports/PART_MASKS.patch` (101 lines, against root js/spb-pro-carmap.js sha1 ea1d2fbf40...)
1. `fullPaintable()` (new, cached per car on CACHE._fp): reads the Mask layer at full resolution (same inversion rule as binaryGrid) and the Wire layer green outlines (same colour test as wallGrid), cuts the paintable area into panel pieces, and builds a full-resolution OWNER map (which island owns each pixel):
   - a piece whose labelled cells all belong to one island, and cover >= 40% of the piece, is that island's whole (restores the unlabelled strips);
   - a shared piece goes to the nearest labelled cell (<= 4 cells); pieces the labels barely touch (vents, wipers) stay nobody's;
   - the island is grown 12 px (1.5 cells) through the bleed network only, so the rim ends on the template's paintable edge.
   - Guard: returns null (maskOne behaves exactly as before) when there is no Mask layer, the server-read mask is in use, or the full-res mask disagrees with the grid (< 90% of paintable cells). DLM, which has no usable Mask layer, is therefore byte-identical.
2. `maskOne()`: for island / library-box parts, pixels outside the paintable area never count; where the owner map says "this part" the pixel is in; where it says another island the pixel is out; where nobody owns it the old bilinear grid answer stays, so coverage never shrinks. Loop bounds grow 13 px on the part's own outer sides only (portion/band cuts unchanged).
Engine, JS API, mask format (Uint8 0/255) unchanged; only part-region edges move. Cost: first `maskFor` per car ~0.7 s once (full-res read + piece labelling), cached; ~24 MB held per car.

## Measured (full 2048 masks, before -> after, me: `part_masks/analyze.py`, metrics.json)
rim_dist = mean distance (px) from the part's boundary to the template Mask edge; on_edge = % of boundary within 1.5 px of that edge; leak = % of part pixels outside the paintable area. Means over all parts:
| car | parts | rim_dist | on_edge % | leak % | total area |
|---|---|---|---|---|---|
| Owner ARCA Chevy SS (SS PSD) | 8 | 3.77 -> 1.65 | 23.9 -> 66.1 | 0.19 -> 0.00 | 2.64M -> 2.76M |
| Gen 6 Camaro (g6) | 8 | 2.73 -> 0.49 | 37.0 -> 89.6 | 0.29 -> 0.00 | 2.47M -> 2.55M |
| Silverado truck | 6 | 3.65 -> 1.34 | 17.8 -> 52.3 | 0.15 -> 0.00 | 2.18M -> 2.27M |
| F150 | 6 | 3.31 -> 1.65 | 20.0 -> 53.1 | 0.19 -> 0.00 | 2.14M -> 2.21M |
| Next Gen city (ngcity) | 8 | 3.44 -> 1.90 | 25.1 -> 64.7 | 0.24 -> 0.00 | 2.11M -> 2.29M |
| DLM | 6 | unchanged (no usable Mask layer; refinement off) | | | |
Per-part numbers (area, perimeter/sqrt(area), holes, islands, leak, gap, rim_dist, on_edge) for every part: `_easy_claude_work/part_masks/analyze_final.txt`. Owner hood: area 358,673 -> 388,180, rim_dist 3.59 -> 2.45, on_edge 17.8 -> 63.5%, gap to template 25,174 -> 11,771 px, perimeter/sqrt(area) 5.57 -> 5.01, leak 0.10 -> 0. Coverage never fell on any part of any car (every part area >= before). Parts of the 33 library cars / 7 server-learned cars without a PSD in `C:/1Shokker Paint Car Examples` were not measurable (ram/ram2 recognise no parts; learned `claude-*` cars have boxes only).
Caveat on the "stair8" column in analyze_final.txt: my axis-aligned-run score is not a reliable staircase measure (it rises when edges get long and straight); trust rim_dist / on_edge / leak.
Known leftovers: a few parts grow small extra pieces or holes (e.g. ngcity hood 1->2 pieces, truck hood holes 2->3, g6 left side holes 2->4: enclosed windows / arches the outlines isolate); roof/trunk/bed on pickups still sit 2-4 px from the template edge where the Wire outline is not closed.

## In-app check (59880, owner ARCA car, same request "make the hood orange" = add_zone region {part:"hood"} colour orange)
`docs/handoff_reports/part_masks_shots/hood_before_after.png` (left = live code, right = fix): the ragged outline with notches and stubs becomes the clean rounded hood panel edge. Added orange pixels: 6,588 of 6,588 on the body colour (146,233,190); 0 on decal / art pixels (the zone is still body-layer-limited and visible-ownership clipped). Preview shows only run-to-run noise elsewhere (3,462 px differ between two no-zone renders of the same car, unrelated). Other shots: `part_masks_shots/sheet_{owner,g6,truck,f150,ngcity}.png` (each part before | after over the template, new rim in yellow). Raw before/after previews: `_easy_claude_work/eval/part_masks_out/{before,after}_{t0,t1}.png`.
Leftover seen: the thin straight strips just under the hood in the template are islands the grid labels as hood; they were ragged before and are now clean (they no longer show as a detached bar after the 40% rule).

## To land (coordinator, after S6)
1. `python _easy_claude_work/part_masks/make_scratch.py --no-hook` rebuilds from the CURRENT root js/spb-pro-carmap.js (asserts every anchor); copy `scratch/spb-pro-carmap.js` over `js/spb-pro-carmap.js` (the checked-in `.landable.js` is the same built from sha ea1d2fbf40). Atomic: write temp + os.replace.
2. `node scripts/sync-runtime-copies.js --write` then `--check` (carmap.js is in both copies; they were identical).
3. Bump only `spb-pro-carmap.js?v=20261005mcp3` in BOTH paint-booth-v2.html copies (e.g. `20261006pm1`).
4. Re-run `python _easy_claude_work/part_masks/inapp_hood.py after` without the route (drop the pg.route line) and compare to `part_masks_shots/hood_before_after.png`. Contracts `tests/ai_carmap_*_contract.cjs` were NOT run against the scratch (they read the root file).
Helper-owned files: nothing needed (no hunk for spb-pro-ai.js / offline / intent / convo-state).
Files: `_easy_claude_work/part_masks/{DIGEST.md,PROGRESS.md,make_scratch.py,measure_dump.py,analyze.py,inapp_hood.py,metrics.json,analyze_final.txt,out/<car>/}`.

