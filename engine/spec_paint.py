"""
engine/spec_paint.py - Standard spec_ and paint_ functions (bases + effects).
Extracted from shokker_engine_v2 for easier editing.
"""
import numpy as np
from PIL import Image, ImageFilter
from scipy.spatial import cKDTree
from engine.core import multi_scale_noise, get_mgrid, hsv_to_rgb_vec, rgb_to_hsv_array
from engine.utils import perlin_multi_octave, generate_perlin_noise_2d

# Alias for legacy carbon/ceramic/glass sections that use _noise shorthand
_noise = multi_scale_noise


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
    """Matte -- flat non-reflective paint. No metallic, very rough (R=220-255), no visible sheen.
    FIXED WEAK-010: added 3-octave FBM roughness variation — G: 220-255 organic flat texture,
    near-zero metallic with micro-variation (R_ch: 0-30), B near max-flat with slight noise."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    # 3-octave FBM for organic matte texture
    rough_fbm = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], seed + 4100)
    # M: near-zero with micro-variation (0-30 range) — chalk/pigment micro-variation
    spec[:,:,0] = np.clip(rough_fbm * 30.0 * sm * mask, 0, 255).astype(np.uint8)
    # R: matte roughness 220-255 spatially varied — heavy diffuse scatter
    spec[:,:,1] = np.clip((220.0 + rough_fbm * 35.0) * mask + 180.0 * (1 - mask), 0, 255).astype(np.uint8)
    # CC: near-flat (200-230) with slight noise variation
    cc_noise    = multi_scale_noise(shape, [4, 8, 16], [0.4, 0.35, 0.25], seed + 4101)
    cc_val      = np.clip(200.0 + cc_noise * 30.0, 160, 255)
    spec[:,:,2] = np.clip(cc_val * mask + 180.0 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_satin(shape, mask, seed, sm):
    """Satin -- semi-gloss between matte and gloss. No metallic, mid-rough (R=80-140), partial clearcoat.
    FIXED WEAK-011: replaced dead-code constant R formula with real 2-octave FBM sheen variation.
    R=100*mask+100*(1-mask) evaluated identically everywhere — now uses genuine spatial noise."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    # 2-octave FBM for subtle satin sheen variation
    sheen_coarse = multi_scale_noise(shape, [8, 16], [0.55, 0.45], seed + 3800)
    sheen_fine   = multi_scale_noise(shape, [2,  4],  [0.6,  0.4], seed + 3801)
    sheen_fbm    = sheen_coarse * 0.7 + sheen_fine * 0.3  # 0..1
    # M: near-zero but with micro-variation for subtle satin sheen (range 0-18)
    spec[:,:,0] = np.clip(sheen_fbm * 18.0 * sm * mask, 0, 255).astype(np.uint8)
    # R: satin roughness 80-140 with spatial noise — distinctly between gloss and matte
    spec[:,:,1] = np.clip((80.0 + sheen_fbm * 60.0 * sm) * mask + 110.0 * (1 - mask), 0, 255).astype(np.uint8)
    # CC: satin clearcoat 40-90 with slight noise variation (moderately glossy)
    cc_noise     = multi_scale_noise(shape, [4, 8], [0.5, 0.5], seed + 3802)
    spec[:,:,2]  = np.clip(40.0 + cc_noise * 50.0, 16, 255).astype(np.uint8)
    spec[:,:,3] = 255
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
    """Pearlescent -- per-platelet M/R/CC decoupled noise, fine-scale platelet flash.
    FIXED WEAK-018: decoupled M/R/CC seeds, added fine-scale platelet flash at seed+99.
    M: 80-200 platelet flash (seed=42 offset), R: 30-90 micro-roughness (seed=137),
    CC: 18-40 very glossy clearcoat (seed=251). Fine platelet flash blended at 30% into M."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    # M: 2-octave FBM at independent seed — platelet surface flash (high metallic at platelet)
    m_wave = multi_scale_noise(shape, [16, 32], [0.55, 0.45], seed + 42)
    # R: 2-octave FBM at DIFFERENT seed — pearl surface micro-roughness
    r_wave = multi_scale_noise(shape, [16, 32], [0.55, 0.45], seed + 137)
    # CC: 2-octave FBM at THIRD seed — very glossy clearcoat with slight variation
    cc_wave = multi_scale_noise(shape, [16, 32], [0.55, 0.45], seed + 251)
    # Fine-scale platelet flash: individual platelet events blended at 30% into M
    platelet_flash = multi_scale_noise(shape, [60, 120], [0.6, 0.4], seed + 99)
    m_combined = m_wave * 0.70 + platelet_flash * 0.30  # 30% fine flash blend
    # M: range 80-200 (platelet flash — high metallic at platelet surface)
    spec[:,:,0] = np.clip(80 * mask + 5 * (1-mask) + m_combined * 120 * sm * mask, 0, 255).astype(np.uint8)
    # R: range 30-90 (pearl surface has some micro-roughness but not much)
    spec[:,:,1] = np.clip(30 * mask + 100 * (1-mask) + r_wave * 60 * sm * mask, 0, 255).astype(np.uint8)
    # CC: range 18-40 (very glossy clearcoat with slight variation)
    cc_val = np.clip(18 + cc_wave * 22, 16, 255)
    spec[:,:,2] = np.clip(cc_val * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:,:,3] = 255
    return spec

def spec_pearlescent_white(shape, mask, seed, sm):
    """Tri-coat pearlescent white -- three independently-seeded noise fields for three physical coats.
    FIXED WEAK-019: genuine tri-coat simulation with decoupled noise seeds per coat layer.
    Base coat: seed+11 (coarse metallic silver base), Pearl mid-coat: seed+73 (interference pigment),
    Top clearcoat: seed+199 (gloss variation). M range ~120-220, R range 15-55."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    # Base coat layer (metallic silver base) — coarse scale, seed=11
    base_metal = multi_scale_noise(shape, [4, 8], [0.55, 0.45], seed + 11)
    # Pearl mid-coat layer (interference pigment) — medium scale, seed=73
    pearl_mid = multi_scale_noise(shape, [20, 40], [0.55, 0.45], seed + 73)
    # Top clearcoat layer (gloss variation) — fine scale, seed=199
    clear_top = multi_scale_noise(shape, [40, 80], [0.55, 0.45], seed + 199)
    # Combined M = 120 + base_metal*60 + pearl_mid*40 (range ~120-220)
    m_val = np.clip(120.0 + base_metal * 60.0 * sm + pearl_mid * 40.0 * sm, 0, 255)
    spec[:,:,0] = np.clip(m_val * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    # Combined R = 15 + pearl_mid*40 (range 15-55) — pearl mid modulates roughness
    r_val = np.clip(15.0 + pearl_mid * 40.0 * sm, 0, 255)
    spec[:,:,1] = np.clip(r_val * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    # CC = 16 + clear_top*8 (range 16-24, very glossy with slight variation)
    cc_val = np.clip(16.0 + clear_top * 8.0, 16, 255)
    spec[:,:,2] = np.clip(cc_val * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:,:,3] = 255
    return spec


def spec_pearl_base(shape, seed, sm, base_m, base_r):
    """base_spec_fn-compatible pearl spec: decoupled M/R/CC noise seeds + fine platelet flash.
    WEAK-018 FIX: replaces single correlated noise field with three independent seeds.
    Signature matches compose.py base_spec_fn API: (shape, seed, sm, base_m, base_r) -> (M, R, CC)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # M: 2-octave FBM seed=42 offset, range 80-200
    m_wave = multi_scale_noise(sh, [16, 32], [0.55, 0.45], seed + 42)
    # R: 2-octave FBM DIFFERENT seed=137, range 30-90
    r_wave = multi_scale_noise(sh, [16, 32], [0.55, 0.45], seed + 137)
    # CC: 2-octave FBM THIRD seed=251, range 18-40
    cc_wave = multi_scale_noise(sh, [16, 32], [0.55, 0.45], seed + 251)
    # Fine-scale platelet flash (seed+99) blended 30% into M
    platelet_flash = multi_scale_noise(sh, [60, 120], [0.6, 0.4], seed + 99)
    m_combined = m_wave * 0.70 + platelet_flash * 0.30
    M_arr = np.clip(80.0 + m_combined * 120.0 * sm, 0, 255).astype(np.float32)
    R_arr = np.clip(30.0 + r_wave * 60.0 * sm, 15, 255).astype(np.float32)  # GGX floor: R>=15
    CC_arr = np.clip(18.0 + cc_wave * 22.0, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def spec_pearlescent_white_base(shape, seed, sm, base_m, base_r):
    """base_spec_fn-compatible tri-coat pearlescent white spec.
    WEAK-019 FIX: three independently-seeded noise fields for three physical coat layers.
    Signature: (shape, seed, sm, base_m, base_r) -> (M_arr, R_arr, CC_arr)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Base coat layer (metallic silver base) — coarse scale, seed+11
    base_metal = multi_scale_noise(sh, [4, 8], [0.55, 0.45], seed + 11)
    # Pearl mid-coat layer (interference pigment) — medium scale, seed+73
    pearl_mid = multi_scale_noise(sh, [20, 40], [0.55, 0.45], seed + 73)
    # Top clearcoat layer (gloss variation) — fine scale, seed+199
    clear_top = multi_scale_noise(sh, [40, 80], [0.55, 0.45], seed + 199)
    # M = 120 + base_metal*60 + pearl_mid*40 (range ~120-220)
    M_arr = np.clip(120.0 + base_metal * 60.0 * sm + pearl_mid * 40.0 * sm, 0, 255).astype(np.float32)
    # R = 15 + pearl_mid*40 (range 15-55)
    R_arr = np.clip(15.0 + pearl_mid * 40.0 * sm, 0, 255).astype(np.float32)
    # CC = 16 + clear_top*8 (range 16-24, very glossy)
    CC_arr = np.clip(16.0 + clear_top * 8.0, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def spec_chrome(shape, mask, seed, sm):
    """Chrome -- pure mirror. Max metallic, near-zero roughness, CC=16 max gloss clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(255 * mask + 5 * (1-mask), 0, 255).astype(np.uint8)  # M=255 full metal
    spec[:,:,1] = np.clip(2 * mask + 100 * (1-mask), 0, 255).astype(np.uint8)  # R=2 mirror smooth
    spec[:,:,2] = 16; spec[:,:,3] = 255  # CC=16 max gloss chrome (WARN-CHROME-002 fix)
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
    spec[:,:,1] = np.clip(15 * mask + 100 * (1-mask) + rf * 40 * sm * mask, 15, 255).astype(np.uint8)
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
    spec[:,:,1] = np.clip((15 + holo * 30 * sm) * mask + 100 * (1-mask), 15, 255).astype(np.uint8)
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
    spec[:,:,1] = np.clip((15 * scanline + 80 * (1 - scanline)) * mask + 100 * (1-mask), 15, 255).astype(np.uint8)
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


def paint_infinite_warp(paint, shape, mask, seed, pm, bb):
    """Infinite Finish — fractal dimensional warp creating impossible recursive material.
    At every zoom level the surface flips between chrome-bright and matte-dark,
    producing a material that appears to recede infinitely into itself.
    PARADIGM FIX: replaces paint_none on infinite_finish (was lazy dup of quantum_foam).
    Physics: multi-octave domain-warped FBM drives brightness + saturation inversions.
    Topology: self-similar fractal warp — distinct from singularity (radial rings)
    and quantum_foam (pure noise, no paint mod)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 7741)
    # 5-octave FBM with domain warping for fractal recursion
    n1 = multi_scale_noise((h, w), [2, 4, 8, 16, 32], [0.3, 0.25, 0.2, 0.15, 0.1], seed + 111)
    n2 = multi_scale_noise((h, w), [3, 6, 12, 24], [0.35, 0.3, 0.2, 0.15], seed + 222)
    # Domain warp: use n1 to warp coordinates for n2 — creates recursive self-similarity
    warp_strength = np.float32(0.12) * pm
    y_idx = np.arange(h, dtype=np.float32)[:, None] / max(h, 1)
    x_idx = np.arange(w, dtype=np.float32)[None, :] / max(w, 1)
    warped = np.sin((x_idx + n1 * warp_strength) * np.float32(6.28) * 3) * \
             np.cos((y_idx + n2 * warp_strength) * np.float32(6.28) * 3)
    warped = (warped * 0.5 + 0.5).astype(np.float32)  # [0, 1]
    # Fractal brightness inversion: where warped > 0.5, push toward chrome-bright;
    # where < 0.5, push toward matte-dark — impossible simultaneous finish
    bright_zone = np.clip(warped * 2 - 0.5, 0, 1).astype(np.float32)
    dark_zone = np.clip(1.0 - warped * 2, 0, 1).astype(np.float32)
    # Apply to paint: chrome zones get brighter + desaturated, dark zones get deeper + saturated
    gray = paint[:,:,:3].mean(axis=2, keepdims=True)
    chrome_push = gray * np.float32(1.3)  # brighter
    matte_push = paint[:,:,:3] * np.float32(0.55)  # darker, keep color
    m3 = mask[:,:,np.newaxis]
    blend = np.float32(0.7) * pm
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + \
                    (chrome_push * bright_zone[:,:,np.newaxis] +
                     matte_push * dark_zone[:,:,np.newaxis]) * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)

def paint_matte_flat(paint, shape, mask, seed, pm, bb):
    """Matte paint modifier: ~12% desaturation + slight darkening to produce chalky matte undertone.
    ADDED for WEAK-010: gives matte finish visually distinct chalky character vs gloss/satin."""
    gray = paint.mean(axis=2, keepdims=True)
    # ~12% desaturation toward gray
    desat = paint * 0.88 + gray * 0.12
    # Slight darkening (~5%) to simulate matte light absorption
    darkened = np.clip(desat * 0.95, 0, 1)
    blend = pm * mask[:, :, np.newaxis]
    return np.clip(paint * (1.0 - blend) + darkened * blend, 0, 1).astype(np.float32)

def paint_scuffed_satin_fn(paint, shape, mask, seed, pm, bb):
    """Scuffed satin paint modifier: slight desaturation + micro-abrasion darkening effect.
    ADDED for WEAK-015 FIX: scuffed surface should read duller/rougher than clean satin.
    Scuffing removes surface clarity — slight desaturation and random micro-dark spots."""
    h, w = shape[:2] if len(shape) > 2 else shape
    gray = paint.mean(axis=2, keepdims=True)
    # ~8% desaturation — scuffing removes some color vibrancy
    desat = paint * 0.92 + gray * 0.08
    # Micro-abrasion spots: fine noise adds subtle darker scratch texture
    micro_abrasion = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 5900)
    # Slight darkening at abrasion peaks (0-4% darkening) to simulate wear marks
    abrasion_darken = 1.0 - micro_abrasion * 0.04 * pm
    scuffed = np.clip(desat * abrasion_darken[:, :, np.newaxis], 0, 1)
    blend = pm * mask[:, :, np.newaxis]
    return np.clip(paint * (1.0 - blend) + scuffed * blend, 0, 1).astype(np.float32)

def paint_liquid_wrap_fn(paint, shape, mask, seed, pm, bb):
    """Liquid wrap / rubber peel coat paint modifier: stretchy rubber/vinyl character.
    ADDED for WEAK-016 FIX: distinct from satin_wrap — rubber has fine Perlin micro-texture
    + slight darkening at 'stretch points' (simulated by noise gradient peaks).
    Satin_wrap: 85-90% saturation, directional sheen. Liquid_wrap: rubbery, no directional sheen."""
    h, w = shape[:2] if len(shape) > 2 else shape
    # Fine Perlin noise for rubber compound particle variation texture
    rubber_grain = multi_scale_noise((h, w), [2, 4, 8], [0.45, 0.35, 0.2], seed + 6300)
    # High-freq gradient noise to simulate stretch point darkening
    stretch_pts = multi_scale_noise((h, w), [1, 2, 3], [0.5, 0.3, 0.2], seed + 6301)
    # Slight darkening at stretch peaks (high curvature): 0-5% darker at gradient peaks
    stretch_darken = 1.0 - np.clip((stretch_pts - 0.7) / 0.3, 0, 1) * 0.05 * pm
    # ~10% desaturation: rubber coat slightly mutes the underlying color
    gray = paint.mean(axis=2, keepdims=True)
    desaturated = paint * 0.90 + gray * 0.10
    # Fine rubber grain texture: very subtle brightness variation from compound particles
    grain_effect = 1.0 + (rubber_grain - 0.5) * 0.03 * pm
    result = np.clip(desaturated * stretch_darken[:,:,np.newaxis] * grain_effect[:,:,np.newaxis], 0, 1)
    blend = pm * mask[:,:,np.newaxis]
    return np.clip(paint * (1.0 - blend) + result * blend, 0, 1).astype(np.float32)

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


