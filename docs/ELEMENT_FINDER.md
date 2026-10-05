# Numbers / sponsors / stripes on a FLAT paint (2026-10-02 / 03)

Most paints people load are flat TGAs with no layers, so "make the numbers purple" has nothing to point at. This is how the app (and an AI driving it) finds them, what is proven, and what is NOT.

## The pieces

| Piece | File | What it does |
|---|---|---|
| Finder | `js/spb-pro-elements.js` + `js/spb-elements-model.js` (generated, 575 KB) | Tiny U-Net (6 input channels, int8 weights, pure JS forward ~3.6 s) says per pixel: body / numbers / sponsors+logos / stripes / dead space. A colour step then sharpens it to crisp glyph edges (boxes from the net, glyph = what differs from the ring of paint around the box). |
| Region selectors | `js/spb-pro-zone-kit.js` | `region.element` (`numbers` / `numbers:fill` / `numbers:outline` / `sponsors` / `stripes`) and `region.exclude` (["numbers","sponsors","stripes"]: the zone covers its selection EXCEPT those). |
| Compiler | `js/spb-pro-edit.js` | Words -> zones (typed sentences, in-app AI tools and MCP share it). "numbers" = fill unless the buyer says outline / the whole number. |
| Chat flow | `js/spb-pro-ai.js` | Always asks first on a flat paint; teach by box; "those are not the numbers"; "there are none on this paint". |
| AI tools | `describe_paint`, `look_at_paint` (MCP only), `mark_elements`, `refinish` (+`boxes`) | An AI that can SEE reads the digits itself and hands over loose boxes. |
| Learning | `localStorage spb_elem_learned_v1` + `/api/ai/learned-elements` | Number places the buyer / AI marked, per iRacing car folder. Proposals only. |

## What is proven (and what is not) - read before trusting it

