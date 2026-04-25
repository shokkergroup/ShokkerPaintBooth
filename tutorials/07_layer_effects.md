# Tutorial 7 — Layer Effects

**Estimated time:** 10 minutes
**Prerequisites:** [Tutorial 6 — Sponsor Placement](06_sponsor_placement.md) (covers stroke + drop shadow basics)
**Skill level:** Intermediate.

SPB's Layer Effects dialog is a full Photoshop-style FX engine with ten effects you can stack on any layer. Tutorial 6 touched on stroke and drop shadow. This tutorial walks through every effect, what it's for, and a recommended settings starting point for each.

## What you'll learn

- How to open the Layer Effects dialog and what's in it
- All ten effects: what they do and when to use them
- How to stack multiple effects on a single layer
- How to save effect presets for reuse
- How to copy effect styles between layers

---

## Step 1 — Open Layer Effects

In the Layers panel, **double-click** any layer name (not the checkbox, the name). The Layer Effects dialog opens as a floating panel with a list of effects on the left and the settings for the selected effect on the right.

![Step 1 — Layer effects dialog open](docs/img/tutorial-07-step1.png)

Each effect has a checkbox. Check it to enable; uncheck to disable without losing settings. This makes A/B-ing a design very fast — check and uncheck effects to compare.

## Step 2 — Drop Shadow

Cast a soft shadow behind the layer. The most-used effect for floating UI elements (logos, numbers, stripes).

**Starting preset:**
- Distance: 4px
- Spread: 0
- Size (blur): 6
- Angle: 135°
- Opacity: 50%
- Color: Black

Tweak opacity down for subtlety. Tweak distance and angle for a stronger "floating off the surface" feel.

## Step 3 — Inner Shadow

Cast a shadow *inside* the layer edge. Makes elements look recessed into the surface.

**Starting preset:**
- Distance: 3px
- Size: 4
- Angle: 135°
- Opacity: 60%
- Color: Black

Use on: number panels that should feel "cut into" the body, text that should look debossed.

## Step 4 — Outer Glow

A soft color halo around the layer edge. Great for neon feels and highlighting.

**Starting preset:**
- Size: 10
- Spread: 0
- Opacity: 70%
- Color: Match a complementary hue (yellow glow on red text, blue on white, etc.)
- Blend Mode: **Screen** (this is critical — Normal looks wrong)

Use on: neon-style text, highlight stripes, "power on" effects.

## Step 5 — Inner Glow

A soft color halo *inside* the layer edge. Subtle and adds dimension to text.

**Starting preset:**
- Size: 6
- Opacity: 40%
- Color: Pure white or lighter version of the fill
- Source: Edge (glows inward from the edge)

Use on: polished chrome text, gem-like logos, anything that should catch light from within.

## Step 6 — Stroke

A clean outline around the layer. Tutorial 6 covered this; here's the full parameter set:

**Starting preset:**
- Size: 4px
- Position: Outside (Outside / Center / Inside)
- Color: Contrasting to body
- Opacity: 100%
- Blend Mode: Normal

Position matters: Outside keeps the layer's fill unchanged; Inside eats into the fill; Center straddles the edge. Outside is safest for logos.

## Step 7 — Color Overlay

Flood the whole layer with a solid color. Useful for mass-recoloring a sponsor logo to match a livery palette.

**Starting preset:**
- Color: Any
- Blend Mode: **Multiply** (preserves logo shape) or **Normal** (hard replace)
- Opacity: 100%

Use on: recoloring black/white logos to match livery, turning a full-color logo into a monochrome version.

## Step 8 — Gradient Overlay

Same as Color Overlay but with a gradient.

**Starting preset:**
- Gradient: Two-color linear
- Angle: 90°
- Opacity: 100%
- Blend Mode: Normal

Use on: number panels that fade top-to-bottom, stripes that shift hue along their length.

## Step 9 — Pattern Overlay

Tile a pattern over the layer. Different from the finish Pattern system — this is layer-level, not zone-level.

**Starting preset:**
- Pattern: Pick from the dropdown
- Scale: 50%
- Opacity: 60%
- Blend Mode: Multiply or Overlay

