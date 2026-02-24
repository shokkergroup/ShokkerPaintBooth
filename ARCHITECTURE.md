# Shokker Paint Booth Engine - Architecture Reference
# ===========================================================
# READ THIS BEFORE TOUCHING ANY CODE. SERIOUSLY.
# ===========================================================
# This file exists because AI sessions keep breaking things
# by not understanding the full system. If you're an AI about
# to modify shokker_engine_v2.py — READ EVERY SECTION.

## File Map
- `shokker_engine_v2.py` — THE engine. ~8300 lines. Everything lives here.
- `electron-app/server/paint-booth-v2.html` — THE UI. ~20000 lines. Single-file HTML/JS/CSS.
- `_build13.py` — Build pipeline (PyInstaller → Electron)
- `electron-app/package.json` — Version, Electron config

## The Four Registries (shokker_engine_v2.py)
There are FOUR separate registries. Each handles a different type of finish.
Mixing them up or putting entries in the wrong one WILL break things.

### 1. FINISH_REGISTRY (~line 3471)
- Legacy simple finishes: gloss, chrome, satin, matte, etc.
- Format: `"name": (spec_fn, paint_fn)`
- These are FLAT finishes with no pattern/texture
- Used via PATH 3 in render dispatch

### 2. BASE_REGISTRY (~line 5007)
- 58+ base materials that CAN have pattern overlays
- Format: `"name": {"M": int, "R": int, "CC": int, "paint_fn": fn, "desc": str}`
- M = Metallic (0-255), R = Roughness (0-255), CC = Clearcoat (0-16)
- These provide the FOUNDATION spec values that patterns modulate
- Used via PATH 1 in render dispatch

### 3. PATTERN_REGISTRY (~line 5095)
- 232+ pattern overlays that go ON TOP of a base material
- Format: `"name": {"texture_fn": fn, "paint_fn": fn, "variable_cc": bool, "desc": str}`
- texture_fn generates the spatial pattern (returns pattern_val 0-1 array)
- paint_fn modifies the paint RGB (darkening in grooves, adding color, etc.)
- PATTERNS CANNOT RENDER ALONE — they need a base material underneath
- Used inside compose_finish() and compose_paint_mod()

### 4. MONOLITHIC_REGISTRY (~line 5335)
- Complex finishes that can't decompose into base + pattern
- Format: `"name": (spec_fn, paint_fn)`
- These DO their own complete spec + paint generation
- CAN have a pattern overlay applied on top afterward
- Used via PATH 2 in render dispatch

## Render Dispatch (4 Paths)
The preview_render() function (~line 7022) and build_multi_zone() both
use the SAME dispatch logic. There are 4 paths, checked in order:

### PATH 1: Compositing (base + pattern)
- Triggered when: zone has `base` key AND base_id is in BASE_REGISTRY
- Flow: compose_finish(base_id, pattern_id, shape, mask, seed, sm, scale=, rotation=)
- Scale and rotation are applied HERE in compose_finish()
- With pattern_stack: uses compose_finish_stacked() instead
- This is the PRIMARY path for most finishes in the v2 UI

### PATH 2: Monolithic
- Triggered when: zone has `finish` key AND finish_name is in MONOLITHIC_REGISTRY
- Flow: spec_fn(shape, mask, seed, sm) + paint_fn(paint, shape, mask, seed, pm, bb)
- Pattern overlay can be applied AFTER via overlay_pattern_on_spec()
- base_scale works here (tiling), but pattern scale uses overlay functions

### PATH 3: Legacy Finish
- Triggered when: zone has `finish` key AND finish_name is in FINISH_REGISTRY
- Simple flat finishes, no pattern support, no scale/rotation

### PATH 4: Generic Fallback
- Triggered when: zone has `finish` AND `finish_colors` (client-defined)
- Used for finishes not in any registry but with color data from the UI
- Calls render_generic_finish()

## Scale Mechanism (CRITICAL — READ THIS)
Scale is applied in compose_finish() around line 5882.

