# CURSOR TASK BRIEF — Image Pattern Pipeline Implementation
**Created:** 2026-03-07 — Claude (Cowork)
**For:** Cursor AI
**Master Strategy:** See `PAINT_BOOTH_V5_STRATEGY.md` for full context
**Pattern Spec:** See `MANUAL_PATTERN_AND_BASES_DISCUSSION.md` for PNG specs, variation system, and category plans

---

## READ THESE FIRST

Before touching ANY code, read these documents in order:
1. `PROJECT_STRUCTURE.md` — know where every file lives
2. `WORK_IN_PROGRESS.md` — know what's broken
3. `MANUAL_PATTERN_AND_BASES_DISCUSSION.md` — the pattern system bible
4. `AGENTS.md` — agent conventions
5. This document — your task sequence

**CRITICAL RULE:** All edits go in the **V5 root** canonical files. NEVER edit files inside `electron-app/` directly. After editing, run `npm run copy-server` in `electron-app/` to sync. Verify in DevTools Sources that the running app loads the updated file.

---

## SECTION 1 — FIX BLOCKERS (Do This First, No Exceptions)

### Task 1.1: Pattern-Pop String Mismatch

**Problem:** The UI sends `"pattern-vivid"` for Pattern-Pop. The engine only branches on `"pop"` / `"pattern-pop"` / `"pattern_pop"`. Result: Pattern-Pop falls into the lerp branch and behaves like Pattern-Reactive.

**File:** `shokker_engine_v2.py` (V5 ROOT — not electron-app copy)

**Edit 1 — `blend_dual_base_spec()` (~line 6646-6671):**
Find the pop branch condition. It currently reads something like:
```python
elif blend_mode in ("pop", "pattern-pop", "pattern_pop") and pattern_mask is not None:
```
Change to:
```python
elif blend_mode in ("pop", "pattern-pop", "pattern_pop", "pattern-vivid", "pattern_vivid") and pattern_mask is not None:
```

Also find the pattern (lerp) branch and REMOVE `"pattern-vivid"` and `"pattern_vivid"` from it if they're listed there. Pattern-vivid must NOT be in the lerp branch.

**Edit 2 — `compose_paint_mod()` (~line 7603-7678):**
Find `_is_pop_mode`. Add `"pattern-vivid"` and `"pattern_vivid"`:
```python
_is_pop_mode = blend_mode in ("pop", "pattern-pop", "pattern_pop", "pattern-vivid", "pattern_vivid")
```

**Edit 3 — `compose_paint_mod_stacked()` (~line 7826-7882):**
Same fix as Edit 2.

**Debug print — `compose_finish()` (before `blend_dual_base_spec` call):**
Add temporarily:
```python
if _needs_pat_mask:
    print(f"[POP DEBUG] mode={blend_mode}, pattern_id={pattern_id}, "
          f"pat_in_reg={pattern_id in PATTERN_REGISTRY}, "
          f"pattern_mask_is_None={pattern_mask is None}")
```

**Verification:**
- Start server with `python server_v5.py` (NOT the .exe)
- Confirm `http://localhost:59876/status` shows `"_v":"py"`
- Select any pattern + Pattern-Pop in the UI
- Check terminal output for `[POP DEBUG]` — confirm `mode=pattern-vivid` appears
- Set strength to 100%: the 2nd base should ONLY cover pattern-bright areas
- Set strength to 10%: only the top ~10% brightest pixels should fire
- If the whole car turns blue at 100%: the fix did not take. Re-check which branch `"pattern-vivid"` landed in.

### Task 1.2: Clarify `paint-booth-app.js`

**Problem:** 890KB file in V5 root. HTML loads modular scripts 1-6 instead. Unknown if it's loaded anywhere.

**Investigation:**
```
# Search the entire V5 folder for references:
grep -r "paint-booth-app" --include="*.html" --include="*.js" --include="*.py" --include="*.json" .
```

**If NO references load it:** Move to `_archive/legacy/paint-booth-app.js`. Add a note to `PROJECT_STRUCTURE.md`:
```
### Legacy (archived)
- `paint-booth-app.js` — Original monolithic UI file. Superseded by modular 1-6 scripts. Archived 2026-03-XX.
```

**If it IS referenced somewhere:** Document where and why. Flag it for consolidation in WORK_IN_PROGRESS.md.

### Task 1.3: Document File Sync Workflow

**In `PROJECT_STRUCTURE.md`, add or update a section:**

