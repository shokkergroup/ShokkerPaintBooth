"""
engine/paint_v2/structural_color.py — ★ COLORSHOXX Finishes
Premium color-shifting finishes where paint+spec work as married pairs.

HOW IT WORKS:
1. A spatial "field" (multi_scale_noise) divides the surface into zones
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
from engine.core import multi_scale_noise


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
    micro = multi_scale_noise(shape, [2, 4, 8], [0.5, 0.3, 0.2], seed + 200)
    return np.clip(micro * 0.5 + 0.5, 0, 1).astype(np.float32)


# ============================================================
# COLORSHOXX 01: INFERNO FLIP — Crimson Red ↔ Midnight Blue
# ============================================================

def paint_colorshoxx_inferno(paint, shape, mask, seed, pm, bb):
    """Inferno Flip — crimson red zones + midnight blue zones.
    At specular angle the red BLAZES. At normal incidence the blue dominates.
    Fine-detail field (4/8/16px cells) + ultra-micro flake shimmer."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.82, 0.06, 0.04], dtype=np.float32),   # vivid crimson — pushed redder
        np.array([0.04, 0.06, 0.58], dtype=np.float32),    # deep midnight blue — pushed bluer
        9001)


def spec_colorshoxx_inferno(shape, seed, sm, base_m, base_r):
    """Inferno Flip spec — MARRIED to paint via identical _cx_fine_field seed.
    Red zones: M=238, R=15 (chrome flash at specular).
    Blue zones: M=75, R=80 (matte-dark at normal incidence).
    Extreme ΔM=163 for maximum zone contrast."""
    return _cx_spec_2color(shape, seed, sm, 9001,
        m_hi=238, m_lo=75, r_hi=15, r_lo=80, cc_hi=16, cc_lo=48)


# ============================================================
# COLORSHOXX 02: ARCTIC MIRAGE — Ice Silver ↔ Deep Teal
# ============================================================

def paint_colorshoxx_arctic(paint, shape, mask, seed, pm, bb):
    """Arctic Mirage — bright ice silver zones + deep teal zones.
    Fine-detail field (4/8/16px cells) + ultra-micro per-flake shimmer.
    Silver flashes brilliantly at specular. Teal holds steady at normal."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.78, 0.82, 0.88], dtype=np.float32),   # brighter ice silver
        np.array([0.02, 0.38, 0.42], dtype=np.float32),    # richer deep teal
        9002)


def spec_colorshoxx_arctic(shape, seed, sm, base_m, base_r):
    """Arctic Mirage spec — MARRIED via identical _cx_fine_field seed.
    Silver zones: M=242, R=15 (chrome mirror flash).
    Teal zones: M=65, R=85 (matte steady at normal incidence).
    ΔM=177 — ice-cold chrome to deep matte shift."""
    return _cx_spec_2color(shape, seed, sm, 9002,
        m_hi=242, m_lo=65, r_hi=15, r_lo=85, cc_hi=16, cc_lo=50)


# ============================================================
# COLORSHOXX 03: VENOM SHIFT — Toxic Green ↔ Black Purple
# ============================================================

def paint_colorshoxx_venom(paint, shape, mask, seed, pm, bb):
    """Venom Shift — toxic neon green zones + deep black-purple zones.
    Fine-detail field (4/8/16px cells) + ultra-micro flake shimmer.
    Green zones flash with metallic pop. Purple zones stay dark and menacing."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.18, 0.82, 0.08], dtype=np.float32),   # hotter neon green
        np.array([0.12, 0.02, 0.28], dtype=np.float32),    # deeper black-purple
        9003)


def spec_colorshoxx_venom(shape, seed, sm, base_m, base_r):
    """Venom Shift spec — MARRIED via identical _cx_fine_field seed.
    Green zones: M=235, R=15 (toxic chrome flash).
    Purple zones: M=15, R=140 (dead matte darkness).
    ΔM=220 — the widest swing in Wave 1. Green BLAZES, purple ABSORBS."""
    return _cx_spec_2color(shape, seed, sm, 9003,
        m_hi=235, m_lo=15, r_hi=15, r_lo=140, cc_hi=16, cc_lo=130)


