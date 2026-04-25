# Tutorial 4 — Finishes Deep Dive

**Estimated time:** 12 minutes
**Prerequisites:** [Tutorial 3 — Zones Explained](03_zones_explained.md)
**Skill level:** Intermediate.

SPB ships with hundreds of finishes. They're not all the same kind of thing. The picker is organized into four categories — Foundations (bases), Patterns, Monolithics, and Spec Patterns — and each category does something fundamentally different. Once you understand the categories, picking the right finish becomes obvious instead of intimidating.

## What you'll learn

- The four finish categories and what they each do
- When to reach for a base vs. a pattern vs. a monolithic
- How to stack finishes (base + pattern + spec pattern)
- The premium catalogs: COLORSHOXX, MORTAL SHOKK, PARADIGM
- How spec patterns add PBR detail without changing color

---

## Step 1 — Open the Finishes tab

Click **Finishes** in the right panel. You'll see the picker organized into expandable categories. The first thing to notice: the categories are stacked top-to-bottom by *fanciness*. The premium catalogs are at the top, the workhorse bases are in the middle, and the spec patterns sit in their own separate area.

![Step 1 — Finishes picker](docs/img/tutorial-04-step1.png)

There's also a search bar at the top. Type any partial name and the list filters in real time. `Ctrl+F` jumps focus there.

## Step 2 — The Foundations (bases)

A **base** is the fundamental "kind of paint" a zone has. Every zone needs exactly one base. The base controls the underlying color, gloss level, metallic flake, and overall material feel.

Common bases:

- **gloss_clean** — high-gloss solid color. Your default for most race liveries.
- **matte_clean** — flat, no-gloss solid color. Modern stealth look.
- **satin_clean** — the in-between. A subtle sheen that's neither candy nor matte.
- **metallic_standard** — solid color with metallic flake suspended in the paint. The classic factory metallic look.
- **candy_apple** — translucent candy coat over a metallic base. Deep, juicy, color-shifting.
- **chrome_mirror** — full mirror chrome. Reflects the world.
- **carbon_composite** — a carbon-fiber look without a separate pattern overlay.
- **ceramic_glass** — a deep, slightly translucent ceramic finish with subsurface scatter feel.

Click a few. Each one totally changes the feel of the truck while keeping your zone's color the same. The *color* you pick on the zone is the *hue* the base wears — so a candy_apple zone with green color is candy green, not candy red.

> Tip: 80% of liveries you'll see in the wild use **gloss_clean** or **metallic_standard**. Start there before reaching for the exotic stuff.

## Step 3 — Patterns (overlays)

A **pattern** sits on top of a base and adds repeating texture. Patterns don't replace the base — they modulate it.

Common patterns:

- **carbon_weave** — classic carbon fiber 2x2 twill weave
- **scales** — overlapping scale pattern, dragon-skin look
- **honeycomb** — hexagonal cells
- **forge_mesh** — industrial mesh
- **chameleon** — color-shifting iridescence
- **brushed_directional** — brushed metal grain

Pick a base (try metallic_standard) and then expand the **Patterns** category. Click **carbon_weave**. The truck now has metallic paint with a carbon weave on top — visible up close, blended at distance, exactly like real carbon-pattern wraps.

Patterns have a **strength slider** in the zone card. 100% is full pattern; 0% is no pattern. Most users live between 30 and 70 depending on how subtle they want the effect. The new Pattern Strength Zones feature (v6.1.1) lets you vary strength per zone region — useful for fading a pattern out across the body.

## Step 4 — Monolithics (the all-in-one premium finishes)

A **monolithic** is a complete finish that bakes the base, pattern, and spec into one unit. You don't pick a base or a pattern when you use a monolithic — the monolithic is the whole package.

The premium monolithic catalogs:

### ★ COLORSHOXX

Color-shifting, energy-feel finishes. They auto-tint based on your zone color but bring their own visual personality.

- **CX Inferno** — flame energy, shifts from base color through orange and yellow
- **CX Aurora** — soft northern-lights gradient
- **CX Glitch** — digital corruption / RGB split aesthetic
- **CX Plasma** — electric-purple plasma feel

