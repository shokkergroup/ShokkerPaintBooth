# Car learning - how the copilot learns where every car's parts are (SPB-AI, 2026-10-02)

**Why:** the paint is ONE flat sheet of islands; the copilot can only say "the hood" if it knows which islands are the hood *on this car*. Vision cannot read the flat sheet (measured 9/22), so the parts come from (1) the shipped library, (2) what buyers teach / confirm, (3) ground truth from the iRacing 3D viewer.

## The ladder (what happens when you ask for "the hood")
1. Layout / iRacing-folder match in `SPB_CAR_ATLAS` (`js/spb-car-atlas-data.js`: 31 cars) or in the learned store -> parts known, apply.
2. Not known, but the sheet is >= 78% like a known car (`SpbProCar.near`) -> **proposal**: that car's boxes snapped to THIS car's islands, drawn as a labelled picture, one click Yes (`adoptNear`). Never applied silently.
3. Nothing close -> the draw-the-parts picker (teach flow).
Every Yes / teach is POSTed to `/api/ai/learned-cars` (`%APPDATA%\ShokkerPaintBooth\ai\learned_cars.json`; `SPB_AI_DIR` / `SPB_LEARNED_CARS` override) and recognised next time.

## Shipping what was learned to every buyer
```bash
python scripts/ai_atlas/merge_learned_cars.py            # taught + viewer layouts only (look-alike guesses stay local; --min-quality 1 ships them)
python scripts/ai_atlas/merge_learned_cars.py --report   # what is in scripts/ai_atlas/car_atlas_learned.json
```
It rebuilds `js/spb-car-atlas-data.js` (bump its `?v=` token in `paint-booth-v2.html`, then sync root -> `electron-app/server/`).

## Ground truth from the iRacing 3D viewer (needs the owner at the machine)
1. In the app (car loaded): `pw/t230_calsheet.py <tag>` -> `_easy_claude_work/viewer_cal/<tag>_sheet.png` + `<tag>_legend.json` (every big island its own flat colour; pass `page` 1, 2 ... for the small islands).
2. `python scripts/ai_atlas/viewer_session.py prepare --folder "trucks ram2026" --png <sheet.png>` - moves the car's own `car_<id>.tga`, `car_num_`, `car_spec_` into `_spb_viewer_backup/<stamp>/` and writes the colour code. **Nothing is deleted.**
3. Owner launches iRacing, logs in (an agent never types credentials), opens the paint viewer, reloads the paint; screenshots from several sides; read off `{"orange": "hood", "blue": ["left side"]}`.
4. `viewer_session.py learn --legend <legend.json> --findings findings.json --folder "trucks ram2026"` -> one box per part (union of its islands), source `viewer` (best quality).
5. `viewer_session.py restore --folder "trucks ram2026"` - the real paint is back.
`viewer_session.py` is unit-tested on a scratch folder only; it has not been driven against the real iRacing viewer yet.

