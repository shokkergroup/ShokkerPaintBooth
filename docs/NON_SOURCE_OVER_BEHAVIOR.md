# Non-Source-Over Layer Behavior — Decisions

Workstream 4 (#69–#71) of the Heenan Family Overnight Sprint.

This document captures **the decided semantics** for layers that use a blend
mode other than `source-over` (a.k.a. "Normal" in Photoshop): multiply,
overlay, screen, destination-out (knockout), etc. The decision is to keep
current behavior; the value of this doc is making that behavior explicit so
later contributors don't accidentally "fix" something that's intentional.

## TL;DR

- **Layer effects always render in source-over composite mode.** The host
  layer's blend mode does NOT propagate into its drop shadow / outer glow /
  stroke / color overlay / bevel.
- **The host layer's pixels DO use the host blend mode.** A layer with
  multiply blend stays multiply; only its effect halos render normally.
- **Restrict-To-Layer treats non-source-over upper layers as semi-visible.**
  A multiply/overlay/screen layer above the source layer does NOT count as
  "hiding the source" because it modulates rather than overrides.
- **Knockout (destination-out) is special.** Setting blend mode to
  destination-out via `knockoutLayer()` punches the layer's shape THROUGH
  layers below; that's the intended "cutout" workflow.

## Current Code Anchor Points

- `paint-booth-3-canvas.js : recompositeFromLayers` (~line 9212):
  - Sets `ctx.globalCompositeOperation = layer.blendMode || 'source-over'`
    BEFORE drawing `layer.img`.
  - Resets to `source-over` AFTER drawing the layer image.
  - `renderLayerEffects(ctx, layer, 'before')` runs BEFORE the blend mode is
    set → drop shadow / outer glow always render in source-over.
  - `renderLayerEffects(ctx, layer, 'after')` runs AFTER the reset →
    stroke / color overlay / bevel also render in source-over.
- `paint-booth-3-canvas.js : renderLayerEffects` (color overlay branch ~9214):
  - Color overlay can OPT-IN to its own blend mode via `effects.colorOverlay.blendMode`,
    independent of the host layer's blend mode.
- `paint-booth-3-canvas.js : getLayerVisibleContributionMask` (line ~9030):
  - Only `source-over` and `normal` layers above the source count as "hiding"
    pixels. `if (layer.blendMode && layer.blendMode !== 'source-over' && layer.blendMode !== 'normal') continue;`

## Intended Semantics

| Combo | Behavior | Why |
|---|---|---|
| `multiply` layer + drop shadow | Shadow renders in source-over BENEATH the layer; layer pixels then multiply through what's already on the canvas. | Photoshop default — "Blend Interior Effects as Group" is off. |
| `overlay` layer + stroke | Stroke renders in source-over AROUND the layer; layer pixels then overlay onto the canvas. | Same. |
| `screen` layer + outer glow | Glow renders source-over BENEATH; layer pixels screen on top. | Same. |
| `destination-out` (knockout) layer + any effect | Effect renders source-over; the destination-out punches through layers below. | Intentional — knockout is for cutting holes, e.g., for sponsor windows in a livery. |
| Source-layer restriction with a `multiply` layer above | Source layer is still "contributing" — pixels selectable by Restrict-To-Layer. | Multiply doesn't replace the source's pixels; it modulates them, so the source is still visually present. |
| Source-layer restriction with a fully-opaque `source-over` layer above | Source layer is "hidden" by that pixel; Restrict-To-Layer skips it. | A normal opaque layer truly hides the source. |

## What We Did NOT Do

- We did NOT add blend-mode-aware effect rendering. That would require a
  per-effect "Blend Interior Effects as Group" toggle in the dialog, plus
  a non-trivial reworking of `renderLayerEffects` to wrap the entire
  layer+effects unit before applying the layer blend mode.
- We did NOT add warnings for "unsupported" combos. The current behavior
  is well-defined for every combo; nothing is unsupported. Adding warnings
  would just be noise.

## How To Verify In The Running App

1. Import a PSD with at least 3 layers.
2. Select a middle layer; set its blend mode to `multiply`.
3. Apply a drop shadow (effects dialog).
4. Recomposite should show: shadow renders in normal (source-over) mode
   BENEATH the layer; the layer's pixels multiply through the canvas
   beneath them.
5. Switch the layer's blend mode through `overlay`, `screen`. Shadow
   stays the same color; only the layer's host pixels change appearance.
6. Toggle the same layer's `destination-out` (Knockout button). The layer
   pixels now punch a hole; the shadow still renders normally below.

## Tests

Source-text guards exist in `tests/test_layer_system.py` for:
- The blend-mode reset between layer draw and `renderLayerEffects` 'after'.
- `getLayerVisibleContributionMask` skipping non-source-over upper layers.

Adding a behavioral test for non-source-over render output would require a
DOM (canvas+ctx) stub, which we deferred. Manual verification per the
"Verify In The Running App" steps above is the acceptance evidence.

## Backlog Tasks Closed By This Doc

- #69 — decide intended semantics for non-source-over effects
- #70 — document current behavior
- #71 — normalize inconsistent effect behavior if needed (decision: NO normalization needed; current behavior is internally consistent and matches Photoshop's default "Blend Interior Effects as Group: off")

## Backlog Tasks Deferred

- #61–#68, #72–#80 — behavioral verifications and per-combo tests. These
  require a running-app harness to validate visual output and were not
  attempted tonight to avoid claiming verification we didn't do.
