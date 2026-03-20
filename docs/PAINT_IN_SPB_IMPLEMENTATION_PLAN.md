# Paint in SPB — Implementation Plan

**Goal:** Make Shokker Paint Booth feel like you can "kind of paint the car" right inside the app — purpose-built for car painting, one-stop shop from load to render. Small steps, ship with Alpha, then iterate.

---

## Alpha slice (next couple of days)

**Ship this:** Decals & Numbers visible on the car canvas, draggable in real time. Users can add PNGs and number decals, see them on the map, and drag them into position. Optional: decals included in render (if easy to wire).

| Step | What | Files | Notes |
|------|------|--------|--------|
| **A1** | Re-enable Decals & Numbers panel | `paint-booth-v2.html` | Replace the comment at ~755 with a compact panel: section "Decals & Numbers", **Import PNG** (calls `importDecal()`), **Add Number** (expandable: text, color, outline, font, size; **Add** calls `addNumberDecal()`). List area with `id="decalLayerList"`, count `id="decalCount"`. Each row: thumbnail, name, scale/opacity/rotation sliders (call existing `setDecalScale(idx,v)` etc.), visibility toggle, remove. Uses existing IDs so `paint-booth-6-ui-boot.js` needs no change for list rendering. |
| **A2** | Draw decals on the canvas overlay | `paint-booth-3-canvas.js` | In `_doRenderRegionOverlay()`, after `ctx.putImageData(imgData, 0, 0);`, add: `if (typeof drawDecalsOnContext === 'function' && typeof decalLayers !== 'undefined' && decalLayers.length > 0) { drawDecalsOnContext(ctx, regionCanvas.width, regionCanvas.height); }`. Removes the "Decal overlay disabled" comment. Decals then appear on top of the zone overlay on the **same** car canvas. |
| **A3** | Wire decal drag to the paint canvas | `paint-booth-3-canvas.js` | In the canvas mousedown handler (where you already check placement drag), **before** or **after** placement: if not doing placement drag and `typeof checkDecalDrag === 'function'` and `checkDecalDrag(canvasX, canvasY)` returns true, set a flag (e.g. `_decalDragActive = true`) and store start. On mousemove: if `_decalDragActive` call `updateDecalDrag(canvasX, canvasY)`. On mouseup: if `_decalDragActive` call `endDecalDrag()`, clear flag. Convert event coordinates to canvas pixel coords (same as other tools). Result: user can drag decals on the **square car canvas** in real time. |
| **A4** | (Optional) Decals in render | `paint-booth-5-api-render.js` + server | If the render API sends a **file path** for paint: before calling render, if `typeof compositeDecalsForRender === 'function'` and decals exist, get composite canvas, export to blob, upload to a temp path or send as multipart, and use that path for render. If the server only reads from disk, may need a small server endpoint to accept a paint image body and write to temp. Defer to post-Alpha if time-critical. |

**Acceptance for Alpha:** User can open "Decals & Numbers", import a PNG or add a number, see it on the car canvas, and drag it to position. No regression to zones, placement, or brush/wand.

---

## Phase 1 — Right after Alpha (quick wins)

| Step | What | Notes |
|------|------|--------|
| **P1.1** | Placement banner clarity | In `paint-booth-v2.html` (and `updatePlacementBanner` copy), make the banner say e.g. "Drag the **pattern** on the **car map** (left) to position it." So it's obvious the left canvas IS the car map. |
| **P1.2** | Decals in render (if not in Alpha) | Wire `compositeDecalsForRender()` into the render path so final output includes decals. |
| **P1.3** | Save/load decals in .shokk | In `paint-booth-2-state-zones.js` (or 7-shokk), extend config object to serialize `decalLayers` (name, image as data URL or path, x, y, scale, rotation, opacity, visible). Load and restore in `loadConfigFromObj` / save in `getConfigForSave`. |

---

## Phase 2 — Transform on canvas (drag + resize + rotate)

| Step | What | Notes |
|------|------|--------|
| **P2.1** | Bounding box for placement overlay | When "Place on map" is active (pattern or base), draw a **rectangle** around the current pattern overlay on the **same** overlay div (or on region canvas with pointer-events). Use zone's `patternOffsetX/Y`, `scale`, `rotation` to compute corners. Stroke only, no fill. So user **sees** what they're moving. |
| **P2.2** | Resize handles (pattern) | Draw small handles at corners (and optionally edges) of that box. On mousedown on handle: drag to change scale (and optionally rotation). Update zone's `scale` and `rotation`; keep position as center or one corner. Single source of truth: zone state; sliders stay in sync. |
| **P2.3** | Same for decals | Each decal already has x, y, scale, rotation. When a decal is "selected" (e.g. last added or click-to-select), draw its bounding box + handles on the canvas. Drag body = move (existing). Drag corner = resize; drag rotate handle = rotate. Reuse same pattern as P2.1/P2.2. |

