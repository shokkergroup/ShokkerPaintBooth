"""
engine/paint_v2/structural_color.py — ★ COLORSHOXX Finishes
Premium color-shifting finishes where paint+spec work as married pairs.

HOW IT WORKS (see docs/COLORSHOXX_ANGLE_REVEAL.md for full doctrine):
1. Bury multiple colors in a dark paint base — they are NOT visible head-on.
2. Fine 8–32px spec pins (2048² canvas) flash at glancing angles only.
3. Directional masks (U / V / diagonal) reveal DIFFERENT hidden colors when panning
   different ways across the car — the COLORSHOXX holy grail (not true hue shift).
4. Reference: cx_electric_storm car photos 2026-05-27 — black straight-on, purple
   when panning; features appear/disappear panel-to-panel.

Classic duo flip (legacy summary):
1. Spatial field divides the surface into zones
2. Paint puts Color A in high-field zones and Color B in low-field zones
3. Spec gives high-field zones HIGH M + LOW R (metallic flash at specular)
   and low-field zones LOWER M + HIGHER R (matte, visible at normal incidence)
4. iRacing's PBR renderer does the rest — high-M zones pop at specular angle,
   low-M zones stay steady. The car appears to FLIP between the two colors.

DIFFERENCE FROM CHAMELEON:
- Chameleon rotates through ALL hues continuously (rainbow)
- COLORSHOXX picks TWO (or three) specific premium colors and flips between them
- More controlled, more intentional, more premium
"""
import numpy as np
import cv2
from functools import lru_cache
from pathlib import Path
from engine.core import multi_scale_noise


def _norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    lo = float(arr.min())
    hi = float(arr.max())
    if hi - lo < 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0, 1).astype(np.float32)


def _colorshoxx_field(shape, seed, flow_scale=0.04, complexity=3):
    """Shared spatial field for paint+spec marriage.
    Smooth, organic, car-panel-following zones. Returns 0-1 float32 array."""
    h, w = shape
    # Multi-scale organic flow field
    n1 = multi_scale_noise((h, w), [32, 64, 128], [0.3, 0.4, 0.3], seed)
    n2 = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 100)
    field = np.clip(n1 * 0.7 + n2 * 0.3, -1, 1)
    # Normalize to 0-1
    field = (field + 1.0) * 0.5
    return np.clip(field, 0, 1).astype(np.float32)


def _colorshoxx_micro(shape, seed):
    """Fine micro-flake variation — per-flake shimmer within zones."""
    micro = multi_scale_noise(shape, [16, 32, 64], [0.5, 0.3, 0.2], seed + 200)
    return np.clip(micro * 0.5 + 0.5, 0, 1).astype(np.float32)


# ============================================================
# COLORSHOXX 01: INFERNO FLIP — Crimson Red ↔ Midnight Blue
# ============================================================

def paint_colorshoxx_inferno(paint, shape, mask, seed, pm, bb):
    """Inferno — buried black base; pan U → crimson flash, pan V → deep blue flash."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    # SPB owner 2026-05-27 angle-reveal doctrine (ref: cx_electric_storm car photos)
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9001,
        (0.03, 0.03, 0.04),
        [((0.92, 0.08, 0.04), "u", 0.88), ((0.08, 0.12, 0.88), "v", 0.82)],
        gate_density=0.0065)


def spec_colorshoxx_inferno(shape, seed, sm, base_m, base_r):
    """Inferno spec — directional buried flash, ΔM≈235 on fine pins."""
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9001,
        m_hi=245, m_lo=8, r_hi=15, r_lo=185, cc_hi=16, cc_lo=160,
        pin_density=0.0065, axis_weights=(("u", 1.0), ("v", 0.9), ("diag_a", 0.7)))


# ============================================================
# COLORSHOXX 02: ARCTIC MIRAGE — Ice Silver ↔ Deep Teal
# ============================================================

def paint_colorshoxx_arctic(paint, shape, mask, seed, pm, bb):
    """Arctic — buried void; U → ice silver, V → deep teal at glancing angles."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9002,
        (0.04, 0.05, 0.06),
        [((0.88, 0.92, 0.98), "u", 0.86), ((0.05, 0.42, 0.48), "v", 0.80)],
        gate_density=0.0062)


def spec_colorshoxx_arctic(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9002,
        m_hi=248, m_lo=6, r_hi=15, r_lo=190, cc_hi=16, cc_lo=165,
        pin_density=0.0062, axis_weights=(("u", 1.0), ("v", 0.88), ("diag_b", 0.72)))


# ============================================================
# COLORSHOXX 03: VENOM SHIFT — Toxic Green ↔ Black Purple
# ============================================================

def paint_colorshoxx_venom(paint, shape, mask, seed, pm, bb):
    """Venom — buried black; U → toxic green, V → black-purple flash."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9003,
        (0.02, 0.03, 0.02),
        [((0.35, 0.95, 0.12), "u", 0.90), ((0.45, 0.05, 0.55), "v", 0.78)],
        gate_density=0.0068)


def spec_colorshoxx_venom(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9003,
        m_hi=242, m_lo=5, r_hi=15, r_lo=192, cc_hi=16, cc_lo=170,
        pin_density=0.0068, axis_weights=(("u", 1.0), ("v", 0.85), ("diag_a", 0.75)))


# ============================================================
# COLORSHOXX 04: SOLAR FLARE — Gold ↔ Copper Red
# ============================================================

def paint_colorshoxx_solar(paint, shape, mask, seed, pm, bb):
    """Solar — buried dark base; U → liquid gold, V → copper-red flash."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9004,
        (0.05, 0.04, 0.03),
        [((0.98, 0.82, 0.15), "u", 0.85), ((0.82, 0.18, 0.08), "v", 0.80)],
        gate_density=0.0060)


def spec_colorshoxx_solar(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9004,
        m_hi=248, m_lo=12, r_hi=15, r_lo=175, cc_hi=16, cc_lo=145,
        pin_density=0.0060, axis_weights=(("u", 1.0), ("v", 0.88), ("diag_b", 0.70)))


# ============================================================
# COLORSHOXX 05: PHANTOM VIOLET — Electric Violet ↔ Gunmetal
# ============================================================

