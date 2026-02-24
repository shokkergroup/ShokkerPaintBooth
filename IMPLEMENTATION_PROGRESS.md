# Shokker Engine v3.0 PRO — Implementation Progress

## Status: PHASES 1-6 COMPLETE + EXPANSION PACK (10 features + 25 new finishes = 576+ combos) — Full Premium Product

## Plan File
`C:\Users\Ricky's PC\.claude\plans\refactored-sparking-raven.md`

## What's Done

### Phase 1: Engine Core (COMPLETE + v3.0 AUDIT FIX)
All changes in `shokker_engine_v2.py`:

- **Phase 1a**: Created `BASE_REGISTRY` (12 bases), `PATTERN_REGISTRY` (18 patterns including "none"), `MONOLITHIC_REGISTRY` (5 specials)
- **Phase 1b**: 17 `texture_*` functions extracted from existing `spec_*` functions
- **Phase 1c**: `compose_finish()` and `compose_paint_mod()` — compositing engine
- **Phase 1d**: Updated `build_multi_zone()` dispatch — 3 paths: compositing, monolithic, legacy
- **Phase 1e**: All tests pass — 216 combinations verified

#### v3.0 Audit Fix (Feb 2026)
Deep audit found fundamental flaws in the original compositing approach:

**Problems found:**
1. All 17 texture functions used ADDITIVE DELTAS calibrated to phantom bases that didn't exist in BASE_REGISTRY — every combination produced wrong M/R values
2. Carbon fiber incorrectly modulated Metallic channel (original only modulates Roughness)
3. Brush grain direction was transposed 90° (vertical instead of horizontal)
4. compose_paint_mod applied 0.7x to base even when pattern="none"
5. Zero of 18 texture extractions could reproduce their original monolithic finish

**Fix applied — MODULATION approach:**
- Texture functions now return `{pattern_val, R_range, M_range, CC}` — a spatial shape (0-1) plus how much M/R should vary
- compose_finish() applies: `base_R + pattern_val * R_range * sm`
- Base determines the CHARACTER (chrome stays chrome, matte stays matte)
- Pattern adds TEXTURE on top (weave, dimples, bolts, etc.)
- Example: Chrome+Carbon = M=255 (chrome), R=2-52 (weave adds roughness)
- Example: Matte+Carbon = M=0 (matte), R=215-255 (weave adds roughness)
- Brush grain fixed to horizontal (columns vary, rows constant)
- compose_paint_mod runs base at 1.0x when pattern="none", 0.7x when pattern exists

### Phase 2: Server (COMPLETE)
Rewrote `server.py` with:

- `GET /status` — capabilities (base list, pattern list, combo count) + config
- `POST /render` — JSON body with local file paths, no upload needed
- `GET /preview/<job_id>/<filename>` — serve PNGs to browser
- `GET /download/<job_id>/<filename>` — download TGAs
- `POST /config` + `GET /config` — iRacing Live Link config
- **iRacing Live Link**: Copies output to iRacing paint folder, backs up originals
- Legacy `/apply-finish` endpoint preserved
- Flask + flask-cors installed

### Phase 3: UI (COMPLETE)
Changes in `paint-booth-v2.html`:

- Title, header, CSS for v3.0 PRO branding
- BASES/PATTERNS/MONOLITHICS arrays replacing old FINISHES
- Zone card: two dropdowns (Base + Pattern) with monolithic optgroup
- Tabbed finish library (Bases / Patterns / Specials)
- ShokkerAPI module (fetch /status, /render, /config, auto-poll)
- RENDER button with shimmer animation + progress bar
- Dual render results panel (paint + spec preview side by side)
- Bottom eyedropper bar: BASE + PAT dropdowns (not just FINISH)
- iRacing Folder button next to Save To field
- generateScript() and generateFullPythonScript() emit base+pattern keys
- Presets updated to base+pattern format
- Zone init defaults with base/pattern fields

### Phase 4: Premium Polish (COMPLETE)
- Combination hints in zone cards (12 hints)
- Randomize/Explore buttons
- Keyboard shortcuts (Ctrl+R render, Ctrl+G generate, 1-9 zone select, R randomize)
- Error panel replacing alerts

### Phase 5: Premium Features — Helmet, Suit, Wear, Export (COMPLETE)

#### Engine (`shokker_engine_v2.py`):
- `_parse_intensity()` — helper to parse intensity string to (spec_mult, paint_mult, bright_boost)
- `_build_color_mask()` — helper to build zone mask from color description
- `build_helmet_spec()` — generates helmet spec map matching car finish zones
- `build_suit_spec()` — generates suit spec map matching car finish zones
- `build_matching_set()` — one-call car + helmet + suit generation
- `apply_wear(spec_map, paint_rgb, wear_level, seed)` — 0-100 wear slider with:
  - Micro-scratches (directional horizontal noise)
  - Clearcoat degradation (multi-scale noise)
  - Paint fading/chips at wear>20
  - Edge wear at color boundaries at wear>30
  - Helmet gets 20% less wear, suit 40% less
