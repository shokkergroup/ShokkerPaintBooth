"""
Shokker Engine - Superman #51 ARCA Multi-Zone Build
=====================================================
Per user specification:
  ZONE 1 - BASE (dark center + blue areas): FROST BITE finish
  ZONE 2 - NUMBERS (all #51 instances): PRISMATIC finish
  ZONE 3 - DOTS (square halftone dots in blue/dark): HOLOGRAPHIC finish
  ZONE 4 - SPONSORS (logo/text areas): GLOSS finish
  ZONE 5 - YELLOW AREAS (rear quarter, splitter): MATTE finish

This builds ONE combined car_num.tga + ONE combined car_spec.tga
where each zone gets its own unique material properties.
"""

import numpy as np
from PIL import Image, ImageFilter
import struct
import os
import sys

# Import the engine
engine_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, engine_dir)
from shokker_engine import (
    write_tga_24bit, write_tga_32bit,
    multi_scale_noise, fractal_noise, hsv_to_rgb_vec,
    INTENSITY
)


def detect_zones(arr):
    """
    Analyze the Superman #51 paint and create 5 separate masks.
    Returns dict of zone_name -> float32 mask (0.0 to 1.0)
    """
    h, w = arr.shape[:2]
    f = arr.astype(np.float32)

    r, g, b = f[:,:,0], f[:,:,1], f[:,:,2]
    brightness = r * 0.299 + g * 0.587 + b * 0.114

    # ================================================================
    # ZONE 5: YELLOW AREAS
    # Yellow paint: high R, high G, low B
    # ================================================================
    yellow_raw = (r > 150) & (g > 140) & (b < 90)
    # Include the yellow-green splatter/halftone areas too
    yellow_green = (r > 120) & (g > 130) & (b < 70) & (g > r * 0.8)
    yellow_mask = (yellow_raw | yellow_green).astype(np.float32)
    # Smooth edges
    yellow_mask = np.array(Image.fromarray((yellow_mask * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius=2))).astype(np.float32) / 255.0

    # ================================================================
    # ZONE 2: NUMBERS (#51 - gold/yellow with distinct characteristics)
    # The 51 numbers are bright gold/yellow with strong saturation
    # They have high R+G but also some blue highlights
    # Key difference from yellow areas: numbers are within the dark zone,
    # not in the yellow rear quarter
    # ================================================================
    # Gold number pixels: bright yellow-gold, high saturation
    gold = (r > 180) & (g > 120) & (b < 110) & ((r + g) > 320)
    # Also catch the blue/cyan highlights in the number outlines
    number_blue = (b > 150) & (r < 100) & (g > 80) & (b > g)
    # Combine and look for clusters (numbers are large connected areas)
    number_raw = gold | number_blue

    # The numbers are in the DARK and MID zones, NOT in the yellow rear
    # So mask out yellow areas from number detection
    number_raw = number_raw & (~yellow_raw)

    # Dilate slightly to catch outlines
    number_mask = np.array(Image.fromarray((number_raw.astype(np.uint8) * 255)).filter(
        ImageFilter.MaxFilter(size=5))).astype(np.float32) / 255.0
    # Smooth
    number_mask = np.array(Image.fromarray((number_mask * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius=3))).astype(np.float32) / 255.0

    # ================================================================
    # ZONE 3: DOTS (halftone square grid pattern)
    # The dots are ~8-12px lighter squares on dark/blue background
    # They're brighter than surrounding but not as bright as numbers
    # Found in both the dark center and blue side areas
    # ================================================================
    # Detect dots by looking for local brightness peaks in a grid pattern
    # In the dark areas: dots are medium brightness (50-150 avg) vs dark base (<50)
    # In the blue areas: dots are lighter cyan vs standard blue

    # Method: compare each pixel's brightness to its local neighborhood
    # Dots will be locally brighter than their immediate surroundings
    blur_big = np.array(Image.fromarray(brightness.astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius=12))).astype(np.float32)
    blur_small = np.array(Image.fromarray(brightness.astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius=2))).astype(np.float32)

    # Local contrast = how much brighter this pixel is vs local average
    local_contrast = blur_small - blur_big

    # Dots are pixels that are locally brighter by at least some threshold
    # But NOT part of numbers, yellow, or sponsor areas
    dot_candidates = (local_contrast > 8) & (~yellow_raw) & (~gold) & (~number_blue)

    # Also specifically look for the cyan/light squares in blue areas
    cyan_dots = (g > 140) & (b > 180) & (r < 80) & (b > r + 80)
    # And lighter squares in dark areas
    dark_area_dots = (brightness > 45) & (brightness < 130) & (r < 100) & (g < 120) & (b < 120)
    dark_area_dots = dark_area_dots & (blur_big < 80)  # Only in dark regions

    dot_raw = dot_candidates | cyan_dots | dark_area_dots
    dot_raw = dot_raw & (~yellow_raw) & (~gold)

    dot_mask = dot_raw.astype(np.float32)
    # Very slight smooth - keep dots sharp
    dot_mask = np.array(Image.fromarray((dot_mask * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius=1))).astype(np.float32) / 255.0

    # ================================================================
    # ZONE 4: SPONSORS (logos, text, decals)
    # These are the small bright detailed areas that aren't numbers or yellow
    # Sponsors: General Tire, TowCall, Vanquish, VRN, Shokker, Menards, etc.
    # They tend to be small, high-detail, multi-colored
    # ================================================================
    # Sponsors are bright-ish pixels that aren't yellow, numbers, or dots
    # They're scattered small areas with high local detail
    # For now, detect as: medium-high brightness, not yellow, not gold, not blue-dominant
    sponsor_candidates = (brightness > 100) & (~yellow_raw) & (~gold) & (~number_blue)
    sponsor_candidates = sponsor_candidates & (~cyan_dots)

    # Sponsors are typically smaller clusters - they're the "everything else that's bright"
    # In the Superman/art areas, we want those to be base, not sponsor
    # Superman art is larger connected regions with flesh tones + cyan + red
    flesh_tone = (r > 150) & (g > 80) & (g < 160) & (b < 100)  # Superman skin
    superman_art = flesh_tone | ((r > 180) & (g < 60) & (b < 60))  # Red cape/eyes
    superman_art = superman_art | ((r < 50) & (g > 130) & (b > 150))  # Cyan Superman

    sponsor_raw = sponsor_candidates & (~superman_art)

    # Known sponsor regions (approximate pixel boxes on the UV)
    # These help catch sponsors that color detection might miss
    sponsor_boxes = [
        # (y1, y2, x1, x2) - known sponsor cluster areas
        (0, 260, 0, 2048),      # Top row - bumpers/headlights (fixed elements)
        (1700, 2048, 0, 2048),  # Bottom row - underbody/misc
    ]

    sponsor_mask = sponsor_raw.astype(np.float32)
    # Remove from other zones
    sponsor_mask = sponsor_mask * (1 - number_mask) * (1 - yellow_mask)
    sponsor_mask = np.array(Image.fromarray((sponsor_mask * 255).clip(0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius=1))).astype(np.float32) / 255.0

    # ================================================================
    # ZONE 1: BASE (everything else - dark center + blue areas)
    # This is whatever isn't claimed by other zones
    # ================================================================
    claimed = np.clip(yellow_mask + number_mask + dot_mask + sponsor_mask, 0, 1)
    base_mask = np.clip(1.0 - claimed, 0, 1)
    # Only where there's actual car paint (not transparent/dead areas)
    has_paint = brightness > 5
    base_mask = base_mask * has_paint.astype(np.float32)

    return {
        "base": base_mask,
        "numbers": number_mask,
        "dots": dot_mask,
        "sponsors": sponsor_mask,
        "yellow": yellow_mask,
    }