def paint_pearlescent_white_fn(paint, shape, mask, seed, pm, bb):
    """Tri-coat pearlescent white paint modifier -- HSV blue-green interference shimmer.
    FIXED WEAK-019: genuine tri-coat paint fn. No paint_fine_sparkle.
    1. Pushes base color slightly toward white (value +0.05-0.08).
    2. Uses pearl_mid noise (seed+73) to add blue-green HSV hue rotation shimmer.
    3. Small hue shift (<=30 deg) since this is WHITE pearl -- keeps it white, not rainbow."""
    if pm == 0.0:
        return paint
    h, w = shape[:2] if len(shape) > 2 else shape
    # Pearl mid-coat interference field — same seed as spec_pearlescent_white pearl_mid layer
    pearl_mid = multi_scale_noise((h, w), [20, 40], [0.55, 0.45], seed + 73)
    mask3 = mask[:,:,np.newaxis]
    # Step 1: push base color toward white (value up 0.05-0.08)
    whitening = 0.065 * pm
    paint_white = np.clip(paint + whitening * mask3, 0, 1)
    # Step 2: HSV hue rotation for blue-green interference shimmer
    r, g, b = paint_white[:,:,0], paint_white[:,:,1], paint_white[:,:,2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin + 1e-8
    hue = np.zeros((h, w), dtype=np.float32)
    m_r = (cmax == r)
    m_g = (cmax == g) & ~m_r
    m_b = ~m_r & ~m_g
    hue[m_r] = ((g[m_r] - b[m_r]) / delta[m_r]) % 6 / 6
    hue[m_g] = ((b[m_g] - r[m_g]) / delta[m_g] + 2) / 6
    hue[m_b] = ((r[m_b] - g[m_b]) / delta[m_b] + 4) / 6
    sat = delta / (cmax + 1e-8)
    val = cmax
    # Hue shift: pearl_mid * 30 degrees (small — white pearl, not full rainbow)
    hue_shift_deg = pearl_mid * 30.0
    new_hue = (hue + hue_shift_deg / 360.0 * mask) % 1.0
    new_rgb = np.stack(hsv_to_rgb_vec(new_hue, sat, val), axis=2)
    blend = np.clip(pm * 0.55, 0, 1)
    result = paint_white * (1.0 - mask3 * blend) + new_rgb * (mask3 * blend)
    result = np.clip(result + bb[:,:,np.newaxis] * 0.20 * pm * mask3 if hasattr(bb, 'ndim') and bb.ndim == 2
                     else result + float(bb) * 0.20 * pm * mask3, 0, 1)
    return result.astype(np.float32)


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
    # cKDTree for fast nearest-two-neighbor query (downsampled for speed)
    ds = 4  # downsample factor
    sh, sw = h // ds, w // ds
    yg, xg = np.mgrid[0:sh, 0:sw]
    yg = (yg * ds).astype(np.float32)
    xg = (xg * ds).astype(np.float32)
    pts = np.column_stack([points_y.astype(np.float32), points_x.astype(np.float32)])
    tree = cKDTree(pts)
    query_pts = np.column_stack([yg.ravel(), xg.ravel()])
    dists, _ = tree.query(query_pts, k=2)
    dist1 = dists[:, 0].reshape(sh, sw)
    dist2 = dists[:, 1].reshape(sh, sw)
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
    # cKDTree for fast nearest-cell query (downsampled for speed)
    ds = 4
    sh, sw = h // ds, w // ds
    yg = np.arange(sh, dtype=np.float32).reshape(-1, 1) * ds
    xg = np.arange(sw, dtype=np.float32).reshape(1, -1) * ds
    pts = np.column_stack([cy, cx])
    tree = cKDTree(pts)
    query_pts = np.column_stack([np.broadcast_to(yg, (sh, sw)).ravel(),
                                  np.broadcast_to(xg, (sh, sw)).ravel()])
    _, nearest_flat = tree.query(query_pts, k=1)
    nearest = nearest_flat.reshape(sh, sw).astype(np.uint8)
    nearest_img = Image.fromarray(nearest)
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
    """Galaxy nebula - multi-region nebula color ramp + LCG star field.
    FIXED WEAK-021: Replaced lazy 12% RGB haze with proper nebula regions and star field.
    - 3-4 nebula color regions via large-scale FBM; each maps to deep blue/violet/rose/teal
    - LCG hash star field: ~0.3% of pixels become white/blue-white/yellow-white star points
    - Stars get Gaussian-dot brightening (radius 1-2px) not noise smear
    - Nebula blends at 40% weight, base livery at 60% so base color still shows"""
    h, w = shape
    # Large-scale FBM to divide canvas into nebula color regions
    region_field = multi_scale_noise(shape, [64, 128, 256], [0.4, 0.35, 0.25], seed + 100)
    region_val = np.clip(region_field * 0.5 + 0.5, 0, 1)

    # 4 nebula color regions mapped by region_val:
    # 0.0-0.25: deep blue H=240, S=0.80, V=0.35
    # 0.25-0.50: violet H=275, S=0.75, V=0.40
    # 0.50-0.75: rose/pink H=340, S=0.70, V=0.45
    # 0.75-1.00: teal H=185, S=0.75, V=0.38
    stops_h = np.array([240.0, 275.0, 340.0, 185.0], dtype=np.float32) / 360.0
    stops_s = np.array([0.80,   0.75,   0.70,  0.75], dtype=np.float32)
    stops_v = np.array([0.35,   0.40,   0.45,  0.38], dtype=np.float32)

    t = region_val * 3.0
    idx = np.clip(t.astype(np.int32), 0, 2)
    frac = t - idx.astype(np.float32)
    out_h = np.zeros((h, w), dtype=np.float32)
    out_s = np.zeros((h, w), dtype=np.float32)
    out_v = np.zeros((h, w), dtype=np.float32)
    for i in range(3):
        seg = (idx == i)
        f = frac[seg]
        out_h[seg] = stops_h[i] * (1 - f) + stops_h[i + 1] * f
        out_s[seg] = stops_s[i] * (1 - f) + stops_s[i + 1] * f
        out_v[seg] = stops_v[i] * (1 - f) + stops_v[i + 1] * f

    neb_r, neb_g, neb_b = hsv_to_rgb_vec(out_h, out_s, out_v)

    # Nebula density modulation (brighter in dense cloud cores)
    density = multi_scale_noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 200)
    density = np.clip(density * 0.5 + 0.5, 0, 1)
    neb_r *= density; neb_g *= density; neb_b *= density

    # LCG hash star field (~0.3% of pixels = stars)
    # LCG: next = (a * prev + c) % m;  threshold determines star density
    flat_idx = np.arange(h * w, dtype=np.uint32)
    lcg = ((flat_idx * 1664525 + (seed & 0xFFFF)) * 22695477 + 1013904223) & 0xFFFFFFFF
    lcg2 = ((lcg * 1664525) + 1013904223) & 0xFFFFFFFF
    star_mask = (lcg % 1000 < 3).reshape(h, w)  # ~0.3% of pixels

    # Star color type: 0=white, 1=blue-white, 2=yellow-white (from lcg2)
    star_type = (lcg2 % 3).reshape(h, w)
    star_r = np.where(star_mask, np.where(star_type == 1, 0.75, np.where(star_type == 2, 1.0, 0.95)), 0.0).astype(np.float32)
    star_g = np.where(star_mask, np.where(star_type == 1, 0.82, np.where(star_type == 2, 0.95, 0.95)), 0.0).astype(np.float32)
    star_b = np.where(star_mask, np.where(star_type == 1, 1.0,  np.where(star_type == 2, 0.70, 0.95)), 0.0).astype(np.float32)

    # Gaussian dot spread for stars (radius ~1.5px via small blur)
    _blur_r = 1.5
    for _ch, _sarr in enumerate([star_r, star_g, star_b]):
        _img = Image.fromarray(np.clip(_sarr * 255, 0, 255).astype(np.uint8), mode='L')
        _blurred = np.array(_img.filter(ImageFilter.GaussianBlur(radius=_blur_r))).astype(np.float32) / 255.0
        if _ch == 0:
            star_r_spread = _blurred
        elif _ch == 1:
            star_g_spread = _blurred
        else:
            star_b_spread = _blurred

    # Combine: base * 0.60 + nebula * 0.40, then overlay star points
    blend_neb = 0.40 * pm
    blend_star = np.clip(pm * 1.0, 0, 1.0)
    m = mask
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend_neb * m) + neb_r * blend_neb * m + star_r_spread * blend_star * m, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend_neb * m) + neb_g * blend_neb * m + star_g_spread * blend_star * m, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend_neb * m) + neb_b * blend_neb * m + star_b_spread * blend_star * m, 0, 1)
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


def paint_desert_worn(paint, shape, mask, seed, pm, bb):
    """Desert worn — sand-blasted UV-hammered surface. UV bleach toward warm sandy pale with
    coarse grit texture (visibly grittier than tactical_flat / volcanic_ash)."""
    h, w = shape
    np.random.seed(seed + 8341)
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    # UV bleach: desaturate + warm sandy tint (red/yellow elevated, blue reduced)
    uv_desat = 0.30 * pm
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] * (1 - uv_desat * mask) + mean_c * uv_desat * mask + 0.040 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] * (1 - uv_desat * mask) + mean_c * uv_desat * mask + 0.015 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] * (1 - uv_desat * mask) + mean_c * uv_desat * mask - 0.020 * pm * mask, 0, 1)
    # Coarse sand grit — 2.5× more pronounced than tactical_flat (0.015 → 0.038)
    coarse = np.random.randn(h, w).astype(np.float32) * 0.038 * pm
    fine   = np.random.randn(h, w).astype(np.float32) * 0.012 * pm
    result = np.clip(result + (coarse + fine)[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return result


# ================================================================
# v5.0 NEW PAINT FUNCTIONS - for 50-base expansion
# ================================================================

def paint_wet_gloss(paint, shape, mask, seed, pm, bb):
    """Wet look - deepens color toward black, adds slight reflection brightening.
    FIX: bb reflection was 0.01 (invisible). Raised to 0.08 for visible wet sheen."""
    darken = 0.08 * pm
    paint = np.clip(paint * (1 - darken * mask[:,:,np.newaxis]) + bb * 0.08 * pm * mask[:,:,np.newaxis], 0, 1)
    return paint

def paint_silk_sheen(paint, shape, mask, seed, pm, bb):
    """Silk finish - directional brightening like light on silk fabric.
    FIX: amplitude was 0.02 (invisible). Raised to 0.08 for visible silk bands."""
    np.random.seed(seed + 900)
    h, w = shape
    y_grad = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
    silk = np.sin(y_grad * np.pi * 3) * 0.08 * pm
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
    """Iridescent - full HSV hue rotation rainbow shift at 8-cycle frequency.
    FIXED WEAK-020: replaced lazy RGB channel add with proper HSV hue rotation modeled
    after paint_interference_shift. 8 cycles across canvas (was ~2), blend=0.55 (was 0.25).
    Uses FBM at seed=17 offset for position-based full rainbow rotation."""
    h, w = shape
    # FBM-driven position field at 8 cycles across canvas (was ~2 cycles, ~4pi)
    t = multi_scale_noise(shape, [8, 16], [0.6, 0.4], seed + 17)
    # Full rainbow rotation: t=0..1 drives 0..360 hue shift
    hue_delta = t  # 0-1 maps to 0-1 on hue wheel (= 360 degrees full rotation)
    # Convert paint to HSV
    r, g, b = paint[:,:,0], paint[:,:,1], paint[:,:,2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin + 1e-8
    hue = np.zeros((h, w), dtype=np.float32)
    m_r = (cmax == r)
    m_g = (cmax == g) & ~m_r
    m_b = ~m_r & ~m_g
    hue[m_r] = ((g[m_r] - b[m_r]) / delta[m_r]) % 6 / 6
    hue[m_g] = ((b[m_g] - r[m_g]) / delta[m_g] + 2) / 6
    hue[m_b] = ((r[m_b] - g[m_b]) / delta[m_b] + 4) / 6
    sat = delta / (cmax + 1e-8)
    val = cmax
    # Rotate H by hue_delta (full 360-degree rainbow sweep), keep S and V
    new_hue = (hue + hue_delta * mask) % 1.0
    new_rgb = np.stack(hsv_to_rgb_vec(new_hue, sat, val), axis=2)
    # Blend at 0.55 weight — vivid and visible (was 0.25)
    blend = np.clip(pm * 0.55, 0, 1.0)
    blend3 = blend[:,:,np.newaxis] if hasattr(blend, 'ndim') and blend.ndim == 2 else blend
    paint[:,:,:3] = paint[:,:,:3] * (1 - mask[:,:,np.newaxis] * blend3) + new_rgb * (mask[:,:,np.newaxis] * blend3)
    return np.clip(paint, 0, 1).astype(np.float32)


def paint_singularity_v2(paint, shape, mask, seed, pm, bb):
    """Singularity — radial colour rings pulsing outward from a central point.
    Concept: theoretical singular point; infinite spectral collapse radiates rainbow rings.
    Topology: concentric rings + 3-petal angular warp — distinct from paint_iridescent_shift
    (FBM blob field) and paint_holographic_base (linear diagonal bands).
    LAZY-ANGLE-001 FIX: replaces paint_iridescent_shift on singularity BASE entry."""
    h, w = shape[:2] if len(shape) > 2 else shape
    cy, cx = np.float32(h) * 0.5, np.float32(w) * 0.5
    y, x = get_mgrid((h, w))
    yf = y.astype(np.float32) - cy
    xf = x.astype(np.float32) - cx
    # Normalised radial distance [0, 1]
    dist = np.sqrt(yf ** 2 + xf ** 2) / (np.float32(min(h, w)) * 0.5)
    dist = np.clip(dist, 0, 1).astype(np.float32)
    # Angular field — 3-petal spiral warp modulates ring phase
    angle = np.arctan2(yf, xf).astype(np.float32)   # [-pi, pi]
    angular_warp = np.sin(angle * 3 + np.float32(seed % 31) * 0.2) * np.float32(0.18)
    # Radial hue rings (8 cycles) with angular warp -> concentric + twisted character
    hue_field = (np.sin((dist + angular_warp) * np.float32(8.0) * np.pi) * 0.5 + 0.5).astype(np.float32)
    # Light FBM perturbation for organic ring edges
    perturb = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 2371) * np.float32(0.08)
    hue_field = np.clip(hue_field + perturb, 0, 1)
    # Full HSV hue rotation (same mechanism as paint_iridescent_shift, different field topology)
    r, g, b = paint[:,:,0].copy(), paint[:,:,1].copy(), paint[:,:,2].copy()
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin + 1e-8
    hue_c = np.zeros((h, w), dtype=np.float32)
    m_r = (cmax == r)
    m_g = (cmax == g) & ~m_r
    m_b = ~m_r & ~m_g
    hue_c[m_r] = ((g[m_r] - b[m_r]) / delta[m_r]) % 6 / 6
    hue_c[m_g] = ((b[m_g] - r[m_g]) / delta[m_g] + 2) / 6
    hue_c[m_b] = ((r[m_b] - g[m_b]) / delta[m_b] + 4) / 6
    sat = delta / (cmax + 1e-8)
    val = cmax
    new_hue = (hue_c + hue_field * mask) % 1.0
    new_rgb = np.stack(hsv_to_rgb_vec(new_hue, sat, val), axis=2)
    blend = np.clip(pm * np.float32(0.65), 0, 1.0)
    blend3 = blend[:,:,np.newaxis] if hasattr(blend, 'ndim') and blend.ndim == 2 else blend
    paint[:,:,:3] = paint[:,:,:3] * (1 - mask[:,:,np.newaxis] * blend3) + new_rgb * (mask[:,:,np.newaxis] * blend3)
    return np.clip(paint, 0, 1).astype(np.float32)


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
    """Heat-treated tool steel (gun barrels, knife blades) oxide color bands.
    FIXED WEAK-024: Distinct from burnt_headers (exhaust titanium). Tool steel has
    more muted, lower-saturation oxide colors with a sharper transition zone (step-like
    gradient ± FBM edge wavering) rather than the organic gradient of exhaust headers.
    4-stop steel oxide progression: straw → bronze → peacock blue → dark blue (muted S).
    Blend at 0.60 — clearly visible while showing base livery color."""
    h, w = shape
    # Sharp step-function gradient (tool steel = controlled uniform heat, not organic exhaust)
    # Use coarse linear ramp along the vertical axis with slight FBM edge wavering
    base_grad = np.linspace(0.0, 1.0, h, dtype=np.float32)[:,np.newaxis]
    # Single-octave FBM waver for natural edge variation (not as organic as burnt_headers)
    waver = multi_scale_noise(shape, [24, 48], [0.7, 0.3], seed + 951)
    heat_val = np.clip(base_grad + waver * 0.18, 0, 1)
    # Apply a mild step-function sharpening (exponent curves the transition zones)
    # This creates ~3 distinct color bands with soft edges instead of a smooth gradient
    heat_val = np.power(heat_val, 1.4)

    # 4-stop tool steel oxide progression (lower saturation than titanium):
    # Stop 0 (t=0.0): dark blue H=230, S=0.65, V=0.40
    # Stop 1 (t=0.33): peacock blue/teal H=195, S=0.60, V=0.50
    # Stop 2 (t=0.67): bronze H=28, S=0.65, V=0.70
    # Stop 3 (t=1.0): straw H=48, S=0.55, V=0.85
    stops_h = np.array([230.0, 195.0, 28.0, 48.0], dtype=np.float32) / 360.0
    stops_s = np.array([0.65,   0.60,  0.65,  0.55], dtype=np.float32)
    stops_v = np.array([0.40,   0.50,  0.70,  0.85], dtype=np.float32)
    n_stops = len(stops_h)

    t = heat_val * (n_stops - 1)
    idx = np.clip(t.astype(np.int32), 0, n_stops - 2)
    frac = t - idx.astype(np.float32)

    out_h = np.zeros((h, w), dtype=np.float32)
    out_s = np.zeros((h, w), dtype=np.float32)
    out_v = np.zeros((h, w), dtype=np.float32)
    for i in range(n_stops - 1):
        seg = (idx == i)
        f = frac[seg]
        out_h[seg] = stops_h[i] * (1 - f) + stops_h[i + 1] * f
        out_s[seg] = stops_s[i] * (1 - f) + stops_s[i + 1] * f
        out_v[seg] = stops_v[i] * (1 - f) + stops_v[i + 1] * f

    r_ox, g_ox, b_ox = hsv_to_rgb_vec(out_h, out_s, out_v)
    blend = 0.60 * pm
    m = mask
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * m) + r_ox * blend * m, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * m) + g_ox * blend * m, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * m) + b_ox * blend * m, 0, 1)
    return paint

def paint_smoked_darken(paint, shape, mask, seed, pm, bb):
    """Smoked tinted glass — cool spectral shift, noise-modulated density, subtle edge vignette."""
    h, w = shape
    base_darken = 0.15 * pm

    # Organic density variation (±35% around uniform tint)
    density = multi_scale_noise((h, w), [8, 16, 32], [0.4, 0.35, 0.25], seed + 2830)
    density = np.clip(density * 0.5 + 0.5, 0.35, 1.0)

    # Subtle edge vignette: up to +25% darkening at corners
    yg = (np.arange(h, dtype=np.float32) / h - 0.5)[:, np.newaxis]
    xg = (np.arange(w, dtype=np.float32) / w - 0.5)[np.newaxis, :]
    vignette = np.clip((xg ** 2 + yg ** 2) * 2.5, 0.0, 0.25)

    darken_field = base_darken * (density * 0.70 + vignette) * mask

    # Cool spectral shift: red absorbs 15% more than blue (automotive tint physics)
    result = paint.copy()
    result[:, :, 0] = np.clip(paint[:, :, 0] * (1.0 - darken_field * 1.15), 0.0, 1.0)
    result[:, :, 1] = np.clip(paint[:, :, 1] * (1.0 - darken_field * 1.00), 0.0, 1.0)
    result[:, :, 2] = np.clip(paint[:, :, 2] * (1.0 - darken_field * 0.85), 0.0, 1.0)
    return result

def paint_diamond_sparkle(paint, shape, mask, seed, pm, bb):
    """Diamond dust - extremely fine ultra-bright point sparkles."""
    np.random.seed(seed + 960)
    h, w = shape
    sparkle = (np.random.rand(h, w).astype(np.float32) > 0.997).astype(np.float32) * 0.08 * pm
    paint = np.clip(paint + sparkle[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


def paint_plasma_shift(paint, shape, mask, seed, pm, bb):
    """Plasma metal - glowing electric vein structure in blue/magenta.
    FIXED WEAK-022: Replaced invisible 4% RGB shift with FBM sin-vein plasma pattern.
    - FBM + sin(fbm*8) creates branching glowing plasma vein shapes
    - Vein pixels push toward electric blue/magenta (H=220-270, S=0.85) at high saturation
    - Blend at 0.50 weight — dramatic and clearly visible plasma finish"""
    h, w = shape
    # FBM field as plasma base
    fbm = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.35, 0.25], seed + 5551)
    # sin(fbm*8) creates narrow bright vein structures at FBM ridge crests
    vein_raw = np.sin(fbm * 8.0 * np.pi)
    # Normalize vein: positive peaks = plasma veins, negative = dark body
    vein = np.clip(vein_raw * 0.5 + 0.5, 0, 1)
    # Sharpen the vein edges: raise to power to concentrate bright areas
    vein = np.power(vein, 2.5)

    # Plasma vein color: electric blue/violet range H=220-270, S=0.85, V varies with vein intensity
    # Body (vein=0) stays near base color; veins (vein=1) push to electric blue-magenta
    vein_hue = 0.62 + (fbm * 0.5 + 0.5) * 0.08  # H=223-252 (electric blue through violet)
    vein_sat = 0.85 * np.ones((h, w), dtype=np.float32)
    vein_val = 0.35 + vein * 0.65  # dark body to bright vein core

    vein_r, vein_g, vein_b = hsv_to_rgb_vec(vein_hue, vein_sat, vein_val)

    # Blend: vein intensity controls per-pixel blend weight (veins blend heavy, body light)
    blend = vein * 0.55 * pm  # max 0.55 at vein peak
    m = mask
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * m) + vein_r * blend * m, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * m) + vein_g * blend * m, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * m) + vein_b * blend * m, 0, 1)
    return paint


def paint_burnt_metal(paint, shape, mask, seed, pm, bb):
    """Burnt metal - titanium exhaust header oxide color gradient.
    FIXED WEAK-023: Full 6-stop titanium oxide progression (silver→straw→amber→purple→blue→gray-blue)
    using FBM-warped linear heat gradient. Blend at 0.65 so base livery color shows through.
    Heat progression matches real titanium oxide bands from temperature increase."""
    h, w = shape
    # FBM-warped linear gradient simulating temperature field (high heat at left/top edge)
    base_grad = np.linspace(1.0, 0.0, w, dtype=np.float32)[np.newaxis, :]  # horizontal gradient
    # 2-octave FBM warp for organic irregularity
    warp = multi_scale_noise(shape, [16, 32], [0.6, 0.4], seed + 5561)
    heat_val = np.clip(base_grad + warp * 0.35, 0, 1)

    # 6-stop titanium oxide color progression (HSV): heat_val 0→1 = coolest→hottest
    # Stop 0 (heat=0.0): gray-blue (hot end, fully oxidized) H=200, S=0.15, V=0.55
    # Stop 1 (heat=0.2): deep blue H=220, S=0.85, V=0.65
    # Stop 2 (heat=0.4): purple H=280, S=0.75, V=0.60
    # Stop 3 (heat=0.6): amber H=30, S=0.85, V=0.80
    # Stop 4 (heat=0.8): straw/gold H=45, S=0.70, V=0.90
    # Stop 5 (heat=1.0): silver (fresh metal, no tint) H=0, S=0.0, V=0.85
    stops_h = np.array([200.0, 220.0, 280.0,  30.0,  45.0,   0.0], dtype=np.float32) / 360.0
    stops_s = np.array([0.15,   0.85,   0.75,  0.85,  0.70,   0.0], dtype=np.float32)
    stops_v = np.array([0.55,   0.65,   0.60,  0.80,  0.90,   0.85], dtype=np.float32)
    n_stops = len(stops_h)

    # Piecewise interpolation along the 6 stops
    t = heat_val * (n_stops - 1)
    idx = np.clip(t.astype(np.int32), 0, n_stops - 2)
    frac = t - idx.astype(np.float32)

    out_h = np.zeros((h, w), dtype=np.float32)
    out_s = np.zeros((h, w), dtype=np.float32)
    out_v = np.zeros((h, w), dtype=np.float32)
    for i in range(n_stops - 1):
        seg = (idx == i)
        f = frac[seg]
        out_h[seg] = stops_h[i] * (1 - f) + stops_h[i + 1] * f
        out_s[seg] = stops_s[i] * (1 - f) + stops_s[i + 1] * f
        out_v[seg] = stops_v[i] * (1 - f) + stops_v[i + 1] * f

    r_ox, g_ox, b_ox = hsv_to_rgb_vec(out_h, out_s, out_v)
    blend = 0.65 * pm
    m = mask
    paint[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * m) + r_ox * blend * m, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * m) + g_ox * blend * m, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * m) + b_ox * blend * m, 0, 1)
    return paint