def paint_colorshoxx_phantom(paint, shape, mask, seed, pm, bb):
    """Phantom — buried gunmetal void; U → electric violet, V → cold steel."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9005,
        (0.06, 0.06, 0.08),
        [((0.55, 0.15, 0.95), "u", 0.88), ((0.18, 0.28, 0.38), "v", 0.76)],
        gate_density=0.0064)


def spec_colorshoxx_phantom(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9005,
        m_hi=245, m_lo=10, r_hi=15, r_lo=180, cc_hi=16, cc_lo=155,
        pin_density=0.0064, axis_weights=(("u", 1.0), ("v", 0.86), ("diag_a", 0.74)))


# ================================================================
# COLORSHOXX WAVE 2 — 20 more finishes with EXTREME detail
# Fine-scale noise (1-4px cells), chrome↔matte extremes, 3 & 4 color
# ================================================================

def _cx_fine_field(shape, seed):
    """FINE detail field with SHARP zone boundaries — NOT smooth blobs.
    Domain-warped noise creates organic but DEFINED zones with visible edges.
    Multiple frequency layers create structure at multiple scales."""
    h, w = shape
    # Domain warp: warp coordinates with one noise field, sample another at warped positions
    warp_x = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 10)
    warp_y = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 20)
    yy = np.arange(h, dtype=np.float32).reshape(h, 1) * np.ones((1, w), dtype=np.float32)
    xx = np.arange(w, dtype=np.float32).reshape(1, w) * np.ones((h, 1), dtype=np.float32)
    # Warp coordinates — this creates stretching/folding that makes zones ORGANIC not blobby
    wy = np.clip((yy + warp_y * h * 0.08).astype(np.int32), 0, h - 1)
    wx = np.clip((xx + warp_x * w * 0.08).astype(np.int32), 0, w - 1)
    # Sample a structured noise at warped positions
    base_noise = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed)
    warped = base_noise[wy, wx]
    # Add fine detail for micro-texture within zones
    fine = multi_scale_noise((h, w), [32, 64], [0.6, 0.4], seed + 50)
    # Combine: warped structure (70%) + fine detail (20%) + slight large-scale bias (10%)
    large = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 80)
    field = np.clip(warped * 0.70 + fine * 0.20 + large * 0.10, -1, 1)
    # SHARPEN: push values toward 0 and 1 (not smooth middle)
    normalized = (field + 1.0) * 0.5
    sharpened = np.clip((normalized - 0.5) * 2.4 + 0.5, 0, 1)  # B06: stronger sharpening for defined zone boundaries
    return sharpened.astype(np.float32)

def _cx_ultra_micro(shape, seed):
    """Ultra-fine per-flake — scale 1-2px for individual metallic particle shimmer."""
    m = multi_scale_noise(shape, [1, 2, 3], [0.5, 0.3, 0.2], seed + 300)
    return np.clip(m * 0.5 + 0.5, 0, 1).astype(np.float32)

# 2026-05-04 SPB-67: COLORSHOXX carrier refresh. The previous 2048-aware
# helper built six full-size multi_scale_noise fields per paint/spec pass,
# which made some COLORSHOXX items look good but needlessly expensive. This
# keeps the same married paint/spec seed contract while switching to vector
# harmonics plus hash flake fields: sharper detail, less memory churn, and no
# single visual "clone stamp" across the family because each ID still drives
# unique seeds, palettes, and zone splits.
def _cx_xy(shape):
    h, w = shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _cx_hash01(shape, seed, salt=0):
    x, y = _cx_xy(shape)
    s = float(seed + salt) * 0.00137
    n = np.sin((x * (127.1 + (salt % 11) * 3.7) + y * (311.7 + (salt % 7) * 5.1) + s) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _cx_fine_field(shape, seed):
    h, w = shape
    x, y = _cx_xy(shape)
    s = float(seed) * 0.017
    angle_a = 0.73 + (seed % 17) * 0.071
    angle_b = 1.91 + (seed % 23) * 0.053
    p1 = x * np.cos(angle_a) + y * np.sin(angle_a)
    p2 = x * np.cos(angle_b) - y * np.sin(angle_b)
    radial = np.sqrt((x - 0.50 - 0.035 * np.sin(s)) ** 2 + (y - 0.50 - 0.035 * np.cos(s * 0.7)) ** 2)

    macro = np.sin((p1 * (7.5 + (seed % 5) * 0.9) + radial * 2.7 + s) * np.pi)
    cross = np.cos((p2 * (11.0 + (seed % 7) * 0.8) - radial * 3.3 + s * 1.31) * np.pi)
    shard = np.sin((x * (31.0 + (seed % 13)) + y * (19.0 + (seed % 9)) + np.sin(p1 * np.pi * 6.0)) * np.pi)
    micro = _cx_hash01(shape, seed, 50) * 2.0 - 1.0
    pepper = _cx_hash01(shape, seed, 80) * 2.0 - 1.0

    field = macro * 0.34 + cross * 0.25 + shard * 0.20 + micro * 0.15 + pepper * 0.06
    field = np.clip((field + 1.0) * 0.5, 0, 1)
    field = np.clip((field - 0.5) * 2.45 + 0.5, 0, 1)
    return field.astype(np.float32)


def _cx_ultra_micro(shape, seed):
    # SPB paint-finish perf loop 2026-06-04; owner: "Speed is king in this app."
    # _cx_ultra_micro was 2 full-res hash sines (0.48/0.34) + a smooth line sine.
    # The two independent hashes only existed to decorrelate the per-pixel grain;
    # one hash, centered and rescaled to the SAME combined std (sqrt(.48^2+.34^2)*u),
    # is statistically identical (mean 0.5, std 0.208 to 4 decimals at every res) but
    # spends one fewer full-res np.sin. Hot for the whole COLORSHOXX family + the
    # spectrum-pop gate stacks. Single-hash carrier validated std/mean drift < 1e-3.
    x, y = _cx_xy(shape)
    hash_a = _cx_hash01(shape, seed, 300)
    lines = 0.5 + 0.5 * np.sin((x * (91.0 + seed % 19) + y * (67.0 + seed % 13) + seed * 0.011) * np.pi)
    # 0.82 = combined hash weight (0.48 + 0.34); 0.7173 rescales one uniform hash's
    # std up to the two-hash mixture std so downstream thresholds keep the same grain.
    hgrain = (hash_a - 0.5) * 0.7173 + 0.5
    micro = hgrain * 0.82 + lines.astype(np.float32) * 0.18
    return np.clip(micro, 0, 1).astype(np.float32)


def _cx_mist(shape, seed, density=0.34):
    micro = _cx_ultra_micro(shape, seed + 701)
    glint = _cx_hash01(shape, seed, 707)
    carrier = np.clip(micro * 0.62 + glint * 0.38, 0, 1)
    return (carrier > (1.0 - float(density))).astype(np.float32), carrier


_CX_STYLE = {
    9001: ("ember_ribbon", 0.40, 0.54, 0.24),
    9002: ("ice_pearl", 0.22, 0.42, 0.18),
    9003: ("toxic_venom", 0.34, 0.58, 0.20),
    9004: ("solar_candy", 0.44, 0.62, 0.28),
    9005: ("violet_ghost", 0.28, 0.48, 0.18),
    9010: ("chrome_void", 0.18, 0.44, 0.16),
    9011: ("blood_glass", 0.32, 0.56, 0.22),
    9012: ("neon_abyss", 0.38, 0.62, 0.22),
    9013: ("thermal_shatter", 0.42, 0.64, 0.28),
    9014: ("obsidian_gold", 0.36, 0.60, 0.30),
    9015: ("electric_storm", 0.40, 0.66, 0.18),
    9016: ("rose_velvet", 0.26, 0.50, 0.16),
    9017: ("acid_chrome", 0.38, 0.64, 0.22),
    9018: ("midnight_chrome", 0.22, 0.46, 0.16),
    9019: ("white_lightning", 0.30, 0.58, 0.18),
    9020: ("aurora_glass", 0.36, 0.60, 0.20),
    9021: ("dragon_scale", 0.42, 0.68, 0.32),
    9022: ("frozen_nebula", 0.30, 0.54, 0.20),
    9023: ("hellfire", 0.46, 0.70, 0.30),
    9024: ("ocean_trench", 0.30, 0.54, 0.18),
    9025: ("supernova", 0.48, 0.72, 0.26),
    9026: ("prism_shatter", 0.44, 0.74, 0.34),
    9027: ("acid_rain", 0.40, 0.68, 0.22),
    9028: ("royal_spectrum", 0.38, 0.66, 0.28),
    9029: ("apocalypse", 0.46, 0.70, 0.30),
}


def _cx_style(seed_off):
    return _CX_STYLE.get(seed_off, ("crystal_microflake", 0.34, 0.58, 0.22))


def _cx_tri_wave(arr):
    return (1.0 - np.abs((arr % 1.0) * 2.0 - 1.0)).astype(np.float32)


def _cx_work_shape(shape, max_work=768):
    # SPB paint-finish perf loop 2026-06-04; owner: "Speed is king in this app."
    # COLORSHOXX 3-/4-color paint material and reference spec are built from a
    # downscaled reference photo then upscaled to canvas, so the material-compute
    # resolution only sets carrier smoothness, not the visible flake (a full-res
    # 1px hash carrier is added after upscale). Dropping the cap 896 -> 768 trims
    # the per-pixel material arithmetic ~27% with the 2048->256 render moving
    # < 0.3/255 mean and std drift ~0.05% (validated cap sweep, p99 diff = 2).
    h, w = shape[:2] if len(shape) > 2 else shape
    h = int(h)
    w = int(w)
    if max(h, w) <= max_work:
        return h, w
    scale = float(max_work) / float(max(h, w))
    return max(1, int(round(h * scale))), max(1, int(round(w * scale)))


def _cx_material(shape, seed, seed_off):
    h, w = shape
    global _CX_MATERIAL_LAST_KEY, _CX_MATERIAL_LAST_VALUE
    cache_key = (int(h), int(w), int(seed), int(seed_off))
    if cache_key == _CX_MATERIAL_LAST_KEY and _CX_MATERIAL_LAST_VALUE is not None:
        return _CX_MATERIAL_LAST_VALUE
    if max(h, w) > _CX_REF_MAX_ANALYSIS and seed_off in _CX_REF_PROFILE:
        scale = _CX_REF_MAX_ANALYSIS / float(max(h, w))
        cache_w = max(1, int(round(w * scale)))
        cache_h = max(1, int(round(h * scale)))
        material = _cx_material_cached(cache_h, cache_w, int(seed), int(seed_off))
        out = tuple(cv2.resize(arr, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32) for arr in material)
    else:
        out = _cx_material_cached(int(h), int(w), int(seed), int(seed_off))
    _CX_MATERIAL_LAST_KEY = cache_key
    _CX_MATERIAL_LAST_VALUE = out
    return out


@lru_cache(maxsize=64)
def _cx_material_cached(h, w, seed, seed_off):
    """Dense reference-inspired COLORSHOXX surface language.

    Returns a small set of married paint/spec carriers: color driver, crushed
    glass texture, spec glints, rosette flakes, and fine shadow. Profiles are
    keyed by finish seed so the category reads like one premium family without
    repeating one pattern.
    """
    shape = (h, w)
    ref_material = _cx_reference_material(shape, seed, seed_off)
    if ref_material is not None:
        return ref_material
    style, sparkle_density, shard_gain, rosette_gain = _cx_style(seed_off)
    x, y = _cx_xy(shape)
    s = float(seed + seed_off) * 0.0091
    angle = 0.35 + ((seed_off * 37) % 314) / 100.0
    ca, sa = np.cos(angle), np.sin(angle)
    u = x * ca + y * sa
    v = x * -sa + y * ca
    cx = 0.50 + np.sin(s * 0.71) * 0.08
    cy = 0.50 + np.cos(s * 0.63) * 0.08
    dx = x - cx
    dy = y - cy
    dist = np.sqrt(dx * dx + dy * dy)
    theta = np.arctan2(dy, dx + 1e-7)

    field = _cx_fine_field(shape, seed + seed_off)
    h1 = _cx_hash01(shape, seed + seed_off, 101)
    h2 = _cx_hash01(shape, seed + seed_off, 151)
    h3 = _cx_hash01(shape, seed + seed_off, 191)
    micro = _cx_ultra_micro(shape, seed + seed_off)

    shard_a = _cx_tri_wave(u * (31.0 + seed_off % 17) + v * (7.0 + seed_off % 5) + h1 * 0.38)
    shard_b = _cx_tri_wave(v * (43.0 + seed_off % 19) - u * (11.0 + seed_off % 7) + h2 * 0.31)
    shard_c = _cx_tri_wave((u + v) * (57.0 + seed_off % 23) + np.sin(theta * 2.0 + s) * 0.12)
    glass = np.clip((shard_a * shard_b) * 0.48 + (shard_b * shard_c) * 0.34 + h3 * 0.18, 0, 1)
    glass = np.clip((glass - 0.18) * (1.7 + shard_gain), 0, 1)

    cells = 9.0 + (seed_off % 6) * 1.7
    jx = _cx_hash01(shape, seed + seed_off, 331) * 0.16 - 0.08
    jy = _cx_hash01(shape, seed + seed_off, 337) * 0.16 - 0.08
    lx = ((u * cells + jx) % 1.0) - 0.5
    ly = ((v * cells + jy) % 1.0) - 0.5
    rr = np.sqrt(lx * lx + ly * ly)
    aa = np.arctan2(ly, lx + 1e-7)
    petals = 0.5 + 0.5 * np.cos(aa * (8.0 + seed_off % 5) + s)
    rosette = np.clip((0.32 - rr) * 6.0, 0, 1) * np.power(np.clip(petals, 0, 1), 2.0)
    rosette *= (h1 > (0.78 - rosette_gain * 0.22)).astype(np.float32)

    sparkle = np.clip((h2 - (0.96 - sparkle_density * 0.11)) * 28.0, 0, 1)
    pin = np.clip((micro - (0.86 - sparkle_density * 0.10)) * 9.0, 0, 1)

    if style in {"ember_ribbon", "solar_candy", "hellfire", "apocalypse", "blood_glass"}:
        ribbon = np.clip(0.5 + 0.5 * np.sin((u * 5.5 + np.sin(v * 14.0 + s) * 0.16 + dist * 2.4) * np.pi), 0, 1)
        driver = np.clip(field * 0.44 + ribbon * 0.36 + glass * 0.20, 0, 1)
        rosette *= 1.18
    elif style in {"ice_pearl", "frozen_nebula", "white_lightning"}:
        frost = np.clip(0.5 + 0.5 * np.cos((u * 17.0 - v * 23.0 + h1 * 0.24) * np.pi), 0, 1)
        driver = np.clip(field * 0.36 + frost * 0.30 + glass * 0.34, 0, 1)
        sparkle *= 1.35
    elif style in {"electric_storm", "prism_shatter", "supernova", "royal_spectrum"}:
        facets = np.clip(shard_a * 0.35 + shard_b * 0.34 + shard_c * 0.31, 0, 1)
        driver = np.clip(field * 0.28 + facets * 0.52 + glass * 0.20, 0, 1)
        sparkle *= 1.25
        rosette *= 0.82
    elif style in {"toxic_venom", "acid_chrome", "acid_rain", "ocean_trench", "aurora_glass"}:
        current = np.clip(0.5 + 0.5 * np.sin((u * 9.0 + np.sin(v * 20.0 + s) * 0.18 + theta * 0.12) * np.pi), 0, 1)
        driver = np.clip(field * 0.34 + current * 0.34 + glass * 0.32, 0, 1)
        rosette *= 0.72
    elif style in {"chrome_void", "midnight_chrome", "violet_ghost", "rose_velvet"}:
        velvet = np.clip(0.5 + 0.5 * np.cos((dist * 20.0 - theta * 0.9 + s) * np.pi), 0, 1)
        driver = np.clip(field * 0.46 + velvet * 0.22 + glass * 0.32, 0, 1)
        sparkle *= 0.88
    elif style == "dragon_scale":
        # SPB owner 2026-05-27 cx_dragon_scale — 8-32px overlapping scale lattice
        scale_a = np.clip(1.0 - np.abs(np.sin((u * 52.0 + np.sin(v * 31.0 + s) * 0.22) * np.pi)), 0, 1)
        scale_b = np.clip(1.0 - np.abs(np.sin((v * 48.0 + np.cos(u * 27.0 + s * 0.7) * 0.18) * np.pi)), 0, 1)
        overlap = np.clip(scale_a * 0.55 + scale_b * 0.45, 0, 1) ** 1.35
        driver = np.clip(field * 0.22 + overlap * 0.52 + glass * 0.26, 0, 1)
        rosette *= 1.85
    else:
        driver = np.clip(field * 0.42 + glass * 0.42 + micro * 0.16, 0, 1)

    glint = np.clip(glass * 0.34 + sparkle * 0.55 + pin * 0.32 + rosette * 0.42, 0, 1)
    shadow = np.clip((1.0 - glass) * 0.16 + (1.0 - field) * 0.10, 0, 0.32)
    return driver.astype(np.float32), glass.astype(np.float32), glint.astype(np.float32), rosette.astype(np.float32), shadow.astype(np.float32)


def _cx_accent(c1, c2, seed_off):
    accent = np.clip((c1 * 0.42 + c2 * 0.42 + np.roll(c1 + c2, seed_off % 3) * 0.16), 0, 1)
    white = np.array([1.0, 0.96, 0.86], dtype=np.float32)
    return np.clip(accent * 0.72 + white * 0.28, 0, 1)


try:
    from engine.asset_packs import resolve_ref_dir as _cx_rrd
except Exception:
    try:
        from ..asset_packs import resolve_ref_dir as _cx_rrd
    except Exception:
        _cx_rrd = lambda r: str(Path(__file__).resolve().parents[2] / "assets" / "reference_textures" / r)  # noqa: E731
# finish-pack-downloader 2026-06-07: route through resolver so a DOWNLOADED colorshoxx pack works
_CX_REF_DIR = Path(_cx_rrd("colorshoxx"))
_CX_REF_MAX_ANALYSIS = 1024
_CX_MATERIAL_LAST_KEY = None
_CX_MATERIAL_LAST_VALUE = None
_CX_REF_TEXTURE_LAST_KEY = None
_CX_REF_TEXTURE_LAST_VALUE = None


_CX_REF_PROFILE = {
    9001: ("red_gold_rosette.png", "gold_red_panel.png", "ribbon", 0.88),
    9002: ("silver_pearl_panel.png", "crystal_ice_panel.png", "pearl", 0.82),
    9003: ("lime_green_microflake.png", "teal_gold_texture.png", "venom", 0.90),
    9004: ("rainbow_candy_flake.png", "gold_red_panel.png", "candy_sweep", 0.86),
    9005: ("magenta_blue_crystal.png", "blue_magenta_sequin.png", "violet_depth", 0.88),
    9010: ("black_rainbow_flow.png", "silver_pearl_panel.png", "black_chrome", 0.92),
    9011: ("gold_red_panel.png", "orange_magenta_glass.png", "blood_glass", 0.84),
    9012: ("magenta_blue_crystal.png", "black_rainbow_flow.png", "neon_crush", 0.82),
    9013: ("crystal_ice_panel.png", "orange_magenta_glass.png", "thermal_split", 0.78),
    9014: ("gold_red_panel.png", "black_rainbow_flow.png", "obsidian_gold", 0.80),
    9015: ("aqua_violet_microflake.png", "blue_magenta_sequin.png", "electric_facets", 0.84),
    9016: ("orange_magenta_glass.png", "white_opal_flake.png", "rose_pearl", 0.80),
    9017: ("teal_gold_texture.png", "lime_green_microflake.png", "acid_glass", 0.86),
    9018: ("black_rainbow_flow.png", "blue_magenta_sequin.png", "midnight", 0.88),
    9019: ("white_opal_flake.png", "silver_pearl_panel.png", "white_flash", 0.84),
    9020: ("teal_microflake.png", "aqua_violet_microflake.png", "aurora", 0.80),
    9021: ("red_gold_rosette.png", "gold_red_panel.png", "scale_rosette", 0.90),
    9022: ("crystal_ice_panel.png", "aqua_violet_microflake.png", "nebula_ice", 0.84),
    9023: ("red_gold_rosette.png", "orange_magenta_glass.png", "hellfire", 0.88),
    9024: ("teal_microflake.png", "black_rainbow_flow.png", "deep_current", 0.82),
    9025: ("rainbow_candy_flake.png", "blue_magenta_sequin.png", "supernova", 0.82),
    9026: ("crystal_ice_panel.png", "rainbow_candy_flake.png", "prism_shards", 0.82),
    9027: ("lime_green_microflake.png", "magenta_blue_crystal.png", "acid_rain", 0.84),
    9028: ("rainbow_candy_flake.png", "teal_seafoam_panel.png", "jewel_crown", 0.84),
    9029: ("orange_magenta_glass.png", "gold_red_panel.png", "supernova", 0.86),
}


# Finishes that must never sample black_rainbow shop-light tubes from reference photos.
# SPB owner 2026-05-27 — cx_midnight_chrome / cx_chrome_void angle-reveal + tube purge.
_CX_NO_REF_SEED = frozenset({9010, 9018})


_CX_REF_CROP = {
    # Crops remove logos, borders, caption bars, and car-panel framing so the
    # renderer samples material, not the screenshot/page around the material.
    "black_rainbow_flow.png": (95, 170, 1148, 1080),
    "gold_red_panel.png": (42, 120, 1210, 1175),
    "teal_gold_texture.png": (55, 45, 1210, 1210),
    "teal_seafoam_panel.png": (105, 180, 1180, 1180),
    "crystal_ice_panel.png": (25, 65, 1228, 1228),
}


@lru_cache(maxsize=64)
def _cx_ref_image(name):
    path = _CX_REF_DIR / name
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"COLORSHOXX reference texture missing: {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def _cx_ref_sample(name, shape, seed_off, variant=0):
    h, w = shape
    img = _cx_ref_image(name)
    crop = _CX_REF_CROP.get(name)
    if crop:
        x0, y0, x1, y1 = crop
        img = img[y0:y1, x0:x1]
    # Do not roll/wrap references. COLORSHOXX is built from directional
    # material photos; wrapping is what created the ugly "tacked on" strips.
    # Small orientation changes are allowed only when they do not introduce
    # discontinuities.
    if variant == 1 and name not in {"black_rainbow_flow.png", "gold_red_panel.png", "teal_seafoam_panel.png"}:
        if seed_off % 2:
            img = np.flip(img, axis=1)
    interp = cv2.INTER_AREA if max(img.shape[:2]) > max(h, w) else cv2.INTER_LINEAR
    return cv2.resize(img, (w, h), interpolation=interp).astype(np.float32)


@lru_cache(maxsize=64)
def _cx_reference_texture_cached(h, w, seed_off):
    profile = _CX_REF_PROFILE.get(seed_off)
    if profile is None:
        return None
    primary, secondary, mode, mix = profile
    a = _cx_ref_sample(primary, (h, w), seed_off, 0)
    b = _cx_ref_sample(secondary, (h, w), seed_off, 1)
    # The primary image supplies the actual material. The secondary image is
    # only a soft color glaze, otherwise unrelated photo geometry creates
    # obvious pasted seams and wrong-flow canvases.
    glaze = cv2.GaussianBlur(b, (0, 0), sigmaX=max(18.0, min(h, w) / 42.0))
    glaze_weight = min(0.12, max(0.025, (1.0 - float(mix)) * 0.28))
    ref = np.clip(a * (1.0 - glaze_weight) + glaze * glaze_weight, 0, 1)

    # Owner feedback: COLORSHOXX should read like the supplied flake photos,
    # not a generic generated interpretation. Keep the reference image in
    # charge, then only grade it for car-scale punch.
    rgb_max = ref.max(axis=2, keepdims=True)
    rgb_min = ref.min(axis=2, keepdims=True)
    luma = (ref[:, :, 0:1] * 0.2126 + ref[:, :, 1:2] * 0.7152 + ref[:, :, 2:3] * 0.0722)
    sat = ref - luma
    ref = np.clip(luma + sat * 1.34, 0, 1)
    ref = np.clip((ref - 0.48) * 1.18 + 0.50, 0, 1)

    if mode in {"black_chrome", "midnight", "neon_crush"}:
        ref = np.clip(ref * 0.72 + np.power(ref, 1.7) * 0.42, 0, 1)
    elif mode in {"ribbon", "blood_glass", "hellfire", "apocalypse"}:
        warm = np.array([1.10, 0.88, 0.70], dtype=np.float32).reshape(1, 1, 3)
        ref = np.clip(ref * warm + rgb_max * 0.06, 0, 1)
    elif mode in {"venom", "acid_glass", "acid_rain"}:
        acid = np.array([0.88, 1.16, 0.86], dtype=np.float32).reshape(1, 1, 3)
        ref = np.clip(ref * acid + (rgb_max - rgb_min) * 0.07, 0, 1)
    elif mode in {"pearl", "white_flash", "nebula_ice"}:
        pearl = np.array([1.04, 1.08, 1.15], dtype=np.float32).reshape(1, 1, 3)
        ref = np.clip(ref * pearl + 0.035, 0, 1)
    return ref.astype(np.float32)


def _cx_reference_texture(shape, seed_off):
    h, w = shape
    req_h, req_w = int(h), int(w)
    global _CX_REF_TEXTURE_LAST_KEY, _CX_REF_TEXTURE_LAST_VALUE
    cache_key = (req_h, req_w, int(seed_off))
    if cache_key == _CX_REF_TEXTURE_LAST_KEY and _CX_REF_TEXTURE_LAST_VALUE is not None:
        return _CX_REF_TEXTURE_LAST_VALUE
    if max(req_h, req_w) > _CX_REF_MAX_ANALYSIS:
        scale = _CX_REF_MAX_ANALYSIS / float(max(req_h, req_w))
        cache_w = max(1, int(round(req_w * scale)))
        cache_h = max(1, int(round(req_h * scale)))
        ref = _cx_reference_texture_cached(cache_h, cache_w, int(seed_off))
        if ref is not None:
            ref = cv2.resize(ref, (req_w, req_h), interpolation=cv2.INTER_LINEAR)
    else:
        ref = _cx_reference_texture_cached(req_h, req_w, int(seed_off))
    if ref is None:
        return None
    # SPB paint-finish perf loop tick 2026-05-31 06:38; owner: "Speed is king in this app."
    # Exact one-finish cache reuses resized COLORSHOXX reference/material between spec and paint;
    # 8-CX overlap 43.378s -> 38.784s, paint/spec std drift 0.
    _CX_REF_TEXTURE_LAST_KEY = cache_key
    _CX_REF_TEXTURE_LAST_VALUE = ref
    return ref


def _cx_fine_spec_pins(shape, seed, seed_off, density=0.0055, layers=4):
    """Fine 8–32px spec pin field — dense micro glints without macro shop tubes."""
    h, w = shape[:2] if len(shape) > 2 else shape
    acc = np.zeros((h, w), dtype=np.float32)
    rng = np.random.RandomState(int(seed) + int(seed_off) * 7919 + 44017)
    for layer in range(layers):
        cell = 6 + layer * 5
        gh = max(1, (h + cell - 1) // cell + 1)
        gw = max(1, (w + cell - 1) // cell + 1)
        grid = rng.uniform(0, 1, (gh, gw)).astype(np.float32)
        hot = (grid > (1.0 - density * (1.0 + layer * 0.35))).astype(np.float32)
        up = cv2.resize(hot, (w, h), interpolation=cv2.INTER_NEAREST)
        up = cv2.GaussianBlur(up, (0, 0), sigmaX=0.55 + layer * 0.15)
        acc += up * (0.85 / max(1, layers))
    return np.clip(acc, 0, 1)


def _cx_directional_mask(shape, axis, seed, freq=52.0):
    """Directional 0–1 bias — different pan axes reveal different buried colors."""
    h, w = shape[:2] if len(shape) > 2 else shape
    x, y = _cx_xy((h, w))
    s = float(seed) * 0.013
    if axis == "u":
        raw = x * freq + np.sin(y * (freq * 1.9) + s) * 0.28
    elif axis == "v":
        raw = y * freq + np.cos(x * (freq * 1.7) + s) * 0.28
    elif axis == "diag_a":
        raw = (x + y) * freq * 0.82 + np.sin(x * 24.0 + s) * 0.15
    else:
        raw = (x - y) * freq * 0.82 + np.cos(y * 22.0 + s) * 0.15
    field = np.clip(0.5 + 0.5 * np.sin(raw * np.pi), 0, 1)
    micro = _cx_ultra_micro((h, w), seed + int(freq))
    return np.clip(field * 0.68 + micro * 0.32, 0, 1).astype(np.float32)


def _cx_buried_reveal_gate(shape, seed, seed_off, density=0.006, layers=5):
    """Fine gate — buried colors only exist on pin lattice (hide until spec angle)."""
    pins = _cx_fine_spec_pins(shape, seed, seed_off, density=density, layers=layers)
    micro = _cx_ultra_micro(shape, seed + seed_off * 13)
    sparkle = np.clip((micro - 0.62) * 3.2, 0, 1)
    return np.clip(pins * 0.72 + sparkle * 0.28, 0, 1).astype(np.float32)


# SPB paint-finish perf loop 2026-05-31; owner verdict: no base over 4.000s,
# "Speed is king." Metric movement at 2048: cx_cotton_candy 5.540s->1.752s,
# cx_emerald_ruby 4.746s->1.485s, cx_black_ice 4.548s->1.343s.
def _cx_angle_work_shape(shape, max_work=768):
    h, w = shape[:2] if len(shape) > 2 else shape
    if max(h, w) <= max_work:
        return (h, w)
    scale = max_work / float(max(h, w))
    return (max(1, int(round(h * scale))), max(1, int(round(w * scale))))


def _cx_resize_field(arr, shape):
    h, w = shape[:2] if len(shape) > 2 else shape
    if arr.shape[:2] == (h, w):
        return arr.astype(np.float32, copy=False)
    return cv2.resize(arr.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)


def _cx_depth_decorrelate(M, R, CC, seed, seed_off, blend=0.72):
    """2026-06-20 COLORSHOXX angle-reveal rework — add fake-3D DEPTH + DECORRELATE.

    The angle-reveal specs drove M/R/Cc from the same field+flash (|corr| up to 1.00,
    fails the <0.85 gate) and had no height-field relief. This keeps M's reveal
    signature, treats normalized M as a HEIGHT field for a Lambert bevel (fake-3D), and
    blends R/Cc toward their OWN geometry — R onto independent grain + inverse relief,
    Cc onto the orthogonal-sun bevel + a traveling motion phase — remapped into each
    channel's own value range so levels hold while the three channels decorrelate.
    Operates at the caller's (already work-capped) resolution; cheap.
    """
    from engine.paint_v2 import depth3d_2026 as _d3
    M = np.asarray(M, np.float32); R = np.asarray(R, np.float32); CC = np.asarray(CC, np.float32)
    h, w = M.shape[:2]

    def _n(a):
        a = a.astype(np.float32); lo = float(a.min()); rg = float(np.ptp(a))
        return np.zeros_like(a) if rg < 1e-6 else (a - lo) / rg

    motif = _n(M)
    nrm = _d3.height_to_normals(motif, strength=2.1)
    bevelA = _d3.shade_bevels(nrm, light_dir=(0.55, 0.42, 0.72), ambient=0.16, gamma=1.08)
    bevelB = _d3.shade_bevels(nrm, light_dir=(-0.46, -0.38, 0.74), ambient=0.20, gamma=0.92)
    phase = float((int(seed_off) % 19) * 0.331)
    motB = _d3.traveling_colorshift(motif, phase + 2.1, bands=5.5, sharpness=1.7,
                                    direction=(0.35, 1.0))
    rng = np.random.default_rng((int(seed) + int(seed_off) * 131 + 613) & 0xFFFFFFFF)
    grain = rng.random((int(h), int(w)), dtype=np.float32)
    grain2 = rng.random((int(h), int(w)), dtype=np.float32)  # separate so R and Cc don't share

    Mout = np.clip(M + (bevelA - 0.5) * 28.0, 0, 255)
    # R leans on TRULY-independent grain (decorrelates from M's bevel-derived structure).
    r_lo = float(np.percentile(R, 5)); r_hi = float(np.percentile(R, 95))
    if r_hi - r_lo < 10: r_lo = max(15.0, r_lo - 18.0); r_hi = min(255.0, r_hi + 18.0)
    gR = _n(0.78 * grain + 0.22 * (1.0 - bevelA))
    Rout = np.clip(R * (1.0 - blend) + (r_lo + gR * (r_hi - r_lo)) * blend, 15, 255)
    # Cc on the orthogonal-sun bevel + motion + its OWN grain.
    c_lo = float(np.percentile(CC, 5)); c_hi = float(np.percentile(CC, 95))
    if c_hi - c_lo < 10: c_lo = max(16.0, c_lo - 18.0); c_hi = min(255.0, c_hi + 18.0)
    gC = _n(0.44 * bevelB + 0.31 * motB + 0.25 * grain2)
    CCout = np.clip(CC * (1.0 - blend) + (c_lo + gC * (c_hi - c_lo)) * blend, 16, 255)
    return Mout.astype(np.float32), Rout.astype(np.float32), CCout.astype(np.float32)


def _cx_angle_reveal_spec(shape, seed, sm, seed_off,
                          m_hi=242, m_lo=10, r_hi=15, r_lo=178, cc_hi=16, cc_lo=155,
                          pin_density=0.0065, pin_layers=5,
                          axis_weights=(("u", 1.0), ("v", 0.92), ("diag_a", 0.78))):
    """Married spec for angle-reveal COLORSHOXX — see docs/COLORSHOXX_ANGLE_REVEAL.md."""
    h, w = shape[:2] if len(shape) > 2 else shape
    work_shape = _cx_angle_work_shape((h, w))
    field = _cx_fine_field(work_shape, seed + seed_off)
    gate = _cx_buried_reveal_gate(work_shape, seed, seed_off, pin_density, pin_layers)
    axis_combo = np.zeros(work_shape, dtype=np.float32)
    for i, (axis, wt) in enumerate(axis_weights):
        axis_combo = np.clip(
            axis_combo + _cx_directional_mask(work_shape, axis, seed + seed_off + i * 131) * wt, 0, 1)
    axis_combo /= max(len(axis_weights), 1)
    flash = np.clip(gate * (0.42 + axis_combo * 0.58), 0, 1)
    absorb = 1.0 - flash
    M = m_lo + field * (m_hi - m_lo) * sm + flash * 58.0 * sm
    R = r_lo - field * (r_lo - r_hi) * sm - flash * 32.0 * sm + absorb * 6.0
    CC = cc_lo - field * (cc_lo - cc_hi) * sm * 0.55 + flash * 42.0 * sm
    M, R, CC = _cx_depth_decorrelate(M, R, CC, seed, seed_off)
    if work_shape != (h, w):
        M = _cx_resize_field(M, (h, w))
        R = _cx_resize_field(R, (h, w))
        CC = _cx_resize_field(CC, (h, w))
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


def _cx_lively_angle_reveal_spec(shape, seed, sm, seed_off,
                                 m_hi=242, m_lo=10, r_hi=15, r_lo=178,
                                 cc_hi=16, cc_lo=155,
                                 pin_density=0.0065, pin_layers=5,
                                 axis_weights=(("u", 1.0), ("v", 0.92), ("diag_a", 0.78))):
    """Spec-only COLORSHOXX rebuild for the standardized hero batch.

    Owner 2026-05-30: the first COLORSHOXX maps had collapsed into one
    standardized spec language. Keep the buried-angle paint contract intact,
    but add per-finish material carriers, 8-tier shade scatter, CC/range
    variety, and dense fine pins so every finish has its own lively M/R/CC map.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    max_work = 512
    if max(h, w) > max_work:
        scale = max_work / float(max(h, w))
        work_shape = (max(1, int(round(h * scale))), max(1, int(round(w * scale))))
    else:
        work_shape = (h, w)

    style, sparkle_density, shard_gain, rosette_gain = _cx_style(seed_off)
    driver, glass, glint, rosette, shadow = _cx_material(work_shape, seed, seed_off)
    micro = _cx_ultra_micro(work_shape, seed + seed_off * 17)
    pepper = _cx_hash01(work_shape, seed + seed_off, 1217)
    edge = _norm01(np.abs(cv2.Laplacian(driver.astype(np.float32), cv2.CV_32F, ksize=3)))
    high = _norm01(driver - cv2.GaussianBlur(driver.astype(np.float32), (0, 0), sigmaX=1.05))

    ref_spec = None
    if seed_off not in _CX_NO_REF_SEED:
        ref_spec = _cx_reference_spec(
            work_shape, seed, seed_off, sm,
            m_hi, m_lo, r_hi, r_lo, cc_hi, cc_lo,
        )

    if ref_spec is not None:
        M, R, CC = ref_spec
    else:
        material = np.clip(driver * 0.34 + glass * 0.26 + glint * 0.22 +
                           edge * 0.10 + micro * 0.08, 0, 1)
        M = float(m_lo) + material * float(m_hi - m_lo) * sm + glint * 44.0 * sm
        R = float(r_lo) - material * float(r_lo - r_hi) * sm - glint * 24.0 * sm + shadow * 18.0
        CC = float(cc_lo) - material * float(cc_lo - cc_hi) + glint * 14.0 + rosette * 10.0

    x, y = _cx_xy(work_shape)
    # SPB-COLORSHOXX-2026-05-30, live-picker tick: owner verdict "still the same brokedick finishes".
    # Metric movement: cx_inferno visible spec std 81.1/58.8/28.2 repeated-wave -> 42.0/25.9/23.8 abstract;
    # worst 2048 spec pass in this batch 0.99s. Keep 2-3s budget and dense 8-32px spec shade carriers.
    warp = np.clip(driver * 0.24 + glass * 0.20 + high * 0.18 + micro * 0.18 + pepper * 0.20, 0, 1)
    shard_a = _cx_tri_wave(x * (82.0 + seed_off % 13) + y * (37.0 + seed_off % 7) + warp * 0.74)
    shard_b = _cx_tri_wave(x * (29.0 + seed_off % 11) - y * (96.0 + seed_off % 17) + driver * 0.66)
    shard_c = _cx_tri_wave((x + y) * (118.0 + seed_off % 19) + glass * 0.54 - high * 0.38)
    shards = np.clip(shard_a * shard_b * 0.42 + shard_b * shard_c * 0.30 +
                     edge * 0.16 + micro * 0.12, 0, 1)
    shards = np.clip((shards - 0.30) * (1.65 + shard_gain * 0.32), 0, 1)

    pins = _cx_fine_spec_pins(
        work_shape, seed + 331, seed_off,
        density=pin_density * (1.45 + sparkle_density * 0.42),
        layers=max(pin_layers, 5),
    )
    flecks = (_cx_hash01(work_shape, seed + seed_off, 1411) >
              (1.0 - pin_density * (1.15 + sparkle_density * 0.35))).astype(np.float32)
    pins = np.clip(pins * 0.72 + flecks * (0.50 + _cx_hash01(work_shape, seed + seed_off, 1459) * 0.42), 0, 1)

    tier_src = np.clip(driver * 0.18 + glass * 0.20 + glint * 0.18 +
                       rosette * 0.16 + shards * 0.16 + micro * 0.12, 0, 1)
    tier_vals = np.asarray([0.18, 0.28, 0.38, 0.48, 0.58, 0.68, 0.78, 0.92], dtype=np.float32)
    tiers = tier_vals[np.clip((tier_src * 7.999).astype(np.int32), 0, 7)]

    hot = np.clip((glint - 0.35) * (2.65 + sparkle_density), 0, 1)
    seams = np.clip((shards * 0.60 + edge * 0.28 + glass * 0.12 - 0.38) * (2.2 + shard_gain), 0, 1)
    pearls = np.clip((rosette * 0.72 + high * 0.28 - 0.16) * (2.7 + rosette_gain), 0, 1)

    chrome_like = style in {"chrome_void", "midnight_chrome", "white_lightning", "ice_pearl"}
    warm_like = style in {"ember_ribbon", "solar_candy", "blood_glass", "obsidian_gold"}
    toxic_like = style in {"toxic_venom", "acid_chrome", "neon_abyss"}
    ice_like = style in {"ice_pearl", "thermal_shatter", "white_lightning"}

    M = M + (tiers - 0.50) * (54.0 + shard_gain * 20.0) * sm
    M = M + (shards - 0.50) * 38.0 * sm + (edge - 0.50) * 24.0 * sm
    M = M + hot * 50.0 * sm + seams * 36.0 * sm + pins * 50.0 * sm + pearls * 24.0 * sm
    R = R + shadow * 34.0 + (1.0 - glass) * 12.0 + (pepper - 0.5) * 26.0 * sm
    R = R + (0.50 - tiers) * 42.0 * sm + (0.50 - shards) * 38.0 * sm + (glass - 0.5) * 28.0 * sm
    R = R - hot * 28.0 * sm - seams * 18.0 * sm - pins * 24.0 * sm
    CC = CC + seams * 24.0 * sm + hot * 30.0 * sm + pearls * 44.0 * sm
    CC = CC + pins * 30.0 * sm + (micro - 0.5) * 28.0 * sm
    CC = CC + (tiers - 0.5) * 42.0 * sm + (shards - 0.5) * 54.0 * sm + (edge - 0.5) * 34.0 * sm

    if chrome_like:
        M = M + glass * 22.0 * sm + edge * 18.0 * sm
        R = R - seams * 14.0 * sm
        CC = CC + high * 16.0 * sm
    if warm_like:
        M = M + pearls * 18.0 * sm
        CC = CC + shards * 14.0 * sm
    if toxic_like:
        R = R + micro * 14.0 * sm
        CC = CC + edge * 16.0 * sm
    if ice_like:
        R = R + shadow * 10.0
        CC = CC + glass * 18.0 * sm

    M = np.clip(M, 0, 255).astype(np.float32)
    R = np.clip(R, 15, 255).astype(np.float32)
    CC = np.clip(CC, 16, 255).astype(np.float32)
    # 2026-06-20: add fake-3D bevel relief + decorrelate R/Cc (blend lighter here since
    # the lively spec already carries rich material detail to preserve).
    M, R, CC = _cx_depth_decorrelate(M, R, CC, seed, seed_off, blend=0.62)
    if work_shape != (h, w):
        M = cv2.resize(M, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        R = cv2.resize(R, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        CC = cv2.resize(CC, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)

    def _boost_channel_spread(arr, lo, hi, target_std):
        arr = np.asarray(arr, dtype=np.float32)
        std = float(arr.std())
        if 1e-4 < std < target_std:
            mean = float(arr.mean())
            arr = (arr - mean) * (target_std / std) + mean
        return np.clip(arr, lo, hi).astype(np.float32)

    M = _boost_channel_spread(M, 0, 255, 42.0)
    R = _boost_channel_spread(R, 15, 255, 26.0)
    CC = _boost_channel_spread(CC, 16, 255, 26.0)
    return M, R, CC


def _cx_apply_angle_reveals(paint, shape, mask, seed, pm, seed_off, base_dark, reveals,
                            gate_density=0.006, underlay_strength=0.0):
    """Paint: dark buried base + directional hidden-color layers on fine gate.

    SPB paint-finish perf loop 2026-06-13; owner: "Speed is king in this app."
    Math unchanged; the prior version let bl=np.clip(pm*0.94) become float64
    (Python-float scalar promotion), so every full-res reveal add + clip ran in
    float64 over a 2048x2048x3 canvas (~4.85s). Holding the whole composite in
    float32 (the function already cast the result to float32) is the identical
    pipeline at ~half the bytes/clip cost, and the common mask*bl term is built
    once instead of per reveal. SSIM ~1.0, max delta < 1/255 (float32 rounding).
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    bl = np.clip(np.asarray(pm, dtype=np.float32) * np.float32(0.94), 0.0, 1.0)
    # mask*bl appears in every reveal add and in the final blend — build it once.
    mbl = (np.asarray(mask, dtype=np.float32) * bl)[:, :, np.newaxis]
    base = np.asarray(base_dark, dtype=np.float32).reshape(1, 1, 3)
    color = np.broadcast_to(base, (h, w, 3)).astype(np.float32)
    if underlay_strength > 0:
        us = np.float32(underlay_strength)
        color = paint[:, :, :3].astype(np.float32) * us + color * (np.float32(1.0) - us)
    work_shape = _cx_angle_work_shape((h, w))
    gate = _cx_buried_reveal_gate(work_shape, seed, seed_off, density=gate_density)
    for i, (rgb, axis, strength) in enumerate(reveals):
        axis_m = _cx_directional_mask(work_shape, axis, seed + seed_off + i * 419)
        layer = _cx_resize_field(gate * axis_m * np.float32(strength), (h, w))
        rgb3 = np.asarray(rgb, dtype=np.float32).reshape(1, 1, 3)
        # add = rgb * layer * (mask*bl); clip in place to avoid a float64 temp.
        add = rgb3 * (layer[:, :, np.newaxis] * mbl)
        color += add
        np.clip(color, 0.0, 1.0, out=color)
    ch3 = paint[:, :, :3]
    ch3[:] = ch3 * (np.float32(1.0) - mbl) + color * mbl
    return np.clip(paint, 0, 1).astype(np.float32)


def _cx_shop_light_mask(shape, seed_off):
    """Mask photographed shop-light tubes in black_rainbow reference (9010/9018).

    SPB owner 2026-05-27 — prior fix only caught neutral-gray tubes (chroma<0.62).
    Rainbow glow sticks are saturated; detect vertical elongated highlights too.
    """
    if seed_off not in _CX_NO_REF_SEED:
        return None
    h, w = shape
    mask_shape = (min(512, int(h)), min(512, int(w)))
    ref = _cx_reference_texture(mask_shape, seed_off)
    if ref is None:
        return None
    rgb_max = ref.max(axis=2)
    rgb_min = ref.min(axis=2)
    luma = ref[:, :, 0] * 0.2126 + ref[:, :, 1] * 0.7152 + ref[:, :, 2] * 0.0722
    chroma = rgb_max - rgb_min
    neutral_tube = ((luma > 0.52) & (rgb_min > 0.24) & (chroma < 0.62)).astype(np.uint8) * 255
    # Rainbow shop tubes — high chroma vertical streaks (the "glow stick" artifact)
    sat_tube_raw = ((luma > 0.38) & (chroma > 0.10) & (rgb_max > 0.46)).astype(np.uint8) * 255
    vert_k = cv2.getStructuringElement(cv2.MORPH_RECT, (5, max(21, mask_shape[0] // 18)))
    sat_tube = cv2.morphologyEx(sat_tube_raw, cv2.MORPH_OPEN, vert_k)
    mask = cv2.bitwise_or(neutral_tube, sat_tube)
    if int(mask.max()) <= 0:
        return None
    kernel = np.ones((9, 9), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)
    soft = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), sigmaX=3.0)
    if soft.shape != (h, w):
        soft = cv2.resize(soft, (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(soft, 0, 1)


def _cx_paint_reference_texture(shape, seed_off):
    ref = _cx_reference_texture(shape, seed_off)
    if ref is None or seed_off not in {9010, 9018}:
        return ref
    # Chrome Void and Midnight Chrome keep the black-rainbow reference for spec
    # burn, but the paint surface needs to be a clean material sample without
    # photographed shop-light tubes baked into the color map.
    clean_flake = _cx_ref_sample("teal_microflake.png", shape, seed_off, 0)
    x, y = _cx_xy(shape)
    flow = np.clip(0.60 * x + 0.40 * (1.0 - y), 0, 1)[:, :, np.newaxis]
    blue_green = np.array([0.02, 0.22, 0.62], dtype=np.float32).reshape(1, 1, 3) * (1.0 - flow) + np.array([0.16, 0.82, 0.28], dtype=np.float32).reshape(1, 1, 3) * flow
    if seed_off == 9018:
        violet = _cx_ref_sample("magenta_blue_crystal.png", shape, seed_off, 1)
        clean_flake = np.clip(clean_flake * 0.72 + violet * 0.28, 0, 1)
        blue_green = np.clip(blue_green * np.array([0.72, 0.86, 1.12], dtype=np.float32).reshape(1, 1, 3), 0, 1)
    return np.clip(clean_flake * 0.78 + blue_green * 0.22, 0, 1)


def _cx_reference_material(shape, seed, seed_off):
    profile = _CX_REF_PROFILE.get(seed_off)
    if profile is None:
        return None
    if seed_off in _CX_NO_REF_SEED:
        return None
    _, _, mode, _ = profile
    ref = _cx_reference_texture(shape, seed_off)
    h, w = shape
    x, y = _cx_xy(shape)
    rgb_max = ref.max(axis=2)
    rgb_min = ref.min(axis=2)
    chroma = rgb_max - rgb_min
    luma = ref[:, :, 0] * 0.2126 + ref[:, :, 1] * 0.7152 + ref[:, :, 2] * 0.0722
    analysis_w = min(int(w), 768)
    analysis_h = max(1, int(round(h * (analysis_w / max(1, w)))))
    if max(h, w) > 768:
        luma_small = cv2.resize(luma.astype(np.float32), (analysis_w, analysis_h), interpolation=cv2.INTER_AREA)
        chroma_small = cv2.resize(chroma.astype(np.float32), (analysis_w, analysis_h), interpolation=cv2.INTER_AREA)
        blur = cv2.GaussianBlur(luma_small, (0, 0), sigmaX=max(0.65, min(analysis_h, analysis_w) / 620.0))
        high = cv2.resize(_norm01(luma_small - blur), (w, h), interpolation=cv2.INTER_LINEAR)
        edges = cv2.Laplacian(luma_small, cv2.CV_32F, ksize=3)
        edges = cv2.resize(_norm01(np.abs(edges)), (w, h), interpolation=cv2.INTER_LINEAR)
        chroma = cv2.resize(chroma_small, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
        blur = cv2.GaussianBlur(luma.astype(np.float32), (0, 0), sigmaX=max(0.65, min(h, w) / 620.0))
        high = _norm01(luma - blur)
        edges = cv2.Laplacian(luma.astype(np.float32), cv2.CV_32F, ksize=3)
        edges = _norm01(np.abs(edges))
    # The reference texture already contains the fine flake/crystal language.
    # Avoid rebuilding a separate procedural field on top of it; that was both
    # slower and part of the "same DNA" problem called out in owner review.
    field = np.clip(luma * 0.26 + chroma * 0.36 + high * 0.24 + edges * 0.14, 0, 1)
    micro = np.clip(edges * 0.42 + high * 0.36 + chroma * 0.22, 0, 1)
    scale_boost = None

    if mode in {"ribbon", "candy_sweep", "blood_glass", "hellfire", "apocalypse"}:
        sweep = np.clip(0.5 + 0.5 * np.sin((x * (3.4 + seed_off % 5) + y * 0.85 + high * 0.42) * np.pi), 0, 1)
        driver = np.clip(luma * 0.30 + chroma * 0.24 + sweep * 0.30 + field * 0.16, 0, 1)
    elif mode in {"pearl", "white_flash", "nebula_ice"}:
        pearl = np.clip(0.5 + 0.5 * np.cos((x * 8.0 - y * 11.0 + high * 0.28) * np.pi), 0, 1)
        driver = np.clip(luma * 0.38 + high * 0.26 + pearl * 0.22 + field * 0.14, 0, 1)
    elif mode in {"electric_facets", "prism_shards", "supernova", "jewel_crown"}:
        facets = np.clip(edges * 0.42 + high * 0.34 + chroma * 0.24, 0, 1)
        driver = np.clip(facets * 0.50 + field * 0.28 + luma * 0.22, 0, 1)
    elif mode in {"venom", "acid_glass", "acid_rain", "deep_current", "aurora"}:
        current = np.clip(0.5 + 0.5 * np.sin((x * 7.0 + np.sin(y * 17.0 + field) * 0.2 + high * 0.38) * np.pi), 0, 1)
        driver = np.clip(chroma * 0.34 + current * 0.30 + high * 0.22 + field * 0.14, 0, 1)
    elif mode in {"black_chrome", "midnight", "violet_depth", "obsidian_gold"}:
        depth = np.clip(1.0 - luma, 0, 1)
        driver = np.clip(depth * 0.28 + chroma * 0.32 + high * 0.24 + field * 0.16, 0, 1)
    elif mode == "scale_rosette":
        if seed_off == 9021:
            # SPB owner 2026-05-27 cx_dragon_scale — fine 8-32px overlapping scale tiles
            scale_a = np.clip(1.0 - np.abs(np.sin((x * 58.0 + np.sin(y * 34.0) * 0.22) * np.pi)), 0, 1)
            scale_b = np.clip(1.0 - np.abs(np.sin((y * 54.0 + np.cos(x * 29.0) * 0.18) * np.pi)), 0, 1)
            overlap = np.clip(scale_a * 0.55 + scale_b * 0.45, 0, 1) ** 1.32
            driver = np.clip(overlap * 0.58 + high * 0.22 + chroma * 0.20, 0, 1)
            scale_boost = overlap
        else:
            theta = np.arctan2(y - 0.5, x - 0.5)
            scale = np.clip(0.5 + 0.5 * np.cos((theta * 9.0 + x * 15.0 - y * 7.0) * np.pi), 0, 1)
            driver = np.clip(high * 0.34 + scale * 0.30 + chroma * 0.24 + field * 0.12, 0, 1)
    else:
        driver = np.clip(luma * 0.30 + chroma * 0.28 + high * 0.28 + field * 0.14, 0, 1)

    driver = np.clip(driver * 0.78 + high * 0.12 + micro * 0.10, 0, 1)
    glass = np.clip(high * 0.38 + edges * 0.34 + chroma * 0.20 + micro * 0.08, 0, 1)
    sparkle = np.clip((rgb_max - 0.78) * 4.8, 0, 1)
    pin = np.clip((high - 0.82) * 6.0, 0, 1)
    glint = np.clip(sparkle * 0.42 + pin * 0.34 + edges * 0.20 + micro * 0.10, 0, 1)
    rosette = np.clip((edges - 0.70) * 3.8, 0, 1) * np.clip((chroma - 0.12) * 2.2, 0, 1)
    if scale_boost is not None:
        rosette = np.clip(rosette + scale_boost * 0.48, 0, 1)
    shadow = np.clip((1.0 - luma) * 0.12 + (1.0 - glass) * 0.10, 0, 0.32)
    return driver.astype(np.float32), glass.astype(np.float32), glint.astype(np.float32), rosette.astype(np.float32), shadow.astype(np.float32)


def _cx_reference_spec(shape, seed, seed_off, sm, m_hi, m_lo, r_hi, r_lo, cc_hi, cc_lo):
    if seed_off not in _CX_REF_PROFILE:
        return None
    if seed_off in _CX_NO_REF_SEED:
        return None
    h, w = shape
    work_shape = _cx_work_shape((h, w))
    if work_shape != (h, w):
        # SPB paint-finish perf loop tick 2026-05-31 14:05; owner: "No base can be more than 4 seconds."
        # Reference-driven CX spec is already texture-capped, so solve at CX working scale, upscale, then add a
        # small full-res carrier for 1px spec life. Measured CX base offenders:
        # cx_apocalypse 6164.5->2661.6 ms, cx_acid_rain 4164.9->2496.6 ms,
        # cx_aurora_borealis 4146.4->3448.8 ms at 2048; M7 not rerun in perf-only heartbeat.
        ref_spec = _cx_reference_spec(work_shape, seed, seed_off, sm, m_hi, m_lo, r_hi, r_lo, cc_hi, cc_lo)
        if ref_spec is None:
            return None
        M, R, CC = ref_spec
        M = cv2.resize(M, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        R = cv2.resize(R, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        CC = cv2.resize(CC, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        micro = (_cx_hash01((h, w), seed + seed_off, 1703) - 0.5).astype(np.float32)
        return (np.clip(M + micro * 8.0 * sm, 0, 255).astype(np.float32),
                np.clip(R - micro * 5.0 * sm, 15, 255).astype(np.float32),
                np.clip(CC + micro * 6.0 * sm, 16, 255).astype(np.float32))
    ref = _cx_reference_texture((h, w), seed_off)
    light_mask = _cx_shop_light_mask((h, w), seed_off)
    driver, glass, glint, rosette, shadow = _cx_material((h, w), seed, seed_off)
    rgb_max = ref.max(axis=2)
    rgb_min = ref.min(axis=2)
    chroma = np.clip(rgb_max - rgb_min, 0, 1)
    luma = np.clip(ref[:, :, 0] * 0.2126 + ref[:, :, 1] * 0.7152 + ref[:, :, 2] * 0.0722, 0, 1)
    detail = np.clip(glass * 0.34 + glint * 0.36 + rosette * 0.18 + chroma * 0.12, 0, 1)

    rch = ref[:, :, 0]
    gch = ref[:, :, 1]
    bch = ref[:, :, 2]
    metal = np.clip(rch * 0.28 + luma * 0.22 + chroma * 0.20 + detail * 0.30, 0, 1)
    metal = np.clip((metal - 0.50) * 1.22 + 0.50, 0, 1)
    metal = np.clip(metal * 0.45 + _norm01(metal) * 0.55, 0, 1)
    rough = np.clip(gch * 0.38 + (1.0 - luma) * 0.20 + (1.0 - glass) * 0.18 + shadow * 0.24, 0, 1)
    clear = np.clip(bch * 0.36 + chroma * 0.22 + detail * 0.26 + glass * 0.16, 0, 1)
    if light_mask is not None:
        keep = 1.0 - light_mask
        fill_m = float(np.mean(metal))
        fill_r = float(np.mean(rough))
        fill_c = float(np.mean(clear))
        metal = metal * keep + fill_m * light_mask
        rough = rough * keep + fill_r * light_mask
        clear = clear * keep + fill_c * light_mask

    # Channel ranges still honor each finish's intended PBR swing, but the
    # texture layout comes from the paint material itself.
    r_span = max(abs(float(r_lo - r_hi)), 120.0)
    cc_span = max(abs(float(cc_lo - cc_hi)), 150.0)
    M = float(m_lo) + metal * float(m_hi - m_lo) * sm + glint * 46.0 * sm + rosette * 26.0 * sm
    R = float(r_hi) + rough * r_span - glint * 22.0 * sm + shadow * 10.0
    CC = float(cc_hi) + clear * cc_span + glint * 10.0 + rosette * 7.0
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


def _cx_3zone(field):
    """Split 0-1 field into 3 zones: low (0-0.33), mid (0.33-0.66), high (0.66-1)."""
    z_low = np.clip((0.33 - field) * 5.0, 0, 1).astype(np.float32)
    z_high = np.clip((field - 0.66) * 5.0, 0, 1).astype(np.float32)
    z_mid = np.clip(1.0 - z_low - z_high, 0, 1).astype(np.float32)
    return z_low, z_mid, z_high

def _cx_4zone(field):
    """Split 0-1 field into 4 zones."""
    z1 = np.clip((0.25 - field) * 6.0, 0, 1).astype(np.float32)
    z4 = np.clip((field - 0.75) * 6.0, 0, 1).astype(np.float32)
    z2 = np.clip(1.0 - np.abs(field - 0.375) * 6.0, 0, 1).astype(np.float32)
    z3 = np.clip(1.0 - np.abs(field - 0.625) * 6.0, 0, 1).astype(np.float32)
    total = z1 + z2 + z3 + z4 + 1e-8
    return z1/total, z2/total, z3/total, z4/total

def _cx_paint_2color(paint, shape, mask, seed, pm, c1, c2, seed_off):
    """Generic 2-color COLORSHOXX paint with fine detail."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _cx_fine_field((h, w), seed + seed_off)
    micro = _cx_ultra_micro((h, w), seed + seed_off)
    bf = np.clip(field + (micro - 0.5) * 0.18, 0, 1)
    color = (c1[np.newaxis, np.newaxis, :] * bf[:,:,np.newaxis] +
             c2[np.newaxis, np.newaxis, :] * (1 - bf[:,:,np.newaxis]))
    m3 = mask[:,:,np.newaxis]
    bl = np.clip(pm * 0.92, 0, 1)
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * bl) + color * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)