# ============================================================
# COLORSHOXX 04: SOLAR FLARE — Gold ↔ Copper Red
# ============================================================

def paint_colorshoxx_solar(paint, shape, mask, seed, pm, bb):
    """Solar Flare — warm gold zones + deep copper-red zones.
    Fine-detail field (4/8/16px cells) + ultra-micro flake shimmer.
    Gold zones flash like liquid metal. Copper zones glow warmly."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.88, 0.72, 0.12], dtype=np.float32),   # richer 24k gold
        np.array([0.52, 0.08, 0.12], dtype=np.float32),    # deep burgundy-copper — pushed away from gold hue
        9004)


def spec_colorshoxx_solar(shape, seed, sm, base_m, base_r):
    """Solar Flare spec — MARRIED via identical _cx_fine_field seed.
    Gold zones: M=245, R=15 (liquid chrome gold flash).
    Burgundy zones: M=55, R=110 (deep matte glow).
    ΔM=190 — molten gold erupts over dark burgundy-copper."""
    return _cx_spec_2color(shape, seed, sm, 9004,
        m_hi=245, m_lo=55, r_hi=15, r_lo=110, cc_hi=16, cc_lo=70)


# ============================================================
# COLORSHOXX 05: PHANTOM VIOLET — Electric Violet ↔ Gunmetal
# ============================================================

def paint_colorshoxx_phantom(paint, shape, mask, seed, pm, bb):
    """Phantom Violet — electric violet zones + cold gunmetal zones.
    Fine-detail field (4/8/16px cells) + ultra-micro flake shimmer.
    Violet zones pop with vivid metallic flash. Gunmetal zones stay cold and steely."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.55, 0.08, 0.80], dtype=np.float32),   # hotter electric violet
        np.array([0.20, 0.22, 0.26], dtype=np.float32),    # colder gunmetal
        9005)


def spec_colorshoxx_phantom(shape, seed, sm, base_m, base_r):
    """Phantom Violet spec — MARRIED via identical _cx_fine_field seed.
    Violet zones: M=240, R=15 (electric chrome flash).
    Gunmetal zones: M=40, R=100 (cold dead matte steel).
    ΔM=200 — violet erupts from nowhere against dead gunmetal."""
    return _cx_spec_2color(shape, seed, sm, 9005,
        m_hi=240, m_lo=40, r_hi=15, r_lo=100, cc_hi=16, cc_lo=55)


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
    base_noise = multi_scale_noise((h, w), [4, 8, 16], [0.4, 0.35, 0.25], seed)
    warped = base_noise[wy, wx]
    # Add fine detail for micro-texture within zones
    fine = multi_scale_noise((h, w), [2, 4], [0.6, 0.4], seed + 50)
    # Combine: warped structure (70%) + fine detail (20%) + slight large-scale bias (10%)
    large = multi_scale_noise((h, w), [64, 128], [0.5, 0.5], seed + 80)
    field = np.clip(warped * 0.70 + fine * 0.20 + large * 0.10, -1, 1)
    # SHARPEN: push values toward 0 and 1 (not smooth middle)
    normalized = (field + 1.0) * 0.5
    sharpened = np.clip((normalized - 0.5) * 1.8 + 0.5, 0, 1)
    return sharpened.astype(np.float32)

def _cx_ultra_micro(shape, seed):
    """Ultra-fine per-flake — scale 1-2px for individual metallic particle shimmer."""
    m = multi_scale_noise(shape, [1, 2, 3], [0.5, 0.3, 0.2], seed + 300)
    return np.clip(m * 0.5 + 0.5, 0, 1).astype(np.float32)

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
    """Chrome Void — pure mirror chrome ↔ absolute matte black. Maximum contrast."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.85, 0.88, 0.92], dtype=np.float32),
        np.array([0.02, 0.02, 0.03], dtype=np.float32), 9010)

def spec_cx_chrome_void(shape, seed, sm, base_m, base_r):
    """Chrome zones M=245/R=15, void zones M=0/R=220. Chrome to dead matte."""
    return _cx_spec_2color(shape, seed, sm, 9010, m_hi=245, m_lo=0, r_hi=15, r_lo=220, cc_hi=16, cc_lo=200)

def paint_cx_blood_mercury(paint, shape, mask, seed, pm, bb):
    """Blood Mercury — warm liquid mercury chrome ↔ deep arterial crimson."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.88, 0.86, 0.82], dtype=np.float32),   # warm mercury — gold-tinted chrome, distinct from Chrome Void
        np.array([0.55, 0.02, 0.04], dtype=np.float32), 9011)