def build_multizone_spec(shape, zones, seed=51):
    """
    Build a COMBINED spec map where each zone gets different material properties.

    ZONE FINISHES:
    - base: FROST BITE (high metallic, high roughness = matte metallic ice)
    - numbers: PRISMATIC (very high metallic, low roughness, multi-scale flake)
    - dots: HOLOGRAPHIC (max metallic, very low roughness, fine flake)
    - sponsors: GLOSS (no metallic, smooth, clearcoat)
    - yellow: MATTE (no metallic, high roughness, no clearcoat)
    """
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.float32)

    # Start with a neutral default
    spec[:,:,0] = 40   # Low metallic
    spec[:,:,1] = 80   # Medium roughness
    spec[:,:,2] = 16   # Clearcoat
    spec[:,:,3] = 255  # Full spec

    # --- ZONE 1: BASE = FROST BITE ---
    # High metallic with crystalline grain, medium-high roughness, no clearcoat
    base = zones["base"]
    mn_base = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+100)
    rn_base = multi_scale_noise(shape, [2, 6, 10], [0.3, 0.4, 0.3], seed+200)

    spec[:,:,0] += (225 * base + mn_base * 35 * base)   # High metallic with grain
    spec[:,:,1] += (90 * base + rn_base * 40 * base)    # Medium-high roughness (frosted)
    spec[:,:,2] = np.where(base > 0.5, 0, spec[:,:,2])  # No clearcoat on frost

    # --- ZONE 2: NUMBERS = PRISMATIC ---
    # Very high metallic, low roughness (mirror-like), multi-scale flake noise
    nums = zones["numbers"]
    mn_nums = multi_scale_noise(shape, [1, 2, 4, 6], [0.2, 0.3, 0.3, 0.2], seed+300)
    rn_nums = multi_scale_noise(shape, [1, 3], [0.5, 0.5], seed+400)

    spec[:,:,0] += (250 * nums + mn_nums * 45 * nums)   # Max metallic with flake
    spec[:,:,1] += (-40 * nums + rn_nums * 25 * nums)   # Low roughness (shiny)
    spec[:,:,2] = np.where(nums > 0.5, 16, spec[:,:,2]) # Clearcoat ON

    # --- ZONE 3: DOTS = HOLOGRAPHIC ---
    # Max metallic, very smooth, fine multi-scale flake
    dots = zones["dots"]
    mn_dots = multi_scale_noise(shape, [1, 2, 3, 5], [0.3, 0.3, 0.2, 0.2], seed+500)
    rn_dots = multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed+600)

    spec[:,:,0] += (250 * dots + mn_dots * 40 * dots)   # Max metallic
    spec[:,:,1] += (-60 * dots + rn_dots * 20 * dots)   # Very smooth
    spec[:,:,2] = np.where(dots > 0.5, 16, spec[:,:,2]) # Clearcoat ON

    # --- ZONE 4: SPONSORS = GLOSS ---
    # No metallic, smooth, clearcoat
    spon = zones["sponsors"]
    spec[:,:,0] += (-30 * spon)     # Remove any metallic
    spec[:,:,1] += (-50 * spon)     # Smooth
    spec[:,:,2] = np.where(spon > 0.5, 16, spec[:,:,2])

    # --- ZONE 5: YELLOW = MATTE ---
    # No metallic, high roughness, no clearcoat
    yel = zones["yellow"]
    spec[:,:,0] += (-30 * yel)      # Remove metallic
    spec[:,:,1] += (120 * yel)      # Very rough (matte)
    spec[:,:,2] = np.where(yel > 0.5, 0, spec[:,:,2])  # No clearcoat

    # Clip everything to valid range
    spec_uint8 = np.clip(spec, 0, 255).astype(np.uint8)
    return spec_uint8


