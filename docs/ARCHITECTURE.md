# SPB Architecture

> How Shokker Paint Booth is built, what the moving parts are, and why they're arranged that way.

This doc is for contributors who want to understand SPB deep enough to fix a bug in an unfamiliar file or add a feature that touches multiple subsystems. If you just want to paint a livery, see [../SPB_GUIDE.md](../SPB_GUIDE.md) instead.

---

## 30-Second Summary

SPB is an **Electron desktop app** that wraps a **Python Flask render server** and a **browser-based canvas UI**.

```
 ┌────────────────────────────────────────────────────┐
 │ Electron main process (main.js)                    │
 │  • spawns Python server subprocess                 │
 │  • manages windows, file dialogs, IPC              │
 └───────────────┬────────────────────────────────────┘
                 │ HTTP (localhost:<port>)
 ┌───────────────▼────────────────────────────────────┐
 │ Python render server (server.py + engine/)        │
 │  • Flask routes for /render, /preview, /save      │
 │  • shokker_engine_v2.py (core physics)            │
 │  • engine/paint_v2/<category>.py (finishes)       │
 │  • engine/base_registry_data.py (registry)        │
 └────────────────────────────────────────────────────┘

 ┌────────────────────────────────────────────────────┐
 │ Electron renderer window (browser)                 │
 │  • paint-booth-*.js (state, canvas, UI, renderer) │
 │  • talks to Python server via fetch()             │
 └────────────────────────────────────────────────────┘
```

---

## The 3-Copy Sync Rule

**CRITICAL.** Every server-side asset exists in three places:

1. **Root level** — for running from source (`engine/`, `paint-booth-*.js`, `server.py`).
2. **electron-app/server/** — copied by `copy-server-assets.js` during build.
3. **electron-app/server/pyserver/_internal/** — the PyInstaller bundle inside the packaged app.

When you edit a server file, you must update all three copies, or the packaged Setup.exe will silently run old code. See [../CONTRIBUTING.md](../CONTRIBUTING.md#the-3-copy-sync-rule) for details.

---

## File Role Map

| File | Lines | Role |
|---|---|---|
| `shokker_engine_v2.py` | ~8,246 | Core paint physics engine. All render math lives here. |
| `server.py` | ~4,481 | Flask API server. Routes, IPC glue, render orchestration. |
| `config.py` | ~400 | Environment / constants / paths. |
| `engine/base_registry_data.py` | large | FINISH_REGISTRY: name → paint/spec function maps. |
| `engine/paint_v2/*.py` | varies | Individual finish implementations (chrome, candy, carbon, etc.). |
| `engine/expansions/*.py` | varies | Big drop-in finish expansions (arsenal, atelier, paradigm). |
| `engine/spec_patterns.py` | large | SPEC_PATTERN catalog — 192 overlay patterns across 19 categories. |
| `engine/expansion_patterns.py` | varies | Color/pattern expansion registries. |
| `engine/compose.py` | varies | Final compositing of base + pattern + spec. |
| `engine/overlay.py` | varies | Layer-effect overlays. |
| `engine/gpu.py` | varies | GPU accelerations where used. |
| `paint-booth-0-finish-data.js` | huge | BASES, PATTERNS, SPEC_PATTERNS, BASE_GROUPS, PATTERN_GROUPS — UI data. |
| `paint-booth-1-data.js` | small | UI constants. |
| `paint-booth-2-state-zones.js` | ~8,008 | State mgmt + zones UI + undo stack. |
| `paint-booth-3-canvas.js` | ~4,660 | Canvas drawing tools + RLE region masks. |
| `paint-booth-4-pattern-renderer.js` | large | Client-side pattern preview. |
| `paint-booth-5-api-render.js` | ~2,506 | API client + render history polling. |
| `paint-booth-6-ui-boot.js` | large | UI wiring and initial boot sequence. |
| `paint-booth-7-shokk.js` | ~44 | Shokk-specific UI extensions. |

---

## Key Abstractions

### Zone
A user-defined region on the car. A zone has a **color**, a **finish** (base), optionally a **pattern**, and optionally a **spec overlay**. Zones can be layer-masked (painting only within a specific PSD layer) or region-masked (RLE-encoded bitmap drawn by the user).

### Layer
A PSD or drawing layer. Zones can be **locked** to a layer so painting only affects pixels on that layer.

### Finish (Base)
A physics-driven material: chrome, candy red, metallic silver, carbon fiber, brushed aluminum. Each finish has a **paint function** (writes color) and a **spec function** (writes spec map RGBA).

### Pattern
A repeating or procedural texture applied on top of a finish. Patterns can be applied to the **color channel**, the **spec channel**, or both (this per-channel control is unique to SPB).

### Spec Overlay
A pattern specifically targeting the spec map — brushed strokes, hammered dents, peened dimples, clearcoat swirls. Exposed via `SPEC_PATTERNS` array and `engine/spec_patterns.py`.

### Monolithic
A bundled **base + pattern + spec** shipped as a single one-click finish. Examples: COLORSHOXX, MORTAL SHOKK, PARADIGM, ATELIER. Monolithics live in `engine/expansions/`.

---

## Pattern System (Three-Registry Architecture)

| Registry | Location | Purpose |
|---|---|---|
| `PATTERNS` | JS | Display list only. Unused entries don't break anything. |
| `PATTERN_GROUPS` | JS | Picker organization. Un-grouped IDs are removed from picker at boot. |
| `PATTERN_REGISTRY` | Python | **Render lookup**. Missing ID = silently renders nothing. |

**To add a pattern:** `PATTERNS` → `PATTERN_GROUPS` → `PATTERN_REGISTRY`. All three JS copies, all three Python copies.

Texture function signature:
```python
def texture_NAME(shape, mask, seed, sm):
    # shape: (H, W) ndarray of car shape
    # mask: (H, W) bool — where to apply
    # seed: int — deterministic RNG seed
    # sm: SpecMap — RGBA ndarray to modify
    ...
```

---

## Spec Map Semantics (iRacing)

- **R = Metallic** (0 = dielectric, 255 = full metal)
- **G = Roughness** (0 = mirror, 255 = matte)
- **B = Clearcoat** (0–15 = none, **16 = max gloss**, 255 = dull) — *inverted from intuition*
- **A = Specular Mask** (rarely used; no consumer tool exposes it yet)

Key finish reference values:

| Finish | R | G | B |
|---|---:|---:|---:|
| Chrome | 255 | 0 | 16 |
| Metallic | 255 | 85 | 0 |
| Matte | 0 | 220 | 15 |

Full details: [../SPB_SPEC_MAP_GUIDE.md](../SPB_SPEC_MAP_GUIDE.md).

---

## Data Flow (Render)

1. User clicks **RENDER** in UI.
2. `paint-booth-5-api-render.js` collects state (zones, layers, finishes, patterns) and POSTs to `http://localhost:<port>/render`.
3. `server.py` accepts the request, parses the spec, and calls into `shokker_engine_v2.py`.
4. Engine walks zones in order, calling each zone's `finish.paint()` and `finish.spec()` functions.
5. Patterns apply as texture passes. Spec overlays stamp on top.
6. `compose.py` merges the final RGBA + spec map.
7. Server writes a preview PNG and (on explicit export) a TGA.
8. Render history polling in `paint-booth-5-api-render.js` picks up the new image and swaps it into the preview surface.

---

## Adding a Finish

Canonical steps:

1. Add `paint()` and `spec()` functions in `engine/paint_v2/<category>.py`.
2. Register under `FINISH_REGISTRY` in `engine/base_registry_data.py`.
3. Add UI entry in `paint-booth-0-finish-data.js` under `BASES` + appropriate group in `BASE_GROUPS`.
4. Mirror changes to the other two copies (3-copy sync rule).
5. Generate a swatch (if a swatch system is active).
6. Add a line to `CHANGELOG.md`.

---

## Cross-cutting Concerns

- **Undo stack** (JS) lives in `paint-booth-2-state-zones.js`. Currently unbounded — on the improvement backlog.
- **DOM rebuild** in `renderZones()` is inefficient for large zone counts. Also on backlog.
- **Render preview** uses HTTP polling. Moving to Server-Sent Events is on backlog.
- **License** validation runs in the Electron preload; see `license-preload.js`.

---

## See Also

- [DEVELOPMENT.md](DEVELOPMENT.md) — getting set up
- [BUILD.md](BUILD.md) — producing a Setup.exe
- [PERFORMANCE.md](PERFORMANCE.md) — perf hotspots and profiling
- [TESTING.md](TESTING.md) — how to prove changes work