def paint_mercury_pool(paint, shape, mask, seed, pm, bb):
    """Mercury - liquid metal pooling effect, heavy desaturation with bright caustics."""
    mean_c = (paint[:,:,0] + paint[:,:,1] + paint[:,:,2]) / 3.0
    desat = 0.5 * pm
    for c in range(3):
        paint[:,:,c] = np.clip(paint[:,:,c] * (1 - desat * mask) + mean_c * desat * mask, 0, 1)
    caustic = multi_scale_noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5571)
    bright = np.clip(caustic, 0, 1) * 0.10 * pm  # FIX: was 0.03 (invisible caustics)
    paint = np.clip(paint + bright[:,:,np.newaxis] * mask[:,:,np.newaxis], 0, 1)
    return paint


def paint_electric_blue_tint(paint, shape, mask, seed, pm, bb):
    """Electric blue tint - icy blue metallic color push.
    FIX: shift was 0.03 (1.5% blue, invisible). Raised to 0.12 for visible icy tint."""
    shift = 0.12 * pm
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
    """Scuffed satin: WEAK-015 FIX — physically corrected to be rougher/duller than clean satin.
    Scuffing removes surface gloss: slight desaturation (~8%) + micro-abrasion darkening texture.
    Previously was paint * 0.96 + 0.03 (actually BRIGHTER than satin — physically wrong)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    gray = paint.mean(axis=2, keepdims=True)
    # ~8% desaturation: scuffing removes vibrancy
    desat = paint * 0.92 + gray * 0.08
    # Slight darkening (~3%) for wear absorption
    darkened = np.clip(desat * 0.97, 0, 1)
    # Fine micro-abrasion noise: very subtle darker scratch marks
    micro = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 5901)
    darkened = np.clip(darkened * (1.0 - micro[:, :, np.newaxis] * 0.04 * pm), 0, 1)
    return darkened * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis])

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
    """Dual Shift chameleon -- HSV hue rotation at moderate frequency, 0.4 blend weight.
    BONUS FIX: upgraded from lazy RGB ±0.25 add to proper HSV hue rotation.
    Uses bb (body brightness) as viewing-angle proxy. Shadow areas shift hue one direction,
    highlights shift hue the other, creating the genuine two-tone chameleon flip effect."""
    if pm == 0.0:
        return paint
    h, w = shape
    mask3 = mask[:,:,np.newaxis]

    # Spatial noise to prevent perfectly uniform shift (moderate frequency ~16 cycles)
    n = multi_scale_noise(shape, [16, 32], [0.5, 0.5], seed + 7700)
    angle_field = np.clip(bb + n * 0.15, 0, 1)

    # Smooth cubic interpolation (smoothstep) for premium feel
    t = angle_field * angle_field * (3.0 - 2.0 * angle_field)

    # HSV hue rotation: shadows shift -60 deg (toward cyan-teal), highlights +60 deg (toward magenta)
    # This creates the genuine chameleon two-tone color flip
    hue_shift = (t - 0.5) * (120.0 / 360.0)  # -60 to +60 degrees, normalized to 0-1 hue wheel

    # Convert paint to HSV
    r, g, b = paint[:,:,0], paint[:,:,1], paint[:,:,2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin + 1e-8
    hue = np.zeros((h, w), dtype=np.float32)
    m_r = (cmax == r)
    m_g = (cmax == g) & ~m_r
    m_b = ~m_r & ~m_g
    hue[m_r] = ((g[m_r] - b[m_r]) / delta[m_r]) % 6 / 6
    hue[m_g] = ((b[m_g] - r[m_g]) / delta[m_g] + 2) / 6
    hue[m_b] = ((r[m_b] - g[m_b]) / delta[m_b] + 4) / 6
    sat = delta / (cmax + 1e-8)
    val = cmax

    # Rotate hue by angle-dependent shift, apply to masked area
    new_hue = (hue + hue_shift * mask) % 1.0
    new_rgb = np.stack(hsv_to_rgb_vec(new_hue, sat, val), axis=2)

    # Blend at 0.4 weight — vivid two-tone shift without obliterating base color
    blend = np.clip(pm * 0.4, 0, 1)
    paint[:,:,:3] = paint[:,:,:3] * (1 - mask3 * blend) + new_rgb * (mask3 * blend)

    # Deepen shadows slightly for wet-candy depth chameleon paints have
    shadow_deepen = (1.0 - angle_field) * 0.15 * pm * mask
    paint[:,:,0] = np.clip(paint[:,:,0] * (1.0 - shadow_deepen), 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] * (1.0 - shadow_deepen), 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] * (1.0 - shadow_deepen), 0, 1)

    return np.clip(paint, 0, 1).astype(np.float32)

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
    R_arr = np.clip(np.full(shape, 25.0, dtype=np.float32) + noise * 150.0 * sm, 15, 255)  # GGX floor: R>=15
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
    R_arr = np.full(shape, 15.0, dtype=np.float32) + fractures * 25.0 * sm  # GGX-FIX: was 4.0
    CC_arr = np.full(shape, 16.0, dtype=np.float32)
    return M_arr, R_arr, CC_arr

def spec_cg_porcelain(shape, seed, sm, base_m, base_r):
    h, w = shape
    crackle = np.clip(1.0 - np.abs(_noise(shape, [16, 32], [0.5, 0.5], seed + 402) - 0.5) * 50.0, 0, 1)

    # Crackles break the clearcoat
    M_arr = np.full(shape, 0.0, dtype=np.float32)
    R_arr = np.full(shape, 15.0, dtype=np.float32) + crackle * 93.0 * sm  # GGX-FIX: was 8.0, adjusted range
    CC_arr = np.full(shape, 16.0, dtype=np.float32) - crackle * 16.0 * sm
    return M_arr, R_arr, CC_arr

def spec_cg_glass(shape, seed, sm, base_m, base_r):
    # Flawless mirror spec map without metallic reflectivity
    M_arr = np.full(shape, 0.0, dtype=np.float32)
    R_arr = np.full(shape, 15.0, dtype=np.float32) # GGX-FIX: was 0.0, below GGX floor
    CC_arr = np.full(shape, 16.0, dtype=np.float32) # Factory clear
    return M_arr, R_arr, CC_arr

# ======================================================================
# 2026 MASS UPGRADE NEW FUNCTIONS
# ======================================================================

def paint_liquid_metal_flow_v2(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid(shape)
    flow = np.sin(x * 0.15 + np.sin(y * 0.08) * 3.0) * 0.5 + 0.5
    grain = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed)
    M = np.clip(180 + flow * 75.0, 0, 255).astype(np.float32)
    R = np.clip(15 + grain * 25.0, 15, 255).astype(np.float32)
    return M, R, np.full(shape, 16.0, dtype=np.float32)  # CC=16 max clearcoat for exotic metals

def paint_tungsten_heavy(paint, shape, mask, seed, pm, bb):

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

    flake1 = multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed+1)
    flake2 = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed+5)
    pearl = np.clip((flake1 * 0.7 + flake2 * 0.3), 0, 1)
    paint[:,:,0] = np.clip(paint[:,:,0] + pearl * 0.08 * pm * mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + pearl * 0.08 * pm * mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + pearl * 0.12 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.5, 0, 1)

def spec_oem_automotive(shape, seed, sm, base_m, base_r):
    """OEM Automotive — factory-realistic orange-peel clearcoat variation.
    FIX: Now uses base_m/base_r instead of hardcoded values so dielectric
    bases (ambulance_white M=0) stay dielectric in the spec."""
    peel = multi_scale_noise(shape, [16, 32], [0.7, 0.3], seed)
    M = np.clip(base_m + peel * 10.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + peel * 20.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + peel * 8.0, 16, 255).astype(np.float32)  # max gloss with slight peel variation
    return M, R, CC

def paint_mil_spec_od_v2(paint, shape, mask, seed, pm, bb):

    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * 0.4 + gray * 0.4
    paint[:,:,0] = np.clip(paint[:,:,0] + 0.15*pm*mask, 0, 1)
    paint[:,:,1] = np.clip(paint[:,:,1] + 0.16*pm*mask, 0, 1)
    paint[:,:,2] = np.clip(paint[:,:,2] + 0.05*pm*mask, 0, 1)
    grime = multi_scale_noise(shape, [8, 16], [0.6, 0.4], seed)
    paint = np.clip(paint - grime[:,:,np.newaxis]*0.05*pm*mask[:,:,np.newaxis], 0, 1)
    return np.clip(paint + bb * 0.2, 0, 1)

def spec_industrial_tactical(shape, seed, sm, base_m, base_r):

    grit = multi_scale_noise(shape, [8, 16, 32], [0.5, 0.3, 0.2], seed)
    M = np.clip(5 + grit * 40.0, 0, 255).astype(np.float32)
    R = np.clip(170 + grit * 85.0, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 180.0, dtype=np.float32)  # CC=180 dead flat military/tactical

def paint_matte_wrap_v2(paint, shape, mask, seed, pm, bb):
    from scipy.ndimage import gaussian_filter
    base = paint.copy()
    smoothed = gaussian_filter(base, sigma=[2, 2, 0])
    target = base * 0.2 + smoothed * 0.8
    blend = np.clip(pm, 0.0, 1.0)
    paint = base * (1.0 - mask[:, :, np.newaxis] * blend) + target * (mask[:, :, np.newaxis] * blend)
    return np.clip(paint + bb * 0.15, 0, 1)

def spec_satin_wrap(shape, seed, sm, base_m, base_r):

    ripple = multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed)
    M = np.clip(10 + ripple * 5.0, 0, 255).astype(np.float32)
    R = np.clip(120 + ripple * 20.0, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 60.0, dtype=np.float32)  # CC=60 satin wrap coating

def paint_sun_fade_v2(paint, shape, mask, seed, pm, bb):

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

    rot = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.3, 0.3], seed)
    M = np.where(rot > 0.6, 90.0, 15.0).astype(np.float32)
    R = np.where(rot > 0.6, 220.0, 90.0).astype(np.float32)
    # WARN-GGX-006 FIX: CC=0.0 was triggering metallised/chrome renderer path on ~60% of pixels.
    # Weathered surfaces have dull clearcoat (130 = very dull), with remnant-gloss pockets (24).
    CC = np.where(rot < 0.4, 24.0, 130.0).astype(np.float32)
    return M, R, CC

def paint_race_day_gloss_v2(paint, shape, mask, seed, pm, bb):

    paint = np.clip(paint * 1.1, 0, 1)
    dust = multi_scale_noise(shape, [2,4,8], [0.5, 0.3, 0.2], seed+1)
    dust_mask = np.where(dust > 0.8, 1, 0).astype(np.float32)
    paint = np.clip(paint - dust_mask[:,:,np.newaxis]*0.3*mask[:,:,np.newaxis]*pm, 0, 1)
    return np.clip(paint + bb * 0.7, 0, 1)

def spec_racing_heritage(shape, seed, sm, base_m, base_r):
    """Racing Heritage — uses base_m/base_r as anchors with scuff variation.
    FIX: Was hardcoded M=100/R=15 ignoring base values. Now show-car bases
    (high M, low R) stay glossy and worn bases (low M, high R) stay rough."""
    scuff = multi_scale_noise(shape, [2, 4, 8], [0.4, 0.4, 0.2], seed)
    M = np.clip(base_m + scuff * 20.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + scuff * 25.0 * sm, 15, 255).astype(np.float32)
    CC = np.clip(16.0 + scuff * 10.0, 16, 255).astype(np.float32)
    return M, R, CC

def paint_quantum_black_v2(paint, shape, mask, seed, pm, bb):

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

    void = multi_scale_noise(shape, [1, 2, 4], [0.33, 0.33, 0.34], seed+99)
    M = np.where(void > 0.8, 255.0, 0.0).astype(np.float32)
    R = np.where(void > 0.8, 0.0, 255.0).astype(np.float32)
    CC = np.where(void > 0.95, 255.0, 0.0).astype(np.float32)
    return M, R, CC

def paint_bentley_silver_v2(paint, shape, mask, seed, pm, bb):

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
    """Premium Luxury — ultra-fine flake with maximum gloss clearcoat.
    CRITICAL FIX: CC was 255 (dead flat) — should be 16-20 (max gloss).
    These are the glossiest paints in the world."""
    flake = multi_scale_noise(shape, [1, 2], [0.8, 0.2], seed)
    M = np.clip(180 + flake * 75.0, 0, 255).astype(np.float32)
    R = np.clip(15 + flake * 5.0, 15, 255).astype(np.float32)  # GGX floor + fixed base 5→15
    CC = np.clip(16.0 + flake * 4.0, 16, 255).astype(np.float32)  # FIXED: was 255 (dead flat) → 16-20 (max gloss)
    return M, R, CC

def spec_metallic_standard(shape, seed, sm, base_m, base_r):

    flake = multi_scale_noise(shape, [1, 2], [0.6, 0.4], seed+1)
    M = np.clip(120 + flake * 80.0, 0, 255).astype(np.float32)
    R = np.clip(30 - flake * 15.0, 15, 255).astype(np.float32)  # GGX floor — MiMo audit catch
    CC = np.full(shape, 24.0, dtype=np.float32)
    return M, R, CC



def spec_brushed_grain(shape, seed, sm, base_m, base_r):

    
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

    
    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Extremely dense, warm, thick mirror. Rolling cloudy spec depth but no grain/no hard pits.
    cloud = multi_scale_noise((h, w), [32, 64, 128], [0.4, 0.4, 0.2], seed + 301)
    
    M = np.clip(base_m - cloud * 25.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r + cloud * 8.0 * sm, 0, 255).astype(np.float32)
    CC = np.full((h, w), 16.0, dtype=np.float32)  # Registry says CC=16
    return M, R, CC



# --- EXTREME & EXPERIMENTAL CUSTOM MATH ---

def paint_bioluminescent(paint, shape, mask, seed, pm, bb):

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

    M = np.full(shape, 0.0, dtype=np.float32)
    n = multi_scale_noise(shape, [8, 16], [0.5, 0.5], seed + 502)
    R = np.clip(15.0 + n * 20.0 * sm, 15, 255).astype(np.float32)
    return M, R, np.full(shape, 16.0, dtype=np.float32)

def paint_dark_matter(paint, shape, mask, seed, pm, bb):

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

    swirl = multi_scale_noise(shape, [32, 64], [0.5, 0.5], seed + 601)
    swirl = np.clip(swirl * 0.5 + 0.5, 0, 1)
    M = np.clip(swirl * 255.0 * sm, 0, 255).astype(np.float32)
    R = np.where(swirl > 0.6, 10.0, 240.0).astype(np.float32)
    return M, R, np.full(shape, 220.0, dtype=np.float32)  # CC=220 dull dark swirl (was 0=mirror)

def paint_black_hole_accretion(paint, shape, mask, seed, pm, bb):

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
    """Accretion ring: void-black center + chrome mirror ring at ~70% radius.
    Void zone: M=base_m(0), R=base_r(255), CC=255 — dead matte absorption.
    Ring zone: M=255, R=2, CC=16 — chrome mirror, max gloss (orbital light burst)."""
    h, w = shape
    yy = np.arange(h, dtype=np.float32) - h * 0.5
    xx = np.arange(w, dtype=np.float32) - w * 0.5
    Y, X = np.meshgrid(yy, xx, indexing='ij')
    r = np.sqrt(Y**2 + X**2) / (min(h, w) * 0.45)  # normalized: r=1 at ~inner region edge
    # Accretion ring Gaussian at r=0.72 from center
    ring = np.exp(-((r - 0.72) ** 2) / (2 * 0.07 ** 2))
    # Gravitational lensing sparkle within the ring
    n = multi_scale_noise((h, w), [3, 6], [0.5, 0.5], seed + 701)
    n_norm = np.clip(n * 0.5 + 0.5, 0, 1)
    ring_s = np.clip(ring * (0.7 + n_norm * 0.3) * sm, 0, 1)
    # M: void=base_m(0 dielectric), ring=255 full chrome
    M = np.clip(float(base_m) * (1.0 - ring_s) + 255.0 * ring_s, 0, 255).astype(np.float32)
    # R: void=base_r(255 ultra-rough), ring=2 mirror
    R = np.clip(float(base_r) * (1.0 - ring_s) + 2.0 * ring_s, 0, 255).astype(np.float32)
    # CC: void=255 dead dull, ring=16 max gloss
    CC = np.clip(255.0 * (1.0 - ring_s) + 16.0 * ring_s, 16, 255).astype(np.float32)
    return M, R, CC

def paint_quantum_black(paint, shape, mask, seed, pm, bb):

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

    M = np.zeros(shape, dtype=np.float32)
    R = np.full(shape, 255.0, dtype=np.float32)
    sparkle = (multi_scale_noise(shape, [1, 2], [0.5, 0.5], seed + 801) > 0.98).astype(np.float32)
    M = np.where(sparkle > 0, 255.0, M)
    R = np.where(sparkle > 0, 0.0, R)
    return M, R, np.full(shape, 240.0, dtype=np.float32)  # CC=240 void dull (was 0=mirror)

def paint_absolute_zero(paint, shape, mask, seed, pm, bb):

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

    n1 = multi_scale_noise(shape, [4, 8], [0.6, 0.4], seed + 901)
    n2 = multi_scale_noise(shape, [2, 4], [0.5, 0.5], seed + 902)
    frost = np.clip(np.abs(np.sin(n1 * 20.0) + np.cos(n2 * 20.0)), 0, 1)
    M = np.clip(base_m + frost * 100.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(base_r - frost * 80.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full(shape, 40.0, dtype=np.float32)



# --- SOLAR PANEL, HOLOGRAPHIC, PLASMA CORE ---

def paint_solar_panel(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    # Foil-like grain
    grain = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + 3001)
    grain = np.clip(grain, 0, 1)
    
    M = np.clip(200.0 + grain * 55.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(15.0 + grain * 10.0 * sm, 15, 255).astype(np.float32)
    return M, R, np.full((h, w), 16.0, dtype=np.float32)


def paint_plasma_core(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    marks = multi_scale_noise((h, w), [4, 16], [0.7, 0.3], seed + 50)
    
    # Exposed steel is highly metallic, oxidized/recessed areas are rough and less metallic
    M = np.clip(60.0 + marks * 140.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(160.0 - marks * 80.0 * sm, 15, 255).astype(np.float32)  # GGX floor: R>=15
    return M, R, np.full((h, w), 130.0, dtype=np.float32)  # CC=130 worn military plate

def paint_battleship_gray_v2(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h,w))
    streaks = np.sin(x * 0.1 + multi_scale_noise((h,w), [16], [1.0], seed) * 2.0) * 0.5 + 0.5
    
    # Sea-weathered paint - dull with slight directional variance
    M = np.full((h, w), 20.0, dtype=np.float32)
    R = np.clip(140.0 + streaks * 30.0 * sm, 15, 255).astype(np.float32)  # GGX floor: R>=15
    CC = np.full((h, w), 120.0, dtype=np.float32)  # CC=120 weathered dull (was 10=near-chrome)
    return M, R, CC

def paint_gunship_gray_v2(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    ram_grit = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 12)
    
    # RAM coating is highly porous/rough and barely metallic
    M = np.full((h, w), 5.0, dtype=np.float32)
    R = np.clip(200.0 + ram_grit * 50.0 * sm, 15, 255).astype(np.float32)  # GGX floor: R>=15
    return M, R, np.full((h, w), 190.0, dtype=np.float32)  # CC=190 near-flat RAM

def paint_mil_spec_od_v3(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    field_grime = multi_scale_noise((h, w), [8, 16, 32], [0.5, 0.3, 0.2], seed + 100)
    
    # Flat durable military paint, dirt adds roughness
    M = np.full((h, w), 2.0, dtype=np.float32)
    R = np.clip(180.0 + field_grime * 60.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 195.0, dtype=np.float32)  # CC=195 dead flat military

def paint_mil_spec_tan_v2(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    dust = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 200)
    
    M = np.full((h, w), 0.0, dtype=np.float32)
    R = np.clip(200.0 + dust * 55.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 200.0, dtype=np.float32)  # CC=200 dead flat desert


def paint_submarine_black_v2(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    streaks = multi_scale_noise((h, w), [4, 16], [0.8, 0.2], seed + 300)
    
    # Highly dielectric, very rough, but varying slightly from wrap stretching
    M = np.full((h, w), 5.0, dtype=np.float32)
    R = np.clip(210.0 + streaks * 20.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 200.0, dtype=np.float32)  # CC=200 murdered-out dead flat


def paint_cerakote_v2(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    grit = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 301)
    
    # Cured ceramic is mostly dielectric but very hard/uniform
    M = np.full((h, w), 30.0, dtype=np.float32)
    R = np.clip(160.0 + grit * 40.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 170.0, dtype=np.float32)  # CC=170 flat ceramic coating


def paint_duracoat_v2(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    ripples = multi_scale_noise((h, w), [16, 32], [0.6, 0.4], seed + 302)
    
    # Less rough than Cerakote, highly uneven due to air-dry pooling
    M = np.full((h, w), 20.0, dtype=np.float32)
    R = np.clip(130.0 + ripples * 60.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 150.0, dtype=np.float32)  # CC=150 tactical epoxy


def paint_martian_regolith(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    clumps = multi_scale_noise((h, w), [4, 8, 32], [0.4, 0.4, 0.2], seed + 303)
    glass_shards = multi_scale_noise((h, w), [1], [1.0], seed + 304)
    
    # Almost entirely rough dirt
    R = np.clip(220.0 + clumps * 35.0 * sm, 0, 255).astype(np.float32)
    
    # Occasional bright crystalline spec hit in the dirt
    M = np.where(glass_shards > 0.98, 200.0, 0.0).astype(np.float32) * sm
    return M, R, np.full((h, w), 200.0, dtype=np.float32)  # CC=200 dead flat Martian dust


def paint_powder_coat_v2(paint, shape, mask, seed, pm, bb):
    # Very solid, thick color layer. Saturates and darkens slightly.
    paint = np.clip(paint * 1.1, 0, 1)
    # The major defining feature of powder coat is the specular orange-peel, so base is relatively clean
    return np.clip(paint + bb * 0.2, 0, 1)

def spec_powder_coat_v2(shape, seed, sm, base_m, base_r):

    h, w = shape[:2] if len(shape) > 2 else shape
    
    # Heavy, thick orange-peel bubbling from cured polyester powder
    peel = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 305)
    
    M = np.full((h, w), 10.0, dtype=np.float32)
    R = np.clip(90.0 + peel * 70.0 * sm, 0, 255).astype(np.float32)
    # Give it a thick clearcoat property to emulate baked finish
    CC = np.clip(50.0 - peel * 20.0 * sm, 0, 255).astype(np.float32)
    return M, R, CC


def paint_sandblasted_v2(paint, shape, mask, seed, pm, bb):

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

    h, w = shape[:2] if len(shape) > 2 else shape
    blast_grit = multi_scale_noise((h, w), [1, 2], [0.7, 0.3], seed + 306)
    
    # Pure metal, but scattered everywhere so it's both highly metallic AND highly rough
    M = np.clip(180.0 + blast_grit * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(150.0 + blast_grit * 50.0 * sm, 0, 255).astype(np.float32)
    return M, R, np.full((h, w), 155.0, dtype=np.float32)  # CC=155 raw stripped metal


# ============================================================
# EXOTIC BASE FINISHES — RESEARCH-008 (6 new finishes)
# Added 2026-03-29
# ============================================================

# ── 1. ChromaFlair "Light Shift" ─────────────────────────────
def spec_chromaflair_base(shape, seed, sm, base_m, base_r):
    """ChromaFlair base_spec_fn: FBM-driven flake field, near-mirror roughness.
    Signature: (shape, seed, sm, base_m, base_r) -> (M_arr, R_arr, CC_arr)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    flake_field = multi_scale_noise(sh, [4, 8, 16], [0.4, 0.35, 0.25], seed + 300)
    flake2      = multi_scale_noise(sh, [2, 4],     [0.6, 0.4],         seed + 301)
    flake_combined = flake_field * 0.65 + flake2 * 0.35
    M_arr  = np.clip(180.0 + flake_combined * 60.0 * sm, 0, 255).astype(np.float32)
    R_arr  = np.clip(  8.0 + flake_combined * 12.0 * sm, 15, 255).astype(np.float32)  # GGX floor: R>=15
    CC_arr = np.clip( 16.0 + flake_combined *  6.0,      16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def paint_chromaflair(paint, shape, mask, seed, pm, bb):
    """ChromaFlair 3-angle color flip via multi-stop hue rotation.
    Angle proxy = large-scale FBM field (simulates viewing angle variation).
    Low angle (<0.33): base color unchanged.
    Mid angle (0.33-0.66): interpolate toward hue+120 deg.
    High angle (>0.66): interpolate toward hue+240 deg."""
    h, w = shape
    # Angle proxy: large-scale FBM
    angle_proxy = multi_scale_noise((h, w), [32, 64, 128], [0.5, 0.3, 0.2], seed + 310)
    angle_proxy = np.clip(angle_proxy * 0.5 + 0.5, 0, 1)  # 0-1
    # Flake density drives blend strength
    flake_dens = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.35, 0.25], seed + 311)
    flake_dens = np.clip(flake_dens * 0.5 + 0.5, 0, 1)

    # Per-pixel HSV of current paint
    hsv = rgb_to_hsv_array(paint)
    h_ch = hsv[:, :, 0]  # hue 0-1
    s_ch = hsv[:, :, 1]
    v_ch = hsv[:, :, 2]

    # Secondary color: hue +120/360
    h_sec = (h_ch + 120.0 / 360.0) % 1.0
    r_sec, g_sec, b_sec = hsv_to_rgb_vec(h_sec, s_ch, v_ch)
    # Tertiary color: hue +240/360
    h_ter = (h_ch + 240.0 / 360.0) % 1.0
    r_ter, g_ter, b_ter = hsv_to_rgb_vec(h_ter, s_ch, v_ch)

    # Blend weights
    mid_w  = np.clip((angle_proxy - 0.33) / 0.33, 0, 1) * (angle_proxy < 0.66).astype(np.float32)
    high_w = np.clip((angle_proxy - 0.66) / 0.34, 0, 1)
    # Flake density amplifies the shift
    mid_w  = mid_w  * flake_dens * pm * mask
    high_w = high_w * flake_dens * pm * mask

    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - mid_w - high_w) + r_sec * mid_w + r_ter * high_w, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - mid_w - high_w) + g_sec * mid_w + g_ter * high_w, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - mid_w - high_w) + b_sec * mid_w + b_ter * high_w, 0, 1)
    return paint


