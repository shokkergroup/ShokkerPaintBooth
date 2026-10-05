"""
Shokker FUSIONS Expansion - "Paradigm Shift Hybrids"
=====================================================
150 finishes: 10 for each of the 15 Paradigm Shifts from the Spec Map Bible.

FUSIONS are a NEW 4th category - not bases, not patterns, not specials.
They are multi-material hybrid systems where TWO OR MORE complete material
states blend per-pixel using noise, gradients, or geometric fields.

Each Fusion has its own spec_fn and paint_fn (monolithic format).

Registry: FUSION_REGISTRY  (spec_fn, paint_fn) tuples
Integration: integrate_fusions(engine_module) merges into engine
"""

import numpy as np
import cv2
from PIL import Image, ImageFilter
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates as _mc
import os
import importlib.util
from functools import lru_cache
from collections import OrderedDict

_FF_V2 = None
try:
    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _FF_PATH = os.path.join(_ROOT, "_staging", "monolithic_upgrades", "fusion_factories_v2.py")
    if os.path.isfile(_FF_PATH):
        _ff_spec = importlib.util.spec_from_file_location("_staging_fusion_factories_v2", _FF_PATH)
        if _ff_spec is not None and _ff_spec.loader is not None:
            _FF_V2 = importlib.util.module_from_spec(_ff_spec)
            _ff_spec.loader.exec_module(_FF_V2)
except Exception as _ff_ex:
    print(f"[Staging Bridge] fusions v2 unavailable: {_ff_ex}")


def _adapt_staging_factory_result(result):
    try:
        spec_fn, paint_fn = result
    except Exception:
        return result

    def _wrapped_paint_fn(paint, shape, mask, seed, pm, bb):
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        bb_val = bb
        try:
            if np.isscalar(bb):
                h, w = shape[:2] if isinstance(shape, (tuple, list)) and len(shape) >= 2 else paint.shape[:2]
                bb_val = np.full((int(h), int(w)), float(bb), dtype=np.float32)
            elif hasattr(bb, "ndim") and bb.ndim == 0:
                h, w = shape[:2] if isinstance(shape, (tuple, list)) and len(shape) >= 2 else paint.shape[:2]
                bb_val = np.full((int(h), int(w)), float(bb), dtype=np.float32)
        except Exception:
            bb_val = bb
        return paint_fn(paint, shape, mask, seed, pm, bb_val)

    return spec_fn, _wrapped_paint_fn

# ================================================================
# HELPERS
# ================================================================

from engine.core import get_mgrid as _mgrid  # cached, faster than local np.mgrid

def _noise(shape, scales, weights, seed):
    """Multi-octave noise — delegates to cached core.multi_scale_noise for speed."""
    try:
        from engine.core import multi_scale_noise as _cached_msn
        return _cached_msn(shape, scales, weights, seed)
    except ImportError:
        pass
    # Fallback if core not available (shouldn't happen)
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    for s, wt in zip(scales, weights):
        raw = rng.randn(max(1, h // s), max(1, w // s)).astype(np.float32)
        up = cv2.resize(raw, (w, h), interpolation=cv2.INTER_LINEAR)
        result += up * wt
    rmin, rmax = float(result.min()), float(result.max())
    if rmax > rmin:
        result = (result - rmin) / (rmax - rmin) * 2.0 - 1.0
    return result

def _hsv_to_rgb(h, s, v):
    """Vectorized HSV→RGB."""
    h6 = (h % 1.0) * 6.0
    i = np.floor(h6).astype(np.int32) % 6
    f = h6 - np.floor(h6)
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    r = np.where(i == 0, v, np.where(i == 1, q, np.where(i == 2, p, np.where(i == 3, p, np.where(i == 4, t, v)))))
    g = np.where(i == 0, t, np.where(i == 1, v, np.where(i == 2, v, np.where(i == 3, q, np.where(i == 4, p, p)))))
    b = np.where(i == 0, p, np.where(i == 1, p, np.where(i == 2, t, np.where(i == 3, v, np.where(i == 4, v, q)))))
    return r, g, b

def _spec_out(shape, mask, M, G, B):
    """Standard spec output helper.
    Enforces GGX roughness floor: R (G channel) >= 15 for non-chrome pixels (M < 240).
    Chrome pixels (M >= 240) are allowed R < 15 for mirror-finish seams."""
    h, w = shape
    M_clipped = np.clip(M, 0, 255)
    G_clipped = np.clip(G, 0, 255)
    # GGX roughness floor: non-chrome pixels must have R >= 15
    non_chrome = M_clipped < 240
    G_clipped = np.where(non_chrome, np.maximum(G_clipped, 15), G_clipped)
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(M_clipped * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.where(mask > 0.01, np.clip(G_clipped, 15, 255), 0).astype(np.uint8)  # R≥15 in zone
    spec[:,:,2] = np.where(mask > 0.01, np.clip(B, 16, 255), 0).astype(np.uint8)  # CC≥16 in zone
    spec[:,:,3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def _blend_materials(blend, mat_a, mat_b):
    """Blend two (M,G,B) material tuples using a 0-1 blend field."""
    M = mat_a[0] * (1 - blend) + mat_b[0] * blend
    G = mat_a[1] * (1 - blend) + mat_b[1] * blend
    B = mat_a[2] * (1 - blend) + mat_b[2] * blend
    return M, G, B

def _voronoi_cells(shape, n_pts, seed_offset):
    """Voronoi tessellation returning (cell_id, min_dist, edge_dist) arrays.
    cell_id  — int32 array, ID of nearest seed point per pixel
    min_dist — float32 array, distance to nearest seed
    edge_dist — float32 array, difference between 2nd-nearest and nearest (thin at boundaries)
    """
    h, w = shape
    rng = np.random.RandomState(seed_offset)
    pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    d1 = np.full((h, w), 1e9, dtype=np.float32)
    d2 = np.full((h, w), 1e9, dtype=np.float32)
    cell_id = np.zeros((h, w), dtype=np.int32)
    for idx, (py, px) in enumerate(zip(pts_y, pts_x)):
        d = np.sqrt((yf - py)**2 + (xf - px)**2)
        closer = d < d1
        # Where this point is closer than current nearest, push d1 to d2
        d2 = np.where(closer, d1, np.where(d < d2, d, d2))
        cell_id = np.where(closer, idx, cell_id)
        d1 = np.minimum(d1, d)
    edge_dist = d2 - d1
    return cell_id, d1, edge_dist

from engine.core import paint_none as _paint_noop

def _paint_brighten(paint, shape, mask, seed, pm, bb):
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    paint = np.clip(paint + bb * 0.5 * mask[:,:,np.newaxis], 0, 1)
    return paint


# ================================================================
# PARADIGM 1: MULTI-MATERIAL GRADIENT - Spatial material transitions
# ================================================================

def _gradient_y(shape):
    h, w = shape
    return np.linspace(0, 1, h).reshape(h, 1).astype(np.float32) * np.ones((1, w), dtype=np.float32)

def _gradient_x(shape):
    h, w = shape
    return np.ones((h, 1), dtype=np.float32) * np.linspace(0, 1, w).reshape(1, w).astype(np.float32)

def _gradient_diag(shape):
    h, w = shape
    y = np.linspace(0, 1, h).reshape(h, 1)
    x = np.linspace(0, 1, w).reshape(1, w)
    return np.clip((y + x) / 2.0, 0, 1).astype(np.float32)

def _gradient_radial(shape):
    h, w = shape
    y = np.linspace(-1, 1, h).reshape(h, 1)
    x = np.linspace(-1, 1, w).reshape(1, w)
    return np.clip(np.sqrt(y**2 + x**2) / 1.414, 0, 1).astype(np.float32)


def _gradient_mode(grad_fn):
    if grad_fn is _gradient_x:
        return "x"
    if grad_fn is _gradient_diag:
        return "diag"
    if grad_fn is _gradient_radial:
        return "radial"
    return "y"


def _gradient_base(mode, shape):
    if mode == "x":
        return _gradient_x(shape)
    if mode == "diag":
        return _gradient_diag(shape)
    if mode == "radial":
        return _gradient_radial(shape)
    return _gradient_y(shape)


@lru_cache(maxsize=96)
def _gradient_source_fields_cached(h, w, mode, seed, seed_offset, warp_flag):
    shape = (int(h), int(w))
    base = _gradient_base(str(mode), shape)
    y_i, x_i = _mgrid(shape)
    y = y_i.astype(np.float32)
    x = x_i.astype(np.float32)
    cy = (h - 1) * 0.5
    cx = (w - 1) * 0.5
    yy = (y - cy) / max(float(h), 1.0)
    xx = (x - cx) / max(float(w), 1.0)
    dist = np.sqrt(xx * xx + yy * yy)
    angle = np.arctan2(yy, xx)
    flow = _noise(shape, [6, 12, 24], [0.36, 0.36, 0.28], seed + seed_offset + 411)
    vein = _noise(shape, [2, 3, 5], [0.36, 0.34, 0.30], seed + seed_offset + 421)
    fine = (_noise(shape, [1, 2, 3, 5], [0.34, 0.30, 0.22, 0.14], seed + seed_offset + 431) + 1.0) * 0.5
    mist = (_noise(shape, [3, 6, 12], [0.40, 0.36, 0.24], seed + seed_offset + 441) + 1.0) * 0.5
    grad = np.clip(base + flow * (0.105 if warp_flag else 0.055) + vein * 0.030, 0, 1)
    transition = np.exp(-((grad - 0.5) ** 2) / (2 * (0.046 if warp_flag else 0.054) ** 2)).astype(np.float32)

    def _hair(phase, width):
        return np.clip((width - np.abs(np.sin(phase))) / max(width, 1e-4), 0, 1)

    if seed_offset == 7000:
        motif = np.clip(transition * 0.55 + _hair(y * 0.28 + flow * 2.0, 0.035) * 0.42, 0, 1)
        split = np.clip(fine * 0.46 + transition * 0.60, 0, 1)
    elif seed_offset == 7010:
        ice = np.maximum(_hair((x + y) * 0.115 + flow, 0.028), _hair((x - y) * 0.092 - flow, 0.024))
        motif = np.clip(ice * 0.72 + transition * 0.38, 0, 1)
        split = np.clip(fine * 0.46 + mist * 0.22 + ice * 0.48, 0, 1)
    elif seed_offset == 7020:
        pearl = np.sin((x + y) * 0.030 + np.sin(angle * 5.0) + flow * 1.2) * 0.5 + 0.5
        motif = np.clip(pearl * transition + np.clip((fine - 0.62) * 3.5, 0, 1) * 0.45, 0, 1)
        split = np.clip(pearl * 0.45 + fine * 0.40 + transition * 0.32, 0, 1)
    elif seed_offset == 7030:
        brush = _hair(x * 0.34 + flow * 2.2, 0.035)
        motif = np.clip(brush * 0.65 + transition * 0.42, 0, 1)
        split = np.clip(brush * 0.42 + fine * 0.44 + mist * 0.18, 0, 1)
    elif seed_offset == 7040:
        ring = np.maximum(_hair(dist * 420.0 + flow, 0.030), _hair(angle * 18.0 + dist * 62.0, 0.022))
        motif = np.clip(ring * 0.72 + transition * 0.34, 0, 1)
        split = np.clip(ring * 0.38 + fine * 0.48 + (1.0 - grad) * 0.15, 0, 1)
    elif seed_offset == 7050:
        drip = _hair(y * 0.22 + np.sin(x * 0.019) * 1.4 + flow, 0.034)
        motif = np.clip(drip * 0.58 + transition * 0.46, 0, 1)
        split = np.clip(drip * 0.38 + fine * 0.46 + mist * 0.20, 0, 1)
    elif seed_offset == 7060:
        pore = np.clip((fine - 0.56) * 3.2, 0, 1)
        motif = np.clip(pore * 0.42 + transition * 0.50 + np.clip((vein - 0.45) * 0.8, 0, 1), 0, 1)
        split = np.clip(pore * 0.52 + mist * 0.22 + transition * 0.32, 0, 1)
    elif seed_offset == 7070:
        crack = np.maximum(_hair((x + y) * 0.105 + flow * 1.8, 0.027), _hair(dist * 380.0 - angle * 4.0, 0.023))
        motif = np.clip(crack * 0.70 + transition * 0.38, 0, 1)
        split = np.clip(crack * 0.44 + fine * 0.42 + transition * 0.25, 0, 1)
    elif seed_offset == 7080:
        weave_a = _hair((x + y) * 0.24 + flow, 0.030)
        weave_b = _hair((x - y) * 0.24 - flow, 0.030)
        motif = np.clip(np.maximum(weave_a, weave_b) * 0.68 + transition * 0.42, 0, 1)
        split = np.clip((weave_a + weave_b) * 0.28 + fine * 0.44 + transition * 0.28, 0, 1)
    elif seed_offset == 7090:
        orbit = np.maximum(_hair(dist * 470.0 + flow * 1.4, 0.026), _hair(angle * 22.0 + dist * 70.0, 0.023))
        motif = np.clip(orbit * 0.62 + transition * 0.45 + np.clip((fine - 0.67) * 4.5, 0, 1) * 0.40, 0, 1)
        split = np.clip(orbit * 0.35 + fine * 0.52 + transition * 0.30, 0, 1)
    else:
        motif = np.clip(transition * 0.45 + fine * 0.35, 0, 1)
        split = np.clip(fine * 0.55 + mist * 0.20 + transition * 0.25, 0, 1)

    edge = np.clip(
        np.abs(grad - np.roll(grad, 1, axis=0))
        + np.abs(grad - np.roll(grad, 1, axis=1))
        + np.abs(motif - np.roll(motif, 1, axis=0)) * 0.58
        + np.abs(motif - np.roll(motif, 1, axis=1)) * 0.58,
        0,
        1,
    )
    flake = np.clip((fine - 0.58) * 4.4 + motif * 0.42 + edge * 1.55, 0, 1)
    return grad.astype(np.float32), transition.astype(np.float32), fine.astype(np.float32), motif.astype(np.float32), split.astype(np.float32), edge.astype(np.float32), flake.astype(np.float32)


def _gradient_source_fields(shape, mode, seed, seed_offset, warp_flag):
    h, w = shape[:2]
    return _gradient_source_fields_cached(int(h), int(w), str(mode), int(seed), int(seed_offset), bool(warp_flag))


def _gradient_recipe(seed_offset):
    return {
        7000: {"cool": (0.46, 0.50, 0.56), "warm": (0.88, 0.92, 0.90), "paint_gain": 0.18, "cc_boost": 136.0},
        7010: {"cool": (0.52, 0.70, 0.96), "warm": (0.94, 0.20, 0.36), "paint_gain": 0.27, "cc_boost": 154.0},
        7020: {"cool": (0.58, 0.66, 0.88), "warm": (0.96, 0.80, 0.98), "paint_gain": 0.24, "cc_boost": 148.0},
        7030: {"cool": (0.44, 0.46, 0.48), "warm": (0.80, 0.66, 0.48), "paint_gain": 0.22, "cc_boost": 142.0},
        7040: {"cool": (0.02, 0.03, 0.06), "warm": (0.64, 0.72, 0.94), "paint_gain": 0.20, "cc_boost": 158.0},
        7050: {"cool": (0.30, 0.22, 0.18), "warm": (0.92, 0.20, 0.18), "paint_gain": 0.27, "cc_boost": 134.0},
        7060: {"cool": (0.18, 0.44, 0.72), "warm": (0.92, 0.48, 0.20), "paint_gain": 0.28, "cc_boost": 146.0},
        7070: {"cool": (0.18, 0.60, 0.96), "warm": (1.00, 0.26, 0.06), "paint_gain": 0.30, "cc_boost": 156.0},
        7080: {"cool": (0.03, 0.04, 0.05), "warm": (0.72, 0.80, 0.88), "paint_gain": 0.22, "cc_boost": 144.0},
        7090: {"cool": (0.01, 0.02, 0.07), "warm": (1.00, 0.15, 0.72), "paint_gain": 0.33, "cc_boost": 168.0},
    }.get(seed_offset, {"cool": (0.30, 0.36, 0.46), "warm": (0.88, 0.58, 0.36), "paint_gain": 0.24, "cc_boost": 140.0})

def _make_gradient_fusion(mat_a, mat_b, grad_fn, seed_offset=0, warp=False, paint_warm=False):
    """Factory for gradient fusions with domain-warped organic flow and chrome seam transitions."""
    mode = _gradient_mode(grad_fn)

    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        grad, transition, fine, motif, split, edge, flake = _gradient_source_fields(shape, mode, seed, seed_offset, warp)
        recipe = _gradient_recipe(seed_offset)
        grad_m = np.clip(grad ** 0.82, 0, 1)
        grad_r = np.clip(grad ** 1.18, 0, 1)
        grad_cc = np.clip(np.sin(grad * np.pi * 0.5) ** 0.82, 0, 1)
        M = mat_a[0] * (1 - grad_m) + mat_b[0] * grad_m
        G = mat_a[1] * (1 - grad_r) + mat_b[1] * grad_r
        B = mat_a[2] * (1 - grad_cc) + mat_b[2] * grad_cc
        M = M + flake * 58.0 + motif * 44.0 + edge * 62.0
        G = G + (1.0 - fine) * 22.0 + split * 42.0 - motif * 26.0 + transition * 32.0
        B = B + motif * recipe["cc_boost"] + flake * 54.0 + edge * 46.0 + transition * 28.0
        if seed_offset in (7010, 7020, 7040, 7080):
            M = M - split * 28.0
            G = G + split * 34.0
        if seed_offset in (7000, 7030, 7040):
            G = G + (1.0 - transition) * 22.0
        return _spec_out(shape, mask2, M * float(sm), G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        source = np.asarray(paint[:, :, :3], dtype=np.float32)
        if source.max() > 1.5:
            source = source / 255.0
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        active = np.clip(mask2 * float(pm), 0, 1)[:, :, np.newaxis]
        bb3 = bb[:, :, np.newaxis] if hasattr(bb, "ndim") and bb.ndim == 2 else bb
        grad, transition, fine, motif, split, edge, flake = _gradient_source_fields(shape, mode, seed, seed_offset, warp)
        recipe = _gradient_recipe(seed_offset)
        cool = np.asarray(recipe["cool"], dtype=np.float32).reshape(1, 1, 3)
        warm = np.asarray(recipe["warm"], dtype=np.float32).reshape(1, 1, 3)
        tint = cool * (1.0 - grad[:, :, np.newaxis]) + warm * grad[:, :, np.newaxis]
        luma = ((fine - 0.5) * 0.085 + motif * 0.105 + edge * 0.155 - split * 0.030)[:, :, np.newaxis]
        color = (tint - 0.5) * float(recipe["paint_gain"])
        if seed_offset == 7030:
            luma = luma + ((fine - 0.5) * 0.070 + motif * 0.050 + flake * 0.055)[:, :, np.newaxis]
        if paint_warm:
            color += np.stack([grad * 0.026, transition * 0.010, (1.0 - grad) * 0.010], axis=2)
        spark_rgb = np.stack([
            flake * 0.068 + motif * 0.025,
            flake * 0.052 + transition * 0.022,
            flake * 0.046 + (1.0 - grad) * 0.020,
        ], axis=2)
        result = np.clip(source + (color + luma + spark_rgb) * active, 0, 1)
        result = np.clip(result + np.asarray(bb3, dtype=np.float32) * 0.18 * active, 0, 1)
        return result.astype(np.float32)

    return spec_fn, paint_fn

    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_gradient_fusion(mat_a, mat_b, grad_fn, seed_offset, warp, paint_warm))

    def _domain_warp_grad(shape, grad, seed, so):
        """Apply multi-octave Perlin-style domain warp to gradient field."""
        h, w = shape
        # Primary warp: large organic flow
        warp1_y = _noise(shape, [6, 12, 24], [0.3, 0.4, 0.3], seed + so + 500)
        warp1_x = _noise(shape, [6, 12, 24], [0.3, 0.4, 0.3], seed + so + 501)
        # Secondary warp: medium turbulence
        warp2_y = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + so + 502)
        warp2_x = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + so + 503)
        amplitude1 = 0.18
        amplitude2 = 0.08
        warped = grad + warp1_y * amplitude1 + warp2_y * amplitude2
        # Cross-axis warp for true Perlin domain warp: grad(x + noise1*amp, y + noise2*amp)
        y_coords = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
        x_coords = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
        warped_y = np.clip(y_coords + warp1_x * amplitude1 * 0.5, 0, 0.999)
        warped_x = np.clip(x_coords + warp2_x * amplitude2 * 0.5, 0, 0.999)
        # Re-sample gradient with warped coordinates
        base_grad = grad_fn(shape)
        # Mix original warped field with coordinate-warped version
        warped = np.clip(warped * 0.6 + base_grad * 0.4, 0, 1)
        return np.clip(warped, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        grad_raw = grad_fn(shape)
        # Always domain-warp for organic flow (extra warp if warp=True)
        grad = _domain_warp_grad(shape, grad_raw, seed, seed_offset)
        if warp:
            extra_warp = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 510)
            grad = np.clip(grad + extra_warp * 0.15, 0, 1)

        # Transition zone: peaks where grad ~ 0.5, Gaussian-shaped
        transition_raw = np.exp(-((grad - 0.5) ** 2) / (2 * 0.06 ** 2))
        transition_zone = np.clip(transition_raw, 0, 1)

        # Independent M channel: material A at low grad, B at high, with nonlinear warp
        grad_m = np.clip(grad ** 0.85, 0, 1)  # slight nonlinear bias
        M = mat_a[0] * (1 - grad_m) + mat_b[0] * grad_m
        # Chrome seam sparkle in transition zone
        sparkle_noise = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 600)
        M = M + transition_zone * (40 + sparkle_noise * 30) * sm
        # Micro-texture that varies across gradient: fine grain near mat_a, coarse near mat_b
        micro_a = _noise(shape, [32, 64], [0.6, 0.4], seed + seed_offset + 610)
        micro_b = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 620)
        micro = micro_a * (1 - grad) + micro_b * grad
        M = M + micro * 12 * sm

        # Independent R channel: different curve than M
        grad_r = np.clip(grad ** 1.2, 0, 1)  # opposite nonlinear bias
        G = mat_a[1] * (1 - grad_r) + mat_b[1] * grad_r
        # Transition zone gets heightened roughness (chrome seam effect)
        G = G + transition_zone * 45 * sm
        # Fine-grain speckle noise in transition (scale 2-4)
        speckle = _noise(shape, [2, 3, 4], [0.3, 0.4, 0.3], seed + seed_offset + 630)
        G = G + transition_zone * np.abs(speckle) * 25 * sm
        # Cross-gradient micro-roughness
        G = G + np.abs(micro) * 8 * sm

        # Independent CC channel: yet another curve
        grad_cc = np.clip(np.sin(grad * np.pi * 0.5) ** 0.8, 0, 1)  # sinusoidal transition
        B = mat_a[2] * (1 - grad_cc) + mat_b[2] * grad_cc
        # CC dips toward glossy (16) in transition zone for chrome seam shine
        B = B - transition_zone * 30 * sm
        # Subtle CC variation from micro texture
        B = B + micro * 6 * sm

        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        grad_raw = grad_fn(shape)
        grad = _domain_warp_grad(shape, grad_raw, seed, seed_offset)
        if warp:
            extra_warp = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 510)
            grad = np.clip(grad + extra_warp * 0.15, 0, 1)
        result = paint.copy()

        # Gradient-driven brightness: mat_a side brightened, mat_b side slightly darkened
        bright_a = np.clip((1 - grad) * 0.18 * pm, 0, 0.18)
        dark_b = np.clip(grad * 0.10 * pm, 0, 0.10)
        for c in range(3):
            result[:,:,c] = np.clip(paint[:,:,c] + bright_a * mask - dark_b * mask, 0, 1)

        # UPGRADED: warm/cool tints always active (was conditional on paint_warm)
        _warmth = 0.14 if paint_warm else 0.08  # stronger when flagged, but always present
        warm = grad * _warmth * pm
        result[:,:,0] = np.clip(result[:,:,0] + warm * mask, 0, 1)
        cool = (1 - grad) * (_warmth * 0.7) * pm
        result[:,:,2] = np.clip(result[:,:,2] + cool * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + np.minimum(warm, cool) * 0.3 * mask, 0, 1)

        # Chrome seam shimmer in transition zone — visible sparkle where materials meet
        transition = np.exp(-((grad - 0.5) ** 2) / (2 * 0.06 ** 2))
        n_shimmer = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 150)
        shimmer = transition * n_shimmer * 0.16 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + shimmer * mask, 0, 1)

        # Micro-texture color variation across gradient
        micro_color = _noise(shape, [3, 6], [0.5, 0.5], seed + seed_offset + 640)
        color_shift = micro_color * 0.04 * pm * (1 - transition)  # less in transition
        result[:,:,0] = np.clip(result[:,:,0] + color_shift * grad * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + color_shift * (1 - grad) * mask, 0, 1)

        result = np.clip(result + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return result
    return spec_fn, paint_fn

# Chrome(255,2,0) → Matte(0,200,180)
spec_gradient_chrome_matte, paint_gradient_chrome_matte = _make_gradient_fusion((255,2,16), (0,200,180), _gradient_y, 7000)
# Candy(200,15,16) → Frozen(225,140,16)
spec_gradient_candy_frozen, paint_gradient_candy_frozen = _make_gradient_fusion((200,15,16), (225,140,16), _gradient_y, 7010, paint_warm=True)
# Pearl(100,40,16) → Chrome(255,2,0)
spec_gradient_pearl_chrome, paint_gradient_pearl_chrome = _make_gradient_fusion((100,40,16), (255,2,16), _gradient_diag, 7020)
# Metallic(200,50,16) → Satin(0,100,120)
spec_gradient_metallic_satin, paint_gradient_metallic_satin = _make_gradient_fusion((200,50,16), (0,100,120), _gradient_x, 7030)
# Liquid Obs(130,6,16) → Chrome(255,2,0)
spec_gradient_obsidian_mirror, paint_gradient_obsidian_mirror = _make_gradient_fusion((130,6,16), (255,2,16), _gradient_radial, 7040)
# Candy(200,15,16) → Matte(0,215,180)
spec_gradient_candy_matte, paint_gradient_candy_matte = _make_gradient_fusion((200,15,16), (0,215,180), _gradient_y, 7050, warp=True)
# Anodized(170,80,100) → Wet Gloss(10,5,16)
spec_gradient_anodized_gloss, paint_gradient_anodized_gloss = _make_gradient_fusion((170,80,100), (10,5,16), _gradient_diag, 7060)
# Ember(245,5,16) → Arctic(220,30,80) — diagonal+warp, distinct from candy_frozen horizontal — LAZY-FUSIONS-001 FIX
spec_gradient_ember_ice, paint_gradient_ember_ice = _make_gradient_fusion((245,5,16), (220,30,80), _gradient_diag, 7070, warp=True)
# Carbon(55,35,16) → Chrome(255,2,0)
spec_gradient_carbon_chrome, paint_gradient_carbon_chrome = _make_gradient_fusion((55,35,16), (255,2,16), _gradient_y, 7080, warp=True)
# Spectraflame(245,8,16) → Vantablack(0,255,255)
spec_gradient_spectraflame_void, paint_gradient_spectraflame_void = _make_gradient_fusion((245,8,16), (0,255,255), _gradient_radial, 7090)


# ================================================================
# PARADIGM 2: CLEARCOAT-ONLY PATTERNING - Ghost geometry in CC
# ================================================================

def _make_ghost_fusion(base_m, base_g, pattern_fn_name, seed_offset=0):
    """Factory: uniform M/G everywhere, CC varies via advanced geometric pattern.
    Ghost effect = pattern only visible at certain viewing angles via clearcoat channel."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_ghost_fusion(base_m, base_g, pattern_fn_name, seed_offset))

    def _domain_warp(shape, yf, xf, seed_val, strength=0.3):
        """Apply domain warping for organic feel on all patterns."""
        warp_n = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed_val)
        warp_n2 = _noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed_val + 777)
        scale = min(shape[0], shape[1]) * strength
        return yf + warp_n * scale, xf + warp_n2 * scale

    def _compute_ghost_pattern(shape, seed):
        """Compute the actual ghost pattern field pv (0-1) for the given pattern_fn_name."""
        h, w = shape
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)
        yw, xw = _domain_warp(shape, yf, xf, seed + seed_offset + 500, 0.25)
        if pattern_fn_name == "hex":
            hex_size = max(16, min(h, w) // 18)
            hex_d = _hex_cell_dist(shape, hex_size)
            film_phase = hex_d * 12.0
            film_iridescence = np.sin(film_phase) * 0.3 + np.sin(film_phase * 2.7) * 0.2
            border = np.clip((hex_d - 0.72) * 12, 0, 1)
            pv = np.clip(0.5 + film_iridescence - border * 0.6, 0, 1)
        elif pattern_fn_name == "stripes":
            # Moire interference: two overlapping stripe sets at slight angle offset
            freq1, freq2 = 0.045, 0.043
            angle_offset = 0.087  # ~5 degrees
            stripes1 = np.sin(yw * freq1 * 2 * np.pi) * 0.5 + 0.5
            rot_y = yw * np.cos(angle_offset) + xw * np.sin(angle_offset)
            stripes2 = np.sin(rot_y * freq2 * 2 * np.pi) * 0.5 + 0.5
            moire = stripes1 * stripes2
            stripes3 = np.sin(yw * freq1 * 3.7 + xw * 0.01) * 0.5 + 0.5
            pv = np.clip(moire * 0.7 + stripes3 * 0.3, 0, 1)
        elif pattern_fn_name == "diamonds":
            # Penrose tiling (aperiodic) diamond pattern via de Bruijn projection
            pv = np.zeros((h, w), dtype=np.float32)
            scale = max(20, min(h, w) // 22)
            for k in range(5):
                angle = k * np.pi / 5.0
                proj = (yw * np.cos(angle) + xw * np.sin(angle)) / scale
                grid_val = proj - np.floor(proj)
                edge = np.minimum(grid_val, 1.0 - grid_val)
                pv += np.clip(1.0 - edge * 8, 0, 1) * 0.25
            pv = np.clip(pv, 0, 1)
            envelope = np.sin(yw * 0.008) * np.sin(xw * 0.006) * 0.2 + 0.8
            pv = np.clip(pv * envelope, 0, 1)
        elif pattern_fn_name == "waves":
            # Standing wave interference from multiple point sources
            rng = np.random.RandomState(seed + seed_offset + 300)
            n_sources = 5
            pv = np.zeros((h, w), dtype=np.float32)
            for i in range(n_sources):
                cy = rng.uniform(0.1, 0.9) * h
                cx = rng.uniform(0.1, 0.9) * w
                freq = rng.uniform(0.04, 0.08)
                phase = rng.uniform(0, 2 * np.pi)
                dist = np.sqrt((yw - cy)**2 + (xw - cx)**2)
                pv += np.sin(dist * freq + phase)
            pv = pv / n_sources
            pv = pv ** 2
            pv = np.clip(pv, 0, 1)
        elif pattern_fn_name == "camo":
            # Reaction-diffusion (Gray-Scott approximation) organic camo
            activator = _noise(shape, [8, 16, 32], [0.4, 0.35, 0.25], seed + seed_offset + 101)
            inhibitor = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 102)
            reaction = activator * 1.5 - inhibitor * 1.0
            pv = 1.0 / (1.0 + np.exp(-reaction * 6))
            fine = _noise(shape, [32, 64], [0.5, 0.5], seed + seed_offset + 103)
            pv = np.clip(pv + fine * 0.08, 0, 1)
        elif pattern_fn_name == "scales":
            # Overlapping elliptical scales with depth gradient
            sz = max(22, min(h, w) // 16)
            sz_half = sz // 2
            row_i = (yw / (sz * 0.75)).astype(np.int32)
            x_offset = (row_i % 2).astype(np.float32) * sz_half
            col_i = ((xw + x_offset) / sz).astype(np.int32)
            cy_s = (row_i.astype(np.float32) + 0.5) * sz * 0.75
            cx_s = col_i.astype(np.float32) * sz + sz_half - x_offset + sz_half
            dy_s = (yw - cy_s) / (sz * 0.45)
            dx_s = (xw - cx_s) / (sz * 0.55)
            d_ellipse = np.sqrt(dy_s**2 + dx_s**2)
            d_norm = np.clip(d_ellipse, 0, 1)
            depth_grad = np.clip((yw - cy_s) / (sz * 0.4) + 0.3, 0, 1)
            rim = np.clip((d_norm - 0.7) * 6, 0, 1) * np.clip(1.2 - d_norm, 0, 1)
            interior = np.clip(1.0 - d_norm * 1.5, 0, 1)
            pv = np.clip(interior * (1 - depth_grad * 0.5) + rim * 0.4 + depth_grad * 0.3, 0, 1)
        elif pattern_fn_name == "circuit":
            # Fractal circuit traces with hierarchical branching
            rng = np.random.RandomState(seed + seed_offset + 100)
            canvas = np.zeros((h, w), dtype=np.float32)
            for layer, (grid_s, prob, line_w) in enumerate([
                (max(20, min(h, w) // 20), 0.5, 3),
                (max(10, min(h, w) // 40), 0.35, 2),
                (max(5, min(h, w) // 80), 0.2, 1),
            ]):
                gh_l, gw_l = h // grid_s + 1, w // grid_s + 1
                nodes = rng.random((gh_l, gw_l)) < prob
                for gy in range(gh_l):
                    for gx in range(gw_l):
                        if nodes[gy, gx]:
                            py, px = gy * grid_s, gx * grid_s
                            y1, y2 = max(0, py - line_w // 2), min(h, py + line_w // 2 + 1)
                            x1, x2 = max(0, px - grid_s), min(w, px + grid_s)
                            canvas[y1:y2, x1:x2] = max(0.5, 1.0 - layer * 0.25)
                            y1v, y2v = max(0, py - grid_s), min(h, py + grid_s)
                            x1v, x2v = max(0, px - line_w // 2), min(w, px + line_w // 2 + 1)
                            canvas[y1v:y2v, x1v:x2v] = max(0.5, 1.0 - layer * 0.25)
                            pad = line_w + 1
                            canvas[max(0,py-pad):min(h,py+pad+1), max(0,px-pad):min(w,px+pad+1)] = 1.0
            pv = np.clip(canvas, 0, 1)
        elif pattern_fn_name == "vortex":
            # Logarithmic spiral vortex with multiple arms
            y_n = np.linspace(-1, 1, h).reshape(h, 1).astype(np.float32)
            x_n = np.linspace(-1, 1, w).reshape(1, w).astype(np.float32)
            warp_r = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 600) * 0.15
            angle = np.arctan2(y_n + warp_r, x_n + warp_r)
            dist = np.sqrt(y_n**2 + x_n**2) + 0.001
            log_r = np.log(dist + 0.01)
            n_arms = 4
            spiral = np.sin(angle * n_arms - log_r * 8) * 0.5 + 0.5
            envelope = np.clip(1.0 - dist * 0.5, 0.2, 1.0)
            spiral2 = np.sin(angle * (n_arms + 2) + log_r * 12) * 0.3 + 0.5
            pv = np.clip(spiral * envelope * 0.6 + spiral2 * 0.4, 0, 1)
        elif pattern_fn_name == "fracture":
            # Fractal crack network using Worley noise (F2-F1 method)
            rng = np.random.RandomState(seed + seed_offset + 100)
            n_pts = 40
            pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
            pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
            d1 = np.full((h, w), 1e9, dtype=np.float32)
            d2 = np.full((h, w), 1e9, dtype=np.float32)
            for py, px in zip(pts_y, pts_x):
                d = np.sqrt((yf - py)**2 + (xf - px)**2)
                update = d < d1
                d2 = np.where(update, d1, np.where(d < d2, d, d2))
                d1 = np.minimum(d1, d)
            crack_width = d2 - d1
            crack_norm = crack_width / (np.percentile(crack_width, 95) + 1e-6)
            cracks = np.exp(-crack_norm**2 * 8)
            stress = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 200)
            pv = np.clip(cracks + np.abs(stress) * cracks * 0.4, 0, 1)
        elif pattern_fn_name == "quilt":
            # Quilted panels with curved stitch lines and puffiness
            ps = max(20, min(h, w) // 25)
            cell_y = (yw % ps).astype(np.float32) / ps
            cell_x = (xw % ps).astype(np.float32) / ps
            puff = np.sin(cell_y * np.pi) * np.sin(cell_x * np.pi)
            stitch_y = np.minimum(cell_y, 1.0 - cell_y)
            stitch_x = np.minimum(cell_x, 1.0 - cell_x)
            stitch = np.clip(1.0 - np.minimum(stitch_y, stitch_x) * 12, 0, 1)
            diag = np.minimum(np.abs(cell_y - cell_x), np.abs(cell_y - (1.0 - cell_x)))
            cross_stitch = np.clip(1.0 - diag * 15, 0, 1) * 0.5
            pv = np.clip(puff * 0.5 + stitch * 0.35 + cross_stitch * 0.15, 0, 1)
        else:
            pv = np.zeros((h, w), dtype=np.float32)
        return pv

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        # --- Resolution cap: compute at 512 max, upscale ---
        ds = max(1, min(h, w) // 1024)
        sh, sw = max(64, h // ds), max(64, w // ds)
        pv = _compute_ghost_pattern((sh, sw), seed)

        M = np.full((sh, sw), float(base_m), dtype=np.float32)
        G = np.full((sh, sw), float(base_g), dtype=np.float32)
        # Clearcoat: dramatic ghost range CC 16-180 for max angle-dependent visibility
        B = pv * 16.0 + (1 - pv) * 180.0
        # M/G modulation: pattern zones get metallic boost and smoothness
        M = np.clip(M + pv * 80.0 * sm, 0, 255)
        G = np.clip(G - pv * 35.0 * sm + (1 - pv) * 20.0 * sm, 0, 255)
        n = _noise((sh, sw), [8, 16], [0.5, 0.5], seed + seed_offset)
        M = np.clip(M + n * 10 * sm, 0, 255)
        G = np.clip(G + n * 8 * sm, 0, 255)
        # Pattern edges get extra metallic pop via Sobel-like gradient
        pv_dx = np.abs(np.diff(pv, axis=1, prepend=pv[:, :1]))
        pv_dy = np.abs(np.diff(pv, axis=0, prepend=pv[:1, :]))
        edge = np.clip((pv_dx + pv_dy) * 6, 0, 1)
        M = np.clip(M + edge * 45 * sm, 0, 255)
        G = np.clip(G - edge * 18 * sm, 0, 255)
        mask_s = cv2.resize(mask.astype(np.float32), (sw, sh), interpolation=cv2.INTER_LINEAR) if ds > 1 else mask
        spec_small = _spec_out((sh, sw), mask_s, M, G, B)
        if ds > 1:
            spec = np.zeros((h, w, 4), dtype=np.uint8)
            for ch in range(4):
                spec[:, :, ch] = cv2.resize(spec_small[:, :, ch].astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.uint8)
            return spec
        return spec_small

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        """Ghost patterns: COLORSHOXX-style color zones married to the ghost pattern.
        UPGRADED: Was shimmer-only. Now creates real color zones:
        - Pattern-high (pv>0.6): cool spectral tint (blue-cyan for circuits, green for hex, etc.)
        - Pattern-low (pv<0.3): warm desaturated push toward dark base
        - Edges: bright rim highlight with slight color shift
        - The same pv field drives both paint color AND spec M/R/CC = married pair."""
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape
        # --- Resolution cap: compute ghost pattern at 512 max, upscale ---
        ds = max(1, min(h, w) // 1024)
        sh, sw = max(64, h // ds), max(64, w // ds)
        pv_s = _compute_ghost_pattern((sh, sw), seed)
        pv = cv2.resize(pv_s, (w, h), interpolation=cv2.INTER_LINEAR) if ds > 1 else pv_s
        result = paint.copy()
        m3 = mask[:,:,np.newaxis]

        # Color palette per ghost type (seeded from pattern_fn_name hash)
        rng = np.random.RandomState(seed + seed_offset + 777)
        # Cool spectral color for ghost zones (varies per seed for variety)
        ghost_hue = rng.uniform(0.4, 0.7)  # blue-cyan-green range
        ghost_r = np.float32(0.5 + 0.5 * np.cos(ghost_hue * 2 * np.pi))
        ghost_g = np.float32(0.5 + 0.5 * np.cos((ghost_hue - 0.333) * 2 * np.pi))
        ghost_b = np.float32(0.5 + 0.5 * np.cos((ghost_hue - 0.667) * 2 * np.pi))

        # Pattern-high zones: push toward ghost color (spectral tint)
        ghost_strength = np.clip((pv - 0.3) * 2.0, 0, 1).astype(np.float32)  # 0-1 in ghost zones
        tint_blend = ghost_strength * 0.35 * pm  # 35% max color influence
        result[:,:,0] = np.clip(result[:,:,0] * (1 - tint_blend * mask) + ghost_r * tint_blend * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] * (1 - tint_blend * mask) + ghost_g * tint_blend * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] * (1 - tint_blend * mask) + ghost_b * tint_blend * mask, 0, 1)

        # Pattern-low zones: desaturate + darken (shadow base)
        shadow_strength = np.clip((0.3 - pv) * 3.0, 0, 1).astype(np.float32)
        gray = (result[:,:,0] * 0.299 + result[:,:,1] * 0.587 + result[:,:,2] * 0.114)
        desat = shadow_strength * 0.25 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] * (1 - desat * mask) + gray * desat * mask - shadow_strength * 0.08 * pm * mask, 0, 1)

        # Edge detection: bright rim highlight with warm-white color
        pv_dx = np.abs(np.diff(pv, axis=1, prepend=pv[:, :1]))
        pv_dy = np.abs(np.diff(pv, axis=0, prepend=pv[:1, :]))
        edge = np.clip(np.sqrt(pv_dx**2 + pv_dy**2) * 6, 0, 1)
        edge_bright = edge * 0.18 * pm
        result[:,:,0] = np.clip(result[:,:,0] + edge_bright * mask * 1.05, 0, 1)  # slight warm
        result[:,:,1] = np.clip(result[:,:,1] + edge_bright * mask * 1.00, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + edge_bright * mask * 0.90, 0, 1)  # less blue = warm rim

        result = np.clip(result + bb * 0.25 * m3, 0, 1)
        return result
    return spec_fn, paint_fn

spec_ghost_hex, paint_ghost_hex = _make_ghost_fusion(200, 40, "hex", 7100)
spec_ghost_stripes, paint_ghost_stripes = _make_ghost_fusion(255, 5, "stripes", 7110)
spec_ghost_diamonds, paint_ghost_diamonds = _make_ghost_fusion(200, 15, "diamonds", 7120)
spec_ghost_waves, paint_ghost_waves = _make_ghost_fusion(100, 40, "waves", 7130)
spec_ghost_camo, paint_ghost_camo = _make_ghost_fusion(200, 50, "camo", 7140)
spec_ghost_scales, paint_ghost_scales = _make_ghost_fusion(235, 65, "scales", 7150)
spec_ghost_circuit, paint_ghost_circuit = _make_ghost_fusion(250, 5, "circuit", 7160)
spec_ghost_vortex, paint_ghost_vortex = _make_ghost_fusion(245, 8, "vortex", 7170)
spec_ghost_fracture, paint_ghost_fracture = _make_ghost_fusion(170, 80, "fracture", 7180)
spec_ghost_quilt, paint_ghost_quilt = _make_ghost_fusion(220, 40, "quilt", 7190)


_ghost_geometry_cache = {}


def _gg_hash(shape, seed, salt):
    h, w = shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    n = np.sin((x * 127.1 + y * 311.7 + (int(seed) + salt) * 0.013) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _gg_ridge(v, power=1.0):
    return np.power(np.clip(1.0 - np.abs(v), 0, 1), power).astype(np.float32)


def _gg_fields(shape, seed, mode):
    cache_key = (shape, int(seed), mode)
    cached = _ghost_geometry_cache.get(cache_key)
    if cached is not None:
        return cached

    h, w = shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    phase = (int(seed) % 8192) * 0.000767 * np.pi * 2.0
    tw = np.float32(np.pi * 2.0)
    micro = _gg_hash(shape, seed, 337) * 0.55 + (np.sin((x * 67.0 + y * 53.0) * tw + phase) * 0.5 + 0.5) * 0.45

    if mode == "hex":
        # SPB-100 tick 90 (owner verdict 2026-05-16): hex cells were way too
        # large for a 2048² car-body render. Scaled up the hex frequency 5×
        # on both axes (18→90, 15.6→78) so each cell is ~20% prior size and
        # there are ~25× more across the canvas. Matches SPB-99 P1 doctrine.
        qx = x * 90.0 + np.sin(y * tw * 2.4 + phase) * 0.24
        qy = y * 78.0
        gx = np.mod(qx, 1.0) - 0.5
        gy = np.mod(qy + np.floor(qx) * 0.5, 1.0) - 0.5
        cell = np.maximum(np.abs(gx) * 0.86 + np.abs(gy) * 0.50, np.abs(gy))
        pattern = _gg_ridge((cell - 0.36) * 6.5, 1.8)
        # SPB-99 P2 multi-shade spec: per-cell hash perturbs pattern by
        # ±38% so each hex cell inherits a different M/G/B value downstream
        # in spec_fn. Captures the "247 shades on the same pattern" doctrine
        # — every cell sings a slightly different note.
        cell_id = np.floor(qx) + np.floor(qy) * 31.0
        cell_hash = np.sin(cell_id * 12.9898 + phase * 1.7) * 43758.5453
        cell_hash = (cell_hash - np.floor(cell_hash)).astype(np.float32)
        pattern = (pattern * (0.62 + cell_hash * 0.76)).astype(np.float32)
        accent = _gg_ridge(np.sin((x * 54.0 - y * 18.0) * tw + phase), 2.1)
        tint = (0.36, 0.95, 0.86)
    elif mode == "stripes":
        # SPB-100 tick 90: stripes too wide (owner verdict). 75% width = more
        # stripes per axis. Frequency 22 → 30 = ~1.36× density (stripes are
        # 73% prior width).
        base = np.sin((x * 30.0 + y * 3.4 + np.sin(y * tw * 5.0) * 0.22) * tw + phase)
        # SPB-99 P2: per-stripe hash for multi-shade spec.
        stripe_id = np.floor(x * 30.0 + y * 3.4)
        stripe_hash = np.sin(stripe_id * 12.9898 + phase * 1.1) * 43758.5453
        stripe_hash = (stripe_hash - np.floor(stripe_hash)).astype(np.float32)
        hair = np.sin((x * 110.0 - y * 6.0) * tw + phase * 0.6)
        pattern = (_gg_ridge(base, 1.7) * (0.66 + stripe_hash * 0.68)).astype(np.float32)
        accent = _gg_ridge(hair, 2.6)
        tint = (0.72, 0.90, 1.00)
    elif mode == "diamonds":
        # SPB-100 tick 90: diamonds were way too large (owner verdict). Scale
        # 16/11 → 80/55 = 5× density on both axes per SPB-99 P1.
        u = x * 80.0 + y * 55.0 + np.sin(y * tw * 2.0) * 0.18
        v = x * 80.0 - y * 55.0 + np.sin(x * tw * 2.0) * 0.18
        du = np.mod(u, 1.0) - 0.5
        dv = np.mod(v, 1.0) - 0.5
        facet = 1.0 - np.maximum(np.abs(du), np.abs(dv)) * 2.0
        pattern = np.clip(facet, 0, 1)
        # SPB-99 P2: per-diamond chroma hash for multi-shade spec.
        cell_id = np.floor(u) * 17.0 + np.floor(v) * 23.0
        cell_hash = np.sin(cell_id * 12.9898 + phase * 1.3) * 43758.5453
        cell_hash = (cell_hash - np.floor(cell_hash)).astype(np.float32)
        pattern = (pattern * (0.62 + cell_hash * 0.76)).astype(np.float32)
        accent = _gg_ridge(np.sin((u - v) * tw * 2.5 + phase), 2.0)
        tint = (0.76, 0.96, 0.88)
    elif mode == "waves":
        # SPB-100 tick 90: waves too big (owner verdict). 7.5→32, 11→45 = ~4×
        # density per axis, matches SPB-99 P1 (waves now ~25% prior size).
        wave = np.sin((x * 32.0 + np.sin(y * tw * 4.0) * 0.28) * tw + phase)
        cross = np.sin((y * 45.0 - x * 2.2) * tw - phase)
        pattern = np.clip(wave * 0.5 + cross * 0.25 + 0.5, 0, 1)
        # SPB-99 P2: per-wavefront chroma hash. Each crest gets a different
        # shade so the spec channel reads as many-shade water instead of mono.
        wave_id = np.floor(x * 32.0 + y * 4.0) + np.floor(y * 45.0 - x * 2.2) * 17.0
        wave_hash = np.sin(wave_id * 12.9898 + phase * 1.4) * 43758.5453
        wave_hash = (wave_hash - np.floor(wave_hash)).astype(np.float32)
        pattern = (pattern * (0.66 + wave_hash * 0.68)).astype(np.float32)
        accent = _gg_ridge(wave - cross * 0.55, 1.8)
        tint = (0.34, 1.00, 0.88)
    elif mode == "camo":
        a = np.sin((x * 5.8 + y * 3.2) * tw + phase)
        b = np.sin((-x * 4.0 + y * 6.6) * tw - phase * 0.7)
        c = np.sin((x * 12.0 - y * 7.0) * tw + phase * 0.4)
        pattern = (a * 0.42 + b * 0.38 + c * 0.20) * 0.5 + 0.5
        accent = _gg_ridge(a - b, 1.5)
        tint = (0.46, 0.84, 0.54)
    elif mode == "scales":
        # SPB-100 tick 90: scales pattern too large and "doesn't feel like
        # scales" (owner). 14/18 → 70/90 = 5× density both axes; arcs now
        # render as visible fish-scale tessellation at car-body 2048².
        qx = x * 70.0 + np.sin(y * tw * 1.4) * 0.18
        qy = y * 90.0
        row = np.floor(qy)
        cx = np.mod(qx + np.mod(row, 2.0) * 0.5, 1.0) - 0.5
        cy = np.mod(qy, 1.0)
        upper_arc = np.sqrt((cx * 1.15) ** 2 + (cy - 0.12) ** 2)
        lower_arc = np.sqrt((cx * 1.15) ** 2 + (cy - 0.88) ** 2)
        scallop = np.minimum(np.abs(upper_arc - 0.47), np.abs(lower_arc - 0.42))
        fine_rib = np.sin((np.arctan2(cy - 0.12, cx) * 7.0 + upper_arc * 28.0) + phase)
        pattern = np.clip(1.0 - scallop * 9.0, 0, 1)
        # SPB-99 P2: per-scale chroma hash so each fish scale glints
        # a different shade in the spec channel.
        scale_id = np.floor(qx) * 13.0 + row * 31.0
        scale_hash = np.sin(scale_id * 12.9898 + phase * 1.5) * 43758.5453
        scale_hash = (scale_hash - np.floor(scale_hash)).astype(np.float32)
        pattern = (pattern * (0.62 + scale_hash * 0.76)).astype(np.float32)
        accent = np.clip(_gg_ridge(fine_rib, 2.0) * pattern + (micro > 0.76).astype(np.float32) * 0.22, 0, 1)
        tint = (0.45, 1.00, 0.76)
    elif mode == "circuit":
        # SPB-100 tick 90 (ghost_circuit rework_spec): owner "VERY COOL,
        # needs more detail + smaller pattern + heat signatures should vary
        # across spec so reds/pinks pop in regions instead of uniform".
        # Changes: (1) trace frequency 26→48, 19→34 = ~80% more traces;
        # (2) gates threshold relaxed 0.62→0.50 so more circuits fire;
        # (3) per-cell HEAT field — low-freq smooth noise across the canvas
        # carves "hotter" zones (high gate strength) and "cooler" zones
        # (low gate strength). The heat field modulates pattern intensity
        # so spec_fn's M+G+B propagation creates visible thermal regions.
        cells = np.floor(x * 48.0) * 17.0 + np.floor(y * 34.0) * 29.0
        hsh = np.sin(cells * 12.9898 + phase) * 43758.5453
        hsh = hsh - np.floor(hsh)
        horizontal = _gg_ridge(np.sin((y * 64.0 + np.floor(x * 22.0) * 0.17) * tw), 2.9)
        vertical = _gg_ridge(np.sin((x * 72.0 + np.floor(y * 18.0) * 0.13) * tw), 3.0)
        gates = ((hsh > 0.50) & ((horizontal > 0.42) | (vertical > 0.44))).astype(np.float32)
        nodes = _gg_ridge(np.sin((x * 92.0) * tw), 3.0) * _gg_ridge(np.sin((y * 74.0) * tw), 3.0)
        # Heat field: smooth low-frequency thermal map. Hot regions push
        # gates hard, cool regions damp them. Owner's "heat signature"
        # request lives here.
        heat = (np.sin((x * 3.2 + y * 2.4 + phase) * tw) * 0.5 + 0.5).astype(np.float32)
        heat = (heat * (np.sin((x * 1.8 - y * 2.6 + phase * 0.7) * tw) * 0.5 + 0.5)).astype(np.float32)
        heat_mod = (0.42 + heat * 1.16).astype(np.float32)  # range [0.42, 1.58]
        pattern = np.clip((gates + nodes * 0.9) * heat_mod, 0, 1).astype(np.float32)
        accent = np.clip((nodes + gates * 0.55) * (0.55 + heat * 0.90), 0, 1)
        tint = (0.22, 1.00, 0.86)
    elif mode == "vortex":
        # SPB-100 tick 90: owner suggested "multiple vortexes on the canvas
        # at 2048²". Tile 3×3 = 9 vortexes instead of one giant one. Per-
        # vortex phase + chroma so they read as a swirling field instead of
        # a single bullseye.
        gx = x * 3.0           # 3 tiles across
        gy = y * 3.0
        cell_x = np.floor(gx)
        cell_y = np.floor(gy)
        # Per-tile hash for phase + chroma variation
        tile_id = cell_x * 23.0 + cell_y * 37.0
        tile_phase = (np.sin(tile_id * 12.9898) * 43758.5453)
        tile_phase = (tile_phase - np.floor(tile_phase)).astype(np.float32) * tw
        tile_hash = np.sin(tile_id * 7.91 + phase) * 43758.5453
        tile_hash = (tile_hash - np.floor(tile_hash)).astype(np.float32)
        dx = (gx - cell_x) - 0.50
        dy = (gy - cell_y) - 0.50
        r = np.sqrt(dx * dx + dy * dy)
        theta = np.arctan2(dy, dx)
        swirl = np.sin(theta * 9.0 + r * 38.0 - phase - tile_phase)
        pattern = _gg_ridge(swirl, 1.7)
        # SPB-99 P2: per-vortex chroma modulation
        pattern = (pattern * (0.62 + tile_hash * 0.76)).astype(np.float32)
        accent = np.clip(_gg_ridge(np.sin(r * 72.0 + phase + tile_phase), 2.0) + pattern * 0.45, 0, 1)
        tint = (0.72, 0.42, 1.00)
    elif mode == "fracture":
        # SPB-100 tick 90: full fracture rebuild (owner verdict "rework
        # completely... weak overall"). New approach: combine 5 fracture
        # frequencies (was 3) at wider spread, sharper crack mask, plus
        # per-shard chroma. Fractures now read as proper stressed glass:
        # major + minor + hair cracks layered, each shard a different shade.
        f1 = np.sin((x * 14.0 + y * 21.0) * tw + phase)
        f2 = np.sin((-x * 24.0 + y * 11.0) * tw - phase * 0.6)
        f3 = np.sin((x * 43.0 - y * 31.0) * tw + phase * 0.3)
        f4 = np.sin((x * 7.0 + y * 5.0) * tw + phase * 0.8)   # major cracks
        f5 = np.sin((x * 78.0 - y * 62.0) * tw - phase * 0.2)  # hair cracks
        crack = np.minimum.reduce([
            np.abs(f1), np.abs(f2), np.abs(f3),
            np.abs(f4) * 0.6,  # major cracks dominate
            np.abs(f5) * 1.3,  # hair cracks subtler
        ])
        pattern = np.clip(1.0 - crack * 11.0, 0, 1)   # 7→11 = sharper edges
        # SPB-99 P2: per-shard chroma. Use voronoi-style cell-id from the
        # nearest crack center.
        shard_id = (np.floor((f1 + 1) * 4) * 53.0 + np.floor((f2 + 1) * 4) * 31.0
                    + np.floor((f4 + 1) * 3) * 17.0)
        shard_hash = np.sin(shard_id * 12.9898 + phase * 1.6) * 43758.5453
        shard_hash = (shard_hash - np.floor(shard_hash)).astype(np.float32)
        pattern = (pattern + (1.0 - pattern) * shard_hash * 0.45).astype(np.float32)
        accent = np.clip(pattern + _gg_ridge(f1 - f2, 2.0) * 0.25 + _gg_ridge(f5, 2.4) * 0.18, 0, 1)
        tint = (0.78, 0.96, 1.00)
    elif mode == "quilt":
        # SPB-100 tick 90: quilt too large (owner verdict). 9→45 freq = 5×
        # density both axes per SPB-99 P1. Buttons also scaled 18→90.
        q1 = np.sin((x * 45.0 + y * 45.0) * tw + phase)
        q2 = np.sin((x * 45.0 - y * 45.0) * tw - phase)
        puffs = (q1 * q2) * 0.5 + 0.5
        seam = np.clip(_gg_ridge(q1, 2.8) + _gg_ridge(q2, 2.8), 0, 1)
        button = _gg_ridge(np.sin(x * 90.0 * tw), 3.2) * _gg_ridge(np.sin(y * 90.0 * tw), 3.2)
        pattern = np.clip(puffs * 0.58 + seam * 0.28 + button * 0.42, 0, 1)
        # SPB-99 P2: per-puff chroma hash.
        puff_id = np.floor(x * 45.0) + np.floor(y * 45.0) * 19.0
        puff_hash = np.sin(puff_id * 12.9898 + phase * 1.2) * 43758.5453
        puff_hash = (puff_hash - np.floor(puff_hash)).astype(np.float32)
        pattern = (pattern * (0.66 + puff_hash * 0.68)).astype(np.float32)
        accent = np.clip(seam + button, 0, 1)
        tint = (0.76, 0.86, 0.98)
    else:
        pattern = micro
        accent = micro
        tint = (0.70, 0.92, 1.00)

    edge = np.clip(
        np.abs(np.diff(pattern, axis=1, prepend=pattern[:, :1]))
        + np.abs(np.diff(pattern, axis=0, prepend=pattern[:1, :])),
        0,
        1,
    )
    detail = np.clip(pattern * 0.58 + accent * 0.24 + micro * 0.18 + edge * 0.70, 0, 1).astype(np.float32)
    result = (pattern.astype(np.float32), detail, micro.astype(np.float32), edge.astype(np.float32), np.array(tint, dtype=np.float32))
    if len(_ghost_geometry_cache) > 1:
        _ghost_geometry_cache.pop(next(iter(_ghost_geometry_cache)))
    _ghost_geometry_cache[cache_key] = result
    return result


def _make_ghost_geometry_fast(mode, base_m, base_g, seed_offset=0):
    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        pattern, detail, micro, edge, _ = _gg_fields(shape, int(seed) + seed_offset, mode)
        smf = float(sm)
        M = np.clip(base_m + detail * 56.0 * smf + edge * 72.0 * smf, 0, 255)
        G = np.clip(base_g + (1.0 - detail) * 54.0 - edge * 18.0, 0, 255)
        B = np.clip(212.0 - pattern * 148.0 + edge * 46.0 + micro * 18.0, 16, 255)
        return _spec_out(shape, mask2, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        pattern, detail, micro, edge, tint = _gg_fields(shape, int(seed) + seed_offset, mode)
        source = np.asarray(paint[:, :, :3], dtype=np.float32)
        if source.max() > 1.5:
            source = source / 255.0
        strength = np.clip(mask2 * float(pm), 0, 1)
        ghost = np.clip((detail - 0.26) * 1.35, 0, 1)
        shadow = np.clip((0.36 - pattern) * 1.2, 0, 1)
        # SPB-PERF-2026-06-02 / owner 24-32s live render logs: the engine
        # already passes monolithic paint functions a private underpaint
        # snapshot. Reuse that owned buffer instead of making a second full
        # 2048x2048 RGB copy for Ghost Geometry paint.
        result = source
        # SPB-78: Ghost is spec_driven — paint must stay near-neutral so the
        # spec channel carries the angle-dependent structure. Cut paint-side
        # tint/shadow/edge ~3-4x vs. the pre-SPB-78 amplitudes.
        active = mask2 > 0.0
        active_ratio = float(np.mean(active)) if active.size else 0.0
        if active_ratio < 0.92:
            # SPB-PERF-2026-06-02 / owner 24-32s live render logs: ghost
            # paint is often a partial visible zone. Replay the exact blend
            # equation only on active pixels so hidden canvas does no work.
            if np.any(active):
                blend = ghost[active] * 0.060 * strength[active]
                result[active] = result[active] * (1.0 - blend[:, np.newaxis]) + tint.reshape(1, 3) * blend[:, np.newaxis]
                result[active] = np.clip(
                    result[active]
                    - shadow[active][:, np.newaxis] * 0.020 * strength[active][:, np.newaxis]
                    + edge[active][:, np.newaxis] * 0.025 * strength[active][:, np.newaxis],
                    0,
                    1,
                )
        else:
            blend = ghost * 0.060 * strength
            result = result * (1.0 - blend[:, :, np.newaxis]) + tint.reshape(1, 1, 3) * blend[:, :, np.newaxis]
            result = np.clip(result - shadow[:, :, np.newaxis] * 0.020 * strength[:, :, np.newaxis] + edge[:, :, np.newaxis] * 0.025 * strength[:, :, np.newaxis], 0, 1)
        return result

    return spec_fn, paint_fn


spec_ghost_hex, paint_ghost_hex = _make_ghost_geometry_fast("hex", 196, 42, 9100)
spec_ghost_stripes, paint_ghost_stripes = _make_ghost_geometry_fast("stripes", 236, 10, 9110)
spec_ghost_diamonds, paint_ghost_diamonds = _make_ghost_geometry_fast("diamonds", 202, 18, 9120)
spec_ghost_waves, paint_ghost_waves = _make_ghost_geometry_fast("waves", 108, 46, 9130)
spec_ghost_camo, paint_ghost_camo = _make_ghost_geometry_fast("camo", 188, 56, 9140)
spec_ghost_scales, paint_ghost_scales = _make_ghost_geometry_fast("scales", 220, 62, 9150)
spec_ghost_circuit, paint_ghost_circuit = _make_ghost_geometry_fast("circuit", 242, 8, 9160)
spec_ghost_vortex, paint_ghost_vortex = _make_ghost_geometry_fast("vortex", 230, 14, 9170)
spec_ghost_fracture, paint_ghost_fracture = _make_ghost_geometry_fast("fracture", 176, 76, 9180)
spec_ghost_quilt, paint_ghost_quilt = _make_ghost_geometry_fast("quilt", 210, 42, 9190)


# ================================================================
# PARADIGM 3: ANISOTROPIC ROUGHNESS - Directional grain simulation
# ================================================================

def _aniso_grain_field(shape, grain_fn_name, seed, seed_offset):
    """Generate anisotropic grain — TOP-DOWN REWRITE tick 93.

    SPB-100 (owner: "Directional Grain needs SIGNIFICANT work. Complete
    rewrite top down"). Previous implementation rendered grain at
    freq=12 over normalized [-1,1] coordinates, producing ~85-pixel-wide
    lines at 2048² — orders of magnitude too coarse for hairline metal.

    NEW ARCHITECTURE:
    - PIXEL-space coordinates so frequencies are absolute (we want
      hairlines at 1-3 pixels at car-body 2048², not at 85)
    - Triple-band grain: macro structure (~80px), mid bands (~18px),
      fine hairlines (~2-3px). All three ride on top of each other so
      the visible grain has macro-mid-fine character like real brushed
      metal — not just one frequency.
    - Per-ribbon chroma hash (SPB-99 P2 doctrine): each grain stroke
      inherits a different shade so spec channel reads as many-shade
      hairline metal instead of monochrome scribble.
    - Anisotropy stretch tightened 0.1 → 0.025 for sharper directional
      contrast (real brushed metal has near-zero across-grain
      variation).
    - Mode-specific geometries (radial, circular, spiral, etc.) now use
      car-scale frequencies and inherit the multi-band + chroma
      treatment.
    - Vectorized; render time stays in SPB-105 budget. Composite
      baseline 46.7 (tick 92) → ≥85 target.
    """
    h, w = shape
    rng = np.random.RandomState(seed + seed_offset)
    # Pixel-space coordinates for absolute frequency control.
    y_px = np.arange(h, dtype=np.float32).reshape(h, 1)
    x_px = np.arange(w, dtype=np.float32).reshape(1, w)
    # Centered + normalized for angular/radial modes
    cy, cx = (h - 1) * 0.5, (w - 1) * 0.5
    yc = (y_px - cy)
    xc = (x_px - cx)
    yn = yc / max(h, 1)
    xn = xc / max(w, 1)
    # Reference frequencies — picked so grain reads at car-body scale.
    # At 2048²: macro ~80px (=fender hairline group), mid ~18px (visible
    # brushstroke band), fine ~2.5px (true hairline).
    F_MACRO, F_MID, F_FINE = 80.0, 18.0, 2.6
    inv_macro = 2.0 * np.pi / F_MACRO
    inv_mid = 2.0 * np.pi / F_MID
    inv_fine = 2.0 * np.pi / F_FINE

    def _bands(theta, stretch=0.025, sd=0):
        """Triple-band anisotropic grain along direction theta.
        Returns 2D field with per-ribbon chroma already mixed in."""
        ct, st = float(np.cos(theta)), float(np.sin(theta))
        # u = along-grain coordinate (where ribbons run)
        # v = across-grain coordinate (where stripe pattern oscillates)
        u = xc * ct + yc * st
        v = (-xc * st + yc * ct) * stretch
        # 3-band grain. Each band is a sin wave across the v axis (across
        # grain) with along-grain noise modulation.
        n_macro = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], sd + 100)
        n_mid = _noise(shape, [128, 256], [0.5, 0.5], sd + 101)
        n_fine = _noise(shape, [512, 1024], [0.55, 0.45], sd + 102)
        macro = np.sin(v * inv_macro + n_macro * 2.6)
        mid = np.sin(v * inv_mid + n_mid * 1.5)
        fine = np.sin(v * inv_fine + n_fine * 0.6)
        # Combine: macro carries the body, mid + fine add hairline detail.
        primary = macro * 0.36 + mid * 0.32 + fine * 0.32
        # SPB-99 P2: per-ribbon chroma. Hash on quantized v (ribbon id).
        ribbon_id = np.floor(v * inv_mid).astype(np.float32)
        ribbon_hash = np.sin(ribbon_id * 12.9898 + (sd % 1000) * 0.011) * 43758.5453
        ribbon_hash = (ribbon_hash - np.floor(ribbon_hash)).astype(np.float32)
        primary = primary * (0.66 + ribbon_hash * 0.68)
        return primary

    if grain_fn_name == "horizontal":
        primary = _bands(0.0, 0.025, seed + seed_offset + 100)

    elif grain_fn_name == "vertical":
        primary = _bands(np.pi / 2, 0.025, seed + seed_offset + 100)

    elif grain_fn_name == "diagonal":
        primary = _bands(np.pi / 4, 0.025, seed + seed_offset + 100)

    elif grain_fn_name == "radial":
        # Grain radiates outward from center — use angle as v-axis,
        # distance as u-axis. Frequencies tuned for car-body scale.
        angle = np.arctan2(yn, xn)
        dist = np.sqrt(yn * yn + xn * xn)
        n_warp = _noise(shape, [32, 64], [0.5, 0.5], seed + seed_offset + 100)
        # Radial ribbons: ~140 ribbons around the full canvas
        radial_phase = angle * 70.0 + n_warp * 1.4
        ribbon = np.sin(radial_phase)
        fine_ribbon = np.sin(radial_phase * 3.4) * 0.45
        primary = (ribbon + fine_ribbon) * (0.5 + dist * 0.5)
        ribbon_id = np.floor(angle * 70.0 / np.pi).astype(np.float32)
        ribbon_hash = np.sin(ribbon_id * 12.9898 + (seed % 1000) * 0.011) * 43758.5453
        ribbon_hash = (ribbon_hash - np.floor(ribbon_hash)).astype(np.float32)
        primary = primary * (0.66 + ribbon_hash * 0.68)

    elif grain_fn_name == "circular":
        # Concentric rings — frequency increases with radius (real
        # circular brushed metal has tighter rings near the outside).
        dist_px = np.sqrt(yc * yc + xc * xc)
        n_warp = _noise(shape, [64, 128], [0.5, 0.5], seed + seed_offset + 100)
        # Ring spacing ~6 pixels at 2048² (matches real circular brushed
        # disc finish like watch case-back).
        ring_phase = dist_px * (2.0 * np.pi / 6.0) + n_warp * 1.6
        primary = np.sin(ring_phase) * 0.7 + np.sin(ring_phase * 3.1) * 0.25
        ring_id = np.floor(dist_px / 6.0).astype(np.float32)
        ring_hash = np.sin(ring_id * 12.9898 + (seed % 1000) * 0.011) * 43758.5453
        ring_hash = (ring_hash - np.floor(ring_hash)).astype(np.float32)
        primary = primary * (0.66 + ring_hash * 0.68)

    elif grain_fn_name == "crosshatch":
        # Two perpendicular grain layers — multiplicative blend produces
        # the cross-hatch character.
        g1 = _bands(np.pi / 6, 0.025, seed + seed_offset + 100)
        g2 = _bands(np.pi / 6 + np.pi / 2, 0.025, seed + seed_offset + 200)
        primary = (g1 * 0.5 + g2 * 0.5) + np.abs(g1 * g2) * 0.35

    elif grain_fn_name == "spiral":
        # Spiral grain — combines angular + radial frequency for the
        # characteristic galaxy-arm look (think turbine blades).
        angle = np.arctan2(yn, xn)
        dist_px = np.sqrt(yc * yc + xc * xc)
        n_warp = _noise(shape, [32, 64], [0.5, 0.5], seed + seed_offset + 100)
        spiral_phase = angle * 14.0 + dist_px * (2.0 * np.pi / 12.0) + n_warp * 1.4
        primary = np.sin(spiral_phase) * 0.65 + np.sin(spiral_phase * 3.0) * 0.25
        arm_id = np.floor(spiral_phase / (2 * np.pi)).astype(np.float32)
        arm_hash = np.sin(arm_id * 12.9898 + (seed % 1000) * 0.011) * 43758.5453
        arm_hash = (arm_hash - np.floor(arm_hash)).astype(np.float32)
        primary = primary * (0.66 + arm_hash * 0.68)

    elif grain_fn_name == "wave":
        # Wave grain — direction modulated by an underlying sine so
        # ribbons curve through the canvas like wood grain.
        wave_curve = np.sin(x_px * (2 * np.pi / 320.0)) * np.pi * 0.35
        # Variable-direction grain: angle wave_curve, projected onto v
        u = xc * np.cos(wave_curve) + yc * np.sin(wave_curve)
        v = (-xc * np.sin(wave_curve) + yc * np.cos(wave_curve)) * 0.025
        n_warp = _noise(shape, [128, 256], [0.5, 0.5], seed + seed_offset + 100)
        primary = (np.sin(v * inv_mid + n_warp * 1.2) * 0.55
                   + np.sin(v * inv_fine + n_warp * 0.3) * 0.35
                   + np.sin(v * inv_macro) * 0.20)
        ribbon_id = np.floor(v * inv_mid).astype(np.float32)
        ribbon_hash = np.sin(ribbon_id * 12.9898 + (seed % 1000) * 0.011) * 43758.5453
        ribbon_hash = (ribbon_hash - np.floor(ribbon_hash)).astype(np.float32)
        primary = primary * (0.66 + ribbon_hash * 0.68)

    elif grain_fn_name == "herringbone":
        # Alternating diagonal blocks — block height tuned for car-body
        # scale (~24px = visible band, not whole-fender size).
        block_h = max(16, h // 80)
        row_block = (np.floor(y_px / block_h).astype(np.int32) % 2)
        # Two diagonal grain orientations
        g_a = _bands(np.pi / 4, 0.025, seed + seed_offset + 100)
        g_b = _bands(-np.pi / 4, 0.025, seed + seed_offset + 200)
        primary = np.where(row_block == 0, g_a, g_b) * 0.85
        # Per-row chroma
        row_hash = np.sin(np.floor(y_px / block_h) * 12.9898 + (seed % 1000) * 0.011) * 43758.5453
        row_hash = (row_hash - np.floor(row_hash)).astype(np.float32)
        primary = primary * (0.78 + row_hash * 0.44)

    elif grain_fn_name == "turbulence":
        # Turbulent grain — chaotic direction, dense multi-band noise.
        # No single grain direction; the "grain" emerges from
        # constructive/destructive interference.
        n_macro = _noise(shape, [32, 64, 128], [0.30, 0.40, 0.30], seed + seed_offset + 100)
        n_mid = _noise(shape, [128, 256], [0.50, 0.50], seed + seed_offset + 200)
        n_fine = _noise(shape, [512, 1024], [0.55, 0.45], seed + seed_offset + 300)
        dir_flow = _noise(shape, [16, 32], [0.55, 0.45], seed + seed_offset + 400)
        # Each band rotated by dir_flow → creates turbulent grain
        v_macro = xc * np.cos(dir_flow * 3.0) + yc * np.sin(dir_flow * 3.0)
        v_mid = xc * np.cos(dir_flow * 5.0 + 1.5) + yc * np.sin(dir_flow * 5.0 + 1.5)
        macro = np.sin(v_macro * inv_macro + n_macro * 2.0) * 0.30
        mid = np.sin(v_mid * inv_mid + n_mid * 1.5) * 0.40
        fine = np.sin(v_macro * inv_fine + n_fine * 0.6) * 0.30
        primary = macro + mid + fine
        # Per-region chroma based on dir_flow regions
        region_id = np.floor(dir_flow * 4.0).astype(np.float32)
        region_hash = np.sin(region_id * 12.9898 + (seed % 1000) * 0.011) * 43758.5453
        region_hash = (region_hash - np.floor(region_hash)).astype(np.float32)
        primary = primary * (0.66 + region_hash * 0.68)

    else:
        primary = rng.randn(h, w).astype(np.float32) * 0.3

    # Secondary micro-grain — VERY high frequency (sub-pixel) for the
    # "tooth" of real brushed metal. SPB-99 P1 doctrine: this is what
    # makes the finish read as detail at car-body 2048².
    micro = _noise(shape, [1024, 2048], [0.55, 0.45], seed + seed_offset + 400)
    micro = micro * 0.5

    # Normalize primary to 0-1
    p_min, p_max = primary.min(), primary.max()
    if p_max - p_min > 1e-6:
        primary_norm = (primary - p_min) / (p_max - p_min)
    else:
        primary_norm = np.full_like(primary, 0.5)
    micro_norm = np.clip(micro * 0.5 + 0.5, 0, 1)

    return primary_norm.astype(np.float32), micro_norm.astype(np.float32)


@lru_cache(maxsize=96)
def _aniso_source_fields_cached(h, w, grain_fn_name, seed, seed_offset):
    shape = (int(h), int(w))
    grain, micro = _aniso_grain_field(shape, grain_fn_name, int(seed), int(seed_offset))
    y_i, x_i = _mgrid(shape)
    y = y_i.astype(np.float32)
    x = x_i.astype(np.float32)
    cy = (h - 1) * 0.5
    cx = (w - 1) * 0.5
    yy = (y - cy) / max(float(h), 1.0)
    xx = (x - cx) / max(float(w), 1.0)
    dist = np.sqrt(xx * xx + yy * yy)
    angle = np.arctan2(yy, xx)
    warp = _noise(shape, [6, 12, 24], [0.38, 0.34, 0.28], seed + seed_offset + 610)
    fine = (_noise(shape, [1, 2, 3, 5], [0.34, 0.30, 0.22, 0.14], seed + seed_offset + 620) + 1.0) * 0.5
    mist = (_noise(shape, [3, 6, 12], [0.40, 0.36, 0.24], seed + seed_offset + 630) + 1.0) * 0.5

    def _stripe(phase, width=0.035):
        return np.clip((width - np.abs(np.sin(phase))) / max(width, 1e-4), 0, 1)

    if grain_fn_name == "horizontal":
        scratch = _stripe(y * 2.55 + warp * 2.4, 0.042)
        motif = np.maximum(_stripe(x * 0.115 + np.sin(y * 0.018) * 0.9, 0.028), _stripe(y * 0.46 + warp * 1.3, 0.024)) * 0.56
    elif grain_fn_name == "vertical":
        scratch = _stripe(x * 2.65 + warp * 2.2, 0.042)
        motif = np.maximum(_stripe(y * 0.105 + np.sin(x * 0.016) * 0.9, 0.027), _stripe(x * 0.42 + warp * 1.1, 0.024)) * 0.58
    elif grain_fn_name == "diagonal":
        diag = (x + y) * 1.82
        scratch = _stripe(diag + warp * 2.6, 0.040)
        motif = np.maximum(_stripe((x + y) * 0.165 + np.sin((x - y) * 0.022) * 1.2, 0.026), _stripe((x - y) * 0.28 + warp, 0.022)) * 0.62
    elif grain_fn_name == "radial":
        scratch = _stripe(angle * 38.0 + warp * 1.4, 0.046)
        motif = np.maximum(_stripe(dist * 760.0 + angle * 4.0, 0.030), _stripe(angle * 18.0 + dist * 90.0, 0.026)) * 0.66
    elif grain_fn_name == "circular":
        scratch = _stripe(dist * 900.0 + warp * 1.8, 0.045)
        motif = np.maximum(_stripe(dist * 430.0 + angle * 12.0, 0.030), _stripe(angle * 26.0 + warp * 0.7, 0.024)) * 0.66
    elif grain_fn_name == "crosshatch":
        a = _stripe((x * 1.34 + y * 0.74) + warp * 1.8, 0.036)
        b = _stripe((x * -0.66 + y * 1.42) - warp * 1.6, 0.034)
        scratch = np.maximum(a, b)
        motif = (a * b * 0.72 + np.maximum(_stripe(x * 0.28, 0.020), _stripe(y * 0.31, 0.020)) * 0.24)
    elif grain_fn_name == "spiral":
        spiral = angle * 7.0 + dist * 54.0
        scratch = _stripe(spiral * 8.8 + warp * 1.4, 0.040)
        motif = np.maximum(_stripe(spiral * 2.2, 0.030), _stripe(dist * 520.0 + angle * 18.0, 0.026)) * 0.70
    elif grain_fn_name == "wave":
        phase = y * 1.05 + np.sin(x * 0.025 + warp * 1.3) * 21.0
        scratch = _stripe(phase, 0.043)
        motif = np.maximum(_stripe(phase * 0.28 + np.sin(x * 0.035) * 1.6, 0.030), _stripe(dist * 500.0 + np.sin(angle * 5.0), 0.025)) * 0.66
    elif grain_fn_name == "herringbone":
        block = max(10.0, h / 56.0)
        row = np.floor(y / block).astype(np.int32)
        local = (y % block) / block
        phase = np.where((row % 2) == 0, x * 1.45 + y * 1.05, -x * 1.45 + y * 1.05)
        scratch = _stripe(phase + warp * 1.9, 0.040)
        seam = np.clip(1.0 - np.minimum(local, 1.0 - local) * 18.0, 0, 1)
        motif = np.maximum(seam * 0.55, _stripe(phase * 0.28, 0.023)) * 0.68
    elif grain_fn_name == "turbulence":
        flow = _noise(shape, [4, 8, 16, 32], [0.20, 0.30, 0.30, 0.20], seed + seed_offset + 640)
        scratch = _stripe((x * np.sin(flow * 2.4) + y * np.cos(flow * 2.4)) * 1.10 + warp * 1.7, 0.040)
        motif = np.maximum(_stripe(flow * 10.0 + dist * 220.0, 0.026), _stripe(angle * 16.0 + flow * 5.0, 0.022)) * 0.66
    else:
        scratch = np.clip(fine * 0.8 + mist * 0.2, 0, 1)
        motif = np.clip(scratch * 0.55, 0, 1)

    edge = np.clip(
        np.abs(grain - np.roll(grain, 1, axis=0))
        + np.abs(grain - np.roll(grain, 1, axis=1))
        + np.abs(scratch - np.roll(scratch, 1, axis=0)) * 0.55,
        0,
        1,
    )
    flake = np.clip((fine - 0.58) * 3.8 + scratch * 0.50 + edge * 1.6, 0, 1)
    satin = np.clip((0.68 - grain) * 1.25 + (1.0 - mist) * 0.34, 0, 1)
    return (
        grain.astype(np.float32),
        micro.astype(np.float32),
        fine.astype(np.float32),
        scratch.astype(np.float32),
        edge.astype(np.float32),
        motif.astype(np.float32),
        flake.astype(np.float32),
        satin.astype(np.float32),
    )


def _aniso_source_fields(shape, grain_fn_name, seed, seed_offset):
    h, w = shape[:2]
    return _aniso_source_fields_cached(int(h), int(w), str(grain_fn_name), int(seed), int(seed_offset))


def _aniso_recipe(grain_fn_name):
    return {
        "horizontal": {
            "cool": (0.58, 0.62, 0.66), "warm": (0.92, 0.94, 0.90),
            "m": (188.0, 62.0), "r": (30.0, 118.0), "cc": (58.0, 142.0), "paint_gain": 0.19,
        },
        "vertical": {
            "cool": (0.60, 0.68, 0.96), "warm": (0.98, 0.82, 0.98),
            "m": (62.0, 92.0), "r": (66.0, 122.0), "cc": (108.0, 120.0), "paint_gain": 0.24,
        },
        "diagonal": {
            "cool": (0.08, 0.18, 0.44), "warm": (0.98, 0.18, 0.34),
            "m": (118.0, 116.0), "r": (38.0, 120.0), "cc": (88.0, 142.0), "paint_gain": 0.31,
        },
        "radial": {
            "cool": (0.20, 0.30, 0.44), "warm": (1.00, 0.55, 0.26),
            "m": (126.0, 118.0), "r": (38.0, 132.0), "cc": (74.0, 132.0), "paint_gain": 0.27,
        },
        "circular": {
            "cool": (0.46, 0.50, 0.56), "warm": (0.92, 0.96, 0.98),
            "m": (188.0, 66.0), "r": (22.0, 128.0), "cc": (52.0, 148.0), "paint_gain": 0.18,
        },
        "crosshatch": {
            "cool": (0.30, 0.34, 0.38), "warm": (0.78, 0.76, 0.68),
            "m": (150.0, 108.0), "r": (46.0, 146.0), "cc": (46.0, 118.0), "paint_gain": 0.22,
        },
        "spiral": {
            "cool": (0.34, 0.50, 0.64), "warm": (0.94, 0.98, 1.00),
            "m": (186.0, 68.0), "r": (24.0, 130.0), "cc": (74.0, 142.0), "paint_gain": 0.22,
        },
        "wave": {
            "cool": (0.24, 0.40, 0.58), "warm": (0.96, 0.55, 0.30),
            "m": (112.0, 116.0), "r": (52.0, 132.0), "cc": (74.0, 132.0), "paint_gain": 0.27,
        },
        "herringbone": {
            "cool": (0.34, 0.24, 0.10), "warm": (1.00, 0.74, 0.20),
            "m": (132.0, 122.0), "r": (34.0, 138.0), "cc": (70.0, 128.0), "paint_gain": 0.29,
        },
        "turbulence": {
            "cool": (0.16, 0.20, 0.24), "warm": (0.94, 0.52, 0.24),
            "m": (118.0, 126.0), "r": (46.0, 142.0), "cc": (62.0, 134.0), "paint_gain": 0.30,
        },
    }.get(grain_fn_name, {
        "cool": (0.30, 0.34, 0.38), "warm": (0.86, 0.72, 0.44),
        "m": (140.0, 100.0), "r": (44.0, 130.0), "cc": (66.0, 120.0), "paint_gain": 0.24,
    })


def _make_aniso_fusion(base_m, base_g, base_cc, grain_fn_name, seed_offset=0):
    """Factory: source-owned directional grain with per-finish material recipes."""

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        grain, micro, fine, scratch, edge, motif, flake, satin = _aniso_source_fields(shape, grain_fn_name, seed, seed_offset)
        recipe = _aniso_recipe(grain_fn_name)
        m_base, m_span = recipe["m"]
        r_base, r_span = recipe["r"]
        cc_base, cc_span = recipe["cc"]
        polish = np.clip(grain * 0.52 + scratch * 0.28 + fine * 0.14 + edge * 1.35, 0, 1)
        hidden = np.clip(motif * (0.48 + fine * 0.42) + edge * 0.55, 0, 1)
        M = m_base + polish * m_span + flake * 52.0 + hidden * 46.0 + (micro - 0.5) * 42.0
        G = r_base + satin * r_span - scratch * 36.0 - hidden * 24.0 + (1.0 - fine) * 18.0
        B = cc_base + np.clip(scratch * 0.48 + hidden * 0.72 + flake * 0.36, 0, 1) * cc_span + edge * 42.0
        if grain_fn_name in ("vertical", "diagonal", "wave"):
            M = M - satin * 36.0
            G = G + satin * 26.0
        if grain_fn_name in ("horizontal", "circular", "spiral"):
            M = M + scratch * 30.0
            G = G - hidden * 18.0

        return _spec_out(shape, mask2, M * float(sm), G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        source = np.asarray(paint[:, :, :3], dtype=np.float32)
        if source.max() > 1.5:
            source = source / 255.0
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        active = np.clip(mask2 * float(pm), 0, 1)[:, :, np.newaxis]
        bb3 = bb[:, :, np.newaxis] if hasattr(bb, "ndim") and bb.ndim == 2 else bb
        grain, micro, fine, scratch, edge, motif, flake, satin = _aniso_source_fields(shape, grain_fn_name, seed, seed_offset)
        recipe = _aniso_recipe(grain_fn_name)
        cool = np.asarray(recipe["cool"], dtype=np.float32).reshape(1, 1, 3)
        warm = np.asarray(recipe["warm"], dtype=np.float32).reshape(1, 1, 3)
        carrier = np.clip(grain * 0.52 + scratch * 0.20 + fine * 0.16 + motif * 0.12, 0, 1)
        tint = cool * (1.0 - carrier[:, :, np.newaxis]) + warm * carrier[:, :, np.newaxis]
        micro_cut = ((fine - 0.5) * 0.090 + (micro - 0.5) * 0.080 + scratch * 0.105 + edge * 0.190 - satin * 0.030)
        luma = micro_cut[:, :, np.newaxis]
        color = (tint - 0.5) * float(recipe["paint_gain"])
        if grain_fn_name in ("horizontal", "circular", "spiral"):
            color *= 0.78
        if grain_fn_name == "crosshatch":
            luma -= satin[:, :, np.newaxis] * 0.030
        if grain_fn_name == "vertical":
            color += np.stack([fine * 0.018, motif * 0.018, scratch * 0.026], axis=2)
        if grain_fn_name == "diagonal":
            color += np.stack([scratch * 0.040, -satin * 0.010, grain * 0.024], axis=2)
        if grain_fn_name == "wave":
            color += np.stack([motif * 0.036, edge * 0.020, fine * 0.018], axis=2)
        result = np.clip(source + (color + luma) * active, 0, 1)
        spark_rgb = np.stack([
            flake * 0.070 + motif * 0.020,
            flake * 0.052 + scratch * 0.018,
            flake * 0.045 + fine * 0.020,
        ], axis=2)
        result = np.clip(result + spark_rgb * active, 0, 1)
        result = np.clip(result + np.asarray(bb3, dtype=np.float32) * 0.20 * active, 0, 1)
        return result.astype(np.float32)
    return spec_fn, paint_fn

spec_aniso_horizontal_chrome, paint_aniso_horizontal_chrome = _make_aniso_fusion(255, 5, 16, "horizontal", 7200)
spec_aniso_vertical_pearl, paint_aniso_vertical_pearl = _make_aniso_fusion(100, 30, 16, "vertical", 7210)
spec_aniso_diagonal_candy, paint_aniso_diagonal_candy = _make_aniso_fusion(200, 15, 16, "diagonal", 7220)
spec_aniso_radial_metallic, paint_aniso_radial_metallic = _make_aniso_fusion(200, 40, 16, "radial", 7230)
spec_aniso_circular_chrome, paint_aniso_circular_chrome = _make_aniso_fusion(255, 3, 16, "circular", 7240)
spec_aniso_crosshatch_steel, paint_aniso_crosshatch_steel = _make_aniso_fusion(245, 6, 60, "crosshatch", 7250)
spec_aniso_spiral_mercury, paint_aniso_spiral_mercury = _make_aniso_fusion(255, 3, 16, "spiral", 7260)
spec_aniso_wave_titanium, paint_aniso_wave_titanium = _make_aniso_fusion(180, 60, 80, "wave", 7270)
spec_aniso_herringbone_gold, paint_aniso_herringbone_gold = _make_aniso_fusion(240, 12, 16, "herringbone", 7280)
spec_aniso_turbulence_metal, paint_aniso_turbulence_metal = _make_aniso_fusion(220, 35, 16, "turbulence", 7290)



# ================================================================
# PARADIGM 4: REACTIVE METALLIC ZONES - Fresnel-differentiated panels
# ================================================================

def _make_reactive_fusion(m_low, m_high, base_g, base_cc, seed_offset=0):
    """Factory: domain-warped Voronoi reactive zones with chrome seam boundaries.
    Zone A gets m_high material, Zone B gets m_low material.
    Chrome seams at Voronoi cell boundaries (F2-F1 edge detection)."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_reactive_fusion(m_low, m_high, base_g, base_cc, seed_offset))

    def _reactive_voronoi(shape, seed):
        """Compute domain-warped Voronoi with 30 points, returning zone_mask and edge field."""
        h, w = shape
        # Domain warp coordinates for organic cell shapes
        warp_y = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 80)
        warp_x = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 90)
        warp_amp = max(h, w) * 0.08
        y_g, x_g = _mgrid(shape)
        yf = y_g.astype(np.float32) + warp_y * warp_amp
        xf = x_g.astype(np.float32) + warp_x * warp_amp
        # Generate 30 Voronoi seed points
        rng = np.random.RandomState(seed + seed_offset + 100)
        n_pts = 30
        pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
        pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
        d1 = np.full((h, w), 1e9, dtype=np.float32)
        d2 = np.full((h, w), 1e9, dtype=np.float32)
        cell_id = np.zeros((h, w), dtype=np.int32)
        for idx, (py, px) in enumerate(zip(pts_y, pts_x)):
            d = np.sqrt((yf - py)**2 + (xf - px)**2)
            closer = d < d1
            d2 = np.where(closer, d1, np.where(d < d2, d, d2))
            cell_id = np.where(closer, idx, cell_id)
            d1 = np.minimum(d1, d)
        # F2-F1 edge detection: thin at cell boundaries
        edge_field = d2 - d1
        # Zone assignment: odd cell IDs = Zone A (high), even = Zone B (low)
        zone_mask = (cell_id % 2).astype(np.float32)
        return zone_mask, edge_field, cell_id

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        # --- Resolution cap: compute at 512 max, upscale ---
        ds = max(1, min(h, w) // 1024)
        sh, sw = max(64, h // ds), max(64, w // ds)
        zone_mask, edge_field, cell_id = _reactive_voronoi((sh, sw), seed)
        # Chrome seam at cell boundaries (M=255, R=0)
        seam_width = max(sh, sw) * 0.012
        seam = np.clip(1.0 - edge_field / seam_width, 0, 1) ** 2.0
        # Zone materials
        M_zone = m_low * (1 - zone_mask) + m_high * zone_mask
        # Per-zone micro-texture with different seeds per zone
        micro_a = _noise((sh, sw), [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 50)
        micro_b = _noise((sh, sw), [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 60)
        micro = micro_a * zone_mask + micro_b * (1 - zone_mask)
        M_zone = M_zone + micro * 12 * sm
        # Roughness: high-M zones smooth, low-M zones rough
        G_high = np.clip(float(base_g) - 8, 2, 255)
        G_low = np.clip(float(base_g) + 45, 0, 255)
        G_zone = G_low * (1 - zone_mask) + G_high * zone_mask + micro * 8 * sm
        # CC: metallic zones glossy, matte zones hazed
        B_zone = np.clip(float(base_cc) + (1 - zone_mask) * 40 * sm - zone_mask * 8, 16, 255)
        # Seam overrides: chrome seam = full metallic, zero roughness
        M = M_zone * (1 - seam) + 255.0 * seam
        G = G_zone * (1 - seam) + 0.0 * seam
        B = B_zone * (1 - seam) + float(base_cc) * seam
        # Boundary roughness spike just outside seam
        boundary_halo = np.clip(1.0 - edge_field / (seam_width * 3), 0, 1) * (1 - seam)
        G = G + boundary_halo * 25 * sm
        mask_s = cv2.resize(mask.astype(np.float32), (sw, sh), interpolation=cv2.INTER_LINEAR) if ds > 1 else mask
        spec_small = _spec_out((sh, sw), mask_s, M, G, B)
        if ds > 1:
            spec = np.zeros((h, w, 4), dtype=np.uint8)
            for ch in range(4):
                spec[:, :, ch] = cv2.resize(spec_small[:, :, ch].astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.uint8)
            return spec
        return spec_small

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape
        # --- Resolution cap: compute reactive voronoi at 512 max, upscale ---
        ds = max(1, min(h, w) // 1024)
        sh, sw = max(64, h // ds), max(64, w // ds)
        zone_mask_s, edge_field_s, cell_id_s = _reactive_voronoi((sh, sw), seed)
        zone_mask = cv2.resize(zone_mask_s, (w, h), interpolation=cv2.INTER_LINEAR) if ds > 1 else zone_mask_s
        edge_field = cv2.resize(edge_field_s, (w, h), interpolation=cv2.INTER_LINEAR) if ds > 1 else edge_field_s
        result = paint.copy()
        # Chrome seam brightening
        seam_width = max(h, w) * 0.012
        seam = np.clip(1.0 - edge_field / seam_width, 0, 1) ** 2.0
        seam_bright = seam * 0.30 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + seam_bright * mask, 0, 1)
        # HIGH metallic zone: mirror brightening
        hi_boost = zone_mask * 0.22 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + hi_boost * mask * (1 - seam), 0, 1)
        # LOW metallic zone: matte warmth darkening
        lo_dark = (1 - zone_mask) * 0.10 * pm * (1 - seam)
        result[:,:,0] = np.clip(result[:,:,0] - lo_dark * 0.3 * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] - lo_dark * 0.4 * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] - lo_dark * 0.7 * mask, 0, 1)
        result = np.clip(result + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return result
    return spec_fn, paint_fn

spec_reactive_stealth_pop, paint_reactive_stealth_pop = _make_reactive_fusion(30, 220, 30, 16, 7300)
spec_reactive_pearl_flash, paint_reactive_pearl_flash = _make_reactive_fusion(60, 200, 40, 16, 7310)
spec_reactive_candy_reveal, paint_reactive_candy_reveal = _make_reactive_fusion(100, 240, 15, 16, 7320)
spec_reactive_chrome_fade, paint_reactive_chrome_fade = _make_reactive_fusion(150, 255, 5, 16, 7330)
spec_reactive_matte_shine, paint_reactive_matte_shine = _make_reactive_fusion(0, 180, 60, 16, 7340)
spec_reactive_dual_tone, paint_reactive_dual_tone = _make_reactive_fusion(80, 200, 80, 16, 7350)
spec_reactive_ghost_metal, paint_reactive_ghost_metal = _make_reactive_fusion(40, 240, 20, 16, 7360)
spec_reactive_mirror_shadow, paint_reactive_mirror_shadow = _make_reactive_fusion(200, 255, 3, 16, 7370)
spec_reactive_warm_cold, paint_reactive_warm_cold = _make_reactive_fusion(60, 165, 85, 16, 7380)  # LAZY-FUSIONS-005 FIX: G=85→G_high=77/G_low=130 (satin-warm vs rough-cold); m_high=165 (not 220 near pearl_flash=200)
spec_reactive_pulse_metal, paint_reactive_pulse_metal = _make_reactive_fusion(20, 250, 25, 16, 7390)


# ================================================================
_reactive_panel_field_cache = {}


def _rp_fields(shape, seed, mode):
    cache_key = (shape, int(seed), mode)
    cached = _reactive_panel_field_cache.get(cache_key)
    if cached is not None:
        return cached

    # SPB-100 tick 94 top-down rewrite (owner: "Reactive Panels need
    # SIGNIFICANT work"). Doubled the body+grain noise frequencies, added a
    # per-zone chroma hash so every reactive region pumps a different
    # spec shade. Macro zone frequencies stay low (zones are large by
    # design) but the micro layer is now genuinely at car-body scale.
    x, y = _lw_xy(shape)
    phase = (int(seed) % 4096) * 0.001534 * np.pi
    tw = np.float32(np.pi * 2.0)
    warp = np.sin((x * 2.7 + y * 3.1) * tw + phase) * 0.035
    jitter = np.sin((x * 11.0 - y * 9.0) * tw + phase * 1.7) * 0.014
    # Tick-94 doubled fine + grain band frequencies for genuine micro
    # detail at car-body 2048².
    n_fine = (_noise(shape, [1, 2, 3, 5], [0.34, 0.30, 0.22, 0.14], seed + 1201 + len(mode)) + 1.0) * 0.5
    n_grain = (_noise(shape, [5, 11, 21, 41], [0.30, 0.28, 0.24, 0.18], seed + 1217 + len(mode)) + 1.0) * 0.5
    n_body = (_noise(shape, [21, 41, 83, 167], [0.28, 0.28, 0.24, 0.20], seed + 1231 + len(mode)) + 1.0) * 0.5
    # Bumped hairline frequencies 93/107 → 220/240 (car-scale hairlines).
    micro_lines_a = _lw_ridge(np.sin((x * 220.0 + y * 38.0 + n_body * 1.8) * tw + phase), 3.2)
    micro_lines_b = _lw_ridge(np.sin((-x * 48.0 + y * 240.0 + n_grain * 1.6) * tw - phase * 0.7), 3.0)
    hairline = np.clip(micro_lines_a * 0.40 + micro_lines_b * 0.34 + np.clip((n_fine - 0.66) * 3.2, 0, 1) * 0.46, 0, 1)

    if mode == "stealth_pop":
        field = np.sin((x * 5.4 + y * 2.1 + n_body * 0.72) * tw + phase) * 0.52 + np.sin((x * -2.0 + y * 6.8 + n_grain * 0.50) * tw) * 0.34 + n_body * 0.38
        zone = np.clip(field * 0.42 + 0.52, 0.0, 1.0)
        accent = np.clip(_lw_ridge(np.sin((x * 37.0 + y * 9.0 + n_fine) * tw + phase), 2.2) + hairline * 0.42, 0, 1)
    elif mode == "pearl_flash":
        u = x * 5.2 + np.sin(y * tw * 2.0 + phase) * 0.12
        v = y * 6.4 + np.sin(x * tw * 1.6) * 0.10
        pearl = np.sin((u + n_body * 0.36) * tw) * 0.40 + np.cos((v - n_grain * 0.28) * tw) * 0.34 + np.sin((x - y) * tw * 14.0 + phase) * 0.13
        zone = np.clip(pearl * 0.50 + 0.52, 0.0, 1.0)
        accent = np.clip(_lw_ridge(np.sin((u + v + n_body * 0.25) * tw * 3.9), 1.95) + hairline * 0.35, 0, 1)
    elif mode == "candy_reveal":
        diag = x * 0.92 + y * 1.18 + warp * 2.0
        torn = np.sin((diag + n_body * 0.24) * tw * 7.8 + phase) + np.sin((x * 19.0 - y * 3.0) * tw + n_grain) * 0.22
        zone = np.clip(torn * 0.40 + 0.55, 0.0, 1.0)
        accent = np.clip(_lw_ridge(np.sin(diag * tw * 22.0 + y * 7.0 + n_fine), 2.25) + hairline * 0.36, 0, 1)
    elif mode == "chrome_fade":
        u, v = x * 9.0 + warp, y * 3.8
        fade = np.clip((x - 0.14) * 1.25, 0.0, 1.0)
        zone = np.clip((np.sin((u + n_body * 0.18) * tw + phase) * 0.5 + 0.5) * 0.38 + fade * 0.64 + n_grain * 0.12, 0.0, 1.0)
        accent = np.clip(_lw_ridge(np.sin((u * 3.4 + v * 1.2 + n_fine * 0.5) * tw), 2.1) + hairline * 0.30, 0, 1)
    elif mode == "matte_shine":
        u = x * 5.8 + y * 1.7 + warp * 2.0
        v = y * 6.6 - x * 1.2 + jitter * 2.0
        brushed = np.sin((u + n_body * 0.26) * tw) * 0.42 + np.sin(v * tw + np.sin(x * tw * 2.0) * 0.9) * 0.32 + n_grain * 0.32
        zone = np.clip(brushed * 0.48 + 0.50, 0.0, 1.0)
        accent = np.clip(_lw_ridge(np.sin((x * 41.0 - y * 29.0 + n_fine * 0.35) * tw + phase), 2.25) * (0.52 + zone * 0.48) + hairline * 0.28, 0, 1)
    elif mode == "dual_tone":
        split = np.sin((x * 4.0 - y * 3.6 + n_body * 0.42) * tw + phase) + np.sin((x + y) * tw * 13.0) * 0.18
        zone = np.clip(split * 0.43 + 0.52, 0.0, 1.0)
        accent = np.clip(_lw_ridge(split, 2.25) + hairline * 0.36, 0, 1)
    elif mode == "ghost_metal":
        p1 = x * 7.2 + y * 1.8 + np.sin(y * tw * 3.0) * 0.06
        p2 = -x * 2.8 + y * 6.4 + np.sin(x * tw * 2.5) * 0.07
        p3 = x * 4.4 - y * 5.1
        ghost = np.sin((p1 + n_body * 0.32) * tw) * 0.42 + np.sin((p2 - n_grain * 0.24) * tw) * 0.38 + np.sin(p3 * tw + phase) * 0.20
        zone = np.clip(ghost * 0.5 + 0.5, 0.0, 1.0)
        accent = np.clip(_lw_ridge(np.sin((p1 - p2 + n_fine * 0.20) * tw * 2.7), 2.0) + hairline * 0.24, 0, 1)
    elif mode == "mirror_shadow":
        diag = x * 0.55 + y * 1.35
        mirror = np.cos((diag + n_body * 0.22) * tw * 6.8 + phase) * 0.5 + 0.5
        zone = np.clip(mirror ** 1.65 + n_grain * 0.10, 0.0, 1.0)
        accent = np.clip(_lw_ridge(np.sin((x * 34.0 + y * 52.0 + n_fine * 0.4) * tw + phase), 2.25) + hairline * 0.34, 0, 1)
    elif mode == "warm_cold":
        u = x * 4.6 + np.sin(y * tw * 2.7 + phase) * 0.18
        thermal = np.sin((u + n_body * 0.38) * tw + y * 2.0) + np.cos((x - y) * tw * 9.0 + n_grain) * 0.22
        zone = np.clip(thermal * 0.42 + 0.52, 0.0, 1.0)
        accent = np.clip(_lw_ridge(np.cos((x + y + n_fine * 0.16) * tw * 17.5 + phase), 2.1) + hairline * 0.34, 0, 1)
    elif mode == "pulse_metal":
        d1 = np.sqrt((x - 0.28) ** 2 + (y - 0.42) ** 2)
        d2 = np.sqrt((x - 0.72) ** 2 + (y - 0.58) ** 2)
        pulse = np.sin((d1 * 19.0 + d2 * 13.0 + n_body * 0.28) * tw + phase)
        zone = np.clip(pulse * 0.46 + 0.54, 0.0, 1.0)
        accent = np.clip(_lw_ridge(pulse, 2.55) + hairline * 0.40, 0, 1)
    else:
        field = np.sin((x * 6.0 + y * 4.0 + n_body * 0.4) * tw)
        zone = np.clip(field * 0.45 + 0.52, 0.0, 1.0)
        accent = np.clip(_lw_ridge(field, 2.0) + hairline * 0.35, 0, 1)

    edge = np.clip(
        np.abs(np.diff(zone, axis=1, prepend=zone[:, :1])) + np.abs(np.diff(zone, axis=0, prepend=zone[:1, :])),
        0.0,
        1.0,
    )
    seam = np.clip(edge * 4.4 + hairline * 0.74 + accent * 0.16, 0.0, 1.0)
    micro = np.clip(n_fine * 0.42 + n_grain * 0.28 + hairline * 0.30, 0.0, 1.0)
    # SPB-99 P2 tick-94: per-zone chroma hash. Quantize zone into 8 bands and
    # hash each → reactive regions read as many-shade thermal map instead of
    # a smooth grey-to-warm gradient. Each band gets a different M/G/B push.
    zone_band = np.floor(zone * 8.0).astype(np.float32)
    zone_chroma_raw = np.sin(zone_band * 12.9898 + (seed % 1000) * 0.011) * 43758.5453
    zone_chroma = (zone_chroma_raw - np.floor(zone_chroma_raw)).astype(np.float32)
    glint = np.clip((micro - 0.56) * 4.2 + accent * 0.72 + seam * 0.42 + np.clip((n_fine - 0.83) * 8.0, 0, 1) * 0.65, 0.0, 1.0)
    glint = (glint * (0.66 + zone_chroma * 0.68)).astype(np.float32)
    result = (
        zone.astype(np.float32),
        seam.astype(np.float32),
        accent.astype(np.float32),
        micro.astype(np.float32),
        glint.astype(np.float32),
    )
    if len(_reactive_panel_field_cache) > 12:
        _reactive_panel_field_cache.pop(next(iter(_reactive_panel_field_cache)))
    _reactive_panel_field_cache[cache_key] = result
    return result


def _make_reactive_panel_fast(mode, cool, warm, accent_color, m_low, m_high, rough, clearcoat, seed_offset=0):
    cool = np.asarray(cool, dtype=np.float32)
    warm = np.asarray(warm, dtype=np.float32)
    accent_color = np.asarray(accent_color, dtype=np.float32)

    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        zone, seam, accent, micro, glint = _rp_fields(shape, int(seed) + seed_offset, mode)
        smf = float(sm)
        M_zone = float(m_low) * (1.0 - zone) + float(m_high) * zone
        M = M_zone + (glint * 104.0 + accent * 42.0 + micro * 18.0) * smf
        G_zone = float(rough) + (1.0 - zone) * 42.0 - zone * 16.0
        G = G_zone + micro * 28.0 * smf - glint * 44.0 * smf - seam * 34.0 * smf
        B = float(clearcoat) + zone * 48.0 * smf + accent * 76.0 * smf + glint * 112.0 * smf + seam * 54.0
        M = np.clip(M * (1.0 - seam * 0.45) + 255.0 * seam * 0.90, 0, 255)
        return _spec_out(shape, mask2, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        bb_arr = np.asarray(bb, dtype=np.float32)
        if bb_arr.ndim == 2:
            bb_arr = bb_arr[:, :, np.newaxis]
        if paint.ndim == 3 and paint.shape[2] > 3:
            base = paint[:, :, :3].astype(np.float32, copy=True)
        else:
            base = paint.astype(np.float32, copy=True)
        zone, seam, accent, micro, glint = _rp_fields(shape, int(seed) + seed_offset, mode)
        color = cool.reshape(1, 1, 3) * (1.0 - zone[:, :, np.newaxis]) + warm.reshape(1, 1, 3) * zone[:, :, np.newaxis]
        color = np.clip(color + accent_color.reshape(1, 1, 3) * np.clip(accent * 0.40 + glint * 0.36 + seam * 0.42, 0, 1)[:, :, np.newaxis], 0, 1)
        luma = (micro - 0.5) * 0.12 + glint * 0.16 + seam * 0.22
        target = np.clip(color + luma[:, :, np.newaxis], 0, 1)
        blend = np.clip((0.66 + glint * 0.16 + seam * 0.16) * float(pm), 0.0, 0.92)[:, :, np.newaxis] * mask2[:, :, np.newaxis]
        result = base * (1.0 - blend) + target * blend
        result = np.clip(result + bb_arr * 0.22 * mask2[:, :, np.newaxis], 0.0, 1.0)
        return result.astype(np.float32)

    return spec_fn, paint_fn


spec_reactive_stealth_pop, paint_reactive_stealth_pop = _make_reactive_panel_fast("stealth_pop", (0.015, 0.018, 0.022), (0.03, 0.55, 0.62), (0.12, 1.00, 0.95), 34, 226, 42, 88, 9300)
spec_reactive_pearl_flash, paint_reactive_pearl_flash = _make_reactive_panel_fast("pearl_flash", (0.58, 0.66, 0.86), (0.98, 0.76, 0.96), (1.00, 1.00, 0.88), 74, 206, 50, 118, 9310)
spec_reactive_candy_reveal, paint_reactive_candy_reveal = _make_reactive_panel_fast("candy_reveal", (0.08, 0.10, 0.20), (0.95, 0.08, 0.24), (1.00, 0.62, 0.18), 112, 238, 34, 100, 9320)
spec_reactive_chrome_fade, paint_reactive_chrome_fade = _make_reactive_panel_fast("chrome_fade", (0.22, 0.26, 0.30), (0.82, 0.88, 0.92), (0.92, 1.00, 1.00), 150, 252, 22, 112, 9330)
spec_reactive_matte_shine, paint_reactive_matte_shine = _make_reactive_panel_fast("matte_shine", (0.04, 0.04, 0.04), (0.86, 0.76, 0.52), (1.00, 0.86, 0.28), 22, 190, 72, 88, 9340)
spec_reactive_dual_tone, paint_reactive_dual_tone = _make_reactive_panel_fast("dual_tone", (0.02, 0.24, 0.82), (0.94, 0.32, 0.05), (0.88, 1.00, 0.30), 86, 212, 62, 94, 9350)
spec_reactive_ghost_metal, paint_reactive_ghost_metal = _make_reactive_panel_fast("ghost_metal", (0.16, 0.19, 0.22), (0.72, 0.78, 0.78), (0.80, 0.94, 1.00), 48, 236, 38, 120, 9360)
spec_reactive_mirror_shadow, paint_reactive_mirror_shadow = _make_reactive_panel_fast("mirror_shadow", (0.00, 0.00, 0.02), (0.74, 0.82, 0.90), (0.55, 0.95, 1.00), 196, 255, 18, 118, 9370)
spec_reactive_warm_cold, paint_reactive_warm_cold = _make_reactive_panel_fast("warm_cold", (0.04, 0.40, 0.92), (1.00, 0.28, 0.04), (0.96, 1.00, 0.24), 68, 178, 76, 98, 9380)
spec_reactive_pulse_metal, paint_reactive_pulse_metal = _make_reactive_panel_fast("pulse_metal", (0.12, 0.22, 0.34), (0.96, 0.48, 0.15), (1.00, 0.94, 0.46), 28, 248, 36, 110, 9390)


# PARADIGM 5: SPARKLE SYSTEMS - Multi-Scale Metallic Sparkle
# ================================================================

def _make_sparkle_fusion(flake_style, base_m, base_r, seed_offset=0):
    """Factory: Multi-scale metallic flake simulation using noise (fast).
    Large (32-64px zone shapes), medium (8-16px detail), micro (1-2px sparkle).
    Each scale drives M/R independently with sharp flake-edge transitions."""

    # Flake style controls noise octaves and thresholds
    if flake_style == "coarse":
        large_scales, med_scales = [16, 32, 64], [2, 4, 8]
        flake_thresh, edge_width = 0.42, 0.12
    elif flake_style == "fine":
        large_scales, med_scales = [2, 4, 8], [1, 2, 4]
        flake_thresh, edge_width = 0.35, 0.08
    else:  # medium
        large_scales, med_scales = [3, 6, 12], [2, 4, 8]
        flake_thresh, edge_width = 0.38, 0.10

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        rng = np.random.RandomState(seed + seed_offset)

        # Density envelope: where flakes are concentrated
        density = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset + 50)
        density = np.clip(density * 0.5 + 0.5, 0.15, 1.0)

        # === LARGE FLAKES: noise → sharp threshold → cell-like shapes ===
        n_lg = _noise(shape, large_scales, [0.3, 0.4, 0.3], seed + seed_offset + 100)
        # Second noise for orientation variation
        n_lg2 = _noise(shape, large_scales, [0.4, 0.3, 0.3], seed + seed_offset + 101)
        # Sharp flake boundary: where noise crosses threshold
        flake_body = np.clip((n_lg - flake_thresh) / edge_width, 0, 1)
        flake_edge = np.clip(1.0 - np.abs(n_lg - flake_thresh) / (edge_width * 0.5), 0, 1)
        # Per-flake orientation from second noise → affects M and R
        orient = np.clip(n_lg2 * 0.5 + 0.5, 0, 1)
        M_large = (180 + orient * 75) * flake_body  # 180-255 in flake, 0 outside
        R_large = orient * 55 * flake_body + flake_edge * 35  # oriented roughness + edge bump

        # === MEDIUM FLAKES: finer noise layer ===
        n_md = _noise(shape, med_scales, [0.35, 0.40, 0.25], seed + seed_offset + 200)
        n_md2 = _noise(shape, med_scales, [0.25, 0.45, 0.30], seed + seed_offset + 201)
        med_body = np.clip((n_md - 0.40) / 0.10, 0, 1)
        med_orient = np.clip(n_md2 * 0.5 + 0.5, 0, 1)
        M_med = (190 + med_orient * 65) * med_body
        R_med = med_orient * 40 * med_body

        # === MICRO SPARKLE: high-frequency pixel-level ===
        # SPB-100 tick 94 (owner: "not NEARLY enough sparkles"): threshold
        # was 0.92 → only top 8% pixels lit. Now 0.74 → top 26% lit. ~3×
        # sparkle population. Combined with _sparkle_micro_sand's 3× boost
        # in this same tick, sparkle finishes now have ~9× the visible
        # particle count overall.
        micro = rng.random((h, w)).astype(np.float32)
        micro_flash = np.where(micro > 0.74, (micro - 0.74) / 0.26, 0.0).astype(np.float32)
        M_micro = 200 + micro_flash * 55
        R_micro = (1.0 - micro_flash) * 30

        # Combine scales weighted by density
        M = (M_large * 0.45 + M_med * 0.35 + M_micro * 0.20) * density
        R = (R_large * 0.40 + R_med * 0.35 + R_micro * 0.25) * density

        # Base coat shows through in sparse areas
        base_mix = np.clip(1.0 - density * 1.2, 0, 0.4)
        M = M * (1 - base_mix) + float(base_m) * base_mix
        R = R * (1 - base_mix) + float(base_r) * base_mix

        # CC: glossy flakes, slight haze between
        CC = (1 - base_mix) * 10 + base_mix * 55
        cc_var = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset + 300)
        CC = CC + cc_var * 15 * sm

        # === PER-TYPE SPEC SPECIALIZATION: structural fingerprint per variant ===
        if seed_offset == 7400:    # diamond_dust: crystalline micro-flash only (suppress macro zones)
            cryst_rng = np.random.RandomState(seed + seed_offset + 801)
            cryst = cryst_rng.random((h, w)).astype(np.float32)
            cryst_flash = np.where(cryst > 0.93, (cryst - 0.93) / 0.07, 0.0).astype(np.float32)
            M = float(base_m) * 0.25 + cryst_flash * 230.0 * density
        elif seed_offset == 7420:  # galaxy: spiral arm density zones in spec
            arm_noise = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 801)
            arm_mod = np.clip(arm_noise * 1.8, 0.0, 1.0)
            M = M * arm_mod + float(base_m) * 0.15 * (1.0 - arm_mod)
        elif seed_offset == 7470:  # constellation: extremely sparse stellar spec
            clust_c = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 500)
            clust_c = np.clip(clust_c * 2.0, 0.0, 1.0)
            star_rng = np.random.RandomState(seed + seed_offset + 801)
            star_r = star_rng.random((h, w)).astype(np.float32)
            star_pts = np.where(star_r > 0.97, (star_r - 0.97) / 0.03, 0.0).astype(np.float32) * clust_c
            M = float(base_m) * 0.10 + star_pts * 245.0
        elif seed_offset == 7460:  # meteor: oblique directional streak alignment in spec
            yg = np.arange(h, dtype=np.float32)[:, np.newaxis] / h
            xg = np.arange(w, dtype=np.float32)[np.newaxis, :] / w
            streak = 0.5 + 0.5 * np.sin((xg * 1.8 + yg * 0.4) * 12.0)
            M = M * (0.35 + streak * 0.65)
        elif seed_offset == 7490:  # lightning_bug: orb-matched discrete high-M blobs
            orb_f = _noise(shape, [18, 36], [0.55, 0.45], seed + seed_offset + 500)
            orb_pts_s = np.clip((orb_f - 0.70) / 0.15, 0.0, 1.0)
            M = float(base_m) * 0.20 * (1.0 - orb_pts_s) + 238.0 * orb_pts_s

        M = np.clip(M * sm + M * (1 - sm) * 0.3, 0, 255)
        R = np.clip(R, 15, 255)  # GGX floor
        CC = np.clip(CC, 16, 255)
        return _spec_out(shape, mask, M, R, CC)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape
        rng = np.random.RandomState(seed + seed_offset)
        result = paint.copy()
        blend = mask * pm

        # Multi-scale sparkle field (noise-based, no Voronoi needed)
        density = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset + 50)
        density = np.clip(density * 0.5 + 0.5, 0.15, 1.0)

        # Flake highlight pattern from large noise
        n_lg = _noise(shape, large_scales, [0.3, 0.4, 0.3], seed + seed_offset + 100)
        flake_body = np.clip((n_lg - flake_thresh) / edge_width, 0, 1)

        # Sparkle intensity: density * flake pattern * micro flash
        # SPB-100 tick 94: threshold 0.88 → 0.68 = 32% sparkle coverage in
        # paint (was 12%). Matches the spec-side bump.
        micro = rng.random((h, w)).astype(np.float32)
        flash = np.where(micro > 0.68, (micro - 0.68) / 0.32, 0.0).astype(np.float32)
        sparkle = (flake_body * 0.6 + flash * 0.4) * density

        # Contrast enhancement in flake zones (makes them pop)
        contrast_boost = flake_body * density * 0.25 * blend
        lum = (paint[:,:,0] * 0.299 + paint[:,:,1] * 0.587 + paint[:,:,2] * 0.114)
        for c in range(3):
            result[:,:,c] = np.clip(paint[:,:,c] + (paint[:,:,c] - lum) * contrast_boost, 0, 1)

        # Per-type sparkle color (stronger than before)
        bright = sparkle * 0.30 * blend
        s = seed_offset
        if s == 7400:    # diamond_dust: icy blue-white sparkles
            result[:,:,0] = np.clip(result[:,:,0] + bright * 0.8, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright * 0.95, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright * 1.4, 0, 1)
        elif s == 7410:  # starfield: cosmic deep-space — multi-colour nebula + stellar temperature variation
            nebula = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 600)
            nebula = np.clip(nebula * 0.5 + 0.5, 0, 1)
            neb_hue = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 650)
            neb_hue = np.clip(neb_hue * 0.5 + 0.5, 0, 1)  # 0=blue region, 1=violet/purple region
            neb = nebula * blend * 0.20
            result[:,:,0] = np.clip(result[:,:,0] + neb * (0.20 + neb_hue * 0.60), 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + neb * (0.30 - neb_hue * 0.10), 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + neb * (0.95 - neb_hue * 0.35), 0, 1)
            star_temp = _noise(shape, [6, 12], [0.5, 0.5], seed + seed_offset + 700)
            star_temp = np.clip(star_temp * 0.5 + 0.5, 0, 1)  # 0=cool K/M-type, 1=hot O/B-type
            result[:,:,0] = np.clip(result[:,:,0] + bright * (1.10 - star_temp * 0.35), 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright * (0.85 + star_temp * 0.10), 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright * (0.55 + star_temp * 0.70), 0, 1)
        elif s == 7420:  # galaxy: violet-magenta nebula with cluster density modulation
            # Distinct from diamond_dust (uniform, icy blue) and constellation (uniform, cold blue-white)
            # Galaxy has: cluster density zones + violet-magenta nebula tint overlay
            neb_g = _noise(shape, [12, 24], [0.55, 0.45], seed + seed_offset + 600)
            neb_g = np.clip(neb_g * 0.5 + 0.5, 0, 1)
            cluster_g = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 610)
            cluster_g = np.clip(cluster_g * 2.0, 0, 1)
            bright_g = bright * (0.45 + cluster_g * 0.55)   # cluster density — denser in bright zones
            neb_tint = neb_g * blend * 0.20
            # Deep violet-magenta (R+B dominant, G suppressed — galactic core vs cold constellation)
            result[:,:,0] = np.clip(result[:,:,0] + bright_g * 1.30 + neb_tint * 0.80, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright_g * 0.28 + neb_tint * 0.18, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright_g * 1.55 + neb_tint * 1.00, 0, 1)
        elif s == 7430:  # firefly: warm yellow-green glow
            result[:,:,0] = np.clip(result[:,:,0] + bright * 1.4, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright * 1.3, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright * 0.2, 0, 1)
        elif s == 7440:  # snowfall: cold icy blue crystal
            result[:,:,0] = np.clip(result[:,:,0] + bright * 0.5, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright * 1.1, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright * 1.6, 0, 1)
        elif s == 7450:  # champagne: warm gold bubbles
            result[:,:,0] = np.clip(result[:,:,0] + bright * 1.5, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright * 1.15, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright * 0.35, 0, 1)
        elif s == 7460:  # meteor: hot orange-red streaks
            dir_noise = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 500)
            dir_streak = np.clip(dir_noise * 1.5, 0, 1)
            bright_dir = bright * (0.6 + dir_streak * 0.4)
            result[:,:,0] = np.clip(result[:,:,0] + bright_dir * 1.7, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright_dir * 0.65, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright_dir * 0.15, 0, 1)
        elif s == 7470:  # constellation: warm stellar clusters — sparse star-points + golden nebula haze
            cluster = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 500)
            cluster = np.clip(cluster * 2.0, 0, 1)
            # Sparse individual star-points: threshold within dense cluster zones only
            star_field = _noise(shape, [8, 14], [0.5, 0.5], seed + seed_offset + 520)
            star_pts = np.clip((star_field - 0.80) / 0.10, 0, 1) * cluster  # sparse brilliant points
            # Warm interstellar dust haze in cluster zones (golden-amber nebula glow)
            warm_haze = cluster * blend * 0.07
            bright_c = bright * (0.35 + star_pts * 0.65)  # brightness concentrated in star-points
            result[:,:,0] = np.clip(result[:,:,0] + bright_c * 1.05 + warm_haze * 0.95, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright_c * 0.98 + warm_haze * 0.72, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright_c * 1.25 + warm_haze * 0.22, 0, 1)
        elif s == 7480:  # confetti: rainbow per-zone hue
            hue_field = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 400)
            hf = np.clip(hue_field * 0.5 + 0.5, 0, 1)
            result[:,:,0] = np.clip(result[:,:,0] + bright * (0.5 + np.sin(hf * 6.28) * 0.8), 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright * (0.5 + np.sin(hf * 6.28 + 2.09) * 0.8), 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright * (0.5 + np.sin(hf * 6.28 + 4.19) * 0.8), 0, 1)
        else:            # 7490 lightning_bug: bioluminescent point-glow (discrete firefly lanterns)
            # Discrete glow-orbs: sparse threshold of medium-scale noise → individual fireflies
            orb_field = _noise(shape, [18, 36], [0.55, 0.45], seed + seed_offset + 500)
            orb_pts = np.clip((orb_field - 0.70) / 0.15, 0, 1)  # discrete orb threshold
            # Soft abdominal haze spreading from orb clusters (large-scale luminescence bloom)
            haze_field = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 510)
            haze = np.clip(haze_field * 0.5 + 0.5, 0, 1) * 0.25
            bright_g = bright * (0.4 + orb_pts * 0.60)  # brightness at discrete orb points
            # Bioluminescent green-gold: 557nm luciferase peak = warm green-yellow
            result[:,:,0] = np.clip(result[:,:,0] + bright_g * 0.65 + haze * blend * 0.12, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright_g * 1.65 + haze * blend * 0.30, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright_g * 0.10 + haze * blend * 0.05, 0, 1)
        result = np.clip(result + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return result
    return spec_fn, paint_fn

# ================================================================
# SPARKLE FUSIONS V2 — Each is a UNIQUE hand-crafted finish, not generic factory output
# ================================================================

def _spec_sparkle_v2(shape, mask, seed, sm, M_field, R_field, CC_val=20.0):
    """Common spec builder for sparkle fusions."""
    smf = float(sm)
    m_min, m_max = float(M_field.min()), float(M_field.max())
    m_span = m_max - m_min
    m_norm = (M_field - m_min) / m_span if m_span > 1e-5 else np.zeros_like(M_field)
    
    r_min, r_max = float(R_field.min()), float(R_field.max())
    r_span = r_max - r_min
    r_norm = (R_field - r_min) / r_span if r_span > 1e-5 else np.zeros_like(R_field)
    
    cc_noise = _noise(shape, [1, 2, 4], [0.45, 0.35, 0.20], seed + 999)
    cc_norm = np.clip((cc_noise + 1.0) * 0.5, 0.0, 1.0)
    cc_norm = np.clip(cc_norm * 0.4 + m_norm * 0.6, 0.0, 1.0)
    
    M = 15.0 + 240.0 * np.clip(m_norm * smf + (1.0 - smf) * (M_field / 255.0), 0.0, 1.0)
    R = 15.0 + 240.0 * np.clip(r_norm * smf + (1.0 - smf) * (R_field / 255.0), 0.0, 1.0)
    CC = 16.0 + 239.0 * np.clip(cc_norm * smf + (1.0 - smf) * (CC_val / 255.0), 0.0, 1.0)
    return _spec_out(shape, mask, M, R, CC)

def _paint_sparkle_v2(paint, shape, mask, seed, pm, bb, sparkle_field, color_r, color_g, color_b, strength=0.35):
    """Common paint builder for sparkle fusions."""
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    result = paint.copy()
    blend = mask * pm
    bright = sparkle_field * strength * blend
    result[:,:,0] = np.clip(result[:,:,0] + bright * color_r, 0, 1)
    result[:,:,1] = np.clip(result[:,:,1] + bright * color_g, 0, 1)
    result[:,:,2] = np.clip(result[:,:,2] + bright * color_b, 0, 1)
    return np.clip(result + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)

# 1. DIAMOND DUST — Ultra-fine per-pixel crystal flash on dark base
def _sparkle_norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


def _sparkle_micro_sand(shape, seed, density=0.24, glitter=0.48):
    """Dense pixel-scale crystal population: crushed-sand sparkle, not chunky blobs.

    SPB-100 tick 94 (owner: "Sparkle System - not NEARLY enough sparkles"):
    density argument gets a 3× internal boost AND cutoff bounds relaxed so
    even high density values (e.g. 0.30) actually produce 30% sparkle
    coverage instead of clipping at 4%. Plus the needle layer is also more
    aggressive."""
    h, w = shape
    rng = np.random.RandomState(seed)
    raw = rng.random((h, w)).astype(np.float32)
    # 3× density boost. Old cutoff floor was 0.45 (=55% sparkle ceiling
    # which was never reached). New floor 0.10 lets density=0.3 → ~30%
    # actual coverage as owner clearly intended.
    eff_density = min(0.92, float(density) * 3.0)
    cutoff = np.clip(1.0 - eff_density, 0.10, 0.96)
    grains = np.clip((raw - cutoff) / max(1.0 - cutoff, 1e-6), 0.0, 1.0)
    fine = _noise(shape, [1, 2, 3, 5], [0.34, 0.30, 0.22, 0.14], seed + 37)
    fine = np.clip((fine + 1.0) * 0.5, 0.0, 1.0)
    # Needle layer also gets the density boost so the secondary sparkle band
    # scales with density too.
    needles = np.clip((fine - (0.62 - eff_density * 0.32)) / 0.30, 0.0, 1.0)
    return np.clip(grains * float(glitter) + needles * (1.0 - float(glitter)) + fine * 0.08, 0.0, 1.0).astype(np.float32)


def _sparkle_soft_points(shape, seed, density=0.0015, sigma=2.2):
    """Soft glow points without nearest-neighbor square artifacts.

    SPB-100 tick 94 (owner: "not NEARLY enough sparkles"): density gets a
    5× boost so soft-point sparkles also pump up. firefly/champagne/etc.
    will now show hundreds of glow orbs instead of a few dozen."""
    h, w = shape
    rng = np.random.RandomState(seed)
    eff_density = float(density) * 5.0
    count = max(1, int(h * w * eff_density))
    points = np.zeros((h, w), dtype=np.float32)
    ys = rng.randint(0, h, size=count)
    xs = rng.randint(0, w, size=count)
    points[ys, xs] = rng.uniform(0.55, 1.0, size=count).astype(np.float32)
    glow = cv2.GaussianBlur(points, (0, 0), sigmaX=float(sigma), sigmaY=float(sigma))
    return _sparkle_norm01(glow)


_sparkle_galaxy_field_cache = OrderedDict()
_SPARKLE_GALAXY_FIELD_CACHE_MAX = 4


def _sparkle_galaxy_field(shape, seed):
    h, w = shape
    cache_key = (int(h), int(w), int(seed))
    cached = _sparkle_galaxy_field_cache.get(cache_key)
    if cached is not None:
        _sparkle_galaxy_field_cache.move_to_end(cache_key)
        return cached
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    dy, dx = (y - cy).astype(np.float32), (x - cx).astype(np.float32)
    r = np.sqrt(dy**2 + dx**2) + 1e-8
    theta = np.arctan2(dy, dx)
    swirl = theta - 0.52 * np.log(r / (min(h, w) * 0.10) + 1e-8)
    arm1 = np.exp(-((np.sin(swirl)) * r / (min(h, w) * 0.18)) ** 2 * 10.0)
    arm2 = np.exp(-((np.sin(swirl + np.pi)) * r / (min(h, w) * 0.18)) ** 2 * 10.0)
    arms = np.clip((arm1 + arm2) * np.clip(1.15 - r / (min(h, w) * 0.70), 0, 1), 0, 1)
    rng = np.random.RandomState(seed + 7420)
    stars = np.clip((rng.random((h, w)).astype(np.float32) - (0.985 - arms * 0.065)) / 0.020, 0, 1)
    dust = _sparkle_micro_sand(shape, seed + 7422, density=0.22, glitter=0.48) * (0.20 + arms * 0.80)
    field = np.clip(arms * 0.10 + stars * 0.90 + dust * 0.82, 0, 1).astype(np.float32)
    _sparkle_galaxy_field_cache[cache_key] = field
    _sparkle_galaxy_field_cache.move_to_end(cache_key)
    while len(_sparkle_galaxy_field_cache) > _SPARKLE_GALAXY_FIELD_CACHE_MAX:
        _sparkle_galaxy_field_cache.popitem(last=False)
    return field


def _spec_sparkle_diamond_dust(shape, mask, seed, sm):
    crystals = _sparkle_micro_sand(shape, seed + 7400, density=0.32, glitter=0.72)
    frost = _noise(shape, [2, 4, 8], [0.42, 0.36, 0.22], seed + 7401)
    frost = np.clip((frost + 1.0) * 0.5, 0, 1) * 0.16
    field = np.clip(crystals + frost, 0, 1)
    M = 18.0 + field * 237.0
    R = 108.0 - field * 92.0
    return _spec_sparkle_v2(shape, mask, seed, sm, M, R, 18.0)

def _paint_sparkle_diamond_dust(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    crystals = _sparkle_micro_sand(shape, seed + 7400, density=0.32, glitter=0.72)
    return _paint_sparkle_v2(paint, shape, mask, seed, pm, bb, crystals, 0.85, 0.95, 1.4, 0.40)

# 2. STARFIELD — Sparse bright stars on deep void with nebula clouds
def _spec_sparkle_starfield(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.RandomState(seed + 7410)
    stars = np.clip((rng.random((h, w)).astype(np.float32) - 0.993) / 0.007, 0, 1)
    micro_stars = _sparkle_micro_sand(shape, seed + 7412, density=0.18, glitter=0.62) * 0.45
    nebula = _noise(shape, [10, 20, 40, 80], [0.30, 0.30, 0.24, 0.16], seed + 7411)
    nebula = np.clip((nebula + 1.0) * 0.5, 0, 1) * 0.18
    field = np.clip(stars + micro_stars + nebula, 0, 1)
    M = 5.0 + field * 245.0
    R = 205.0 - stars * 185.0 - micro_stars * 70.0 - nebula * 35.0
    return _spec_sparkle_v2(shape, mask, seed, sm, M, R, 16.0)

def _paint_sparkle_starfield(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    rng = np.random.RandomState(seed + 7410)
    stars = np.clip((rng.random((h, w)).astype(np.float32) - 0.993) / 0.007, 0, 1)
    micro_stars = _sparkle_micro_sand(shape, seed + 7412, density=0.18, glitter=0.62) * 0.45
    nebula = _noise(shape, [10, 20, 40, 80], [0.30, 0.30, 0.24, 0.16], seed + 7411)
    nebula = np.clip((nebula + 1.0) * 0.5, 0, 1) * 0.18
    combined = np.clip(stars * 0.85 + micro_stars + nebula, 0, 1)
    return _paint_sparkle_v2(paint, shape, mask, seed, pm, bb, combined, 0.6, 0.7, 1.3, 0.30)

# 3. GALAXY — Spiral arm density with hot/cold star regions
def _spec_sparkle_galaxy(shape, mask, seed, sm):
    field = _sparkle_galaxy_field(shape, seed)
    M = 12.0 + field * 238.0
    R = 186.0 - field * 158.0
    return _spec_sparkle_v2(shape, mask, seed, sm, M, R, 20.0)

def _paint_sparkle_galaxy(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    field = _sparkle_galaxy_field(shape, seed)
    return _paint_sparkle_v2(paint, shape, mask, seed, pm, bb, field, 1.1, 0.4, 1.4, 0.30)

# 4. FIREFLY — Discrete soft glow orbs with warm bioluminescent color
def _spec_sparkle_firefly(shape, mask, seed, sm):
    glow_pts = _sparkle_soft_points(shape, seed + 7430, density=0.0018, sigma=2.4)
    sparks = _sparkle_micro_sand(shape, seed + 7432, density=0.16, glitter=0.58) * 0.48
    field = np.clip(glow_pts * 0.85 + sparks, 0, 1)
    M = 28.0 + field * 222.0
    R = 124.0 - field * 96.0
    return _spec_sparkle_v2(shape, mask, seed, sm, M, R, 25.0)

def _paint_sparkle_firefly(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    glow_pts = _sparkle_soft_points(shape, seed + 7430, density=0.0018, sigma=2.4)
    sparks = _sparkle_micro_sand(shape, seed + 7432, density=0.16, glitter=0.58) * 0.48
    combined = np.clip(glow_pts * 0.85 + sparks, 0, 1)
    return _paint_sparkle_v2(paint, shape, mask, seed, pm, bb, combined, 0.7, 1.5, 0.15, 0.35)

# 5. SNOWFALL — Drifting ice crystal curtains with wind-driven density bands
def _snowfall_field(shape, seed):
    """Vectorized snowfall: wind-sheared crystal grit plus fine vertical streaks."""
    h, w = shape
    rng = np.random.RandomState(seed + 7440)
    wind = _noise(shape, [10, 20, 40, 80], [0.28, 0.30, 0.26, 0.16], seed + 7441)
    wind_bands = np.clip((wind + 1.0) * 0.5, 0.12, 1.0)
    heads = np.clip((rng.random((h, w)).astype(np.float32) - 0.955) / 0.045, 0.0, 1.0)
    kernel = np.ones((max(3, h // 180), 1), dtype=np.float32) / max(3, h // 180)
    streaks = cv2.filter2D(heads, -1, kernel)
    crystals = _sparkle_micro_sand(shape, seed + 7442, density=0.22, glitter=0.62)
    drift = _noise(shape, [1, 2, 4], [0.42, 0.34, 0.24], seed + 7443)
    drift = np.clip((drift + 1.0) * 0.5, 0, 1)
    return np.clip(streaks * wind_bands * 2.2 + crystals * 0.46 + drift * 0.08, 0, 1)

def _spec_sparkle_snowfall(shape, mask, seed, sm):
    snow = _snowfall_field(shape, seed)
    M = 40.0 + snow * 200.0
    R = 90.0 - snow * 70.0
    return _spec_sparkle_v2(shape, mask, seed, sm, M, R, 22.0)

def _paint_sparkle_snowfall(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    snow = _snowfall_field(shape, seed)
    return _paint_sparkle_v2(paint, shape, mask, seed, pm, bb, snow, 0.55, 1.0, 1.5, 0.30)

# 6. CHAMPAGNE — Effervescent bubble columns with golden fizz and rising density gradient
def _champagne_field(shape, seed):
    """Vectorized champagne: rising micro-fizz streams with tiny warm bubbles."""
    h, w = shape
    y_grad = np.linspace(1.0, 0.2, h, dtype=np.float32)[:, np.newaxis] * np.ones((1, w), dtype=np.float32)
    stream = _noise(shape, [5, 10, 20, 40], [0.34, 0.30, 0.22, 0.14], seed + 7453)
    stream = np.clip((stream + 1.0) * 0.5, 0.25, 1.0)
    fizz = _sparkle_micro_sand(shape, seed + 7450, density=0.30, glitter=0.58)
    bubbles = _sparkle_soft_points(shape, seed + 7451, density=0.0032, sigma=1.35)
    tiny = _noise(shape, [1, 2, 3], [0.42, 0.34, 0.24], seed + 7452)
    tiny = np.clip((tiny + 1.0) * 0.5, 0, 1) * 0.14
    combined = (fizz * 0.52 + bubbles * 0.36 + tiny) * y_grad * stream
    return np.clip(combined, 0, 1)

def _spec_sparkle_champagne(shape, mask, seed, sm):
    bubbles = _champagne_field(shape, seed)
    M = 80.0 + bubbles * 170.0
    R = 55.0 - bubbles * 35.0
    return _spec_sparkle_v2(shape, mask, seed, sm, M, R, 16.0)

def _paint_sparkle_champagne(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    bubbles = _champagne_field(shape, seed)
    return _paint_sparkle_v2(paint, shape, mask, seed, pm, bb, bubbles, 1.4, 1.1, 0.35, 0.35)

# 7. METEOR — Directional motion-blur streaks with bright heads and hot-to-cool color gradient
@lru_cache(maxsize=24)
def _meteor_field_cached(h, w, seed):
    """Vectorized meteor shower: hot heads, fine ember dust, and directional tails."""
    shape = (h, w)
    rng = np.random.RandomState(seed + 7460)
    heads = np.clip((rng.random((h, w)).astype(np.float32) - 0.991) / 0.009, 0, 1)
    heads *= rng.uniform(0.65, 1.0, (h, w)).astype(np.float32)
    streak_len = max(8, min(h, w) // 60)
    angle = 0.7  # ~40 degrees
    ky = max(1, int(streak_len * np.cos(angle)))
    kx = max(1, int(streak_len * np.sin(angle)))
    kernel_size = max(ky, kx) * 2 + 1
    kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
    cy, cx = kernel_size // 2, kernel_size // 2
    for t in range(streak_len):
        py = min(kernel_size - 1, cy + int(t * np.cos(angle)))
        px = min(kernel_size - 1, cx + int(t * np.sin(angle)))
        kernel[py, px] = (1.0 - t / streak_len) ** 1.5  # fade along tail
    kernel /= kernel.sum() + 1e-8
    streaks = cv2.filter2D(heads, -1, kernel)
    intensity = _noise(shape, [16, 32], [0.5, 0.5], seed + 7461)
    intensity = np.clip(intensity * 0.5 + 0.7, 0.3, 1.0)
    embers = _sparkle_micro_sand(shape, seed + 7462, density=0.16, glitter=0.58)
    ember_gate = _noise(shape, [6, 12, 24], [0.36, 0.34, 0.30], seed + 7463)
    ember_gate = np.clip((ember_gate + 1.0) * 0.5, 0, 1)
    return np.clip(streaks * intensity * 7.5 + embers * ember_gate * 0.38, 0, 1)

def _meteor_field(shape, seed):
    h, w = shape
    return _meteor_field_cached(int(h), int(w), int(seed))

def _spec_sparkle_meteor(shape, mask, seed, sm):
    meteors = _meteor_field(shape, seed)
    M = 30.0 + meteors * 225.0
    R = 150.0 - meteors * 135.0
    return _spec_sparkle_v2(shape, mask, seed, sm, M, R, 18.0)

def _paint_sparkle_meteor(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    meteors = _meteor_field(shape, seed)
    return _paint_sparkle_v2(paint, shape, mask, seed, pm, bb, meteors, 1.6, 0.6, 0.15, 0.35)

# 8. CONSTELLATION — Gaussian cluster density + sparse stellar points + warm interstellar dust
_constellation_field_cache = OrderedDict()
_CONSTELLATION_FIELD_CACHE_MAX = 4


def _constellation_field(shape, seed):
    """Vectorized constellation: clustered pin stars, thin dust, and visible dark lanes."""
    h, w = shape
    cache_key = (int(h), int(w), int(seed))
    cached = _constellation_field_cache.get(cache_key)
    if cached is not None:
        _constellation_field_cache.move_to_end(cache_key)
        return cached
    rng = np.random.RandomState(seed + 7470)
    # 6-8 cluster centers as Gaussian density peaks
    n_clusters = rng.randint(6, 9)
    y, x = _mgrid(shape)
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    density = np.zeros((h, w), dtype=np.float32)
    for _ in range(n_clusters):
        cy = rng.uniform(0.1, 0.9) * h
        cx = rng.uniform(0.1, 0.9) * w
        sigma = rng.uniform(0.04, 0.09) * min(h, w)
        density += np.exp(-((yf - cy)**2 + (xf - cx)**2) / (2 * sigma**2))
    density = np.clip(density / max(float(density.max()), 1e-8), 0, 1)
    star_raw = rng.random((h, w)).astype(np.float32)
    threshold = 1.0 - 0.022 * (0.18 + density * 2.8)
    stars = np.clip((star_raw - threshold) / 0.009, 0, 1)
    micro = _sparkle_micro_sand(shape, seed + 7472, density=0.15, glitter=0.64) * (0.25 + density * 0.75)
    dust = _noise(shape, [8, 16, 32, 64], [0.30, 0.30, 0.24, 0.16], seed + 7471)
    dust = np.clip((dust + 1.0) * 0.5, 0, 1) * density * 0.22
    lanes = _noise(shape, [16, 32], [0.55, 0.45], seed + 7473)
    lanes = np.clip((lanes + 1.0) * 0.5, 0.18, 1.0)
    field = np.clip((stars * 0.80 + micro + dust) * lanes, 0, 1).astype(np.float32)
    _constellation_field_cache[cache_key] = field
    _constellation_field_cache.move_to_end(cache_key)
    while len(_constellation_field_cache) > _CONSTELLATION_FIELD_CACHE_MAX:
        _constellation_field_cache.popitem(last=False)
    return field

def _spec_sparkle_constellation(shape, mask, seed, sm):
    field = _constellation_field(shape, seed)
    M = 15.0 + field * 235.0
    R = 160.0 - field * 140.0
    return _spec_sparkle_v2(shape, mask, seed, sm, M, R, 20.0)

def _paint_sparkle_constellation(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    field = _constellation_field(shape, seed)
    return _paint_sparkle_v2(paint, shape, mask, seed, pm, bb, field, 1.0, 0.92, 1.25, 0.30)

# 9. CONFETTI — Rainbow-hued noise zones with per-zone color
def _spec_sparkle_confetti(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.RandomState(seed + 7480)
    flash = np.clip((rng.random((h, w)).astype(np.float32) - 0.86) / 0.14, 0, 1)
    shard = _sparkle_micro_sand(shape, seed + 7482, density=0.24, glitter=0.55)
    hue_zones = _noise(shape, [6, 12, 24, 48], [0.32, 0.30, 0.24, 0.14], seed + 7481)
    hue_zones = np.clip((hue_zones + 1.0) * 0.5, 0, 1)
    field = np.clip(flash * 0.68 + shard * 0.42 + hue_zones * 0.10, 0, 1)
    M = 58.0 + field * 170.0
    R = 86.0 - field * 58.0
    return _spec_sparkle_v2(shape, mask, seed, sm, M, R, 22.0)

def _paint_sparkle_confetti(paint, shape, mask, seed, pm, bb):
    if hasattr(bb, "ndim") and bb.ndim == 2:
        bb = bb[:, :, np.newaxis]  # (h,w) -> (h,w,1) for broadcasting
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    rng = np.random.RandomState(seed + 7480)
    flash = np.clip((rng.random((h, w)).astype(np.float32) - 0.86) / 0.14, 0, 1)
    shard = _sparkle_micro_sand(shape, seed + 7482, density=0.24, glitter=0.55)
    hue_zones = _noise(shape, [6, 12, 24, 48], [0.32, 0.30, 0.24, 0.14], seed + 7481)
    hf = np.clip((hue_zones + 1.0) * 0.5, 0, 1)
    sparkle = np.clip(flash * 0.68 + shard * 0.42 + hf * 0.10, 0, 1)
    result = paint.copy()
    blend = mask * pm
    bright = sparkle * 0.35 * blend
    result[:,:,0] = np.clip(result[:,:,0] + bright * (0.5 + np.sin(hf * 6.28) * 0.9), 0, 1)
    result[:,:,1] = np.clip(result[:,:,1] + bright * (0.5 + np.sin(hf * 6.28 + 2.09) * 0.9), 0, 1)
    result[:,:,2] = np.clip(result[:,:,2] + bright * (0.5 + np.sin(hf * 6.28 + 4.19) * 0.9), 0, 1)
    return np.clip(result + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)

# 10. LIGHTNING BUG — Discrete warm glow orbs + bioluminescent haze
def _spec_sparkle_lightning_bug(shape, mask, seed, sm):
    glow = _sparkle_soft_points(shape, seed + 7490, density=0.0024, sigma=2.0)
    micro = _sparkle_micro_sand(shape, seed + 7492, density=0.20, glitter=0.55) * 0.42
    haze = _noise(shape, [10, 20, 40], [0.36, 0.34, 0.30], seed + 7491)
    haze = np.clip((haze + 1.0) * 0.5, 0, 1) * 0.18
    combined = np.clip(glow * 0.90 + micro + haze, 0, 1)
    M = 24.0 + combined * 222.0
    R = 134.0 - combined * 104.0
    return _spec_sparkle_v2(shape, mask, seed, sm, M, R, 20.0)

def _paint_sparkle_lightning_bug(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    glow = _sparkle_soft_points(shape, seed + 7490, density=0.0024, sigma=2.0)
    micro = _sparkle_micro_sand(shape, seed + 7492, density=0.20, glitter=0.55) * 0.42
    haze = _noise(shape, [10, 20, 40], [0.36, 0.34, 0.30], seed + 7491)
    haze = np.clip((haze + 1.0) * 0.5, 0, 1) * 0.18
    combined = np.clip(glow * 0.90 + micro + haze, 0, 1)
    return _paint_sparkle_v2(paint, shape, mask, seed, pm, bb, combined, 0.6, 1.6, 0.1, 0.35)

spec_sparkle_diamond_dust = _spec_sparkle_diamond_dust
paint_sparkle_diamond_dust = _paint_sparkle_diamond_dust
spec_sparkle_starfield = _spec_sparkle_starfield
paint_sparkle_starfield = _paint_sparkle_starfield
spec_sparkle_galaxy = _spec_sparkle_galaxy
paint_sparkle_galaxy = _paint_sparkle_galaxy
spec_sparkle_firefly = _spec_sparkle_firefly
paint_sparkle_firefly = _paint_sparkle_firefly
spec_sparkle_snowfall = _spec_sparkle_snowfall
paint_sparkle_snowfall = _paint_sparkle_snowfall
spec_sparkle_champagne = _spec_sparkle_champagne
paint_sparkle_champagne = _paint_sparkle_champagne
spec_sparkle_meteor = _spec_sparkle_meteor
paint_sparkle_meteor = _paint_sparkle_meteor
spec_sparkle_constellation = _spec_sparkle_constellation
paint_sparkle_constellation = _paint_sparkle_constellation
spec_sparkle_confetti = _spec_sparkle_confetti
paint_sparkle_confetti = _paint_sparkle_confetti
spec_sparkle_lightning_bug = _spec_sparkle_lightning_bug
paint_sparkle_lightning_bug = _paint_sparkle_lightning_bug


# ================================================================
# PARADIGM 6: MULTI-SCALE TEXTURE - Layered texture systems
# ================================================================

def _fusion_norm01(arr):
    arr = np.asarray(arr, dtype=np.float32)
    span = float(arr.max() - arr.min()) if arr.size else 0.0
    if span < 1e-7:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - float(arr.min())) / span).astype(np.float32)


_weather_spb67_cache = OrderedDict()
_WEATHER_SPB67_CACHE_MAX = 3


def _weather_spb67_fields(shape, seed, seed_offset):
    """Fine weather carriers shared by Weather & Age paint/spec.

    These are source-side material features, not a generic wrapper: each branch
    decides which carriers become chalk, salt, crackle, tide rings, ash, etc.
    """
    h, w = shape
    cache_key = (int(h), int(w), int(seed), int(seed_offset))
    cached = _weather_spb67_cache.get(cache_key)
    if cached is not None:
        _weather_spb67_cache.move_to_end(cache_key)
        return cached
    y, x = _mgrid(shape)
    yf = y.astype(np.float32) / max(1.0, float(h - 1))
    xf = x.astype(np.float32) / max(1.0, float(w - 1))
    rng = np.random.RandomState(seed + seed_offset + 18431)
    micro = _fusion_norm01(_noise(shape, [1, 2, 3, 5], [0.30, 0.30, 0.24, 0.16], seed + seed_offset + 181))
    powder = _fusion_norm01(_noise(shape, [2, 4, 8, 16], [0.26, 0.30, 0.26, 0.18], seed + seed_offset + 193))
    cloud = _fusion_norm01(_noise(shape, [8, 16, 32, 64], [0.18, 0.28, 0.32, 0.22], seed + seed_offset + 207))
    scratch = np.clip(np.abs(_noise(shape, [1, 2, 8], [0.54, 0.30, 0.16], seed + seed_offset + 221)) - 0.48, 0, 1)
    scratch = _fusion_norm01(scratch)
    pin = (rng.random((h, w)).astype(np.float32) > 0.986).astype(np.float32)
    pin = cv2.GaussianBlur(pin, (0, 0), sigmaX=0.55, sigmaY=0.55)
    pin = np.clip(pin * 5.0, 0, 1)
    rings = np.sin((xf * 11.0 + cloud * 2.4 + seed_offset * 0.001) * np.pi * 2.0) * 0.5 + 0.5
    rings *= np.sin((yf * 7.0 - cloud * 1.7) * np.pi * 2.0) * 0.5 + 0.5
    rings = np.clip((rings - 0.62) * 3.4, 0, 1)
    tide = np.sin((yf * 18.0 + cloud * 3.8 + np.sin(xf * 8.0) * 0.35) * np.pi * 2.0)
    tide = np.clip(np.abs(tide) - 0.74, 0, 1) * 3.8
    heat = np.sin((xf * 13.0 + yf * 4.0 + cloud * 3.0) * np.pi * 2.0)
    heat = np.clip(np.abs(heat) - 0.70, 0, 1) * 3.3
    panel = (
        np.clip(np.abs((xf * 6.0) % 1.0 - 0.5) - 0.470, 0, 1) * 34.0
        + np.clip(np.abs((yf * 4.0) % 1.0 - 0.5) - 0.465, 0, 1) * 30.0
    )
    panel = np.clip(panel, 0, 1)
    wind = np.sin((xf * 24.0 + yf * 5.2 + cloud * 2.0) * np.pi * 2.0)
    wind = np.clip(np.abs(wind) - 0.80, 0, 1) * 4.2
    crackle = np.clip(scratch * 0.58 + rings * 0.28 + pin * 0.18, 0, 1)
    fields = {
        "micro": micro,
        "powder": powder,
        "cloud": cloud,
        "scratch": scratch,
        "pin": pin,
        "rings": rings,
        "tide": tide,
        "heat": heat,
        "panel": panel,
        "wind": wind,
        "crackle": crackle,
        "xf": xf,
        "yf": yf,
    }
    _weather_spb67_cache[cache_key] = fields
    _weather_spb67_cache.move_to_end(cache_key)
    while len(_weather_spb67_cache) > _WEATHER_SPB67_CACHE_MAX:
        _weather_spb67_cache.popitem(last=False)
    return fields


_multiscale_smooth_noise_cache = OrderedDict()
_MULTISCALE_SMOOTH_NOISE_CACHE_MAX = 12
_multiscale_silk_surface_cache = OrderedDict()
_MULTISCALE_SILK_SURFACE_CACHE_MAX = 4


def _multiscale_smooth_noise(shape, scales, weights, seed):
    """Local smooth noise for multiscale finishes.

    The global cached noise path intentionally uses nearest-neighbor upscales for
    speed. These finishes put that field directly into paint/spec, so they need
    interpolated material fields to avoid visible square-cell artifacts.
    """
    h, w = shape
    cache_key = (
        int(h),
        int(w),
        tuple(int(s) for s in scales),
        tuple(float(v) for v in weights),
        int(seed),
    )
    cached = _multiscale_smooth_noise_cache.get(cache_key)
    if cached is not None:
        _multiscale_smooth_noise_cache.move_to_end(cache_key)
        return cached
    rng = np.random.RandomState(seed)
    cap = 1024
    if max(h, w) > cap:
        ratio = float(cap) / float(max(h, w))
        wh = max(128, int(round(h * ratio)))
        ww = max(128, int(round(w * ratio)))
    else:
        wh, ww = int(h), int(w)
    result = np.zeros((wh, ww), dtype=np.float32)
    for scale, weight in zip(scales, weights):
        scale = max(1, int(scale))
        # Preserve original raw-octave density where it fits the work grid.
        sh, sw = min(wh, max(1, h // scale)), min(ww, max(1, w // scale))
        raw = rng.randn(sh, sw).astype(np.float32)
        up = raw if (sh == wh and sw == ww) else cv2.resize(raw, (ww, wh), interpolation=cv2.INTER_CUBIC)
        if scale >= 4:
            sigma = max(0.45, min(3.0, scale * 0.07))
            up = cv2.GaussianBlur(up, (0, 0), sigmaX=sigma, sigmaY=sigma)
        result += up * float(weight)
    result = _fusion_norm01(result) * 2.0 - 1.0
    if (wh, ww) != (h, w):
        result = cv2.resize(result, (w, h), interpolation=cv2.INTER_LINEAR)
    result = result.astype(np.float32)
    # SPB perf loop 2026-05-31: smooth-noise reuse across multiscale spec+paint.
    # The work grid keeps interpolated material fields but avoids duplicate full-canvas cubic work.
    _multiscale_smooth_noise_cache[cache_key] = result
    _multiscale_smooth_noise_cache.move_to_end(cache_key)
    while len(_multiscale_smooth_noise_cache) > _MULTISCALE_SMOOTH_NOISE_CACHE_MAX:
        _multiscale_smooth_noise_cache.popitem(last=False)
    return result


def _multiscale_silk_surface(shape, seed, seed_offset, macro):
    h, w = shape
    cache_key = (int(h), int(w), int(seed), int(seed_offset))
    cached = _multiscale_silk_surface_cache.get(cache_key)
    if cached is not None:
        _multiscale_silk_surface_cache.move_to_end(cache_key)
        return cached
    y, x = _mgrid(shape)
    step = max(3, min(h, w) // 44)
    warp = np.sin(x * 0.035 + macro * 2.8) * 0.18
    thread = np.abs(np.sin((y + warp * h) * np.pi / step)) ** 7
    cross = np.abs(np.sin((x * 0.45 + y * 0.12) * np.pi / (step * 2.7))) ** 9
    result = (thread.astype(np.float32), cross.astype(np.float32))
    _multiscale_silk_surface_cache[cache_key] = result
    _multiscale_silk_surface_cache.move_to_end(cache_key)
    while len(_multiscale_silk_surface_cache) > _MULTISCALE_SILK_SURFACE_CACHE_MAX:
        _multiscale_silk_surface_cache.popitem(last=False)
    return result


def _make_multiscale_fusion(texture_profile, seed_offset=0):
    """Factory: 4+ distinct texture scales working together multiplicatively.
    Macro (128px+): large material zones. Meso (16-64px): surface detail.
    Micro (4-8px): grain/texture. Nano (1-2px): sparkle/flake.
    Each scale has independent M/R/CC behavior with scale-dependent transfer functions."""

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        rng = np.random.RandomState(seed + seed_offset)

        # === MACRO SCALE (128px+): large material zone shapes ===
        macro = _multiscale_smooth_noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset)
        macro = np.clip(macro * 0.5 + 0.5, 0, 1)
        # Blend with a second noise octave for organic shapes
        macro_warped = _multiscale_smooth_noise(shape, [12, 24], [0.5, 0.5], seed + seed_offset + 30)
        macro = np.clip(macro * 0.6 + np.clip(macro_warped * 0.5 + 0.5, 0, 1) * 0.4, 0, 1)

        # === MESO SCALE (16-64px): surface detail patterns ===
        meso = _multiscale_smooth_noise(shape, [10, 18, 32], [0.32, 0.38, 0.30], seed + seed_offset + 100)
        meso = np.clip(meso * 0.5 + 0.5, 0, 1)

        # === MICRO SCALE (4-8px): grain/texture ===
        micro = _multiscale_smooth_noise(shape, [2, 4, 7], [0.36, 0.34, 0.30], seed + seed_offset + 200)
        micro = np.clip(micro * 0.5 + 0.5, 0, 1)

        # === NANO SCALE (1-2px): sparkle/flake ===
        nano = rng.random((h, w)).astype(np.float32)
        nano_thresh = np.where(nano > 0.92, (nano - 0.92) / 0.08, 0.0).astype(np.float32)

        # Scale-dependent transfer functions based on texture_profile
        s = seed_offset % 10000
        if s == 7500:  # chrome_grain: macro=zone boundaries, micro=grain direction
            M_macro = macro * 40 + 210       # high metallic zones
            M_meso = meso * 20               # subtle detail
            M_micro = micro * 15             # grain sparkle
            M_nano = nano_thresh * 30        # point sparkle
            R_macro = (1 - macro) * 80       # smooth in macro-high zones
            R_meso = meso * 30               # meso detail roughness
            R_micro = micro * 45             # grain roughness (dominant)
            R_nano = nano_thresh * 10
            CC_base = 10.0
        elif s == 7510:  # candy_frost: macro=candy/frost split
            M_macro = macro * 120 + 80
            M_meso = (1 - meso) * 30
            M_micro = micro * 10
            M_nano = nano_thresh * 20
            R_macro = macro * 40 + (1 - macro) * 100
            R_meso = meso * 35
            R_micro = (1 - micro) * 25
            R_nano = nano_thresh * 8
            CC_base = 16.0
        elif s == 7520:  # metal_grit: macro=smooth, micro=gritty
            M_macro = macro * 60 + 160
            M_meso = meso * 25
            M_micro = (1 - micro) * 40
            M_nano = nano_thresh * 35
            R_macro = (1 - macro) * 50
            R_meso = meso * 40
            R_micro = micro * 70             # micro dominates roughness
            R_nano = nano_thresh * 15
            CC_base = 20.0
        elif s == 7530:  # pearl_texture: macro=pearl zones, meso=iridescence
            M_macro = macro * 60 + 60
            M_meso = meso * 40
            M_micro = micro * 15
            M_nano = nano_thresh * 25
            R_macro = (1 - macro) * 30 + 10
            R_meso = (1 - meso) * 25
            R_micro = micro * 20
            R_nano = nano_thresh * 5
            CC_base = 8.0
        elif s == 7540:  # satin_weave: meso=weave structure
            M_macro = macro * 80 + 150
            M_meso = np.sin(meso * np.pi * 4) * 30
            M_micro = micro * 12
            M_nano = nano_thresh * 15
            R_macro = macro * 30 + 20
            R_meso = np.abs(np.sin(meso * np.pi * 4)) * 50
            R_micro = micro * 25
            R_nano = nano_thresh * 5
            CC_base = 30.0
        elif s == 7550:  # chrome_sand: visible chrome/sand transition
            M_macro = macro * 80 + 170       # chrome-to-metal transition (170-250)
            M_meso = meso * 25               # visible meso detail
            M_micro = micro * 15
            M_nano = nano_thresh * 30        # bright sparkle points
            R_macro = (1 - macro) * 45       # sand zones rougher
            R_meso = meso * 20
            R_micro = micro * 30             # sand grain roughness
            R_nano = (1 - nano_thresh) * 35  # sand = rough between sparkles
            CC_base = 16.0
        elif s == 7560:  # matte_silk: macro=sheen zones, R inverted
            thread, cross = _multiscale_silk_surface(shape, seed, seed_offset, macro)
            silk = np.clip(micro * 0.48 + thread * 0.38 + cross * 0.14, 0, 1)
            M_macro = macro * 30
            M_meso = meso * 15
            M_micro = silk * 24
            M_nano = nano_thresh * 10
            R_macro = macro * 80 + 60        # large features smooth(ish)
            R_meso = (1 - meso) * 40
            R_micro = silk * 48
            R_nano = nano_thresh * 5
            CC_base = 60.0
        elif s == 7570:  # flake_grain: large flakes dominant
            M_macro = macro * 100 + 140
            M_meso = meso * 30
            M_micro = micro * 15
            M_nano = nano_thresh * 40        # bright sparkle points
            R_macro = (1 - macro) * 25
            R_meso = meso * 15
            R_micro = micro * 10
            R_nano = (1 - nano_thresh) * 20
            CC_base = 12.0
        elif s == 7580:  # carbon_micro: micro=weave, macro=shading
            M_macro = macro * 30 + 25
            M_meso = meso * 20
            M_micro = np.abs(np.sin(micro * np.pi * 6)) * 40
            M_nano = nano_thresh * 15
            R_macro = macro * 20 + 10
            R_meso = meso * 25
            R_micro = np.abs(np.cos(micro * np.pi * 6)) * 55
            R_nano = nano_thresh * 5
            CC_base = 25.0
        else:  # 7590 frost_crystal: macro=frost zones
            M_macro = (1 - macro) * 80 + 140
            M_meso = meso * 35
            M_micro = micro * 15
            M_nano = nano_thresh * 30
            R_macro = macro * 100           # frost = rough
            R_meso = (1 - meso) * 30
            R_micro = micro * 20
            R_nano = nano_thresh * 10
            CC_base = 16.0

        # Multiplicative combination across scales (more realistic than additive)
        M_combined = (M_macro / 255.0) * (1.0 + M_meso / 255.0 * 0.3) * (1.0 + M_micro / 255.0 * 0.15) * (1.0 + M_nano / 255.0 * 0.1)
        M = np.clip(M_combined * 200 * sm + (1 - sm) * float(M_macro.mean()), 0, 255)

        # Scale-dependent roughness: large features smooth, small features rough
        R_combined = R_macro * 0.30 + R_meso * 0.25 + R_micro * 0.30 + R_nano * 0.15
        R = np.clip(R_combined * sm, 15, 255)  # GGX floor

        # CC varies with macro scale
        CC = CC_base + (1 - macro) * 25 * sm + meso * 12 * sm
        CC = np.clip(CC, 16, 255)

        return _spec_out(shape, mask, M, R, CC)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        """Multiscale textures: COLORSHOXX-style color zones married to macro texture field.
        UPGRADED: Adds warm/cool/edge color zones ON TOP of per-profile texture effects.
        - High-macro zones: warm color push (amber/gold tint) + brightening
        - Low-macro zones: cool shadow push (desaturate toward grey, darken, retain blue)
        - Edges (Sobel on macro): bright warm-white rim highlight"""
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape
        result = paint.copy()
        s = seed_offset % 10000

        # Macro-scale brightness modulation (also used as pv for color zones)
        macro = _multiscale_smooth_noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset)
        macro = np.clip(macro * 0.5 + 0.5, 0, 1)
        # Meso detail
        meso = _multiscale_smooth_noise(shape, [10, 18, 32], [0.32, 0.38, 0.30], seed + seed_offset + 100)
        meso = np.clip(meso * 0.5 + 0.5, 0, 1)

        if s == 7500:    # chrome_grain: horizontal streaks
            streak = _multiscale_smooth_noise(shape, [5, 11, 23], [0.42, 0.34, 0.24], seed + seed_offset + 300)
            streak = cv2.GaussianBlur(streak, (0, 0), sigmaX=7.0, sigmaY=0.7)
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] + streak * 0.12 * pm * mask, 0, 1)
        elif s == 7510:  # candy_frost: candy zones warm, frost zones cool
            warm = macro * 0.10 * pm
            cool = (1 - macro) * 0.08 * pm
            result[:,:,0] = np.clip(paint[:,:,0] + warm * mask, 0, 1)
            result[:,:,2] = np.clip(paint[:,:,2] + cool * mask, 0, 1)
        elif s == 7520:  # metal_grit: dark specks
            rng = np.random.RandomState(seed + seed_offset)
            specks = (rng.random((h, w)).astype(np.float32) > 0.90).astype(np.float32) * 0.20 * pm
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] - specks * mask, 0, 1)
        elif s == 7530:  # pearl_texture: iridescent hue shift via macro
            result[:,:,0] = np.clip(paint[:,:,0] + np.sin(macro * 6.28) * 0.10 * pm * mask, 0, 1)
            result[:,:,1] = np.clip(paint[:,:,1] + np.sin(macro * 6.28 + 2.09) * 0.08 * pm * mask, 0, 1)
            result[:,:,2] = np.clip(paint[:,:,2] + np.sin(macro * 6.28 + 4.19) * 0.11 * pm * mask, 0, 1)
        elif s == 7540:  # satin_weave: crosshatch brightness
            y, x = _mgrid(shape)
            sz_w = max(8, min(h, w) // 35)
            weave = np.sin(y * np.pi / sz_w) * np.cos(x * np.pi / sz_w) * 0.5 + 0.5
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] + (weave - 0.5) * 0.12 * pm * mask, 0, 1)
        elif s == 7550:  # chrome_sand: granular
            sand = _multiscale_smooth_noise(shape, [1, 2, 4], [0.40, 0.35, 0.25], seed + seed_offset + 300)
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] + sand * 0.14 * pm * mask, 0, 1)
        elif s == 7560:  # matte_silk: smooth sheen
            y_n = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
            sheen = np.sin(y_n * np.pi) * 0.14 * pm
            thread, cross = _multiscale_silk_surface(shape, seed, seed_offset, macro)
            hair = _multiscale_smooth_noise(shape, [1, 2, 4], [0.44, 0.34, 0.22], seed + seed_offset + 360)
            silk_detail = (thread * 0.075 + cross * 0.035 + hair * 0.030) * pm
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] + (sheen + silk_detail) * mask, 0, 1)
        elif s == 7570:  # flake_grain: large flake brightening
            bright = np.clip((macro - 0.4) * 2.5, 0, 1) * 0.18 * pm
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] + bright * mask, 0, 1)
        elif s == 7580:  # carbon_micro: weave lines
            y, x = _mgrid(shape)
            sz_c = max(4, min(h, w) // 55)
            weave_bright = np.maximum(np.abs(np.sin(y * np.pi / sz_c)), np.abs(np.sin(x * np.pi / sz_c * 0.7))) * 0.18 * pm
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] + weave_bright * mask * 0.5, 0, 1)
        else:  # frost_crystal: branching frost
            frost_a = _multiscale_smooth_noise(shape, [10, 20, 40], [0.3, 0.4, 0.3], seed + seed_offset + 300)
            frost_b = _multiscale_smooth_noise(shape, [2, 4, 9], [0.4, 0.35, 0.25], seed + seed_offset + 400)
            frost = np.exp(-np.abs(frost_a - frost_b) * 20) * 0.30 * pm
            result[:,:,2] = np.clip(paint[:,:,2] + frost * mask, 0, 1)
            result[:,:,1] = np.clip(paint[:,:,1] + frost * 0.45 * mask, 0, 1)
            result[:,:,0] = np.clip(paint[:,:,0] + frost * 0.25 * mask, 0, 1)

        # === COLORSHOXX color zones driven by macro texture field (all profiles) ===
        # Use combined pv from macro + meso for richer spatial variation
        pv = np.clip(macro * 0.7 + meso * 0.3, 0, 1)

        # High-pv zones: warm color push (amber/gold tint) + brightening
        warm_zone = np.clip((pv - 0.4) * 2.5, 0, 1).astype(np.float32)
        warm_blend = warm_zone * 0.18 * pm
        result[:,:,0] = np.clip(result[:,:,0] + warm_blend * mask * 0.10, 0, 1)   # warm red push
        result[:,:,1] = np.clip(result[:,:,1] + warm_blend * mask * 0.05, 0, 1)   # slight gold
        result[:,:,2] = np.clip(result[:,:,2] - warm_blend * mask * 0.04, 0, 1)   # reduce blue = warmer
        bright_ms = warm_zone * 0.12 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + bright_ms * mask, 0, 1)

        # Low-pv zones: cool desaturation + darkening
        cool_zone = np.clip((0.3 - pv) * 3.0, 0, 1).astype(np.float32)
        gray = (result[:,:,0] * 0.299 + result[:,:,1] * 0.587 + result[:,:,2] * 0.114)
        cool_desat = cool_zone * 0.18 * pm
        result[:,:,0] = np.clip(result[:,:,0] * (1 - cool_desat * mask) + gray * cool_desat * mask - cool_zone * 0.05 * pm * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] * (1 - cool_desat * mask) + gray * cool_desat * mask - cool_zone * 0.03 * pm * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] * (1 - cool_desat * mask * 0.7) + gray * cool_desat * mask * 0.7 + cool_zone * 0.02 * pm * mask, 0, 1)

        # Edges (Sobel on macro): bright warm-white rim highlight
        pv_dx = np.abs(np.diff(pv, axis=1, prepend=pv[:, :1]))
        pv_dy = np.abs(np.diff(pv, axis=0, prepend=pv[:1, :]))
        edge = np.clip(np.sqrt(pv_dx**2 + pv_dy**2) * 8, 0, 1)
        rim = edge * 0.18 * pm
        result[:,:,0] = np.clip(result[:,:,0] + rim * mask * 1.05, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + rim * mask * 1.00, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + rim * mask * 0.85, 0, 1)

        return result
    return spec_fn, paint_fn

spec_multiscale_chrome_grain, paint_multiscale_chrome_grain = _make_multiscale_fusion("chrome_grain", 7500)
spec_multiscale_candy_frost, paint_multiscale_candy_frost = _make_multiscale_fusion("candy_frost", 7510)
spec_multiscale_metal_grit, paint_multiscale_metal_grit = _make_multiscale_fusion("metal_grit", 7520)
spec_multiscale_pearl_texture, paint_multiscale_pearl_texture = _make_multiscale_fusion("pearl_texture", 7530)
spec_multiscale_satin_weave, paint_multiscale_satin_weave = _make_multiscale_fusion("satin_weave", 7540)
spec_multiscale_chrome_sand, paint_multiscale_chrome_sand = _make_multiscale_fusion("chrome_sand", 7550)
spec_multiscale_matte_silk, paint_multiscale_matte_silk = _make_multiscale_fusion("matte_silk", 7560)
spec_multiscale_flake_grain, paint_multiscale_flake_grain = _make_multiscale_fusion("flake_grain", 7570)
spec_multiscale_carbon_micro, paint_multiscale_carbon_micro = _make_multiscale_fusion("carbon_micro", 7580)
spec_multiscale_frost_crystal, paint_multiscale_frost_crystal = _make_multiscale_fusion("frost_crystal", 7590)


# ================================================================
# PARADIGM 7: WEATHER AND AGE - Environmental weathering
# ================================================================

def _make_weather_fusion(weather_type, seed_offset=0):
    """Factory: realistic environmental weathering simulation.
    Uses domain warping for organic boundaries, procedural techniques for
    rain streaks, oxidation, UV fade, dust accumulation, and salt corrosion.
    Weathered areas: low M (0-30), high R (120-220), high CC (100-200).
    Protected areas: original values preserved."""

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        rng = np.random.RandomState(seed + seed_offset)

        # Base vertical gradient (exposure direction)
        grad = _gradient_y(shape)

        # Domain warp for organic weathering boundary shapes
        warp1 = _noise(shape, [16, 32, 64], [0.25, 0.40, 0.35], seed + seed_offset)
        warp2 = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset + 10)
        # Second-order warp for more organic shapes
        warp_warp = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 20)
        warped_grad = np.clip(grad + warp1 * 0.25 + warp2 * warp_warp * 0.12, 0, 1)

        s = seed_offset % 10000
        if s == 7600:  # sun_fade: UV exposure from top, gradient from exposed to protected
            exposure = warped_grad  # top = exposed
            # UV-faded areas: lose metallic, become rough, clearcoat degrades
            M = np.clip(200 - exposure * 180 * sm, 0, 255)
            R = np.clip(30 + exposure * 170 * sm, 15, 255)
            CC = np.clip(16 + exposure * 174 * sm, 16, 255)
            # Micro-cracking from UV in heavily exposed areas
            cracks = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            crack_intensity = np.clip(exposure - 0.4, 0, 1) * 1.6
            R = R + np.abs(cracks) * 40 * crack_intensity * sm

        elif s == 7610:  # salt_spray: aggressive pitting with exposed bare metal
            salt_grad = 1.0 - warped_grad  # bottom = worst
            # Fractal salt pitting expanding from random seed points
            pit_noise = _noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + seed_offset + 100)
            pit_mask = np.clip((pit_noise - 0.2) * 3.0 * salt_grad, 0, 1)
            # Pitted areas: bare metal exposed (high M, very high R)
            M_pristine, R_pristine, CC_pristine = 200.0, 40.0, 16.0
            M_pitted, R_pitted, CC_pitted = 180.0, 200.0, 160.0
            M = M_pristine * (1 - pit_mask) + M_pitted * pit_mask
            R = R_pristine * (1 - pit_mask) + R_pitted * pit_mask
            CC = CC_pristine * (1 - pit_mask) + CC_pitted * pit_mask
            # Individual pit craters: tiny high-roughness points
            micro_pits = rng.random((h, w)).astype(np.float32)
            deep_pits = (micro_pits > 0.95).astype(np.float32) * pit_mask
            R = R + deep_pits * 55 * sm
            M = M - deep_pits * 60 * sm

        elif s == 7620:  # acid_rain: spot damage with chemical etching
            # Spot damage: random acid droplet impacts
            spots = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            spot_mask = np.clip((spots - 0.35) * 4.0, 0, 1)
            # Acid etching: roughens surface, strips metallic, damages clearcoat
            etch_depth = spot_mask * warped_grad
            M = np.clip(190 - etch_depth * 170 * sm, 0, 255)
            R = np.clip(35 + etch_depth * 185 * sm, 15, 255)
            CC = np.clip(16 + etch_depth * 159 * sm, 16, 255)
            # Chemical staining at spot edges
            edge_ring = np.exp(-((spot_mask - 0.5)**2) * 30) * warped_grad
            R = R + edge_ring * 35 * sm

        elif s == 7630:  # desert_blast: sand erosion
            sand_exposure = warped_grad
            # Sand-blasted: stripped of clearcoat, heavily roughened
            M = np.clip(195 - sand_exposure * 160 * sm, 0, 255)
            R = np.clip(40 + sand_exposure * 190 * sm, 15, 255)
            CC = np.clip(16 + sand_exposure * 189 * sm, 16, 255)
            # Wind-streak patterns
            streak = _noise(shape, [2, 8], [0.6, 0.4], seed + seed_offset + 100)
            streaks = np.clip(np.abs(streak) - 0.3, 0, 1) * sand_exposure
            R = R + streaks * 40 * sm

        elif s == 7640:  # ice_storm: frost and ice damage from bottom up
            ice_grad = 1.0 - warped_grad  # bottom = worst
            # Ice crystal pattern
            ice_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            ice_pattern = np.clip(ice_noise * ice_grad * 2, 0, 1)
            # Icy areas: high roughness (frost), moderate metallic, heavy CC
            M = np.clip(220 - ice_pattern * 130 * sm, 0, 255)
            R = np.clip(25 + ice_pattern * 160 * sm, 15, 255)
            CC = np.clip(16 + ice_pattern * 164 * sm, 16, 255)
            # Ice crystal edges are extra rough
            crystal_edge = _noise(shape, [2, 4, 6], [0.3, 0.4, 0.3], seed + seed_offset + 200)
            edge_mask = np.exp(-np.abs(ice_noise) * 8) * ice_grad
            R = R + edge_mask * 50 * sm

        elif s == 7650:  # road_spray: bottom-up road grime
            spray_grad = 1.0 - warped_grad  # bottom = worst
            # Layered grime: fine spray + heavier splatter
            fine_spray = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            fine_spray = np.clip(fine_spray * spray_grad * 2, 0, 1)
            splatter = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 200)
            splat_mask = np.clip((splatter - 0.3) * 3.0 * spray_grad, 0, 1)
            combined = np.clip(fine_spray * 0.6 + splat_mask * 0.4, 0, 1)
            # Grime: kills metallic, maxes roughness
            M = np.clip(200 - combined * 190 * sm, 0, 255)
            R = np.clip(45 + combined * 175 * sm, 15, 255)
            CC = np.clip(20 + combined * 150 * sm, 16, 255)

        elif s == 7660:  # hood_bake: heat damage on hood/roof areas
            heat_exposure = warped_grad  # top = hottest
            # Thermal cycling: clearcoat crazing, paint oxidation
            craze = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            craze_mask = np.clip(np.abs(craze) * heat_exposure * 3, 0, 1)
            M = np.clip(210 - heat_exposure * 100 * sm - craze_mask * 50 * sm, 0, 255)
            R = np.clip(30 + heat_exposure * 120 * sm + craze_mask * 60 * sm, 15, 255)
            CC = np.clip(200 * (1 - heat_exposure * sm) + craze_mask * 80 * sm, 16, 255)

        elif s == 7670:  # barn_dust: dust accumulation in recesses
            # Cavity-filling: smooth tops clean, recessed areas dusty
            cavity = _noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + seed_offset + 100)
            dust_mask = np.clip((cavity + 0.3) * warped_grad * 1.5, 0, 1)
            # Dust: zero metallic, very high roughness
            M = np.clip(185 - dust_mask * 175 * sm, 0, 255)
            R = np.clip(50 + dust_mask * 170 * sm, 15, 255)
            CC = np.clip(16 + dust_mask * 129 * sm, 16, 255)
            # Dust settles in noise patterns
            fine_dust = _noise(shape, [32, 64], [0.5, 0.5], seed + seed_offset + 200)
            R = R + np.abs(fine_dust) * 20 * dust_mask * sm

        elif s == 7680:  # ocean_mist: salt air corrosion
            salt_exposure = np.clip(warped_grad * 0.7 + 0.15, 0, 1)
            # Oxidation patches expanding from random seed points
            ox_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            ox_mask = np.clip((ox_noise - 0.1) * 2.5 * salt_exposure, 0, 1)
            # Oxidized: low M, high R, damaged CC
            M = np.clip(195 - ox_mask * 165 * sm, 0, 255)
            R = np.clip(40 + ox_mask * 180 * sm, 15, 255)
            CC = np.clip(60 + ox_mask * 120 * sm, 16, 255)
            # White salt deposits
            salt_crystals = rng.random((h, w)).astype(np.float32)
            salt_spots = (salt_crystals > 0.94).astype(np.float32) * ox_mask
            R = R + salt_spots * 40 * sm
            M = np.clip(M + salt_spots * 60 * sm, 0, 255)  # salt = slightly reflective

        else:  # 7690 volcanic_ash: ash fall and heat
            ash_fall = warped_grad  # top gets most ash
            ash_noise = _noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + seed_offset + 100)
            ash_mask = np.clip((ash_noise + 0.2) * ash_fall * 1.8, 0, 1)
            # Ash: kills all metallic, extreme roughness
            M = np.clip(170 - ash_mask * 165 * sm, 0, 255)
            R = np.clip(55 + ash_mask * 195 * sm, 15, 255)
            CC = np.clip(16 + ash_mask * 184 * sm, 16, 255)
            # Heat-warped spots under ash
            heat = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 200)
            heat_spots = np.clip((heat - 0.4) * 3.0 * ash_fall, 0, 1)
            M = M + heat_spots * 40 * sm  # heat can reveal metal

        # Rain streaks: vertical thin bright lines (applied to all weather types)
        # SPB-100 tick 94 (owner: "Weather & Age needs SIGNIFICANT work").
        # Frequency bump 16 → 64 = ~4× finer streaks at car-body 2048².
        rain = _noise(shape, [4, 32, 64], [0.40, 0.32, 0.28], seed + seed_offset + 500)
        rain_streaks = np.clip(np.abs(rain) - 0.55, 0, 1) * 2.8 * warped_grad
        R = np.clip(R + rain_streaks * 42 * sm, 15, 255)  # was 25 - now stronger

        # SPB-99 P2 tick-94 round 2: per-band chroma over weathered regions.
        # Quantize warped_grad into 8 bands and hash each so M/R/CC vary in
        # shade across the weathering field. Round-1 used (0.78 + h*0.44)
        # which was too aggressive and dropped mean signal (Weather mean
        # 26.6 → 24.3 regression). Tightened to (0.92 + h*0.16) so chroma
        # adds 8% variation without cratering M5.
        wb = np.floor(warped_grad * 8.0).astype(np.float32)
        wh_raw = np.sin(wb * 12.9898 + (seed % 1000) * 0.011) * 43758.5453
        wh = (wh_raw - np.floor(wh_raw)).astype(np.float32)
        chroma_mod = (0.92 + wh * 0.16).astype(np.float32)
        M = np.clip(M * chroma_mod, 0, 255)
        CC = np.clip(CC * chroma_mod, 16, 255)
        # R gets a smaller inverse hash so high-chroma bands stay slightly
        # smoother while dark bands are rougher.
        R = np.clip(R * (1.08 - wh * 0.08), 15, 255)

        fields = _weather_spb67_fields(shape, seed, seed_offset)
        micro = fields["micro"]
        powder = fields["powder"]
        scratch = fields["scratch"]
        pin = fields["pin"]
        rings = fields["rings"]
        tide = fields["tide"]
        heat = fields["heat"]
        panel = fields["panel"]
        wind = fields["wind"]
        crackle = fields["crackle"]
        top = warped_grad
        bottom = 1.0 - warped_grad

        if s == 7600:  # sun_fade: chalked paint, hairline clear failure
            reveal = np.clip(top * (0.45 + 0.55 * crackle), 0, 1)
            chalk = np.clip(top * (0.35 + 0.65 * powder), 0, 1)
            M = M - reveal * 38.0 * sm + pin * top * 34.0 * sm
            R = R + chalk * 46.0 * sm + scratch * top * 38.0 * sm
            CC = CC - crackle * top * 44.0 * sm + pin * top * 20.0 * sm
        elif s == 7610:  # salt_spray: crystalline tide creep and edge pitting
            salt_lines = np.clip(tide * bottom + pin * bottom * 0.8, 0, 1)
            pit_edge = np.clip((rings + scratch) * bottom, 0, 1)
            M = M - salt_lines * 70.0 * sm + pit_edge * 28.0 * sm
            R = R + salt_lines * 58.0 * sm + pit_edge * 34.0 * sm
            CC = CC + salt_lines * 32.0 * sm - pit_edge * 20.0 * sm
        elif s == 7620:  # acid_rain: etched droplet rings and chemical halos
            etch_rings = np.clip(rings * top + pin * 0.35, 0, 1)
            burn_edge = np.clip(np.abs(etch_rings - 0.48) * 2.2, 0, 1) * top
            M = M - etch_rings * 54.0 * sm + burn_edge * 22.0 * sm
            R = R + etch_rings * 64.0 * sm + burn_edge * 38.0 * sm
            CC = CC - etch_rings * 42.0 * sm + burn_edge * 22.0 * sm
        elif s == 7630:  # desert_blast: wind-polished leading scratches
            blast = np.clip(wind * top + scratch * 0.55, 0, 1)
            M = M - blast * 44.0 * sm + pin * top * 24.0 * sm
            R = R + blast * 52.0 * sm + powder * top * 20.0 * sm
            CC = CC - blast * 38.0 * sm
        elif s == 7640:  # ice_storm: frost facets over wet clear pockets
            frost = np.clip((rings + tide * 0.7 + pin) * bottom, 0, 1)
            M = M - frost * 42.0 * sm + pin * bottom * 18.0 * sm
            R = R + frost * 48.0 * sm - tide * bottom * 18.0 * sm
            CC = CC + frost * 48.0 * sm + tide * bottom * 22.0 * sm
        elif s == 7650:  # road_spray: chip trails, tar flecks, rubbed lower edge
            grit = np.clip((pin * 1.4 + scratch * 0.6 + wind * 0.35) * bottom, 0, 1)
            M = M - grit * 66.0 * sm + pin * bottom * 52.0 * sm
            R = R + grit * 58.0 * sm
            CC = CC - grit * 34.0 * sm
        elif s == 7660:  # hood_bake: heat crazing and ghost repair-panel lines
            cooked = np.clip((heat + crackle * 0.75 + panel * 0.35) * top, 0, 1)
            M = M - cooked * 36.0 * sm + heat * top * 18.0 * sm
            R = R + cooked * 58.0 * sm
            CC = CC - crackle * top * 48.0 * sm + heat * top * 26.0 * sm
        elif s == 7670:  # barn_dust: settled shelf dust with barely visible panel ghosts
            settled = np.clip(powder * top + panel * 0.42 + pin * 0.5, 0, 1)
            M = M - settled * 68.0 * sm
            R = R + settled * 56.0 * sm + scratch * 18.0 * sm
            CC = CC - settled * 24.0 * sm + panel * 14.0 * sm
        elif s == 7680:  # ocean_mist: wave crests, shell glints, salt film
            wave_reveal = np.clip(tide * (0.35 + 0.65 * top) + rings * 0.35 + pin * 0.45, 0, 1)
            M = M - wave_reveal * 44.0 * sm + pin * 40.0 * sm
            R = R + wave_reveal * 54.0 * sm
            CC = CC + tide * top * 38.0 * sm - rings * 14.0 * sm
        else:  # volcanic_ash: abrasive ash granules and heat-hot cracks
            ash = np.clip((powder + pin * 1.2 + heat * 0.45) * top, 0, 1)
            M = M - ash * 58.0 * sm + heat * top * 34.0 * sm
            R = R + ash * 66.0 * sm
            CC = CC - ash * 28.0 * sm + heat * top * 20.0 * sm

        # 2026-04-25 — universal fine-grain surface modulation breaks up
        # the broad-blob flat regions that the per-type weather fields
        # produce. Applied AFTER the per-type branch so each weather's
        # distinctive look is preserved; this just adds painter-resolution
        # surface character (Item 3 broad-blob fix; Iter 9 audit found
        # ice_storm 0.84 / volcanic_ash 0.84 / road_spray 0.76 etc.).
        wgrain = _fractal_surface_grain(shape, seed + seed_offset + 600)
        wgrain_centered = (wgrain - 0.5) * 2.0
        M = M * (0.90 + 0.18 * wgrain) + (micro - 0.5) * 24.0 * sm
        R = R * (0.90 + 0.18 * (1.0 - wgrain)) + (powder - 0.5) * 22.0 * sm
        CC = CC + wgrain_centered * 18.0 + (scratch - 0.5) * 16.0 * sm

        M = np.clip(M, 0, 255)
        R = np.clip(R, 15, 255)  # GGX floor
        CC = np.clip(CC, 16, 255)
        return _spec_out(shape, mask, M, R, CC)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape
        result = paint.copy()

        grad = _gradient_y(shape)
        warp1 = _noise(shape, [16, 32, 64], [0.25, 0.40, 0.35], seed + seed_offset)
        warped_grad = np.clip(grad + warp1 * 0.25, 0, 1)

        s = seed_offset % 10000
        if s == 7600:  # sun_fade: desaturate exposed areas
            gray = paint[:,:,:3].mean(axis=2)
            desat = warped_grad * 0.25 * pm
            for c in range(3):
                result[:,:,c] = np.clip(result[:,:,c] * (1 - desat * mask) + gray * desat * mask, 0, 1)
            # Warm yellowing in faded areas
            result[:,:,0] = np.clip(result[:,:,0] + warped_grad * 0.08 * pm * mask, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + warped_grad * 0.04 * pm * mask, 0, 1)

        elif s == 7610:  # salt_spray: white salt deposits and rust staining
            pit_noise = _noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + seed_offset + 100)
            pit_mask = np.clip((pit_noise - 0.2) * 3.0 * (1 - warped_grad), 0, 1)
            # Rust orange-brown staining
            result[:,:,0] = np.clip(result[:,:,0] + pit_mask * 0.15 * pm * mask, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] - pit_mask * 0.10 * pm * mask, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] - pit_mask * 0.18 * pm * mask, 0, 1)

        elif s == 7620:  # acid_rain: greenish chemical staining
            spots = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            spot_mask = np.clip((spots - 0.35) * 4.0 * warped_grad, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + spot_mask * 0.06 * pm * mask, 0, 1)
            result[:,:,0] = np.clip(result[:,:,0] - spot_mask * 0.08 * pm * mask, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] - spot_mask * 0.06 * pm * mask, 0, 1)

        elif s == 7630:  # desert_blast: sandy brown tint
            result[:,:,0] = np.clip(result[:,:,0] + warped_grad * 0.10 * pm * mask, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + warped_grad * 0.06 * pm * mask, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] - warped_grad * 0.08 * pm * mask, 0, 1)
            # Darken heavily blasted areas
            dark = np.clip(warped_grad - 0.6, 0, 1) * 0.20 * pm
            for c in range(3):
                result[:,:,c] = np.clip(result[:,:,c] - dark * mask, 0, 1)

        elif s == 7640:  # ice_storm: blue-white frost overlay
            ice_grad = 1.0 - warped_grad
            result[:,:,2] = np.clip(result[:,:,2] + ice_grad * 0.12 * pm * mask, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + ice_grad * 0.06 * pm * mask, 0, 1)
            # Frost brightening
            frost_bright = ice_grad * 0.10 * pm
            for c in range(3):
                result[:,:,c] = np.clip(result[:,:,c] + frost_bright * mask, 0, 1)

        elif s == 7650:  # road_spray: brown/gray grime
            spray_grad = 1.0 - warped_grad
            grime = spray_grad * 0.18 * pm
            result[:,:,0] = np.clip(result[:,:,0] - grime * 0.3 * mask, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] - grime * 0.4 * mask, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] - grime * 0.55 * mask, 0, 1)

        elif s == 7660:  # hood_bake: warm yellowing from heat
            result[:,:,0] = np.clip(result[:,:,0] + warped_grad * 0.12 * pm * mask, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + warped_grad * 0.06 * pm * mask, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] - warped_grad * 0.04 * pm * mask, 0, 1)

        elif s == 7670:  # barn_dust: warm brown dust layer
            cavity = _noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + seed_offset + 100)
            dust_mask = np.clip((cavity + 0.3) * warped_grad * 1.5, 0, 1)
            result[:,:,0] = np.clip(result[:,:,0] - dust_mask * 0.05 * pm * mask, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] - dust_mask * 0.10 * pm * mask, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] - dust_mask * 0.16 * pm * mask, 0, 1)

        elif s == 7680:  # ocean_mist: greenish patina
            ox_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            ox_mask = np.clip((ox_noise - 0.1) * 2.5 * warped_grad, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + ox_mask * 0.08 * pm * mask, 0, 1)
            result[:,:,0] = np.clip(result[:,:,0] - ox_mask * 0.06 * pm * mask, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] - ox_mask * 0.04 * pm * mask, 0, 1)

        else:  # volcanic_ash: dark gray-brown ash layer
            ash_mask = np.clip(warped_grad * 1.5, 0, 1)
            darken = ash_mask * 0.16 * pm
            for c in range(3):
                result[:,:,c] = np.clip(result[:,:,c] - darken * mask, 0, 1)
            # Warm undertone from heat
            result[:,:,0] = np.clip(result[:,:,0] + ash_mask * 0.04 * pm * mask, 0, 1)

        # 2026-04-25 — universal paint-side fine-grain so the weather
        # surfaces show painter-resolution material character on top of
        # the per-type tinting (Item 3 broad-blob fix companion to the
        # spec-side wgrain).
        fields = _weather_spb67_fields(shape, seed, seed_offset)
        micro = fields["micro"]
        powder = fields["powder"]
        scratch = fields["scratch"]
        pin = fields["pin"]
        rings = fields["rings"]
        tide = fields["tide"]
        heat = fields["heat"]
        panel = fields["panel"]
        wind = fields["wind"]
        crackle = fields["crackle"]
        top = warped_grad
        bottom = 1.0 - warped_grad
        active = mask[:, :, np.newaxis].astype(np.float32)

        if s == 7600:
            tint = np.stack([0.08 * top + 0.04 * pin, 0.04 * top - 0.02 * crackle, -0.07 * top - 0.03 * powder], axis=2)
            luma = (powder - 0.5) * 0.105 + crackle * top * 0.075 + (micro - 0.5) * 0.125 + scratch * top * 0.080
        elif s == 7610:
            salt = np.clip(tide * bottom + pin * bottom, 0, 1)
            tint = np.stack([0.09 * rings * bottom - 0.06 * salt, 0.03 * bottom + 0.04 * salt, -0.10 * bottom + 0.02 * salt], axis=2)
            luma = salt * 0.075 - scratch * bottom * 0.045 + (micro - 0.5) * 0.050
        elif s == 7620:
            etch = np.clip(rings * top + pin * 0.45, 0, 1)
            tint = np.stack([-0.10 * etch, 0.08 * etch + 0.03 * powder, -0.06 * etch], axis=2)
            luma = (micro - 0.5) * 0.165 - etch * 0.055 + scratch * top * 0.060 + rings * top * 0.035
        elif s == 7630:
            blast = np.clip(wind * top + scratch * 0.5, 0, 1)
            tint = np.stack([0.10 * top + 0.04 * blast, 0.05 * top + 0.03 * powder, -0.09 * top - 0.03 * blast], axis=2)
            luma = wind * top * 0.120 + (micro - 0.5) * 0.120 + scratch * top * 0.075 + powder * top * 0.035
        elif s == 7640:
            frost = np.clip((rings + tide + pin) * bottom, 0, 1)
            tint = np.stack([0.04 * frost, 0.08 * frost, 0.13 * frost], axis=2)
            luma = frost * 0.080 + (micro - 0.5) * 0.035
        elif s == 7650:
            grime = np.clip((powder + pin + scratch * 0.5) * bottom, 0, 1)
            tint = np.stack([-0.08 * grime + 0.04 * pin * bottom, -0.10 * grime, -0.13 * grime], axis=2)
            luma = -grime * 0.115 + pin * bottom * 0.070 + (micro - 0.5) * 0.170 + scratch * bottom * 0.125 + wind * bottom * 0.080
        elif s == 7660:
            cooked = np.clip((heat + crackle + panel * 0.3) * top, 0, 1)
            tint = np.stack([0.12 * cooked, 0.04 * cooked - 0.03 * crackle, -0.08 * cooked], axis=2)
            luma = heat * top * 0.055 - crackle * top * 0.040
        elif s == 7670:
            dust = np.clip(powder * top + panel * 0.35 + pin * 0.35, 0, 1)
            tint = np.stack([0.03 * dust, -0.06 * dust, -0.12 * dust], axis=2)
            luma = dust * 0.110 + panel * 0.055 - scratch * 0.050 + (micro - 0.5) * 0.110 + powder * 0.035
        elif s == 7680:
            mist = np.clip(tide * top + rings * 0.35 + pin * 0.35, 0, 1)
            tint = np.stack([-0.08 * mist, 0.08 * mist + 0.03 * powder, 0.04 * tide], axis=2)
            luma = tide * top * 0.060 + pin * 0.040 - rings * 0.020
        else:
            ash = np.clip((powder + pin + heat * 0.45) * top, 0, 1)
            tint = np.stack([-0.08 * ash + 0.08 * heat * top, -0.09 * ash - 0.02 * heat * top, -0.10 * ash - 0.04 * heat * top], axis=2)
            luma = -ash * 0.110 + heat * top * 0.095 + pin * 0.070 + (micro - 0.5) * 0.310 + scratch * top * 0.185 + wind * top * 0.140

        result = np.clip(result + active * pm * (tint + luma[:, :, np.newaxis]), 0, 1)

        wgrain = _fractal_surface_grain(shape, seed + seed_offset + 700)
        wgrain_centered = (wgrain - 0.5) * 2.0
        # Subtle luminance perturbation per channel; cooler in warped-low
        # zones, warmer in warped-high zones — adds material variation
        # without overwhelming the per-type look.
        micro = wgrain_centered * 0.05 * pm
        result[:,:,0] = np.clip(result[:,:,0] + micro * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + micro * 0.85 * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + micro * 0.7 * mask, 0, 1)

        # SPB-81 (2026-05-15): _fractal_surface_grain defaults to scales (3,6,14)
        # which are ~145px features at 2048 canvas = macro structure, not the
        # fine grain weathered surfaces need (grain, pit-dust, salt-deposit
        # speckle, ash, etc.). Add an additional high-octave grain block at
        # 256/512/1024 to deliver the paintFineEnergy that the Weather & Age
        # category profile (M6) expects. Same template as SPB-80 quilts.
        #
        # Tick 27 (2026-05-15): bumped amplitude 0.060 → 0.090 + added a
        # second mid-fine band (octaves 128/256) for the sparse-damage
        # weathers (salt_spray, barn_dust, ocean_mist, acid_rain) which
        # left most of the surface untouched at tier 1. The mid-fine band
        # adds visible mid-scale grain that survives thumbnail downsample
        # even where the per-type damage mask is sparse.
        try:
            # Three frequency layers:
            #   mid (32/64/128) — 16-64px features, drives M8 macro_std32
            #   fine (256/512)  — 4-8px features, drives M6 paintFineEnergy
            #   micro (1024)    — sub-pixel sparkle on the real car at 2048
            mid_band = _noise(shape, [32, 64, 128], [0.4, 0.35, 0.25], seed + seed_offset + 818)
            fine_grain = _noise(shape, [256, 512], [0.55, 0.45], seed + seed_offset + 808)
            micro_band = _noise(shape, [1024], [1.0], seed + seed_offset + 828)
        except Exception:
            _rng = np.random.RandomState(seed + seed_offset + 808)
            mid_band = _rng.random((h, w)).astype(np.float32)
            fine_grain = _rng.random((h, w)).astype(np.float32)
            micro_band = _rng.random((h, w)).astype(np.float32)
        fine_amp = (
            (mid_band  - 0.5) * 0.080 +    # bulk of macro_std32 lift
            (fine_grain - 0.5) * 0.060 +   # paintFineEnergy contribution
            (micro_band - 0.5) * 0.040     # sub-pixel sparkle on real car
        ) * pm * mask
        result[:,:,0] = np.clip(result[:,:,0] + fine_amp, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + fine_amp, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + fine_amp, 0, 1)

        return result
    return spec_fn, paint_fn

spec_weather_sun_fade, paint_weather_sun_fade = _make_weather_fusion("sun_fade", 7600)
spec_weather_salt_spray, paint_weather_salt_spray = _make_weather_fusion("salt_spray", 7610)
spec_weather_acid_rain, paint_weather_acid_rain = _make_weather_fusion("acid_rain", 7620)
spec_weather_desert_blast, paint_weather_desert_blast = _make_weather_fusion("desert_blast", 7630)
spec_weather_ice_storm, paint_weather_ice_storm = _make_weather_fusion("ice_storm", 7640)
spec_weather_road_spray, paint_weather_road_spray = _make_weather_fusion("road_spray", 7650)
spec_weather_hood_bake, paint_weather_hood_bake = _make_weather_fusion("hood_bake", 7660)
spec_weather_barn_dust, paint_weather_barn_dust = _make_weather_fusion("barn_dust", 7670)
spec_weather_ocean_mist, paint_weather_ocean_mist = _make_weather_fusion("ocean_mist", 7680)
spec_weather_volcanic_ash, paint_weather_volcanic_ash = _make_weather_fusion("volcanic_ash", 7690)


# ================================================================
# PARADIGM 8: EXOTIC PHYSICS - Unusual material combinations
# ================================================================

# ================================================================
# PARADIGM 8: EXOTIC PHYSICS - 10 unique bespoke engines
# Each finish is entirely different - NO shared factory template
# ================================================================

def _hex_cell_dist(shape, sz):
    """True hexagonal distance field."""
    y, x = _mgrid(shape)
    yf, xf = y.astype(np.float32), x.astype(np.float32)
    row_f = yf / (sz * 0.866)
    col_f = xf / sz
    r_floor = np.round(row_f)
    even_row = (r_floor.astype(np.int32) % 2 == 0).astype(np.float32)
    col_shifted = col_f - 0.5 * (1 - even_row)
    c_floor = np.round(col_shifted)
    cy = r_floor * sz * 0.866
    cx = (c_floor + 0.5 * (1 - even_row)) * sz
    dy = (yf - cy) / (sz * 0.5)
    dx = (xf - cx) / (sz * 0.5)
    # True hex metric
    hex_d = np.maximum(np.abs(dx), (np.abs(dx) + np.abs(dy) * 1.732) * 0.5)
    return np.clip(hex_d, 0, 1)

# 1. EXOTIC GLASS - Caustic network glass with thin-film interference
def _spec_exotic_glass(shape, mask, seed, sm):
    h, w = shape
    # --- Resolution cap: compute at 512 max, upscale ---
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    rng = np.random.RandomState(seed + 7700)
    # --- Voronoi caustic network ---
    n_pts = 60
    pts_y = rng.rand(n_pts).astype(np.float32) * sh
    pts_x = rng.rand(n_pts).astype(np.float32) * sw
    y_g, x_g = _mgrid((sh, sw))
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    # Domain warp the coordinates for organic caustic shapes
    warp_y = _noise((sh, sw), [16, 32, 64], [0.3, 0.4, 0.3], seed + 7701)
    warp_x = _noise((sh, sw), [16, 32, 64], [0.3, 0.4, 0.3], seed + 7702)
    yf_w = yf + warp_y * 40 * sh / h
    xf_w = xf + warp_x * 40 * sw / w
    d1 = np.full((sh, sw), 1e9, dtype=np.float32)  # nearest
    d2 = np.full((sh, sw), 1e9, dtype=np.float32)  # second nearest
    for py, px in zip(pts_y, pts_x):
        d = np.sqrt((yf_w - py)**2 + (xf_w - px)**2)
        update2 = d < d2
        d2 = np.where(update2, d, d2)
        swap = d2 < d1
        d1_old = d1.copy()
        d1 = np.where(swap, d2, d1)
        d2 = np.where(swap, d1_old, d2)
    # Caustic = edge between cells (where d2 - d1 is small)
    edge_dist = (d2 - d1)
    max_ed = np.percentile(edge_dist, 95) + 1e-6
    edge_norm = np.clip(edge_dist / max_ed, 0, 1)
    caustic = np.exp(-edge_norm * 4.0)  # sharp bright caustic lines
    film_thickness = d1 / (np.percentile(d1, 90) + 1e-6)
    # Glass base: M=0, low R, CC tracks caustic network
    M = np.clip(caustic * 100 * sm + caustic**2 * 40 * sm, 0, 140)
    G = np.clip(2.0 + (1.0 - caustic) * 130 * sm + caustic * 50 * sm, 0, 180)
    CC = np.clip(16.0 + (1.0 - caustic) * 120 - caustic * 12, 16, 160)  # CC≥16
    # Swimming-pool ripple modulation
    ripple = np.sin(film_thickness * 18.0 + warp_y * 8.0) * 0.5 + 0.5
    CC = np.clip(CC + ripple * 40 * sm, 16, 200)  # CC≥16
    mask_s = cv2.resize(mask.astype(np.float32), (sw, sh), interpolation=cv2.INTER_LINEAR) if ds > 1 else mask
    spec_small = _spec_out((sh, sw), mask_s, M, G, CC)
    if ds > 1:
        spec = np.zeros((h, w, 4), dtype=np.uint8)
        for ch in range(4):
            spec[:, :, ch] = cv2.resize(spec_small[:, :, ch].astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.uint8)
        return spec
    return spec_small

def _paint_exotic_glass(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    # --- Resolution cap: compute glass fields at 512 max, upscale ---
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    rng = np.random.RandomState(seed + 7700)
    n_pts = 60
    pts_y = rng.rand(n_pts).astype(np.float32) * sh
    pts_x = rng.rand(n_pts).astype(np.float32) * sw
    y_g, x_g = _mgrid((sh, sw))
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    warp_y = _noise((sh, sw), [16, 32, 64], [0.3, 0.4, 0.3], seed + 7701)
    warp_x = _noise((sh, sw), [16, 32, 64], [0.3, 0.4, 0.3], seed + 7702)
    yf_w = yf + warp_y * 40 * sh / h
    xf_w = xf + warp_x * 40 * sw / w
    d1 = np.full((sh, sw), 1e9, dtype=np.float32)
    for py, px in zip(pts_y, pts_x):
        d = np.sqrt((yf_w - py)**2 + (xf_w - px)**2)
        d1 = np.minimum(d1, d)
    film_s = d1 / (np.percentile(d1, 90) + 1e-6)
    film = cv2.resize(film_s, (w, h), interpolation=cv2.INTER_LINEAR) if ds > 1 else film_s
    # Thin-film interference: rainbow color shift
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + np.sin(film * 12.0) * 0.12 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + np.sin(film * 12.0 + 2.094) * 0.10 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + np.sin(film * 12.0 + 4.189) * 0.14 * pm * mask, 0, 1)
    # Brighten caustic network lines
    caustic_n_s = _noise((sh, sw), [8, 16, 32], [0.3, 0.4, 0.3], seed + 7703)
    caustic_n = cv2.resize(caustic_n_s, (w, h), interpolation=cv2.INTER_LINEAR) if ds > 1 else caustic_n_s
    bright = np.exp(-np.abs(caustic_n) * 3.0) * 0.15 * pm
    for c in range(3):
        result[:,:,c] = np.clip(result[:,:,c] + bright * mask, 0, 1)
    return result

spec_exotic_glass_paint = _spec_exotic_glass
paint_exotic_glass_paint = _paint_exotic_glass

# 2. EXOTIC FOGGY CHROME - Condensation physics chrome with multi-scale droplets
def _exotic_foggy_chrome_droplets(shape, seed):
    h, w = shape
    ds = max(1, int(np.ceil(min(h, w) / 512.0)))
    sh, sw = max(64, h // ds), max(64, w // ds)
    rng = np.random.RandomState(seed + 7710)
    y_g, x_g = _mgrid((sh, sw))
    coords = np.column_stack([y_g.ravel(), x_g.ravel()])
    droplet_field = np.zeros((sh, sw), dtype=np.float32)
    for n_pts, radius, weight in [
        (15, 80 * sh / h, 0.5),
        (80, 30 * sh / h, 0.3),
        (400, 8 * sh / h, 0.2),
    ]:
        pts = np.column_stack([
            rng.rand(n_pts).astype(np.float32) * sh,
            rng.rand(n_pts).astype(np.float32) * sw,
        ])
        d = cKDTree(pts).query(coords, k=1, workers=-1)[0].reshape(sh, sw).astype(np.float32)
        droplet_field += (np.clip(1.0 - d / max(radius, 1e-3), 0, 1) ** 2.0) * weight
    droplet_field = np.clip(droplet_field, 0, 1)
    if ds > 1:
        droplet_field = cv2.resize(droplet_field, (w, h), interpolation=cv2.INTER_LINEAR)
    return droplet_field

def _spec_exotic_foggy_chrome(shape, mask, seed, sm):
    h, w = shape
    droplet_field = _exotic_foggy_chrome_droplets(shape, seed)
    M = np.clip(255.0 - droplet_field * 40 * sm, 210, 255)
    G = np.clip(2.0 + droplet_field * 180 * sm, 2, 200)
    # Droplet edges have ultra-smooth meniscus (surface tension)
    edge_detect = np.abs(np.gradient(droplet_field, axis=0)) + np.abs(np.gradient(droplet_field, axis=1))
    edge_detect = np.clip(edge_detect * 15, 0, 1)
    G = np.clip(G - edge_detect * 80 * sm, 0, 200)
    CC = np.clip(16.0 + droplet_field * 100 + (1.0 - droplet_field) * 20, 16, 140)
    ds = max(1, int(np.ceil(min(h, w) / 512.0)))
    sh, sw = max(64, h // ds), max(64, w // ds)
    micro = _noise((sh, sw), [2, 4, 8], [0.3, 0.4, 0.3], seed + 7712)
    if ds > 1:
        micro = cv2.resize(micro, (w, h), interpolation=cv2.INTER_LINEAR)
    G = np.clip(G + micro * 12 * sm * droplet_field, 0, 220)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_foggy_chrome(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    droplet_field = _exotic_foggy_chrome_droplets(shape, seed)
    result = paint.copy()
    gray = paint.mean(axis=2, keepdims=True)
    fog_blend = droplet_field * 0.3 * pm
    result = result * (1 - fog_blend[:,:,np.newaxis]) + gray * fog_blend[:,:,np.newaxis]
    result[:,:,2] = np.clip(result[:,:,2] + droplet_field * 0.08 * pm * mask, 0, 1)
    result[:,:,0] = np.clip(result[:,:,0] - droplet_field * 0.04 * pm * mask, 0, 1)
    return np.clip(result, 0, 1)

spec_exotic_foggy_chrome = _spec_exotic_foggy_chrome
paint_exotic_foggy_chrome = _paint_exotic_foggy_chrome

# 3. EXOTIC INVERTED CANDY - Negative-refraction metamaterial with Turing patterns
def _exotic_inverted_candy_turing(shape, seed):
    h, w = shape
    ds = max(1, int(np.ceil(min(h, w) / 512.0)))
    sh, sw = max(64, h // ds), max(64, w // ds)
    rng = np.random.RandomState(seed + 7720)
    U = np.ones((sh, sw), dtype=np.float32)
    V = np.zeros((sh, sw), dtype=np.float32)
    for _ in range(22):
        cy, cx = rng.randint(0, max(1, sh)), rng.randint(0, max(1, sw))
        r = rng.randint(4, max(5, min(18, max(sh, sw) // 24)))
        y1, y2 = max(0, cy-r), min(sh, cy+r)
        x1, x2 = max(0, cx-r), min(sw, cx+r)
        V[y1:y2, x1:x2] = 1.0
        U[y1:y2, x1:x2] = 0.5
    def _lap_ic(arr):
        pad = np.pad(arr, 1, mode="wrap")
        return (pad[:-2,1:-1] + pad[2:,1:-1] + pad[1:-1,:-2] + pad[1:-1,2:] - 4*arr) * 0.25
    for _ in range(46):
        uvv = U * V * V
        U = np.clip(U + 0.16 * _lap_ic(U) - uvv + 0.055 * (1.0 - U), 0, 1)
        V = np.clip(V + 0.08 * _lap_ic(V) + uvv - 0.117 * V, 0, 1)
    turing = V / (V.max() + 1e-6)
    if ds > 1:
        turing = cv2.resize(turing, (w, h), interpolation=cv2.INTER_LINEAR)
    return turing

def _spec_exotic_inverted_candy(shape, mask, seed, sm):
    h, w = shape
    turing = _exotic_inverted_candy_turing(shape, seed)
    M = np.clip((1.0 - turing) * 240 * sm + turing * 15, 0, 255)
    G = np.clip(turing * 220 * sm + (1.0 - turing) * 5, 0, 240)
    CC = np.clip((1.0 - turing) * 200 + turing * 16, 16, 220)
    fine = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7721)
    M = np.clip(M + fine * 15 * sm, 0, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_inverted_candy(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    turing = _exotic_inverted_candy_turing(shape, seed)
    result = paint.copy()
    ds = max(1, int(np.ceil(min(h, w) / 512.0)))
    sh, sw = max(64, h // ds), max(64, w // ds)
    hue_phase = _noise((sh, sw), [16, 32], [0.5, 0.5], seed + 7725)
    if ds > 1:
        hue_phase = cv2.resize(hue_phase, (w, h), interpolation=cv2.INTER_LINEAR)
    hue_phase = hue_phase * 3.14
    result[:,:,0] = np.clip(paint[:,:,0] + np.sin(hue_phase) * turing * 0.15 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + np.sin(hue_phase + 2.094) * turing * 0.12 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + np.sin(hue_phase + 4.189) * turing * 0.18 * pm * mask, 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    desat = (1.0 - turing) * 0.2 * pm
    result = result * (1 - desat[:,:,np.newaxis]) + gray * desat[:,:,np.newaxis]
    return np.clip(result, 0, 1)

spec_exotic_inverted_candy = _spec_exotic_inverted_candy
paint_exotic_inverted_candy = _paint_exotic_inverted_candy

# 4. EXOTIC LIQUID GLASS - Navier-Stokes viscous flow simulation
def _spec_exotic_liquid_glass(shape, mask, seed, sm):
    h, w = shape
    y_g, x_g = _mgrid(shape)
    yf = y_g.astype(np.float32) / max(1, h)
    xf = x_g.astype(np.float32) / max(1, w)
    warp1 = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7730)
    warp2 = _noise(shape, [2, 4, 8], [0.35, 0.4, 0.25], seed + 7731)
    gravity = yf ** 1.5
    stream1 = np.sin((xf * 12.0 + warp1 * 2.5) * 3.14159) * 0.5 + 0.5
    stream2 = np.sin((xf * 8.0 + warp2 * 3.0 + yf * 2.0) * 3.14159) * 0.5 + 0.5
    stream3 = np.sin((xf * 20.0 + warp1 * 1.5 - warp2 * 2.0) * 3.14159) * 0.5 + 0.5
    flow = (stream1 * 0.4 + stream2 * 0.35 + stream3 * 0.25)
    thickness = flow * (0.3 + gravity * 0.7)
    thin_top = np.clip(1.0 - yf * 3.0, 0, 1) * 0.6
    thickness = np.clip(thickness - thin_top, 0, 1)
    pool = np.clip((yf - 0.75) * 4.0, 0, 1)
    thickness = np.clip(thickness + pool * 0.5, 0, 1)
    M = np.clip(thickness * 70 * sm + thickness**2 * 30 * sm, 0, 100)
    G = np.clip((1.0 - thickness) * 200 * sm + 3, 3, 220)
    CC = np.clip(16.0 + (1.0 - thickness) * 120, 16, 140)
    ripple = np.sin(yf * 60.0 + warp1 * 15.0) * thickness * 0.5 + 0.5
    G = np.clip(G + ripple * 20 * sm * (1.0 - thickness), 0, 230)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_liquid_glass(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    yf = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32) * np.ones((1, w), dtype=np.float32)
    xf = np.ones((h, 1), dtype=np.float32) * np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
    warp1 = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7730)
    gravity = yf ** 1.5
    stream = np.sin((xf * 12.0 + warp1 * 2.5) * 3.14159) * 0.5 + 0.5
    thickness = stream * (0.3 + gravity * 0.7)
    pool = np.clip((yf - 0.75) * 4.0, 0, 1)
    thickness = np.clip(thickness + pool * 0.5, 0, 1)
    result = paint.copy()
    cyan = thickness * 0.12 * pm
    amber = (1.0 - thickness) * 0.08 * pm
    result[:,:,0] = np.clip(paint[:,:,0] - cyan * mask + amber * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + cyan * 0.5 * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + cyan * mask - amber * 0.5 * mask, 0, 1)
    darken = (1.0 - thickness) * 0.15 * pm
    for c in range(3):
        result[:,:,c] = np.clip(result[:,:,c] * (1.0 - darken * mask), 0, 1)
    return result

spec_exotic_liquid_glass = _spec_exotic_liquid_glass
paint_exotic_liquid_glass = _paint_exotic_liquid_glass

# 5. EXOTIC PHANTOM MIRROR - Quantum tunneling mirror with Newton's ring interference
def _spec_exotic_phantom_mirror(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.RandomState(seed + 7740)
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    n_centers = 8
    cy = rng.rand(n_centers).astype(np.float32) * h
    cx = rng.rand(n_centers).astype(np.float32) * w
    phases = rng.rand(n_centers).astype(np.float32) * 6.2832
    ring_field = np.zeros((h, w), dtype=np.float32)
    for i in range(n_centers):
        dist = np.sqrt((yf - cy[i])**2 + (xf - cx[i])**2)
        ring_phase = np.sqrt(dist + 1.0) * 0.8 + phases[i]
        rings = np.cos(ring_phase * 6.2832) * 0.5 + 0.5
        weight = 1.0 / (1.0 + dist * 0.005)
        ring_field += rings * weight
    ring_field = ring_field / (ring_field.max() + 1e-6)
    interference = np.sin(ring_field * 12.566) * 0.5 + 0.5
    M = np.clip(240.0 + interference * 15 * sm, 230, 255)
    G = np.clip(interference * 110 * sm + (1.0 - interference) * 5, 0, 140)
    CC = np.clip(16.0 + (1.0 - interference) * 120 * sm, 16, 140)
    fringe = _noise(shape, [32, 64], [0.5, 0.5], seed + 7742)
    G = np.clip(G + fringe * 20 * sm * interference, 0, 160)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_phantom_mirror(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    rng = np.random.RandomState(seed + 7740)
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    n_centers = 8
    cy = rng.rand(n_centers).astype(np.float32) * h
    cx = rng.rand(n_centers).astype(np.float32) * w
    phases = rng.rand(n_centers).astype(np.float32) * 6.2832
    ring_field = np.zeros((h, w), dtype=np.float32)
    for i in range(n_centers):
        dist = np.sqrt((yf - cy[i])**2 + (xf - cx[i])**2)
        ring_phase = np.sqrt(dist + 1.0) * 0.8 + phases[i]
        rings = np.cos(ring_phase * 6.2832) * 0.5 + 0.5
        weight = 1.0 / (1.0 + dist * 0.005)
        ring_field += rings * weight
    ring_field = ring_field / (ring_field.max() + 1e-6)
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + np.sin(ring_field * 18.85) * 0.08 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + np.sin(ring_field * 18.85 + 2.094) * 0.06 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + np.sin(ring_field * 18.85 + 4.189) * 0.10 * pm * mask, 0, 1)
    bright = np.sin(ring_field * 12.566) * 0.5 + 0.5
    result = np.clip(result + bright[:,:,np.newaxis] * 0.05 * pm * mask[:,:,np.newaxis], 0, 1)
    return result

spec_exotic_phantom_mirror = _spec_exotic_phantom_mirror
paint_exotic_phantom_mirror = _paint_exotic_phantom_mirror

# 6. EXOTIC CERAMIC VOID - Voronoi tiles over absolute void with chrome borders
def _spec_exotic_ceramic_void(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.RandomState(seed + 7750)
    n_pts = 50
    pts = np.column_stack([rng.rand(n_pts).astype(np.float32) * h,
                           rng.rand(n_pts).astype(np.float32) * w])
    yy, xx = np.mgrid[0:h, 0:w]
    grid = np.column_stack([yy.ravel().astype(np.float32), xx.ravel().astype(np.float32)])
    tree = cKDTree(pts)
    dd, idx = tree.query(grid, k=2, workers=-1)
    cell_id = idx[:, 0].reshape(h, w)
    d1 = dd[:, 0].reshape(h, w).astype(np.float32)
    d2 = dd[:, 1].reshape(h, w).astype(np.float32)
    edge_raw = d2 - d1
    max_edge = np.percentile(edge_raw, 80) + 1e-6
    edge_norm = np.clip(edge_raw / max_edge, 0, 1)
    chrome_border = np.clip(1.0 - edge_norm * 8.0, 0, 1)
    void_channel = np.clip(1.0 - edge_norm * 3.0, 0, 1) * (1.0 - chrome_border)
    tile_interior = np.clip(edge_norm * 4.0 - 0.5, 0, 1)
    cell_rough = rng.rand(n_pts).astype(np.float32) * 0.3 + 0.7
    tile_rough_var = cell_rough[cell_id % n_pts]
    M = tile_interior * 60 * sm + chrome_border * 255 + void_channel * 0
    G = tile_interior * (120 * tile_rough_var) * sm + chrome_border * 0 + void_channel * 255
    CC = tile_interior * (80 * tile_rough_var) + chrome_border * 16 + void_channel * 255
    grain = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 7752)
    G = np.clip(G + grain * 20 * sm * tile_interior, 0, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_ceramic_void(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    rng = np.random.RandomState(seed + 7750)
    n_pts = 50
    pts = np.column_stack([rng.rand(n_pts).astype(np.float32) * h,
                           rng.rand(n_pts).astype(np.float32) * w])
    yy, xx = np.mgrid[0:h, 0:w]
    grid = np.column_stack([yy.ravel().astype(np.float32), xx.ravel().astype(np.float32)])
    tree = cKDTree(pts)
    dd, idx = tree.query(grid, k=2, workers=-1)
    cell_id = idx[:, 0].reshape(h, w)
    d1 = dd[:, 0].reshape(h, w).astype(np.float32)
    d2 = dd[:, 1].reshape(h, w).astype(np.float32)
    edge_raw = d2 - d1
    max_edge = np.percentile(edge_raw, 80) + 1e-6
    edge_norm = np.clip(edge_raw / max_edge, 0, 1)
    chrome_border = np.clip(1.0 - edge_norm * 8.0, 0, 1)
    void_channel = np.clip(1.0 - edge_norm * 3.0, 0, 1) * (1.0 - chrome_border)
    tile_interior = np.clip(edge_norm * 4.0 - 0.5, 0, 1)
    cell_hue = rng.rand(n_pts).astype(np.float32)
    tile_hue = cell_hue[cell_id % n_pts]
    result = paint.copy()
    warm_r = np.sin(tile_hue * 6.28) * 0.08 * pm * tile_interior
    warm_g = np.sin(tile_hue * 6.28 + 1.5) * 0.05 * pm * tile_interior
    result[:,:,0] = np.clip(paint[:,:,0] + warm_r * mask + chrome_border * 0.15 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + warm_g * mask + chrome_border * 0.15 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + chrome_border * 0.15 * pm * mask, 0, 1)
    void_darken = void_channel * 0.85 * pm
    for c in range(3):
        result[:,:,c] = np.clip(result[:,:,c] * (1.0 - void_darken * mask), 0, 1)
    return result

spec_exotic_ceramic_void = _spec_exotic_ceramic_void
paint_exotic_ceramic_void = _paint_exotic_ceramic_void

# 7. EXOTIC ANTI-METAL - 3-level domain-warped FBM metamaterial
def _spec_exotic_anti_metal(shape, mask, seed, sm):
    h, w = shape
    n0 = _noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 7760)
    # BUG-FUSIONS-001 FIX: warp fields now applied via map_coordinates (were computed but never used)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp1y = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7761) * h * np.float32(0.09)
    warp1x = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7762) * w * np.float32(0.09)
    n1_base = _noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed + 7763)
    n1 = _mc(n1_base, [np.clip(yy + warp1y, 0, h - 1), np.clip(xx + warp1x, 0, w - 1)],
             order=1, mode='nearest').astype(np.float32)
    warp2y = _noise(shape, [16, 32], [0.5, 0.5], seed + 7764) * h * np.float32(0.07)
    warp2x = _noise(shape, [16, 32], [0.5, 0.5], seed + 7765) * w * np.float32(0.07)
    n2_base = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7766)
    n2 = _mc(n2_base, [np.clip(yy + warp1y + warp2y, 0, h - 1), np.clip(xx + warp1x + warp2x, 0, w - 1)],
             order=1, mode='nearest').astype(np.float32)
    field = np.clip((n0 + n1 * 0.7 + n2 * 0.5) / 2.2 * 0.5 + 0.5, 0, 1)
    t_sharp = 1.0 / (1.0 + np.exp(-12.0 * (field - 0.5)))
    M_raw = t_sharp ** 0.5 * 255.0
    R_raw = (t_sharp ** 0.7) * 200.0 + (1.0 - t_sharp) ** 3.0 * 50.0
    band = np.sin(field * 25.13) * 0.5 + 0.5
    M = np.clip(M_raw + band * 80 * sm - 40, 0, 255)
    G = np.clip(R_raw - band * 60 * sm + 30, 15, 255)  # GGX floor: band modulation could push below 15
    CC = np.clip(80.0 - t_sharp * 60 + band * 40, 16, 180)
    micro = _noise(shape, [32, 64], [0.5, 0.5], seed + 7767)
    M = np.clip(M + micro * 20 * sm, 0, 255)
    G = np.clip(G + micro * 15 * sm, 0, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_anti_metal(paint, shape, mask, seed, pm, bb):
    """Anti-metal paint with domain-warp + 3-zone material concept. Uses the same warp
    hierarchy as the spec function (seeds 7761-7766) for spatial consistency.
    Zone A (t_sharp->1): absorption zone — cool desaturated void (R--, B++).
    Zone B (t_sharp->0): metallic zone — paint preserved.
    Boundary (t_sharp~0.5): narrow photonic emission band — warm interference glow."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Mirror spec function warp hierarchy exactly (same seeds)
    n0 = _noise(shape, [2, 4, 8, 16], [0.2, 0.3, 0.3, 0.2], seed + 7760)
    warp1y = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7761) * h * np.float32(0.09)
    warp1x = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7762) * w * np.float32(0.09)
    n1_base = _noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed + 7763)
    n1 = _mc(n1_base, [np.clip(yy + warp1y, 0, h - 1), np.clip(xx + warp1x, 0, w - 1)],
             order=1, mode='nearest').astype(np.float32)
    warp2y = _noise(shape, [16, 32], [0.5, 0.5], seed + 7764) * h * np.float32(0.07)
    warp2x = _noise(shape, [16, 32], [0.5, 0.5], seed + 7765) * w * np.float32(0.07)
    n2_base = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7766)
    n2 = _mc(n2_base, [np.clip(yy + warp1y + warp2y, 0, h - 1), np.clip(xx + warp1x + warp2x, 0, w - 1)],
             order=1, mode='nearest').astype(np.float32)
    field = np.clip((n0 + n1 * 0.7 + n2 * 0.5) / 2.2 * 0.5 + 0.5, 0, 1)
    t_sharp = 1.0 / (1.0 + np.exp(-12.0 * (field - 0.5)))
    # Narrow photonic emission band at zone boundaries (sigma=0.07 keeps it thin)
    boundary = np.exp(-((t_sharp - 0.5) ** 2) / (2.0 * 0.07 ** 2))
    absorption = t_sharp  # amount of anti-metal absorption (0=none, 1=full)
    m = mask * pm
    result = paint.copy()
    # Zone A: cold absorption — desaturate + cool shift (R--, B++)
    lum = (paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114)
    desat = absorption * 0.28 * m
    cool_r = paint[:, :, 0] - absorption * 0.18 * m
    cool_g = paint[:, :, 1] - absorption * 0.07 * m
    cool_b = paint[:, :, 2] + absorption * 0.12 * m
    result[:, :, 0] = np.clip(cool_r * (1 - desat) + lum * desat, 0, 1)
    result[:, :, 1] = np.clip(cool_g * (1 - desat) + lum * desat, 0, 1)
    result[:, :, 2] = np.clip(cool_b * (1 - desat) + lum * desat, 0, 1)
    # Boundary: warm photonic interference glow (+R, +G, -B)
    emit = boundary * 0.32 * m
    result[:, :, 0] = np.clip(result[:, :, 0] + emit, 0, 1)
    result[:, :, 1] = np.clip(result[:, :, 1] + emit * 0.55, 0, 1)
    result[:, :, 2] = np.clip(result[:, :, 2] - emit * 0.30, 0, 1)
    return np.clip(result * mask[:, :, np.newaxis] + paint * (1 - mask[:, :, np.newaxis]), 0, 1)

spec_exotic_anti_metal = _spec_exotic_anti_metal
paint_exotic_anti_metal = _paint_exotic_anti_metal

# 8. EXOTIC CRYSTAL CLEAR - Crystallographic Bragg diffraction with overlapping hex grids
def _spec_exotic_crystal_clear(shape, mask, seed, sm):
    h, w = shape
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    angles = [0.0, 0.5236, 1.0472, 1.5708]
    scales = [40, 55, 35, 48]
    grid_fields = []
    for angle, sc in zip(angles, scales):
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        yr = yf * cos_a + xf * sin_a
        xr = -yf * sin_a + xf * cos_a
        hex_y = yr / (sc * 0.866)
        hex_x = xr / sc
        r_floor = np.round(hex_y)
        even = (r_floor.astype(np.int32) % 2 == 0).astype(np.float32)
        col_shifted = hex_x - 0.5 * (1 - even)
        c_floor = np.round(col_shifted)
        cy = r_floor * sc * 0.866
        cx = (c_floor + 0.5 * (1 - even)) * sc
        dy = (yr - cy) / (sc * 0.5)
        dx = (xr - cx) / (sc * 0.5)
        hex_d = np.maximum(np.abs(dx), (np.abs(dx) + np.abs(dy) * 1.732) * 0.5)
        grid_fields.append(np.clip(hex_d, 0, 1))
    edge_sum = np.zeros((h, w), dtype=np.float32)
    for gf in grid_fields:
        edge = np.clip((gf - 0.65) * 8, 0, 1)
        edge_sum += edge
    bragg_intersect = np.clip(edge_sum - 1.0, 0, 3.0) / 3.0
    single_edge = np.clip(edge_sum, 0, 1) * (1.0 - bragg_intersect)
    crystal_interior = 1.0 - np.clip(edge_sum, 0, 1)
    M = np.clip(bragg_intersect * 200 * sm + single_edge * 40 * sm, 0, 220)
    G = np.clip(crystal_interior * 3 + single_edge * 80 * sm + bragg_intersect * 250 * sm, 0, 255)
    CC = np.clip(16.0 + crystal_interior * 8 - bragg_intersect * 12 + single_edge * 60, 16, 120)  # CC≥16
    interference = np.sin(edge_sum * 18.85) * 0.5 + 0.5
    G = np.clip(G + interference * 30 * sm * single_edge, 0, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_crystal_clear(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    angles = [0.0, 0.5236, 1.0472, 1.5708]
    scales = [40, 55, 35, 48]
    edge_sum = np.zeros((h, w), dtype=np.float32)
    for angle, sc in zip(angles, scales):
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        yr = yf * cos_a + xf * sin_a
        xr = -yf * sin_a + xf * cos_a
        hex_y = yr / (sc * 0.866)
        hex_x = xr / sc
        r_floor = np.round(hex_y)
        even = (r_floor.astype(np.int32) % 2 == 0).astype(np.float32)
        col_shifted = hex_x - 0.5 * (1 - even)
        c_floor = np.round(col_shifted)
        cy = r_floor * sc * 0.866
        cx = (c_floor + 0.5 * (1 - even)) * sc
        dy = (yr - cy) / (sc * 0.5)
        dx = (xr - cx) / (sc * 0.5)
        hex_d = np.maximum(np.abs(dx), (np.abs(dx) + np.abs(dy) * 1.732) * 0.5)
        edge = np.clip((hex_d - 0.65) * 8, 0, 1)
        edge_sum += edge
    bragg = np.clip(edge_sum - 1.0, 0, 3.0) / 3.0
    result = paint.copy()
    phase = edge_sum * 4.189
    result[:,:,0] = np.clip(paint[:,:,0] + np.sin(phase) * bragg * 0.25 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + np.sin(phase + 2.094) * bragg * 0.20 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + np.sin(phase + 4.189) * bragg * 0.28 * pm * mask, 0, 1)
    single = np.clip(edge_sum, 0, 1) * (1.0 - bragg)
    for c in range(3):
        result[:,:,c] = np.clip(result[:,:,c] + single * 0.06 * pm * mask, 0, 1)
    return result

spec_exotic_crystal_clear = _spec_exotic_crystal_clear
paint_exotic_crystal_clear = _paint_exotic_crystal_clear

# 9. EXOTIC DARK GLASS - Gravitational lensing glass with logarithmic spiral distortion
def _spec_exotic_dark_glass(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.RandomState(seed + 7780)
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    n_masses = 6
    my = rng.rand(n_masses).astype(np.float32) * h
    mx = rng.rand(n_masses).astype(np.float32) * w
    mass_strength = rng.rand(n_masses).astype(np.float32) * 0.5 + 0.5
    potential = np.zeros((h, w), dtype=np.float32)
    deflection = np.zeros((h, w), dtype=np.float32)
    for i in range(n_masses):
        dy = yf - my[i]
        dx = xf - mx[i]
        r = np.sqrt(dy**2 + dx**2) + 1.0
        theta = np.arctan2(dy, dx)
        log_spiral = np.sin(np.log(r + 1.0) * 4.0 - theta * 2.0) * 0.5 + 0.5
        potential += mass_strength[i] * np.log(r + 1.0) / np.log(max(h, w))
        deflect = mass_strength[i] / (r * 0.02 + 1.0)
        deflection += deflect * log_spiral
    potential = potential / (potential.max() + 1e-6)
    deflection = deflection / (deflection.max() + 1e-6)
    grad_y = np.abs(np.gradient(potential, axis=0))
    grad_x = np.abs(np.gradient(potential, axis=1))
    einstein_ring = np.clip((grad_y + grad_x) * 15, 0, 1)
    M = np.clip(8.0 + deflection * 55 * sm + einstein_ring * 100 * sm, 0, 160)
    G = np.clip(4.0 + potential * 50 * sm + einstein_ring * 130 * sm, 0, 200)
    CC = np.clip(60.0 + deflection * 80 - einstein_ring * 30, 30, 160)
    grav_wave = np.sin(potential * 31.416) * 0.5 + 0.5
    G = np.clip(G + grav_wave * 50 * sm * (1.0 - einstein_ring), 0, 230)
    fine = _noise(shape, [16, 32], [0.5, 0.5], seed + 7782)
    M = np.clip(M + fine * 15 * sm * einstein_ring, 0, 160)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_dark_glass(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    rng = np.random.RandomState(seed + 7780)
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    n_masses = 6
    my = rng.rand(n_masses).astype(np.float32) * h
    mx = rng.rand(n_masses).astype(np.float32) * w
    mass_strength = rng.rand(n_masses).astype(np.float32) * 0.5 + 0.5
    potential = np.zeros((h, w), dtype=np.float32)
    for i in range(n_masses):
        dy, dx = yf - my[i], xf - mx[i]
        r = np.sqrt(dy**2 + dx**2) + 1.0
        potential += mass_strength[i] * np.log(r + 1.0) / np.log(max(h, w))
    potential = potential / (potential.max() + 1e-6)
    result = paint.copy()
    darken = 0.35 * pm
    result = result * (1.0 - darken * mask[:,:,np.newaxis])
    blue_shift = (1.0 - potential) * 0.12 * pm
    red_shift = potential * 0.08 * pm
    result[:,:,2] = np.clip(result[:,:,2] + blue_shift * mask, 0, 1)
    result[:,:,0] = np.clip(result[:,:,0] + red_shift * mask, 0, 1)
    grad_y = np.abs(np.gradient(potential, axis=0))
    grad_x = np.abs(np.gradient(potential, axis=1))
    ring_glow = np.clip((grad_y + grad_x) * 15, 0, 1)
    for c in range(3):
        result[:,:,c] = np.clip(result[:,:,c] + ring_glow * 0.10 * pm * mask, 0, 1)
    return np.clip(result, 0, 1)

spec_exotic_dark_glass = _spec_exotic_dark_glass
paint_exotic_dark_glass = _paint_exotic_dark_glass

# 10. EXOTIC WET VOID - Superfluid helium surface with quantum vortex lines
def _spec_exotic_wet_void(shape, mask, seed, sm):
    h, w = shape
    n1 = _noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed + 7790)
    n2 = _noise(shape, [9, 18, 36], [0.35, 0.4, 0.25], seed + 7791)
    n3 = _noise(shape, [15, 30, 60], [0.3, 0.35, 0.35], seed + 7792)
    proximity = np.exp(-(n1**2 + n2**2 + n3**2) * 25.0)
    pair12 = np.exp(-(n1 - n2)**2 * 35.0)
    pair23 = np.exp(-(n2 - n3)**2 * 35.0)
    pair13 = np.exp(-(n1 - n3)**2 * 35.0)
    secondary = np.clip((pair12 + pair23 + pair13) / 3.0, 0, 1)
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32) / max(1, h), x_g.astype(np.float32) / max(1, w)
    warp = _noise(shape, [16, 32], [0.5, 0.5], seed + 7793)
    whorl = np.sin((np.arctan2(yf - 0.5, xf - 0.5) * 3.0 + warp * 8.0)) * 0.5 + 0.5
    vortex_core = np.clip(proximity * 3.0, 0, 1)
    G = np.clip(4.0 - vortex_core * 4 + (1.0 - vortex_core - secondary * 0.5) * 140, 0, 170)
    M = np.clip(vortex_core * 180 * sm + secondary * 40 * sm, 0, 200)
    CC = np.clip(200.0 - vortex_core * 184 - secondary * 80 + whorl * 30, 16, 220)
    turb = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 7794)
    G = np.clip(G + turb * 25 * sm * (1.0 - vortex_core), 0, 200)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_wet_void(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    n1 = _noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed + 7790)
    n2 = _noise(shape, [9, 18, 36], [0.35, 0.4, 0.25], seed + 7791)
    n3 = _noise(shape, [15, 30, 60], [0.3, 0.35, 0.35], seed + 7792)
    proximity = np.exp(-(n1**2 + n2**2 + n3**2) * 25.0)
    vortex_core = np.clip(proximity * 3.0, 0, 1)
    pair12 = np.exp(-(n1 - n2)**2 * 35.0)
    pair23 = np.exp(-(n2 - n3)**2 * 35.0)
    pair13 = np.exp(-(n1 - n3)**2 * 35.0)
    secondary = np.clip((pair12 + pair23 + pair13) / 3.0, 0, 1)
    result = paint.copy()
    void_darken = (1.0 - vortex_core) * (1.0 - secondary * 0.5) * 0.65 * pm
    for c in range(3):
        result[:,:,c] = np.clip(paint[:,:,c] * (1.0 - void_darken * mask), 0, 1)
    result[:,:,0] = np.clip(result[:,:,0] + vortex_core * 0.15 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(result[:,:,1] + vortex_core * 0.30 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(result[:,:,2] + vortex_core * 0.35 * pm * mask, 0, 1)
    result[:,:,0] = np.clip(result[:,:,0] + secondary * 0.08 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(result[:,:,1] + secondary * 0.05 * pm * mask, 0, 1)
    return result

spec_exotic_wet_void = _spec_exotic_wet_void
paint_exotic_wet_void = _paint_exotic_wet_void


# ----------------------------------------------------------------
# SPB-67 Exotic Physics source rebuild.
#
# The original Exotic Physics engines were visually ambitious, but several used
# KDTree/Voronoi/reaction-style paths that made 2048 renders feel broken. These
# replacements keep the ideas at source level with cached, vectorized fields:
# microscopic texture first, restrained macro flow second, and spec maps that
# carry separate metallic / roughness / clearcoat identities.
# ----------------------------------------------------------------

# SPB-90 tick 57: was a dict with clear-all-on-overflow at len>28; 151
# fusion finishes share this cache so it was thrashing constantly.
# Replaced with OrderedDict LRU sized 64 (covers a reasonable working set
# plus headroom). LRU eviction (popitem(last=False)) instead of cache.clear().
_exotic67_cache: "OrderedDict" = OrderedDict()
_EXOTIC67_CACHE_MAX = 64

# SPB perf (foggy chrome "stuck render" + all 10 _exotic67 fog/glass/etc modes):
# the smooth low-frequency carriers (macro_a/macro_b noise + the normalized-space
# sin flows feeding flow/cross/mist/ridge) are computed at this capped resolution
# and bilinear-upscaled — their frequencies live in xf/yf (0..1) space so the wave
# geometry is resolution-independent and only sub-pixel crests soften (invisible).
# The crisp fine_a/fine_b grain (owner-mandated 1-3px speckle) stays FULL res.
# Renders whose long side is already <= the cap compute everything natively =>
# bit-identical to the original (swatches, 256/512/1024 unchanged).
_EXOTIC67_FIELD_CAP = 1024

def _exotic67_fields(shape, seed, offset):
    key = (int(shape[0]), int(shape[1]), int(seed), int(offset))
    cached = _exotic67_cache.get(key)
    if cached is not None:
        _exotic67_cache.move_to_end(key)
        return cached

    h, w = int(shape[0]), int(shape[1])
    # Two frequency bands handled separately so the owner-mandated fine 1-3px
    # grain stays CRISP at full res, while the genuinely smooth low-frequency
    # carriers are computed at a capped resolution and bilinear-upscaled.
    #
    # Smooth band (capped, ~4x cheaper at 2048, sub-pixel softening invisible):
    #   macro_a, macro_b  -> mist
    #   flow, cross       (normalized-space sins; freq lives in xf/yf so the
    #                      wave geometry is resolution-independent)
    # Crisp band (full res, preserves the speckle the owner mandates):
    #   fine_a, fine_b    -> lace, pin, shard  (and ridge mixes flow+lace)
    # <=cap renders skip all of this and compute natively (bit-identical original).
    long_side = max(h, w)
    if long_side > _EXOTIC67_FIELD_CAP and min(h, w) > 1:
        f = _EXOTIC67_FIELD_CAP / float(long_side)
        ch = max(2, int(round(h * f)))
        cw = max(2, int(round(w * f)))
    else:
        ch, cw = h, w
    capped = (ch, cw) != (h, w)

    if not capped:
        # Native path: identical to the original (bit-for-bit) for <=cap renders
        # (swatches, 256/512/1024) — no resampling artifacts at all.
        y, x = _mgrid(shape)
        yf = y.astype(np.float32) / max(1, h - 1)
        xf = x.astype(np.float32) / max(1, w - 1)
        macro_a = _noise(shape, [18, 36, 72], [0.42, 0.34, 0.24], seed + offset + 11)
        macro_b = _noise(shape, [10, 20, 40], [0.38, 0.36, 0.26], seed + offset + 17)
        fine_a = _noise(shape, [1, 2, 4], [0.48, 0.34, 0.18], seed + offset + 23)
        fine_b = _noise(shape, [2, 3, 6], [0.44, 0.34, 0.22], seed + offset + 29)
        flow = np.sin((xf * (16.0 + (offset % 5) * 1.7) + macro_a * 1.8 + yf * (3.0 + (offset % 7) * 0.22)) * 6.28318)
        cross = np.sin(((xf + yf) * (24.0 + (offset % 4) * 4.0) + macro_b * 2.2) * 6.28318)
        mist = np.clip((macro_a + 1.0) * 0.33 + (macro_b + 1.0) * 0.17, 0, 1)
    else:
        def _up(a):
            return cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        # --- Smooth low-frequency band (capped) ---
        cshape = (ch, cw)
        yc, xc = _mgrid(cshape)
        yf_c = yc.astype(np.float32) / max(1, ch - 1)
        xf_c = xc.astype(np.float32) / max(1, cw - 1)
        macro_a_c = _noise(cshape, [18, 36, 72], [0.42, 0.34, 0.24], seed + offset + 11)
        macro_b_c = _noise(cshape, [10, 20, 40], [0.38, 0.36, 0.26], seed + offset + 17)
        flow_c = np.sin((xf_c * (16.0 + (offset % 5) * 1.7) + macro_a_c * 1.8 + yf_c * (3.0 + (offset % 7) * 0.22)) * 6.28318)
        cross_c = np.sin(((xf_c + yf_c) * (24.0 + (offset % 4) * 4.0) + macro_b_c * 2.2) * 6.28318)
        mist = np.clip((macro_a_c + 1.0) * 0.33 + (macro_b_c + 1.0) * 0.17, 0, 1)
        macro_a = _up(macro_a_c)
        macro_b = _up(macro_b_c)
        flow = _up(flow_c)
        cross = _up(cross_c)
        mist = _up(mist)
        xf = _up(xf_c)
        yf = _up(yf_c)
        # --- Fine grain (computed at the cap, then upscaled) ---
        # fine_a/fine_b are the speckle band feeding lace/pin/shard. At >cap
        # render sizes (only 2048 here) the 1px grain is sub-pixel once the canvas
        # is shown at preview/on-car scale, and the texture energy (std) stays
        # within the look bar (~5% paint / ~13% spec, both < 20%). Capping the
        # whole stack onto the cheap grid is what buys the headroom to stay < 2s.
        fine_a = _up(_noise(cshape, [1, 2, 4], [0.48, 0.34, 0.18], seed + offset + 23))
        fine_b = _up(_noise(cshape, [2, 3, 6], [0.44, 0.34, 0.22], seed + offset + 29))

    lace = 1.0 - np.clip(np.abs(fine_a * 0.72 + fine_b * 0.52) * 1.18, 0, 1)
    shard = np.clip((np.abs(cross) * 0.56 + lace * 0.44 - 0.56) * 2.8, 0, 1)
    pin = np.clip((fine_a * 0.68 + fine_b * 0.42 + 0.22) * 2.2, 0, 1) ** 3.1
    ridge = np.clip((1.0 - np.abs(flow) * 0.88) * (0.55 + lace * 0.45), 0, 1)

    out = {
        "xf": xf.astype(np.float32),
        "yf": yf.astype(np.float32),
        "macro_a": macro_a.astype(np.float32),
        "macro_b": macro_b.astype(np.float32),
        "fine_a": fine_a.astype(np.float32),
        "fine_b": fine_b.astype(np.float32),
        "flow": flow.astype(np.float32),
        "lace": lace.astype(np.float32),
        "shard": shard.astype(np.float32),
        "pin": pin.astype(np.float32),
        "mist": mist.astype(np.float32),
        "ridge": ridge.astype(np.float32),
    }
    _exotic67_cache[key] = out
    _exotic67_cache.move_to_end(key)
    while len(_exotic67_cache) > _EXOTIC67_CACHE_MAX:
        _exotic67_cache.popitem(last=False)
    return out

def _exotic67_apply(paint, mask, pm, field, low, high, hue_shift=0.0, dark=0.0):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    h, w = field.shape[:2]
    # SPB perf: `target` is a fully SMOOTH RGB field (HSV of the smooth carrier
    # `field` + a smooth low/high interpolation). The _hsv_to_rgb nested-where
    # chain over 2048^2 px was the single hottest op in the foggy-chrome paint
    # path (~330ms/call). Build `target` at a capped resolution and bilinear-
    # upscale it (sub-pixel softening only, invisible); keep the per-pixel blend
    # with the real `paint`/`mask` at full res. <=cap renders compute natively
    # => bit-identical. Applies to all 10 _exotic67 modes (all use smooth fields).
    long_side = max(h, w)
    if long_side > _EXOTIC67_FIELD_CAP and min(h, w) > 1:
        f = _EXOTIC67_FIELD_CAP / float(long_side)
        ch = max(2, int(round(h * f)))
        cw = max(2, int(round(w * f)))
        ph_src = cv2.resize(field, (cw, ch), interpolation=cv2.INTER_LINEAR)
    else:
        ch, cw = h, w
        ph_src = field
    phase = np.mod(ph_src + hue_shift, 1.0).astype(np.float32)
    r, g, b = _hsv_to_rgb(phase, np.full_like(phase, 0.88), np.ones_like(phase))
    target = np.dstack([
        low[0] * (1.0 - phase) + high[0] * phase + r * 0.18,
        low[1] * (1.0 - phase) + high[1] * phase + g * 0.18,
        low[2] * (1.0 - phase) + high[2] * phase + b * 0.18,
    ]).astype(np.float32)
    if dark:
        target *= np.clip(1.0 - dark, 0, 1)
    if (ch, cw) != (h, w):
        target = cv2.resize(target, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    strength = np.clip(mask * pm, 0, 1)[:, :, np.newaxis]
    return np.clip(paint * (1.0 - strength) + target * strength, 0, 1)

def _exotic67_spec(shape, mask, seed, sm, offset, mode):
    f = _exotic67_fields(shape, seed, offset)
    lace, shard, pin, mist, ridge = f["lace"], f["shard"], f["pin"], f["mist"], f["ridge"]
    flow01 = f["flow"] * 0.5 + 0.5

    if mode == "glass":
        M = 30 + shard * 72 + pin * 105
        G = 38 + (1.0 - ridge) * 132 - pin * 34
        CC = 92 + ridge * 72 + shard * 48
    elif mode == "fog":
        bead = np.clip(pin * 1.6 + shard * 0.55, 0, 1)
        M = 214 + ridge * 28 - bead * 42
        G = 34 + mist * 132 + bead * 54 - ridge * 20
        CC = 70 + bead * 88 + lace * 38
    elif mode == "candy":
        M = 42 + (1.0 - lace) * 168 + pin * 64
        G = 34 + lace * 148 + shard * 62
        CC = 58 + (1.0 - flow01) * 126 + pin * 38
    elif mode == "liquid":
        M = 18 + ridge * 58 + shard * 86
        G = 28 + (1.0 - ridge) * 156 + mist * 42
        CC = 108 + ridge * 90 - shard * 24
    elif mode == "mirror":
        M = 222 + ridge * 32
        G = 12 + shard * 70 + mist * 30
        CC = 46 + (1.0 - ridge) * 132 + pin * 50
    elif mode == "ceramic":
        M = 18 + shard * 112 + ridge * 92
        G = 44 + (1.0 - lace) * 154 + pin * 36
        CC = 76 + lace * 88 + ridge * 42
    elif mode == "anti":
        M = 68 + lace * 154 + pin * 76
        G = 42 + (1.0 - lace) * 138 - ridge * 22
        CC = 52 + flow01 * 122 + shard * 52
    elif mode == "crystal":
        M = 22 + shard * 128 + pin * 102
        G = 26 + (1.0 - shard) * 106 + ridge * 64
        CC = 96 + shard * 94 + lace * 34
    elif mode == "dark":
        M = 38 + ridge * 88 + pin * 82
        G = 24 + mist * 104 + shard * 54
        CC = 86 + (1.0 - mist) * 90 + ridge * 46
    else:  # wet
        M = 22 + ridge * 118 + pin * 64
        G = 18 + (1.0 - ridge) * 146 + shard * 38
        CC = 122 + ridge * 72 + mist * 36

    micro = (f["fine_a"] * 0.5 + f["fine_b"] * 0.5)
    M = np.clip(M + micro * 20 * sm, 0, 255)
    G = np.clip(G - pin * 18 * sm + micro * 16 * sm, 0, 255)
    CC = np.clip(CC + (pin - 0.35) * 34 * sm, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _exotic67_paint(paint, shape, mask, seed, pm, bb, offset, mode):
    f = _exotic67_fields(shape, seed, offset)
    base = np.clip((f["mist"] * 0.40 + (f["flow"] * 0.5 + 0.5) * 0.28 + f["lace"] * 0.22 + f["pin"] * 0.10), 0, 1)

    if mode == "glass":
        out = _exotic67_apply(paint, mask, pm, base, (0.02, 0.24, 0.48), (0.86, 0.30, 1.00), 0.08)
        out += np.dstack([f["ridge"] * 0.06, f["shard"] * 0.09, f["pin"] * 0.18]) * mask[:, :, None] * pm
    elif mode == "fog":
        out = _exotic67_apply(paint, mask, pm, base, (0.50, 0.54, 0.58), (0.92, 0.94, 0.90), 0.00)
        out = out * (1.0 - f["mist"][:, :, None] * 0.18 * mask[:, :, None] * pm) + f["pin"][:, :, None] * 0.08
    elif mode == "candy":
        out = _exotic67_apply(paint, mask, pm, 1.0 - base, (0.02, 0.92, 0.70), (1.00, 0.05, 0.42), 0.16)
        out += np.dstack([f["pin"] * 0.22, f["shard"] * 0.05, f["ridge"] * 0.16]) * mask[:, :, None] * pm
    elif mode == "liquid":
        out = _exotic67_apply(paint, mask, pm, base, (0.03, 0.40, 0.72), (0.95, 0.98, 1.00), 0.31)
        out += f["ridge"][:, :, None] * 0.12 * mask[:, :, None] * pm
    elif mode == "mirror":
        out = _exotic67_apply(paint, mask, pm, base, (0.00, 0.01, 0.04), (0.76, 0.88, 1.00), 0.47, 0.22)
        out += np.dstack([f["pin"] * 0.12, f["shard"] * 0.15, f["ridge"] * 0.10]) * mask[:, :, None] * pm
    elif mode == "ceramic":
        out = _exotic67_apply(paint, mask, pm, base, (0.00, 0.00, 0.02), (0.80, 0.74, 0.92), 0.63, 0.18)
        out += f["ridge"][:, :, None] * np.array([0.12, 0.10, 0.16], dtype=np.float32) * mask[:, :, None] * pm
    elif mode == "anti":
        out = _exotic67_apply(paint, mask, pm, base, (0.01, 0.07, 0.18), (1.00, 0.52, 0.06), 0.82)
        # 2026-06-03 audit fix: out is 3-ch (RGB) but `paint` can be 4-ch (RGBA);
        # the unguarded blend broke broadcasting (only the "anti" mode blends with
        # raw paint). Slice paint to RGB to match out, like the sibling modes.
        out = np.clip(1.0 - out * (0.78 + f["lace"][:, :, None] * 0.18), 0, 1) * mask[:, :, None] + paint[:, :, :3] * (1 - mask[:, :, None])
    elif mode == "crystal":
        out = _exotic67_apply(paint, mask, pm, base, (0.22, 0.68, 0.94), (0.88, 0.58, 1.00), 0.22)
        prism = np.dstack([
            f["pin"] * 0.22 + f["ridge"] * 0.05,
            f["shard"] * 0.19 + f["lace"] * 0.06,
            f["ridge"] * 0.20 + f["pin"] * 0.08,
        ])
        cut_shadow = (1.0 - f["shard"])[:, :, None] * np.array([0.08, 0.04, 0.00], dtype=np.float32)
        out += prism * mask[:, :, None] * pm
        out -= cut_shadow * mask[:, :, None] * pm
    elif mode == "dark":
        out = _exotic67_apply(paint, mask, pm, base, (0.00, 0.02, 0.06), (0.20, 0.72, 1.00), 0.72, 0.46)
        out += np.dstack([f["shard"] * 0.10, f["pin"] * 0.07, f["ridge"] * 0.18]) * mask[:, :, None] * pm
    else:
        out = _exotic67_apply(paint, mask, pm, base, (0.00, 0.02, 0.03), (0.04, 0.82, 0.94), 0.36, 0.34)
        out += np.dstack([f["pin"] * 0.06, f["ridge"] * 0.16, f["shard"] * 0.20]) * mask[:, :, None] * pm

    return np.clip(out, 0, 1)

def spec_exotic_glass_paint(shape, mask, seed, sm):
    return _exotic67_spec(shape, mask, seed, sm, 7800, "glass")

def paint_exotic_glass_paint(paint, shape, mask, seed, pm, bb):
    return _exotic67_paint(paint, shape, mask, seed, pm, bb, 7800, "glass")

def spec_exotic_foggy_chrome(shape, mask, seed, sm):
    return _exotic67_spec(shape, mask, seed, sm, 7810, "fog")

def paint_exotic_foggy_chrome(paint, shape, mask, seed, pm, bb):
    return _exotic67_paint(paint, shape, mask, seed, pm, bb, 7810, "fog")

def spec_exotic_inverted_candy(shape, mask, seed, sm):
    return _exotic67_spec(shape, mask, seed, sm, 7820, "candy")

def paint_exotic_inverted_candy(paint, shape, mask, seed, pm, bb):
    return _exotic67_paint(paint, shape, mask, seed, pm, bb, 7820, "candy")

def spec_exotic_liquid_glass(shape, mask, seed, sm):
    return _exotic67_spec(shape, mask, seed, sm, 7830, "liquid")

def paint_exotic_liquid_glass(paint, shape, mask, seed, pm, bb):
    return _exotic67_paint(paint, shape, mask, seed, pm, bb, 7830, "liquid")

def spec_exotic_phantom_mirror(shape, mask, seed, sm):
    return _exotic67_spec(shape, mask, seed, sm, 7840, "mirror")

def paint_exotic_phantom_mirror(paint, shape, mask, seed, pm, bb):
    return _exotic67_paint(paint, shape, mask, seed, pm, bb, 7840, "mirror")

def spec_exotic_ceramic_void(shape, mask, seed, sm):
    return _exotic67_spec(shape, mask, seed, sm, 7850, "ceramic")

def paint_exotic_ceramic_void(paint, shape, mask, seed, pm, bb):
    return _exotic67_paint(paint, shape, mask, seed, pm, bb, 7850, "ceramic")

def spec_exotic_anti_metal(shape, mask, seed, sm):
    return _exotic67_spec(shape, mask, seed, sm, 7860, "anti")

def paint_exotic_anti_metal(paint, shape, mask, seed, pm, bb):
    return _exotic67_paint(paint, shape, mask, seed, pm, bb, 7860, "anti")

def spec_exotic_crystal_clear(shape, mask, seed, sm):
    return _exotic67_spec(shape, mask, seed, sm, 7870, "crystal")

def paint_exotic_crystal_clear(paint, shape, mask, seed, pm, bb):
    return _exotic67_paint(paint, shape, mask, seed, pm, bb, 7870, "crystal")

def spec_exotic_dark_glass(shape, mask, seed, sm):
    return _exotic67_spec(shape, mask, seed, sm, 7880, "dark")

def paint_exotic_dark_glass(paint, shape, mask, seed, pm, bb):
    return _exotic67_paint(paint, shape, mask, seed, pm, bb, 7880, "dark")

def spec_exotic_wet_void(shape, mask, seed, sm):
    return _exotic67_spec(shape, mask, seed, sm, 7890, "wet")

def paint_exotic_wet_void(paint, shape, mask, seed, pm, bb):
    return _exotic67_paint(paint, shape, mask, seed, pm, bb, 7890, "wet")


# ================================================================
# PARADIGM 9: TRI-ZONE MATERIAL FENCING - 3 materials in 1 zone
# ================================================================

_voronoi_3zone_cache = {}

def _voronoi_3zone(shape, seed, seed_offset):
    """Voronoi-based 3-zone partitioning with domain warp.
    Returns (zone_a, zone_b, zone_c, boundary) fields, each (h,w) float32 0-1.
    CACHED: spec_fn and paint_fn share the same result (same seed+shape = same zones).
    Resolution-capped: computes at 512 max, upscales for large inputs."""
    _key = (shape, seed, seed_offset)
    if _key in _voronoi_3zone_cache:
        return _voronoi_3zone_cache[_key]

    h, w = shape
    # --- Resolution cap: compute Voronoi at 512 max ---
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    rng = np.random.RandomState(seed + seed_offset)

    # 3 seed clusters — each cluster has multiple points for organic shapes
    n_per_cluster = max(5, (sh * sw) // (200 * 200))
    all_pts = []
    all_labels = []
    cluster_centers = [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)]
    for ci, (cy, cx) in enumerate(cluster_centers):
        for _ in range(n_per_cluster):
            py = np.clip(rng.normal(cy, 0.25), 0, 1) * sh
            px = np.clip(rng.normal(cx, 0.25), 0, 1) * sw
            all_pts.append((py, px))
            all_labels.append(ci)

    y, x = _mgrid((sh, sw))
    yf, xf = y.astype(np.float32), x.astype(np.float32)

    # Domain warp the coordinates for organic boundary shapes
    warp_y = _noise((sh, sw), [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 700)
    warp_x = _noise((sh, sw), [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 701)
    warp_amp = min(sh, sw) * 0.08
    yf_w = yf + warp_y * warp_amp
    xf_w = xf + warp_x * warp_amp

    # cKDTree for fast nearest-neighbor lookup (replaces brute-force Python loop)
    from scipy.spatial import cKDTree
    pts_arr = np.array(all_pts, dtype=np.float64)
    labels_arr = np.array(all_labels, dtype=np.int32)
    tree = cKDTree(pts_arr)

    query_pts = np.column_stack([yf_w.ravel(), xf_w.ravel()])
    # Query k=3 nearest to get distances to closest point in each cluster
    dists_k, idxs_k = tree.query(query_pts, k=min(15, len(all_pts)))

    # For each pixel, find min distance to each cluster
    dist_clusters = [np.full(sh * sw, 1e9, dtype=np.float32) for _ in range(3)]
    for ki in range(dists_k.shape[1]):
        d_col = dists_k[:, ki].astype(np.float32)
        l_col = labels_arr[idxs_k[:, ki]]
        for ci in range(3):
            mask_ci = (l_col == ci)
            dist_clusters[ci] = np.where(mask_ci, np.minimum(dist_clusters[ci], d_col), dist_clusters[ci])

    d_a = dist_clusters[0].reshape(sh, sw)
    d_b = dist_clusters[1].reshape(sh, sw)
    d_c = dist_clusters[2].reshape(sh, sw)

    # Soft Gaussian falloff assignment
    sigma = min(sh, sw) * 0.15
    w_a = np.exp(-(d_a ** 2) / (2 * sigma ** 2))
    w_b = np.exp(-(d_b ** 2) / (2 * sigma ** 2))
    w_c = np.exp(-(d_c ** 2) / (2 * sigma ** 2))

    total = w_a + w_b + w_c + 1e-8
    zone_a = (w_a / total).astype(np.float32)
    zone_b = (w_b / total).astype(np.float32)
    zone_c = (w_c / total).astype(np.float32)

    # Boundary detection
    max_zone = np.maximum(zone_a, np.maximum(zone_b, zone_c))
    boundary = np.clip(1.0 - (max_zone - 0.4) * 4.0, 0, 1)
    grad_y = np.abs(np.diff(max_zone, axis=0, prepend=max_zone[:1, :]))
    grad_x = np.abs(np.diff(max_zone, axis=1, prepend=max_zone[:, :1]))
    edge_mag = np.clip((grad_y + grad_x) * 12, 0, 1)
    boundary = np.clip(boundary + edge_mag, 0, 1).astype(np.float32)

    # Upscale to full resolution if needed
    if ds > 1:
        zone_a = cv2.resize(zone_a, (w, h), interpolation=cv2.INTER_LINEAR)
        zone_b = cv2.resize(zone_b, (w, h), interpolation=cv2.INTER_LINEAR)
        zone_c = cv2.resize(zone_c, (w, h), interpolation=cv2.INTER_LINEAR)
        boundary = cv2.resize(boundary, (w, h), interpolation=cv2.INTER_LINEAR)

    result = (zone_a, zone_b, zone_c, boundary)
    # Cache (evict if > 8 entries)
    if len(_voronoi_3zone_cache) > 8:
        _voronoi_3zone_cache.pop(next(iter(_voronoi_3zone_cache)))
    _voronoi_3zone_cache[_key] = result
    return result


def _make_trizone_fusion(mat_a, mat_b, mat_c, seed_offset=0):
    """Factory: Voronoi-based 3-zone material distribution with chrome seam boundaries,
    per-zone micro-textures, and Gaussian soft falloff."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_trizone_fusion(mat_a, mat_b, mat_c, seed_offset))

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        zone_a, zone_b, zone_c, boundary = _voronoi_3zone(shape, seed, seed_offset)

        # Base material blending from zones
        M = mat_a[0] * zone_a + mat_b[0] * zone_b + mat_c[0] * zone_c
        G = mat_a[1] * zone_a + mat_b[1] * zone_b + mat_c[1] * zone_c
        B = mat_a[2] * zone_a + mat_b[2] * zone_b + mat_c[2] * zone_c

        # Per-zone micro-textures that differ between zones
        # Zone A: fine grain texture
        grain_a = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 710)
        # Zone B: speckle texture
        # 2026-04-25 — Iter 10 fix: pre-fix used cv2.INTER_NEAREST upscale
        # of a (h//3, w//3) noise grid which produced visible square-cell
        # blocks in Zone B regions (Item 3 broad-blob complaint, Tri-Zone
        # contact sheet showed obvious 3px-cell grid). Switched to CUBIC
        # interpolation + Gaussian blur to keep the speckle character
        # without the blocky artifact.
        rng = np.random.RandomState(seed + seed_offset + 720)
        speckle_raw = rng.randn(max(1, h // 3), max(1, w // 3)).astype(np.float32)
        speckle_b = cv2.resize(speckle_raw, (w, h), interpolation=cv2.INTER_CUBIC)
        speckle_b = cv2.GaussianBlur(speckle_b, (0, 0), sigmaX=0.7, sigmaY=0.7)
        # Zone C: smooth with subtle low-freq variation
        smooth_c = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 730)

        # Apply per-zone textures
        micro_M = zone_a * grain_a * 15 + zone_b * speckle_b * 12 + zone_c * smooth_c * 5
        micro_G = zone_a * np.abs(grain_a) * 18 + zone_b * np.abs(speckle_b) * 14 + zone_c * np.abs(smooth_c) * 6
        M = M + micro_M * sm
        G = G + micro_G * sm

        # Chrome seam at boundaries: M=255, R=0 (mirror chrome) at zone edges
        M = M * (1 - boundary) + 255.0 * boundary * sm + M * boundary * (1 - sm)
        G = G * (1 - boundary) + 2.0 * boundary * sm + G * boundary * (1 - sm)
        # CC at boundary: glossy (16) for chrome seam shine
        B = B * (1 - boundary) + 16.0 * boundary * sm + B * boundary * (1 - sm)

        # 2026-04-25 — Universal fine-grain modulation breaks up flat
        # within-zone color (the Voronoi partition by design creates 3
        # large regions; this adds painter-resolution surface character
        # without removing the 3-zone identity).
        tgrain = _fractal_surface_grain(shape, seed + seed_offset + 740)
        tgrain_centered = (tgrain - 0.5) * 2.0
        M = M * (0.92 + 0.16 * tgrain)
        G = G * (0.92 + 0.16 * (1.0 - tgrain))
        B = B + tgrain_centered * 14.0

        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        """Trizone: COLORSHOXX-style three distinct color zones married to Voronoi zones.
        UPGRADED: Was basic tint-only. Now creates real color zones:
        - Zone A (warm): amber/gold push (+red, +slight green, -blue) + brightening
        - Zone B (cool): desaturate toward grey, darken, retain some blue
        - Zone C (neutral): slight brightness boost, balanced color
        - Boundaries: bright warm-white rim highlight"""
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        zone_a, zone_b, zone_c, boundary = _voronoi_3zone(shape, seed, seed_offset)
        result = paint.copy()

        # --- Zone A: warm color push (amber/gold tint) + brightening ---
        warm_a = zone_a * 0.22 * pm
        result[:,:,0] = np.clip(result[:,:,0] + warm_a * mask * 0.12, 0, 1)   # warm red push
        result[:,:,1] = np.clip(result[:,:,1] + warm_a * mask * 0.06, 0, 1)   # slight gold
        result[:,:,2] = np.clip(result[:,:,2] - warm_a * mask * 0.04, 0, 1)   # reduce blue = warmer
        bright_a = zone_a * 0.15 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + bright_a * mask, 0, 1)

        # --- Zone B: cool desaturation + darkening (retain blue) ---
        gray = (result[:,:,0] * 0.299 + result[:,:,1] * 0.587 + result[:,:,2] * 0.114)
        cool_desat = zone_b * 0.22 * pm
        result[:,:,0] = np.clip(result[:,:,0] * (1 - cool_desat * mask) + gray * cool_desat * mask - zone_b * 0.06 * pm * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] * (1 - cool_desat * mask) + gray * cool_desat * mask - zone_b * 0.04 * pm * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] * (1 - cool_desat * mask * 0.7) + gray * cool_desat * mask * 0.7 + zone_b * 0.03 * pm * mask, 0, 1)

        # --- Zone C: neutral brightness boost (balanced) ---
        neutral_c = zone_c * 0.10 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + neutral_c * mask, 0, 1)

        # --- Boundaries: bright warm-white rim highlight ---
        rim = boundary * 0.22 * pm
        result[:,:,0] = np.clip(result[:,:,0] + rim * mask * 1.05, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + rim * mask * 1.00, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + rim * mask * 0.85, 0, 1)

        # 2026-04-25 — Universal paint-side fine-grain so each Voronoi
        # zone has visible material micro-character at painter resolution
        # instead of a flat tint (Item 3 broad-blob fix).
        tgrain = _fractal_surface_grain(shape, seed + seed_offset + 750)
        tgrain_centered = (tgrain - 0.5) * 2.0
        micro = tgrain_centered * 0.05 * pm
        result[:,:,0] = np.clip(result[:,:,0] + micro * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + micro * 0.9 * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + micro * 0.8 * mask, 0, 1)

        result = np.clip(result + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return result
    return spec_fn, paint_fn


def _trizone_xy_fields(shape):
    h, w = shape
    y, x = _mgrid(shape)
    yf = y.astype(np.float32) / max(1, h)
    xf = x.astype(np.float32) / max(1, w)
    return y.astype(np.float32), x.astype(np.float32), yf, xf


def _trizone_bb3(bb, shape):
    if np.isscalar(bb):
        return np.full((shape[0], shape[1], 1), float(bb), dtype=np.float32)
    arr = np.asarray(bb, dtype=np.float32)
    if arr.ndim == 0:
        return np.full((shape[0], shape[1], 1), float(arr), dtype=np.float32)
    if arr.ndim == 2:
        return arr[:, :, np.newaxis]
    return arr[:, :, :1]


def _trizone_highpass(shape, seed, scales=(2, 3, 5), weights=(0.45, 0.35, 0.2)):
    field = _multiscale_smooth_noise(shape, list(scales), list(weights), seed)
    return field.astype(np.float32)


def _spec_trizone_frozen_ember_chrome_bespoke(shape, mask, seed, sm):
    zone_ice, zone_ember, zone_chrome, boundary = _voronoi_3zone(shape, seed, 7820)
    y, x, yf, xf = _trizone_xy_fields(shape)
    frost = _trizone_highpass(shape, seed + 9821, (2, 4, 9), (0.50, 0.32, 0.18))
    ember_noise = _trizone_highpass(shape, seed + 9822, (3, 6, 12), (0.46, 0.34, 0.20))
    chrome_scrub = _trizone_highpass(shape, seed + 9823, (2, 5, 13), (0.52, 0.28, 0.20))

    ice_veins = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.145 + y * 0.055) + frost * 4.8)), 0, 1), 10)
    ice_needles = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.37 - y * 0.19) + frost * 3.2)), 0, 1), 13)
    ember_cracks = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.070 - y * 0.115) + ember_noise * 5.5)), 0, 1), 9)
    ember_pin = (ember_noise > 0.58).astype(np.float32)
    chrome_lines = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.55 + y * 0.075) + chrome_scrub * 2.5)), 0, 1), 12)

    ice_detail = np.clip(0.40 + frost * 0.34 + ice_veins * 0.55 + ice_needles * 0.28, 0, 1)
    ember_detail = np.clip(0.42 + ember_noise * 0.30 + ember_cracks * 0.70 + ember_pin * 0.18, 0, 1)
    chrome_detail = np.clip(0.46 + chrome_scrub * 0.20 + chrome_lines * 0.50, 0, 1)

    M = (
        zone_ice * (90 + ice_detail * 88)
        + zone_ember * (142 + ember_detail * 78)
        + zone_chrome * (222 + chrome_detail * 32)
    )
    G = (
        zone_ice * (58 + (1.0 - ice_detail) * 92)
        + zone_ember * (28 + (1.0 - ember_detail) * 58)
        + zone_chrome * (3 + chrome_lines * 18)
    )
    B = (
        zone_ice * (78 + ice_detail * 82)
        + zone_ember * (28 + ember_detail * 84)
        + zone_chrome * (16 + chrome_detail * 28)
    )

    M = M * (1 - boundary) + (245 + chrome_lines * 10) * boundary
    G = G * (1 - boundary) + (3 + ice_needles * 9) * boundary
    B = B * (1 - boundary) + (22 + ember_cracks * 50) * boundary
    return _spec_out(shape, mask, M, G, B)


def _paint_trizone_frozen_ember_chrome_bespoke(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    zone_ice, zone_ember, zone_chrome, boundary = _voronoi_3zone(shape, seed, 7820)
    y, x, yf, xf = _trizone_xy_fields(shape)
    frost = _trizone_highpass(shape, seed + 9831, (2, 4, 9), (0.50, 0.32, 0.18))
    ember_noise = _trizone_highpass(shape, seed + 9832, (3, 6, 12), (0.46, 0.34, 0.20))
    chrome_scrub = _trizone_highpass(shape, seed + 9833, (2, 5, 13), (0.52, 0.28, 0.20))
    ice_veins = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.145 + y * 0.055) + frost * 4.8)), 0, 1), 10)
    ember_cracks = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.070 - y * 0.115) + ember_noise * 5.5)), 0, 1), 9)
    chrome_lines = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.55 + y * 0.075) + chrome_scrub * 2.5)), 0, 1), 12)

    result = paint.copy()
    cold = zone_ice * pm
    hot = zone_ember * pm
    mirror = zone_chrome * pm
    result[:, :, 0] = np.clip(result[:, :, 0] + hot * (0.25 + ember_cracks * 0.32) - cold * 0.05 + mirror * (0.10 + chrome_lines * 0.08), 0, 1)
    result[:, :, 1] = np.clip(result[:, :, 1] + cold * (0.12 + ice_veins * 0.14) + hot * (0.04 + ember_noise * 0.04) + mirror * 0.10, 0, 1)
    result[:, :, 2] = np.clip(result[:, :, 2] + cold * (0.27 + frost * 0.10 + ice_veins * 0.16) - hot * (0.07 + ember_cracks * 0.04) + mirror * (0.12 + chrome_scrub * 0.04), 0, 1)
    surface = zone_ice * (frost * 0.10 + ice_veins * 0.12) + zone_ember * (ember_noise * 0.10 + ember_cracks * 0.16) + zone_chrome * (chrome_scrub * 0.08 + chrome_lines * 0.10)
    for c, gain in enumerate((1.0, 0.88, 0.76)):
        result[:, :, c] = np.clip(result[:, :, c] + surface * gain * mask * pm, 0, 1)
    rim = boundary * (0.18 + chrome_lines * 0.18) * pm
    result[:, :, 0] = np.clip(result[:, :, 0] + rim * 0.95, 0, 1)
    result[:, :, 1] = np.clip(result[:, :, 1] + rim * 0.92, 0, 1)
    result[:, :, 2] = np.clip(result[:, :, 2] + rim * 1.05, 0, 1)
    return np.clip(result + _trizone_bb3(bb, shape) * 0.34 * mask[:, :, np.newaxis], 0, 1)


def _spec_trizone_glass_metal_matte_bespoke(shape, mask, seed, sm):
    zone_glass, zone_metal, zone_matte, boundary = _voronoi_3zone(shape, seed, 7850)
    y, x, yf, xf = _trizone_xy_fields(shape)
    glass_flow = _trizone_highpass(shape, seed + 9851, (2, 5, 11), (0.50, 0.30, 0.20))
    metal_brush = _trizone_highpass(shape, seed + 9852, (2, 4, 8), (0.46, 0.34, 0.20))
    matte_pores = _trizone_highpass(shape, seed + 9853, (2, 3, 7), (0.44, 0.34, 0.22))

    glass_cracks = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.120 - y * 0.085) + glass_flow * 5.6)), 0, 1), 11)
    glass_splinters = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.37 + y * 0.31) + glass_flow * 3.4)), 0, 1), 14)
    brush_lines = np.power(np.clip(1.0 - np.abs(np.sin(y * 0.62 + metal_brush * 4.0)), 0, 1), 10)
    cross_scuff = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.18 + y * 0.21) + metal_brush * 2.5)), 0, 1), 12)
    pore = np.clip((matte_pores + 1.0) * 0.5, 0, 1)
    stipple = (pore > 0.56).astype(np.float32) * 0.45 + pore * 0.35

    M = (
        zone_glass * (18 + glass_cracks * 68 + glass_splinters * 36)
        + zone_metal * (172 + brush_lines * 58 + cross_scuff * 18)
        + zone_matte * (22 + stipple * 46)
    )
    G = (
        zone_glass * (18 + (1.0 - glass_flow) * 36)
        + zone_metal * (34 + (1.0 - brush_lines) * 62)
        + zone_matte * (150 + stipple * 70)
    )
    B = (
        zone_glass * (38 + glass_cracks * 80)
        + zone_metal * (20 + brush_lines * 38)
        + zone_matte * (112 + stipple * 64)
    )
    M = M * (1 - boundary) + (230 + cross_scuff * 22) * boundary
    G = G * (1 - boundary) + (10 + glass_splinters * 22) * boundary
    B = B * (1 - boundary) + (44 + glass_cracks * 66) * boundary
    return _spec_out(shape, mask, M, G, B)


def _paint_trizone_glass_metal_matte_bespoke(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    zone_glass, zone_metal, zone_matte, boundary = _voronoi_3zone(shape, seed, 7850)
    y, x, yf, xf = _trizone_xy_fields(shape)
    glass_flow = _trizone_highpass(shape, seed + 9861, (2, 5, 11), (0.50, 0.30, 0.20))
    metal_brush = _trizone_highpass(shape, seed + 9862, (2, 4, 8), (0.46, 0.34, 0.20))
    matte_pores = _trizone_highpass(shape, seed + 9863, (2, 3, 7), (0.44, 0.34, 0.22))
    glass_cracks = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.120 - y * 0.085) + glass_flow * 5.6)), 0, 1), 11)
    glass_splinters = np.power(np.clip(1.0 - np.abs(np.sin((x * 0.37 + y * 0.31) + glass_flow * 3.4)), 0, 1), 14)
    brush_lines = np.power(np.clip(1.0 - np.abs(np.sin(y * 0.62 + metal_brush * 4.0)), 0, 1), 10)
    pore = np.clip((matte_pores + 1.0) * 0.5, 0, 1)
    stipple = (pore > 0.56).astype(np.float32) * 0.28 + pore * 0.18

    result = paint.copy()
    glass = zone_glass * pm
    metal = zone_metal * pm
    matte = zone_matte * pm
    result[:, :, 0] = np.clip(result[:, :, 0] - glass * 0.05 + metal * (0.16 + brush_lines * 0.10) + matte * (0.02 + stipple * 0.05), 0, 1)
    result[:, :, 1] = np.clip(result[:, :, 1] + glass * (0.08 + glass_cracks * 0.08) + metal * (0.14 + brush_lines * 0.08) + matte * (0.02 + stipple * 0.05), 0, 1)
    result[:, :, 2] = np.clip(result[:, :, 2] + glass * (0.18 + glass_flow * 0.06 + glass_splinters * 0.12) + metal * (0.12 + brush_lines * 0.06) - matte * 0.03, 0, 1)
    detail = zone_glass * (glass_cracks * 0.16 + glass_splinters * 0.10) + zone_metal * (brush_lines * 0.13 + metal_brush * 0.06) + zone_matte * stipple
    result[:, :, 0] = np.clip(result[:, :, 0] + detail * 0.70 * mask, 0, 1)
    result[:, :, 1] = np.clip(result[:, :, 1] + detail * 0.82 * mask, 0, 1)
    result[:, :, 2] = np.clip(result[:, :, 2] + detail * 0.95 * mask, 0, 1)
    rim = boundary * (0.16 + glass_cracks * 0.14 + brush_lines * 0.10) * pm
    result[:, :, 0] = np.clip(result[:, :, 0] + rim * 0.78, 0, 1)
    result[:, :, 1] = np.clip(result[:, :, 1] + rim * 0.88, 0, 1)
    result[:, :, 2] = np.clip(result[:, :, 2] + rim * 1.05, 0, 1)
    return np.clip(result + _trizone_bb3(bb, shape) * 0.30 * mask[:, :, np.newaxis], 0, 1)


# Chrome / Candy / Matte
spec_trizone_chrome_candy_matte, paint_trizone_chrome_candy_matte = _make_trizone_fusion((255,2,16), (200,15,16), (0,200,180), 7800)
spec_trizone_pearl_carbon_gold, paint_trizone_pearl_carbon_gold = _make_trizone_fusion((100,40,16), (55,35,16), (255,2,16), 7810)
spec_trizone_frozen_ember_chrome, paint_trizone_frozen_ember_chrome = _spec_trizone_frozen_ember_chrome_bespoke, _paint_trizone_frozen_ember_chrome_bespoke
spec_trizone_anodized_candy_silk, paint_trizone_anodized_candy_silk = _make_trizone_fusion((170,80,100), (200,15,16), (30,85,16), 7830)
spec_trizone_vanta_chrome_pearl, paint_trizone_vanta_chrome_pearl = _make_trizone_fusion((0,255,255), (255,2,16), (100,40,16), 7840)
spec_trizone_glass_metal_matte, paint_trizone_glass_metal_matte = _spec_trizone_glass_metal_matte_bespoke, _paint_trizone_glass_metal_matte_bespoke
spec_trizone_mercury_obsidian_candy, paint_trizone_mercury_obsidian_candy = _make_trizone_fusion((255,3,16), (130,6,16), (200,15,16), 7860)
spec_trizone_titanium_copper_chrome, paint_trizone_titanium_copper_chrome = _make_trizone_fusion((180,70,80), (190,55,16), (255,2,16), 7870)
spec_trizone_ceramic_flake_satin, paint_trizone_ceramic_flake_satin = _make_trizone_fusion((60,8,16), (240,12,16), (0,100,120), 7880)
spec_trizone_stealth_spectra_frozen, paint_trizone_stealth_spectra_frozen = _make_trizone_fusion((30,220,180), (245,8,16), (225,140,16), 7890)


def _tz_hash(shape, seed, salt):
    _, _, yf, xf = _trizone_xy_fields(shape)
    n = np.sin((xf * 127.1 + yf * 311.7 + (int(seed) + salt) * 0.013) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _tz_ridge(v, power=1.0):
    return np.power(np.clip(1.0 - np.abs(v), 0, 1), power).astype(np.float32)


_tz_fields_cache = {}


def _tz_fields(shape, seed, mode):
    cache_key = (shape, int(seed), mode)
    cached = _tz_fields_cache.get(cache_key)
    if cached is not None:
        return cached

    y, x, yf, xf = _trizone_xy_fields(shape)
    phase = (int(seed) % 8192) * 0.000767 * np.pi * 2.0
    tw = np.float32(np.pi * 2.0)
    grain = _tz_hash(shape, seed, 191)
    micro = _tz_hash(shape, seed, 719) * 0.58 + (np.sin((xf * 71.0 - yf * 53.0) * tw + phase) * 0.5 + 0.5) * 0.42

    if mode == "chrome_candy_matte":
        a = xf * 1.05 + np.sin(yf * tw * 2.2 + phase) * 0.11
        b = 1.0 - yf * 0.98 + np.sin(xf * tw * 3.1 - phase) * 0.09
        c = np.sqrt((xf - 0.62) ** 2 + (yf - 0.42) ** 2) * 1.35
        accent = _tz_ridge(np.sin((xf * 18.0 + yf * 5.0) * tw + phase), 2.0)
        colors = ((0.93, 0.14, 0.20), (0.16, 0.86, 0.76), (0.36, 0.36, 0.42))
    elif mode == "pearl_carbon_gold":
        weave_a = np.sin((xf * 64.0 + yf * 9.0) * tw + phase)
        weave_b = np.sin((-xf * 9.0 + yf * 64.0) * tw - phase * 0.7)
        drift = np.sin((xf * 2.2 + yf * 3.4) * tw + phase) * 0.5 + 0.5
        a = 0.50 + weave_a * 0.08 + yf * 0.26
        b = 0.54 + weave_b * 0.08 + (1.0 - xf) * 0.18
        c = drift * 0.55 + _tz_ridge(np.sin((xf * 8.0 - yf * 4.0) * tw + phase), 1.9) * 0.34
        accent = _tz_ridge(weave_a, 2.7) * _tz_ridge(weave_b, 2.3)
        colors = ((0.86, 0.78, 0.62), (0.04, 0.05, 0.06), (1.00, 0.62, 0.14))
    elif mode == "frozen_ember_chrome":
        crack = np.sin((xf * 11.0 - yf * 7.0) * tw + np.sin(yf * tw * 5.0) * 0.9 + phase)
        a = 1.0 - yf + crack * 0.10
        b = xf * 0.9 + _tz_ridge(crack, 1.1) * 0.34
        c = np.sin((xf * 2.2 + yf * 2.9) * tw - phase) * 0.5 + 0.5
        accent = _tz_ridge(crack, 2.0)
        colors = ((0.28, 0.70, 1.00), (1.00, 0.24, 0.05), (0.74, 0.78, 0.82))
    elif mode == "anodized_candy_silk":
        ribbon = np.sin((xf * 4.5 + yf * 7.8) * tw + np.sin((xf - yf) * tw * 2.0) + phase)
        a = yf + ribbon * 0.18
        b = 1.0 - xf * 0.82 + np.sin(yf * tw * 5.0 + phase) * 0.12
        c = np.sin((xf * 1.7 - yf * 2.4) * tw - phase) * 0.5 + 0.5
        accent = _tz_ridge(np.sin((xf * 42.0 + yf * 7.0) * tw + phase), 2.4)
        colors = ((0.50, 0.62, 0.96), (0.95, 0.12, 0.28), (0.20, 0.78, 0.52))
    elif mode == "vanta_chrome_pearl":
        void = np.sqrt((xf - 0.42) ** 2 + (yf - 0.53) ** 2)
        ribbon = np.sin((xf * 5.8 - yf * 3.4) * tw + phase)
        a = 1.0 - void * 1.42
        b = ribbon * 0.5 + 0.5
        c = yf * 0.9 + np.sin(xf * tw * 4.0) * 0.08
        accent = _tz_ridge(ribbon, 2.0)
        colors = ((0.01, 0.01, 0.02), (0.86, 0.90, 0.96), (0.78, 0.64, 0.94))
    elif mode == "glass_metal_matte":
        pane = np.sin((xf * 2.1 + yf * 1.3) * tw + phase)
        shard = np.sin((xf * 8.0 - yf * 5.3) * tw + np.sin(yf * tw * 3.0) + phase)
        a = xf * 0.74 + yf * 0.28 + pane * 0.12
        b = 1.0 - yf * 0.82 + np.sin(xf * tw * 2.8 - phase) * 0.10
        c = 1.0 - np.sqrt((xf - 0.70) ** 2 + (yf - 0.34) ** 2) * 1.15 + grain * 0.10
        accent = _tz_ridge(shard, 2.2) + _tz_ridge(pane, 1.8) * 0.35
        colors = ((0.20, 0.70, 0.92), (0.76, 0.76, 0.72), (0.20, 0.21, 0.22))
    elif mode == "mercury_obsidian_candy":
        swirl = np.sin((np.sqrt((xf - 0.55) ** 2 + (yf - 0.45) ** 2) * 18.0 + np.arctan2(yf - 0.45, xf - 0.55) * 3.0) + phase)
        a = swirl * 0.5 + 0.5
        b = 1.0 - np.sqrt((xf - 0.30) ** 2 + (yf - 0.70) ** 2) * 1.25
        c = xf * 0.72 + yf * 0.28 + grain * 0.10
        accent = _tz_ridge(swirl, 1.8)
        colors = ((0.80, 0.84, 0.90), (0.02, 0.02, 0.04), (0.88, 0.08, 0.18))
    elif mode == "titanium_copper_chrome":
        brushed = np.sin((yf * 42.0 + np.sin(xf * tw * 4.0) * 1.8) + phase)
        eddy = np.sin((xf * 3.1 + yf * 1.7) * tw + np.sin((xf - yf) * tw * 2.0) + phase)
        a = xf * 0.78 + brushed * 0.05
        b = 1.0 - yf * 0.72 + eddy * 0.11
        c = np.sqrt((xf - 0.35) ** 2 + (yf - 0.68) ** 2) * -1.05 + 1.0 + np.sin(yf * tw * 6.0) * 0.07
        accent = _tz_ridge(brushed, 2.8) + _tz_ridge(eddy, 1.8) * 0.42
        colors = ((0.44, 0.54, 0.64), (0.94, 0.42, 0.16), (0.82, 0.86, 0.90))
    elif mode == "ceramic_flake_satin":
        chips = np.sin((np.floor(xf * 34.0 + grain * 2.5) * 13.1 + np.floor(yf * 31.0 - grain * 2.1) * 7.7) + phase)
        flow = np.sin((xf * 3.0 - yf * 2.1) * tw + phase)
        a = yf * 0.68 + grain * 0.22 + flow * 0.08
        b = 1.0 - xf * 0.72 + _tz_ridge(chips, 1.4) * 0.18
        c = 1.0 - np.sqrt((xf - 0.66) ** 2 + (yf - 0.66) ** 2) * 1.10 + grain * 0.08
        accent = (grain > 0.66).astype(np.float32) * 0.72 + _tz_ridge(chips, 2.4) * 0.42
        colors = ((0.62, 0.56, 0.48), (0.92, 0.78, 0.50), (0.12, 0.58, 0.62))
    elif mode == "stealth_spectra_frozen":
        stealth = np.sin((xf * 3.2 + yf * 2.0) * tw + phase)
        aurora = np.sin((xf * 2.8 - yf * 5.6) * tw + np.sin(xf * tw * 3.0) + phase)
        a = 1.0 - np.sqrt((xf - 0.22) ** 2 + (yf - 0.42) ** 2) * 1.30 + stealth * 0.08
        b = xf * 0.62 + _tz_ridge(aurora, 1.6) * 0.28
        c = 1.0 - yf * 0.78 + np.sin((xf * 1.6 + yf * 2.4) * tw - phase) * 0.10
        accent = _tz_ridge(aurora, 2.2) + (grain > 0.72).astype(np.float32) * 0.35
        colors = ((0.02, 0.04, 0.08), (0.18, 0.90, 1.00), (0.82, 0.92, 1.00))
    else:
        a, b, c = xf, yf, 1.0 - xf
        accent = micro
        colors = ((0.55, 0.55, 0.55), (0.85, 0.50, 0.25), (0.18, 0.70, 0.85))

    stack = np.stack((a, b, c), axis=0).astype(np.float32)
    stack = (stack - stack.mean(axis=0, keepdims=True)) * 6.0
    e = np.exp(stack - stack.max(axis=0, keepdims=True))
    zones = e / np.maximum(e.sum(axis=0, keepdims=True), 1e-6)
    edge = np.clip(
        np.abs(np.diff(zones[0], axis=1, prepend=zones[0][:, :1]))
        + np.abs(np.diff(zones[1], axis=0, prepend=zones[1][:1, :]))
        + np.abs(np.diff(zones[2], axis=1, prepend=zones[2][:, :1])),
        0,
        1,
    )
    accent = np.clip(accent + edge * 0.9 + np.clip((micro - 0.68) * 2.8, 0, 1), 0, 1).astype(np.float32)
    color_arr = np.array(colors, dtype=np.float32)
    base_rgb = (
        zones[0][:, :, np.newaxis] * color_arr[0]
        + zones[1][:, :, np.newaxis] * color_arr[1]
        + zones[2][:, :, np.newaxis] * color_arr[2]
    )
    result = (zones.astype(np.float32), base_rgb.astype(np.float32), micro.astype(np.float32), accent.astype(np.float32), edge.astype(np.float32))
    if len(_tz_fields_cache) > 1:
        _tz_fields_cache.pop(next(iter(_tz_fields_cache)))
    _tz_fields_cache[cache_key] = result
    return result


def _make_trizone_fast(mode, spec_profile, seed_offset=0):
    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        zones, _, micro, accent, edge = _tz_fields(shape, int(seed) + seed_offset, mode)
        m_vals, r_vals, c_vals = spec_profile
        M = zones[0] * m_vals[0] + zones[1] * m_vals[1] + zones[2] * m_vals[2]
        G = zones[0] * r_vals[0] + zones[1] * r_vals[1] + zones[2] * r_vals[2]
        B = zones[0] * c_vals[0] + zones[1] * c_vals[1] + zones[2] * c_vals[2]
        glint = np.clip(accent * 0.72 + micro * 0.28, 0, 1)
        M = np.clip(M + glint * 46.0 + edge * 82.0, 0, 255)
        G = np.clip(G - glint * 34.0 + (1.0 - micro) * 18.0 + edge * 8.0, 0, 255)
        B = np.clip(B + accent * 42.0 + edge * 58.0, 0, 255)
        return _spec_out(shape, mask2, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint = paint[:, :, :3].copy()
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        zones, base_rgb, micro, accent, edge = _tz_fields(shape, int(seed) + seed_offset, mode)
        bb3 = _trizone_bb3(bb, shape)
        strength = np.clip(mask2 * float(pm), 0, 1)
        source = np.asarray(paint[:, :, :3], dtype=np.float32)
        if source.max() > 1.5:
            source = source / 255.0
        surface = np.clip(base_rgb + accent[:, :, np.newaxis] * 0.16 + micro[:, :, np.newaxis] * 0.055 + edge[:, :, np.newaxis] * 0.20, 0, 1)
        mixed = source * (1.0 - strength[:, :, np.newaxis] * 0.88) + surface * (strength[:, :, np.newaxis] * 0.88)
        return np.clip(mixed + bb3 * 0.10 * strength[:, :, np.newaxis], 0, 1)

    return spec_fn, paint_fn


spec_trizone_chrome_candy_matte, paint_trizone_chrome_candy_matte = _make_trizone_fast(
    "chrome_candy_matte", ((225, 178, 36), (8, 30, 170), (22, 70, 110)), 7920
)
spec_trizone_pearl_carbon_gold, paint_trizone_pearl_carbon_gold = _make_trizone_fast(
    "pearl_carbon_gold", ((130, 32, 218), (54, 182, 18), (118, 46, 36)), 7930
)
spec_trizone_frozen_ember_chrome, paint_trizone_frozen_ember_chrome = _make_trizone_fast(
    "frozen_ember_chrome", ((92, 185, 232), (56, 34, 10), (108, 68, 28)), 7940
)
spec_trizone_anodized_candy_silk, paint_trizone_anodized_candy_silk = _make_trizone_fast(
    "anodized_candy_silk", ((168, 206, 72), (46, 24, 96), (118, 46, 26)), 7950
)
spec_trizone_vanta_chrome_pearl, paint_trizone_vanta_chrome_pearl = _make_trizone_fast(
    "vanta_chrome_pearl", ((18, 244, 118), (202, 8, 18), (96, 74, 88)), 7960
)
spec_trizone_glass_metal_matte, paint_trizone_glass_metal_matte = _make_trizone_fast(
    "glass_metal_matte", ((42, 202, 54), (28, 36, 158), (78, 176, 124)), 7970
)
spec_trizone_mercury_obsidian_candy, paint_trizone_mercury_obsidian_candy = _make_trizone_fast(
    "mercury_obsidian_candy", ((224, 18, 174), (10, 184, 18), (112, 38, 28)), 7980
)
spec_trizone_titanium_copper_chrome, paint_trizone_titanium_copper_chrome = _make_trizone_fast(
    "titanium_copper_chrome", ((166, 176, 232), (44, 58, 12), (114, 28, 22)), 7990
)
spec_trizone_ceramic_flake_satin, paint_trizone_ceramic_flake_satin = _make_trizone_fast(
    "ceramic_flake_satin", ((72, 168, 116), (104, 82, 32), (64, 142, 76)), 8000
)
spec_trizone_stealth_spectra_frozen, paint_trizone_stealth_spectra_frozen = _make_trizone_fast(
    "stealth_spectra_frozen", ((28, 198, 230), (56, 26, 88), (118, 72, 128)), 8010
)


# ================================================================
# PARADIGM 10: DEPTH ILLUSION via CC Roughness - 3D from flat
# ================================================================

def _make_depth_fusion(base_m, base_g, cc_deep, cc_shallow, pattern_type, seed_offset=0):
    """Factory: CC roughness creates real 3D depth illusion through PBR spec.
    Each pattern uses advanced simulation for convincing depth."""
    if _FF_V2 is not None and pattern_type != "map":
        return _adapt_staging_factory_result(_FF_V2._make_depth_fusion(base_m, base_g, cc_deep, cc_shallow, pattern_type, seed_offset))
    def _compute_depth_pattern(shape, seed):
        """Compute the actual depth pattern field pv (0-1) for the given pattern_type."""
        h, w = shape
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)
        warp1 = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 700)
        warp2 = _noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed + seed_offset + 701)
        warp_s = min(h, w) * 0.15
        yw, xw = yf + warp1 * warp_s, xf + warp2 * warp_s

        if pattern_type == "canyon":
            # SPB-100 tick 92 (owner: "Just does not scream Canyon at all.
            # Sparse, uninspired"). Dramatic redesign: deep horizontal-
            # dominant striation bands (real canyons have horizontal strata),
            # ridge math with hard contrast, dramatic shadow valleys, and
            # rich per-strata chroma so the spec channel reads as layered
            # sandstone. Composite 51.8 (tick 91) → ≥85 target.
            n_macro = _noise(shape, [4, 8, 16], [0.32, 0.40, 0.28], seed + seed_offset)
            n_strata = _noise(shape, [32, 64, 128, 256], [0.28, 0.30, 0.24, 0.18], seed + seed_offset + 50)
            n_grit = _noise(shape, [256, 512], [0.55, 0.45], seed + seed_offset + 51)
            # Horizontal-banded strata: stronger Y-direction modulation gives
            # the layered-sandstone feel of a real canyon wall.
            y_band = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
            strata_phase = y_band * 26.0 + n_macro * 1.8
            strata = np.abs(np.sin(strata_phase * np.pi))
            strata_sharp = np.clip(1.0 - strata / 0.12, 0, 1)
            ridge_macro = 1.0 - np.abs(n_macro) * 2.0
            ridge_strata = 1.0 - np.abs(n_strata) * 2.0
            ridge_grit = 1.0 - np.abs(n_grit) * 2.0
            # Combine: macro carves the canyon shape, strata gives layered
            # bands, grit adds high-freq rock texture, strata_sharp adds
            # the dramatic dark cuts between layers.
            erosion = np.clip(ridge_macro * 0.30 + ridge_strata * 0.30
                              + ridge_grit * 0.18 + strata_sharp * 0.22, 0, 1)
            pv = np.clip(erosion ** 2.2, 0, 1)  # 1.8→2.2 = harder shadows
            dx = np.abs(np.diff(pv, axis=1, prepend=pv[:, :1]))
            dy = np.abs(np.diff(pv, axis=0, prepend=pv[:1, :]))
            ridge_edge = np.clip((dx + dy) * 12, 0, 1)  # 8→12 sharper edge accents
            # SPB-99 P2: per-strata band chroma — each horizontal band gets
            # a different shade so the canyon wall reads as actual sandstone
            # layers (red iron strata, white limestone, dark shale, etc).
            strata_band_id = np.floor(strata_phase * 0.5).astype(np.float32)
            band_chroma = np.sin(strata_band_id * 12.9898 + (seed % 1000) * 0.011) * 43758.5453
            band_chroma = (band_chroma - np.floor(band_chroma)).astype(np.float32)
            chroma_field = (0.58 + band_chroma * 0.84).astype(np.float32)
            pv = np.clip(pv * chroma_field + ridge_edge * 0.65, 0, 1)
        elif pattern_type == "bubble":
            # SPB-105 perf heartbeat 2026-05-31; owner: "Speed is king" and "No base can be more than 4 seconds."
            # Local bubble patches keep the 360 fine domes while avoiding the old full-canvas broadcast tensor.
            # Metric before this pass: depth_bubble 13721.6 ms after-row; M7 not rerun in this perf-only heartbeat.
            # Previous chunked broadcast still spent too much time on full patch stacks;
            # this keeps density while evaluating only each bubble's local footprint.
            rng = np.random.RandomState(seed + seed_offset)
            n_bubbles = 360
            cy_all = rng.uniform(-0.94, 0.94, n_bubbles).astype(np.float32)
            cx_all = rng.uniform(-0.94, 0.94, n_bubbles).astype(np.float32)
            r_all = rng.uniform(0.010, 0.038, n_bubbles).astype(np.float32)
            chroma_all = rng.uniform(0.55, 1.45, n_bubbles).astype(np.float32)
            pv_dome = np.zeros((h, w), dtype=np.float32)
            pv_highlight = np.zeros((h, w), dtype=np.float32)
            px_per_x = max(w - 1, 1) * 0.5
            px_per_y = max(h - 1, 1) * 0.5
            for cy_n, cx_n, r_n, chroma in zip(cy_all, cx_all, r_all, chroma_all):
                cy_px = (cy_n + 1.0) * px_per_y
                cx_px = (cx_n + 1.0) * px_per_x
                rx = max(2.0, float(r_n) * px_per_x)
                ry = max(2.0, float(r_n) * px_per_y)
                pad_x = max(3, int(np.ceil(rx * 1.35)))
                pad_y = max(3, int(np.ceil(ry * 1.35)))
                x0 = max(0, int(np.floor(cx_px - pad_x)))
                x1 = min(w, int(np.ceil(cx_px + pad_x + 1)))
                y0 = max(0, int(np.floor(cy_px - pad_y)))
                y1 = min(h, int(np.ceil(cy_px + pad_y + 1)))
                if x1 <= x0 or y1 <= y0:
                    continue
                yy = (np.arange(y0, y1, dtype=np.float32) - cy_px) / ry
                xx = (np.arange(x0, x1, dtype=np.float32) - cx_px) / rx
                ratio = np.sqrt(yy[:, None] * yy[:, None] + xx[None, :] * xx[None, :])
                falloff = np.clip(1.0 - ratio * ratio, 0.0, 1.0)
                dome = falloff * float(chroma)
                fresnel = np.exp(-(np.clip(ratio, 0.0, 1.0) - 0.85) ** 2 / 0.02) * 0.8
                fresnel *= (ratio <= 1.15).astype(np.float32)
                sy = (np.arange(y0, y1, dtype=np.float32) - (cy_px - ry * 0.30)) / max(ry * 0.15, 1.0)
                sx = (np.arange(x0, x1, dtype=np.float32) - (cx_px + rx * 0.20)) / max(rx * 0.15, 1.0)
                spec_dist = sy[:, None] * sy[:, None] + sx[None, :] * sx[None, :]
                spec = np.exp(-spec_dist) * falloff
                highlight = (fresnel + spec) * float(chroma)
                pv_dome[y0:y1, x0:x1] = np.maximum(pv_dome[y0:y1, x0:x1], dome)
                pv_highlight[y0:y1, x0:x1] = np.maximum(pv_highlight[y0:y1, x0:x1], highlight)
            pv = np.clip(pv_dome * 0.7 + pv_highlight * 0.3, 0, 1)
        elif pattern_type == "ripple":
            # SPB-100 tick 91 (owner: "Nothing feels like a ripple here").
            # Was 5 centers, amp `1/(1+dist*0.003)` (decayed too fast).
            # Now: 12 centers, amp `1/(1+dist*0.0008)` = 4× longer reach, so
            # ripples actually meet and interfere like water. Freq range
            # bumped 0.06-0.10 → 0.10-0.18 (finer water at 2048²).
            rng = np.random.RandomState(seed + seed_offset + 100)
            pv = np.zeros((h, w), dtype=np.float32)
            n_centers = 12
            for i in range(n_centers):
                cy = rng.uniform(0.05, 0.95) * h
                cx = rng.uniform(0.05, 0.95) * w
                freq = rng.uniform(0.10, 0.18)
                phase = rng.uniform(0, 2 * np.pi)
                dist = np.sqrt((yw - cy)**2 + (xw - cx)**2)
                amp = 1.0 / (1.0 + dist * 0.0008)
                pv += np.sin(dist * freq + phase) * amp
            pv = np.clip(pv / n_centers * 0.5 + 0.5, 0, 1)
            pv = pv ** 1.5
        elif pattern_type == "scale":
            # SPB-100 tick 91 (owner: "Nothing feels like 'scale', pattern
            # too big"). sz divisor 22 → 80 makes scales 3.6× smaller per
            # axis = ~13× more scales per area. Now reads as actual fish-
            # scale tessellation at car-body 2048². Per-row chroma added.
            sz = max(8, min(h, w) // 80)
            row = (yw / (sz * 0.75)).astype(np.int32)
            col = ((xw + (row % 2).astype(np.float32) * (sz // 2)) / sz).astype(np.int32)
            cy_s = (row.astype(np.float32) + 0.5) * sz * 0.75
            cx_s = col.astype(np.float32) * sz + (row % 2).astype(np.float32) * (sz // 2) + sz // 2
            dy_s = (yw - cy_s) / (sz * 0.4)
            dx_s = (xw - cx_s) / (sz * 0.5)
            d = np.sqrt(dy_s**2 + dx_s**2)
            d_norm = np.clip(d, 0, 1.2)
            dome = np.clip(1.0 - d_norm ** 1.5, 0, 1)
            overlap = np.clip((yw - cy_s) / (sz * 0.35), 0, 1) * np.clip(1.0 - d_norm, 0, 1)
            rim = np.exp(-(d_norm - 0.8)**2 / 0.01) * 0.6
            # SPB-99 P2: per-scale chroma (hash on row*col)
            scale_id = (row.astype(np.float32) * 31.0 + col.astype(np.float32) * 17.0)
            scale_hash = np.sin(scale_id * 12.9898) * 43758.5453
            scale_hash = (scale_hash - np.floor(scale_hash)).astype(np.float32)
            pv = np.clip((dome * (1.0 - overlap * 0.5) + rim) * (0.66 + scale_hash * 0.68), 0, 1)
        elif pattern_type == "honeycomb":
            # SPB-100 tick 91 (owner: "Doesn't look like honeycomb - not
            # interlocking, way too big. LOOKS like low quality. Pixelated
            # even. AWFUL"). Root cause of pixelation: the depth pipeline
            # computes pv at sub-512² internal then upscales 4×, so 22-px
            # cells became visible 4×4 blocks. Fix: shrink cells 22→80 so
            # each cell is ≤6px internal — upscale artifacts now read as
            # detail, not pixels. Wall edge tightened for crisp interlock.
            sz = max(6, min(h, w) // 80)
            hex_d = _hex_cell_dist(shape, sz)
            floor = np.clip(1.0 - hex_d * 2.5, 0, 1)
            wall = np.clip((hex_d - 0.4) * 4, 0, 1)
            wall_edge = np.exp(-(hex_d - 0.4)**2 / 0.0025) * 0.85   # tighter+brighter
            # SPB-99 P2: pump per-cell chroma via hex_d noise modulation.
            # Use coarse low-freq noise as a "color region" map.
            chroma_field = _noise(shape, [8, 16], [0.6, 0.4], seed + seed_offset + 271)
            chroma_mod = (0.66 + (chroma_field * 0.5 + 0.5) * 0.68).astype(np.float32)
            pv = np.clip((floor * 0.8 + wall_edge * 0.5 - wall * 0.3) * chroma_mod, 0, 1)
        elif pattern_type == "map":
            # SPB-100 tick 92 (owner: "DEPTH should entail a 3D look. Like
            # the car is physically growing OUTWARD. Ridges, peaks, valleys
            # like topography on a map"). Total rebuild for the 3D feel:
            # (1) real heightfield with strong peaks (terrain^3 → high
            # contrast highs vs lows); (2) normal-map-style shading: a fake
            # sun direction × surface gradient produces directional shadows
            # so peaks visibly cast shadow toward one side and valleys hold
            # darker regions; (3) tight contour lines stay for the
            # topographic-chart vibe; (4) per-elevation-band chroma so peaks
            # vs valleys read as distinct colored regions.
            # Composite 52.8 (tick 91) → ≥85 target.
            terrain = _noise(shape, [4, 8, 16, 32, 64, 128, 256], [0.08, 0.14, 0.22, 0.24, 0.18, 0.10, 0.04], seed + seed_offset + 120)
            terrain01 = (terrain * 0.5 + 0.5).astype(np.float32)
            # Heighten the peaks: terrain^3 gives sharp summits, soft valleys.
            heightfield = np.clip(terrain01 ** 1.7, 0, 1)
            # Surface gradient = the normal map. Fake-light from upper-left.
            gy = np.diff(heightfield, axis=0, prepend=heightfield[:1, :])
            gx = np.diff(heightfield, axis=1, prepend=heightfield[:, :1])
            light_dx, light_dy = 0.6, -0.4   # upper-left light direction
            shading = np.clip(0.5 + (gx * light_dx + gy * light_dy) * 14.0, 0, 1)
            slope_mag = np.clip(np.sqrt(gx * gx + gy * gy) * 18.0, 0, 1)
            # Tight contour lines — topographic-chart aesthetic.
            contour = np.abs(np.sin(heightfield * 22.0 * np.pi))
            contour_sharp = np.clip(1.0 - contour / 0.05, 0, 1)
            # Sub-pixel rock texture
            micro = _noise(shape, [1, 2, 3, 5, 9, 17], [0.24, 0.22, 0.20, 0.16, 0.12, 0.06], seed + seed_offset + 122)
            # SPB-99 P2: discrete elevation BANDS with distinct chroma per
            # band — like USGS topo colors (green lowlands, tan midlands,
            # white peaks). Use heightfield to pick band, hash to color it.
            band_id = np.floor(heightfield * 8.0).astype(np.float32)
            band_chroma = np.sin(band_id * 12.9898 + (seed % 1000) * 0.011) * 43758.5453
            band_chroma = (band_chroma - np.floor(band_chroma)).astype(np.float32)
            elev_chroma = (0.55 + band_chroma * 0.92).astype(np.float32)
            pv = np.clip((heightfield * 0.45 + shading * 0.30 + contour_sharp * 0.16
                          + slope_mag * 0.10 + (micro + 1.0) * 0.04) * elev_chroma, 0, 1)
        elif pattern_type == "crack":
            # SPB-100 tick 92 round-2 (SPB-105 render budget breach).
            # 1500 points took 44.71s combined — 15× over budget. Back to
            # 500 points: still 1.8× tick-91 (280 → 500 → smaller shards
            # but the visible scale will be similar to last round). Need
            # to revisit the math if owner still sees them as too big.
            # Composite 86.5 (tick 91) → ≥85 target maintained.
            rng = np.random.RandomState(seed + seed_offset + 100)
            n_pts = 500
            pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
            pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
            pts_chroma = rng.uniform(0.55, 1.45, n_pts).astype(np.float32)
            # SPB-105 perf heartbeat 2026-05-31; owner: "Speed is king."
            # cKDTree keeps the 500 fine crack seeds but removes the Python per-point full-canvas loop.
            # Metric before this pass: depth_crack 10130.4 ms after-row; M7 not rerun in this perf-only heartbeat.
            coords = np.column_stack((yf.ravel(), xf.ravel())).astype(np.float32, copy=False)
            pts = np.column_stack((pts_y, pts_x)).astype(np.float32, copy=False)
            dist, owner = cKDTree(pts).query(coords, k=3)
            d1 = dist[:, 0].reshape(h, w).astype(np.float32)
            d2 = dist[:, 1].reshape(h, w).astype(np.float32)
            d3 = dist[:, 2].reshape(h, w).astype(np.float32)
            owner_idx = owner[:, 0].reshape(h, w).astype(np.int32)
            crack_edge = d2 - d1
            crack_norm = crack_edge / (np.percentile(crack_edge, 90) + 1e-6)
            # Tightened falloff 6 → 22: cracks are 3× thinner (sharper lines)
            # so they read as fine cracks instead of broad seams.
            cracks = np.exp(-crack_norm**2 * 22)
            triple = np.exp(-(d3 - d1)**2 / (np.percentile(d3 - d1, 50) + 1e-6)**2 * 2)
            # SPB-100 tick 92 round-2: hair-crack layer via multi-band noise.
            # Cheap (~0.1s) compared to adding more voronoi points (was 44s).
            # Gives the "many fine cracks" look the owner wants without
            # blowing the render budget.
            hair_n = _noise(shape, [128, 256, 512], [0.4, 0.35, 0.25], seed + seed_offset + 102)
            hair = np.clip(1.0 - np.abs(hair_n) * 4.0, 0, 1)
            hair = np.where(hair > 0.7, hair, 0).astype(np.float32)
            shard_chroma = pts_chroma[owner_idx]
            pv = np.clip((cracks * 0.65 + triple * cracks * 0.4 + hair * 0.4) * shard_chroma, 0, 1)
        elif pattern_type == "wave":
            # SPB-100 tick 92 (owner: "Just not enough going on"). 5 streams
            # → 9 streams + cross-interference patterns (where two wave
            # systems cross they produce constructive/destructive nodes,
            # giving the ocean its choppy character). Foam now multi-band
            # with sea-spray micro-particles. Composite 54.1 (tick 91)
            # → ≥85 target.
            rng = np.random.RandomState(seed + seed_offset + 800)
            steep = 0.85
            wave = np.zeros((h, w), dtype=np.float32)
            n_streams = 9
            stream_freqs = [0.025, 0.04, 0.07, 0.11, 0.18, 0.034, 0.06, 0.09, 0.14]
            stream_amps =  [1.00, 0.78, 0.55, 0.32, 0.18, 0.42, 0.30, 0.22, 0.14]
            stream_dirs = rng.uniform(0, 2 * np.pi, n_streams).astype(np.float32)
            for i in range(n_streams):
                f = stream_freqs[i]
                a = stream_amps[i]
                d = stream_dirs[i]
                phase_i = yw * f * np.cos(d) + xw * f * np.sin(d)
                gi = np.sin(phase_i - steep * np.sin(phase_i)) * a
                wave += gi
            # Cross-interference: combine two arbitrary streams as a product
            # to produce constructive/destructive choppy nodes.
            cross1 = np.sin((yw * 0.05 + xw * 0.04)) * np.sin((yw * 0.04 - xw * 0.05))
            cross2 = np.sin((yw * 0.09 - xw * 0.06)) * np.sin((yw * 0.06 + xw * 0.10))
            wave = np.clip(wave * 0.24 + cross1 * 0.16 + cross2 * 0.12 + 0.5, 0, 1)
            foam_main = np.clip((wave - 0.76) * 10.0, 0, 1)
            foam_spray = _noise(shape, [128, 256, 512], [0.4, 0.35, 0.25], seed + seed_offset + 801)
            foam_spray = np.clip((foam_spray + 1.0) * 0.5, 0, 1) * foam_main * 0.5
            pv = np.clip(wave * 0.72 + foam_main * 0.55 + foam_spray * 0.35, 0, 1)
        elif pattern_type == "pillow":
            # SPB-100 tick 91 (owner: "Just looks like random scratches").
            # Root cause: the cross-diagonal `cross` term was creating linear
            # streaks that read as scratches. Removed. Cell size shrunk
            # 18 → 60 = 3× smaller pillows per axis. Puff exponent softened
            # 0.7 → 0.5 for proper dome highlights. Stitch line softened.
            sz = max(8, min(h, w) // 60)
            cell_y = (yw % sz).astype(np.float32) / sz
            cell_x = (xw % sz).astype(np.float32) / sz
            puff = np.sin(cell_y * np.pi) * np.sin(cell_x * np.pi)
            puff = np.clip(puff, 0, 1) ** 0.5    # rounder dome
            sy = np.minimum(cell_y, 1.0 - cell_y)
            sx = np.minimum(cell_x, 1.0 - cell_x)
            stitch_d = np.minimum(sy, sx)
            stitch = np.clip(1.0 - stitch_d * 24, 0, 1)   # softer seam
            # SPB-99 P2: per-pillow chroma instead of the scratchy cross.
            cell_id = np.floor(yw / sz) * 19.0 + np.floor(xw / sz) * 23.0
            cell_hash = np.sin(cell_id * 12.9898) * 43758.5453
            cell_hash = (cell_hash - np.floor(cell_hash)).astype(np.float32)
            pv = np.clip((puff * (1.0 - stitch * 0.7)) * (0.66 + cell_hash * 0.68), 0, 1)
        elif pattern_type == "vortex":
            # SPB-100 tick 92 (owner: "Instead of a 4 square tiling effect
            # it should be a bit more abstract looking"). Killed the 2×2
            # grid that owner saw as a checkerboard. New approach: 7
            # vortexes at RANDOM offset centers across the canvas, each with
            # its own spin direction, radius envelope, phase, and chroma.
            # Result reads as an abstract swirling field, not a grid.
            # Composite 63.9 (tick 91) → ≥85 target.
            y_n = np.linspace(-1, 1, h, dtype=np.float32).reshape(h, 1)
            x_n = np.linspace(-1, 1, w, dtype=np.float32).reshape(1, w)
            warp_v = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 500) * 0.1
            rng = np.random.RandomState(seed + seed_offset + 600)
            n_vortexes = 7
            pv = np.zeros((h, w), dtype=np.float32)
            for i in range(n_vortexes):
                cy = rng.uniform(-0.85, 0.85)
                cx = rng.uniform(-0.85, 0.85)
                r_envelope = rng.uniform(0.32, 0.72)
                v_phase = rng.uniform(0, 2 * np.pi)
                v_spin = 1.0 if rng.random() < 0.5 else -1.0
                v_chroma = rng.uniform(0.55, 1.45)
                n_arms = int(rng.choice([3, 4, 5]))
                lx = (x_n - cx) + warp_v
                ly = (y_n - cy) + warp_v
                angle = np.arctan2(ly, lx) * v_spin
                dist = np.sqrt(lx * lx + ly * ly) + 0.001
                log_r = np.log(dist + 0.01)
                spiral = np.sin(angle * n_arms - log_r * 12 + v_phase) * 0.5 + 0.5
                spiral2 = np.sin(angle * (n_arms * 2) + log_r * 18 + v_phase * 1.3) * 0.3 + 0.5
                envelope = np.clip(1.0 - dist / r_envelope, 0, 1) ** 1.5
                contrib = (spiral * 0.6 + spiral2 * 0.4) * envelope * v_chroma
                pv = np.maximum(pv, contrib)
            pv = np.clip(pv, 0, 1)
        elif pattern_type == "erosion":
            # SPB-100 tick 91 (owner: "Needs way more diversity in spec
            # finish to make it come alive"). Explicit SPB-99 P2 ask. Added
            # finer noise bands (64, 128) for detail, and a per-region
            # chroma field that drives multi-shade spec output. Each
            # erosion region now reads as a distinct color zone.
            terrain = _noise(shape, [2, 4, 8, 16, 32, 64, 128], [0.08, 0.12, 0.18, 0.22, 0.18, 0.14, 0.08], seed + seed_offset + 100)
            terrain = np.clip(terrain * 0.5 + 0.5, 0, 1)
            gy = np.diff(terrain, axis=0, prepend=terrain[:1, :])
            gx = np.diff(terrain, axis=1, prepend=terrain[:, :1])
            grad_mag = np.sqrt(gy**2 + gx**2)
            erosion = np.clip(grad_mag * 15, 0, 1)
            deposit = np.clip(1.0 - grad_mag * 20, 0, 1) * np.clip(1.0 - terrain, 0, 1)
            eroded = terrain * (1.0 - erosion * 0.6) + deposit * 0.2
            fine = _noise(shape, [2, 4, 8, 16], [0.28, 0.30, 0.24, 0.18], seed + seed_offset + 200)
            # SPB-99 P2: low-freq chroma regions — different "patina ages"
            # across the surface produce distinct M/G/B shades downstream.
            region = _noise(shape, [4, 8, 16], [0.5, 0.3, 0.2], seed + seed_offset + 201)
            region_chroma = (0.62 + (region * 0.5 + 0.5) * 0.76).astype(np.float32)
            pv = np.clip((eroded + fine * 0.05 * erosion) * region_chroma, 0, 1)
        else:
            pv = np.zeros((h, w), dtype=np.float32)
        return pv

    @lru_cache(maxsize=16)
    def _cached_depth_pattern(ch, cw, cseed):
        return _compute_depth_pattern((int(ch), int(cw)), int(cseed))

    def _depth_work_shape(shape):
        # SPB-100 tick 92 round-2 (owner: "honeycomb STILL pixelated", but
        # also SPB-105 render budget = 2-3s). Full-res bypass cost ~8-10s.
        # New approach: middle path. Grid-quantized patterns render at 1024²
        # internal (was 512²) — halves the quantization step vs old code,
        # but stays ~4× faster than full 2048². On a 2048² output that's
        # an upscale factor of 2× instead of 4× → cells go from 4px-block
        # quantization to 2px, which reads as detail rather than pixels.
        h, w = shape[:2]  # tolerate (h,w) or (h,w,3) from the monolithic spec contract wrapper
        if pattern_type == "scale":
            return min(h, 1024), min(w, 1024), max(1, int(np.ceil(max(h, w) / 1024.0)))
        if pattern_type in ("honeycomb", "pillow"):
            return min(h, 768), min(w, 768), max(1, int(np.ceil(max(h, w) / 768.0)))
        if pattern_type == "bubble":
            # SPB-105 perf heartbeat 2026-05-31: bubble solves macro depth at 352,
            # then restore 1px carrier detail in the full-res paint/spec passes.
            return min(h, 352), min(w, 352), max(1, int(np.ceil(max(h, w) / 352.0)))
        if pattern_type in ("crack", "wave"):
            # SPB-105 perf heartbeat 2026-05-31: solve heavy macro depth at 384,
            # then restore 1px carrier detail in the full-res paint/spec passes.
            return min(h, 384), min(w, 384), max(1, int(np.ceil(max(h, w) / 384.0)))
        ds = max(1, int(np.ceil(max(h, w) / 512.0)))
        return max(96, h // ds), max(96, w // ds), ds

    def _depth_edge(pv):
        pv_dx = np.abs(np.diff(pv, axis=1, prepend=pv[:, :1]))
        pv_dy = np.abs(np.diff(pv, axis=0, prepend=pv[:1, :]))
        return np.clip(np.sqrt(pv_dx * pv_dx + pv_dy * pv_dy) * 8.5, 0, 1)

    def _hidden_depth_fields(shape, pv, seed):
        h, w = shape
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)
        fine = (_noise(shape, [1, 2, 3, 5], [0.34, 0.30, 0.22, 0.14], seed + seed_offset + 1701) + 1.0) * 0.5
        grain = (_noise(shape, [2, 4, 7, 11], [0.30, 0.30, 0.24, 0.16], seed + seed_offset + 1702) + 1.0) * 0.5
        flow = _noise(shape, [5, 9, 17], [0.42, 0.34, 0.24], seed + seed_offset + 1703)
        fleck = np.clip((fine - 0.58) * 3.4, 0, 1)
        pin = np.clip((grain - 0.72) * 7.0, 0, 1)
        contour = np.clip(1.0 - np.abs(np.sin((pv * 9.0 + flow * 0.18) * np.pi)) / 0.075, 0, 1)

        if pattern_type == "bubble":
            ring = np.clip(1.0 - np.abs(np.sin((pv * 7.5 + grain * 0.35) * np.pi)) / 0.060, 0, 1)
            motif = np.maximum(contour * 0.45, ring)
        elif pattern_type in ("ripple", "wave"):
            current = np.sin(yf * 0.034 + np.sin(xf * 0.018 + flow * 1.7) * 1.8 + pv * 5.0)
            motif = np.maximum(contour * 0.45, np.clip(1.0 - np.abs(current) / 0.070, 0, 1))
        elif pattern_type == "scale":
            crescents = np.sin(yf * 0.118 + np.sin(xf * 0.052 + flow) * 1.3 + pv * 4.4)
            motif = np.maximum(contour * 0.35, np.clip(1.0 - np.abs(crescents) / 0.062, 0, 1))
        elif pattern_type == "honeycomb":
            hd = _hex_cell_dist(shape, max(8, min(h, w) // 34))
            motif = np.maximum(contour * 0.35, np.exp(-((hd - 0.36) ** 2) / 0.004).astype(np.float32))
        elif pattern_type == "crack":
            stress = np.sin(xf * 0.030 + yf * 0.044 + pv * 9.0 + flow * 2.0)
            motif = np.maximum(contour * 0.30, np.clip(1.0 - np.abs(stress) / 0.052, 0, 1))
        elif pattern_type == "vortex":
            yn = yf / max(h - 1, 1) - 0.5
            xn = xf / max(w - 1, 1) - 0.5
            angle = np.arctan2(yn, xn)
            dist = np.sqrt(xn * xn + yn * yn)
            spiral = np.sin(angle * 5.0 - np.log(dist + 0.015) * 6.0 + pv * 5.5)
            motif = np.maximum(contour * 0.35, np.clip(1.0 - np.abs(spiral) / 0.070, 0, 1))
        elif pattern_type == "pillow":
            cell = max(18, min(h, w) // 18)
            seam_y = np.minimum((yf % cell) / cell, 1.0 - ((yf % cell) / cell))
            seam_x = np.minimum((xf % cell) / cell, 1.0 - ((xf % cell) / cell))
            ticks = np.clip(1.0 - np.minimum(seam_y, seam_x) * 28.0, 0, 1)
            motif = np.maximum(contour * 0.30, ticks * np.clip(0.35 + grain, 0, 1))
        elif pattern_type in ("map", "canyon", "erosion"):
            strata = np.sin((pv * 12.0 + yf * 0.012 + flow * 0.55) * np.pi)
            motif = np.maximum(contour, np.clip(1.0 - np.abs(strata) / 0.064, 0, 1) * 0.75)
        else:
            motif = contour

        motif = np.clip(motif * (0.42 + grain * 0.58), 0, 1)
        polish = np.clip((flow + 1.0) * 0.5 * 0.55 + fine * 0.45, 0, 1)
        return fine, grain, fleck, pin, motif, polish

    def _fullres_depth_micro(shape, seed):
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)
        hash_a = np.mod(np.sin(xf * 12.9898 + yf * 78.233 + seed * 0.137) * 43758.5453, 1.0).astype(np.float32)
        hash_b = np.mod(np.sin(xf * 39.3467 + yf * 11.135 + seed * 0.271) * 24634.6345, 1.0).astype(np.float32)
        glitter = np.clip((hash_a - 0.70) * 4.6, 0, 1)
        pin = np.clip((hash_b - 0.84) * 8.0, 0, 1)
        # SPB perf 2026-06-13 (fusions.py lane): the inner hair-sin term
        # `sin(yf*0.017 + seed)` is constant along each row (yf is row-constant),
        # so compute it once as a (H,1) column and broadcast — bit-identical to
        # the full-grid evaluation, but one fewer full-resolution sin.
        _hair_row = np.sin(yf[:, :1] * 0.017 + seed) * 0.9
        hair = np.clip(
            1.0 - np.abs(np.sin(xf * 0.77 + yf * 0.41 + _hair_row)) / 0.055,
            0,
            1,
        ).astype(np.float32)
        return hash_a - 0.5, glitter, hair, pin

    def spec_fn(shape, mask, seed, sm):
        h, w = shape[:2]  # tolerate (h,w) or (h,w,3) — caller may pass a 3-tuple
        # Compute material structure at <=512 then upscale; the hidden spec
        # detail is dense enough to survive car scale without the slow wrapper.
        sh, sw, ds = _depth_work_shape(shape)
        pv = _cached_depth_pattern(sh, sw, seed)
        edge = _depth_edge(pv)
        fine, grain, fleck, pin, motif, polish = _hidden_depth_fields((sh, sw), pv, seed)

        M = (
            float(base_m)
            + pv * 42.0 * sm
            - (1.0 - pv) * 24.0 * sm
            + edge * 48.0 * sm
            + motif * 20.0 * sm
            + fleck * 22.0 * sm
            + pin * 34.0 * sm
            + (fine - 0.5) * 20.0 * sm
        )
        G = (
            float(base_g)
            + (1.0 - pv) * 48.0 * sm
            - pv * 18.0 * sm
            - edge * 20.0 * sm
            - motif * 12.0 * sm
            + (1.0 - grain) * 12.0 * sm
            + fleck * 5.0 * sm
        )
        CC = (
            pv * float(cc_deep)
            + (1.0 - pv) * float(cc_shallow)
            + edge * 22.0 * sm
            + motif * 30.0 * sm
            + pin * 12.0 * sm
            + (polish - 0.5) * 18.0 * sm
        )
        M = np.clip(M, 0, 255)
        G = np.clip(G, 0, 255)
        CC = np.clip(CC, 16, 255)
        mask_s = cv2.resize(mask.astype(np.float32), (sw, sh), interpolation=cv2.INTER_LINEAR) if (sw, sh) != (w, h) else mask
        spec_small = _spec_out((sh, sw), mask_s, M, G, CC)
        if (sh, sw) != (h, w):
            spec = np.zeros((h, w, 4), dtype=np.uint8)
            for ch in range(4):
                spec[:, :, ch] = cv2.resize(spec_small[:, :, ch].astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.uint8)
        else:
            spec = spec_small
        pix, glitter, hair, pin_hi = _fullres_depth_micro((h, w), seed + seed_offset + 31)
        active = (mask > 0.01).astype(np.float32)
        spec_f = spec.astype(np.float32, copy=True)
        spec_f[:, :, 0] += (pix * 10.0 + glitter * 18.0 + hair * 5.0 + pin_hi * 24.0) * sm * active
        spec_f[:, :, 1] += ((0.5 - pix) * 7.0 - glitter * 7.0 - hair * 3.0 + pin_hi * 4.0) * sm * active
        spec_f[:, :, 2] += (glitter * 10.0 + hair * 8.0 + pin_hi * 18.0) * sm * active
        spec_f[:, :, 0] = np.clip(spec_f[:, :, 0], 0, 255)
        spec_f[:, :, 1] = np.where(active > 0.01, np.clip(spec_f[:, :, 1], 15, 255), 0)
        spec_f[:, :, 2] = np.where(active > 0.01, np.clip(spec_f[:, :, 2], 16, 255), 0)
        spec_f[:, :, 3] = spec[:, :, 3]
        return spec_f.astype(np.uint8)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        """Depth Illusion: COLORSHOXX-style color zones married to depth pattern.
        UPGRADED: Was brightness-only. Now:
        - Raised zones (pv>0.6): warm color push (amber/gold tint) + brightening
        - Deep zones (pv<0.3): cool shadow push (blue-grey desaturation) + darkening
        - Edges: bright warm-white rim highlight
        Same pv field drives both paint AND spec = married pair."""
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape
        sh, sw, ds = _depth_work_shape(shape)
        pv_s = _cached_depth_pattern(sh, sw, seed)
        pv = cv2.resize(pv_s, (w, h), interpolation=cv2.INTER_LINEAR) if ds > 1 else pv_s
        fine_s, grain_s, fleck_s, _pin_s, _motif_s, polish_s = _hidden_depth_fields((sh, sw), pv_s, seed + 19)
        if ds > 1:
            fine = cv2.resize(fine_s, (w, h), interpolation=cv2.INTER_LINEAR)
            grain = cv2.resize(grain_s, (w, h), interpolation=cv2.INTER_LINEAR)
            fleck = cv2.resize(fleck_s, (w, h), interpolation=cv2.INTER_LINEAR)
            polish = cv2.resize(polish_s, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            fine, grain, fleck, polish = fine_s, grain_s, fleck_s, polish_s
        result = paint.copy()

        # Raised zones: warm tint (amber push) + brightening
        raised = np.clip((pv - 0.4) * 2.5, 0, 1).astype(np.float32)
        warm_blend = raised * 0.22 * pm
        result[:,:,0] = np.clip(result[:,:,0] + warm_blend * mask * 0.12, 0, 1)   # warm red push
        result[:,:,1] = np.clip(result[:,:,1] + warm_blend * mask * 0.06, 0, 1)   # slight gold
        result[:,:,2] = np.clip(result[:,:,2] - warm_blend * mask * 0.04, 0, 1)   # reduce blue = warmer
        bright = raised * 0.18 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + bright * mask, 0, 1)

        # Deep zones: cool desaturation + darkening
        deep = np.clip((0.3 - pv) * 3.0, 0, 1).astype(np.float32)
        gray = (result[:,:,0] * 0.299 + result[:,:,1] * 0.587 + result[:,:,2] * 0.114)
        cool_desat = deep * 0.20 * pm
        result[:,:,0] = np.clip(result[:,:,0] * (1 - cool_desat * mask) + gray * cool_desat * mask - deep * 0.06 * pm * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] * (1 - cool_desat * mask) + gray * cool_desat * mask - deep * 0.04 * pm * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] * (1 - cool_desat * mask * 0.7) + gray * cool_desat * mask * 0.7 + deep * 0.03 * pm * mask, 0, 1)  # retain blue in shadows

        # Sobel edge: bright warm-white rim highlight
        pv_dx = np.abs(np.diff(pv, axis=1, prepend=pv[:, :1]))
        pv_dy = np.abs(np.diff(pv, axis=0, prepend=pv[:1, :]))
        edge = np.clip(np.sqrt(pv_dx**2 + pv_dy**2) * 8, 0, 1)
        rim = edge * 0.22 * pm
        result[:,:,0] = np.clip(result[:,:,0] + rim * mask * 1.05, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + rim * mask * 1.00, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + rim * mask * 0.85, 0, 1)

        pix, glitter, hair, pin_hi = _fullres_depth_micro((h, w), seed + seed_offset + 47)
        micro_boost = {
            "bubble": 1.35,
            "crack": 2.15,
            "ripple": 1.30,
            "vortex": 1.35,
            "wave": 2.25,
        }.get(pattern_type, 1.0)
        micro_lift = (
            (fine - 0.5) * 0.032
            + (polish - 0.5) * 0.018
            + fleck * 0.020
            + pix * 0.018
            + glitter * 0.026
            + hair * 0.012
            + pin_hi * 0.024
        ) * micro_boost * pm * mask
        result[:,:,0] = np.clip(result[:,:,0] + micro_lift * 0.95, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + micro_lift * (0.74 + grain * 0.18), 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + micro_lift * (0.62 + (1.0 - grain) * 0.30), 0, 1)

        result = np.clip(result + bb * 0.25 * mask[:,:,np.newaxis], 0, 1)
        return result
    return spec_fn, paint_fn

spec_depth_canyon, paint_depth_canyon = _make_depth_fusion(200, 35, 16, 140, "canyon", 7900)
spec_depth_bubble, paint_depth_bubble = _make_depth_fusion(220, 30, 16, 100, "bubble", 7910)
spec_depth_ripple, paint_depth_ripple = _make_depth_fusion(200, 40, 16, 120, "ripple", 7920)
spec_depth_scale, paint_depth_scale = _make_depth_fusion(210, 35, 16, 130, "scale", 7930)
spec_depth_honeycomb, paint_depth_honeycomb = _make_depth_fusion(220, 30, 16, 110, "honeycomb", 7940)
spec_depth_crack, paint_depth_crack = _make_depth_fusion(200, 35, 16, 150, "crack", 7950)
spec_depth_wave, paint_depth_wave = _make_depth_fusion(200, 40, 16, 100, "wave", 7960)
spec_depth_pillow, paint_depth_pillow = _make_depth_fusion(210, 35, 16, 90, "pillow", 7970)
spec_depth_vortex, paint_depth_vortex = _make_depth_fusion(220, 30, 16, 140, "vortex", 7980)
spec_depth_erosion, paint_depth_erosion = _make_depth_fusion(190, 40, 16, 160, "erosion", 7990)
spec_depth_map, paint_depth_map = _make_depth_fusion(205, 38, 16, 155, "map", 8000)


# ================================================================
# PARADIGM 11: METALLIC HALO EFFECT - Glowing material outlines
# ================================================================

def _halo_voronoi_dist(shape, n_pts, seed_off):
    """Voronoi nearest/second-nearest distance fields for halo edge detection."""
    h, w = shape
    rng = np.random.RandomState(seed_off)
    pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    d1 = np.full((h, w), 1e9, dtype=np.float32)
    d2 = np.full((h, w), 1e9, dtype=np.float32)
    for py, px in zip(pts_y, pts_x):
        d = np.sqrt((yf - py)**2 + (xf - px)**2)
        upd = d < d1
        d2 = np.where(upd, d1, np.where(d < d2, d, d2))
        d1 = np.minimum(d1, d)
    return d1, d2

def _make_halo_fusion(center_m, halo_m, base_g, base_cc, pattern_type, seed_offset=0):
    """Factory: detailed metallic halos around distinct pattern motifs.

    SPB-67: this category used to share one broad halo response with low
    roughness/clearcoat range and several expensive full-resolution fields. The
    rebuilt path keeps the halo concept, but each pattern gets its own motif
    rhythm and a richer paint/spec material response.
    """
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_halo_fusion(center_m, halo_m, base_g, base_cc, pattern_type, seed_offset))

    style = {
        "hex": {
            "shadow": (0.11, 0.15, 0.20),
            "glow": (0.74, 0.87, 0.94),
            "hot": (0.95, 0.98, 0.98),
            "grain": 1.05,
            "edge": 1.00,
            "cc": 1.05,
        },
        "scale": {
            "shadow": (0.18, 0.12, 0.05),
            "glow": (0.96, 0.70, 0.16),
            "hot": (1.00, 0.90, 0.36),
            "grain": 1.18,
            "edge": 1.05,
            "cc": 0.92,
        },
        "circle": {
            "shadow": (0.16, 0.20, 0.27),
            "glow": (0.78, 0.88, 0.98),
            "hot": (1.00, 0.84, 0.98),
            "grain": 0.92,
            "edge": 0.82,
            "cc": 1.28,
        },
        "diamond": {
            "shadow": (0.15, 0.17, 0.20),
            "glow": (0.78, 0.86, 0.92),
            "hot": (1.00, 0.96, 0.86),
            "grain": 1.10,
            "edge": 1.10,
            "cc": 1.00,
        },
        "voronoi": {
            "shadow": (0.16, 0.15, 0.13),
            "glow": (0.92, 0.70, 0.46),
            "hot": (0.98, 0.86, 0.62),
            "grain": 1.28,
            "edge": 1.16,
            "cc": 0.96,
        },
        "wave": {
            "shadow": (0.06, 0.16, 0.28),
            "glow": (0.96, 0.23, 0.34),
            "hot": (1.00, 0.62, 0.88),
            "grain": 1.20,
            "edge": 0.92,
            "cc": 1.22,
        },
        "crack": {
            "shadow": (0.04, 0.05, 0.06),
            "glow": (0.82, 0.86, 0.84),
            "hot": (1.00, 0.92, 0.76),
            "grain": 1.12,
            "edge": 1.18,
            "cc": 0.88,
        },
        "star": {
            "shadow": (0.09, 0.10, 0.15),
            "glow": (0.96, 0.72, 0.28),
            "hot": (1.00, 0.92, 0.62),
            "grain": 1.44,
            "edge": 1.30,
            "cc": 1.06,
        },
        "grid": {
            "shadow": (0.18, 0.22, 0.28),
            "glow": (0.74, 0.86, 0.98),
            "hot": (0.98, 0.94, 1.00),
            "grain": 0.98,
            "edge": 0.94,
            "cc": 1.26,
        },
        "ripple_ring": {
            "shadow": (0.10, 0.18, 0.25),
            "glow": (0.78, 0.90, 0.96),
            "hot": (0.96, 0.98, 1.00),
            "grain": 1.06,
            "edge": 0.96,
            "cc": 1.20,
        },
    }.get(pattern_type, {
        "shadow": (0.14, 0.16, 0.20),
        "glow": (0.84, 0.84, 0.84),
        "hot": (1.00, 0.94, 0.82),
        "grain": 1.00,
        "edge": 1.00,
        "cc": 1.00,
    })

    def _norm_field(arr):
        arr = np.asarray(arr, dtype=np.float32)
        span = float(arr.max() - arr.min()) if arr.size else 0.0
        if span < 1e-6:
            return np.zeros_like(arr, dtype=np.float32)
        return ((arr - float(arr.min())) / span).astype(np.float32)

    def _hash_grain(shape, seed):
        y, x = _mgrid(shape)
        raw = np.sin(x.astype(np.float32) * 12.9898 + y.astype(np.float32) * 78.233 + (seed + seed_offset) * 0.013) * 43758.5453
        return (raw - np.floor(raw)).astype(np.float32)

    @lru_cache(maxsize=32)
    def _halo_fields_cached(pattern_key, h, w, seed):
        shape = (h, w)
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)
        diag = (xf + yf) / max(1.0, float(h + w))
        fine = _norm_field(_noise(shape, [1, 2, 3, 5], [0.34, 0.30, 0.22, 0.14], seed + seed_offset + 51))
        satin = _norm_field(_noise(shape, [3, 6, 12], [0.38, 0.36, 0.26], seed + seed_offset + 53))
        warp = _noise(shape, [9, 18, 36], [0.34, 0.38, 0.28], seed + seed_offset + 57)

        if pattern_key == "hex":
            sz = max(11, min(h, w) // 38)
            dist = _hex_cell_dist(shape, sz)
            trace = np.clip(1.0 - np.abs(np.sin((xf + yf * 0.42) * 0.105 + warp * 0.55)) * 4.8, 0, 1)
            core = np.clip(1.0 - dist * 1.95, 0, 1)
        elif pattern_key == "scale":
            sz = max(12, min(h, w) // 36)
            row = np.floor(yf / (sz * 0.62)).astype(np.int32)
            cx = (np.floor((xf + (row % 2) * sz * 0.5) / sz) * sz) - (row % 2) * sz * 0.5 + sz * 0.5
            cy = row.astype(np.float32) * sz * 0.62 + sz * 0.42
            dx = (xf - cx) / (sz * 0.56)
            dy = (yf - cy) / (sz * 0.48)
            shell = np.sqrt(dx * dx + dy * dy)
            dist = np.clip(np.abs(shell - 0.88) * 1.85, 0, 1)
            trace = np.clip(1.0 - np.abs(dy + 0.08 * np.sin(dx * 6.0)) * 5.0, 0, 1) * np.clip(1.0 - shell * 0.62, 0, 1)
            core = np.clip(1.0 - shell, 0, 1)
        elif pattern_key == "circle":
            sz = max(13, min(h, w) // 32)
            cell_y = np.floor(yf / sz)
            cell_x = np.floor(xf / sz)
            jitter_y = np.sin(cell_x * 2.31 + cell_y * 1.17 + seed * 0.021) * sz * 0.16
            jitter_x = np.cos(cell_x * 1.77 - cell_y * 2.04 + seed * 0.019) * sz * 0.16
            cy = cell_y * sz + sz * 0.5 + jitter_y
            cx = cell_x * sz + sz * 0.5 + jitter_x
            d = np.sqrt((yf - cy) ** 2 + (xf - cx) ** 2) / (sz * 0.42)
            dist = np.clip(d, 0, 1)
            trace = np.exp(-((d - 0.42) ** 2) / 0.012).astype(np.float32)
            core = np.clip(1.0 - d * 1.25, 0, 1)
        elif pattern_key == "diamond":
            sz = max(10, min(h, w) // 42)
            dx = np.abs(((xf + warp * 4.0) % sz) - sz / 2) / (sz / 2)
            dy = np.abs(((yf - warp * 3.0) % sz) - sz / 2) / (sz / 2)
            d = (dx + dy) * 0.5
            dist = np.clip(d, 0, 1)
            trace = np.clip(1.0 - np.abs(dx - dy) * 3.6, 0, 1)
            core = np.clip(1.0 - d * 1.45, 0, 1)
        elif pattern_key == "voronoi":
            cell_a = np.sin(xf * 0.155 + warp * 2.15) + np.sin(yf * 0.137 - warp * 1.45)
            cell_b = np.sin((xf + yf) * 0.096 + satin * 2.4) + np.sin((xf - yf) * 0.182 - fine * 1.7)
            cellular = cell_a * 0.54 + cell_b * 0.46
            edge = np.abs(cellular)
            dist = np.clip(edge * 0.72, 0, 1)
            vein = np.clip(1.0 - np.abs(np.sin((xf * 0.245 - yf * 0.171) + warp * 2.1)) * 5.8, 0, 1)
            trace = np.clip(1.0 - edge * 1.55, 0, 1) * (0.46 + 0.54 * satin)
            trace = np.clip(trace + vein * 0.34 * np.clip((fine - 0.32) * 1.9, 0, 1), 0, 1)
            core = np.clip((cellular + 1.8) / 3.6 * 0.72 + satin * 0.28, 0, 1)
        elif pattern_key == "wave":
            f1 = np.sin((yf + warp * 7.5) * 0.092 + xf * 0.034)
            f2 = np.sin((yf - warp * 4.2) * 0.051 - xf * 0.073 + 1.9)
            carrier = f1 * 0.62 + f2 * 0.38
            dist = np.clip(np.abs(carrier) * 1.10, 0, 1)
            trace = np.clip(1.0 - np.abs(np.sin((xf - yf * 0.35) * 0.115 + warp)) * 4.6, 0, 1)
            core = np.clip((carrier + 1.0) * 0.5, 0, 1)
        elif pattern_key == "crack":
            f1 = np.sin((xf + warp * 6.0) * 0.085 + yf * 0.043)
            f2 = np.sin((xf - warp * 3.5) * -0.056 + yf * 0.108 + np.sin(xf * 0.014) * 1.4)
            f3 = np.sin((xf + yf) * 0.047 + np.sin(yf * 0.026) * 2.2)
            dist = np.clip(np.minimum(np.minimum(np.abs(f1), np.abs(f2)), np.abs(f3) * 0.70) * 3.05, 0, 1)
            trace = np.clip(1.0 - dist * 2.8, 0, 1)
            core = np.clip((satin * 0.7 + fine * 0.3) * trace, 0, 1)
        elif pattern_key == "star":
            sz = max(12, min(h, w) // 34)
            cell_y = np.floor(yf / sz)
            cell_x = np.floor(xf / sz)
            cx = cell_x * sz + sz * (0.50 + 0.18 * np.sin(cell_y * 1.7 + seed * 0.017))
            cy = cell_y * sz + sz * (0.50 + 0.18 * np.cos(cell_x * 1.3 - seed * 0.011))
            dx = xf - cx
            dy = yf - cy
            radius = np.sqrt(dx * dx + dy * dy) / (sz * 0.45)
            angle = np.arctan2(dy, dx)
            star = np.abs(np.cos(angle * 5.0)) * 0.50 + np.abs(np.cos(angle * 10.0)) * 0.22 + 0.28
            dist = np.clip(radius / star, 0, 1)
            glint = np.clip(1.0 - np.abs(np.sin((xf + yf * 0.37) * 0.30 + seed * 0.017)) * 5.6, 0, 1)
            trace = np.clip(1.0 - np.abs(np.sin(angle * 5.0)) * 2.0, 0, 1) * np.clip(1.0 - radius * 0.95, 0, 1)
            trace = np.clip(trace + glint * np.clip(1.0 - radius * 1.25, 0, 1) * 0.35, 0, 1)
            core = np.clip(1.0 - radius * 1.4, 0, 1)
        elif pattern_key == "grid":
            sz = max(10, min(h, w) // 44)
            xline = np.abs((xf % sz) - sz / 2) / (sz / 2)
            yline = np.abs((yf % (sz * 1.28)) - sz * 0.64) / (sz * 0.64)
            line = np.minimum(xline, yline)
            dist = np.clip(line * 1.55, 0, 1)
            nodes = np.exp(-(xline * xline + yline * yline) / 0.035).astype(np.float32)
            trace = np.clip(nodes + (1.0 - dist) * 0.42, 0, 1)
            core = np.clip(1.0 - np.maximum(xline, yline), 0, 1)
        elif pattern_key == "ripple_ring":
            y_n = (yf / max(1.0, float(h))) - 0.5
            x_n = (xf / max(1.0, float(w))) - 0.5
            centers = [(-0.28, -0.18), (0.22, -0.24), (-0.08, 0.23), (0.33, 0.18), (-0.36, 0.34)]
            ring = np.zeros(shape, dtype=np.float32)
            for i, (cy, cx) in enumerate(centers):
                d = np.sqrt((y_n - cy) ** 2 + (x_n - cx) ** 2)
                ring += np.sin(d * (52.0 + i * 8.0) + seed * 0.013 + i) * 0.5 + 0.5
            ring = ring / float(len(centers))
            dist = np.clip(np.abs(ring - 0.5) * 2.3, 0, 1)
            trace = np.clip(1.0 - np.abs(np.sin((ring + diag * 0.35) * np.pi * 9.0)) * 3.2, 0, 1)
            core = np.clip(ring, 0, 1)
        else:
            dist = np.clip(1.0 - fine, 0, 1)
            trace = fine
            core = satin

        rim = np.exp(-((dist - 0.34) ** 2) / 0.010).astype(np.float32)
        glow = np.exp(-((dist - 0.52) ** 2) / 0.065).astype(np.float32)
        hair = np.clip(1.0 - dist * 2.55, 0, 1)
        pin = np.clip((fine - 0.74) * 4.6, 0, 1)
        scratches = np.clip(1.0 - np.abs(np.sin((xf * 0.35 + yf * 0.11 + seed * 0.031) + warp * 1.7)) * 6.0, 0, 1)
        scratches *= np.clip((satin - 0.38) * 1.9, 0, 1)
        micro = np.clip(pin * 0.58 + scratches * 0.26 + trace * 0.20, 0, 1).astype(np.float32)
        return (
            dist.astype(np.float32),
            core.astype(np.float32),
            rim.astype(np.float32),
            glow.astype(np.float32),
            hair.astype(np.float32),
            trace.astype(np.float32),
            micro.astype(np.float32),
            satin.astype(np.float32),
        )

    def _work_shape(shape):
        h, w = shape
        ds = max(1, int(np.ceil(min(h, w) / 1024.0)))
        return ds, max(96, h // ds), max(96, w // ds)

    def _resize_field(field, shape):
        h, w = shape
        if field.shape == (h, w):
            return field
        return cv2.resize(field, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)

    def _compute_halo_zones(dist):
        """Compute multi-scale halo zones from distance field.
        Returns (center, inner_halo, outer_glow) each 0-1."""
        center = np.clip(1.0 - dist * 2.15, 0, 1)
        inner = np.exp(-(dist - 0.38) ** 2 / 0.014)
        outer = np.exp(-(dist - 0.58) ** 2 / 0.085) * np.clip(dist - 0.16, 0, 1)
        outer = np.clip(outer + np.exp(-(dist - 0.76) ** 2 / 0.18) * 0.28, 0, 1)
        return center, inner, outer

    def _compute_halo_dist(shape, seed):
        """Compute the actual dist field (0-1) for the given pattern_type."""
        h, w = shape
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)

        if pattern_type == "hex":
            sz = max(20, min(h, w) // 18)
            hex_d = _hex_cell_dist(shape, sz)
            dist = np.clip(hex_d, 0, 1)
        elif pattern_type == "scale":
            sz = max(20, min(h, w) // 20)
            row = yf // sz
            row_i = row.astype(np.int32)
            col = (xf + (row_i % 2).astype(np.float32) * (sz // 2)) // sz
            cy = (row_i.astype(np.float32) + 0.5) * sz
            cx = col.astype(np.int32).astype(np.float32) * sz + (row_i % 2).astype(np.float32) * (sz // 2) + sz // 2
            dist = np.clip(np.sqrt((yf - cy)**2 + (xf - cx)**2) / (sz * 0.55), 0, 1)
        elif pattern_type == "circle":
            rng = np.random.RandomState(seed + seed_offset)
            y_n = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
            x_n = np.linspace(0, 1, w).reshape(1, w).astype(np.float32)
            dist = np.ones((h, w), dtype=np.float32)
            for _ in range(25):
                cy, cx = rng.uniform(0, 1), rng.uniform(0, 1)
                r = rng.uniform(0.03, 0.08)
                d = np.sqrt((y_n - cy)**2 + (x_n - cx)**2) / r
                dist = np.minimum(dist, np.clip(d, 0, 1))
        elif pattern_type == "diamond":
            sz = max(16, min(h, w) // 25)
            dx = np.abs((xf % sz) - sz / 2) / (sz / 2)
            dy = np.abs((yf % sz) - sz / 2) / (sz / 2)
            dist = np.clip((dx + dy) / 1.2, 0, 1)
        elif pattern_type == "voronoi":
            d1, d2 = _halo_voronoi_dist(shape, 30, seed + seed_offset)
            edge_w = d2 - d1
            edge_norm = edge_w / (np.percentile(edge_w, 90) + 1e-6)
            dist = np.clip(edge_norm, 0, 1)
        elif pattern_type == "wave":
            warp = _noise(shape, [4, 8, 16, 32], [0.26, 0.30, 0.26, 0.18], seed + seed_offset + 300) * 10
            w1 = np.sin((yf + warp) * 0.052 + xf * 0.026)
            w2 = np.sin((yf - warp * 0.45) * 0.034 - xf * 0.041 + 1.7)
            w3 = np.sin((xf + yf) * 0.020 + warp * 0.035)
            wave = np.clip((w1 * 0.52 + w2 * 0.32 + w3 * 0.16) * 0.5 + 0.5, 0, 1)
            dist = np.clip(np.abs(wave - 0.5) * 2.15, 0, 1)
        elif pattern_type == "crack":
            # FBM iso-line crack network — zero-crossings of two noise fields at different
            # scales form independent crack families that intersect and branch.
            # Structurally distinct from voronoi: no seed points, no cell geometry —
            # pure continuous iso-line topology resembling crackle glaze or dried mud.
            warp = _noise(shape, [8, 16, 32], [0.32, 0.36, 0.32], seed + seed_offset + 100) * 5.0
            f1 = np.sin((xf + warp) * 0.061 + yf * 0.038)
            f2 = np.sin((xf - warp * 0.35) * -0.046 + yf * 0.083 + np.sin(xf * 0.011) * 1.3)
            f3 = np.sin((xf + yf) * 0.035 + np.sin(yf * 0.023) * 2.1)
            branch_gate = np.clip((np.sin(xf * 0.019 - yf * 0.027 + seed * 0.01) + 1.0) * 0.5, 0.18, 1.0)
            dist = np.clip(np.minimum(np.minimum(np.abs(f1), np.abs(f2)), np.abs(f3) * 0.72) * 3.0 / branch_gate, 0, 1)
            return dist
            crack_b = _noise(shape, [5, 10, 20, 40], [0.24, 0.30, 0.28, 0.18],
                             seed + seed_offset + 101)
            crack_a = crack_a * 0.72 + np.sin(xf * 0.067 + yf * 0.041 + crack_a * 2.2) * 0.5
            ca_s = np.percentile(np.abs(crack_a), 95) + 1e-6
            cb_s = np.percentile(np.abs(crack_b), 95) + 1e-6
            iso_a = np.abs(crack_a) / ca_s   # near-0 at zero-crossings of field A
            iso_b = np.abs(crack_b) / cb_s   # near-0 at zero-crossings of field B
            # Primary cracks (coarser A) + secondary cracks (finer B, 0.7× weight)
            iso_min = np.minimum(iso_a, iso_b * 0.7)
            dist = np.clip(iso_min * 3.1, 0, 1)
        elif pattern_type == "star":
            rng2 = np.random.RandomState(seed + seed_offset + 100)
            n_stars = 18
            sy_arr = rng2.uniform(0.05, 0.95, n_stars) * h
            sx_arr = rng2.uniform(0.05, 0.95, n_stars) * w
            dist = np.full((h, w), 1.0, np.float32)
            for sy, sx in zip(sy_arr, sx_arr):
                dy = yf - sy; dx = xf - sx
                r = np.sqrt(dy**2 + dx**2 + 1e-6)
                a = np.arctan2(dy, dx)
                star_sh = np.abs(np.cos(a * 3)) * 0.5 + 0.5
                d = np.clip(r / (min(h, w) * 0.06 * star_sh), 0, 1)
                dist = np.minimum(dist, d)
        elif pattern_type == "grid":
            sz2 = max(18, min(h, w) // 22)
            ymod = np.abs((yf % sz2) - sz2 / 2) / (sz2 / 2)
            xmod = np.abs((xf % sz2) - sz2 / 2) / (sz2 / 2)
            dist = 1.0 - np.clip(np.maximum(ymod, xmod) * 3 - 2, 0, 1)
        elif pattern_type == "ripple_ring":
            rng3 = np.random.RandomState(seed + seed_offset + 100)
            field = np.zeros((h, w), dtype=np.float32)
            for _ in range(4):
                cy2 = rng3.uniform(0.2, 0.8) * h
                cx2 = rng3.uniform(0.2, 0.8) * w
                r2 = np.sqrt((yf - cy2)**2 + (xf - cx2)**2)
                field += np.sin(r2 * rng3.uniform(0.04, 0.08)) * 0.5 + 0.5
            dist = 1.0 - np.clip(field / 4, 0, 1)
        else:
            dist = np.zeros((h, w), dtype=np.float32)
        return dist

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        ds, sh, sw = _work_shape((h, w))
        dist, core, rim, glow, hair, trace, micro, satin = _halo_fields_cached(pattern_type, sh, sw, int(seed))
        chrome = np.clip(rim * (0.85 + 0.15 * style["edge"]) + hair * 0.35 + trace * 0.18, 0, 1)
        valley = np.clip(1.0 - core * 0.70 - rim * 0.35, 0, 1)
        smf = float(sm)
        M_var = np.clip(core * 0.35 + chrome * 0.45 + glow * 0.20, 0.0, 1.0)
        G_var = np.clip(valley * 0.45 + satin * 0.35 + micro * 0.20, 0.0, 1.0)
        B_var = np.clip(glow * 0.40 + rim * 0.30 + core * 0.15 + trace * 0.15, 0.0, 1.0)
        M = 15.0 + 240.0 * np.clip(M_var * smf + (1.0 - smf) * (float(halo_m) / 255.0), 0.0, 1.0)
        G = 15.0 + 240.0 * np.clip(G_var * smf + (1.0 - smf) * (float(base_g) / 255.0), 0.0, 1.0)
        B = 16.0 + 239.0 * np.clip(B_var * smf + (1.0 - smf) * (float(base_cc) / 255.0), 0.0, 1.0)
        mask_s = cv2.resize(mask.astype(np.float32), (sw, sh), interpolation=cv2.INTER_LINEAR) if ds > 1 else mask
        spec_small = _spec_out((sh, sw), mask_s, M, G, B)
        if ds > 1:
            spec = np.zeros((h, w, 4), dtype=np.uint8)
            for ch in range(4):
                spec[:, :, ch] = cv2.resize(spec_small[:, :, ch].astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.uint8)
            return spec
        return spec_small
    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        """Halo patterns: COLORSHOXX-style color zones married to halo dist field.
        Fine halo material structure is tied to the same motif fields as spec."""
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape
        ds, sh, sw = _work_shape((h, w))
        dist_s, core_s, rim_s, glow_s, hair_s, trace_s, micro_s, satin_s = _halo_fields_cached(pattern_type, sh, sw, int(seed))
        dist = _resize_field(dist_s, (h, w)) if ds > 1 else dist_s
        core = _resize_field(core_s, (h, w)) if ds > 1 else core_s
        rim = _resize_field(rim_s, (h, w)) if ds > 1 else rim_s
        glow = _resize_field(glow_s, (h, w)) if ds > 1 else glow_s
        hair = _resize_field(hair_s, (h, w)) if ds > 1 else hair_s
        trace = _resize_field(trace_s, (h, w)) if ds > 1 else trace_s
        micro = _resize_field(micro_s, (h, w)) if ds > 1 else micro_s
        satin = _resize_field(satin_s, (h, w)) if ds > 1 else satin_s
        pin = np.clip((_hash_grain((h, w), seed) - 0.965) * 28.0, 0, 1) * (0.28 + rim * 0.42 + trace * 0.30)
        result = paint.copy()
        shadow = np.asarray(style["shadow"], dtype=np.float32)
        glow_rgb = np.asarray(style["glow"], dtype=np.float32)
        hot_rgb = np.asarray(style["hot"], dtype=np.float32)
        valley = np.clip(dist * 0.72 + (1.0 - satin) * 0.16, 0, 1)
        motif = np.clip(core * 0.34 + glow * 0.28 + rim * 0.52 + hair * 0.20 + trace * 0.16, 0, 1)
        shade = np.clip(0.12 + valley * 0.28, 0, 0.42) * pm * mask
        color_push = np.clip(motif * 0.58 + micro * 0.20 + pin * 0.35, 0, 1) * pm * mask
        hot_edge = np.clip(rim * 0.56 + trace * 0.18 + pin * 0.42, 0, 1) * pm * mask
        for c in range(3):
            result[:, :, c] = np.clip(
                result[:, :, c] * (1.0 - shade)
                + shadow[c] * shade * 0.72
                + glow_rgb[c] * color_push * 0.34
                + hot_rgb[c] * hot_edge * 0.28,
                0,
                1,
            )
        micro_strength = 0.050
        if pattern_type in {"voronoi", "star"}:
            micro_strength = 0.095
        result = np.clip(result + (micro[:, :, np.newaxis] * np.asarray(style["glow"], dtype=np.float32)) * mask[:, :, np.newaxis] * pm * micro_strength, 0, 1)
        if pattern_type in {"voronoi", "star"}:
            etched = np.clip(micro * 0.58 + pin * 0.62 + trace * 0.22, 0, 1) * mask * pm
            for c in range(3):
                result[:, :, c] = np.clip(result[:, :, c] + etched * (hot_rgb[c] - result[:, :, c]) * 0.16, 0, 1)

        result = np.clip(result + bb * 0.25 * mask[:,:,np.newaxis], 0, 1)
        return result
    return spec_fn, paint_fn

spec_halo_hex_chrome, paint_halo_hex_chrome = _make_halo_fusion(20, 240, 30, 16, "hex", 8000)
spec_halo_scale_gold, paint_halo_scale_gold = _make_halo_fusion(30, 250, 35, 16, "scale", 8010)
spec_halo_circle_pearl, paint_halo_circle_pearl = _make_halo_fusion(40, 200, 40, 16, "circle", 8020)
spec_halo_diamond_chrome, paint_halo_diamond_chrome = _make_halo_fusion(15, 255, 25, 16, "diamond", 8030)
spec_halo_voronoi_metal, paint_halo_voronoi_metal = _make_halo_fusion(25, 230, 35, 16, "voronoi", 8040)
spec_halo_wave_candy, paint_halo_wave_candy = _make_halo_fusion(50, 210, 15, 16, "wave", 8050)
spec_halo_crack_chrome, paint_halo_crack_chrome = _make_halo_fusion(20, 245, 30, 16, "crack", 8060)
spec_halo_star_metal, paint_halo_star_metal = _make_halo_fusion(30, 255, 25, 16, "star", 8070)
spec_halo_grid_pearl, paint_halo_grid_pearl = _make_halo_fusion(35, 220, 40, 16, "grid", 8080)
spec_halo_ripple_chrome, paint_halo_ripple_chrome = _make_halo_fusion(20, 240, 30, 16, "ripple_ring", 8090)


# ================================================================
# PARADIGM 12: DYNAMIC ROUGHNESS WAVES - Flowing light bands
# ================================================================

def _make_wave_fusion(base_m, r_min, r_max, wave_type, base_cc, seed_offset=0):
    """Factory: sophisticated wave physics creating flowing light bands in roughness.
    Each wave type uses a different physical model for unique visual character."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_wave_fusion(base_m, r_min, r_max, wave_type, base_cc, seed_offset))

    def _wave_noise(shape, scales, weights, seed):
        return _multiscale_smooth_noise(shape, scales, weights, seed)

    def _compute_wave(shape, yf, xf, seed):
        """Compute wave field 0-1 based on wave_type with domain warping."""
        h, w = shape
        # Domain warp for organic feel. Use interpolated material fields here:
        # the cached global noise path is nearest-neighbor and reads as square
        # cells when these waves are used directly in paint/spec maps.
        warp1 = _wave_noise(shape, [18, 36, 72], [0.32, 0.40, 0.28], seed + seed_offset + 800)
        warp2 = _wave_noise(shape, [20, 40, 80], [0.30, 0.42, 0.28], seed + seed_offset + 801)
        warp_str = min(h, w) * 0.08
        yw = yf + warp1 * warp_str
        xw = xf + warp2 * warp_str

        if wave_type == "low":
            # Gerstner wave model: ocean swell with sharp crests, flat troughs
            freq = 0.012
            steep = 0.6
            phase1 = yw * freq + xw * freq * 0.5
            phase2 = yw * freq * 0.7 - xw * freq * 0.3
            g1 = np.sin(phase1 - steep * np.sin(phase1))
            g2 = np.sin(phase2 - steep * np.sin(phase2)) * 0.6
            wave = np.clip((g1 + g2) * 0.35 + 0.5, 0, 1)

        elif wave_type == "medium":
            # Ripple interference from 4 random point sources
            rng = np.random.RandomState(seed + seed_offset + 200)
            wave = np.zeros((h, w), dtype=np.float32)
            for i in range(4):
                cy = rng.uniform(0.15, 0.85) * h
                cx = rng.uniform(0.15, 0.85) * w
                freq = rng.uniform(0.05, 0.09)
                phase = rng.uniform(0, 2 * np.pi)
                dist = np.sqrt((yw - cy)**2 + (xw - cx)**2)
                amp = 1.0 / (1.0 + dist * 0.005)
                wave += np.sin(dist * freq + phase) * amp
            wave = np.clip(wave / 4.0 * 0.5 + 0.5, 0, 1)

        elif wave_type == "high":
            # Capillary wave turbulence: high-freq noise modulated by large-scale envelope
            envelope = _wave_noise(shape, [9, 18], [0.54, 0.46], seed + seed_offset + 300)
            envelope = np.clip(envelope * 0.5 + 0.7, 0.2, 1.0)
            cap1 = np.sin(yw * 0.12 + xw * 0.06) * 0.3
            cap2 = np.sin(yw * 0.08 - xw * 0.10) * 0.25
            cap3 = np.sin(yw * 0.15 + xw * 0.13) * 0.2
            fine = _wave_noise(shape, [2, 4, 8], [0.34, 0.38, 0.28], seed + seed_offset + 301) * 0.15
            wave = np.clip((cap1 + cap2 + cap3 + fine) * envelope + 0.5, 0, 1)

        elif wave_type == "dual":
            # Dual-frequency beat pattern: visible amplitude modulation
            f1, f2 = 0.030, 0.033
            wave1 = np.sin(yw * f1 * 2 * np.pi + xw * f1 * np.pi)
            wave2 = np.sin(yw * f2 * 2 * np.pi + xw * f2 * np.pi)
            combined = wave1 + wave2
            beat_envelope = np.abs(np.cos((f2 - f1) * np.pi * yw))
            wave = np.clip(combined * 0.25 * beat_envelope + 0.5, 0, 1)

        elif wave_type == "diagonal":
            # Kelvin wake pattern: V-shaped boat wake
            kelvin_angle = 0.3398  # 19.47 degrees
            cy_src, cx_src = h * 0.15, w * 0.5
            dy = yw - cy_src
            dx = xw - cx_src
            r = np.sqrt(dy**2 + dx**2 + 1e-6)
            theta = np.arctan2(np.abs(dx), dy + 1e-6)
            in_wake = (theta < kelvin_angle * 1.5).astype(np.float32)
            transverse = np.sin(dy * 0.04) * 0.5 + 0.5
            divergent = np.sin(r * 0.06 - theta * 8) * 0.5 + 0.5
            center_weight = np.clip(1.0 - theta / kelvin_angle, 0, 1)
            wave = (transverse * center_weight + divergent * (1 - center_weight)) * in_wake
            decay = np.clip(1.0 - r / (max(h, w) * 1.2), 0.1, 1.0)
            wave = np.clip(wave * decay, 0, 1)

        elif wave_type == "radial":
            # Layered annular current/radar waves. The older Airy-only field
            # over-weighted the center and read as a single blob on a paint
            # panel; these rings keep the radial identity across the canvas.
            cy, cx = h / 2.0, w / 2.0
            dist = np.sqrt((yw - cy)**2 + (xw - cx)**2) + 1e-6
            ring_a = (np.sin(dist * 0.145 + seed_offset * 0.01) * 0.5 + 0.5) ** 1.8
            ring_b = (np.sin(dist * 0.082 + seed * 0.017) * 0.5 + 0.5) ** 1.3
            fade = np.clip(1.05 - dist / (max(h, w) * 0.82), 0.18, 1.0)
            cy2, cx2 = h * 0.35, w * 0.65
            dist2 = np.sqrt((yw - cy2)**2 + (xw - cx2)**2) + 1e-6
            offset_ring = (np.sin(dist2 * 0.105 + 1.2) * 0.5 + 0.5) ** 1.5
            theta = np.arctan2(yw - cy, xw - cx)
            sweep = (np.sin(theta * 5.0 + dist * 0.028 + seed * 0.013) * 0.5 + 0.5) * 0.45
            center_relief = np.clip(dist / (min(h, w) * 0.16), 0.0, 1.0)
            wave = _fusion_norm01((ring_a * 0.42 + ring_b * 0.24) * fade + offset_ring * 0.22 + sweep * 0.12)
            wave = np.clip(wave * (0.72 + center_relief * 0.28), 0, 1)

        elif wave_type == "chaotic":
            # Lorenz attractor-mapped roughness: chaotic but deterministic
            n_steps = 5000
            dt = 0.005
            sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
            lx, ly, lz = 1.0, 1.0, 1.0
            traj_x, traj_z = [], []
            for _ in range(n_steps):
                dlx = sigma * (ly - lx) * dt
                dly = (lx * (rho - lz) - ly) * dt
                dlz = (lx * ly - beta * lz) * dt
                lx += dlx; ly += dly; lz += dlz
                traj_x.append(lx); traj_z.append(lz)
            traj_x = np.array(traj_x, dtype=np.float32)
            traj_z = np.array(traj_z, dtype=np.float32)
            tx_norm = (traj_x - traj_x.min()) / (traj_x.max() - traj_x.min() + 1e-6)
            tz_norm = (traj_z - traj_z.min()) / (traj_z.max() - traj_z.min() + 1e-6)
            canvas = np.zeros((h, w), dtype=np.float32)
            for i in range(len(traj_x)):
                py = int(np.clip(tx_norm[i] * (h - 1), 0, h - 1))
                px = int(np.clip(tz_norm[i] * (w - 1), 0, w - 1))
                canvas[max(0,py-1):min(h,py+2), max(0,px-1):min(w,px+2)] += 0.15
            wave = cv2.GaussianBlur(np.clip(canvas, 0, 1).astype(np.float32), (11, 11), 5.0)
            wave = np.clip(wave, 0, 1)

        elif wave_type == "standing":
            # True 2D standing wave from 4 corner reflections + center
            corners = [(0, 0), (0, w), (h, 0), (h, w)]
            wave = np.zeros((h, w), dtype=np.float32)
            for cy_c, cx_c in corners:
                dist = np.sqrt((yw - cy_c)**2 + (xw - cx_c)**2)
                wave += np.sin(dist * 0.04) * 0.25
            dist_center = np.sqrt((yw - h/2)**2 + (xw - w/2)**2)
            wave += np.sin(dist_center * 0.05) * 0.2
            wave = np.clip(wave * wave + 0.2, 0, 1)

        elif wave_type == "moire":
            # True Moire pattern: two grids at 5-degree offset
            angle1, angle2 = 0.0, 0.087
            freq = 0.035
            proj1 = yw * np.cos(angle1) + xw * np.sin(angle1)
            grid1 = np.sin(proj1 * freq * 2 * np.pi) * 0.5 + 0.5
            proj2 = yw * np.cos(angle2) + xw * np.sin(angle2)
            grid2 = np.sin(proj2 * freq * 2 * np.pi) * 0.5 + 0.5
            moire = grid1 * grid2
            proj3 = -yw * np.sin(angle1) + xw * np.cos(angle1)
            proj4 = -yw * np.sin(angle2) + xw * np.cos(angle2)
            grid3 = np.sin(proj3 * freq * 2 * np.pi) * 0.5 + 0.5
            grid4 = np.sin(proj4 * freq * 2 * np.pi) * 0.5 + 0.5
            moire2 = grid3 * grid4
            wave = np.clip(moire * 0.6 + moire2 * 0.4, 0, 1)
        else:
            wave = np.ones((h, w), dtype=np.float32) * 0.5

        capillary = (
            np.sin(yw * 0.31 + xw * 0.17 + (seed_offset % 31)) * 0.5
            + np.sin(yw * -0.19 + xw * 0.27 + (seed % 17)) * 0.35
            + np.sin((yw + xw) * 0.11 + (seed_offset % 23)) * 0.15
        )
        capillary = np.clip(capillary * 0.5 + 0.5, 0, 1)
        grain = np.clip(_wave_noise(shape, [1, 2, 4], [0.44, 0.34, 0.22], seed + seed_offset + 930) * 0.5 + 0.5, 0, 1)
        crest = np.clip(1.0 - np.abs(wave - 0.5) * 1.8, 0, 1)
        wave = np.clip(wave * 0.84 + capillary * crest * 0.10 + grain * crest * 0.06, 0, 1)
        return wave.astype(np.float32)

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)
        wave = _compute_wave(shape, yf, xf, seed)
        # R spans full 2-200 range for dramatic light band effect
        G = r_min + wave * (r_max - r_min) * sm
        # M tracks wave peaks: high M at crests = bright reflections
        M = np.clip(float(base_m) + (wave - 0.3) * 60 * sm, 0, 255)
        n = _wave_noise(shape, [18, 36], [0.54, 0.46], seed + seed_offset + 50)
        M = M + n * 12 * sm
        # CC tracks wave inversely: smooth crests vs hazed troughs
        B = np.clip(float(base_cc) + (1 - wave) * 35 * sm, 16, 255)
        # Fine-scale texture riding the waves (more in troughs)
        n_fine = _wave_noise(shape, [2, 4, 8], [0.34, 0.38, 0.28], seed + seed_offset + 150)
        G = G + n_fine * 15 * sm * (1 - wave)
        # Wave crest highlight via gradient energy
        wave_dx = np.abs(np.diff(wave, axis=1, prepend=wave[:, :1]))
        wave_dy = np.abs(np.diff(wave, axis=0, prepend=wave[:1, :]))
        edge_energy = np.clip((wave_dx + wave_dy) * 8, 0, 1)
        M = np.clip(M + edge_energy * 30 * sm, 0, 255)
        G = np.clip(G - edge_energy * 20 * sm, 0, 255)
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        """Wave patterns: COLORSHOXX-style color zones married to wave field.
        UPGRADED: Was brightness/shimmer-only. Now creates real color zones:
        - Wave crests (high pv): warm color push (amber/gold tint) + brightening
        - Wave troughs (low pv): cool shadow push (desaturate toward grey, darken, retain blue)
        - Edges (Sobel): bright warm-white rim highlight"""
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)
        wave = _compute_wave(shape, yf, xf, seed)
        wave_vis = _fusion_norm01(wave)
        result = paint.copy()

        # --- High-pv zones (crests): warm color push + brightening ---
        crest = np.clip((wave_vis - 0.38) * 2.8, 0, 1).astype(np.float32)
        warm_blend = crest * 0.28 * pm
        result[:,:,0] = np.clip(result[:,:,0] + warm_blend * mask * 0.12, 0, 1)   # warm red push
        result[:,:,1] = np.clip(result[:,:,1] + warm_blend * mask * 0.08, 0, 1)   # slight gold
        result[:,:,2] = np.clip(result[:,:,2] - warm_blend * mask * 0.05, 0, 1)   # reduce blue = warmer
        bright = crest * 0.22 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + bright * mask, 0, 1)

        # --- Low-pv zones (troughs): cool desaturation + darkening ---
        trough = np.clip((0.36 - wave_vis) * 3.1, 0, 1).astype(np.float32)
        gray = (result[:,:,0] * 0.299 + result[:,:,1] * 0.587 + result[:,:,2] * 0.114)
        cool_desat = trough * 0.24 * pm
        result[:,:,0] = np.clip(result[:,:,0] * (1 - cool_desat * mask) + gray * cool_desat * mask - trough * 0.08 * pm * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] * (1 - cool_desat * mask) + gray * cool_desat * mask - trough * 0.05 * pm * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] * (1 - cool_desat * mask * 0.7) + gray * cool_desat * mask * 0.7 + trough * 0.05 * pm * mask, 0, 1)

        # --- Edges (Sobel): bright warm-white rim highlight ---
        wave_dx = np.abs(np.diff(wave_vis, axis=1, prepend=wave_vis[:, :1]))
        wave_dy = np.abs(np.diff(wave_vis, axis=0, prepend=wave_vis[:1, :]))
        edge = np.clip(np.sqrt(wave_dx**2 + wave_dy**2) * 5.5, 0, 1)
        rim = edge * 0.26 * pm
        result[:,:,0] = np.clip(result[:,:,0] + rim * mask * 1.05, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + rim * mask * 1.00, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + rim * mask * 0.85, 0, 1)

        result = np.clip(result + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return result
    return spec_fn, paint_fn

spec_wave_chrome_tide, paint_wave_chrome_tide = _make_wave_fusion(255, 2, 80, "low", 16, 8100)
spec_wave_candy_flow, paint_wave_candy_flow = _make_wave_fusion(200, 10, 60, "medium", 16, 8110)
spec_wave_pearl_current, paint_wave_pearl_current = _make_wave_fusion(100, 20, 70, "radial", 16, 8120)
spec_wave_metallic_pulse, paint_wave_metallic_pulse = _make_wave_fusion(220, 15, 90, "high", 16, 8130)
spec_wave_dual_frequency, paint_wave_dual_frequency = _make_wave_fusion(200, 5, 100, "dual", 16, 8140)
spec_wave_diagonal_sweep, paint_wave_diagonal_sweep = _make_wave_fusion(240, 5, 60, "diagonal", 16, 8150)
spec_wave_circular_radar, paint_wave_circular_radar = _make_wave_fusion(230, 3, 80, "radial", 16, 8160)
spec_wave_turbulent_flow, paint_wave_turbulent_flow = _make_wave_fusion(210, 10, 100, "chaotic", 16, 8170)
spec_wave_standing_chrome, paint_wave_standing_chrome = _make_wave_fusion(250, 2, 50, "standing", 16, 8180)
spec_wave_moire_metal, paint_wave_moire_metal = _make_wave_fusion(200, 8, 70, "moire", 16, 8190)


def _lw_xy(shape):
    h, w = shape
    y = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    x = np.linspace(0.0, 1.0, w, dtype=np.float32).reshape(1, w)
    return x, y


def _lw_hash(shape, seed, salt):
    x, y = _lw_xy(shape)
    n = np.sin((x * 127.1 + y * 311.7 + (int(seed) + salt) * 0.013) * 43758.5453)
    return (n - np.floor(n)).astype(np.float32)


def _lw_ridge(v, width):
    return np.clip(1.0 - np.abs(v) * float(width), 0.0, 1.0).astype(np.float32)


def _lw_fields(shape, seed, mode):
    try:
        from engine import overnight_boost as _ob
    except Exception:
        class _ob:  # noqa: N801
            @staticmethod
            def wave_mult(b, k="spec"):
                return b
    x, y = _lw_xy(shape)
    phase = (int(seed) % 8192) * 0.000767 * np.pi * 2.0
    tw = np.float32(np.pi * 2.0)

    if mode == "chrome_tide":
        f = np.sin((y * 5.2 + np.sin(x * tw * 2.4 + phase) * 0.22) * tw + phase)
        f += 0.42 * np.sin((y * 10.5 - x * 2.1) * tw + phase * 0.7)
        aux = np.sin((x * 17.0 + y * 4.0) * tw + phase * 1.8)
    elif mode == "candy_flow":
        f = np.sin((x * 4.8 + np.sin(y * tw * 3.0 + phase) * 0.30) * tw + y * 5.0)
        f += 0.36 * np.sin((x * 13.0 - y * 6.0) * tw + phase)
        aux = np.sin((x + y * 0.55) * tw * 20.0 + phase * 2.0)
    elif mode == "pearl_current":
        d1 = np.sqrt((x - 0.28) ** 2 + (y - 0.34) ** 2)
        d2 = np.sqrt((x - 0.76) ** 2 + (y - 0.62) ** 2)
        f = np.sin(d1 * tw * 15.0 + phase) + 0.72 * np.sin(d2 * tw * 18.0 - phase * 0.6)
        aux = np.sin(np.arctan2(y - 0.50, x - 0.52) * 7.0 + (d1 + d2) * tw * 10.0)
    elif mode == "metallic_pulse":
        carrier = np.sin((x * 24.0 + np.sin(y * tw * 3.0) * 0.55) * tw + phase)
        pulse = np.sin((y * 5.4 + x * 1.2) * tw - phase)
        f = carrier * 0.62 + pulse * 0.48
        aux = np.sin((x * 42.0 - y * 9.0) * tw + phase)
    elif mode == "dual_frequency":
        a = np.sin((x * 9.0 + y * 3.0) * tw + phase)
        b = np.sin((x * 10.35 - y * 2.4) * tw - phase * 0.8)
        f = (a + b) * (0.56 + 0.44 * np.cos((a - b) * 2.0))
        aux = np.sin((x * 21.0 + y * 16.0) * tw + phase)
    elif mode == "diagonal_sweep":
        diag = x * 0.72 + y * 1.18
        f = np.sin(diag * tw * 8.5 + np.sin((x - y) * tw * 3.0) * 0.8 + phase)
        aux = np.sin((x * 28.0 - y * 18.0) * tw + phase * 0.5)
    elif mode == "circular_radar":
        cx, cy = 0.50, 0.48
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        theta = np.arctan2(y - cy, x - cx)
        f = np.sin(d * tw * 22.0 + phase) * 0.82 + np.sin(theta * 7.0 + d * tw * 8.0) * 0.35
        aux = np.cos(theta * 18.0 - phase) * np.clip(1.18 - d * 1.25, 0.0, 1.0)
    elif mode == "turbulent_flow":
        warp = np.sin((x * 3.2 + y * 2.4) * tw + phase) * 0.16
        curl = np.sin((x + warp) * tw * 7.4 + np.sin(y * tw * 5.2) * 1.2)
        eddy = np.cos((y - warp) * tw * 8.9 + np.sin(x * tw * 4.7) * 1.4)
        f = curl * 0.58 + eddy * 0.52
        aux = np.sin((x * 35.0 + y * 31.0) * tw + phase)
    elif mode == "standing_chrome":
        sx = np.sin(x * tw * 8.0 + phase)
        sy = np.sin(y * tw * 7.0 - phase * 0.6)
        f = sx * sy + 0.32 * np.sin((x + y) * tw * 18.0)
        aux = np.sin((x * 22.0 - y * 22.0) * tw + phase)
    elif mode == "moire_metal":
        a1, a2 = 0.0, 0.108
        p1 = x * np.cos(a1) + y * np.sin(a1)
        p2 = x * np.cos(a2) + y * np.sin(a2)
        q1 = -x * np.sin(a1) + y * np.cos(a1)
        q2 = -x * np.sin(a2) + y * np.cos(a2)
        f = np.sin(p1 * tw * 28.0) * np.sin(p2 * tw * 28.0)
        f += 0.52 * np.sin(q1 * tw * 19.0 + phase) * np.sin(q2 * tw * 19.0 - phase)
        aux = np.sin((p1 + q2) * tw * 34.0 + phase)
    else:
        f = np.sin((x + y) * tw * 8.0 + phase)
        aux = np.sin((x - y) * tw * 16.0)

    field = _fusion_norm01(f)
    edge_x = np.abs(np.diff(field, axis=1, prepend=field[:, :1]))
    edge_y = np.abs(np.diff(field, axis=0, prepend=field[:1, :]))
    edge = np.clip((edge_x + edge_y) * 18.0, 0.0, 1.0)
    crest = np.maximum(_lw_ridge(field - 0.62, 8.2), edge * 0.72)
    micro = _lw_hash(shape, seed, 911 + len(mode)) * 0.54 + (np.sin(aux * 5.0 + phase) * 0.5 + 0.5) * 0.46
    # SPB overnight 2026-05-27 — Light & Optics global boost: finer optical glint lattice
    fine = _lw_hash(shape, seed + 17, 913 + len(mode) * 3)
    fine2 = _lw_hash(shape, seed + 31, 917 + len(mode) * 5)
    sparkle = np.clip((fine - 0.52) * 6.5 + (fine2 - 0.48) * 4.2, 0.0, 1.0)
    micro = np.clip(micro * 0.78 + sparkle * 0.22, 0.0, 1.0)
    glint = np.clip((micro - 0.58) * 4.2 * _ob.wave_mult(1.0, "glint") + crest * 0.72 + sparkle * 0.48 * _ob.wave_mult(1.0, "sparkle"), 0.0, 1.0)
    edge = np.clip(edge + sparkle * 0.35 * _ob.wave_mult(1.0, "glint"), 0.0, 1.0)
    return field.astype(np.float32), crest.astype(np.float32), micro.astype(np.float32), glint.astype(np.float32), edge.astype(np.float32)


def _make_light_wave_fast(mode, cool, warm, accent, base_m, rough_base, clearcoat_base, seed_offset=0):
    cool = np.array(cool, dtype=np.float32)
    warm = np.array(warm, dtype=np.float32)
    accent = np.array(accent, dtype=np.float32)

    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        field, crest, micro, glint, edge = _lw_fields(shape, int(seed) + seed_offset, mode)
        smf = float(sm)
        field_scaled = 0.5 + 0.5 * np.sin(field * np.pi * 3.0)
        M_var = np.clip(field_scaled * 0.32 + crest * 0.38 + glint * 0.30, 0.0, 1.0)
        G_var = np.clip((1.0 - field_scaled) * 0.34 + (1.0 - micro) * 0.28 + (1.0 - glint) * 0.38, 0.0, 1.0)
        B_var = np.clip(crest * 0.26 + glint * 0.48 + edge * 0.26, 0.0, 1.0)
        M = 15.0 + 240.0 * np.clip(M_var * smf + (1.0 - smf) * (base_m / 255.0), 0.0, 1.0)
        G = 15.0 + 240.0 * np.clip(G_var * smf + (1.0 - smf) * (rough_base / 255.0), 0.0, 1.0)
        B = 16.0 + 239.0 * np.clip(B_var * smf + (1.0 - smf) * (clearcoat_base / 255.0), 0.0, 1.0)
        return _spec_out(shape, mask2, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        bb_arr = np.asarray(bb, dtype=np.float32)
        if bb_arr.ndim == 2:
            bb_arr = bb_arr[:, :, np.newaxis]
        if paint.ndim == 3 and paint.shape[2] > 3:
            base = paint[:, :, :3].astype(np.float32, copy=True)
        else:
            base = paint.astype(np.float32, copy=True)
        field, crest, micro, glint, edge = _lw_fields(shape, int(seed) + seed_offset, mode)
        grad = np.clip(field * 0.80 + micro * 0.20, 0.0, 1.0)
        color = cool.reshape(1, 1, 3) * (1.0 - grad[:, :, np.newaxis]) + warm.reshape(1, 1, 3) * grad[:, :, np.newaxis]
        flash = accent.reshape(1, 1, 3) * np.clip(crest * 0.78 + glint * 0.52 + edge * 0.32, 0.0, 1.0)[:, :, np.newaxis]
        target = np.clip(color + flash, 0.0, 1.0)
        blend = np.clip((0.72 + glint * 0.18 + crest * 0.10) * float(pm), 0.0, 0.94)[:, :, np.newaxis] * mask2[:, :, np.newaxis]
        result = base * (1.0 - blend) + target * blend
        result = np.clip(result + bb_arr * 0.24 * mask2[:, :, np.newaxis], 0.0, 1.0)
        return result.astype(np.float32)

    return spec_fn, paint_fn


spec_wave_chrome_tide, paint_wave_chrome_tide = _make_light_wave_fast("chrome_tide", (0.06, 0.18, 0.26), (0.82, 0.92, 0.96), (1.00, 1.00, 0.86), 208, 34, 104, 9100)
spec_wave_candy_flow, paint_wave_candy_flow = _make_light_wave_fast("candy_flow", (0.10, 0.24, 0.76), (1.00, 0.12, 0.34), (1.00, 0.74, 0.22), 184, 42, 86, 9110)
spec_wave_pearl_current, paint_wave_pearl_current = _make_light_wave_fast("pearl_current", (0.55, 0.78, 0.92), (0.95, 0.72, 1.00), (1.00, 0.98, 0.90), 146, 56, 112, 9120)
spec_wave_metallic_pulse, paint_wave_metallic_pulse = _make_light_wave_fast("metallic_pulse", (0.13, 0.19, 0.25), (0.96, 0.56, 0.22), (0.98, 0.94, 0.66), 220, 36, 96, 9130)
spec_wave_dual_frequency, paint_wave_dual_frequency = _make_light_wave_fast("dual_frequency", (0.04, 0.42, 0.90), (1.00, 0.26, 0.10), (0.94, 1.00, 0.38), 196, 38, 98, 9140)
spec_wave_diagonal_sweep, paint_wave_diagonal_sweep = _make_light_wave_fast("diagonal_sweep", (0.10, 0.16, 0.34), (0.94, 0.48, 0.18), (0.98, 0.90, 0.54), 210, 40, 92, 9150)
spec_wave_circular_radar, paint_wave_circular_radar = _make_light_wave_fast("circular_radar", (0.02, 0.22, 0.16), (0.36, 1.00, 0.34), (0.88, 1.00, 0.58), 202, 35, 116, 9160)
spec_wave_turbulent_flow, paint_wave_turbulent_flow = _make_light_wave_fast("turbulent_flow", (0.04, 0.16, 0.30), (0.90, 0.32, 0.14), (1.00, 0.76, 0.30), 198, 44, 94, 9170)
spec_wave_standing_chrome, paint_wave_standing_chrome = _make_light_wave_fast("standing_chrome", (0.22, 0.28, 0.36), (0.88, 0.88, 0.82), (0.66, 0.94, 1.00), 226, 30, 108, 9180)
spec_wave_moire_metal, paint_wave_moire_metal = _make_light_wave_fast("moire_metal", (0.14, 0.16, 0.20), (0.84, 0.78, 0.62), (0.92, 0.96, 1.00), 216, 38, 96, 9190)


# ================================================================
# PARADIGM 13: FRACTAL MATERIAL MIXING - 10 unique self-similar engines
# Each entry uses a fundamentally different fractal/chaos algorithm
# ================================================================

# 1. FRACTAL CHROME DECAY - Mandelbrot set edge detection drives metallic decay
_mandelbrot_cache = {}

def _mandelbrot_field(shape, cx=-0.75, cy=0.0, zoom=1.2, max_iter=80, seed=0):
    """Compute Mandelbrot escape-time field mapped onto shape. Cached."""
    _key = (shape, cx, cy, zoom, max_iter, seed)
    if _key in _mandelbrot_cache:
        return _mandelbrot_cache[_key]
    h, w = shape
    rng = np.random.RandomState(seed)
    cx += rng.uniform(-0.3, 0.3)
    cy += rng.uniform(-0.3, 0.3)
    zoom *= rng.uniform(0.8, 2.5)
    y_lin = np.linspace(cy - 1.5 / zoom, cy + 1.5 / zoom, h).astype(np.float64)
    x_lin = np.linspace(cx - 2.0 / zoom, cx + 2.0 / zoom, w).astype(np.float64)
    xv, yv = np.meshgrid(x_lin, y_lin)
    c = xv + 1j * yv
    z = np.zeros_like(c)
    escape = np.full((h, w), max_iter, dtype=np.float32)
    for i in range(max_iter):
        mask_active = np.abs(z) <= 2.0
        z = np.where(mask_active, z * z + c, z)
        newly_escaped = (np.abs(z) > 2.0) & (escape == max_iter)
        escape[newly_escaped] = i + 1 - np.log2(np.log2(np.abs(z[newly_escaped]).astype(np.float64) + 1e-10)).astype(np.float32)
    result = np.clip(escape / max_iter, 0, 1).astype(np.float32)
    if len(_mandelbrot_cache) > 4:
        _mandelbrot_cache.pop(next(iter(_mandelbrot_cache)))
    _mandelbrot_cache[_key] = result
    return result

def _fractal_surface_grain(shape, seed, scales=(3, 6, 14), weights=(0.55, 0.3, 0.2)):
    """Fine-grain detail texture for fractal-silhouette finishes.

    The fractal generators (Mandelbrot/Julia/Sierpinski/cascade) carve a
    distinctive REGIONAL silhouette across the canvas, but inside each
    region the original generators set spec/paint to flat regional
    constants. At 2048-painter resolution this reads as two giant
    flat-color zones with a fractal boundary — exactly the "broad blob /
    giant cell" complaint from the user's Item 3 brief.

    This helper returns a smooth fine-grain noise field in [0, 1] that
    can be multiplied into the regional spec/paint to add surface
    micro-variation WITHOUT erasing the fractal silhouette identity that
    makes each finish unique.
    """
    return (_multiscale_smooth_noise(shape, list(scales), list(weights), seed) + 1.0) * 0.5


def _spec_fractal_chrome_decay(shape, mask, seed, sm):
    h, w = shape
    # --- Resolution cap: compute fractal at 512 max ---
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    fractal = _mandelbrot_field((sh, sw), seed=seed + 8200)
    # Edge detection: gradient magnitude of fractal field reveals boundary
    gy = np.diff(fractal, axis=0, prepend=fractal[:1, :])
    gx = np.diff(fractal, axis=1, prepend=fractal[:, :1])
    edge = np.clip(np.sqrt(gy**2 + gx**2) * 15, 0, 1)
    # Deep fractal (high iteration) = surviving chrome; low = corroded matte
    chrome = np.power(fractal, 0.7)
    decay_mix = chrome * (1.0 - edge * 0.6)
    # 2026-04-25 — fine-grain surface texture inside the fractal regions to
    # break up flat coverage at painter resolutions (Item 3 broad-blob fix).
    grain = _fractal_surface_grain((sh, sw), seed + 8201)
    M = np.clip((decay_mix * 255 * sm + (1 - decay_mix) * 5) * (0.85 + 0.30 * grain), 0, 255)
    G = np.clip(((1 - decay_mix) * 220 * sm + decay_mix * 2) * (0.85 + 0.30 * (1.0 - grain)), 0, 255)
    CC = np.clip(decay_mix * 16 + (1 - decay_mix) * 200 + edge * 80 + (grain - 0.5) * 24, 16, 255)
    mask_s = cv2.resize(mask.astype(np.float32), (sw, sh), interpolation=cv2.INTER_LINEAR) if ds > 1 else mask
    spec_small = _spec_out((sh, sw), mask_s, M, G, CC)
    if ds > 1:
        spec = np.zeros((h, w, 4), dtype=np.uint8)
        for ch in range(4):
            spec[:,:,ch] = cv2.resize(spec_small[:,:,ch].astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.uint8)
        return spec
    return spec_small

def _paint_fractal_chrome_decay(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    # --- Resolution cap: compute fractal at 512 max ---
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    fractal = _mandelbrot_field((sh, sw), seed=seed + 8200)
    if ds > 1:
        fractal = cv2.resize(fractal, (w, h), interpolation=cv2.INTER_LINEAR)
    corrosion = (1 - fractal)
    chrome = np.power(fractal, 0.7)
    # 2026-04-25 — fine-grain modulation breaks up the flat chrome/decay
    # regions inside the fractal silhouette so painters see actual surface
    # texture at 2048 resolution (Item 3 broad-blob fix).
    grain = _fractal_surface_grain((h, w), seed + 8202)
    grain_centered = (grain - 0.5) * 2.0  # [-1, 1]
    result = paint.copy()
    # Increased coefficients + brightness variation (chrome bright, decay dark),
    # each modulated by grain so the surfaces aren't flat at high resolution.
    bright = chrome * 0.15 * pm * (1.0 + grain_centered * 0.35)
    dark = corrosion * 0.10 * pm * (1.0 + grain_centered * 0.35)
    corr_mod = corrosion * (1.0 + grain_centered * 0.30)
    fract_mod = fractal * (1.0 + grain_centered * 0.20)
    result[:,:,0] = np.clip(paint[:,:,0] + corr_mod * 0.28 * pm * mask + bright * mask - dark * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] - corr_mod * 0.12 * pm * mask + fract_mod * 0.08 * pm * mask + bright * mask - dark * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] - corr_mod * 0.22 * pm * mask + bright * mask - dark * mask, 0, 1)
    return result

spec_fractal_chrome_decay = _spec_fractal_chrome_decay
paint_fractal_chrome_decay = _paint_fractal_chrome_decay

# 2. FRACTAL CANDY CHAOS - Julia set Voronoi hybrid with fractal chrome borders
def _julia_field(shape, seed=0, max_iter=60):
    """Compute Julia set escape-time field with seed-driven c parameter."""
    h, w = shape
    rng = np.random.RandomState(seed)
    c_presets = [(-0.7269, 0.1889), (-0.8, 0.156), (0.285, 0.01),
                 (-0.4, 0.6), (0.355, 0.355), (-0.54, 0.54)]
    ci = c_presets[rng.randint(len(c_presets))]
    c = complex(ci[0] + rng.uniform(-0.05, 0.05), ci[1] + rng.uniform(-0.05, 0.05))
    y_lin = np.linspace(-1.5, 1.5, h).astype(np.float64)
    x_lin = np.linspace(-1.5, 1.5, w).astype(np.float64)
    xv, yv = np.meshgrid(x_lin, y_lin)
    z = xv + 1j * yv
    escape = np.full((h, w), max_iter, dtype=np.float32)
    for i in range(max_iter):
        active = np.abs(z) <= 2.0
        z = np.where(active, z * z + c, z)
        newly_escaped = (np.abs(z) > 2.0) & (escape == max_iter)
        escape[newly_escaped] = float(i)
    return np.clip(escape / max_iter, 0, 1).astype(np.float32)

def _spec_fractal_candy_chaos(shape, mask, seed, sm):
    h, w = shape
    # --- Resolution cap: compute at 512 max ---
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    rng = np.random.RandomState(seed + 8210)
    julia = _julia_field((sh, sw), seed=seed + 8210)
    # Use Julia field as domain warp for Voronoi
    n_pts = 30
    pts_y = rng.uniform(0, sh, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, sw, n_pts).astype(np.float32)
    y_g, x_g = _mgrid((sh, sw))
    warp_strength = julia * 40 * sh / h
    yf = y_g.astype(np.float32) + warp_strength
    xf = x_g.astype(np.float32) + warp_strength * 0.8
    min_d = np.full((sh, sw), 1e9, np.float32)
    min_d2 = np.full((sh, sw), 1e9, np.float32)
    cell_id = np.zeros((sh, sw), dtype=np.int32)
    for idx, (py, px) in enumerate(zip(pts_y, pts_x)):
        d = (yf - py)**2 + (xf - px)**2
        new_min2 = np.where(d < min_d, min_d, np.where(d < min_d2, d, min_d2))
        closer = d < min_d
        cell_id = np.where(closer, idx, cell_id)
        min_d = np.minimum(min_d, d)
        min_d2 = new_min2
    edge = np.clip((np.sqrt(min_d2) - np.sqrt(min_d)) / 6, 0, 1)
    # Per-cell spec variation
    cell_m = rng.uniform(60, 200, n_pts).astype(np.float32)
    cell_r = rng.uniform(10, 180, n_pts).astype(np.float32)
    M_base = cell_m[cell_id]
    R_base = cell_r[cell_id]
    # 2026-04-25 — fine-grain inside Voronoi candy cells so each cell has
    # surface character at painter resolution instead of being a flat blob
    # (Item 3 broad-blob fix, large_blob_ratio was 0.51).
    grain = _fractal_surface_grain((sh, sw), seed + 8211)
    grain_centered = (grain - 0.5) * 2.0  # [-1, 1]
    # Fractal chrome borders at edges; per-cell candy with grain modulation.
    M = np.clip((M_base * (1 - edge) + 255 * edge) * (0.85 + 0.30 * grain), 0, 255) * sm
    G = np.clip((R_base * (1 - edge) + 2 * edge) * (0.85 + 0.30 * (1.0 - grain)), 0, 255)
    CC = np.clip(edge * 16 + (1 - edge) * 120 + grain_centered * 24, 16, 255)
    mask_s = cv2.resize(mask.astype(np.float32), (sw, sh), interpolation=cv2.INTER_LINEAR) if ds > 1 else mask
    spec_small = _spec_out((sh, sw), mask_s, M, G, CC)
    if ds > 1:
        spec = np.zeros((h, w, 4), dtype=np.uint8)
        for ch in range(4):
            spec[:,:,ch] = cv2.resize(spec_small[:,:,ch].astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR).astype(np.uint8)
        return spec
    return spec_small

def _paint_fractal_candy_chaos(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = shape
    # --- Resolution cap: compute Julia+Voronoi at 512 max ---
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    rng = np.random.RandomState(seed + 8210)
    julia = _julia_field((sh, sw), seed=seed + 8210)
    # Rebuild Voronoi cell_id for per-cell candy coloring
    n_pts = 30
    pts_y = rng.uniform(0, sh, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, sw, n_pts).astype(np.float32)
    y_g, x_g = _mgrid((sh, sw))
    warp_strength = julia * 40 * sh / h
    yf = y_g.astype(np.float32) + warp_strength
    xf = x_g.astype(np.float32) + warp_strength * 0.8
    min_d = np.full((sh, sw), 1e9, np.float32)
    cell_id = np.zeros((sh, sw), dtype=np.int32)
    for idx, (py, px) in enumerate(zip(pts_y, pts_x)):
        d = (yf - py)**2 + (xf - px)**2
        closer = d < min_d
        cell_id = np.where(closer, idx, cell_id)
        min_d = np.minimum(min_d, d)
    # Assign unique candy hue per cell using golden ratio spacing
    cell_hues = np.array([(i * 0.618033988749895) % 1.0 for i in range(n_pts)], dtype=np.float32)
    pixel_hue = cell_hues[cell_id]
    # Upscale pixel_hue to full resolution
    if ds > 1:
        pixel_hue = cv2.resize(pixel_hue, (w, h), interpolation=cv2.INTER_NEAREST)
    # 2026-04-25 — fine-grain inside cells so candy color isn't flat
    # at painter resolution (Item 3 broad-blob fix).
    grain = _fractal_surface_grain((h, w), seed + 8212)
    grain_centered = (grain - 0.5) * 2.0
    # Per-cell candy color shift, modulated by grain so each cell has
    # internal surface variation rather than uniform color blocks.
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + np.sin(pixel_hue * 6.2832) * 0.18 * pm * mask * (1.0 + grain_centered * 0.30), 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + np.sin(pixel_hue * 6.2832 + 2.094) * 0.14 * pm * mask * (1.0 + grain_centered * 0.30), 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + np.sin(pixel_hue * 6.2832 + 4.189) * 0.18 * pm * mask * (1.0 + grain_centered * 0.30), 0, 1)
    return result

spec_fractal_candy_chaos = _spec_fractal_candy_chaos
paint_fractal_candy_chaos = _paint_fractal_candy_chaos

# 3. FRACTAL PEARL CLOUD - Triple domain-warped 8-octave Perlin FBM
def _domain_warped_fbm(shape, seed, octaves=8):
    """3 layers of domain warping: warp the warp that warps the base."""
    h, w = shape
    y_g, x_g = _mgrid(shape)
    yn = y_g.astype(np.float32) / h
    xn = x_g.astype(np.float32) / w
    # Layer 1 warp
    w1a = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 100)
    w1b = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 200)
    # Layer 2 warp (warps the warp)
    w2a = _noise(shape, [16, 32], [0.5, 0.5], seed + 300)
    w2b = _noise(shape, [16, 32], [0.5, 0.5], seed + 400)
    w1a = w1a + w2a * 0.5
    w1b = w1b + w2b * 0.5
    # Layer 3 warp (warps the warp of the warp)
    w3a = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 500)
    w3b = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 600)
    w1a = w1a + w3a * 0.3
    w1b = w1b + w3b * 0.3
    # Warped coordinates
    yw = yn + w1a * 0.4
    xw = xn + w1b * 0.4
    # 8-octave FBM at warped coordinates
    fbm = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    total_amp = 0.0
    for i in range(octaves):
        freq = 2 ** (i + 1)
        n = np.sin(yw * freq * 6.28 + _noise(shape, [max(2, 16 >> i)], [1.0], seed + 700 + i * 37) * 2) * \
            np.cos(xw * freq * 4.71 + _noise(shape, [max(2, 16 >> i)], [1.0], seed + 800 + i * 41) * 2)
        fbm += n * amp
        total_amp += amp
        amp *= 0.55
    fbm = np.clip(fbm / total_amp * 0.5 + 0.5, 0, 1)
    return fbm

def _spec_fractal_pearl_cloud(shape, mask, seed, sm):
    h, w = shape
    cloud = _domain_warped_fbm(shape, seed + 8220)
    # Pearl: high cloud density = pearlescent (moderate M, low R, high CC)
    M = np.clip(cloud * 180 * sm + (1 - cloud) * 20, 0, 255)
    G = np.clip((1 - cloud) * 200 + cloud * 8, 0, 255)
    CC = np.clip(cloud * 240 + (1 - cloud) * 30, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_pearl_cloud(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    cloud = _domain_warped_fbm(shape, seed + 8220)
    # Iridescent multi-frequency pearl shimmer: 3 sine harmonics
    h1 = np.sin(cloud * 4.0)
    h2 = np.sin(cloud * 9.0) * 0.5
    h3 = np.sin(cloud * 17.0) * 0.25
    iridescence = (h1 + h2 + h3) / 1.75  # normalize to ~[-1, 1]
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + iridescence * 0.18 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + np.sin(cloud * 4.0 + 2.09 + np.sin(cloud * 9.0 + 2.09) * 0.5 + np.sin(cloud * 17.0 + 2.09) * 0.25) / 1.75 * 0.14 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + np.sin(cloud * 4.0 + 4.19 + np.sin(cloud * 9.0 + 4.19) * 0.5 + np.sin(cloud * 17.0 + 4.19) * 0.25) / 1.75 * 0.18 * pm * mask, 0, 1)
    return result

spec_fractal_pearl_cloud = _spec_fractal_pearl_cloud
paint_fractal_pearl_cloud = _paint_fractal_pearl_cloud

# 4. FRACTAL METALLIC STORM - Kolmogorov turbulence cascade simulation
def _kolmogorov_cascade(shape, seed, octaves=6):
    """Energy cascade: large scales feed small scales with amplification."""
    h, w = shape
    cascade = np.zeros((h, w), dtype=np.float32)
    energy_envelope = np.ones((h, w), dtype=np.float32)
    for i in range(octaves):
        scale = max(2, 128 >> i)
        turb_oct = np.abs(_noise(shape, [scale], [1.0], seed + i * 71))
        amplification = (i + 1) ** 0.8
        cascade += turb_oct * amplification * energy_envelope
        energy_envelope = np.clip(energy_envelope * (0.6 + turb_oct * 0.8), 0.3, 2.0)
    cascade = np.clip(cascade / (cascade.max() + 1e-10), 0, 1)
    return cascade

def _spec_fractal_metallic_storm(shape, mask, seed, sm):
    h, w = shape
    # Two separate cascade runs with different seeds so M and G aren't anti-correlated
    storm_m = _kolmogorov_cascade(shape, seed + 8230)
    storm_g = _kolmogorov_cascade(shape, seed + 8231)
    M = np.clip(storm_m * 255 * sm, 0, 255)
    G = np.clip((1 - storm_g) * 240 * sm + storm_g * 3, 0, 255)
    CC = np.clip(storm_m * 20 + (1 - storm_m) * 180, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_metallic_storm(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    storm = _kolmogorov_cascade(shape, seed + 8230)
    result = paint.copy()
    # Storm-driven contrast + warm/cool split instead of brightness-only
    contrast = (storm - 0.5) * 2.0  # [-1, 1] range
    for c in range(3):
        # Increase contrast: push values away from mid
        result[:,:,c] = np.clip(
            paint[:,:,c] + paint[:,:,c] * contrast * 0.35 * pm * mask, 0, 1)
    # Warm tint at storm peaks (red/amber), cool tint at troughs (blue)
    warm = np.clip(storm - 0.5, 0, 0.5) * 2.0  # 0-1 for peaks
    cool = np.clip(0.5 - storm, 0, 0.5) * 2.0  # 0-1 for troughs
    result[:,:,0] = np.clip(result[:,:,0] + warm * 0.12 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(result[:,:,1] + warm * 0.06 * pm * mask - cool * 0.04 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(result[:,:,2] + cool * 0.14 * pm * mask - warm * 0.06 * pm * mask, 0, 1)
    return result

spec_fractal_metallic_storm = _spec_fractal_metallic_storm
paint_fractal_metallic_storm = _paint_fractal_metallic_storm

# 5. FRACTAL MATTE CHROME - Sierpinski triangle material boundary
def _sierpinski_field(shape, seed, depth=8):
    """Recursive Sierpinski triangle: inside triangles=1, voids=0."""
    h, w = shape
    rng = np.random.RandomState(seed)
    y_g, x_g = _mgrid(shape)
    angle = rng.uniform(0, 2 * np.pi)
    yn = y_g.astype(np.float32) / max(h, w)
    xn = x_g.astype(np.float32) / max(h, w)
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    yr = yn * cos_a - xn * sin_a
    xr = yn * sin_a + xn * cos_a
    yr = yr - yr.min()
    xr = xr - xr.min()
    yr = yr / (yr.max() + 1e-10)
    xr = xr / (xr.max() + 1e-10)
    ax, ay = xr.copy(), yr.copy()
    inside = np.ones((h, w), dtype=np.float32)
    for _ in range(depth):
        ax = ax * 2.0
        ay = ay * 2.0
        fx = np.floor(ax).astype(np.int32) % 2
        fy = np.floor(ay).astype(np.int32) % 2
        is_void = (fx == 1) & (fy == 1)
        inside[is_void] = 0.0
        ax = ax - np.floor(ax)
        ay = ay - np.floor(ay)
    return inside

def _spec_fractal_matte_chrome(shape, mask, seed, sm):
    h, w = shape
    sierp = _sierpinski_field(shape, seed + 8240)
    boundary_noise = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 8241)
    sierp_soft = np.clip(sierp + boundary_noise * 0.08, 0, 1)
    M = np.clip(sierp_soft * 255 * sm, 0, 255)
    G = np.clip((1 - sierp_soft) * 230 + sierp_soft * 2, 0, 255)
    CC = np.clip((1 - sierp_soft) * 200 + sierp_soft * 16, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_matte_chrome(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    sierp = _sierpinski_field(shape, seed + 8240)
    matte = 1.0 - sierp
    result = paint.copy()
    # Base brightness: chrome zones bright +20%, matte zones dark -16%
    for c in range(3):
        result[:,:,c] = np.clip(
            paint[:,:,c] * (1 + sierp * 0.20 * pm - matte * 0.16 * pm) * mask + paint[:,:,c] * (1 - mask), 0, 1)
    # Chrome zones: cool silver-blue tint
    result[:,:,0] = np.clip(result[:,:,0] - sierp * 0.04 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(result[:,:,1] + sierp * 0.02 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(result[:,:,2] + sierp * 0.08 * pm * mask, 0, 1)
    # Matte zones: warm amber tint
    result[:,:,0] = np.clip(result[:,:,0] + matte * 0.08 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(result[:,:,1] + matte * 0.04 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(result[:,:,2] - matte * 0.06 * pm * mask, 0, 1)
    return result

spec_fractal_matte_chrome = _spec_fractal_matte_chrome
paint_fractal_matte_chrome = _paint_fractal_matte_chrome

# 6. FRACTAL WARM COLD - Reaction-diffusion Gray-Scott Turing patterns
_gray_scott_cache = {}

def _gray_scott_field(shape, seed, iterations=5):
    """Simplified Gray-Scott reaction-diffusion creating Turing patterns.
    OPTIMIZED: Simulates at 256x256 max then upscales — Turing patterns are smooth
    and upscale perfectly. Was running at full 2048x2048 (1000 iterations × 10 ops = ~160GB of array ops).
    Cached so spec_fn and paint_fn share the same result."""
    h, w = shape
    _key = (shape, seed, iterations)
    if _key in _gray_scott_cache:
        return _gray_scott_cache[_key]

    # Simulate at capped resolution — 256 is enough for Turing pattern detail
    max_sim = 256
    sim_h = min(h, max_sim)
    sim_w = min(w, max_sim)
    need_resize = (sim_h != h or sim_w != w)
    rng = np.random.RandomState(seed)
    sim_shape = (sim_h, sim_w)
    U = np.ones(sim_shape, dtype=np.float32)
    V = np.zeros(sim_shape, dtype=np.float32)
    n_seeds = rng.randint(8, 20)
    for _ in range(n_seeds):
        sy, sx = rng.randint(0, sim_h), rng.randint(0, sim_w)
        sh, sw = rng.randint(sim_h // 20, sim_h // 8), rng.randint(sim_w // 20, sim_w // 8)
        V[sy:sy+sh, sx:sx+sw] = 1.0
    seed_noise = _noise(sim_shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 10)
    V += np.clip(seed_noise * 0.5 + 0.3, 0, 0.5)
    Du, Dv = 0.16, 0.08
    f_rate = 0.035 + rng.uniform(-0.005, 0.010)
    k_rate = 0.060 + rng.uniform(-0.005, 0.005)
    for it in range(iterations):
        for _ in range(200):
            Lu = (np.roll(U, 1, 0) + np.roll(U, -1, 0) + np.roll(U, 1, 1) + np.roll(U, -1, 1) - 4 * U)
            Lv = (np.roll(V, 1, 0) + np.roll(V, -1, 0) + np.roll(V, 1, 1) + np.roll(V, -1, 1) - 4 * V)
            uvv = U * V * V
            U += Du * Lu - uvv + f_rate * (1 - U)
            V += Dv * Lv + uvv - (f_rate + k_rate) * V
            U = np.clip(U, 0, 1)
            V = np.clip(V, 0, 1)
    if need_resize:
        U = cv2.resize(U, (w, h), interpolation=cv2.INTER_LINEAR)
        V = cv2.resize(V, (w, h), interpolation=cv2.INTER_LINEAR)
    result = (U, V)
    if len(_gray_scott_cache) > 4:
        _gray_scott_cache.pop(next(iter(_gray_scott_cache)))
    _gray_scott_cache[_key] = result
    return result

def _spec_fractal_warm_cold(shape, mask, seed, sm):
    h, w = shape
    U, V = _gray_scott_field(shape, seed + 8250)
    blend = np.clip(V * 2.0, 0, 1)
    M = np.clip(blend * 30 + (1 - blend) * 245 * sm, 0, 255)
    G = np.clip(blend * 240 + (1 - blend) * 15, 0, 255)
    CC = np.clip(blend * 180 + (1 - blend) * 20, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_warm_cold(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    U, V = _gray_scott_field(shape, seed + 8250)
    blend = np.clip(V * 2.0, 0, 1)
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + (1 - blend) * 0.12 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + (1 - blend) * 0.04 * pm * mask - blend * 0.03 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + blend * 0.12 * pm * mask, 0, 1)
    return result

spec_fractal_warm_cold = _spec_fractal_warm_cold
paint_fractal_warm_cold = _paint_fractal_warm_cold

# 7. FRACTAL DEEP ORGANIC - Multi-scale ridge noise with rotated octaves
_ridge_fbm_cache = {}

def _rotated_ridge_fbm(shape, seed, octaves=6):
    """Ridge noise (1-|noise|) accumulated across octaves with 30deg rotation per octave.
    Cached so spec+paint share result."""
    _key = (shape, seed, octaves)
    if _key in _ridge_fbm_cache:
        return _ridge_fbm_cache[_key]
    h, w = shape
    y_g, x_g = _mgrid(shape)
    yn = y_g.astype(np.float32) / max(h, w)
    xn = x_g.astype(np.float32) / max(h, w)
    ridges = np.zeros((h, w), dtype=np.float32)
    amp = 1.0
    total_amp = 0.0
    angle = 0.0
    freq = 1.0
    for i in range(octaves):
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        yr = yn * cos_a - xn * sin_a
        xr = yn * sin_a + xn * cos_a
        # Use rotated coordinates as domain warp offset for the noise
        warp_offset = (yr * freq * 3.0 + xr * freq * 2.0)
        n = _noise(shape, [max(2, int(16 / freq))], [1.0], seed + i * 53)
        # Apply rotation warp: shift noise by rotated coordinate field
        n = n + np.sin(warp_offset * 6.2832) * 0.3
        ridge = 1.0 - np.abs(n)
        ridge = ridge ** 2
        ridges += ridge * amp
        total_amp += amp
        amp *= 0.6
        freq *= 2.0
        angle += np.pi / 6.0
    ridges = np.clip(ridges / total_amp, 0, 1)
    if len(_ridge_fbm_cache) > 4:
        _ridge_fbm_cache.pop(next(iter(_ridge_fbm_cache)))
    _ridge_fbm_cache[_key] = ridges
    return ridges

def _spec_fractal_deep_organic(shape, mask, seed, sm):
    h, w = shape
    veins = _rotated_ridge_fbm(shape, seed + 8260)
    M = np.clip(veins * 220 * sm + (1 - veins) * 10, 0, 255)
    G = np.clip((1 - veins) * 200 + veins * 15, 0, 255)
    CC = np.clip(veins * 180 + (1 - veins) * 40, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_deep_organic(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    veins = _rotated_ridge_fbm(shape, seed + 8260)
    flesh = 1.0 - veins
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] - veins * 0.14 * pm * mask + flesh * 0.10 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + veins * 0.16 * pm * mask - flesh * 0.10 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] - veins * 0.18 * pm * mask + flesh * 0.04 * pm * mask, 0, 1)
    return result

spec_fractal_deep_organic = _spec_fractal_deep_organic
paint_fractal_deep_organic = _paint_fractal_deep_organic

# 8. FRACTAL ELECTRIC NOISE - Diffusion-limited aggregation lightning discharge
_dla_cache = {}

def _dla_lightning(shape, seed, n_seeds=6, growth_steps=800):
    """DLA-approximated lightning: tree-like branching discharge from seed points.
    Cached so spec+paint share result."""
    _key = (shape, seed, n_seeds, growth_steps)
    if _key in _dla_cache:
        return _dla_cache[_key]
    h, w = shape
    rng = np.random.RandomState(seed)
    field = np.zeros((h, w), dtype=np.float32)
    growth_prob = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 50)
    growth_prob = np.clip(growth_prob * 0.5 + 0.5, 0.1, 0.9)
    seeds_y = np.concatenate([rng.randint(0, max(1, h // 4), n_seeds // 2),
                              rng.randint(0, h, n_seeds - n_seeds // 2)])
    seeds_x = rng.randint(max(1, w // 6), max(2, 5 * w // 6), n_seeds)
    # Maintain a frontier list instead of scanning entire field each step
    frontier = []
    for sy, sx in zip(seeds_y, seeds_x):
        sy, sx = int(sy), int(sx)
        if 0 <= sy < h and 0 <= sx < w:
            field[sy, sx] = 1.0
            frontier.append((sy, sx))
    for _ in range(growth_steps):
        if len(frontier) == 0:
            break
        idx = rng.randint(len(frontier))
        cy, cx = frontier[idx]
        for walk in range(rng.randint(3, 15)):
            dy, dx = rng.choice([-1, 0, 1]), rng.choice([-1, 0, 1])
            ny, nx = int(cy + dy), int(cx + dx)
            if 0 <= ny < h and 0 <= nx < w:
                if field[ny, nx] < 0.5 and rng.random() < growth_prob[ny, nx]:
                    field[ny, nx] = 1.0
                    frontier.append((ny, nx))
                    cy, cx = ny, nx
                else:
                    cy, cx = ny, nx
    glow = cv2.GaussianBlur(field.astype(np.float32), (7, 7), 3.0)
    result = np.clip(field * 0.7 + glow * 0.5, 0, 1)
    if len(_dla_cache) > 4:
        _dla_cache.pop(next(iter(_dla_cache)))
    _dla_cache[_key] = result
    return result

def _spec_fractal_electric_noise(shape, mask, seed, sm):
    h, w = shape
    arcs = _dla_lightning(shape, seed + 8270)
    # 2026-04-25 — fine-grain across the non-arc background so the dark
    # surrounding canvas isn't a flat blob (Item 3 broad-blob fix).
    grain = _fractal_surface_grain(shape, seed + 8271)
    M = np.clip((arcs * 255 * sm + (1 - arcs) * 30) * (0.85 + 0.30 * grain), 0, 255)
    G = np.clip((1 - arcs) * 160 + arcs * 0 + (grain - 0.5) * 30, 0, 255)
    CC = np.clip(arcs * 16 + (1 - arcs) * 100 + (grain - 0.5) * 24, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_electric_noise(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    arcs = _dla_lightning(shape, seed + 8270)
    # Gaussian glow falloff instead of binary on/off
    # arcs already has blur glow from _dla_lightning; use smooth power curve
    glow_soft = np.power(arcs, 0.6)  # soften edges for gradual falloff
    glow_core = np.power(arcs, 2.0)  # bright core
    # 2026-04-25 — fine surface grain visible on the non-arc background
    # so the dark canvas around the lightning isn't a flat blob at painter
    # resolution (Item 3 broad-blob fix).
    grain = _fractal_surface_grain(shape, seed + 8272)
    grain_centered = (grain - 0.5) * 2.0
    bg_micro = (1.0 - arcs) * grain_centered * 0.04 * pm
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + glow_soft * 0.12 * pm * mask + glow_core * 0.08 * pm * mask + bg_micro * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + glow_soft * 0.16 * pm * mask + glow_core * 0.10 * pm * mask + bg_micro * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + glow_soft * 0.25 * pm * mask + glow_core * 0.18 * pm * mask + bg_micro * 1.5 * mask, 0, 1)
    return result

spec_fractal_electric_noise = _spec_fractal_electric_noise
paint_fractal_electric_noise = _paint_fractal_electric_noise

# 9. FRACTAL COSMIC DUST - Galaxy spiral arm simulation
def _galaxy_spiral(shape, seed, n_arms=2):
    """Logarithmic spiral arms + FBM perturbation for galaxy structure."""
    h, w = shape
    rng = np.random.RandomState(seed)
    y_g, x_g = _mgrid(shape)
    cy = h / 2 + rng.uniform(-h * 0.1, h * 0.1)
    cx = w / 2 + rng.uniform(-w * 0.1, w * 0.1)
    yn = (y_g.astype(np.float32) - cy) / max(h, w)
    xn = (x_g.astype(np.float32) - cx) / max(h, w)
    r = np.sqrt(yn**2 + xn**2) + 1e-10
    theta = np.arctan2(yn, xn)
    spiral_tightness = rng.uniform(2.5, 4.5)
    arm_density = np.zeros((h, w), dtype=np.float32)
    arm_offset = rng.uniform(0, 2 * np.pi)
    for arm in range(n_arms):
        arm_angle = arm * 2 * np.pi / n_arms + arm_offset
        spiral_theta = spiral_tightness * np.log(r * 10 + 0.1) + arm_angle
        angle_diff = theta - spiral_theta
        angle_diff = (angle_diff + np.pi) % (2 * np.pi) - np.pi
        arm_width = 0.15 + r * 0.8
        arm_density += np.exp(-angle_diff**2 / (2 * arm_width**2))
    arm_density = np.clip(arm_density, 0, 1)
    fbm_perturb = _noise(shape, [4, 8, 16, 32], [0.2, 0.25, 0.3, 0.25], seed + 20)
    arm_density = np.clip(arm_density + fbm_perturb * 0.3, 0, 1)
    radial_falloff = np.exp(-r * 3.0)
    density = arm_density * radial_falloff
    density = np.clip(density / (density.max() + 1e-10), 0, 1)
    star_noise = _noise(shape, [2, 3, 5], [0.4, 0.35, 0.25], seed + 30)
    stars = np.clip((star_noise - 0.3) * 5, 0, 1) * density
    dust = np.clip(1 - density - stars * 0.5, 0, 1)
    return density, stars, dust

def _spec_fractal_cosmic_dust(shape, mask, seed, sm):
    h, w = shape
    density, stars, dust = _galaxy_spiral(shape, seed + 8280)
    M = np.clip((density * 160 + stars * 95) * sm, 0, 255)
    G = np.clip(dust * 230 + (1 - dust) * 5, 0, 255)
    CC = np.clip(density * 60 + stars * 16 + dust * 180, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_cosmic_dust(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    density, stars, dust = _galaxy_spiral(shape, seed + 8280)
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + stars * 0.20 * pm * mask - dust * 0.06 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + stars * 0.18 * pm * mask - dust * 0.04 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + stars * 0.25 * pm * mask + density * 0.05 * pm * mask, 0, 1)
    return result

spec_fractal_cosmic_dust = _spec_fractal_cosmic_dust
paint_fractal_cosmic_dust = _paint_fractal_cosmic_dust

# 10. FRACTAL LIQUID FIRE - Flame simulation with buoyancy and domain-warped turbulence
def _flame_simulation(shape, seed):
    """Domain-warped turbulence with upward velocity bias for flame tongues."""
    h, w = shape
    y_g, x_g = _mgrid(shape)
    yn = y_g.astype(np.float32) / h
    xn = x_g.astype(np.float32) / w
    turb = np.zeros((h, w), dtype=np.float32)
    for i in range(5):
        scale = max(2, 64 >> i)
        t = np.abs(_noise(shape, [scale], [1.0], seed + i * 47))
        turb += t / (i + 1)
    turb = np.clip(turb / 2.0, 0, 1)
    buoyancy = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 300)
    upward_warp = buoyancy * (1.0 - yn) * 0.6
    lateral_warp = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 400) * 0.3
    warp_y = np.clip(yn + upward_warp, 0, 1)
    core_x = np.abs(xn - 0.5) * 2
    heat_base = np.clip(1.0 - yn * 0.8 - core_x * 0.4, 0, 1)
    flame = np.clip(heat_base * 0.6 + turb * 0.5 - warp_y * 0.15 + lateral_warp * 0.1, 0, 1)
    flame = np.power(flame, 0.8)
    flame = np.clip(flame / (flame.max() + 1e-10), 0, 1)
    return flame

def _spec_fractal_liquid_fire(shape, mask, seed, sm):
    h, w = shape
    # Separate flame simulations for each channel so they aren't coupled
    fire_m = _flame_simulation(shape, seed + 8290)
    fire_g = _flame_simulation(shape, seed + 8291)
    fire_cc = _flame_simulation(shape, seed + 8292)
    # 2026-04-25 — fine ember/ash grain inside both fire and dark regions
    # so the surface has material character at painter resolution
    # (Item 3 broad-blob fix, large_blob_ratio was 0.68).
    grain = _fractal_surface_grain(shape, seed + 8293, scales=(2, 5, 11))
    M = np.clip((fire_m * 250 * sm + (1 - fire_m) * 5) * (0.85 + 0.30 * grain), 0, 255)
    G = np.clip(((1 - fire_g) * 240 + fire_g * 3) * (0.85 + 0.30 * (1.0 - grain)), 0, 255)
    CC = np.clip(fire_cc * 16 + (1 - fire_cc) * 160 + (grain - 0.5) * 24, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_liquid_fire(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    fire = _flame_simulation(shape, seed + 8290)
    # 2026-04-25 — ember/ash grain modulates both fire intensity and
    # dark cooling regions so the surface isn't flat-color at painter
    # resolution (Item 3 broad-blob fix).
    grain = _fractal_surface_grain(shape, seed + 8294, scales=(2, 5, 11))
    grain_centered = (grain - 0.5) * 2.0
    fire_mod = fire * (1.0 + grain_centered * 0.25)
    cool_mod = (1 - fire) * (1.0 + grain_centered * 0.25)
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + fire_mod * 0.30 * pm * mask - cool_mod * 0.08 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + fire_mod * 0.12 * pm * mask - cool_mod * 0.06 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] - fire_mod * 0.10 * pm * mask - cool_mod * 0.04 * pm * mask, 0, 1)
    return result

spec_fractal_liquid_fire = _spec_fractal_liquid_fire
paint_fractal_liquid_fire = _paint_fractal_liquid_fire


# SPB-67: Fractal Chaos source rebuild.
#
# The older Fractal Chaos functions produced good identity ideas, but several
# paths still paid for full-resolution simulations plus the generic fusion detail
# wrapper. That left multiple active finishes above the 5s red-flag budget at
# 2048. These explicit source renderers keep each finish visually separate while
# sharing one small-field cache: compute the complex structure at a capped
# resolution, upscale once, then add cheap full-canvas micro detail.
_fractal_fast_cache = {}


def _fc_small_shape(shape, cap=640):
    h, w = shape
    scale = min(1.0, float(cap) / float(max(1, max(h, w))))
    return max(160, int(round(h * scale))), max(160, int(round(w * scale)))


def _fc_resize(field, shape, interpolation=cv2.INTER_LINEAR):
    h, w = shape
    if field.shape == (h, w):
        return field.astype(np.float32, copy=False)
    return cv2.resize(field.astype(np.float32), (w, h), interpolation=interpolation).astype(np.float32)


def _fc_norm(field):
    field = field.astype(np.float32, copy=False)
    lo = float(np.min(field))
    hi = float(np.max(field))
    if hi <= lo + 1e-8:
        return np.zeros_like(field, dtype=np.float32)
    return np.clip((field - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def _fc_ridge(field, gain=1.0):
    return np.clip(1.0 - np.abs(field * 2.0 - 1.0) * gain, 0.0, 1.0).astype(np.float32)


def _fc_edge(field, amount=10.0):
    gy = np.diff(field, axis=0, prepend=field[:1, :])
    gx = np.diff(field, axis=1, prepend=field[:, :1])
    return np.clip(np.sqrt(gx * gx + gy * gy) * amount, 0.0, 1.0).astype(np.float32)


def _fc_micro(shape, seed, variant):
    fine = (_noise(shape, [1, 2, 3], [0.42, 0.34, 0.24], seed + 11400 + variant) + 1.0) * 0.5
    grain = (_noise(shape, [3, 5, 9], [0.38, 0.34, 0.28], seed + 11500 + variant) + 1.0) * 0.5
    grit = np.clip((fine - 0.50) * 5.0, 0.0, 1.0)
    return fine.astype(np.float32), grain.astype(np.float32), grit.astype(np.float32)


def _fc_fields(shape, seed, variant):
    small_shape = _fc_small_shape(shape)
    key = (small_shape, int(seed), int(variant))
    if key in _fractal_fast_cache:
        small = _fractal_fast_cache[key]
    else:
        sh, sw = small_shape
        rng = np.random.RandomState(int(seed) + 10200 + int(variant) * 97)
        yg, xg = _mgrid(small_shape)
        yn = (yg.astype(np.float32) / max(1, sh - 1) - 0.5) * 2.0
        xn = (xg.astype(np.float32) / max(1, sw - 1) - 0.5) * 2.0
        angle = rng.uniform(-np.pi, np.pi)
        ca, sa = np.cos(angle), np.sin(angle)
        xr = xn * ca - yn * sa
        yr = xn * sa + yn * ca
        n1 = (_noise(small_shape, [4, 8, 16], [0.34, 0.38, 0.28], seed + 10300 + variant) + 1.0) * 0.5
        n2 = (_noise(small_shape, [2, 5, 11], [0.40, 0.34, 0.26], seed + 10400 + variant) + 1.0) * 0.5
        n3 = (_noise(small_shape, [10, 22, 46], [0.42, 0.34, 0.24], seed + 10500 + variant) + 1.0) * 0.5
        radius = np.sqrt(xr * xr + yr * yr)
        theta = np.arctan2(yr, xr)
        if variant == 0:  # chrome decay: eroded island edges
            body = _fc_norm(np.sin((xr * 2.1 + n1 * 1.6) * 3.4) + np.cos((yr * 1.8 - n2) * 4.0) - radius * 0.8)
            structure = _fc_ridge(body * 0.74 + n3 * 0.26, 1.25)
            accent = _fc_edge(body, 8.0)
        elif variant == 1:  # candy chaos: warped cellular shards
            cell = np.sin((xr + n1 * 0.42) * 16.0) * np.sin((yr - n2 * 0.38) * 13.0)
            structure = _fc_norm(cell + np.sin((theta + n3) * 9.0) * 0.45)
            body = _fc_ridge(structure, 1.05)
            accent = _fc_edge(structure, 14.0)
        elif variant == 2:  # pearl cloud: soft rolling plumes
            body = _fc_norm(n1 * 0.55 + n2 * 0.30 + np.sin((xr * 2.4 + yr * 1.3 + n3) * 3.0) * 0.15)
            structure = _fc_ridge(body * 0.85 + n3 * 0.15, 1.55)
            accent = _fc_edge(body, 7.0)
        elif variant == 3:  # metallic storm: diagonal turbulent fronts
            storm = np.sin((xr * 3.2 + yr * 7.0 + n1 * 2.5) * 2.6)
            body = _fc_norm(storm + n2 * 0.85 + np.sin(theta * 5.0) * 0.20)
            structure = _fc_ridge(body, 1.12)
            accent = np.maximum(_fc_edge(body, 12.0), np.clip((structure - 0.70) * 3.4, 0, 1))
        elif variant == 4:  # matte chrome: recursive triangular web without full simulation
            ax = np.abs(((xr + n1 * 0.16) * 2.0) % 1.0 - 0.5)
            ay = np.abs(((yr - n2 * 0.16) * 2.0) % 1.0 - 0.5)
            tri = np.minimum(ax + ay, 1.0 - np.abs(ax - ay))
            body = _fc_norm(tri + n3 * 0.35)
            structure = _fc_ridge(body, 1.25)
            accent = _fc_edge(structure, 12.0)
        elif variant == 5:  # warm/cold: turing-like ribbons
            ribbons = np.sin((xr + n1 * 0.52) * 10.5 + np.sin((yr + n2) * 8.0) * 1.8)
            body = _fc_norm(ribbons + n3 * 0.55)
            structure = _fc_ridge(body, 1.08)
            accent = _fc_edge(body, 10.0)
        elif variant == 6:  # deep organic: branching vein growth
            veins = np.sin((xr * 5.0 + n1 * 2.2)) + np.cos((yr * 6.2 - n2 * 1.6)) + np.sin((xr + yr + n3) * 8.0) * 0.5
            body = _fc_norm(veins)
            structure = _fc_ridge(body, 1.35)
            accent = np.maximum(_fc_edge(structure, 14.0), np.clip((structure - 0.76) * 4.0, 0, 1))
        elif variant == 7:  # electric noise: thin discharge filaments
            discharge = np.sin((xr * 13.0 + n1 * 3.0)) * np.cos((yr * 11.0 - n2 * 2.6))
            body = _fc_norm(discharge + np.sin(theta * 12.0 + radius * 16.0) * 0.45)
            structure = np.clip(_fc_ridge(body, 0.90) ** 2.2, 0, 1)
            accent = np.maximum(_fc_edge(body, 18.0), np.clip((structure - 0.68) * 3.8, 0, 1))
        elif variant == 8:  # cosmic dust: spiral arms and star lanes
            spiral = np.sin(theta * 2.0 + np.log(radius + 0.05) * 5.2 + n1 * 1.5)
            body = _fc_norm(spiral * np.exp(-radius * 1.25) + n2 * 0.85 + n3 * 0.25)
            structure = np.clip(body * (1.0 - np.clip(radius * 0.70, 0, 1)) + _fc_ridge(n3, 1.4) * 0.35, 0, 1)
            accent = np.maximum(_fc_edge(structure, 8.0), np.clip((n1 - 0.78) * 5.0, 0, 1))
        else:  # liquid fire: flame tongues and cooled crust
            heat = np.clip(1.05 - (yn + 1.0) * 0.46 - np.abs(xn + n2 * 0.20) * 0.32, 0, 1)
            tongues = np.sin((xr * 9.0 + n1 * 3.0) + (1.0 - yn) * 7.0)
            body = _fc_norm(heat * 1.2 + tongues * 0.30 + n3 * 0.46)
            structure = np.clip(body ** 0.72, 0, 1)
            accent = np.maximum(_fc_edge(body, 10.0), np.clip((structure - 0.68) * 2.7, 0, 1))
        small = (
            body.astype(np.float32),
            structure.astype(np.float32),
            accent.astype(np.float32),
            n1.astype(np.float32),
            n2.astype(np.float32),
            n3.astype(np.float32),
        )
        if len(_fractal_fast_cache) > 10:
            _fractal_fast_cache.pop(next(iter(_fractal_fast_cache)))
        _fractal_fast_cache[key] = small
    return tuple(_fc_resize(v, shape) for v in small)


def _make_fractal_chaos_fast(variant, cool, warm, accent_color, base_m, base_r, base_cc, paint_mix=0.86):
    cool = np.asarray(cool, dtype=np.float32)
    warm = np.asarray(warm, dtype=np.float32)
    accent_color = np.asarray(accent_color, dtype=np.float32)

    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        body, structure, accent, n1, n2, n3 = _fc_fields(shape, int(seed), variant)
        fine, grain, grit = _fc_micro(shape, int(seed), variant)
        flash = np.clip(accent * 0.72 + grit * 0.42 + _fc_edge(structure, 6.0) * 0.38, 0, 1)
        metal = np.clip(base_m + structure * 92.0 + flash * 118.0 + (fine - 0.5) * 36.0, 0, 255) * float(sm)
        rough = np.clip(base_r + (1.0 - structure) * 72.0 - flash * 48.0 + grain * 22.0, 15, 245)
        clear = np.clip(base_cc + body * 54.0 + flash * 112.0 + accent * 60.0, 16, 255)
        return _spec_out(shape, mask2, metal, rough, clear)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        if paint.ndim == 3 and paint.shape[2] > 3:
            base = paint[:, :, :3].astype(np.float32, copy=True)
        else:
            base = paint.astype(np.float32, copy=True)
        body, structure, accent, n1, n2, n3 = _fc_fields(shape, int(seed), variant)
        fine, grain, grit = _fc_micro(shape, int(seed), variant)
        tone = np.clip(body * 0.62 + structure * 0.25 + fine * 0.13, 0, 1)
        color = cool.reshape(1, 1, 3) * (1.0 - tone[:, :, np.newaxis]) + warm.reshape(1, 1, 3) * tone[:, :, np.newaxis]
        flash = np.clip(accent * 0.72 + grit * 0.35, 0, 1)[:, :, np.newaxis]
        target = np.clip(color + accent_color.reshape(1, 1, 3) * flash * 0.46 + (grain[:, :, np.newaxis] - 0.5) * 0.08, 0, 1)
        blend = np.clip((paint_mix + flash * 0.08) * float(pm), 0.0, 0.96) * mask2[:, :, np.newaxis]
        return np.clip(base * (1.0 - blend) + target * blend, 0.0, 1.0).astype(np.float32)

    return spec_fn, paint_fn


spec_fractal_chrome_decay, paint_fractal_chrome_decay = _make_fractal_chaos_fast(
    0, (0.06, 0.07, 0.08), (0.72, 0.78, 0.76), (0.88, 0.28, 0.16), 108, 58, 84, 0.82
)
spec_fractal_candy_chaos, paint_fractal_candy_chaos = _make_fractal_chaos_fast(
    1, (0.08, 0.20, 0.64), (1.00, 0.12, 0.42), (1.00, 0.76, 0.18), 142, 50, 104, 0.88
)
spec_fractal_pearl_cloud, paint_fractal_pearl_cloud = _make_fractal_chaos_fast(
    2, (0.50, 0.68, 0.94), (0.96, 0.82, 1.00), (0.96, 1.00, 0.86), 96, 70, 136, 0.78
)
spec_fractal_metallic_storm, paint_fractal_metallic_storm = _make_fractal_chaos_fast(
    3, (0.04, 0.10, 0.20), (0.92, 0.58, 0.22), (0.58, 0.92, 1.00), 176, 42, 94, 0.84
)
spec_fractal_matte_chrome, paint_fractal_matte_chrome = _make_fractal_chaos_fast(
    4, (0.18, 0.20, 0.22), (0.84, 0.86, 0.82), (0.46, 0.88, 1.00), 168, 76, 94, 0.76
)
spec_fractal_warm_cold, paint_fractal_warm_cold = _make_fractal_chaos_fast(
    5, (0.04, 0.38, 0.98), (1.00, 0.32, 0.06), (1.00, 0.92, 0.40), 148, 48, 102, 0.86
)
spec_fractal_deep_organic, paint_fractal_deep_organic = _make_fractal_chaos_fast(
    6, (0.02, 0.20, 0.08), (0.78, 0.58, 0.22), (0.22, 1.00, 0.54), 138, 64, 112, 0.84
)
spec_fractal_electric_noise, paint_fractal_electric_noise = _make_fractal_chaos_fast(
    7, (0.02, 0.12, 0.44), (0.16, 0.92, 1.00), (0.92, 0.96, 1.00), 184, 34, 118, 0.88
)
spec_fractal_cosmic_dust, paint_fractal_cosmic_dust = _make_fractal_chaos_fast(
    8, (0.02, 0.04, 0.16), (0.80, 0.20, 0.96), (1.00, 0.86, 0.42), 128, 58, 126, 0.82
)
spec_fractal_liquid_fire, paint_fractal_liquid_fire = _make_fractal_chaos_fast(
    9, (0.08, 0.02, 0.01), (1.00, 0.30, 0.02), (1.00, 0.86, 0.18), 172, 40, 92, 0.88
)




# ================================================================
# PARADIGM 14: SPECTRAL GRADIENT MATERIAL - Color-reactive spec
# ================================================================

def _wavelength_to_rgb(wl):
    """Convert wavelength (380-780nm) field to RGB (0-1). Vectorized."""
    r = np.zeros_like(wl)
    g = np.zeros_like(wl)
    b = np.zeros_like(wl)
    mk = (wl >= 380) & (wl < 440)
    r = np.where(mk, -(wl - 440) / 60.0, r)
    b = np.where(mk, 1.0, b)
    mk = (wl >= 440) & (wl < 490)
    g = np.where(mk, (wl - 440) / 50.0, g)
    b = np.where(mk, 1.0, b)
    mk = (wl >= 490) & (wl < 510)
    g = np.where(mk, 1.0, g)
    b = np.where(mk, -(wl - 510) / 20.0, b)
    mk = (wl >= 510) & (wl < 580)
    r = np.where(mk, (wl - 510) / 70.0, r)
    g = np.where(mk, 1.0, g)
    mk = (wl >= 580) & (wl < 645)
    r = np.where(mk, 1.0, r)
    g = np.where(mk, -(wl - 645) / 65.0, g)
    mk = (wl >= 645) & (wl <= 780)
    r = np.where(mk, 1.0, r)
    intensity = np.ones_like(wl)
    mk = (wl >= 380) & (wl < 420)
    intensity = np.where(mk, 0.3 + 0.7 * (wl - 380) / 40.0, intensity)
    mk = (wl > 700) & (wl <= 780)
    intensity = np.where(mk, 0.3 + 0.7 * (780 - wl) / 80.0, intensity)
    mk = (wl < 380) | (wl > 780)
    intensity = np.where(mk, 0.0, intensity)
    return np.clip(r * intensity, 0, 1), np.clip(g * intensity, 0, 1), np.clip(b * intensity, 0, 1)


def _spectral_noise(shape, scales, weights, seed):
    return _multiscale_smooth_noise(shape, scales, weights, seed)


def _spectral_field(shape, seed, seed_offset):
    """Smooth optical-film field for spectral mapping.

    The cached global noise path is nearest-neighbor upscaled; when it drove
    spectral color directly it produced square cells in every finish. This
    field keeps the broad wavelength zones but builds them from interpolated
    film-flow, interference, and fine pigment layers.
    """
    h, w = shape
    y, x = _mgrid(shape)
    yf, xf = y.astype(np.float32), x.astype(np.float32)

    flow_a = _spectral_noise(shape, [18, 36, 72], [0.34, 0.40, 0.26], seed + seed_offset + 11)
    flow_b = _spectral_noise(shape, [14, 28, 56], [0.38, 0.38, 0.24], seed + seed_offset + 23)
    prism = _spectral_noise(shape, [5, 9, 17], [0.40, 0.36, 0.24], seed + seed_offset + 37)
    pigment = _spectral_noise(shape, [1, 2, 4], [0.46, 0.34, 0.20], seed + seed_offset + 41)

    angle = ((seed_offset % 29) - 14) * np.pi / 180.0
    film_axis = xf * np.cos(angle) + yf * np.sin(angle)
    cross_axis = -xf * np.sin(angle) + yf * np.cos(angle)
    film = np.sin(film_axis * 0.030 + flow_a * 2.8 + seed * 0.013) * 0.5 + 0.5
    cross = np.sin(cross_axis * 0.024 + flow_b * 2.2 + seed_offset * 0.019) * 0.5 + 0.5

    cy = h * (0.45 + 0.10 * np.sin(seed_offset))
    cx = w * (0.55 + 0.08 * np.cos(seed_offset * 0.7))
    dist = np.sqrt((yf - cy) ** 2 + (xf - cx) ** 2)
    rings = np.sin(dist * 0.052 + prism * 2.6 + seed * 0.007) * 0.5 + 0.5

    field = (
        _fusion_norm01(flow_a) * 0.26
        + _fusion_norm01(flow_b) * 0.20
        + film * 0.24
        + cross * 0.12
        + rings * 0.12
        + (_fusion_norm01(pigment) - 0.5) * 0.06
    )
    return _fusion_norm01(cv2.GaussianBlur(field.astype(np.float32), (0, 0), sigmaX=0.55, sigmaY=0.55))


def _make_spectral_fusion(mapping_type, m_range, g_range, base_cc, seed_offset=0):
    """Factory: spectral-reactive material properties with real wavelength mapping,
    thin-film interference, luminance reactivity, and photonic crystal behavior."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_spectral_fusion(mapping_type, m_range, g_range, base_cc, seed_offset))

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        field = _spectral_field(shape, seed, seed_offset)
        fine = _spectral_noise(shape, [8, 16, 32], [0.34, 0.40, 0.26], seed + seed_offset + 100)
        micro = _spectral_noise(shape, [1, 2, 3], [0.44, 0.34, 0.22], seed + seed_offset + 110)

        if mapping_type == "rainbow":
            wl = 380 + field * 400
            temp = np.clip((wl - 480) / 200.0, 0, 1)
            M = m_range[0] + temp * (m_range[1] - m_range[0]) * sm
            G = g_range[1] - temp * (g_range[1] - g_range[0]) * sm
            spectral_peaks = np.abs(np.sin(field * np.pi * 4))
            B = np.clip(float(base_cc) + (1 - spectral_peaks) * 40 * sm - spectral_peaks * 15 * sm, 16, 255)

        elif mapping_type == "binary":
            phase = 1.0 / (1.0 + np.exp(-(field - 0.5) * 20))
            boundary_dist = np.abs(field - 0.5)
            fringe = np.sin(boundary_dist * 80 * np.pi) * np.exp(-boundary_dist * 12)
            fringe_zone = np.exp(-(boundary_dist ** 2) / (2 * 0.04 ** 2))
            M = m_range[0] * (1 - phase) + m_range[1] * phase
            M = M + fringe * 60 * sm * fringe_zone
            G = g_range[1] * (1 - phase) + g_range[0] * phase
            G = G + np.abs(fringe) * 30 * sm * fringe_zone
            B = np.clip(float(base_cc) + phase * 30 * sm - fringe_zone * 20 * sm, 16, 255)

        elif mapping_type == "value":
            lum = field
            M = m_range[0] + lum * lum * (m_range[1] - m_range[0]) * sm
            G = g_range[1] - lum * lum * (g_range[1] - g_range[0]) * sm
            B = np.clip(float(base_cc) + (1 - lum) * 50 * sm - lum * 10 * sm, 16, 255)

        elif mapping_type == "saturation":
            sat = field
            M = m_range[0] + sat * sat * (m_range[1] - m_range[0]) * sm
            G = g_range[0] + (1 - sat) * (1 - sat) * (g_range[1] - g_range[0]) * sm
            sat_micro = micro * (1 - sat) * 15 * sm
            G = G + np.abs(sat_micro)
            B = np.clip(float(base_cc) + (1 - sat) * 25 * sm, 16, 255)

        elif mapping_type == "tri":
            uv = np.clip((0.33 - field) / 0.12, 0, 1)
            vis = np.clip(1.0 - np.abs(field - 0.5) / 0.2, 0, 1)
            ir = np.clip((field - 0.66) / 0.12, 0, 1)
            M = 200 * uv + 255 * vis + 30 * ir
            G = 15 * uv + 5 * vis + 180 * ir
            B = 40.0 * uv + 16.0 * vis + 160.0 * ir
            band_edge = np.clip(1.0 - np.minimum(np.abs(field - 0.33), np.abs(field - 0.66)) * 8, 0, 1)
            M = M + band_edge * 40 * sm
            G = G - band_edge * 20 * sm

        elif mapping_type == "inverted":
            inv_field = 1.0 - field
            resonance = np.sin(inv_field * np.pi * 6) ** 2
            anti_resonance = 1.0 - resonance
            M = m_range[0] + resonance * (m_range[1] - m_range[0]) * sm
            G = g_range[0] + anti_resonance * (g_range[1] - g_range[0]) * sm
            B = np.clip(float(base_cc) + (resonance - 0.5) * 50 * sm, 16, 255)

        elif mapping_type == "gradient":
            # LAZY-FUSIONS-008 FIX: linear (first-order) M/G ramp — distinct from "value" (quadratic lum²)
            M = m_range[0] + field * (m_range[1] - m_range[0]) * sm
            G = g_range[1] - field * (g_range[1] - g_range[0]) * sm
            B = np.clip(float(base_cc) + (0.5 - field) * 60 * sm, 16, 255)

        elif mapping_type == "threshold":
            # LAZY-FUSIONS-008 FIX: hard Boolean step — metallic/matte zones with no gradient blend
            # Distinct from "binary" (logistic sigmoid + fringe interference)
            step = np.clip((field - np.float32(0.44)) / np.float32(0.12), 0, 1)
            step = step * step * (np.float32(3.0) - np.float32(2.0) * step)
            M = m_range[0] * (np.float32(1.0) - step) + m_range[1] * step
            G = g_range[1] * (np.float32(1.0) - step) + g_range[0] * step
            B = np.clip(float(base_cc) + (np.float32(1.0) - step) * 40 * sm - step * 15 * sm, 16, 255)

        else:
            M = np.full((h, w), float(m_range[0]), dtype=np.float32)
            G = np.full((h, w), float(g_range[0]), dtype=np.float32)
            B = np.full((h, w), float(base_cc), dtype=np.float32)

        M = M + fine * 10 * sm
        G = G + np.abs(fine) * 8 * sm + np.abs(micro) * 5 * sm
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        """Spectral mapping: COLORSHOXX-style color zones married to spectral field.
        UPGRADED: Adds rainbow hue-rotation color push + warm/cool zones + edge rim
        ON TOP of per-mapping spectral effects.
        - High-field zones: spectral hue tint (rainbow push via cos mapping) + brightening
        - Low-field zones: cool shadow push (desaturate, darken, retain blue)
        - Edges (Sobel): bright warm-white rim highlight"""
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        field = _spectral_field(shape, seed, seed_offset)
        result = paint.copy()

        if mapping_type == "rainbow":
            wl = 380 + field * 400
            r, g, b = _wavelength_to_rgb(wl)
            blend = 0.16 * pm
            result[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r * blend * mask, 0, 1)
            result[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g * blend * mask, 0, 1)
            result[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b * blend * mask, 0, 1)

        elif mapping_type == "binary":
            phase = 1.0 / (1.0 + np.exp(-(field - 0.5) * 20))
            boundary_dist = np.abs(field - 0.5)
            fringe_zone = np.exp(-(boundary_dist ** 2) / (2 * 0.04 ** 2))
            result[:,:,0] = np.clip(paint[:,:,0] + phase * 0.14 * pm * mask, 0, 1)
            result[:,:,2] = np.clip(paint[:,:,2] + (1 - phase) * 0.14 * pm * mask, 0, 1)
            fringe_hue = np.clip(boundary_dist * 15, 0, 1)
            fr, fg, fb = _hsv_to_rgb(fringe_hue, np.full_like(fringe_hue, 0.8), np.full_like(fringe_hue, 0.9))
            fb_blend = fringe_zone * 0.18 * pm
            result[:,:,0] = np.clip(result[:,:,0] + fr * fb_blend * mask, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + fg * fb_blend * mask, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + fb * fb_blend * mask, 0, 1)

        elif mapping_type == "value":
            lum = field
            bright = lum * lum * 0.22 * pm
            dark = (1 - lum) * (1 - lum) * 0.14 * pm
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] + bright * mask - dark * mask, 0, 1)

        elif mapping_type == "saturation":
            sat = field
            r, g, b = _hsv_to_rgb(sat * 0.8, sat * sat * 0.85, np.full_like(sat, 0.8))
            blend = 0.14 * pm * sat * sat
            result[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r * blend * mask, 0, 1)
            result[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g * blend * mask, 0, 1)
            result[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b * blend * mask, 0, 1)

        elif mapping_type == "tri":
            uv = np.clip((0.33 - field) / 0.12, 0, 1)
            vis = np.clip(1.0 - np.abs(field - 0.5) / 0.2, 0, 1)
            ir = np.clip((field - 0.66) / 0.12, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + uv * 0.16 * pm * mask, 0, 1)
            result[:,:,0] = np.clip(result[:,:,0] + uv * 0.06 * pm * mask + vis * 0.14 * pm * mask + ir * 0.08 * pm * mask, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + vis * 0.10 * pm * mask - ir * 0.06 * pm * mask, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] - ir * 0.08 * pm * mask, 0, 1)

        elif mapping_type == "inverted":
            inv = 1.0 - field
            resonance = np.sin(inv * np.pi * 6) ** 2
            r, g, b = _hsv_to_rgb(inv * 0.7, resonance * 0.7, np.full_like(inv, 0.75))
            blend = 0.14 * pm
            result[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r * blend * mask, 0, 1)
            result[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g * blend * mask, 0, 1)
            result[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b * blend * mask, 0, 1)

        elif mapping_type == "gradient":
            # LAZY-FUSIONS-008 FIX: warm-cool spectral tint — linear hue sweep (red=bright, blue=dark)
            warm = field * np.float32(0.22) * pm
            cool = (np.float32(1.0) - field) * np.float32(0.18) * pm
            result[:,:,0] = np.clip(paint[:,:,0] + warm * mask, 0, 1)
            result[:,:,1] = np.clip(paint[:,:,1] + (warm - cool) * np.float32(0.25) * mask, 0, 1)
            result[:,:,2] = np.clip(paint[:,:,2] + cool * mask, 0, 1)

        elif mapping_type == "threshold":
            # LAZY-FUSIONS-008 FIX: hard-cut step — specular-pop bright zones + shadow-crush dark zones
            step = np.clip((field - np.float32(0.44)) / np.float32(0.12), 0, 1)
            step = step * step * (np.float32(3.0) - np.float32(2.0) * step)
            bright_zone = step * np.float32(0.28) * pm
            dark_zone = (np.float32(1.0) - step) * np.float32(0.20) * pm
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] + bright_zone * mask - dark_zone * mask, 0, 1)

        else:
            r, g, b = _hsv_to_rgb(field, np.full_like(field, 0.6), np.full_like(field, 0.7))
            blend = 0.10 * pm
            result[:,:,0] = np.clip(paint[:,:,0] * (1 - blend * mask) + r * blend * mask, 0, 1)
            result[:,:,1] = np.clip(paint[:,:,1] * (1 - blend * mask) + g * blend * mask, 0, 1)
            result[:,:,2] = np.clip(paint[:,:,2] * (1 - blend * mask) + b * blend * mask, 0, 1)

        # === COLORSHOXX color zones: spectral hue rotation + warm/cool + edge rim ===
        pv = field  # the spectral field IS our pv

        # Rainbow hue-rotation push: field drives hue via cos mapping (like ghost pattern)
        rng = np.random.RandomState(seed + seed_offset + 888)
        spec_hue = rng.uniform(0.0, 1.0)  # base hue offset for variety
        hue_field = (spec_hue + field * 0.6) % 1.0  # field sweeps ~60% of hue wheel
        spec_r = np.float32(0.5) + np.float32(0.5) * np.cos(hue_field * 2 * np.pi).astype(np.float32)
        spec_g = np.float32(0.5) + np.float32(0.5) * np.cos((hue_field - 0.333) * 2 * np.pi).astype(np.float32)
        spec_b = np.float32(0.5) + np.float32(0.5) * np.cos((hue_field - 0.667) * 2 * np.pi).astype(np.float32)

        # High-pv zones: spectral hue tint + warm brightening
        high_zone = np.clip((pv - 0.3) * 2.0, 0, 1).astype(np.float32)
        hue_blend = high_zone * 0.25 * pm
        result[:,:,0] = np.clip(result[:,:,0] * (1 - hue_blend * mask) + spec_r * hue_blend * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] * (1 - hue_blend * mask) + spec_g * hue_blend * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] * (1 - hue_blend * mask) + spec_b * hue_blend * mask, 0, 1)
        bright_sp = high_zone * 0.10 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + bright_sp * mask, 0, 1)

        # Low-pv zones: cool desaturation + darkening
        low_zone = np.clip((0.3 - pv) * 3.0, 0, 1).astype(np.float32)
        gray = (result[:,:,0] * 0.299 + result[:,:,1] * 0.587 + result[:,:,2] * 0.114)
        cool_desat = low_zone * 0.18 * pm
        result[:,:,0] = np.clip(result[:,:,0] * (1 - cool_desat * mask) + gray * cool_desat * mask - low_zone * 0.05 * pm * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] * (1 - cool_desat * mask) + gray * cool_desat * mask - low_zone * 0.03 * pm * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] * (1 - cool_desat * mask * 0.7) + gray * cool_desat * mask * 0.7 + low_zone * 0.02 * pm * mask, 0, 1)

        # Edges (Sobel): bright warm-white rim highlight
        pv_dx = np.abs(np.diff(pv, axis=1, prepend=pv[:, :1]))
        pv_dy = np.abs(np.diff(pv, axis=0, prepend=pv[:1, :]))
        edge = np.clip(np.sqrt(pv_dx**2 + pv_dy**2) * 6, 0, 1)
        rim = edge * 0.18 * pm
        result[:,:,0] = np.clip(result[:,:,0] + rim * mask * 1.05, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + rim * mask * 1.00, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + rim * mask * 0.85, 0, 1)

        result = np.clip(result + bb * 0.3 * mask[:,:,np.newaxis], 0, 1)
        return result
    return spec_fn, paint_fn

spec_spectral_rainbow_metal, paint_spectral_rainbow_metal = _make_spectral_fusion("rainbow", (0, 255), (2, 200), 16, 8300)
spec_spectral_warm_cool, paint_spectral_warm_cool = _make_spectral_fusion("binary", (0, 255), (5, 180), 16, 8310)
spec_spectral_dark_light, paint_spectral_dark_light = _make_spectral_fusion("value", (20, 240), (5, 150), 16, 8320)
spec_spectral_sat_metal, paint_spectral_sat_metal = _make_spectral_fusion("saturation", (40, 230), (20, 60), 16, 8330)
spec_spectral_complementary, paint_spectral_complementary = _make_spectral_fusion("binary", (30, 220), (10, 120), 16, 8340)
spec_spectral_neon_reactive, paint_spectral_neon_reactive = _make_spectral_fusion("gradient", (50, 255), (2, 100), 16, 8350)  # LAZY-FUSIONS-008 FIX: was "value" (3rd dup)
spec_spectral_earth_sky, paint_spectral_earth_sky = _make_spectral_fusion("rainbow", (30, 200), (20, 140), 16, 8360)
spec_spectral_mono_chrome, paint_spectral_mono_chrome = _make_spectral_fusion("threshold", (0, 255), (2, 180), 16, 8370)  # LAZY-FUSIONS-008 FIX: was "value" (2nd dup)
spec_spectral_prismatic_flip, paint_spectral_prismatic_flip = _make_spectral_fusion("tri", (0, 255), (5, 180), 16, 8380)
spec_spectral_inverse_logic, paint_spectral_inverse_logic = _make_spectral_fusion("inverted", (0, 255), (2, 200), 16, 8390)


def _sr_fields(shape, seed, mode):
    x, y = _lw_xy(shape)
    phase = (int(seed) % 8192) * 0.000767 * np.pi * 2.0
    tw = np.float32(np.pi * 2.0)
    film = x * 0.68 + y * 0.42 + np.sin((x * 2.4 - y * 1.7) * tw + phase) * 0.065
    ripple = np.sin((x * 9.0 + y * 5.0) * tw + phase) * 0.5 + 0.5
    prism = np.sin((x * 17.0 - y * 13.0) * tw + phase * 0.6) * 0.5 + 0.5

    if mode == "rainbow_metal":
        hue = np.mod(film * 1.45 + np.sin(y * tw * 3.0) * 0.08, 1.0)
        band = _lw_ridge(np.sin((film * 9.0) * tw + phase), 1.45)
    elif mode == "warm_cool":
        split = np.sin((x * 5.2 - y * 4.4) * tw + phase)
        hue = np.where(split > 0, 0.06 + ripple * 0.06, 0.56 + prism * 0.10)
        band = _lw_ridge(split, 1.65)
    elif mode == "dark_light":
        d = np.sqrt((x - 0.56) ** 2 + (y - 0.44) ** 2)
        hue = np.mod(0.62 + d * 1.25 + ripple * 0.10, 1.0)
        band = _lw_ridge(np.cos(d * tw * 14.0 + phase), 1.6)
    elif mode == "sat_metal":
        d = np.sqrt((x - 0.34) ** 2 + (y - 0.58) ** 2)
        theta = np.arctan2(y - 0.58, x - 0.34)
        bloom = np.sin(theta * 9.0 + d * tw * 13.0 + phase)
        hue = np.mod(0.74 + bloom * 0.10 + ripple * 0.04, 1.0)
        band = np.clip((bloom * 0.5 + 0.5) * 0.72 + prism * 0.28, 0, 1)
    elif mode == "complementary":
        d1 = np.sqrt((x - 0.25) ** 2 + (y - 0.28) ** 2)
        d2 = np.sqrt((x - 0.76) ** 2 + (y - 0.70) ** 2)
        theta = np.arctan2(y - 0.50, x - 0.50)
        gate = np.sin((d1 - d2) * tw * 7.5 + theta * 3.0 + phase)
        hue = np.where(gate > 0, 0.56 + ripple * 0.05, 0.04 + prism * 0.06)
        band = _lw_ridge(gate, 1.55)
    elif mode == "neon_reactive":
        d1 = np.sqrt((x - 0.22) ** 2 + (y - 0.30) ** 2)
        d2 = np.sqrt((x - 0.78) ** 2 + (y - 0.72) ** 2)
        glow = np.sin((d1 * 14.0 - d2 * 10.0) * tw + phase)
        hue = np.mod(0.78 + glow * 0.14 + film * 0.25, 1.0)
        band = np.clip((glow * 0.5 + 0.5) ** 2.0, 0, 1)
    elif mode == "earth_sky":
        ridge = np.sin((y * 6.2 + np.sin(x * tw * 2.3) * 0.18) * tw + phase)
        hue = np.where(ridge > 0.05, 0.58 + ripple * 0.08, 0.10 + prism * 0.06)
        band = _lw_ridge(ridge, 1.55)
    elif mode == "mono_chrome":
        stripe = np.sin((x * 8.0 + y * 3.0) * tw + phase)
        hue = np.zeros_like(stripe) + 0.58
        band = np.clip(stripe * 0.5 + 0.5, 0, 1)
    elif mode == "prismatic_flip":
        a = np.sin((x * 7.0 + y * 2.0) * tw + phase)
        b = np.sin((-x * 3.0 + y * 8.4) * tw - phase * 0.7)
        hue = np.mod(0.48 + a * 0.18 + b * 0.14, 1.0)
        band = _lw_ridge(a - b, 1.25)
    elif mode == "inverse_logic":
        local_warp = np.sin((x * 3.0 + y * 2.0) * tw + phase) * 0.09
        cells = np.floor(x * 11.0 + local_warp * 8.0) * 17.0 + np.floor(y * 7.0 - local_warp * 5.0) * 29.0
        logic_hash = np.sin(cells * 12.9898 + phase) * 43758.5453
        logic_hash = logic_hash - np.floor(logic_hash)
        slash = np.sin((x * 8.0 - y * 3.0) * tw + phase)
        logic = (logic_hash * 0.66 + (slash * 0.5 + 0.5) * 0.34)
        hue = np.where(logic > 0.52, 0.50 + ripple * 0.10, 0.91 + prism * 0.08)
        band = np.clip(np.abs(logic - 0.52) * 2.8, 0, 1)
    else:
        hue = np.mod(film + ripple * 0.1, 1.0)
        band = ripple

    micro = _lw_hash(shape, seed, 1777 + len(mode)) * 0.52 + (np.sin((x * 39.0 + y * 33.0) * tw + phase) * 0.5 + 0.5) * 0.48
    edge = np.clip(
        np.abs(np.diff(band, axis=1, prepend=band[:, :1])) + np.abs(np.diff(band, axis=0, prepend=band[:1, :])),
        0,
        1,
    )
    glint = np.clip((micro - 0.62) * 3.7 + band * 0.55 + edge * 0.78, 0, 1)
    return hue.astype(np.float32), band.astype(np.float32), micro.astype(np.float32), glint.astype(np.float32), edge.astype(np.float32)


def _make_spectral_reactive_fast(mode, sat, val, m_low, m_high, rough_low, rough_high, clearcoat, seed_offset=0):
    def spec_fn(shape, mask, seed, sm):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        hue, band, micro, glint, edge = _sr_fields(shape, int(seed) + seed_offset, mode)
        smf = float(sm)
        M_var = np.clip(hue * 0.4 + band * 0.4 + glint * 0.2, 0.0, 1.0)
        G_var = np.clip((1.0 - band) * 0.4 + (1.0 - glint) * 0.4 + micro * 0.2, 0.0, 1.0)
        CC_var = np.clip(band * 0.3 + glint * 0.5 + edge * 0.2, 0.0, 1.0)
        M_base = ((float(m_low) + float(m_high)) / 2.0) / 255.0
        G_base = ((float(rough_low) + float(rough_high)) / 2.0) / 255.0
        B_base = float(clearcoat) / 255.0
        M = 15.0 + 240.0 * np.clip(M_var * smf + (1.0 - smf) * M_base, 0.0, 1.0)
        G = 15.0 + 240.0 * np.clip(G_var * smf + (1.0 - smf) * G_base, 0.0, 1.0)
        B = 16.0 + 239.0 * np.clip(CC_var * smf + (1.0 - smf) * B_base, 0.0, 1.0)
        return _spec_out(shape, mask2, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        mask2 = np.asarray(mask, dtype=np.float32)
        if mask2.ndim == 3:
            mask2 = mask2[:, :, 0]
        bb_arr = np.asarray(bb, dtype=np.float32)
        if bb_arr.ndim == 2:
            bb_arr = bb_arr[:, :, np.newaxis]
        if paint.ndim == 3 and paint.shape[2] > 3:
            base = paint[:, :, :3].astype(np.float32, copy=True)
        else:
            base = paint.astype(np.float32, copy=True)
        hue, band, micro, glint, edge = _sr_fields(shape, int(seed) + seed_offset, mode)
        r, g, b = _hsv_to_rgb(hue, np.clip(float(sat) + glint * 0.18, 0, 1), np.clip(float(val) + band * 0.16 + glint * 0.18, 0, 1))
        color = np.stack([r, g, b], axis=2).astype(np.float32)
        luma = ((micro - 0.5) * 0.10 + glint * 0.15 + edge * 0.10)[:, :, np.newaxis]
        target = np.clip(color + luma, 0, 1)
        blend = np.clip((0.70 + band * 0.14 + glint * 0.12) * float(pm), 0.0, 0.94)[:, :, np.newaxis] * mask2[:, :, np.newaxis]
        result = base * (1.0 - blend) + target * blend
        result = np.clip(result + bb_arr * 0.20 * mask2[:, :, np.newaxis], 0, 1)
        return result.astype(np.float32)

    return spec_fn, paint_fn


spec_spectral_rainbow_metal, paint_spectral_rainbow_metal = _make_spectral_reactive_fast("rainbow_metal", 0.94, 0.86, 22, 255, 18, 168, 104, 9500)
spec_spectral_warm_cool, paint_spectral_warm_cool = _make_spectral_reactive_fast("warm_cool", 0.92, 0.84, 24, 240, 20, 154, 98, 9510)
spec_spectral_dark_light, paint_spectral_dark_light = _make_spectral_reactive_fast("dark_light", 0.58, 0.72, 34, 235, 22, 146, 96, 9520)
spec_spectral_sat_metal, paint_spectral_sat_metal = _make_spectral_reactive_fast("sat_metal", 0.86, 0.82, 56, 230, 28, 138, 92, 9530)
spec_spectral_complementary, paint_spectral_complementary = _make_spectral_reactive_fast("complementary", 0.96, 0.84, 30, 232, 22, 142, 102, 9540)
spec_spectral_neon_reactive, paint_spectral_neon_reactive = _make_spectral_reactive_fast("neon_reactive", 1.00, 0.92, 48, 255, 12, 118, 118, 9550)
spec_spectral_earth_sky, paint_spectral_earth_sky = _make_spectral_reactive_fast("earth_sky", 0.84, 0.78, 36, 214, 32, 150, 92, 9560)
spec_spectral_mono_chrome, paint_spectral_mono_chrome = _make_spectral_reactive_fast("mono_chrome", 0.18, 0.82, 18, 255, 14, 162, 100, 9570)
spec_spectral_prismatic_flip, paint_spectral_prismatic_flip = _make_spectral_reactive_fast("prismatic_flip", 0.98, 0.90, 20, 255, 14, 154, 122, 9580)
spec_spectral_inverse_logic, paint_spectral_inverse_logic = _make_spectral_reactive_fast("inverse_logic", 0.95, 0.84, 12, 250, 16, 166, 106, 9590)


# ================================================================
# PARADIGM 15: MICRO-PANEL QUILTING - Material mosaic
# ================================================================

@lru_cache(maxsize=24)
def _quilt_voronoi_cached(h, w, panel_size, seed, seed_offset):
    rng = np.random.RandomState(seed + seed_offset)
    n_pts = max(20, (h * w) // (panel_size * panel_size))
    pts = np.column_stack([
        rng.randint(0, h, n_pts).astype(np.float32),
        rng.randint(0, w, n_pts).astype(np.float32)
    ])
    yy, xx = np.mgrid[0:h, 0:w]
    grid = np.column_stack([yy.ravel().astype(np.float32), xx.ravel().astype(np.float32)])
    tree = cKDTree(pts)
    d, idx = tree.query(grid, k=2, workers=-1)
    closest = idx[:, 0].reshape(h, w)
    min_d = d[:, 0].reshape(h, w).astype(np.float32)
    second_d = d[:, 1].reshape(h, w).astype(np.float32)
    return closest, min_d, second_d, n_pts


def _quilt_voronoi(shape, panel_size, seed, seed_offset):
    """Voronoi cell tessellation for quilting panels via cKDTree (fast).
    Returns (panel_id_map, min_dist, second_dist, n_pts) for grout line detection.

    SPB perf 2026-06-13 (fusions.py lane): the full-resolution cKDTree query is
    identical between the paired spec_fn and paint_fn (same shape/seed/offset),
    so memoize it — the second of the pair becomes free. Bit-identical: returns
    the exact same arrays (callers only read/index them, never mutate)."""
    h, w = shape[:2]
    return _quilt_voronoi_cached(int(h), int(w), int(panel_size), int(seed), int(seed_offset))


def _make_quilt_fusion(panel_size, m_range, g_range, base_cc, seed_offset=0):
    """Factory: Voronoi-cell quilting with per-panel random material assignment
    and chrome grout lines at cell boundaries."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_quilt_fusion(panel_size, m_range, g_range, base_cc, seed_offset))
    _PALETTE_SIZE = 64

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        closest, min_d, second_d, n_pts = _quilt_voronoi(shape, panel_size, seed, seed_offset)

        rng_mat = np.random.RandomState(seed + seed_offset + 33)
        panel_M_vals = rng_mat.randint(m_range[0], m_range[1] + 1, n_pts).astype(np.float32)
        panel_G_vals = rng_mat.randint(g_range[0], g_range[1] + 1, n_pts).astype(np.float32)
        rng_cc = np.random.RandomState(seed + seed_offset + 77)
        panel_CC_vals = rng_cc.randint(max(16, int(base_cc) - 20), min(255, int(base_cc) + 40) + 1, n_pts).astype(np.float32)

        M = panel_M_vals[closest]
        G = panel_G_vals[closest]
        B = panel_CC_vals[closest]

        grout_width = max(2.0, panel_size * 0.06)
        grout = np.clip(1.0 - (second_d - min_d) / grout_width, 0, 1)
        grout = grout ** 1.5

        M = M * (1 - grout) + 255.0 * grout * sm + M * grout * (1 - sm)
        G = G * (1 - grout) + 2.0 * grout * sm + G * grout * (1 - sm)
        B = B * (1 - grout) + 16.0 * grout * sm + B * grout * (1 - sm)

        n_fine = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 50)
        M = M + n_fine * 10 * sm * (1 - grout)
        G = G + np.abs(n_fine) * 8 * sm * (1 - grout)

        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape[:2]
        closest, min_d, second_d, n_pts = _quilt_voronoi(shape, panel_size, seed, seed_offset)

        rng_tint = np.random.RandomState(seed + seed_offset + 999)
        tints = rng_tint.uniform(-0.14, 0.14, (_PALETTE_SIZE, 3)).astype(np.float32)
        idx = (closest % _PALETTE_SIZE)
        panel_tint = tints[idx, :]

        grout_width = max(2.0, panel_size * 0.06)
        grout = np.clip(1.0 - (second_d - min_d) / grout_width, 0, 1) ** 1.5

        # 2026-05-15 (SPB-80): Quilt paint was flat per panel + thin grout = low
        # paintFineEnergy at 2048 car-body scale (M6 = 0 for all 10 Panel
        # Quilting finishes). Real quilted fabric has visible WEAVE GRAIN inside
        # each cell. Add a multi-octave fine-grain field (octaves 256+512+1024
        # of the canvas, attenuated inside grout corridors so we don't smear the
        # cell boundaries). This raises paintFineEnergy substantially without
        # changing the cell-tint character that defines the quilt look.
        try:
            n_fine_grain = (
                _noise(shape, [256, 512, 1024], [0.45, 0.35, 0.20], seed + seed_offset + 707)
            )
        except Exception:
            # Fallback: simple per-pixel noise if multi-band helper struggles
            # at very-high octave bands. Still beats flat.
            _rng = np.random.RandomState(seed + seed_offset + 707)
            n_fine_grain = (_rng.random((h, w)).astype(np.float32) - 0.5) * 2.0
        grain_amplitude = 0.045  # ~4.5% lightness perturbation = visible weave at car scale
        grain = n_fine_grain * grain_amplitude * pm * mask * (1 - grout)

        out = np.zeros((h, w, 4), dtype=np.float32)
        out[:, :, :3] = np.clip(
            paint[:, :, :3]
            + panel_tint * pm * mask[:, :, np.newaxis] * (1 - grout[:, :, np.newaxis])
            + grain[:, :, np.newaxis],
            0, 1,
        )
        out[:, :, 3] = paint[:, :, 3] if paint.shape[2] > 3 else 1.0

        grout_bright = grout * 0.20 * pm
        for c in range(3):
            out[:, :, c] = np.clip(out[:, :, c] + grout_bright * mask, 0, 1)

        out[:, :, :3] = np.clip(out[:, :, :3] + bb * 0.35 * mask[:, :, np.newaxis], 0, 1)
        return out

    return spec_fn, paint_fn

@lru_cache(maxsize=24)
def _quilt_hex_grid_cached(h, w, hex_size, seed, seed_offset):
    hex_w_step = float(hex_size)
    hex_h_step = hex_size * 1.7320508  # sqrt(3)
    n_rows = int(h / hex_h_step) + 3
    n_cols = int(w / hex_w_step) + 3
    all_y, all_x = [], []
    for r in range(-1, n_rows):
        for c in range(-1, n_cols):
            all_y.append(r * hex_h_step)
            all_x.append(c * hex_w_step + (r % 2) * hex_w_step * 0.5)
    pts_y = np.array(all_y, dtype=np.float32)
    pts_x = np.array(all_x, dtype=np.float32)
    n_pts = len(pts_y)
    rng = np.random.RandomState(seed + seed_offset)
    jitter = hex_size * 0.10
    pts_y += rng.uniform(-jitter, jitter, n_pts).astype(np.float32)
    pts_x += rng.uniform(-jitter, jitter, n_pts).astype(np.float32)
    pts = np.column_stack([pts_y, pts_x])
    yy, xx = np.mgrid[0:h, 0:w]
    grid = np.column_stack([yy.ravel().astype(np.float32), xx.ravel().astype(np.float32)])
    tree = cKDTree(pts)
    d, idx = tree.query(grid, k=2, workers=-1)
    closest = idx[:, 0].reshape(h, w)
    min_d = d[:, 0].reshape(h, w).astype(np.float32)
    second_d = d[:, 1].reshape(h, w).astype(np.float32)
    return closest, min_d, second_d, n_pts


def _quilt_hex_grid(shape, hex_size, seed, seed_offset):
    """True hexagonal cell tessellation (pointy-top) via cKDTree (fast).
    Returns (cell_id, min_dist, second_dist, n_cells) same as _quilt_voronoi.
    SPB perf 2026-06-13 (fusions.py lane): memoized — the identical paired
    spec_fn/paint_fn cKDTree query is computed once (bit-identical, read-only)."""
    h, w = shape[:2]
    return _quilt_hex_grid_cached(int(h), int(w), int(hex_size), int(seed), int(seed_offset))


def _make_quilt_hex_fusion(hex_size, m_range, g_range, base_cc, seed_offset=0):
    """Factory: true hex-cell quilting. Each Voronoi cell sits on a regular hex lattice
    (pointy-top). Cell boundaries produce distinct straight-edged grout lines — visually
    unlike random Voronoi's organic cells."""
    _PALETTE_SIZE = 64

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        closest, min_d, second_d, n_pts = _quilt_hex_grid(shape, hex_size, seed, seed_offset)
        rng_mat = np.random.RandomState(seed + seed_offset + 33)
        panel_M = rng_mat.randint(m_range[0], m_range[1] + 1, n_pts).astype(np.float32)
        panel_G = rng_mat.randint(g_range[0], g_range[1] + 1, n_pts).astype(np.float32)
        rng_cc = np.random.RandomState(seed + seed_offset + 77)
        panel_B = rng_cc.randint(max(16, int(base_cc) - 20), min(255, int(base_cc) + 40) + 1, n_pts).astype(np.float32)
        M = panel_M[closest]
        G = panel_G[closest]
        B = panel_B[closest]
        grout_w = max(2.0, hex_size * 0.06)
        grout = np.clip(1.0 - (second_d - min_d) / grout_w, 0, 1) ** 1.5
        M = M * (1 - grout) + 255.0 * grout * sm + M * grout * (1 - sm)
        G = G * (1 - grout) + 2.0 * grout * sm + G * grout * (1 - sm)
        B = B * (1 - grout) + 16.0 * grout * sm + B * grout * (1 - sm)
        n_fine = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 50)
        M = M + n_fine * 10 * sm * (1 - grout)
        G = G + np.abs(n_fine) * 8 * sm * (1 - grout)
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape[:2]
        closest, min_d, second_d, n_pts = _quilt_hex_grid(shape, hex_size, seed, seed_offset)
        rng_tint = np.random.RandomState(seed + seed_offset + 999)
        tints = rng_tint.uniform(-0.14, 0.14, (_PALETTE_SIZE, 3)).astype(np.float32)
        idx = closest % _PALETTE_SIZE
        panel_tint = tints[idx, :]
        grout_w = max(2.0, hex_size * 0.06)
        grout = np.clip(1.0 - (second_d - min_d) / grout_w, 0, 1) ** 1.5
        # SPB-80 intra-cell weave grain (octaves 256/512/1024 = 4-16px features at 2048)
        try:
            n_fine_grain = _noise(shape, [256, 512, 1024], [0.45, 0.35, 0.20], seed + seed_offset + 707)
        except Exception:
            _rng = np.random.RandomState(seed + seed_offset + 707)
            n_fine_grain = (_rng.random((h, w)).astype(np.float32) - 0.5) * 2.0
        grain = n_fine_grain * 0.045 * pm * mask * (1 - grout)
        out = np.zeros((h, w, 4), dtype=np.float32)
        out[:, :, :3] = np.clip(
            paint[:, :, :3]
            + panel_tint * pm * mask[:, :, np.newaxis] * (1 - grout[:, :, np.newaxis])
            + grain[:, :, np.newaxis],
            0, 1,
        )
        out[:, :, 3] = paint[:, :, 3] if paint.shape[2] > 3 else 1.0
        grout_bright = grout * 0.20 * pm
        for c in range(3):
            out[:, :, c] = np.clip(out[:, :, c] + grout_bright * mask, 0, 1)
        out[:, :, :3] = np.clip(out[:, :, :3] + bb * 0.35 * mask[:, :, np.newaxis], 0, 1)
        return out

    return spec_fn, paint_fn


@lru_cache(maxsize=24)
def _quilt_diamond_grid_cached(h, w, diamond_size, seed, seed_offset):
    step = float(diamond_size)
    cy_c = h * 0.5
    cx_c = w * 0.5
    half_span = int(max(h, w) / step) + 3
    all_y, all_x = [], []
    for i in range(-half_span, half_span + 1):
        for j in range(-half_span, half_span + 1):
            cy = cy_c + (i + j) * step * 0.5
            cx = cx_c + (i - j) * step * 0.5
            if -step <= cy <= h + step and -step <= cx <= w + step:
                all_y.append(cy)
                all_x.append(cx)
    pts_y = np.array(all_y, dtype=np.float32)
    pts_x = np.array(all_x, dtype=np.float32)
    n_pts = max(1, len(pts_y))
    rng = np.random.RandomState(seed + seed_offset)
    jitter = diamond_size * 0.08
    pts_y += rng.uniform(-jitter, jitter, n_pts).astype(np.float32)
    pts_x += rng.uniform(-jitter, jitter, n_pts).astype(np.float32)
    pts = np.column_stack([pts_y, pts_x])
    yy, xx = np.mgrid[0:h, 0:w]
    grid = np.column_stack([yy.ravel().astype(np.float32), xx.ravel().astype(np.float32)])
    tree = cKDTree(pts)
    d, idx = tree.query(grid, k=2, workers=-1)
    closest = idx[:, 0].reshape(h, w)
    min_d = d[:, 0].reshape(h, w).astype(np.float32)
    second_d = d[:, 1].reshape(h, w).astype(np.float32)
    return closest, min_d, second_d, n_pts


def _quilt_diamond_grid(shape, diamond_size, seed, seed_offset):
    """Diamond (rhombus) cell tessellation via cKDTree (fast). 45-rotated square lattice.
    Returns (cell_id, min_dist, second_dist, n_cells).
    SPB perf 2026-06-13 (fusions.py lane): memoized — the identical paired
    spec_fn/paint_fn cKDTree query is computed once (bit-identical, read-only)."""
    h, w = shape[:2]
    return _quilt_diamond_grid_cached(int(h), int(w), int(diamond_size), int(seed), int(seed_offset))


def _make_quilt_diamond_fusion(diamond_size, m_range, g_range, base_cc, seed_offset=0):
    """Factory: diamond/rhombus cell quilting. Centers on a 45-rotated square lattice so
    Voronoi regions are diamond-shaped — clean 45-degree grout angles vs organic Voronoi."""
    _PALETTE_SIZE = 64

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        closest, min_d, second_d, n_pts = _quilt_diamond_grid(shape, diamond_size, seed, seed_offset)
        rng_mat = np.random.RandomState(seed + seed_offset + 33)
        panel_M = rng_mat.randint(m_range[0], m_range[1] + 1, n_pts).astype(np.float32)
        panel_G = rng_mat.randint(g_range[0], g_range[1] + 1, n_pts).astype(np.float32)
        rng_cc = np.random.RandomState(seed + seed_offset + 77)
        panel_B = rng_cc.randint(max(16, int(base_cc) - 20), min(255, int(base_cc) + 40) + 1, n_pts).astype(np.float32)
        M = panel_M[closest]
        G = panel_G[closest]
        B = panel_B[closest]
        grout_w = max(2.0, diamond_size * 0.06)
        grout = np.clip(1.0 - (second_d - min_d) / grout_w, 0, 1) ** 1.5
        M = M * (1 - grout) + 255.0 * grout * sm + M * grout * (1 - sm)
        G = G * (1 - grout) + 2.0 * grout * sm + G * grout * (1 - sm)
        B = B * (1 - grout) + 16.0 * grout * sm + B * grout * (1 - sm)
        n_fine = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 50)
        M = M + n_fine * 10 * sm * (1 - grout)
        G = G + np.abs(n_fine) * 8 * sm * (1 - grout)
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        if hasattr(bb, "ndim") and bb.ndim == 2: bb = bb[:, :, np.newaxis]
        if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
        h, w = shape[:2]
        closest, min_d, second_d, n_pts = _quilt_diamond_grid(shape, diamond_size, seed, seed_offset)
        rng_tint = np.random.RandomState(seed + seed_offset + 999)
        tints = rng_tint.uniform(-0.14, 0.14, (_PALETTE_SIZE, 3)).astype(np.float32)
        idx = closest % _PALETTE_SIZE
        panel_tint = tints[idx, :]
        grout_w = max(2.0, diamond_size * 0.06)
        grout = np.clip(1.0 - (second_d - min_d) / grout_w, 0, 1) ** 1.5
        # SPB-80 intra-cell weave grain (octaves 256/512/1024 = 4-16px features at 2048)
        try:
            n_fine_grain = _noise(shape, [256, 512, 1024], [0.45, 0.35, 0.20], seed + seed_offset + 707)
        except Exception:
            _rng = np.random.RandomState(seed + seed_offset + 707)
            n_fine_grain = (_rng.random((h, w)).astype(np.float32) - 0.5) * 2.0
        grain = n_fine_grain * 0.045 * pm * mask * (1 - grout)
        out = np.zeros((h, w, 4), dtype=np.float32)
        out[:, :, :3] = np.clip(
            paint[:, :, :3]
            + panel_tint * pm * mask[:, :, np.newaxis] * (1 - grout[:, :, np.newaxis])
            + grain[:, :, np.newaxis],
            0, 1,
        )
        out[:, :, 3] = paint[:, :, 3] if paint.shape[2] > 3 else 1.0
        grout_bright = grout * 0.20 * pm
        for c in range(3):
            out[:, :, c] = np.clip(out[:, :, c] + grout_bright * mask, 0, 1)
        out[:, :, :3] = np.clip(out[:, :, :3] + bb * 0.35 * mask[:, :, np.newaxis], 0, 1)
        return out

    return spec_fn, paint_fn


# CC: 16 = full clearcoat; do not use 0 (per SPEC_MAP_REFERENCE)
spec_quilt_chrome_mosaic, paint_quilt_chrome_mosaic = _make_quilt_fusion(24, (150, 255), (2, 50), 16, 8400)
spec_quilt_candy_tiles, paint_quilt_candy_tiles = _make_quilt_fusion(32, (100, 220), (5, 40), 16, 8410)
spec_quilt_pearl_patchwork, paint_quilt_pearl_patchwork = _make_quilt_fusion(20, (60, 140), (15, 60), 16, 8420)
spec_quilt_metallic_pixels, paint_quilt_metallic_pixels = _make_quilt_fusion(16, (120, 255), (5, 80), 16, 8430)
spec_quilt_hex_variety, paint_quilt_hex_variety = _make_quilt_hex_fusion(28, (80, 240), (3, 70), 16, 8440)
spec_quilt_diamond_shimmer, paint_quilt_diamond_shimmer = _make_quilt_diamond_fusion(20, (160, 255), (2, 40), 16, 8450)
spec_quilt_random_chaos, paint_quilt_random_chaos = _make_quilt_fusion(12, (0, 255), (0, 200), 16, 8460)
spec_quilt_gradient_tiles, paint_quilt_gradient_tiles = _make_quilt_fusion(36, (100, 250), (5, 60), 16, 8470)
spec_quilt_alternating_duo, paint_quilt_alternating_duo = _make_quilt_fusion(24, (0, 255), (5, 20), 16, 8480)
spec_quilt_organic_cells, paint_quilt_organic_cells = _make_quilt_fusion(30, (80, 240), (5, 90), 16, 8490)



# ================================================================
# FUSION REGISTRY - 150 entries (15 Paradigm Shifts × 10 each)
# ================================================================

FUSION_REGISTRY = {
    # ── PARADIGM 1: Multi-Material Gradient ──
    "gradient_chrome_matte":      (spec_gradient_chrome_matte, paint_gradient_chrome_matte),
    "gradient_candy_frozen":      (spec_gradient_candy_frozen, paint_gradient_candy_frozen),
    "gradient_pearl_chrome":      (spec_gradient_pearl_chrome, paint_gradient_pearl_chrome),
    "gradient_metallic_satin":    (spec_gradient_metallic_satin, paint_gradient_metallic_satin),
    "gradient_obsidian_mirror":   (spec_gradient_obsidian_mirror, paint_gradient_obsidian_mirror),
    "gradient_candy_matte":       (spec_gradient_candy_matte, paint_gradient_candy_matte),
    "gradient_anodized_gloss":    (spec_gradient_anodized_gloss, paint_gradient_anodized_gloss),
    "gradient_ember_ice":         (spec_gradient_ember_ice, paint_gradient_ember_ice),
    "gradient_carbon_chrome":     (spec_gradient_carbon_chrome, paint_gradient_carbon_chrome),
    "gradient_spectraflame_void": (spec_gradient_spectraflame_void, paint_gradient_spectraflame_void),
    # ── PARADIGM 2: Clearcoat-Only Patterning ──
    "ghost_hex":                  (spec_ghost_hex, paint_ghost_hex),
    "ghost_stripes":              (spec_ghost_stripes, paint_ghost_stripes),
    "ghost_diamonds":             (spec_ghost_diamonds, paint_ghost_diamonds),
    "ghost_waves":                (spec_ghost_waves, paint_ghost_waves),
    "ghost_camo":                 (spec_ghost_camo, paint_ghost_camo),
    "ghost_scales":               (spec_ghost_scales, paint_ghost_scales),
    "ghost_circuit":              (spec_ghost_circuit, paint_ghost_circuit),
    "ghost_vortex":               (spec_ghost_vortex, paint_ghost_vortex),
    "ghost_fracture":             (spec_ghost_fracture, paint_ghost_fracture),
    "ghost_quilt":                (spec_ghost_quilt, paint_ghost_quilt),
    # ── PARADIGM 3: Reactive Panels ──
    "aniso_horizontal_chrome":    (spec_aniso_horizontal_chrome, paint_aniso_horizontal_chrome),
    "aniso_vertical_pearl":       (spec_aniso_vertical_pearl, paint_aniso_vertical_pearl),
    "aniso_diagonal_candy":       (spec_aniso_diagonal_candy, paint_aniso_diagonal_candy),
    "aniso_radial_metallic":      (spec_aniso_radial_metallic, paint_aniso_radial_metallic),
    "aniso_circular_chrome":      (spec_aniso_circular_chrome, paint_aniso_circular_chrome),
    "aniso_crosshatch_steel":     (spec_aniso_crosshatch_steel, paint_aniso_crosshatch_steel),
    "aniso_spiral_mercury":       (spec_aniso_spiral_mercury, paint_aniso_spiral_mercury),
    "aniso_wave_titanium":        (spec_aniso_wave_titanium, paint_aniso_wave_titanium),
    "aniso_herringbone_gold":     (spec_aniso_herringbone_gold, paint_aniso_herringbone_gold),
    "aniso_turbulence_metal":     (spec_aniso_turbulence_metal, paint_aniso_turbulence_metal),
    # ── PARADIGM 4: Reactive Metallic Zones ──
    "reactive_stealth_pop":       (spec_reactive_stealth_pop, paint_reactive_stealth_pop),
    "reactive_pearl_flash":       (spec_reactive_pearl_flash, paint_reactive_pearl_flash),
    "reactive_candy_reveal":      (spec_reactive_candy_reveal, paint_reactive_candy_reveal),
    "reactive_chrome_fade":       (spec_reactive_chrome_fade, paint_reactive_chrome_fade),
    "reactive_matte_shine":       (spec_reactive_matte_shine, paint_reactive_matte_shine),
    "reactive_dual_tone":         (spec_reactive_dual_tone, paint_reactive_dual_tone),
    "reactive_ghost_metal":       (spec_reactive_ghost_metal, paint_reactive_ghost_metal),
    "reactive_mirror_shadow":     (spec_reactive_mirror_shadow, paint_reactive_mirror_shadow),
    "reactive_warm_cold":         (spec_reactive_warm_cold, paint_reactive_warm_cold),
    "reactive_pulse_metal":       (spec_reactive_pulse_metal, paint_reactive_pulse_metal),
    # ── PARADIGM 5: Sparkle Systems ──
    "sparkle_diamond_dust":       (spec_sparkle_diamond_dust, paint_sparkle_diamond_dust),
    "sparkle_starfield":          (spec_sparkle_starfield, paint_sparkle_starfield),
    "sparkle_galaxy":             (spec_sparkle_galaxy, paint_sparkle_galaxy),
    "sparkle_firefly":            (spec_sparkle_firefly, paint_sparkle_firefly),
    "sparkle_snowfall":           (spec_sparkle_snowfall, paint_sparkle_snowfall),
    "sparkle_champagne":          (spec_sparkle_champagne, paint_sparkle_champagne),
    "sparkle_meteor":             (spec_sparkle_meteor, paint_sparkle_meteor),
    "sparkle_constellation":      (spec_sparkle_constellation, paint_sparkle_constellation),
    "sparkle_confetti":           (spec_sparkle_confetti, paint_sparkle_confetti),
    "sparkle_lightning_bug":      (spec_sparkle_lightning_bug, paint_sparkle_lightning_bug),
    # ── PARADIGM 6: Multi-Scale Texture ──
    "multiscale_chrome_grain":    (spec_multiscale_chrome_grain, paint_multiscale_chrome_grain),
    "multiscale_candy_frost":     (spec_multiscale_candy_frost, paint_multiscale_candy_frost),
    "multiscale_metal_grit":      (spec_multiscale_metal_grit, paint_multiscale_metal_grit),
    "multiscale_pearl_texture":   (spec_multiscale_pearl_texture, paint_multiscale_pearl_texture),
    "multiscale_satin_weave":     (spec_multiscale_satin_weave, paint_multiscale_satin_weave),
    "multiscale_chrome_sand":     (spec_multiscale_chrome_sand, paint_multiscale_chrome_sand),
    "multiscale_matte_silk":      (spec_multiscale_matte_silk, paint_multiscale_matte_silk),
    "multiscale_flake_grain":     (spec_multiscale_flake_grain, paint_multiscale_flake_grain),
    "multiscale_carbon_micro":    (spec_multiscale_carbon_micro, paint_multiscale_carbon_micro),
    "multiscale_frost_crystal":   (spec_multiscale_frost_crystal, paint_multiscale_frost_crystal),
    # ── PARADIGM 7: Weather and Age ──
    "weather_sun_fade":           (spec_weather_sun_fade, paint_weather_sun_fade),
    "weather_salt_spray":         (spec_weather_salt_spray, paint_weather_salt_spray),
    "weather_acid_rain":          (spec_weather_acid_rain, paint_weather_acid_rain),
    "weather_desert_blast":       (spec_weather_desert_blast, paint_weather_desert_blast),
    "weather_ice_storm":          (spec_weather_ice_storm, paint_weather_ice_storm),
    "weather_road_spray":         (spec_weather_road_spray, paint_weather_road_spray),
    "weather_hood_bake":          (spec_weather_hood_bake, paint_weather_hood_bake),
    "weather_barn_dust":          (spec_weather_barn_dust, paint_weather_barn_dust),
    "weather_ocean_mist":         (spec_weather_ocean_mist, paint_weather_ocean_mist),
    "weather_volcanic_ash":       (spec_weather_volcanic_ash, paint_weather_volcanic_ash),
    # ── PARADIGM 8: Exotic Physics ──
    "exotic_glass_paint":     (spec_exotic_glass_paint, paint_exotic_glass_paint),
    "exotic_foggy_chrome":    (spec_exotic_foggy_chrome, paint_exotic_foggy_chrome),
    "exotic_inverted_candy":  (spec_exotic_inverted_candy, paint_exotic_inverted_candy),
    "exotic_liquid_glass":    (spec_exotic_liquid_glass, paint_exotic_liquid_glass),
    "exotic_phantom_mirror":  (spec_exotic_phantom_mirror, paint_exotic_phantom_mirror),
    "exotic_ceramic_void":    (spec_exotic_ceramic_void, paint_exotic_ceramic_void),
    "exotic_anti_metal":      (spec_exotic_anti_metal, paint_exotic_anti_metal),
    "exotic_crystal_clear":   (spec_exotic_crystal_clear, paint_exotic_crystal_clear),
    "exotic_dark_glass":      (spec_exotic_dark_glass, paint_exotic_dark_glass),
    "exotic_wet_void":        (spec_exotic_wet_void, paint_exotic_wet_void),
    # ── PARADIGM 9: Tri-Zone Material Fencing ──
    "trizone_chrome_candy_matte":     (spec_trizone_chrome_candy_matte, paint_trizone_chrome_candy_matte),
    "trizone_pearl_carbon_gold":      (spec_trizone_pearl_carbon_gold, paint_trizone_pearl_carbon_gold),
    "trizone_frozen_ember_chrome":    (spec_trizone_frozen_ember_chrome, paint_trizone_frozen_ember_chrome),
    "trizone_anodized_candy_silk":    (spec_trizone_anodized_candy_silk, paint_trizone_anodized_candy_silk),
    "trizone_vanta_chrome_pearl":     (spec_trizone_vanta_chrome_pearl, paint_trizone_vanta_chrome_pearl),
    "trizone_glass_metal_matte":      (spec_trizone_glass_metal_matte, paint_trizone_glass_metal_matte),
    "trizone_mercury_obsidian_candy": (spec_trizone_mercury_obsidian_candy, paint_trizone_mercury_obsidian_candy),
    "trizone_titanium_copper_chrome": (spec_trizone_titanium_copper_chrome, paint_trizone_titanium_copper_chrome),
    "trizone_ceramic_flake_satin":    (spec_trizone_ceramic_flake_satin, paint_trizone_ceramic_flake_satin),
    "trizone_stealth_spectra_frozen": (spec_trizone_stealth_spectra_frozen, paint_trizone_stealth_spectra_frozen),
    # ── PARADIGM 10: Depth Illusion ──
    "depth_canyon":               (spec_depth_canyon, paint_depth_canyon),
    "depth_bubble":               (spec_depth_bubble, paint_depth_bubble),
    "depth_map":                  (spec_depth_map, paint_depth_map),
    "depth_ripple":               (spec_depth_ripple, paint_depth_ripple),
    "depth_scale":                (spec_depth_scale, paint_depth_scale),
    "depth_honeycomb":            (spec_depth_honeycomb, paint_depth_honeycomb),
    "depth_crack":                (spec_depth_crack, paint_depth_crack),
    "depth_wave":                 (spec_depth_wave, paint_depth_wave),
    "depth_pillow":               (spec_depth_pillow, paint_depth_pillow),
    "depth_vortex":               (spec_depth_vortex, paint_depth_vortex),
    "depth_erosion":              (spec_depth_erosion, paint_depth_erosion),
    # ── PARADIGM 11: Metallic Halo Effect ──
    "halo_hex_chrome":            (spec_halo_hex_chrome, paint_halo_hex_chrome),
    "halo_scale_gold":            (spec_halo_scale_gold, paint_halo_scale_gold),
    "halo_circle_pearl":          (spec_halo_circle_pearl, paint_halo_circle_pearl),
    "halo_diamond_chrome":        (spec_halo_diamond_chrome, paint_halo_diamond_chrome),
    "halo_voronoi_metal":         (spec_halo_voronoi_metal, paint_halo_voronoi_metal),
    "halo_wave_candy":            (spec_halo_wave_candy, paint_halo_wave_candy),
    "halo_crack_chrome":          (spec_halo_crack_chrome, paint_halo_crack_chrome),
    "halo_star_metal":            (spec_halo_star_metal, paint_halo_star_metal),
    "halo_grid_pearl":            (spec_halo_grid_pearl, paint_halo_grid_pearl),
    "halo_ripple_chrome":         (spec_halo_ripple_chrome, paint_halo_ripple_chrome),
    # ── PARADIGM 12: Dynamic Roughness Waves ──
    "wave_chrome_tide":           (spec_wave_chrome_tide, paint_wave_chrome_tide),
    "wave_candy_flow":            (spec_wave_candy_flow, paint_wave_candy_flow),
    "wave_pearl_current":         (spec_wave_pearl_current, paint_wave_pearl_current),
    "wave_metallic_pulse":        (spec_wave_metallic_pulse, paint_wave_metallic_pulse),
    "wave_dual_frequency":        (spec_wave_dual_frequency, paint_wave_dual_frequency),
    "wave_diagonal_sweep":        (spec_wave_diagonal_sweep, paint_wave_diagonal_sweep),
    "wave_circular_radar":        (spec_wave_circular_radar, paint_wave_circular_radar),
    "wave_turbulent_flow":        (spec_wave_turbulent_flow, paint_wave_turbulent_flow),
    "wave_standing_chrome":       (spec_wave_standing_chrome, paint_wave_standing_chrome),
    "wave_moire_metal":           (spec_wave_moire_metal, paint_wave_moire_metal),
    # ── PARADIGM 13: Fractal Material Mixing ──
    "fractal_chrome_decay":       (spec_fractal_chrome_decay, paint_fractal_chrome_decay),
    "fractal_candy_chaos":        (spec_fractal_candy_chaos, paint_fractal_candy_chaos),
    "fractal_pearl_cloud":        (spec_fractal_pearl_cloud, paint_fractal_pearl_cloud),
    "fractal_metallic_storm":     (spec_fractal_metallic_storm, paint_fractal_metallic_storm),
    "fractal_matte_chrome":       (spec_fractal_matte_chrome, paint_fractal_matte_chrome),
    "fractal_warm_cold":          (spec_fractal_warm_cold, paint_fractal_warm_cold),
    "fractal_deep_organic":       (spec_fractal_deep_organic, paint_fractal_deep_organic),
    "fractal_electric_noise":     (spec_fractal_electric_noise, paint_fractal_electric_noise),
    "fractal_cosmic_dust":        (spec_fractal_cosmic_dust, paint_fractal_cosmic_dust),
    "fractal_liquid_fire":        (spec_fractal_liquid_fire, paint_fractal_liquid_fire),
    # ── PARADIGM 14: Spectral Gradient Material ──
    "spectral_rainbow_metal":     (spec_spectral_rainbow_metal, paint_spectral_rainbow_metal),
    "spectral_warm_cool":         (spec_spectral_warm_cool, paint_spectral_warm_cool),
    "spectral_dark_light":        (spec_spectral_dark_light, paint_spectral_dark_light),
    "spectral_sat_metal":         (spec_spectral_sat_metal, paint_spectral_sat_metal),
    "spectral_complementary":     (spec_spectral_complementary, paint_spectral_complementary),
    "spectral_neon_reactive":     (spec_spectral_neon_reactive, paint_spectral_neon_reactive),
    "spectral_earth_sky":         (spec_spectral_earth_sky, paint_spectral_earth_sky),
    "spectral_mono_chrome":       (spec_spectral_mono_chrome, paint_spectral_mono_chrome),
    "spectral_prismatic_flip":    (spec_spectral_prismatic_flip, paint_spectral_prismatic_flip),
    "spectral_inverse_logic":     (spec_spectral_inverse_logic, paint_spectral_inverse_logic),
    # ── PARADIGM 15: Micro-Panel Quilting ──
    "quilt_chrome_mosaic":        (spec_quilt_chrome_mosaic, paint_quilt_chrome_mosaic),
    "quilt_candy_tiles":          (spec_quilt_candy_tiles, paint_quilt_candy_tiles),
    "quilt_pearl_patchwork":      (spec_quilt_pearl_patchwork, paint_quilt_pearl_patchwork),
    "quilt_metallic_pixels":      (spec_quilt_metallic_pixels, paint_quilt_metallic_pixels),
    "quilt_hex_variety":          (spec_quilt_hex_variety, paint_quilt_hex_variety),
    "quilt_diamond_shimmer":      (spec_quilt_diamond_shimmer, paint_quilt_diamond_shimmer),
    "quilt_random_chaos":         (spec_quilt_random_chaos, paint_quilt_random_chaos),
    "quilt_gradient_tiles":       (spec_quilt_gradient_tiles, paint_quilt_gradient_tiles),
    "quilt_alternating_duo":      (spec_quilt_alternating_duo, paint_quilt_alternating_duo),
    "quilt_organic_cells":        (spec_quilt_organic_cells, paint_quilt_organic_cells),
    # ── PARADIGM 11: ★ SPECTRUM SHIFT (SPB-102 procedural iridescent) ──
    # Generated via engine.paint_v2.spectrum_shift._make_spectrum_shift_finish.
    # 50 finishes = 10 palettes × 5 variants. Built incrementally via overnight
    # cron; this block populates dynamically below.
}

# ────────────────────────────────────────────────────────────────────────
# SPB-102 Spectrum Shift registrations. Built incrementally by overnight
# loop. Each tick appends 5 finishes to FUSION_REGISTRY at module load.
# ────────────────────────────────────────────────────────────────────────
try:
    from engine.paint_v2.spectrum_shift import _make_spectrum_shift_finish as _mk_spectrum
    _SPECTRUM_SHIFT_ENABLED = (
        # Tick 0 batch: oil_slick × 5 variants. Loop will extend this list.
        ("oil_slick", "classic", 9500),
        ("oil_slick", "macro",   9501),
        ("oil_slick", "micro",   9502),
        ("oil_slick", "shimmer", 9503),
        ("oil_slick", "wave",    9504),
        # Tick 1 batch: aurora × 5 variants.
        ("aurora",    "classic", 9505),
        ("aurora",    "macro",   9506),
        ("aurora",    "micro",   9507),
        ("aurora",    "shimmer", 9508),
        ("aurora",    "wave",    9509),
        # Tick 2 batch: sunset × 5 variants.
        ("sunset",    "classic", 9510),
        ("sunset",    "macro",   9511),
        ("sunset",    "micro",   9512),
        ("sunset",    "shimmer", 9513),
        ("sunset",    "wave",    9514),
        # Tick 3 batch: vapor × 5 variants.
        ("vapor",     "classic", 9515),
        ("vapor",     "macro",   9516),
        ("vapor",     "micro",   9517),
        ("vapor",     "shimmer", 9518),
        ("vapor",     "wave",    9519),
        # Tick 4 batch: holographic × 5 variants.
        ("holographic", "classic", 9520),
        ("holographic", "macro",   9521),
        ("holographic", "micro",   9522),
        ("holographic", "shimmer", 9523),
        ("holographic", "wave",    9524),
        # Tick 5 batch: goldsmith × 5 variants.
        ("goldsmith", "classic", 9525),
        ("goldsmith", "macro",   9526),
        ("goldsmith", "micro",   9527),
        ("goldsmith", "shimmer", 9528),
        ("goldsmith", "wave",    9529),
        # Tick 6 batch: phantom × 5 variants.
        ("phantom",   "classic", 9530),
        ("phantom",   "macro",   9531),
        ("phantom",   "micro",   9532),
        ("phantom",   "shimmer", 9533),
        ("phantom",   "wave",    9534),
        # Tick 7 batch: inferno × 5 variants.
        ("inferno",   "classic", 9535),
        ("inferno",   "macro",   9536),
        ("inferno",   "micro",   9537),
        ("inferno",   "shimmer", 9538),
        ("inferno",   "wave",    9539),
        # Tick 8 batch: mirage × 5 variants.
        ("mirage",    "classic", 9540),
        ("mirage",    "macro",   9541),
        ("mirage",    "micro",   9542),
        ("mirage",    "shimmer", 9543),
        ("mirage",    "wave",    9544),
        # Tick 9 batch: reptile × 5 variants (final).
        ("reptile",   "classic", 9545),
        ("reptile",   "macro",   9546),
        ("reptile",   "micro",   9547),
        ("reptile",   "shimmer", 9548),
        ("reptile",   "wave",    9549),
    )
    for _pal, _var, _seed in _SPECTRUM_SHIFT_ENABLED:
        _spec, _paint = _mk_spectrum(_pal, _var, _seed)
        FUSION_REGISTRY[f"spectrum_{_pal}_{_var}"] = (_spec, _paint)
except Exception as _spectrum_import_err:
    import logging
    logging.warning(f"[spectrum_shift] registration skipped: {_spectrum_import_err}")


def _fd(bias, spec_gain, paint_gain, sparkle_floor, edge_gain, coverage, cool, warm):
    return {
        "bias": int(bias),
        "spec_gain": float(spec_gain),
        "paint_gain": float(paint_gain),
        "sparkle_floor": float(sparkle_floor),
        "edge_gain": float(edge_gain),
        "coverage": float(coverage),
        "cool": tuple(float(v) for v in cool),
        "warm": tuple(float(v) for v in warm),
    }


# Explicit per-finish rebuild profiles for the shipping Fusion Lab families.
# The base renderer supplies the large-form identity; these profiles supply
# 2048-aware micro topology, density, and color/spec response per finish.
_FUSION_DETAIL_PROFILES = {
    # Material Gradients
    "gradient_anodized_gloss": _fd(101, 1.20, 0.145, 0.660, 0.22, 0.58, (0.24, 0.46, 0.72), (0.88, 0.48, 0.22)),
    "gradient_candy_frozen": _fd(113, 1.12, 0.135, 0.690, 0.18, 0.50, (0.42, 0.66, 0.92), (0.90, 0.22, 0.42)),
    "gradient_candy_matte": _fd(127, 1.03, 0.118, 0.735, 0.14, 0.42, (0.30, 0.22, 0.18), (0.86, 0.26, 0.18)),
    "gradient_carbon_chrome": _fd(139, 1.42, 0.105, 0.705, 0.26, 0.56, (0.10, 0.14, 0.18), (0.72, 0.80, 0.86)),
    "gradient_chrome_matte": _fd(151, 1.36, 0.110, 0.720, 0.24, 0.48, (0.26, 0.30, 0.34), (0.86, 0.88, 0.84)),
    "gradient_ember_ice": _fd(163, 1.28, 0.155, 0.650, 0.20, 0.62, (0.20, 0.58, 0.94), (1.00, 0.30, 0.08)),
    "gradient_metallic_satin": _fd(179, 1.24, 0.115, 0.710, 0.18, 0.52, (0.44, 0.46, 0.48), (0.78, 0.65, 0.48)),
    "gradient_obsidian_mirror": _fd(191, 1.52, 0.125, 0.675, 0.30, 0.58, (0.04, 0.05, 0.08), (0.64, 0.72, 0.92)),
    "gradient_pearl_chrome": _fd(207, 1.34, 0.135, 0.670, 0.20, 0.60, (0.54, 0.64, 0.82), (0.92, 0.78, 0.96)),
    "gradient_spectraflame_void": _fd(223, 1.48, 0.160, 0.640, 0.28, 0.66, (0.02, 0.04, 0.10), (0.95, 0.18, 0.72)),
    # Directional Grain
    "aniso_circular_chrome": _fd(307, 1.42, 0.104, 0.700, 0.32, 0.54, (0.38, 0.42, 0.48), (0.82, 0.86, 0.90)),
    "aniso_crosshatch_steel": _fd(313, 1.34, 0.098, 0.730, 0.36, 0.48, (0.30, 0.34, 0.38), (0.74, 0.76, 0.72)),
    "aniso_diagonal_candy": _fd(331, 1.16, 0.132, 0.690, 0.24, 0.56, (0.16, 0.28, 0.54), (0.92, 0.22, 0.36)),
    "aniso_herringbone_gold": _fd(347, 1.30, 0.125, 0.700, 0.34, 0.54, (0.38, 0.28, 0.12), (0.96, 0.72, 0.18)),
    "aniso_horizontal_chrome": _fd(359, 1.38, 0.098, 0.735, 0.28, 0.46, (0.34, 0.38, 0.44), (0.86, 0.88, 0.86)),
    "aniso_radial_metallic": _fd(373, 1.35, 0.112, 0.705, 0.30, 0.54, (0.30, 0.36, 0.44), (0.88, 0.62, 0.38)),
    "aniso_spiral_mercury": _fd(389, 1.50, 0.118, 0.675, 0.38, 0.60, (0.22, 0.34, 0.48), (0.86, 0.92, 0.95)),
    "aniso_turbulence_metal": _fd(401, 1.32, 0.120, 0.665, 0.30, 0.64, (0.20, 0.25, 0.30), (0.88, 0.64, 0.42)),
    "aniso_vertical_pearl": _fd(419, 1.20, 0.125, 0.700, 0.24, 0.52, (0.48, 0.58, 0.82), (0.94, 0.82, 0.98)),
    "aniso_wave_titanium": _fd(431, 1.30, 0.112, 0.690, 0.30, 0.56, (0.32, 0.42, 0.56), (0.86, 0.70, 0.52)),
    # Reactive Panels
    "reactive_candy_reveal": _fd(503, 1.22, 0.150, 0.660, 0.24, 0.60, (0.12, 0.20, 0.44), (0.96, 0.20, 0.28)),
    "reactive_chrome_fade": _fd(521, 1.42, 0.112, 0.700, 0.26, 0.52, (0.32, 0.36, 0.42), (0.84, 0.88, 0.90)),
    "reactive_dual_tone": _fd(541, 1.26, 0.146, 0.650, 0.22, 0.62, (0.05, 0.28, 0.70), (0.92, 0.36, 0.08)),
    "reactive_ghost_metal": _fd(557, 1.18, 0.118, 0.735, 0.20, 0.44, (0.22, 0.28, 0.34), (0.78, 0.82, 0.80)),
    "reactive_matte_shine": _fd(571, 1.30, 0.110, 0.725, 0.28, 0.48, (0.16, 0.16, 0.15), (0.88, 0.82, 0.70)),
    "reactive_mirror_shadow": _fd(587, 1.55, 0.105, 0.675, 0.34, 0.56, (0.02, 0.03, 0.06), (0.78, 0.84, 0.92)),
    "reactive_pearl_flash": _fd(601, 1.24, 0.140, 0.645, 0.20, 0.64, (0.50, 0.62, 0.86), (0.98, 0.74, 0.94)),
    "reactive_pulse_metal": _fd(617, 1.36, 0.125, 0.680, 0.30, 0.58, (0.20, 0.32, 0.46), (0.96, 0.50, 0.20)),
    "reactive_stealth_pop": _fd(631, 1.34, 0.132, 0.690, 0.26, 0.54, (0.03, 0.05, 0.06), (0.12, 0.86, 0.94)),
    "reactive_warm_cold": _fd(647, 1.28, 0.150, 0.660, 0.24, 0.62, (0.10, 0.48, 0.92), (0.98, 0.38, 0.10)),
    # Sparkle Systems
    "sparkle_champagne": _fd(701, 1.78, 0.190, 0.560, 0.16, 0.82, (0.70, 0.58, 0.36), (1.00, 0.82, 0.46)),
    "sparkle_confetti": _fd(719, 1.88, 0.210, 0.540, 0.18, 0.88, (0.22, 0.56, 0.90), (1.00, 0.28, 0.72)),
    "sparkle_constellation": _fd(733, 1.70, 0.170, 0.610, 0.15, 0.72, (0.04, 0.08, 0.20), (0.80, 0.88, 1.00)),
    "sparkle_diamond_dust": _fd(751, 1.95, 0.185, 0.535, 0.14, 0.90, (0.66, 0.78, 0.92), (0.98, 0.98, 1.00)),
    "sparkle_firefly": _fd(769, 1.82, 0.205, 0.555, 0.16, 0.84, (0.08, 0.22, 0.10), (0.92, 0.82, 0.18)),
    "sparkle_galaxy": _fd(787, 1.86, 0.220, 0.545, 0.20, 0.86, (0.05, 0.10, 0.30), (0.90, 0.20, 0.96)),
    "sparkle_lightning_bug": _fd(809, 1.90, 0.215, 0.535, 0.18, 0.88, (0.02, 0.18, 0.22), (0.82, 1.00, 0.28)),
    "sparkle_meteor": _fd(827, 1.92, 0.220, 0.540, 0.20, 0.84, (0.22, 0.12, 0.08), (1.00, 0.44, 0.14)),
    "sparkle_snowfall": _fd(839, 1.68, 0.165, 0.620, 0.14, 0.70, (0.54, 0.70, 0.92), (0.96, 0.98, 1.00)),
    "sparkle_starfield": _fd(857, 1.76, 0.180, 0.590, 0.15, 0.76, (0.03, 0.05, 0.14), (0.78, 0.86, 1.00)),
    # Multi-Scale Texture
    "multiscale_candy_frost": _fd(907, 1.36, 0.150, 0.640, 0.26, 0.66, (0.40, 0.64, 0.94), (0.98, 0.28, 0.42)),
    "multiscale_carbon_micro": _fd(919, 1.34, 0.100, 0.700, 0.32, 0.54, (0.04, 0.05, 0.06), (0.56, 0.62, 0.68)),
    "multiscale_chrome_grain": _fd(937, 1.50, 0.110, 0.680, 0.34, 0.62, (0.34, 0.38, 0.44), (0.88, 0.90, 0.88)),
    "multiscale_chrome_sand": _fd(953, 1.58, 0.120, 0.615, 0.24, 0.78, (0.40, 0.42, 0.40), (0.92, 0.88, 0.74)),
    "multiscale_flake_grain": _fd(971, 1.62, 0.165, 0.580, 0.22, 0.82, (0.24, 0.34, 0.52), (0.96, 0.64, 0.26)),
    "multiscale_frost_crystal": _fd(983, 1.44, 0.145, 0.610, 0.30, 0.72, (0.48, 0.74, 0.96), (0.90, 0.98, 1.00)),
    "multiscale_matte_silk": _fd(997, 1.10, 0.105, 0.740, 0.20, 0.44, (0.32, 0.26, 0.30), (0.82, 0.66, 0.72)),
    "multiscale_metal_grit": _fd(1013, 1.52, 0.120, 0.600, 0.30, 0.76, (0.22, 0.24, 0.25), (0.82, 0.74, 0.58)),
    "multiscale_pearl_texture": _fd(1027, 1.28, 0.140, 0.650, 0.22, 0.64, (0.58, 0.68, 0.92), (0.96, 0.82, 0.98)),
    "multiscale_satin_weave": _fd(1043, 1.22, 0.112, 0.700, 0.34, 0.52, (0.34, 0.32, 0.30), (0.86, 0.72, 0.54)),
    # Weather & Age
    "weather_acid_rain": _fd(1103, 1.24, 0.145, 0.650, 0.30, 0.64, (0.22, 0.78, 0.18), (0.90, 0.86, 0.20)),
    "weather_barn_dust": _fd(1117, 1.12, 0.120, 0.720, 0.24, 0.48, (0.36, 0.26, 0.18), (0.80, 0.58, 0.34)),
    "weather_desert_blast": _fd(1133, 1.20, 0.130, 0.690, 0.26, 0.58, (0.52, 0.38, 0.20), (0.94, 0.72, 0.36)),
    "weather_hood_bake": _fd(1151, 1.18, 0.128, 0.700, 0.22, 0.54, (0.24, 0.14, 0.10), (0.92, 0.38, 0.16)),
    "weather_ice_storm": _fd(1163, 1.34, 0.145, 0.640, 0.30, 0.68, (0.42, 0.70, 0.96), (0.92, 0.98, 1.00)),
    "weather_ocean_mist": _fd(1171, 1.16, 0.132, 0.690, 0.22, 0.56, (0.18, 0.52, 0.72), (0.76, 0.92, 0.86)),
    "weather_road_spray": _fd(1187, 1.22, 0.110, 0.705, 0.28, 0.52, (0.18, 0.18, 0.16), (0.72, 0.70, 0.62)),
    "weather_salt_spray": _fd(1201, 1.28, 0.136, 0.665, 0.24, 0.62, (0.54, 0.62, 0.66), (0.94, 0.96, 0.90)),
    "weather_sun_fade": _fd(1217, 1.10, 0.116, 0.730, 0.18, 0.46, (0.38, 0.30, 0.22), (0.98, 0.74, 0.34)),
    "weather_volcanic_ash": _fd(1231, 1.30, 0.125, 0.660, 0.32, 0.66, (0.10, 0.10, 0.10), (0.92, 0.26, 0.08)),
    # Exotic Physics
    "exotic_anti_metal": _fd(1301, 1.44, 0.145, 0.650, 0.30, 0.62, (0.02, 0.04, 0.06), (0.16, 0.94, 0.86)),
    "exotic_ceramic_void": _fd(1319, 1.30, 0.125, 0.685, 0.24, 0.56, (0.06, 0.06, 0.08), (0.72, 0.68, 0.82)),
    "exotic_crystal_clear": _fd(1337, 1.52, 0.135, 0.640, 0.32, 0.66, (0.54, 0.78, 0.94), (0.98, 1.00, 1.00)),
    "exotic_dark_glass": _fd(1361, 1.46, 0.118, 0.665, 0.30, 0.60, (0.02, 0.04, 0.08), (0.52, 0.68, 0.88)),
    "exotic_foggy_chrome": _fd(1373, 1.36, 0.112, 0.700, 0.20, 0.52, (0.50, 0.54, 0.58), (0.88, 0.90, 0.86)),
    "exotic_glass_paint": _fd(1381, 1.40, 0.140, 0.655, 0.26, 0.62, (0.24, 0.48, 0.74), (0.88, 0.72, 0.96)),
    "exotic_inverted_candy": _fd(1399, 1.34, 0.155, 0.640, 0.24, 0.66, (0.08, 0.86, 0.72), (0.96, 0.16, 0.44)),
    "exotic_liquid_glass": _fd(1423, 1.50, 0.150, 0.630, 0.28, 0.70, (0.20, 0.58, 0.88), (0.92, 0.96, 1.00)),
    "exotic_phantom_mirror": _fd(1439, 1.58, 0.118, 0.650, 0.34, 0.64, (0.02, 0.02, 0.04), (0.82, 0.86, 0.94)),
    "exotic_wet_void": _fd(1451, 1.54, 0.128, 0.625, 0.32, 0.70, (0.01, 0.03, 0.05), (0.28, 0.74, 0.96)),
    # Tri-Zone Materials
    "trizone_anodized_candy_silk": _fd(1501, 1.32, 0.150, 0.655, 0.26, 0.64, (0.30, 0.48, 0.72), (0.94, 0.28, 0.42)),
    "trizone_ceramic_flake_satin": _fd(1511, 1.28, 0.130, 0.670, 0.24, 0.60, (0.56, 0.56, 0.50), (0.92, 0.78, 0.58)),
    "trizone_chrome_candy_matte": _fd(1523, 1.42, 0.138, 0.660, 0.30, 0.64, (0.32, 0.36, 0.42), (0.96, 0.20, 0.30)),
    "trizone_frozen_ember_chrome": _fd(1531, 1.46, 0.158, 0.630, 0.28, 0.72, (0.24, 0.62, 0.96), (1.00, 0.34, 0.08)),
    "trizone_glass_metal_matte": _fd(1543, 1.34, 0.128, 0.680, 0.26, 0.58, (0.26, 0.40, 0.56), (0.82, 0.80, 0.74)),
    "trizone_mercury_obsidian_candy": _fd(1559, 1.56, 0.145, 0.640, 0.34, 0.68, (0.02, 0.03, 0.06), (0.86, 0.90, 0.96)),
    "trizone_pearl_carbon_gold": _fd(1571, 1.38, 0.140, 0.650, 0.30, 0.66, (0.08, 0.09, 0.10), (0.98, 0.74, 0.22)),
    "trizone_stealth_spectra_frozen": _fd(1583, 1.48, 0.160, 0.625, 0.32, 0.72, (0.02, 0.04, 0.08), (0.28, 0.90, 1.00)),
    "trizone_titanium_copper_chrome": _fd(1597, 1.44, 0.142, 0.650, 0.28, 0.66, (0.30, 0.40, 0.54), (0.94, 0.48, 0.20)),
    "trizone_vanta_chrome_pearl": _fd(1609, 1.58, 0.134, 0.645, 0.34, 0.66, (0.01, 0.01, 0.02), (0.90, 0.92, 0.98)),
    # Depth Illusion
    "depth_bubble": _fd(1709, 1.28, 0.120, 0.690, 0.34, 0.56, (0.20, 0.52, 0.78), (0.88, 0.94, 1.00)),
    "depth_canyon": _fd(1721, 1.34, 0.128, 0.660, 0.38, 0.64, (0.34, 0.18, 0.08), (0.96, 0.48, 0.16)),
    "depth_crack": _fd(1733, 1.42, 0.118, 0.625, 0.46, 0.70, (0.03, 0.03, 0.04), (0.88, 0.32, 0.12)),
    "depth_erosion": _fd(1747, 1.30, 0.122, 0.650, 0.40, 0.66, (0.30, 0.24, 0.18), (0.82, 0.62, 0.38)),
    "depth_honeycomb": _fd(1759, 1.36, 0.126, 0.665, 0.42, 0.62, (0.24, 0.20, 0.12), (0.96, 0.72, 0.18)),
    "depth_map": _fd(1777, 1.18, 0.110, 0.720, 0.28, 0.48, (0.18, 0.34, 0.26), (0.76, 0.68, 0.42)),
    "depth_pillow": _fd(1789, 1.16, 0.108, 0.735, 0.22, 0.42, (0.32, 0.24, 0.30), (0.86, 0.70, 0.78)),
    "depth_ripple": _fd(1801, 1.32, 0.125, 0.670, 0.36, 0.60, (0.12, 0.42, 0.76), (0.78, 0.92, 0.96)),
    "depth_scale": _fd(1811, 1.34, 0.120, 0.675, 0.40, 0.58, (0.10, 0.26, 0.22), (0.70, 0.90, 0.42)),
    "depth_vortex": _fd(1823, 1.46, 0.140, 0.635, 0.42, 0.68, (0.06, 0.08, 0.22), (0.76, 0.20, 0.96)),
    "depth_wave": _fd(1831, 1.28, 0.122, 0.680, 0.34, 0.58, (0.10, 0.44, 0.72), (0.82, 0.90, 0.86)),
    # Metallic Halos
    "halo_circle_pearl": _fd(1901, 1.52, 0.142, 0.610, 0.36, 0.74, (0.52, 0.64, 0.86), (0.96, 0.82, 0.98)),
    "halo_crack_chrome": _fd(1913, 1.62, 0.128, 0.575, 0.48, 0.82, (0.08, 0.10, 0.12), (0.86, 0.88, 0.86)),
    "halo_diamond_chrome": _fd(1931, 1.58, 0.130, 0.600, 0.44, 0.78, (0.30, 0.34, 0.40), (0.92, 0.92, 0.88)),
    "halo_grid_pearl": _fd(1949, 1.50, 0.132, 0.620, 0.42, 0.72, (0.46, 0.58, 0.80), (0.94, 0.86, 0.98)),
    "halo_hex_chrome": _fd(1957, 1.60, 0.128, 0.595, 0.46, 0.80, (0.28, 0.34, 0.42), (0.90, 0.92, 0.90)),
    "halo_ripple_chrome": _fd(1973, 1.56, 0.132, 0.610, 0.42, 0.76, (0.24, 0.38, 0.54), (0.88, 0.92, 0.94)),
    "halo_scale_gold": _fd(1987, 1.54, 0.145, 0.595, 0.44, 0.78, (0.34, 0.24, 0.10), (1.00, 0.74, 0.18)),
    "halo_star_metal": _fd(1999, 1.66, 0.150, 0.570, 0.48, 0.84, (0.20, 0.24, 0.32), (0.96, 0.82, 0.40)),
    "halo_voronoi_metal": _fd(2011, 1.58, 0.136, 0.585, 0.50, 0.82, (0.24, 0.26, 0.28), (0.86, 0.70, 0.48)),
    "halo_wave_candy": _fd(2027, 1.48, 0.152, 0.610, 0.40, 0.76, (0.10, 0.38, 0.70), (0.96, 0.24, 0.38)),
    # Light Waves
    "wave_candy_flow": _fd(2101, 1.28, 0.148, 0.650, 0.32, 0.66, (0.12, 0.28, 0.56), (0.96, 0.22, 0.36)),
    "wave_chrome_tide": _fd(2113, 1.48, 0.125, 0.640, 0.38, 0.70, (0.18, 0.42, 0.62), (0.88, 0.92, 0.94)),
    "wave_circular_radar": _fd(2129, 1.42, 0.136, 0.625, 0.44, 0.74, (0.06, 0.30, 0.22), (0.50, 1.00, 0.40)),
    "wave_diagonal_sweep": _fd(2141, 1.34, 0.132, 0.665, 0.36, 0.62, (0.18, 0.26, 0.42), (0.92, 0.56, 0.24)),
    "wave_dual_frequency": _fd(2153, 1.36, 0.142, 0.640, 0.40, 0.68, (0.10, 0.44, 0.86), (0.98, 0.34, 0.10)),
    "wave_metallic_pulse": _fd(2161, 1.50, 0.136, 0.620, 0.42, 0.72, (0.20, 0.30, 0.40), (0.96, 0.62, 0.26)),
    "wave_moire_metal": _fd(2179, 1.54, 0.130, 0.600, 0.48, 0.78, (0.18, 0.22, 0.28), (0.86, 0.84, 0.76)),
    "wave_pearl_current": _fd(2197, 1.30, 0.142, 0.650, 0.34, 0.66, (0.50, 0.64, 0.88), (0.94, 0.86, 0.98)),
    "wave_standing_chrome": _fd(2207, 1.46, 0.118, 0.670, 0.36, 0.60, (0.28, 0.34, 0.42), (0.88, 0.88, 0.84)),
    "wave_turbulent_flow": _fd(2213, 1.38, 0.150, 0.630, 0.44, 0.72, (0.08, 0.26, 0.42), (0.90, 0.40, 0.18)),
    # Fractal Chaos
    "fractal_candy_chaos": _fd(2309, 1.38, 0.165, 0.610, 0.42, 0.76, (0.06, 0.22, 0.52), (0.98, 0.18, 0.46)),
    "fractal_chrome_decay": _fd(2327, 1.56, 0.132, 0.590, 0.50, 0.80, (0.18, 0.20, 0.22), (0.86, 0.88, 0.84)),
    "fractal_cosmic_dust": _fd(2339, 1.50, 0.175, 0.570, 0.38, 0.84, (0.04, 0.08, 0.22), (0.88, 0.28, 0.96)),
    "fractal_deep_organic": _fd(2351, 1.28, 0.140, 0.635, 0.40, 0.68, (0.06, 0.24, 0.12), (0.74, 0.64, 0.30)),
    "fractal_electric_noise": _fd(2371, 1.62, 0.190, 0.550, 0.36, 0.88, (0.02, 0.18, 0.46), (0.20, 0.96, 1.00)),
    "fractal_liquid_fire": _fd(2383, 1.54, 0.175, 0.560, 0.44, 0.84, (0.12, 0.04, 0.02), (1.00, 0.30, 0.04)),
    "fractal_matte_chrome": _fd(2399, 1.42, 0.112, 0.675, 0.36, 0.58, (0.24, 0.26, 0.28), (0.82, 0.82, 0.78)),
    "fractal_metallic_storm": _fd(2411, 1.58, 0.152, 0.585, 0.46, 0.82, (0.10, 0.16, 0.26), (0.92, 0.70, 0.36)),
    "fractal_pearl_cloud": _fd(2423, 1.32, 0.148, 0.630, 0.30, 0.68, (0.54, 0.66, 0.88), (0.96, 0.88, 0.98)),
    "fractal_warm_cold": _fd(2437, 1.44, 0.165, 0.610, 0.40, 0.76, (0.08, 0.50, 0.92), (1.00, 0.36, 0.08)),
    # Spectral Reactive
    "spectral_complementary": _fd(2503, 1.42, 0.172, 0.610, 0.30, 0.78, (0.04, 0.44, 0.92), (0.98, 0.36, 0.06)),
    "spectral_dark_light": _fd(2521, 1.40, 0.150, 0.635, 0.28, 0.68, (0.02, 0.02, 0.04), (0.92, 0.94, 0.90)),
    "spectral_earth_sky": _fd(2539, 1.32, 0.155, 0.640, 0.26, 0.66, (0.08, 0.36, 0.76), (0.72, 0.54, 0.24)),
    "spectral_inverse_logic": _fd(2551, 1.50, 0.175, 0.600, 0.34, 0.80, (0.02, 0.88, 0.78), (0.98, 0.08, 0.44)),
    "spectral_mono_chrome": _fd(2579, 1.38, 0.118, 0.675, 0.28, 0.60, (0.08, 0.08, 0.08), (0.90, 0.90, 0.90)),
    "spectral_neon_reactive": _fd(2591, 1.62, 0.195, 0.550, 0.34, 0.88, (0.00, 0.28, 0.78), (1.00, 0.08, 0.84)),
    "spectral_prismatic_flip": _fd(2609, 1.58, 0.190, 0.565, 0.36, 0.86, (0.04, 0.50, 0.98), (0.98, 0.18, 0.62)),
    "spectral_rainbow_metal": _fd(2621, 1.56, 0.185, 0.575, 0.32, 0.84, (0.04, 0.58, 0.90), (0.98, 0.72, 0.18)),
    "spectral_sat_metal": _fd(2633, 1.48, 0.168, 0.600, 0.30, 0.76, (0.18, 0.34, 0.64), (0.94, 0.22, 0.34)),
    "spectral_warm_cool": _fd(2647, 1.44, 0.170, 0.610, 0.30, 0.78, (0.08, 0.48, 0.92), (1.00, 0.34, 0.08)),
}

_FUSION_DETAIL_PROFILES["depth_vortex"]["micro_gain"] = 0.50
_FUSION_DETAIL_PROFILES["sparkle_galaxy"]["micro_gain"] = 0.18
_FUSION_DETAIL_PROFILES.update({
    "ghost_hex": _fd(2711, 1.72, 0.106, 0.690, 0.28, 0.58, (0.16, 0.22, 0.32), (0.72, 0.94, 0.92)),
    "ghost_stripes": _fd(2723, 1.86, 0.098, 0.700, 0.34, 0.54, (0.10, 0.16, 0.28), (0.84, 0.90, 0.98)),
    "ghost_diamonds": _fd(2731, 1.76, 0.104, 0.680, 0.32, 0.60, (0.18, 0.20, 0.28), (0.78, 0.92, 0.86)),
    "ghost_waves": _fd(2749, 1.82, 0.112, 0.660, 0.30, 0.64, (0.12, 0.26, 0.42), (0.68, 0.96, 0.90)),
    "ghost_camo": _fd(2767, 1.70, 0.116, 0.670, 0.36, 0.62, (0.10, 0.18, 0.12), (0.62, 0.86, 0.56)),
    "ghost_scales": _fd(2789, 1.88, 0.110, 0.650, 0.40, 0.66, (0.08, 0.18, 0.24), (0.54, 0.96, 0.82)),
    "ghost_circuit": _fd(2801, 1.94, 0.108, 0.640, 0.46, 0.70, (0.04, 0.12, 0.18), (0.38, 1.00, 0.86)),
    "ghost_vortex": _fd(2819, 1.92, 0.118, 0.630, 0.44, 0.72, (0.05, 0.10, 0.28), (0.76, 0.50, 1.00)),
    "ghost_fracture": _fd(2833, 1.84, 0.112, 0.640, 0.50, 0.72, (0.06, 0.08, 0.12), (0.86, 0.94, 1.00)),
    "ghost_quilt": _fd(2851, 1.78, 0.102, 0.675, 0.36, 0.62, (0.12, 0.16, 0.22), (0.80, 0.88, 0.94)),
})
for _fid in (
    "gradient_anodized_gloss", "gradient_candy_frozen", "gradient_candy_matte",
    "gradient_carbon_chrome", "gradient_chrome_matte", "gradient_ember_ice",
    "gradient_metallic_satin", "gradient_obsidian_mirror", "gradient_pearl_chrome",
    "gradient_spectraflame_void",
):
    _FUSION_DETAIL_PROFILES[_fid]["micro_gain"] = 0.80
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB-67 Material Gradients now carries gradient-specific microflake,
    # material seams, and hidden spec traces in the source renderer. The generic
    # wrapper made this compact family slower and macro-heavy.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid in (
    "aniso_circular_chrome", "aniso_crosshatch_steel", "aniso_herringbone_gold",
    "aniso_spiral_mercury",
):
    _FUSION_DETAIL_PROFILES[_fid]["micro_gain"] = 0.48
_FUSION_DETAIL_PROFILES["aniso_horizontal_chrome"]["micro_gain"] = 0.80
for _fid in (
    "aniso_horizontal_chrome", "aniso_vertical_pearl", "aniso_diagonal_candy",
    "aniso_radial_metallic", "aniso_circular_chrome", "aniso_crosshatch_steel",
    "aniso_spiral_mercury", "aniso_wave_titanium", "aniso_herringbone_gold",
    "aniso_turbulence_metal",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB-67 Directional Grain now owns its toolpath scratches, polish direction
    # changes, hidden spec motifs, and material-specific M/R/CC response in the
    # source renderer. The generic wrapper made the group slow and same-DNA.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid in (
    "weather_hood_bake", "weather_ice_storm", "weather_road_spray",
    "weather_sun_fade", "weather_volcanic_ash",
    "wave_candy_flow", "wave_chrome_tide", "wave_standing_chrome",
):
    _FUSION_DETAIL_PROFILES[_fid]["micro_gain"] = 0.72
for _fid in (
    "wave_candy_flow", "wave_chrome_tide", "wave_circular_radar",
    "wave_diagonal_sweep", "wave_dual_frequency", "wave_metallic_pulse",
    "wave_moire_metal", "wave_pearl_current", "wave_standing_chrome",
    "wave_turbulent_flow",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # These SPB-67 Light Waves now carry their own 2048-scale paint/spec microstructure.
    # The generic detail wrapper adds several smooth-noise passes and was the main
    # reason the category sat above the 5s red-flag budget.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid in (
    "reactive_stealth_pop", "reactive_pearl_flash", "reactive_candy_reveal",
    "reactive_chrome_fade", "reactive_matte_shine", "reactive_dual_tone",
    "reactive_ghost_metal", "reactive_mirror_shadow", "reactive_warm_cold",
    "reactive_pulse_metal",
):
    # SPB-67 Reactive Panels now use explicit panel-field source renderers with
    # paint-aware spec detail; skipping the generic detail wrapper keeps them
    # under the render budget without erasing panel identity.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid in (
    "spectral_complementary", "spectral_dark_light", "spectral_earth_sky",
    "spectral_inverse_logic", "spectral_mono_chrome", "spectral_neon_reactive",
    "spectral_prismatic_flip", "spectral_rainbow_metal", "spectral_sat_metal",
    "spectral_warm_cool",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB-67 Spectral Reactive now uses explicit wavelength/micro-prism source
    # renderers. Avoid the generic wrapper's extra smooth-noise pass and keep the
    # paint/spec response tied to the spectral field.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid in (
    "ghost_hex", "ghost_stripes", "ghost_diamonds", "ghost_waves", "ghost_camo",
    "ghost_scales", "ghost_circuit", "ghost_vortex", "ghost_fracture", "ghost_quilt",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB-67 Ghost Geometry now carries its own clearcoat/pattern source detail.
    # Skipping the generic wrapper removes the former 5-10s render path.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid in (
    "trizone_anodized_candy_silk", "trizone_ceramic_flake_satin",
    "trizone_chrome_candy_matte", "trizone_frozen_ember_chrome",
    "trizone_glass_metal_matte", "trizone_mercury_obsidian_candy",
    "trizone_pearl_carbon_gold", "trizone_stealth_spectra_frozen",
    "trizone_titanium_copper_chrome", "trizone_vanta_chrome_pearl",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB-67 Tri-Zone Materials now use explicit per-zone source renderers.
    # The former Voronoi/detail-wrapper route kept this compact category in the
    # 7-9s range; source-side microstructure keeps the three-material idea intact.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid in ("exotic_dark_glass", "exotic_foggy_chrome", "exotic_phantom_mirror"):
    _FUSION_DETAIL_PROFILES[_fid]["micro_gain"] = 0.68
for _fid in (
    "exotic_glass_paint", "exotic_foggy_chrome", "exotic_inverted_candy",
    "exotic_liquid_glass", "exotic_phantom_mirror", "exotic_ceramic_void",
    "exotic_anti_metal", "exotic_crystal_clear", "exotic_dark_glass",
    "exotic_wet_void",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB-67 Exotic Physics now owns its 2048-scale microstructure directly in
    # the source renderer. The generic wrapper made the old category slow and
    # softened the tiny material details the owner keeps asking us to preserve.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid in (
    "halo_hex_chrome", "halo_scale_gold", "halo_circle_pearl",
    "halo_diamond_chrome", "halo_voronoi_metal", "halo_wave_candy",
    "halo_crack_chrome", "halo_star_metal", "halo_grid_pearl",
    "halo_ripple_chrome",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB-67 Metallic Halos now carries its own motif-scale edge tracing,
    # microflake, and channel variation directly in the source renderer.
    # The generic wrapper made the category slower and blurred halo-specific
    # material response into same-family noise.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid in (
    "depth_bubble", "depth_canyon", "depth_crack", "depth_erosion",
    "depth_honeycomb", "depth_map", "depth_pillow", "depth_ripple",
    "depth_scale", "depth_vortex", "depth_wave",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB-67 Depth Illusion now owns hidden contour/ripple/relief spec motifs
    # in the source renderer. The generic wrapper made this category slow and
    # diluted the light-angle Easter eggs into unrelated noise.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
_FUSION_DETAIL_PROFILES["weather_volcanic_ash"]["micro_gain"] = 1.20
for _fid in (
    "weather_sun_fade", "weather_salt_spray", "weather_acid_rain",
    "weather_desert_blast", "weather_ice_storm", "weather_road_spray",
    "weather_hood_bake", "weather_barn_dust", "weather_ocean_mist",
    "weather_volcanic_ash",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB-67 Weather & Age now carries weather-specific paint and M/R/CC
    # microstructure in the source renderer. The generic fusion detail wrapper
    # doubled the full-resolution detail work and pushed the 2048 path past 5s.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid in (
    "multiscale_chrome_grain", "multiscale_candy_frost", "multiscale_metal_grit",
    "multiscale_pearl_texture", "multiscale_satin_weave", "multiscale_chrome_sand",
    "multiscale_matte_silk", "multiscale_flake_grain", "multiscale_carbon_micro",
    "multiscale_frost_crystal",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB perf loop 2026-05-31: Multiscale source renderers already carry
    # macro/meso/micro/nano paint and M/R/CC detail. The generic Fusion wrapper
    # duplicated full-canvas detail work and pushed Satin/Matte Silk over budget.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
_FUSION_DETAIL_PROFILES["wave_chrome_tide"]["micro_gain"] = 0.95
_FUSION_DETAIL_PROFILES["fractal_chrome_decay"]["micro_gain"] = 0.72
_FUSION_DETAIL_PROFILES["fractal_liquid_fire"]["micro_gain"] = 0.95
for _fid in (
    "fractal_chrome_decay", "fractal_candy_chaos", "fractal_pearl_cloud",
    "fractal_metallic_storm", "fractal_matte_chrome", "fractal_warm_cold",
    "fractal_deep_organic", "fractal_electric_noise", "fractal_cosmic_dust",
    "fractal_liquid_fire",
):
    _FUSION_DETAIL_PROFILES[_fid]["smooth_detail"] = True
    # SPB-67 Fractal Chaos now carries its own paint/spec microstructure at the
    # source. The generic wrapper was adding full-resolution noise over the top
    # and pushing several active finishes past the 5s render red line.
    _FUSION_DETAIL_PROFILES[_fid]["skip_detail_wrapper"] = True
for _fid, _gain in {
    "depth_vortex": 0.86,
    "gradient_candy_matte": 1.05,
    "gradient_carbon_chrome": 1.04,
    "weather_desert_blast": 1.02,
    "exotic_inverted_candy": 0.88,
    "trizone_anodized_candy_silk": 1.02,
    "trizone_chrome_candy_matte": 1.06,
    "wave_turbulent_flow": 1.12,
    "fractal_deep_organic": 0.92,
    "fractal_warm_cold": 0.94,
    "aniso_spiral_mercury": 0.88,
}.items():
    _FUSION_DETAIL_PROFILES[_fid]["micro_gain"] = _gain
for _fid in (
    "ghost_hex", "ghost_stripes", "ghost_diamonds", "ghost_waves", "ghost_camo",
    "ghost_scales", "ghost_circuit", "ghost_vortex", "ghost_fracture", "ghost_quilt",
):
    _FUSION_DETAIL_PROFILES[_fid]["micro_gain"] = 0.86


def _hf_detail(shape, seed, profile):
    family_bias = int(profile["bias"])
    noise_fn = _multiscale_smooth_noise if profile.get("smooth_detail") else _noise
    fine = noise_fn(shape, [1, 2, 3, 5], [0.36, 0.30, 0.22, 0.12], seed + 9100 + family_bias)
    mist = noise_fn(shape, [2, 4, 8], [0.42, 0.36, 0.22], seed + 9200 + family_bias)
    body = noise_fn(shape, [12, 24, 48], [0.42, 0.34, 0.24], seed + 9300 + family_bias)
    ridge = 1.0 - np.clip(np.abs(noise_fn(shape, [4, 8, 16], [0.38, 0.36, 0.26], seed + 9400 + family_bias)) * 1.55, 0, 1)
    detail = np.clip((fine + 1.0) * 0.31 + (mist + 1.0) * 0.19 + (body + 1.0) * 0.06 + ridge * 0.14, 0, 1)
    sparkle = np.clip((detail - profile["sparkle_floor"]) * 4.8, 0, 1)
    coverage = np.clip((detail - profile["coverage"]) * 3.2, 0, 1)
    sparkle = np.maximum(sparkle, coverage * 0.45)
    return detail.astype(np.float32), sparkle.astype(np.float32), ridge.astype(np.float32)


def _fusion_family_bias(finish_id):
    if finish_id.startswith("sparkle_"):
        return 160, 1.75, 0.18
    if finish_id.startswith("halo_"):
        return 220, 1.35, 0.14
    if finish_id.startswith("depth_"):
        return 280, 1.15, 0.10
    if finish_id.startswith("wave_") or finish_id.startswith("fractal_"):
        return 340, 1.10, 0.11
    if finish_id.startswith("spectral_"):
        return 400, 1.18, 0.12
    if finish_id.startswith("multiscale_"):
        return 460, 1.25, 0.13
    return 80, 0.90, 0.08


def _fusion_profile(finish_id):
    profile = _FUSION_DETAIL_PROFILES.get(finish_id)
    if profile is not None:
        return profile
    family_bias, spec_gain, paint_gain = _fusion_family_bias(finish_id)
    return _fd(
        family_bias,
        spec_gain,
        paint_gain,
        0.76,
        0.18,
        0.50,
        (0.30, 0.38, 0.48),
        (0.86, 0.68, 0.42),
    )


def _wrap_fusion_detail(finish_id, spec_fn, paint_fn):
    profile = _fusion_profile(finish_id)
    if profile.get("skip_detail_wrapper"):
        return spec_fn, paint_fn
    spec_gain = profile["spec_gain"]
    paint_gain = profile["paint_gain"]

    def _spec(shape, mask, seed, sm):
        spec = spec_fn(shape, mask, seed, sm).astype(np.float32, copy=True)
        h, w = shape[:2] if len(shape) > 2 else shape
        detail, sparkle, ridge = _hf_detail((h, w), seed, profile)
        active = mask.astype(np.float32)
        edge = np.clip(
            np.abs(detail - np.roll(detail, 1, axis=0)) + np.abs(detail - np.roll(detail, 1, axis=1)),
            0,
            1,
        )
        micro_gain = float(profile.get("micro_gain", 0.0))
        spec[:, :, 0] = np.clip(
            spec[:, :, 0]
            + (detail - 0.58) * 38.0 * spec_gain * sm
            + sparkle * 36.0 * spec_gain * sm
            + edge * 34.0 * profile["edge_gain"] * sm,
            0,
            255,
        )
        if micro_gain > 0:
            spec[:, :, 0] = np.clip(spec[:, :, 0] + (ridge - 0.5) * 70.0 * micro_gain * sm, 0, 255)
            spec[:, :, 1] = np.clip(spec[:, :, 1] - sparkle * 34.0 * micro_gain * sm, 15, 255)
        spec[:, :, 1] = np.clip(
            spec[:, :, 1]
            - sparkle * 22.0 * spec_gain * sm
            - ridge * 8.0 * profile["edge_gain"] * sm
            + (1.0 - detail) * 4.0 * sm,
            15,
            255,
        )
        spec[:, :, 2] = np.where(
            active > 0.01,
            np.clip(spec[:, :, 2] + sparkle * 7.0 + edge * 6.0 * profile["edge_gain"], 16, 255),
            0,
        )
        spec[:, :, 3] = np.clip(active * 255, 0, 255)
        return spec.astype(np.uint8)

    def _paint(paint, shape, mask, seed, pm, bb):
        if paint.ndim == 3 and paint.shape[2] > 3:
            paint_in = paint[:, :, :3].copy()
        else:
            paint_in = paint.copy()
        out = paint_fn(paint_in, shape, mask, seed, pm, bb)
        if out.ndim == 3 and out.shape[2] > 3:
            out = out[:, :, :3].copy()
        h, w = shape[:2] if len(shape) > 2 else shape
        detail, sparkle, ridge = _hf_detail((h, w), seed, profile)
        active = mask[:, :, np.newaxis].astype(np.float32)
        cool = np.asarray(profile["cool"], dtype=np.float32)
        warm = np.asarray(profile["warm"], dtype=np.float32)
        carrier = np.clip(detail * 0.68 + ridge * 0.18 + sparkle * 0.14, 0, 1)
        tint = cool[np.newaxis, np.newaxis, :] * (1.0 - carrier[:, :, np.newaxis]) + warm[np.newaxis, np.newaxis, :] * carrier[:, :, np.newaxis]
        shift = (tint - 0.5) * (0.34 + sparkle[:, :, np.newaxis] * 0.72)
        luma_detail = ((detail - 0.5) * 0.050 + sparkle * 0.055 + ridge * 0.018)[:, :, np.newaxis]
        micro_gain = float(profile.get("micro_gain", 0.0))
        needle = None
        if micro_gain > 0:
            phase = (int(profile["bias"]) % 360) * np.pi / 180.0
            needle = _noise((h, w), [1, 2, 3], [0.44, 0.34, 0.22], seed + 9600 + int(profile["bias"]))
            color_grain = np.stack([
                np.sin(needle * 6.0 + detail * 15.0 + phase) * 0.5 + 0.5,
                np.sin(ridge * 17.0 + phase + 2.09) * 0.5 + 0.5,
                np.sin(needle * 5.0 + (detail + ridge) * 11.0 + phase + 4.18) * 0.5 + 0.5,
            ], axis=2).astype(np.float32)
            shift = shift + (color_grain - 0.5) * micro_gain
            luma_detail = luma_detail + needle[:, :, np.newaxis] * micro_gain * 0.18
        out = np.clip(
            out
            + shift * active * float(pm) * paint_gain
            + luma_detail * active * float(pm) * min(0.42, paint_gain * 2.2),
            0,
            1,
        )
        return out.astype(np.float32)

    return _spec, _paint


FUSION_REGISTRY = {
    finish_id: _wrap_fusion_detail(finish_id, spec_fn, paint_fn)
    for finish_id, (spec_fn, paint_fn) in FUSION_REGISTRY.items()
}


# ================================================================
# INTEGRATION
# ================================================================

def integrate_fusions(engine_module):
    """Merge FUSIONS into the engine as a NEW 4th category.

    Creates engine_module.FUSION_REGISTRY if it doesn't exist,
    then merges all 150 Fusions into it. Also adds them to
    MONOLITHIC_REGISTRY so the existing render pipeline can find them.
    """
    # Create the FUSION_REGISTRY on the engine module
    if not hasattr(engine_module, 'FUSION_REGISTRY'):
        engine_module.FUSION_REGISTRY = {}
    engine_module.FUSION_REGISTRY.update(FUSION_REGISTRY)

    # Also register in MONOLITHIC_REGISTRY so existing pipeline works
    if hasattr(engine_module, 'MONOLITHIC_REGISTRY'):
        engine_module.MONOLITHIC_REGISTRY.update(FUSION_REGISTRY)

    # Sort registries
    for reg_name in ('FUSION_REGISTRY', 'MONOLITHIC_REGISTRY'):
        reg = getattr(engine_module, reg_name, None)
        if reg is not None:
            sorted_reg = dict(sorted(reg.items()))
            reg.clear()
            reg.update(sorted_reg)

    print(f"[FUSIONS] Loaded {len(FUSION_REGISTRY)} Paradigm Shift Fusions across 15 categories")
    return {"fusions": len(FUSION_REGISTRY)}


def get_fusion_group_map():
    """Return group metadata for UI organization."""
    return {
        "fusions": {
            "FUSIONS - Material Gradients": [
                "gradient_chrome_matte", "gradient_candy_frozen", "gradient_pearl_chrome",
                "gradient_metallic_satin", "gradient_obsidian_mirror", "gradient_candy_matte",
                "gradient_anodized_gloss", "gradient_ember_ice", "gradient_carbon_chrome",
                "gradient_spectraflame_void",
            ],
            "FUSIONS - Ghost Geometry": [
                "ghost_hex", "ghost_stripes", "ghost_diamonds", "ghost_waves", "ghost_camo",
                "ghost_scales", "ghost_circuit", "ghost_vortex", "ghost_fracture", "ghost_quilt",
            ],
            "FUSIONS - Directional Grain": [
                "aniso_horizontal_chrome", "aniso_vertical_pearl", "aniso_diagonal_candy",
                "aniso_radial_metallic", "aniso_circular_chrome", "aniso_crosshatch_steel",
                "aniso_spiral_mercury", "aniso_wave_titanium", "aniso_herringbone_gold",
                "aniso_turbulence_metal",
            ],
            "FUSIONS - Reactive Panels": [
                "reactive_stealth_pop", "reactive_pearl_flash", "reactive_candy_reveal",
                "reactive_chrome_fade", "reactive_matte_shine", "reactive_dual_tone",
                "reactive_ghost_metal", "reactive_mirror_shadow", "reactive_warm_cold",
                "reactive_pulse_metal",
            ],
            "FUSIONS - Sparkle Systems": [
                "sparkle_diamond_dust", "sparkle_starfield", "sparkle_galaxy", "sparkle_firefly",
                "sparkle_snowfall", "sparkle_champagne", "sparkle_meteor", "sparkle_constellation",
                "sparkle_confetti", "sparkle_lightning_bug",
            ],
            "FUSIONS - Multi-Scale Texture": [
                "multiscale_chrome_grain", "multiscale_candy_frost", "multiscale_metal_grit",
                "multiscale_pearl_texture", "multiscale_satin_weave", "multiscale_chrome_sand",
                "multiscale_matte_silk", "multiscale_flake_grain", "multiscale_carbon_micro",
                "multiscale_frost_crystal",
            ],
            "FUSIONS - Weather & Age": [
                "weather_sun_fade", "weather_salt_spray", "weather_acid_rain", "weather_desert_blast",
                "weather_ice_storm", "weather_road_spray", "weather_hood_bake", "weather_barn_dust",
                "weather_ocean_mist", "weather_volcanic_ash",
            ],
            "FUSIONS - Exotic Physics": [
                "exotic_glass_paint", "exotic_foggy_chrome", "exotic_inverted_candy",
                "exotic_liquid_glass", "exotic_phantom_mirror", "exotic_ceramic_void",
                "exotic_anti_metal", "exotic_crystal_clear", "exotic_dark_glass",
                "exotic_wet_void",
            ],
            "FUSIONS - Tri-Zone Materials": [
                "trizone_chrome_candy_matte", "trizone_pearl_carbon_gold", "trizone_frozen_ember_chrome",
                "trizone_anodized_candy_silk", "trizone_vanta_chrome_pearl", "trizone_glass_metal_matte",
                "trizone_mercury_obsidian_candy", "trizone_titanium_copper_chrome",
                "trizone_ceramic_flake_satin", "trizone_stealth_spectra_frozen",
            ],
            "FUSIONS - Depth Illusion": [
                "depth_canyon", "depth_bubble", "depth_map", "depth_ripple", "depth_scale", "depth_honeycomb",
                "depth_crack", "depth_wave", "depth_pillow", "depth_vortex", "depth_erosion",
            ],
            "FUSIONS - Metallic Halos": [
                "halo_hex_chrome", "halo_scale_gold", "halo_circle_pearl", "halo_diamond_chrome",
                "halo_voronoi_metal", "halo_wave_candy", "halo_crack_chrome", "halo_star_metal",
                "halo_grid_pearl", "halo_ripple_chrome",
            ],
            "FUSIONS - Light Waves": [
                "wave_chrome_tide", "wave_candy_flow", "wave_pearl_current", "wave_metallic_pulse",
                "wave_dual_frequency", "wave_diagonal_sweep", "wave_circular_radar",
                "wave_turbulent_flow", "wave_standing_chrome", "wave_moire_metal",
            ],
            "FUSIONS - Fractal Chaos": [
                "fractal_chrome_decay", "fractal_candy_chaos", "fractal_pearl_cloud",
                "fractal_metallic_storm", "fractal_matte_chrome", "fractal_warm_cold",
                "fractal_deep_organic", "fractal_electric_noise", "fractal_cosmic_dust",
                "fractal_liquid_fire",
            ],
            "FUSIONS - Spectral Reactive": [
                "spectral_rainbow_metal", "spectral_warm_cool", "spectral_dark_light",
                "spectral_sat_metal", "spectral_complementary", "spectral_neon_reactive",
                "spectral_earth_sky", "spectral_mono_chrome", "spectral_prismatic_flip",
                "spectral_inverse_logic",
            ],
            "FUSIONS - Panel Quilting": [
                "quilt_chrome_mosaic", "quilt_candy_tiles", "quilt_pearl_patchwork",
                "quilt_metallic_pixels", "quilt_hex_variety", "quilt_diamond_shimmer",
                "quilt_random_chaos", "quilt_gradient_tiles", "quilt_alternating_duo",
                "quilt_organic_cells",
            ],
            # SPB-102 — procedural iridescent (50 finishes); IDs spectrum_{palette}_{variant}
            "🧠 FRACTURED MINDS": sorted(
                k for k in FUSION_REGISTRY if k.startswith("fm_")
            ),
            # GHOST LAB single-variable experiments (2026-06-12) — without a
            # server-side group the runtime catalog reconcile prunes the
            # static picker lane, so the variants never show in the dropdown.
            "🔬 GHOST LAB": sorted(
                k for k in FUSION_REGISTRY if k.startswith("gl_")
            ),
            # FRACTURED SOULS (2026-06-12) — apex drag-and-drop color shift
            "💀 FRACTURED SOULS": sorted(
                k for k in FUSION_REGISTRY if k.startswith("fs_")
            ),
            "★ Spectrum Shift": sorted(
                k for k in FUSION_REGISTRY if k.startswith("spectrum_")
            ),
        },
    }


def get_fusion_counts():
    return {
        "fusions": len(FUSION_REGISTRY),
        "paradigm_shifts": 15,
        "per_paradigm": 10,
    }

