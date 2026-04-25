# SPB Command Surface Matrix

**Built:** 2026-04-19 by Bockwinkel (research) + Windham (action) for Win #2 of TWENTY WINS shift.

## Ownership policy

- **Left rail** = primary tool selection (brush, erase, recolor, shape, marquee…)
- **Top strip** = session actions + transform controls (undo/redo/render/save/transform commit/cancel)
- **Right panels** = properties + per-layer / per-zone stack actions
- **Context menu** = quick mirror of session-relevant actions (Cut/Copy/Paste/Undo/Redo)
- **Layer dock** = mirror of layer-panel actions when a layer is active
- **Keyboard** = power-user accelerator for everything

## Verbs catalogued (~95 across 7 surfaces)

The full audit lives in the agent transcript for Win #2 (Bockwinkel). The matrix below captures the highest-impact items that were actually addressed this shift.

## Shipped this shift (Win #2 surgical fixes)

| Verb | Before | After | Why |
|---|---|---|---|
| **UI Scale (header L434–437)** | "Zoom In/Out (Ctrl+Plus/Minus)" — same shortcut hint as canvas zoom | "UI Smaller / UI Larger" — explicitly tells painter this scales chrome, NOT canvas | Pre-fix: Ctrl+Plus shortcut hint pointed at the wrong action. The Ctrl+Plus shortcut actually fires `canvasZoom('in')` (canvas.js L6192), not `setUIScale`. Painters following the tooltip tried to zoom the canvas with the toolbar buttons. |
| **Flip View H/V (left rail L621–622)** | "Flip Horizontal / Flip Vertical" — collided with Flip Layer / Flip Decal / Flip Placement (4 different fns, 1 label) | "Flip View Horizontal / Flip View Vertical" + tooltip explicitly says "preview only, does NOT modify pixels" | Painters who clicked Flip H expecting to flip a sponsor logo flipped the camera instead and lost orientation. |
| **Flip Layer H/V (top strip)** | "Flip H / Flip V" — same label as flip view | "Flip Layer H / Flip Layer V" + tooltip "destructive — undo with Ctrl+Z" | Disambiguation. |
| **Flip Decal H/V (decal panel)** | "Flip H / Flip V" — same label as flip view | "Flip Decal H / Flip Decal V" via title attribute | Disambiguation. |
| **Flip Placement H/V (manual placement bar)** | "Flip H / Flip V" — same label as flip view | "Flip Placement H / Flip Placement V" | Disambiguation. |
| **Zone Mask ← Layer (layer panel row)** | Label "MASK CURRENT ZONE" on layer-panel row, top-strip says "Zone Mask ← Layer" — same fn, two labels | Both surfaces now say "Zone Mask ← Layer" | One verb, one name. |
| **Undo/Redo (left rail L535–536)** | Generic tooltip | Tooltip now mentions context menu + Ctrl+Z/Y as the canonical surfaces ("convenience mirror") | Demoted without removing — preserves muscle memory while signalling ownership. |

## Logged but not shipped (deferred to future shifts)

- **Add visible Copy/Cut/Paste buttons to top strip.** Currently they're keyboard-only (Ctrl+C/X/V) + context-menu-only. New painters never find them. Future polish.
- **Decide the fate of left-rail Color Harmonies / Palettes / Quick Export buttons.** They're not tools — they belong in the right-panel "Color Tools" section. Out of scope tonight.
- **Disambiguate "Apply" (top-strip transform commit)** → "Commit Transform". Bockwinkel flagged but the action is short-lived and only appears during transform — minor.
- **Promote `Ctrl+J` (New Layer via Copy) and `Ctrl+Shift+N` (New Blank Layer)** to layer-panel header buttons. Layer panel already has "+ Layer" import — the New Blank shortcut isn't visible.
- **Header "Keyboard Shortcuts (?)" duplicates left-rail bottom + render-bar.** Pick one (header) and remove the others. Minor.

## How to extend

Future agents adding a new command:

1. Decide its primary owner per the policy above.
2. If it appears on a secondary surface, the secondary tooltip MUST say "Also available via &lt;canonical surface&gt; or &lt;keyboard shortcut&gt;".
3. If two surfaces use different labels for the same `onclick=` handler, that's a bug — pick one.
4. Tool tip language: ACTION (SHORTCUT) — short description. No marketing prose, no emoji-only labels.

## Tests

`tests/test_layer_system.py::test_command_surface_label_truthfulness` — ratchet that:

- Confirms the UI Scale buttons are labeled "UI Smaller/Larger" (not "Zoom In/Out").
- Confirms `flipViewH` / `flipViewV` tooltips contain "View" so they don't claim to flip pixels.
- Confirms `selectLayerPixels` is labeled "Zone Mask ← Layer" in both the layer panel row and the top-strip context bar.