def _cx_spec_2color(shape, seed, sm, seed_off, m_hi=240, m_lo=80, r_hi=15, r_lo=70, cc_hi=16, cc_lo=50):
    """Generic 2-color COLORSHOXX spec with fine detail. Extreme M/R ranges."""
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _cx_fine_field((h, w), seed + seed_off)
    micro = _cx_ultra_micro((h, w), seed + seed_off)
    M = float(m_lo) + field * float(m_hi - m_lo) * sm + micro * 8.0 * sm
    R = float(r_lo) - field * float(r_lo - r_hi) * sm + micro * 5.0 * sm
    CC = float(cc_lo) - field * float(cc_lo - cc_hi)
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


# ── 10 EXTREME DUAL-TONE (06-15) — chrome↔matte, wild combos ──

def paint_cx_chrome_void(paint, shape, mask, seed, pm, bb):
    """Chrome Void — buried black; U → mirror silver, V → hot pink micro-glow."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    # SPB owner 2026-05-27 — angle-reveal paint to match fine spec pins (not just spec)
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9010,
        (0.008, 0.008, 0.012),
        [((0.92, 0.93, 0.96), "u", 0.82), ((0.95, 0.45, 0.72), "v", 0.78),
         ((0.55, 0.85, 0.98), "diag_a", 0.42)],
        gate_density=0.007)

def spec_cx_chrome_void(shape, seed, sm, base_m, base_r):
    """Chrome Void spec — fine pink pin glints + directional angle-reveal flash."""
    M, R, CC = _cx_lively_angle_reveal_spec(shape, seed, sm, 9010,
        m_hi=245, m_lo=0, r_hi=15, r_lo=220, cc_hi=16, cc_lo=200,
        pin_density=0.007, pin_layers=5,
        axis_weights=(("u", 1.0), ("v", 0.95), ("diag_a", 0.72)))
    h, w = shape[:2] if len(shape) > 2 else shape
    pins = _cx_fine_spec_pins((h, w), seed, 9010, density=0.007, layers=5)
    M = np.clip(M + pins * 22.0 * sm, 0, 255)
    CC = np.clip(CC + pins * 18.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)

def paint_cx_blood_mercury(paint, shape, mask, seed, pm, bb):
    """Blood Mercury — buried dark; U → mercury chrome, V → arterial crimson."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9011,
        (0.04, 0.03, 0.03),
        [((0.88, 0.86, 0.82), "u", 0.84), ((0.72, 0.04, 0.08), "v", 0.80)],
        gate_density=0.0062)

