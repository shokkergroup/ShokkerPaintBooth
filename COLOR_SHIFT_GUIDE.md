# Shokker Paint Booth — Color Shift Master Guide
## The Definitive Technical Reference for Color-Shifting Paint in iRacing

**Version 1.0 — February 2026**
**Classification: Internal Development Reference**

---

## Table of Contents

1. [The Physics of Real Color-Shift Paint](#1-the-physics-of-real-color-shift-paint)
2. [iRacing's Rendering Constraints](#2-iracings-rendering-constraints)
3. [What Competitors Are Doing (And Why It's Limited)](#3-what-competitors-are-doing)
4. [The Shokker Dual-Map Approach (Novel Technique)](#4-the-shokker-dual-map-approach)
5. [Technique Catalog: All Color-Shift Methods](#5-technique-catalog)
6. [Implementation Plan](#6-implementation-plan)
7. [The Showcar Strategy](#7-the-showcar-strategy)

---

## 1. The Physics of Real Color-Shift Paint

### 1.1 Thin-Film Interference (How Real Chameleon Paint Works)

Real color-shift paint (DuPont ChromaLusion, VIAVI ChromaFlair, Dupli-Color Color Shift) uses **thin-film interference** — the same physics that creates colors in soap bubbles and oil slicks.

**The 5-Layer Flake Structure:**
```
Layer 5: Transparent topcoat
Layer 4: Semi-transparent absorber (color filter)
Layer 3: Aluminum reflector (mirror)
Layer 2: Magnesium fluoride spacer (THIS controls the color)
Layer 1: Aluminum reflector (mirror)
```

Light enters the flake, bounces between the two aluminum mirrors, and exits. The **spacer layer thickness** determines which wavelengths constructively interfere (amplify) and which destructively interfere (cancel).

**The Critical Equation:**
```
2 * n * t * cos(θ) = m * λ
```
Where:
- `n` = refractive index of spacer
- `t` = spacer thickness
- `θ` = angle of light through the spacer
- `m` = interference order (integer)
- `λ` = wavelength of constructively interfered light

**Why Viewing Angle Changes Color:**
As `θ` changes (viewing angle), `cos(θ)` changes, which changes which `λ` (wavelength = color) satisfies the equation. At normal incidence (head-on), a flake might reflect green (530nm). At 45°, the effective path length shrinks, shifting to blue (470nm). At grazing angles, it shifts further to violet/purple.

**Natural Color Progressions (physically accurate):**
These follow the spectral order because shorter wavelengths satisfy the interference equation at steeper angles:
- Green → Blue → Purple → Pink (most common, ChromaFlair)
- Gold → Green → Blue → Purple (Mystichrome)
- Red → Orange → Gold → Green (warm shift)
- Teal → Blue → Violet (cool shift)

### 1.2 What Human Eyes Actually Perceive

The brain identifies "color-shift" through these cues:
1. **Smooth, continuous color transition** — not random; follows surface curvature
2. **Metallic depth** — the color appears to come from WITHIN the surface, not painted ON
3. **Specular flash** — bright white/colorless highlights at glancing angles (clearcoat)
4. **Gradient coherence** — adjacent areas have similar but slightly different hues
5. **View-dependent change** — as the camera/eye moves, colors smoothly transition

**Critical insight:** The human brain is remarkably easy to fool. If you provide cues #1, #2, #3, and #4, most viewers will ASSUME #5 is also happening, even on a static image. This is the basis of our approach.

---

## 2. iRacing's Rendering Constraints

### 2.1 The PBR Pipeline

iRacing uses standard **Metallic/Roughness PBR** (same as Unreal Engine, Unity HDRP):

```
F0 = mix(vec3(0.04), albedo_color, metalness)
F_schlick = F0 + (1 - F0) * pow(1 - NdotV, 5)
```

**Two files control appearance:**
- `car_num_{id}.tga` — 24-bit RGB diffuse/albedo (the "paint")
- `car_spec_{id}.tga` — 32-bit RGBA PBR channels:
  - R = Metallic (0=dielectric, 255=full metal)
  - G = Roughness (0=mirror, 255=rough)
  - B = Clearcoat (16=maximum, 0=off, >16=duller — INVERTED)
  - A = Specular mask (255=full)

**What happens at render time:**
1. When Metallic is HIGH: `F0 = albedo_color` → Paint color BECOMES the reflection color
2. Diffuse component drops to zero (metals don't diffuse-scatter)
3. Surface appearance = environment reflections × paint color
4. At grazing angles: Fresnel pushes reflections toward white (100% reflectance)

### 2.2 What We CANNOT Do

- **No custom shaders** — we can't add thin-film interference code
- **No normal maps for car paint** — all 4 spec channels are spoken for
- **No view-dependent color** — paint TGA is static; pixel (500,500) is always the same RGB
- **No per-pixel IOR control** — index of refraction is not a paintable channel
- **No anisotropic reflections** — can't fake brushed metal direction

### 2.3 What We CAN Exploit

1. **PBR Fresnel is REAL** — high metallic surfaces genuinely shift brighter/whiter at grazing angles
2. **Paint color IS reflection color** when metallic is high — we control what color reflects
3. **Both files are ours** — we control BOTH the paint AND the spec simultaneously
4. **Camera is always moving** in iRacing (chase cam, replays, spotter) — spatial color variation creates temporal shift
5. **Clearcoat vs. metallic creates two reflection layers** — colored metallic underneath, white clearcoat on top
6. **Roughness variation** creates micro-regions of different reflection behavior
7. **2048×2048 resolution** gives us ~4.2 million pixels to work with per file
8. **We know the UV layout** — we know which pixels map to which body panels

### 2.4 The Fundamental Insight

> **iRacing's PBR Fresnel IS a real color-shift mechanism.** When metallic is high, the surface reflects the paint color at normal incidence and shifts toward white at grazing angles. If we paint DIFFERENT colors in different spatial regions AND vary the metallic/roughness to create different Fresnel behaviors, the combination produces GENUINE view-dependent color variation — not a trick, but actual physics being exploited.

The difference between our approach and "true" chameleon paint: real paint shifts EVERY point independently based on view angle. We shift based on SPATIAL position + Fresnel. In motion (which is 99% of iRacing viewing), the result is perceptually identical.

---

## 3. What Competitors Are Doing

### 3.1 Current State of iRacing Color-Shift Paints

**Manual Photoshop painters ($50-$150/paint):**
- Apply gradient overlays in Photoshop across body panels
- Use 2-3 colors with soft blends
- Create spec maps with flat high-metallic values
- Result: Visible color bands, no organic flow, gradient direction is obvious

**Trading Paints Paint Builder:**
- Offers basic material finishes (chrome, matte, metallic)
- No color-shift capability at all
- Single material per layer

**What's missing from ALL competitors:**
1. No physically-motivated color ramps (they use arbitrary colors)
2. No coordination between paint and spec (spec is flat/uniform)
3. No micro-texture in the paint (just smooth gradients)
4. No exploitation of clearcoat variation for dual-layer shift
5. No UV-aware gradient mapping (they apply gradients globally, not per-panel)
6. No metallic variation to create differential Fresnel zones

### 3.2 Why "$100 Color Shift" Paints Look Flat

The typical competitor approach:
```
Paint TGA:  Linear gradient (purple → blue → green) across entire car
Spec TGA:   Flat metallic=200, roughness=20 everywhere
```

This produces:
- ❌ Visible gradient direction (looks like a Photoshop filter)
- ❌ No organic flow (straight lines on a curved car)
- ❌ Same Fresnel behavior everywhere (metallic is uniform)
- ❌ No depth perception (no micro-texture)
- ❌ Looks like a gradient, not like paint

---

## 4. The Shokker Dual-Map Approach (Novel Technique)

### 4.1 Overview: "Coordinated Dual-Map Color Shifting"

**This is the Shokker Paint Booth innovation — nobody else is doing this.**

Instead of treating paint and spec as independent files, we generate them as a **coordinated pair** where:

1. **The paint TGA** contains a physically-motivated color ramp with multi-scale organic flow
2. **The spec TGA** contains SPATIALLY VARIED metallic/roughness/clearcoat that creates DIFFERENT Fresnel behaviors in different regions
3. **The two maps are mathematically correlated** — regions with warmer colors get different metallic values than regions with cooler colors, creating genuine differential reflection behavior

The result: as the camera moves around the car, different regions show different reflection intensities AND different base colors simultaneously. This is NOT a static gradient that looks the same from every angle — the Fresnel variation means each region GENUINELY looks different from different viewing angles.

### 4.2 The Five Layers of Shokker Color Shift

**Layer 1: Macro Color Ramp (Paint TGA)**
Multi-directional sine-wave field mapped through a physically-accurate thin-film color sequence. This creates the broad color variation visible at car-length distance.
```
Primary gradient field: 4 directional sine waves at different frequencies
+ Perlin noise for organic breakup
→ Map through HSV color ramp following spectral interference order
```

**Layer 2: Micro Flake Texture (Paint TGA)**
High-frequency Voronoi/cellular noise that simulates individual metallic flakes catching light at different angles. Each "flake" gets a slightly different hue from the macro ramp, creating the sparkle depth that says "this is metallic paint, not a gradient."
```
Voronoi cell noise at fine scale (cell size ~4-8 pixels)
Each cell: sample macro ramp + small random hue offset
→ Creates per-flake color variation visible up close
```

**Layer 3: Fresnel Zone Mapping (Spec TGA — Metallic Channel)**
Instead of flat metallic everywhere, we vary metallic spatially:
- **"Head-on" regions** (hood center, door flats): M=200-220 — strong colored reflections
- **"Transition" regions** (fender curves, A-pillars): M=230-245 — approaching chrome
- **"Grazing" regions** (edges, panel seams): M=250-255 — near-full chrome

This creates GENUINE differential Fresnel behavior. The transition zones reflect more white at moderate angles (because their higher metallic makes F0 closer to the paint color, and the Fresnel curve is steeper). This is ACTUAL physics — not a visual trick.

```python
# Pseudo-NdotV map based on UV panel regions + surface curvature estimation
metallic = base_M + curvature_map * M_boost
# curvature_map: 0.0 = flat panel center, 1.0 = panel edge/curve
```

**Layer 4: Roughness Micro-Variation (Spec TGA — Roughness Channel)**
Subtle roughness variation creates regions where reflections are sharp (shows color clearly) vs slightly diffused (softens color into a glow):
```
roughness = base_R + micro_noise * R_variation
# base_R = 10-20 (mostly smooth)
# micro_noise: Perlin at multiple scales
# R_variation: ±8 (subtle but visible)
```
This mimics how real flake paint has individual flakes at slightly different orientations — some reflect sharply (low R), others scatter slightly (higher R).

**Layer 5: Clearcoat Competition (Spec TGA — Blue Channel)**
Spatially varied clearcoat creates a competing white specular layer:
- **Strong clearcoat (B=16)**: White highlights dominate at grazing angles — like the "flash" in real chameleon paint
- **Weaker clearcoat (B=24-36)**: Colored metallic reflections dominate
- **Pattern**: Varies inversely with metallic ramp — where metallic is lower, clearcoat is stronger, and vice versa

This creates a TWO-LAYER visual effect:
1. Base layer: Colored metallic reflections (from paint TGA × metallic)
2. Top layer: White clearcoat specular (from clearcoat channel)

The balance between these layers shifts with viewing angle — at grazing angles the clearcoat dominates (white flash), at normal incidence the colored metallic dominates. This IS how real chameleon paint works (interference layer + clearcoat topcoat).

### 4.3 The Coordinated Math

Here's the mathematical relationship between the two maps:

```python
# 1. Generate base gradient field (0-1, drives everything)
field = multi_directional_sine_field(shape, seed)  # 4 waves + Perlin noise
field = normalize_0_1(field)

# 2. PAINT TGA: Map field through color ramp
hue = primary_hue + field * hue_shift_range  # e.g., 120° + field * 240° for Mystichrome
saturation = 0.75 + field * 0.15  # peaks mid-shift
value = 0.55 + 0.20 * sin(field * pi)  # brightest in transition zone
paint_rgb = hsv_to_rgb(hue, saturation, value)

# 3. Add micro-flake texture to paint
flake_noise = voronoi_cells(shape, cell_size=6, seed=seed+1)
flake_hue_offset = flake_noise * 0.05  # ±5° hue per flake
paint_rgb = apply_flake_hue(paint_rgb, flake_hue_offset)

# 4. SPEC TGA: Metallic follows INVERSE of field (darker paint = more metallic)
metallic = 200 + (1 - field) * 50  # 200-250 range
# Add curvature-based boost
metallic = metallic + curvature_map * 15  # edges get 15 more metallic
metallic = clip(metallic, 180, 255)

# 5. SPEC TGA: Roughness — low base with micro-variation
roughness = 12 + micro_noise * 8  # 4-20 range, mostly smooth

# 6. SPEC TGA: Clearcoat follows field (opposing metallic)
clearcoat = 16 + field * 20  # 16-36 range
# Where metallic is HIGH (edges), clearcoat is LOW → colored reflections dominate
# Where metallic is LOWER (flats), clearcoat is HIGHER → white flash competes

# 7. Blend paint modification into original car paint
final_paint = original_paint * (1 - blend_strength * mask) + paint_rgb * blend_strength * mask
```

### 4.4 Why This Is Genuinely Novel

1. **Coordinated dual-map generation** — Paint and spec are generated from the SAME field, creating mathematical harmony between color and reflection behavior. Nobody else does this.

2. **Physically-motivated Fresnel zones** — We don't just set flat metallic values. We create GENUINE differential Fresnel behavior by varying metallic spatially, meaning different regions actually reflect differently at different viewing angles.

3. **Micro-flake paint texture** — Real chameleon paint has individual flakes. Our Voronoi-based micro-texture adds per-flake color variation that's visible up close, creating depth that gradients lack.

4. **Clearcoat-metallic opposition** — The competing dual-layer (colored metallic + white clearcoat) creates a genuine two-tone system where the balance shifts with viewing angle. This is actual physics, not a visual trick.

5. **Multi-scale approach** — Macro color ramp (visible at distance) + micro flake texture (visible close up) = realistic at ALL viewing distances. Competitor gradients look good from far away but flat up close.

6. **UV-aware curvature mapping** — We can estimate which UV regions correspond to curved vs. flat surfaces and adjust the Fresnel mapping accordingly, creating more natural transitions.

### 4.5 Comparison: Competitor vs. Shokker

| Aspect | Competitor ($100 paint) | Shokker Color Shift |
|--------|------------------------|---------------------|
| Paint TGA | Linear 2-color gradient | Multi-wave organic ramp with micro-flake texture |
| Spec TGA | Flat metallic=200 everywhere | Spatially varied M/R/CC coordinated with paint |
| Fresnel behavior | Same everywhere (uniform) | Differential — genuine view-dependent variation |
| Clearcoat | Flat or off | Opposing metallic — creates dual-layer competition |
| Visible from far | Looks like gradient | Looks like metallic paint with color depth |
| Visible up close | Smooth/flat/boring | Individual flake texture with hue variation |
| In motion | Static gradient scrolls past | Multiple effects interact — Fresnel + spatial + clearcoat |
| Cost to produce | 2-4 hours in Photoshop | 30 seconds automated |

---

## 5. Technique Catalog: All Color-Shift Methods

### 5.1 Method: Chameleon Gradient (Current — Enhanced)

**What it does:** Multi-directional sine-wave field → HSV hue ramp → blend into paint
**Paint:** Spatial color gradient following thin-film color sequence
**Spec:** spec_chameleon_pro — M=220, R=15, CC=16 (flat)

**Enhancement needed:** Currently the spec is flat (same M/R/CC everywhere). Adding the coordinated Fresnel zones and clearcoat opposition would dramatically improve this.

### 5.2 Method: Coordinated Dual-Map (NEW — The Shokker Innovation)

**What it does:** Full Layer 1-5 approach described in Section 4
**Paint:** Macro ramp + micro flake texture + brightness compensation
**Spec:** Spatially varied M (Fresnel zones), varied R (micro-roughness), varied CC (dual-layer opposition)

**This is the premium feature.** Every other method is a subset of this.

### 5.3 Method: Panel-Aware Color Mapping (NEW)

**What it does:** Uses knowledge of the car's UV layout to assign different base hues to different body panels, then blends smoothly at panel boundaries.

**Concept:** Real chameleon paint looks different on different panels because each panel faces a different direction. The hood (roughly horizontal) shows a different color than the door (roughly vertical) at any given viewing angle.

We can manually map this:
- Hood/roof/trunk (horizontal panels): Color A
- Doors/quarter panels (vertical panels): Color B
- Fenders/A-pillars (curved transitions): Gradient A→B
- Front bumper/nose (complex curves): Color C

**Paint:** Per-panel base hue with soft blending at boundaries
**Spec:** Per-panel metallic variation (flats lower, curves higher)

### 5.4 Method: Fresnel-Mapped Brightness Ramp (NEW)

**What it does:** Instead of shifting HUE, shifts BRIGHTNESS/VALUE based on estimated surface angle. Combined with high metallic, this creates genuine brightness shift that matches what real Fresnel does.

**Concept:** High metallic surfaces appear darker head-on and brighter at edges (Fresnel effect). If we pre-compensate by making the paint BRIGHTER in "head-on" regions and DARKER in "edge" regions, the Fresnel effect partially cancels in some areas and amplifies in others, creating an unusual brightness distribution that reads as "exotic paint."

**Paint:** Brightness/value gradient mapped to pseudo-NdotV regions
**Spec:** High uniform metallic (M=240+) to maximize Fresnel contribution

### 5.5 Method: Spectral Flake Field (NEW)

**What it does:** Generates a field of individual "flakes" using Voronoi cells, where each flake has a random orientation that determines its color from the shift ramp. Creates the look of actual metallic flake paint where individual flakes flash different colors.

**Concept:** In real chameleon paint, each micro-flake has a slightly different orientation relative to the viewer. At any given viewing angle, some flakes show green, some show blue, some show purple — creating a field of sparkle. As the view changes, each flake smoothly transitions through the spectrum.

We simulate this with Voronoi cells where each cell (flake) gets assigned a random "orientation" value, which determines where it falls on the color ramp.

**Paint:** Voronoi field → per-cell color from interference ramp
**Spec:** Per-cell metallic + roughness variation for individual flake behavior

### 5.6 Method: Dual-Tone Metallic (Enhancement of existing)

**What it does:** Two colors with an organic boundary, high metallic on both, different roughness values. The different roughness creates genuinely different Fresnel behavior for each color zone.

**Concept:** The simplest form of color shift — just two colors that transition smoothly. But our version adds roughness differentiation so the two zones actually BEHAVE differently under reflection.

**Paint:** Two HSV hues with Perlin noise boundary
**Spec:** Zone A: M=220, R=10 / Zone B: M=240, R=25 — different reflection behavior

### 5.7 Technique Combinations

The real power comes from COMBINING methods:

| Combo | Name | Paint Technique | Spec Technique |
|-------|------|----------------|----------------|
| 5.2 alone | Shokker Shift Pro | Full dual-map | Full coordinated |
| 5.2 + 5.3 | Panel-Aware Shift | Per-panel ramp + micro flake | Panel-aware M/R/CC |
| 5.2 + 5.5 | Spectral Flake Pro | Ramp + individual flakes | Per-flake M/R variation |
| 5.3 + 5.4 | Directional Shift | Panel hues + brightness | Panel M + brightness ramp |
| All combined | Shokker Ultimate | Everything | Everything |

---

## 6. Implementation Plan

### 6.1 Phase 1: Coordinated Dual-Map System (Core)

**Add to shokker_engine_v2.py:**

1. **New function: `generate_colorshift_field(shape, seed, params)`**
   - Generates the master gradient field that drives both paint and spec
   - Accepts parameters for wave frequencies, noise scales, field complexity
   - Returns normalized 0-1 field

2. **New function: `paint_colorshift_pro(paint, shape, mask, seed, pm, bb, params)`**
   - Takes the field and maps through a physically-accurate color ramp
   - Adds micro-flake Voronoi texture
   - Applies brightness compensation for dark paints
   - `params` dict: primary_hue, shift_range, saturation_curve, flake_size, flake_hue_spread

3. **New function: `spec_colorshift_pro(shape, mask, seed, sm, field, params)`**
   - Takes the SAME field used for paint
   - Generates coordinated M/R/CC channels:
     - M: base_M + (1 - field) * M_range → darker paint regions get more metallic
     - R: base_R + micro_noise * R_range → subtle roughness variation
     - CC: base_CC + field * CC_range → opposing metallic
   - `params` dict: M_base, M_range, R_base, R_range, CC_base, CC_range

4. **New monolithic entries in MONOLITHIC_REGISTRY:**
   - `colorshift_emerald` — Green → Blue → Purple (Mystichrome tribute but better)
   - `colorshift_inferno` — Red → Gold → Green (warm shift)
   - `colorshift_nebula` — Purple → Pink → Gold (cosmic)
   - `colorshift_ocean` — Teal → Blue → Violet (cool shift)
   - `colorshift_copper` — Copper → Magenta → Cyan (wide shift)
   - `colorshift_midnight` — Deep blue → Purple → Pink (dark luxury)

### 6.2 Phase 2: Micro-Flake System

1. **New function: `generate_flake_field(shape, seed, cell_size, density)`**
   - Voronoi-based cellular pattern
   - Each cell = one "flake" with random orientation value
   - Returns: flake_map (which cell each pixel belongs to), flake_orientations (per-cell 0-1 value)

2. **Integrate into paint_colorshift_pro:**
   - Each flake gets its macro ramp color + orientation-based hue offset
   - Flake boundaries get slightly different roughness (micro-edge effect)

### 6.3 Phase 3: Panel-Aware Mapping

1. **New function: `estimate_panel_curvature(shape, car_type)`**
   - Returns a curvature_map (0-1) estimating surface angle for each UV region
   - Uses known UV layouts for different car types
   - 0.0 = flat panel center (hood, roof, door)
   - 1.0 = curved transition (fender, A-pillar, bumper)

2. **Integrate into spec_colorshift_pro:**
   - Metallic boost at curved regions
   - Clearcoat variation matched to curvature

### 6.4 Phase 4: UI Integration

1. **New "Color Shift" section in Paint Booth:**
   - Preset selector (Emerald, Inferno, Nebula, Ocean, Copper, Midnight)
   - Custom color picker for start/end hues
   - Shift range slider (60° narrow → 300° full rainbow)
   - Flake size slider (fine 4px → coarse 12px)
   - Flake density slider
   - Fresnel zone strength slider
   - Clearcoat opposition strength slider

2. **Live preview** for color shift effects in the paint booth

### 6.5 Technical Notes

**Performance:** The coordinated approach generates one field and derives both maps from it — so it's actually FASTER than running independent spec and paint generators. Estimated render time: 2-4 seconds per zone for full color shift.

**Backward compatibility:** These are new monolithic finishes. They don't affect existing bases/patterns.

**Quality:** Because the paint and spec are mathematically linked, the result always looks physically coherent. You can't create "bad" combinations — the math enforces consistency.

---

## 7. The Showcar Strategy

### 7.1 The NASCAR Chevy Silverado Truck Concept

**Purpose:** A rolling billboard for Shokker Paint Booth that demonstrates every color-shift capability.

**Design Concept: "The Spectrum"**
- Full Shokker Paint Booth branding
- Multiple color-shift techniques visible on different panels
- QR code to Paint Booth download
- "Powered by Shokker Engine v3.0" branding

### 7.2 Recommended Base Paint Design

**The paint should be designed to MAXIMIZE the color-shift effect:**

1. **Dark base with bright accents** — Color shift shows best on medium-dark metallic surfaces. The base paint should be a medium gray or dark silver, NOT black (too dark kills metallic reflection) or white (too bright overwhelms the shift colors).

2. **Large uninterrupted body panels** — The color ramp needs physical space to transition. Minimize decals/logos on the main body so the shift effect has room to breathe.

3. **Strategic color zones:**
   - Main body (60-70%): Medium gray base → Full Shokker Color Shift treatment
   - Accent stripe: Complementary solid color to frame the shift effect
   - Number panel: Second color-shift variant (different hue range)
   - Sponsor panels: Clean areas for Shokker branding

4. **Recommended base colors:**
   - Main body: RGB(160, 160, 165) — medium silver-gray. Not too dark (kills reflections), not too bright (overwhelms shift colors). This becomes the canvas for the color-shift.
   - Accent: RGB(30, 30, 35) — near-black for contrast framing
   - The color shift will REPLACE these colors with the interference ramp

### 7.3 Multi-Zone Showcase Layout

```
Zone 1: Main body (60%) — Full Shokker Dual-Map Color Shift (Emerald variant)
         Green → Blue → Purple with micro-flake + Fresnel zones + CC opposition
         THE headline effect. This is what sells the product.

Zone 2: Hood/roof accent (15%) — Spectral Flake Pro variant
         Same color ramp but with visible individual flakes
         Shows "this isn't just a gradient — look at those flakes"

Zone 3: Number panel (5%) — Different color shift (Inferno: Red → Gold → Green)
         Proves we can do MULTIPLE shift palettes, not just one

Zone 4: Lower body/rocker (10%) — Directional Panel-Aware Shift
         Subtle, professional — shows it works at all viewing angles

Zone 5: Sponsors/logos (10%) — Clean gloss
         Shokker branding, URL, QR code — stays readable
```

### 7.4 Screenshot/Video Strategy

The truck should be photographed/recorded to maximize the shift visibility:
1. **Orbit shots** — Camera circling the parked car. Different regions light up differently.
2. **Track passing shots** — Car drives past camera. The color sweeps across body panels.
3. **Close-up flake shots** — Zoomed in to show micro-flake texture detail.
4. **Before/after comparison** — Plain paint vs. Shokker color shift on same car.
5. **Split-screen angles** — Same car from two different angles showing different color dominance.

---

## Appendix A: Color Ramp Presets (Physically Motivated)

These follow thin-film interference spectral progression:

| Preset | Start Hue | Shift Range | Color Journey | Inspiration |
|--------|-----------|-------------|---------------|-------------|
| Emerald | 120° | +240° | Green → Blue → Purple | ChromaFlair classic |
| Inferno | 0° | +120° | Red → Orange → Gold → Green | Warm interference |
| Nebula | 270° | +120° | Purple → Pink → Gold | Cosmic/luxury |
| Ocean | 190° | +100° | Teal → Blue → Indigo | Cool interference |
| Copper | 20° | +300° | Copper → Magenta → Violet → Teal | Full spectrum wrap |
| Midnight | 240° | +90° | Deep Blue → Purple → Magenta | Dark luxury |
| Mystichrome | 120° | +240° | Green → Blue → Purple (wide) | Ford SVT tribute |
| Solar Flare | 45° | +90° | Gold → Amber → Red | Sunset metal |
| Arctic | 180° | +60° | Teal → Cyan → Blue | Ice shift |
| Venom | 90° | -180° | Yellow-Green → Teal → Purple | Toxic |

## Appendix B: Reference Links

### PBR Theory
- LearnOpenGL PBR Theory: https://learnopengl.com/PBR/Theory
- Marmoset PBR Guide: https://marmoset.co/posts/basic-theory-of-physically-based-rendering/
- Adobe Substance PBR Guide Part 2: https://substance3d.adobe.com/tutorials/courses/the-pbr-guide-part-2

### Thin Film / Iridescence
- Wikipedia Thin-Film Interference: https://en.wikipedia.org/wiki/Thin-film_interference
- Alan Zucconi Car Paint Shader: https://www.alanzucconi.com/2017/10/27/carpaint-shader-thin-film-interference/
- VIAVI ChromaFlair Pigments: https://www.viavisolutions.com/en-us/osp/products/chromaflair

### iRacing Painting
- iRacing Custom Paint Textures: https://www.iracing.com/custom-paint-textures/
- Trading Paints Spec Map Guide: https://help.tradingpaints.com/kb/guide/en/what-is-a-spec-map-and-how-do-i-create-a-spec-map-for-iracing-khifMwlPLX
- BSimRacing Spec Map Tutorial: https://www.bsimracing.com/iracing-tutorial-how-to-use-custom-spec-maps/

### Color Shift Simulation
- Polycount UE4 Iridescent Materials: https://polycount.com/discussion/40373/iridescent-materials
- 80.lv Building Iridescence Shader: https://80.lv/articles/building-an-iridescence-shader-in-ue4
- Blender Artists Chameleon Car Paint: https://blenderartists.org/t/chameleon-car-paint/615333

---

*This guide is a living document. Update as new techniques are discovered and tested.*