---

## Phase 3 — Decals as first-class (spec + library)

| Step | What | Notes |
|------|------|--------|
| **P3.1** | Decal → zone or spec override | Give each decal layer an optional **spec** (e.g. Gloss / Matte / Same as below). Engine: treat decal as a single mask (PNG alpha) and apply one spec value to that region. Data: add `specPreset` or `specOverride` to each decal; server receives decals + spec and composites. |
| **P3.2** | Decal library panel | "Project assets" or "My decals": grid/list of imported PNGs + number presets. Click to preview; **drag from panel onto canvas** to add at drop position. Improves discoverability and "grab and place" feel. |

---

## Phase 4 — Polish and purpose-built differentiators

| Step | What | Notes |
|------|------|--------|
| **P4.1** | Gradient position on canvas | If engine supports gradient origin/angle: show a draggable (and rotatable) representation on the car map for "Base (gradient/duo)" when Place on map = base; drag to align gradient per car. |
| **P4.2** | Stretch (non-uniform scale) | If engine supports scaleX/scaleY, add aspect-ratio handle or separate horizontal/vertical resize. Otherwise keep uniform scale. |
| **P4.3** | Car-paint-specific UX | E.g. "Align to hood", "Mirror to other side", or presets for common placements (door number, roof number). Optional based on feedback. |

---

## User vision (post-Alpha): “Like Photoshop on the Source layer”

**Simplify decals UI**
- One control: **Import File** only. Remove the separate “Add Number” generator. Numbers, sponsors, decals all come in via Import File (PNG, etc.). The built-in number generator can be dropped or hidden.

**Transform on Source layer (decals)**
- When an imported decal is **selected**, show a **bounding box** on the car map (SOURCE) with:
  - **Drag** the content to move (already in place; ensure it’s obvious and reliable).
  - **Handles**: corners to scale, optional rotate handle to rotate.
  - **Flip / Mirror**: Flip H, Flip V (or mirror) so the decal can be flipped without leaving the canvas.
- **Commit** (or “Done”): deselect so the box goes away and the decal is “placed.” No more transform handles until the user clicks the decal again.
- **Re-activate**: Click on a decal (or pick it from the list) to select it again and show the box so the user can move/scale/rotate/flip again.
- Single source of truth: decal’s `x, y, scale, rotation`, plus a `flipH` / `flipV` if we add them. Sliders in the panel stay in sync with the box.

**Magic eraser (background removal)**
- For an **imported decal**, allow “magic eraser” behavior: e.g. click (or brush) on the background (e.g. white behind a number) to make that area transparent. Implementation options: (a) per-decal alpha mask: wand/brush that sets alpha to 0 where the user clicks/paints; (b) “remove background by color” with tolerance so all pixels near that color become transparent. This is **per decal layer**, not the main paint. Needs a mode like “Decal: Magic Eraser” and storage of a modified alpha or a second mask for that decal.

**Recolor decal by color picker (“smart object”)**
- For a **selected decal**, allow “pick color on this decal” and “recolor to new color”: e.g. click inside the number to sample color, then choose a new color and replace all pixels of that color (within tolerance) on that decal. Result: recolor the number/sponsor without leaving SPB. Implementation: sample at click → build a mask of similar pixels on the decal’s image → replace those pixels with the new color (or a blend). Can be a “Recolor” sub-mode when a decal is selected.

**Car mask layer (overlay only)**
- **Import car masks** (e.g. one PNG per car/template) and **toggle them on/off** as an overlay on top of the SOURCE view. They are **not** part of the paint or spec at all — purely visual so the user can see how the car lays out (hood, door, roof, etc.) while painting or spec mapping. Implementation: a separate list “Car masks” (or “Layout overlays”), load PNG, draw on top of the canvas with e.g. 50% opacity and a distinct color/tint, checkbox to show/hide each. Stored in config so they can be saved per project/car.

---

## Order summary (revised)

- **Alpha (done):** A1–A4 (decals panel, draw on canvas, drag on canvas, decals in render).
- **Next (high impact):**  
  1. **Simplify to “Import File” only** (remove or hide Add Number).  
  2. **Decal transform on Source:** select decal → bounding box, drag (verify/fix), corner handles (scale), rotate handle, Flip H/V, **Commit** to deselect, **click decal again** to re-activate.  
  3. **Smarter default placement:** e.g. place new import at center of viewport or last drop position instead of fixed (100, 100).
- **Then:** Magic eraser (per-decal background removal), Recolor by color picker (per-decal), Car mask layer (toggleable overlay).

This gets “paint the car in SPB” to feel like Photoshop on the Source layer: one import path, move/scale/rotate/flip on canvas, commit and re-edit, then optional eraser, recolor, and mask overlay.
