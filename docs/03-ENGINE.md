# Shokker Paint Booth — Engine Reference (shokker_engine_v2.py)

## Overview

The engine is a ~7,015 line Python module that handles all pixel-level operations: finish generation, spec map compositing, zone mask building, paint recoloring, wear simulation, and TGA I/O. It contains no HTTP logic — that's the server's job.

## Registries

### BASE_REGISTRY (155 entries)
Each base defines a surface material with default spec values:

```python
BASE_REGISTRY = {
    "gloss": {
        "name": "Gloss",
        "metallic": 5,
        "roughness": 40,
        "clearcoat": 16,
        "authority": 255,
        "generator": gen_gloss  # Function that produces the base texture
    },
    "matte": { ... },
    "chrome": { ... },
    # ... 152 more
}
```

**Base Categories (from BASE_GROUPS in HTML):**
- Classic (gloss, matte, satin, semi_gloss, eggshell)
- Metallic (chrome, brushed_aluminum, copper, gold, bronze, titanium, etc.)
- Candy (candy_red, candy_blue, candy_green, candy_purple, etc.)
- Pearl (pearl_white, pearl_blue, pearl_pink, etc.)
- Carbon & Fiber (carbon_fiber, kevlar, fiberglass, etc.)
- Exotic (ceramic, liquid_metal, mirror, blackout, etc.)
- Weathered (rust, patina, battle_worn, sand_blasted, etc.)
- Frozen (frozen_glass, ice_crystal, frost, etc.)

### PATTERN_REGISTRY (155 entries)
Each pattern defines a texture overlay:

```python
PATTERN_REGISTRY = {
    "carbon_fiber": {
        "name": "Carbon Fiber",
        "generator": gen_carbon_fiber  # Returns a 2D intensity array
    },
    "hex_mesh": { ... },
    # ... 153 more
}
```

**Pattern Categories (from PATTERN_GROUPS in HTML):**
- Weaves (carbon_fiber, kevlar_weave, basket_weave, twill, etc.)
- Geometric (hex_mesh, diamond_plate, chevron, triangle_grid, etc.)
- Organic (scales, wood_grain, leather, bark, etc.)
- Racing (checkered, racing_stripe, number_plate, etc.)
- Military (camo_woodland, camo_digital, camo_desert, etc.)
- Artistic (skull, celtic_knot, tribal, paisley, etc.)
- Tech (circuit_board, binary_code, pixel, glitch, etc.)
- Weathering (scratches, chips, rust_spots, dirt, etc.)

### MONOLITHIC_REGISTRY (155+ entries)
Each monolithic is a self-contained finish with its own generator:

```python
MONOLITHIC_REGISTRY = {
    "chameleon_v2": {
        "name": "Chameleon v2",
        "generator": gen_chameleon_v2  # Produces BOTH spec AND paint modifications
    },
    # ... 154 more
}
```

**Monolithic Categories (from SPECIAL_GROUPS in HTML):**
- Color-Shift (chameleon variants, color_shift, prizm, etc.)
- Holographic (holographic, diffraction, rainbow, etc.)
- Animated/Dynamic (thermochromic, hydrochromic, etc.)
- Glitch (glitch, pixel_sort, data_corrupt, etc.)
- Natural (aurora, nebula, galaxy, lava, etc.)
- Exotic (quantum, plasma, void, antimatter, etc.)

### FINISH_REGISTRY (25 legacy entries)
Pre-dates the base/pattern split. Each entry is a direct function call:

```python
FINISH_REGISTRY = {
    "chrome": gen_chrome_legacy,
    "matte_black": gen_matte_black_legacy,
    # ... 23 more
}
```

These still work but new finishes use the base+pattern or monolithic system.

## Core Functions

### compose_finish()
```python
def compose_finish(base_id, pattern_id, shape, mask, seed, sm,
                   scale=1.0, spec_mult=1.0, rotation=0):
    """
    Combines a base material with a pattern texture.
    
    Returns: numpy array of shape (H, W, 4) — R=M, G=R, B=CC, A=Auth
    """
```

Process:
1. Get base spec values (M, R, CC, A) from BASE_REGISTRY
2. Generate pattern texture via PATTERN_REGISTRY generator
3. Apply scale and rotation to pattern
4. Modulate: base values × pattern intensity
5. Apply spec_mult for intensity control
6. Clamp all values to 0–255
7. Return composited spec array