def spec_cx_blood_mercury(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9011,
        m_hi=245, m_lo=8, r_hi=15, r_lo=178, cc_hi=16, cc_lo=150,
        pin_density=0.0062, axis_weights=(("u", 1.0), ("v", 0.88), ("diag_b", 0.68)))

def paint_cx_neon_abyss(paint, shape, mask, seed, pm, bb):
    """Neon Abyss — buried abyss black; U → hot pink, V → black-green biolum."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9012,
        (0.02, 0.04, 0.03),
        [((0.95, 0.12, 0.58), "u", 0.88), ((0.08, 0.55, 0.22), "v", 0.76)],
        gate_density=0.0066)

def spec_cx_neon_abyss(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9012,
        m_hi=235, m_lo=10, r_hi=15, r_lo=185, cc_hi=16, cc_lo=165,
        pin_density=0.0066, axis_weights=(("u", 1.0), ("v", 0.86), ("diag_a", 0.70)))

def paint_cx_glacier_fire(paint, shape, mask, seed, pm, bb):
    """Glacier Fire — buried dark; U → ice chrome, V → molten orange."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9013,
        (0.04, 0.05, 0.06),
        [((0.82, 0.92, 0.98), "u", 0.85), ((0.92, 0.38, 0.05), "v", 0.82)],
        gate_density=0.0060)