# ── 2. Xirallic "Crystal Flake" ──────────────────────────────
def spec_xirallic_base(shape, seed, sm, base_m, base_r):
    """Xirallic base_spec_fn: large sparse alumina flakes with steep M falloff at edges.
    Signature: (shape, seed, sm, base_m, base_r) -> (M_arr, R_arr, CC_arr)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Coarse noise creates 10-20 sparse flake regions
    flake_coarse = multi_scale_noise(sh, [32, 64], [0.6, 0.4], seed + 320)
    # Threshold to isolate sparse flake peaks (top ~15% = flake areas)
    flake_coarse_n = np.clip(flake_coarse * 0.5 + 0.5, 0, 1)
    flake_thresh = np.clip((flake_coarse_n - 0.82) / 0.18, 0, 1)  # steep peak
    # Fine inter-flake noise
    inter_noise = multi_scale_noise(sh, [8, 16], [0.5, 0.5], seed + 321)
    inter_noise_n = np.clip(inter_noise * 0.5 + 0.5, 0, 1)

    # M: flake center 240+, flake edge drops toward 60, inter-flake 80-100
    M_inter = 80.0 + inter_noise_n * 20.0
    M_flake = 240.0 + flake_thresh * 15.0 * sm
    M_arr = np.clip(M_inter * (1 - flake_thresh) + M_flake * flake_thresh, 0, 255).astype(np.float32)

    # R: very low on flake surface, slightly higher between flakes
    R_inter = 30.0 + inter_noise_n * 20.0
    R_flake = 8.0 + (1 - flake_thresh) * 7.0
    R_arr = np.clip(R_inter * (1 - flake_thresh) + R_flake * flake_thresh, 15, 255).astype(np.float32)  # GGX floor: flake zones were hitting R=8

    CC_arr = np.full((h, w), 18.0, dtype=np.float32)
    return M_arr, R_arr, CC_arr


def paint_xirallic(paint, shape, mask, seed, pm, bb):
    """Xirallic crystal flake - iron oxide blue-silver interference on flake areas.
    Flake areas: push toward blue-silver (H~210, S=0.3, high V).
    Inter-flake: slight desaturation + darkening (depth effect)."""
    h, w = shape
    flake_coarse = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 320)
    flake_coarse_n = np.clip(flake_coarse * 0.5 + 0.5, 0, 1)
    flake_thresh = np.clip((flake_coarse_n - 0.82) / 0.18, 0, 1)

    # Iron oxide signature: blue-silver at H=210, S=0.3
    blue_silver_r = np.full((h, w), 0.55, dtype=np.float32)
    blue_silver_g = np.full((h, w), 0.70, dtype=np.float32)
    blue_silver_b = np.full((h, w), 0.90, dtype=np.float32)

    flake_w = flake_thresh * 0.35 * pm * mask
    inter_desat = (1 - flake_thresh) * 0.08 * pm

    gray = paint.mean(axis=2)
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - flake_w) + blue_silver_r * flake_w
                              - inter_desat * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - flake_w) + blue_silver_g * flake_w
                              - inter_desat * 0.5 * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - flake_w) + blue_silver_b * flake_w, 0, 1)
    return paint


# ── 3. Anodized (new exotic version) ─────────────────────────
def spec_anodized_exotic_base(shape, seed, sm, base_m, base_r):
    """Anodized exotic base_spec_fn: oxide layer + fine hex pore modulation.
    Signature: (shape, seed, sm, base_m, base_r) -> (M_arr, R_arr, CC_arr)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    base_noise = multi_scale_noise(sh, [4, 8, 16], [0.3, 0.4, 0.3], seed + 330)
    base_n = np.clip(base_noise * 0.5 + 0.5, 0, 1)

    # Fine hex pore grid at tiny scale (~8px cells)
    y_idx = np.arange(h, dtype=np.float32).reshape(-1, 1) * np.ones((1, w), dtype=np.float32)
    x_idx = np.ones((h, 1), dtype=np.float32) * np.arange(w, dtype=np.float32).reshape(1, -1)
    cell = 8.0
    row = (y_idx / cell).astype(np.int32) % 2
    sx_hex = (x_idx + row * (cell * 0.5)) % cell
    sy_hex = y_idx % cell
    dist_hex = np.sqrt((sx_hex - cell * 0.5) ** 2 + (sy_hex - cell * 0.5) ** 2)
    hex_pore = np.clip(dist_hex / (cell * 0.5), 0, 1)  # 0=center, 1=edge
    # Pore modulation: ±15 amplitude
    pore_mod = (hex_pore - 0.5) * 15.0  # -7.5 to +7.5

    M_arr  = np.clip( 80.0 + base_n * 60.0 * sm + pore_mod, 0, 255).astype(np.float32)
    R_arr  = np.clip( 25.0 + base_n * 30.0 * sm + pore_mod * 0.5, 0, 255).astype(np.float32)
    CC_arr = np.clip( 35.0 + base_n * 30.0      + pore_mod * 0.5, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def paint_anodized_exotic(paint, shape, mask, seed, pm, bb):
    """Anodized exotic - desaturation + darkening + hex pore rim/center depth.
    WEAK-035 FIX: hex pore grid (same 8px cell geometry as spec_anodized_exotic_base)
    echoed into paint layer. Pore rims catch light (+4.2% at pm=1); pore centers dim
    slightly (-1.8%). Gives the paint spatial depth matching the spec channel."""
    h, w = shape[:2] if len(shape) > 2 else shape
    gray = paint.mean(axis=2, keepdims=True)
    desat = 0.12 * pm
    darken = 0.04 * pm

    # Hex pore grid — same 8px cell geometry as spec_anodized_exotic_base
    y_idx = np.arange(h, dtype=np.float32).reshape(-1, 1) * np.ones((1, w), dtype=np.float32)
    x_idx = np.ones((h, 1), dtype=np.float32) * np.arange(w, dtype=np.float32).reshape(1, -1)
    cell = 8.0
    row = (y_idx / cell).astype(np.int32) % 2
    sx_hex = (x_idx + row * (cell * 0.5)) % cell
    sy_hex = y_idx % cell
    dist_hex = np.sqrt((sx_hex - cell * 0.5) ** 2 + (sy_hex - cell * 0.5) ** 2)
    hex_pore = np.clip(dist_hex / (cell * 0.5), 0, 1)  # 0=center, 1=rim
    # pore_depth: rim=+0.042, center=-0.018 at pm=1.0
    pore_depth = ((hex_pore - 0.3) * 0.06 * pm)[:, :, np.newaxis]

    mask_3d = mask[:, :, np.newaxis]
    paint = np.clip(
        paint * (1 - desat * mask_3d) + gray * desat * mask_3d
        - darken * mask_3d
        + pore_depth * mask_3d,
        0, 1
    )
    return paint


# ── 4. Oil Slick (monolithic base) ───────────────────────────
def spec_oil_slick_base(shape, mask, seed, sm):
    """Oil Slick monolithic spec: extremely smooth, high metallic, FBM thickness variation."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[0], shape[1]
    thickness = multi_scale_noise((h, w), [4, 8, 16, 32], [0.3, 0.3, 0.2, 0.2], seed + 400)
    thickness_n = np.clip(thickness * 0.5 + 0.5, 0, 1)
    M = np.clip(180.0 + thickness_n * 60.0, 0, 255)
    R = np.clip(  4.0 + thickness_n *  8.0, 15, 255)  # GGX floor: oil slick was R=4-12, all below 15
    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = 16
    spec[:, :, 3] = 255
    return spec


def paint_oil_slick_full(paint, shape, mask, seed, pm, bb):
    """Oil Slick full monolithic paint: full 360 hue rotation thin-film over deep dark base.
    Dark base: desaturate + darken input.
    Thin-film: FBM film thickness drives full 360 hue rotation at S=0.9.
    Blend: 0.7 thin-film + 0.3 dark base."""
    h, w = shape
    # Dark base
    gray = paint.mean(axis=2)
    dark_base_r = np.clip(gray * 0.15, 0, 1)
    dark_base_g = np.clip(gray * 0.15, 0, 1)
    dark_base_b = np.clip(gray * 0.18, 0, 1)

    # Thin-film: FBM film thickness (4 octaves, tight scale)
    thickness = multi_scale_noise((h, w), [4, 8, 16, 32], [0.3, 0.3, 0.2, 0.2], seed + 400)
    thickness_n = np.clip(thickness * 0.5 + 0.5, 0, 1)
    # Full 360 hue rotation with S=0.9
    hue = thickness_n  # 0-1 maps to 0-360 deg
    sat = np.full((h, w), 0.9, dtype=np.float32)
    val = np.full((h, w), 0.75, dtype=np.float32)
    tf_r, tf_g, tf_b = hsv_to_rgb_vec(hue, sat, val)

    # Blend: 0.7 thin-film + 0.3 dark base
    blend_tf = 0.7 * pm * mask
    blend_db = 0.3 * pm * mask
    total = blend_tf + blend_db

    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - total) + tf_r * blend_tf + dark_base_r * blend_db, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - total) + tf_g * blend_tf + dark_base_g * blend_db, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - total) + tf_b * blend_tf + dark_base_b * blend_db, 0, 1)
    return paint


# ── 5. Thermal Titanium (monolithic base) ────────────────────
def spec_thermal_titanium(shape, mask, seed, sm):
    """Thermal Titanium monolithic spec: M/R vary with heat zone (oxide zones = lower M, higher R)."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[0], shape[1]
    heat = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 500)
    # Warp with secondary FBM for organic heat zones
    warp = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 501)
    heat_warped = np.clip((heat + warp * 0.3) * 0.5 + 0.5, 0, 1)
    # heat_warped=0 (cold/gray zone) -> high M, low R
    # heat_warped=1 (hot/oxide zone) -> lower M, higher R
    M = np.clip(220.0 - heat_warped * 60.0, 0, 255)
    R = np.clip( 15.0 + heat_warped * 30.0, 0, 255)
    CC = np.clip( 20.0 + heat_warped * 30.0, 16, 255)
    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def paint_thermal_titanium(paint, shape, mask, seed, pm, bb):
    """Thermal Titanium full monolithic paint: FBM-warped gradient heat color ramp.
    Color sequence: silver -> straw -> amber/gold -> purple -> deep blue -> gray-blue.
    No base color used — this IS the color."""
    h, w = shape
    heat = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 500)
    warp = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 501)
    heat_val = np.clip((heat + warp * 0.3) * 0.5 + 0.5, 0, 1)

    # Titanium oxide color ramp via HSV stops:
    # 0.00 silver (H=0.58, S=0.05, V=0.85)
    # 0.20 straw  (H=0.12, S=0.55, V=0.80)
    # 0.40 amber  (H=0.08, S=0.70, V=0.75)
    # 0.60 purple (H=0.78, S=0.65, V=0.55)
    # 0.80 deep blue (H=0.63, S=0.70, V=0.45)
    # 1.00 gray-blue (H=0.60, S=0.30, V=0.50)
    stops_h = np.array([0.58, 0.12, 0.08, 0.78, 0.63, 0.60], dtype=np.float32)
    stops_s = np.array([0.05, 0.55, 0.70, 0.65, 0.70, 0.30], dtype=np.float32)
    stops_v = np.array([0.85, 0.80, 0.75, 0.55, 0.45, 0.50], dtype=np.float32)
    n_stops = len(stops_h)

    t = heat_val * (n_stops - 1)
    idx = np.clip(t.astype(np.int32), 0, n_stops - 2)
    frac = t - idx.astype(np.float32)
    out_h = np.zeros((h, w), dtype=np.float32)
    out_s = np.zeros((h, w), dtype=np.float32)
    out_v = np.zeros((h, w), dtype=np.float32)
    for i in range(n_stops - 1):
        seg = (idx == i)
        f = frac[seg]
        out_h[seg] = stops_h[i] * (1 - f) + stops_h[i + 1] * f
        out_s[seg] = stops_s[i] * (1 - f) + stops_s[i + 1] * f
        out_v[seg] = stops_v[i] * (1 - f) + stops_v[i + 1] * f

    ti_r, ti_g, ti_b = hsv_to_rgb_vec(out_h, out_s, out_v)
    blend = pm * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + ti_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + ti_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + ti_b * blend, 0, 1)
    return paint


