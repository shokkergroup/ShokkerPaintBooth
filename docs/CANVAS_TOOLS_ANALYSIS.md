# Canvas Tools — Analysis & Photoshop/GIMP Alignment Plan

**Goal:** Make the zone drawing/selection panel work like Photoshop or GIMP: reliable tools, familiar shortcuts, everything undoable (Ctrl+Z), and selections that reliably transfer into zones. Support multiple drawn/selected areas per zone (like multiple color options).

---

## What Stays As-Is (Working)

| Feature | Behavior | Notes |
|--------|----------|--------|
| **Pick (eyedropper)** | Click canvas → grab color; show in swatch/hex. | Simple, works. |
| **ADD at bottom** | In zone detail: "Add Color" uses current picker/hex and adds to zone's `colors[]`. | Easiest way to add a color to a zone. Keep. |
| **Spatial Include / Exclude** | Select a zone → paint green (include) or red (exclude) on canvas → refines which pixels count for that zone's color match. | Works; draw region then colors picked only in that area. Keep. |

---

## Current Tools — What Exists vs What’s Broken

### Selection tools (apply to **current zone’s** `regionMask`)

| Tool | Current behavior | Issues |
|------|------------------|--------|
| **Wand** | Flood-fill by color tolerance; Shift=add, Alt=subtract. Contiguous checkbox. | Works; UX unclear (modifier hints not in toolbar). No keyboard shortcut. |
| **Select All** | Select every pixel matching clicked color (non-contiguous). | Works; no shortcut. |
| **Edge** | Flood fill that stops at Sobel edges. | **Bug:** Called with 5 args `(..., addToExisting, subtractMode)` but function only takes 4; subtract never applied. No shortcut. |
| **Rect** | Drag rectangle; Shift=square. Can be "color-aware" (only fill pixels matching eyedropper in rect). | Document-level mouseup can commit with wrong fill (always 1 in doc handler). Replace/add/subtract from selection mode not applied in doc-level mouseup. |
| **Lasso** | Click to add vertices; double-click to close and fill. Right-click = undo last point. Backspace (in 6-ui-boot) cancels lasso. | Add/replace/subtract from dropdown works. No P/GIMP-style shortcut (L). |

### Drawing tools

| Tool | Current behavior | Issues |
|------|------------------|--------|
| **Brush** | Paint into zone’s regionMask (value 1). | Works; no shortcut. |
| **Erase** | Paint 0 into regionMask. | Works; no shortcut. |

### Undo / Redo

| Action | Current behavior | Issues |
|--------|------------------|--------|
| **Ctrl+Z** | If `undoStack` (draw/mask) has entries → `undoDrawStroke()`. Else → `undoZoneChange()`. | Good: draw undo first. |
| **Ctrl+Shift+Z / Ctrl+Y** | Only `redoZoneChange()`. | **No redo for draw/mask** — once you undo a stroke, you can’t redo it. |
| **Spatial stroke undo** | "Undo last spatial stroke" button; no Ctrl+Z for spatial. | Spatial could push to same undoStack or a separate one; currently button-only. |

---

## Photoshop / GIMP Shortcuts to Support

| Shortcut | PS/GIMP | Intended action |
|----------|---------|------------------|
| **Ctrl+Z** | Undo | Undo last draw/mask action, else zone config. ✅ Already. |
| **Ctrl+Shift+Z** / **Ctrl+Y** | Redo | Redo zone config; **add:** redo draw/mask when applicable. |
| **Escape** | Cancel | Deselect / cancel lasso / close panels. **Add:** cancel active lasso, cancel rect drag. |
| **P** | Pick / Eyedropper | Set canvas mode to eyedropper. |
| **W** | Magic Wand | Set canvas mode to wand. |
| **L** | Lasso | Set canvas mode to lasso. |
| **B** | Brush | Set canvas mode to brush. |
| **R** | (PS: Smudge / GIMP: Rotate) | We use **R** for Randomize zone; **rect** can use **O** or keep **R** for Rect (toolbar says "R"). Prefer **O** for Rect to avoid clash, or keep R=Rect and move Randomize to another key. |
| **E** | Eraser | Set canvas mode to erase. **Conflict:** we use E for zone editor panel. Use **X** for Erase (GIMP uses X to swap fg/bg; PS uses E for eraser). Toolbar already says "X" for Erase. |
| **X** | (PS: swap fg/bg) | We use **X** for Erase. ✅ Keep. |
| **A** | Select All (color) | Set canvas mode to selectall. |
| **Shift+click** | Add to selection | Wand/rect/lasso: add to existing. ✅ In code. |
| **Alt+click** | Subtract from selection | Wand: subtract. ✅ In code. Lasso/rect: subtract when mode or modifier. |

**Recommended mapping (no conflict with app):**

- **P** = Pick (eyedropper)  
- **W** = Wand  
- **A** = Select All Color  
- **B** = Brush  
- **O** = Rect (rectangle) — avoid R vs Randomize  
- **L** = Lasso  
- **X** = Erase  
- **E** = keep for Zone Editor panel toggle (don’t use for Erase)  
- **R** = keep for Randomize zone  

Edge tool: **G** (as in “edge”) or keep unassigned and only toolbar.

---

## Panel UX (Photoshop-like)

1. **Selection mode**  
   Dropdown already exists (Add / Replace / Subtract). Show it whenever a selection tool is active; label clearly “Add (+)” / “Replace” / “Subtract (-)”.

2. **Modifier hints**  
   In toolbar or under canvas: “Shift+click = add to selection, Alt+click = subtract” when Wand / Select All / Edge / Rect / Lasso are active.

3. **Contiguous**  
   Only for Wand / Select All; already shown. Keep.