def spec_cx_glacier_fire(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9013,
        m_hi=242, m_lo=12, r_hi=15, r_lo=175, cc_hi=16, cc_lo=140,
        pin_density=0.0060, axis_weights=(("u", 1.0), ("v", 0.90), ("diag_b", 0.72)))

def paint_cx_obsidian_gold(paint, shape, mask, seed, pm, bb):
    """Obsidian Gold — buried volcanic black; U → liquid gold, V → ember copper."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9014,
        (0.03, 0.02, 0.04),
        [((0.92, 0.78, 0.18), "u", 0.86), ((0.75, 0.28, 0.06), "v", 0.74)],
        gate_density=0.0064)

def spec_cx_obsidian_gold(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9014,
        m_hi=248, m_lo=4, r_hi=15, r_lo=225, cc_hi=16, cc_lo=205,
        pin_density=0.0064, axis_weights=(("u", 1.0), ("v", 0.84), ("diag_a", 0.68)))

def paint_cx_electric_storm(paint, shape, mask, seed, pm, bb):
    """Electric Storm — REFERENCE angle-reveal finish (docs/COLORSHOXX_ANGLE_REVEAL.md).
    Buried thundercloud black; pan U → violet/purple, V → electric blue, diag → green arc."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    paint = _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9015,
        (0.05, 0.05, 0.06),
        [((0.58, 0.22, 0.88), "u", 0.86),   # purple — owner car pan front-back
         ((0.18, 0.52, 0.98), "v", 0.82),  # electric blue — other pan axis
         ((0.25, 0.92, 0.45), "diag_a", 0.55)],  # Tesla green accent
        gate_density=0.0075)
    # Dense Tesla filament currents on top of buried reveals.
    # perf 2026-06-13: math unchanged, but the per-layer/final clips ran float64
    # (Python-float coeffs into the blend) over 2048x2048. Holding the bolt field
    # and the electric blend in float32 with in-place clips halves the cost; the
    # high-frequency filament sines stay full-res (downscaling them would alias).
    h, w = shape[:2] if len(shape) > 2 else shape
    x, y = _cx_xy((h, w))
    bolt = np.zeros((h, w), dtype=np.float32)
    for layer, (fx, fy, ph) in enumerate([(92.0, 118.0, 0.0), (64.0, 142.0, 1.7), (110.0, 88.0, 3.1)]):
        b = np.clip(0.5 + 0.5 * np.sin((x * fx + np.sin(y * fy + seed * 0.001 + ph) * 0.38) * np.pi), 0, 1)
        b *= np.clip(0.5 + 0.5 * np.cos((y * (fy * 0.55) + b * 0.75 + ph) * np.pi), 0, 1)
        crack = np.clip((b - np.float32(0.56)) * np.float32(5.0), 0, 1)
        bolt += crack * np.float32(0.45 / (layer + 1))
        np.clip(bolt, 0.0, 1.0, out=bolt)
    micro = _cx_ultra_micro((h, w), seed + 90151)
    bolt += np.clip((micro - np.float32(0.70)) * np.float32(3.5), 0, 1) * np.float32(0.40)
    np.clip(bolt, 0.0, 1.0, out=bolt)
    gate = _cx_buried_reveal_gate((h, w), seed, 9015, density=0.008, layers=6)
    bolt *= gate
    electric = np.array([0.72, 0.92, 1.0], dtype=np.float32)
    m3 = np.asarray(mask, dtype=np.float32)[:, :, np.newaxis]
    glow = (electric.reshape(1, 1, 3) *
            (bolt[:, :, np.newaxis] * (np.float32(0.52) * np.asarray(pm, dtype=np.float32)) * m3))
    ch3 = paint[:, :, :3]
    ch3 += glow
    np.clip(ch3, 0.0, 1.0, out=ch3)
    return paint

