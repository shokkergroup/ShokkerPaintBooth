# Shokker Paint Booth — PBR System

## What is PBR in iRacing?

iRacing uses a Physically Based Rendering (PBR) pipeline for car paint. Each car has two key files:

1. **Paint File** (`car_XXX.tga`) — The visible color/texture of the car. 32-bit RGBA TGA, 2048×2048.
2. **Spec Map** (`car_XXX_spec.tga`) — Controls how light interacts with every pixel. 32-bit RGBA TGA, 2048×2048.

The spec map is where the Shokker Paint Booth does its magic. By controlling the spec map channels, we control whether a surface looks like chrome, matte rubber, glossy candy paint, carbon fiber, or anything else.

## Spec Map Channel Breakdown

The spec map is a standard 32-bit TGA where each RGBA channel encodes a different physical property:

### Red Channel — Metallic (0–255)
- **0** = Fully dielectric (plastic, rubber, paint)
- **255** = Fully metallic (chrome, bare metal)
- **Default**: 5 (slight metallic hint for standard paint)
- Higher values make the surface reflect the environment color rather than a fixed specular color
- Chrome finishes push this to 200–255
- Matte/rubber finishes keep this at 0–10

### Green Channel — Roughness (0–255)
- **0** = Mirror-smooth (perfect reflections)
- **255** = Extremely rough (completely diffuse)
- **Default**: 100 (standard automotive paint)
- Gloss finishes: 30–60
- Matte finishes: 160–220
- Chrome: 10–30
- Frozen/ice effects: 140–180

### Blue Channel — Clearcoat (0–255)
- **0–15** = Clearcoat OFF
- **16+** = Clearcoat ON (value controls clearcoat roughness)
- **Default**: 16 (clearcoat on, smooth)
- This is a threshold system, not linear — the jump from 15→16 enables the clearcoat layer
- Higher values = rougher clearcoat (orange peel, weathered clear)
- Carbon fiber typically: clearcoat ON with moderate roughness

### Alpha Channel — Spec Authority / Mask (0–255)
- **0** = Spec map has NO effect (iRacing uses its default shading)
- **255** = Spec map has FULL control
- **Default**: 255 (full authority)
- This channel determines how much the spec map overrides iRacing's built-in material
- Partial values (64, 128) create blended effects between custom spec and iRacing default
- Useful for subtle effects where you want some iRacing default behavior to show through

## Default Spec Values

When a zone has no finish applied or uses "standard paint":
```
Metallic  = 5
Roughness = 100
Clearcoat = 16  (on, smooth)
Authority = 255 (full control)
```

These defaults produce a reasonable automotive paint look.

## How compose_finish() Works

The compositing system combines a base material with a pattern texture:

```python
def compose_finish(base_id, pattern_id, shape, mask, seed, sm, 
                   scale=1.0, spec_mult=1.0, rotation=0):
```

**Parameters:**
- `base_id` — Which base material (e.g., "gloss", "chrome", "candy_red")
- `pattern_id` — Which pattern overlay (e.g., "carbon_fiber", "hex_mesh")
- `shape` — The 2D area being processed (2048×2048 or scaled)
- `mask` — Zone mask (which pixels belong to this zone)
- `seed` — Random seed for reproducible noise/patterns
- `sm` — Spec multiplier dict with keys: spec_mult, paint_mult, bright_mult
- `scale` — Pattern scale factor (default 1.0)
- `spec_mult` — Additional spec intensity multiplier
- `rotation` — Pattern rotation in degrees

**Process:**
1. Look up base in `BASE_REGISTRY` → get base M/R/CC/A values
2. Look up pattern in `PATTERN_REGISTRY` → get pattern texture generator
3. Generate pattern texture at specified scale/rotation
4. Modulate base values with pattern: the pattern creates variation across the surface
5. Apply spec multiplier for intensity control
6. Return composited spec map array

## Monolithic Finishes

Monolithics bypass the base+pattern compositing entirely. Each monolithic has its own dedicated generator function that directly produces all four spec channels. Examples:

### Chameleon v2
- Sine-wave hue shift across the surface
- Creates color-shift effect when viewed from different angles
- Generates both spec map AND modified paint pixels