# ── 6. Galaxy Nebula (monolithic base) ───────────────────────
def spec_galaxy_nebula_base(shape, mask, seed, sm):
    """Galaxy Nebula monolithic spec: star metallic peaks + nebula dust region roughness."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[0], shape[1]
    nebula = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 600)
    nebula_val = np.clip(nebula * 0.5 + 0.5, 0, 1)

    # LCG star field (~0.4% density)
    flat_idx = np.arange(h * w, dtype=np.uint32)
    lcg = ((flat_idx * 1664525 + (seed & 0xFFFF)) * 22695477 + 1013904223) & 0xFFFFFFFF
    stars = (lcg % 1000 < 4).reshape(h, w).astype(np.float32)
    _simg = Image.fromarray(np.clip(stars * 255, 0, 255).astype(np.uint8), mode='L')
    stars_spread = np.array(_simg.filter(ImageFilter.GaussianBlur(radius=1.5))).astype(np.float32) / 255.0

    M_nebula = 80.0 + nebula_val * 70.0
    M_stars   = np.clip(stars_spread * 255.0 * 1.3, 0, 255)
    M = np.clip(M_nebula + M_stars, 0, 255)

    R_nebula = 40.0 + nebula_val * 40.0
    R_stars   = stars_spread * 255.0
    R = np.clip(R_nebula - R_stars * 0.9, 15, 255)  # GGX floor: star peaks were clipping to 2

    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((16.0 + nebula_val * 12.0) * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def paint_galaxy_nebula_full(paint, shape, mask, seed, pm, bb):
    """Galaxy Nebula full monolithic paint: near-black base + 4-region nebula colors + LCG star field.
    50% nebula color, 30% star contribution, 20% near-black void.
    5 nebula palette colors (blue, violet, rose, teal, gold) cycling through regions."""
    h, w = shape
    # Near-black base
    gray = paint.mean(axis=2)
    void_r = np.clip(gray * 0.06, 0, 1)
    void_g = np.clip(gray * 0.05, 0, 1)
    void_b = np.clip(gray * 0.10, 0, 1)

    # 4-region nebula color system
    region_field = multi_scale_noise((h, w), [64, 128, 256], [0.4, 0.35, 0.25], seed + 600)
    region_val = np.clip(region_field * 0.5 + 0.5, 0, 1)

    # Nebula palette: blue, violet, rose, teal, gold
    stops_h = np.array([240.0, 275.0, 340.0, 185.0, 45.0], dtype=np.float32) / 360.0
    stops_s = np.array([0.85,   0.80,  0.75,  0.80, 0.70], dtype=np.float32)
    stops_v = np.array([0.40,   0.45,  0.50,  0.42, 0.55], dtype=np.float32)
    n_stops = len(stops_h)

    t = region_val * (n_stops - 1)
    idx = np.clip(t.astype(np.int32), 0, n_stops - 2)
    frac = t - idx.astype(np.float32)
    out_h = np.zeros((h, w), dtype=np.float32)
    out_s = np.zeros((h, w), dtype=np.float32)
    out_v = np.zeros((h, w), dtype=np.float32)
    for i in range(n_stops - 1):
        seg = (idx == i)
        f = frac[seg]
        out_h[seg] = stops_h[i] * (1 - f) + stops_h[i + 1] * f
        out_s[seg] = stops_s[i] * (1 - f) + stops_s[i + 1] * f
        out_v[seg] = stops_v[i] * (1 - f) + stops_v[i + 1] * f

    # Density modulation (brighter in cloud cores)
    density = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 601)
    density = np.clip(density * 0.5 + 0.5, 0, 1)

    neb_r, neb_g, neb_b = hsv_to_rgb_vec(out_h, out_s, out_v)
    neb_r *= density; neb_g *= density; neb_b *= density

    # LCG star field (~0.4%)
    flat_idx = np.arange(h * w, dtype=np.uint32)
    lcg = ((flat_idx * 1664525 + (seed & 0xFFFF)) * 22695477 + 1013904223) & 0xFFFFFFFF
    lcg2 = ((lcg * 1664525) + 1013904223) & 0xFFFFFFFF
    star_mask_arr = (lcg % 1000 < 4).reshape(h, w)
    star_type = (lcg2 % 3).reshape(h, w)
    star_r = np.where(star_mask_arr, np.where(star_type == 1, 0.75, np.where(star_type == 2, 1.0, 0.95)), 0.0).astype(np.float32)
    star_g = np.where(star_mask_arr, np.where(star_type == 1, 0.82, np.where(star_type == 2, 0.95, 0.95)), 0.0).astype(np.float32)
    star_b = np.where(star_mask_arr, np.where(star_type == 1, 1.0,  np.where(star_type == 2, 0.70, 0.95)), 0.0).astype(np.float32)

    for _ch, _sarr in enumerate([star_r, star_g, star_b]):
        _img = Image.fromarray(np.clip(_sarr * 255, 0, 255).astype(np.uint8), mode='L')
        _bl = np.array(_img.filter(ImageFilter.GaussianBlur(radius=1.5))).astype(np.float32) / 255.0
        if _ch == 0: star_r_s = _bl
        elif _ch == 1: star_g_s = _bl
        else: star_b_s = _bl

    # Blend: 50% nebula + 30% stars + 20% void
    blend_neb  = 0.50 * pm * mask
    blend_star = 0.30 * pm * mask
    blend_void = 0.20 * pm * mask
    total = blend_neb + blend_star + blend_void

    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - total)
                              + neb_r * blend_neb + star_r_s * blend_star + void_r * blend_void, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - total)
                              + neb_g * blend_neb + star_g_s * blend_star + void_g * blend_void, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - total)
                              + neb_b * blend_neb + star_b_s * blend_star + void_b * blend_void, 0, 1)
    return paint


# ══════════════════════════════════════════════════════════════════════════════
# RESEARCH SESSION 6 — 23 New Finishes (9 Base + 8 Special + 6 Monolithic)
# Implemented 2026-03-29. All values calibrated for post-2025 S1 GGX renderer.
# B minimum=16, R minimum=2, candy G=15-25, chrome albedo near-white.
# ══════════════════════════════════════════════════════════════════════════════

# ── SECTION 3: 9 NEW BASE FINISHES ──────────────────────────────────────────

# 3.1 Alubeam / Liquid Mirror
def spec_alubeam_base(shape, seed, sm, base_m, base_r):
    """Alubeam / Liquid Mirror base spec: ultra-fine oriented aluminum flake — fills the
    'blurry chrome' zone between mirror and standard metallic.
    R=248 near-max metallic, G=15-25 tight-but-not-perfect blur, CC=16-18 max gloss.
    DISTINCT from chrome (G=2) and metallic (G=50): occupies the coherent-blur window."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Oriented flake: single-scale flake noise with directional character
    flake_x = multi_scale_noise(sh, [4, 8], [0.6, 0.4], seed + 701)
    flake_y = multi_scale_noise(sh, [4, 8], [0.6, 0.4], seed + 702)
    # Mercury-like coherent flow: combine axes for liquid appearance
    liquid_flow = np.clip((flake_x * 0.6 + flake_y * 0.4) * 0.5 + 0.5, 0, 1)
    # M: 240-250 (near-max, ultra-fine aluminum — not full chrome)
    M_arr = np.clip(240.0 + liquid_flow * 10.0 * sm, 0, 255).astype(np.float32)
    # R: 15-25 (tight blur — NOT zero, not standard metallic; the liquid mirror zone)
    R_arr = np.clip(15.0 + liquid_flow * 10.0 * sm, 2, 255).astype(np.float32)
    # CC: 16-18 (maximum gloss, slight pooling variation)
    CC_arr = np.clip(16.0 + liquid_flow * 2.0, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def paint_alubeam(paint, shape, mask, seed, pm, bb):
    """Alubeam / Liquid Mirror paint: near-white albedo with flowing silver tint.
    Oriented aluminum flakes produce a coherent silver-white liquid appearance.
    Preserves base hue but strongly desaturates toward silver-white."""
    h, w = shape
    flake_x = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 701)
    flake_y = multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 702)
    flow = np.clip((flake_x * 0.6 + flake_y * 0.4) * 0.5 + 0.5, 0, 1)
    # Near-white silver: target albedo ~(230-250, 230-250, 235-252)
    silver_r = np.clip(0.90 + flow * 0.08, 0, 1)
    silver_g = np.clip(0.90 + flow * 0.08, 0, 1)
    silver_b = np.clip(0.92 + flow * 0.06, 0, 1)
    blend = pm * 0.65 * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + silver_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + silver_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + silver_b * blend, 0, 1)
    return paint


# 3.2 Satin Candy (Matte Candy)
def spec_satin_candy_base(shape, seed, sm, base_m, base_r):
    """Satin Candy / Matte Candy base spec: R=0 (non-metallic), G=160-180 (satin range),
    CC forced to B=0-12 regardless of user B — the candy pigment under satin clear.
    DISTINCT from gloss candy (G=15-25, CC=16): this locks clearcoat to near-zero.
    The 'glowing coal' effect — color all, shine none."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Satin roughness variation — organic surface character (160-180)
    satin_fbm = multi_scale_noise(sh, [8, 16, 32], [0.5, 0.3, 0.2], seed + 710)
    M_arr = np.zeros((h, w), dtype=np.float32)  # R=0: non-metallic candy
    # G: 160-180 satin roughness — locked into the satin range, not gloss candy
    R_arr = np.clip(160.0 + satin_fbm * 20.0 * sm, 2, 255).astype(np.float32)
    # CC: 0-12 — explicitly below the 16 gloss threshold (satin clear behavior)
    # NOTE: Intentional dead-zone use — satin clear effectively kills gloss response
    CC_arr = np.clip(satin_fbm * 12.0, 0, 12).astype(np.float32)
    return M_arr, R_arr, CC_arr


def paint_satin_candy(paint, shape, mask, seed, pm, bb):
    """Satin Candy paint: boosts color saturation to vivid max — the color IS everything.
    Converts paint albedo to HSV, locks S=0.95-1.0, preserves hue and value.
    The 'glowing coal' visual: color saturates under overcast, zero reflection."""
    h, w = shape
    satin_fbm = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 711)
    # Convert each pixel to saturated color — pull S to near-max
    gray = paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114
    # Boost saturation: blend toward full-saturation version
    sat_boost = 0.95 + satin_fbm * 0.05
    r_sat = np.clip(paint[:, :, 0] + (paint[:, :, 0] - gray) * sat_boost * 2.0, 0, 1)
    g_sat = np.clip(paint[:, :, 1] + (paint[:, :, 1] - gray) * sat_boost * 2.0, 0, 1)
    b_sat = np.clip(paint[:, :, 2] + (paint[:, :, 2] - gray) * sat_boost * 2.0, 0, 1)
    blend = pm * 0.70 * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + r_sat * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + g_sat * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + b_sat * blend, 0, 1)
    return paint


# 3.3 Velvet / Suede Floc
def spec_velvet_floc_base(shape, seed, sm, base_m, base_r):
    """Velvet / Suede Floc base spec: true visual black — the car becomes a silhouette.
    G=245-255 eliminates all microfacet response entirely. R=0 (no metallic). CC=0.
    DISTINCT from matte (G=220, residual specular) — velvet at G=245+ is absolute.
    Forces G=245 regardless of sm input."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Micro flock variation — flock pile has some height variation (narrow range)
    flock_fbm = multi_scale_noise(sh, [2, 4], [0.6, 0.4], seed + 720)
    M_arr = np.zeros((h, w), dtype=np.float32)  # No metallic — pure light absorption
    # G: 245-255 — far above even deep matte, eliminates all specular
    R_arr = np.clip(245.0 + flock_fbm * 10.0, 2, 255).astype(np.float32)
    # CC: 0 — zero clearcoat (no coat on flock pile)
    CC_arr = np.zeros((h, w), dtype=np.float32)
    return M_arr, R_arr, CC_arr


def paint_velvet_floc(paint, shape, mask, seed, pm, bb):
    """Velvet paint: forces albedo to deep black (5-10 range) — the car is a shadow.
    Desaturates and darkens to near-black. Micro flock pile texture via fine noise."""
    h, w = shape
    flock_fbm = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 720)
    # Target: near-black (5-12 in 0-255 range = 0.020-0.047 float)
    black_r = np.clip(0.022 + flock_fbm * 0.018, 0, 1)
    black_g = np.clip(0.018 + flock_fbm * 0.018, 0, 1)
    black_b = np.clip(0.022 + flock_fbm * 0.018, 0, 1)
    blend = pm * 0.90 * mask  # Strong override — velvet fights user color
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + black_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + black_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + black_b * blend, 0, 1)
    return paint


# 3.4 Deep Pearl (Type III Three-Stage)
def spec_deep_pearl_base(shape, seed, sm, base_m, base_r):
    """Deep Pearl / Type III Three-Stage pearl base spec: three independently-seeded layers
    simulating base coat + mica midcoat + clearcoat.
    M=80-100 edge-weighted (flop simulation), R=50-70, CC=16-20 max gloss.
    DISTINCT from single-stage pearl (M=100, R=40): true flop requires edge weighting."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Three independent coat noise layers (different seeds)
    base_coat   = multi_scale_noise(sh, [8,  16], [0.55, 0.45], seed + 730)   # metallic silver base
    pearl_mid   = multi_scale_noise(sh, [20, 40], [0.55, 0.45], seed + 731)   # interference mica
    clear_top   = multi_scale_noise(sh, [32, 64], [0.55, 0.45], seed + 732)   # gloss clearcoat
    # Edge weighting: simulate flop angle shift (smooth gradient across surface)
    y_pos = np.linspace(0, 1, h, dtype=np.float32)
    x_pos = np.linspace(0, 1, w, dtype=np.float32)
    yy, xx = np.meshgrid(y_pos, x_pos, indexing='ij')
    edge_weight = np.clip(np.sin(yy * np.pi) * np.sin(xx * np.pi), 0, 1)
    # M: 80-100 with edge-weighted flop (face=80, edge=100)
    M_arr = np.clip(80.0 + edge_weight * 20.0 + pearl_mid * 15.0 * sm, 0, 255).astype(np.float32)
    # R: 50-70 (pearl surface micro-roughness — distinctly rougher than standard pearl)
    R_arr = np.clip(50.0 + pearl_mid * 20.0 * sm + base_coat * 10.0, 2, 255).astype(np.float32)
    # CC: 16-20 (glossy tri-coat clear with slight pooling)
    CC_arr = np.clip(16.0 + clear_top * 4.0, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def paint_deep_pearl(paint, shape, mask, seed, pm, bb):
    """Deep Pearl type-III paint: near-white/pastel albedo with warm/cool flop hint.
    Edge-weighted hue shift adds secondary color flop (gold, pink, or blue tint at angles).
    Preserves base color but pushes lightness toward pearl range."""
    h, w = shape
    pearl_mid = multi_scale_noise((h, w), [20, 40], [0.55, 0.45], seed + 731)
    clear_top  = multi_scale_noise((h, w), [32, 64], [0.55, 0.45], seed + 732)
    # Edge-weighted flop: warm gold hint at raking angles
    y_pos = np.linspace(0, 1, h, dtype=np.float32)
    x_pos = np.linspace(0, 1, w, dtype=np.float32)
    yy, xx = np.meshgrid(y_pos, x_pos, indexing='ij')
    edge_w = np.clip(1.0 - np.sin(yy * np.pi) * np.sin(xx * np.pi), 0, 1)
    # Gold flop color: (0.75, 0.60, 0.16)
    flop_r = 0.75 * edge_w * pearl_mid + 0.1
    flop_g = 0.60 * edge_w * pearl_mid + 0.1
    flop_b = 0.16 * edge_w * pearl_mid + 0.1
    # Lighten base toward pearl-white
    white_lift = np.clip(clear_top * 0.3, 0, 0.3)
    blend_flop  = pm * 0.25 * mask
    blend_white = pm * 0.30 * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend_flop - blend_white)
                              + flop_r * blend_flop + (paint[:, :, 0] + white_lift) * blend_white, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend_flop - blend_white)
                              + flop_g * blend_flop + (paint[:, :, 1] + white_lift) * blend_white, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend_flop - blend_white)
                              + flop_b * blend_flop + (paint[:, :, 2] + white_lift) * blend_white, 0, 1)
    return paint


# 3.5 Gunmetal Satin (Dark Industrial Metallic)
def spec_gunmetal_satin_base(shape, seed, sm, base_m, base_r):
    """Gunmetal Satin / Dark Industrial Metallic base spec: M=190-220, R=130-160, CC=20-40.
    The 'dark metallic without gloss' zone — not chrome, not anodized.
    CNC-machined aluminum / Ducati Streetfighter raw panel aesthetic.
    DISTINCT from standard gunmetal (M=220, R=40, high gloss): this is satin industrial."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Industrial surface: coarse grain FBM
    grain_coarse = multi_scale_noise(sh, [4,  8], [0.55, 0.45], seed + 740)
    grain_fine   = multi_scale_noise(sh, [16, 32], [0.55, 0.45], seed + 741)
    combined     = grain_coarse * 0.65 + grain_fine * 0.35
    # M: 190-220 (high but not chrome — raw machined metal)
    M_arr = np.clip(190.0 + combined * 30.0 * sm, 0, 255).astype(np.float32)
    # R: 130-160 (moderate roughness — machined surface, not brushed)
    R_arr = np.clip(130.0 + combined * 30.0 * sm, 2, 255).astype(np.float32)
    # CC: 20-40 (slight clearcoat — thin industrial coat)
    CC_arr = np.clip(20.0 + combined * 20.0, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def paint_gunmetal_satin(paint, shape, mask, seed, pm, bb):
    """Gunmetal Satin paint: dark grey desaturation with industrial metallic cast.
    Pushes color toward dark grey (40-70 range), preserves a subtle metallic sheen.
    Feels raw-machined, not painted."""
    h, w = shape
    grain = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.35, 0.25], seed + 741)
    # Target dark grey: (0.22-0.28)
    dark_grey_r = np.clip(0.22 + grain * 0.06, 0, 1)
    dark_grey_g = np.clip(0.22 + grain * 0.06, 0, 1)
    dark_grey_b = np.clip(0.24 + grain * 0.06, 0, 1)  # Very slight blue-grey cast
    blend = pm * 0.65 * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + dark_grey_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + dark_grey_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + dark_grey_b * blend, 0, 1)
    return paint


# 3.6 Forged Carbon Visible Weave
def spec_forged_carbon_vis_base(shape, seed, sm, base_m, base_r):
    """Forged Carbon Visible Weave base spec: random-fiber organic pattern (vs aligned twill).
    M=20-40, R=25-50 (varying with weave), CC=16-24 (glossy clearcoat).
    DISTINCT from carbon_base (aligned 2x2 twill): Lamborghini forged carbon is RANDOM.
    Generates organic random-fiber spec automatically as part of the finish."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Random fiber: three rotated noise fields at different angles simulate random strands
    rng = np.random.RandomState(seed + 750)
    angle1 = rng.uniform(0, np.pi)
    angle2 = rng.uniform(0, np.pi)
    angle3 = rng.uniform(0, np.pi)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    # Rotated projection for each fiber orientation
    fiber1 = np.sin((x * np.cos(angle1) + y * np.sin(angle1)) * 0.15) * 0.5 + 0.5
    fiber2 = np.sin((x * np.cos(angle2) + y * np.sin(angle2)) * 0.12) * 0.5 + 0.5
    fiber3 = np.sin((x * np.cos(angle3) + y * np.sin(angle3)) * 0.18) * 0.5 + 0.5
    # Random scatter noise to break up regularity
    scatter = multi_scale_noise(sh, [4, 8, 16], [0.3, 0.4, 0.3], seed + 751)
    forged = np.clip(fiber1 * 0.35 + fiber2 * 0.30 + fiber3 * 0.20 + scatter * 0.15, 0, 1)
    # M: 20-40 (low metallic, carbon is dielectric but has surface sheen variation)
    M_arr = np.clip(20.0 + forged * 20.0 * sm, 0, 255).astype(np.float32)
    # R: 25-50 (varies with weave — rib tops smoother, recesses rougher)
    R_arr = np.clip(25.0 + forged * 25.0 * sm, 2, 255).astype(np.float32)
    # CC: 16-24 (glossy clearcoat pooling over random weave)
    CC_arr = np.clip(16.0 + forged * 8.0, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def paint_forged_carbon_vis(paint, shape, mask, seed, pm, bb):
    """Forged Carbon Visible Weave paint: charcoal base with organic random-strand depth.
    Non-repeating dark charcoal with organic fiber flow character (not aligned twill).
    Deep wet clearcoat appearance simulated via color value modulation."""
    h, w = shape
    rng = np.random.RandomState(seed + 750)
    angle1 = rng.uniform(0, np.pi)
    angle2 = rng.uniform(0, np.pi)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    fiber1 = np.sin((x * np.cos(angle1) + y * np.sin(angle1)) * 0.15) * 0.5 + 0.5
    fiber2 = np.sin((x * np.cos(angle2) + y * np.sin(angle2)) * 0.12) * 0.5 + 0.5
    scatter = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 751)
    forged = np.clip(fiber1 * 0.45 + fiber2 * 0.35 + scatter * 0.20, 0, 1)
    # Charcoal base: dark (0.08-0.18) with organic brightness variation
    char_r = np.clip(0.08 + forged * 0.10, 0, 1)
    char_g = np.clip(0.08 + forged * 0.10, 0, 1)
    char_b = np.clip(0.09 + forged * 0.10, 0, 1)
    blend = pm * 0.75 * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + char_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + char_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + char_b * blend, 0, 1)
    return paint


# 3.7 Electroplated Gold / Rose Gold
def spec_electroplated_gold_base(shape, seed, sm, base_m, base_r):
    """Electroplated Gold / Rose Gold base spec: M=245-255, R=5-18, CC=16.
    Chrome physics with warm-colored albedo — the 'warm mirror' zone.
    DISTINCT from chrome (neutral silver albedo): electroplated gold = warm tinted mirror.
    Rolls-Royce Bespoke Gold / Porsche 911 Turbo S Exclusive reference."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Crystal-grain micro noise for plating surface character
    crystal = multi_scale_noise(sh, [2, 4], [0.6, 0.4], seed + 760)
    # M: 245-255 (near-max metallic — electroplated surface)
    M_arr = np.clip(245.0 + crystal * 10.0 * sm, 0, 255).astype(np.float32)
    # R: 5-18 (very low roughness — tight mirror-like reflection, warmer than chrome)
    R_arr = np.clip(5.0 + crystal * 13.0 * sm, 2, 255).astype(np.float32)
    # CC: 16 (max gloss — no clearcoat degradation)
    CC_arr = np.full((h, w), 16.0, dtype=np.float32)
    return M_arr, R_arr, CC_arr