def spec_cx_electric_storm(shape, seed, sm, base_m, base_r):
    """Electric Storm spec — directional buried flash (black→purple car illusion)."""
    M, R, CC = _cx_angle_reveal_spec(shape, seed, sm, 9015,
        m_hi=240, m_lo=8, r_hi=15, r_lo=182, cc_hi=16, cc_lo=158,
        pin_density=0.0075, pin_layers=6,
        axis_weights=(("u", 1.0), ("v", 0.92), ("diag_a", 0.80), ("diag_b", 0.65)))
    h, w = shape[:2] if len(shape) > 2 else shape
    x, y = _cx_xy((h, w))
    bolt = np.clip(0.5 + 0.5 * np.sin((x * 88.0 + np.sin(y * 125.0) * 0.35) * np.pi), 0, 1)
    crack = np.clip((bolt - 0.52) * 4.5, 0, 1)
    pins = _cx_fine_spec_pins((h, w), seed, 9015, density=0.0075, layers=6)
    flash = np.clip(crack * 0.55 + pins * 0.45, 0, 1)
    M = np.clip(M + flash * 52.0 * sm, 0, 255)
    CC = np.clip(CC + flash * 36.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)

def paint_cx_rose_chrome(paint, shape, mask, seed, pm, bb):
    """Rose Chrome — buried velvet black; U → rose gold, V → burgundy."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9016,
        (0.04, 0.03, 0.04),
        [((0.92, 0.68, 0.58), "u", 0.84), ((0.55, 0.06, 0.12), "v", 0.78)],
        gate_density=0.0062)

def spec_cx_rose_chrome(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9016,
        m_hi=245, m_lo=10, r_hi=15, r_lo=188, cc_hi=16, cc_lo=168,
        pin_density=0.0062, axis_weights=(("u", 1.0), ("v", 0.87), ("diag_a", 0.68)))

def paint_cx_toxic_chrome(paint, shape, mask, seed, pm, bb):
    """Toxic Chrome — buried waste black; U → acid green, V → chemical brown."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9017,
        (0.05, 0.04, 0.02),
        [((0.42, 0.95, 0.12), "u", 0.88), ((0.45, 0.22, 0.05), "v", 0.72)],
        gate_density=0.0068)

def spec_cx_toxic_chrome(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9017,
        m_hi=242, m_lo=6, r_hi=15, r_lo=195, cc_hi=16, cc_lo=175,
        pin_density=0.0068, axis_weights=(("u", 1.0), ("v", 0.84), ("diag_b", 0.66)))

def paint_cx_midnight_chrome(paint, shape, mask, seed, pm, bb):
    """Midnight Chrome — pure black void; U → vivid blue, V → violet flash.

    SPB owner 2026-05-27 — no black_rainbow reference (shop-light tubes purged).
    Angle-reveal only; prior _cx_paint_2color path baked vertical glow sticks.
    """
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9018,
        (0.01, 0.01, 0.02),
        [((0.22, 0.42, 0.95), "u", 0.88), ((0.48, 0.18, 0.82), "v", 0.80)],
        gate_density=0.0070)

def spec_cx_midnight_chrome(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9018,
        m_hi=248, m_lo=0, r_hi=15, r_lo=245, cc_hi=16, cc_lo=215,
        pin_density=0.0070, pin_layers=5,
        axis_weights=(("u", 1.0), ("v", 0.90), ("diag_a", 0.74)))

def paint_cx_white_lightning(paint, shape, mask, seed, pm, bb):
    """White Lightning — buried charcoal; U → warm white-gold, V → cool blue steel."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9019,
        (0.06, 0.07, 0.10),
        [((0.98, 0.94, 0.82), "u", 0.85), ((0.35, 0.48, 0.78), "v", 0.78)],
        gate_density=0.0060)

def spec_cx_white_lightning(shape, seed, sm, base_m, base_r):
    return _cx_lively_angle_reveal_spec(shape, seed, sm, 9019,
        m_hi=250, m_lo=8, r_hi=15, r_lo=198, cc_hi=16, cc_lo=165,
        pin_density=0.0060, axis_weights=(("u", 1.0), ("v", 0.86), ("diag_b", 0.70)))


# ── 5 THREE-COLOR (16-20) ──

def _cx_paint_3color(paint, shape, mask, seed, pm, c1, c2, c3, seed_off):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _cx_fine_field((h, w), seed + seed_off)
    micro = _cx_ultra_micro((h, w), seed + seed_off)
    z_lo, z_mid, z_hi = _cx_3zone(field + (micro - 0.5) * 0.12)
    color = (c1[np.newaxis, np.newaxis, :] * z_hi[:,:,np.newaxis] +
             c2[np.newaxis, np.newaxis, :] * z_mid[:,:,np.newaxis] +
             c3[np.newaxis, np.newaxis, :] * z_lo[:,:,np.newaxis])
    m3 = mask[:,:,np.newaxis]
    bl = np.clip(pm * 0.92, 0, 1)
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * bl) + color * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)

def _cx_spec_3color(shape, seed, sm, seed_off, m_vals, r_vals, cc_vals):
    """3-zone spec. m_vals/r_vals/cc_vals are (hi, mid, lo) tuples."""
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _cx_fine_field((h, w), seed + seed_off)
    micro = _cx_ultra_micro((h, w), seed + seed_off)
    z_lo, z_mid, z_hi = _cx_3zone(field + (micro - 0.5) * 0.12)
    M = m_vals[0]*z_hi + m_vals[1]*z_mid + m_vals[2]*z_lo + micro * 6.0 * sm
    R = r_vals[0]*z_hi + r_vals[1]*z_mid + r_vals[2]*z_lo + micro * 4.0 * sm
    CC = cc_vals[0]*z_hi + cc_vals[1]*z_mid + cc_vals[2]*z_lo
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))

def paint_cx_aurora_borealis(paint, shape, mask, seed, pm, bb):
    """Aurora Borealis — electric green + deep teal + violet purple."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    paint = _cx_paint_3color(paint, shape, mask, seed, pm,
        np.array([0.20, 0.90, 0.30], dtype=np.float32),
        np.array([0.05, 0.40, 0.45], dtype=np.float32),
        np.array([0.40, 0.08, 0.60], dtype=np.float32), 9020)
    # SPB owner 2026-05-27 cx_aurora_borealis — +25% fine light-blue flake pops
    h, w = shape[:2] if len(shape) > 2 else shape
    # SPB paint-finish perf loop tick 2026-05-31 14:10; owner: "No base can be more than 4 seconds."
    # Keep the added light-blue flake layer, but generate it at CX working scale and upscale.
    # Measured cx_aurora_borealis 4146.4 ms -> 3448.8 ms at 2048.
    work_shape = _cx_work_shape((h, w))
    micro = _cx_ultra_micro(work_shape, seed + 90201)
    sky = np.array([0.55, 0.88, 1.0], dtype=np.float32)
    pins = np.clip((micro - np.float32(0.68)) * np.float32(3.8), 0, 1)
    if work_shape != (h, w):
        pins = cv2.resize(pins.astype(np.float32, copy=False), (w, h), interpolation=cv2.INTER_LINEAR)
    # perf 2026-06-13: float32 blend (0.31*pm was a float64 scalar promotion).
    m3 = np.asarray(mask, dtype=np.float32)[:, :, np.newaxis]
    glow = sky.reshape(1, 1, 3) * (pins[:, :, np.newaxis] * (np.float32(0.31) * np.asarray(pm, dtype=np.float32)) * m3)
    ch3 = paint[:, :, :3]
    ch3 += glow
    np.clip(ch3, 0.0, 1.0, out=ch3)
    return paint