### How Scale Works:
1. User moves scale slider (range 0.10 to 4.0, default 1.0)
2. UI stores `zones[i].scale = floatValue`
3. UI sends `zoneObj.scale = z.scale` when != 1.0
4. Server reads `zone_scale = float(zone.get("scale", 1.0))`
5. compose_finish() receives `scale=zone_scale`
6. INSIDE compose_finish:
   - scale > 1.0 = BIGGER pattern
     → Generate texture at SMALLER dims: tex_h = int(shape[0] / scale)
     → Upscale result back to original shape
   - scale < 1.0 = SMALLER pattern
     → Generate texture at LARGER dims: tex_h = int(shape[0] / scale)
     → Downscale result back to original shape
   - MAX_TEX_DIM = 4096 (caps memory usage)

### Why Scale Might LOOK Broken:
- Preview renders at 0.25x (512x512 from 2048x2048)
- If a texture has tiny weave_size (like 6 = repeats every 12px),
  even a 4x scale change doesn't produce dramatic visual difference
  at 512px preview
- FIX: Make texture functions use larger base sizes (20-40px)
  so scale changes are VISIBLE at preview resolution
- DO NOT change the scale mechanism itself — it works correctly

### NEVER DO THIS:
- Don't modify compose_finish() scale logic
- Don't modify the preview_scale (0.25) without testing
- Don't change how the UI sends scale values
- Don't change MAX_TEX_DIM without memory testing

## Texture Functions (How Patterns Are Generated)
Each pattern in PATTERN_REGISTRY points to a texture_fn.
Texture functions have this signature:
    def texture_something(shape, mask, seed, sm):
        # shape = (height, width) in pixels
        # mask = zone mask (0-1 float array)
        # seed = random seed for reproducibility
        # sm = spec multiplier (intensity)
        return {
            "pattern_val": np_array_0_to_1,  # The spatial pattern shape
            "R_range": float,    # How much roughness varies (+ or -)
            "M_range": float,    # How much metallic varies (+ or -)
            "CC": float_or_None, # Clearcoat override (None = no change)
        }

### Pattern Size Guidelines:
- weave_size / diamond_size / cell_size controls visual scale
- At preview (512x512), a size of 6 gives 42 repeats — TOO FINE
- RECOMMENDED minimum sizes for visible patterns:
  - Fine textures (carbon fiber): 6-10 (subtle, realistic)
  - Medium textures (kevlar, denim): 20-30 (clearly visible)
  - Large textures (basket weave, diamond plate): 30-50
  - Very large (plaid, houndstooth): 40-60
- When adding NEW patterns, use >= 20 for visibility at preview scale

## Paint Modifier Functions
Paint functions modify the RGB paint layer. Two signatures exist:

### For PATTERN_REGISTRY patterns (used in compose_paint_mod):
    def paint_something(paint, pattern_val, mask, pm, bb):
        # paint = RGB float array (0-1), MODIFY IN PLACE within mask
        # pattern_val = same 0-1 spatial shape from texture_fn
        # mask = zone mask
        # pm = paint multiplier, bb = brightness boost

### For BASE/MONOLITHIC (standalone paint mods):
    def paint_something(paint, shape, mask, seed, pm, bb):
        # paint = RGB float array, modify in place
        # shape = (h, w)

## UI → Server Data Flow (paint-booth-v2.html → shokker_engine_v2.py)

### Preview Render Request:
1. User changes a setting → triggerPreviewRender() called
2. JS builds `serverZones` array from `zones[]` state
3. Each zone object includes: base, pattern, finish, scale, rotation,
   pattern_opacity, pattern_stack, base_scale, wear_level, etc.
4. POST to /preview-render with {paint_file, zones, seed, preview_scale}
5. Server calls preview_render() which loops zones and dispatches

### Key UI Fields → Server Fields:
- `z.base` → `zone["base"]` (base material ID)
- `z.pattern` → `zone["pattern"]` (pattern overlay ID)
- `z.finish` → `zone["finish"]` (monolithic/legacy finish ID)
- `z.scale` → `zone["scale"]` (pattern scale, 0.10-4.0)
- `z.rotation` → `zone["rotation"]` (pattern rotation, 0-359 deg)
- `z.baseScale` → `zone["base_scale"]` (base tiling, 1.0-10.0)
- `z.patternOpacity` → `zone["pattern_opacity"]` (0-1.0)
- `z.patternStack` → `zone["pattern_stack"]` (array of extra patterns)

