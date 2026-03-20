# Rebuilding and Overriding Patterns

This doc covers how patterns render on the car, why some (e.g. Snake Skin) look great and how to get your **custom image patterns** and **rebuilt replacements** to look just as good.

---

## Why some patterns look great (e.g. Snake Skin)

Patterns like **Snake Skin**, **Carbon Fiber**, **Dragon Scale** are **procedural**: the engine generates them at **full zone resolution** with a `texture_fn`. So they’re always sharp and tile correctly. No PNG load, no stretch.

---

## Why image patterns used to look bad (and what we fixed)

Custom patterns (Decades, Music Inspired, upgraded smile, etc.) are **image-based**: a PNG is loaded, then scaled/tiled to the zone.

Previously:

- At **scale = 1** we **resized one copy** of the image to the full zone → one stretched, blurry pattern.
- Resize used **bilinear** only → softer edges when scaling.
- **Spec punch** (M_range / R_range) was low → pattern didn’t read clearly on the car.

**Fixes applied:**

1. **Scale = 1**: the image is **tiled** to fill the zone (no single stretched copy). If the image is larger than the zone, we crop the center. Result: crisp repeats.
2. **Resize**: when we do resize (e.g. for scale ≠ 1), we use **LANCZOS** for better quality.
3. **Spec punch**: image patterns now use **M_range = 50, R_range = 60** (was 30/40) so they read clearly on the car.

Your HQ PNGs should now render much closer to the procedural patterns in clarity and strength.

---

## Rebuilding patterns you don’t like (same ID, new art)

You can **replace** a built-in pattern with your own PNG so the same ID shows your art.

### Option A: Replace the PNG (image-based patterns only)

For patterns that are **already image-based** (e.g. in `assets/patterns/50s/`, `musicinspired/`, `_generated/`):

1. Find the pattern ID (e.g. `smilexx_pure_upgraded_tiled`) and its path in `engine/registry.py` (search for the ID; it will have `image_path`).
2. Replace the PNG file at that path with your new art. Keep:
   - **Same filename** (so the registry doesn’t need changes).
   - **Transparent background** for clean masks (or keep opaque if you want luminance-based).
   - **Reasonable resolution** (e.g. 512–1024 px per repeat) so tiling stays crisp.

Restart the server and run a clean boot so the new file is used.

### Option B: Add an image override for a procedural pattern

To **override a procedural pattern** (e.g. one you don’t like in a category) with your own PNG:

1. **Add your PNG** under `assets/patterns/_generated/` or a category folder, e.g.  
   `assets/patterns/_generated/my_snake_style.png`.
2. **Register it** in `engine/registry.py` in the image-pattern block:
   - Either give it a **new ID** (e.g. `snake_skin_custom`) and add that ID to `paint-booth-1-data.js` in the right `PATTERN_GROUPS` so it appears in the UI.
   - Or **override the existing ID**: in `engine/registry.py`, after the main `PATTERN_REGISTRY` is built from the monolith, add a line that sets that ID to an image_path entry (same structure as other image patterns: `image_path`, `paint_fn`, `desc`). That makes the engine use your PNG instead of the procedural `texture_fn` for that ID.

Example override (in `engine/registry.py`, after pattern_reg is built):

```python
# Override a procedural pattern with custom PNG
pattern_reg["some_id_you_dont_like"] = {
    "image_path": "assets/patterns/_generated/my_replacement.png",
    "paint_fn": paint_none,
    "desc": "Custom replacement for some_id_you_dont_like",
}
```

3. **UI**: If you used a **new** ID, add it to the right group in `paint-booth-1-data.js` (`PATTERNS` and `PATTERN_GROUPS`). If you **overrode** an existing ID, the UI already shows that ID; no JS change needed.
4. Restart server (and clean boot) so the new registry is loaded.

---

## Adding new custom patterns (new IDs)

1. **PNG**: Put the file in `assets/patterns/_generated/` or a category folder (e.g. `assets/patterns/musicinspired/`). Prefer **transparent background** for clean car render.
2. **Backend**: In `engine/registry.py`, add an entry in the image-pattern list (same format as existing `_img_pats` or the `smilexx_pure_upgraded` block) with your new ID and `image_path`.
3. **Front-end**: In `paint-booth-1-data.js`, add the ID to `PATTERNS` (and optionally `swatch_image` if you want a client-side thumbnail) and to the right `PATTERN_GROUPS` so it appears in the picker.
4. Restart server and do a clean boot.

---

## Listing patterns by category (script)

To see which pattern IDs live in which category (so you can pick what to rebuild), run:

```bash
python scripts/list_patterns_by_category.py
```

That prints pattern IDs grouped by the UI categories (Decades, Music Inspired, etc.) so you can choose “ones I don’t like in certain categories” and replace them as above.

---

## Quick checklist for “custom pattern looks bad on car”

- **Clean boot**: Run `python server_v5.py` so no old process is serving (clean_boot frees the port and stops other Shokker servers).
- **Scale**: Try scale **1.0** first (crisp tiling). Then adjust scale slider if you want more/less repeats.
- **File**: PNG is in the path registered in `engine/registry.py`; transparent background preferred.
- **UI**: Pattern ID is in `paint-booth-1-data.js` and in a `PATTERN_GROUPS` so it’s selectable.