## Learning from the paint corpus (owner: "thousands of TGAs in my iRacing folders - train from them")
`_easy_claude_work/corpus/` (derived data stays in `corpus/cache`, never ships - the paints are other drivers' artwork; only fingerprints and boxes leave).
1. `s0_inventory.py` (headers only) -> 180 folders, 2,929 `car_*.tga` + 1,858 `car_num_*.tga` (skewed: ~25 folders have >= 20 paints, ~100 have none). `s1_aggregate.py` caches every paint (minus the owner's id) at 256x256.
2. **Dead space is the template's own brown (84,68,68)** (tan (116,100,84) on a few): `s2_layout.py` reads it from the per-pixel MODAL colour, p_dead < 0.12 = paintable. The footprint fingerprints match the PSD-derived library at 0.89-0.96 for 12 families -> `s7_folder_overlay.py` wrote `scripts/ai_atlas/car_atlas_folders.json` (folder keys + corpus fingerprints for 15 library cars; `build_car_atlas.py` merges it).
3. **Edge-frequency maps** (`s2b_edges.py`: fraction of paints with a strong edge at each pixel) redraw the template's panel outlines crisply, including seams between touching panels -> `corpus_lib.islands_walled` = PSD-free island segmentation (21 islands on a winged sprint car, 26 on a dirt modified).
4. **The convention is real** (`s5_loo.py`, 13 labelled families): every iRacing stock-car-style sheet puts front bumper top-left, rear bumper beside it, spoiler far right, RIGHT side = the upper long band, LEFT side = the lower band, trunk | roof | hood across the middle. Median-box prediction from the other cars alone gives median IoU 0.81 on the big four panels (45/52 >= 0.6); snapping to corpus islands did NOT improve it (0.76).
5. `s8_calsheets.py` makes PSD-free calibration sheets (14 colours per page + legend) for every folder without a close library match: the iRacing viewer loop above works for a car even when nobody owns its PSD (sprint cars, modifieds, legends, ...).

### Measured results (read these before trusting a "reader" or a prior)
- Folder keys + corpus fingerprints: 15 library cars (`car_atlas_folders.json`). A real sprint paint loaded flat matches the corpus fingerprint at 0.98, so these fingerprints do recognise real sheets.
- **Dirt late model**: the library entry was `folder_only`, and `atlasMatch` only accepts a folder-only car when the sheet's fingerprint is unusable - the DLM's is usable (85% paintable), so the DLM was never recognised. Fixed by giving it fingerprints (PSD route and app route differ: 0.73).
- Blind reading of evidence sheets (`s4_evidence.py` -> a fresh model -> `s6_score_blind.py`): 13 stock-car families, big-4 panels median IoU 0.78 (47/52 >= 0.6), left/right never swapped, confidence monotone (5 -> 0.90, 2 -> 0.62); the arrangement prior alone: 0.81 (45/52). On the DLM (different layout): side panels found, hood 0.61, roof / spoiler / nose wrong, left/right swapped. => the reader adds nothing in-family and is unsafe out-of-family.

### Recognising a car from a finished paint (`js/spb-car-edge.js`)
Why: `s9_coverage.py` - 71% of 4,661 real paints have no template dead space left, so the layout fingerprint reads ~38% of them. What every paint of one car still shares is where the panel outlines are.
How: `s14_export_edge.py` -> `js/spb-car-edge-data.js` (per iRacing folder: P(edge) on a 64x64 grid from ALL its paints, per-car impostor mean/sd). The page computes the paint's own Sobel edges at 256x256 (successive halving, threshold 20), pools to 64x64, scores every folder by naive-Bayes log-likelihood minus a generic null, Z-normalises per car, best z >= 4 = recognised.
Measured (`s15_znorm.py`, fit on half / test on the other half, 50 folders, 2,295 paints): right family on top 95.3% (raw, un-normalised 90.2%: hub fingerprints); z >= 4 accepts 87.1% (85.1% right family) of known cars' paints and 10.2% of paints of cars the model never saw (the whole family left out). Twin folders (same UV, e.g. dirtlatemodel 350/358, skmodified/tour) count as one family. JS vs Python on real paints: 119/121 same winner, median score gap 0.003 (`pw/t237_edge_parity.py`).
Use in the app: ONLY when the layout fingerprint is unreadable. A recognised library car is a confirm-first proposal ("the panel outlines in your paint look like the ... sheet") unless the iRacing folder box agrees, the car was taught here, or the buyer confirmed it once (`spb_rec_confirm_v1`). A usable layout fingerprint always decides alone: the RAM (88% like the Silverado) must stay a proposal / its own car. Teach-once works for cars with no library entry (`pw/t239_rec_learn.py`: sprint car taught on one paint, a different paint recognised).
Trap: `scipy.ndimage.sobel` on a stack of images also smooths ACROSS the stack axis (it blends neighbouring paints): use `corpus_lib.sobel_mag`. A first set of numbers was measured that way and discarded.

### Honest coverage and the owner labelling page
`docs/CAR_COVERAGE.md` lists every car folder with its status (generated by `corpus/s19_coverage_report.py`): 23 PARTS KNOWN (61% of paints), 32 RECOGNISED BUT PARTS UNKNOWN, 52 FEW PAINTS, 73 NOTHING. The fastest way to move cars from the second group to the first is the owner's own eyes: `_easy_claude_work/labeler/index.html` (README.txt next to it) -> Export -> `python scripts/ai_atlas/apply_owner_labels.py spb_car_labels.json`. The iRacing viewer (below) then only has to VERIFY.
Panel maps: `js/spb-car-islands-data.js` gives a no-evidence paint of a recognised car its islands and footprint (`finishFromTemplate` in carmap); regenerate with `corpus/s17_export_islands.py`.
Out-of-sample reality check (`corpus/s16_owner_check.py`, the owner's own Shokker-made paints): z >= 4 accepts 57%, 90% of those right; paints of folders the model does not know are accepted 26% of the time (several are same-template cousins). Treat every recognition as a proposal.

### Draft parts from the owner's own templates (`corpus/claude_suggestions.json`)
The owner keeps hundreds of template / livery PSDs. Official templates carry guide layers (Number Blocks, Sponsor Blocks, Number Locations ...); designers' finished liveries carry named layers (Numbers, Side Colors, tub, Nerf Bars ...) that sit on the real panels. `s21_psd_match.py` extracts them (Mask / Wire / number / sponsor at 256x256), `s22` / `s24` match PSDs to car folders (footprint IoU is reliable on sparse sheets only; dense sheets: look at the overlay), `s26_overlays.py "folder::psd.psd"` draws them over the corpus panels with a percent grid (`SPB_WALL_THR=0.12` splits touching panels better). Boxes are then read off and written into `claude_suggestions.json` (tier T1 = guide block inside an unmistakable silhouette, T2 = plausible; `lr: conv` = left/right by the upper = right convention). `scripts/ai_atlas/apply_suggestions.py` ships them as `guess: true` entries: confirm-first picture until a buyer confirms once. The labeler page shows them as dashed boxes. NOT 3D-verified.
Families done: UMP modified, Pro 4, Pro 2 Lite, Legends '34, SK modified (+ tour), dirt modified 358 (+ big block), dirt sprint (305/360/410). Next candidates need a matching template with guides: street stock, silver crown, dirt midget, formula cars.

## Known gaps
- Dirt sprint cars, modifieds, legends, pro trucks, UMP, formula / sports cars (every folder in `viewer_cal/PLAN.md`) have no entry: they use ask / teach until someone runs the iRacing viewer step.
- A proposal is a guess from a look-alike. Parts covered by decal artwork may look unchanged after a recolour (the zone repaints body-paint layers only).
- Learned layouts stay on one machine until merged (above); uploading them from buyers is an open owner decision (see the wiki Known Trouble Spots).

## Tests
`_easy_claude_work/pw/t225_ram_flow.py <tag>` (ask -> Use -> proposal -> Yes -> apply -> learned), `t227_masks.py` (every part selects pixels), `t229_twocolours.py`, `t230_calsheet.py`; `_easy_claude_work/test_learned_server.py` (server store). Test server: `SHOKKER_PORT=59879 SPB_LEARNED_CARS=<scratch> python server_v5.py` - never the owner's port 59876.