def build_multizone_paint(scheme, shape, zones, seed=51):
    """
    Apply MINIMAL paint modifications per zone.
    Most zones get NO paint change - spec does the work.
    Only prismatic numbers and holographic dots get subtle flake noise.
    """
    paint = scheme.copy()
    h, w = shape

    # --- NUMBERS: Subtle per-channel flake for prismatic shimmer ---
    nums = zones["numbers"]
    for c in range(3):
        flake = multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed + c * 17 + 300)
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.04 * nums, 0, 1)
    # Slight brightness boost for metallic rendering
    paint = np.clip(paint + 0.03 * nums[:,:,np.newaxis], 0, 1)

    # --- DOTS: Very subtle brightness flake for holographic ---
    dots = zones["dots"]
    dot_flake = multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed + 500)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + dot_flake * 0.02 * dots, 0, 1)

    # --- BASE: Tiny crystalline grain for frost bite ---
    base = zones["base"]
    grain = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 100)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + grain * 0.015 * base, 0, 1)
    # Slight brightness for frost metallic
    paint = np.clip(paint + 0.02 * base[:,:,np.newaxis], 0, 1)

    # --- YELLOW: Slight desaturation for matte look ---
    yel = zones["yellow"]
    gray = paint[:,:,0]*0.299 + paint[:,:,1]*0.587 + paint[:,:,2]*0.114
    for c in range(3):
        diff = paint[:,:,c] - gray
        paint[:,:,c] = np.clip(paint[:,:,c] - diff * 0.08 * yel, 0, 1)

    # --- SPONSORS: No modification at all ---
    # (gloss = spec only, paint stays exactly as-is)

    return paint


