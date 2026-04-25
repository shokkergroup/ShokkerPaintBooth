"""
MICRO-FLAKE COLOR SHIFT ENGINE
===============================
Ultra-fine per-pixel color variation that creates living, breathing metallic
surfaces. Each pixel has its own slightly different color and metallic value.

The grain is generated at FULL RESOLUTION — no downscale/upscale. The blur
is minimal (0.6-1.0px) so individual flakes are 1-2 pixels. At 2048x2048
you should NOT be able to see individual dots at normal zoom.

The spec map mirrors the paint with per-pixel M/R micro-variation that
creates angle-dependent Fresnel color shift in iRacing's PBR renderer.
"""

import numpy as np
import cv2


def _grain(shape, seed, blur_sigma=0.7):
    """Per-pixel random noise with MINIMAL blur. Generated at FULL resolution.
    blur_sigma=0.7  to flakes are ~1.5px. Should be invisible at normal zoom."""
    rng = np.random.RandomState(seed)
    raw = rng.random(shape).astype(np.float32)
    if blur_sigma > 0.2:
        ksize = max(3, int(blur_sigma * 3) | 1)
        raw = cv2.GaussianBlur(raw, (ksize, ksize), blur_sigma)
    mn, mx = raw.min(), raw.max()
    if mx > mn:
        raw = (raw - mn) / (mx - mn)
    return raw


def _layered_grain(shape, seed):
    """3-layer grain: ultra-fine (dominant) + two subtle larger layers for organic feel.
    All at FULL resolution — no downscaling."""
    g1 = _grain(shape, seed, blur_sigma=0.35)       # Ultra-fine: mostly pixel-scale
    g2 = _grain(shape, seed + 1000, blur_sigma=0.9) # Fine: 1-2px clusters
    g3 = _grain(shape, seed + 2000, blur_sigma=2.2) # Soft body, not visible blobs
    result = g1 * 0.56 + g2 * 0.32 + g3 * 0.12
    mn, mx = result.min(), result.max()
    if mx > mn:
        result = (result - mn) / (mx - mn)
    return result


def _hsv_to_rgb(h_deg, s, v):
    h_norm = (h_deg % 360) / 60.0
    c = v * s
    x = c * (1 - abs(h_norm % 2 - 1))
    m = v - c
    if h_norm < 1:   r, g, b = c, x, 0
    elif h_norm < 2: r, g, b = x, c, 0
    elif h_norm < 3: r, g, b = 0, c, x
    elif h_norm < 4: r, g, b = 0, x, c
    elif h_norm < 5: r, g, b = x, 0, c
    else:            r, g, b = c, 0, x
    return (r + m, g + m, b + m)


def _map_gradient(noise, rgb_stops):
    """Map 0-1 noise through multi-stop RGB gradient via LUT."""
    h, w = noise.shape
    n = len(rgb_stops)
    if n < 2:
        c = rgb_stops[0]
        return np.stack([np.full((h, w), c[i], dtype=np.float32) for i in range(3)], axis=2)
    lut = np.zeros((1024, 3), dtype=np.float32)
    for i in range(1024):
        t = i / 1023.0
        seg = t * (n - 1)
        lo = min(int(seg), n - 2)
        frac = seg - lo
        for c in range(3):
            lut[i, c] = rgb_stops[lo][c] + (rgb_stops[lo + 1][c] - rgb_stops[lo][c]) * frac
    idx = np.clip((noise * 1023).astype(np.int32), 0, 1023)
    return lut[idx.ravel()].reshape(h, w, 3)


# ---------------------------------------------------------------------------
# Spec generator — FULL RESOLUTION grain, respects sm (spec multiplier)
# ---------------------------------------------------------------------------