- `build_export_package()` — ZIP with all TGAs, PNGs, config JSON, README
- `full_render_pipeline()` — ultimate one-call: car + helmet + suit + wear + export

#### Server (`server.py`):
- `/render` now accepts: `helmet_paint_file`, `suit_paint_file`, `wear_level` (0-100), `export_zip` (bool)
- Uses `full_render_pipeline()` instead of `build_multi_zone()` when extras present
- Live Link pushes helmet + suit files alongside car files
- `/status` advertises helmet_spec, suit_spec, wear_slider, export_zip, matching_set features
- Export ZIP download URL returned when export_zip=true

#### UI (`paint-booth-v2.html`):
- New "Extras" section in Car Info: Helmet path, Suit path, Wear slider, Export ZIP checkbox
- Helmet/Suit Browse buttons with auto-path building from car paint directory
- Wear slider (0-100) with live description text (Factory New => Destroyed)
- Export ZIP checkbox
- Render results panel shows: helmet spec preview, suit spec preview, wear badge, ZIP download link
- `doRender()` gathers extras and passes to server
- `ShokkerAPI.render()` accepts extras parameter
- `showRenderResults()` displays helmet/suit previews, wear badge, ZIP link
- `getConfig()` / `loadConfigFromObj()` save/restore helmet, suit, wear, export settings
- `generateScript()` / `generateFullPythonScript()` emit full_render_pipeline when extras used

### Phase 6: Full Feature Expansion — 10 Premium Features (COMPLETE)

#### Batch 1: Pure UI Features (paint-booth-v2.html only)

**Feature 1: Before/After Visual Comparison**
- "Compare" button in canvas toolbar, visible after render completes
- Draggable vertical divider: original paint on left, rendered on right
- `toggleCompareMode()`, `drawCompareView()`, drag handlers
- Escape key exits compare mode

**Feature 2: Preset Gallery with Thumbnails**
- Visual card gallery modal replaces dropdown preset selector
- "Presets" button opens modal; cards show name, description, swatch dots
- Swatch dots use base material's color with pattern stripe indicator
- `openPresetGallery()`, `closePresetGallery()`, `renderPresetGalleryCards()`

**Feature 3: Randomize with Style Lock**
- Lock icons on Base, Pattern, Intensity dropdowns per zone
- `lockBase`, `lockPattern`, `lockIntensity`, `lockColor` zone properties
- `GOOD_COMBOS` (38 curated), `BAD_COMBOS` (8 exclusions) for smart mode
- Smart checkbox: 80% pick good combos, 20% random excluding bad combos

**Feature 4: Zone Templates (Save/Load Layouts)**
- Save/Load zone layouts to localStorage (separate from presets)
- Templates preserve layout (names, colors, modes) without finish assignments
- `saveZoneTemplate()`, `loadZoneTemplate()`, `deleteZoneTemplate()`
- Delete via dropdown with `__delete__:` prefix

**Feature 5: Color Harmony Suggestions**
- Harmony panel below color selector in selected zone card
- Shows complementary, analogous, triadic, split-complementary swatches
- Mini SVG color wheel with dots at harmony positions
- Clickable chips apply harmony color to next zone
- `hexToHSL()`, `hslToHex()`, `getHarmonies()`, `applyHarmonyColor()`

#### Batch 2: Engine + UI Features

**Feature 6: Intensity Curve Editor**
- 3 inline sliders per zone: Spec (0-2.5), Paint (0-2.0), Bright (0-0.20)
- Quick-fill dropdown still available (Subtle/Medium/Aggressive/Extreme + Custom)
- `INTENSITY_VALUES` lookup mirrors engine's INTENSITY dict
- `setCustomIntensity()`, `toggleIntensitySliders()` functions
- Engine: `build_multi_zone()` checks `zone.get("custom_intensity")` before preset lookup
- Server: passthrough (zones passed as-is)

**Feature 7: Day/Night Dual Spec Maps**
- Engine: `generate_night_variant(day_spec, night_boost)` — Metallic boost, Roughness reduction, Clearcoat push
- `full_render_pipeline()` accepts `dual_spec=False, night_boost=0.7`
- Night spec saved as `car_spec_night_{id}.tga` + `PREVIEW_spec_night.png`
- Server: accepts `dual_spec` and `night_boost` in `/render`
- UI: "Day/Night Dual Spec" checkbox + "Night Boost" slider (0-1.0) in extras
- Render results show night spec preview

**Feature 8: Zone Gradient/Fade Tool**
- Engine: `generate_gradient_mask(h, w, direction, center, start_pct, end_pct)` — linear/vertical/radial/diagonal
- UI: "Grad" button in canvas toolbar alongside Brush/Rect/Erase/Wand
- Gradient type dropdown (Linear/Radial) visible when gradient tool selected
- Click-drag defines gradient start/end points with live preview (dashed line + dots)
- `applyGradientMask()` uses dithered probability for smooth fade
- Auto-assigns inverse mask to next zone for clean two-zone transitions

