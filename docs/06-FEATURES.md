# Shokker Paint Booth — Alpha Features (All 11 Complete)

## Feature #1: Pattern Rotation

**What it does:** Allows rotating pattern textures in increments on each zone.

**Implementation:**
- Each pattern stack layer has a `rotation` property (degrees)
- UI: Rotation input field per pattern layer in zone card and detail panel
- Engine: `compose_finish()` accepts `rotation` parameter
- Pattern texture is rotated before modulation with base spec values
- Rotation applies to the pattern's 2D noise/texture generation, not post-hoc image rotation

**Where in code:**
- HTML: Pattern stack controls in `renderZones()` (~line 5700–5800)
- Engine: `compose_finish()` rotation parameter and matrix transform logic

---

## Feature #2: Spec Map Import & Merge

**What it does:** Import an existing spec map TGA and merge/blend it with generated specs.

**Implementation:**
- File browse button for spec map import (UI)
- Server endpoint: `POST /upload-spec-map`
- Engine: `full_render_pipeline()` accepts `import_spec_map` parameter
- Merge logic: imported spec values blended with generated spec per-pixel
- Per-channel merge options available (blend, overlay, replace)

**Where in code:**
- HTML: Import spec map button and file browser in header area
- Server: `/upload-spec-map` endpoint (~line range in server.py)
- Engine: `import_spec_map` handling in `full_render_pipeline()`

---

## Feature #3: Spec Map Channel Visualizer

**What it does:** Shows individual M/R/CC/A channels as grayscale preview images, plus a PBR ball preview.

**Implementation:**
- Four grayscale channel previews (one per spec channel)
- PBR ball: 3D sphere rendered in Canvas using Blinn-Phong approximation
- Ball updates in real-time as zone spec values change
- Shows metallic reflection, roughness diffusion, clearcoat gloss
- Visualizer is in the right panel, below the finish library

**Where in code:**
- HTML: PBR visualizer rendering (~line 12800–12850)
- Channel preview rendering alongside spec map output in render results

---

## Feature #4: Randomize / Inspire Mode

**What it does:** Randomly assigns finishes, colors, and intensity to zones for creative inspiration.

**Implementation:**
- `R` keyboard shortcut randomizes selected zone
- `Ctrl+G` randomizes ALL zones
- Random selection from: bases, patterns, monolithics, colors, intensity presets
- Weighted toward interesting combinations (not pure uniform random)
- Avoids "muted" zones
- Can be applied to individual zones or globally

**Where in code:**
- HTML: Randomize logic in keyboard shortcut handler (~line 15900)
- Zone randomization function generates random base+pattern or monolithic + random color + random intensity

---

## Feature #5: Before/After Comparison

**What it does:** Side-by-side compare of original paint vs. rendered output with a draggable divider.

**Implementation:**
- Overlay mode activated after render completes
- Original paint on left, rendered result on right
- Vertical divider line that user drags horizontally
- Divider position controls clip mask on the overlay images
- Toggle on/off from render results panel

**Where in code:**
- HTML: Compare mode UI and divider handler (~lines 14400–14550)
- CSS: Compare overlay styles with clip-path or overflow hidden

---

## Feature #6: Real-Time Preview / WebSocket

**Status:** SKIPPED — Decided to use HTTP polling with debounce instead.

**What was planned:** WebSocket connection for instant preview updates.

**What was implemented instead:**
- HTTP-based preview with 300ms debounce (`triggerPreviewRender()`)
- Zone hash comparison to skip unchanged configs
- AbortController to cancel superseded preview requests
- Split-view pane with live preview panel

**Where in code:**
- HTML: `triggerPreviewRender()`, hash comparison, abort logic (~lines 9800–10100)
- Server: `POST /preview-render` endpoint

---

## Feature #7: Zone Linking / Groups

**What it does:** Link zones together so changes to one automatically apply to linked zones.

**Implementation:**
- Each zone has a `linked` property (index of zone to link to, or null)
- Link button (🔗) on each zone card
- When a zone is linked, changes to the source zone propagate to the linked zone
- Linked zones show a visual indicator (chain icon + source zone name)
- Useful for: matching left/right sides, sponsor consistency, etc.

**Where in code:**
- HTML: Link button handler in `renderZones()`, link propagation in zone change handlers
- Zone object: `linked` property

---

## Feature #8: Onboarding Tutorial

**What it does:** Step-by-step guided tour for new users.

**Implementation:**
- `TUTORIAL_STEPS` array defines 8 tutorial steps
- Each step: target element selector, title, description, position
- Spotlight effect highlights the target element
- Next/Skip buttons
- Auto-starts on first visit (checks `localStorage` flag)
- Can be manually triggered from settings menu

**Steps:**
1. Welcome / overview
2. Zone system explanation
3. Color selection
4. Finish library (bases)
5. Pattern selection
6. Canvas tools
7. Render button
8. Deploy to iRacing

**Where in code:**
- HTML: Tutorial system (~lines 16120–16252)
- `startTutorial()`, `showTutorialStep()`, `nextTutorialStep()`, `skipTutorial()`
- CSS: Tutorial overlay, spotlight, tooltip positioning

---

