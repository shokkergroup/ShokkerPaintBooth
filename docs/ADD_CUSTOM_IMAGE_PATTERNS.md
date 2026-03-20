# Adding Custom Image Patterns (Flames, Tribal, Your Art)

You can add **real pattern art** (flames, tribal, logos, etc.) so they appear in the pattern picker and render correctly on the car. The app supports two ways patterns are made:

1. **Procedural** — Code draws the pattern (e.g. many “flame” entries share the same lava flow code). Good for variety but not “your” art.
2. **Image-based** — A PNG (or image you convert to PNG) is used as the pattern. **This is how you use your own JPGs / artwork.**

---

## What you need

- **Image**: JPG is fine for you; the pipeline expects **PNG**. Easiest: export/save as PNG from any editor (Photoshop, GIMP, etc.). Use **grayscale or RGB**; the engine uses luminance (bright = pattern shows, dark = base shows). Transparent PNGs work: alpha is used when present.
- **Name**: A short **id** (e.g. `tribal_flame_custom_1`, `my_flame_01`). Use lowercase, underscores, no spaces.

---

## Option A — One pattern at a time (you pick the art)

1. **Prepare the image**
   - Save as PNG (e.g. `my_flame.png`).
   - Prefer a **tileable** design if you want it to repeat; otherwise it will be tiled or cropped to fit the zone.
   - Bright areas = pattern visible; dark = base shows through.

2. **Put the file in the right folder**
   - Create a category folder if needed, e.g. `Shokker Paint Booth V5/assets/patterns/flames/` or `tribal/`.
   - Save your PNG there with the **id** as the filename: `my_flame.png`.

3. **Ask the agent (or do it yourself)**
   - “Add image pattern: id = `my_flame`, category = `flames`, display name = `My Flame`.”
   - The agent will add:
     - **Backend**: One entry in `engine/registry.py` (in the image-pattern list) pointing to `assets/patterns/flames/my_flame.png`.
     - **Front-end**: One entry in `paint-booth-1-data.js` in `PATTERNS` (id, name, desc, swatch) and, if you use categories, in the right section (e.g. “Flames — Custom” or “Tribal”).

4. **Restart / refresh**
   - Restart the server (or Electron app) and refresh the UI. The new pattern appears in the picker and renders like the existing Decades/Music Inspired image patterns.

---

## Option B — Batch: “Make X slots in Y category”

- Ask: “Add 5 image pattern slots in category **Flames** and 5 in **Tribal** with placeholder paths.”
- The agent adds registry + UI entries with IDs like `flame_custom_1` … `flame_custom_5` and `tribal_custom_1` … `tribal_custom_5`, and paths like `assets/patterns/flames/flame_custom_1.png`.
- You (or a designer) then **drop in PNGs** with those exact filenames. No code change needed per image.
- Until the PNG exists, the app can use a fallback from `assets/patterns/_placeholders/<id>_placeholder.png` if you add one; otherwise that slot will show missing until the file is added.

---

## Technical details (for agents / devs)

- **Registry**: `engine/registry.py` — extend the `_img_pats` list with `(category, id)` or add a new block like the existing Decades/Music one. Each entry gets `image_path`: `assets/patterns/<category>/<id>.png`, `paint_fn`: `paint_none`, `desc`.
- **UI**: `paint-booth-1-data.js` — add to `PATTERNS` and, if using sections, to the right `SPECIALS_SECTIONS` / category list (e.g. “Flames — Custom”, “Tribal — Custom”).
- **Loader**: `engine/render.py` — `_load_image_pattern()` loads PNG (PIL); supports RGBA (uses alpha when transparent, else luminance). Tiling, scale, and rotation are applied in compose.

---

## Summary

| You want… | Do this |
|-----------|--------|
| One pattern from a JPG I have | Save as PNG, put in `assets/patterns/<category>/<id>.png`, then ask to add one pattern with that id/category/name. |
| Several slots for my own art | Ask for “X slots in category Y”; add PNGs with the given filenames. |
| Text/mood suggestions | Describe the look (e.g. “aggressive tribal”, “soft flame fade”); we can name and categorize slots; you supply the final art as PNG. |

The agent **cannot generate or edit the image**. It can wire any PNG you provide into the app so it behaves like the existing image patterns (scale, rotate, position, intensity).
