# Shokker Paint Booth — The Complete Guide

> The painter's painter for iRacing. Built by racers, for racers.

Welcome to **Shokker Paint Booth (SPB)** — a purpose-built liveries tool for iRacing that does what Photoshop, GIMP, paint.net, and Trading Paints Paint Builder were never designed to do: paint *paint*. Real paint. Metallics that flake. Chrome that bends light. Carbon that weaves. Anodized aluminum that shifts color across the body. And it does it in real time, on a 3D-aware preview of your actual car.

This guide will take you from "what's a spec map?" to "I just shipped a tribute livery in 20 minutes."

---

## Table of Contents

1. [What SPB Is (and isn't)](#1-what-spb-is)
2. [Installation & First Launch](#2-installation--first-launch)
3. [The Interface Tour](#3-the-interface-tour)
4. [Loading Your Paint](#4-loading-your-paint)
5. [Understanding Zones](#5-understanding-zones)
6. [Understanding Layers (and the layer-vs-zone trap)](#6-understanding-layers)
7. [The Finish System](#7-the-finish-system)
8. [Spec Map Basics](#8-spec-map-basics)
9. [The Tools](#9-the-tools)
10. [Layer Effects](#10-layer-effects)
11. [Sponsor & Logo Tooling](#11-sponsor--logo-tooling)
12. [Rendering](#12-rendering)
13. [Live Preview](#13-live-preview)
14. [Saving Your Work](#14-saving-your-work)
15. [Keyboard Shortcuts](#15-keyboard-shortcuts)
16. [Tips & Tricks](#16-tips--tricks)
17. [Common Workflows](#17-common-workflows)
18. [Troubleshooting](#18-troubleshooting)
19. [FAQ](#19-faq)
20. [Glossary](#20-glossary)

---

## 1. What SPB Is

SPB is a **livery painter**. It takes your PSD/TGA/PNG paint, lets you assign real-world materials (chrome, brushed aluminum, candy red, anodized purple, carbon fiber) to specific regions of the car, and writes out **the exact files iRacing wants** — including the spec map and (where supported) the metallic map.

### How SPB compares

| Tool | Strength | Where it falls short |
|---|---|---|
| **Photoshop** | Pixel-pushing king | No idea what a spec map is. You hand-paint roughness in greyscale and pray. |
| **GIMP / paint.net** | Free | Same problem. Plus no PBR preview. |
| **Trading Paints Paint Builder** | Beginner-friendly | Limited finish library. No real-time PBR. No zone-level spec control. |
| **SPB** | Real materials, real preview, zone-level spec control | Windows-only. Built for iRacing. |

> Tip: SPB is not a replacement for Photoshop when you're designing a logo from scratch. Build your logos and graphics in Photoshop, then bring the PSD into SPB for *finishing* — color, material, gloss, sheen, flake, and rendering.

### The SPB moat

SPB is the only iRacing painting tool that gives you:

- **Pattern-per-channel control** (different patterns on color vs spec)
- **Real-time car-shape preview** (not a flat paint kit — a proper 3D-aware view)
- **Zone-level spec settings** (one panel matte, the next mirror chrome, side by side)
- **192 spec overlay patterns** (across 19 PBR categories)
- **Monolithic finishes** like COLORSHOXX, MORTAL SHOKK, and PARADIGM that bundle base + pattern + spec into one click

---

## 2. Installation & First Launch

### Install

1. Download `Setup.exe` (Shokker Paint Booth installer).
2. Run it. Windows SmartScreen may warn — click **More info → Run anyway**. The build is unsigned during the Gold-to-Platinum experimental phase; we sign on stable releases.
3. Choose install location (default is fine).
4. Launch from the Start Menu shortcut **Shokker Paint Booth**.

> Warning: SPB is **Windows-only**. iRacing is Windows-only. We have no plans for Mac/Linux builds.

### First launch

The first time you open SPB it auto-loads the **Chevy Silverado 2019** demo PSD so you have something to play with. You'll see:

- The Silverado paint kit in the canvas
- A pre-populated layer list on the right
- An empty Zones list on the left
- The Live Preview pane updating

This is your **sandbox**. Mess with it. Nothing is saved to your iRacing folder until you press **RENDER**.

### Sandbox testing

Before you touch a real livery, run a render of the Silverado:

1. Add a zone (left panel `+ Add Zone`)
2. Pick any color from the canvas with the Eyedropper
3. Browse Finishes → click any finish (try `★ COLORSHOXX → CX Inferno`)
4. Press **RENDER**

If you see your iRacing trucks/silverado2019 folder receive `car_*.tga` files, the install is healthy.

---

## 3. The Interface Tour

![Interface overview](docs/img/interface-overview.png)

SPB has six main UI regions:

### Header (top bar)
- **File** menu: New, Open, Save, Render, Export Config
- **Edit** menu: Undo / Redo, Preferences
- **View** menu: Toggle Live Preview, Toggle Reference, Zoom controls
- **RENDER** button (the big one — top right)
- **Save SHOKK** button (saves your full state as a `.shokker` preset)

### Left toolbar (vertical)
A tall vertical strip of icon buttons grouped by category — **Sel, Layer, Draw, Spatial, Mask, Shapes, Refn, Xfrm, View**. See [The Tools](#9-the-tools) for the full breakdown.

### Zone panel (left side)
Shows your zones as numbered cards, in priority order (Zone 1 wins over Zone 2 in overlapping pixels). Each card has a color swatch, a finish label, and a layer-restriction indicator.

### Canvas (center)
Your paint, displayed at native resolution. Pan with middle-mouse drag, zoom with the scroll wheel. The active tool's cursor appears here.

### Right panel (Layers / Finishes tabs)
Two tabs:
- **Layers** — the PSD layer tree, like Photoshop. Eye toggles visibility, opacity sliders, double-click for layer effects.
- **Finishes** — the finish browser. Bases, Patterns, Monolithics, Spec Patterns. Categorized and searchable.

### Status bar (bottom)
Cursor position, paint dimensions, render server status (green = healthy), live preview status.

---

## 4. Loading Your Paint

SPB accepts:

| Format | Editable layers? | Recommended? |
|---|---|---|
| **PSD** | Yes (full Photoshop layer tree) | **Strongly preferred** |
| **TGA** | No (flat) | OK for quick recolors |
| **PNG** | No (flat) | OK for quick recolors |

### Why PSD

PSD preserves your layer tree. SPB reads layer names (`Body`, `Numbers`, `Stripes`, `Sponsors`) and uses them for **layer-restriction** on zones — the secret sauce of clean liveries. With a flat TGA, every zone has to use color matching alone, which is harder.

### Where to put files

Put your paint anywhere. SPB has a file picker (`File → Open Paint…`) and remembers your last-loaded paint across launches. If you want to keep things tidy, drop them in your iRacing paint folder, e.g. `Documents\iRacing\paint\trucks\silverado2019\`.

> Tip: Build your PSD in Photoshop with named, organized layers. Group by car region (`Front`, `Sides`, `Rear`) and by purpose (`Base Color`, `Sponsors`, `Numbers`). Future-you will thank present-you.

---

## 5. Understanding Zones

This is the **heart** of SPB. Take your time here.

### What a zone is

A **zone** is a slice of your paint that the engine treats as a single material. You define a zone by saying:

> "Take all the **yellow pixels** on the **Numbers layer** and paint them in **COLORSHOXX Inferno**."

That sentence has three pieces:
1. A **color match** (yellow)
2. A **layer restriction** (Numbers)
3. A **finish** (CX Inferno)

That's a zone.

### Color matching

Use the Eyedropper (or click `+ Add Color` in the zone panel). SPB samples the pixel and sets a color tolerance window. Every pixel within tolerance is "in the zone."

You can add **multiple colors** to a zone — useful when a sponsor logo has a primary and an accent shade.

### Layer restriction

A zone can be **restricted** to only apply where a specific PSD layer has pixels. This is huge: you can have yellow pixels on three different layers (numbers, stripes, sponsor) and make sure your finish only paints the yellow on the *Numbers* layer.

### Priority order

Zones are stacked top-down. **Zone 1 wins over Zone 2** in any pixel they both claim. Drag zone cards to reorder.

> Tip: Put your most specific zones first (e.g. small sponsor logo) and your broadest zones last (e.g. body base color). Otherwise a "paint everything red" zone will swallow your sponsor.

### "Remaining" and "Everything"

Two special selectors save you from chasing every stray pixel:

- **Remaining** — paints anything not claimed by a higher-priority zone. Great for "fill the rest of the body with gloss white."
- **Everything** — paints the entire canvas. Useful as a base layer at the bottom of your zone stack.

---

## 6. Understanding Layers

**This is the single most-confused thing in SPB.** Read this section twice.

There are two completely different "layer" concepts:

### A) Layer SELECTION (right panel)
This is the layer that **drawing tools** target. Brush, Erase, Pencil — when you paint a pixel, it goes on the currently selected layer. Same as Photoshop.

### B) Layer RESTRICTION (zone settings)
This is the layer that **a zone is allowed to paint over**. The finish only applies where that layer has pixels.

These are **independent**. Selecting the Numbers layer in the right panel does NOT restrict your active zone to the Numbers layer. You have to do that explicitly in zone settings — or use the gold **🔒 Lock Active Zone to This Layer** button in the canvas dock.

> Warning: New users frequently get confused when their zone "doesn't work." 9 times out of 10 the cause is: they selected a layer in the right panel but didn't restrict the zone to that layer. The zone is happily painting yellow pixels — just on the wrong layer.

### The fix: Lock Active Zone to This Layer

We added a gold button (`🔒 Lock Active Zone to This Layer`) in the dock above the canvas. It does both at once: sets the right-panel selection AND restricts the active zone to that layer. Use it. It's there for a reason.

---

## 7. The Finish System

SPB ships with hundreds of finishes organized into four buckets:

### Bases — your foundation
A **base** is the underlying material: gloss paint, matte paint, satin, chrome, brushed aluminum, anodized, carbon fiber, candy, pearl, flake, etc. Every zone has exactly one base.

Browse: `Finishes tab → Bases`. Categories include **Foundation** (clean solids), **Metallics**, **Pearls**, **Chromes**, **Anodized**, **Specials**, and more.

### Patterns — texture on top
A **pattern** overlays a texture on the base — carbon weave, plaid, scales, noise, hex, brushed grain, you name it. Patterns are optional; not every zone needs one.

Browse: `Finishes tab → Patterns`.

### Monolithics — all-in-one premium finishes
Monolithics bundle base + pattern + spec settings + sometimes color logic into a single finish. Three flagship lines:

- **★ COLORSHOXX** — high-energy color-shifting finishes (CX Inferno, CX Cobalt Storm, CX Phantom, etc.)
- **★ MORTAL SHOKK** — aggressive, character-driven looks (Reptile Skin, Skull Lacquer, Bloodforge)
- **★ PARADIGM** — premium designer finishes

Click one and your zone is *done*. No need to layer base + pattern + spec.

### Spec Patterns — PBR overlay control
**192 spec overlay patterns** in 19 categories let you modify reflectivity *independently* of your color. Want a glossy hood with a brushed-metal sheen pattern in the spec channel only? Spec patterns. This is where SPB beats everything else.

Browse: `Finishes tab → Spec Patterns`. Categories include Brushed, Hex, Damascus, Carbon, Worn, Damage, Geometric, and more.

---

## 8. Spec Map Basics

iRacing uses a **spec map** alongside your color paint to control how light bounces off the car. SPB writes this for you automatically — but if you understand the channels, you can fine-tune.

### The four channels

| Channel | Controls | Range |
|---|---|---|
| **R — Metallic** | Is this a dielectric (paint) or a metal? | 0 = paint, 255 = pure metal |
| **G — Roughness** | How polished? | 0 = mirror, 255 = matte |
| **B — Clearcoat** | How much clearcoat gloss? | **16 = max gloss**, 255 = no clearcoat (inverted!) |
| **A — Specular Mask** | Rarely used. Reserved. | — |

> Warning: The B channel is **inverted** from intuition. Lower numbers = more clearcoat shine. `B=16` is the magic value for "max gloss." `B=255` means "no clearcoat" (looks dull). It's an iRacing convention.

### Iron rules

- **Chrome** = R255 / G0 / B16 (full metal, mirror polish, max clearcoat)
- **Glossy painted body** = R0 / G85 / B16 (paint, slightly polished, max clearcoat)
- **Matte plastic / vinyl wrap** = R0 / G220 / B15 (paint, very rough, slight clearcoat)
- **Brushed aluminum** = R255 / G140 / B30 (full metal, semi-rough, mid clearcoat)

You don't normally edit these by hand — pick a base finish and SPB sets them. But if you click **Custom Spec** in zone settings, you can override.

---

## 9. The Tools

The left toolbar groups tools into 9 categories. Hover any icon for a tooltip.

### Sel (Selection)
| Tool | Use |
|---|---|
| **Eyedropper** | Sample a pixel color (also adds it to the active zone) |
| **Magic Wand** | Select a color region by tolerance |
| **Select All** | `Ctrl+A` — select the whole canvas |
| **Edge Detect** | Auto-find edges in the current layer |

### Layer
| Tool | Use |
|---|---|
| **Move** | Drag a layer around the canvas |
| **Pick** | Click a pixel to auto-select the layer it's on |
| **Transform — NEW** | Scale / rotate / skew the selected layer |

### Draw
Brush, Erase, Color Brush, Recolor, Smudge, Pencil, Dodge, Burn, Blur, Sharpen, Clone, History Brush. Full Photoshop-style toolkit.

### Spatial
| Tool | Use |
|---|---|
| **Include** | Add a region to the active zone |
| **Exclude** | Subtract a region from the active zone |
| **Erase** | Erase from the active zone selection |

### Mask
Brush, Erase, Lasso — paint a non-destructive mask on the current layer.

### Shapes
Rect, Ellipse, Line, Polygon, Pen.

### Refn (Reference)
| Tool | Use |
|---|---|
| **Plus** | Add a reference image to the canvas overlay |
| **Minus** | Remove a reference |
| **Toggle** | Show/hide all references |

### Xfrm (Transform)
Transform (constrained) and Free Transform (anything goes).

### View
Rotate, Flip, Reset.

---

## 10. Layer Effects

**Double-click any layer** in the right panel to open the Layer Effects dialog — Photoshop fans will feel right at home.

| Effect | What it does |
|---|---|
| **Drop Shadow** | Soft shadow behind the layer pixels |
| **Outer Glow** | Soft halo around the layer |
| **Stroke** | Hard or soft outline (color, width, position: inside/center/outside) |
| **Color Overlay** | Tint the layer a single color (with blend mode + opacity) |
| **Bevel & Emboss** | Faux 3D ridge — useful for embossed text and chrome script |

Effects render live in the canvas and are baked into your spec output at render time.

> Tip: Heavy stacks of layer effects on many layers can slow Live Preview. If it gets sluggish, toggle effects off temporarily and re-enable before render.

---

## 11. Sponsor & Logo Tooling

SPB has dedicated workflows for sponsor patches.

### Outline
Adds a clean colored border around a layer's pixels. Use it to make a logo "pop" off the body color. Width and color are adjustable.

### Knockout
**Punches through** layers below — useful when you want a logo to expose the bare metal under your paint, or when you're cutting a window in a stripe.

### Mirror Clone
Duplicates the selected layer to the **opposite side of the car**. SPB knows where the centerline is. One click and your sponsor is on both doors, perfectly mirrored.

### Center on canvas / Fit to canvas
Quick alignment helpers for any layer — center horizontally, vertically, both, or scale to fit the paint dimensions.

---

## 12. Rendering

Click the big **RENDER** button in the header.

What happens:

1. SPB composites every zone's finish into the final color paint
2. SPB generates the matching spec map from your zone spec settings
3. (Where supported) SPB writes the metallic map
4. Files are saved as iRacing's expected `car_*.tga` filenames
5. Files are written to your iRacing paints folder via **Live Link** integration

Default destination for the demo Silverado: `Documents\iRacing\paint\trucks\silverado2019\car_<custid>.tga`.

> Tip: If iRacing is running, you can swap to the Paint screen and reload the car to see your render in-sim. No restart needed.

---

## 13. Live Preview

The Live Preview pane shows your paint composited into a 3D-aware view of the car body. It updates automatically as you change zones, finishes, or layer pixels.

- **Refresh manually:** press `F5` or click the 🔄 button in the preview header.
- **Split view:** drag the divider between Canvas and Preview to resize.
- **Stuck?** If the preview freezes (rare), `F5` forces a full re-render.

The preview uses the same Python rendering engine as the final RENDER — so what you see is what you'll get in iRacing (lighting differences aside; see FAQ).

---

## 14. Saving Your Work

SPB saves continuously and never asks "do you want to save?"

- **Auto-save** — every change you make is persisted to local state.
- **Last-loaded paint** — auto-restored when you re-open SPB.
- **Config export** — `File → Export Config` gives you a `.json` of zones + finishes (no pixels).
- **`.shokker` preset** — `Save SHOKK` button packages your zones, layer effects, and finish picks for sharing or backup.

> Tip: If a friend asks how you got that look, send them your `.shokker` file. They drop it into SPB and get your full setup.

---

## 15. Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` / `Ctrl+Y` | Redo |
| `Ctrl+S` | Save SHOKK preset |
| `Ctrl+R` | Render |
| `Ctrl+A` | Select All |
| `Ctrl+D` | Deselect |
| `Ctrl+0` | Fit canvas to view |
| `Ctrl++` / `Ctrl+-` | Zoom in / out |
| `Space + drag` | Pan canvas |
| `B` | Brush tool |
| `E` | Eraser |
| `I` | Eyedropper |
| `M` | Magic Wand |
| `V` | Move tool |
| `T` | Transform |
| `[` / `]` | Brush size down / up |
| `F5` | Refresh Live Preview |
| `F11` | Fullscreen |
| `Esc` | Cancel current operation |

---

## 16. Tips & Tricks

> Tip 1: Use **🔒 Lock Active Zone to This Layer** (gold button in the canvas dock). It's the single biggest workflow shortcut in the app — sets the layer restriction AND focuses your drawing tools on that layer in one click.

> Tip 2: Use **Foundation bases** (`Finishes → Bases → Foundation`) for clean solid colors. They're the cleanest, most predictable base layer.

> Tip 3: Use **Pattern overlays** sparingly. A subtle carbon weave on the hood reads as luxury; carbon weave on the entire car reads as a 2008 forum sig.

> Tip 4: **COLORSHOXX and MORTAL SHOKK auto-fill the base color** from your zone's color swatch. So if your zone is set to red, CX Inferno comes in red-tinted automatically. Use this to keep finishes on-brand.

> Tip 5: For symmetric sponsor placement, paint one side of the car and use **Mirror Clone**. Don't fight the centerline manually.

> Tip 6: If Live Preview is frozen, hit `F5` before assuming the render server is dead. 95% of the time it's just a stuck frame.

> Tip 7: For multi-color sponsor regions (e.g. a 3-color logo), add **multiple colors to a single zone**. The finish applies to all matched colors.

> Tip 8: Use **"Restrict to Layer"** for surgical paint application. Without it, your zone may bleed onto unrelated pixels of the same color.

> Tip 9: The **"Remaining"** selector is gold for body base color. Set up your detail zones first, then add a final zone with selector = Remaining and finish = your body color. Anything you forgot still gets painted.

> Tip 10: **Save a `.shokker` preset** every major step. It's tiny, it's free, and undo doesn't survive an app restart.

> Tip 11: Browse the **Spec Patterns** category. Most painters never touch them. They are the difference between "looks fine" and "looks expensive."

> Tip 12: Use the **Reference image** tool (`Refn`) to overlay a real-world car photo while you paint. Match the curves and the proportions, not just the colors.

---

## 17. Common Workflows

### Workflow A — Build a livery from scratch

1. `File → New` and pick your car (or open the default Silverado).
2. Add a `Body` zone with selector = **Everything** and your base color (e.g. gloss black). Set as Zone 2 priority.
3. Add a `Numbers` zone — eyedrop the number pixels, restrict to the Numbers layer, assign **COLORSHOXX Inferno**. Zone 1.
4. Add a `Stripes` zone — eyedrop stripe color, restrict to Stripes layer, assign a Pattern (carbon weave or plaid).
5. Add a `Sponsors` zone — restrict to Sponsors layer, assign **gloss white** so logos read clean.
6. Click **RENDER**.

### Workflow B — Recolor an existing PSD

1. `File → Open Paint…` → select your PSD.
2. For each color you want to swap: add a zone, eyedrop the source color, pick the new finish.
3. Use the **Remaining** selector for "leave everything else as-is" with a transparent base.
4. Render.

### Workflow C — Apply a sponsor logo with stroke + drop shadow

1. Add the sponsor as a new layer (drag from Photoshop, or use `Layer → Place Image`).
2. Position with **Move tool**, scale with **Free Transform**.
3. Use **Mirror Clone** to put it on both sides.
4. **Double-click the layer** → enable **Stroke** (2px white) and **Drop Shadow** (low opacity, 4px offset).
5. Add a zone restricted to the sponsor layer with finish = `Foundation → Gloss White` (or whatever color the logo wants).
6. Render.

### Workflow D — Match a real-world car paint

1. Open a reference photo of the car with the **Refn → Plus** tool.
2. Use the Eyedropper on your reference to sample the exact color.
3. In the Finishes panel, search for a base that matches the *type* of paint (Pearl, Candy, Metallic Flake, etc.).
4. Tune the spec channel manually (Custom Spec → drag G slider for roughness) until the highlights look right.
5. Compare side-by-side in Live Preview against your reference.

---

## 18. Troubleshooting

| Problem | Likely fix |
|---|---|
| Paint won't load | Check the file path. Try PSD instead of TGA. Confirm the file isn't open in Photoshop with a write lock. |
| Live Preview is blank | No zones added yet, or the render server died — restart SPB. |
| Number is still yellow after assigning a finish | You set the color but not the finish. Open the zone, scroll to **Finish**, click a base/monolithic. |
| Stripe color "bleeds" into another region | The stripe layer needs its own zone (with its own layer restriction). |
| Render button does nothing | Status bar shows server status — if it's red, restart SPB. |
| iRacing doesn't show new paint | Reload the car in the iRacing Paint screen. Confirm `car_*.tga` arrived in the trucks/silverado2019 folder. |
| App is sluggish | Too many zones, too many layer effects, or too-large paint dims. Try `F5` to reset preview, close other apps. |

---

## 19. FAQ

See [SPB_FAQ.md](SPB_FAQ.md) for 30+ Q&A pairs covering installation, workflow, file formats, spec maps, sharing, performance, and bug reporting.

---

## 20. Glossary

- **Paint** — your color file (PSD/TGA/PNG). The visible layer of the car.
- **Spec map** — the companion file iRacing uses to control reflectivity. RGB = Metallic / Roughness / Clearcoat.
- **Base** — a foundation finish material (gloss, matte, chrome, anodized, etc.).
- **Pattern** — a texture overlay applied on top of a base (carbon weave, plaid, hex, etc.).
- **Monolithic** — an all-in-one finish that bundles base + pattern + spec (COLORSHOXX, MORTAL SHOKK, PARADIGM).
- **Spec Pattern** — a PBR overlay pattern that modifies reflectivity independently of color.
- **Finish** — any of base / pattern / monolithic. The thing you assign to a zone.
- **Zone** — a rule that says "paint these pixels (matching colors X, Y, Z, restricted to layer L) with finish F." The atomic unit of SPB.
- **Layer (PSD)** — a Photoshop-style layer in your paint file. Editable, toggleable, can have effects.
- **Layer Restriction** — a zone setting that limits where a finish applies, scoped to one PSD layer.
- **Live Link** — the integration that writes finished renders directly into your iRacing paints folder.
- **PBR** — Physically Based Rendering. The lighting model iRacing (and most modern games) use.
- **Live Preview** — the real-time rendered view of your car body, updated as you paint.
- **`.shokker` file** — the SPB preset format. Bundles zones + finishes + layer effects for sharing.

---

## 21. Recipe Library

SPB ships with a curated library of preset recipes — complete zone configurations that load directly into the app, so you can start from a polished livery instead of a blank canvas. Recipes live in the `recipes/` folder at the project root and import via the **SHOKK library** or **Import Config** button.

Current library (v6.2.0):

- **NASCAR Classic** — Throwback stock car: gloss body, chrome numbers, carbon hood, matte lower trim.
- **GT3 Modern** — Pearl body with color-shift accents, gloss sponsors, brushed aluminum roof.
- **Stealth Matte** — Murdered-out matte black body with satin accent stripe and tinted numbers.
- **Rally Weathered** — Mud splatter, battle scars, and edge patina. Earned-not-given.
- **LMP Prototype** — Brushed aluminum body, carbon aero, fluorescent hi-viz accents.
- **Vintage 70s F1** — Gulf-style powder blue with marigold orange stripe and weathered patina.
- **Chrome Show Car** — Full chrome body, candy-colored accents, deep piano-black trim.
- **Drift Wrap** — Matte vinyl wrap base with bold graphic stripes and matte decals.
- **Muscle Car Stripe** — Deep gloss body, twin matte-black over-the-top stripes, chrome trim.
- **Hologram Chameleon** — Color-shift base, pearl overlay, iridescent sponsor panels.

Recipes are versioned (`version` field) and backward-compatible across SPB 6.x — a recipe built on v6.0 still loads cleanly on v6.2+. Unknown fields on older SPB versions are ignored on import. See `recipes/README.md` for format reference, usage instructions, and contribution guidelines.

---

## Closing thoughts

SPB is built by painters who got fed up with finishing liveries in Photoshop. If you find a bug, want a feature, or built something cool, find us on Discord (QR in the install folder) — we ship updates fast, and user feedback drives the roadmap.

Now go paint something nasty.

— The Shokker team