4. **Tolerance**  
   One slider for Wand / Select All / Edge. Already shared. Keep.

---

## Region vs Spatial Selection

| Term | What it is | When to use |
|------|------------|-------------|
| **Drawn region / Region** | Rectangle, lasso, brush, or wand selection stored in the zone’s `regionMask`. | You want the zone to apply **only** in that area; no color matching. Draw → "Using Region" → set base/finish → Render. |
| **Spatial Selection (Include/Exclude)** | Green (include) / red (exclude) painted into `spatialMask`. | You use **color matching** and want to refine where it applies: only in green areas, or everywhere except red. |

- **Region** = “paint this zone only inside my drawn shape.” The engine uses `region_mask` and ignores color for that zone.
- **Spatial** = “within my color match, only include/exclude these pixels.” The engine intersects color mask with `spatial_mask`.
- For an **empty zone** (no color) with a **drawn rectangle** and "Using Region", only the **region** matters; the INCLUDE/EXCLUDE toggle at the bottom does nothing because there is no color mask to refine. Just set base/finish and Render.

## Move / reshape selection

- **Nudge (implemented):** When the current zone has a drawn region, **Alt+Arrow** moves the selection 1 px; **Shift+Alt+Arrow** moves it 5 px. (Arrow without Alt still changes the selected zone.)
- **Not yet:** A “Move selection” mode: drag to translate the whole region; or drag handles to resize the rectangle.

---

## Transfer to Zones

- All selection/draw tools write into **the current zone’s** `regionMask` (or `spatialMask` for include/exclude).
- **Selected zone** = `selectedZoneIndex`. User must select the zone in the list first; then Wand/brush/rect/lasso apply to that zone.
- **Multiple areas per zone:**  
  Currently one `regionMask` per zone; “add to selection” (Shift+click or mode Add) ORs new pixels into the same mask. So multiple disconnected regions in one zone are already supported (e.g. wand click 1, Shift+wand click 2 → both areas in the same zone). No data model change needed; ensure UX makes “add another area to this zone” obvious (hints, selection mode, shortcuts).

---

## Implementation Phases

### Phase 1 — Shortcuts & Escape (quick wins)

- Wire **P, W, A, B, O, L, X** to set canvas mode (when canvas/tools are in context; skip when typing in inputs).
- **Escape:**  
  - Cancel active lasso (clear points, exit lasso).  
  - Cancel rect drag (discard, no commit).  
  - Already closes modals/panels; keep that.
- **R:** Keep for Randomize zone. **Rect** shortcut = **O** (and update toolbar tooltip to “Rect (O)”).

### Phase 2 — Undo/redo for draw/mask

- Add **redo stack** for draw/mask (mirror of undoStack).
- On `undoDrawStroke()`, push current state to redo stack before reverting.
- **Ctrl+Shift+Z** / **Ctrl+Y:** if redo stack has entries, pop and reapply draw state; else `redoZoneChange()`.
- Optionally: spatial stroke undo/redo in same stacks so Ctrl+Z undoes last spatial stroke too.

### Phase 3 — Fix edge and rect

- **Edge:** Add `subtractMode` to `edgeDetectFill`; when true, clear matching pixels from `regionMask` (same as wand subtract). Fix call site to pass subtractMode and use it.
- **Rect:** Document-level mouseup must use same logic as canvas mouseup: selection mode (add/replace/subtract) and color-aware fill when applicable. Single code path for “commit rect.”

### Phase 4 — Panel copy and hints

- Ensure selection mode dropdown is visible and clearly labeled for Wand, Select All, Edge, Rect, Lasso.
- Add a short hint line when a selection tool is active: “Shift+click add, Alt+click subtract.”
- Optional: add “Add to zone” / “Replace selection” / “Subtract from zone” as explicit buttons that set mode (like PS option bar).

### Phase 5 (optional) — Multi-region UX

- Already supported in data (one mask, multiple regions). Optional: “Add current selection to zone” as an explicit action (e.g. after lasso close, “Add to Zone 3” button) for clarity.
- Optional: show pixel count for current zone’s region in zone list (e.g. “Zone 2: 12,340 px”).

---

## File Map

| Change | File(s) |
|--------|--------|
| Tool shortcuts P/W/A/B/O/L/X, Escape (lasso/rect cancel) | `paint-booth-6-ui-boot.js` (keydown) and/or `paint-booth-3-canvas.js` if tool logic lives there |
| Draw/mask redo stack + Ctrl+Shift+Z / Ctrl+Y | `paint-booth-2-state-zones.js` (undo handler), `paint-booth-3-canvas.js` (pushRedo, redoDrawStroke) |
| Edge subtract + fix 5-arg call | `paint-booth-3-canvas.js` (`edgeDetectFill`, and call site) |
| Rect document mouseup use selection mode + color-aware | `paint-booth-3-canvas.js` (document mouseup handler, share commit logic) |
| Toolbar hints (Shift/Alt), selection mode visibility | `paint-booth-v2.html`, `paint-booth-2-state-zones.js` (zone detail / draw indicator) |
| Rect shortcut O, tooltips | `paint-booth-v2.html` (button title), shortcut in 6-ui-boot or 3-canvas |

---

## Summary

- **Keep:** Pick, ADD color, Spatial Include/Exclude.
- **Fix:** Edge subtract + call signature; Rect doc mouseup (selection mode + color-aware); redo for draw/mask.
- **Add:** P/W/A/B/O/L/X and Escape (cancel lasso/rect); modifier hints in UI.
- **Result:** One unified, Photoshop-like tool panel: same shortcuts, Ctrl+Z/Ctrl+Shift+Z on everything, selections and draws that reliably apply to the selected zone, with optional clearer “add another area” UX.