### CRITICAL: Pattern ID Must Be in PATTERN_REGISTRY
If a pattern ID is NOT in PATTERN_REGISTRY, the server silently
drops it to "none" (no pattern rendered). This was the root cause
of the original "patterns don't work" bug. Fixed by adding 162
alias entries in v7.0 that map every UI pattern to an existing
texture function.

## Safe vs Dangerous Changes

### SAFE (additive, won't break existing):
- Adding NEW texture functions (def texture_xxx)
- Adding NEW paint modifier functions
- Adding NEW entries to PATTERN_REGISTRY
- Changing which texture_fn a PATTERN_REGISTRY alias points to
- Adding NEW entries to BASE_REGISTRY or MONOLITHIC_REGISTRY
- Adding comments or documentation

### DANGEROUS (can break everything):
- Modifying compose_finish() or compose_paint_mod()
- Modifying compose_finish_stacked() or compose_paint_mod_stacked()
- Modifying preview_render() dispatch logic
- Modifying build_multi_zone() dispatch logic
- Changing texture function signatures (shape, mask, seed, sm)
- Changing return dict format from texture functions
- Modifying the scale/rotation mechanism
- Changing BASE_REGISTRY entry format
- Renaming or removing existing functions that other entries reference
- Modifying the HTTP server routes or request parsing

### GOLDEN RULE:
If you need to change behavior for a specific pattern, create a
NEW texture function and point the registry entry at it.
DO NOT modify the shared texture function that other patterns use.
Example: kevlar_weave needed bigger weave than carbon_fiber.
WRONG: Change weave_size in texture_carbon_fiber (breaks carbon_fiber!)
RIGHT: Create texture_kevlar_weave with its own weave_size, update registry.

## Build & Deploy Process

### Local Build:
1. Run `E:\run_build.bat` (wraps _build13.py)
2. PyInstaller builds shokker-server.exe (~65MB)
3. HTML files copied to electron-app/server/
4. electron-builder creates installer (~146MB Setup.exe)
5. Output in electron-app/dist/

### Testing Locally:
- Launch: `electron-app/dist/win-unpacked/Shokker Paint Booth.exe`
- Server starts on random port, check /status endpoint
- /status returns: pattern_count, base_count, monolithic_count, version

### Publishing to GitHub:
- Repo: shokkergroup/ShokkerPaintBooth (private)
- Release: v0.1.0-alpha (pre-release)
- Assets: Setup.exe, Setup.exe.blockmap, latest.yml
- Use GitHub REST API for uploads (electron-builder publish has issues)
- PAT stored separately, not in this file

## Bug History (Learn From Past Mistakes)

### Bug 1: Patterns Don't Render
- Root cause: 162 UI pattern IDs had no PATTERN_REGISTRY entry
- Server silently dropped unknown patterns to "none"
- Fix: Added 162 alias entries mapping to closest existing texture_fn
- NEVER remove these aliases

### Bug 2: Patterns Too Small, Scale Doesn't Visibly Change
- Root cause: Aliases pointed to texture_carbon_fiber (weave_size=6)
- At preview scale (512px), 6px weave is imperceptible
- Fix: Create dedicated texture functions with appropriate sizes
- texture_kevlar_weave (weave_size=24)
- texture_basket_weave (weave_size=36)
- LESSON: When aliasing, consider if the target texture_fn is
  visually appropriate, not just "closest match"

## Checklist Before Any Code Change
1. Read this ARCHITECTURE.md fully
2. Identify which registry/function you're touching
3. Verify your change is in the SAFE category
4. If DANGEROUS, understand ALL code paths affected
5. After changes, rebuild and test preview render
6. Verify /status endpoint shows correct counts
7. Test at least 2 different patterns with scale slider