### ★ MORTAL SHOKK

Aggressive, high-contrast battle finishes. Less color-shifty than COLORSHOXX, more "this car wants to fight."

- **MS Battlescar** — distressed, scratched battle-worn look
- **MS Kintsugi** — gold-cracked ceramic feel
- **MS Warpaint** — bold tribal slash overlay

### ★ PARADIGM

The flagship category. Each PARADIGM finish is hand-tuned to look like a specific high-end real-world finish you'd pay $20k for at a custom shop.

- **PD Liquid Metal** — molten chrome look
- **PD Holographic** — true holographic foil aesthetic
- **PD Cosmic** — galaxy / nebula effect
- **PD Prism** — prism diffraction rainbow

Try one. Click **CX Inferno** with a yellow zone. The truck transforms into a deep, color-shifting flame finish that no amount of base+pattern stacking would have produced. That's why monolithics exist — some looks are too cohesive to build by hand.

> Tip: Monolithics override your base and pattern selections while active. To go back to mix-and-match, just pick a regular base.

## Step 5 — Spec Patterns (the PBR layer)

A **spec pattern** is a separate overlay that adds variation to the **spec map** without changing the color paint. Most users miss this category at first because it's not in the main bases list — it lives in its own section.

Why does this matter? The spec map controls *material*, not color. A spec pattern can add things like:

- **clearcoat_orange_peel** — subtle orange-peel texture on the clearcoat (looks like real automotive paint up close)
- **water_droplets** — beaded water on the surface
- **scuff_micro** — micro-scuffing for a worn-in look
- **rain_streaks** — vertical rain streaks for "drove home in a storm" realism
- **honeycomb_spec** — hexagonal honeycomb in the spec channel only (color stays uniform; reflectance varies)

These don't change what color the car is. They change how light catches it. Stacking a clearcoat_orange_peel spec pattern on top of a glossy red base is the difference between "video game paint" and "this looks like a real car."

The new SPB v6.2 catalog has 100+ spec patterns. Most are subtle on purpose. Apply one and look at the **Live Preview** with light dragged across it — you'll see the surface respond differently than before.

## Step 6 — The full stack

The maximum recipe is:

```
Zone Color: red
Base:           metallic_standard
Pattern:        carbon_weave (40% strength)
Spec Pattern:   clearcoat_orange_peel
```

Color (red) flows through metallic_standard (which gives a metallic red base), then carbon_weave overlays a subtle weave pattern, then the clearcoat_orange_peel spec pattern adds realistic clearcoat micro-texture.

Hit RENDER. Look closely. That's a four-layer finish — and it took four clicks to build.

---

## Try it yourself

Stack a real combo and feel the layering:

1. New zone, color `#A02828` (deep red).
2. Pick base **metallic_standard**.
3. Add pattern **carbon_weave** at strength 50%.
4. Add spec pattern **clearcoat_orange_peel**.
5. RENDER.
6. Now swap the base to **candy_apple** (keep everything else). RENDER again.
7. Now swap the base to **chrome_mirror**. RENDER.

Watch how the same color, pattern, and spec pattern produce three radically different looks because the base is doing 60% of the work. Bases are the foundation — pick them carefully.

---

## Troubleshooting

**The pattern looks too aggressive.** Drop the pattern strength slider. 30-50% is usually the sweet spot.

**My monolithic looks plain.** Monolithics are tuned to specific color ranges. Try a more saturated zone color, or pick a different monolithic — some require warm colors to shine, others cool.

**Spec pattern doesn't seem to do anything.** Spec patterns are subtle on purpose. Drag the camera around the live preview — they're most visible at glancing angles. Also confirm you applied a *spec* pattern, not a regular pattern, by checking it's listed in the zone's "Spec" slot.

**The picker is overwhelming.** Use the search bar (`Ctrl+F`). Type "matte" to see all matte options. Type "carbon" to see every carbon-related finish across categories.

---

## Next up

[Tutorial 5 — Spec Map Mastery](05_spec_map_mastery.md). You just played with finishes from the user side. Next we'll pop the hood and look at what's actually happening in the spec map — and why understanding it lets you fake any material in any game with a PBR pipeline.
