"""
SHOKKER PAINT BOOTH - Auto-Generated Build Script
Car: Superman #51 ARCA | iRacing ID: 23371
Zones: Base=holographic_flake, Numbers=carbon_fiber, Sponsors=gloss
"""
import numpy as np
from PIL import Image, ImageFilter
import struct
import os
import time

# ================================================================
# CONFIG
# ================================================================
PAINT_FILE = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\Driver Paints\Dillon Bryant\db51sm_tga.tga"
OUTPUT_DIR = r"E:\Claude Code Assistant\12-iRacing Misc\Shokker iRacing\Driver Paints\Dillon Bryant"
IRACING_ID = "23371"
SEED = 51

ZONES = [
    {"name": "Base / Body", "desc": "Main body panels and base color areas", "finish": "holographic_flake", "intensity": "aggressive"},
    {"name": "Numbers", "desc": "Door numbers, roof number", "finish": "carbon_fiber", "intensity": "aggressive"},
    {"name": "Sponsors / Logos", "desc": "Sponsor decals and logo areas", "finish": "gloss", "intensity": "aggressive"},
]

# ================================================================
# TGA WRITERS
# ================================================================
def write_tga_32bit(filepath, rgba_array):
    h, w = rgba_array.shape[:2]
    with open(filepath, 'wb') as f:
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 2))
        f.write(struct.pack('<5B', 0, 0, 0, 0, 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', w))
        f.write(struct.pack('<H', h))
        f.write(struct.pack('<B', 32))
        f.write(struct.pack('<B', 0x28))
        bgra = np.stack([rgba_array[:,:,2], rgba_array[:,:,1],
                         rgba_array[:,:,0], rgba_array[:,:,3]], axis=-1)
        f.write(bgra.tobytes())

def write_tga_24bit(filepath, rgb_array):
    h, w = rgb_array.shape[:2]
    with open(filepath, 'wb') as f:
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<B', 2))
        f.write(struct.pack('<5B', 0, 0, 0, 0, 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', w))
        f.write(struct.pack('<H', h))
        f.write(struct.pack('<B', 24))
        f.write(struct.pack('<B', 0x20))
        bgr = np.stack([rgb_array[:,:,2], rgb_array[:,:,1], rgb_array[:,:,0]], axis=-1)
        f.write(bgr.tobytes())

# ================================================================
# NOISE GENERATORS
# ================================================================
def generate_perlin_noise_2d(shape, res, seed=None):
    if seed is not None:
        np.random.seed(seed)
    def f(t):
        return 6*t**5 - 15*t**4 + 10*t**3
    delta = (res[0]/shape[0], res[1]/shape[1])
    d = (shape[0]//res[0], shape[1]//res[1])
    grid = np.mgrid[0:res[0]:delta[0], 0:res[1]:delta[1]].transpose(1,2,0) % 1
    angles = 2*np.pi*np.random.rand(res[0]+1, res[1]+1)
    gradients = np.dstack((np.cos(angles), np.sin(angles)))
    g00 = gradients[:-1,:-1].repeat(d[0],0).repeat(d[1],1)
    g10 = gradients[1:,:-1].repeat(d[0],0).repeat(d[1],1)
    g01 = gradients[:-1,1:].repeat(d[0],0).repeat(d[1],1)
    g11 = gradients[1:,1:].repeat(d[0],0).repeat(d[1],1)
    n00 = np.sum(np.dstack((grid[:,:,0], grid[:,:,1]))*g00, 2)
    n10 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]))*g10, 2)
    n01 = np.sum(np.dstack((grid[:,:,0], grid[:,:,1]-1))*g01, 2)
    n11 = np.sum(np.dstack((grid[:,:,0]-1, grid[:,:,1]-1))*g11, 2)
    t = f(grid)
    n0 = n00*(1-t[:,:,0]) + t[:,:,0]*n10
    n1 = n01*(1-t[:,:,0]) + t[:,:,0]*n11
    return np.sqrt(2)*((1-t[:,:,1])*n0 + t[:,:,1]*n1)

def multi_scale_noise(shape, scales, weights, seed=42):
    h, w = shape
    combined = np.zeros((h, w))
    total_weight = sum(weights)
    for scale, weight in zip(scales, weights):
        np.random.seed(seed + scale * 7)
        if scale == 1:
            noise = np.random.randn(h, w)
        else:
            small_h = max(1, h // scale)
            small_w = max(1, w // scale)
            small_noise = np.random.randn(small_h, small_w)
            noise_img = Image.fromarray(
                ((small_noise + 3) / 6 * 255).clip(0, 255).astype(np.uint8)
            )
            noise_img = noise_img.resize((w, h), Image.NEAREST)
            noise = np.array(noise_img).astype(np.float32) / 255.0 * 2 - 1
        combined += noise * weight
    return combined / total_weight

# ================================================================
# INTENSITY PRESETS
# ================================================================
INTENSITY = {
    "subtle":     {"paint": 0.3,  "spec": 0.6,  "bright": 0.02},
    "medium":     {"paint": 0.6,  "spec": 1.0,  "bright": 0.04},
    "aggressive": {"paint": 1.0,  "spec": 1.5,  "bright": 0.06},
    "extreme":    {"paint": 1.5,  "spec": 2.0,  "bright": 0.10},
}

# ================================================================
# SPEC MAP GENERATORS
# ================================================================
def spec_gloss(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(5 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(25 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_holographic_flake(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mf = multi_scale_noise(shape, [1, 2, 4, 6], [0.2, 0.3, 0.3, 0.2], seed+100)
    rf = multi_scale_noise(shape, [1, 3], [0.5, 0.5], seed+200)
    spec[:,:,0] = np.clip(245 * mask + 5 * (1-mask) + mf * 45 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(10 * mask + 100 * (1-mask) + rf * 30 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_carbon_fiber(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    weave_size = 6
    cf = (((x // weave_size + y // weave_size) % 2).astype(np.float32) * 0.6 +
          ((np.sin(x * np.pi / weave_size) * np.sin(y * np.pi / weave_size) + 1) / 2) * 0.4)
    spec[:,:,0] = np.clip(50 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(45 * mask + 100 * (1-mask) + cf * 35 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

# ================================================================
# PAINT MODIFIERS
# ================================================================
def paint_none(paint, shape, mask, seed, pm, bb):
    return paint

def paint_coarse_flake(paint, shape, mask, seed, pm, bb):
    r_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+11)
    g_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+22)
    b_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+33)
    strength = 0.06 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + r_flake * strength * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + g_flake * strength * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + b_flake * strength * mask, 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_carbon_darken(paint, shape, mask, seed, pm, bb):
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    weave_size = 6
    cf = (((x // weave_size + y // weave_size) % 2).astype(np.float32) * 0.6 +
          ((np.sin(x * np.pi / weave_size) * np.sin(y * np.pi / weave_size) + 1) / 2) * 0.4)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - cf * 0.08 * pm * mask, 0, 1)
    return paint

# ================================================================
# FINISH REGISTRY (only finishes used in this build)
# ================================================================
FINISH_REGISTRY = {
    "gloss":              (spec_gloss,             paint_none),
    "holographic_flake":  (spec_holographic_flake, paint_coarse_flake),
    "carbon_fiber":       (spec_carbon_fiber,      paint_carbon_darken),
}

# ================================================================
# MASK
# ================================================================
def compute_mask(scheme, threshold=0.40, softness=0.15):
    brightness = scheme[:,:,0]*0.299 + scheme[:,:,1]*0.587 + scheme[:,:,2]*0.114
    low = threshold - softness/2
    high = threshold + softness/2
    mask = np.clip((high - brightness) / (high - low + 1e-10), 0, 1)
    mask_img = Image.fromarray((mask*255).astype(np.uint8))
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=2))
    return np.array(mask_img).astype(np.float32) / 255.0

# ================================================================
# MAIN
# ================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  SHOKKER PAINT BOOTH - Multi-Zone Build")
    print(f"  Car: Superman #51 ARCA")
    print(f"  Zones: {len(ZONES)}")
    print("=" * 60)

    start_time = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n  Loading paint: {PAINT_FILE}")
    scheme_img = Image.open(PAINT_FILE).convert('RGB')
    scheme = np.array(scheme_img).astype(np.float32) / 255.0
    h, w = scheme.shape[:2]
    shape = (h, w)
    print(f"  Resolution: {w}x{h}")

    mask = compute_mask(scheme)

    # Initialize combined spec and paint
    combined_spec = np.zeros((h, w, 4), dtype=np.uint8)
    combined_spec[:,:,0] = 5
    combined_spec[:,:,1] = 100
    combined_spec[:,:,2] = 16
    combined_spec[:,:,3] = 255
    paint = scheme.copy()

    for zone in ZONES:
        name = zone["name"]
        finish_name = zone["finish"]
        intensity = zone["intensity"]

        if finish_name not in FINISH_REGISTRY:
            print(f"  WARNING: Unknown finish '{finish_name}', skipping")
            continue

        preset = INTENSITY[intensity]
        pm = preset["paint"]
        sm = preset["spec"]
        bb = preset["bright"]

        spec_fn, paint_fn = FINISH_REGISTRY[finish_name]
        print(f"  [{name}] => {finish_name} ({intensity})")

        zone_spec = spec_fn(shape, mask, SEED, sm)
        paint = paint_fn(paint, shape, mask, SEED, pm, bb)

        for c in range(4):
            combined_spec[:,:,c] = np.where(
                mask > 0.1,
                zone_spec[:,:,c],
                combined_spec[:,:,c]
            ).astype(np.uint8)

    paint_rgb = (np.clip(paint, 0, 1) * 255).astype(np.uint8)

    paint_path = os.path.join(OUTPUT_DIR, f"car_{IRACING_ID}.tga")
    spec_path = os.path.join(OUTPUT_DIR, f"car_spec_{IRACING_ID}.tga")

    write_tga_24bit(paint_path, paint_rgb)
    write_tga_32bit(spec_path, combined_spec)

    Image.fromarray(paint_rgb).save(os.path.join(OUTPUT_DIR, "PREVIEW_paint.png"))
    Image.fromarray(combined_spec).save(os.path.join(OUTPUT_DIR, "PREVIEW_spec.png"))
    Image.fromarray((mask * 255).astype(np.uint8)).save(os.path.join(OUTPUT_DIR, "PREVIEW_mask.png"))

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  DONE in {elapsed:.1f}s!")
    print(f"  Paint: {paint_path}")
    print(f"  Spec:  {spec_path}")
    print(f"{'=' * 60}")