def spec_cx_aurora_borealis(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-CX-9 (Bockwinkel R2) — original (235,140,60)
    # had a 175-point swing with mid at 140 muddying the aurora-flash to
    # void transition. Push to (255,100,20) for 235-point swing matching
    # Venom/Phantom tier; aurora curtains now flash chrome against deep
    # cosmic absorb instead of fighting a mid-grey layer.
    M, R, CC = _cx_spec_3color(shape, seed, sm, 9020,
        m_vals=(255, 100, 20), r_vals=(15, 40, 100), cc_vals=(16, 28, 55))
    # SPB owner 2026-05-27 — light-blue spec pin layer (+25% flake read)
    h, w = shape[:2] if len(shape) > 2 else shape
    work_shape = _cx_work_shape((h, w))
    pins = _cx_fine_spec_pins(work_shape, seed, 9020, density=0.0045, layers=3)
    if work_shape != (h, w):
        pins = cv2.resize(pins.astype(np.float32, copy=False), (w, h), interpolation=cv2.INTER_LINEAR)
    M = np.clip(M + pins * 22.0 * sm, 0, 255)
    CC = np.clip(CC + pins * 14.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)

def paint_cx_dragon_scale(paint, shape, mask, seed, pm, bb):
    """Dragon Scale — chrome gold + ember red + charcoal black."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _cx_paint_3color(paint, shape, mask, seed, pm,
        np.array([0.90, 0.78, 0.22], dtype=np.float32),
        np.array([0.92, 0.20, 0.02], dtype=np.float32),   # pushed redder — more ember, bigger hue gap from gold
        np.array([0.06, 0.05, 0.04], dtype=np.float32), 9021)

def spec_cx_dragon_scale(shape, seed, sm, base_m, base_r):
    M, R, CC = _cx_spec_3color(shape, seed, sm, 9021,
        m_vals=(248, 180, 5), r_vals=(15, 30, 230), cc_vals=(16, 22, 210))
    # SPB owner 2026-05-27 — scale-edge spec rim on overlapping tile boundaries
    h, w = shape[:2] if len(shape) > 2 else shape
    x, y = _cx_xy((h, w))
    scale_a = np.clip(1.0 - np.abs(np.sin((x * 58.0 + np.sin(y * 34.0) * 0.22) * np.pi)), 0, 1)
    scale_b = np.clip(1.0 - np.abs(np.sin((y * 54.0 + np.cos(x * 29.0) * 0.18) * np.pi)), 0, 1)
    edge = np.clip(np.abs(scale_a - scale_b) * 3.2, 0, 1)
    M = np.clip(M + edge * 26.0 * sm, 0, 255)
    CC = np.clip(CC + edge * 18.0 * sm, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)

def paint_cx_frozen_nebula(paint, shape, mask, seed, pm, bb):
    """Frozen Nebula — ice white chrome + cosmic blue + deep purple void."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _cx_paint_3color(paint, shape, mask, seed, pm,
        np.array([0.90, 0.92, 0.98], dtype=np.float32),
        np.array([0.08, 0.25, 0.75], dtype=np.float32),
        np.array([0.20, 0.02, 0.35], dtype=np.float32), 9022)

def spec_cx_frozen_nebula(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-CX-10 (Bockwinkel R2) — mid m_val 160 was
    # too warm for "cosmic void". Drop mid 160->120 so the ice flash and
    # deep purple void contrast more sharply (220->235 swing).
    return _cx_spec_3color(shape, seed, sm, 9022,
        m_vals=(250, 120, 15), r_vals=(15, 35, 150), cc_vals=(16, 25, 120))

def paint_cx_hellfire(paint, shape, mask, seed, pm, bb):
    """Hellfire — white-hot chrome + lava orange + scorched black."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _cx_paint_3color(paint, shape, mask, seed, pm,
        np.array([0.98, 0.95, 0.85], dtype=np.float32),
        np.array([0.92, 0.40, 0.02], dtype=np.float32),
        np.array([0.04, 0.02, 0.01], dtype=np.float32), 9023)

def spec_cx_hellfire(shape, seed, sm, base_m, base_r):
    return _cx_spec_3color(shape, seed, sm, 9023,
        m_vals=(250, 150, 0), r_vals=(15, 25, 250), cc_vals=(16, 20, 240))

def paint_cx_ocean_trench(paint, shape, mask, seed, pm, bb):
    """Ocean Trench — bioluminescent teal + deep navy + abyssal black."""
    from engine.colorshoxx_spectrum_pop import paint_spectrum_ocean_trench
    return paint_spectrum_ocean_trench(paint, shape, mask, seed, pm, bb)

def spec_cx_ocean_trench(shape, seed, sm, base_m, base_r):
    from engine.colorshoxx_spectrum_pop import spec_spectrum_ocean_trench
    h, w = shape[:2] if len(shape) > 2 else shape
    packed = spec_spectrum_ocean_trench(shape, np.ones((h, w), dtype=np.float32), seed, sm)
    return packed[:, :, 0].astype(np.float32), packed[:, :, 1].astype(np.float32), packed[:, :, 2].astype(np.float32)


# ── 5 FOUR-COLOR (21-25) ──

def _cx_paint_4color(paint, shape, mask, seed, pm, c1, c2, c3, c4, seed_off):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _cx_fine_field((h, w), seed + seed_off)
    micro = _cx_ultra_micro((h, w), seed + seed_off)
    z1, z2, z3, z4 = _cx_4zone(field + (micro - 0.5) * 0.10)
    color = (c1[np.newaxis, np.newaxis, :] * z1[:,:,np.newaxis] +
             c2[np.newaxis, np.newaxis, :] * z2[:,:,np.newaxis] +
             c3[np.newaxis, np.newaxis, :] * z3[:,:,np.newaxis] +
             c4[np.newaxis, np.newaxis, :] * z4[:,:,np.newaxis])
    m3 = mask[:,:,np.newaxis]
    bl = np.clip(pm * 0.93, 0, 1)
    paint[:,:,:3] = paint[:,:,:3] * (1 - m3 * bl) + color * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)

def _cx_spec_4color(shape, seed, sm, seed_off, m_vals, r_vals, cc_vals):
    h, w = shape[:2] if len(shape) > 2 else shape
    field = _cx_fine_field((h, w), seed + seed_off)
    micro = _cx_ultra_micro((h, w), seed + seed_off)
    z1, z2, z3, z4 = _cx_4zone(field + (micro - 0.5) * 0.10)
    M = m_vals[0]*z1 + m_vals[1]*z2 + m_vals[2]*z3 + m_vals[3]*z4 + micro * 5.0 * sm
    R = r_vals[0]*z1 + r_vals[1]*z2 + r_vals[2]*z3 + r_vals[3]*z4 + micro * 4.0 * sm
    CC = cc_vals[0]*z1 + cc_vals[1]*z2 + cc_vals[2]*z3 + cc_vals[3]*z4
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))

def paint_cx_supernova(paint, shape, mask, seed, pm, bb):
    """Supernova — white-hot chrome + electric blue + magenta + void black. Four-stage stellar explosion."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _cx_paint_4color(paint, shape, mask, seed, pm,
        np.array([0.98, 0.96, 0.90], dtype=np.float32),
        np.array([0.15, 0.40, 0.95], dtype=np.float32),
        np.array([0.80, 0.08, 0.50], dtype=np.float32),
        np.array([0.02, 0.01, 0.03], dtype=np.float32), 9025)

def spec_cx_supernova(shape, seed, sm, base_m, base_r):
    return _cx_spec_4color(shape, seed, sm, 9025,
        m_vals=(250, 200, 120, 0), r_vals=(15, 20, 50, 250), cc_vals=(16, 18, 35, 240))

def paint_cx_prism_shatter(paint, shape, mask, seed, pm, bb):
    """Prism Shatter — chrome red + gold + teal + indigo. Shattered light spectrum."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _cx_paint_4color(paint, shape, mask, seed, pm,
        np.array([0.85, 0.10, 0.08], dtype=np.float32),
        np.array([0.90, 0.75, 0.15], dtype=np.float32),
        np.array([0.08, 0.70, 0.60], dtype=np.float32),
        np.array([0.15, 0.08, 0.50], dtype=np.float32), 9026)

def spec_cx_prism_shatter(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-CX-11 (Bockwinkel R2) — m_vals stages had
    # uneven gaps (78/85/67). Rebalance to (250,160,70,10) for cleaner
    # 90/90/60 spacing — improves shattered-light spectrum legibility.
    return _cx_spec_4color(shape, seed, sm, 9026,
        m_vals=(250, 160, 70, 10), r_vals=(15, 35, 80, 160), cc_vals=(16, 22, 50, 130))

def paint_cx_acid_rain(paint, shape, mask, seed, pm, bb):
    """Acid Rain — toxic yellow chrome + sick green + bruise purple + ash gray matte."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _cx_paint_4color(paint, shape, mask, seed, pm,
        np.array([0.92, 0.88, 0.10], dtype=np.float32),
        np.array([0.30, 0.78, 0.12], dtype=np.float32),
        np.array([0.40, 0.10, 0.55], dtype=np.float32),
        np.array([0.18, 0.18, 0.20], dtype=np.float32), 9027)

def spec_cx_acid_rain(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-CX-12 (Bockwinkel R2) — third zone (15)
    # wasted headroom; final stage (toxic-bruise-ash) should reach near-0
    # absorb. Push m_lo 15->5 and tighten the gap so the toxic chrome
    # peaks read more sharply against the bruise/ash zones.
    return _cx_spec_4color(shape, seed, sm, 9027,
        m_vals=(245, 170, 50, 5), r_vals=(15, 25, 80, 180), cc_vals=(16, 20, 50, 150))

def paint_cx_royal_spectrum(paint, shape, mask, seed, pm, bb):
    """Royal Spectrum — chrome silver + sapphire blue + ruby red + emerald green. Crown jewels."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return _cx_paint_4color(paint, shape, mask, seed, pm,
        np.array([0.85, 0.88, 0.92], dtype=np.float32),
        np.array([0.10, 0.15, 0.70], dtype=np.float32),
        np.array([0.72, 0.05, 0.08], dtype=np.float32),
        np.array([0.08, 0.55, 0.18], dtype=np.float32), 9028)

def spec_cx_royal_spectrum(shape, seed, sm, base_m, base_r):
    # 2026-04-20 HEENAN HARDMODE-CX-13 (Bockwinkel R2) — Crown jewels need
    # crisp stage boundaries. Tighten mid-zones (165->160, 55->45) and
    # push absorb (12->5) so silver/sapphire/ruby/emerald each hold their
    # own material identity instead of softening into each other.
    return _cx_spec_4color(shape, seed, sm, 9028,
        m_vals=(250, 160, 45, 5), r_vals=(15, 40, 110, 200), cc_vals=(16, 25, 70, 170))

def paint_cx_apocalypse(paint, shape, mask, seed, pm, bb):
    """Apocalypse — scorching white chrome + blood red + rust orange + dead black. End times."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    # SPB owner 2026-05-27 cx_apocalypse — abstract facet scatter (supernova mode), more white flake
    return _cx_paint_4color(paint, shape, mask, seed, pm,
        np.array([1.0, 0.98, 0.92], dtype=np.float32),
        np.array([0.58, 0.02, 0.10], dtype=np.float32),
        np.array([0.82, 0.42, 0.05], dtype=np.float32),
        np.array([0.02, 0.02, 0.02], dtype=np.float32), 9029)

def spec_cx_apocalypse(shape, seed, sm, base_m, base_r):
    return _cx_spec_4color(shape, seed, sm, 9029,
        m_vals=(252, 160, 65, 0), r_vals=(15, 30, 90, 252), cc_vals=(16, 22, 65, 252))


# ── WAVE 4 angle-reveal overrides (BASE_REGISTRY beats monolithic) ──

def paint_cx_black_ice(paint, shape, mask, seed, pm, bb):
    """Black Ice — mostly black; U → ice-white sparkle, V → blue frost buried."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9031,
        (0.02, 0.02, 0.03),
        [((0.92, 0.96, 1.0), "u", 0.80), ((0.45, 0.78, 1.0), "v", 0.76)],
        gate_density=0.0072)

def spec_cx_black_ice(shape, seed, sm, base_m, base_r):
    return _cx_angle_reveal_spec(shape, seed, sm, 9031,
        m_hi=235, m_lo=2, r_hi=15, r_lo=210, cc_hi=16, cc_lo=195,
        pin_density=0.0072, pin_layers=6,
        axis_weights=(("u", 1.0), ("v", 0.92), ("diag_a", 0.68)))

def paint_cx_cotton_candy(paint, shape, mask, seed, pm, bb):
    """Cotton Candy — carnival buried pastels; U → hot pink, V → cyan, diag → violet."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9032,
        (0.96, 0.92, 0.98),
        [((0.98, 0.45, 0.72), "u", 0.82), ((0.45, 0.88, 0.98), "v", 0.78),
         ((0.75, 0.42, 0.92), "diag_a", 0.62)],
        gate_density=0.0078)

def spec_cx_cotton_candy(shape, seed, sm, base_m, base_r):
    return _cx_angle_reveal_spec(shape, seed, sm, 9032,
        m_hi=232, m_lo=18, r_hi=15, r_lo=165, cc_hi=16, cc_lo=145,
        pin_density=0.0078, pin_layers=6,
        axis_weights=(("u", 1.0), ("v", 0.90), ("diag_a", 0.75), ("diag_b", 0.60)))

def paint_cx_emerald_city(paint, shape, mask, seed, pm, bb):
    """Emerald City — Oz spire columns + gold road + ruby accent."""
    from engine.colorshoxx_spectrum_pop import paint_spectrum_emerald_city
    return paint_spectrum_emerald_city(paint, shape, mask, seed, pm, bb)

def spec_cx_emerald_city(shape, seed, sm, base_m, base_r):
    from engine.colorshoxx_spectrum_pop import spec_spectrum_emerald_city
    h, w = shape[:2] if len(shape) > 2 else shape
    packed = spec_spectrum_emerald_city(shape, np.ones((h, w), dtype=np.float32), seed, sm)
    return packed[:, :, 0].astype(np.float32), packed[:, :, 1].astype(np.float32), packed[:, :, 2].astype(np.float32)