def spec_cx_blood_mercury(shape, seed, sm, base_m, base_r):
    return _cx_spec_2color(shape, seed, sm, 9011, m_hi=245, m_lo=12, r_hi=15, r_lo=165, cc_hi=16, cc_lo=140)

def paint_cx_neon_abyss(paint, shape, mask, seed, pm, bb):
    """Neon Abyss — electric hot pink ↔ abyssal black-green."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.95, 0.10, 0.55], dtype=np.float32),
        np.array([0.02, 0.10, 0.06], dtype=np.float32), 9012)

def spec_cx_neon_abyss(shape, seed, sm, base_m, base_r):
    return _cx_spec_2color(shape, seed, sm, 9012, m_hi=230, m_lo=15, r_hi=15, r_lo=180, cc_hi=16, cc_lo=170)

def paint_cx_glacier_fire(paint, shape, mask, seed, pm, bb):
    """Glacier Fire — icy white-blue chrome ↔ molten orange-red matte."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.80, 0.88, 0.95], dtype=np.float32),
        np.array([0.85, 0.25, 0.03], dtype=np.float32), 9013)

def spec_cx_glacier_fire(shape, seed, sm, base_m, base_r):
    return _cx_spec_2color(shape, seed, sm, 9013, m_hi=240, m_lo=30, r_hi=15, r_lo=140, cc_hi=16, cc_lo=120)

def paint_cx_obsidian_gold(paint, shape, mask, seed, pm, bb):
    """Obsidian Gold — liquid 24k gold chrome ↔ volcanic obsidian matte black."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.90, 0.75, 0.20], dtype=np.float32),
        np.array([0.03, 0.02, 0.04], dtype=np.float32), 9014)

def spec_cx_obsidian_gold(shape, seed, sm, base_m, base_r):
    return _cx_spec_2color(shape, seed, sm, 9014, m_hi=248, m_lo=5, r_hi=15, r_lo=230, cc_hi=16, cc_lo=210)

def paint_cx_electric_storm(paint, shape, mask, seed, pm, bb):
    """Electric Storm — crackling electric blue chrome ↔ thundercloud dark gray matte."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.15, 0.45, 0.95], dtype=np.float32),
        np.array([0.12, 0.13, 0.15], dtype=np.float32), 9015)

def spec_cx_electric_storm(shape, seed, sm, base_m, base_r):
    return _cx_spec_2color(shape, seed, sm, 9015, m_hi=238, m_lo=20, r_hi=15, r_lo=160, cc_hi=16, cc_lo=140)

def paint_cx_rose_chrome(paint, shape, mask, seed, pm, bb):
    """Rose Chrome — rose gold chrome mirror ↔ deep burgundy velvet matte."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.88, 0.65, 0.58], dtype=np.float32),
        np.array([0.30, 0.04, 0.08], dtype=np.float32), 9016)

def spec_cx_rose_chrome(shape, seed, sm, base_m, base_r):
    return _cx_spec_2color(shape, seed, sm, 9016, m_hi=245, m_lo=25, r_hi=15, r_lo=190, cc_hi=16, cc_lo=180)

def paint_cx_toxic_chrome(paint, shape, mask, seed, pm, bb):
    """Toxic Chrome — acid green chrome ↔ chemical waste matte brown-black."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.40, 0.90, 0.15], dtype=np.float32),
        np.array([0.12, 0.08, 0.03], dtype=np.float32), 9017)

def spec_cx_toxic_chrome(shape, seed, sm, base_m, base_r):
    return _cx_spec_2color(shape, seed, sm, 9017, m_hi=242, m_lo=8, r_hi=15, r_lo=200, cc_hi=16, cc_lo=190)