```markdown
## File Sync — V5 Root to Electron App

**Canonical source:** All JS, CSS, HTML, and Python files in the V5 root folder.
**Electron copy:** `electron-app/server/` mirrors V5 root files for Electron dev/build.

**After EVERY edit session:**
1. Save your changes to V5 root files
2. cd into `electron-app/`
3. Run `npm run copy-server`
4. If running Electron: restart the app
5. Open DevTools → Sources → confirm the file you edited shows your changes

**NEVER edit `electron-app/server/` files directly.** They will be overwritten by the next copy-server run.

**For production builds:**
1. `npm run copy-server` (sync files)
2. `npm run build` (builds Electron distributable)
3. Output goes to `electron-app/dist/`
```

### Section 1 Checklist
- [ ] Pattern-Pop string fix applied to V5 root `shokker_engine_v2.py`
- [ ] `[POP DEBUG]` confirms pop branch is reached with `mode=pattern-vivid`
- [ ] Pattern-Pop visually works (threshold, not lerp)
- [ ] `paint-booth-app.js` resolved (archived or documented)
- [ ] File sync workflow documented in `PROJECT_STRUCTURE.md`
- [ ] `npm run copy-server` tested and confirmed working
- [ ] `test_regression.py` still passes (54 tests)

**STOP. Verify all items above before proceeding to Section 2.**

---

## SECTION 2 — Wire the Image-Based Pattern Loader

**Reference:** `MANUAL_PATTERN_AND_BASES_DISCUSSION.md` — Parts 1 and 2

### Task 2.1: Implement `_load_image_pattern()`

**File:** `shokker_engine_v2.py` (or `engine/render.py` if migration allows — check `MIGRATION_STATUS.md`)

```python
import PIL.Image
import functools

# Module-level cache
_IMAGE_PATTERN_CACHE = {}

def _load_image_pattern(image_path, shape, scale=1.0, rotation=0):
    """
    Load a grayscale PNG and return as float32 pattern_val array.
    
    Args:
        image_path: Path to grayscale PNG (relative to server root or absolute)
        shape: (H, W) target output shape
        scale: Pattern scale (1.0 = fill once, 0.5 = tile 2x2, 0.25 = tile 4x4)
        rotation: Degrees to rotate (0, 90, 180, 270)
    
    Returns:
        (H, W) float32 array, values 0.0-1.0
    """
    cache_key = (image_path, shape)
    
    # Check cache for the base loaded image (pre-scale, pre-rotation)
    if cache_key not in _IMAGE_PATTERN_CACHE:
        try:
            img = PIL.Image.open(image_path).convert('L')
            arr = np.array(img, dtype=np.float32) / 255.0
            # Resize to target shape using LANCZOS
            if arr.shape != shape:
                img_resized = img.resize((shape[1], shape[0]), PIL.Image.LANCZOS)
                arr = np.array(img_resized, dtype=np.float32) / 255.0
            _IMAGE_PATTERN_CACHE[cache_key] = arr
        except FileNotFoundError:
            print(f"[WARN] Pattern image not found: {image_path}")
            return np.zeros(shape, dtype=np.float32)
        except Exception as e:
            print(f"[WARN] Failed to load pattern image {image_path}: {e}")
            return np.zeros(shape, dtype=np.float32)
    
    pattern_val = _IMAGE_PATTERN_CACHE[cache_key].copy()
    
    # Apply tiling via scale (uses existing helper)
    if scale != 1.0 and scale > 0:
        pattern_val = _tile_fractional(pattern_val, scale)
        pattern_val = _crop_center_array(pattern_val, shape)
    
    # Apply rotation (uses existing helper)
    if rotation != 0:
        pattern_val = _rotate_single_array(pattern_val, rotation)
        pattern_val = _crop_center_array(pattern_val, shape)
    
    return np.clip(pattern_val, 0.0, 1.0)
```

**Important:** Confirm that `_tile_fractional`, `_crop_center_array`, and `_rotate_single_array` (or their equivalents in `engine/core.py`) are accessible from wherever you place this function. Import them if needed.

### Task 2.2: Update `_get_pattern_mask()` Routing

Find `_get_pattern_mask()` (likely in `shokker_engine_v2.py` or `engine/render.py`).

Add image_path routing BEFORE the existing texture_fn path:

```python
def _get_pattern_mask(pattern_id, shape, scale=1.0, rotation=0, **kwargs):
    if pattern_id not in PATTERN_REGISTRY:
        return None
    
    entry = PATTERN_REGISTRY[pattern_id]
    
    # NEW: Image-based pattern path
    if entry.get('image_path'):
        return _load_image_pattern(entry['image_path'], shape, scale, rotation)
    
    # EXISTING: Procedural texture_fn path
    if entry.get('texture_fn'):
        # ... existing code unchanged ...
```

### Task 2.3: Add Test Pattern to Registry

Add ONE entry to PATTERN_REGISTRY to test the pipeline:

