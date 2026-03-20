"""
engine/spec_paint.py - Standard spec_ and paint_ functions (bases + effects).
Extracted from shokker_engine_v2 for easier editing.
"""
import numpy as np
from PIL import Image, ImageFilter
from engine.core import multi_scale_noise, get_mgrid, hsv_to_rgb_vec
from engine.utils import perlin_multi_octave, generate_perlin_noise_2d


def clamp_cc(cc_array):
    """Clamp clearcoat channel to valid iRacing range [16, 255].
    CC=16 is max clearcoat (glossiest). CC=255 is dead flat.
    Values 0-15 are legacy/undefined — never output them.
    """
    return np.clip(cc_array, 16, 255)


# SPEC MAP GENERATORS (identical to v1 - proven working)
# ================================================================

def spec_gloss(shape, mask, seed, sm):
    """Gloss -- standard clearcoat paint. Dielectric (M=0), very smooth (R=20), full clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(0 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # M=0 dielectric
    spec[:,:,1] = np.clip(20 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=20 smooth
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_matte(shape, mask, seed, sm):
    """Matte -- flat non-reflective paint. No metallic, very rough (R=215), no clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = 0  # M=0 dielectric
    spec[:,:,1] = np.clip(215 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=215 very rough
    spec[:,:,2] = 0; spec[:,:,3] = 255
    return spec

def spec_satin(shape, mask, seed, sm):
    """Satin -- semi-gloss between matte and gloss. No metallic, mid-rough (R=100), partial clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = 0  # M=0 dielectric
    spec[:,:,1] = np.clip(100 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=100 mid
    spec[:,:,2] = 50; spec[:,:,3] = 255  # CC=50 semi-gloss satin (verified: 16=max gloss, 50=satin, 128=matte-ish)
    return spec

def spec_metallic(shape, mask, seed, sm):
    """Metallic -- standard metallic paint with visible micro-flake. M=200, R=50, visible flake texture."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [4, 8, 16], [0.2, 0.4, 0.4], seed+100)  # Visible flake scales
    spec[:,:,0] = np.clip(200 * mask + 5 * (1-mask) + mn * 40 * sm * mask, 0, 255).astype(np.uint8)  # M=200
    spec[:,:,1] = np.clip(50 * mask + 100 * (1-mask) + mn * 18 * sm * mask, 0, 255).astype(np.uint8)  # R=50
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_pearl(shape, mask, seed, sm):
    """Pearlescent -- moderate metallic so paint color shows through with soft iridescent sheen.
    M=100 (moderate, not chrome-like), R=40 (smooth but not mirror), large gentle waves."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    wave = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    # M=100: moderate metallic lets paint color shine through with pearlescent depth
    spec[:,:,0] = np.clip(100 * mask + 5 * (1-mask) + wave * 20 * sm * mask, 0, 255).astype(np.uint8)
    # R=40: smooth but not mirror - soft diffuse glow, not sharp reflection
    spec[:,:,1] = np.clip(40 * mask + 100 * (1-mask) + wave * 12 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_chrome(shape, mask, seed, sm):
    """Chrome -- pure mirror. Max metallic, near-zero roughness, NO clearcoat (raw metal)."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(255 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # M=255 full metal
    spec[:,:,1] = np.clip(2 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=2 mirror smooth
    spec[:,:,2] = 0; spec[:,:,3] = 255  # CC=0 raw chrome, no clearcoat
    return spec

def spec_satin_metal(shape, mask, seed, sm):
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    np.random.seed(seed)
    brush = np.random.randn(1, w) * 0.5
    brush = np.tile(brush, (h, 1))
    brush += np.random.randn(h, w) * 0.2
    spec[:,:,0] = np.clip(235 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(65 * mask + 100 * (1-mask) + brush * 20 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_metal_flake(shape, mask, seed, sm):
    """Metal flake -- heavy metallic with coarse visible flake sparkle. Like classic hot rod paint."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mf = multi_scale_noise(shape, [4, 8, 16, 32], [0.1, 0.2, 0.35, 0.35], seed+100)  # Visible flake
    rf = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+200)
    spec[:,:,0] = np.clip(240 * mask + 5 * (1-mask) + mf * 50 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(12 * mask + 100 * (1-mask) + rf * 40 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_holographic_flake(shape, mask, seed, sm):
    """Holographic flake -- prismatic micro-grid that creates rainbow diffraction.
    Unlike metal_flake (random coarse sparkle), this has fine directional stripe interference.
    The grid creates the holographic 'rainbow shift' effect in-sim."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    # Fine diagonal micro-grid - creates prismatic interference
    grid_size = 8  # Fine grid for holographic shimmer
    diag1 = np.sin((x + y) * np.pi / grid_size) * 0.5 + 0.5
    diag2 = np.sin((x - y) * np.pi / (grid_size * 1.3)) * 0.5 + 0.5
    holo = diag1 * 0.6 + diag2 * 0.4  # Cross-hatch interference
    # Add per-flake sparkle on top of grid
    rng = np.random.RandomState(seed + 100)
    sparkle = rng.random((h, w)).astype(np.float32)
    bright_flakes = (sparkle > (1.0 - 0.03 * sm)).astype(np.float32)
    spec[:,:,0] = np.clip(245 * mask + 5 * (1-mask) + bright_flakes * 10 * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 + holo * 40 * sm) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_stardust(shape, mask, seed, sm):
    """Stardust -- dark mirror base with sparse bright pinpoint stars scattered across surface."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Dark mirror base: medium-high metallic, moderate roughness (so paint color shows)
    spec[:,:,0] = np.clip(160 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(55 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    # Scatter bright star points: ultra-smooth mirror pinpoints that flash in light
    rng = np.random.RandomState(seed + 100)
    star_field = rng.random((h, w)).astype(np.float32)
    # Density: ~2% of pixels become stars (sparse enough to see individual sparkles)
    stars = (star_field > (1.0 - 0.02 * sm)).astype(np.float32)
    # Stars: max metallic, zero roughness = bright pinpoint flashes
    spec[:,:,0] = np.clip(spec[:,:,0].astype(np.float32) + stars * 95 * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.where(stars > 0.5, np.clip(3 * mask + 100 * (1-mask), 0, 255), spec[:,:,1]).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_candy(shape, mask, seed, sm):
    """Candy -- deep transparent gloss like looking through tinted glass at a metallic base.
    M=130 (moderate metallic so color shows through), R=15 (very smooth wet surface), full clearcoat.
    Key: lower metallic than chrome lets the paint color dominate with depth."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(130 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # M=130 lets color show
    spec[:,:,1] = np.clip(15 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=15 wet smooth
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_brushed_titanium(shape, mask, seed, sm):
    """Brushed titanium -- STRONG directional horizontal grain with moderate metallic.
    Unlike satin_metal (subtle brush), this has aggressive visible grain lines."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    rng = np.random.RandomState(seed + 100)
    # Heavy directional grain: each row is a brush stroke, minimal vertical variation
    row_grain = rng.randn(h, 1).astype(np.float32) * 0.8
    row_grain = np.tile(row_grain, (1, w))
    # Add slight per-pixel variation (but keep directional character)
    row_grain += rng.randn(h, w).astype(np.float32) * 0.1
    # Medium metallic (not chrome-mirror, shows as brushed metal)
    spec[:,:,0] = np.clip(180 * mask + 5 * (1-mask) + row_grain * 25 * sm * mask, 0, 255).astype(np.uint8)
    # Roughness dominated by grain direction: visible streaks of smooth/rough
    spec[:,:,1] = np.clip(70 * mask + 100 * (1-mask) + row_grain * 45 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255  # no clearcoat = raw metal look
    return spec

def spec_anodized(shape, mask, seed, sm):
    """Anodized aluminum -- matte metallic with fine industrial grain and NO clearcoat.
    Higher roughness than pearl/metallic, gritty industrial feel. Color pops through the matte."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Visible industrial grain texture
    grain = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+100)
    # Medium metallic: enough to reflect but not mirror-chrome
    spec[:,:,0] = np.clip(170 * mask + 5 * (1-mask) + grain * 20 * sm * mask, 0, 255).astype(np.uint8)
    # HIGH roughness base (80) with grain variation: gritty matte surface
    spec[:,:,1] = np.clip(80 * mask + 100 * (1-mask) + grain * 25 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255  # NO clearcoat = raw anodized look
    return spec

def spec_hex_mesh(shape, mask, seed, sm):
    """Hex mesh -- honeycomb wire grid where wire is matte and hex centers are chrome mirror.
    Like looking through metallic chicken wire. Visible geometric pattern at car scale."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    hex_size = 24  # visible at car scale
    # Hex grid coordinates
    row = y / (hex_size * 0.866)  # sqrt(3)/2 spacing
    col = x / hex_size
    # Offset every other row
    col_shifted = col - 0.5 * (np.floor(row).astype(int) % 2)
    # Distance from nearest hex center
    row_round = np.round(row)
    col_round = np.round(col_shifted)
    cy = row_round * hex_size * 0.866
    cx = (col_round + 0.5 * (row_round.astype(int) % 2)) * hex_size
    dist = np.sqrt((y - cy)**2 + (x - cx)**2)
    # Normalize: 0=center, 1=edge
    norm_dist = np.clip(dist / (hex_size * 0.45), 0, 1)
    # Wire frame: the outer ring of each hex
    wire = (norm_dist > 0.75).astype(np.float32)
    center = 1.0 - wire
    # Wire: matte rough metal. Center: chrome mirror
    spec[:,:,0] = np.clip((255 * center + 100 * wire) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 * center + 160 * wire) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_frozen(shape, mask, seed, sm):
    """Frozen -- icy matte metal. High metallic, high roughness, no clearcoat.
    Frost crystals visible as large-scale noise patches."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)  # Visible frost patches
    spec[:,:,0] = np.clip(225 * mask + 5 * (1-mask) + mn * 30 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(140 * mask + 100 * (1-mask) + mn * 30 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255
    return spec

def spec_carbon_fiber(shape, mask, seed, sm):
    """Carbon fiber 2x2 twill weave - visible crosshatch pattern at car scale.
    Weave threads alternate shiny/matte creating the classic carbon look.
    Metallic ~50 (semi-metallic resin-coated fiber), low roughness on weave peaks."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    # Weave size 24px = visible threads at 2048x2048 car scale
    weave_size = 24
    # 2x2 twill: two threads over, two under - classic carbon weave
    # Diagonal bias creates the characteristic angled crosshatch
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)  # 0-1 per horizontal repeat
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)  # 0-1 per vertical repeat
    # Horizontal tows vs vertical tows - 2x2 twill offset
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5  # horizontal thread shape
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5   # vertical thread shape
    # Twill: which thread is on top alternates in a diagonal pattern
    twill_cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    cf = twill_cell * horiz + (1 - twill_cell) * vert
    # Thread edge definition - sharper transitions between tows
    cf = np.clip(cf * 1.3 - 0.15, 0, 1)
    # Spec channels: fiber peaks are smoother/shinier, valleys are rougher
    spec[:,:,0] = np.clip(55 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # Metallic: semi-metallic
    spec[:,:,1] = np.clip((30 + cf * 50 * sm) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # Roughness: weave varies 30-80
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_ripple(shape, mask, seed, sm):
    """Ripple -- concentric expanding rings like a water drop impact on liquid metal.
    Multiple ring origins create overlapping interference-like patterns. Visible at car scale."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    # Multiple ring origins scattered across the surface
    rng = np.random.RandomState(seed + 100)
    num_origins = int(6 + sm * 4)  # 6-10 ring centers
    ripple_sum = np.zeros((h, w), dtype=np.float32)
    for _ in range(num_origins):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        dist = np.sqrt((y - cy)**2 + (x - cx)**2).astype(np.float32)
        ring_spacing = rng.uniform(20, 40)  # visible ring spacing
        ripple = np.sin(dist / ring_spacing * 2 * np.pi)
        # Fade out with distance from origin
        fade = np.clip(1.0 - dist / (max(h, w) * 0.6), 0, 1)
        ripple_sum += ripple * fade
    # Normalize
    rmax = np.abs(ripple_sum).max() + 1e-8
    ripple_norm = ripple_sum / rmax
    # Ring peaks: chrome mirror smooth. Ring valleys: matte rough
    ring_val = (ripple_norm + 1.0) * 0.5  # 0-1
    spec[:,:,0] = np.clip((240 * ring_val + 140 * (1-ring_val)) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 * ring_val + 90 * (1-ring_val)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_hammered(shape, mask, seed, sm):
    """Hammered metal -- random circular dimple impacts across surface like hand-hammered copper.
    Each dimple is a smooth concave mirror, flat areas between are matte. Visible texture."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Generate random dimple positions
    rng = np.random.RandomState(seed + 100)
    num_dimples = int(400 * sm)
    dimple_y = rng.randint(0, h, num_dimples).astype(np.float32)
    dimple_x = rng.randint(0, w, num_dimples).astype(np.float32)
    dimple_r = rng.randint(8, 22, num_dimples).astype(np.float32)
    # Downsample 4x for speed
    ds = 4
    sh, sw = h // ds, w // ds
    yg, xg = np.mgrid[0:sh, 0:sw]
    yg = (yg * ds).astype(np.float32)
    xg = (xg * ds).astype(np.float32)
    dimple_small = np.zeros((sh, sw), dtype=np.float32)
    for dy, dx, dr in zip(dimple_y, dimple_x, dimple_r):
        # Only compute within bounding box of each dimple (massive speedup)
        y_lo = max(0, int((dy - dr) / ds))
        y_hi = min(sh, int((dy + dr) / ds) + 1)
        x_lo = max(0, int((dx - dr) / ds))
        x_hi = min(sw, int((dx + dr) / ds) + 1)
        if y_hi <= y_lo or x_hi <= x_lo:
            continue
        sub_y = yg[y_lo:y_hi, x_lo:x_hi]
        sub_x = xg[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((sub_y - dy)**2 + (sub_x - dx)**2)
        dimple = np.clip(1.0 - dist / dr, 0, 1) ** 2
        dimple_small[y_lo:y_hi, x_lo:x_hi] = np.maximum(
            dimple_small[y_lo:y_hi, x_lo:x_hi], dimple)
    # Upsample
    dimple_img = Image.fromarray((dimple_small * 255).astype(np.uint8))
    dimple_img = dimple_img.resize((w, h), Image.BILINEAR)
    dimple_map = np.array(dimple_img).astype(np.float32) / 255.0
    # Dimple centers: smooth mirror. Flat areas between: matte rough
    spec[:,:,0] = np.clip((245 * dimple_map + 150 * (1-dimple_map)) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((8 * dimple_map + 120 * (1-dimple_map)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255  # no clearcoat = raw hammered metal
    return spec

def spec_lightning(shape, mask, seed, sm):
    """Lightning bolt -- bright forked bolt paths on a dark matte surface.
    Unlike plasma (thin veins everywhere), lightning has THICK main bolts with thin forks.
    High contrast: bolt = chrome mirror, background = dark matte."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Generate lightning using random walk paths
    rng = np.random.RandomState(seed + 100)
    bolt_map = np.zeros((h, w), dtype=np.float32)
    num_bolts = int(3 + sm * 2)  # 3-5 main bolts
    for b in range(num_bolts):
        # Start from random edge position
        py = rng.randint(0, h // 4)
        px = rng.randint(w // 4, 3 * w // 4)
        thickness = rng.randint(4, 8)  # main bolt width
        # Walk downward with random jitter (lightning goes top to bottom)
        for step in range(h * 2):
            py += rng.randint(1, 4)  # mostly downward
            px += rng.randint(-6, 7)  # horizontal jitter
            if py >= h:
                break
            px = max(0, min(w - 1, px))
            # Draw thick bolt
            y_lo = max(0, py - thickness)
            y_hi = min(h, py + thickness + 1)
            x_lo = max(0, px - thickness)
            x_hi = min(w, px + thickness + 1)
            bolt_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(
                bolt_map[y_lo:y_hi, x_lo:x_hi], 1.0)
            # Random fork branches
            if rng.random() < 0.03:
                fork_px, fork_py = px, py
                fork_thick = max(1, thickness // 2)
                fork_dir = rng.choice([-1, 1])
                for _ in range(rng.randint(20, 80)):
                    fork_py += rng.randint(1, 3)
                    fork_px += fork_dir * rng.randint(1, 5)
                    if fork_py >= h or fork_px < 0 or fork_px >= w:
                        break
                    fy_lo = max(0, fork_py - fork_thick)
                    fy_hi = min(h, fork_py + fork_thick + 1)
                    fx_lo = max(0, fork_px - fork_thick)
                    fx_hi = min(w, fork_px + fork_thick + 1)
                    bolt_map[fy_lo:fy_hi, fx_lo:fx_hi] = np.maximum(
                        bolt_map[fy_lo:fy_hi, fx_lo:fx_hi], 0.7)
    # Slight blur to soften bolt edges (using PIL, no scipy dependency)
    bolt_pil = Image.fromarray((bolt_map * 255).astype(np.uint8), 'L')
    bolt_pil = bolt_pil.filter(ImageFilter.GaussianBlur(radius=1.5))
    bolt_map = np.array(bolt_pil).astype(np.float32) / 255.0
    bolt_map = np.clip(bolt_map, 0, 1)
    # Background: dark matte. Bolts: chrome mirror = extreme contrast
    spec[:,:,0] = np.clip((255 * bolt_map + 80 * (1-bolt_map)) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((3 * bolt_map + 180 * (1-bolt_map)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_frost_bite(shape, mask, seed, sm):
    """Frost bite -- aggressive frozen metal. Higher roughness than frozen, no clearcoat.
    Rougher and more crystalline than 'frozen' - visible ice crystal patches."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)  # Visible crystal patches
    rn = multi_scale_noise(shape, [8, 16, 24], [0.3, 0.4, 0.3], seed+200)
    spec[:,:,0] = np.clip(230 * mask + 5 * (1-mask) + mn * 35 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(160 * mask + 100 * (1-mask) + rn * 40 * sm * mask, 0, 255).astype(np.uint8)  # R=160 rougher than frozen
    spec[:,:,2] = 0; spec[:,:,3] = 255  # CC=0 raw frozen metal, no clearcoat
    return spec


# ================================================================
# NEW SPEC GENERATORS - Exotic Finishes
# ================================================================

def spec_battle_worn(shape, mask, seed, sm):
    """Scratched weathered metal -- variable clearcoat, wild roughness variation."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    mn = multi_scale_noise(shape, [1, 2, 4], [0.3, 0.4, 0.3], seed+100)
    # Scratch pattern: directional noise
    rng = np.random.RandomState(seed + 301)
    scratch_noise = rng.randn(1, w) * 0.6
    scratch_noise = np.tile(scratch_noise, (h, 1))
    scratch_noise += rng.randn(h, w) * 0.3
    spec[:,:,0] = np.clip(200 * mask + 5 * (1-mask) + mn * 30 * sm * mask + scratch_noise * 20 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(50 * mask + 100 * (1-mask) + scratch_noise * 80 * sm * mask + mn * 40 * sm * mask, 0, 255).astype(np.uint8)
    # VARIABLE clearcoat: 0-16 based on scratch damage
    cc_noise = np.clip((mn + 0.5) * 16, 0, 16)
    spec[:,:,2] = np.clip(cc_noise * mask, 0, 16).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_diamond_plate(shape, mask, seed, sm):
    """Diamond tread plate -- LARGE geometric diamond pattern, visible at car scale."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    diamond_size = 32  # Bigger diamonds (was 12) so visible on the car
    dx = (x % diamond_size) - diamond_size / 2
    dy = (y % diamond_size) - diamond_size / 2
    diamond = ((np.abs(dx) + np.abs(dy)) < diamond_size * 0.38).astype(np.float32)
    # Diamonds are smooth mirror, flat areas are rough = huge visual contrast
    spec[:,:,0] = np.clip((240 * diamond + 180 * (1-diamond)) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((8 * diamond + 140 * (1 - diamond)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255  # no clearcoat, raw metal
    return spec

def spec_dragon_scale(shape, mask, seed, sm):
    """Overlapping scale pattern -- mirror centers, rough matte edges. BIG scales."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    scale_size = 40  # MUCH bigger scales (was 16) so you can actually SEE them on the car
    y, x = get_mgrid((h, w))
    row = y // scale_size
    col = (x + (row % 2) * (scale_size // 2)) // scale_size
    cy = (row + 0.5) * scale_size
    cx = col * scale_size + (row % 2) * (scale_size // 2) + scale_size // 2
    dist = np.sqrt((y - cy)**2 + (x - cx)**2) / (scale_size * 0.55)
    dist = np.clip(dist, 0, 1)
    # Centers: chrome mirror. Edges: rough matte (HUGE contrast so you see the scales)
    spec[:,:,0] = np.clip((255 * (1-dist) + 120 * dist) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((3 * (1-dist) + 160 * dist) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_worn_chrome(shape, mask, seed, sm):
    """Patchy chrome with worn areas -- all 3 channels variable."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [4, 8, 16], [0.2, 0.4, 0.4], seed+100)
    wear = np.clip((mn + 0.3) * 1.5, 0, 1)  # patchy wear map
    # Chrome patches: high R, low G. Worn patches: lower R, higher G
    spec[:,:,0] = np.clip((255 * (1-wear) + 100 * wear) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((2 * (1-wear) + 120 * wear) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    # Clearcoat worn through in damaged spots
    cc = np.clip(16 * (1-wear), 0, 16)
    spec[:,:,2] = np.clip(cc * mask, 0, 16).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_liquid_metal(shape, mask, seed, sm):
    """Mercury/T-1000 -- chrome mirror with large visible pooling distortions."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    wave = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    # Max metallic everywhere, but roughness has large flowing pools
    # Some areas mirror-smooth (G=2), other areas slightly diffuse (G=40)
    spec[:,:,0] = np.clip(255 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    pool = np.clip((wave + 0.5) * 1.3, 0, 1)
    spec[:,:,1] = np.clip((2 * (1-pool) + 50 * pool) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 0; spec[:,:,3] = 255  # CC=0 raw liquid metal, no clearcoat
    return spec

def spec_plasma(shape, mask, seed, sm):
    """Electric plasma -- branching vein pattern visible as roughness contrast."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    n1 = multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed+100)
    n2 = multi_scale_noise(shape, [1, 3, 6, 12], [0.2, 0.3, 0.3, 0.2], seed+200)
    veins = np.abs(n1 + n2 * 0.5)
    vein_mask_f = np.clip(1.0 - veins * 3.0, 0, 1) ** 2  # thin bright lines
    # Veins are mirror-smooth chrome, background is matte -- visible lightning pattern
    spec[:,:,0] = np.clip((255 * vein_mask_f + 160 * (1-vein_mask_f)) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((2 * vein_mask_f + 120 * (1-vein_mask_f)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_ember_glow(shape, mask, seed, sm):
    """Hot ember -- medium metallic with mid clearcoat for warm depth."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    hot_mask = np.clip((mn + 0.2) * 2.0, 0, 1)
    spec[:,:,0] = np.clip((180 + hot_mask * 40) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(40 * mask + 100 * (1-mask) + mn * 20 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = 16  # Full clearcoat (iRacing: 0-15=OFF, 16=ON)
    spec[:,:,3] = 255
    return spec

def spec_acid_wash(shape, mask, seed, sm):
    """Acid etched -- splotchy high-variance roughness, corroded clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    etch = multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed+100)
    spec[:,:,0] = np.clip(200 * mask + 5 * (1-mask) + etch * 35 * sm * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(60 * mask + 100 * (1-mask) + etch * 60 * sm * mask, 0, 255).astype(np.uint8)
    # Clearcoat eaten away in heavily etched areas
    etch_depth = np.clip(np.abs(etch) * 2, 0, 1)
    cc = np.clip(16 * (1 - etch_depth * 0.8), 0, 16)
    spec[:,:,2] = np.clip(cc * mask, 0, 16).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_hologram(shape, mask, seed, sm):
    """Holographic projection -- horizontal scanline banding visible in roughness."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y = np.arange(h).reshape(-1, 1)
    # Visible scanline bands in the roughness channel (alternating smooth/rough rows)
    scanline = ((y % 6) < 3).astype(np.float32)
    scanline = np.broadcast_to(scanline, (h, w))
    spec[:,:,0] = np.clip(220 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    # Roughness alternates: 5 on bright lines, 80 on dark lines = visible line pattern
    spec[:,:,1] = np.clip((5 * scanline + 80 * (1 - scanline)) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_interference(shape, mask, seed, sm):
    """Thin-film interference -- flowing rainbow bands via roughness waves."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    y, x = get_mgrid((h, w))
    # Large flowing wave bands that create visible stripes of different reflectivity
    wave = np.sin(y * 0.02 + x * 0.01) * 0.4 + np.sin(y * 0.01 - x * 0.015) * 0.3 + \
           np.sin((y + x) * 0.008) * 0.3
    wave = (wave + 1.0) * 0.5  # normalize 0-1
    # High metallic with wave-modulated roughness = visible flowing bands on the car
    spec[:,:,0] = np.clip(240 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip((5 + wave * 100) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def _forged_carbon_chunks(shape, seed):
    """Generate forged carbon chunk pattern - irregular angular fiber patches.
    Returns a float array [0..1] where different value ranges = different chunks.
    Uses large-scale smooth noise with hard quantisation for chunk boundaries."""
    h, w = shape
    rng = np.random.RandomState(seed)
    # Layer 1: large smooth blobs (the main chunk shapes) - tighter for realistic forged CF
    s1h, s1w = max(1, h // 24), max(1, w // 24)
    raw1 = rng.randn(s1h, s1w).astype(np.float32)
    img1 = Image.fromarray(((raw1 + 3) / 6 * 255).clip(0, 255).astype(np.uint8))
    n1 = np.array(img1.resize((int(w), int(h)), Image.BILINEAR)).astype(np.float32) / 255.0
    # Layer 2: medium detail (breaks up the blobs into angular sub-chunks)
    s2h, s2w = max(1, h // 12), max(1, w // 12)
    raw2 = rng.randn(s2h, s2w).astype(np.float32)
    img2 = Image.fromarray(((raw2 + 3) / 6 * 255).clip(0, 255).astype(np.uint8))
    n2 = np.array(img2.resize((int(w), int(h)), Image.BILINEAR)).astype(np.float32) / 255.0
    # Layer 3: fine grain for surface texture within chunks
    s3h, s3w = max(1, h // 4), max(1, w // 4)
    raw3 = rng.randn(s3h, s3w).astype(np.float32)
    img3 = Image.fromarray(((raw3 + 3) / 6 * 255).clip(0, 255).astype(np.uint8))
    n3 = np.array(img3.resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
    # Combine: large shapes dominate, medium adds sub-structure, fine adds grain
    combined = n1 * 0.55 + n2 * 0.35 + n3 * 0.10
    # Quantise into ~8-12 discrete chunk levels for sharp boundaries
    num_levels = 10
    quantised = np.floor(combined * num_levels) / num_levels
    # Normalise to [0, 1]
    qmin, qmax = quantised.min(), quantised.max()
    if qmax > qmin:
        quantised = (quantised - qmin) / (qmax - qmin)
    return quantised, n3  # return fine noise too for per-chunk sheen

def spec_forged_carbon(shape, mask, seed, sm):
    """Chopped carbon fiber - irregular chunks with varying roughness/reflectivity.
    Each chunk is a pressed fiber strand at a random angle, creating subtle
    differences in roughness and metallic response across the surface."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    chunks, fine = _forged_carbon_chunks(shape, seed + 100)
    # Metallic: moderate-high, slight per-chunk variation (carbon is semi-metallic)
    metal_base = 60 + chunks * 40 * sm  # 60..100 range
    spec[:,:,0] = np.clip(metal_base * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    # Roughness: each chunk has slightly different roughness (fiber orientation)
    # Lower roughness = shinier chunk face, higher = matte fiber edge
    rough_base = 25 + chunks * 50 * sm + fine * 8 * sm  # 25..83 range
    spec[:,:,1] = np.clip(rough_base * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    # Clearcoat: ON (real forged carbon has epoxy clearcoat, B=16=ON in iRacing)
    spec[:,:,2] = np.clip(16 * mask + 0 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_cracked_ice(shape, mask, seed, sm):
    """Frozen cracked surface -- smooth ice with rough crack lines."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Simplified crack pattern using noise zero-crossings
    n1 = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed+200)
    # Cracks where noise is near zero
    crack1 = np.exp(-n1**2 * 20)
    crack2 = np.exp(-n2**2 * 20)
    cracks = np.clip(crack1 + crack2, 0, 1)
    mn = multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed+300)
    spec[:,:,0] = np.clip((230 + mn * 15 * sm) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    # Smooth ice (15) vs rough cracks (130)
    spec[:,:,1] = np.clip((15 * (1-cracks) + 130 * cracks) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    spec[:,:,2] = 16; spec[:,:,3] = 255
    return spec

def spec_phantom(shape, mask, seed, sm):
    """Phantom -- ultra-mirror finish that makes paint vanish into reflections.
    High metallic + near-zero roughness = environment reflects instead of paint color.
    Paint 'disappears' at most angles, ghosts back when lighting is just right.
    Noise pattern creates hot spots where paint peeks through vs fully vanished."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape
    # Noise for where paint "peeks through" vs fully mirrored
    peek = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    peek_map = np.clip((peek + 0.3) * 0.8, 0, 1)  # mostly mirrored, some peek spots
    # R = very high metallic everywhere (mirror behavior)
    spec[:,:,0] = np.clip((245 - peek_map * 30 * sm) * mask + 5 * (1-mask), 0, 255).astype(np.uint8)
    # G = the key: ultra-low roughness makes the color vanish into reflections
    # Near 0 = perfect mirror (color invisible), 15-25 = slight diffuse (color peeks through)
    spec[:,:,1] = np.clip((2 + peek_map * 20 * sm) * mask + 100 * (1-mask), 0, 255).astype(np.uint8)
    # B = max clearcoat for glossy wet look
    spec[:,:,2] = 16
    spec[:,:,3] = 255
    return spec

def paint_phantom_fade(paint, shape, mask, seed, pm, bb):
    """Phantom paint -- slightly desaturate and brighten to enhance the mirror vanishing effect.
    The paint color becomes more 'ghostly' so when it does peek through reflections,
    it looks ethereal rather than solid."""
    h, w = shape
    # Slight desaturation: push toward silver/white to enhance mirror
    gray = paint.mean(axis=2, keepdims=True)
    desat = 0.25 * pm
    paint = paint * (1 - desat * mask[:,:,np.newaxis]) + gray * desat * mask[:,:,np.newaxis]
    # Brighten slightly so the color reads cleaner when it peeks through
    paint = np.clip(paint + bb * 1.5 * pm * mask[:,:,np.newaxis], 0, 1)
    # Subtle noise shimmer
    shimmer = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 500)
    paint = np.clip(paint + shimmer[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def spec_blackout(shape, mask, seed, sm):
    """Stealth murdered-out -- minimal metallic, max rough, no clearcoat. Full spec authority."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(30 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # M=30 near-zero
    spec[:,:,1] = np.clip(220 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=220 very rough
    spec[:,:,2] = 0  # No clearcoat
    spec[:,:,3] = 255  # Full spec authority (A=255)
    return spec


# ================================================================
# PAINT MODIFIERS (SUBTLE - no color shifts)
# ================================================================

def paint_none(paint, shape, mask, seed, pm, bb):
    return paint

def paint_subtle_flake(paint, shape, mask, seed, pm, bb):
    """Fine metallic flake -- visible sparkle texture on the base paint."""
    for c in range(3):
        flake = multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + c * 17)
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.10 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 0.8 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_fine_sparkle(paint, shape, mask, seed, pm, bb):
    """Fine sparkle points -- candy/pearl glitter effect."""
    flake = multi_scale_noise(shape, [1], [1.0], seed + 50)
    h, w = shape
    rng = np.random.RandomState(seed + 77)
    sparkle = rng.random((h, w)).astype(np.float32)
    sparkle = np.where(sparkle > 0.93, sparkle * 0.15 * pm, 0)  # More visible sparkle dots
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.08 * pm * mask + sparkle * mask, 0, 1)
    paint = np.clip(paint + bb * 0.8 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_coarse_flake(paint, shape, mask, seed, pm, bb):
    """Coarse metallic flake -- holographic/prismatic color shift visible in paint.
    Visible flake sparkle that adds metallic character to the base paint.
    The spec map handles the real metallic/flake appearance."""
    h, w = shape
    r_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+11)
    g_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+22)
    b_flake = multi_scale_noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed+33)
    strength = 0.12 * pm  # Visible flake - this IS the "heavy visible" base
    paint[:,:,0] = np.clip(paint[:,:,0] + r_flake * strength * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + g_flake * strength * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + b_flake * strength * mask, 0, 1)
    # Sparkle glints -- visible bright spots
    rng = np.random.RandomState(seed + 99)
    glint = rng.random((h, w)).astype(np.float32)
    glint = np.where(glint > 0.93, glint * 0.15 * pm, 0)  # More frequent, brighter glints
    paint = np.clip(paint + glint[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * 0.8 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_carbon_darken(paint, shape, mask, seed, pm, bb):
    """Carbon fiber weave -- visible crosshatch darkening matching the spec pattern.
    Uses same 6px weave_size as texture_carbon_fiber for alignment."""
    h, w = shape
    y, x = get_mgrid((h, w))
    weave_size = 6  # Must match texture_carbon_fiber
    # Same 2x2 twill pattern as spec function
    tow_x = (x % (weave_size * 2)) / (weave_size * 2)
    tow_y = (y % (weave_size * 2)) / (weave_size * 2)
    horiz = np.sin(tow_x * np.pi * 2) * 0.5 + 0.5
    vert = np.sin(tow_y * np.pi * 2) * 0.5 + 0.5
    twill_cell = ((x // weave_size + y // weave_size) % 2).astype(np.float32)
    cf = twill_cell * horiz + (1 - twill_cell) * vert
    cf = np.clip(cf * 1.3 - 0.15, 0, 1)
    # Adaptive: dark paint gets lightened weave, light paint gets darkened weave
    brightness = paint[:,:,0]*0.299 + paint[:,:,1]*0.587 + paint[:,:,2]*0.114
    is_dark = np.clip((0.2 - brightness) / 0.15, 0, 1)  # smooth transition
    darken_strength = 0.10 * pm
    lighten_strength = 0.07 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            - cf * darken_strength * (1 - is_dark) * mask
            + cf * lighten_strength * is_dark * mask, 0, 1)
    # Weave peak sheen - subtle glossy highlight on raised threads
    sheen = np.clip(cf - 0.4, 0, 0.6) / 0.6
    paint = np.clip(paint + sheen[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_chrome_brighten(paint, shape, mask, seed, pm, bb):
    """Chrome mirror effect -- pushes paint toward bright reflective silver.
    SUBTLER than before: adds a chrome sheen without destroying the base paint.
    The spec map does the heavy lifting for chrome appearance."""
    blend = 0.22 * pm  # Bumped from 0.15 - PBR research: metallic albedo needs brighter for chrome to read correctly
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - mask * blend) + 0.92 * mask * blend
    h, w = shape
    reflection = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 150)
    paint = np.clip(paint + reflection[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# FINISH REGISTRY
# ================================================================

# ================================================================
# NEW PAINT MODIFIERS - Exotic Effects
# ================================================================

def paint_scratch_marks(paint, shape, mask, seed, pm, bb):
    """Battle-worn scratches -- directional linear marks across the surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 300)
    scratches = np.zeros((h, w), dtype=np.float32)
    num_scratches = int(120 * pm)
    for _ in range(num_scratches):
        y0 = rng.randint(0, h)
        x0 = rng.randint(0, w)
        angle = rng.uniform(-0.3, 0.3)
        length = rng.randint(50, 400)
        for t in range(length):
            yi = int(y0 + t * np.sin(angle))
            xi = int(x0 + t * np.cos(angle))
            if 0 <= yi < h and 0 <= xi < w:
                width = rng.randint(1, 3)
                for dy in range(-width, width + 1):
                    yy = yi + dy
                    if 0 <= yy < h:
                        scratches[yy, xi] = max(scratches[yy, xi], rng.uniform(0.3, 1.0))
    # Scratches brighten on dark paint, darken on light paint
    brightness = paint.mean(axis=2)
    is_dark = (brightness < 0.15).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            + scratches * 0.12 * pm * mask * is_dark        # lighten scratches on dark
            - scratches * 0.10 * pm * mask * (1 - is_dark),  # darken scratches on light
        0, 1)
    return paint

def paint_diamond_emboss(paint, shape, mask, seed, pm, bb):
    """Diamond plate -- geometric raised diamond shapes visible on paint."""
    h, w = shape
    y, x = get_mgrid((h, w))
    diamond_size = 16
    dx = (x % diamond_size) - diamond_size / 2
    dy = (y % diamond_size) - diamond_size / 2
    diamond = (np.abs(dx) + np.abs(dy)) < diamond_size * 0.35
    diamond_f = diamond.astype(np.float32)
    # Raised diamonds: brighten. Flat areas: slight darken. Visible on ALL paints.
    paint = np.clip(paint + diamond_f[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint - (1 - diamond_f)[:,:,np.newaxis] * 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    # Extra brightness boost so diamond pattern shows on dark paints
    paint = np.clip(paint + bb * 1.5 * diamond_f[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_scale_pattern(paint, shape, mask, seed, pm, bb):
    """Dragon scales -- overlapping hexagonal scale pattern with per-scale color shift."""
    h, w = shape
    scale_size = 24
    y, x = get_mgrid((h, w))
    # Offset hex grid
    row = y // scale_size
    col = (x + (row % 2) * (scale_size // 2)) // scale_size
    # Distance from scale center
    cy = (row + 0.5) * scale_size
    cx = col * scale_size + (row % 2) * (scale_size // 2) + scale_size // 2
    dist = np.sqrt((y - cy)**2 + (x - cx)**2) / (scale_size * 0.6)
    dist = np.clip(dist, 0, 1)
    # Per-scale color variation (visible shimmer)
    color_shift = np.zeros((h, w, 3), dtype=np.float32)
    for c in range(3):
        noise = multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 401 + c)
        color_shift[:,:,c] = noise * 0.08 * pm
    # Scale centers shimmer bright, edges are darker grooves
    center_boost = (1 - dist) * 0.12 * pm
    edge_groove = dist * 0.08 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            + center_boost * mask + color_shift[:,:,c] * (1 - dist) * mask
            - edge_groove * mask, 0, 1)
    # Brightness boost on scale centers for dark paints
    paint = np.clip(paint + bb * 2.0 * (1 - dist)[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_patina(paint, shape, mask, seed, pm, bb):
    """Worn chrome patina -- greenish/brownish oxidation in rough areas."""
    h, w = shape
    # Generate patchy oxidation map
    patina_map = multi_scale_noise(shape, [4, 8, 16], [0.2, 0.4, 0.4], seed + 500)
    patina_mask = np.clip((patina_map + 0.3) * 1.5, 0, 1)  # biased toward more patina
    # Patina tint: greenish-brown (oxidized copper/chrome)
    tint_r = -0.04 * pm  # less red
    tint_g = 0.02 * pm   # slight green
    tint_b = -0.03 * pm  # less blue
    paint[:,:,0] = np.clip(paint[:,:,0] + tint_r * patina_mask * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + tint_g * patina_mask * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + tint_b * patina_mask * mask, 0, 1)
    return paint

def paint_liquid_reflect(paint, shape, mask, seed, pm, bb):
    """Liquid metal -- large flowing wave reflections like mercury."""
    h, w = shape
    wave1 = multi_scale_noise(shape, [16, 32], [0.4, 0.6], seed + 600)
    wave2 = multi_scale_noise(shape, [24, 48], [0.5, 0.5], seed + 601)
    combined = (wave1 + wave2) * 0.5
    # Push paint toward bright silver in wave peaks
    wave_peaks = np.clip(combined, 0, 1)
    blend = wave_peaks * 0.30 * pm
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - blend * mask) + 0.88 * blend * mask
    # Wave brightness modulation visible even on dark paints
    paint = np.clip(paint + bb * 2.5 * wave_peaks[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_plasma_veins(paint, shape, mask, seed, pm, bb):
    """Plasma veins -- branching lightning/vein patterns that glow."""
    h, w = shape
    n1 = multi_scale_noise(shape, [2, 4, 8, 16], [0.15, 0.25, 0.35, 0.25], seed + 700)
    n2 = multi_scale_noise(shape, [1, 3, 6, 12], [0.2, 0.3, 0.3, 0.2], seed + 701)
    veins = np.abs(n1 + n2 * 0.5)
    vein_mask = np.clip(1.0 - veins * 3.0, 0, 1)
    vein_mask = vein_mask ** 2
    # Veins glow bright -- visible even on black paint
    glow = vein_mask * 0.22 * pm
    paint = np.clip(paint + glow[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    # Blue/purple tint to veins (electric plasma look)
    paint[:,:,0] = np.clip(paint[:,:,0] + vein_mask * 0.05 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + vein_mask * 0.10 * pm * mask, 0, 1)
    return paint

def paint_ember_glow(paint, shape, mask, seed, pm, bb):
    """Ember glow -- hot spots where paint appears to glow from within."""
    h, w = shape
    # Generate hot spot map
    hotspots = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 800)
    hot_mask = np.clip((hotspots + 0.2) * 2.0, 0, 1)
    # Read the paint brightness to enhance warm areas
    brightness = paint.mean(axis=2)
    warmth = np.clip(brightness * 1.5, 0, 1)
    # Add warm glow (orange/red tint) in hot areas
    glow_strength = hot_mask * warmth * pm * 0.08
    paint[:,:,0] = np.clip(paint[:,:,0] + glow_strength * 1.5 * mask, 0, 1)  # more red
    paint[:,:,1] = np.clip(paint[:,:,1] + glow_strength * 0.6 * mask, 0, 1)  # some green (orange)
    paint[:,:,2] = np.clip(paint[:,:,2] - glow_strength * 0.3 * mask, 0, 1)  # less blue
    # Darken cool areas slightly for contrast
    cool_mask = 1.0 - hot_mask
    paint = np.clip(paint - cool_mask[:,:,np.newaxis] * 0.02 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_acid_etch(paint, shape, mask, seed, pm, bb):
    """Acid wash -- corroded erosion patterns with desaturation."""
    h, w = shape
    # Heavy splotchy erosion pattern
    etch = multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed + 900)
    etch_mask = np.clip(np.abs(etch) * 2.0, 0, 1)
    # Dark erosion lines
    paint = np.clip(paint - etch_mask[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    # Desaturate in heavily etched areas
    gray = paint.mean(axis=2, keepdims=True)
    desat = etch_mask[:,:,np.newaxis] * 0.3 * pm * mask[:,:,np.newaxis]
    paint = paint * (1 - desat) + gray * desat
    return paint

def paint_hologram_lines(paint, shape, mask, seed, pm, bb):
    """Hologram scanlines -- horizontal line pattern with chromatic aberration.
    Scanline thickness scales with resolution for visibility at 2048+."""
    h, w = shape
    y = np.arange(h)
    # Scale scanline period to match texture_hologram (~80 bands)
    period = max(4, h // 80)
    half = max(1, period // 2)
    scanline = ((y % period) < half).astype(np.float32).reshape(-1, 1)
    scanline = np.broadcast_to(scanline, (h, w)).copy()
    # Scanlines add visible brightness on ALL paint colors
    paint = np.clip(paint + scanline[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    # Chromatic aberration: shift R and B channels for rainbow fringing
    shift = max(2, int(pm * max(3, h // 500)))
    shifted_r = np.roll(paint[:,:,0], -shift, axis=0)
    shifted_b = np.roll(paint[:,:,2], shift, axis=0)
    blend = 0.30 * pm
    paint[:,:,0] = paint[:,:,0] * (1 - mask * blend) + shifted_r * mask * blend
    paint[:,:,2] = paint[:,:,2] * (1 - mask * blend) + shifted_b * mask * blend
    # Base brightness boost for dark paints
    paint = np.clip(paint + bb * 2.5 * scanline[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_interference_shift(paint, shape, mask, seed, pm, bb):
    """Thin-film interference -- actual hue rotation creating rainbow bands."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Large-scale sine waves for rainbow band direction
    wave = np.sin(y * 0.015 + x * 0.008 + seed * 0.1) * 0.5 + \
           np.sin(y * 0.008 - x * 0.012 + seed * 0.2) * 0.3 + \
           np.sin((y + x) * 0.006 + seed * 0.3) * 0.2
    # Normalize to 0-1 for hue rotation amount
    hue_shift = (wave + 1.0) * 0.5  # 0 to 1
    # Convert paint to HSV, rotate hue, convert back
    r, g, b = paint[:,:,0], paint[:,:,1], paint[:,:,2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin + 1e-8
    # Compute hue (0-1)
    hue = np.zeros((h, w), dtype=np.float32)
    m_r = (cmax == r)
    m_g = (cmax == g) & ~m_r
    m_b = ~m_r & ~m_g
    hue[m_r] = ((g[m_r] - b[m_r]) / delta[m_r]) % 6 / 6
    hue[m_g] = ((b[m_g] - r[m_g]) / delta[m_g] + 2) / 6
    hue[m_b] = ((r[m_b] - g[m_b]) / delta[m_b] + 4) / 6
    sat = delta / (cmax + 1e-8)
    val = cmax
    # Rotate hue by the interference wave
    shift_amount = hue_shift * 0.4 * pm  # rotate up to 40% of the hue wheel
    new_hue = (hue + shift_amount * mask) % 1.0
    # Convert back to RGB
    new_rgb = np.stack(hsv_to_rgb_vec(new_hue, sat, val), axis=2)  # (H,W,3)
    # Blend based on mask intensity; support both RGB and RGBA paint
    blend = mask * 0.7 * pm
    blend3 = blend[:,:,np.newaxis]
    paint[:,:,:3] = paint[:,:,:3] * (1 - blend3) + new_rgb * blend3
    paint = np.clip(paint, 0, 1)
    return paint[:,:,:3].astype(np.float32, copy=False)

def paint_forged_carbon(paint, shape, mask, seed, pm, bb):
    """Forged carbon - darkens toward carbon black with per-chunk brightness variation.
    Real forged carbon is almost black with subtle tonal shifts between fiber chunks."""
    h, w = shape
    chunks, fine = _forged_carbon_chunks(shape, seed + 1000)
    mask3 = mask[:,:,np.newaxis]
    # Step 1: Darken heavily toward near-black (carbon is dark)
    # pm controls how aggressive: at pm=1.0, moderate darkening; at extreme, very dark
    darken_strength = 0.06 * pm  # 0.06 per pm level
    dark_rgb = np.array([0.03, 0.03, 0.04], dtype=np.float32)
    paint[:,:,:3] = paint[:,:,:3] * (1 - mask3 * darken_strength) + mask3 * darken_strength * dark_rgb
    # Step 2: Per-chunk tonal variation - some chunks slightly lighter/warmer
    # This creates the distinctive forged carbon "swirl" look
    chunk_brightness = (chunks - 0.5) * 0.04 * pm  # subtle +-0.04 brightness shift
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + chunk_brightness * mask, 0, 1)
    # Step 3: Very subtle warm/cool shift per chunk (some chunks slightly blue, some warm)
    warm_shift = (chunks > 0.5).astype(np.float32) * 0.008 * pm
    cool_shift = (chunks <= 0.5).astype(np.float32) * 0.005 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + warm_shift * mask, 0, 1)   # slightly warmer reds
    paint[:,:,2] = np.clip(paint[:,:,2] + cool_shift * mask, 0, 1)   # slightly cooler blues
    return paint[:,:,:3].astype(np.float32, copy=False)

def paint_ice_cracks(paint, shape, mask, seed, pm, bb):
    """Cracked ice -- Voronoi crack network with blue tint."""
    h, w = shape
    rng = np.random.RandomState(seed + 1100)
    # Generate Voronoi seed points
    num_points = 200
    points_y = rng.randint(0, h, num_points)
    points_x = rng.randint(0, w, num_points)
    # Compute distance to nearest two points for each pixel (downsampled for speed)
    ds = 4  # downsample factor
    sh, sw = h // ds, w // ds
    yg, xg = np.mgrid[0:sh, 0:sw]
    yg = yg * ds
    xg = xg * ds
    dist1 = np.full((sh, sw), 1e9)
    dist2 = np.full((sh, sw), 1e9)
    for py, px in zip(points_y, points_x):
        d = np.sqrt((yg - py)**2 + (xg - px)**2).astype(np.float32)
        update2 = d < dist2
        update1 = d < dist1
        dist2 = np.where(update2, np.minimum(d, dist2), dist2)
        dist2 = np.where(update1, dist1, dist2)
        dist1 = np.where(update1, d, dist1)
    # Crack = where dist1 ~ dist2 (boundary between cells)
    crack_raw = np.clip(1.0 - (dist2 - dist1) / 8.0, 0, 1)
    # Upsample back to full resolution
    crack_img = Image.fromarray((crack_raw * 255).astype(np.uint8))
    crack_img = crack_img.resize((w, h), Image.BILINEAR)
    cracks = np.array(crack_img).astype(np.float32) / 255.0
    # Dark crack lines
    paint = np.clip(paint - cracks[:,:,np.newaxis] * 0.1 * pm * mask[:,:,np.newaxis], 0, 1)
    # Blue tint on ice surfaces (non-crack areas)
    ice = 1.0 - cracks
    paint[:,:,2] = np.clip(paint[:,:,2] + ice * 0.03 * pm * mask, 0, 1)  # add blue
    paint[:,:,0] = np.clip(paint[:,:,0] - ice * 0.01 * pm * mask, 0, 1)  # less red
    return paint


def paint_stardust_sparkle(paint, shape, mask, seed, pm, bb):
    """Stardust -- scattered bright pinpoint sparkles across the paint surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 1200)
    sparkles = rng.random((h, w)).astype(np.float32)
    # Sparse bright pinpoints (matching the star density in spec)
    star_mask = (sparkles > (1.0 - 0.02)).astype(np.float32)
    # Stars brighten the paint dramatically at their point
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + star_mask * 0.35 * pm * mask, 0, 1)
    # General subtle brightness boost
    paint = np.clip(paint + bb * 1.0 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_hex_emboss(paint, shape, mask, seed, pm, bb):
    """Hex mesh -- honeycomb wire pattern visible in the paint with light/shadow."""
    h, w = shape
    y, x = get_mgrid((h, w))
    hex_size = 24
    row = y / (hex_size * 0.866)
    col = x / hex_size
    col_shifted = col - 0.5 * (np.floor(row).astype(int) % 2)
    row_round = np.round(row)
    col_round = np.round(col_shifted)
    cy = row_round * hex_size * 0.866
    cx = (col_round + 0.5 * (row_round.astype(int) % 2)) * hex_size
    dist = np.sqrt((y - cy)**2 + (x - cx)**2)
    norm_dist = np.clip(dist / (hex_size * 0.45), 0, 1)
    wire = (norm_dist > 0.75).astype(np.float32)
    # Wire darkens, centers brighten
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            - wire * 0.08 * pm * mask
            + (1 - wire) * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 1.5 * (1 - wire)[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_ripple_reflect(paint, shape, mask, seed, pm, bb):
    """Ripple -- concentric ring reflections like water surface."""
    h, w = shape
    y, x = get_mgrid((h, w))
    rng = np.random.RandomState(seed + 1300)
    ripple_sum = np.zeros((h, w), dtype=np.float32)
    for _ in range(6):
        cy = rng.randint(0, h)
        cx = rng.randint(0, w)
        dist = np.sqrt((y - cy)**2 + (x - cx)**2).astype(np.float32)
        ring_spacing = rng.uniform(20, 40)
        ripple = np.sin(dist / ring_spacing * 2 * np.pi)
        fade = np.clip(1.0 - dist / (max(h, w) * 0.6), 0, 1)
        ripple_sum += ripple * fade
    rmax = np.abs(ripple_sum).max() + 1e-8
    ripple_norm = ripple_sum / rmax
    wave_peaks = np.clip(ripple_norm, 0, 1)
    # Brighten on ring peaks, darken in valleys
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            + wave_peaks * 0.08 * pm * mask
            - (1 - wave_peaks) * 0.03 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 2.0 * wave_peaks[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_hammered_dimples(paint, shape, mask, seed, pm, bb):
    """Hammered -- dimple indentation pattern visible in the paint."""
    h, w = shape
    rng = np.random.RandomState(seed + 1400)
    num_dimples = 400
    # Quick dimple map (same algorithm as spec but for paint effect)
    ds = 4
    sh, sw = h // ds, w // ds
    yg, xg = np.mgrid[0:sh, 0:sw]
    yg = (yg * ds).astype(np.float32)
    xg = (xg * ds).astype(np.float32)
    dimple_small = np.zeros((sh, sw), dtype=np.float32)
    dimple_y = rng.randint(0, h, num_dimples).astype(np.float32)
    dimple_x = rng.randint(0, w, num_dimples).astype(np.float32)
    dimple_r = rng.randint(8, 22, num_dimples).astype(np.float32)
    for dy, dx, dr in zip(dimple_y, dimple_x, dimple_r):
        y_lo = max(0, int((dy - dr) / ds))
        y_hi = min(sh, int((dy + dr) / ds) + 1)
        x_lo = max(0, int((dx - dr) / ds))
        x_hi = min(sw, int((dx + dr) / ds) + 1)
        if y_hi <= y_lo or x_hi <= x_lo:
            continue
        sub_y = yg[y_lo:y_hi, x_lo:x_hi]
        sub_x = xg[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((sub_y - dy)**2 + (sub_x - dx)**2)
        dimple = np.clip(1.0 - dist / dr, 0, 1) ** 2
        dimple_small[y_lo:y_hi, x_lo:x_hi] = np.maximum(
            dimple_small[y_lo:y_hi, x_lo:x_hi], dimple)
    dimple_img = Image.fromarray((dimple_small * 255).astype(np.uint8))
    dimple_img = dimple_img.resize((w, h), Image.BILINEAR)
    dimple_map = np.array(dimple_img).astype(np.float32) / 255.0
    # Dimple centers catch light, edges are dark grooves
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            + dimple_map * 0.06 * pm * mask
            - (1 - dimple_map) * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 1.5 * dimple_map[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_lightning_glow(paint, shape, mask, seed, pm, bb):
    """Lightning -- bolt paths glow bright white/blue against the paint."""
    h, w = shape
    rng = np.random.RandomState(seed + 1500)
    bolt_map = np.zeros((h, w), dtype=np.float32)
    num_bolts = 4
    for b in range(num_bolts):
        py = rng.randint(0, h // 4)
        px = rng.randint(w // 4, 3 * w // 4)
        thickness = rng.randint(3, 6)
        for step in range(h * 2):
            py += rng.randint(1, 4)
            px += rng.randint(-6, 7)
            if py >= h: break
            px = max(0, min(w - 1, px))
            y_lo, y_hi = max(0, py - thickness), min(h, py + thickness + 1)
            x_lo, x_hi = max(0, px - thickness), min(w, px + thickness + 1)
            bolt_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(
                bolt_map[y_lo:y_hi, x_lo:x_hi], 1.0)
            if rng.random() < 0.03:
                fork_px, fork_py = px, py
                fork_dir = rng.choice([-1, 1])
                for _ in range(rng.randint(15, 60)):
                    fork_py += rng.randint(1, 3)
                    fork_px += fork_dir * rng.randint(1, 5)
                    if fork_py >= h or fork_px < 0 or fork_px >= w: break
                    ft = max(1, thickness // 2)
                    bolt_map[max(0,fork_py-ft):min(h,fork_py+ft+1),
                             max(0,fork_px-ft):min(w,fork_px+ft+1)] = \
                        np.maximum(bolt_map[max(0,fork_py-ft):min(h,fork_py+ft+1),
                                            max(0,fork_px-ft):min(w,fork_px+ft+1)], 0.6)
    bolt_map = np.clip(bolt_map, 0, 1)
    # Bolts glow bright white/blue
    paint = np.clip(paint + bolt_map[:,:,np.newaxis] * 0.25 * pm * mask[:,:,np.newaxis], 0, 1)
    # Blue tint on bolts
    paint[:,:,2] = np.clip(paint[:,:,2] + bolt_map * 0.08 * pm * mask, 0, 1)
    # Darken background slightly for contrast
    paint = np.clip(paint - (1 - bolt_map)[:,:,np.newaxis] * 0.02 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_brushed_grain(paint, shape, mask, seed, pm, bb):
    """Brushed titanium -- horizontal grain lines visible in the paint."""
    h, w = shape
    rng = np.random.RandomState(seed + 1600)
    row_grain = rng.randn(h, 1).astype(np.float32) * 0.7
    row_grain = np.tile(row_grain, (1, w))
    row_grain += rng.randn(h, w).astype(np.float32) * 0.08
    grain_light = np.clip(row_grain, 0, 1)
    grain_dark = np.clip(-row_grain, 0, 1)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            + grain_light * 0.06 * pm * mask
            - grain_dark * 0.04 * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 1.0 * mask[:,:,np.newaxis], 0, 1)
    return paint

# --- PAINT MODIFIERS: Expansion Pack (25 new finishes) ---

def paint_ceramic_gloss(paint, shape, mask, seed, pm, bb):
    """Ceramic coating - ultra-deep wet gloss effect."""
    # Saturate colors slightly and add very smooth reflection
    brightness = paint[:,:,0]*0.299 + paint[:,:,1]*0.587 + paint[:,:,2]*0.114
    for c in range(3):
        # Boost saturation relative to luminance
        diff = paint[:,:,c] - brightness
        paint[:,:,c] = np.clip(brightness + diff * (1.0 + 0.15 * pm) + bb * 1.5, 0, 1) * mask[:,:] + paint[:,:,c] * (1 - mask)
    return paint

def paint_satin_wrap(paint, shape, mask, seed, pm, bb):
    """Satin vinyl wrap - slightly desaturated, uniform matte sheen."""
    brightness = paint[:,:,0]*0.299 + paint[:,:,1]*0.587 + paint[:,:,2]*0.114
    for c in range(3):
        diff = paint[:,:,c] - brightness
        paint[:,:,c] = np.clip(brightness + diff * 0.85, 0, 1) * mask + paint[:,:,c] * (1 - mask)
    return paint

def paint_primer_flat(paint, shape, mask, seed, pm, bb):
    """Primer - desaturate and push toward flat gray."""
    brightness = paint[:,:,0]*0.299 + paint[:,:,1]*0.587 + paint[:,:,2]*0.114
    gray_blend = 0.5 * pm
    for c in range(3):
        paint[:,:,c] = (paint[:,:,c] * (1 - gray_blend * mask) + brightness * gray_blend * mask)
    # Add very fine grain noise
    rng = np.random.RandomState(seed + 500)
    grain = rng.randn(*shape).astype(np.float32) * 0.03 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + grain * mask, 0, 1)
    return paint

def paint_warm_metal(paint, shape, mask, seed, pm, bb):
    """Warm metallic shift - push toward copper/gold tones."""
    for c in range(3):
        shift = [0.06, 0.02, -0.03][c]  # warm: more red/green, less blue
        flake = multi_scale_noise(shape, [1, 2, 4], [0.4, 0.35, 0.25], seed + c * 17)
        paint[:,:,c] = np.clip(paint[:,:,c] + flake * 0.08 * pm * mask + shift * pm * mask, 0, 1)
    paint = np.clip(paint + bb * 1.5 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_chameleon_shift(paint, shape, mask, seed, pm, bb):
    """Chameleon color-shift - visible smooth color bands rotating hue across surface."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Spatial angle field - pm controls BLEND STRENGTH, not frequency
    # (high pm was wrapping cos/sin too many times, creating noise instead of bands)
    angle = np.sin(y * 0.08 + x * 0.06) * 0.5 + np.sin(y * 0.04 - x * 0.07) * 0.3
    angle = angle + np.sin((y + x) * 0.03) * 0.2
    # Smooth RGB rotation (fixed frequency, pm controls strength)
    cos_a = np.cos(angle * np.pi * 2.0)
    sin_a = np.sin(angle * np.pi * 2.0)
    r, g, b = paint[:,:,0].copy(), paint[:,:,1].copy(), paint[:,:,2].copy()
    # Full hue rotation matrix
    nr = np.clip(r * (0.33 + 0.67 * cos_a) + g * (0.33 * (1 - cos_a) + 0.58 * sin_a) + b * (0.33 * (1 - cos_a) - 0.58 * sin_a), 0, 1)
    ng = np.clip(r * (0.33 * (1 - cos_a) - 0.58 * sin_a) + g * (0.33 + 0.67 * cos_a) + b * (0.33 * (1 - cos_a) + 0.58 * sin_a), 0, 1)
    nb = np.clip(r * (0.33 * (1 - cos_a) + 0.58 * sin_a) + g * (0.33 * (1 - cos_a) - 0.58 * sin_a) + b * (0.33 + 0.67 * cos_a), 0, 1)
    # pm controls blend strength (capped at full replacement)
    blend = np.clip(pm * 0.25, 0, 1.0)
    paint[:,:,0] = nr * blend * mask + r * (1 - blend * mask)
    paint[:,:,1] = ng * blend * mask + g * (1 - blend * mask)
    paint[:,:,2] = nb * blend * mask + b * (1 - blend * mask)
    paint = np.clip(paint + bb * 1.5 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_tricolore_shift(paint, shape, mask, seed, pm, bb):
    """Pagani Tricolore -- premium three-tone angle-resolved color shift.
    Uses bb to create three angular zones with smooth transitions between them,
    giving the appearance of a paint that shows three distinct colors depending
    on the viewing angle. Ultra-premium feel."""
    if pm == 0.0:
        return paint
    h, w = shape

    # Add subtle spatial variation so the shift isn't perfectly uniform
    n = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 8800)
    angle_field = np.clip(bb + n * 0.12, 0, 1)

    # Three zones via smooth thresholds:
    # Zone 1: shadow/edge (angle 0.0-0.33) -> deep sapphire blue
    # Zone 2: mid-angle  (angle 0.33-0.66) -> rich amethyst purple
    # Zone 3: highlight   (angle 0.66-1.0)  -> warm bronze-gold

    # Smooth zone weights using cosine-bell transitions
    zone1 = np.clip(1.0 - angle_field * 3.0, 0, 1)              # peaks at 0
    zone3 = np.clip(angle_field * 3.0 - 2.0, 0, 1)              # peaks at 1
    zone2 = np.clip(1.0 - np.abs(angle_field - 0.5) * 3.0, 0, 1)  # peaks at 0.5

    # Smooth the zones with squared falloff for premium feel
    zone1 = zone1 * zone1
    zone2 = zone2 * zone2
    zone3 = zone3 * zone3

    # Normalize so they sum to ~1
    total = zone1 + zone2 + zone3 + 1e-8
    zone1 = zone1 / total
    zone2 = zone2 / total
    zone3 = zone3 / total

    # Color shifts per zone (additive to preserve user's chosen paint color)
    # Zone 1: sapphire blue (R--, G-, B++)
    # Zone 2: amethyst purple (R+, G--, B+)
    # Zone 3: bronze gold (R++, G+, B--)
    shift_r = zone1 * (-0.18) + zone2 * (0.15) + zone3 * (0.22)
    shift_g = zone1 * (-0.08) + zone2 * (-0.15) + zone3 * (0.10)
    shift_b = zone1 * (0.22)  + zone2 * (0.12)  + zone3 * (-0.18)

    strength = pm * mask
    paint[:,:,0] = np.clip(paint[:,:,0] + shift_r * strength, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + shift_g * strength, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + shift_b * strength, 0, 1)

    # Subtle depth enhancement: darken shadows, brighten highlights for wet-candy depth
    depth = (angle_field - 0.5) * 0.12 * pm * mask
    paint[:,:,0] = np.clip(paint[:,:,0] + depth, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + depth, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + depth, 0, 1)

    return paint


def paint_carbon_weave(paint, shape, mask, seed, pm, bb):
    """Carbon Weave -- visible diagonal twill weave pattern in the paint channel.
    Creates the distinctive 2x2 twill carbon fiber pattern with alternating
    over/under thread bundles at +45/-45 degrees. Subtle but clearly identifiable."""
    if pm == 0.0:
        return paint
    h, w = shape
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)

    # --- 2x2 twill weave: two sets of diagonal threads at +/-45 degrees ---
    thread_width = 12.0  # pixels per thread bundle (controls weave scale)

    # Thread set A: +45 degrees (top-left to bottom-right)
    diag_a = (yf + xf) / thread_width
    # Thread set B: -45 degrees (top-right to bottom-left)
    diag_b = (yf - xf) / thread_width

    # Create over/under pattern: alternating which set is "on top"
    # In a 2x2 twill, each thread goes over 2, under 2
    phase_a = np.mod(diag_a, 2.0)
    phase_b = np.mod(diag_b, 2.0)

    # Thread A is "on top" when its phase < 1, thread B when phase_b < 1
    a_on_top = (phase_a < 1.0).astype(np.float32)
    b_on_top = (phase_b < 1.0).astype(np.float32)

    # Thread visibility: smooth sine wave within each thread for rounded bundle shape
    thread_a_shape = (np.sin(diag_a * np.pi) ** 2) * 0.5 + 0.5
    thread_b_shape = (np.sin(diag_b * np.pi) ** 2) * 0.5 + 0.5

    # Weave: where A is on top, show A profile; where B is on top, show B profile
    # Add subtle height difference (on-top threads are slightly brighter)
    weave = np.where(
        a_on_top > b_on_top,
        thread_a_shape * 1.0,    # A on top: full brightness
        np.where(
            b_on_top > a_on_top,
            thread_b_shape * 0.85,  # B on top but slightly different angle reflection
            (thread_a_shape + thread_b_shape) * 0.45  # intersection
        )
    )

    # Add fine noise within threads for fiber texture
    fiber_noise = multi_scale_noise(shape, [2, 4], [0.6, 0.4], seed + 8900)
    fiber_texture = np.clip(fiber_noise * 0.5 + 0.5, 0, 1) * 0.08

    # Combine into weave pattern
    weave_pattern = np.clip(weave + fiber_texture, 0, 1)

    # Darken toward carbon-black and modulate with weave pattern
    strength = pm * mask
    # Carbon is dark: darken base significantly
    dark_base = 0.12  # how dark the "under" threads are
    bright_base = 0.30  # how bright the "over" threads are

    carbon_value = dark_base + weave_pattern * (bright_base - dark_base)

    # Blend: at full pm, strong weave visible; at low pm, subtle
    for c in range(3):
        paint[:,:,c] = np.clip(
            paint[:,:,c] * (1.0 - strength * 0.7) + carbon_value * strength * 0.7,
            0, 1
        )

    return paint


def paint_pinstripe(paint, shape, mask, seed, pm, bb):
    """Pinstripe - thin regular lines lighten/darken paint."""
    h, w = shape
    y, x = get_mgrid((h, w))
    stripe = ((y % 16) < 2).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + stripe * 0.12 * pm * mask, 0, 1)
    return paint

def paint_camo_pattern(paint, shape, mask, seed, pm, bb):
    """Camo - splinter blocks shift paint toward green/tan/brown."""
    rng = np.random.RandomState(seed + 700)
    h, w = shape
    block_h, block_w = max(1, h // 16), max(1, w // 16)
    raw = rng.randint(0, 3, (block_h, block_w)).astype(np.float32)
    img = Image.fromarray((raw * 127).astype(np.uint8))
    blocks = np.array(img.resize((w, h), Image.NEAREST)).astype(np.float32) / 254.0
    # 3 camo tones: dark, medium, light
    for c in range(3):
        tone_shift = [[-0.1, 0.0, 0.05], [-0.05, 0.04, 0.06], [-0.08, -0.02, 0.0]][c]
        shift = np.where(blocks < 0.33, tone_shift[0], np.where(blocks < 0.66, tone_shift[1], tone_shift[2]))
        paint[:,:,c] = np.clip(paint[:,:,c] + shift * pm * mask, 0, 1)
    return paint

def paint_wood_grain(paint, shape, mask, seed, pm, bb):
    """Wood grain - warm directional streaks."""
    h, w = shape
    rng = np.random.RandomState(seed + 800)
    # Horizontal flowing grain
    row_grain = rng.randn(h, 1).astype(np.float32) * 0.8
    grain = np.tile(row_grain, (1, w))
    grain += rng.randn(h, w).astype(np.float32) * 0.1
    grain_val = np.clip(grain, -1, 1)
    # Warm tint (browns)
    for c in range(3):
        tint = [0.04, 0.02, -0.02][c]
        paint[:,:,c] = np.clip(paint[:,:,c] + grain_val * 0.06 * pm * mask + tint * pm * mask, 0, 1)
    return paint

def paint_snake_emboss(paint, shape, mask, seed, pm, bb):
    """Snake skin - elongated scale edge darkening."""
    h, w = shape
    y, x = get_mgrid((h, w))
    scale_w, scale_h = 12, 18
    row = y // scale_h
    sx = (x + (row % 2) * (scale_w // 2)) % scale_w
    sy = y % scale_h
    edge_x = np.minimum(sx, scale_w - sx) / (scale_w * 0.5)
    edge_y = np.minimum(sy, scale_h - sy) / (scale_h * 0.5)
    edge = np.clip(np.minimum(edge_x, edge_y) * 3, 0, 1)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - (1 - edge) * 0.08 * pm * mask, 0, 1)
    return paint

def paint_tread_darken(paint, shape, mask, seed, pm, bb):
    """Tire tread - V-groove darkening in directional pattern."""
    h, w = shape
    y, x = get_mgrid((h, w))
    groove_period = 20
    groove = np.abs(((x + y * 0.5) % groove_period) - groove_period / 2) / (groove_period / 2)
    groove = np.clip(groove, 0, 1)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - (1 - groove) * 0.10 * pm * mask, 0, 1)
    return paint

def paint_circuit_glow(paint, shape, mask, seed, pm, bb):
    """Circuit board - trace lines glow slightly."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Orthogonal grid lines
    hlines = ((y % 18) < 2).astype(np.float32)
    vlines = ((x % 24) < 2).astype(np.float32)
    traces = np.clip(hlines + vlines, 0, 1)
    for c in range(3):
        glow = [0.08, 0.12, 0.06][c]  # green-ish glow
        paint[:,:,c] = np.clip(paint[:,:,c] + traces * glow * pm * mask, 0, 1)
    return paint

def paint_mosaic_tint(paint, shape, mask, seed, pm, bb):
    """Mosaic - Voronoi cells get slight random tint shifts."""
    h, w = shape
    rng = np.random.RandomState(seed + 900)
    num_cells = 80
    cx = rng.randint(0, w, num_cells).astype(np.float32)
    cy = rng.randint(0, h, num_cells).astype(np.float32)
    tints = rng.randn(num_cells, 3).astype(np.float32) * 0.06 * pm
    y, x = get_mgrid((h, w))
    # Find nearest cell center for each pixel (downsampled for speed)
    ds = 4
    sh, sw = h // ds, w // ds
    yg = np.arange(sh).reshape(-1, 1) * ds
    xg = np.arange(sw).reshape(1, -1) * ds
    nearest = np.zeros((sh, sw), dtype=np.int32)
    min_dist = np.full((sh, sw), 1e9, dtype=np.float32)
    for i in range(num_cells):
        dist = (yg - cy[i])**2 + (xg - cx[i])**2
        closer = dist < min_dist
        nearest[closer] = i
        min_dist[closer] = dist[closer]
    nearest_img = Image.fromarray(nearest.astype(np.uint8))
    nearest_full = np.array(nearest_img.resize((w, h), Image.NEAREST))
    for c in range(3):
        shift = tints[nearest_full, c]
        paint[:,:,c] = np.clip(paint[:,:,c] + shift * mask, 0, 1)
    return paint

def paint_lava_glow(paint, shape, mask, seed, pm, bb):
    """Lava flow - hot cracks glow orange/red."""
    mn = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed+100)
    cracks = np.exp(-mn**2 * 15)
    hot = np.clip(cracks * 2, 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + hot * 0.15 * pm * mask, 0, 1)  # red glow
    paint[:,:,1] = np.clip(paint[:,:,1] + hot * 0.06 * pm * mask, 0, 1)  # slight orange
    paint[:,:,2] = np.clip(paint[:,:,2] - hot * 0.03 * pm * mask, 0, 1)  # less blue
    return paint

def paint_rain_droplets(paint, shape, mask, seed, pm, bb):
    """Rain drops - tiny bright circular highlights scattered on surface."""
    h, w = shape
    rng = np.random.RandomState(seed + 1100)
    num_drops = int(200 * pm)
    for _ in range(num_drops):
        dy, dx, dr = rng.randint(0, h), rng.randint(0, w), rng.randint(2, 5)
        y_lo = max(0, dy - dr); y_hi = min(h, dy + dr + 1)
        x_lo = max(0, dx - dr); x_hi = min(w, dx + dr + 1)
        yg, xg = np.mgrid[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((yg - dy)**2 + (xg - dx)**2)
        drop = np.clip(1.0 - dist / dr, 0, 1) ** 2
        for c in range(3):
            region = paint[y_lo:y_hi, x_lo:x_hi, c]
            m = mask[y_lo:y_hi, x_lo:x_hi]
            paint[y_lo:y_hi, x_lo:x_hi, c] = np.clip(region + drop * 0.08 * m, 0, 1)
    return paint

def paint_barbed_scratch(paint, shape, mask, seed, pm, bb):
    """Barbed wire - sharp scratch marks at regular intervals."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Diagonal slash marks
    slash = np.abs(((x - y) % 24) - 12) < 2
    barb = np.abs(((x + y) % 24) - 12) < 1
    wire = (slash | barb).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - wire * 0.10 * pm * mask, 0, 1)
    return paint

def paint_chainmail_emboss(paint, shape, mask, seed, pm, bb):
    """Chainmail - interlocking ring edge shadows."""
    h, w = shape
    y, x = get_mgrid((h, w))
    ring_size = 10
    # Offset rows of circles
    row = y // ring_size
    cx = (x + (row % 2) * (ring_size // 2)) % ring_size - ring_size // 2
    cy = y % ring_size - ring_size // 2
    dist = np.sqrt(cx.astype(np.float32)**2 + cy.astype(np.float32)**2)
    ring_edge = np.abs(dist - ring_size * 0.35) < 1.5
    ring_center = dist < ring_size * 0.25
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c]
            - ring_edge.astype(np.float32) * 0.08 * pm * mask
            + ring_center.astype(np.float32) * 0.03 * pm * mask, 0, 1)
    return paint

def paint_brick_mortar(paint, shape, mask, seed, pm, bb):
    """Brick - mortar line darkening between blocks."""
    h, w = shape
    y, x = get_mgrid((h, w))
    brick_h, brick_w = 12, 24
    row = y // brick_h
    bx = (x + (row % 2) * (brick_w // 2)) % brick_w
    by = y % brick_h
    mortar = ((bx < 2) | (by < 2)).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - mortar * 0.12 * pm * mask, 0, 1)
    return paint

def paint_leopard_spots(paint, shape, mask, seed, pm, bb):
    """Leopard - organic rosette spot darkening."""
    h, w = shape
    rng = np.random.RandomState(seed + 1200)
    num_spots = int(120 * pm)
    spot_map = np.zeros((h, w), dtype=np.float32)
    for _ in range(num_spots):
        sy, sx = rng.randint(0, h), rng.randint(0, w)
        sr = rng.randint(4, 10)
        inner_r = sr * 0.5
        y_lo = max(0, sy - sr); y_hi = min(h, sy + sr + 1)
        x_lo = max(0, sx - sr); x_hi = min(w, sx + sr + 1)
        yg, xg = np.mgrid[y_lo:y_hi, x_lo:x_hi]
        dist = np.sqrt((yg - sy)**2 + (xg - sx)**2).astype(np.float32)
        ring = ((dist > inner_r) & (dist < sr)).astype(np.float32)
        spot_map[y_lo:y_hi, x_lo:x_hi] = np.maximum(spot_map[y_lo:y_hi, x_lo:x_hi], ring)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] - spot_map * 0.12 * pm * mask, 0, 1)
    return paint

def paint_razor_slash(paint, shape, mask, seed, pm, bb):
    """Razor - diagonal slash mark brightening."""
    h, w = shape
    y, x = get_mgrid((h, w))
    dim = min(h, w)
    slash_period = max(20, dim // 50)
    slash_w = max(2, dim // 512)
    slash = ((x - y * 2) % slash_period)
    thin_slash = (slash < slash_w).astype(np.float32)
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + thin_slash * 0.10 * pm * mask, 0, 1)
    return paint

def paint_oil_slick(paint, shape, mask, seed, pm, bb):
    """Oil slick - rainbow color pools on surface."""
    h, w = shape
    y, x = get_mgrid((h, w))
    n1 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [4, 12, 24], [0.3, 0.4, 0.3], seed+200)
    hue = (n1 * 0.5 + n2 * 0.5 + 1) * 0.5  # 0-1
    strength = 0.10 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + np.sin(hue * np.pi * 2) * strength * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + np.sin(hue * np.pi * 2 + 2.094) * strength * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + np.sin(hue * np.pi * 2 + 4.189) * strength * mask, 0, 1)
    return paint

def paint_galaxy_nebula(paint, shape, mask, seed, pm, bb):
    """Galaxy - nebula clouds with color variation."""
    n1 = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed+100)
    n2 = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+200)
    nebula = np.clip((n1 + 0.3) * 1.5, 0, 1)
    strength = 0.12 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + nebula * n2 * strength * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + nebula * 0.3 * strength * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + nebula * 0.8 * strength * mask, 0, 1)
    return paint

def paint_rust_corrosion(paint, shape, mask, seed, pm, bb):
    """Rust - orange/brown oxidation patches eating through paint."""
    if pm == 0.0:
        return paint
    mn = multi_scale_noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed+100)
    rust = np.clip((mn + 0.2) * 2, 0, 1)
    strength = 0.15 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + rust * strength * 1.2 * mask, 0, 1)  # orange-red
    paint[:,:,1] = np.clip(paint[:,:,1] + rust * strength * 0.4 * mask - rust * 0.02 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - rust * strength * 0.5 * mask, 0, 1)  # remove blue
    return paint

def paint_neon_edge(paint, shape, mask, seed, pm, bb):
    """Neon glow - MASK EDGES glow bright fluorescent + large-scale glow blobs.
    v3: Uses mask gradient (zone boundaries) as edge source instead of paint
    brightness edges, which are zero on uniformly-painted cars."""
    from PIL import ImageFilter
    h, w = shape
    rng = np.random.RandomState(seed)

    # === PRIMARY: Mask edge glow (zone boundary edges) ===
    mask_img = Image.fromarray((mask * 255).astype(np.uint8))
    mask_edges_raw = np.array(mask_img.filter(ImageFilter.FIND_EDGES)).astype(np.float32) / 255.0
    # Dilate edges for wider glow band
    edge_dilated = Image.fromarray((np.clip(mask_edges_raw * 3, 0, 1) * 255).astype(np.uint8))
    edge_dilated = edge_dilated.filter(ImageFilter.GaussianBlur(radius=max(3, min(h, w) // 80)))
    mask_edges = np.array(edge_dilated).astype(np.float32) / 255.0

    # === SECONDARY: Large-scale noise glow blobs (fills interior) ===
    noise = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 200)
    noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
    glow_blobs = np.clip((noise - 0.3) * 2.5, 0, 1)

    # === COMBINE: edge glow + interior blobs ===
    combined = np.clip(mask_edges * 2.0 + glow_blobs * 0.6, 0, 1)
    glow = combined * pm * mask

    # Strong fluorescent green/cyan glow - VERY visible
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - glow * 0.3) + glow * 0.10, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - glow * 0.3) + glow * 0.85, 0, 1)  # bright green neon
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - glow * 0.3) + glow * 0.55, 0, 1)  # cyan tint

    # White-hot cores where glow is strongest
    hot_core = np.clip((combined - 0.6) * 4.0, 0, 1) * pm * mask * 0.25
    paint = np.clip(paint + hot_core[:,:,np.newaxis], 0, 1)
    return paint

def paint_weathered_peel(paint, shape, mask, seed, pm, bb):
    """Weathered paint - patches fade toward primer gray."""
    mn = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed+100)
    peel = np.clip((mn + 0.1) * 1.5, 0, 1)
    peel_strength = 0.25 * pm
    gray = 0.45  # primer gray
    for c in range(3):
        paint[:,:,c] = paint[:,:,c] * (1 - peel * peel_strength * mask) + gray * peel * peel_strength * mask
    return paint


# ================================================================
# NEW BASE PAINT FUNCTIONS (v4.0)
# ================================================================

def paint_spectraflame(paint, shape, mask, seed, pm, bb):
    """Spectraflame - Hot Wheels candy-over-chrome: deep saturated color + dense sparkle."""
    h, w = shape
    rng = np.random.RandomState(seed + 800)
    # Dense visible sparkle layer (Hot Wheels signature)
    sparkle = rng.random((h, w)).astype(np.float32)
    sparkle_bright = np.where(sparkle > 0.90, (sparkle - 0.90) * 3.0 * pm, 0.0)
    # DEEP color saturation boost (candy effect)
    gray = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    for c in range(3):
        diff = paint[:,:,c] - gray
        paint[:,:,c] = np.clip(paint[:,:,c] + diff * 0.8 * pm * mask, 0, 1)
    # Darken slightly for candy depth
    paint = np.clip(paint * (1 - 0.15 * pm * mask[:,:,np.newaxis]), 0, 1)
    # Apply sparkle on top
    paint = np.clip(paint + sparkle_bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    # Chrome brightness undertone
    paint = np.clip(paint + bb * 1.5 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_rose_gold_tint(paint, shape, mask, seed, pm, bb):
    """Rose Gold - shifts paint toward pink-gold tint."""
    # Rose gold = warm pink-gold tone
    tint_r, tint_g, tint_b = 0.85, 0.62, 0.58
    blend = 0.20 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + tint_r * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + tint_g * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + tint_b * blend * mask, 0, 1)
    # Add fine sparkle
    np.random.seed(seed + 810)
    sparkle = np.random.rand(*shape).astype(np.float32)
    sparkle = np.where(sparkle > 0.96, 1.0, 0.0) * 0.05 * pm
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    paint = np.clip(paint + bb * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_tactical_flat(paint, shape, mask, seed, pm, bb):
    """Tactical flat - Cerakote/Duracoat: desaturates + flattens toward olive-gray."""
    # Slight desaturation for military/tactical look
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.25 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    # Subtle grain texture
    np.random.seed(seed + 820)
    grain = np.random.randn(*shape).astype(np.float32) * 0.015 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# v5.0 NEW PAINT FUNCTIONS - for 50-base expansion
# ================================================================

def paint_wet_gloss(paint, shape, mask, seed, pm, bb):
    """Wet look - deepens color toward black, adds slight reflection brightening."""
    darken = 0.08 * pm
    paint = np.clip(paint * (1 - darken * mask[:,:,np.newaxis]) + bb * 0.01 * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_silk_sheen(paint, shape, mask, seed, pm, bb):
    """Silk finish - very subtle directional brightening like light on silk fabric."""
    np.random.seed(seed + 900)
    h, w = shape
    y_grad = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    silk = np.sin(y_grad * np.pi * 3) * 0.02 * pm
    paint = np.clip(paint + silk[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_patina_green(paint, shape, mask, seed, pm, bb):
    """Aged patina - shifts toward green/teal oxidation."""
    np.random.seed(seed + 910)
    noise = np.random.randn(*shape).astype(np.float32) * 0.3
    patina_mask = np.clip(noise + 0.2, 0, 1) * mask * pm * 0.12
    # Green/teal shift
    paint[:,:,0] = np.clip(paint[:,:,0] - patina_mask * 0.06, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + patina_mask * 0.04, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + patina_mask * 0.02, 0, 1)
    return paint

def paint_iridescent_shift(paint, shape, mask, seed, pm, bb):
    """Iridescent - strong rainbow hue shifts across surface based on position."""
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    x = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    angle = np.sin(y * np.pi * 4 + x * np.pi * 3) * 0.5 + 0.5
    # Strong color shifts - pm controls blend, not frequency
    blend = np.clip(pm * 0.25, 0, 1.0)
    shift_r = np.sin(angle * np.pi * 2) * 0.25
    shift_g = np.sin(angle * np.pi * 2 + 2.094) * 0.25
    shift_b = np.sin(angle * np.pi * 2 + 4.189) * 0.25
    r, g, b = paint[:,:,0].copy(), paint[:,:,1].copy(), paint[:,:,2].copy()
    paint[:,:,0] = np.clip(r + shift_r * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(g + shift_g * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(b + shift_b * blend * mask, 0, 1)
    return paint

def paint_raw_aluminum(paint, shape, mask, seed, pm, bb):
    """Raw aluminum - desaturates heavily, adds fine grain."""
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.35 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    np.random.seed(seed + 930)
    grain = np.random.randn(*shape).astype(np.float32) * 0.01 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_tinted_clearcoat(paint, shape, mask, seed, pm, bb):
    """Tinted clear - deep saturated transparent color coat, darkens + richens."""
    # Strong saturation boost (colored glass over paint)
    gray = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    for c in range(3):
        diff = paint[:,:,c] - gray
        paint[:,:,c] = np.clip(paint[:,:,c] + diff * 0.45 * pm * mask, 0, 1)
    # Darken for deep tinted glass look
    paint = np.clip(paint * (1 - 0.12 * pm * mask[:,:,np.newaxis]), 0, 1)
    # Subtle clearcoat highlight
    h, w = paint.shape[:2]
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    highlight = np.clip(1.0 - np.abs(y - 0.3) * 5, 0, 1) * 0.06 * pm
    paint = np.clip(paint + highlight[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_galvanized_speckle(paint, shape, mask, seed, pm, bb):
    """Galvanized zinc - speckled crystalline grain pattern."""
    np.random.seed(seed + 940)
    h, w = shape
    grain = np.random.randn(h // 2, w // 2).astype(np.float32) * 0.4
    grain = np.array(Image.fromarray(((grain + 2) * 64).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0 - 0.5
    paint = np.clip(paint + (grain * 0.025 * pm)[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_heat_tint(paint, shape, mask, seed, pm, bb):
    """Heat-treated titanium - blue/purple/gold tinting zones."""
    np.random.seed(seed + 950)
    h, w = shape
    noise = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 951)
    heat_val = np.clip(noise * 0.5 + 0.5, 0, 1)
    # Blue zone
    blue_mask = np.clip(1 - np.abs(heat_val - 0.3) * 5, 0, 1) * mask * pm * 0.06
    paint[:,:,2] = np.clip(paint[:,:,2] + blue_mask, 0, 1)
    # Gold zone
    gold_mask = np.clip(1 - np.abs(heat_val - 0.7) * 5, 0, 1) * mask * pm * 0.04
    paint[:,:,0] = np.clip(paint[:,:,0] + gold_mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + gold_mask * 0.6, 0, 1)
    return paint

def paint_smoked_darken(paint, shape, mask, seed, pm, bb):
    """Smoked - darkens paint uniformly like tinted lens."""
    darken = 0.15 * pm
    paint = np.clip(paint * (1 - darken * mask[:,:,np.newaxis]), 0, 1)
    return paint

def paint_diamond_sparkle(paint, shape, mask, seed, pm, bb):
    """Diamond dust - extremely fine ultra-bright point sparkles."""
    np.random.seed(seed + 960)
    h, w = shape
    sparkle = (np.random.rand(h, w).astype(np.float32) > 0.997).astype(np.float32) * 0.08 * pm
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


def paint_plasma_shift(paint, shape, mask, seed, pm, bb):
    """Plasma metal - electric purple/blue micro-shift hue injection."""
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5551)
    shift = np.clip(n * 0.5 + 0.5, 0, 1) * pm * 0.04
    paint[:,:,0] = np.clip(paint[:,:,0] + shift * 0.4 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] - shift * 0.15 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + shift * 0.5 * mask, 0, 1)
    return paint


def paint_burnt_metal(paint, shape, mask, seed, pm, bb):
    """Burnt metal - exhaust header heat discoloration, golden/blue oxide."""
    heat = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 5561)
    heat_val = np.clip(heat * 0.5 + 0.5, 0, 1)
    gold = heat_val * 0.04 * pm
    blue = (1 - heat_val) * 0.03 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] + gold * 0.6 * mask - blue * 0.1 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + gold * 0.35 * mask - blue * 0.05 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] - gold * 0.1 * mask + blue * 0.5 * mask, 0, 1)
    return paint


def paint_mercury_pool(paint, shape, mask, seed, pm, bb):
    """Mercury - liquid metal pooling effect, heavy desaturation with bright caustics."""
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.5 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    caustic = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5571)
    bright = np.clip(caustic, 0, 1) * 0.03 * pm
    paint = np.clip(paint + bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


def paint_electric_blue_tint(paint, shape, mask, seed, pm, bb):
    """Electric blue tint - icy blue metallic color push."""
    shift = 0.03 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] - shift * 0.3 * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + shift * 0.2 * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + shift * 0.5 * mask, 0, 1)
    return paint


def paint_volcanic_ash(paint, shape, mask, seed, pm, bb):
    """Volcanic ash - desaturates and darkens with gritty fine grain."""
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.3 * pm
    darken = 0.06 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask - darken * mask, 0, 1)
    np.random.seed(seed + 5590)
    grain = np.random.randn(*shape).astype(np.float32) * 0.015 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# v6.0 NEW TARGETED PAINT FUNCTIONS - precision base upgrades
# 2026-03-08: Replacing borrowed approximations on newly registered bases
# ================================================================

def paint_moonstone_adularescence(paint, shape, mask, seed, pm, bb):
    """Moonstone - internal adularescence: soft floating blue-white glow from within.
    Real moonstone has a diffuse internal scattered light (schiller effect) that
    moves as a glowing cloud beneath the surface. Not sparkle - smooth and milky."""
    h, w = shape
    # Large-scale smooth noise for the internal glow 'cloud'
    glow = multi_scale_noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 6001)
    glow = np.clip(glow * 0.5 + 0.5, 0, 1)  # 0..1
    # Adularescence is a floating blue-white billow centred on brightness peaks
    adular = np.clip((glow - 0.35) * 2.5, 0, 1) * mask * pm
    # Push toward milky blue-white (less saturation, blue-white cast)
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    milky_blend = adular * 0.40
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - milky_blend) + mean_c * milky_blend, 0, 1)
    # Cool blue-white tint on the glow cloud
    paint[:,:,0] = np.clip(paint[:,:,0] - adular * 0.04, 0, 1)   # slightly less red
    paint[:,:,1] = np.clip(paint[:,:,1] + adular * 0.02, 0, 1)   # slight cyan
    paint[:,:,2] = np.clip(paint[:,:,2] + adular * 0.07, 0, 1)   # blue lift
    return paint


def paint_opal_fire(paint, shape, mask, seed, pm, bb):
    """Stellar Dust / Nebula -- cosmic dust field with deep-space nebula colors,
    fine metallic micro-sparkle at grazing angles, and star-like point highlights.
    Purple-blue-pink nebula clouds with scattered bright star points."""
    if pm == 0.0:
        return paint
    h, w = shape
    rng = np.random.RandomState(seed + 6100)

    # --- Layer 1: Nebula gas clouds (large-scale purple-blue-pink swirls) ---
    cloud1 = multi_scale_noise(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 6101)
    cloud2 = multi_scale_noise(shape, [12, 24, 48],     [0.3, 0.4, 0.3],          seed + 6102)
    cloud3 = multi_scale_noise(shape, [6, 20, 40],      [0.2, 0.5, 0.3],          seed + 6103)

    # Normalize clouds to 0..1 range
    c1 = np.clip(cloud1 * 0.5 + 0.5, 0, 1)
    c2 = np.clip(cloud2 * 0.5 + 0.5, 0, 1)
    c3 = np.clip(cloud3 * 0.5 + 0.5, 0, 1)

    # Nebula color palette: deep purple, cosmic blue, faint pink
    # Purple regions (high c1)
    neb_r = c1 * 0.35 + c3 * 0.15   # purple + faint pink
    neb_g = c2 * 0.08                 # very little green (space is not green)
    neb_b = c1 * 0.30 + c2 * 0.25    # strong blue-purple

    # --- Layer 2: Fine metallic micro-sparkle at grazing angles ---
    # Use bb as angle proxy: sparkle appears more at grazing angles (low bb)
    sparkle_noise = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 6104)
    grazing = np.clip(1.0 - bb, 0, 1)  # high at edges/grazing angles
    micro_sparkle = np.clip(sparkle_noise * 2.0, 0, 1) ** 3.0  # sharp sparkle peaks
    sparkle_intensity = micro_sparkle * grazing * 0.25

    # --- Layer 3: Star-like point highlights scattered throughout ---
    # Generate random star positions
    num_stars = min(800, h * w // 200)
    star_field = np.zeros((h, w), dtype=np.float32)
    star_y = rng.randint(0, h, num_stars)
    star_x = rng.randint(0, w, num_stars)
    star_brightness = rng.uniform(0.4, 1.0, num_stars).astype(np.float32)
    # Place stars with small glow radius
    for sy, sx, sb in zip(star_y, star_x, star_brightness):
        r_glow = rng.randint(1, 3)
        y0 = max(0, sy - r_glow)
        y1 = min(h, sy + r_glow + 1)
        x0 = max(0, sx - r_glow)
        x1 = min(w, sx + r_glow + 1)
        star_field[y0:y1, x0:x1] = np.maximum(star_field[y0:y1, x0:x1], sb)

    # --- Combine all layers ---
    strength = pm * mask
    # Tint the base paint with nebula colors (additive blend)
    paint[:,:,0] = np.clip(paint[:,:,0] + neb_r * strength * 0.5
                           + sparkle_intensity * strength * 0.8
                           + star_field * strength * 0.6, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + neb_g * strength * 0.3
                           + sparkle_intensity * strength * 0.7
                           + star_field * strength * 0.7, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + neb_b * strength * 0.6
                           + sparkle_intensity * strength * 0.9
                           + star_field * strength * 0.9, 0, 1)
    return paint


def paint_obsidian_depth(paint, shape, mask, seed, pm, bb):
    """Obsidian - volcanic glass depth effect. Pushes paint toward absolute black with
    a subtle blue-violet edge scatter, like the way obsidian flashes colour at angles
    while reading as near-void at normal incidence."""
    # Step 1: Strong darkening - obsidian is very dark
    darken = 0.50 * pm
    paint = np.clip(paint * (1.0 - darken * mask[:,:,np.newaxis]), 0, 1)
    # Step 2: Blue-violet scatter from smooth noise (conchoidal fracture lines)
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 6201)
    scatter = np.clip(n * 0.5 + 0.5, 0, 1) * mask * pm * 0.06
    paint[:,:,0] = np.clip(paint[:,:,0] + scatter * 0.3, 0, 1)  # slight red
    paint[:,:,1] = np.clip(paint[:,:,1] - scatter * 0.1, 0, 1)  # suppress green
    paint[:,:,2] = np.clip(paint[:,:,2] + scatter * 0.7, 0, 1)  # strong blue-violet
    return paint


def paint_antique_patina(paint, shape, mask, seed, pm, bb):
    """Antique chrome patina - aged warm brown/gold oxidation, NOT green.
    Real chrome ages to warm tarnish (sulfur compounds), not the green of copper.
    Creates irregular warm patina patches with a slight dulling of the mirror."""
    n = multi_scale_noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 6301)
    patina = np.clip(n * 0.5 + 0.5, 0, 1) * mask * pm
    age_blend = patina * 0.35
    # Warm brown/amber tint target
    tint_r, tint_g, tint_b = 0.55, 0.40, 0.22
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - age_blend) + tint_r * age_blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - age_blend) + tint_g * age_blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - age_blend) + tint_b * age_blend, 0, 1)
    # Dull (desaturate) the patinated areas slightly
    mean_p = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    dull = patina * 0.15
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - dull) + mean_p * dull, 0, 1)
    return paint


def paint_glass_tint(paint, shape, mask, seed, pm, bb):
    """Tempered glass - iron-green desaturated tint of real float/tempered glass.
    Real glass has residual iron content giving a cool green tint most visible at
    edges and thick sections. Very subtle - just enough to read as 'glass' not 'clear'."""
    # Step 1: Strong desaturation (glass mutes the colour behind it)
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.55 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    # Step 2: Iron green tint (very subtle - glass green, not lime green)
    shift = pm * 0.025
    paint[:,:,0] = np.clip(paint[:,:,0] - shift * 0.4 * mask, 0, 1)  # reduce red
    paint[:,:,1] = np.clip(paint[:,:,1] + shift * 0.5 * mask, 0, 1)  # add green
    paint[:,:,2] = np.clip(paint[:,:,2] + shift * 0.2 * mask, 0, 1)  # slight cyan
    return paint


def paint_aramid_fiber(paint, shape, mask, seed, pm, bb):
    """Aramid / Kevlar - warm golden-tan push with subtle cross-woven grain.
    Kevlar and aramid are warm amber-gold, NOT dark like carbon. The woven
    texture should show as directional warm/cool alternation, not darkening."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Woven grid - horizontal and diagonal threads
    h_thread = np.abs(np.sin(y / 5.0 * np.pi)) ** 8      # tight horizontal bands
    d_thread = np.abs(np.sin((x + y * 0.5) / 5.0 * np.pi)) ** 8  # diagonal
    weave = np.clip(h_thread + d_thread, 0, 1) * mask
    # Warm golden-tan base tint
    shift = pm * 0.12
    paint[:,:,0] = np.clip(paint[:,:,0] + shift * 0.55, 0, 1)   # red/gold
    paint[:,:,1] = np.clip(paint[:,:,1] + shift * 0.38, 0, 1)   # amber
    paint[:,:,2] = np.clip(paint[:,:,2] - shift * 0.10, 0, 1)   # lose blue
    # Subtle weave lightening on thread peaks
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] + weave * 0.04 * pm, 0, 1)
    return paint


def paint_graphene_mono(paint, shape, mask, seed, pm, bb):
    """Graphene - near-neutral dark gray monochrome. Kills warm/cool casts.
    Real graphene is a perfect grayscale material - it doesn't brighten toward
    silver (like chrome_brighten would), it just becomes a very neutral dark mirror."""
    # Full desaturation to neutral gray
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.85 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    # Slight darkening (graphene is dark - not reflective silver)
    darken = 0.12 * pm
    paint = np.clip(paint * (1.0 - darken * mask[:,:,np.newaxis]), 0, 1)
    # Very faint atomic lattice shimmer (nearly invisible at render scale)
    n = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 6601)
    grain = np.clip(n * 0.5 + 0.5, 0, 1) * mask * pm * 0.015
    paint = np.clip(paint + grain[:,:,np.newaxis], 0, 1)
    return paint


def paint_rubber_absorb(paint, shape, mask, seed, pm, bb):
    """Sub black / anechoic rubber - absolute light absorption. Kills all highlights.
    Anechoic rubber tiles eat light - no sparkle, no caustics, just a matte void.
    The surface reads darker than flat_black because it actively suppresses any
    residual brightness variation."""
    # Aggressive darkening
    darken = 0.55 * pm
    paint = np.clip(paint * (1.0 - darken * mask[:,:,np.newaxis]), 0, 1)
    # Kill any remaining brightness variance (compress dynamic range toward darkness)
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    compress = 0.40 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - compress * mask) + mean_c * compress * mask, 0, 1)
    # Very subtle micro-grain for acoustic-tile texture
    np.random.seed(seed + 6701)
    grain = np.random.randn(*shape).astype(np.float32) * 0.008 * pm
    paint = np.clip(paint + grain[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


def paint_tri_coat_depth(paint, shape, mask, seed, pm, bb):
    """Tri-coat pearl depth - three-layer directional pearl layering.
    Unlike fine_sparkle (random scatter), tri-coat pearl has DIRECTIONAL depth:
    the middle pearl layer catches light at specific angles, creating a wave-like
    glow that moves across the surface. Stronger and more directional than pearl."""
    h, w = shape
    y, x = get_mgrid((h, w))
    # Layer 1: base saturation boost (the underlying metallic base coat)
    gray = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    for c in range(3):
        diff = paint[:,:,c] - gray
        paint[:,:,c] = np.clip(paint[:,:,c] + diff * 0.20 * pm * mask, 0, 1)
    # Layer 2: directional pearl wave (the mica pearl mid-coat)
    wave = np.sin(y / 40.0 * np.pi + x / 60.0 * np.pi) * 0.5 + 0.5
    wave2 = np.sin(y / 25.0 * np.pi - x / 35.0 * np.pi) * 0.5 + 0.5
    pearl_glow = np.clip(wave * wave2, 0, 1) * mask * pm * 0.12
    for c in range(3):
        tint = [1.0, 0.95, 1.05][c]  # very slight cool-white
        paint[:,:,c] = np.clip(paint[:,:,c] + pearl_glow * tint, 0, 1)
    # Layer 3: dense bright sparkle pinpoints (the top clear coat sparkle)
    np.random.seed(seed + 6801)
    sparkle = (np.random.rand(h, w).astype(np.float32) > 0.985).astype(np.float32)
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint



# ================================================================
# FOUNDATION OVERHAUL (2026) — Solid bases, NO texture/pattern, subtle spec only
# Foundation = tame backgrounds for users to build on. No grain, no bands, no stripes.
# ================================================================

def paint_f_clear_matte(paint, shape, mask, seed, pm, bb):
    # Solid matte clearcoat — diffuse only, no pattern
    diffuse = np.clip(paint + 0.04 * pm * mask[:,:,np.newaxis], 0, 1)
    return np.clip((diffuse - 0.5) * 0.85 + 0.5, 0, 1) * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_eggshell(paint, shape, mask, seed, pm, bb):
    # Solid eggshell — low luster, no grain. Slight desat only.
    gray = paint.mean(axis=2, keepdims=True)
    desat = np.clip(paint * 0.92 + gray * 0.08, 0, 1)
    return desat * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_flat_black(paint, shape, mask, seed, pm, bb):
    # Solid dead flat black — no pattern
    black = np.zeros_like(paint)
    edge = bb * 0.06 * mask
    black[:, :, 0] = edge
    black[:, :, 1] = edge
    black[:, :, 2] = edge
    return black * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_gloss(paint, shape, mask, seed, pm, bb):
    # Solid gloss — subtle contrast, very subtle spec hint (no visible stripes/ping)
    contrasted = np.clip((paint - 0.5) * 1.04 + 0.5, 0, 1)
    ping = np.clip(bb - 0.9, 0, 1) * 0.15 * pm
    return np.clip(contrasted + (ping * np.ones_like(mask))[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)

def paint_f_matte(paint, shape, mask, seed, pm, bb):
    # Solid flat matte — no pattern
    darken = np.clip(paint * 0.85, 0, 1)
    flat = np.clip((darken - 0.5) * 0.7 + 0.5, 0, 1)
    return flat * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_primer(paint, shape, mask, seed, pm, bb):
    # Solid primer grey — no grain
    gray = np.full_like(paint, 0.42)
    primer = np.clip(paint * 0.25 + gray * 0.75, 0, 1)
    return primer * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_satin(paint, shape, mask, seed, pm, bb):
    # Solid satin — no pattern
    soft = np.clip(paint * 0.97 + 0.02, 0, 1)
    return soft * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_semi_gloss(paint, shape, mask, seed, pm, bb):
    # Solid semi-gloss — no pattern
    contrasted = np.clip((paint - 0.5) * 1.02 + 0.5, 0, 1)
    return contrasted * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_silk(paint, shape, mask, seed, pm, bb):
    # Solid silk — no bands or pattern, just soft lift
    soft = np.clip(paint + 0.03 * pm * mask[:,:,np.newaxis], 0, 1)
    return soft * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_wet_look(paint, shape, mask, seed, pm, bb):
    # Solid wet look — subtle depth, no aggressive ping
    wet = np.clip(paint ** 1.1, 0, 1)
    wet = np.clip(wet + ((bb**2) * np.ones_like(mask))[:,:,np.newaxis] * 0.12 * mask[:,:,np.newaxis] * pm, 0, 1)
    return wet * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_scuffed_satin(paint, shape, mask, seed, pm, bb):
    # Solid satin (no orange peel / scuff pattern) — clean foundation
    soft = np.clip(paint * 0.96 + 0.03, 0, 1)
    return soft * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_living_matte(paint, shape, mask, seed, pm, bb):
    # Solid organic matte — no Perlin variation
    darken = np.clip(paint * 0.88, 0, 1)
    flat = np.clip((darken - 0.5) * 0.75 + 0.5, 0, 1)
    return flat * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_chalky_base(paint, shape, mask, seed, pm, bb):
    # Solid chalky flat — no texture
    gray = np.full_like(paint, 0.48)
    chalk = np.clip(paint * 0.3 + gray * 0.7, 0, 1)
    return chalk * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_f_pure_white(paint, shape, mask, seed, pm, bb):
    # Solid near-white foundation — no texture, slight brighten
    bright = np.clip(paint + 0.06 * pm * mask[:,:,np.newaxis], 0, 1)
    return bright * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])


# ================================================================
# CANDY & PEARL OVERHAUL (2026)
# ================================================================

def paint_cp_candy_burgundy(paint, shape, mask, seed, pm, bb):
    # Deep red translucent tint over a silver metallic base
    h, w = shape
    rng = np.random.RandomState(seed + 201)
    flake = rng.randn(h, w).astype(np.float32) * 0.08 * pm
    # Force base color towards a rich deep red
    base_silver = np.full_like(paint, 0.6) + flake[:,:,np.newaxis]
    candy_tint = np.zeros_like(paint)
    candy_tint[:,:,0] = 0.8  # Red
    candy_tint[:,:,1] = 0.05  # Green
    candy_tint[:,:,2] = 0.1  # Blue
    
    # Shadows are almost black-red, highlights are bright red-silver
    mix = np.clip(base_silver * candy_tint * 1.8, 0, 1)
    # Add deep specular glow
    glow = (bb**2) * 1.5 * pm
    mix[:, :, 0] = np.clip(mix[:, :, 0] + (glow * np.ones_like(mask)), 0, 1)
    return mix * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_cp_candy_cobalt(paint, shape, mask, seed, pm, bb):
    # Deep blue oceanic tint
    h, w = shape
    rng = np.random.RandomState(seed + 202)
    flake = rng.randn(h, w).astype(np.float32) * 0.08 * pm
    base_silver = np.full_like(paint, 0.6) + flake[:,:,np.newaxis]
    candy_tint = np.zeros_like(paint)
    candy_tint[:,:,0] = 0.05
    candy_tint[:,:,1] = 0.2
    candy_tint[:,:,2] = 0.9
    
    mix = np.clip(base_silver * candy_tint * 1.8, 0, 1)
    glow = (bb**2) * 1.5 * pm
    mix[:, :, 2] = np.clip(mix[:, :, 2] + (glow * np.ones_like(mask)), 0, 1)
    return mix * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_cp_candy_emerald(paint, shape, mask, seed, pm, bb):
    # Deep green tint
    h, w = shape
    rng = np.random.RandomState(seed + 203)
    flake = rng.randn(h, w).astype(np.float32) * 0.08 * pm
    base_silver = np.full_like(paint, 0.6) + flake[:,:,np.newaxis]
    candy_tint = np.zeros_like(paint)
    candy_tint[:,:,0] = 0.05
    candy_tint[:,:,1] = 0.8
    candy_tint[:,:,2] = 0.2
    
    mix = np.clip(base_silver * candy_tint * 1.8, 0, 1)
    glow = (bb**2) * 1.5 * pm
    mix[:, :, 1] = np.clip(mix[:, :, 1] + (glow * np.ones_like(mask)), 0, 1)
    return mix * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_cp_chameleon(paint, shape, mask, seed, pm, bb):
    """Dual Shift chameleon -- dramatic two-tone color shift driven by surface angle.
    Uses bb (body brightness) as viewing-angle proxy: shadows show one color,
    highlights show a completely different one, with smooth transition between."""
    if pm == 0.0:
        return paint
    h, w = shape
    mask3 = mask[:,:,np.newaxis]

    # bb is the angle proxy (0=shadow/edge, 1=highlight/direct)
    # Add subtle spatial noise so the shift isn't perfectly uniform
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 7700)
    angle_field = np.clip(bb + n * 0.15, 0, 1)

    # Two chameleon tones (relative to base paint color):
    # Shadow tone: shift toward deep teal-blue (cool)
    # Highlight tone: shift toward warm magenta-copper (warm)
    # This creates that real chameleon flip where the car looks like two different colors

    # Shadow color influence (teal-blue: R--, G+, B+)
    shadow_r = -0.25
    shadow_g =  0.10
    shadow_b =  0.20

    # Highlight color influence (magenta-copper: R+, G--, B slight)
    highlight_r =  0.20
    highlight_g = -0.20
    highlight_b =  0.08

    # Smooth cubic interpolation for premium feel (not linear)
    t = angle_field * angle_field * (3.0 - 2.0 * angle_field)  # smoothstep

    # Blend between shadow and highlight shift
    shift_r = shadow_r * (1.0 - t) + highlight_r * t
    shift_g = shadow_g * (1.0 - t) + highlight_g * t
    shift_b = shadow_b * (1.0 - t) + highlight_b * t

    # Apply shift scaled by pm and mask
    strength = pm * mask
    paint[:,:,0] = np.clip(paint[:,:,0] + shift_r * strength, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + shift_g * strength, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + shift_b * strength, 0, 1)

    # Deepen shadows slightly for that wet-candy depth chameleon paints have
    shadow_deepen = (1.0 - angle_field) * 0.15 * pm * mask
    paint[:,:,0] = np.clip(paint[:,:,0] * (1.0 - shadow_deepen), 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1.0 - shadow_deepen), 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1.0 - shadow_deepen), 0, 1)

    return paint

def paint_cp_iridescent(paint, shape, mask, seed, pm, bb):
    # Multidimensional rainbow lattice that shifts continuously
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    yf = y.astype(np.float32) * 0.02
    xf = x.astype(np.float32) * 0.02
    
    # RGB phase shifted sine waves
    r_wave = np.sin(yf + xf) * 0.5 + 0.5
    g_wave = np.sin(yf + xf + 2.094) * 0.5 + 0.5
    b_wave = np.sin(yf + xf + 4.189) * 0.5 + 0.5
    
    rainbow = np.zeros_like(paint)
    rainbow[:,:,0] = np.clip(paint[:,:,0] + r_wave * 0.4 * pm, 0, 1)
    rainbow[:,:,1] = np.clip(paint[:,:,1] + g_wave * 0.4 * pm, 0, 1)
    rainbow[:,:,2] = np.clip(paint[:,:,2] + b_wave * 0.4 * pm, 0, 1)
    return rainbow * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_cp_moonstone(paint, shape, mask, seed, pm, bb):
    # Soft milky translucent shimmer. Blue-white adularescence that glows
    moon = np.clip(paint * 0.8 + 0.1, 0, 1)
    
    # Blue-white glow in the highlight areas
    glow = np.clip(bb * 2.0, 0, 1) * pm
    moon[:,:,0] = np.clip(moon[:,:,0] + glow * 0.2, 0, 1)
    moon[:,:,1] = np.clip(moon[:,:,1] + glow * 0.4, 0, 1)
    moon[:,:,2] = np.clip(moon[:,:,2] + glow * 0.6, 0, 1)
    
    return moon * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_cp_opal(paint, shape, mask, seed, pm, bb):
    # Multi-colored large flakes under clearcoat
    h, w = shape
    rng = np.random.RandomState(seed + 207)
    # Generate chunky noise
    small = rng.rand(h // 16, w // 16).astype(np.float32) * 3.0
    from PIL import Image
    big = np.array(Image.fromarray(small).resize((w, h), Image.NEAREST))
    
    r_flake = np.sin(big) * 0.5 + 0.5
    g_flake = np.sin(big + 2.094) * 0.5 + 0.5
    b_flake = np.sin(big + 4.189) * 0.5 + 0.5
    
    base = paint.copy()
    target = base.copy()
    target[:,:,0] = np.clip(base[:,:,0] * 0.7 + r_flake * 0.5, 0, 1)
    target[:,:,1] = np.clip(base[:,:,1] * 0.7 + g_flake * 0.5, 0, 1)
    target[:,:,2] = np.clip(base[:,:,2] * 0.7 + b_flake * 0.5, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    return np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )

def paint_cp_spectraflame(paint, shape, mask, seed, pm, bb):
    # Transparent color over high-polish chrome.
    # We turn the base color into a highly saturated, highly contrasted glass coat
    # Add fake bright chrome reflections underneath
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    chrome_ref = np.clip(1.0 - np.abs(y - 0.4) * 3, 0, 1) * 0.6
    chrome_ref += np.clip(1.0 - np.abs(y - 0.7) * 4, 0, 1) * 0.3
    
    # Highly saturated user paint
    max_c = paint.max(axis=2, keepdims=True) + 1e-8
    sat_paint = paint / max_c
    
    mix = np.clip(sat_paint * (chrome_ref[:,:,np.newaxis] + 0.3) * 2.0, 0, 1)
    return mix * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_cp_tinted_clear(paint, shape, mask, seed, pm, bb):
    # Deep tinted clearcoat tracking the base color explicitly
    # Very dark off-angles, high color transmission in highlights
    intensity = np.clip(bb + 0.2, 0, 1) * pm
    
    tinted = np.zeros_like(paint)
    tinted[:,:,0] = np.clip(paint[:,:,0] * intensity * 2.0, 0, 1)
    tinted[:,:,1] = np.clip(paint[:,:,1] * intensity * 2.0, 0, 1)
    tinted[:,:,2] = np.clip(paint[:,:,2] * intensity * 2.0, 0, 1)
    
    return tinted * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])

def paint_cp_tri_coat_pearl(paint, shape, mask, seed, pm, bb):
    # 3-stage pearl. Adds a pearlescent mica layer (usually gold/silver/blue tint) over base.
    # Then clears.
    h, w = shape
    rng = np.random.RandomState(seed + 210)
    mica = rng.randn(h, w).astype(np.float32) * 0.12 * pm
    
    # White/Gold mica shift
    shift_r = mica * 1.5
    shift_g = mica * 1.3
    shift_b = mica * 0.9
    
    tri = np.zeros_like(paint)
    tri[:,:,0] = np.clip(paint[:,:,0] + shift_r * mask, 0, 1)
    tri[:,:,1] = np.clip(paint[:,:,1] + shift_g * mask, 0, 1)
    tri[:,:,2] = np.clip(paint[:,:,2] + shift_b * mask * mask, 0, 1)
    
    # Glaze highlight
    glaze = (bb**2) * 0.4 * pm
    tri = np.clip(tri + (glaze * np.ones_like(mask))[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return tri * mask[:,:,np.newaxis] + paint * (1 - mask[:,:,np.newaxis])




# ================================================================
# CARBON & COMPOSITE OVERHAUL (2026)
# ================================================================

# --- PAINT MODIFIERS ---
def paint_cc_carbon(paint, shape, mask, seed, pm, bb):
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    # Simple 2x2 Twill Weave math
    weave = (np.sin(y * 0.4 + np.sin(x * 0.4)) * np.cos(x * 0.4 - np.cos(y * 0.4))) * 0.5 + 0.5
    # Darken paint to deep carbon grey/black but keep a tiny bit of user tint
    carbon_tint = np.clip(paint * 0.15 + 0.05, 0, 1)
    
    # Highlights clip
    glow = (bb**2) * 2.0 * pm
    
    mix = np.clip(carbon_tint + (weave * 0.2 + glow) * mask[:, :, np.newaxis], 0, 1)
    return mix * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis])

def paint_cc_forged(paint, shape, mask, seed, pm, bb):
    h, w = shape
    rng = np.random.RandomState(seed + 301)
    # Voronoi/cellular noise approximation for chopped geometric chunks
    n1 = _noise(shape, [16, 32], [0.5, 0.5], seed + 302)
    n2 = _noise(shape, [8, 16], [0.5, 0.5], seed + 303)
    chunks = np.clip((np.sin(n1 * 20.0) * np.cos(n2 * 20.0)) * 0.5 + 0.5, 0, 1)
    
    carbon_tint = np.clip(paint * 0.1 + 0.1, 0, 1)
    glow = (bb**2) * 1.5 * pm
    
    mix = np.clip(carbon_tint + (chunks * 0.3 + glow) * mask[:, :, np.newaxis], 0, 1)
    return mix * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis])

def paint_cc_fiberglass(paint, shape, mask, seed, pm, bb):
    h, w = shape
    # Chopped strand mat
    strands = _noise(shape, [8, 16, 32], [0.6, 0.3, 0.1], seed + 304)
    # User paint defines the resin tint color
    resin = np.clip(paint * 0.85 + strands[:, :, np.newaxis] * 0.15 * mask[:, :, np.newaxis], 0, 1)
    glow = (bb**3) * 1.0 * pm
    return np.clip(resin + glow[:, :, np.newaxis], 0, 1) * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis])

def paint_cc_aramid(paint, shape, mask, seed, pm, bb):
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    # Tight Kevlar/Aramid weave
    weave = (np.sin(y * 1.2) * np.cos(x * 1.2)) * 0.5 + 0.5
    
    # Mix user paint with a golden-yellow aramid base tint
    aramid_base = np.zeros_like(paint)
    aramid_base[:,:,0] = 0.8
    aramid_base[:,:,1] = 0.6
    aramid_base[:,:,2] = 0.1
    
    mix = np.clip(paint * 0.4 + aramid_base * 0.6, 0, 1)
    mix = np.clip(mix * (0.6 + weave[:, :, np.newaxis] * 0.4), 0, 1)
    return mix * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis])

def paint_cc_graphene(paint, shape, mask, seed, pm, bb):
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    # Hexagonal atomic grid representation
    yf = y.astype(np.float32)
    xf = x.astype(np.float32)
    s = 4.0
    hex_grid = np.abs(np.sin(yf * s) + np.sin((yf * 0.5 + xf * 0.866) * s) + np.sin((yf * 0.5 - xf * 0.866) * s)) / 3.0
    
    # Extremely dark core
    core = np.clip(paint * 0.05, 0, 1)
    glow = (bb**2) * 3.0 * pm # Highly reflective
    
    mix = np.clip(core + (hex_grid * 0.5 + glow)[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    return mix * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis])


# --- SPEC MODIFIERS ---
def spec_cc_carbon(shape, seed, sm, base_m, base_r):
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    weave = (np.sin(y * 0.4 + np.sin(x * 0.4)) * np.cos(x * 0.4 - np.cos(y * 0.4))) * 0.5 + 0.5
    
    M_arr = np.full(shape, base_m, dtype=np.float32) + weave * 50.0 * sm
    R_arr = np.full(shape, base_r, dtype=np.float32) - weave * 30.0 * sm
    CC_arr = np.full(shape, 16.0, dtype=np.float32) # Coated carbon
    return M_arr, R_arr, CC_arr

def spec_cc_carbon_ceramic(shape, seed, sm, base_m, base_r):
    h, w = shape
    noise = _noise(shape, [4, 8, 16], [0.5, 0.3, 0.2], seed + 310)
    # Porous, metallic-flake embedded raw rotor material
    M_arr = np.full(shape, 120.0, dtype=np.float32) + noise * 60.0 * sm
    R_arr = np.full(shape, 25.0, dtype=np.float32) + noise * 150.0 * sm
    CC_arr = np.full(shape, 0.0, dtype=np.float32) # No clearcoat on rotors
    return M_arr, R_arr, CC_arr

def spec_cc_forged(shape, seed, sm, base_m, base_r):
    h, w = shape
    n1 = _noise(shape, [16, 32], [0.5, 0.5], seed + 302)
    n2 = _noise(shape, [8, 16], [0.5, 0.5], seed + 303)
    chunks = np.clip((np.sin(n1 * 20.0) * np.cos(n2 * 20.0)) * 0.5 + 0.5, 0, 1)
    
    M_arr = np.full(shape, base_m, dtype=np.float32) + chunks * 60.0 * sm
    R_arr = np.full(shape, base_r, dtype=np.float32) - chunks * 20.0 * sm
    CC_arr = np.full(shape, 16.0, dtype=np.float32)
    return M_arr, R_arr, CC_arr


# ================================================================
# CERAMIC & GLASS OVERHAUL (2026)
# ================================================================

# --- PAINT MODIFIERS ---
def paint_cg_obsidian(paint, shape, mask, seed, pm, bb):
    h, w = shape
    # Volcanic glass with sharp chipped conchoidal fractures
    n1 = _noise(shape, [32, 64], [0.7, 0.3], seed + 401)
    fractures = np.clip(np.abs(np.sin(n1 * 15.0)), 0, 1)
    
    # Deep violent black with a purple/blue micro-tint
    obsidian_base = np.zeros_like(paint)
    obsidian_base[:,:,0] = 0.02
    obsidian_base[:,:,1] = 0.01
    obsidian_base[:,:,2] = 0.05
    
    # Highlights gather on fractures
    glow = (bb**4) * 2.0 * pm * (1.0 - fractures * 0.8)
    
    mix = np.clip(obsidian_base + glow[:, :, np.newaxis], 0, 1)
    return mix * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis])

def paint_cg_crystal(paint, shape, mask, seed, pm, bb):
    # Perfect clear optical transmission, enhances user paint saturation heavily
    sat_paint = paint / (paint.max(axis=2, keepdims=True) + 1e-8)
    crystal = np.clip(sat_paint * 0.8 + paint * 0.4, 0, 1)
    
    # Sharp glass ping highlight
    glow = (bb**5) * 2.5 * pm
    crystal = np.clip(crystal + glow[:, :, np.newaxis] * mask[:, :, np.newaxis], 0, 1)
    return crystal * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis])

def paint_cg_porcelain(paint, shape, mask, seed, pm, bb):
    h, w = shape
    # Milky ceramic with microscopic crackle
    crackle = np.clip(1.0 - np.abs(_noise(shape, [16, 32], [0.5, 0.5], seed + 402) - 0.5) * 50.0, 0, 1)
    
    # Desaturate slightly, milkify
    gray = paint.mean(axis=2, keepdims=True)
    milky = np.clip(paint * 0.7 + gray * 0.2 + 0.1, 0, 1)
    
    # Cracks are dark
    milky = np.clip(milky - (crackle * 0.4)[:, :, np.newaxis], 0, 1)
    
    return milky * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis])


# --- SPEC MODIFIERS ---
def spec_cg_obsidian(shape, seed, sm, base_m, base_r):
    h, w = shape
    n1 = _noise(shape, [32, 64], [0.7, 0.3], seed + 401)
    fractures = np.clip(np.abs(np.sin(n1 * 15.0)), 0, 1)
    
    # Sharp edges disrupt roughness
    M_arr = np.full(shape, 20.0, dtype=np.float32) + fractures * 50.0 * sm
    R_arr = np.full(shape, 4.0, dtype=np.float32) + fractures * 30.0 * sm
    CC_arr = np.full(shape, 16.0, dtype=np.float32)
    return M_arr, R_arr, CC_arr

def spec_cg_porcelain(shape, seed, sm, base_m, base_r):
    h, w = shape
    crackle = np.clip(1.0 - np.abs(_noise(shape, [16, 32], [0.5, 0.5], seed + 402) - 0.5) * 50.0, 0, 1)
    
    # Crackles break the clearcoat
    M_arr = np.full(shape, 0.0, dtype=np.float32)
    R_arr = np.full(shape, 8.0, dtype=np.float32) + crackle * 100.0 * sm
    CC_arr = np.full(shape, 16.0, dtype=np.float32) - crackle * 16.0 * sm
    return M_arr, R_arr, CC_arr

def spec_cg_glass(shape, seed, sm, base_m, base_r):
    # Flawless mirror spec map without metallic reflectivity
    M_arr = np.full(shape, 0.0, dtype=np.float32)
    R_arr = np.full(shape, 0.0, dtype=np.float32) # Perfect smooth
    CC_arr = np.full(shape, 16.0, dtype=np.float32) # Factory clear
    return M_arr, R_arr, CC_arr

# ======================================================================
# 2026 MASS UPGRADE NEW FUNCTIONS
# ======================================================================

def paint_liquid_metal_flow_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import get_mgrid
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid(shape)
    flow = np.sin(x * 0.15 + np.sin(y * 0.08) * 3.0) * 0.5 + 0.5
    flow = np.clip((flow + 1.0) * 0.5, 0, 1).astype(np.float32)
    base = paint.copy()
    gray = base.mean(axis=2, keepdims=True)
    target = np.clip(base * 0.5 + gray * 0.5 + flow[:,:,np.newaxis] * 0.15, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.05 * mask * blend, 0, 1)
    return np.clip(paint + bb * 0.6 * mask[:,:,np.newaxis], 0, 1)

def spec_exotic_metal(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise, get_mgrid
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid(shape)
    flow = np.sin(x * 0.15 + np.sin(y * 0.08) * 3.0) * 0.5 + 0.5
    grain = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed)
    M = np.clip(180 + flow * 75.0, 0, 255).astype(np.float32)
    R = np.clip(5 + grain * 25.0, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 16.0, dtype=np.float32)  # CC=16 max clearcoat for exotic metals

def paint_tungsten_heavy(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    base = paint.copy()
    gray = base.mean(axis=2, keepdims=True)
    target = base.copy()
    target[:,:,0] = np.clip(base[:,:,0] * 0.6 + gray[:,:,0] * 0.2, 0, 1)
    target[:,:,1] = np.clip(base[:,:,1] * 0.6 + gray[:,:,0] * 0.2, 0, 1)
    target[:,:,2] = np.clip(base[:,:,2] * 0.6 + gray[:,:,0] * 0.35 + 0.05, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    flake = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed)
    return np.clip(paint + flake[:,:,np.newaxis] * 0.08 * blend * mask[:,:,np.newaxis] + bb * 0.3, 0, 1)

def paint_oem_metallic_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    flake1 = multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed+1)
    flake2 = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed+5)
    pearl = np.clip((flake1 * 0.7 + flake2 * 0.3), 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + pearl * 0.08 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + pearl * 0.08 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + pearl * 0.12 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.5, 0, 1)

def spec_oem_automotive(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    peel = multi_scale_noise(shape, [16, 32], [0.7, 0.3], seed)
    M = np.clip(30 + peel * 10.0, 0, 255).astype(np.float32)
    R = np.clip(45 + peel * 20.0, 0, 255).astype(np.float32)
    CC = np.clip(32 - peel * 16.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_mil_spec_od_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * 0.4 + gray * 0.4
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.15*pm*mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.16*pm*mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.05*pm*mask, 0, 1)
    grime = multi_scale_noise(shape, [8, 16], [0.6, 0.4], seed)
    paint = np.clip(paint - grime[:,:,np.newaxis]*0.05*pm*mask[:,:,np.newaxis], 0, 1)
    return np.clip(paint + bb * 0.2, 0, 1)

def spec_industrial_tactical(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    grit = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], seed)
    M = np.clip(5 + grit * 40.0, 0, 255).astype(np.float32)
    R = np.clip(170 + grit * 85.0, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 180.0, dtype=np.float32)  # CC=180 dead flat military/tactical

def paint_matte_wrap_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from scipy.ndimage import gaussian_filter
    base = paint.copy()
    smoothed = gaussian_filter(base, sigma=[2, 2, 0])
    target = base * 0.2 + smoothed * 0.8
    blend = np.clip(pm, 0.0, 1.0)
    paint = base * (1.0 - mask[:, :, np.newaxis] * blend) + target * (mask[:, :, np.newaxis] * blend)
    return np.clip(paint + bb * 0.15, 0, 1)

def spec_satin_wrap(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    ripple = multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed)
    M = np.clip(10 + ripple * 5.0, 0, 255).astype(np.float32)
    R = np.clip(120 + ripple * 20.0, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 60.0, dtype=np.float32)  # CC=60 satin wrap coating

def paint_sun_fade_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    base = paint.copy()
    damage = multi_scale_noise(shape, [16,32,64], [0.4, 0.4, 0.2], seed)
    pre = np.clip(base + damage[:,:,np.newaxis] * 0.15, 0, 1)
    gray = pre.mean(axis=2, keepdims=True)
    target = np.clip(pre * 0.6 + gray * 0.4, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    return np.clip(paint + bb * 0.2, 0, 1)

def spec_weathered_aged(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    rot = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.3, 0.3], seed)
    M = np.where(rot > 0.6, 90.0, 15.0).astype(np.float32)
    R = np.where(rot > 0.6, 220.0, 90.0).astype(np.float32)
    CC = np.where(rot < 0.4, 24.0, 0.0).astype(np.float32)
    return M, R, CC

def paint_race_day_gloss_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    paint = np.clip(paint * 1.1, 0, 1)
    dust = multi_scale_noise(shape, [2,4,8], [0.5, 0.3, 0.2], seed+1)
    dust_mask = np.where(dust > 0.8, 1, 0).astype(np.float32)
    paint = np.clip(paint - dust_mask[:,:,np.newaxis]*0.3*mask[:,:,np.newaxis]*pm, 0, 1)
    return np.clip(paint + bb * 0.7, 0, 1)

def spec_racing_heritage(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    scuff = multi_scale_noise(shape, [2, 4, 8], [0.4, 0.4, 0.2], seed)
    M = np.clip(100 - scuff * 80.0, 0, 255).astype(np.float32)
    R = np.clip(15 + scuff * 200.0, 0, 255).astype(np.float32)
    CC = np.clip(32 - scuff * 32.0, 0, 255).astype(np.float32)
    return M, R, CC

def paint_quantum_black_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    base = paint.copy()
    dark_target = np.clip(base * 0.02, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        dark_target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    flux = multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed)
    glow = np.where(flux > 0.95, 1, 0).astype(np.float32)
    paint[:,:,2] = np.clip(paint[:,:,2] + glow * 0.4 * blend * mask, 0, 1)
    return np.clip(paint + bb * 0.05, 0, 1)

def spec_extreme_experimental(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    void = multi_scale_noise(shape, [1, 2, 4], [0.33, 0.33, 0.34], seed+99)
    M = np.where(void > 0.8, 255.0, 0.0).astype(np.float32)
    R = np.where(void > 0.8, 0.0, 255.0).astype(np.float32)
    CC = np.where(void > 0.95, 255.0, 0.0).astype(np.float32)
    return M, R, CC

def paint_bentley_silver_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    base = paint.copy()
    gray = base.mean(axis=2, keepdims=True)
    target = gray * 0.10 + 0.90
    silver = base.copy()
    for c in range(3):
        silver[:,:,c] = np.clip(base[:,:,c] * 0.5 + target[:,:,0] * 0.5, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        silver * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    flake = multi_scale_noise(shape, [1,2], [0.7,0.3], seed)
    return np.clip(paint + flake[:,:,np.newaxis]*0.05*mask[:,:,np.newaxis]*blend + bb*0.8, 0, 1)

def spec_premium_luxury(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    flake = multi_scale_noise(shape, [1, 2], [0.8, 0.2], seed)
    M = np.clip(180 + flake * 75.0, 0, 255).astype(np.float32)
    R = np.clip(5 + flake * 5.0, 0, 255).astype(np.float32)
    CC = np.full(shape, 255.0, dtype=np.float32) 
    return M, R, CC

def spec_metallic_standard(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    flake = multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed+1)
    M = np.clip(120 + flake * 80.0, 0, 255).astype(np.float32)
    R = np.clip(30 - flake * 15.0, 0, 255).astype(np.float32)
    CC = np.full(shape, 24.0, dtype=np.float32)
    return M, R, CC



def spec_brushed_grain(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    
    h, w = shape
    rng = np.random.RandomState(seed + 900)
    
    # Base directional streak (high frequency)
    base_streak = np.tile(rng.randn(1, w).astype(np.float32), (h, 1))
    
    # Blur vertically to create smooth brush lines instead of noise
    from scipy.ndimage import gaussian_filter1d
    base_streak = gaussian_filter1d(base_streak, sigma=15.0, axis=0) # Smooth vertical
    base_streak = gaussian_filter1d(base_streak, sigma=0.5, axis=1) # Tiny horizontal blend
    
    # Normalize the streak
    streak_min = base_streak.min()
    streak_max = base_streak.max()
    if streak_max > streak_min:
        base_streak = (base_streak - streak_min) / (streak_max - streak_min)
    else:
        base_streak = np.zeros_like(base_streak)
        
    # Introduce micro-wobble so lines aren't perfectly straight
    wobble = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed) * 0.1
    base_streak = np.clip(base_streak + wobble, 0, 1)

    # Some very fine grit
    grit = rng.randn(h, w).astype(np.float32) * 0.05
    
    final_grain = np.clip(base_streak + grit, 0, 1)
    
    M_arr = np.full(shape, base_m, dtype=np.float32) + (final_grain - 0.5) * 40.0 * sm
    R_arr = np.full(shape, base_r, dtype=np.float32) - (final_grain - 0.5) * 60.0 * sm
    CC_arr = np.full(shape, 16.0, dtype=np.float32)  # CC=16 max clearcoat for brushed metals
    return M_arr, R_arr, CC_arr

def spec_liquid_titanium(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise, get_mgrid
    
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    
    # Pure fluid dynamics - flowing vortexes of metallic density (mercury)
    flow1 = np.sin(x / 45.0 + np.cos(y / 35.0) * 2.0)
    flow2 = np.cos(y / 55.0 + np.sin(x / 25.0) * 1.5)
    swirl = (flow1 * flow2) * 0.5 + 0.5
    
    depth = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed)
    
    combined = np.clip(swirl * 0.7 + depth * 0.3, 0, 1)
    
    M = np.clip(base_m - (1.0 - combined) * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + (1.0 - combined) * 20.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat

def spec_cobalt_metal(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Crystalline, fragmented geometric interference
    n1 = multi_scale_noise((h, w), [8, 16], [0.7, 0.3], seed + 101)
    n2 = multi_scale_noise((h, w), [12, 24], [0.5, 0.5], seed + 102)
    
    crystal = np.clip(np.abs(np.sin(n1 * 15.0) + np.cos(n2 * 20.0)) * 0.6, 0, 1)
    grain = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 103)
    
    M = np.clip(base_m + crystal * 50.0 * sm - grain * 15.0, 0, 255).astype(np.float32)
    R = np.clip(base_r + crystal * 35.0 * sm + grain * 25.0, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat

def spec_tungsten_metal(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Extremely heavy, ultra-dense coarse granular grain - NO wavy shapes
    grain = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 201)
    
    pits = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 202)
    pitting = np.where(pits > 0.8, (pits - 0.8) * 5.0, 0.0)
    
    overall = np.clip(grain + pitting, 0, 1)
    
    M = np.clip(base_m - pitting * 80.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + overall * 60.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 16.0, dtype=np.float32)  # CC=16 max clearcoat

def spec_platinum_metal(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Extremely dense, warm, thick mirror. Rolling cloudy spec depth but no grain/no hard pits.
    cloud = multi_scale_noise((h, w), [32, 64, 128], [0.4, 0.4, 0.2], seed + 301)
    
    M = np.clip(base_m - cloud * 25.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + cloud * 8.0 * sm, 0, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # Registry says CC=16
    return M, R, CC



# --- EXTREME & EXPERIMENTAL CUSTOM MATH ---

def paint_bioluminescent(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    n = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 501)
    cells = np.clip(1.0 - np.abs(n), 0, 1) ** 3.0
    gray = paint.mean(axis=2, keepdims=True)
    ambient = paint * 0.4 + gray * 0.4
    max_c = paint.max(axis=2, keepdims=True) + 1e-8
    glow_color = paint / max_c
    glow = cells * 0.8 * pm * mask
    mix = np.clip(ambient + glow_color * glow[:, :, np.newaxis], 0, 1)
    return mix * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis])

def spec_bioluminescent(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    M = np.full(shape, 0.0, dtype=np.float32)
    n = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 502)
    R = np.clip(10.0 + n * 20.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 16.0, dtype=np.float32)

def paint_dark_matter(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise, get_mgrid
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    base = paint.copy()
    core = np.clip(base * 0.05, 0, 1)
    n1 = multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 601)
    n2 = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 602)
    swirl = np.clip((n1 * np.cos(n2 * 3.0)) * 0.5 + 0.5, 0, 1)
    r_shift = np.sin(swirl * 10.0) * 0.5 + 0.5
    g_shift = np.sin(swirl * 10.0 + 2.094) * 0.5 + 0.5
    b_shift = np.sin(swirl * 10.0 + 4.189) * 0.5 + 0.5
    shift_color = np.stack([r_shift, g_shift, b_shift], axis=2)
    blend = np.clip(pm, 0.0, 1.0)
    dark_mix = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        core * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    reveal = (bb ** 2) * 2.0 * blend * mask
    mix = np.clip(dark_mix + shift_color * reveal[:, :, np.newaxis] * swirl[:, :, np.newaxis], 0, 1)
    return mix * mask[:, :, np.newaxis] + base * (1 - mask[:, :, np.newaxis])

def spec_dark_matter(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    swirl = multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 601)
    swirl = np.clip(swirl * 0.5 + 0.5, 0, 1)
    M = np.clip(swirl * 255.0 * sm, 0, 255).astype(np.float32)
    R = np.where(swirl > 0.6, 10.0, 240.0).astype(np.float32)
    return M, R, np.full(shape, 220.0, dtype=np.float32)  # CC=220 dull dark swirl (was 0=mirror)

def paint_black_hole_accretion(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    n = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 701)
    base = paint.copy()
    core = np.zeros_like(base)
    rings = np.abs(np.sin((bb * 50.0) + n * 2.0))
    blend = np.clip(pm, 0.0, 1.0)
    glow_mask = np.clip((bb ** 1.5) * 3.0 * rings * blend, 0, 1) * mask
    max_c = base.max(axis=2, keepdims=True) + 1e-8
    hot_color = base / max_c
    hot_color[:,:,0] = np.clip(hot_color[:,:,0] + 0.5, 0, 1)
    hot_color[:,:,1] = np.clip(hot_color[:,:,1] + 0.2, 0, 1)
    dark_mix = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        core * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    mix = np.clip(dark_mix + hot_color * glow_mask[:, :, np.newaxis], 0, 1)
    return mix * mask[:, :, np.newaxis] + base * (1 - mask[:, :, np.newaxis])
    
def spec_black_hole_accretion(shape, seed, sm, base_m, base_r):
    import numpy as np
    M = np.full(shape, 255.0, dtype=np.float32)
    R = np.full(shape, 255.0, dtype=np.float32)
    CC = np.full(shape, 255.0, dtype=np.float32)
    return M, R, CC

def paint_quantum_black(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    base = paint.copy()
    void = np.zeros_like(base)
    sparkle = (multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed + 801) > 0.98).astype(np.float32)
    blend = np.clip(pm, 0.0, 1.0)
    shimmer = sparkle * 0.8 * blend * mask
    dark_mix = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        void * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    mix = np.clip(dark_mix + shimmer[:, :, np.newaxis], 0, 1)
    return mix * mask[:, :, np.newaxis] + base * (1 - mask[:, :, np.newaxis])

def spec_quantum_black(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    M = np.zeros(shape, dtype=np.float32)
    R = np.full(shape, 255.0, dtype=np.float32)
    sparkle = (multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed + 801) > 0.98).astype(np.float32)
    M = np.where(sparkle > 0, 255.0, M)
    R = np.where(sparkle > 0, 0.0, R)
    return M, R, np.full(shape, 240.0, dtype=np.float32)  # CC=240 void dull (was 0=mirror)

def paint_absolute_zero(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    n1 = multi_scale_noise(shape, [4, 8], [0.6, 0.4], seed + 901)
    n2 = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 902)
    frost = np.clip(np.abs(np.sin(n1 * 20.0) + np.cos(n2 * 20.0)), 0, 1)
    base = paint.copy()
    mean_c = base.mean(axis=2, keepdims=True)
    frozen = np.clip(base * 0.3 + mean_c * 0.7 + 0.1, 0, 1)
    frozen[:,:,0] = np.clip(frozen[:,:,0] - 0.1, 0, 1)
    frozen[:,:,2] = np.clip(frozen[:,:,2] + 0.1, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    cold_mix = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        frozen * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    glow = (bb ** 1.5) * 2.0 * blend * frost * mask
    mix = np.clip(cold_mix + glow[:, :, np.newaxis], 0, 1)
    return mix * mask[:, :, np.newaxis] + base * (1 - mask[:, :, np.newaxis])

def spec_absolute_zero(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    n1 = multi_scale_noise(shape, [4, 8], [0.6, 0.4], seed + 901)
    n2 = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 902)
    frost = np.clip(np.abs(np.sin(n1 * 20.0) + np.cos(n2 * 20.0)), 0, 1)
    M = np.clip(base_m + frost * 100.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r - frost * 80.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 40.0, dtype=np.float32)



# --- SOLAR PANEL, HOLOGRAPHIC, PLASMA CORE ---

def paint_solar_panel(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import get_mgrid
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    blend = np.clip(pm, 0.0, 1.0)
    target = base.copy()
    target[:,:,0] = np.clip(base[:,:,0] * 0.2 + 0.05, 0, 1)
    target[:,:,1] = np.clip(base[:,:,1] * 0.2 + 0.08, 0, 1)
    target[:,:,2] = np.clip(base[:,:,2] * 0.4 + 0.25, 0, 1)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Visible photovoltaic grid lines
    y, x = get_mgrid((h, w))
    cell_size = 40
    grid_h = (y % cell_size < 2).astype(np.float32)
    grid_v = (x % cell_size < 2).astype(np.float32)
    grid = np.maximum(grid_h, grid_v)
    
    # Grid lines are silver bus-bars
    paint[:,:,0] = np.clip(paint[:,:,0] + grid * 0.25 * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + grid * 0.25 * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + grid * 0.25 * mask * blend, 0, 1)
    return paint

def spec_solar_panel(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import get_mgrid
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    cell_size = 40
    grid_h = (y % cell_size < 2).astype(np.float32)
    grid_v = (x % cell_size < 2).astype(np.float32)
    grid = np.maximum(grid_h, grid_v)
    
    # High metallic on the silver lines, dielectric on the dark blue cells
    M = np.where(grid > 0, 240.0, 15.0).astype(np.float32)
    R = np.where(grid > 0, 10.0, 45.0).astype(np.float32)
    return M, R, np.full((h, w), 16.0, dtype=np.float32)


def paint_holographic_base(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise, get_mgrid
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))

    # Multi-scale angle field for hue rotation
    angle_field = (x * 0.03 + y * 0.02)  
    noise_perturb = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 3000)
    angle_field = angle_field + noise_perturb * 1.5

    # Generate massive RGB hue bands 
    r_band = (np.sin(angle_field) * 0.5 + 0.5).astype(np.float32)
    g_band = (np.sin(angle_field + 2.094) * 0.5 + 0.5).astype(np.float32)
    b_band = (np.sin(angle_field + 4.189) * 0.5 + 0.5).astype(np.float32)
    
    # It aggressively forces rainbow holographic foils, over-writing most of the base color
    blend = 0.85 * pm
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - mask * blend) + r_band * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - mask * blend) + g_band * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - mask * blend) + b_band * mask * blend, 0, 1)
    return paint

def spec_holographic_base(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    # Foil-like grain
    grain = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + 3001)
    grain = np.clip(grain, 0, 1)
    
    M = np.clip(200.0 + grain * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(6.0 + grain * 15.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 16.0, dtype=np.float32)


def paint_plasma_core(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import get_mgrid
    h, w = shape[:2] if len(shape) > 2 else shape
    
    base = paint.copy()
    blend = np.clip(pm, 0.0, 1.0)
    target = base.copy()
    target[:,:,0] = np.clip(base[:,:,0] * 0.4 + 0.55, 0, 1)
    target[:,:,1] = np.clip(base[:,:,1] * 0.2 + 0.10, 0, 1)
    target[:,:,2] = np.clip(base[:,:,2] * 0.4 + 0.80, 0, 1)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Plasma veins that snake across surface
    y, x = get_mgrid((h,w))
    vein1 = np.sin(x * 0.06 + np.sin(y * 0.04) * 4.0) * 0.5 + 0.5
    vein2 = np.sin(y * 0.05 + np.sin(x * 0.03) * 5.0) * 0.5 + 0.5
    veins = np.clip(vein1 * vein2, 0, 1).astype(np.float32)
    hot_veins = np.where(veins > 0.7, (veins - 0.7) / 0.3, 0).astype(np.float32)
    
    # Veins glow bright magenta-white
    paint[:,:,0] = np.clip(paint[:,:,0] + hot_veins * 0.6 * blend * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + hot_veins * 0.2 * blend * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + hot_veins * 0.4 * blend * mask, 0, 1)
    return paint

def spec_plasma_core(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import get_mgrid
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h,w))
    
    vein1 = np.sin(x * 0.06 + np.sin(y * 0.04) * 4.0) * 0.5 + 0.5
    vein2 = np.sin(y * 0.05 + np.sin(x * 0.03) * 5.0) * 0.5 + 0.5
    veins = np.clip(vein1 * vein2, 0, 1).astype(np.float32)
    hot_veins = np.where(veins > 0.7, (veins - 0.7) / 0.3, 0).astype(np.float32)
    
    # The veins themselves are intensely metallic and zero roughness. The outer void area is rougher.
    M = np.clip(base_m + hot_veins * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + (1.0 - hot_veins) * 20.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 30.0, dtype=np.float32)  # CC=30 semi-gloss plasma (was 0=mirror)



# ======================================================================
# UNIQUE TACTICAL & INDUSTRIAL PHYSICS
# ======================================================================

def paint_armor_plate_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    # Make it dark heavy steel
    base = paint.copy()
    gray = base.mean(axis=2, keepdims=True)
    target = np.clip(base * 0.2 + gray * 0.4 + 0.1, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Heavy rolling marks/scratches in the metal
    marks = multi_scale_noise((h, w), [4, 16], [0.7, 0.3], seed + 50)
    
    # Very slight green/brown oxidation in the recesses
    rust = np.where(marks < 0.3, 0.1, 0.0).astype(np.float32)
    paint[:,:,0] = np.clip(paint[:,:,0] + rust * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + rust * 0.5 * mask * blend, 0, 1)
    
    paint = np.clip(paint - (1.0 - marks)[:,:,np.newaxis] * 0.15 * mask[:,:,np.newaxis] * blend, 0, 1)
    return np.clip(paint + bb * 0.2, 0, 1)

def spec_armor_plate_v2(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    marks = multi_scale_noise((h, w), [4, 16], [0.7, 0.3], seed + 50)
    
    # Exposed steel is highly metallic, oxidized/recessed areas are rough and less metallic
    M = np.clip(60.0 + marks * 140.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(160.0 - marks * 80.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 130.0, dtype=np.float32)  # CC=130 worn military plate

def paint_battleship_gray_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise, get_mgrid
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Force to naval haze gray but preserve a hint of the user's color
    base = paint.copy()
    target = base.copy()
    target[:,:,0] = np.clip(base[:,:,0] * 0.1 + 0.45, 0, 1)
    target[:,:,1] = np.clip(base[:,:,1] * 0.1 + 0.48, 0, 1)
    target[:,:,2] = np.clip(base[:,:,2] * 0.1 + 0.52, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Salt spray and vertical streaking from seawater
    y, x = get_mgrid((h,w))
    streaks = np.sin(x * 0.1 + multi_scale_noise((h,w), [16], [1.0], seed) * 2.0) * 0.5 + 0.5
    salt = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + 10)
    weathering = (streaks * 0.6 + salt * 0.4)
    
    paint = np.clip(paint + (weathering - 0.5)[:,:,np.newaxis] * 0.1 * mask[:,:,np.newaxis] * blend, 0, 1)
    return np.clip(paint + bb * 0.1, 0, 1)

def spec_battleship_gray_v2(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise, get_mgrid
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h,w))
    streaks = np.sin(x * 0.1 + multi_scale_noise((h,w), [16], [1.0], seed) * 2.0) * 0.5 + 0.5
    
    # Sea-weathered paint - dull with slight directional variance
    M = np.full((h, w), 20.0, dtype=np.float32)
    R = np.clip(140.0 + streaks * 30.0 * sm, 0, 255).astype(np.float32)
    CC = np.full((h, w), 120.0, dtype=np.float32)  # CC=120 weathered dull (was 10=near-chrome)
    return M, R, CC

def paint_gunship_gray_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Darker, flatter radar-absorbent material look
    base = paint.copy()
    target = base.copy()
    target[:,:,0] = np.clip(base[:,:,0] * 0.1 + 0.25, 0, 1)
    target[:,:,1] = np.clip(base[:,:,1] * 0.1 + 0.26, 0, 1)
    target[:,:,2] = np.clip(base[:,:,2] * 0.1 + 0.28, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Ultra-fine gritty RAM texture
    ram_grit = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 12)
    paint = np.clip(paint - ram_grit[:,:,np.newaxis] * 0.05 * mask[:,:,np.newaxis] * blend, 0, 1)
    
    # No bb highlight boost for radar absorbent
    return paint

def spec_gunship_gray_v2(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    ram_grit = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 12)
    
    # RAM coating is highly porous/rough and barely metallic
    M = np.full((h, w), 5.0, dtype=np.float32)
    R = np.clip(200.0 + ram_grit * 50.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 190.0, dtype=np.float32)  # CC=190 near-flat RAM

def paint_mil_spec_od_v3(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Force OD Green
    base = paint.copy()
    target = base.copy()
    target[:,:,0] = np.clip(base[:,:,0] * 0.1 + 0.35, 0, 1)
    target[:,:,1] = np.clip(base[:,:,1] * 0.1 + 0.40, 0, 1)
    target[:,:,2] = np.clip(base[:,:,2] * 0.1 + 0.20, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Heavy field dirt and mud smudging
    field_grime = multi_scale_noise((h, w), [8, 16, 32], [0.5, 0.3, 0.2], seed + 100)
    paint[:,:,0] = np.clip(paint[:,:,0] + field_grime * 0.05 * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] - field_grime * 0.10 * mask * blend, 0, 1) # Reduce green where muddy
    
    return np.clip(paint + bb * 0.05, 0, 1)

def spec_mil_spec_od_v3(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    field_grime = multi_scale_noise((h, w), [8, 16, 32], [0.5, 0.3, 0.2], seed + 100)
    
    # Flat durable military paint, dirt adds roughness
    M = np.full((h, w), 2.0, dtype=np.float32)
    R = np.clip(180.0 + field_grime * 60.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 195.0, dtype=np.float32)  # CC=195 dead flat military

def paint_mil_spec_tan_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Force Desert Tan
    base = paint.copy()
    target = base.copy()
    target[:,:,0] = np.clip(base[:,:,0] * 0.1 + 0.65, 0, 1)
    target[:,:,1] = np.clip(base[:,:,1] * 0.1 + 0.55, 0, 1)
    target[:,:,2] = np.clip(base[:,:,2] * 0.1 + 0.40, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Dust accumulation
    dust = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 200)
    paint = np.clip(paint + dust[:,:,np.newaxis] * 0.1 * mask[:,:,np.newaxis] * blend, 0, 1)
    return np.clip(paint + bb * 0.08, 0, 1)

def spec_mil_spec_tan_v2(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    dust = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 200)
    
    M = np.full((h, w), 0.0, dtype=np.float32)
    R = np.clip(200.0 + dust * 55.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 200.0, dtype=np.float32)  # CC=200 dead flat desert


def paint_submarine_black_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Submarine hulls are ultra-dark rubbery/resin
    base = paint.copy()
    dark_target = np.clip(base * 0.05, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        dark_target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Add anechoic tile grid lines and texture
    tile_size = 32
    y, x = np.mgrid[0:h, 0:w]
    grid = ((y % tile_size < 2) | (x % tile_size < 2)).astype(np.float32)
    
    # Grid lines are slightly lighter and recessed
    paint[:,:,0] = np.clip(paint[:,:,0] + grid * 0.08 * mask * blend, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + grid * 0.08 * mask * blend, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + grid * 0.08 * mask * blend, 0, 1)
    
    # Heavy rubber grain
    rubber_grain = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 500)
    paint = np.clip(paint + rubber_grain[:,:,np.newaxis] * 0.03 * mask[:,:,np.newaxis] * blend, 0, 1)
    
    # Absolutely no bb highlight boost on anechoic rubber
    return paint

def spec_submarine_black_v2(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    
    tile_size = 32
    y, x = np.mgrid[0:h, 0:w]
    grid = ((y % tile_size < 2) | (x % tile_size < 2)).astype(np.float32)
    rubber_grain = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 500)
    
    # Rubber is highly dielectric and extremely rough
    M = np.full((h, w), 0.0, dtype=np.float32)
    M = np.clip(M + grid * 15.0 * sm, 0, 255) # slight met on the seams
    
    R = np.clip(235.0 + rubber_grain * 20.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 210.0, dtype=np.float32)  # CC=210 anechoic rubber, dead flat



# ======================================================================
# TACTICAL & INDUSTRIAL PART 2
# ======================================================================

def paint_blackout_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    # Stealth murdered-out matte wrap style
    base = paint.copy()
    dark_target = np.clip(base * 0.05 + 0.05, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        dark_target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    # Faint thin layer streaking (from applying matte wraps)
    streaks = multi_scale_noise((h, w), [4, 16], [0.8, 0.2], seed + 300)
    paint = np.clip(paint - streaks[:,:,np.newaxis] * 0.02 * mask[:,:,np.newaxis] * blend, 0, 1)
    return np.clip(paint + bb * 0.05, 0, 1)

def spec_blackout_v2(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    streaks = multi_scale_noise((h, w), [4, 16], [0.8, 0.2], seed + 300)
    
    # Highly dielectric, very rough, but varying slightly from wrap stretching
    M = np.full((h, w), 5.0, dtype=np.float32)
    R = np.clip(210.0 + streaks * 20.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 200.0, dtype=np.float32)  # CC=200 murdered-out dead flat


def paint_cerakote_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    # Ceramic mil-spec coating - flattens out color and heavily desaturates
    base = paint.copy()
    gray = base.mean(axis=2, keepdims=True)
    target = np.clip(base * 0.5 + gray * 0.4 + 0.1, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Needs microscopic hard chalky ceramic speckling (high freq noise)
    grit = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 301)
    paint = np.clip(paint + (grit - 0.5)[:,:,np.newaxis] * 0.08 * mask[:,:,np.newaxis] * blend, 0, 1)
    return np.clip(paint + bb * 0.1, 0, 1)

def spec_cerakote_v2(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    grit = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 301)
    
    # Cured ceramic is mostly dielectric but very hard/uniform
    M = np.full((h, w), 30.0, dtype=np.float32)
    R = np.clip(160.0 + grit * 40.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 170.0, dtype=np.float32)  # CC=170 flat ceramic coating


def paint_duracoat_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    # Epoxy air-dried paint. Maintains color better than cerakote but gets muddy
    base = paint.copy()
    target = np.clip(base * 0.8, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Rippling pooling effect from heavy air-dried spray
    ripples = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 302)
    paint = np.clip(paint - ripples[:,:,np.newaxis] * 0.1 * mask[:,:,np.newaxis] * blend, 0, 1)
    return np.clip(paint + bb * 0.15, 0, 1)

def spec_duracoat_v2(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    ripples = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 302)
    
    # Less rough than Cerakote, highly uneven due to air-dry pooling
    M = np.full((h, w), 20.0, dtype=np.float32)
    R = np.clip(130.0 + ripples * 60.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 150.0, dtype=np.float32)  # CC=150 tactical epoxy


def paint_martian_regolith(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # OVERWRITE into iron-oxide rusty red Martian dirt
    base = paint.copy()
    target = base.copy()
    target[:,:,0] = np.clip(base[:,:,0] * 0.2 + 0.65, 0, 1) # Red high
    target[:,:,1] = np.clip(base[:,:,1] * 0.1 + 0.25, 0, 1) # Green low
    target[:,:,2] = np.clip(base[:,:,2] * 0.0 + 0.10, 0, 1) # Blue very low
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
    
    # Heavy dunes and dirt clumping
    clumps = multi_scale_noise((h, w), [4, 8, 32], [0.4, 0.4, 0.2], seed + 303)
    paint = np.clip(paint - clumps[:,:,np.newaxis] * 0.3 * mask[:,:,np.newaxis] * blend, 0, 1)
    
    # Occasional oxidized black streaks
    black_sand = np.where(clumps > 0.8, 0.6, 0.0).astype(np.float32)
    paint = np.clip(paint - black_sand[:,:,np.newaxis] * mask[:,:,np.newaxis] * blend, 0, 1)
    return paint # No light BB boost, it's just dirt

def spec_martian_regolith(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    clumps = multi_scale_noise((h, w), [4, 8, 32], [0.4, 0.4, 0.2], seed + 303)
    glass_shards = multi_scale_noise((h, w), [1], [1.0], seed + 304)
    
    # Almost entirely rough dirt
    R = np.clip(220.0 + clumps * 35.0 * sm, 0, 255).astype(np.float32)
    
    # Occasional bright crystalline spec hit in the dirt
    M = np.where(glass_shards > 0.98, 200.0, 0.0).astype(np.float32) * sm
    return M, R, np.full((h, w), 200.0, dtype=np.float32)  # CC=200 dead flat Martian dust


def paint_powder_coat_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    # Very solid, thick color layer. Saturates and darkens slightly.
    paint = np.clip(paint * 1.1, 0, 1)
    # The major defining feature of powder coat is the specular orange-peel, so base is relatively clean
    return np.clip(paint + bb * 0.2, 0, 1)

def spec_powder_coat_v2(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Heavy, thick orange-peel bubbling from cured polyester powder
    peel = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 305)
    
    M = np.full((h, w), 10.0, dtype=np.float32)
    R = np.clip(90.0 + peel * 70.0 * sm, 0, 255).astype(np.float32)
    # Give it a thick clearcoat property to emulate baked finish
    CC = np.clip(50.0 - peel * 20.0 * sm, 0, 255).astype(np.float32)
    return M, R, CC


def paint_sandblasted_v2(paint, shape, mask, seed, pm, bb):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Stripped metal. It totally destroys the user saturation, leaving it light grey/metallic
    base = paint.copy()
    gray = base.mean(axis=2, keepdims=True)
    target = base.copy()
    for c in range(3):
        target[:,:,c] = np.clip(base[:,:,c] * 0.1 + gray[:,:,0] * 0.5 + 0.3, 0, 1)
    blend = np.clip(pm, 0.0, 1.0)
    paint = np.clip(
        base * (1.0 - mask[:, :, np.newaxis] * blend) +
        target * (mask[:, :, np.newaxis] * blend),
        0, 1
    )
        
    # Heavy sharp static noise
    blast_grit = multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 306)
    paint = np.clip(paint + (blast_grit - 0.5)[:,:,np.newaxis] * 0.2 * mask[:,:,np.newaxis] * blend, 0, 1)
    return np.clip(paint + bb * 0.3, 0, 1)

def spec_sandblasted_v2(shape, seed, sm, base_m, base_r):
    import numpy as np
    from engine.core import multi_scale_noise
    h, w = shape[:2] if len(shape) > 2 else shape
    blast_grit = multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 306)
    
    # Pure metal, but scattered everywhere so it's both highly metallic AND highly rough
    M = np.clip(180.0 + blast_grit * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(150.0 + blast_grit * 50.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 155.0, dtype=np.float32)  # CC=155 raw stripped metal


def _load_v2_base_upgrades():
    """Re-export v2 paint/spec from engine.paint_v2 so existing imports in base_registry_data resolve."""
    try:
        import importlib
        modules = [
            "brushed_directional", "candy_special", "carbon_composite", "ceramic_glass",
            "chrome_mirror", "exotic_metal", "finish_basic", "metallic_flake", "metallic_standard",
            "military_tactical", "oem_automotive", "paradigm_scifi", "premium_luxury",
            "racing_heritage", "raw_weathered", "shokk_series", "weathered_worn", "wrap_vinyl",
        ]
        skip = {"paint_chameleon_shift"}
        patched = 0
        for mod_name in modules:
            try:
                mod = importlib.import_module("engine.paint_v2." + mod_name)
            except ImportError:
                continue
            for name in dir(mod):
                if not (name.startswith("paint_") or name.startswith("spec_")):
                    continue
                if name in skip:
                    continue
                fn = getattr(mod, name)
                if callable(fn) and name in globals():
                    globals()[name] = fn
                    patched += 1
        if patched:
            print(f"[V2 Registry] spec_paint re-exports: {patched}")
    except Exception as exc:
        print(f"[V2 Registry] spec_paint v2 load skipped: {exc}")


_load_v2_base_upgrades()