def spec_micro_flake(shape, mask, seed, sm,
                     m_base=225, m_range=25,
                     r_base=18, r_range=8,
                     cc_base=16, cc_range=4,
                     seed_offset=0, sparkle_density=0.01, sparkle_boost=10.0):
    """Spec map with per-pixel M/R micro-variation at FULL resolution.

    Parameters:
        sm: variation scale (lower = subtler shift)
        seed_offset: per-preset perturbation so the grain field differs
            between presets that share the same base/range values.
            Without this every cs_* duo used the same noise field seeds
            (7/107/207/307) and the flake PATTERN was identical across
            all 73 pairs — only the metallic baseline differed with
            average colour brightness. HARDMODE-R3-MICRO uses
            seed_offset to give each pair its own flake topology.
        sparkle_density: fraction of pixels that become bright sparkles
            (default 0.01 = 1%). Lets complementary-pair presets have
            denser sparkle than subtle same-hue pairs.
        sparkle_boost: additive M boost at sparkle pixels.
    """
    h, w = shape
    base_seed = seed + int(seed_offset)
    # ALL grain at full resolution — no downscale
    gm = _layered_grain((h, w), base_seed + 7)
    gr = _layered_grain((h, w), base_seed + 107)
    gr = 1.0 - gr  # Anti-correlate: smooth where most metallic
    mist = _layered_grain((h, w), base_seed + 157)

    # Sparkle particles (rare bright flakes; density is now per-preset).
    rng = np.random.RandomState(base_seed + 207)
    sparkle = rng.random((h, w)).astype(np.float32)
    threshold = max(0.0, min(0.2, 1.0 - float(sparkle_density)))
    sparkle = np.where(sparkle > threshold,
                       (sparkle - threshold) / max(1.0 - threshold, 1e-4),
                       0).astype(np.float32)

    # Build channels — sm scales the variation, not the base
    M = np.clip(m_base + (gm - 0.5) * 2.0 * m_range * sm + sparkle * float(sparkle_boost) * sm + mist * 6.0 * sm, 0, 255)
    R = np.clip(r_base + (gr - 0.5) * 2.0 * r_range * sm - sparkle * 4.0 * sm, 15, 255)
    CC = np.clip(cc_base + (_grain((h, w), base_seed + 307, 0.9) - 0.5) * 2.0 * cc_range * sm + mist * 1.5, 16, 255)
    A = mask * 255

    # Iron rules
    non_chrome = M < 240
    R = np.where(non_chrome, np.maximum(R, 15), R)
    CC = np.maximum(CC, 16)

    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:, :, 0] = np.clip(M, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R, 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(CC, 0, 255).astype(np.uint8)
    spec[:, :, 3] = np.clip(A, 0, 255).astype(np.uint8)
    return spec


# ---------------------------------------------------------------------------
# Paint generator — FULL RESOLUTION, multi-stop color mapping
# ---------------------------------------------------------------------------

def paint_micro_flake(paint, shape, mask, seed, pm, bb,
                      color_stops_hsv=None, blend_strength=0.75,
                      seed_offset=0):
    """Per-pixel multi-color shift at FULL resolution.

    seed_offset — matches the spec's seed_offset so paint and spec agree
    pixel-for-pixel on where the flake grain lies. See spec_micro_flake
    docstring for why this is needed (HARDMODE-R3-MICRO).
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]
    h, w = shape

    if color_stops_hsv is None:
        color_stops_hsv = [(45, 0.85, 0.90), (65, 0.70, 0.85)]

    rgb_stops = [_hsv_to_rgb(*hsv) for hsv in color_stops_hsv]

    # Grain at FULL resolution — different seed than spec (offset = the shift)
    grain = _layered_grain((h, w), seed + int(seed_offset))
    mist = _layered_grain((h, w), seed + int(seed_offset) + 157)
    fine_select = np.clip(grain * 0.74 + mist * 0.26, 0, 1)
    flake_color = _map_gradient(fine_select, rgb_stops)
    glitter = (mist > 0.82).astype(np.float32)[:, :, np.newaxis]
    flake_color = np.clip(flake_color * (0.94 + mist[:, :, np.newaxis] * 0.10) + glitter * 0.045, 0, 1)

    strength = blend_strength * pm
    result = paint.copy()
    for c in range(3):
        result[:, :, c] = np.clip(
            paint[:, :, c] * (1.0 - mask * strength) + flake_color[:, :, c] * mask * strength,
            0, 1)
    return result


# ---------------------------------------------------------------------------
# PRESETS
# ---------------------------------------------------------------------------

MICRO_SHIFT_PRESETS = {
    # 2-color
    "gold_green": {
        "name": "Micro Flake: Gold-Green",
        "desc": "Warm gold with green-gold micro-flakes. Subtle shift — breathes between gold and olive.",
        "stops": [(45, 0.85, 0.90), (72, 0.70, 0.82)],
        "m_base": 224, "m_range": 32, "r_base": 17, "r_range": 11, "blend": 0.78,
    },
    "gold_purple": {
        "name": "Micro Flake: Gold-Purple",
        "desc": "Gold base with violet-bronze micro-flakes. Royal warmth that hints plum at edges.",
        "stops": [(42, 0.80, 0.88), (310, 0.45, 0.70)],
        "m_base": 222, "m_range": 28, "r_base": 19, "r_range": 10, "blend": 0.72,
    },
    "teal_blue": {
        "name": "Micro Flake: Teal-Blue",
        "desc": "Cool teal metallic with deep blue flakes. Ocean depth that darkens at angle.",
        "stops": [(178, 0.72, 0.78), (218, 0.68, 0.70)],
        "m_base": 218, "m_range": 25, "r_base": 18, "r_range": 9, "blend": 0.74,
    },
    "copper_rose": {
        "name": "Micro Flake: Copper-Rose",
        "desc": "Warm copper with rose-pink micro-flakes. Sunset metal that blushes.",
        "stops": [(22, 0.75, 0.84), (345, 0.52, 0.78)],
        "m_base": 220, "m_range": 24, "r_base": 17, "r_range": 8, "blend": 0.75,
    },
    # 3-color
    "gold_olive_emerald": {
        "name": "Micro Flake: Gold  to Olive  to Emerald",
        "desc": "3-shade: warm gold through olive into emerald. Living forest metal.",
        "stops": [(48, 0.82, 0.90), (75, 0.60, 0.78), (145, 0.55, 0.68)],
        "m_base": 225, "m_range": 28, "r_base": 18, "r_range": 10, "blend": 0.76,
    },
    "purple_plum_bronze": {
        "name": "Micro Flake: Purple  to Plum  to Bronze",
        "desc": "3-shade: royal purple through plum into warm bronze. Ancient royalty.",
        "stops": [(280, 0.60, 0.55), (320, 0.50, 0.62), (35, 0.65, 0.75)],
        "m_base": 215, "m_range": 30, "r_base": 20, "r_range": 12, "blend": 0.70,
    },
    "blue_teal_cyan": {
        "name": "Micro Flake: Blue  to Teal  to Cyan",
        "desc": "3-shade oceanic: deep blue through teal into bright cyan. Tropical lagoon.",
        "stops": [(220, 0.70, 0.55), (185, 0.65, 0.70), (175, 0.55, 0.82)],
        "m_base": 220, "m_range": 26, "r_base": 18, "r_range": 9, "blend": 0.74,
    },
    "burgundy_wine_gold": {
        "name": "Micro Flake: Burgundy  to Wine  to Gold",
        "desc": "3-shade luxury: burgundy through wine into gold. Vintage Rolls-Royce.",
        "stops": [(345, 0.70, 0.40), (355, 0.65, 0.55), (42, 0.75, 0.85)],
        "m_base": 218, "m_range": 30, "r_base": 19, "r_range": 11, "blend": 0.72,
    },
    # 4-color
    "sunset_horizon": {
        "name": "Micro Flake: Sunset Horizon",
        "desc": "4-shade: gold  to amber  to coral  to rose. Full sunset in micro-flakes.",
        "stops": [(48, 0.80, 0.92), (28, 0.78, 0.88), (10, 0.65, 0.82), (345, 0.50, 0.78)],
        "m_base": 225, "m_range": 25, "r_base": 17, "r_range": 8, "blend": 0.77,
    },
    "northern_lights": {
        "name": "Micro Flake: Northern Lights",
        "desc": "4-shade aurora: green  to teal  to violet  to magenta at flake level.",
        "stops": [(120, 0.55, 0.72), (175, 0.60, 0.68), (270, 0.50, 0.58), (310, 0.45, 0.65)],
        "m_base": 215, "m_range": 30, "r_base": 20, "r_range": 12, "blend": 0.70,
    },
    "peacock_fan": {
        "name": "Micro Flake: Peacock Fan",
        "desc": "4-shade: deep blue  to teal  to emerald  to bronze. Iridescent feather.",
        "stops": [(225, 0.65, 0.50), (185, 0.60, 0.62), (155, 0.55, 0.68), (55, 0.60, 0.75)],
        "m_base": 220, "m_range": 28, "r_base": 18, "r_range": 10, "blend": 0.73,
    },
    # 5-6 color
    "rainbow_stealth": {
        "name": "Micro Flake: Rainbow Stealth",
        "desc": "6-shade: full rainbow at barely-visible flake level. Only shows in direct sun.",
        "stops": [(0, 0.55, 0.72), (45, 0.50, 0.78), (120, 0.45, 0.70), (200, 0.50, 0.65), (270, 0.45, 0.60), (330, 0.50, 0.68)],
        "m_base": 222, "m_range": 22, "r_base": 18, "r_range": 8, "blend": 0.65,
    },
    "oil_slick": {
        "name": "Micro Flake: Oil Slick",
        "desc": "5-shade: magenta  to violet  to blue  to teal  to green. Gasoline on water, metallic.",
        "stops": [(320, 0.55, 0.65), (275, 0.50, 0.58), (220, 0.55, 0.60), (180, 0.50, 0.65), (140, 0.45, 0.62)],
        "m_base": 218, "m_range": 28, "r_base": 19, "r_range": 10, "blend": 0.72,
    },
    "molten_metal": {
        "name": "Micro Flake: Molten Metal",
        "desc": "5-shade: black  to red  to orange  to gold  to white. Forge-hot at micro scale.",
        "stops": [(0, 0.20, 0.15), (5, 0.80, 0.45), (25, 0.85, 0.75), (45, 0.80, 0.90), (45, 0.15, 0.95)],
        "m_base": 230, "m_range": 25, "r_base": 16, "r_range": 8, "blend": 0.80,
    },
    # Impossible combos
    "red_green_chaos": {
        "name": "Micro Flake: Red-Green Impossible",
        "desc": "Red and green micro-flakes that shouldn't work but the subtlety makes it sing.",
        "stops": [(355, 0.70, 0.72), (15, 0.55, 0.78), (90, 0.45, 0.70), (135, 0.55, 0.65)],
        "m_base": 218, "m_range": 30, "r_base": 20, "r_range": 12, "blend": 0.68,
    },
    "orange_blue_electric": {
        "name": "Micro Flake: Orange-Blue Electric",
        "desc": "Warm orange and cool blue at pixel level. Electric complementary tension.",
        "stops": [(25, 0.75, 0.85), (35, 0.60, 0.78), (200, 0.55, 0.65), (220, 0.65, 0.58)],
        "m_base": 222, "m_range": 28, "r_base": 18, "r_range": 10, "blend": 0.72,
    },
    "pink_yellow_pop": {
        "name": "Micro Flake: Pink-Yellow Pop",
        "desc": "Hot pink and bright yellow at flake scale — surprisingly elegant.",
        "stops": [(330, 0.60, 0.82), (350, 0.45, 0.88), (50, 0.55, 0.90), (60, 0.70, 0.85)],
        "m_base": 225, "m_range": 24, "r_base": 17, "r_range": 8, "blend": 0.75,
    },
    "purple_gold_majesty": {
        "name": "Micro Flake: Purple-Gold Majesty",
        "desc": "Deep purple and rich gold in noble opposition. LSU. Lakers. Royalty.",
        "stops": [(275, 0.65, 0.48), (290, 0.55, 0.58), (45, 0.70, 0.82), (52, 0.80, 0.90)],
        "m_base": 220, "m_range": 30, "r_base": 19, "r_range": 11, "blend": 0.73,
    },
}


def build_micro_shift_monolithics():
    monolithics = {}
    for idx, (key, preset) in enumerate(MICRO_SHIFT_PRESETS.items()):
        stops = preset["stops"]
        mb, mr = preset["m_base"], preset["m_range"]
        rb, rr = preset["r_base"], preset["r_range"]
        bl = preset["blend"]

        preset_seed_offset = (idx + 1) * 173
        sparkle_density = 0.010 + min(0.020, len(stops) * 0.0025)

        def _mk_spec(_mb=mb, _mr=mr, _rb=rb, _rr=rr, _so=preset_seed_offset, _sd=sparkle_density):
            def fn(shape, mask, seed, sm):
                return spec_micro_flake(shape, mask, seed, sm,
                                        m_base=_mb, m_range=_mr,
                                        r_base=_rb, r_range=_rr,
                                        seed_offset=_so,
                                        sparkle_density=_sd,
                                        sparkle_boost=14.0)
            return fn

        def _mk_paint(_stops=stops, _bl=bl, _so=preset_seed_offset):
            def fn(paint, shape, mask, seed, pm, bb):
                return paint_micro_flake(paint, shape, mask, seed, pm, bb,
                                         color_stops_hsv=_stops, blend_strength=_bl,
                                         seed_offset=_so)
            return fn

        monolithics[f"cx_{key}"] = (_mk_spec(), _mk_paint())
        # Backward compat: also register under old microshift_ ID
        monolithics[f"microshift_{key}"] = monolithics[f"cx_{key}"]
    return monolithics


MICRO_SHIFT_MONOLITHICS = build_micro_shift_monolithics()


# ══════════════════════════════════════════════════════════════════════════════
# CS DUO  to MICRO-FLAKE CONVERSION
# Replaces the old flat-gradient CS Duo system with per-pixel micro-flake shifts.
# Each color pair generates a 3-stop gradient (color A  to mid-blend  to color B)
# with independent M/R noise for real shimmer.
# ══════════════════════════════════════════════════════════════════════════════

# Color name  to HSV lookup (H=0-360°, S=0-1, V=0-1)
_COLOR_NAME_HSV = {
    "racing_red": (0, 0.90, 0.80), "fire_orange": (20, 0.90, 0.90),
    "gold": (45, 0.85, 0.90), "sunburst_yellow": (55, 0.90, 0.95),
    "lime_green": (90, 0.80, 0.85), "forest_green": (135, 0.70, 0.50),
    "teal": (178, 0.70, 0.70), "sky_blue": (200, 0.60, 0.85),
    "royal_blue": (225, 0.80, 0.75), "navy": (230, 0.80, 0.35),
    "purple": (270, 0.70, 0.60), "violet": (280, 0.65, 0.65),
    "hot_pink": (330, 0.75, 0.85), "magenta": (310, 0.70, 0.75),
    "copper": (22, 0.75, 0.72), "bronze": (30, 0.65, 0.60),
    "silver": (0, 0.03, 0.78), "gunmetal": (210, 0.12, 0.40),
    "black": (0, 0.0, 0.08), "white": (0, 0.0, 0.95),
    "crimson": (348, 0.85, 0.65), "coral": (16, 0.70, 0.85),
    "amber": (38, 0.85, 0.88), "jade": (155, 0.60, 0.55),
    "cobalt": (215, 0.75, 0.65), "indigo": (260, 0.70, 0.50),
    "honey": (42, 0.75, 0.85), "plum": (295, 0.55, 0.45),
    "mint": (155, 0.45, 0.80), "maroon": (345, 0.80, 0.35),
    "rose": (350, 0.50, 0.80), "emerald": (145, 0.70, 0.55),
    "slate": (210, 0.15, 0.50), "champagne": (48, 0.30, 0.92),
    "titanium": (210, 0.08, 0.60), "lavender": (270, 0.35, 0.78),
    "charcoal": (0, 0.05, 0.28), "ivory": (48, 0.10, 0.95),
    "peach": (28, 0.45, 0.90), "sage": (120, 0.25, 0.60),
    "blush": (348, 0.30, 0.88), "burgundy": (345, 0.75, 0.40),
    "chocolate": (20, 0.70, 0.35), "pewter": (200, 0.08, 0.55),
    "graphite": (0, 0.05, 0.35), "aqua": (180, 0.60, 0.80),
}


def _get_hsv(color_name):
    """Look up a color name and return (H, S, V). Falls back to neutral grey."""
    return _COLOR_NAME_HSV.get(color_name, (0, 0.05, 0.50))


def build_cs_duo_micro_shifts():
    """Build micro-flake monolithics for all CS Duo color pairs.
    Each pair generates a 3-stop HSV gradient: color_a  to midpoint_blend  to color_b
    This creates richer shimmer than a simple 2-stop because the mid-zone
    has its own character (blend of both colors' hue/sat/val).
    """
    # Define all CS Duo pairs: (id_suffix, color_a_name, color_b_name)
    pairs = [
        ("fire_ice", "racing_red", "sky_blue"), ("sunset_ocean", "fire_orange", "royal_blue"),
        ("gold_emerald", "gold", "forest_green"), ("copper_teal", "copper", "teal"),
        ("pink_purple", "hot_pink", "purple"), ("lime_blue", "lime_green", "royal_blue"),
        ("red_gold", "racing_red", "gold"), ("navy_silver", "navy", "silver"),
        ("violet_teal", "violet", "teal"), ("bronze_green", "bronze", "forest_green"),
        ("bronze_navy", "bronze", "navy"), ("green_gold", "forest_green", "gold"),
        ("magenta_gold", "magenta", "gold"), ("navy_gold", "navy", "gold"),
        ("purple_lime", "purple", "lime_green"), ("silver_purple", "silver", "purple"),
        ("gunmetal_orange", "gunmetal", "fire_orange"), ("teal_pink", "teal", "hot_pink"),
        ("black_red", "black", "racing_red"), ("blue_orange", "royal_blue", "fire_orange"),
        ("white_blue", "white", "royal_blue"), ("copper_violet", "copper", "violet"),
        ("yellow_blue", "sunburst_yellow", "royal_blue"), ("pink_teal", "hot_pink", "teal"),
        ("orange_purple", "fire_orange", "purple"), ("gold_navy", "gold", "navy"),
        ("lime_pink", "lime_green", "hot_pink"), ("copper_blue", "copper", "royal_blue"),
        ("white_red", "white", "racing_red"), ("black_gold", "black", "gold"),
        ("silver_red", "silver", "racing_red"), ("teal_orange", "teal", "fire_orange"),
        ("purple_gold", "purple", "gold"), ("navy_orange", "navy", "fire_orange"),
        ("green_blue", "forest_green", "royal_blue"), ("bronze_red", "bronze", "racing_red"),
        ("violet_gold", "violet", "gold"), ("magenta_teal", "magenta", "teal"),
        ("gunmetal_lime", "gunmetal", "lime_green"), ("black_blue", "black", "royal_blue"),
        ("white_green", "white", "forest_green"), ("copper_gold", "copper", "gold"),
        ("red_purple", "racing_red", "purple"), ("sky_gold", "sky_blue", "gold"),
        ("orange_navy", "fire_orange", "navy"), ("lime_violet", "lime_green", "violet"),
        ("silver_teal", "silver", "teal"), ("bronze_purple", "bronze", "purple"),
        ("pink_gold", "hot_pink", "gold"), ("black_silver", "black", "silver"),
        ("white_purple", "white", "purple"), ("copper_lime", "copper", "lime_green"),
        ("magenta_blue", "magenta", "royal_blue"), ("gunmetal_gold", "gunmetal", "gold"),
        ("crimson_jade", "crimson", "jade"), ("coral_cobalt", "coral", "cobalt"),
        ("amber_indigo", "amber", "indigo"), ("honey_plum", "honey", "plum"),
        ("mint_maroon", "mint", "maroon"), ("rose_emerald", "rose", "emerald"),
        ("slate_amber", "slate", "amber"), ("champagne_cobalt", "champagne", "cobalt"),
        ("titanium_crimson", "titanium", "crimson"), ("lavender_jade", "lavender", "jade"),
        ("charcoal_honey", "charcoal", "honey"), ("ivory_indigo", "ivory", "indigo"),
        ("peach_cobalt", "peach", "cobalt"), ("sage_crimson", "sage", "crimson"),
        ("blush_emerald", "blush", "emerald"), ("burgundy_gold", "burgundy", "gold"),
        ("chocolate_mint", "chocolate", "mint"), ("pewter_rose", "pewter", "rose"),
        ("graphite_coral", "graphite", "coral"), ("aqua_maroon", "aqua", "maroon"),
    ]

    monolithics = {}
    # 2026-04-20 HEENAN HARDMODE-R3-MICRO — the original cs_* duo builder
    # used identical spec noise seeds (7/107/207/307) for every one of
    # the 73 pairs, so the flake FIELD was pixel-identical across all of
    # them and only the metallic baseline differed by average colour
    # brightness. Even a gold_green vs a gold_purple shared the same
    # sparkle locations. Now:
    #   - Each pair gets a unique seed_offset (index * 131) that
    #     perturbs the grain, gr, sparkle, and cc fields so every cs_*
    #     monolithic has its own flake topology.
    #   - Sparkle density varies with hue distance (complementary pairs
    #     earn denser sparkle; adjacent-hue pairs stay subtle).
    #   - r_range varies with hue distance too (wider hue gap → wider
    #     roughness swing, reinforcing the visual tension of the flip).
    for idx, (suffix, ca_name, cb_name) in enumerate(pairs):
        ca = _get_hsv(ca_name)
        cb = _get_hsv(cb_name)
        h_a, s_a, v_a = ca
        h_b, s_b, v_b = cb
        h_diff = ((h_b - h_a + 180) % 360) - 180
        h_mid = (h_a + h_diff * 0.5) % 360
        s_mid = (s_a + s_b) * 0.5
        v_mid = (v_a + v_b) * 0.5
        stops = [ca, (h_mid, s_mid, v_mid), cb]

        avg_v = (v_a + v_b) / 2
        hue_distance = abs(h_diff) / 180.0    # 0 = same hue, 1 = complementary

        m_base = int(215 + avg_v * 15)
        m_range = int(22 + (1 - avg_v) * 10 + hue_distance * 14)
        r_base = 16
        r_range = int(10 + avg_v * 6 + hue_distance * 18)
        blend = 0.72 + avg_v * 0.06
        # Complementary pairs earn denser sparkle; same-hue pairs stay subtle.
        sparkle_density = 0.006 + hue_distance * 0.020      # 0.6%..2.6%
        sparkle_boost = 8.0 + hue_distance * 14.0           # 8..22
        # Per-pair seed offset — index * 131 gives 73 unique offsets
        # spread over ~10k integer range (prime step avoids aliasing).
        pair_seed_offset = (idx + 1) * 131

        finish_id = f"cs_{suffix}"

        def _mk_spec(_mb=m_base, _mr=m_range, _rb=r_base, _rr=r_range,
                     _so=pair_seed_offset, _sd=sparkle_density, _sbs=sparkle_boost):
            def fn(shape, mask, seed, sm):
                return spec_micro_flake(shape, mask, seed, sm,
                                        m_base=_mb, m_range=_mr,
                                        r_base=_rb, r_range=_rr,
                                        seed_offset=_so,
                                        sparkle_density=_sd,
                                        sparkle_boost=_sbs)
            return fn

        def _mk_paint(_stops=stops, _bl=blend, _so=pair_seed_offset):
            def fn(paint, shape, mask, seed, pm, bb):
                return paint_micro_flake(paint, shape, mask, seed, pm, bb,
                                         color_stops_hsv=_stops,
                                         blend_strength=_bl,
                                         seed_offset=_so)
            return fn

        monolithics[finish_id] = (_mk_spec(), _mk_paint())

    return monolithics


CS_DUO_MICRO_MONOLITHICS = build_cs_duo_micro_shifts()


# ══════════════════════════════════════════════════════════════════════════════
# COLORSHOXX WAVE 4 — New multi-color flake shifts (2026-04-15)
# Fill color gaps in the unified COLORSHOXX lineup.
# Each uses 3-8 HSV stops through the micro-flake gradient engine.
# ══════════════════════════════════════════════════════════════════════════════

CX_WAVE4_PRESETS = {
    "cotton_candy": {
        "stops": [(340, 0.40, 0.95), (200, 0.35, 0.90), (0, 0.05, 0.98)],
        "m_base": 220, "m_range": 20, "r_base": 18, "r_range": 8, "blend": 0.75,
    },
    "forest_fire": {
        "stops": [(140, 0.70, 0.40), (25, 0.85, 0.80), (0, 0.85, 0.65)],
        "m_base": 215, "m_range": 30, "r_base": 20, "r_range": 12, "blend": 0.78,
    },
    "deep_sea": {
        "stops": [(215, 0.80, 0.20), (178, 0.65, 0.55), (175, 0.55, 0.80), (180, 0.15, 0.95)],
        "m_base": 218, "m_range": 28, "r_base": 19, "r_range": 10, "blend": 0.74,
    },
    "galaxy_dust": {
        "stops": [(280, 0.75, 0.40), (235, 0.80, 0.30), (0, 0.05, 0.78), (335, 0.60, 0.80)],
        "m_base": 222, "m_range": 26, "r_base": 18, "r_range": 10, "blend": 0.72,
    },
    "autumn_blaze": {
        "stops": [(0, 0.80, 0.70), (25, 0.85, 0.80), (45, 0.85, 0.90), (20, 0.65, 0.35)],
        "m_base": 225, "m_range": 25, "r_base": 17, "r_range": 9, "blend": 0.77,
    },
    "thunderstorm": {
        "stops": [(210, 0.15, 0.30), (215, 0.75, 0.70), (0, 0.03, 0.90)],
        "m_base": 215, "m_range": 32, "r_base": 20, "r_range": 12, "blend": 0.76,
    },
    "tropical_sunset": {
        "stops": [(16, 0.65, 0.90), (335, 0.70, 0.75), (48, 0.75, 0.90), (25, 0.80, 0.85)],
        "m_base": 225, "m_range": 24, "r_base": 17, "r_range": 8, "blend": 0.78,
    },
    "black_ice": {
        "stops": [(0, 0.0, 0.08), (210, 0.12, 0.55), (200, 0.35, 0.85)],
        "m_base": 210, "m_range": 35, "r_base": 22, "r_range": 14, "blend": 0.74,
    },
    "cherry_blossom": {
        "stops": [(340, 0.40, 0.90), (0, 0.04, 0.97), (135, 0.30, 0.70)],
        "m_base": 220, "m_range": 20, "r_base": 18, "r_range": 8, "blend": 0.72,
    },
    "volcanic_glass": {
        "stops": [(0, 0.0, 0.10), (0, 0.85, 0.50), (35, 0.85, 0.85), (25, 0.80, 0.80)],
        "m_base": 225, "m_range": 30, "r_base": 18, "r_range": 10, "blend": 0.80,
    },
    "neon_dreams": {
        "stops": [(330, 0.80, 0.90), (195, 0.75, 0.85), (90, 0.80, 0.90), (270, 0.70, 0.80)],
        "m_base": 222, "m_range": 24, "r_base": 17, "r_range": 8, "blend": 0.76,
    },
    "champagne_toast": {
        "stops": [(48, 0.55, 0.88), (0, 0.05, 0.80), (345, 0.25, 0.88), (48, 0.12, 0.95)],
        "m_base": 224, "m_range": 28, "r_base": 16, "r_range": 9, "blend": 0.70,
    },
    "emerald_city": {
        "stops": [(160, 0.70, 0.50), (48, 0.85, 0.90), (170, 0.60, 0.60), (90, 0.80, 0.85)],
        "m_base": 222, "m_range": 26, "r_base": 18, "r_range": 10, "blend": 0.75,
    },
    "midnight_aurora": {
        "stops": [(0, 0.0, 0.08), (145, 0.75, 0.80), (280, 0.70, 0.50), (235, 0.80, 0.30)],
        "m_base": 218, "m_range": 30, "r_base": 20, "r_range": 12, "blend": 0.74,
    },
    "bronze_age": {
        "stops": [(22, 0.70, 0.72), (25, 0.55, 0.55), (48, 0.80, 0.88), (20, 0.60, 0.28)],
        "m_base": 225, "m_range": 25, "r_base": 18, "r_range": 10, "blend": 0.76,
    },
}


def build_cx_wave4_monolithics():
    """Build monolithics for COLORSHOXX Wave 4 new finishes."""
    monolithics = {}
    for idx, (key, preset) in enumerate(CX_WAVE4_PRESETS.items()):
        stops = preset["stops"]
        mb, mr = preset["m_base"], preset["m_range"]
        rb, rr = preset["r_base"], preset["r_range"]
        bl = preset["blend"]

        preset_seed_offset = (idx + 1) * 197
        sparkle_density = 0.012 + min(0.024, len(stops) * 0.003)

        def _mk_spec(_mb=mb, _mr=mr, _rb=rb, _rr=rr, _so=preset_seed_offset, _sd=sparkle_density):
            def fn(shape, mask, seed, sm):
                return spec_micro_flake(shape, mask, seed, sm,
                                        m_base=_mb, m_range=_mr,
                                        r_base=_rb, r_range=_rr,
                                        seed_offset=_so,
                                        sparkle_density=_sd,
                                        sparkle_boost=16.0)
            return fn

        def _mk_paint(_stops=stops, _bl=bl, _so=preset_seed_offset):
            def fn(paint, shape, mask, seed, pm, bb):
                return paint_micro_flake(paint, shape, mask, seed, pm, bb,
                                         color_stops_hsv=_stops, blend_strength=_bl,
                                         seed_offset=_so)
            return fn

        monolithics[f"cx_{key}"] = (_mk_spec(), _mk_paint())
    return monolithics


CX_WAVE4_MONOLITHICS = build_cx_wave4_monolithics()