```python
"smilexx_pure": {
    "image_path": "assets/patterns/musicinspired/smilexx_pure.png",
    "paint_fn": paint_none,
    "variable_cc": False,
    "desc": "Nirvana Smiley - clean white outline on black"
},
```

**Note:** `paint_none` should be a no-op function that returns the paint array unchanged. If it doesn't exist, create it:
```python
def paint_none(paint, pattern_val, color, **kw):
    return paint
```

### Task 2.4: Add Test Pattern to UI Data

In `paint-booth-1-data.js`, add to the PATTERNS array:
```javascript
{ id: "smilexx_pure", name: "Nirvana Smiley (Pure)", desc: "Clean white outline - test image pattern" }
```

Add a temporary test group or add to an existing group.

### Task 2.5: Verification

1. Start server: `python server_v5.py`
2. Confirm `assets/patterns/musicinspired/smilexx_pure.png` exists and is a valid grayscale PNG
3. Select the Nirvana Smiley pattern in the UI
4. Apply to a zone with Pattern-Reactive at 50% strength
5. Render — confirm the smiley shape appears in the specular/paint output
6. Switch to Pattern-Pop at 50% strength — confirm threshold behavior
7. Test scale slider: 1.0 (full), 0.5 (tiled 2x2), 0.25 (tiled 4x4)
8. Test rotation: 90° and 180°
9. Run `test_regression.py` — all 54 tests must pass (no regressions)

### Section 2 Checklist
- [ ] `_load_image_pattern()` implemented with caching
- [ ] `_get_pattern_mask()` routes on `image_path` before `texture_fn`
- [ ] `paint_none` exists (or equivalent no-op paint function)
- [ ] `smilexx_pure` renders correctly with Pattern-Reactive
- [ ] `smilexx_pure` renders correctly with Pattern-Pop
- [ ] Scale/tiling works (0.5, 0.25 tested)
- [ ] Rotation works (90°, 180° tested)
- [ ] `test_regression.py` passes (54 tests, no regressions)
- [ ] `npm run copy-server` run after all changes

**STOP. Verify all items above before proceeding to Section 3.**

---

## SECTION 3 — Swatch Renderer for Image Patterns

### Task 3.1: Add Static Route for Pattern Assets

**File:** `server_v5.py` (or `server.py` if V5 routes are inherited)

Add a route to serve pattern PNGs:
```python
@app.route('/assets/patterns/<path:filename>')
def serve_pattern_asset(filename):
    return send_from_directory('assets/patterns', filename)
```

Verify: `http://localhost:59876/assets/patterns/musicinspired/smilexx_pure.png` should return the PNG.

### Task 3.2: Canvas2D Image Pattern Swatch Renderer

**File:** `paint-booth-4-pattern-renderer.js`

Add a generic renderer for any pattern that has an `image_path` or `swatch_image` property:

```javascript
// Generic image-based pattern swatch renderer
function renderImagePatternSwatch(ctx, w, h, imageUrl) {
    // Dark background so white patterns are visible
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, w, h);
    
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = function() {
        ctx.drawImage(img, 0, 0, w, h);
    };
    img.onerror = function() {
        // Fallback: draw an X to indicate missing image
        ctx.strokeStyle = '#444';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, 0); ctx.lineTo(w, h);
        ctx.moveTo(w, 0); ctx.lineTo(0, h);
        ctx.stroke();
    };
    img.src = imageUrl;
}
```

**Integration:** In the swatch dispatch logic, check if the pattern entry has `swatch_image`. If so, use `renderImagePatternSwatch`. Otherwise fall through to existing procedural renderers.

### Task 3.3: Update UI Data Entries

In `paint-booth-1-data.js`, image-based patterns should include a `swatch_image` key:
```javascript
{
    id: "smilexx_pure",
    name: "Nirvana Smiley (Pure)",
    desc: "Clean white outline",
    swatch_image: "/assets/patterns/musicinspired/smilexx_pure.png"
}
```

The swatch renderer dispatches on this key.

### Task 3.4: Verification

1. Open the pattern picker
2. Find Nirvana Smiley (Pure)
3. Confirm the swatch shows a white smiley outline on a dark background
4. Confirm the swatch loads without blocking the UI
5. Confirm other pattern swatches still render correctly (no regressions)

### Section 3 Checklist
- [ ] Static route serves pattern PNGs
- [ ] Canvas2D renderer draws image patterns on dark background
- [ ] Swatch dispatch routes image patterns to the new renderer
- [ ] `swatch_image` key added to test pattern in UI data
- [ ] Swatch is visible and identifiable in picker
- [ ] Swatch loads asynchronously (no UI blocking)
- [ ] Existing pattern swatches unaffected
- [ ] `npm run copy-server` run after all changes

