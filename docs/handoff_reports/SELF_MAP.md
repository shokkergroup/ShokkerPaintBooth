# SELF-MAP: the data for the self-understanding helper (2026-10-03)

Worker: SELF-MAP (Sonnet). Consumer: SELF-BRAIN. Everything below is generated or authored inside the lane; nothing else was touched.

## What exists (all published)

| Deliverable | File | Size |
|---|---|---|
| UI map | `scripts/ai_atlas/ui_map.json` (builder: `scripts/ai_atlas/build_ui_map.py`, run `python scripts/ai_atlas/build_ui_map.py`; `--md` keeps the old 07 card generator) | 534 items, 24 panel nodes, 3 mode nodes, 118 how-do-I index entries |
| Panel knowledge chunks | `docs/ai_knowledge/app_map.md` (generated from ui_map.json) | 55 chunks (one or more per panel, each under 1,400 chars) |
| How-do-I knowledge | `docs/ai_knowledge/how_do_i.md` | 118 entries, numbered steps with exact labels, each with a tag line `[hdi.id / mode / needs / ui ids]` plus an "Also asked as:" line fed from the stuck questions |
| Stuck-question corpus | `_easy_claude_work/stuck_questions.json` | 182 questions |
| Knowledge library | `js/spb-ai-knowledge.js` rebuilt with `python scripts/build_ai_knowledge.py` | 350 chunks total (55 app_map + 118 how_do_i from this lane), token `spb-ai-kb-20261003self5` |

## ui_map.json shape (for SELF-BRAIN)
`meta` (counts, schema, caveats) / `modes[3]` (pro, chat, easy) / `panels[24]` (id, label, mode, where, does, needs, items[]) / `items[534]` / `how_do_i[118]` (id, title, mode, needs, ui[], steps[]) / integrity lists (`unmatched_curation_keys`, `unknown_control_ids`, `dangling_related`, `how_do_i_dangling_ui`, all empty at publish).
Item fields: `id`, `label`, `mode`, `panel`, `where`, `kind`, `does`, `when`, `needs[]` (paint, psd, zone, parts, render, car_folder, none), `mistakes`, `related[]`, `help_text` (tooltip from the HTML), `control_id` (id in app_controls.json), `dom_id`, `source`, `curated`.
Id scheme: the DOM id when there is one, else `<panel>.<slug>`; controls built by JavaScript use `zone.*`, `layer.*`, `easy.*`, `ai.*`, `mcp.*`.

## Counts by kind (534 items)
button 323, slider 58, toggle 33, dropdown 32, text input 25, picker 16, number input 14, menu 8, section 12, panel 7, tab 2, search box 1, mode 3. Exact numbers are in `meta.counts` after each build.
By mode: pro 494, easy 30, pro+chat 9, chat 1 (the CHAT pill and the AI panel share the Pro screen).
Curated by hand (buyer-words does / when / needs / mistakes): 289 of 534. The rest are generated from the HTML tooltip (still real, labelled `curated:false`).

## How it was made (so it can be re-run)
1. Static DOM: `paint-booth-v2.html` parsed with html.parser (ids, labels, titles, aria-labels, onclick handlers, container ids mapped to panels).
2. Controls built by JavaScript (Pro zone editor, layer rows, Easy mode, AI panel) were read from the LIVE DOM on the test server (127.0.0.1:59879 via the CDP 9444 Chrome, read-only) and written as tables in the builder.
3. `app_controls.json` control ids are attached to zone controls (28 of its 35 are linked).
4. Buyer-words knowledge is hand-written in the builder's tables (CUR / ROWS_*), so editing the map = edit the tables in `build_ui_map.py`, rebuild, run `build_ai_knowledge.py`.

## Findings worth knowing (measured / read today)
- **EASY is live**, although the pill tooltip still says "(parked)". Easy = Tell-Shokker bar, SOURCE + LIVE PREVIEW, colour-parts rail ("YOUR CAR - BUILT FOR YOU"), part panel (COLOR REACH, Merge with, FINISH cards, ADJUST, COLOR, PUT IT ON), layer list, WHERE IT GOES, READY TO RACE checklist, SAVE TO iRACING.
- **No sort-by-colour in the Layers panel** (Smart Separate was withdrawn per the HTML comment). Answer "can I sort by colour" honestly: filter box by name only; colour work = Pro zone PICK COLOR FROM CAR, or Easy's colour parts.
- **No Text tool button** in the main tool row (text options exist but nothing opens them); the how-do-I says use a PNG layer or Photoshop.
- Dropping a picture on the canvas replaces the paint (already in the 07 card); "+ Layer" adds a logo.
- Solid colour on a brings-its-own-colours finish flattens it (measured earlier today, app_controls R2); the answer is Hue Shift. Written into `hdi.colour_not_applying` / `hdi.finish_colour` and the BASE COLOR row.
- CHAT mode in the pill is the Pro screen with the AI panel; the CHAT click did not change the stored mode in my test profile (it behaves as an AI panel opener).

## Coverage gaps (honest list)
- **Not captured**: the Spec Overlay picker popup contents and the pattern picker (opened from `SPBSpecOverlayPicker.open`), Preset Gallery cards, Spec Sculpt guided UI, Shokk Drop lab, Training Wheels quest text, the AI-panel gear drawer's inner fields (key, model, daily cap, bridge settings) beyond what the knowledge cards say, the render-history gallery, car-map tools, and the file-picker style setting (Shokker Browser vs Windows File Explorer, `mainFilePickerMode`).
- Zone controls `Intensity`, `Wear` and `Clearcoat Quality (legacy)` are in app_controls.json but were NOT present in the live zone panel dump; mapped as `zone.intensity` / `zone.wear` with a "not seen on 10.0.3" note; `zone_cc_quality`, `zone_spec_material_override_remap_lightingmask`, `zone_base_colour_strength` and `paint_global_base_color_depth_rule` have no UI row (no control to point at).
- 245 of 534 items are tooltip-only (labelled `curated:false`): mostly tool options (brush / clone / text / shape), dialog buttons and the finish-picker hashtag chips.
- Layer rows are curated from the titles in `paint-booth-3-canvas.js` (renderLayerPanel), not from a live PSD dump.
- `how_do_i` entries are written from the HTML / JS labels and the existing cards; none was click-tested end to end except the Easy and zone-panel labels read from the live DOM.
- Two traps for SELF-BRAIN: the Easy pill title says parked; the layers "zone icon" is described by its tooltip, not its glyph.

## Sync note
`node scripts/sync-runtime-copies.js --manifest _easy_claude_work/sync_mine.json --write` succeeded after each rebuild; the final `--check` reports no drift (an intermediate check showed drift in `js/spb-pro-rank.js`, another worker's file, since synced).
