# Tutorial 9 — Advanced Tools

**Estimated time:** 12 minutes
**Prerequisites:** [Tutorial 2 — Layer Basics](02_layer_basics.md) for the basic drawing tools
**Skill level:** Intermediate to advanced.

Zones and recipes handle the 80% case. For the remaining 20% — touch-ups, custom details, pixel-perfect precision — you need the advanced toolbox. This tutorial covers stabilizer, smart guides, snap-to-pixel, recent colors, brush presets, and the four "specialty" tools most new users never touch: smudge, clone stamp, dodge, and burn.

## What you'll learn

- How brush stabilizer smooths your hand tremor into clean lines
- How smart guides and snap-to-pixel keep your layout geometrically clean
- How to manage the recent colors palette and create brush presets
- When to reach for smudge, clone stamp, dodge, and burn

---

## Step 1 — Brush Stabilizer

Everyone's hand shakes a little. At canvas zoom levels, even a small tremor produces wobbly lines. SPB's **brush stabilizer** fixes this by lagging your brush stroke behind the cursor slightly and smoothing the path.

Pick the Brush tool (`B`). In the **Tool Options** bar above the canvas, find the **Stabilizer** slider. Default is 0 (off). Try 30.

Draw a long curved line. The line follows your cursor but smoother — micro-tremor is filtered out. The brush tip "trails" the cursor by a controlled amount.

Settings guide:

- **0-10:** Minimal stabilization. Fast response, near-raw cursor.
- **30-50:** Comfortable zone for most hand-drawn work. Visible smoothing without feeling laggy.
- **60-80:** Heavy smoothing. Great for long flowing lines. Feels laggy on short strokes.
- **90+:** Extreme. The brush trails substantially behind the cursor. Use for calligraphy-style effects.

> Tip: Stabilizer works on brush, pencil, eraser, smudge, dodge, and burn. Set it once and every pen tool benefits.

## Step 2 — Smart Guides

Smart guides are alignment lines that appear automatically when you move a layer or draw near the edges or center of other shapes.

Press `V` (Move tool). Drag any sponsor logo. As it approaches the horizontal centerline of the canvas, a pink line snaps on and the layer jumps to center. Same for the vertical centerline, and for alignment with any other layer's edges.

![Step 2 — Smart guides snapping](docs/img/tutorial-09-step2.png)

Toggle smart guides with `View → Smart Guides` (or `Ctrl+;`). They can get chatty on a busy canvas — disable if they're in the way, re-enable for final alignment pass.

## Step 3 — Snap to Pixel

At fine zoom levels, cursor positions fall between pixel boundaries. Without pixel snap, a text layer might land with its edge at position 237.6 px, causing subtle antialiasing blur.

Enable `View → Snap to Pixel`. Now every move, resize, and shape creation rounds to integer pixel positions. Lines are crisp. Edges don't blur.

> Tip: Disable snap-to-pixel when you *want* sub-pixel positioning for organic feel (like scattered grass, dust, or stippled effects). Enable for geometric, technical work (numbers, stripes, logos).

## Step 4 — Recent Colors palette

The **Recent Colors** row below the main color picker keeps the last 20 colors you used. Click any swatch to reload that color instantly.

![Step 4 — Recent colors palette](docs/img/tutorial-09-step4.png)

The palette is per-project by default (each paint file has its own recent colors history). `Ctrl+.` and `Ctrl+,` cycle forward and back through recent colors.

**Pin a color** by right-clicking the swatch → **Pin to Palette**. Pinned colors move to the left and never get pushed off by new colors. Useful for team palette ("these four colors are our team brand; always keep them").

## Step 5 — Brush Presets

If you customize brush size, hardness, flow, spacing, and stabilizer for a specific look, save it as a preset.

- `Brush → Save Current as Preset`
- Name it ("Soft Detail," "Hard Line," "Grain Spray")
- Optionally assign a keyboard shortcut (`Brush → Assign Shortcut`)

Presets appear in the **Brush Presets** dropdown in the toolbar. Pick one to load all its settings at once.

Bundled presets worth trying:

- **Hard Round** — 100% hardness, 100% flow. Classic pixel brush.
- **Soft Airbrush** — 0% hardness, 30% flow. Cloud / fade work.
- **Pencil 1px** — tiny hard brush for pixel art cleanup.
- **Grain Spray** — textured brush for noise / dust effects.