def paint_electroplated_gold(paint, shape, mask, seed, pm, bb):
    """Electroplated Gold paint: warm gold/rose albedo — near-white with strong warm tint.
    Target: warm gold (190,150,40)/255 or rose gold (210,140,120)/255 depending on base hue.
    Detects warm vs. rose intent from paint color and biases accordingly."""
    h, w = shape
    crystal = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 761)
    # Warm gold target: (0.745, 0.588, 0.157)
    gold_r = np.clip(0.745 + crystal * 0.04, 0, 1)
    gold_g = np.clip(0.588 + crystal * 0.04, 0, 1)
    gold_b = np.clip(0.157 + crystal * 0.04, 0, 1)
    # Detect if base leans pink/rose: weight toward rose gold
    base_r_avg = float(paint[:, :, 0].mean())
    base_b_avg = float(paint[:, :, 2].mean())
    rose_weight = np.clip((base_r_avg - base_b_avg) * 2.0, 0.0, 1.0)
    # Rose gold: (0.824, 0.549, 0.471)
    rose_r = np.clip(0.824 + crystal * 0.04, 0, 1)
    rose_g = np.clip(0.549 + crystal * 0.04, 0, 1)
    rose_b = np.clip(0.471 + crystal * 0.04, 0, 1)
    final_r = gold_r * (1 - rose_weight) + rose_r * rose_weight
    final_g = gold_g * (1 - rose_weight) + rose_g * rose_weight
    final_b = gold_b * (1 - rose_weight) + rose_b * rose_weight
    blend = pm * 0.70 * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + final_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + final_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + final_b * blend, 0, 1)
    return paint


# 3.8 Cerakote / PVD Hard Coat
def spec_cerakote_pvd_base(shape, seed, sm, base_m, base_r):
    """Cerakote / PVD Hard Coat base spec: M=160-200, R=160-190, CC=0-10.
    Thin, flat, hard metallic finish — TiN/TiAlN PVD or Cerakote on precision parts.
    DISTINCT from existing cerakote (M=30, tactical ceramic): PVD is more metallic.
    Black, tan, OD green, or bronze tones. Flat = zero clearcoat (CC=0-10)."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Hard coat surface: fine micro-texture from deposition process
    deposit_fine = multi_scale_noise(sh, [4, 8],   [0.55, 0.45], seed + 770)
    deposit_med  = multi_scale_noise(sh, [16, 32],  [0.55, 0.45], seed + 771)
    combined = deposit_fine * 0.5 + deposit_med * 0.5
    # M: 160-200 (moderate-high metallic — harder/more metallic than polymer Cerakote)
    M_arr = np.clip(160.0 + combined * 40.0 * sm, 0, 255).astype(np.float32)
    # R: 160-190 (moderate-high roughness — flat PVD surface, no gloss)
    R_arr = np.clip(160.0 + combined * 30.0 * sm, 2, 255).astype(np.float32)
    # CC: 0-10 (zero clearcoat — PVD IS the finish, no topcoat)
    CC_arr = np.clip(combined * 10.0, 0, 10).astype(np.float32)
    return M_arr, R_arr, CC_arr


def paint_cerakote_pvd(paint, shape, mask, seed, pm, bb):
    """Cerakote PVD paint: desaturates toward deep muted industrial color.
    Preserves hue but crushes saturation to industrial flat (S≈0.3-0.5).
    Darkens toward the deep muted range — black, OD, tan, bronze."""
    h, w = shape
    deposit = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.35, 0.25], seed + 771)
    # Desaturate toward muted industrial: blend toward grey at 45-50%
    gray = paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114
    # Target: reduced saturation + slight value crush
    desat = 0.45 + deposit * 0.10
    desat_r = np.clip(paint[:, :, 0] * (1 - desat) + gray * desat, 0, 1)
    desat_g = np.clip(paint[:, :, 1] * (1 - desat) + gray * desat, 0, 1)
    desat_b = np.clip(paint[:, :, 2] * (1 - desat) + gray * desat, 0, 1)
    # Value crush: darken by 20-30%
    value_crush = np.clip(0.72 + deposit * 0.08, 0.65, 0.85)
    desat_r *= value_crush; desat_g *= value_crush; desat_b *= value_crush
    blend = pm * 0.65 * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + desat_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + desat_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + desat_b * blend, 0, 1)
    return paint


# 3.9 Hypershift Spectral (360° Color Rotation)
def spec_hypershift_spectral_base(shape, seed, sm, base_m, base_r):
    """Hypershift Spectral / 360° Color Rotation base spec: M=200-240, R=20-50, CC=16-24.
    PPG HyperShift: stronger color anchors and steeper transitions than chameleon.
    DISTINCT from chameleon (smooth hue rotation): hypershift has defined color ANCHORS.
    6+ distinct hue anchors with sharp transitions between them."""
    h, w = shape[:2] if len(shape) > 2 else shape
    sh = (h, w)
    # Coarse shift field (large scale — color regions)
    shift_coarse = multi_scale_noise(sh, [32, 64, 128], [0.4, 0.35, 0.25], seed + 780)
    # Fine anchor-lock noise (medium scale — anchor boundary sharpening)
    shift_fine   = multi_scale_noise(sh, [8,  16],       [0.6,  0.4],       seed + 781)
    raw = shift_coarse * 0.7 + shift_fine * 0.3
    # FIX: Normalize to full [0,1] instead of np.clip — clip crushed negative half to 0
    r_min, r_max = float(raw.min()), float(raw.max())
    if r_max - r_min > 1e-6:
        combined = (raw - r_min) / (r_max - r_min)
    else:
        combined = np.full_like(raw, 0.5)
    # M: 200-240 (high metallic — the spectral pigment carrier)
    M_arr = np.clip(200.0 + combined * 40.0 * sm, 0, 255).astype(np.float32)
    # R: 20-50 (low-moderate roughness — spectral pigment needs some blur for color reading)
    R_arr = np.clip(20.0 + combined * 30.0 * sm, 2, 255).astype(np.float32)
    # CC: 16-24 (max gloss range — spectral pigments need clearcoat depth)
    CC_arr = np.clip(16.0 + combined * 8.0, 16, 255).astype(np.float32)
    return M_arr, R_arr, CC_arr


def paint_hypershift_spectral(paint, shape, mask, seed, pm, bb):
    """Hypershift Spectral paint: 6-anchor FULL 360° spectral hue rotation.
    FIX: Previous version used np.clip(combined, 0, 1) which crushed the entire
    negative half of the noise field to 0, collapsing ~50% of the surface onto
    the first anchor (Red). Now properly normalizes the combined noise to [0, 1]
    so ALL 6 anchors get equal representation = true full-spectrum sweep.
    Anchors: Red(0°)→Orange(29°)→Yellow-Green(86°)→Blue(230°)→Purple(281°)→Red(360°)."""
    h, w = shape
    shift_coarse = multi_scale_noise((h, w), [32, 64, 128], [0.4, 0.35, 0.25], seed + 780)
    shift_fine   = multi_scale_noise((h, w), [8, 16],        [0.6, 0.4],        seed + 781)
    raw = shift_coarse * 0.7 + shift_fine * 0.3
    # ── FIX: Normalize to full [0, 1] instead of clipping (was: np.clip(raw, 0, 1)) ──
    # np.clip crushed all negative noise values to 0, meaning ~half the surface sat
    # at the first anchor. Proper normalization ensures full spectral sweep.
    r_min, r_max = float(raw.min()), float(raw.max())
    if r_max - r_min > 1e-6:
        combined = (raw - r_min) / (r_max - r_min)
    else:
        combined = np.full_like(raw, 0.5)

    # Steepened anchor transitions (sharper than linear hue rotation)
    # Apply gamma to steepen mid-transitions (amplify anchor saturation)
    steep = np.clip(np.power(combined, 0.65), 0, 1)  # gamma<1 steepens transitions

    # 6 HSV anchor stops (H in 0-1) — full 360° sweep
    # Red(0.00), Orange(0.08), Yellow-Green(0.24), Blue(0.64), Purple(0.78), Red(1.00)
    stops_h = np.array([0.00, 0.08, 0.24, 0.64, 0.78, 1.00], dtype=np.float32)
    stops_s = np.array([1.00, 1.00, 0.95, 1.00, 0.95, 1.00], dtype=np.float32)
    stops_v = np.array([0.85, 0.88, 0.82, 0.75, 0.78, 0.85], dtype=np.float32)
    n_stops = len(stops_h)

    t = steep * (n_stops - 1)
    idx = np.clip(t.astype(np.int32), 0, n_stops - 2)
    frac = t - idx.astype(np.float32)
    out_h = np.zeros((h, w), dtype=np.float32)
    out_s = np.zeros((h, w), dtype=np.float32)
    out_v = np.zeros((h, w), dtype=np.float32)
    for i in range(n_stops - 1):
        seg = (idx == i)
        f = frac[seg]
        out_h[seg] = stops_h[i] * (1 - f) + stops_h[i + 1] * f
        out_s[seg] = stops_s[i] * (1 - f) + stops_s[i + 1] * f
        out_v[seg] = stops_v[i] * (1 - f) + stops_v[i + 1] * f

    hs_r, hs_g, hs_b = hsv_to_rgb_vec(out_h, out_s, out_v)
    blend = pm * 0.80 * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + hs_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + hs_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + hs_b * blend, 0, 1)
    return paint


# ── SECTION 4: 8 NEW SPECIAL FINISHES ────────────────────────────────────────
# Specials apply ON TOP of base finish — modify without replacing.
# paint_fn signature: (paint, shape, mask, seed, pm, bb)
# spec_fn signature:  (shape, mask, seed, sm)

# 4.1 Iridescent Fog Overlay
def spec_iridescent_fog(shape, mask, seed, sm):
    """Iridescent Fog Overlay special spec: semi-transparent oil-film haze.
    Adds metallic + roughness variation overlay with viewing-angle-weighted hue bias.
    R=200-220 (near-max metallic for oil film), G=20-40 (smooth blur), CC=16."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    fog = multi_scale_noise(shape, [16, 32, 64], [0.4, 0.35, 0.25], seed + 790)
    fog_n = np.clip(fog * 0.5 + 0.5, 0, 1)
    spec[:, :, 0] = np.clip((200.0 + fog_n * 20.0 * sm) * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((20.0  + fog_n * 20.0 * sm) * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = 16
    spec[:, :, 3] = 255
    return spec


def paint_iridescent_fog(paint, shape, mask, seed, pm, bb):
    """Iridescent Fog paint: thin oil-film haze — warm/cool tone shift with angle without
    changing underlying color character. Additive semi-transparent iridescent overlay.
    FBM film thickness drives 180° partial hue rotation at low saturation (S=0.35)."""
    h, w = shape
    fog = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 790)
    fog_n = np.clip(fog * 0.5 + 0.5, 0, 1)
    # 180° hue rotation (warm→cool half-cycle) at low saturation — additive iridescence
    hue = fog_n * 0.5   # 0-180° (warm to cool range only)
    sat = np.full((h, w), 0.35, dtype=np.float32)  # Low sat = subtle fog not garish
    val = np.full((h, w), 0.70, dtype=np.float32)
    fog_r, fog_g, fog_b = hsv_to_rgb_vec(hue, sat, val)
    # Low-opacity additive blend — preserves base character
    blend = pm * 0.25 * mask  # 25% max — fog is an overlay, not a replacement
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + fog_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + fog_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + fog_b * blend, 0, 1)
    return paint