def main():
    base_dir = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing"
    scheme_path = os.path.join(base_dir, "BryantSuperman51 TGA.tga")
    output_dir = os.path.join(base_dir, "output", "superman51_multizone")
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("  SHOKKER ENGINE - MULTI-ZONE BUILD")
    print("  Superman #51 ARCA - 5 Zone Composite")
    print("=" * 70)
    print()
    print("  ZONE 1 - Base (dark+blue):  FROST BITE")
    print("  ZONE 2 - Numbers (#51):     PRISMATIC")
    print("  ZONE 3 - Dots (halftone):   HOLOGRAPHIC")
    print("  ZONE 4 - Sponsors/logos:    GLOSS")
    print("  ZONE 5 - Yellow areas:      MATTE")
    print()

    # Load scheme
    print("  [1/5] Loading paint file...")
    scheme_img = Image.open(scheme_path).convert('RGB')
    scheme = np.array(scheme_img).astype(np.float32) / 255.0
    h, w = scheme.shape[:2]
    shape = (h, w)
    print(f"         {w}x{h}")

    # Detect zones
    print("  [2/5] Detecting zones...")
    zones = detect_zones(np.array(scheme_img))

    for name, mask in zones.items():
        coverage = mask.mean() * 100
        print(f"         {name:12s}: {coverage:.1f}% of car")

    # Save zone visualization
    viz = np.zeros((h, w, 3), dtype=np.uint8)
    viz[:,:,0] = np.clip(zones["numbers"] * 255, 0, 255).astype(np.uint8)  # Red = numbers
    viz[:,:,1] = np.clip(zones["dots"] * 200 + zones["yellow"] * 180, 0, 255).astype(np.uint8)  # Green = dots + yellow
    viz[:,:,2] = np.clip(zones["base"] * 150 + zones["sponsors"] * 255, 0, 255).astype(np.uint8)  # Blue = base + sponsors
    Image.fromarray(viz).save(os.path.join(output_dir, "PREVIEW_zones.png"))
    print("         >> PREVIEW_zones.png")

    # Save individual zone masks
    for name, mask in zones.items():
        mask_path = os.path.join(output_dir, f"MASK_{name}.png")
        Image.fromarray((mask * 255).clip(0, 255).astype(np.uint8)).save(mask_path)
    print("         >> Individual masks saved")

    # Build combined spec map
    print("  [3/5] Building multi-zone spec map...")
    spec = build_multizone_spec(shape, zones, seed=51)
    print("         Frost base + Prismatic numbers + Holo dots + Gloss sponsors + Matte yellow")

    # Build paint (minimal modifications)
    print("  [4/5] Applying subtle paint adjustments...")
    paint = build_multizone_paint(scheme, shape, zones, seed=51)
    paint_rgb = (np.clip(paint, 0, 1) * 255).astype(np.uint8)

    # Save everything
    print("  [5/5] Saving output files...")
    iracing_id = "23371"

    write_tga_24bit(os.path.join(output_dir, f"car_num_{iracing_id}.tga"), paint_rgb)
    write_tga_32bit(os.path.join(output_dir, f"car_spec_{iracing_id}.tga"), spec)

    Image.fromarray(paint_rgb).save(os.path.join(output_dir, "PREVIEW_paint.png"))
    Image.fromarray(spec).save(os.path.join(output_dir, "PREVIEW_spec.png"))

    # Save a comparison: original vs modified
    orig_rgb = (scheme * 255).astype(np.uint8)
    diff = np.abs(paint_rgb.astype(int) - orig_rgb.astype(int)).astype(np.uint8)
    diff_enhanced = np.clip(diff * 5, 0, 255).astype(np.uint8)  # Enhance to see subtle changes
    Image.fromarray(diff_enhanced).save(os.path.join(output_dir, "PREVIEW_paint_diff_5x.png"))

    print(f"\n{'=' * 70}")
    print(f"  MULTI-ZONE BUILD COMPLETE!")
    print(f"{'=' * 70}")
    print(f"\n  Output: {os.path.abspath(output_dir)}")
    print(f"\n  Files:")
    print(f"    car_num_{iracing_id}.tga  - Paint (your scheme, barely modified)")
    print(f"    car_spec_{iracing_id}.tga - Multi-zone spec map")
    print(f"    PREVIEW_paint.png        - Paint preview")
    print(f"    PREVIEW_spec.png         - Spec map preview")
    print(f"    PREVIEW_zones.png        - Zone detection visualization")
    print(f"    PREVIEW_paint_diff_5x    - Shows paint changes (5x enhanced)")
    print(f"    MASK_*.png               - Individual zone masks")
    print(f"\n  Zone Legend:")
    print(f"    Base (dark+blue) = Frost Bite: matte metallic ice")
    print(f"    Numbers (#51)   = Prismatic: rainbow mirror flake")
    print(f"    Dots (halftone) = Holographic: max metallic shimmer")
    print(f"    Sponsors/logos  = Gloss: clean standard finish")
    print(f"    Yellow areas    = Matte: flat dead finish")


if __name__ == '__main__':
    main()
