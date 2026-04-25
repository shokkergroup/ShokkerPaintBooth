# -*- coding: utf-8 -*-
"""
CARBON & COMPOSITE -- 8 bases, each with unique paint_fn + spec_fn
Composite materials have physically distinct weave/structure patterns.
Each technique creates a different geometric or material pattern.

Techniques (all different):
  carbon_base      - 2x2 twill weave via modular arithmetic (classic CF)
  carbon_ceramic   - Carbon base + ceramic glaze overlay (SiC matrix)
  aramid           - Plain weave at different frequency (Nomex/Twaron)
  fiberglass       - Random chopped strand mat (CSM orientation scatter)
  forged_composite - Marbled short-fiber compression (no weave pattern)
  graphene         - Hexagonal honeycomb lattice (atomic structure)
  hybrid_weave     - Two-material interlocked weave (carbon+kevlar)
  kevlar_base      - Basket weave with golden fiber color
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid
from engine.paint_v2 import ensure_bb_2d

# ==================================================================
# CARBON BASE - 2x2 twill weave via modular arithmetic
# Classic carbon fiber is a 2x2 twill: each tow passes over 2
# then under 2, offset by 1 row. Creates the iconic diagonal pattern.
# ==================================================================

def paint_carbon_base_v2(paint, shape, mask, seed, pm, bb):
    """Carbon fiber 2x2 twill weave via modular arithmetic with anisotropic shading."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # Tow size scales with canvas (each tow is ~8px at 2048)
    tow = max(h // 256, 2)
    # 2x2 twill: diagonal pattern from modular arithmetic
    ty = (y // tow).astype(int)
    tx = (x // tow).astype(int)
    # Twill: fiber on top when (ty + tx) % 4 < 2
    twill = ((ty + tx) % 4 < 2).astype(np.float32)

    # Fiber direction creates anisotropic shading
    # Warp fibers (vertical) and weft fibers (horizontal)
    fiber_angle = twill * 0.7 + (1.0 - twill) * 0.3
    # Micro-variation within each tow
    tow_noise = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 300)

    # Carbon is very dark with slight directional shine
    gray = base.mean(axis=2, keepdims=True)
    carbon = np.clip(gray * 0.08 + 0.02, 0, 1)  # near black
    # Weave pattern creates brightness variation
    weave_bright = carbon * (0.6 + fiber_angle[:,:,np.newaxis] * 0.4 + tow_noise[:,:,np.newaxis] * 0.15)
    effect = np.clip(weave_bright, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.12 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)

def spec_carbon_base(shape, seed, sm, base_m, base_r):
    """Carbon fiber: moderate metallic (conductive), low roughness where clearcoated."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    tow = max(h // 256, 2)
    twill = (((y // tow).astype(int) + (x // tow).astype(int)) % 4 < 2).astype(np.float32)
    tow_noise = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 300)
    M = np.clip(80.0 + twill * 40.0 * sm + tow_noise * 15.0, 0, 255).astype(np.float32)
    R = np.clip(15.0 + (1.0 - twill) * 25.0 * sm, 15, 255)
    CC = np.clip(16.0 + twill * 5.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# CARBON CERAMIC - Carbon + silicon carbide ceramic matrix
# CMC (Ceramic Matrix Composite): carbon fiber embedded in a ceramic
# binder. The ceramic fills gaps between tows creating a smoother
# surface with a matte ceramic sheen over the weave pattern.
# ==================================================================

def paint_carbon_ceramic_v2(paint, shape, mask, seed, pm, bb):
    """Carbon ceramic matrix composite: carbon twill under ceramic glaze overlay."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # Same twill base but partially obscured by ceramic matrix
    tow = max(h // 256, 2)
    twill = (((y // tow).astype(int) + (x // tow).astype(int)) % 4 < 2).astype(np.float32)

    # Ceramic matrix fill — smoother, lighter than bare carbon
    matrix_fill = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 310)
    # Matrix partially covers weave (0.4 = visible weave, 0.8 = mostly matrix)
    matrix_coverage = np.clip(matrix_fill * 0.6 + 0.3, 0, 1)
    gray = base.mean(axis=2, keepdims=True)
    carbon_layer = np.clip(gray * 0.06 + 0.02, 0, 1)
    ceramic_layer = np.clip(gray * 0.15 + 0.12, 0, 1)  # lighter ceramic

    # Blend carbon weave with ceramic matrix
    combined = (carbon_layer * (1.0 - matrix_coverage[:,:,np.newaxis]) * (0.5 + twill[:,:,np.newaxis] * 0.5) +
                ceramic_layer * matrix_coverage[:,:,np.newaxis])
    effect = np.clip(combined, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_carbon_ceramic(shape, seed, sm, base_m, base_r):
    """CMC: lower metallic (ceramic binder is dielectric), higher roughness from matte ceramic."""
    h, w = shape[:2] if len(shape) > 2 else shape
    matrix = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 310)
    M = np.clip(40.0 + (1.0 - matrix) * 50.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(60.0 + matrix * 80.0 * sm, 15, 255)
    CC = np.clip(16.0 + matrix * 10.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# ARAMID - Plain weave at different frequency
# Aramid fibers (Nomex, Twaron) use a plain 1/1 weave — each tow
# alternates over/under every crossing. Finer than carbon fiber.
# Natural color is off-white/tan. Different weave math from twill.
# ==================================================================

def paint_aramid_weave_v2(paint, shape, mask, seed, pm, bb):
    """Aramid plain 1/1 weave with off-white/cream fiber coloring."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))
    # Plain weave: 1/1 — alternating every single tow crossing
    tow = max(h // 384, 2)  # finer than carbon
    ty = (y // tow).astype(int)
    tx = (x // tow).astype(int)
    plain = ((ty + tx) % 2).astype(np.float32)  # checkerboard at tow scale

    # Aramid is off-white/cream colored, NOT black like carbon
    gray = base.mean(axis=2, keepdims=True)
    aramid_base = np.clip(gray * 0.2 + 0.55, 0, 1)  # light tan base
    aramid_color = np.stack([
        np.clip(aramid_base[:,:,0] + 0.04, 0, 1),   # warm
        np.clip(aramid_base[:,:,0] + 0.02, 0, 1),
        np.clip(aramid_base[:,:,0] - 0.05, 0, 1),   # less blue
    ], axis=-1)

    # Weave shadow pattern
    fiber_var = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 320)
    effect = np.clip(aramid_color * (0.75 + plain[:,:,np.newaxis] * 0.25 + fiber_var[:,:,np.newaxis] * 0.1), 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_aramid_weave(shape, seed, sm, base_m, base_r):
    """Aramid: dielectric fiber, moderate roughness from weave texture."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    tow = max(h // 384, 2)
    plain = (((y // tow).astype(int) + (x // tow).astype(int)) % 2).astype(np.float32)
    M = np.clip(base_m * 0.1 + plain * 8.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(80.0 + plain * 30.0 * sm, 15, 255)
    CC = np.clip(16.0 + plain * 6.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# FIBERGLASS - Chopped strand mat (CSM)
# Random fiber orientation scatter — NOT woven. Short fibers are
# sprayed and compressed. Each fiber has a random angle and length,
# creating a distinctive random-directional texture.
# ==================================================================

def paint_fiberglass_cloth_v2(paint, shape, mask, seed, pm, bb):
    """Fiberglass chopped strand mat with random fiber orientation scatter."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.RandomState(seed + 330)
    base = paint.copy()

    # Random fiber strands scattered across surface
    fiber_map = np.zeros((h, w), dtype=np.float32)
    n_fibers = 500 + (seed % 200)
    for _ in range(n_fibers):
        fy, fx = rng.randint(0, h), rng.randint(0, w)
        angle = rng.uniform(0, np.pi)
        length = rng.randint(max(2, h // 128), max(4, h // 32))
        # Draw fiber as a line
        for t in range(length):
            py = int(fy + t * np.sin(angle))
            px = int(fx + t * np.cos(angle))
            if 0 <= py < h and 0 <= px < w:
                fiber_map[py, px] = rng.uniform(0.5, 1.0)

    # Blur slightly (fibers have width)
    import cv2 as _cv2
    fiber_map = _cv2.GaussianBlur(fiber_map.astype(np.float32), (0, 0), max(h // 512, 1))
    # Fiberglass is translucent white/cream with visible strand texture
    gray = base.mean(axis=2)
    fg_base = np.clip(gray * 0.15 + 0.6, 0, 1)
    # Fibers are slightly brighter than resin between them
    fg_3ch = np.stack([fg_base, fg_base, fg_base], axis=-1)
    effect = np.clip(fg_3ch * (0.85 + fiber_map[:,:,np.newaxis] * 0.15), 0, 1)
    # Slight green tint (epoxy resin color)
    effect[:,:,1] = np.clip(effect[:,:,1] + 0.02, 0, 1)
    effect = effect.astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_fiberglass_cloth(shape, seed, sm, base_m, base_r):
    """Fiberglass CSM: dielectric, moderate roughness from random fiber texture."""
    h, w = shape[:2] if len(shape) > 2 else shape
    fiber = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 330)
    M = np.clip(base_m * 0.05 + fiber * 5.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(70.0 + fiber * 40.0 * sm, 15, 255)
    CC = np.clip(16.0 + fiber * 8.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# FORGED COMPOSITE - Marbled short-fiber compression
# Lamborghini's forged composite: chopped carbon fibers compressed
# in resin. Creates a marbled/swirled pattern, NOT a weave.
# Uses domain warping for the characteristic swirl pattern.
# ==================================================================

def paint_forged_composite_v2(paint, shape, mask, seed, pm, bb):
    """Forged composite marbled short-fiber compression with domain-warped swirl pattern."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    # Domain warping for marble/swirl pattern
    warp1 = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 340)
    warp2 = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 341)
    base_noise = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 342)

    y, x = get_mgrid((h, w))
    yn = y / max(h - 1, 1) + (warp1 - 0.5) * 0.5
    xn = x / max(w - 1, 1) + (warp2 - 0.5) * 0.5

    # Marble pattern from warped coordinates
    marble = np.sin(yn * 8.0 + xn * 4.0 + base_noise * 3.0) * 0.5 + 0.5
    marble = np.clip(marble, 0, 1).astype(np.float32)

    # Forged composite: dark carbon fiber chunks in darker resin
    gray = base.mean(axis=2, keepdims=True)
    fiber_dark = np.clip(gray * 0.05 + 0.01, 0, 1)
    resin_dark = np.clip(gray * 0.03 + 0.015, 0, 1)

    effect = np.clip(fiber_dark * marble[:,:,np.newaxis] + resin_dark * (1.0 - marble[:,:,np.newaxis]), 0, 1)
    # Fiber chunks catch light slightly differently
    effect = np.clip(effect + marble[:,:,np.newaxis] * 0.03, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.1 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_forged_composite(shape, seed, sm, base_m, base_r):
    """Forged: fiber chunks are more metallic than resin. Random roughness."""
    h, w = shape[:2] if len(shape) > 2 else shape
    marble = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 342)
    M = np.clip(50.0 + marble * 60.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(30.0 + (1.0 - marble) * 50.0 * sm, 15, 255)
    CC = np.clip(16.0 + marble * 6.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# GRAPHENE - Hexagonal honeycomb lattice
# Graphene's atomic structure is a hexagonal lattice. We render this
# as a visible honeycomb pattern — the hex grid creates distinctive
# cell boundaries with slightly different shading per cell.
# ==================================================================

def paint_graphene_lattice_v2(paint, shape, mask, seed, pm, bb):
    """Graphene hexagonal honeycomb lattice with per-cell shading variation."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # Hex grid parameters
    cell_size = max(h // 64, 3)  # ~32px cells at 2048
    sqrt3 = np.sqrt(3.0)

    # Axial hex coordinates
    q = (2.0/3.0 * x) / cell_size
    r_hex = (-1.0/3.0 * x + sqrt3/3.0 * y) / cell_size

    # Round to nearest hex center (cube coordinate rounding)
    s = -q - r_hex
    rq, rr, rs = np.round(q), np.round(r_hex), np.round(s)
    dq = np.abs(rq - q)
    dr = np.abs(rr - r_hex)
    ds = np.abs(rs - s)
    # Fix rounding to maintain q+r+s=0
    rq = np.where((dq > dr) & (dq > ds), -rr - rs, rq)
    rr = np.where((dr > ds) & ~((dq > dr) & (dq > ds)), -rq - rs, rr)

    # Distance from hex center (for cell boundary detection)
    fq = q - rq
    fr = r_hex - rr
    hex_dist = np.sqrt(fq**2 + fr**2 + (fq + fr)**2)
    # Cell boundary: where distance is high
    boundary = np.clip(hex_dist * 2.5, 0, 1).astype(np.float32)
    # Per-cell shading variation (each hex cell has slightly different tone)
    cell_id = (rq * 73856093 + rr * 19349663).astype(np.int64)  # hash
    cell_shade = ((cell_id % 256) / 256.0).astype(np.float32) * 0.08

    # Graphene is very dark, semi-metallic with hex pattern
    gray = base.mean(axis=2, keepdims=True)
    graphene_base = np.clip(gray * 0.06 + 0.03 + cell_shade[:,:,np.newaxis], 0, 1)
    # Boundaries are slightly brighter (bond lines)
    effect = np.clip(graphene_base + boundary[:,:,np.newaxis] * 0.06, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.18 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_graphene_lattice(shape, seed, sm, base_m, base_r):
    """Graphene: semi-metallic (sp2 bonding conducts), smooth with hex texture in roughness."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    cell_size = max(h // 64, 3)
    sqrt3 = np.sqrt(3.0)
    q = (2.0/3.0 * x) / cell_size
    r_hex = (-1.0/3.0 * x + sqrt3/3.0 * y) / cell_size
    rq, rr = np.round(q), np.round(r_hex)
    fq, fr = q - rq, r_hex - rr
    hex_dist = np.sqrt(fq**2 + fr**2 + (fq + fr)**2)
    boundary = np.clip(hex_dist * 2.5, 0, 1)
    # Hex boundaries are rougher (grain boundaries)
    M = np.clip(120.0 + (1.0 - boundary) * 40.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(12.0 + boundary * 30.0 * sm, 15, 255).astype(np.float32)  # GGX floor
    CC = np.clip(16.0 + boundary * 5.0, 16, 255).astype(np.float32)
    return M, R, CC

# ==================================================================
# HYBRID WEAVE - Two-material interlocked weave (carbon + kevlar)
# Alternating carbon and kevlar tows in a twill. Carbon tows are
# black, kevlar tows are golden yellow. Creates a distinctive
# two-tone woven pattern used in high-end automotive.
# ==================================================================

def paint_hybrid_weave_v2(paint, shape, mask, seed, pm, bb):
    """Hybrid carbon+kevlar interlocked twill weave with two-tone tow coloring."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    tow = max(h // 256, 2)
    ty = (y // tow).astype(int)
    tx = (x // tow).astype(int)

    # 2x2 twill pattern
    twill = ((ty + tx) % 4 < 2).astype(np.float32)
    # Material alternation: even columns = carbon, odd = kevlar
    material = ((tx // 2) % 2).astype(np.float32)

    # Carbon tow color (black)
    gray = base.mean(axis=2, keepdims=True)
    carbon_color = np.clip(gray * 0.06 + 0.02, 0, 1)
    carbon_rgb = np.concatenate([carbon_color, carbon_color, carbon_color], axis=-1)

    # Kevlar tow color (golden yellow)
    kevlar_rgb = np.stack([
        np.clip(gray[:,:,0] * 0.15 + 0.55, 0, 1),
        np.clip(gray[:,:,0] * 0.12 + 0.40, 0, 1),
        np.clip(gray[:,:,0] * 0.05 + 0.08, 0, 1),
    ], axis=-1)
    # Mix materials based on which tow is on top
    tow_color = carbon_rgb * (1.0 - material[:,:,np.newaxis]) + kevlar_rgb * material[:,:,np.newaxis]
    # Weave gives depth: top tows are brighter
    effect = np.clip(tow_color * (0.7 + twill[:,:,np.newaxis] * 0.3), 0, 1)
    tow_noise = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 350)
    effect = np.clip(effect + tow_noise[:,:,np.newaxis] * 0.04, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.15 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_hybrid_weave(shape, seed, sm, base_m, base_r):
    """Hybrid: carbon tows are metallic, kevlar tows are dielectric. Mixed spec."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    tow = max(h // 256, 2)
    material = (((x // tow).astype(int) // 2) % 2).astype(np.float32)
    twill = (((y // tow).astype(int) + (x // tow).astype(int)) % 4 < 2).astype(np.float32)
    # Carbon = metallic, kevlar = dielectric
    M = np.clip((1.0 - material) * 90.0 + material * 15.0 + twill * 15.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(20.0 + material * 50.0 * sm + (1.0 - twill) * 15.0, 15, 255)
    CC = np.clip(16.0 + twill * 5.0, 16, 255).astype(np.float32)
    return M, R, CC


# ==================================================================
# KEVLAR BASE - Basket weave with golden fiber color
# Kevlar uses a 2x2 basket weave (pairs of tows interlocked).
# Different from twill (offset) and plain (1/1 alternation).
# Golden yellow color, dielectric, distinctive weave rhythm.
# ==================================================================
def paint_kevlar_golden_v2(paint, shape, mask, seed, pm, bb):
    """Kevlar basket weave with golden yellow fiber color and tow border detail."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bb = ensure_bb_2d(bb, shape)
    h, w = shape[:2] if len(shape) > 2 else shape
    base = paint.copy()
    y, x = get_mgrid((h, w))

    # 2x2 basket weave: pairs of tows travel together
    tow = max(h // 256, 2)
    pair = tow * 2  # pairs of tows
    ty = (y // pair).astype(int)
    tx = (x // pair).astype(int)
    # Basket: block pattern at pair scale, NOT diagonal like twill
    basket = ((ty + tx) % 2).astype(np.float32)

    # Individual tow borders within the basket
    tow_border_y = np.abs(np.sin(y / tow * np.pi)) < 0.15
    tow_border_x = np.abs(np.sin(x / tow * np.pi)) < 0.15
    borders = (tow_border_y | tow_border_x).astype(np.float32) * 0.15

    # Kevlar golden color
    gray = base.mean(axis=2, keepdims=True)
    kevlar_r = np.clip(gray[:,:,0] * 0.15 + 0.58, 0, 1)
    kevlar_g = np.clip(gray[:,:,0] * 0.12 + 0.42, 0, 1)
    kevlar_b = np.clip(gray[:,:,0] * 0.05 + 0.10, 0, 1)
    kevlar = np.stack([kevlar_r, kevlar_g, kevlar_b], axis=-1)

    # Basket weave shadow + tow noise
    tow_noise = multi_scale_noise((h, w), [1, 2], [0.5, 0.5], seed + 360)
    effect = np.clip(kevlar * (0.7 + basket[:,:,np.newaxis] * 0.3) -
                     borders[:,:,np.newaxis] * 0.1 + tow_noise[:,:,np.newaxis] * 0.05, 0, 1).astype(np.float32)

    blend = np.clip(pm, 0.0, 1.0)
    result = np.clip(base * (1.0 - mask[:,:,np.newaxis] * blend) + effect * (mask[:,:,np.newaxis] * blend), 0, 1)
    return np.clip(result + bb[:,:,np.newaxis] * 0.10 * pm * mask[:,:,np.newaxis], 0, 1).astype(np.float32)


def spec_kevlar_golden(shape, seed, sm, base_m, base_r):
    """Kevlar: dielectric, moderate roughness from basket weave."""
    h, w = shape[:2] if len(shape) > 2 else shape
    y, x = get_mgrid((h, w))
    pair = max(h // 256, 2) * 2
    basket = (((y // pair).astype(int) + (x // pair).astype(int)) % 2).astype(np.float32)
    M = np.clip(base_m * 0.08 + basket * 8.0 * sm, 0, 255).astype(np.float32)
    R = np.clip(75.0 + basket * 35.0 * sm, 15, 255)
    CC = np.clip(16.0 + basket * 5.0, 16, 255).astype(np.float32)
    return M, R, CC