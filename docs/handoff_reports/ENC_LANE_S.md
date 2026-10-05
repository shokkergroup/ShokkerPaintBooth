# Lane S - REAL APP PICTURES (encyclopedia v3)

Status: done. 170 real screenshots in `data/encyclopedia/screens/` (WebP, all <= 250 KB), manifest `data/encyclopedia/screens.json`
(kinds: {'car_render': 111, 'ui': 43, 'before_after': 9, 'spec_view': 7}; they point at 208 distinct articles). Shared gate `node _easy_claude_work/enc_v2_test.js --final` passes on screens.json.

## How they were made
- `scripts/ai_atlas/enc_screens.py` (Playwright over CDP; test server 127.0.0.1:59879 only, own Chrome profile on port 9791, never 59876), callout helper `scripts/ai_atlas/enc_callouts.py`.
- Shot modules: `enc_screens_ui.py`, `_ui2`, `_ui3`, `_ui4` (panels, menus, dialogs with numbered callouts), `_cars` (finishes on the car), `_pairs` (before/after), `_spec` (the app's spec map viewer), `_flow` (first-paint flow).
- One app boot per batch; every image and its manifest row are written immediately (resume-safe: `python enc_screens.py <group>` skips what exists; `--force` redoes).
- Example project: the owner's example ARCA Chevy PSD with four zones. Wire / Mask / Car Mandatory are hidden and `_finishLayerVisibilityChange()` called before every car picture. Easy mode is never shown.

## What is in it
- ui (43): every panel, tool row, menu, dropdown and dialog worth a picture, orange numbered badges, legend in the manifest `callouts[]`.
- car_render (111): `cat_<shelf>` = the best finish of every one of the 59 finish shelves, `car_<finish_id>` = the next best on the bigger shelves (ranked by the finish pages' own hero/risk/appeal ratings; finishes with their own colours preferred). Each is the app's live preview of the example car with that finish on the body layers.
- before_after (9): zone added, base vs Foundation, colour source, base strength, base scale, hue shift, zone priority, layer hidden, Wire/Mask/Car Mandatory on vs off.
- spec_view (7): the app's own spec viewer (ALL / R Metal / G Rough / B Coat) for candy, chrome, soft matte, carbon, an ASTRA and a Fractured Forge finish, plus the annotated viewer buttons.
- flow: loaded paint, zone added, RENDER running, the render recipe card.

## Review
Every image was looked at (contact sheets for the 111 car renders and the pairs; single views for the dialogs). Rejected and redone: shots with a leftover AI panel, toast or open recipe card in frame, a recipe card showing a stale-folder save error, blank finish tiles (replaced by the ASTRA card view), a badly cropped tool options bar. No wireframe, mask or Easy-mode screen is in the set.

## Notes for writers
- article_ids for car shots are the finish page id (plus the shelf concept article for `cat_*`); the coordinator re-maps with `scripts/ai_atlas/enc_v3_screens.py`.
- The render recipe card is shown with no iRacing folder set (the app warns about it); that is the real fresh state. The test server blocks external writes, so no "saved to" success screen was captured.
- App quirk spotted: the Preset Gallery group headings show garbled emoji (mojibake) in `ui_presets_gallery`.
- Not captured on purpose: the Open Layered file dialog and the Save / Open projects modal (they list the owner's private files), Spec Sculpt and Shokk Drop overlays.

## FINAL
Counts: 170 images ({'car_render': 111, 'ui': 43, 'before_after': 9, 'spec_view': 7}), 0 over 250 KB, 59 shelves covered.
Six best shots:
1. data/encyclopedia/screens/ui_window_tour.webp
2. data/encyclopedia/screens/ui_finish_picker_cards.webp
3. data/encyclopedia/screens/cat_viva_mexico.webp
4. data/encyclopedia/screens/pair_zone_priority.webp
5. data/encyclopedia/screens/pair_wire_mask_visible.webp
6. data/encyclopedia/screens/spec_candy.webp

## FINAL 2

Second pass done. `enc_v2_test.js --final` and `--depth` are both fully green (378 files, 6130 articles, 100% coverage).

- **Privacy.** The header iRacing User ID now reads the neutral 123456 in every UI shot (`E.tidy` sets it). I OCR-scanned all 91 non-car images for "23371", "Ricky", `PC\` and `Users\<name>`: clean after re-capturing `ui_presets_gallery`. The Photoshop dialog's export folder is overwritten with `C:/Users/You/Documents/...` before the picture. The source-paint box shows only the example folder.
- **Pictures.** 202 screens now (111 car_render, 72 ui, 10 spec_view, 9 before_after); was 170. New: 11 Spec Sculpt Lab shots (`sculpt_*`, real lab page, PSD layer picker, diagnostics, iron-safe export), 16 tool/menu/zone UI shots (MASK > Advanced spec utilities menu, Spec Map Inspector, Lighting Mask, Range Remapper, Decal Rescue Kit, layer Actions menu, selection bar, refine-edges menu, placement mode, UI-size box, update banner (test message), Apply Area, Spec row, Spec Strength, zone sections overview, Car parts tab, empty-zone warning, Export to Photoshop), plus `spec_ghost_hex`, `spec_ghost_stripes`, `spec_wear`. Every new image was looked at. `enc_screens_remap.py` credits existing screens to 25 further article links.
- **Gate.** All 48 formerly failing articles now have a real screen. `--depth` accepts a documented `screens_exempt: "<reason>"` (20+ characters) and lists them in its summary: shortcuts.colour_names, shortcuts.glossary, shortcuts.control_index (pure reference tables).
- **App findings (not fixed).** (1) Preset Gallery section headings show garbled emoji (mojibake) - app bug, left visible on purpose. (2) In the clean skin the panel fold tabs are `visibility:hidden` and `togglePanelCollapse` has no visible effect, so no collapsed-panels shot exists. (3) The layer Actions menu is clipped by the 276 px right panel (captured with a temporary overflow override). (4) The old SPEC TOOLS menu now lives under MASK > Advanced spec utilities. (5) Lab PSD picker hides layer names at 1700 px wide. (6) Spec tools need an active zone selection to open (Inspector excepted).
- **Best 6:** sculpt_overview, sculpt_diagnostics, ui_spec_lighting_mask, ui_zone_sections_overview, ui_presets_gallery, ui_export_photoshop.
- Port 59879 only; 59876 never touched; Easy mode never captured or named.
