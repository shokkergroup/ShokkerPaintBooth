# Tutorial 6 — Sponsor Placement

**Estimated time:** 10 minutes
**Prerequisites:** [Tutorial 2 — Layer Basics](02_layer_basics.md)
**Skill level:** Beginner to intermediate.

A clean livery with no sponsors looks unfinished. Sponsors fill the visual rhythm of a race car and break up large swaths of body color. SPB has dedicated tools for placing logos quickly, mirroring them across the truck for visual symmetry, and dressing them with effects. This tutorial walks through the whole sponsor workflow.

## What you'll learn

- How to use the Sponsors layer that ships in SPB templates
- How to import a logo as a new layer
- How to use the Move tool to position a sponsor
- How Mirror Clone produces left-right symmetric placement in one click
- How to add stroke and drop shadow to make logos pop

---

## Step 1 — Find the Sponsors layer

In the Layers panel, scroll until you see a layer (or a group) called **Sponsors**. The Silverado template has a small starter set of placeholder sponsor logos already on this layer.

Click the **Sponsors** layer to make it active.

![Step 1 — Sponsors layer selected](docs/img/tutorial-06-step1.png)

> Tip: If your template has sponsors in a group rather than a single layer, expand the group to see individual logos as sub-layers. SPB treats group children as fully independent layers.

## Step 2 — Import a logo

Most users want to add their own sponsor logos, not the placeholders. Two ways to do it.

**Method A — File menu:**
1. `File → Import as Layer` (or `Ctrl+I`).
2. Pick a PNG or SVG of your sponsor logo. PNG with transparency is best.
3. The logo arrives as a new layer at the top of the stack, sized at original resolution.

**Method B — Drag and drop:**
1. Drag a PNG file from Windows Explorer directly onto the canvas.
2. Same result — a new layer at the top.

For best results your logo PNG should:

- Be transparent background (no white square around the logo)
- Be sized at least 512x512 (we'll downscale, but starting big preserves detail)
- Use a single solid color or simple gradient (busy logos lose detail in iRacing's compression)

## Step 3 — The Move tool

Press `V` to switch to the Move tool. Click your new logo on the canvas. Drag to position it.

You'll see:

- A **bounding box** around the logo with eight handles for resize
- A **center pivot** for rotation (drag the small circle outside the bounding box)
- **Smart guides** that snap to other layer edges and the canvas centerlines

![Step 3 — Move tool with bounding box](docs/img/tutorial-06-step3.png)

Hold `Shift` while dragging a corner handle to scale uniformly. Hold `Alt` to scale from center. Hold `Ctrl` while rotating to snap to 15-degree increments.

For sponsor placement on a truck, common positions are:

- **Front door panel** — primary sponsor, biggest size
- **Quarter panel** — secondary sponsor, medium size
- **Hood** — manufacturer or series sponsor, large
- **Rear bumper** — small text sponsors

## Step 4 — Mirror Clone

Race cars are usually visually symmetric — what's on the driver's side is mirrored on the passenger side. SPB has a one-click solution: **Mirror Clone**.

With your logo layer selected:

1. `Layer → Mirror Clone Across Centerline` (or `Ctrl+M`)
2. Pick the axis: **Vertical (left-right)** for the typical "mirror to the other side" use case.
3. Click **OK**.

A new layer is created — an exact horizontal mirror of your original — placed at the corresponding position on the opposite side of the truck.

This is non-destructive in a clever way: the mirror clone is its own layer, fully editable. You can move, rotate, or even delete one side independently. They aren't linked — Mirror Clone is a one-time operation.

> Tip: If you want a *linked* mirror that updates when you change the original, use `Ctrl+Shift+M` to create a **smart mirror** instead. Smart mirrors re-sync any time you edit the source. Costs a small render performance hit, but worth it for iterative design work.

## Step 5 — Layer effects: Stroke

Logos often look weak floating on a body color. A **stroke** (outline) makes them pop.

Double-click the logo's layer in the Layers panel. The **Layer Effects** dialog opens.

![Step 5 — Layer effects dialog](docs/img/tutorial-06-step5.png)

In the left list, click **Stroke**. Then:

- **Size:** 4-8 pixels for a noticeable but not overpowering outline
- **Color:** White if your body is dark, black if your body is light
- **Position:** Outside (the stroke sits outside the logo edge — most common)
- **Opacity:** 100% for a solid edge, 50-70% for a softer feel

Hit **OK**. The logo now has a clean outline that separates it from the body color.

## Step 6 — Layer effects: Drop Shadow

A subtle drop shadow adds depth and makes a sponsor feel "applied to the body" rather than "floating."

Re-open Layer Effects (double-click the layer). Click **Drop Shadow**.

- **Distance:** 3-5 pixels
- **Spread:** 0-2 pixels
- **Size (blur):** 4-8 pixels
- **Angle:** 135° (standard "light from upper-left" convention)
- **Opacity:** 40-60% — subtlety is key, real shadows aren't black
- **Color:** Pure black, or a darker version of the body color for a warmer feel

Hit **OK**. The sponsor now sits convincingly on the surface.

## Step 7 — Bake or live?

By default, layer effects are **live** — they re-render every time you adjust them, and they persist as editable across save/load. If you want to flatten them into the layer permanently (so the effect baked into the layer pixels rather than applied at render), right-click the layer and pick **Rasterize Effects**.

Most users leave effects live so they can tweak. Rasterize when you're done iterating, or to free up render budget on a heavy livery with many effects.

---

## Try it yourself

Place a sponsor on both quarter panels with full polish:

1. Find or make a simple sponsor PNG (any logo will do — your name in a bold font is fine).
2. Drag it onto the canvas. Move tool (`V`), position it on the **driver's side rear quarter panel.**
3. Resize to about 200 pixels wide using a corner handle with `Shift` held.
4. `Ctrl+M` (or `Layer → Mirror Clone`) → Vertical → OK. The logo now exists on the passenger side too.
5. Select the original layer. Double-click → Stroke 5px white, Drop Shadow 4px distance 50% opacity.
6. Select the mirror layer. Apply the same effects (or copy-paste effects via right-click → Copy Layer Style → Paste Layer Style).
7. RENDER. Spin the truck in iRacing or in the Live Preview. Both quarter panels show your branded sponsor with depth.

---

## Troubleshooting

**Logo imported huge, can't see the truck.** That's fine — the logo arrived at original resolution. Just use the Move tool's corner handles to scale down. Hold `Shift` to keep aspect ratio.

**Logo looks pixelated.** Source PNG was too low-res. Re-export from your source at 1024x1024 or higher and re-import. SVG sources scale infinitely if you have them.

**Mirror Clone went the wrong direction.** You picked the wrong axis. Undo (`Ctrl+Z`), `Layer → Mirror Clone` again, pick the other axis. Vertical = left-right; Horizontal = top-bottom (rare for sponsors).

**Stroke looks jaggy.** Increase the stroke size — strokes below 2px alias badly. Or enable **Anti-alias** in the stroke settings.

**Drop shadow is too harsh.** Drop opacity to 30-40% and increase blur to 10+. Real-world shadows are soft and translucent. Hard 100%-black shadows look cartoonish.

**The mirror logo edits aren't following the original.** You used Mirror Clone (one-time copy) instead of Smart Mirror (linked). Use `Ctrl+Shift+M` next time, or just edit both copies.

---

## Next up

[Tutorial 7 — Layer Effects](07_layer_effects.md). You used stroke and drop shadow on a sponsor. The Layer Effects dialog has eight more effects — outer glow, color overlay, bevel, satin, gradient overlay, pattern overlay, inner glow, inner shadow — and the next tutorial walks through every one with a use case.
