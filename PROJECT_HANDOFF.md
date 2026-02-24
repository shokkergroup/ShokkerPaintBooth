# SHOKKER PAINT BOOTH — Complete Project Handoff Document

> **Purpose:** This document gives a new Claude session 100% of the context needed to continue development on the Shokker Paint Booth project. Read this FIRST before touching any code.

---

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [File Locations & Architecture](#2-file-locations--architecture)
3. [iRacing PBR Spec Map System](#3-iracing-pbr-spec-map-system)
4. [Engine Deep Dive (shokker_engine_v2.py)](#4-engine-deep-dive)
5. [Paint Booth UI Deep Dive (paint-booth-v2.html)](#5-paint-booth-ui-deep-dive)
6. [Server Deep Dive (server.py)](#6-server-deep-dive)
7. [The Finish System](#7-the-finish-system)
8. [Prizm v4 Color-Shift System](#8-prizm-v4-color-shift-system)
9. [Pattern-Over-Monolithic System](#9-pattern-over-monolithic-system)
10. [Canvas Pan/Zoom System](#10-canvas-panzoom-system)
11. [Critical Lessons & Gotchas](#11-critical-lessons--gotchas)
12. [Competitive Intelligence (Neonizm)](#12-competitive-intelligence)
13. [Current Status & Known Issues](#13-current-status--known-issues)
14. [Development Workflow](#14-development-workflow)

---

## 1. What This Project Is

**Shokker Paint Booth** is a desktop application for generating iRacing car PBR (Physically Based Rendering) spec maps and paint modifications. It's a **zone-based painting system** where the user:

1. Loads a car's paint TGA file
2. Defines zones on the car (hood, body, fenders, etc.) using color picking or brush tools
3. Assigns finishes to each zone (e.g., Chrome base + Carbon Fiber pattern)
4. Clicks RENDER → engine generates spec map + modified paint TGA
5. Files are deployed to iRacing via Live Link

**The user is Ricky ("DownNDirtyTN")** — iRacing ID 23371. He is not a programmer. He designs racing liveries.

**Stack:** Python engine + Flask server + Single-file HTML/JS/CSS frontend. No frameworks, no build system.

---

## 2. File Locations & Architecture

### Core Files (THE ONLY FILES YOU'LL USUALLY EDIT)

```
E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\
├── shokker_engine_v2.py     # ~6,845 lines — The brain. Finish registry, compositing, rendering
├── paint-booth-v2.html      # ~14,067 lines — The UI. Single-file SPA (CSS+HTML+JS)
├── server.py                # ~1,212 lines — Flask API bridge between UI and engine
├── shokker_config.json      # User config (iRacing ID, car paths, Live Link)
├── run_server.bat            # Server launcher
└── output/                   # Rendered job folders (job_{timestamp}_{id}/)
```

### Documentation Files

```
ShokkerEngine/
├── KNOWLEDGE_BASE.md         # 698 lines — iRacing PBR reference, finish algorithms, color-shift research
├── COLOR_SHIFT_GUIDE.md      # 558 lines — Deep dive on chameleon paint techniques
├── FINISH_AUDIT.md           # 292 lines — PBR compliance audit of all finishes
├── IMPLEMENTATION_PROGRESS.md # 247 lines — Phase-by-phase dev status
├── PROJECT_HANDOFF.md        # THIS FILE
├── ROADMAP.md                # 3-phase productization roadmap
└── TODO.md                   # Active task checklist
```

### Other Project Files

```
E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\
├── Driver Paints/            # Per-driver paint files (car_num/car_spec TGAs)
│   ├── MAD-SHOKK/            # Ricky's own paints
│   ├── Mike Adamson/          # Client
│   ├── Dillon Bryant/         # Client
│   └── ...
├── NEONIZM_BIBLE.md          # Competitive intelligence on Jesse Abraham (competitor)
├── PaintVault/               # Future: AI-powered paint analyzer (not yet integrated)
├── Big Show/                 # Historical client work archive (25 GB)
└── .claude/                  # Claude project settings
```

### Architecture Flow

```
┌──────────────────┐     HTTP/JSON      ┌──────────────┐     Python      ┌──────────────────┐
│  paint-booth-v2  │ ──────────────────▶ │   server.py  │ ──────────────▶ │ shokker_engine_v2│
│    .html         │ ◀────────────────── │  Flask:5000  │ ◀────────────── │     .py          │
│  (Browser UI)    │   base64 PNGs /     │              │  numpy arrays   │                  │
│                  │   job IDs / JSON     │              │  + TGA bytes    │                  │
└──────────────────┘                     └──────────────┘                 └──────────────────┘
                                              │
                                              │ File I/O
                                              ▼
                                    Documents/iRacing/paint/
                                    (Live Link deployment)
```

---

## 3. iRacing PBR Spec Map System

### Channel Definitions (32-bit RGBA TGA, 2048×2048)

| Channel | Property | Range | Notes |
|---------|----------|-------|-------|
| **R** | Metallic | 0–255 | 0=dielectric plastic, 255=full metal |
| **G** | Roughness | 0–255 | 0=mirror smooth, 255=completely matte |
| **B** | Clearcoat | 0–255 | **⚠️ INVERTED — see below** |
| **A** | SpecMask | 0–255 | 255=full specular, 0=masked out |

### ⚠️ CRITICAL: Clearcoat B Channel is INVERTED

**Changed in iRacing 2023 Season 1 (December 2022):**
- **B = 0–15:** Clearcoat DISABLED (pre-2023 behavior)
- **B = 16:** MAXIMUM clearcoat shine (shiniest possible)
- **B = 17–255:** Progressively DULLER clearcoat
- **B = 255:** Dullest — sun-baked junkyard look

This is the #1 gotcha. Many references and even the KNOWLEDGE_BASE.md was written before this was fully understood. Always remember: **B=16 is MAX, NOT B=255**.

### File Naming & Format

- **Paint TGA:** `car_num_{customerID}.tga` — 24-bit RGB, uncompressed, descriptor 0x20
- **Spec TGA:** `car_spec_{customerID}.tga` — 32-bit RGBA, BGRA byte order, descriptor 0x28
- **Both:** 2048×2048, top-left origin, uncompressed

### Metallic + Paint Color Interaction (PBR Physics)

```
F0 = mix(vec3(0.04), albedo_color, metalness)
```

- **Metallic=0 (plastic):** Paint drives diffuse; reflections are white/achromatic
- **Metallic=255 (metal):** Paint color BECOMES the reflection color; diffuse drops to ZERO
- **CRITICAL:** Dark paint + high metallic = VERY dark car (no diffuse, dark reflections)
- Chrome requires near-white paint (RGB ~240-255) to look like actual chrome

### What iRacing CANNOT Do

1. True thin-film interference / color-shifting shader
2. Anisotropic reflections
3. Subsurface scattering
4. Per-pixel normal/bump maps (all 4 spec channels spoken for)
5. User-controllable IOR
6. Independent reflection tint vs diffuse color

---

## 4. Engine Deep Dive (shokker_engine_v2.py)

**~6,845 lines.** This is the rendering brain.

### Major Sections (Line Ranges)

| Lines | Section | Description |
|-------|---------|-------------|
| 1-53 | Color zone docs | Explains color-based zone detection |
| 55-99 | Imports + TGA writers | `write_tga_32bit()`, `write_tga_24bit()` |
| 107-175 | Noise utilities | Perlin noise, multi-scale noise, HSV conversion |
| 183-188 | `INTENSITY` dict | subtle/medium/aggressive/extreme presets |
| 192-450 | Color analysis | `parse_color_selector()`, `build_zone_masks()` |
| 1196-2624 | Paint modifiers | 80+ `paint_*()` functions — modify RGB in-place |
| 2625-3120 | **Prizm v4 system** | Panel-aware color shift (THE breakthrough) |
| 3130-3390 | Spec generators | 60+ `spec_*()` functions — generate RGBA spec |
| 3400-4650 | Texture patterns | 55+ `texture_*()` functions — spatial patterns |
| 4718-4800 | `BASE_REGISTRY` | 55 base materials (dict) |
| 4803-4863 | `PATTERN_REGISTRY` | 55 patterns including "none" (dict) |
| 4866-4924 | `MONOLITHIC_REGISTRY` | 50 special finishes (dict) |
| 4929-5049 | `compose_finish()` | Main compositing: base + pattern → spec map |
| 5051-5100 | `compose_paint_mod()` | Paint-side compositing |
| 5100-5240 | Stacked patterns | `compose_finish_stacked()` for multi-pattern |
| 5248-5318 | Pattern overlays | `overlay_pattern_on_spec/paint()` for monolithics |
| 5325-5760 | `build_multi_zone()` | Core zone-based renderer (main entry point) |
| 5769-5930 | `preview_render()` | Fast 0.25x preview (~100-250ms) |
| 6092-6358 | Helmet/Suit | `build_helmet_spec()`, `build_suit_spec()` |
| 6360-6680 | `build_matching_set()` | Car + helmet + suit ensemble |
| 6686-6808 | `full_render_pipeline()` | Ultimate one-call: everything + wear + ZIP export |
| 6810-6845 | CLI entry | Example render for testing |

### Function Signatures

```python
# Spec functions: generate RGBA spec map
def spec_*(shape, mask, seed, sm) -> np.array(h, w, 4, uint8)

# Paint functions: modify RGB paint in-place
def paint_*(paint, shape, mask, seed, pm, bb) -> np.array(h, w, 3, float[0-1])
#   paint = float32 [0-1] range, NOT uint8!
#   pm = paint_modifier strength, bb = brightness_boost

# Texture functions: generate spatial pattern shape
def texture_*(shape, mask, seed, sm) -> dict {
    "pattern_val": array[0-1],   # spatial shape (modulates base)
    "R_range": float,            # roughness modulation range
    "M_range": float,            # metallic modulation range
    "CC": int or array,          # clearcoat override
}

# Compose: combines base + pattern into final spec
def compose_finish(base_id, pattern_id, shape, mask, seed, scale) -> np.array(h,w,4,uint8)
```

### Source File Protection (CRITICAL)

The engine saves output TGAs to the SAME directory as the source paint — **overwriting the original**. To prevent data loss:

1. First render: backs up source as `ORIGINAL_{filename}`
2. Subsequent renders: loads from `ORIGINAL_*` backup instead of the (now-modified) source
3. This prevents cumulative corruption from re-processing rendered files
4. `/reset-backup` endpoint deletes ORIGINAL_ files to force fresh backup

---

## 5. Paint Booth UI Deep Dive (paint-booth-v2.html)

**~14,067 lines.** Single-file SPA (CSS + HTML + JS). No frameworks.

### File Structure

| Lines | Section |
|-------|---------|
| 6-2677 | `<style>` — All CSS |
| 2678-3524 | HTML body — Layout structure |
| 3525-14056 | `<script>` — All JavaScript |

### CSS Architecture (Lines 6-2677)

**CSS Variables** (Line 7-22):
```css
:root {
    --bg-dark: #0a0a0a; --bg-card: #111118; --accent: #ff3366;
    --accent-blue: #3366ff; --text: #e0e0e0; --border: #2a2a38;
    --success: #00ff88; /* ... */
}
```

**Key CSS Classes:**
- `.header` (line 40) — Top toolbar bar
- `.zone-card` (line 417) — Individual zone in sidebar
- `.canvas-viewport` (line 1242) — Canvas scroll container (**NO flexbox — plain block**)
- `.split-pane` (line 1269) — Split view panes (**NO flexbox centering**)
- `.finish-library` (line 1543) — Finish list container
- `.finish-popup` (line 1643) — Hover preview tooltip
- `.modal-overlay` (line 1707) — Modal backdrop
- `.toast` (line 1964) — Notification popup

### HTML Structure (Lines 2678-3524)

```
body
├── .header                    # Top toolbar (driver, car, ID, source paint inputs)
│   ├── .header-brand          # Logo
│   ├── .header-fields         # Input fields
│   └── .header-right          # Gear icon → settings dropdown
│       └── #settingsDropdown  # Wear, Night, Live Link, Config
│
├── .main-container
│   ├── .left-panel            # Left sidebar
│   │   ├── #fleetPanel        # Fleet batch mode
│   │   ├── #seasonPanel       # Season batch mode
│   │   ├── .panel-mode-bar    # Specmap/Recolor toggle
│   │   ├── Workflow guide     # Collapsible steps
│   │   ├── #zoneList          # Zone cards
│   │   ├── Zone action buttons # Add/Clear/Rand/Templates
│   │   └── #decalPanel        # Decals & Numbers
│   │
│   ├── .center-panel          # Canvas area
│   │   ├── #canvasViewport    # Scrollable container
│   │   │   ├── #paintPreviewEmptyBig  # Empty state
│   │   │   └── #splitViewContainer
│   │   │       ├── #splitSource       # Left pane (source)
│   │   │       │   ├── #paintCanvas   # Main paint canvas
│   │   │       │   └── #regionCanvas  # Zone overlay (transparent)
│   │   │       └── #splitPreview      # Right pane (preview)
│   │   ├── #renderFloat       # Floating RENDER button
│   │   ├── #zoomControls      # Zoom toolbar (+/-/FIT/1:1/Compare/SPLIT)
│   │   └── #renderResultsPanel # Results after render
│   │
│   └── .right-panel           # Finish library
│       ├── .finish-search-bar # Search input
│       └── #finishLibrary     # Tabbed finish list (Bases/Patterns/Specials)
│
├── #finishPopup               # Floating tooltip preview (240x160 canvas)
├── #scriptModal               # Python script generator modal
└── (other modals)
```

### JavaScript Global State (Lines 3525+)

**Data Arrays** (Lines 3697-3896):
```javascript
const BASES = [...]           // 55 base materials: {id, name, desc, swatch}
const PATTERNS = [...]        // 55 patterns (inc. "none"): {id, name, desc, swatch}
const MONOLITHICS = [...]     // 50 monolithics: {id, name, desc, swatch}
```

**Core State** (Lines 4100-4147):
```javascript
let zones = [];               // Zone array — THE central state
let selectedZoneIndex = 0;    // Currently selected zone
let canvasMode = 'eyedropper'; // Tool mode
let isDrawing = false;        // Drawing in progress
let panelMode = 'specmap';    // 'specmap' | 'recolor'
let currentZoom = 1.0;        // Canvas zoom level
```

### Key Functions (with Line Numbers)

**Zone Management:**
- `renderZones()` — Line 4234 — Renders all zone cards to sidebar
- `selectZone(index)` — Line 4555 — Sets active zone
- `assignFinishToSelected(finishId)` — Line 5286 — Assigns finish to zone
- `zoneDragStart(e, index)` — Line 4608 — Zone reorder drag

**Canvas & Zoom:**
- `canvasZoom(action)` — Line 8525 — Zoom in/out/fit/100%
- `applyZoom()` — Line 8553 — Applies zoom transform
- `getScrollContainer()` — Line 8790 — Returns correct scroll element
- `startPan(e, viewport)` — Line 8794 — Initiates pan

**Canvas Tools:**
- `setupCanvasHandlers(canvas)` — Line 7260 — Mouse event setup
- `setCanvasMode(mode)` — Line 7462 — Sets tool mode + cursor
- `magicWandFill(...)` — Line 7804 — Flood fill similar colors
- `applyGradientMask(...)` — Line 7695 — Linear gradient mask
- `selectAllColor(...)` — Line 7890 — Select all matching colors
- `edgeDetectFill(...)` — Line 7916 — Edge-aware Sobel fill
- `renderRegionOverlay()` — Line 7522 — Draw zone overlays on regionCanvas

**Rendering:**
- `doRender()` — Line 11343 — Main render (async, sends to Flask)
- `renderFinishLibrary()` — Line 5336 — Renders finish library tabs
- `showFinishPopup(e, id)` — Line 10684 — Hover tooltip preview

**Persistence:**
- `autoSave()` — Line 6024 — Debounced localStorage save (300ms)
- `autoRestore()` — Line 6044 — Restore state on page load

**Other:**
- `randomizeAllZones()` — Line 12947 — Smart randomizer
- `toggleCompareMode()` — Line 12460 — Before/after slider

### Canvas Tool Modes

| Mode | Cursor | Action |
|------|--------|--------|
| `eyedropper` | crosshair | Click to pick color, auto-assign to zone |
| `brush` | cell | Drag to paint zone mask (circular brush) |
| `erase` | cell | Drag to erase zone mask |
| `rect` | crosshair | Drag rectangle selection |
| `wand` | crosshair | Click flood-fill similar colors |
| `gradient` | crosshair | Drag for linear gradient mask |
| `selectall` | crosshair | Click to select ALL matching colors globally |
| `edge` | crosshair | Click for Sobel edge-aware fill |

### Zone Mask System

Each zone has a `regionMask` — a `Uint8Array(canvas.width * canvas.height)`:
- Value 0 = not selected
- Value 1 = selected (or 0-255 for gradients)
- When rendering, masks are RLE-encoded and sent to server
- Server decodes to 2D numpy float32 array (0.0-1.0)

---

## 6. Server Deep Dive (server.py)

**~1,212 lines.** Flask server on localhost:5000.

### Key Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/` | Serves paint-booth-v2.html |
| GET | `/status` | Server heartbeat + engine capabilities |
| POST | `/render` | Full-res render (returns job_id) |
| POST | `/preview-render` | Low-res preview (returns base64 PNGs inline) |
| GET | `/preview/<job>/<file>` | Serve preview PNG |
| GET | `/download/<job>/<file>` | Download output TGA |
| GET | `/swatch/<base>/<pattern>` | 64x64 swatch thumbnail (disk-cached) |
| GET | `/swatch/mono/<finish>` | 64x64 monolithic swatch |
| POST | `/check-file` | Validate file path |
| POST | `/browse-files` | Filesystem browser (for file picker) |
| POST | `/preview-tga` | Convert TGA→PNG for browser display |
| GET | `/iracing-cars` | Discover car folders in iRacing dir |
| POST | `/deploy-to-iracing` | Copy TGAs to iRacing paint folder |
| POST | `/reset-backup` | Delete ORIGINAL_ backups |
| GET/POST | `/config` | Load/save user config |
| POST | `/cleanup` | Delete old render job folders |

### Zone Data Flow: UI → Server → Engine

**UI sends JSON:**
```json
{
  "zones": [
    {
      "name": "Body",
      "color": "blue",
      "base": "chrome",
      "pattern": "carbon_fiber",
      "scale": 1.5,
      "pattern_opacity": 0.8,
      "intensity": "aggressive",
      "region_mask": {"width": 2048, "height": 2048, "runs": [[255,100],[0,50],...]}
    }
  ]
}
```

**Server decodes RLE masks** into 2D numpy arrays, passes zone dicts to engine.

**Engine returns:** numpy arrays (paint RGB, spec RGBA) → server saves as TGAs + PNGs.

### Dependencies

- Flask 3.1.2, flask-cors
- Pillow (PIL), NumPy
- Python 3.13 at C:\Python313

---

## 7. The Finish System

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ COMPOSITING (3,025 combinations)                            │
│ 55 Bases × 55 Patterns (inc. "none")                       │
│ compose_finish(base_id, pattern_id, shape, mask, seed, scale) │
│                                                             │
│ Base: defines flat M/R/CC foundation + optional paint_fn    │
│ Pattern: defines spatial texture that modulates base values │
│ Scale: 0.25x–4.0x pattern size                             │
│ Intensity: subtle/medium/aggressive/extreme                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MONOLITHIC (50 special finishes)                            │
│ Each has its own spec_fn + paint_fn                         │
│ Cannot decompose into base + pattern                        │
│ CAN have a pattern overlaid on top (since v6.0)            │
│                                                             │
│ Includes: phantom, liquid_metal, galaxy, all chameleons,   │
│ all color-shifts (cs_*), all Prizm v4 (prizm_*), glitch,  │
│ cel_shade, aurora, etc.                                     │
└─────────────────────────────────────────────────────────────┘

TOTAL: 3,025 compositing + 50 monolithic = 3,075 finishes
```

### Compositing Formula

```python
# Base provides foundation:
final_M = base_M + noise_M  (optional per-base noise)
final_R = base_R + noise_R
final_CC = base_CC

# Pattern modulates ON TOP of base:
final_M += pattern_val * M_range * sm  (spec_modifier from intensity)
final_R += pattern_val * R_range * sm
# Clearcoat may be overridden by pattern
```

When both base and pattern have paint effects, both run at **0.7x strength** to prevent double-stacking.

### Intensity Levels

```python
INTENSITY = {
    "subtle":     {"paint": 0.5,  "spec": 0.6,  "bright": 0.03},
    "medium":     {"paint": 0.8,  "spec": 1.0,  "bright": 0.06},
    "aggressive": {"paint": 1.0,  "spec": 1.5,  "bright": 0.10},
    "extreme":    {"paint": 1.5,  "spec": 2.0,  "bright": 0.15},
}
```

### Base Registry (55 entries, line 4718)

**Categories:**
- Standard: gloss, matte, satin (3)
- Metallic: metallic, pearl, chrome, candy, satin_metal, brushed_titanium, anodized, frozen, gunmetal, copper, chameleon (11)
- Specialty: blackout, ceramic, satin_wrap, primer (4)
- v4.0 Premium: satin_chrome, spectraflame, frozen_matte, cerakote, sandblasted, vantablack, rose_gold, surgical_steel, duracoat, powder_coat (10)
- v5.0 Expansion: wet_look, silk, patina_bronze, iridescent, raw_aluminum, tinted_clear, galvanized, heat_treated, smoked, diamond_coat, flat_black, mirror_gold, brushed_aluminum, clear_matte, piano_black, satin_gold, rugged, pearlescent_white, dark_chrome, titanium_raw, candy_chrome, liquid_wrap (22)
- v5.5 SHOKK: plasma_metal, burnt_headers, mercury, electric_ice, volcanic (5)

### Pattern Registry (55 entries inc. "none", line 4803)

Covers: carbon_fiber, forged_carbon, diamond_plate, dragon_scale, hex_mesh, ripple, hammered, lightning, plasma, hologram, interference, battle_worn, acid_wash, cracked_ice, metal_flake, holographic_flake, stardust, pinstripe, camo, wood_grain, snake_skin, tire_tread, circuit_board, mosaic, lava_flow, rain_drop, barbed_wire, chainmail, brick, leopard, razor, tron, dazzle, marble, mega_flake, multicam, magma_crack, fishnet, frost_crystal, wave, spiderweb, topographic, crosshatch, chevron, celtic_knot, skull, damascus, houndstooth, plaid, shockwave, ember_mesh, turbine, static_noise, razor_wire

### Monolithic Registry (50 entries, line 4866)

- **Original 5:** phantom, ember_glow, liquid_metal, frost_bite, worn_chrome
- **Expansion 5:** oil_slick, galaxy, rust, neon_glow, weathered_paint
- **Chameleon 7:** chameleon_midnight/phoenix/ocean/venom/copper/arctic, mystichrome
- **CS v2 Adaptive 5:** cs_warm, cs_cool, cs_rainbow, cs_subtle, cs_extreme
- **CS v2 Preset 7:** cs_emerald, cs_inferno, cs_nebula, cs_deepocean, cs_supernova, cs_solarflare, cs_mystichrome
- **v4.0 Special 4:** glitch, cel_shade, thermochromic, aurora
- **v5.0 Special 4:** static, scorched, radioactive, holographic_wrap
- **Prizm v4 (13):** prizm_holographic, prizm_midnight, prizm_phoenix, prizm_oceanic, prizm_ember, prizm_arctic, prizm_solar, prizm_venom, prizm_mystichrome, prizm_black_rainbow, prizm_duochrome, prizm_iridescent, prizm_adaptive

---

## 8. Prizm v4 Color-Shift System

### The Problem

iRacing has NO thin-film interference shader. A pixel on the paint TGA is always the same color regardless of camera angle. True per-pixel color shifting is impossible.

### The Breakthrough (Prizm v4)

**Panel-aware color mapping** — different UV regions get different colors based on simulated 3D panel orientation. When the camera orbits the car, different panels dominate the view → different colors visible → brain interprets it as color shift.

### How It Works

```python
# Step 1: Generate panel direction field from UV coordinates
def _generate_panel_direction_field(shape, seed, flow_complexity):
    # 5-axis flow: diagonal, cross-flow, radial, sine undulation, Perlin breakup
    # Returns smooth 0-1 field representing simulated panel orientation

# Step 2: Map multi-stop color ramp through direction field
def _apply_color_ramp(paint, direction_field, color_stops, mask, blend):
    # Smoothstep interpolation between color stops
    # Each stop: (position, (R, G, B))

# Step 3: Add micro-flake noise
def _add_micro_flake(paint, shape, seed, mask, strength):
    # 1-4% random brightness variation simulating metallic flake

# Step 4: THE HEART
def paint_prizm_core(paint, shape, mask, seed, pm, bb, color_stops, flow_complexity):
    direction_field = _generate_panel_direction_field(shape, seed, flow_complexity)
    paint = _apply_color_ramp(paint, direction_field, color_stops, mask, blend=0.88)
    paint = _add_micro_flake(paint, shape, seed, mask, strength=0.025)
    # Metallic brightness compensation (+0.10)
    return paint
```

### Key Principle

**The color shift comes from the PAINT, not the spec.** The spec map is uniform high-metallic:
- M=220-235, R=10-20, CC=16-22
- Subtle noise variation only

### 13 Prizm Presets

holographic, midnight, phoenix, oceanic, ember, arctic, solar, venom, mystichrome, black_rainbow, duochrome, iridescent, adaptive

Each defines `color_stops` (multi-color ramp) and `flow_complexity` (1-3).

---

## 9. Pattern-Over-Monolithic System

### What It Does

Allows special/monolithic finishes to have patterns overlaid on top, just like base finishes can. For example: "Prizm Holographic + Carbon Fiber texture".

### UI Side (paint-booth-v2.html)

**`assignFinishToSelected()` (line 5286):**
- When pattern selected while monolithic is active → KEEPS monolithic, ADDS pattern on top
- When monolithic selected while pattern exists → KEEPS existing pattern overlay

**Zone card rendering (line 4234):**
- Shows "Pattern Overlay" section for monolithic zones
- Shows "(optional — adds texture over special finish)" hint
- Single pattern layer for monolithics (vs. multi-stack for bases)

**`doRender()` serverZones (line 11343):**
- For monolithic zones, sends `pattern`, `scale`, `pattern_opacity` alongside `finish`

### Engine Side (shokker_engine_v2.py)

**`build_multi_zone()` (line 5625-5638):**
```python
# PATH 2: MONOLITHIC — with optional pattern overlay
spec_fn, paint_fn = MONOLITHIC_REGISTRY[finish_name]
zone_spec = spec_fn(shape, zone_mask, seed, sm)
paint = paint_fn(paint, shape, zone_mask, seed, pm, bb)

# Pattern overlay on monolithic
mono_pat = zone.get("pattern", "none")
if mono_pat and mono_pat != "none" and mono_pat in PATTERN_REGISTRY:
    zone_spec = overlay_pattern_on_spec(zone_spec, mono_pat, ...)
    paint = overlay_pattern_paint(paint, mono_pat, ...)
```

**`overlay_pattern_on_spec()` (line 5248):** Applies pattern texture modulation on top of existing spec.
**`overlay_pattern_paint()` (line 5309):** Applies pattern paint modification on top of existing paint.

---

## 10. Canvas Pan/Zoom System

### Architecture

The canvas is nested inside a scroll container:
```
#canvasViewport → #splitViewContainer → #splitSource → .canvas-inner → #paintCanvas
```

The **actual scrollable container** is `#splitSource` (when split view active) or `#canvasViewport` (when not). The `getScrollContainer()` helper (line 8790) returns the correct one.

### ⚠️ Critical CSS: NO Flexbox Centering

The `.canvas-viewport` and `.split-pane` classes use **plain block layout**, NOT flexbox. This was a hard-won fix — flexbox + `align-items:center` + `overflow:auto` causes the **flexbox scroll truncation bug** where content larger than the container can't be scrolled to one side.

```css
/* CORRECT — plain block, NO flexbox centering */
.canvas-viewport {
    overflow: auto;
    background: #050508;
}
.canvas-inner {
    margin: 0 auto;  /* Horizontal centering via margin */
}
```

**Vertical centering** is handled via JavaScript `marginTop` in `applyZoom()` (line 8553).

### Zoom

- `canvasZoom(action)` (line 8525) — increments/decrements zoom level
- `applyZoom()` (line 8553) — sets canvas-inner width/height, adjusts marginTop
- Mouse wheel → zooms toward cursor position (zoom-to-cursor math in wheel handler, line 8660)

### Pan

- Left-click drag = pan when zoomed in (any tool mode, with 5px deadzone)
- Right-click drag = pan when zoomed in
- Middle-click drag = pan always
- Space+click = pan always
- All pan code uses `getScrollContainer()` to target the correct scrollable element

---

## 11. Critical Lessons & Gotchas

### Python on Windows

- **NEVER** add `#!/usr/bin/env python3` shebang — routes to Microsoft Store Python which lacks numpy/Pillow
- User's real Python: `C:\Python313\python.exe`
- Use `py -3` in .bat files
- Always generate `.bat` launchers alongside `.py` scripts
- Files created programmatically get Zone.Identifier flag → use `Unblock-File` in PowerShell

### Paint Modifier Strength

- Keep in **0.04–0.08 range** for safe visible effects
- Carbon darken at 0.15 → destroyed dark cars to pure black
- Chrome brighten at 0.6 → washed everything to gray
- When both base and pattern have paint effects: each runs at **0.7x**

### Engine Source File Protection

- Engine outputs to `car_num_{id}.tga` in SAME dir as source → **overwrites original**
- Backs up to `ORIGINAL_` prefix on first render
- Loads from backup on subsequent renders
- `/reset-backup` endpoint to force fresh backup

### Slider Drag Ghost Fix

- `draggable="true"` must ONLY be on the drag handle `<span>`, NOT on the zone card `<div>`
- Having it on the parent div hijacks all child interactions (sliders, inputs, dropdowns)

### Flexbox Scroll Bug

- `.split-pane` and `.canvas-viewport` must NOT use `display:flex` + `align-items:center`
- This combination with `overflow:auto` prevents scrolling when child is larger than container
- Use plain block layout with `margin: 0 auto` for centering instead

### File Formats

- **Paint TGA:** 24-bit RGB, descriptor 0x20, top-left origin
- **Spec TGA:** 32-bit RGBA, BGRA byte order, descriptor 0x28, top-left origin
- Both 2048×2048, uncompressed

---

## 12. Competitive Intelligence

### Jesse Abraham ("Neonizm")

**Who:** iRacing's leading manual Photoshop paint artist. 2024 Trading Paints Paint of the Year winner.

**His Technique:** Hand-paints different colors on different body panels in Photoshop based on their simulated 3D orientation. NOT pixel-level tricks — he exploits UV-space panel mapping. His "Prizm Paint" products sell for $9.97-$30.00 each.

**Our Advantage:** Shokker automates this in 30 seconds with `paint_prizm_core()` (vs. hours in Photoshop). 3,075 combinations vs. his ~30 manual products. Pattern overlays, batch processing, and intensity controls that he can't match.

**His Advantage:** Pixel-perfect artistic polish, hand-tuned color ramps, established brand, micro-texture quality.

**Full analysis:** See `NEONIZM_BIBLE.md` in project root.

---

## 13. Current Status & Known Issues

### Completed Features (v6.0 Prizm v4)

✅ 55 bases, 55 patterns, 50 monolithics (3,075 finishes)
✅ Multi-zone canvas painting (brush, rect, wand, gradient, selectall, edge tools)
✅ Pattern-over-monolithic support
✅ Prizm v4 panel-aware color shift (13 presets)
✅ Pattern scale slider (0.25x-4.0x)
✅ 4 intensity levels + custom intensity sliders
✅ Helmet + suit spec generation
✅ Wear simulation (0-100%)
✅ Day/night dual spec maps
✅ Fleet batch mode
✅ Season batch mode (12-race wear progression)
✅ Export ZIP packages
✅ iRacing Live Link deployment
✅ Auto-save/auto-restore to localStorage
✅ Smart randomizer (GOOD_COMBOS / BAD_COMBOS)
✅ Zone templates (save/load)
✅ Color harmony suggestions
✅ Canvas zoom with zoom-to-cursor
✅ Canvas pan (left-click, right-click, middle-click, space)
✅ Finish library with search/filter and canvas-rendered swatches
✅ Finish hover popup with 240×160 preview

### Pending / In Progress

🔧 Canvas pan/zoom — Fixed flexbox scroll bug + scroll container targeting. Awaiting user confirmation that it works properly.

### Known Issues

- KNOWLEDGE_BASE.md finish counts are outdated (says 28 bases / 38 patterns / 21 monolithics — actual is 55/55/50)
- Some documentation references pre-2023 clearcoat values

### Future Roadmap

1. **Undo/Redo system** — Command pattern, 50+ step history
2. **Lasso/Polygon selection tools** — Freehand zone masking
3. **3D car preview** — Three.js WebGL with orbit/zoom
4. **AI auto-zone detection** — k-means clustering on paint colors
5. **PyInstaller packaging** — Single .exe installer
6. **Licensing system** — Key check on startup

---

## 14. Development Workflow

### Starting the Server

```
cd "E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine"
run_server.bat
```
Or manually: `py -3 server.py` → Flask runs at http://localhost:5000

### Opening the UI

Navigate to http://localhost:5000 (server serves paint-booth-v2.html at root)
Or double-click paint-booth-v2.html directly (but /render won't work without server)

### Making Changes

1. **Engine changes:** Edit `shokker_engine_v2.py` → restart server
2. **UI changes:** Edit `paint-booth-v2.html` → refresh browser (no build step)
3. **Server changes:** Edit `server.py` → restart server

### Testing a Render

1. Open UI → Load paint from `Driver Paints/MAD-SHOKK/`
2. Pick some zones with eyedropper
3. Assign finishes (e.g., Base: Chrome, Pattern: Carbon Fiber)
4. Click RENDER
5. Check output in `ShokkerEngine/output/job_{timestamp}_23371/`

### Important Rules

- **NEVER add shebang** to Python files
- **NEVER use flexbox centering** on scrollable containers
- **Keep paint modifier strength** in 0.04-0.08 range
- **Always test with dark paints** (modifiers can destroy dark colors)
- **Clearcoat B=16 is MAX** (not 255!)
- Engine saves output in same dir as source → always has backup system

---

*Last updated: 2026-02-13*
*Engine version: v6.0 (Prizm v4)*
*Finish count: 3,075 (55 bases × 55 patterns + 50 monolithics)*