# 4.2 Chrome Delete Accent Edge
def spec_chrome_delete_edge(shape, mask, seed, sm):
    """Chrome Delete Accent Edge special spec: mirror-chrome edge line at zone boundaries.
    Simulates production brightwork (A-pillar chrome, door trim).
    Edge pixels: R=255, G=2, CC=16. Interior: unchanged (spec pass-through).
    Edge detection from mask boundaries — configurable border width."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    # Detect edges from mask using Sobel-like gradient
    mask_img = Image.fromarray(np.clip(mask * 255, 0, 255).astype(np.uint8), mode='L')
    # Edge detection: find mask boundaries
    edge_raw = np.array(mask_img.filter(ImageFilter.FIND_EDGES())).astype(np.float32) / 255.0
    # Dilate edge band to configurable width (~3px)
    edge_dilated = np.array(Image.fromarray(
        np.clip(edge_raw * 255, 0, 255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(size=3))).astype(np.float32) / 255.0
    edge_band = np.clip(edge_dilated * sm, 0, 1)
    # Edge: full chrome (R=255, G=2, CC=16). Non-edge: neutral pass-through.
    spec[:, :, 0] = np.clip(edge_band * 255 * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip((2 * edge_band + 120 * (1 - edge_band)) * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip((16 * edge_band + 80 * (1 - edge_band)) * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def paint_chrome_delete_edge(paint, shape, mask, seed, pm, bb):
    """Chrome Delete Edge paint: brightens edge band toward near-white for chrome appearance.
    Interior paint color preserved. Edge band pushed toward chrome white (0.9-0.95)."""
    h, w = shape
    mask_img = Image.fromarray(np.clip(mask * 255, 0, 255).astype(np.uint8), mode='L')
    edge_raw = np.array(mask_img.filter(ImageFilter.FIND_EDGES())).astype(np.float32) / 255.0
    edge_dilated = np.array(Image.fromarray(
        np.clip(edge_raw * 255, 0, 255).astype(np.uint8)).filter(
        ImageFilter.MaxFilter(size=3))).astype(np.float32) / 255.0
    edge_band = np.clip(edge_dilated * pm, 0, 1) * mask
    chrome_white = 0.92
    blend = edge_band * 0.85
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + chrome_white * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + chrome_white * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + chrome_white * blend, 0, 1)
    return paint


# 4.3 Carbon Weave Clearcoat Phase-Lock
def spec_carbon_clearcoat_phaselock(shape, mask, seed, sm):
    """Carbon Weave Clearcoat Phase-Lock special spec: B-channel clearcoat variation
    locked to carbon weave pattern — rib tops catch more clearcoat (glossier).
    CC: weave peaks=16, recesses=30-45. Makes carbon look wet and deep.
    DISTINCT from carbon roughness overlay: this is CC-domain-only operation."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    # 2x2 twill weave at 45° (same math as existing carbon spec overlay)
    weave_size = 8.0
    diag1 = np.sin((x + y) * np.pi / weave_size) * 0.5 + 0.5
    diag2 = np.sin((x - y) * np.pi / weave_size) * 0.5 + 0.5
    weave = diag1 * 0.55 + diag2 * 0.45
    # R (metallic): neutral, near-zero (pass-through)
    spec[:, :, 0] = np.clip(30 * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    # G (roughness): weave-driven roughness (same as standard carbon)
    spec[:, :, 1] = np.clip((20 + weave * 25 * sm) * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    # B (clearcoat): PHASE-LOCKED to weave — rib tops=16 (max gloss), recesses=35-45
    cc_val = np.clip(16.0 + (1.0 - weave) * 28.0, 16, 255)
    spec[:, :, 2] = np.clip(cc_val * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def paint_carbon_clearcoat_phaselock(paint, shape, mask, seed, pm, bb):
    """Carbon Weave Clearcoat Phase-Lock paint: darkens toward carbon base + gloss depth.
    The clearcoat pooling gives the 3D depth; paint darkens to reveal it."""
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    weave_size = 8.0
    diag1 = np.sin((x + y) * np.pi / weave_size) * 0.5 + 0.5
    diag2 = np.sin((x - y) * np.pi / weave_size) * 0.5 + 0.5
    weave = diag1 * 0.55 + diag2 * 0.45
    # Carbon-darken: push toward dark charcoal where weave recesses sit
    dark_r = np.clip(0.06 + weave * 0.10, 0, 1)
    dark_g = np.clip(0.06 + weave * 0.10, 0, 1)
    dark_b = np.clip(0.07 + weave * 0.10, 0, 1)
    blend = pm * 0.60 * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + dark_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + dark_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + dark_b * blend, 0, 1)
    return paint


# 4.4 Racing Scratch / Race Wear
def spec_racing_scratch(shape, mask, seed, sm):
    """Racing Scratch / Race Wear special spec: directional micro-scratches front-weighted.
    G gains slight roughness in scratch zones; B loses slight clearcoat there.
    R unchanged. Directional: scratches run in travel direction (horizontal).
    Front-heavy weighting: nose area heaviest, tail lightest."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[:2]
    # Front-heavy gradient (left = front/nose)
    x_pos = np.linspace(1.0, 0.0, w, dtype=np.float32)
    front_weight = np.tile(x_pos, (h, 1))
    # Directional scratch noise: horizontal bias (scratch direction = car travel)
    rng = np.random.RandomState(seed + 800)
    scratch_h = rng.randn(h, 1).astype(np.float32) * 0.6  # Row-dominant (horizontal scratches)
    scratch_h = np.tile(scratch_h, (1, w))
    scratch_fine = rng.randn(h, w).astype(np.float32) * 0.15
    scratch_raw = scratch_h + scratch_fine
    scratch = np.clip(scratch_raw * 0.5 + 0.5, 0, 1)
    # Weight by front position and sm
    scratch_weighted = scratch * front_weight * sm
    # G (roughness): base 60 + scratch zones add roughness (60-100)
    spec[:, :, 1] = np.clip((60.0 + scratch_weighted * 40.0) * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    # R (metallic): slight increase in scratch zone (scratch exposes metal)
    spec[:, :, 0] = np.clip((100.0 + scratch_weighted * 60.0) * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    # B (clearcoat): base 16, scratch zones lose clearcoat (16 → 50)
    cc_val = np.clip(16.0 + scratch_weighted * 34.0, 16, 255)
    spec[:, :, 2] = np.clip(cc_val * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def paint_racing_scratch(paint, shape, mask, seed, pm, bb):
    """Racing Scratch paint: subtle scratch brightening where metal exposed + slight dulling.
    Directional micro-scratch brightening (exposed base metal) at nose area."""
    h, w = shape
    rng = np.random.RandomState(seed + 800)
    scratch_h = rng.randn(h, 1).astype(np.float32) * 0.6
    scratch_h = np.tile(scratch_h, (1, w))
    scratch_fine = rng.randn(h, w).astype(np.float32) * 0.15
    scratch = np.clip((scratch_h + scratch_fine) * 0.5 + 0.5, 0, 1)
    x_pos = np.linspace(1.0, 0.0, w, dtype=np.float32)
    front_weight = np.tile(x_pos, (h, 1))
    scratch_w = scratch * front_weight * pm * mask
    # Scratch brightening: exposed metal micro-highlight
    bright = np.clip(scratch_w * 0.15, 0, 0.15)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + bright, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + bright, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + bright, 0, 1)
    return paint


# 4.5 Pearlescent Flip Coat
def spec_pearlescent_flip(shape, mask, seed, sm):
    """Pearlescent Flip Coat special spec: additive angle-dependent flop over any existing finish.
    Edge-weighted metallic gradient overlay — edges get higher R than face pixels.
    Simulates pearl/flip pigment angle-dependent metallic response.
    Preserves base roughness and clearcoat."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[:2]
    # Edge weighting: simulate grazing-angle flop
    y_pos = np.linspace(0, 1, h, dtype=np.float32)
    x_pos = np.linspace(0, 1, w, dtype=np.float32)
    yy, xx = np.meshgrid(y_pos, x_pos, indexing='ij')
    edge_flop = np.clip(1.0 - np.sin(yy * np.pi) * np.sin(xx * np.pi), 0, 1)
    # Fine pearl platelet variation
    platelet = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.35, 0.25], seed + 810)
    platelet_n = np.clip(platelet * 0.5 + 0.5, 0, 1)
    flip_strength = edge_flop * platelet_n * sm
    # R: edge-weighted metallic (face=70, edge=100 with platelet variation)
    spec[:, :, 0] = np.clip((70.0 + flip_strength * 30.0) * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    # G: mild roughness variation (50-75)
    spec[:, :, 1] = np.clip((50.0 + platelet_n * 25.0 * sm) * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    # B: preserve gloss (16-20)
    spec[:, :, 2] = np.clip((16.0 + platelet_n * 4.0) * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def paint_pearlescent_flip(paint, shape, mask, seed, pm, bb):
    """Pearlescent Flip Coat paint: adds secondary color flop to any base finish.
    At edges/grazing angles, a secondary hint of gold flop appears.
    Low-opacity additive — doesn't replace base color, just adds the angle reveal."""
    h, w = shape
    platelet = multi_scale_noise((h, w), [8, 16, 32], [0.4, 0.35, 0.25], seed + 810)
    platelet_n = np.clip(platelet * 0.5 + 0.5, 0, 1)
    y_pos = np.linspace(0, 1, h, dtype=np.float32)
    x_pos = np.linspace(0, 1, w, dtype=np.float32)
    yy, xx = np.meshgrid(y_pos, x_pos, indexing='ij')
    edge_flop = np.clip(1.0 - np.sin(yy * np.pi) * np.sin(xx * np.pi), 0, 1)
    flip = edge_flop * platelet_n
    # Gold flop: (0.85, 0.72, 0.20) at grazing edges
    flop_r = 0.85 * flip
    flop_g = 0.72 * flip
    flop_b = 0.20 * flip
    blend = pm * 0.30 * mask  # Additive — only 30% blend so base shows through
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + flop_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + flop_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + flop_b * blend, 0, 1)
    return paint


# 4.6 Frost / Ice Crystal Overlay
def spec_frost_crystal(shape, mask, seed, sm):
    """Frost / Ice Crystal Overlay special spec: Voronoi crystal pattern.
    Cell interiors: G=120-160 (moderate roughness).
    Cell boundaries: G=5-15 (near-zero roughness) + CC=16 (sparkle at edges).
    The 'crystal edge sparkle' appearance — interior diffuse, boundary mirror-flash."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[:2]
    # Voronoi crystal pattern: random seed points + nearest-neighbor distance
    rng = np.random.RandomState(seed + 820)
    n_cells = max(20, int(50 * sm))
    cell_x = (rng.rand(n_cells) * w).astype(np.float32)
    cell_y = (rng.rand(n_cells) * h).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # cKDTree for fast nearest-cell distance
    pts = np.column_stack([cell_y, cell_x])
    tree = cKDTree(pts)
    query_pts = np.column_stack([yy.ravel(), xx.ravel()])
    min_dist_flat, _ = tree.query(query_pts, k=1)
    min_dist = min_dist_flat.reshape(h, w).astype(np.float32)
    # Normalize distance to [0, 1] (1 = cell interior, 0 = cell boundary)
    max_d = float(min_dist.max()) + 1e-6
    norm_dist = np.clip(min_dist / max_d, 0, 1)
    # Boundary zone (sharp edge): norm_dist < 0.3
    boundary = np.clip(1.0 - norm_dist / 0.3, 0, 1)
    interior = np.clip((norm_dist - 0.3) / 0.7, 0, 1)
    # R (metallic): boundary gets slight metallic for sparkle
    spec[:, :, 0] = np.clip((boundary * 80 * sm) * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    # G (roughness): boundary=15-20, interior=120-160
    r_val = boundary * 18 * sm + interior * 130
    spec[:, :, 1] = np.clip(r_val * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    # B (clearcoat): boundary=16 (max gloss sparkle), interior=60-80 (frosted)
    cc_val = boundary * 16 + interior * 65
    spec[:, :, 2] = np.clip(np.maximum(cc_val, 16) * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def paint_frost_crystal(paint, shape, mask, seed, pm, bb):
    """Frost Crystal paint: ice-white crystal overlay with semi-transparent interior.
    Crystal interiors: blue-tinted white (frost). Boundaries: near-clear sparkle.
    Underlying color visible through frost interior."""
    h, w = shape
    rng = np.random.RandomState(seed + 820)
    n_cells = max(20, int(50 * pm))
    cell_x = (rng.rand(n_cells) * w).astype(np.float32)
    cell_y = (rng.rand(n_cells) * h).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # cKDTree for fast nearest-cell distance
    pts = np.column_stack([cell_y, cell_x])
    tree = cKDTree(pts)
    query_pts = np.column_stack([yy.ravel(), xx.ravel()])
    min_dist_flat, _ = tree.query(query_pts, k=1)
    min_dist = min_dist_flat.reshape(h, w).astype(np.float32)
    max_d = float(min_dist.max()) + 1e-6
    norm_dist = np.clip(min_dist / max_d, 0, 1)
    # Frost interior: slight blue-white tint (ice color: R=0.82, G=0.90, B=0.97)
    ice_r = np.full((h, w), 0.82, dtype=np.float32)
    ice_g = np.full((h, w), 0.90, dtype=np.float32)
    ice_b = np.full((h, w), 0.97, dtype=np.float32)
    frost_alpha = np.clip(0.35 * pm * mask, 0, 0.45)  # Semi-transparent frost
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - frost_alpha) + ice_r * frost_alpha, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - frost_alpha) + ice_g * frost_alpha, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - frost_alpha) + ice_b * frost_alpha, 0, 1)
    return paint


# 4.7 Satin Wax / Concours Polish
def spec_satin_wax(shape, mask, seed, sm):
    """Satin Wax / Concours Polish special spec: maximum clearcoat (B=16) + subtle buffer
    swirl marks in G channel. The characteristic hand-polished appearance.
    Large-radius buffer swirl at minimal amplitude — barely visible but adds realism."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[:2]
    # Large-scale buffer swirl noise (scale~30% of image width)
    swirl_scale = max(4, int(w * 0.30 / 8))
    swirl = multi_scale_noise(shape, [swirl_scale, swirl_scale * 2], [0.6, 0.4], seed + 830)
    swirl_n = np.clip(swirl * 0.5 + 0.5, 0, 1)
    # R (metallic): near-zero (gloss paint, not metallic)
    spec[:, :, 0] = np.clip(5 * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    # G (roughness): 10-15 base + very faint swirl at minimal amplitude
    swirl_amp = np.clip(swirl_n * 5.0 * sm, 0, 5)  # Only 0-5 range — barely visible
    spec[:, :, 1] = np.clip((10.0 + swirl_amp) * mask + 100 * (1 - mask), 0, 255).astype(np.uint8)
    # B (clearcoat): maximum 16 — concours hand-waxed finish
    spec[:, :, 2] = 16
    spec[:, :, 3] = 255
    return spec


def paint_satin_wax(paint, shape, mask, seed, pm, bb):
    """Satin Wax: hand-wax swirl character — depth lift, saturation warmth, micro-buffing texture.
    WEAK-026 FIX: amplitude raised 5%→15%, +10% saturation push in swirl peaks, fine
    micro-buff FBM octave blended at 25% for hand-work scratch texture."""
    h, w = shape
    swirl_scale = max(4, int(w * 0.30 / 8))

    # Coarse orbital swirl (primary) + fine micro-buffing scratch layer (secondary)
    swirl = multi_scale_noise((h, w), [swirl_scale, swirl_scale * 2], [0.6, 0.4], seed + 830)
    swirl_n = np.clip(swirl * 0.5 + 0.5, 0, 1)
    micro = multi_scale_noise((h, w), [max(2, swirl_scale // 2), swirl_scale], [0.5, 0.5], seed + 831)
    micro_n = np.clip(micro * 0.5 + 0.5, 0, 1)
    combined = swirl_n * 0.75 + micro_n * 0.25  # 75% coarse swirl, 25% micro scratch

    mask_3d = mask[:, :, np.newaxis]
    gray = paint.mean(axis=2, keepdims=True)

    # Brightness lift: 0–15% in highlights (was 0–5%)
    depth_lift = np.clip(combined * 0.15 * pm, 0, 0.15)[:, :, np.newaxis]

    # Saturation warmth: +10% push-from-gray in swirl peak zones (adds wax warmth/richness)
    swirl_peak = np.clip((swirl_n - 0.5) * 2.0, 0, 1)[:, :, np.newaxis]
    sat_push = (paint - gray) * swirl_peak * 0.10 * pm

    return np.clip(paint + (depth_lift + sat_push) * mask_3d, 0, 1).astype(np.float32)


# 4.8 UV-Active Night Accent
def spec_uv_night_accent(shape, mask, seed, sm):
    """UV-Active Night Accent special spec: high R + near-zero G + max CC=16 for selected zones.
    In bright lighting: areas washed out by ambient, look like surrounding finish.
    In low-ambient night: high specular creates visible bright reflections.
    'Hidden pattern' — only reveals in night race conditions."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[:2]
    # Accent pattern: sparse high-specular zones driven by fine noise
    uv_pattern = multi_scale_noise(shape, [8, 16, 32], [0.4, 0.35, 0.25], seed + 840)
    uv_n = np.clip(uv_pattern * 0.5 + 0.5, 0, 1)
    # Threshold: top 30% of noise becomes UV-active zone
    uv_active = np.clip((uv_n - 0.70) / 0.30 * sm, 0, 1)
    # R: UV zones = near max (230-255), inactive = low (20-40)
    spec[:, :, 0] = np.clip((20.0 + uv_active * 215.0) * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    # G: UV zones = near zero (2-5), inactive = moderate (80-120)
    spec[:, :, 1] = np.clip((80.0 - uv_active * 78.0) * mask + 100 * (1 - mask), 2, 255).astype(np.uint8)
    # B (clearcoat): UV zones = 16 (max gloss), inactive = base value
    spec[:, :, 2] = np.clip((16.0 + (1.0 - uv_active) * 60.0) * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def paint_uv_night_accent(paint, shape, mask, seed, pm, bb):
    """UV Night Accent paint: subtle brightening of UV-active zones.
    In daylight: slight increase in brightness (barely visible).
    At night (IBL low): the high-specular creates visible bright hot-spots."""
    h, w = shape
    uv_pattern = multi_scale_noise((h, w), [8, 16, 32], [0.4, 0.35, 0.25], seed + 840)
    uv_n = np.clip(uv_pattern * 0.5 + 0.5, 0, 1)
    uv_active = np.clip((uv_n - 0.70) / 0.30, 0, 1)
    # Slight brightness lift only in UV zones
    uv_lift = np.clip(uv_active * 0.08 * pm * mask, 0, 0.10)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + uv_lift, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + uv_lift, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + uv_lift, 0, 1)
    return paint


# ── SECTION 5: 6 NEW MONOLITHIC FINISHES ─────────────────────────────────────
# Monolithics override both color and spec completely.

# 5.1 Aurora Borealis Monolithic
def spec_aurora_borealis_mono(shape, mask, seed, sm):
    """Aurora Borealis monolithic spec: CURTAIN structure (vs galaxy point-source sparkle).
    Large-scale sinusoidal zones simulate vertical drapery light curtains.
    M=230-255, G=30-80 (smooth large-scale variation), CC=16."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[0], shape[1]
    # Flowing curtain structure: sinusoidal vertical bands (large scale)
    y_pos = np.linspace(0, 1, h, dtype=np.float32)
    x_pos = np.linspace(0, 1, w, dtype=np.float32)
    yy, xx = np.meshgrid(y_pos, x_pos, indexing='ij')
    # Curtain bands: primarily vertical variation with slight x-warp
    warp = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 850)
    warp_n = np.clip(warp * 0.5 + 0.5, 0, 1)
    curtain_x = xx + warp_n * 0.3  # x-warp for organic curtain movement
    curtain = np.clip(np.sin(curtain_x * np.pi * 4.0) * 0.5 + 0.5, 0, 1)
    # Add multi-scale nebula density
    density = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 851)
    density_n = np.clip(density * 0.5 + 0.5, 0, 1)
    combined = curtain * 0.65 + density_n * 0.35
    M = np.clip(230.0 + combined * 25.0, 0, 255)
    R = np.clip( 30.0 + combined * 50.0, 2, 255)
    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = 16
    spec[:, :, 3] = 255
    return spec


def paint_aurora_borealis_mono(paint, shape, mask, seed, pm, bb):
    """Aurora Borealis monolithic paint: near-black base + flowing curtain color bands.
    Color: green → teal → cyan → violet (aurora palette) flowing vertically.
    Curtain structure = broad flowing zones, not point-source sparkle."""
    h, w = shape
    warp = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 850)
    warp_n = np.clip(warp * 0.5 + 0.5, 0, 1)
    y_pos = np.linspace(0, 1, h, dtype=np.float32)
    x_pos = np.linspace(0, 1, w, dtype=np.float32)
    yy, xx = np.meshgrid(y_pos, x_pos, indexing='ij')
    curtain_x = xx + warp_n * 0.3
    curtain = np.clip(curtain_x, 0, 1)
    density = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 851)
    density_n = np.clip(density * 0.5 + 0.5, 0, 1)
    field = np.clip(curtain * 0.6 + density_n * 0.4, 0, 1)

    # Aurora color stops: green(0.38) → teal(0.51) → cyan(0.54) → blue(0.64) → violet(0.78)
    stops_h = np.array([0.38, 0.51, 0.54, 0.64, 0.78], dtype=np.float32)
    stops_s = np.array([0.90, 0.85, 0.88, 0.90, 0.85], dtype=np.float32)
    stops_v = np.array([0.70, 0.65, 0.68, 0.60, 0.55], dtype=np.float32)
    n_stops = len(stops_h)
    t = field * (n_stops - 1)
    idx = np.clip(t.astype(np.int32), 0, n_stops - 2)
    frac = t - idx.astype(np.float32)
    out_h = np.zeros((h, w), dtype=np.float32)
    out_s = np.zeros((h, w), dtype=np.float32)
    out_v = np.zeros((h, w), dtype=np.float32)
    for i in range(n_stops - 1):
        seg = (idx == i)
        f = frac[seg]
        out_h[seg] = stops_h[i] * (1 - f) + stops_h[i + 1] * f
        out_s[seg] = stops_s[i] * (1 - f) + stops_s[i + 1] * f
        out_v[seg] = stops_v[i] * (1 - f) + stops_v[i + 1] * f

    # Near-black base
    void_r = np.clip(paint.mean(axis=2) * 0.06, 0, 1)
    void_g = np.clip(paint.mean(axis=2) * 0.07, 0, 1)
    void_b = np.clip(paint.mean(axis=2) * 0.08, 0, 1)

    ab_r, ab_g, ab_b = hsv_to_rgb_vec(out_h, out_s, out_v)
    ab_r *= density_n; ab_g *= density_n; ab_b *= density_n

    blend_ab   = 0.75 * pm * mask
    blend_void = 0.25 * pm * mask
    total = blend_ab + blend_void
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - total) + ab_r * blend_ab + void_r * blend_void, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - total) + ab_g * blend_ab + void_g * blend_void, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - total) + ab_b * blend_ab + void_b * blend_void, 0, 1)
    return paint


# 5.2 Deep Space Void Monolithic
def spec_deep_space_void(shape, mask, seed, sm):
    """Deep Space Void monolithic spec: near-absolute black with ultra-sparse bright stars.
    Background: R=0, G=255. Star pixels: R=255, G=0.
    Sparse Poisson-disk sampled (or LCG) star positions — ~0.15% density."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[0], shape[1]
    # Background: zero metallic, maximum roughness (void black)
    # Stars: max metallic, zero roughness (ultra-bright pinpoints)
    flat_idx = np.arange(h * w, dtype=np.uint32)
    # Very sparse star field: 0.15% = 1.5 per 1000 pixels
    lcg = ((flat_idx * 1664525 + (seed & 0xFFFF)) * 22695477 + 1013904223) & 0xFFFFFFFF
    stars = (lcg % 10000 < 15).reshape(h, w).astype(np.float32)  # ~0.15% density
    _simg = Image.fromarray(np.clip(stars * 255, 0, 255).astype(np.uint8), mode='L')
    stars_spread = np.array(_simg.filter(ImageFilter.GaussianBlur(radius=1.0))).astype(np.float32) / 255.0

    M = np.clip(stars_spread * 255.0 * 1.5, 0, 255)
    R = np.clip(255.0 - stars_spread * 260.0, 2, 255)
    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = 16
    spec[:, :, 3] = 255
    return spec


def paint_deep_space_void(paint, shape, mask, seed, pm, bb):
    """Deep Space Void monolithic paint: near-absolute black with white star pinpoints.
    Albedo locked: background (5,5,8), stars (white-blue).
    The car nearly disappears — only star collection visible."""
    h, w = shape
    flat_idx = np.arange(h * w, dtype=np.uint32)
    lcg = ((flat_idx * 1664525 + (seed & 0xFFFF)) * 22695477 + 1013904223) & 0xFFFFFFFF
    lcg2 = ((lcg * 1664525) + 1013904223) & 0xFFFFFFFF
    star_mask_arr = (lcg % 10000 < 15).reshape(h, w)
    star_type = (lcg2 % 3).reshape(h, w)
    # Star types: warm white, blue-white, pure white
    star_r = np.where(star_mask_arr, np.where(star_type == 0, 1.0, np.where(star_type == 1, 0.85, 0.95)), 0.0).astype(np.float32)
    star_g = np.where(star_mask_arr, np.where(star_type == 0, 1.0, np.where(star_type == 1, 0.90, 0.95)), 0.0).astype(np.float32)
    star_b = np.where(star_mask_arr, np.where(star_type == 0, 0.90, np.where(star_type == 1, 1.0,  0.95)), 0.0).astype(np.float32)
    for _ch, _sarr in enumerate([star_r, star_g, star_b]):
        _img = Image.fromarray(np.clip(_sarr * 255, 0, 255).astype(np.uint8), mode='L')
        _bl = np.array(_img.filter(ImageFilter.GaussianBlur(radius=1.0))).astype(np.float32) / 255.0
        if _ch == 0: star_r_s = _bl
        elif _ch == 1: star_g_s = _bl
        else: star_b_s = _bl
    # Near-black void
    void_v = 0.020 + multi_scale_noise((h, w), [4, 8], [0.6, 0.4], seed + 861) * 0.008
    void_r = np.clip(void_v * 0.90, 0, 1).astype(np.float32)
    void_g = np.clip(void_v * 0.90, 0, 1).astype(np.float32)
    void_b = np.clip(void_v * 1.10, 0, 1).astype(np.float32)  # Slight blue bias (space)
    blend_void = 0.80 * pm * mask
    blend_star = 0.20 * pm * mask
    total = blend_void + blend_star
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - total) + void_r * blend_void + star_r_s * blend_star, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - total) + void_g * blend_void + star_g_s * blend_star, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - total) + void_b * blend_void + star_b_s * blend_star, 0, 1)
    return paint


# 5.3 Polished Obsidian Monolithic
def spec_polished_obsidian_mono(shape, mask, seed, sm):
    """Polished Obsidian monolithic spec: R=0 (no metallic), G=0-5 (near-perfectly smooth),
    CC=16 (maximum clearcoat). The 'anti-chrome' — dark reflections in deep black.
    Non-metallic maximum-gloss = environment reflects in near-black tint.
    CRITICAL: R=0 (metallic) ensures it stays BLACK not silver."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[0], shape[1]
    # Very slight surface variation (volcanic glass is near-perfect but not absolute)
    micro = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 870)
    micro_n = np.clip(micro * 0.5 + 0.5, 0, 1)
    # R (metallic): 0 — pure dielectric. ANY metallic shifts to silver and ruins the look.
    spec[:, :, 0] = np.clip(0 * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    # G (roughness): 0-5 (near-perfect mirror surface — volcanic glass is smooth)
    spec[:, :, 1] = np.clip((2.0 + micro_n * 3.0) * mask + 100 * (1 - mask), 2, 255).astype(np.uint8)
    # B (clearcoat): 16 — maximum gloss, no degradation
    spec[:, :, 2] = 16
    spec[:, :, 3] = 255
    return spec


def paint_polished_obsidian_mono(paint, shape, mask, seed, pm, bb):
    """Polished Obsidian paint: near-black albedo (8,8,10) — deep black volcanic glass.
    Color is locked to near-absolute black. The finish IS the reflection, not the color."""
    h, w = shape
    micro = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 870)
    micro_n = np.clip(micro * 0.5 + 0.5, 0, 1)
    # Near-black: (8,8,10)/255 = (0.031, 0.031, 0.039) float
    obs_r = np.clip(0.031 + micro_n * 0.008, 0, 1)
    obs_g = np.clip(0.031 + micro_n * 0.008, 0, 1)
    obs_b = np.clip(0.039 + micro_n * 0.010, 0, 1)  # Very slight blue (obsidian tint)
    blend = pm * 0.90 * mask  # Strong override — obsidian forces near-black
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + obs_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + obs_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + obs_b * blend, 0, 1)
    return paint