- Training truth = the Numbers / Logos / Tape layers of the owner's 114 livery PSDs composited with the template layers off (`_easy_claude_work/elements/e2_build_truth.py`).
- Holdout (cars whose template dead-space layout the net never saw), `elements/e6_eval.js holdout`: numbers pixel IoU **0.74** (precision 0.89, recall 0.82), sponsors **0.47**, stripes **0.34**.
- **BUT** that holdout is almost all truck sheets (Chevy / Ram / F150 / ARCA trucks - the owner's PSDs are mostly trucks), and its own confidence cannot be trusted as a gate: on the 175 real unlabelled paints of the lab (`elements/lab/summary.json`) the median numbers confidence is 0.76 and Ferrari GT paints where the picture shows tinted junk score 0.82-0.93 (the only holdout-based confidence check, `elements/e10_conf.js`, is CONTAMINATED: the shipped model was trained on ALL paints, so `e6_eval.js holdout` against it reads 0.88 / 0.69 / 0.81; the honest numbers are the 0.74 / 0.47 / 0.34 measured with the model trained WITHOUT the holdout). On a GT car (Ferrari 488 sheet) and several ARCA paints it tints junk (engine bay, sponsor panels) and misses the real digits. Treat it as "good on trucks, a guess elsewhere".
- **Many real paints have NO number drawn at all**: iRacing stamps it (Sim-Stamped Number, `car_<id>.tga`). `car_num_<id>.tga` is the same kind of sheet with the painter's own number in it - NOT a separate number texture. A paint with no number should get an honest "there is none on this paint", never an invented one.
- Numbers are NOT in the same place on every paint of one car folder (4 ARCA paints, `pw/t260_same_car_places.py`), so remembered places are proposals, not facts.

## The rules the app follows because of that

1. A flat-paint request about numbers / sponsors / stripes **always shows what it found first** (tinted picture: numbers pink, sponsors blue, stripes yellow; Yes / No, I will show you / There are none on this paint), unless the buyer already confirmed or drew it on this paint.
2. "No, I will show you" -> the buyer drags a box around ONE number; its glyph colours (not the paint behind it) become the mask. This REPLACES the net's guess. Colours first; if that fails, connected-region mode.
3. "those are not the numbers" switches off what the last change did to them and asks again. Nothing is deleted; Undo / Versions still work.
4. Stripes not found -> the helper asks for the colour instead (no box flow: one box cannot find all the stripes).

## For an AI (MCP / online model)

1. `spb_describe_paint` - says what the finder thinks and warns that it is truck-proven only.
2. `spb_look_at_paint` - two images: the whole flat paint with a 0.1 ruler (x along the top, y down the left, 0..1) and the same tinted with the app's guess (`app_guess:false` leaves the guess out, for an unbiased read). Read the digits / logos / stripes yourself. **Zoom:** `region:[x0,y0,x1,y1]` returns that part at full resolution with a finer ruler that stays in whole-sheet fractions, so small digits (under ~1.5% of the sheet) can be read and the boxes are valid as they are.
3. `spb_mark_elements {kind, boxes:[[x0,y0,x1,y1],...]}` - one LOOSE box per number, as fractions. A glyph = a region of one colour lying fully inside the box (art running out through the box edge, the background colour and glyph counters are not glyph). Reply lists `glyph_colours_found`, `boxes_not_used` + why, and an image of what is marked. Check it.
4. `spb_refinish {target:"numbers", colour, look}` (or pass `boxes` straight to refinish). Colour zones created later sit BELOW element zones, so the numbers keep their look.
Verified by Claude through `pw/aibridge.py` (an isolated page that answers exactly like the MCP bridge): ARCA "Mello Yello 00" sheet - both "00" selected cleanly (counters out, stripes untouched), then `numbers purple chrome` + `yellow -> orange pearl` kept the numbers on top.

## Limits / harness notes

- The live preview does not redraw after a FLAT file is loaded in the test harness (no render request is made), so flat-paint results there are judged from the tinted overlay + the zone list, not the preview. In the owner's own app, check the preview.
- Recolours are exact-colour regions: anti-aliased fringes of the old colour can remain on very fine glyphs (adaptive tolerance / soft-edge growth NOT done).
- The `learned_elements.json` rows on the local server are the raw material for a shipped atlas (merge script not written).

## Retrain / measure

```bash
python _easy_claude_work/elements/e2_build_truth.py      # truth from the PSDs
python _easy_claude_work/elements/e3_train.py --res 192 --c 24 --final
python _easy_claude_work/elements/e4_export.py            # -> js/spb-elements-model.js
node   _easy_claude_work/elements/e6_eval.js holdout      # honest ONLY with a model trained without the holdout (the shipped --final model saw every paint: 0.88 / 0.69 / 0.81 = contaminated)
node   _easy_claude_work/elements/e10_conf.js             # same caveat; on real paints use elements/lab/summary.json
```
Real-app checks: `pw/t259_elem_policy.py "<folder>"` (ask-first / teach / none), `pw/t258_overlay.py`, `pw/t260_same_car_places.py`; AI-through-MCP: start `pw/aibridge.py`, drive with `pw/br.py`.

## 2026-10-03 afternoon sprint - what changed (details: `docs/handoff_reports/`)
- **Segmentation (WP2):** a glyph is now EVERYTHING inside the box that is not a ring/background colour (outline + fill + shading), rim rule, low-contrast fallback to the old one-colour rule, per-box reply (`pixels_selected`, `share_of_box_pct`, `colours_used`, `touched_rim_px`, `low_contrast`), `maybe_more` candidates (an assist to LOOK at, 1 of 8 was a real number). Blind replay (30 PSD-truth paints, same AI boxes): mean IoU 0.457 -> 0.745, places 60 -> 103/108, no paint worse (in-sample). Real TGAs (WP3, 15 unseen cars): 33/53 places clean, 13 partial, 4 failed; "leave the numbers alone" 12/15.
- **Modes (WP5):** `mark_elements {mode: "glyph" | "colour_in_region" | "logo", colour, spread, lettering}` - stripes = a colour flooded inside/through the box with caps (12% sheet per box, 25% per call, 4x growth, 1.6x thickness), logos = everything that is not the ring colour (plate included unless `lettering:true`); `refinish` passes `mark_mode` / `mark_colour` / `spread`. Stripes blind test (12 truth paints): IoU 0.31 / precision 0.32 / places 46% - misses are mostly the reader calling banners "stripes"; where boxes matched the tape layer the tool scored 0.83-0.96.
- **Ask-first for the online tier (WP12):** `refinish` with a numbers / sponsors / stripes TARGET on a flat paint returns `needs_confirmation` and shows the card; an `exclude` never asks; `mark_elements {none:true}` records "there are none on this paint"; "by eye" / counts removed from tool replies.
- **Fixes from the real-TGA battery:** per-number fill colour (a plate behind the digits is never the fill), a stripes zone is placed below an existing numbers zone, stripe core colour over the AA fringe, textured-body guard.
- Replays: `pw/blind_replay.py run` (numbers), `pw/blind.py --kind stripes` (stripes), `pw/t259_elem_policy.py arcachevy25` (11/11), `elements_modes_test.js` (14/14 synthetic).