def paint_cx_midnight_chrome(paint, shape, mask, seed, pm, bb):
    """Midnight Chrome — vivid blue chrome mirror ↔ pure flat black void."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.22, 0.35, 0.88], dtype=np.float32),   # brighter vivid blue — visible at non-specular angles
        np.array([0.01, 0.01, 0.02], dtype=np.float32), 9018)

def spec_cx_midnight_chrome(shape, seed, sm, base_m, base_r):
    return _cx_spec_2color(shape, seed, sm, 9018, m_hi=248, m_lo=0, r_hi=15, r_lo=248, cc_hi=16, cc_lo=240)

def paint_cx_white_lightning(paint, shape, mask, seed, pm, bb):
    """White Lightning — warm white-gold chrome ↔ cool blue-charcoal matte."""
    return _cx_paint_2color(paint, shape, mask, seed, pm,
        np.array([0.98, 0.94, 0.82], dtype=np.float32),   # warm white-gold — distinct from Chrome Void's cool chrome
        np.array([0.08, 0.10, 0.18], dtype=np.float32),   # cool blue-charcoal — distinct from Chrome Void's pure black
        9019)

def spec_cx_white_lightning(shape, seed, sm, base_m, base_r):
    return _cx_spec_2color(shape, seed, sm, 9019, m_hi=250, m_lo=10, r_hi=15, r_lo=200, cc_hi=16, cc_lo=180)


# ── 5 THREE-COLOR (16-20) ──

def _cx_paint_3color(paint, shape, mask, seed, pm, c1, c2, c3, seed_off):
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
    return _cx_paint_3color(paint, shape, mask, seed, pm,
        np.array([0.20, 0.90, 0.30], dtype=np.float32),
        np.array([0.05, 0.40, 0.45], dtype=np.float32),
        np.array([0.40, 0.08, 0.60], dtype=np.float32), 9020)

def spec_cx_aurora_borealis(shape, seed, sm, base_m, base_r):
    return _cx_spec_3color(shape, seed, sm, 9020,
        m_vals=(235, 140, 60), r_vals=(15, 40, 100), cc_vals=(16, 28, 55))

def paint_cx_dragon_scale(paint, shape, mask, seed, pm, bb):
    """Dragon Scale — chrome gold + ember red + charcoal black."""
    return _cx_paint_3color(paint, shape, mask, seed, pm,
        np.array([0.90, 0.78, 0.22], dtype=np.float32),
        np.array([0.92, 0.20, 0.02], dtype=np.float32),   # pushed redder — more ember, bigger hue gap from gold
        np.array([0.06, 0.05, 0.04], dtype=np.float32), 9021)

def spec_cx_dragon_scale(shape, seed, sm, base_m, base_r):
    return _cx_spec_3color(shape, seed, sm, 9021,
        m_vals=(248, 180, 5), r_vals=(15, 30, 230), cc_vals=(16, 22, 210))

def paint_cx_frozen_nebula(paint, shape, mask, seed, pm, bb):
    """Frozen Nebula — ice white chrome + cosmic blue + deep purple void."""
    return _cx_paint_3color(paint, shape, mask, seed, pm,
        np.array([0.90, 0.92, 0.98], dtype=np.float32),
        np.array([0.08, 0.25, 0.75], dtype=np.float32),
        np.array([0.20, 0.02, 0.35], dtype=np.float32), 9022)

def spec_cx_frozen_nebula(shape, seed, sm, base_m, base_r):
    return _cx_spec_3color(shape, seed, sm, 9022,
        m_vals=(250, 160, 30), r_vals=(15, 35, 150), cc_vals=(16, 25, 120))

def paint_cx_hellfire(paint, shape, mask, seed, pm, bb):
    """Hellfire — white-hot chrome + lava orange + scorched black."""
    return _cx_paint_3color(paint, shape, mask, seed, pm,
        np.array([0.98, 0.95, 0.85], dtype=np.float32),
        np.array([0.92, 0.40, 0.02], dtype=np.float32),
        np.array([0.04, 0.02, 0.01], dtype=np.float32), 9023)

def spec_cx_hellfire(shape, seed, sm, base_m, base_r):
    return _cx_spec_3color(shape, seed, sm, 9023,
        m_vals=(250, 150, 0), r_vals=(15, 25, 250), cc_vals=(16, 20, 240))

def paint_cx_ocean_trench(paint, shape, mask, seed, pm, bb):
    """Ocean Trench — bioluminescent teal + deep navy + abyssal black."""
    return _cx_paint_3color(paint, shape, mask, seed, pm,
        np.array([0.10, 0.85, 0.70], dtype=np.float32),
        np.array([0.06, 0.18, 0.58], dtype=np.float32),   # brighter navy — more visible separation from abyss
        np.array([0.01, 0.02, 0.05], dtype=np.float32), 9024)

def spec_cx_ocean_trench(shape, seed, sm, base_m, base_r):
    return _cx_spec_3color(shape, seed, sm, 9024,
        m_vals=(230, 120, 5), r_vals=(15, 45, 200), cc_vals=(16, 30, 180))


# ── 5 FOUR-COLOR (21-25) ──

def _cx_paint_4color(paint, shape, mask, seed, pm, c1, c2, c3, c4, seed_off):
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
    return _cx_paint_4color(paint, shape, mask, seed, pm,
        np.array([0.85, 0.10, 0.08], dtype=np.float32),
        np.array([0.90, 0.75, 0.15], dtype=np.float32),
        np.array([0.08, 0.70, 0.60], dtype=np.float32),
        np.array([0.15, 0.08, 0.50], dtype=np.float32), 9026)

def spec_cx_prism_shatter(shape, seed, sm, base_m, base_r):
    return _cx_spec_4color(shape, seed, sm, 9026,
        m_vals=(248, 170, 85, 18), r_vals=(15, 35, 80, 160), cc_vals=(16, 22, 50, 130))

def paint_cx_acid_rain(paint, shape, mask, seed, pm, bb):
    """Acid Rain — toxic yellow chrome + sick green + bruise purple + ash gray matte."""
    return _cx_paint_4color(paint, shape, mask, seed, pm,
        np.array([0.92, 0.88, 0.10], dtype=np.float32),
        np.array([0.30, 0.78, 0.12], dtype=np.float32),
        np.array([0.40, 0.10, 0.55], dtype=np.float32),
        np.array([0.18, 0.18, 0.20], dtype=np.float32), 9027)

def spec_cx_acid_rain(shape, seed, sm, base_m, base_r):
    return _cx_spec_4color(shape, seed, sm, 9027,
        m_vals=(245, 180, 60, 15), r_vals=(15, 25, 80, 180), cc_vals=(16, 20, 50, 150))

def paint_cx_royal_spectrum(paint, shape, mask, seed, pm, bb):
    """Royal Spectrum — chrome silver + sapphire blue + ruby red + emerald green. Crown jewels."""
    return _cx_paint_4color(paint, shape, mask, seed, pm,
        np.array([0.85, 0.88, 0.92], dtype=np.float32),
        np.array([0.10, 0.15, 0.70], dtype=np.float32),
        np.array([0.72, 0.05, 0.08], dtype=np.float32),
        np.array([0.08, 0.55, 0.18], dtype=np.float32), 9028)

def spec_cx_royal_spectrum(shape, seed, sm, base_m, base_r):
    return _cx_spec_4color(shape, seed, sm, 9028,
        m_vals=(250, 165, 55, 12), r_vals=(15, 40, 110, 200), cc_vals=(16, 25, 70, 170))

def paint_cx_apocalypse(paint, shape, mask, seed, pm, bb):
    """Apocalypse — scorching white chrome + blood red + rust orange + dead black. End times."""
    return _cx_paint_4color(paint, shape, mask, seed, pm,
        np.array([0.98, 0.95, 0.88], dtype=np.float32),
        np.array([0.58, 0.02, 0.10], dtype=np.float32),   # cooler blood red — more distinct from rust
        np.array([0.82, 0.42, 0.05], dtype=np.float32),   # brighter rust orange — more distinct from blood
        np.array([0.02, 0.02, 0.02], dtype=np.float32), 9029)

def spec_cx_apocalypse(shape, seed, sm, base_m, base_r):
    return _cx_spec_4color(shape, seed, sm, 9029,
        m_vals=(252, 160, 65, 0), r_vals=(15, 30, 90, 252), cc_vals=(16, 22, 65, 252))