**STOP. Verify all items above before proceeding to Section 4.**

---

## SECTION 4 — Music Inspired Category Buildout

**Prerequisite:** Ricky has delivered the PNG files to `assets/patterns/musicinspired/`

### Task 4.1: Wire Each Delivered Pattern

For EACH PNG file Ricky delivers:

1. **PATTERN_REGISTRY** — Add entry:
```python
"[pattern_id]": {
    "image_path": "assets/patterns/musicinspired/[filename].png",
    "paint_fn": paint_none,
    "variable_cc": False,
    "desc": "[description]"
},
```

2. **paint-booth-1-data.js** — Add to PATTERNS array:
```javascript
{ id: "[pattern_id]", name: "[Display Name]", desc: "[description]", swatch_image: "/assets/patterns/musicinspired/[filename].png" }
```

3. **PATTERN_GROUPS** — Add to "Music Inspired" group:
```javascript
"🎵 Music Inspired": ["smilexx_pure", "smilexx_gradient", "smilexx_halftone", ...]
```

### Task 4.2: Test Each Pattern

For EVERY pattern added:
- [ ] Swatch visible in picker
- [ ] Renders correctly with Pattern-Reactive (smooth blend)
- [ ] Renders correctly with Pattern-Pop (threshold-based coverage)
- [ ] Scale slider works (tiling at 0.5 and 0.25)
- [ ] At least 2 variations exist (pure + gradient minimum)

### Task 4.3: Category Quality Gate

Before marking Music Inspired complete:
- [ ] All patterns pass individual tests above
- [ ] `test_regression.py` passes
- [ ] Run `npm run copy-server` and verify in Electron
- [ ] Take screenshots of each pattern rendering in both modes
- [ ] Report to Ricky for final approval

### Section 4 Checklist
- [ ] All Music Inspired PNGs wired in PATTERN_REGISTRY
- [ ] All added to paint-booth-1-data.js with swatch_image
- [ ] All added to PATTERN_GROUPS
- [ ] All swatches visible
- [ ] All tested in both blend modes
- [ ] Regression tests pass
- [ ] Screenshots captured
- [ ] Awaiting Ricky approval

**FULL STOP. Do NOT proceed to Decades or Zodiac until Ricky signs off on Music Inspired.**

---

## SECTION 5 — Expansion Categories

**Do not start this section without Ricky's approval on Section 4.**

Follow the exact same process as Section 4 for each sub-category:
1. Decades — 1950s (Ricky delivers PNGs → Cursor wires)
2. Decades — 1960s
3. Decades — 1970s
4. Decades — 1980s
5. Decades — 1990s
6. Zodiac (12 signs × 2 variations minimum)

**Build order is strict. Complete one sub-category before starting the next.**

### Parallel Work (While Waiting for Ricky's PNGs)

If Ricky is building PNGs and Cursor has idle time, work on these (in priority order):
1. Fix broken thumbnail categories listed in `WORK_IN_PROGRESS.md`
2. Wire bespoke Reactive Shimmer functions from `engine/expansion_patterns.py` to replace placeholder texture_fn mappings
3. Remove `[POP DEBUG]` prints from production code
4. Base overlay tuning (Uniform vs Pattern-Reactive)
5. Any bugs or polish items from `WORK_IN_PROGRESS.md`

---

## NAMING CONVENTIONS

### Pattern IDs (PATTERN_REGISTRY keys)
- Lowercase, underscores, no spaces
- Category prefix where helpful: `decade_50s_atomicstarburst_pure`
- Variation suffix: `_pure`, `_gradient`, `_halftone`, `_fill`, `_noise`, `_mix`, `_inverted`

### PNG File Names
- Match the pattern ID exactly: `decade_50s_atomicstarburst_pure.png`
- Stored in `assets/patterns/[category]/`

### UI Display Names
- Title Case, human readable: "50s Atomic Starburst (Pure)"
- Variation in parentheses

---

## COMMON MISTAKES TO AVOID

1. **Editing electron-app files directly** — They get overwritten. Edit V5 root only.
2. **Forgetting `npm run copy-server`** — Your changes won't show in the running app.
3. **Testing with .exe instead of hot Python** — The .exe doesn't pick up .py changes. Use `python server_v5.py`.
4. **Adding `"pattern-vivid"` to the lerp branch** — It must be in the POP branch. Double-check.
5. **Skipping regression tests** — Run `test_regression.py` after every section.
6. **Starting the next category before approval** — Ricky signs off on each category. Full stop.
7. **Using RGB PNGs** — Pattern images MUST be Grayscale mode. RGB will work but files are 3x larger and color channels have uneven luminance.

---

*End of task brief. Cursor: execute sections in order. Do not skip ahead.*