#### Batch 3: Large Multi-Job Features

**Feature 9: Multi-Car Fleet Mode**
- "Fleet Mode" toggle button in action bar
- Fleet panel with car entries: name, paint path, iRacing ID per car
- `doFleetRender()`: loops through cars, sequential API calls
- Progress: "Rendering car 2/5: Car Name..."
- Results grid shows all cars' previews after fleet render

**Feature 10: Batch Season Mode**
- "Season Mode" toggle button in action bar
- Season panel with race entries: name, wear level per race
- "Quick: Wear Ramp" button auto-fills 0-100% wear progression
- `doSeasonRender()`: sequential renders with per-race wear overrides
- Progress: "Rendering race 3/12: Talladega (wear 40%)..."
- Results grid shows all race previews with wear badges

### Post-Phase 6: Polish & Texture Fixes

#### Texture Scale Fixes (shokker_engine_v2.py)
- **Carbon Fiber**: `weave_size` 24→6 — tiny realistic weave (was way too big/pixelated)
- **Diamond Plate**: `diamond_size` 32→20 — tighter tread pattern
- **Dragon Scale**: `scale_size` 40→24 — more visible, tighter scales
- **Hex Mesh**: `hex_size` 24→16 — finer honeycomb mesh
- **Forged Carbon**: Chunk noise layers tightened (48→24, 24→12, 8→4 divisors)

#### Finish Library Visual Overhaul (paint-booth-v2.html)
- **Canvas-rendered pattern previews** replace flat color swatches in library list
- Each finish gets a 40×40 canvas with procedural pattern rendering
- **Enhanced hover popup** with 240×160 canvas preview showing actual pattern
- Preview cache system (`_previewCache`) prevents re-rendering on tab switch
- Client-side pattern renderers for all 18 bases, 32 patterns, 10 specials
- Helper functions: `_seededRng()`, `_hslToRgb()`, `_simpleNoise2D()`, `renderPatternPreview()`
- Updated channel hints to show accurate engine values (M/R/CC)

#### Expansion Pack: 25 New Finishes (shokker_engine_v2.py + paint-booth-v2.html)
**New Bases (6):** ceramic, satin_wrap, primer, gunmetal, copper, chameleon
**New Patterns (14):** pinstripe, camo, wood_grain, snake_skin, tire_tread, circuit_board, mosaic, lava_flow, rain_drop, barbed_wire, chainmail, brick, leopard, razor
**New Specials (5):** oil_slick, galaxy, rust, neon_glow, weathered_paint

- Engine: 25 new texture functions + 25 new paint modifier functions + 5 new spec functions
- All registered in BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY
- UI: All added to BASES, PATTERNS, MONOLITHICS arrays with swatch colors
- Client-side preview renderers for all 25 new finishes
- Channel hints updated for all 25 in hover popup
- **Total: 18 bases × 32 patterns = 576+ combinations + 10 specials**
- Carbon fiber paint modifier `weave_size` synced to 6 (was 24, mismatched with texture fix)

#### UI Improvements (paint-booth-v2.html)
- **iRacing Folder field**: Renamed from "Save To", with Browse button for folder picker
- **Auto-Save/Auto-Restore**: Debounced 500ms localStorage persistence, auto-restore on page load
- **ORIGINAL_ double-prefix fix**: Engine skips backup when filename already starts with ORIGINAL_

## Key File Locations
| File | Description |
|------|-------------|
| `E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\shokker_engine_v2.py` | Engine with modulation-based compositing |
| `E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\paint-booth-v2.html` | Paint Booth UI |
| `E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\server.py` | Flask server with Live Link |
| `E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\shokker_config.json` | User config (iRacing ID, car paths) |
| `E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\FINISH_AUDIT.md` | PBR audit results |

## Important Notes
- Python: Use `py -3` on Windows (NOT `python3`). NEVER add shebang lines.
- Paint modifier strength: Keep in 0.04-0.08 range (0.15 was too aggressive)
- iRacing PBR: R=Metallic, G=Roughness, B=Clearcoat(0-15=OFF,16=ON), A=SpecMask
- TGA: Paint=24-bit RGB (0x20), Spec=32-bit RGBA BGRA (0x28)
- Flask deps installed: flask 3.1.2, flask-cors
- User's iRacing ID: 23371
- Compositing: texture functions return {pattern_val, R_range, M_range, CC}
- compose_finish applies pattern as modulation ON TOP of base, not replacement

## If Starting a New Chat
Point Claude to this file:
```
Read this file first: E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\IMPLEMENTATION_PROGRESS.md
Then read the plan: C:\Users\Ricky's PC\.claude\plans\refactored-sparking-raven.md
```
