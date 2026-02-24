# Shokker Paint Booth — Architecture Overview

## What This Is

The Shokker Paint Booth is a desktop web application for designing iRacing car liveries using a massive library of PBR-correct finishes. It runs as a local Flask server serving a single-page HTML frontend. The engine generates 32-bit TGA spec maps and recolored paint files that drop directly into iRacing's paint folder.

## System Diagram

```
┌─────────────────────────────────────────────────┐
│              paint-booth-v2.html                │
│         (16,252 lines - Single Page App)        │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Zone UI  │  │ Canvas   │  │ Finish       │  │
│  │ System   │  │ Viewport │  │ Library      │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │               │          │
│       └──────────────┼───────────────┘          │
│                      │                          │
│              ShokkerAPI Object                  │
│         (fetch calls to localhost)               │
└──────────────────────┬──────────────────────────┘
                       │ HTTP (port 5000)
┌──────────────────────┴──────────────────────────┐
│                  server.py                      │
│            (Flask, ~1,417 lines)                │
│                                                 │
│  Routes: /render, /preview-render, /status,     │
│  /swatch/*, /config, /deploy-to-iracing,        │
│  /license, /finish-groups, /browse-files, etc.  │
└──────────────────────┬──────────────────────────┘
                       │ Python imports
┌──────────────────────┴──────────────────────────┐
│           shokker_engine_v2.py                  │
│          (Python, ~7,015 lines)                 │
│                                                 │
│  Registries: 155 Bases, 155 Patterns,           │
│              155 Monolithics, 25 Legacy         │
│  Core: compose_finish(), full_render_pipeline() │
│  PBR: Spec map generation (M/R/CC/A channels)  │
│  Paint: Zone masks, recolor, wear system        │
└─────────────────────────────────────────────────┘
```

## File Map

| File | Lines | Role |
|------|-------|------|
| `shokker_engine_v2.py` | ~7,015 | Core engine — registries, compositing, PBR spec maps, paint recolor, zone masks, wear, noise, TGA I/O |
| `server.py` | ~1,417 | Flask HTTP server — routes, file management, render orchestration, license system, swatch generation |
| `paint-booth-v2.html` | ~16,252 | Entire frontend — HTML structure, CSS (dark theme), all JavaScript (zone UI, canvas, NLP chat, finish browser, presets, templates, config, keyboard shortcuts, everything) |

All three files live in: `E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\ShokkerEngine\`

## Tech Stack

**Backend:**
- Python 3.13 (`C:\Python313\python.exe`)
- Flask (HTTP server on port 5000)
- NumPy (array operations for pixel manipulation)
- Pillow/PIL (image loading/saving)
- struct (TGA binary I/O)

**Frontend:**
- Vanilla HTML/CSS/JavaScript (no frameworks, no build step)
- Single monolithic HTML file with inline CSS and JS
- localStorage for persistence (templates, combos, favorites, settings)
- Canvas API for region mask painting, recolor preview, pattern preview rendering
- Web Audio API for render completion chime
- Fetch API for all server communication

**File Formats:**
- TGA (32-bit RGBA) — iRacing's native paint/spec format, 2048×2048
- PNG — preview renders, swatches
- JSON — config save/load, .shokker preset files
- ZIP — bundled render output (paint + spec + extras)

## The "24K Arsenal"

The finish library is the core value proposition:
- **155 Bases** — surface materials (Gloss, Matte, Chrome, Candy, Pearl, Metallic, Carbon, Frozen, etc.)
- **155 Patterns** — texture overlays (Carbon Fiber, Hex Mesh, Diamond Plate, Chevron, Damascus, etc.)
- **155 Monolithics** — special effect finishes that bypass compositing (Chameleon, Glitch, Aurora, Thermochromic, etc.)
- **Compositing**: Any base × any pattern = 24,025 combinations
- **Total**: 24,025 composited + 155 monolithic = **24,180 unique finishes**

## Three Dispatch Paths

When a zone gets rendered, the engine determines which path to use:

1. **Compositing Path** — Base + Pattern selected → `compose_finish()` modulates base spec values with pattern texture
2. **Monolithic Path** — Monolithic selected → dedicated generator function, full pixel control
3. **Legacy Path** — Old `FINISH_REGISTRY` entries (25 finishes) → direct function call, pre-dates the Base/Pattern split

## Data Flow: Render

```
User configures zones in UI
        ↓
doRender() collects zone configs
        ↓
ShokkerAPI.render() → POST /render
        ↓
server.py validates, calls engine
        ↓
full_render_pipeline():
  1. Load car paint TGA (2048×2048)
  2. Build zone masks (color detection + region masks)
  3. For each zone: compose/generate spec map
  4. Merge all zone specs into final spec map
  5. Apply wear if enabled
  6. Recolor paint if rules exist
  7. Write output TGA files
        ↓
Response with file paths, previews
        ↓
showRenderResults() displays in UI
```

## Data Flow: Preview

```
User modifies a zone
        ↓
triggerPreviewRender() (300ms debounce)
        ↓
Hash current zones → compare to last preview hash
        ↓
If changed: POST /preview-render (lower resolution)
        ↓
preview_render() in engine (scaled down)
        ↓
Split-view pane updates with new preview
```

## State Management

All state lives in JavaScript variables (no state library):

- `zones[]` — Array of zone objects (color, finish, pattern stack, wear, intensity, region mask, etc.)
- `selectedZoneIndex` — Currently active zone
- `canvasMode` — Current tool (eyedropper, brush, rect, erase, wand, gradient)
- `panelMode` — Active right panel (specmap, recolor)
- `recolorRules[]` — HSV shift rules for paint recolor
- `recolorMask` — Uint8Array spatial mask for selective recolor
- `undoStack` — Region mask undo (brush strokes)
- `zoneUndoStack` / `zoneRedoStack` — Zone property change history (max 50)
- `decalLayers[]` — Image overlay positions
- `renderHistory[]` — Previous render results

Persistence via `localStorage`:
- Zone templates (save/load named configs)
- Finish combos (saved finish combinations)
- Finish browser favorites
- Auto-save on every zone change
- Tutorial completion flag

## Port & URLs

- Server: `http://localhost:5000`
- Frontend: `http://localhost:5000/` (serves paint-booth-v2.html)
- All API calls use relative paths from the frontend

## Python Path

Hardcoded: `C:\Python313\python.exe`
Server started via: `cd ShokkerEngine && python server.py`

## License System (Alpha: Disabled)

Format: `SHOKKER-XXXX-XXXX-XXXX`
Both server-side gate (on /render endpoint, ~line 532 in server.py) and client-side gate (in doRender()) are commented out for Alpha testing. System is built and ready to re-enable.