Use on: adding texture to text (wood grain, carbon, fabric weave) without changing the underlying finish of the zone.

## Step 10 — Bevel & Emboss

Add a 3D beveled edge to the layer. The most "Photoshop-y" of the effects.

**Starting preset:**
- Style: Inner Bevel
- Depth: 100%
- Size: 4px
- Angle: 135°, Altitude 30°
- Highlight: White, Screen mode, 75%
- Shadow: Black, Multiply mode, 75%

Use on: 3D-looking team logos, embossed number panels, coin-like stamps. Use sparingly — overdone bevels look very 1998.

## Step 11 — Satin

A subtle inner sheen that simulates satin fabric. Rarely used but beautiful in the right spot.

**Starting preset:**
- Color: Darker than fill
- Opacity: 30%
- Size: 14
- Distance: 8
- Blend Mode: Multiply

Use on: silky-smooth team logos, stylized name plates. Very subtle effect.

## Step 12 — Stacking and order

Layer effects stack in a specific order, top-to-bottom in the dialog list. You can't reorder them — Photoshop uses the same fixed order.

The render order is:

1. Pattern Overlay, Gradient Overlay, Color Overlay (in that order, later ones on top)
2. Inner Shadow
3. Inner Glow
4. Satin
5. Bevel & Emboss
6. Stroke
7. Outer Glow
8. Drop Shadow (at the back)

This order is why drop shadow always appears *behind* the layer fill, and stroke always *outlines* the fill.

## Step 13 — Effect presets

If you build a combo you like, save it as a preset. In the Layer Effects dialog, click **Save Preset...** at the bottom. Give it a name like "Gold Logo" or "Neon Pink."

Presets are stored per-project by default; tick **Save to global library** to make them available in every project.

To apply a preset to a new layer: double-click the layer to open effects, click **Load Preset...**, pick your saved set.

## Step 14 — Copy / paste layer style

Built a complex effect combo on Layer A and want it on Layer B?

- Right-click Layer A → **Copy Layer Style**
- Right-click Layer B → **Paste Layer Style**

Every effect, every setting, applied in one click. Much faster than recreating.

---

## Try it yourself

Make a sponsor logo pop with a signature "neon" feel:

1. Import or pick a text-heavy sponsor logo layer.
2. Double-click to open Layer Effects.
3. Enable **Stroke** — 3px, white, outside, opacity 100%.
4. Enable **Outer Glow** — size 20, color `#FF3DFF` (hot pink), blend mode Screen, opacity 80%.
5. Enable **Drop Shadow** — distance 2, size 8, opacity 40%.
6. Hit **OK**.
7. RENDER. Look at the logo — it should feel genuinely neon, with a soft pink halo and a hovering depth.

Now save it as a preset called "Neon Sponsor" and apply it to another logo layer with one click.

---

## Troubleshooting

**Outer Glow looks like a dirty shadow instead of a glow.** Blend Mode is wrong. Switch to **Screen** — it's the correct mode for additive light effects.

**Drop Shadow doesn't appear.** Check the layer has transparency around it. If the layer is a solid rectangle touching the canvas edge, there's nothing for the shadow to cast onto.

**Effects preview is laggy on a huge layer.** Pattern Overlay and Bevel & Emboss are the expensive ones. Temporarily disable the checkbox while you position, re-enable before render.

**I can't find my saved preset.** Presets are per-project by default. Tick "Save to global library" when saving to make them persist across projects.

**Paste Layer Style didn't work.** Make sure you right-clicked the layer name, not the checkbox. The context menu for the name is the full menu; the checkbox just toggles visibility.

**Effects look right in SPB but fade in iRacing.** The spec map doesn't carry layer effects — effects only live in the color paint TGA. This is iRacing's limitation, not SPB's. Heavy effects will always look a bit tamer in-sim than in Live Preview.

---

## Next up

[Tutorial 8 — Recipe Workflow](08_recipe_workflow.md). You've built liveries from scratch. The next step is browsing SPB's recipe library, importing a preset design (like "NASCAR Classic"), and customizing it to your team. Recipes save hours of setup for common livery templates.