## Step 6 — Smudge Tool

`R` (or `Shift+S` on some configs). The smudge tool pushes color around as if you were dragging wet paint. Great for:

- Softening a hard edge
- Blending two colors into a gradient
- Creating "streaking" feel (rain, blur, motion)

Parameters:

- **Strength:** How much color is carried per stroke (30-50% for gentle, 80%+ for aggressive drag)
- **Sample All Layers:** On = pick up color from all visible layers; off = only from the active layer

Light smudging on the boundary of two zones (with a zone merged and flattened first) hides the hard transition beautifully.

## Step 7 — Clone Stamp

`S`. Sample pixels from one part of the canvas and paint them at another.

Workflow:

1. Hold `Alt` and click a source point (where you want to copy from).
2. Release `Alt`. Move to the destination.
3. Paint. Pixels from the source are painted under the cursor.

Useful for:

- Extending a pattern across a surface (clone a stripe to make it longer)
- Covering up a spec speckle by cloning a clean area over it
- Duplicating a sponsor logo without re-importing

**Aligned mode** (checkbox in tool options): the sample point follows the cursor offset. **Unaligned**: the sample point resets to the original every stroke.

## Step 8 — Dodge & Burn

`O` for dodge (lighten), `Shift+O` for burn (darken). Classic darkroom tools for subtle tonal adjustment.

- **Dodge** brightens the area under the brush.
- **Burn** darkens it.

Both have a **Range** setting: **Shadows, Midtones, or Highlights**. Only pixels in the chosen tonal range respond to the stroke. This lets you brighten highlights without blowing out midtones, or deepen shadows without crushing midtones.

**Exposure** (0-100%) controls strength per stroke. Keep it low (10-20%) for subtle work; multiple light strokes build up more natural than one heavy stroke.

Use cases:

- **Dodge highlights on a metallic zone** to simulate where light catches the flake.
- **Burn shadows under a drop shadow** for extra depth.
- **Dodge the center of a logo** to make it feel lit from within.

---

## Try it yourself

Detail a sponsor logo with the smudge tool and a custom brush preset:

1. Import a simple text-only sponsor logo. Give it a solid color fill (no effects yet).
2. Pick the **Smudge** tool (`R`). Set strength to 40%.
3. Enable stabilizer at 40.
4. On the logo, drag the smudge brush *across* the text at 45 degrees. The text edges now have a slight motion-blur/streak feel.
5. Save your smudge tool settings as a preset called "Motion Streak."
6. Pick the **Dodge** tool (`O`). Range: Highlights. Exposure: 15%.
7. Lightly dodge the top of the logo. It should feel lit from above.
8. Switch to **Burn** (`Shift+O`). Range: Shadows. Exposure: 15%.
9. Gently burn the bottom of the logo. It should feel shaded from below.
10. RENDER.

The logo now has subtle 3D depth that a flat fill couldn't achieve. Real photography uses dodge and burn constantly; liveries benefit from the same technique.

---

## Troubleshooting

**Stabilizer feels too laggy.** Drop the slider. 30 is a comfortable default; above 60 noticeably trails.

**Smart guides don't appear.** Confirm they're enabled in `View → Smart Guides`. Also check you're in Move tool (`V`); guides don't show for brush-tool operations.

**Clone Stamp paints nothing.** You didn't `Alt+click` a source first. Hold `Alt`, click somewhere with pixels (not empty canvas), release, then paint.

**Dodge / Burn seem not to work.** Check the Range dropdown. If it's set to "Highlights" and you're painting on midtone pixels, nothing happens. Switch to the appropriate range, or try "Midtones" which affects the broadest swath.

**My brush preset didn't save the stabilizer setting.** Some older preset files don't include stabilizer. Re-save the preset with current SPB and the setting will persist.

**Smudge picks up color I didn't want.** Turn off "Sample All Layers." Smudge will only carry pixels from the currently active layer.

---

## Next up

[Tutorial 10 — Render & Export](10_render_export.md). The final tutorial. You know how to build liveries; now we'll master the render pipeline itself — live preview vs. full render, the render history panel, Live Link to iRacing, and how to export a `.shokker` file to share your complete project with friends.