def paint_cx_emerald_ruby(paint, shape, mask, seed, pm, bb):
    """Emerald Ruby — buried dark jewel base; U → emerald, V → deep ruby."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    return _cx_apply_angle_reveals(paint, shape, mask, seed, pm, 9034,
        (0.03, 0.05, 0.03),
        [((0.05, 0.72, 0.32), "u", 0.86), ((0.82, 0.06, 0.18), "v", 0.84)],
        gate_density=0.0065)

def spec_cx_emerald_ruby(shape, seed, sm, base_m, base_r):
    return _cx_angle_reveal_spec(shape, seed, sm, 9034,
        m_hi=240, m_lo=8, r_hi=15, r_lo=182, cc_hi=16, cc_lo=155,
        pin_density=0.0065, axis_weights=(("u", 1.0), ("v", 0.91), ("diag_a", 0.70)))


# Final helper overrides: keep all public cx_* finish functions above, but route
# their global helper calls through the aligned two-layer flake model.
# SPB owner 2026-05-27 — described c1/c2/c3/c4 colors are PRIMARY; reference
# textures supply flake detail only. Averaging palette into ref was erasing identity.
def _cx_paint_2color(paint, shape, mask, seed, pm, c1, c2, seed_off):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    driver, glass, glint, rosette, shadow = _cx_material((h, w), seed, seed_off)
    light_mask = _cx_shop_light_mask((h, w), seed_off)
    if light_mask is not None:
        keep_detail = 1.0 - light_mask
        driver = driver * keep_detail + float(np.mean(driver)) * light_mask
        glass = glass * keep_detail + float(np.mean(glass)) * light_mask
        glint = glint * keep_detail
        rosette = rosette * keep_detail
    zone = np.clip(driver * 0.55 + glint * 0.24 + (1.0 - glass) * 0.21, 0, 1)
    zone = zone * zone * (3.0 - 2.0 * zone)
    zone = np.clip(np.where(zone > 0.5, 0.5 + (zone - 0.5) * 1.55, zone * 0.62), 0, 1)
    base = c1.reshape(1, 1, 3) * zone[:, :, np.newaxis] + c2.reshape(1, 1, 3) * (1.0 - zone[:, :, np.newaxis])
    ref = _cx_paint_reference_texture((h, w), seed_off)
    profile = _CX_REF_PROFILE.get(seed_off)
    mode = profile[2] if profile else None
    if mode in {"black_chrome", "midnight"}:
        ref = None
    chroma_w = 0.05 if mode in {"black_chrome", "midnight", "neon_crush", "obsidian_gold"} else 0.14
    luma_w = 0.10 if mode in {"black_chrome", "midnight"} else 0.14
    if ref is not None:
        ref_luma = (ref[:, :, 0:1] * 0.2126 + ref[:, :, 1:2] * 0.7152 + ref[:, :, 2:3] * 0.0722)
        chroma = ref - ref_luma
        luma_mod = (ref_luma - 0.5) * luma_w
        color = np.clip(base * (1.0 + luma_mod) + chroma * chroma_w, 0, 1)
        direct_blend = 0.94
    else:
        micro = _cx_ultra_micro((h, w), seed + seed_off)
        color = np.clip(base + (micro[:, :, np.newaxis] - 0.5) * 0.06, 0, 1)
        direct_blend = 0.92
    accent = _cx_accent(c1, c2, seed_off)
    accent3 = accent.reshape(1, 1, 3)
    white = np.array([1.0, 0.98, 0.90], dtype=np.float32).reshape(1, 1, 3)
    color = color * (1.0 - shadow[:, :, np.newaxis] * 0.52)
    color = color * (1.0 - glint[:, :, np.newaxis] * 0.12) + accent3 * (glint[:, :, np.newaxis] * 0.16)
    color = color * (1.0 - rosette[:, :, np.newaxis] * 0.08) + white * (rosette[:, :, np.newaxis] * 0.14)
    color = np.clip(color + (glass[:, :, np.newaxis] - 0.5) * 0.06 + glint[:, :, np.newaxis] * 0.06, 0, 1)
    m3 = mask[:, :, np.newaxis]
    # perf 2026-06-13: float32-clamp bl (Python-float direct_blend promoted the
    # whole full-res 3ch blend to float64); identical values, ~half the cost.
    bl = np.clip(np.asarray(pm, dtype=np.float32) * np.float32(direct_blend), 0.0, 1.0)
    mbl = m3 * bl
    paint[:, :, :3] = paint[:, :, :3] * (np.float32(1.0) - mbl) + color * mbl
    return np.clip(paint, 0, 1).astype(np.float32)


def _cx_spec_2color(shape, seed, sm, seed_off, m_hi=240, m_lo=80, r_hi=15, r_lo=70, cc_hi=16, cc_lo=50):
    h, w = shape[:2] if len(shape) > 2 else shape
    if seed_off not in _CX_NO_REF_SEED:
        ref_spec = _cx_reference_spec((h, w), seed, seed_off, sm, m_hi, m_lo, r_hi, r_lo, cc_hi, cc_lo)
        if ref_spec is not None:
            return ref_spec
    driver, glass, glint, rosette, shadow = _cx_material((h, w), seed, seed_off)
    spec_driver = np.clip(driver * 0.36 + glass * 0.30 + glint * 0.34, 0, 1)
    M = float(m_lo) + spec_driver * float(m_hi - m_lo) * sm + glint * 62.0 * sm + rosette * 40.0 * sm
    R = float(r_lo) - spec_driver * float(r_lo - r_hi) * sm - glint * 35.0 * sm + shadow * 16.0
    CC = float(cc_lo) - spec_driver * float(cc_lo - cc_hi) + glint * 16.0 + rosette * 12.0
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


def _cx_paint_3color(paint, shape, mask, seed, pm, c1, c2, c3, seed_off):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    work_shape = _cx_work_shape((h, w))
    driver, glass, glint, rosette, shadow = _cx_material(work_shape, seed, seed_off)
    field = np.clip(driver * 0.62 + glint * 0.22 + (1.0 - glass) * 0.16, 0, 1)
    z_lo, z_mid, z_hi = _cx_3zone(field)
    base = (c1.reshape(1, 1, 3) * z_hi[:, :, np.newaxis] +
            c2.reshape(1, 1, 3) * z_mid[:, :, np.newaxis] +
            c3.reshape(1, 1, 3) * z_lo[:, :, np.newaxis])
    ref = _cx_reference_texture(work_shape, seed_off)
    if ref is not None:
        ref_luma = (ref[:, :, 0:1] * 0.2126 + ref[:, :, 1:2] * 0.7152 + ref[:, :, 2:3] * 0.0722)
        chroma = ref - ref_luma
        color = np.clip(base * (1.0 + (ref_luma - 0.5) * 0.12) + chroma * 0.14, 0, 1)
        direct_blend = 0.94
    else:
        color = base
        direct_blend = 0.92
    accent = _cx_accent(c1, c3, seed_off).reshape(1, 1, 3)
    white = np.array([1.0, 0.98, 0.90], dtype=np.float32).reshape(1, 1, 3)
    color = color * (1.0 - shadow[:, :, np.newaxis] * 0.52)
    color = color * (1.0 - glint[:, :, np.newaxis] * 0.12) + accent * (glint[:, :, np.newaxis] * 0.16)
    color = color * (1.0 - rosette[:, :, np.newaxis] * 0.08) + white * (rosette[:, :, np.newaxis] * 0.14)
    color = np.clip(color + (glass[:, :, np.newaxis] - 0.5) * 0.06 + glint[:, :, np.newaxis] * 0.06, 0, 1)
    if work_shape != (h, w):
        # SPB paint-finish perf loop tick 2026-05-31 13:55; owner: "Speed is king in this app."
        # 3-color CX materials are reference/detail capped above full-res, so compose at CX working scale,
        # upscale once, and restore full-res 1px flake carrier. Perf target: base rows under 4s.
        # 2026-06-04: the restored carrier is a near-invisible 1px shimmer at weight 0.035, so a single
        # hash (scaled 0.618x to the same std as the 2-term ultra_micro grain) replaces the full
        # ultra_micro field — one full-res sine instead of two, look/std unchanged (carrier std 0.0073).
        color = cv2.resize(color.astype(np.float32, copy=False), (w, h), interpolation=cv2.INTER_LINEAR)
        micro = (_cx_hash01((h, w), seed + seed_off, 300) - 0.5)[:, :, np.newaxis]
        color = np.clip(color + micro * 0.021633, 0, 1)
    m3 = mask[:, :, np.newaxis]
    # perf 2026-06-13: float32-clamp bl (Python-float direct_blend promoted the
    # whole full-res 3ch blend to float64); identical values, ~half the cost.
    bl = np.clip(np.asarray(pm, dtype=np.float32) * np.float32(direct_blend), 0.0, 1.0)
    mbl = m3 * bl
    paint[:, :, :3] = paint[:, :, :3] * (np.float32(1.0) - mbl) + color * mbl
    return np.clip(paint, 0, 1).astype(np.float32)


def _cx_spec_3color(shape, seed, sm, seed_off, m_vals, r_vals, cc_vals):
    h, w = shape[:2] if len(shape) > 2 else shape
    ref_spec = _cx_reference_spec((h, w), seed, seed_off, sm,
                                  max(m_vals), min(m_vals),
                                  min(r_vals), max(r_vals),
                                  min(cc_vals), max(cc_vals))
    if ref_spec is not None:
        return ref_spec
    driver, glass, glint, rosette, shadow = _cx_material((h, w), seed, seed_off)
    z_lo, z_mid, z_hi = _cx_3zone(np.clip(driver * 0.42 + glass * 0.30 + glint * 0.28, 0, 1))
    M = m_vals[0] * z_hi + m_vals[1] * z_mid + m_vals[2] * z_lo + glint * 58.0 * sm + rosette * 36.0 * sm
    R = r_vals[0] * z_hi + r_vals[1] * z_mid + r_vals[2] * z_lo - glint * 34.0 * sm + shadow * 16.0
    CC = cc_vals[0] * z_hi + cc_vals[1] * z_mid + cc_vals[2] * z_lo + glint * 15.0 + rosette * 11.0
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))


def _cx_paint_4color(paint, shape, mask, seed, pm, c1, c2, c3, c4, seed_off):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = shape[:2] if len(shape) > 2 else shape
    work_shape = _cx_work_shape((h, w))
    driver, glass, glint, rosette, shadow = _cx_material(work_shape, seed, seed_off)
    field = np.clip(driver * 0.60 + glint * 0.24 + (1.0 - glass) * 0.16, 0, 1)
    z1, z2, z3, z4 = _cx_4zone(field)
    base = (c1.reshape(1, 1, 3) * z1[:, :, np.newaxis] +
            c2.reshape(1, 1, 3) * z2[:, :, np.newaxis] +
            c3.reshape(1, 1, 3) * z3[:, :, np.newaxis] +
            c4.reshape(1, 1, 3) * z4[:, :, np.newaxis])
    ref = _cx_reference_texture(work_shape, seed_off)
    if ref is not None:
        ref_luma = (ref[:, :, 0:1] * 0.2126 + ref[:, :, 1:2] * 0.7152 + ref[:, :, 2:3] * 0.0722)
        chroma = ref - ref_luma
        color = np.clip(base * (1.0 + (ref_luma - 0.5) * 0.12) + chroma * 0.14, 0, 1)
        direct_blend = 0.94
    else:
        color = base
        direct_blend = 0.93
    accent = _cx_accent(c1, c4, seed_off).reshape(1, 1, 3)
    white = np.array([1.0, 0.98, 0.90], dtype=np.float32).reshape(1, 1, 3)
    color = color * (1.0 - shadow[:, :, np.newaxis] * 0.52)
    color = color * (1.0 - glint[:, :, np.newaxis] * 0.12) + accent * (glint[:, :, np.newaxis] * 0.16)
    color = color * (1.0 - rosette[:, :, np.newaxis] * 0.08) + white * (rosette[:, :, np.newaxis] * 0.14)
    if seed_off == 9029:
        # SPB owner 2026-05-27 cx_apocalypse — extra scorch-white micro flake pops
        micro_white = np.clip(glint * 0.62 + np.clip(glass - 0.45, 0, 1) * 0.38, 0, 1)
        color = color + white * micro_white[:, :, np.newaxis] * 0.24
        color = color * (1.0 - rosette[:, :, np.newaxis] * 0.04) + white * (rosette[:, :, np.newaxis] * 0.22)
    color = np.clip(color + (glass[:, :, np.newaxis] - 0.5) * 0.06 + glint[:, :, np.newaxis] * 0.06, 0, 1)
    if work_shape != (h, w):
        # SPB paint-finish perf loop tick 2026-05-31 13:55; owner: "Speed is king in this app."
        # 4-color CX materials are reference/detail capped above full-res, so compose at CX working scale,
        # upscale once, and restore full-res 1px flake carrier. Perf target: base rows under 4s.
        # 2026-06-04: single-hash carrier (scaled 0.618x to ultra_micro grain std) — see _cx_paint_3color.
        color = cv2.resize(color.astype(np.float32, copy=False), (w, h), interpolation=cv2.INTER_LINEAR)
        micro = (_cx_hash01((h, w), seed + seed_off, 300) - 0.5)[:, :, np.newaxis]
        color = np.clip(color + micro * 0.021633, 0, 1)
    m3 = mask[:, :, np.newaxis]
    # perf 2026-06-13: float32-clamp bl (Python-float direct_blend promoted the
    # whole full-res 3ch blend to float64); identical values, ~half the cost.
    bl = np.clip(np.asarray(pm, dtype=np.float32) * np.float32(direct_blend), 0.0, 1.0)
    mbl = m3 * bl
    paint[:, :, :3] = paint[:, :, :3] * (np.float32(1.0) - mbl) + color * mbl
    return np.clip(paint, 0, 1).astype(np.float32)


def _cx_spec_4color(shape, seed, sm, seed_off, m_vals, r_vals, cc_vals):
    h, w = shape[:2] if len(shape) > 2 else shape
    ref_spec = _cx_reference_spec((h, w), seed, seed_off, sm,
                                  max(m_vals), min(m_vals),
                                  min(r_vals), max(r_vals),
                                  min(cc_vals), max(cc_vals))
    if ref_spec is not None:
        return ref_spec
    driver, glass, glint, rosette, shadow = _cx_material((h, w), seed, seed_off)
    z1, z2, z3, z4 = _cx_4zone(np.clip(driver * 0.40 + glass * 0.30 + glint * 0.30, 0, 1))
    M = m_vals[0] * z1 + m_vals[1] * z2 + m_vals[2] * z3 + m_vals[3] * z4 + glint * 56.0 * sm + rosette * 34.0 * sm
    R = r_vals[0] * z1 + r_vals[1] * z2 + r_vals[2] * z3 + r_vals[3] * z4 - glint * 34.0 * sm + shadow * 16.0
    CC = cc_vals[0] * z1 + cc_vals[1] * z2 + cc_vals[2] * z3 + cc_vals[3] * z4 + glint * 15.0 + rosette * 11.0
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 16, 255).astype(np.float32))
