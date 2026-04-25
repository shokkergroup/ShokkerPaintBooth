# TOOLS WAR — Tonight's Task Board

Heenan Family overnight shift — Tools-first reframe.
Top product goal: a painter can do real work in SPB without bouncing to Photoshop.

## Tool Inventory (canvasMode values)

### Selection tools
- `rect` — rectangular marquee
- `ellipse-marquee` — elliptical marquee
- `lasso` — freehand lasso
- `wand` — magic wand (color similarity)
- `selectall` — select all matching color globally
- `edge` — edge-detect selection
- `pen` — pen/path

### Region/spatial mask tools
- `brush` — paints zone region mask
- `spatial-include` / `spatial-exclude` / `spatial-erase` — refines color-based zones

### Pixel paint tools (route to layer if `isLayerPaintMode()`)
- `colorbrush` — paint color
- `recolor` — recolor matching pixels
- `smudge` — smudge tool
- `clone` — clone stamp
- `pencil` — hard-edge pencil
- `dodge` / `burn` — dodge & burn
- `blur-brush` / `sharpen-brush` — blur/sharpen brushes
- `history-brush` — paint from history snapshot

### Tool-agnostic ops (route via `isLayerEditTarget()`)
- `fill` — bucket fill
- `gradient` — gradient
- `erase` — erase mode (gates via inline `isLayerPaintMode` check)
- Edit > Fill / Edit > Delete (selection-fill / selection-delete)

### Other
- `eyedropper` — color picker
- `text` — text tool (creates layer)
- `shape` — shape tool (creates layer)

## Trust matrix (audit)

| Tool | Layer-local routing | Undo | Cursor | Status toast | Modifier keys |
|---|---|---|---|---|---|
| colorbrush | gate | per-stroke | crosshair | (none on stroke) | Shift=line |
| recolor | gate | per-stroke | crosshair | (none on stroke) | — |
| smudge | gate | per-stroke | crosshair | (none on stroke) | — |
| clone | gate | per-stroke | crosshair | source toast | Alt=set source |
| pencil | gate | per-stroke | crosshair | (none on stroke) | — |
| dodge/burn | gate | per-stroke | crosshair | (none on stroke) | — |
| blur/sharpen brush | gate | per-stroke | crosshair | (none on stroke) | — |
| history-brush | gate | per-stroke | crosshair | (none on stroke) | — |
| erase | gate | per-stroke | crosshair | (none on stroke) | Alt=temp eraser |
| fill | inline gate | per-op | crosshair | "Filled X pixels w/ color → target" | — |
| gradient | inline gate | per-op | crosshair | (gradient toast) | — |
| rect/ellipse/lasso | (no layer routing — selection only) | zone undo | crosshair | (selection toast) | Shift=add, Alt=subtract |
| wand | (selection) | zone undo | crosshair | (selection toast) | Shift=add |
| edge | (selection) | zone undo | crosshair | (selection toast) | — |
| brush (zone mask) | (no layer routing) | zone undo | crosshair | — | — |
| spatial-include/-exclude/-erase | (no layer routing) | zone undo | crosshair | — | — |
| text | creates layer | layer-stack push | text cursor | "Text added as layer" | — |
| shape | creates layer | layer-stack push | crosshair | "Shape added as layer" | — |
| eyedropper | (sample only) | none | crosshair | "Picked color" | Shift=add to swatches |

## Identified TOOLS WAR gaps to address

1. **Brush-stroke tools (colorbrush/recolor/smudge/etc.) emit no completion toast.** Painters lose feedback.
2. **Cursor consistency** — all set 'crosshair' but real Photoshop varies (brush ring, eyedropper droplet, smudge finger). Beyond scope tonight; flag as future.
3. **Modifier-key consistency** — Shift means different things across tools (line for brushes, add for selections). Documented but not surfaced as UI hint.
4. **Eraser doesn't show its toast** when run on a layer. The user can't tell whether the erase landed on layer or composite.
5. **Brush size/opacity/hardness** — every tool reads from `brushSize`, `brushOpacity`, `brushHardness` inputs. Need to verify ALL tools honor opacity and hardness.
6. **Clone source not visualized at cursor.** Clone-tool users in Photoshop see the source-area preview at the cursor; SPB just shows a static crosshair until source is set.
7. **Tool switch mid-stroke**: does isDrawing get cleaned up?
8. **Text-tool commit on Esc cleans up properly?**
