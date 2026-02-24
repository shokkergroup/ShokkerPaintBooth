# SHOKKER PAINT BOOTH — Master Knowledge Base

> **Last updated:** 2026-02-10
> **Purpose:** Comprehensive reference for the Shokker Paint Booth engine — iRacing PBR rendering, finish algorithms, color-shift techniques, feature roadmap, and architectural decisions.

---

## Table of Contents

1. [iRacing PBR Spec Map System](#1-iracing-pbr-spec-map-system)
2. [Current Engine Architecture](#2-current-engine-architecture)
3. [Complete Finish Registry](#3-complete-finish-registry)
4. [Color-Shifting / Chameleon Techniques](#4-color-shifting--chameleon-techniques)
5. [New Finish Ideas (Research)](#5-new-finish-ideas-research)
6. [Feature Roadmap & Tool Improvements](#6-feature-roadmap--tool-improvements)
7. [Critical Lessons & Gotchas](#7-critical-lessons--gotchas)
8. [Reference Values & Presets](#8-reference-values--presets)
9. [Sources & References](#9-sources--references)

---

## 1. iRacing PBR Spec Map System

### 1.1 Channel Definitions

iRacing's spec map is a **32-bit RGBA TGA** (2048x2048). Each channel controls a different PBR material property:

| Channel | Property | Range | Notes |
|---------|----------|-------|-------|
| **R** | Metallic | 0–255 | 0=dielectric, 255=full metal. Typically binary (0 or 255), but grays work for semi-metallic |
| **G** | Roughness | 0–255 | 0=mirror smooth, 255=completely matte/diffuse |
| **B** | Clearcoat | 0–255 | **INVERTED**: 0-15=disabled, 16=MAX shine, 17-255=progressively duller |
| **A** | SpecMask | 0–255 | 255=full specular, 0=environment effects masked out. Rarely used by painters |

### 1.2 File Naming Convention
- Paint: `car_num_{customerID}.tga` — 24-bit RGB, 2048x2048
- Spec: `car_spec_{customerID}.tga` — 32-bit RGBA, 2048x2048
- Location: `Documents\iRacing\paint\{vehicle}\`

### 1.3 The Clearcoat Blue Channel (Critical)

The B channel behavior changed in **2023 Season 1** (December 2022):

- **B=0 to B=15**: Clearcoat **DISABLED** (pre-2023 behavior)
- **B=16**: **MAXIMUM** clearcoat shine — the shiniest possible clear shell
- **B=17 to B=254**: Progressively **duller** clearcoat
- **B=255**: Dullest clearcoat — sun-baked junkyard look

The clearcoat is a **separate specular layer** on top of the base material. It has its own (always white/untinted) specular response independent of metallic/roughness. You can have matte metal under glossy clearcoat.

### 1.4 PBR Physics: How Metallic Interacts with Paint Color

iRacing uses the standard metallic/roughness PBR workflow. The core Fresnel formula:

```
F0 = mix(vec3(0.04), albedo_color, metalness)
```

**When Metallic = 0 (Non-Metal):**
- F0 = 0.04 (4% reflectance, white/achromatic reflections)
- Paint color drives diffuse component
- Reflections are UNTINTED (white/gray environment reflections)

**When Metallic = 255 (Full Metal):**
- F0 = albedo_color (paint TGA color BECOMES the reflection color)
- Diffuse drops to ZERO — metals have no diffuse scattering
- Surface appearance comes entirely from reflections colored by the paint
- **Dark paint + high metallic = VERY dark car** (this is critical to understand)

**Fresnel-Schlick Approximation:**
```
F = F0 + (1 - F0) * (1 - cos(theta))^5
```
At grazing angles, ALL materials approach 100% white reflectance regardless of F0. This means metallic surfaces look brighter/whiter at edges — a natural "shift" effect.

### 1.5 Key Implication for Paint Colors

iRacing's metallic rendering makes colors appear **significantly darker** than the paint TGA values. For metallic finishes:
- Chrome/mirror: Paint TGA must be near-white (RGB ~240-255)
- Metallic red: Paint TGA should be ~RGB(220, 60, 60) for a rich red in-game
- Dark base + high metallic = practically invisible car

### 1.6 What iRacing CANNOT Do

These effects are **impossible** through the spec map system:
1. **True pearlescent / color-shifting** — requires multi-layer thin-film interference shader
2. **Anisotropic reflections** — no BRDF anisotropy parameter; must fake via albedo texture
3. **Independent reflection tint vs. diffuse color** — PBR metallic ties these together
4. **True chameleon / flip-flop paint** — would need view-angle-dependent color shader
5. **Subsurface scattering** — no SSS in car paint shader
6. **User-controllable normal/bump maps** — all 4 spec channels are spoken for
7. **Per-pixel IOR control** — not exposed as a paintable channel

### 1.7 Environment Reflections

iRacing uses cubemap-based reflections controlled in `rendererDX11.ini`:
- `NumFixedCubemaps`: Static pre-baked env maps (100 = 1/frame)
- `NumDynamicCubemaps`: Real-time rendered env maps (default 0, perf-intensive)
- `ShaderQuality`: 0-3 (level 3 = experimental per-pixel lighting)

High metallic + low roughness = sharp cubemap reflections tinted by base color. Dynamic cubemaps create naturally shifting colors as car moves through different lighting.

---

## 2. Current Engine Architecture

### 2.1 File Structure

```
ShokkerEngine/
├── shokker_engine_v2.py    # ~1200 lines, core rendering engine
├── paint-booth-v2.html     # ~7000+ lines, web UI (monolithic)
├── server.py               # ~615 lines, Flask server
├── KNOWLEDGE_BASE.md       # This file
├── FINISH_AUDIT.md         # Finish testing notes
├── ROADMAP.md              # Feature roadmap
└── output/                 # Rendered output files
```

### 2.2 Compositing System (v3.0)

The engine uses a **Base + Pattern** compositing model:

- **Bases** (28): Define flat material properties (Metallic, Roughness, Clearcoat) + optional paint effect
- **Patterns** (38): Define spatial texture shape (0-1 array) that modulates the base properties
- **Monolithics** (21): Special finishes that bypass the base+pattern system entirely (incl. 7 chameleon/color-shift)

**Composition formula:**
```python
final_R = base_R + pattern_val * R_range * sm
final_M = base_M + pattern_val * M_range * sm
```

When both base and pattern have paint effects, both run at **0.7x** to prevent double-stacking.

### 2.3 Function Signatures

```python
# Spec functions: generate spec map RGBA
def spec_*(shape, mask, seed, sm) -> np.array(h, w, 4, uint8)

# Paint functions: modify paint RGB in-place
def paint_*(paint, shape, mask, seed, pm, bb) -> np.array(h, w, 3, float[0-1])

# Texture/pattern functions: generate spatial pattern
def texture_*(shape, mask, seed, sm) -> dict {
    "pattern_val": array[0-1],  # spatial shape
    "R_range": float,            # roughness modulation
    "M_range": float,            # metallic modulation
    "CC": int or array,          # clearcoat override
    "R_extra": array (optional), # independent R noise
    "M_extra": array (optional), # independent M noise
}
```

### 2.4 Intensity Levels

```python
INTENSITY = {
    "subtle":     {"paint": 0.5,  "spec": 0.6,  "bright": 0.03},
    "medium":     {"paint": 0.8,  "spec": 1.0,  "bright": 0.06},
    "aggressive": {"paint": 1.0,  "spec": 1.5,  "bright": 0.10},
    "extreme":    {"paint": 1.5,  "spec": 2.0,  "bright": 0.15},
}
```

### 2.5 Paint Booth UI (paint-booth-v2.html)

- Zone-based color picking (pick colors, assign finishes)
- 1,085 total finishes (28 bases × 38 patterns = 1,064 combos + 21 monolithics)
- Drawing tools: Eyedropper, Brush, Eraser, Rectangle, Magic Wand, Gradient
- Canvas zoom + pan (Spacebar+drag, middle-click, mousewheel zoom)
- Batch rendering: Fleet mode, Season mode
- Save/Load configurations, Export ZIP
- Live Link to iRacing (pushes files directly)
- Color Harmony panel (complement, analogous, triadic, split)
- Finish Library with search/filter
- Gear dropdown for settings

---

## 3. Complete Finish Registry

### 3.1 Bases (28)

| ID | Name | M | R | CC | Paint Effect | Notes |
|----|------|---|---|----|----|-------|
| `gloss` | Gloss | 0 | 20 | 16 | none | Standard glossy clearcoat |
| `matte` | Matte | 0 | 215 | 0 | none | Flat matte, zero shine |
| `satin` | Satin | 0 | 100 | 10 | none | Soft satin, partial clearcoat |
| `metallic` | Metallic | 200 | 50 | 16 | subtle_flake | Standard metallic with visible flake |
| `pearl` | Pearlescent | 100 | 40 | 16 | fine_sparkle | Iridescent sheen |
| `chrome` | Chrome | 255 | 2 | 0 | chrome_brighten | Pure mirror chrome |
| `candy` | Candy | 200 | 15 | 16 | fine_sparkle | Deep wet candy glass (M bumped for depth) |
| `satin_metal` | Satin Metallic | 235 | 65 | 16 | subtle_flake | Subtle brushed satin |
| `brushed_titanium` | Brushed Titanium | 180 | 70 | 0 | brushed_grain | Heavy directional grain |
| `anodized` | Anodized | 170 | 80 | 0 | subtle_flake | Gritty matte anodized |
| `frozen` | Frozen | 225 | 140 | 0 | subtle_flake | Frozen icy matte metal |
| `blackout` | Blackout | 30 | 220 | 0 | none | Stealth murdered-out ultra dark |
| `ceramic` | Ceramic | 60 | 8 | 16 | ceramic_gloss | Ultra-smooth deep wet shine |
| `satin_wrap` | Satin Wrap | 0 | 130 | 0 | satin_wrap | Vinyl wrap non-metallic sheen |
| `primer` | Primer | 0 | 200 | 0 | primer_flat | Raw flat primer gray |
| `gunmetal` | Gunmetal | 220 | 40 | 16 | subtle_flake | Dark blue-gray metallic |
| `copper` | Copper | 190 | 55 | 16 | warm_metal | Warm oxidized copper |
| `chameleon` | Chameleon | 160 | 25 | 16 | chameleon_shift | Dual-tone color-shift |
| `satin_chrome` | Satin Chrome | 250 | 45 | 0 | chrome_brighten | BMW silky satin chrome |
| `spectraflame` | Spectraflame | 245 | 8 | 16 | spectraflame | Hot Wheels candy-over-chrome |
| `frozen_matte` | Frozen Matte | 210 | 160 | 0 | subtle_flake | BMW Individual frozen metallic |
| `cerakote` | Cerakote | 40 | 130 | 0 | tactical_flat | Mil-spec ceramic tactical |
| `sandblasted` | Sandblasted | 200 | 180 | 0 | none | Raw sandblasted metal |
| `vantablack` | Vantablack | 0 | 255 | 0 | none | Absolute void zero reflection |
| `rose_gold` | Rose Gold | 240 | 12 | 16 | rose_gold_tint | Pink-gold metallic shimmer |
| `surgical_steel` | Surgical Steel | 245 | 6 | 0 | chrome_brighten | Medical grade mirror |
| `duracoat` | Duracoat | 25 | 170 | 0 | tactical_flat | Tactical epoxy coating |
| `powder_coat` | Powder Coat | 20 | 155 | 0 | none | Thick industrial powder coat |

### 3.2 Patterns (38)

| # | ID | Name | R_range | M_range | CC | Special |
|---|-----|------|---------|---------|-----|---------|
| 1 | `none` | None | — | — | — | No overlay |
| 2 | `carbon_fiber` | Carbon Fiber | 50 | 0 | 16 | 2x2 twill weave |
| 3 | `forged_carbon` | Forged Carbon | 50 | 40 | 16 | Chopped irregular chunks |
| 4 | `diamond_plate` | Diamond Plate | -132 | 60 | 0 | Industrial raised diamonds |
| 5 | `dragon_scale` | Dragon Scale | -157 | 135 | 16 | Hex reptile scales |
| 6 | `hex_mesh` | Hex Mesh | -155 | 155 | 16 | Honeycomb wire grid |
| 7 | `ripple` | Ripple | -85 | 100 | 16 | Water drop rings |
| 8 | `hammered` | Hammered | -112 | 95 | 0 | Hand-hammered dimples |
| 9 | `lightning` | Lightning | -177 | 175 | 16 | Forked bolt paths |
| 10 | `plasma` | Plasma | -118 | 95 | 16 | Electric plasma veins |
| 11 | `hologram` | Hologram | -75 | 0 | 16 | Horizontal scanlines |
| 12 | `interference` | Interference | 100 | 0 | 16 | Rainbow wave bands |
| 13 | `battle_worn` | Battle Worn | 80 | 30 | var | Scratched damage |
| 14 | `acid_wash` | Acid Wash | 60 | 35 | var | Corroded acid-etched |
| 15 | `cracked_ice` | Cracked Ice | 115 | 0 | 16 | Frozen crack network |
| 16 | `metal_flake` | Metal Flake | 0 | 50 | 16 | Coarse metallic flake |
| 17 | `holographic_flake` | Holographic Flake | 40 | 0 | 16 | Rainbow prismatic micro-grid |
| 18 | `stardust` | Stardust | -52 | 95 | 16 | Sparse bright pinpoints |
| 19 | `pinstripe` | Pinstripe | -60 | 40 | 16 | Thin parallel stripes |
| 20 | `camo` | Camo | 60 | -30 | 0 | Digital splinter blocks |
| 21 | `wood_grain` | Wood Grain | 80 | -50 | 0 | Natural flowing wood |
| 22 | `snake_skin` | Snake Skin | -100 | 80 | 16 | Elongated reptile scales |
| 23 | `tire_tread` | Tire Tread | 80 | -40 | 0 | V-groove rubber tread |
| 24 | `circuit_board` | Circuit Board | -120 | 140 | 16 | PCB traces with pads |
| 25 | `mosaic` | Mosaic | -90 | 80 | 16 | Voronoi stained glass |
| 26 | `lava_flow` | Lava Flow | -140 | 120 | var | Molten rock with cracks |
| 27 | `rain_drop` | Rain Drop | -80 | 60 | 16 | Water droplet beading |
| 28 | `barbed_wire` | Barbed Wire | -100 | 130 | 0 | Twisted wire with barbs |
| 29 | `chainmail` | Chainmail | -90 | 100 | 0 | Interlocking metal rings |
| 30 | `brick` | Brick | 60 | -40 | 0 | Offset brick + mortar |
| 31 | `leopard` | Leopard | 50 | -60 | 0 | Organic rosette spots |
| 32 | `razor` | Razor | -80 | 120 | 0 | Diagonal slash marks |
| 33 | `tron` | Tron | -120 | 180 | 0 | Neon 48px grid with 2px lines |
| 34 | `dazzle` | Dazzle | 60 | -80 | 0 | Bold Voronoi B/W dazzle camo |
| 35 | `marble` | Marble | -40 | 30 | 16 | Soft noise veins (zero-crossings) |
| 36 | `mega_flake` | Mega Flake | -50 | 60 | 0 | Large hex glitter flakes |
| 37 | `multicam` | Multicam | 40 | -30 | 0 | 5-layer organic Perlin camo |
| 38 | `magma_crack` | Magma Crack | -160 | 140 | 0 | Voronoi cracks + orange lava glow |

### 3.3 Monolithic Finishes (21)

| ID | Name | Spec | Paint | Description |
|----|------|------|-------|-------------|
| `phantom` | Phantom | spec_phantom | paint_phantom_fade | Ultra-mirror vanishes into reflections |
| `ember_glow` | Ember Glow | spec_ember_glow | paint_ember_glow | Hot ember metallic |
| `liquid_metal` | Liquid Metal | spec_liquid_metal | paint_liquid_reflect | Mercury/T-1000 chrome with distortions |
| `frost_bite` | Frost Bite | spec_frost_bite | paint_subtle_flake | Aggressive frozen metal |
| `worn_chrome` | Worn Chrome | spec_worn_chrome | paint_patina | Patchy chrome with oxidation |
| `oil_slick` | Oil Slick | spec_oil_slick | paint_oil_slick | Flowing rainbow pools |
| `galaxy` | Galaxy | spec_galaxy | paint_galaxy_nebula | Deep space nebula + stars |
| `rust` | Rust | spec_rust | paint_rust_corrosion | Progressive rust patches |
| `neon_glow` | Neon Glow | spec_neon_glow | paint_neon_edge | Edge-detected metallic glow |
| `weathered_paint` | Weathered Paint | spec_weathered_paint | paint_weathered_peel | Faded peeling layers |
| `chameleon_midnight` | Chameleon Midnight | spec_chameleon_pro | paint_chameleon_midnight | Purple → Teal → Gold (H=270, +150°) |
| `chameleon_phoenix` | Chameleon Phoenix | spec_chameleon_pro | paint_chameleon_phoenix | Red → Orange → Gold (H=0, +60°) |
| `chameleon_ocean` | Chameleon Ocean | spec_chameleon_pro | paint_chameleon_ocean | Blue → Teal → Emerald (H=220, +100°) |
| `chameleon_venom` | Chameleon Venom | spec_chameleon_pro | paint_chameleon_venom | Green → Teal → Purple (H=120, -150°) |
| `chameleon_copper` | Chameleon Copper | spec_chameleon_pro | paint_chameleon_copper | Copper → Magenta → Violet (H=20, +280°) |
| `chameleon_arctic` | Chameleon Arctic | spec_chameleon_pro | paint_chameleon_arctic | Teal → Blue → Purple (H=180, +90°) |
| `mystichrome` | Mystichrome | spec_chameleon_pro | paint_mystichrome | Ford SVT: Green → Blue → Purple (H=120, +240°) |
| `glitch` | Glitch | spec_glitch | paint_glitch | RGB channel offset + scanlines + tear bands |
| `cel_shade` | Cel Shade | spec_cel_shade | paint_cel_shade | Posterized flat tones + Sobel edge outlines |
| `thermochromic` | Thermochromic | spec_thermochromic | paint_thermochromic | Blue→Green→Yellow→Red thermal colormap |
| `aurora` | Aurora | spec_aurora | paint_aurora | Flowing green/cyan/pink borealis bands |

---

## 4. Color-Shifting / Chameleon Techniques

### 4.1 The Fundamental Challenge

Real chameleon paint (DuPont Chromalusion, VIAVI ChromaFlair) uses **thin-film interference** — 5-layer micro-prism flakes where light path differences cause constructive/destructive interference at specific wavelengths. As viewing angle changes, the apparent flake thickness changes, shifting which wavelengths interfere.

**We cannot replicate this** because iRacing has no thin-film shader. Our paint TGA is static — the same pixel is always the same color regardless of viewing angle.

### 4.2 What We CAN Exploit

1. **PBR Fresnel** — metallic surfaces naturally shift brighter/whiter at grazing angles
2. **Spatial color mapping** — paint DIFFERENT regions different colors to simulate what angle-dependent shifting would look like
3. **Clearcoat vs. metallic dual-layer** — clearcoat adds white specular on top of colored metallic reflections
4. **Camera motion in iRacing** — the camera is almost always moving (chase cam, TV cam, replays), so spatial color variation creates the ILLUSION of shifting

### 4.3 Strategy 1: Gradient Color Ramp (Primary Technique)

Generate a thin-film-accurate color ramp and map it across the car surface:

```python
def compute_chameleon_ramp(primary_hue, shift_range=120, steps=256):
    """Physically-motivated chameleon color sequence.
    Colors follow the spectral progression of thin-film interference."""
    ramp = []
    for i in range(steps):
        t = i / (steps - 1)
        hue = (primary_hue + t * shift_range) % 360
        sat = 0.7 + 0.3 * sin(t * pi)  # peaks mid-shift
        val = 0.3 + 0.15 * sin(t * pi * 0.5)  # moderate brightness
        ramp.append(hsv_to_rgb(hue/360, sat, val))
    return ramp
```

Map using multi-directional sine-wave gradients + Perlin noise for organic flow:

```python
field = (
    sin(y/h * pi*2.0 + x/w * pi*1.5) * 0.35 +
    sin(y/h * pi*0.8 - x/w * pi*2.2) * 0.25 +
    sin((y+x)/max(h,w) * pi*3.0) * 0.20 +
    perlin_noise * 0.20
)
```

### 4.4 Strategy 2: Fresnel-Exploiting UV-Region Mapping

Estimate "pseudo-viewing-angles" based on UV regions:
- **Flat panels** (hood, roof, trunk) — moderate NdotV at typical chase cam
- **Side panels** (doors, quarters) — head-on on near side, steep on far side
- **Curved transitions** (fenders, A-pillars) — strongest Fresnel shift zone

Paint primary chameleon color in "head-on" regions, shift color in "grazing" regions. PBR Fresnel then FURTHER enhances this, creating a double-shift effect.

### 4.5 Strategy 3: Clearcoat Variation

Vary clearcoat intensity spatially:
- Strong clearcoat zones: white highlights dominate (like looking edge-on)
- Weak clearcoat zones: metallic base color dominates (like looking head-on)

```python
# Clearcoat range: 16 (max) to 40 (moderate)
cc_values = 16 + cc_noise_field * 24 * sm
```

### 4.6 Recommended Chameleon Spec Values

```python
M = 220    # Very high metallic (not 255 to avoid full chrome)
R = 15     # Very smooth — sharp reflections show color clearly
CC = 16    # Full clearcoat for the white "flash" layer
A = 255    # Full spec mask
```

### 4.7 Chameleon Color Presets

| Preset | Head-On → Grazing | HSV Start | Shift |
|--------|-------------------|-----------|-------|
| **Midnight Galaxy** | Purple → Blue → Teal → Gold | H=270 | +150° |
| **Phoenix Fire** | Red → Orange → Gold | H=0 | +60° |
| **Ocean Depths** | Blue → Teal → Emerald | H=220 | +100° |
| **Toxic Venom** | Green → Teal → Purple | H=120 | -150° |
| **Copper Rose** | Copper → Magenta → Violet | H=20 | +280° |
| **Arctic Shift** | Teal → Blue → Purple | H=180 | +90° |

### 4.8 Honest Assessment

**What works:** Camera orbiting reveals different colored regions, creating a convincing shift impression. PBR Fresnel adds genuine brightness variation. Clearcoat creates "flash" highlights. In motion, the effect is quite convincing.

**What doesn't:** A single fixed point on the car never changes color — only different points have different colors. From a completely static camera, there is no shift. The color boundaries might be visible as bands at certain angles.

---

## 5. New Finish Ideas (Research)

### 5.1 High-Impact New Finishes (Recommended Next)

#### Mystichrome / Color-Flip (Monolithic)
Ford's legendary ChromaFlair paint. Multi-hue spatial gradient with high metallic.
- **Spec:** M=220, R=15, CC=16
- **Paint:** Directional gradient field through a 3-color HSV ramp (green→blue→purple) with Perlin noise for organic flow

#### Glitch / Digital Corruption (Monolithic)
VHS tracking errors + chromatic aberration aesthetic.
- **Spec:** Base M=160, R=50, CC=16. Random horizontal "tear bands" with drastically different values
- **Paint:** Separate RGB channels and offset them ±3-8px. Horizontal pixel-shift in tear bands. Scanlines every 2nd row. Random dead pixel blocks

#### Cel-Shaded / Comic Book (Monolithic)
Non-photorealistic flat cartoon look with bold outlines.
- **Spec:** M=0, R=180, CC=0 (kills all realistic reflections)
- **Paint:** Posterize RGB to 4-5 levels. Sobel edge detection for black outlines (2-3px thick)

#### Volcanic / Magma Crack (Pattern)
Cooled black obsidian with thin glowing orange cracks.
- **Texture:** Voronoi cells (100-150) for cooled plates. Boundary edges = magma cracks
- **Spec:** Cracks: smooth + metallic. Plates: rough + non-metallic
- **Paint:** Plates → near-black (RGB*0.12). Cracks → hot orange [255,140,20]

#### Dazzle Camouflage (Pattern)
WWI ship camo — bold geometric high-contrast patches. Not to hide but to confuse.
- **Texture:** Voronoi cells (30-50) with 3-level values (black/gray/white). Diagonal stripe overlays
- **Spec:** Subtle R variation between zones
- **Paint:** Map levels to near-black, mid-gray, near-white at 0.7 blend

#### Tron Lines (Pattern)
Neon light grid on dark surface.
- **Texture:** Orthogonal grid with 2px lines every 48px + intersection pads
- **Spec:** Lines = smooth + metallic. Background = matte
- **Paint:** Lines → full saturation + bright. Background → near black

### 5.2 Easy-to-Implement New Bases

| ID | Name | M | R | CC | Paint | Notes |
|----|------|---|---|----|----|-------|
| `satin_chrome` | Satin Chrome | 250 | 45 | 0 | Lighten 0.06 | BMW-style silky chrome |
| `spectraflame` | Spectraflame | 245 | 8 | 16 | Lighten + candy tint | Hot Wheels transparent lacquer over bare metal |
| `frozen_matte` | Frozen Matte | 210 | 160 | 0 | Very subtle flake | BMW Individual Frozen |
| `cerakote` | Cerakote | 40 | 130 | 0 | Darken 0.95x | Mil-spec ceramic firearm coating |
| `sandblasted` | Sandblasted | 200 | 180 | 0 | Neutral gray shift | Raw blasted metal |
| `powder_coat` | Powder Coat | 20 | 155 | 0 | Minimal noise | Thick epoxy powder finish |
| `vantablack` | Vantablack | 0 | 255 | 0 | Force near [5,5,5] | Blackest possible surface |
| `rose_gold` | Rose Gold | 240 | 12 | 16 | Shift to [210,160,140] | Electroplated rose gold |
| `surgical_steel` | Surgical Steel | 245 | 6 | 0 | Cool blue-gray shift | Ultra-clean medical grade |
| `duracoat` | Duracoat | 25 | 170 | 0 | Darken + desaturate | Tactical epoxy finish |

### 5.3 New Patterns

| ID | Name | Approach | Notes |
|----|------|----------|-------|
| `tron` | Tron Lines | Orthogonal grid 48px | Neon grid on dark |
| `wireframe` | Wireframe | 3-direction parallel lines (0°/60°/120°) | CAD mesh look |
| `marble` | Marble | Noise-based veins (softer than cracked_ice) | Polished stone |
| `gold_leaf` | Gold Leaf | Voronoi cells (foil sheets) + wrinkle noise | Hammered foil |
| `crocodile` | Crocodile | Randomized brick pattern + flat centers | Luxury leather |
| `shagreen` | Shagreen | Dense small circular bumps in 6x6 grid | Stingray leather |
| `ice_crystal` | Ice Crystal | Multi-scale directional branching noise | Windshield frost dendrites |
| `magma_crack` | Magma Crack | Voronoi boundaries = glowing cracks | Cooled lava crust |
| `dazzle` | Dazzle Camo | Large Voronoi + 3-level B/W values | WWI ship camo |
| `multicam` | Multicam | 5-layer Perlin with Gaussian-blurred edges | Organic military camo |
| `mega_flake` | Mega Flake | Large hex grid flakes with orientation vals | Visible glitter confetti |

### 5.4 New Monolithics

| ID | Name | Key Effect |
|----|------|------------|
| `mystichrome` | Mystichrome | Multi-hue color-shift gradient |
| `aurora` | Aurora Borealis | Flowing sine-wave color bands (green/cyan/pink/lavender) |
| `glitch` | Glitch | Chromatic aberration + scan lines + tear bands |
| `cel_shade` | Cel-Shaded | Posterize + Sobel edge outlines |
| `pixel_art` | Pixel Art | Downsample to coarse grid + reduced palette |
| `thermochromic` | Thermochromic | Noise-driven thermal colormap (blue→green→yellow→red) |
| `holo_vinyl` | Holographic Vinyl | Continuous flowing rainbow bands (not flake) |
| `copper_patina` | Copper Patina | Warm copper + verdigris green zones |
| `bronze_statue` | Bronze Statue | Dark bronze + heavy green-brown patina |
| `rain_soaked` | Rain Soaked | Vertical flow streaks + ultra-wet spec |
| `titanium_heat` | Titanium Heat Color | Directional gradient: straw→bronze→purple→blue |

---

## 6. Feature Roadmap & Tool Improvements

### 6.1 Phase 1 — Foundation (Highest Impact)

**Undo/Redo System**
- Command Pattern: each action becomes a reversible command object
- Lightweight "command intents" not full canvas snapshots
- 50+ step history, Ctrl+Z / Ctrl+Shift+Z
- History panel with action descriptions

**Keyboard Shortcuts**
| Key | Action | Key | Action |
|-----|--------|-----|--------|
| B | Brush | Ctrl+Z | Undo |
| E | Eraser | Ctrl+Shift+Z | Redo |
| I | Eyedropper | Ctrl+S | Save config |
| G | Gradient | Ctrl+Shift+E | Export |
| W | Magic Wand | [ / ] | Brush size |
| M | Rectangle | Tab | Toggle panels |
| Space+drag | Pan | F | Fullscreen canvas |
| 1-9 | Tool opacity | ? | Shortcut help |

**Layer System (Basic)**
- Layer stack: reorder, visibility toggle, lock toggle
- Blend modes via Canvas `globalCompositeOperation`: multiply, screen, overlay, etc.
- Per-layer opacity slider
- Flatten/merge operations

### 6.2 Phase 2 — Power Tools

**Masking Improvements**
- Lasso tool (freehand selection)
- Polygonal lasso (click-to-add-points)
- Bezier path tool (smooth curves)
- Feathered edges (Gaussian blur radius 1-20px)
- Selection grow/shrink/smooth/invert

**Symmetry / Mirror Mode**
- Mirror paint mode: paint on left, auto-mirror to right
- Adjustable center-line axis
- Paired zone groups (left fender / right fender)

**Template / Preset System**
- Pre-made zone configs per popular car model
- Design templates ("Gulf Racing", "NASCAR stock")
- User template sharing via JSON export/import

**Batch Multi-Zone Operations**
- Select multiple zones → apply same finish
- Find/replace color across all zones
- Batch finish swap (all Chrome → all Matte)

### 6.3 Phase 3 — Wow Factor

**3D Car Model Preview (Three.js WebGL)**
- Simplified car mesh with paint UV-mapped
- Orbit/zoom/pan controls
- Lighting presets (daylight, garage, night)
- Split view: 2D template + 3D preview side-by-side
- Environment reflections for metallic/chrome preview

**AI / Smart Features**
- **Auto zone detection:** k-means color clustering on paint TGA
- **Smart color suggestions:** given primary color, suggest accent colors via harmony rules
- **Auto-palette from image:** upload a photo, extract dominant colors
- **One-click schemes:** "NASCAR stock car look", "rally car look"

**Custom Finish Editor**
- Manual sliders: M(0-255), R(0-255), CC(0-16), A(0-255)
- Real-time spec map preview
- Finish comparison swatches
- Save custom finishes to user library

### 6.4 Phase 4 — Polish

**Export Options**
- PNG/JPG for social sharing
- PSD-compatible layered export
- Batch export (paint + spec + preview in one click)
- Trading Paints direct upload (if API available)

**Accessibility**
- Color blind simulation modes (deuteranopia, protanopia, tritanopia)
- High-contrast UI mode
- Guided onboarding tutorials
- ARIA labels for screen readers

**Additional Drawing Tools**
- Text tool with font selection
- Shape primitives (circle, rect, triangle, star)
- Snap-to-grid with configurable spacing
- Ruler overlays and draggable guide lines

### 6.5 Competitive Position

| Feature | Trading Paints | Shokker Paint Booth |
|---------|---------------|-------------------|
| Layers | Full (2025) | Planned |
| Zone-based painting | No | **YES** |
| Combinable finishes | 8 preset finishes | **1,085 total (1,064 combos + 21 monolithics)** |
| Batch fleet mode | No | **YES** |
| Live iRacing link | Via downloader | **YES** |
| AI features | None | Planned (unique) |
| 3D preview | Via iRacing viewer | Planned (WebGL) |
| Custom spec editor | No | Planned |
| Free | Pro required | **YES** |

---

## 7. Critical Lessons & Gotchas

### 7.1 Python on Windows (py.exe)

- `#!/usr/bin/env python3` shebang causes py.exe to route to **Microsoft Store Python** which lacks numpy/Pillow
- **NEVER** add shebang to generated scripts
- User has Python 3.13 at `C:\Python313` + Store Python
- Always generate `.bat` launchers alongside `.py` scripts
- Files created programmatically get Zone.Identifier flag — use `Unblock-File` in PowerShell

### 7.2 Engine Source File Protection

- Engine saves output to `car_num_{id}.tga` in the SAME dir as the source paint
- This **OVERWRITES** the original paint!
- Engine now backs up to `ORIGINAL_` prefix on first run
- On subsequent runs it loads from the backup (prevents cumulative corruption)

### 7.3 Paint Modifier Strength

- Carbon darken at 0.15 was WAY too aggressive (destroyed dark cars to pure black)
- Chrome brighten at 0.6 washed everything to gray
- **Safe range: 0.04–0.08** for visible effects that don't destroy
- When both base and pattern have paint effects: **0.7x reduction** each

### 7.4 TGA File Format

**Paint TGA:** 24-bit RGB, uncompressed, descriptor 0x20 (top-left origin)
**Spec TGA:** 32-bit RGBA, uncompressed, BGRA byte order, descriptor 0x28 (top-left origin)

### 7.5 Clearcoat Migration (2023)

When iRacing migrated to the new clearcoat system, existing paints defaulted to B=255 (full shine). This broke many custom paints. To restore pre-2023 appearance: set B=0 (clearcoat disabled).

---

## 8. Reference Values & Presets

### 8.1 Trading Paints Spec Presets

| Preset | R(M) | G(R) | B(CC) | Hex | Description |
|--------|------|------|-------|-----|-------------|
| Shiny Side Up | 255 | 64 | 18 | #FF4012 | Heavy metallic, 25% rough |
| Freshly Waxed | 255 | 26 | 217 | #FF1AD9 | Full metallic, 10% rough, dull CC |
| Brushed Alloy | 255 | 128 | 64 | #FF8040 | Full metallic, 50% rough |
| Arizona Patina | 229 | 178 | 0 | #E5B200 | 90% metallic, 70% rough, no CC |
| Pure Chrome | 255 | 0 | 0 | #FF0000 | Full metal, zero rough, no CC |
| Max Clearcoat | 0 | 0 | 16 | #000010 | No metallic, smooth, max CC |

### 8.2 Common Community Recipes

**Chrome:** M=255, R=0, CC=0. Paint near-white.
**Candy:** M=255, R=26, CC=217. Paint saturated + lightened.
**Matte:** M=0, R=200+, CC=0. Paint normal.
**Brushed Metal:** M=255, R=128, CC=64. Paint with directional streaks in albedo.
**Carbon Fiber:** M=0-30, R=80-140, CC=16-32. Paint with woven pattern.
**Anodized:** M=180-220, R=40-80, CC=0. Paint saturated + lightened.

### 8.3 Thin-Film Interference Color Sequences

Real chameleon paints follow spectral progressions:
- Purple → Blue → Teal → Green → Gold
- Red → Orange → Gold → Green
- Blue → Purple → Magenta → Red
- Green → Gold → Copper → Purple

These are NOT arbitrary — they follow the wavelength progression of constructive interference at increasing optical path lengths through thin-film flakes.

---

## 9. Sources & References

### iRacing Official
- [iRacing Custom Paint Textures](https://www.iracing.com/custom-paint-textures/)
- [iRacing Paint Textures Support](https://support.iracing.com/support/solutions/articles/31000153524-paint-textures)
- [2023 Season 1 Release Notes](https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-)
- [rendererDX11.ini](https://github.com/CraigLager/iRacing/blob/master/rendererDX11.ini)

### Trading Paints
- [Spec Map: Shiny Side Up](https://blog.tradingpaints.com/spec-map-shiny-side-up/)
- [Spec Map: Freshly Waxed](https://blog.tradingpaints.com/spec-map-freshly-waxed/)
- [Spec Map: Brushed Alloy](https://blog.tradingpaints.com/spec-map-brushed-alloy/)
- [Spec Map: Arizona Patina](https://blog.tradingpaints.com/spec-map-arizona-patina/)
- [Paint Builder Basics](https://help.tradingpaints.com/paint-builder/paint-builder-basics/)
- [Sim Preview](https://help.tradingpaints.com/paint-builder/sim-preview-viewing-your-paint-builder-projects-in-iracings-3d-car-model-viewer/)

### PBR Theory
- [LearnOpenGL: PBR Theory](https://learnopengl.com/PBR/Theory)
- [Marmoset: Basic Theory of PBR](https://marmoset.co/posts/basic-theory-of-physically-based-rendering/)
- [Substance 3D: PBR Guide](https://substance3d.adobe.com/tutorials/courses/the-pbr-guide-part-1)
- [Chaos: Understanding Metalness](https://blog.chaos.com/understanding-metalness)

### Color Shifting / Thin-Film
- [Alan Zucconi: Car Paint Shader - Thin Film Interference](https://www.alanzucconi.com/2017/10/27/carpaint-shader-thin-film-interference/)
- [Alan Zucconi: Iridescence on Mobile](https://www.alanzucconi.com/2017/07/21/iridescence-on-mobile/)
- [Belcour & Barla 2017: Practical Extension to Microfacet Theory for Iridescence](https://belcour.github.io/blog/research/publication/2017/05/01/brdf-thin-film.html)
- [ThreeJS Thin Film Iridescence](https://github.com/DerSchmale/threejs-thin-film-iridescence)
- [VIAVI ChromaFlair Pigments](https://www.viavisolutions.com/en-us/osp/products/chromaflair)
- [NVIDIA 2024: Appearance Modeling of Iridescent Feathers](https://research.nvidia.com/publication/2024-11_appearance-modeling-iridescent-feathers-diverse-nanostructures)
- [Polycount: Emulating Iridescent/Pearlescent in PBR](https://polycount.com/discussion/140473/how-would-you-emulate-iridescent-pearlescent-materials-in-pbr)

### Community Tutorials
- [bSimRacing: Custom Spec Map Tutorial](https://www.bsimracing.com/iracing-tutorial-how-to-use-custom-spec-maps/)
- [SimWrapMarket: Clearcoat Blues](https://www.simwrapmarket.com/post/iracing-and-the-clearcoat-blues)
- [Gabir Motors: Spec Map Tool](https://gabirmotors.com/tools/specmapping)
- [Gabir Motors: Liveries Guide](https://gabirmotors.com/tutorials/iracing-liveries-guide)
- [EdRacing: DirectX 11 Compilation](http://www.edracing.com/edr/DirectX_11.php)

### Automotive Paint
- [Ford Mystichrome Press Release](https://www.mystichrome.com/authority/pressrelease-ford/)
- [Hot Wheels Spectraflame Explained](https://munclemikes.com/blogs/news/what-is-spectraflame-hot-wheels-spectreflame-paint-explained)
- [BMW Frozen Paint Explained](https://www.autoevolution.com/news/bmw-frozen-paint-explained-video-66464.html)
- [3M Satin Flip Wraps](https://www.rvinyl.com/3M-Wrap-Film-Series-2080-Satin-Flip-Psychedelic-Vinyl)

### Web Technologies
- [Canvas Blend Modes (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation)
- [Konva.js Canvas Editor](https://konvajs.org/docs/sandbox/Canvas_Editor.html)
- [Three.js Car Visualizer](https://carvisualizer.plus360degrees.com/threejs/)
- [Photopea Web Editor](https://www.photopea.com/)
- [Lasso Canvas Library](https://github.com/akcyp/lasso-canvas-image)

---

*This document is the comprehensive reference for all Shokker Paint Booth development. Update it as new features are implemented or new research is conducted.*