# 5.4 Patinated Bronze Monolithic
def spec_patinated_bronze(shape, mask, seed, sm):
    """Patinated Bronze monolithic spec: two-zone system — warm bronze + verdigris patina.
    Bronze zones: M=140-180, G=100-140, CC=40-60.
    Patina zones: M=50-80, G=150-180, CC=20-40.
    Perlin noise heightmap drives the patina distribution (low areas = patina)."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[0], shape[1]
    # Bronze vs patina: height map (Perlin noise) — low areas collect patina
    height = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 880)
    height_n = np.clip(height * 0.5 + 0.5, 0, 1)
    # Warp for organic patina zones
    warp = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 881)
    warp_n = np.clip(warp * 0.5 + 0.5, 0, 1)
    patina_zone = np.clip(1.0 - height_n + warp_n * 0.3, 0, 1)  # Low areas get patina

    # Bronze zones: M=140-180, G=100-140, CC=40-60
    M_bronze = 140.0 + height_n * 40.0
    R_bronze = 100.0 + height_n * 40.0
    CC_bronze = 40.0 + height_n * 20.0
    # Patina zones: M=50-80, G=150-180, CC=20-40
    M_patina = 50.0  + patina_zone * 30.0
    R_patina = 150.0 + patina_zone * 30.0
    CC_patina = 20.0 + patina_zone * 20.0

    blend_p = np.clip(patina_zone * sm, 0, 1)
    M  = M_bronze  * (1 - blend_p) + M_patina  * blend_p
    R  = R_bronze  * (1 - blend_p) + R_patina  * blend_p
    CC = CC_bronze * (1 - blend_p) + CC_patina * blend_p

    spec[:, :, 0] = np.clip(M  * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R  * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)  # GGX floor
    spec[:, :, 2] = np.clip(CC * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def paint_patinated_bronze(paint, shape, mask, seed, pm, bb):
    """Patinated Bronze monolithic paint: warm dark bronze base + turquoise-green patina zones.
    Bronze: HSV approx (0.10, 0.65, 0.45). Patina: (0.51, 0.70, 0.42) (verdigris turquoise).
    Same Perlin heightmap drives both color and spec for physical consistency."""
    h, w = shape
    height = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 880)
    height_n = np.clip(height * 0.5 + 0.5, 0, 1)
    warp = multi_scale_noise((h, w), [8, 16], [0.6, 0.4], seed + 881)
    warp_n = np.clip(warp * 0.5 + 0.5, 0, 1)
    patina_zone = np.clip(1.0 - height_n + warp_n * 0.3, 0, 1)

    # Bronze palette stops (dark bronze)
    bronze_h = np.full((h, w), 0.10, dtype=np.float32) + height_n * 0.02
    bronze_s = np.clip(0.62 + height_n * 0.08, 0, 1).astype(np.float32)
    bronze_v = np.clip(0.40 + height_n * 0.12, 0, 1).astype(np.float32)
    b_r, b_g, b_b = hsv_to_rgb_vec(bronze_h, bronze_s, bronze_v)

    # Patina palette (verdigris turquoise)
    patina_h = np.full((h, w), 0.51, dtype=np.float32) + patina_zone * 0.02
    patina_s = np.clip(0.68 + patina_zone * 0.06, 0, 1).astype(np.float32)
    patina_v = np.clip(0.38 + patina_zone * 0.10, 0, 1).astype(np.float32)
    p_r, p_g, p_b = hsv_to_rgb_vec(patina_h, patina_s, patina_v)

    blend_p = np.clip(patina_zone * pm, 0, 1)
    final_r = b_r * (1 - blend_p) + p_r * blend_p
    final_g = b_g * (1 - blend_p) + p_g * blend_p
    final_b = b_b * (1 - blend_p) + p_b * blend_p

    total_blend = pm * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - total_blend) + final_r * total_blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - total_blend) + final_g * total_blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - total_blend) + final_b * total_blend, 0, 1)
    return paint


# 5.5 Reactive Plasma Monolithic
def spec_reactive_plasma(shape, mask, seed, sm):
    """Reactive Plasma monolithic spec: electric plasma discharge tendrils.
    Tendrils: R=240-255, G=0-10 (mirror-bright streaks).
    Background: R=0, G=200 (near-flat void).
    Tendril structure generated via multi-scale noise at high contrast."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[0], shape[1]
    # Multi-scale noise at high contrast for electric tendril structure
    plasma1 = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 890)
    plasma2 = multi_scale_noise((h, w), [2, 4],     [0.6, 0.4],       seed + 891)
    # Sharpen via high gamma (emphasize bright peaks = plasma discharge)
    combined = np.clip(plasma1 * 0.6 + plasma2 * 0.4, 0, 1)
    sharp = np.power(combined, 0.25)  # Gamma compress: pulls brights, darkens background
    tendril = np.clip((sharp - 0.55) / 0.45, 0, 1)  # Threshold tendrils

    # R (metallic): tendrils=240-255, background=0
    M = np.clip(tendril * 255.0, 0, 255)
    # G (roughness): tendrils=0-10, background=200
    R = np.clip(200.0 - tendril * 195.0, 2, 255)
    spec[:, :, 0] = np.clip(M * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 2, 255).astype(np.uint8)
    spec[:, :, 2] = 16
    spec[:, :, 3] = 255
    return spec


def paint_reactive_plasma(paint, shape, mask, seed, pm, bb):
    """Reactive Plasma monolithic paint: plasma tendrils = vivid electric white/blue/violet.
    Background = deep near-black (10,5,20)/255.
    Same noise drives color AND spec — physical consistency (tendrils = bright + mirror)."""
    h, w = shape
    plasma1 = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 890)
    plasma2 = multi_scale_noise((h, w), [2, 4],     [0.6, 0.4],       seed + 891)
    combined = np.clip(plasma1 * 0.6 + plasma2 * 0.4, 0, 1)
    sharp = np.power(combined, 0.25)
    tendril = np.clip((sharp - 0.55) / 0.45, 0, 1)

    # Tendril color palette: electric white → cyan → blue-violet via hue
    tendril_h = np.clip(0.58 + tendril * 0.08, 0, 1).astype(np.float32)  # blue-cyan
    tendril_s = np.clip(0.30 + tendril * 0.50, 0, 1).astype(np.float32)  # core=desaturated (white)
    tendril_v = np.clip(0.78 + tendril * 0.20, 0, 1).astype(np.float32)  # bright
    t_r, t_g, t_b = hsv_to_rgb_vec(tendril_h, tendril_s, tendril_v)
    # Invert saturation for core: core is near-white (S low), edges are vivid (S high)
    t_r = np.clip(t_r + (1.0 - tendril) * 0.10, 0, 1)
    t_g = np.clip(t_g + (1.0 - tendril) * 0.05, 0, 1)
    t_b = np.clip(t_b + (1.0 - tendril) * 0.20, 0, 1)

    # Background: deep near-black (10,5,20)/255
    bg_r = np.full((h, w), 0.039, dtype=np.float32)
    bg_g = np.full((h, w), 0.020, dtype=np.float32)
    bg_b = np.full((h, w), 0.078, dtype=np.float32)

    # Blend: tendril drives contribution
    blend_t  = pm * tendril * mask
    blend_bg = pm * (1.0 - tendril) * mask
    total = blend_t + blend_bg
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - total) + t_r * blend_t + bg_r * blend_bg, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - total) + t_g * blend_t + bg_g * blend_bg, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - total) + t_b * blend_t + bg_b * blend_bg, 0, 1)
    return paint


# 5.6 Molten Metal Monolithic
def spec_molten_metal(shape, mask, seed, sm):
    """Molten Metal monolithic spec: position-based heat map across car body.
    Hot zones (rear/edges): M=230-255, G=20-40, CC=20-30.
    Cool zones (nose/center): M=160-190, G=80-120, CC=30-50.
    Heat gradient: rear = hot, front = cool — simulates post-forge state."""
    spec = np.zeros((shape[0], shape[1], 4), dtype=np.uint8)
    h, w = shape[0], shape[1]
    # Position-based heat: x=0(left/front)=cool, x=1(right/rear)=hot
    x_pos = np.tile(np.linspace(0, 1, w, dtype=np.float32), (h, 1))
    # Add organic variation with FBM
    heat_noise = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 900)
    heat_noise_n = np.clip(heat_noise * 0.5 + 0.5, 0, 1)
    # Heat: front=cool (0.0), rear=hot (1.0) with FBM variation
    heat = np.clip(x_pos * 0.7 + heat_noise_n * 0.3, 0, 1)

    # Hot zone spec: M=230-255, G=20-40, CC=20-30
    # Cool zone spec: M=160-190, G=80-120, CC=30-50
    M  = np.clip(160.0 + heat * 70.0,  0, 255)
    R  = np.clip(120.0 - heat * 100.0, 2, 255)  # Hot=20, Cool=120
    CC = np.clip( 50.0 - heat * 20.0,  16, 255)  # Hot=30, Cool=50

    spec[:, :, 0] = np.clip(M  * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R  * mask + 100 * (1 - mask), 2, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC * mask + 80 * (1 - mask), 16, 255).astype(np.uint8)
    spec[:, :, 3] = 255
    return spec


def paint_molten_metal(paint, shape, mask, seed, pm, bb):
    """Molten Metal monolithic paint: heat gradient color — orange-gold at hot zones,
    dark bronze-grey at cool zones. Same heat gradient as spec for physical consistency.
    Hot: bright orange-gold (H=0.09, S=0.90, V=0.88).
    Cool: dark bronze-grey (H=0.08, S=0.35, V=0.32)."""
    h, w = shape
    x_pos = np.tile(np.linspace(0, 1, w, dtype=np.float32), (h, 1))
    heat_noise = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 900)
    heat_noise_n = np.clip(heat_noise * 0.5 + 0.5, 0, 1)
    heat = np.clip(x_pos * 0.7 + heat_noise_n * 0.3, 0, 1)

    # HSV color ramp: cool → warm → hot
    # 0.0 = cool dark bronze-grey: (H=0.08, S=0.35, V=0.32)
    # 1.0 = hot bright orange-gold: (H=0.09, S=0.90, V=0.88)
    m_h = np.clip(0.08 + heat * 0.01, 0, 1).astype(np.float32)
    m_s = np.clip(0.35 + heat * 0.55, 0, 1).astype(np.float32)
    m_v = np.clip(0.32 + heat * 0.56, 0, 1).astype(np.float32)
    m_r, m_g, m_b = hsv_to_rgb_vec(m_h, m_s, m_v)

    blend = pm * mask
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend) + m_r * blend, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend) + m_g * blend, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend) + m_b * blend, 0, 1)
    return paint


# ── END RESEARCH SESSION 6 ────────────────────────────────────────────────────


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


# ================================================================
# ★ STRUCTURAL COLOR — Biologically-inspired finishes
# Each paint+spec pair is MARRIED: the spec function knows exactly
# what the paint function does spatially and tunes M/R/CC to make
# the color effect render correctly in iRacing's PBR pipeline.
# No wild patterns — fine detail that serves the physics.
#
# KEY PRINCIPLE: The PAINT function creates the STATIC COLOR texture.
# The SPEC function creates the MATERIAL PROPERTIES (M/R/CC) that tell
# iRacing's PBR renderer HOW to light that color at different angles.
# Angle-dependent behavior comes from the RENDERER reading M/R/CC,
# NOT from the paint function trying to simulate angles.
# ================================================================


def paint_morpho_blue(paint, shape, mask, seed, pm, bb):
    """Morpho Blue — V2: rich saturated blue always visible.
    Spec controls the flash/darken via M/R, not the paint function."""
    h, w = shape[:2] if len(shape) > 2 else shape
    lobe = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 8801)
    lobe_n = np.clip(lobe * 0.5 + 0.5, 0, 1).astype(np.float32)
    micro = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 8802)
    micro_n = np.clip(micro * 0.12 + 0.88, 0.75, 1.0).astype(np.float32)
    deep = np.array([0.04, 0.08, 0.45], dtype=np.float32)
    bright = np.array([0.10, 0.30, 0.85], dtype=np.float32)
    blue_field = lobe_n * micro_n
    color = (deep[np.newaxis, np.newaxis, :] * (1 - blue_field[:,:,np.newaxis]) +
             bright[np.newaxis, np.newaxis, :] * blue_field[:,:,np.newaxis])
    blend = np.clip(pm * 0.88, 0, 1)
    m3 = mask[:,:,np.newaxis]
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + color * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)


def spec_morpho_blue(shape, seed, sm, base_m, base_r):
    """Morpho Blue spec — V2: uniform high M (190-210), tight R (20-30).
    No chrome splotches. Renderer creates the angle-dependent flash."""
    h, w = shape[:2] if len(shape) > 2 else shape
    lobe = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed + 8801)
    lobe_n = np.clip(lobe * 0.5 + 0.5, 0, 1).astype(np.float32)
    micro = multi_scale_noise((h, w), [2, 4, 8], [0.5, 0.3, 0.2], seed + 8802)
    micro_n = np.clip(micro * 0.5 + 0.5, 0, 1).astype(np.float32)
    M = 190.0 + lobe_n * 20.0 * sm + micro_n * 5.0 * sm
    R = 20.0 + (1.0 - lobe_n) * 8.0 * sm + micro_n * 4.0 * sm
    CC = 16.0 + micro_n * 3.0
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


def paint_labradorite_flash(paint, shape, mask, seed, pm, bb):
    """Labradorite Flash — dark gray stone base with sudden dramatic blue-gold
    iridescent flash in a localized zone. Most of the surface is plain dark stone.
    One region BLAZES with color when you hit the right angle.
    The flash zone position is noise-driven (organic, not geometric).
    Real reference: Labradorite feldspar gemstone."""
    h, w = shape[:2] if len(shape) > 2 else shape

    # Flash zone: large-scale noise defines WHERE the labradorescence lives
    zone_noise = multi_scale_noise((h, w), [64, 128], [0.4, 0.6], seed + 8810)
    # Sharp threshold: only ~30% of surface gets the flash zone
    flash_zone = np.clip((zone_noise - 0.2) * 3.0, 0, 1).astype(np.float32)

    # Within the flash zone: blue-gold iridescent color
    hue_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 8811)
    hue_blend = np.clip(hue_noise * 0.5 + 0.5, 0, 1).astype(np.float32)

    # Blue: [0.08, 0.15, 0.55], Gold: [0.60, 0.45, 0.10]
    blue = np.array([0.08, 0.15, 0.55], dtype=np.float32)
    gold = np.array([0.60, 0.45, 0.10], dtype=np.float32)
    flash_color = (blue[np.newaxis, np.newaxis, :] * (1 - hue_blend[:,:,np.newaxis]) +
                   gold[np.newaxis, np.newaxis, :] * hue_blend[:,:,np.newaxis])

    # Angle sensitivity: flash is strongest at ~45° (moderate bb values)
    angle_response = np.clip(1.0 - np.abs(bb - 0.5) * 3.0, 0, 1).astype(np.float32)

    # Dark stone base: push toward dark gray
    gray = paint[:,:,:3].mean(axis=2, keepdims=True)
    stone_color = np.clip(gray * 0.35, 0, 0.10)
    # Fine grain texture for stone feel
    grain = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + 8812)
    stone_color = np.clip(stone_color + grain[:,:,np.newaxis] * 0.015 * pm, 0, 1)

    # Compose: stone everywhere, flash color in flash zones modulated by angle
    flash_strength = flash_zone * angle_response * pm
    result = stone_color * (1 - flash_strength[:,:,np.newaxis]) + flash_color * flash_strength[:,:,np.newaxis]

    m3 = mask[:,:,np.newaxis]
    blend = np.clip(pm * 0.90, 0, 1)
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + result * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)


def spec_labradorite_flash(shape, seed, sm, base_m, base_r):
    """Labradorite Flash spec — MARRIED to paint_labradorite_flash.
    Stone zones: low M (dark dielectric), high R (rough stone).
    Flash zones: high M (metallic iridescent reflection), low R (mirror-sharp).
    Uses the SAME zone_noise seed so spec knows where paint put the flash."""
    h, w = shape[:2] if len(shape) > 2 else shape

    # SAME flash zone as paint — married by seed
    zone_noise = multi_scale_noise((h, w), [64, 128], [0.4, 0.6], seed + 8810)
    flash_zone = np.clip((zone_noise - 0.2) * 3.0, 0, 1).astype(np.float32)

    # Stone grain for texture variation
    grain = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.3, 0.3], seed + 8812)
    grain_n = np.clip(grain * 0.5 + 0.5, 0, 1).astype(np.float32)

    # M: dark stone = 20-40, flash zone = 180-220
    M = 25.0 + flash_zone * 180.0 * sm + grain_n * 15.0 * sm * (1 - flash_zone)
    # R: stone = 80-120 (rough), flash zone = 15-25 (near-mirror for specular pop)
    R = 100.0 * (1 - flash_zone) + 18.0 * flash_zone + grain_n * 20.0 * (1 - flash_zone) * sm
    # CC: stone = 80-100 (matte stone), flash zone = 16-20 (max gloss for the reveal)
    CC = 90.0 * (1 - flash_zone) + 16.0 * flash_zone + grain_n * 10.0 * (1 - flash_zone)

    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


def paint_hummingbird_gorget(paint, shape, mask, seed, pm, bb):
    """Hummingbird Gorget — the most dramatic angle-dependent flash in nature.
    DARK from most angles. Then at one narrow viewing cone (~15°), BRILLIANT
    magenta-red-orange flash. Like a strobe hitting the car at one angle.
    Real reference: Ruby-throated Hummingbird gorget feathers.
    Uses bb (angle proxy) with a sharp Gaussian gate for the narrow flash cone."""
    h, w = shape[:2] if len(shape) > 2 else shape

    # Feather-scale texture: fine cells that individually catch light
    cell_noise = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 8820)
    cells = np.clip(cell_noise * 0.5 + 0.5, 0, 1).astype(np.float32)

    # NARROW flash cone: only fires when bb is in a tight range (0.35-0.55)
    cone_center = 0.45
    cone_width = 0.10
    flash_gate = np.exp(-((bb - cone_center) ** 2) / (2 * cone_width ** 2)).astype(np.float32)
    flash_gate = np.clip(flash_gate, 0, 1)

    # Per-cell flash variation: each micro-scale cell fires slightly differently
    cell_variation = np.clip(cells * 0.8 + 0.2, 0.2, 1.0).astype(np.float32)

    # Flash color: magenta-red-orange gradient based on cell position
    cell_phase = multi_scale_noise((h, w), [6, 12], [0.5, 0.5], seed + 8821)
    hue_field = np.clip(cell_phase * 0.5 + 0.5, 0, 1).astype(np.float32)
    magenta = np.array([0.70, 0.05, 0.40], dtype=np.float32)
    red_orange = np.array([0.85, 0.20, 0.05], dtype=np.float32)
    flash_color = (magenta[np.newaxis, np.newaxis, :] * (1 - hue_field[:,:,np.newaxis]) +
                   red_orange[np.newaxis, np.newaxis, :] * hue_field[:,:,np.newaxis])

    # Dark base: nearly black with faint warm undertone
    dark_base = np.clip(paint[:,:,:3] * 0.08 + 0.02, 0, 0.10)
    grain = multi_scale_noise((h, w), [2, 4], [0.5, 0.5], seed + 8822)
    dark_base = np.clip(dark_base + grain[:,:,np.newaxis] * 0.008, 0, 0.12)

    # Compose: dark everywhere, flash color ONLY in the narrow cone
    flash_intensity = flash_gate * cell_variation * pm
    result = dark_base * (1 - flash_intensity[:,:,np.newaxis]) + flash_color * flash_intensity[:,:,np.newaxis]

    m3 = mask[:,:,np.newaxis]
    blend = np.clip(pm * 0.92, 0, 1)
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * blend) + result * m3 * blend
    return np.clip(paint, 0, 1).astype(np.float32)


def spec_hummingbird_gorget(shape, seed, sm, base_m, base_r):
    """Hummingbird Gorget spec — MARRIED to paint_hummingbird_gorget.
    Dark zones: low M (dielectric black), high R (matte dark feathers).
    Flash cells: high M (metallic barbule flash), low R (mirror-sharp specular).
    Uses the SAME cell_noise seed so spec aligns with paint's per-cell structure.
    The M/R inversion between dark/flash cells is what creates the DRAMA."""
    h, w = shape[:2] if len(shape) > 2 else shape

    # SAME cell texture as paint — married by seed
    cell_noise = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 8820)
    cells = np.clip(cell_noise * 0.5 + 0.5, 0, 1).astype(np.float32)

    # Cell-level M variation: each barbule has slightly different metallic character
    M = 30.0 + cells * 190.0 * sm
    # R inversely correlated: high M cells are smooth, low M cells are rough
    R = 120.0 * (1 - cells * 0.85 * sm) + 15.0
    # CC: tight, max clearcoat on flash cells, slightly degraded in gaps
    CC = 16.0 + (1 - cells) * 20.0

    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


_load_v2_base_upgrades()