### full_render_pipeline()
```python
def full_render_pipeline(car_paint_file, output_dir, zones, iracing_id, seed,
                         wear=0, import_spec_map=None, export_zip=False,
                         dual_spec=False, helmet_file=None, suit_file=None,
                         recolor_rules=None, recolor_mask=None):
    """
    The big one. Takes zone configs and produces all output files.
    
    Returns: dict with paths to all generated files
    """
```

Steps:
1. Load car paint TGA (2048×2048 RGBA)
2. Load import spec map if provided
3. For each zone:
   a. Build zone mask (color detection + region mask)
   b. Determine dispatch path (composited, monolithic, or legacy)
   c. Generate spec map for zone
   d. Handle pattern stack (multiple layers with opacity)
   e. Apply intensity multipliers
4. Merge all zone specs (later zones override earlier ones in overlapping areas)
5. Apply wear if wear > 0
6. Apply recolor rules if provided
7. Write output files:
   - `{iracing_id}.tga` — spec map
   - `{iracing_id}_paint.tga` — modified paint (if recolored)
   - Preview PNGs
   - Night spec variant (optional)
   - ZIP bundle (optional)

### preview_render()
```python
def preview_render(paint_file, zones, seed, preview_scale=0.25,
                   import_spec_map=None):
    """
    Lightweight render for live preview. Same logic, lower resolution.
    """
```

### build_zone_mask()
```python
def build_zone_mask(scheme, stats, selector, blur_radius=3):
    """
    Builds a pixel mask for a zone based on color/region selection.
    
    selector types: color name, hex value, "everything", "remaining",
                    brightness/saturation keywords, multi-color array
    
    Returns: numpy array (H, W) of uint8, 255=in zone, 0=out
    """
```

### apply_paint_recolor()
```python
def apply_paint_recolor(paint_pixels, rules, mask=None):
    """
    HSV-based hue shifting for paint recoloring.
    
    rules: list of {source_hex, target_hex, tolerance}
    mask: optional spatial mask (Uint8Array)
    
    For each pixel, if it's within tolerance of source color,
    shift its hue/sat/val toward target color.
    """
```

## Noise Functions

The engine includes several noise generators used by pattern and monolithic generators:

- **Simplex noise** — Smooth organic patterns
- **Perlin noise** — Classic gradient noise
- **Worley/Voronoi noise** — Cell-based patterns
- **FBM (Fractal Brownian Motion)** — Multi-octave noise layering
- **Seeded RNG** — Reproducible random values from seed parameter

## TGA I/O

Custom TGA reader/writer for iRacing's 32-bit format:

```python
def read_tga(path):
    """Reads 32-bit RGBA TGA. Returns (width, height, pixels_array)"""

def write_tga(path, width, height, pixels):
    """Writes 32-bit RGBA TGA from pixel array"""
```

Key details:
- iRacing expects bottom-up row order (TGA standard)
- 32-bit = 4 bytes per pixel (R, G, B, A)
- No RLE compression (uncompressed type 2)
- Always 2048×2048 for car paints

## Color-Shift Systems (Deep Dive)

### Chameleon v2
- Uses sine wave modulation across the surface
- Hue shifts based on pixel position (simulating view angle)
- Modifies BOTH spec map AND paint pixels
- Parameters: base_hue, shift_range, frequency

### Color-Shift v3
- Pixel-level dithering to simulate Fresnel effect
- More granular than Chameleon — individual pixel decisions
- Uses a view-angle approximation based on surface normal estimation
- Creates more realistic color-shift than sine wave approach

### PRIZM v4
- Panel-aware: uses zone mask boundaries to create per-panel gradients
- Multi-stop color ramps (not just two-color shifts)
- Most complex and realistic color-shift system
- Parameters: color_stops[], ramp_mode, panel_blend

## Wear System Details

```python
def apply_wear(spec_map, wear_level, seed):
    """
    wear_level: 0-100
    
    Effects by level:
    0-20: Minor scuffs, slight roughness increase
    20-50: Visible scratches, some clearcoat damage
    50-80: Heavy wear, chips, clearcoat failure zones
    80-100: Destroyed, major material degradation
    """
```

Wear modifies:
- Roughness (increases in wear zones)
- Clearcoat (degrades, can go below threshold 16→off)
- Metallic (exposes in scratch zones)
- Uses noise-based wear pattern for organic look

## Swatch Generation

The engine can generate small preview swatches for the finish browser:

```python
def generate_swatch(base_id, pattern_id=None, size=64):
    """Generates a small preview image of a finish combination"""
```

Used by the `/swatch/<base>/<pattern>` and `/swatch/mono/<id>` server endpoints.