### Color-Shift v3
- Pixel-dithered Fresnel simulation
- More complex than Chameleon — uses view-angle approximation

### PRIZM v4
- Panel-aware multi-stop color ramps
- Uses the zone mask to create panel-specific color gradients
- Most complex color-shift system

### Other Monolithics
- Glitch — Digital distortion artifacts
- Aurora — Northern lights flowing effect
- Thermochromic — Heat-map style color variation
- Holographic — Rainbow diffraction simulation
- And ~150 more

## Pattern Stack (Up to 3 Layers)

Each zone supports a stack of up to 3 pattern layers:

```javascript
zone.patternStack = [
  { id: "carbon_fiber", opacity: 1.0, scale: 1.0, rotation: 0 },
  { id: "hex_mesh", opacity: 0.5, scale: 2.0, rotation: 45 },
  { id: "scratches", opacity: 0.3, scale: 1.0, rotation: 0 }
];
```

Layers composite top-down with opacity blending. This allows complex multi-texture effects.

## Intensity System

Controls how aggressively finishes affect the spec map:

| Preset | spec_mult | paint_mult | bright_mult |
|--------|-----------|------------|-------------|
| Subtle | 0.5 | 0.3 | 0.2 |
| Medium | 1.0 | 0.6 | 0.5 |
| Aggressive | 1.5 | 1.0 | 0.8 |
| Extreme | 2.0 | 1.5 | 1.2 |

- `spec_mult` — Amplifies spec map channel values
- `paint_mult` — Controls paint color modification strength
- `bright_mult` — Controls brightness/luminance shifts

Users can also set custom values via sliders (each 0.0–2.0).

## Wear System

Simulates racing wear on the spec map:

- Wear slider: 0 (pristine) → 100 (destroyed)
- Adds roughness variation (scratches, chips, scuffs)
- Reduces clearcoat in wear zones
- Can generate progressive wear for "season mode" (multiple renders at increasing wear levels)
- Wear is zone-aware — affects only the zones it's applied to

## Spec Map Import & Merge

Feature #2 allows importing an existing spec map TGA and merging it with generated specs:

- Load external spec map via file browse
- Merge modes: blend, overlay, replace per-channel
- Useful for preserving hand-painted spec details while adding finish effects
- Channel visualizer shows individual M/R/CC/A channels as grayscale previews

## Zone Mask Building

`build_zone_mask()` determines which pixels belong to each zone:

```python
def build_zone_mask(scheme, stats, selector, blur_radius=3):
```

**Selector Types:**
- **Color name** (e.g., "red", "blue") — Hue range matching
- **Hex value** (e.g., "#FF0000") — Exact RGB matching with tolerance
- **"everything"** — All pixels
- **"remaining"** — Pixels not claimed by any other zone
- **Brightness/saturation ranges** — "dark", "light", "saturated"
- **Multi-color** — Multiple colors combined into one zone mask

Zone masks are Uint8Array (2048×2048) where 255 = in zone, 0 = not in zone. Gaussian blur smooths edges.

## Region Masks (Canvas Painting)

In addition to automatic color detection, users can hand-paint region masks on the canvas:

- Brush tool: Paint inclusion areas
- Erase tool: Remove from mask
- Rectangle tool: Click-drag rectangular selection
- Wand tool: Flood fill with tolerance
- Gradient tool: Linear gradient mask
- Select All tool: Global color-based selection
- Edge tool: Edge detection fill

Region masks are combined with color-based masks via OR logic — if either says "in zone," the pixel is in the zone.

## Output Pipeline

After render completes:

1. **Spec Map TGA** — 32-bit RGBA, 2048×2048, all zone specs merged
2. **Paint TGA** — Recolored/modified paint file (if recolor rules applied)
3. **Preview PNGs** — Scaled preview images for the UI
4. **Night Spec** — Optional darkened spec variant for night racing
5. **Dual Spec** — Optional secondary spec map variant
6. **ZIP Bundle** — All outputs packaged for download
7. **Deploy** — One-click copy to iRacing's paint folder

## iRacing Integration

- Paint folder auto-detection via standard iRacing paths
- `/iracing-cars` endpoint lists available car folders
- `/deploy-to-iracing` copies output files to the correct car folder
- Proper file naming: `car_XXX.tga` and `car_XXX_spec.tga`
