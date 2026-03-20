# Toolbar, PNG Overlays & Drag‑Resize on Canvas — Roadmap

This doc answers: (1) toolbar improvements, (2) sponsors/numbers/custom PNG layers with layer-specific SPEC, (3) **drag and resize on the square car canvas** in real time.

---

## 1. Toolbar improvements (done / in progress)

- **Deselect** — Clear current zone’s drawn region and switch to Pick (or stay in current tool). Fits in ACTIONS.
- **Feather** — Soften selection edges (grow then shrink by N px to round corners). Fits in REFINE or right of Opacity.
- **Smooth** — Smooth jagged boundaries (shrink 1px then grow 1px). Fits in REFINE.
- **Grow 1px / Shrink 1px** — Finer steps next to existing Grow/Shrink.
- **Extra row or right-of-Opacity** — Use empty space right of Opacity/Mirror and right of Erase for the above so we don’t break layout.

All of these work with the existing zone/region mask model and don’t change the render pipeline.

---

## 2. PNG sponsors, numbers, custom livery (image overlay layers)

**Goal:** User adds a PNG (sponsor, number, livery) as a layer on top; that layer has its **own SPEC** (e.g. one gloss value for the whole decal) and doesn’t affect other zones.

**What exists today:**

- Zones are **color- or region-mask based**: each zone targets pixels (by color, wand, or drawn region) and applies a base/pattern/finish. There is no “image overlay” zone type that composites a PNG at a position.

**What’s needed:**

1. **Data model**
   - New zone type or layer type: e.g. `image_overlay` with `image_path` (or base64), `position_x`, `position_y` (0–1), `scale`, `rotation`, `spec_override` (single M/R/CC or “gloss” preset).
2. **UI**
   - “Add image layer” / “Add sponsor” that opens file picker → user selects PNG → layer appears in zone list (or a separate “Decals” list). Layer has: image thumbnail, position (X/Y), scale, rotation, **SPEC** (e.g. “Gloss”, “Matte”, “Same as zone”).
3. **Engine**
   - In `build_multi_zone` / compose: for each image-overlay layer, load the PNG, place it at position/scale/rotation in UV space, composite paint (blend with underlying), and apply a **single** spec value (or small spec map) for that layer only (no bleed into other zones).

**Feasibility:** Doable. The engine already composites zones by mask; an “image overlay” zone would use the PNG alpha as the mask and a constant (or simple) spec for that layer. No need to change how other zones work.

---

## 3. Drag and resize on the square car canvas

**Goal:** User “stamps” a pattern or image on the canvas and **drags it to move** and **drags corners/handles to resize** (and optionally rotate) in real time, instead of only sliders.

**What exists today:**

- **Place on map** already does **drag-to-position** for the **primary pattern** (and 2nd–5th base overlays): when “Place on map” is set, an overlay is shown and the user drags it; that updates `patternOffsetX`, `patternOffsetY` (and equivalent for other layers). So **position** is already draggable.
- **Scale and rotation** are still slider/input only; there is no on-canvas resize handle or rotate handle.

**What’s needed for full “drag and resize on canvas”:**

1. **Visual**
   - When a zone has a pattern (or image overlay) and “Place on map” is active, draw a **bounding box** (and optional rotation handle) on the canvas around the positioned content, so the user sees what they’re moving.
2. **Hit-testing**
   - Detect mousedown on (a) the “content” area → drag to move, (b) corner handles → drag to resize (scale), (c) rotation handle → drag to rotate. Use the same offset/scale/rotation that the engine already uses (`patternOffsetX/Y`, `scale`, `rotation`).
3. **State sync**
   - On drag/resize/rotate, update the zone’s `patternOffsetX`, `patternOffsetY`, `scale`, `rotation` (and for image overlays the same fields). The existing preview and render already use these, so **no engine change** for pattern placement—only UI.
4. **Optional: resize handles**
   - Corners (and maybe edge midpoints) of the bounding box; drag to change scale and optionally aspect ratio. If we keep aspect ratio locked, one drag updates a single `scale` value.

**Feasibility:** **Yes.** The pipeline already supports position, scale, and rotation per zone/layer. The missing piece is **on-canvas interaction**: draw the box and handles, and on mousedown/mousemove/mouseup update the same numbers that the sliders set. That’s a front-end change in the canvas/overlay logic (e.g. in `paint-booth-3-canvas.js` and the placement overlay in `paint-booth-2-state-zones.js`), and does not require changing the engine’s compose or build_multi_zone.

**Risk / “don’t break anything”:** Keep the existing slider/position inputs in sync with the drag state (single source of truth: zone’s `patternOffsetX/Y`, `scale`, `rotation`). When the user drags, update those; when they type in the panel, update the overlay. No duplicate state.

---

## 4. Suggested order of work

| Phase | What | Notes |
|-------|------|--------|
| **1** | Toolbar: Deselect, Feather, Smooth, Grow/Shrink 1px | Low risk, immediate value. |
| **2** | On-canvas resize/rotate handles for “Place on map” | Reuse existing placement drag; add box + handles and sync scale/rotation. |
| **3** | Image overlay layer type (PNG + layer-specific SPEC) | New zone type + UI + engine branch for image composite. |

Phase 1 is done or in progress. Phase 2 makes “drag and resize on the canvas” real without touching the render engine. Phase 3 unlocks sponsors/numbers/custom liveries with their own SPEC.