## Feature #9: Licensing & Activation

**What it does:** License key system for controlling access to renders.

**Implementation:**
- Key format: `SHOKKER-XXXX-XXXX-XXXX`
- Server endpoints: `GET /license`, `POST /license`, `POST /license/deactivate`
- Client-side: `checkLicenseStatus()`, `updateLicenseUI()`, `activateLicense()`, `deactivateLicense()`
- License gate on `/render` endpoint (server-side) — COMMENTED OUT for Alpha
- License gate in `doRender()` (client-side) — COMMENTED OUT for Alpha
- Status polling: `/status` endpoint returns license info, polled every 10s

**Current State:** Fully built but disabled. Both gates commented out so Alpha testers can render without a key.

**Where in code:**
- HTML: License UI and functions (~lines 16020–16120)
- Server: License endpoints and gate (~line 532 for render gate)

---

## Feature #10: Undo History Panel

**What it does:** Full undo/redo system for zone property changes with visual history panel.

**Implementation:**
- Two undo systems:
  1. **Region mask undo** (`undoStack`) — Brush stroke undo for canvas painting
  2. **Zone property undo** (`zoneUndoStack` / `zoneRedoStack`) — All zone config changes
- Max 50 zone undo states (`MAX_ZONE_UNDO = 50`)
- `pushZoneUndo()` captures full zone state snapshot
- `undoZoneChange()` / `redoZoneChange()` restore states
- `jumpToUndoState(index)` — jump to any point in history
- Visual panel shows timestamped history entries
- `formatTimeAgo()` for human-readable timestamps
- `Ctrl+Z` / `Ctrl+Y` keyboard shortcuts
- Panel toggle: `toggleUndoHistoryPanel()`
- Clear history: `clearUndoHistory()`

**Where in code:**
- HTML: Undo system (~lines 5150–5350)
- CSS: Undo history panel styles
- Keyboard handler integration (~line 15900)

---

## Feature #11: Offline Finish Catalog

**What it does:** Browse all 24,180+ finishes without server connection, using CSS-generated swatch previews.

**Implementation:**
- `renderPatternPreview()` function — ~50+ client-side Canvas texture generators
- Generates base previews (gloss, matte, chrome, candy, pearl, metallic, etc.) using gradients, noise, and procedural effects
- Generates pattern previews (carbon fiber, hex mesh, diamond plate, etc.) using Canvas drawing APIs
- Generates monolithic previews (chameleon, glitch, aurora, etc.) with animated-style static renders
- Uses seeded RNG and simplex noise (both implemented in JS)
- Finish browser modal: full catalog/list view with search, favorites, sorting
- Favorites persisted in localStorage
- Compare mode: side-by-side finish comparison
- Works completely offline — no server swatch endpoints needed
- Performance: lazy rendering, only generates visible swatches

**Client-Side Texture Generators Include:**
- Bases: Gloss (smooth gradient), Matte (noise texture), Chrome (mirror reflection sim), Candy (color-tinted clear), Pearl (iridescent shimmer), Metallic (sparkle noise), Carbon (weave pattern), Frozen (ice crystal noise), Blackout (near-black matte), Ceramic (smooth high-gloss), etc.
- Patterns: Carbon fiber (weave grid), Hex mesh (hexagonal grid), Diamond plate (raised diamonds), Chevron (V-pattern), Skull (yes, skull pattern), Damascus (wavy steel), Houndstooth (textile pattern), Circuit board (tech lines), etc.
- Monolithics: Chameleon (hue-shifting gradient), Glitch (digital artifacts), Aurora (flowing bands), Thermochromic (heat map), Holographic (rainbow diffraction), etc.

**Where in code:**
- HTML: `renderPatternPreview()` (~lines 10700–12200, ~1500 lines of Canvas generators)
- HTML: Finish browser modal and catalog logic (~lines 14550–14750)
- HTML: Finish compare modal
- HTML: Favorites system (localStorage)
- CSS: Catalog grid, list view, swatch card styles

## Feature Summary Table

| # | Feature | Status | Server | Client | Engine |
|---|---------|--------|--------|--------|--------|
| 1 | Pattern Rotation | ✅ Complete | — | renderZones() | compose_finish() |
| 2 | Spec Map Import & Merge | ✅ Complete | /upload-spec-map | File browse | full_render_pipeline() |
| 3 | Spec Map Channel Visualizer | ✅ Complete | — | PBR ball canvas | — |
| 4 | Randomize / Inspire | ✅ Complete | — | Keyboard R / Ctrl+G | — |
| 5 | Before/After Compare | ✅ Complete | — | Compare overlay | — |
| 6 | Real-Time Preview | ✅ HTTP (WS skipped) | /preview-render | Split view + debounce | preview_render() |
| 7 | Zone Linking | ✅ Complete | — | Link propagation | — |
| 8 | Onboarding Tutorial | ✅ Complete | — | 8-step tour | — |
| 9 | Licensing | ✅ Built, disabled | /license endpoints | License UI | — |
| 10 | Undo History | ✅ Complete | — | Undo panel + Ctrl+Z/Y | — |
| 11 | Offline Finish Catalog | ✅ Complete | — | 1500 lines of Canvas | — |
