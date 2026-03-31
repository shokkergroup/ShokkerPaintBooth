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
from PIL import Image, ImageFilter
from scipy.spatial import cKDTree
import os
import importlib.util

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

def _mgrid(shape):
    return np.mgrid[0:shape[0], 0:shape[1]]

def _noise(shape, scales, weights, seed):
    """Multi-octave noise."""
    h, w = shape
    rng = np.random.RandomState(seed)
    result = np.zeros((h, w), dtype=np.float32)
    for s, wt in zip(scales, weights):
        raw = rng.randn(max(1, h // s), max(1, w // s)).astype(np.float32)
        img = Image.fromarray((raw * 127 + 128).clip(0, 255).astype(np.uint8))
        up = np.array(img.resize((w, h), Image.BILINEAR)).astype(np.float32) / 127.0 - 1.0
        result += up * wt
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
    """Standard spec output helper."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    spec[:,:,0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:,:,1] = np.clip(G * mask, 0, 255).astype(np.uint8)
    spec[:,:,2] = np.clip(B * mask, 0, 255).astype(np.uint8)
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

def _paint_noop(paint, shape, mask, seed, pm, bb):
    return paint

def _paint_brighten(paint, shape, mask, seed, pm, bb):
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

def _make_gradient_fusion(mat_a, mat_b, grad_fn, seed_offset=0, warp=False, paint_warm=False):
    """Factory for gradient fusions with domain-warped organic flow and chrome seam transitions."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_gradient_fusion(mat_a, mat_b, grad_fn, seed_offset, warp, paint_warm))

    def _domain_warp_grad(shape, grad, seed, so):
        """Apply multi-octave Perlin-style domain warp to gradient field."""
        h, w = shape
        # Primary warp: large organic flow
        warp1_y = _noise(shape, [48, 96, 192], [0.3, 0.4, 0.3], seed + so + 500)
        warp1_x = _noise(shape, [48, 96, 192], [0.3, 0.4, 0.3], seed + so + 501)
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
            extra_warp = _noise(shape, [24, 48], [0.5, 0.5], seed + seed_offset + 510)
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
        micro_a = _noise(shape, [2, 4], [0.6, 0.4], seed + seed_offset + 610)
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
        grad_raw = grad_fn(shape)
        grad = _domain_warp_grad(shape, grad_raw, seed, seed_offset)
        if warp:
            extra_warp = _noise(shape, [24, 48], [0.5, 0.5], seed + seed_offset + 510)
            grad = np.clip(grad + extra_warp * 0.15, 0, 1)
        result = paint.copy()

        # Gradient-driven brightness: mat_a side brightened, mat_b side slightly darkened
        bright_a = np.clip((1 - grad) * 0.18 * pm, 0, 0.18)
        dark_b = np.clip(grad * 0.10 * pm, 0, 0.10)
        for c in range(3):
            result[:,:,c] = np.clip(paint[:,:,c] + bright_a * mask - dark_b * mask, 0, 1)

        if paint_warm:
            warm = grad * 0.14 * pm
            result[:,:,0] = np.clip(result[:,:,0] + warm * mask, 0, 1)
            cool = (1 - grad) * 0.10 * pm
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
        warp_n2 = _noise(shape, [12, 24, 48], [0.3, 0.4, 0.3], seed_val + 777)
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
            inhibitor = _noise(shape, [24, 48, 96], [0.3, 0.4, 0.3], seed + seed_offset + 102)
            reaction = activator * 1.5 - inhibitor * 1.0
            pv = 1.0 / (1.0 + np.exp(-reaction * 6))
            fine = _noise(shape, [2, 4], [0.5, 0.5], seed + seed_offset + 103)
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
            stress = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 200)
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
        pv = _compute_ghost_pattern(shape, seed)

        M = np.full((h, w), float(base_m), dtype=np.float32)
        G = np.full((h, w), float(base_g), dtype=np.float32)
        # Clearcoat: dramatic ghost range CC 16-180 for max angle-dependent visibility
        B = pv * 16.0 + (1 - pv) * 180.0
        # M/G modulation: pattern zones get metallic boost and smoothness
        M = np.clip(M + pv * 80.0 * sm, 0, 255)
        G = np.clip(G - pv * 35.0 * sm + (1 - pv) * 20.0 * sm, 0, 255)
        n = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset)
        M = np.clip(M + n * 10 * sm, 0, 255)
        G = np.clip(G + n * 8 * sm, 0, 255)
        # Pattern edges get extra metallic pop via Sobel-like gradient
        pv_dx = np.abs(np.diff(pv, axis=1, prepend=pv[:, :1]))
        pv_dy = np.abs(np.diff(pv, axis=0, prepend=pv[:1, :]))
        edge = np.clip((pv_dx + pv_dy) * 6, 0, 1)
        M = np.clip(M + edge * 45 * sm, 0, 255)
        G = np.clip(G - edge * 18 * sm, 0, 255)
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        """Ghost patterns: COLORSHOXX-style color zones married to the ghost pattern.
        UPGRADED: Was shimmer-only. Now creates real color zones:
        - Pattern-high (pv>0.6): cool spectral tint (blue-cyan for circuits, green for hex, etc.)
        - Pattern-low (pv<0.3): warm desaturated push toward dark base
        - Edges: bright rim highlight with slight color shift
        - The same pv field drives both paint color AND spec M/R/CC = married pair."""
        h, w = shape
        pv = _compute_ghost_pattern(shape, seed)
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


# ================================================================
# PARADIGM 3: ANISOTROPIC ROUGHNESS - Directional grain simulation
# ================================================================

def _aniso_grain_field(shape, grain_fn_name, seed, seed_offset):
    """Generate anisotropic grain using elongated noise (Gabor-like filtering).
    Returns (primary_grain, micro_grain) both normalized 0-1."""
    h, w = shape
    rng = np.random.RandomState(seed + seed_offset)
    y_norm = np.linspace(-1, 1, h).reshape(h, 1).astype(np.float32)
    x_norm = np.linspace(-1, 1, w).reshape(1, w).astype(np.float32)
    y_px = np.arange(h, dtype=np.float32).reshape(h, 1)
    x_px = np.arange(w, dtype=np.float32).reshape(1, w)

    def _gabor_noise(theta, stretch, freq, sd):
        """Anisotropic noise: stretch coordinates along grain direction.
        noise(x*cos(t)+y*sin(t), -x*sin(t)*stretch + y*cos(t)*stretch)"""
        ct, st = np.cos(theta), np.sin(theta)
        u = x_norm * ct + y_norm * st  # along grain
        v = (-x_norm * st + y_norm * ct) * stretch  # across grain (compressed)
        along = np.sin(u * freq * np.pi) * 0.5
        n1 = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], sd)
        n2 = _noise(shape, [2, 4], [0.5, 0.5], sd + 1)
        stretched = along + n1 * 0.4 + n2 * np.abs(np.cos(u * freq * np.pi * 2)) * 0.3
        return stretched

    if grain_fn_name == "horizontal":
        primary = _gabor_noise(0.0, 0.1, 12.0, seed + seed_offset + 100)
        stroke_raw = rng.randn(max(1, h // 2), 1).astype(np.float32)
        img = Image.fromarray((stroke_raw * 127 + 128).clip(0, 255).astype(np.uint8))
        strokes = np.array(img.resize((1, h), Image.BILINEAR)).astype(np.float32).reshape(h, 1) / 127.0 - 1.0
        strokes = np.tile(strokes, (1, w))
        primary = primary + strokes * 0.4

    elif grain_fn_name == "vertical":
        primary = _gabor_noise(np.pi / 2, 0.1, 12.0, seed + seed_offset + 100)
        stroke_raw = rng.randn(1, max(1, w // 2)).astype(np.float32)
        img = Image.fromarray((stroke_raw * 127 + 128).clip(0, 255).astype(np.uint8))
        strokes = np.array(img.resize((w, 1), Image.BILINEAR)).astype(np.float32).reshape(1, w) / 127.0 - 1.0
        strokes = np.tile(strokes, (h, 1))
        primary = primary + strokes * 0.4

    elif grain_fn_name == "diagonal":
        primary = _gabor_noise(np.pi / 4, 0.1, 10.0, seed + seed_offset + 100)
        diag_len = h + w
        stroke_raw = rng.randn(max(1, diag_len // 3)).astype(np.float32)
        img = Image.fromarray((stroke_raw * 127 + 128).clip(0, 255).astype(np.uint8).reshape(1, -1))
        strokes_1d = np.array(img.resize((diag_len, 1), Image.BILINEAR)).astype(np.float32).flatten() / 127.0 - 1.0
        y_i, x_i = _mgrid(shape)
        idx = np.clip(y_i + x_i, 0, diag_len - 1)
        primary = primary + strokes_1d[idx] * 0.35

    elif grain_fn_name == "radial":
        angle = np.arctan2(y_norm, x_norm)
        dist = np.sqrt(y_norm ** 2 + x_norm ** 2)
        n_ang = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 100)
        primary = np.sin(angle * 50 + n_ang * 2) * 0.5
        primary = primary * (0.7 + dist * 0.3) + n_ang * 0.2

    elif grain_fn_name == "circular":
        dist = np.sqrt(y_norm ** 2 + x_norm ** 2)
        n_warp = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 100)
        warped_dist = dist + n_warp * 0.05
        primary = np.sin(warped_dist * 80) * 0.5
        n_ring = _noise(shape, [2, 4], [0.5, 0.5], seed + seed_offset + 101)
        primary = primary + n_ring * np.clip(1.0 - np.abs(np.sin(warped_dist * 80)), 0, 1) * 0.3

    elif grain_fn_name == "crosshatch":
        g1 = _gabor_noise(np.pi / 6, 0.1, 10.0, seed + seed_offset + 100)
        g2 = _gabor_noise(-np.pi / 6 + np.pi / 2, 0.1, 10.0, seed + seed_offset + 200)
        primary = g1 * 0.55 + g2 * 0.55
        primary = primary + np.abs(g1 * g2) * 0.3

    elif grain_fn_name == "spiral":
        angle = np.arctan2(y_norm, x_norm)
        dist = np.sqrt(y_norm ** 2 + x_norm ** 2)
        spiral_phase = angle * 6 + dist * 30
        n_warp = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 100)
        primary = np.sin(spiral_phase + n_warp * 1.5) * 0.55
        primary = primary + np.sin(spiral_phase * 2.3) * 0.2

    elif grain_fn_name == "wave":
        wave_mod = np.sin(y_px * 0.02 + np.sin(x_px * 0.01) * 5)
        g_base = _gabor_noise(wave_mod.mean() * 0.1, 0.12, 10.0, seed + seed_offset + 100)
        n_w = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 101)
        primary = g_base * (0.6 + wave_mod * 0.3) + n_w * wave_mod * 0.25

    elif grain_fn_name == "herringbone":
        y_i, x_i = _mgrid(shape)
        block_h = max(16, h // 30)
        row_block = (y_i // block_h) % 2
        g_a = _gabor_noise(np.pi / 4, 0.1, 10.0, seed + seed_offset + 100)
        g_b = _gabor_noise(-np.pi / 4, 0.1, 10.0, seed + seed_offset + 200)
        primary = np.where(row_block == 0, g_a, g_b) * 0.8
        block_edge = np.abs((y_i % block_h) - block_h / 2.0) / (block_h / 2.0)
        seam = np.clip(1.0 - block_edge * 3, 0, 1)
        primary = primary + seam * 0.3

    elif grain_fn_name == "turbulence":
        n1 = _noise(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + seed_offset + 100)
        n2 = _noise(shape, [3, 6, 12], [0.3, 0.4, 0.3], seed + seed_offset + 200)
        primary = np.abs(n1) * 1.0 + np.abs(n2) * 0.5
        n_dir = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 300)
        primary = primary + n_dir * 0.3

    else:
        primary = rng.randn(h, w).astype(np.float32)

    # Secondary micro-grain riding on top of primary (fine scale)
    micro = _noise(shape, [1, 2, 3], [0.3, 0.4, 0.3], seed + seed_offset + 400)
    micro = micro * 0.25

    # Normalize primary to 0-1
    p_min, p_max = primary.min(), primary.max()
    if p_max - p_min > 1e-6:
        primary_norm = (primary - p_min) / (p_max - p_min)
    else:
        primary_norm = np.full_like(primary, 0.5)
    micro_norm = np.clip(micro * 0.5 + 0.5, 0, 1)

    return primary_norm.astype(np.float32), micro_norm.astype(np.float32)


def _make_aniso_fusion(base_m, base_g, base_cc, grain_fn_name, seed_offset=0):
    """Factory: true anisotropic brushed metal with elongated noise, Gabor-like filtering,
    multi-grain layers, and visible brush stroke marks at 2048x2048 scale."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_aniso_fusion(base_m, base_g, base_cc, grain_fn_name, seed_offset))

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        grain, micro = _aniso_grain_field(shape, grain_fn_name, seed, seed_offset)

        grain_m = np.clip(grain + 0.1, 0, 1)
        M = np.full((h, w), float(base_m), dtype=np.float32)
        M = M + grain_m * 40 * sm - (1 - grain_m) * 25 * sm
        M = M + (micro - 0.5) * 18 * sm

        grain_r = np.clip(grain - 0.08, 0, 1)
        G = np.full((h, w), float(base_g), dtype=np.float32)
        G = G + grain_r * 70 * sm
        G = G + np.abs(micro - 0.5) * 20 * sm
        cross = _noise(shape, [2, 4], [0.5, 0.5], seed + seed_offset + 450)
        G = G + np.abs(cross) * 14 * sm

        grain_cc = grain ** 1.3
        B = np.full((h, w), float(base_cc), dtype=np.float32)
        B = B + (grain_cc - 0.5) * 30 * sm
        B = B + (micro - 0.5) * 8 * sm

        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        grain, micro = _aniso_grain_field(shape, grain_fn_name, seed, seed_offset)

        bright = grain * 0.18 * pm
        dark = (1 - grain) * 0.09 * pm
        result = paint.copy()
        for c in range(3):
            result[:,:,c] = np.clip(paint[:,:,c] + bright * mask - dark * mask, 0, 1)

        micro_shift = (micro - 0.5) * 0.05 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + micro_shift * mask, 0, 1)

        result = np.clip(result + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return result
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
        warp_y = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + seed_offset + 80)
        warp_x = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + seed_offset + 90)
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
        zone_mask, edge_field, cell_id = _reactive_voronoi(shape, seed)
        # Chrome seam at cell boundaries (M=255, R=0)
        seam_width = max(h, w) * 0.012
        seam = np.clip(1.0 - edge_field / seam_width, 0, 1) ** 2.0
        # Zone materials
        M_zone = m_low * (1 - zone_mask) + m_high * zone_mask
        # Per-zone micro-texture with different seeds per zone
        micro_a = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 50)
        micro_b = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 60)
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
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        zone_mask, edge_field, cell_id = _reactive_voronoi(shape, seed)
        result = paint.copy()
        # Chrome seam brightening
        seam_width = max(shape[0], shape[1]) * 0.012
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
# PARADIGM 5: SPARKLE SYSTEMS - Multi-Scale Metallic Sparkle
# ================================================================

def _make_sparkle_fusion(flake_style, base_m, base_r, seed_offset=0):
    """Factory: Multi-scale metallic flake simulation using noise (fast).
    Large (32-64px zone shapes), medium (8-16px detail), micro (1-2px sparkle).
    Each scale drives M/R independently with sharp flake-edge transitions."""

    # Flake style controls noise octaves and thresholds
    if flake_style == "coarse":
        large_scales, med_scales = [32, 64, 128], [8, 16, 32]
        flake_thresh, edge_width = 0.42, 0.12
    elif flake_style == "fine":
        large_scales, med_scales = [16, 32, 64], [4, 8, 16]
        flake_thresh, edge_width = 0.35, 0.08
    else:  # medium
        large_scales, med_scales = [24, 48, 96], [6, 12, 24]
        flake_thresh, edge_width = 0.38, 0.10

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        rng = np.random.RandomState(seed + seed_offset)

        # Density envelope: where flakes are concentrated
        density = _noise(shape, [64, 128, 256], [0.3, 0.4, 0.3], seed + seed_offset + 50)
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
        micro = rng.random((h, w)).astype(np.float32)
        # Only top 8% sparkle brightly
        micro_flash = np.where(micro > 0.92, (micro - 0.92) / 0.08, 0.0).astype(np.float32)
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
            arm_noise = _noise(shape, [80, 160], [0.5, 0.5], seed + seed_offset + 801)
            arm_mod = np.clip(arm_noise * 1.8, 0.0, 1.0)
            M = M * arm_mod + float(base_m) * 0.15 * (1.0 - arm_mod)
        elif seed_offset == 7470:  # constellation: extremely sparse stellar spec
            clust_c = _noise(shape, [48, 96], [0.5, 0.5], seed + seed_offset + 500)
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
        h, w = shape
        rng = np.random.RandomState(seed + seed_offset)
        result = paint.copy()
        blend = mask * pm

        # Multi-scale sparkle field (noise-based, no Voronoi needed)
        density = _noise(shape, [64, 128, 256], [0.3, 0.4, 0.3], seed + seed_offset + 50)
        density = np.clip(density * 0.5 + 0.5, 0.15, 1.0)

        # Flake highlight pattern from large noise
        n_lg = _noise(shape, large_scales, [0.3, 0.4, 0.3], seed + seed_offset + 100)
        flake_body = np.clip((n_lg - flake_thresh) / edge_width, 0, 1)

        # Sparkle intensity: density * flake pattern * micro flash
        micro = rng.random((h, w)).astype(np.float32)
        flash = np.where(micro > 0.88, (micro - 0.88) / 0.12, 0.0).astype(np.float32)
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
            nebula = _noise(shape, [128, 256], [0.5, 0.5], seed + seed_offset + 600)
            nebula = np.clip(nebula * 0.5 + 0.5, 0, 1)
            neb_hue = _noise(shape, [64, 96], [0.5, 0.5], seed + seed_offset + 650)
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
            neb_g = _noise(shape, [100, 180], [0.55, 0.45], seed + seed_offset + 600)
            neb_g = np.clip(neb_g * 0.5 + 0.5, 0, 1)
            cluster_g = _noise(shape, [45, 80], [0.5, 0.5], seed + seed_offset + 610)
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
            cluster = _noise(shape, [48, 96], [0.5, 0.5], seed + seed_offset + 500)
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
            haze_field = _noise(shape, [56, 112], [0.5, 0.5], seed + seed_offset + 510)
            haze = np.clip(haze_field * 0.5 + 0.5, 0, 1) * 0.25
            bright_g = bright * (0.4 + orb_pts * 0.60)  # brightness at discrete orb points
            # Bioluminescent green-gold: 557nm luciferase peak = warm green-yellow
            result[:,:,0] = np.clip(result[:,:,0] + bright_g * 0.65 + haze * blend * 0.12, 0, 1)
            result[:,:,1] = np.clip(result[:,:,1] + bright_g * 1.65 + haze * blend * 0.30, 0, 1)
            result[:,:,2] = np.clip(result[:,:,2] + bright_g * 0.10 + haze * blend * 0.05, 0, 1)
        result = np.clip(result + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return result
    return spec_fn, paint_fn

spec_sparkle_diamond_dust, paint_sparkle_diamond_dust = _make_sparkle_fusion("fine", 60, 80, 7400)
spec_sparkle_starfield, paint_sparkle_starfield = _make_sparkle_fusion("coarse", 40, 90, 7410)
spec_sparkle_galaxy, paint_sparkle_galaxy = _make_sparkle_fusion("fine", 50, 70, 7420)
spec_sparkle_firefly, paint_sparkle_firefly = _make_sparkle_fusion("coarse", 70, 60, 7430)
spec_sparkle_snowfall, paint_sparkle_snowfall = _make_sparkle_fusion("fine", 80, 50, 7440)
spec_sparkle_champagne, paint_sparkle_champagne = _make_sparkle_fusion("medium", 90, 45, 7450)
spec_sparkle_meteor, paint_sparkle_meteor = _make_sparkle_fusion("coarse", 55, 85, 7460)
spec_sparkle_constellation, paint_sparkle_constellation = _make_sparkle_fusion("fine", 45, 75, 7470)
spec_sparkle_confetti, paint_sparkle_confetti = _make_sparkle_fusion("medium", 75, 55, 7480)
spec_sparkle_lightning_bug, paint_sparkle_lightning_bug = _make_sparkle_fusion("coarse", 50, 80, 7490)


# ================================================================
# PARADIGM 6: MULTI-SCALE TEXTURE - Layered texture systems
# ================================================================

def _make_multiscale_fusion(texture_profile, seed_offset=0):
    """Factory: 4+ distinct texture scales working together multiplicatively.
    Macro (128px+): large material zones. Meso (16-64px): surface detail.
    Micro (4-8px): grain/texture. Nano (1-2px): sparkle/flake.
    Each scale has independent M/R/CC behavior with scale-dependent transfer functions."""

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        rng = np.random.RandomState(seed + seed_offset)

        # === MACRO SCALE (128px+): large material zone shapes ===
        macro = _noise(shape, [128, 256], [0.5, 0.5], seed + seed_offset)
        macro = np.clip(macro * 0.5 + 0.5, 0, 1)
        # Blend with a second noise octave for organic shapes
        macro_warped = _noise(shape, [96, 192], [0.5, 0.5], seed + seed_offset + 30)
        macro = np.clip(macro * 0.6 + np.clip(macro_warped * 0.5 + 0.5, 0, 1) * 0.4, 0, 1)

        # === MESO SCALE (16-64px): surface detail patterns ===
        meso = _noise(shape, [16, 32, 64], [0.25, 0.40, 0.35], seed + seed_offset + 100)
        meso = np.clip(meso * 0.5 + 0.5, 0, 1)

        # === MICRO SCALE (4-8px): grain/texture ===
        micro = _noise(shape, [4, 6, 8], [0.3, 0.4, 0.3], seed + seed_offset + 200)
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
        elif s == 7550:  # chrome_sand: nano dominates
            M_macro = macro * 20 + 230
            M_meso = meso * 10
            M_micro = micro * 8
            M_nano = nano_thresh * 25
            R_macro = (1 - macro) * 15
            R_meso = meso * 10
            R_micro = micro * 20
            R_nano = (1 - nano_thresh) * 40  # sand = rough between sparkles
            CC_base = 5.0
        elif s == 7560:  # matte_silk: macro=sheen zones, R inverted
            M_macro = macro * 30
            M_meso = meso * 15
            M_micro = micro * 8
            M_nano = nano_thresh * 10
            R_macro = macro * 80 + 60        # large features smooth(ish)
            R_meso = (1 - meso) * 40
            R_micro = micro * 30
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
        """Multiscale textures: COLORSHOXX-style color zones married to macro texture field.
        UPGRADED: Adds warm/cool/edge color zones ON TOP of per-profile texture effects.
        - High-macro zones: warm color push (amber/gold tint) + brightening
        - Low-macro zones: cool shadow push (desaturate toward grey, darken, retain blue)
        - Edges (Sobel on macro): bright warm-white rim highlight"""
        h, w = shape
        result = paint.copy()
        s = seed_offset % 10000

        # Macro-scale brightness modulation (also used as pv for color zones)
        macro = _noise(shape, [128, 256], [0.5, 0.5], seed + seed_offset)
        macro = np.clip(macro * 0.5 + 0.5, 0, 1)
        # Meso detail
        meso = _noise(shape, [16, 32, 64], [0.25, 0.40, 0.35], seed + seed_offset + 100)
        meso = np.clip(meso * 0.5 + 0.5, 0, 1)

        if s == 7500:    # chrome_grain: horizontal streaks
            streak = _noise(shape, [2, 4], [0.5, 0.5], seed + seed_offset + 300)
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
            sand = _noise(shape, [2, 3, 5], [0.4, 0.35, 0.25], seed + seed_offset + 300)
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] + sand * 0.14 * pm * mask, 0, 1)
        elif s == 7560:  # matte_silk: smooth sheen
            y_n = np.linspace(0, 1, h).reshape(h, 1).astype(np.float32)
            sheen = np.sin(y_n * np.pi) * 0.14 * pm
            for c in range(3):
                result[:,:,c] = np.clip(paint[:,:,c] + sheen * mask, 0, 1)
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
            frost_a = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 300)
            frost_b = _noise(shape, [3, 6, 12], [0.4, 0.35, 0.25], seed + seed_offset + 400)
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
        warp_warp = _noise(shape, [32, 64], [0.5, 0.5], seed + seed_offset + 20)
        warped_grad = np.clip(grad + warp1 * 0.25 + warp2 * warp_warp * 0.12, 0, 1)

        s = seed_offset % 10000
        if s == 7600:  # sun_fade: UV exposure from top, gradient from exposed to protected
            exposure = warped_grad  # top = exposed
            # UV-faded areas: lose metallic, become rough, clearcoat degrades
            M = np.clip(200 - exposure * 180 * sm, 0, 255)
            R = np.clip(30 + exposure * 170 * sm, 0, 255)
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
            spots = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            spot_mask = np.clip((spots - 0.35) * 4.0, 0, 1)
            # Acid etching: roughens surface, strips metallic, damages clearcoat
            etch_depth = spot_mask * warped_grad
            M = np.clip(190 - etch_depth * 170 * sm, 0, 255)
            R = np.clip(35 + etch_depth * 185 * sm, 0, 255)
            CC = np.clip(16 + etch_depth * 159 * sm, 16, 255)
            # Chemical staining at spot edges
            edge_ring = np.exp(-((spot_mask - 0.5)**2) * 30) * warped_grad
            R = R + edge_ring * 35 * sm

        elif s == 7630:  # desert_blast: sand erosion
            sand_exposure = warped_grad
            # Sand-blasted: stripped of clearcoat, heavily roughened
            M = np.clip(195 - sand_exposure * 160 * sm, 0, 255)
            R = np.clip(40 + sand_exposure * 190 * sm, 0, 255)
            CC = np.clip(16 + sand_exposure * 189 * sm, 16, 255)
            # Wind-streak patterns
            streak = _noise(shape, [2, 64], [0.6, 0.4], seed + seed_offset + 100)
            streaks = np.clip(np.abs(streak) - 0.3, 0, 1) * sand_exposure
            R = R + streaks * 40 * sm

        elif s == 7640:  # ice_storm: frost and ice damage from bottom up
            ice_grad = 1.0 - warped_grad  # bottom = worst
            # Ice crystal pattern
            ice_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            ice_pattern = np.clip(ice_noise * ice_grad * 2, 0, 1)
            # Icy areas: high roughness (frost), moderate metallic, heavy CC
            M = np.clip(220 - ice_pattern * 130 * sm, 0, 255)
            R = np.clip(25 + ice_pattern * 160 * sm, 0, 255)
            CC = np.clip(16 + ice_pattern * 164 * sm, 16, 255)
            # Ice crystal edges are extra rough
            crystal_edge = _noise(shape, [2, 4, 6], [0.3, 0.4, 0.3], seed + seed_offset + 200)
            edge_mask = np.exp(-np.abs(ice_noise) * 8) * ice_grad
            R = R + edge_mask * 50 * sm

        elif s == 7650:  # road_spray: bottom-up road grime
            spray_grad = 1.0 - warped_grad  # bottom = worst
            # Layered grime: fine spray + heavier splatter
            fine_spray = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            fine_spray = np.clip(fine_spray * spray_grad * 2, 0, 1)
            splatter = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 200)
            splat_mask = np.clip((splatter - 0.3) * 3.0 * spray_grad, 0, 1)
            combined = np.clip(fine_spray * 0.6 + splat_mask * 0.4, 0, 1)
            # Grime: kills metallic, maxes roughness
            M = np.clip(200 - combined * 190 * sm, 0, 255)
            R = np.clip(45 + combined * 175 * sm, 0, 255)
            CC = np.clip(20 + combined * 150 * sm, 16, 255)

        elif s == 7660:  # hood_bake: heat damage on hood/roof areas
            heat_exposure = warped_grad  # top = hottest
            # Thermal cycling: clearcoat crazing, paint oxidation
            craze = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            craze_mask = np.clip(np.abs(craze) * heat_exposure * 3, 0, 1)
            M = np.clip(210 - heat_exposure * 100 * sm - craze_mask * 50 * sm, 0, 255)
            R = np.clip(30 + heat_exposure * 120 * sm + craze_mask * 60 * sm, 0, 255)
            CC = np.clip(200 * (1 - heat_exposure * sm) + craze_mask * 80 * sm, 16, 255)

        elif s == 7670:  # barn_dust: dust accumulation in recesses
            # Cavity-filling: smooth tops clean, recessed areas dusty
            cavity = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + seed_offset + 100)
            dust_mask = np.clip((cavity + 0.3) * warped_grad * 1.5, 0, 1)
            # Dust: zero metallic, very high roughness
            M = np.clip(185 - dust_mask * 175 * sm, 0, 255)
            R = np.clip(50 + dust_mask * 170 * sm, 0, 255)
            CC = np.clip(16 + dust_mask * 129 * sm, 16, 255)
            # Dust settles in noise patterns
            fine_dust = _noise(shape, [2, 4], [0.5, 0.5], seed + seed_offset + 200)
            R = R + np.abs(fine_dust) * 20 * dust_mask * sm

        elif s == 7680:  # ocean_mist: salt air corrosion
            salt_exposure = np.clip(warped_grad * 0.7 + 0.15, 0, 1)
            # Oxidation patches expanding from random seed points
            ox_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + seed_offset + 100)
            ox_mask = np.clip((ox_noise - 0.1) * 2.5 * salt_exposure, 0, 1)
            # Oxidized: low M, high R, damaged CC
            M = np.clip(195 - ox_mask * 165 * sm, 0, 255)
            R = np.clip(40 + ox_mask * 180 * sm, 0, 255)
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
            R = np.clip(55 + ash_mask * 195 * sm, 0, 255)
            CC = np.clip(16 + ash_mask * 184 * sm, 16, 255)
            # Heat-warped spots under ash
            heat = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 200)
            heat_spots = np.clip((heat - 0.4) * 3.0 * ash_fall, 0, 1)
            M = M + heat_spots * 40 * sm  # heat can reveal metal

        # Rain streaks: vertical thin bright lines (applied to all weather types)
        rain = _noise(shape, [2, 128], [0.7, 0.3], seed + seed_offset + 500)
        rain_streaks = np.clip(np.abs(rain) - 0.6, 0, 1) * 2.5 * warped_grad
        R = np.clip(R + rain_streaks * 25 * sm, 15, 255)  # GGX floor

        M = np.clip(M, 0, 255)
        R = np.clip(R, 15, 255)  # GGX floor
        CC = np.clip(CC, 16, 255)
        return _spec_out(shape, mask, M, R, CC)

    def paint_fn(paint, shape, mask, seed, pm, bb):
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
            spots = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + seed_offset + 100)
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
            cavity = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + seed_offset + 100)
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
            darken = ash_mask * 0.22 * pm
            for c in range(3):
                result[:,:,c] = np.clip(result[:,:,c] - darken * mask, 0, 1)
            # Warm undertone from heat
            result[:,:,0] = np.clip(result[:,:,0] + ash_mask * 0.04 * pm * mask, 0, 1)

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
    rng = np.random.RandomState(seed + 7700)
    # --- Voronoi caustic network ---
    n_pts = 60
    pts_y = rng.rand(n_pts).astype(np.float32) * h
    pts_x = rng.rand(n_pts).astype(np.float32) * w
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    # Domain warp the coordinates for organic caustic shapes
    warp_y = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7701)
    warp_x = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7702)
    yf_w = yf + warp_y * 40
    xf_w = xf + warp_x * 40
    d1 = np.full((h, w), 1e9, dtype=np.float32)  # nearest
    d2 = np.full((h, w), 1e9, dtype=np.float32)  # second nearest
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
    CC = np.clip(16.0 + (1.0 - caustic) * 120 - caustic * 12, 4, 160)
    # Swimming-pool ripple modulation
    ripple = np.sin(film_thickness * 18.0 + warp_y * 8.0) * 0.5 + 0.5
    CC = np.clip(CC + ripple * 40 * sm, 4, 200)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_glass(paint, shape, mask, seed, pm, bb):
    h, w = shape
    rng = np.random.RandomState(seed + 7700)
    n_pts = 60
    pts_y = rng.rand(n_pts).astype(np.float32) * h
    pts_x = rng.rand(n_pts).astype(np.float32) * w
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    warp_y = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7701)
    warp_x = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7702)
    yf_w = yf + warp_y * 40
    xf_w = xf + warp_x * 40
    d1 = np.full((h, w), 1e9, dtype=np.float32)
    for py, px in zip(pts_y, pts_x):
        d = np.sqrt((yf_w - py)**2 + (xf_w - px)**2)
        d1 = np.minimum(d1, d)
    film = d1 / (np.percentile(d1, 90) + 1e-6)
    # Thin-film interference: rainbow color shift
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + np.sin(film * 12.0) * 0.12 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + np.sin(film * 12.0 + 2.094) * 0.10 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + np.sin(film * 12.0 + 4.189) * 0.14 * pm * mask, 0, 1)
    # Brighten caustic network lines
    caustic_n = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 7703)
    bright = np.exp(-np.abs(caustic_n) * 3.0) * 0.15 * pm
    for c in range(3):
        result[:,:,c] = np.clip(result[:,:,c] + bright * mask, 0, 1)
    return result

spec_exotic_glass_paint = _spec_exotic_glass
paint_exotic_glass_paint = _paint_exotic_glass

# 2. EXOTIC FOGGY CHROME - Condensation physics chrome with multi-scale droplets
def _spec_exotic_foggy_chrome(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.RandomState(seed + 7710)
    # --- 3-scale Voronoi droplet simulation ---
    droplet_field = np.zeros((h, w), dtype=np.float32)
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    for scale_idx, (n_pts, radius, weight) in enumerate([
        (15, 80, 0.5),   # large merged drops
        (80, 30, 0.3),   # medium drops
        (400, 8, 0.2),   # tiny beads
    ]):
        pts_y = rng.rand(n_pts).astype(np.float32) * h
        pts_x = rng.rand(n_pts).astype(np.float32) * w
        min_d = np.full((h, w), 1e9, dtype=np.float32)
        for py, px in zip(pts_y, pts_x):
            d = np.sqrt((yf - py)**2 + (xf - px)**2)
            min_d = np.minimum(min_d, d)
        drop = np.clip(1.0 - min_d / radius, 0, 1)
        drop = drop ** 2.0  # quadratic falloff for realistic droplet profile
        droplet_field += drop * weight
    droplet_field = np.clip(droplet_field, 0, 1)
    M = np.clip(255.0 - droplet_field * 40 * sm, 210, 255)
    G = np.clip(2.0 + droplet_field * 180 * sm, 2, 200)
    # Droplet edges have ultra-smooth meniscus (surface tension)
    edge_detect = np.abs(np.gradient(droplet_field, axis=0)) + np.abs(np.gradient(droplet_field, axis=1))
    edge_detect = np.clip(edge_detect * 15, 0, 1)
    G = np.clip(G - edge_detect * 80 * sm, 0, 200)
    CC = np.clip(16.0 + droplet_field * 100 + (1.0 - droplet_field) * 20, 16, 140)
    micro = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + 7712)
    G = np.clip(G + micro * 12 * sm * droplet_field, 0, 220)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_foggy_chrome(paint, shape, mask, seed, pm, bb):
    rng = np.random.RandomState(seed + 7710)
    h, w = shape
    droplet_field = np.zeros((h, w), dtype=np.float32)
    y_g, x_g = _mgrid(shape)
    yf, xf = y_g.astype(np.float32), x_g.astype(np.float32)
    for n_pts, radius, weight in [(15, 80, 0.5), (80, 30, 0.3), (400, 8, 0.2)]:
        pts_y = rng.rand(n_pts).astype(np.float32) * h
        pts_x = rng.rand(n_pts).astype(np.float32) * w
        min_d = np.full((h, w), 1e9, dtype=np.float32)
        for py, px in zip(pts_y, pts_x):
            d = np.sqrt((yf - py)**2 + (xf - px)**2)
            min_d = np.minimum(min_d, d)
        drop = np.clip(1.0 - min_d / radius, 0, 1) ** 2.0
        droplet_field += drop * weight
    droplet_field = np.clip(droplet_field, 0, 1)
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
def _spec_exotic_inverted_candy(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.RandomState(seed + 7720)
    U = np.ones((h, w), dtype=np.float32)
    V = np.zeros((h, w), dtype=np.float32)
    for _ in range(25):
        cy, cx = rng.randint(0, max(1,h)), rng.randint(0, max(1,w))
        r = rng.randint(5, 20)
        y1, y2 = max(0, cy-r), min(h, cy+r)
        x1, x2 = max(0, cx-r), min(w, cx+r)
        V[y1:y2, x1:x2] = 1.0
        U[y1:y2, x1:x2] = 0.5
    f_rate, k_rate = 0.055, 0.062
    def _lap_ic(arr):
        pad = np.pad(arr, 1, mode="wrap")
        return (pad[:-2,1:-1] + pad[2:,1:-1] + pad[1:-1,:-2] + pad[1:-1,2:] - 4*arr) * 0.25
    for _ in range(60):
        uvv = U * V * V
        U = np.clip(U + 0.16 * _lap_ic(U) - uvv + f_rate * (1.0 - U), 0, 1)
        V = np.clip(V + 0.08 * _lap_ic(V) + uvv - (f_rate + k_rate) * V, 0, 1)
    turing = V / (V.max() + 1e-6)
    M = np.clip((1.0 - turing) * 240 * sm + turing * 15, 0, 255)
    G = np.clip(turing * 220 * sm + (1.0 - turing) * 5, 0, 240)
    CC = np.clip((1.0 - turing) * 200 + turing * 16, 16, 220)
    fine = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 7721)
    M = np.clip(M + fine * 15 * sm, 0, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_inverted_candy(paint, shape, mask, seed, pm, bb):
    h, w = shape
    rng = np.random.RandomState(seed + 7720)
    U = np.ones((h, w), dtype=np.float32)
    V = np.zeros((h, w), dtype=np.float32)
    for _ in range(25):
        cy, cx = rng.randint(0, max(1,h)), rng.randint(0, max(1,w))
        r = rng.randint(5, 20)
        y1, y2 = max(0, cy-r), min(h, cy+r)
        x1, x2 = max(0, cx-r), min(w, cx+r)
        V[y1:y2, x1:x2] = 1.0
        U[y1:y2, x1:x2] = 0.5
    def _lap_ic(arr):
        pad = np.pad(arr, 1, mode="wrap")
        return (pad[:-2,1:-1] + pad[2:,1:-1] + pad[1:-1,:-2] + pad[1:-1,2:] - 4*arr) * 0.25
    for _ in range(60):
        uvv = U * V * V
        U = np.clip(U + 0.16 * _lap_ic(U) - uvv + 0.055 * (1.0 - U), 0, 1)
        V = np.clip(V + 0.08 * _lap_ic(V) + uvv - 0.117 * V, 0, 1)
    turing = V / (V.max() + 1e-6)
    result = paint.copy()
    hue_phase = _noise(shape, [32, 64], [0.5, 0.5], seed + 7725) * 3.14
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
    warp2 = _noise(shape, [8, 24, 48], [0.35, 0.4, 0.25], seed + 7731)
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
    fringe = _noise(shape, [2, 4], [0.5, 0.5], seed + 7742)
    G = np.clip(G + fringe * 20 * sm * interference, 0, 160)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_phantom_mirror(paint, shape, mask, seed, pm, bb):
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
    n0 = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 7760)
    # BUG-FUSIONS-001 FIX: warp fields now applied via map_coordinates (were computed but never used)
    from scipy.ndimage import map_coordinates as _mc
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    warp1y = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7761) * h * np.float32(0.09)
    warp1x = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7762) * w * np.float32(0.09)
    n1_base = _noise(shape, [12, 24, 48], [0.3, 0.4, 0.3], seed + 7763)
    n1 = _mc(n1_base, [np.clip(yy + warp1y, 0, h - 1), np.clip(xx + warp1x, 0, w - 1)],
             order=1, mode='nearest').astype(np.float32)
    warp2y = _noise(shape, [24, 48], [0.5, 0.5], seed + 7764) * h * np.float32(0.07)
    warp2x = _noise(shape, [24, 48], [0.5, 0.5], seed + 7765) * w * np.float32(0.07)
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
    micro = _noise(shape, [2, 4], [0.5, 0.5], seed + 7767)
    M = np.clip(M + micro * 20 * sm, 0, 255)
    G = np.clip(G + micro * 15 * sm, 0, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_anti_metal(paint, shape, mask, seed, pm, bb):
    """Anti-metal paint with domain-warp + 3-zone material concept. Uses the same warp
    hierarchy as the spec function (seeds 7761-7766) for spatial consistency.
    Zone A (t_sharp->1): absorption zone — cool desaturated void (R--, B++).
    Zone B (t_sharp->0): metallic zone — paint preserved.
    Boundary (t_sharp~0.5): narrow photonic emission band — warm interference glow."""
    h, w = shape
    from scipy.ndimage import map_coordinates as _mc
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Mirror spec function warp hierarchy exactly (same seeds)
    n0 = _noise(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 7760)
    warp1y = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7761) * h * np.float32(0.09)
    warp1x = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 7762) * w * np.float32(0.09)
    n1_base = _noise(shape, [12, 24, 48], [0.3, 0.4, 0.3], seed + 7763)
    n1 = _mc(n1_base, [np.clip(yy + warp1y, 0, h - 1), np.clip(xx + warp1x, 0, w - 1)],
             order=1, mode='nearest').astype(np.float32)
    warp2y = _noise(shape, [24, 48], [0.5, 0.5], seed + 7764) * h * np.float32(0.07)
    warp2x = _noise(shape, [24, 48], [0.5, 0.5], seed + 7765) * w * np.float32(0.07)
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
    CC = np.clip(16.0 + crystal_interior * 8 - bragg_intersect * 12 + single_edge * 60, 4, 120)
    interference = np.sin(edge_sum * 18.85) * 0.5 + 0.5
    G = np.clip(G + interference * 30 * sm * single_edge, 0, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_crystal_clear(paint, shape, mask, seed, pm, bb):
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
    fine = _noise(shape, [4, 8], [0.5, 0.5], seed + 7782)
    M = np.clip(M + fine * 15 * sm * einstein_ring, 0, 160)
    return _spec_out(shape, mask, M, G, CC)

def _paint_exotic_dark_glass(paint, shape, mask, seed, pm, bb):
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
    n1 = _noise(shape, [12, 24, 48], [0.3, 0.4, 0.3], seed + 7790)
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
    h, w = shape
    n1 = _noise(shape, [12, 24, 48], [0.3, 0.4, 0.3], seed + 7790)
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


# ================================================================
# PARADIGM 9: TRI-ZONE MATERIAL FENCING - 3 materials in 1 zone
# ================================================================

def _voronoi_3zone(shape, seed, seed_offset):
    """Voronoi-based 3-zone partitioning with domain warp.
    Returns (zone_a, zone_b, zone_c, boundary) fields, each (h,w) float32 0-1."""
    h, w = shape
    rng = np.random.RandomState(seed + seed_offset)

    # 3 seed clusters — each cluster has multiple points for organic shapes
    n_per_cluster = max(5, (h * w) // (200 * 200))
    centers = []
    # Cluster A: upper-left tendency, B: center, C: lower-right tendency
    cluster_centers = [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)]
    for ci, (cy, cx) in enumerate(cluster_centers):
        for _ in range(n_per_cluster):
            py = np.clip(rng.normal(cy, 0.25), 0, 1) * h
            px = np.clip(rng.normal(cx, 0.25), 0, 1) * w
            centers.append((py, px, ci))

    y, x = _mgrid(shape)
    yf, xf = y.astype(np.float32), x.astype(np.float32)

    # Domain warp the coordinates for organic boundary shapes
    warp_y = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + seed_offset + 700)
    warp_x = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + seed_offset + 701)
    warp_amp = min(h, w) * 0.08
    yf_w = yf + warp_y * warp_amp
    xf_w = xf + warp_x * warp_amp

    # Compute distance to nearest point in each cluster
    dist_clusters = [np.full((h, w), 1e9, dtype=np.float32) for _ in range(3)]
    for py, px, ci in centers:
        d = np.sqrt((yf_w - py) ** 2 + (xf_w - px) ** 2)
        dist_clusters[ci] = np.minimum(dist_clusters[ci], d)

    d_a, d_b, d_c = dist_clusters

    # Soft Gaussian falloff assignment: probability of each zone
    sigma = min(h, w) * 0.15  # falloff width
    w_a = np.exp(-(d_a ** 2) / (2 * sigma ** 2))
    w_b = np.exp(-(d_b ** 2) / (2 * sigma ** 2))
    w_c = np.exp(-(d_c ** 2) / (2 * sigma ** 2))

    total = w_a + w_b + w_c + 1e-8
    zone_a = w_a / total
    zone_b = w_b / total
    zone_c = w_c / total

    # Boundary detection using gradient magnitude of zone assignments
    # A boundary exists where no single zone dominates
    max_zone = np.maximum(zone_a, np.maximum(zone_b, zone_c))
    # boundary = 1 when max_zone ~ 0.33 (all equal), 0 when max_zone ~ 1.0
    boundary = np.clip(1.0 - (max_zone - 0.4) * 4.0, 0, 1)
    # Sharpen boundary with gradient magnitude
    grad_y = np.abs(np.diff(max_zone, axis=0, prepend=max_zone[:1, :]))
    grad_x = np.abs(np.diff(max_zone, axis=1, prepend=max_zone[:, :1]))
    edge_mag = np.clip((grad_y + grad_x) * 12, 0, 1)
    boundary = np.clip(boundary + edge_mag, 0, 1)

    return zone_a, zone_b, zone_c, boundary


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
        rng = np.random.RandomState(seed + seed_offset + 720)
        speckle_raw = rng.randn(max(1, h // 3), max(1, w // 3)).astype(np.float32)
        img = Image.fromarray((speckle_raw * 127 + 128).clip(0, 255).astype(np.uint8))
        speckle_b = np.array(img.resize((w, h), Image.NEAREST)).astype(np.float32) / 127.0 - 1.0
        # Zone C: smooth with subtle low-freq variation
        smooth_c = _noise(shape, [32, 64], [0.5, 0.5], seed + seed_offset + 730)

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

        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        """Trizone: COLORSHOXX-style three distinct color zones married to Voronoi zones.
        UPGRADED: Was basic tint-only. Now creates real color zones:
        - Zone A (warm): amber/gold push (+red, +slight green, -blue) + brightening
        - Zone B (cool): desaturate toward grey, darken, retain some blue
        - Zone C (neutral): slight brightness boost, balanced color
        - Boundaries: bright warm-white rim highlight"""
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

        result = np.clip(result + bb * 0.4 * mask[:,:,np.newaxis], 0, 1)
        return result
    return spec_fn, paint_fn

# Chrome / Candy / Matte
spec_trizone_chrome_candy_matte, paint_trizone_chrome_candy_matte = _make_trizone_fusion((255,2,16), (200,15,16), (0,200,180), 7800)
spec_trizone_pearl_carbon_gold, paint_trizone_pearl_carbon_gold = _make_trizone_fusion((100,40,16), (55,35,16), (255,2,16), 7810)
spec_trizone_frozen_ember_chrome, paint_trizone_frozen_ember_chrome = _make_trizone_fusion((225,140,16), (200,40,16), (255,2,16), 7820)
spec_trizone_anodized_candy_silk, paint_trizone_anodized_candy_silk = _make_trizone_fusion((170,80,100), (200,15,16), (30,85,16), 7830)
spec_trizone_vanta_chrome_pearl, paint_trizone_vanta_chrome_pearl = _make_trizone_fusion((0,255,255), (255,2,16), (100,40,16), 7840)
spec_trizone_glass_metal_matte, paint_trizone_glass_metal_matte = _make_trizone_fusion((0,0,16), (200,50,16), (0,200,180), 7850)
spec_trizone_mercury_obsidian_candy, paint_trizone_mercury_obsidian_candy = _make_trizone_fusion((255,3,16), (130,6,16), (200,15,16), 7860)
spec_trizone_titanium_copper_chrome, paint_trizone_titanium_copper_chrome = _make_trizone_fusion((180,70,80), (190,55,16), (255,2,16), 7870)
spec_trizone_ceramic_flake_satin, paint_trizone_ceramic_flake_satin = _make_trizone_fusion((60,8,16), (240,12,16), (0,100,120), 7880)
spec_trizone_stealth_spectra_frozen, paint_trizone_stealth_spectra_frozen = _make_trizone_fusion((30,220,180), (245,8,16), (225,140,16), 7890)


# ================================================================
# PARADIGM 10: DEPTH ILLUSION via CC Roughness - 3D from flat
# ================================================================

def _make_depth_fusion(base_m, base_g, cc_deep, cc_shallow, pattern_type, seed_offset=0):
    """Factory: CC roughness creates real 3D depth illusion through PBR spec.
    Each pattern uses advanced simulation for convincing depth."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_depth_fusion(base_m, base_g, cc_deep, cc_shallow, pattern_type, seed_offset))
    def _compute_depth_pattern(shape, seed):
        """Compute the actual depth pattern field pv (0-1) for the given pattern_type."""
        h, w = shape
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)
        warp1 = _noise(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + seed_offset + 700)
        warp2 = _noise(shape, [12, 24, 48], [0.3, 0.4, 0.3], seed + seed_offset + 701)
        warp_s = min(h, w) * 0.15
        yw, xw = yf + warp1 * warp_s, xf + warp2 * warp_s

        if pattern_type == "canyon":
            n1 = _noise(shape, [4, 8, 16, 32], [0.15, 0.25, 0.35, 0.25], seed + seed_offset)
            n2 = _noise(shape, [6, 12, 24], [0.3, 0.4, 0.3], seed + seed_offset + 50)
            ridge1 = 1.0 - np.abs(n1) * 2.0
            ridge2 = 1.0 - np.abs(n2) * 2.0
            erosion = np.clip(ridge1 * 0.6 + ridge2 * 0.4, 0, 1)
            pv = np.clip(erosion ** 1.8, 0, 1)
            dx = np.abs(np.diff(pv, axis=1, prepend=pv[:, :1]))
            dy = np.abs(np.diff(pv, axis=0, prepend=pv[:1, :]))
            ridge_edge = np.clip((dx + dy) * 8, 0, 1)
            pv = np.clip(pv + ridge_edge * 0.3, 0, 1)
        elif pattern_type == "bubble":
            y_n = np.linspace(-1, 1, h).reshape(h, 1).astype(np.float32)
            x_n = np.linspace(-1, 1, w).reshape(1, w).astype(np.float32)
            rng = np.random.RandomState(seed + seed_offset)
            pv = np.zeros((h, w), dtype=np.float32)
            highlight = np.zeros((h, w), dtype=np.float32)
            for _ in range(20):
                cy, cx = rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)
                r = rng.uniform(0.04, 0.18)
                dist = np.sqrt((y_n - cy)**2 + (x_n - cx)**2)
                dome = np.clip(1.0 - (dist / r) ** 2, 0, 1)
                rim_dist = np.clip(dist / r, 0, 1)
                fresnel = np.exp(-(rim_dist - 0.85)**2 / 0.02) * 0.8
                spec_cy, spec_cx = cy - r * 0.3, cx + r * 0.2
                spec_dist = np.sqrt((y_n - spec_cy)**2 + (x_n - spec_cx)**2)
                spec = np.exp(-spec_dist**2 / (r * 0.15)**2) * dome
                pv = np.maximum(pv, dome)
                highlight = np.maximum(highlight, fresnel + spec)
            pv = np.clip(pv * 0.7 + highlight * 0.3, 0, 1)
        elif pattern_type == "ripple":
            rng = np.random.RandomState(seed + seed_offset + 100)
            pv = np.zeros((h, w), dtype=np.float32)
            n_centers = 5
            for i in range(n_centers):
                cy = rng.uniform(0.15, 0.85) * h
                cx = rng.uniform(0.15, 0.85) * w
                freq = rng.uniform(0.06, 0.10)
                phase = rng.uniform(0, 2 * np.pi)
                dist = np.sqrt((yw - cy)**2 + (xw - cx)**2)
                amp = 1.0 / (1.0 + dist * 0.003)
                pv += np.sin(dist * freq + phase) * amp
            pv = np.clip(pv / n_centers * 0.5 + 0.5, 0, 1)
            pv = pv ** 1.5
        elif pattern_type == "scale":
            sz = max(18, min(h, w) // 22)
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
            pv = np.clip(dome * (1.0 - overlap * 0.5) + rim, 0, 1)
        elif pattern_type == "honeycomb":
            sz = max(16, min(h, w) // 22)
            hex_d = _hex_cell_dist(shape, sz)
            floor = np.clip(1.0 - hex_d * 2.5, 0, 1)
            wall = np.clip((hex_d - 0.4) * 4, 0, 1)
            wall_edge = np.exp(-(hex_d - 0.4)**2 / 0.005) * 0.7
            pv = np.clip(floor * 0.8 + wall_edge * 0.5 - wall * 0.3, 0, 1)
        elif pattern_type == "crack":
            rng = np.random.RandomState(seed + seed_offset + 100)
            n_pts = 50
            pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
            pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
            d1 = np.full((h, w), 1e9, dtype=np.float32)
            d2 = np.full((h, w), 1e9, dtype=np.float32)
            d3 = np.full((h, w), 1e9, dtype=np.float32)
            for py, px in zip(pts_y, pts_x):
                d = np.sqrt((yf - py)**2 + (xf - px)**2)
                upd1 = d < d1
                upd2 = (~upd1) & (d < d2)
                d3 = np.where(upd1, d2, np.where(upd2, d2, np.where(d < d3, d, d3)))
                d2 = np.where(upd1, d1, np.where(upd2, d, d2))
                d1 = np.minimum(d1, d)
            crack_edge = d2 - d1
            crack_norm = crack_edge / (np.percentile(crack_edge, 90) + 1e-6)
            cracks = np.exp(-crack_norm**2 * 6)
            triple = np.exp(-(d3 - d1)**2 / (np.percentile(d3 - d1, 50) + 1e-6)**2 * 2)
            pv = np.clip(cracks * 0.7 + triple * cracks * 0.5, 0, 1)
        elif pattern_type == "wave":
            freq1, freq2, freq3 = 0.02, 0.035, 0.015
            steep = 0.5
            phase1 = yw * freq1 + xw * freq1 * 0.6
            phase2 = yw * freq2 * 0.7 - xw * freq2
            phase3 = yw * freq3 + xw * freq3 * 1.2
            g1 = np.sin(phase1 - steep * np.sin(phase1))
            g2 = np.sin(phase2 - steep * np.sin(phase2)) * 0.5
            g3 = np.sin(phase3 - steep * np.sin(phase3)) * 0.3
            wave = np.clip((g1 + g2 + g3) * 0.3 + 0.5, 0, 1)
            foam = np.clip((wave - 0.7) * 5, 0, 1)
            pv = np.clip(wave * 0.8 + foam * 0.4, 0, 1)
        elif pattern_type == "pillow":
            sz = max(24, min(h, w) // 18)
            cell_y = (yw % sz).astype(np.float32) / sz
            cell_x = (xw % sz).astype(np.float32) / sz
            puff = np.sin(cell_y * np.pi) * np.sin(cell_x * np.pi)
            puff = puff ** 0.7
            sy = np.minimum(cell_y, 1.0 - cell_y)
            sx = np.minimum(cell_x, 1.0 - cell_x)
            stitch_d = np.minimum(sy, sx)
            stitch = np.clip(1.0 - stitch_d * 15, 0, 1)
            diag1 = np.abs(cell_y - cell_x)
            diag2 = np.abs(cell_y - (1.0 - cell_x))
            cross = np.clip(1.0 - np.minimum(diag1, diag2) * 20, 0, 1) * 0.3
            pv = np.clip(puff * (1.0 - stitch * 0.8) + cross * 0.2, 0, 1)
        elif pattern_type == "vortex":
            y_n = np.linspace(-1, 1, h).reshape(h, 1).astype(np.float32)
            x_n = np.linspace(-1, 1, w).reshape(1, w).astype(np.float32)
            warp_v = _noise(shape, [16, 32], [0.5, 0.5], seed + seed_offset + 500) * 0.1
            angle = np.arctan2(y_n + warp_v, x_n + warp_v)
            dist = np.sqrt(y_n**2 + x_n**2) + 0.001
            log_r = np.log(dist + 0.01)
            n_arms = 3
            spiral = np.sin(angle * n_arms - log_r * 10) * 0.5 + 0.5
            depth_envelope = np.clip(1.0 - dist * 0.8, 0.1, 1.0)
            spiral2 = np.sin(angle * (n_arms * 2) + log_r * 15) * 0.3 + 0.5
            pv = np.clip((spiral * 0.6 + spiral2 * 0.4) * depth_envelope, 0, 1)
        elif pattern_type == "erosion":
            terrain = _noise(shape, [8, 16, 32, 64, 128], [0.1, 0.15, 0.25, 0.3, 0.2], seed + seed_offset + 100)
            terrain = np.clip(terrain * 0.5 + 0.5, 0, 1)
            gy = np.diff(terrain, axis=0, prepend=terrain[:1, :])
            gx = np.diff(terrain, axis=1, prepend=terrain[:, :1])
            grad_mag = np.sqrt(gy**2 + gx**2)
            erosion = np.clip(grad_mag * 15, 0, 1)
            deposit = np.clip(1.0 - grad_mag * 20, 0, 1) * np.clip(1.0 - terrain, 0, 1)
            eroded = terrain * (1.0 - erosion * 0.6) + deposit * 0.2
            fine = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 200)
            pv = np.clip(eroded + fine * 0.05 * erosion, 0, 1)
        else:
            pv = np.zeros((h, w), dtype=np.float32)
        return pv

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        pv = _compute_depth_pattern(shape, seed)

        # M modulated by depth: raised = more metallic, deep = less
        M = np.clip(float(base_m) + pv * 45 * sm - (1 - pv) * 25 * sm, 0, 255)
        # G modulated: deep areas rougher, raised smoother
        G = np.clip(float(base_g) + (1 - pv) * 50 * sm - pv * 20 * sm, 0, 255)
        # CC range 16-200 for max depth impression
        CC = pv * float(cc_deep) + (1 - pv) * float(cc_shallow)
        n = _noise(shape, [8, 16], [0.5, 0.5], seed + seed_offset + 50)
        M = M + n * 10 * sm
        G = G + n * 8 * sm
        # Sobel edge detection for rim lighting at depth transitions
        pv_dx = np.abs(np.diff(pv, axis=1, prepend=pv[:, :1]))
        pv_dy = np.abs(np.diff(pv, axis=0, prepend=pv[:1, :]))
        edge = np.clip(np.sqrt(pv_dx**2 + pv_dy**2) * 8, 0, 1)
        M = np.clip(M + edge * 60 * sm, 0, 255)  # edges are bright metallic rim
        G = np.clip(G - edge * 25 * sm, 0, 255)   # edges are smooth
        CC = np.clip(CC, 16, 255)
        return _spec_out(shape, mask, M, G, CC)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        """Depth Illusion: COLORSHOXX-style color zones married to depth pattern.
        UPGRADED: Was brightness-only. Now:
        - Raised zones (pv>0.6): warm color push (amber/gold tint) + brightening
        - Deep zones (pv<0.3): cool shadow push (blue-grey desaturation) + darkening
        - Edges: bright warm-white rim highlight
        Same pv field drives both paint AND spec = married pair."""
        h, w = shape
        pv = _compute_depth_pattern(shape, seed)
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
    """Factory: spectacular glowing halos around pattern elements.
    Multi-scale halo: thin inner bright line + wider outer glow with Gaussian falloff.
    Center = diffuse matte/candy, Rim = mirror chrome (M=240-255, R=0-5)."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_halo_fusion(center_m, halo_m, base_g, base_cc, pattern_type, seed_offset))

    def _compute_halo_zones(dist):
        """Compute multi-scale halo zones from distance field.
        Returns (center, inner_halo, outer_glow) each 0-1."""
        # Center zone: interior of pattern element
        center = np.clip(1.0 - dist * 2.5, 0, 1)
        # Inner halo: thin bright chrome line at element boundary
        # Gaussian peak at dist~0.4 with narrow sigma
        inner = np.exp(-(dist - 0.42)**2 / 0.008)
        # Outer glow: wider falloff beyond the edge
        outer = np.exp(-(dist - 0.6)**2 / 0.04) * np.clip(dist - 0.3, 0, 1)
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
            warp = _noise(shape, [32, 64], [0.5, 0.5], seed + seed_offset + 300) * 15
            wave = np.sin((yf + warp) * 0.035 + xf * 0.015) * 0.5 + 0.5
            dist = np.abs(wave - 0.5) * 2.0
        elif pattern_type == "crack":
            # FBM iso-line crack network — zero-crossings of two noise fields at different
            # scales form independent crack families that intersect and branch.
            # Structurally distinct from voronoi: no seed points, no cell geometry —
            # pure continuous iso-line topology resembling crackle glaze or dried mud.
            crack_a = _noise(shape, [max(h // 6, 12), max(h // 12, 6)], [0.65, 0.35],
                             seed + seed_offset + 100)
            crack_b = _noise(shape, [max(h // 9, 8), max(h // 18, 4)], [0.60, 0.40],
                             seed + seed_offset + 101)
            ca_s = np.percentile(np.abs(crack_a), 95) + 1e-6
            cb_s = np.percentile(np.abs(crack_b), 95) + 1e-6
            iso_a = np.abs(crack_a) / ca_s   # near-0 at zero-crossings of field A
            iso_b = np.abs(crack_b) / cb_s   # near-0 at zero-crossings of field B
            # Primary cracks (coarser A) + secondary cracks (finer B, 0.7× weight)
            iso_min = np.minimum(iso_a, iso_b * 0.7)
            dist = np.clip(iso_min * 3.5, 0, 1)
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
        dist = _compute_halo_dist(shape, seed)

        # Multi-scale halo computation
        center, inner_halo, outer_glow = _compute_halo_zones(dist)
        halo_total = np.clip(inner_halo + outer_glow * 0.6, 0, 1)

        # M: center 20-60, rim 240-255
        M = float(center_m) * center + float(halo_m) * halo_total
        M = np.clip(M + (1 - center - halo_total) * (float(center_m) + float(halo_m)) * 0.3, 0, 255)
        # R: center 30-100 (diffuse), rim 0-5 (mirror)
        G = float(base_g) * center + 2.0 * inner_halo + 5.0 * outer_glow
        G = np.clip(G + (1 - center) * (1 - halo_total) * float(base_g) * 0.6, 0, 255)
        # CC: center gets clearcoat, halo rim = no clearcoat (pure metallic mirror)
        B = float(base_cc) * center + 16.0 * halo_total
        B = np.clip(B + (1 - center) * (1 - halo_total) * float(base_cc) * 0.4, 16, 255)
        # Subtle noise (preserve halo smoothness)
        n = _noise(shape, [4, 8], [0.5, 0.5], seed + seed_offset + 50)
        M = np.clip(M + n * 6 * sm * (1 - halo_total), 0, 255)
        G = np.clip(G + n * 4 * sm * (1 - halo_total), 0, 255)
        return _spec_out(shape, mask, M, G, B)
    def paint_fn(paint, shape, mask, seed, pm, bb):
        """Halo patterns: COLORSHOXX-style color zones married to halo dist field.
        UPGRADED: Was sheen/darken-only. Now creates real color zones:
        - Center (low dist): warm color push (amber/gold glow) + brightening
        - Outer zone (high dist): cool shadow push (desaturate, darken, retain blue)
        - Halo rim (inner_halo edge): bright warm-white rim highlight"""
        h, w = shape
        dist = _compute_halo_dist(shape, seed)
        center, inner_halo, outer_glow = _compute_halo_zones(dist)
        halo_glow = np.clip(inner_halo + outer_glow * 0.6, 0, 1)
        result = paint.copy()
        # Use inverted dist as pv: center=high, outer=low
        pv = np.clip(1.0 - dist, 0, 1)

        # --- High-pv zones (center): warm color push + brightening ---
        warm_zone = np.clip((pv - 0.4) * 2.5, 0, 1).astype(np.float32)
        warm_blend = warm_zone * 0.22 * pm
        result[:,:,0] = np.clip(result[:,:,0] + warm_blend * mask * 0.12, 0, 1)   # warm red push
        result[:,:,1] = np.clip(result[:,:,1] + warm_blend * mask * 0.06, 0, 1)   # slight gold
        result[:,:,2] = np.clip(result[:,:,2] - warm_blend * mask * 0.04, 0, 1)   # reduce blue = warmer
        bright = warm_zone * 0.15 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + bright * mask, 0, 1)

        # --- Low-pv zones (outer): cool desaturation + darkening ---
        cool_zone = np.clip((0.3 - pv) * 3.0, 0, 1).astype(np.float32)
        gray = (result[:,:,0] * 0.299 + result[:,:,1] * 0.587 + result[:,:,2] * 0.114)
        cool_desat = cool_zone * 0.20 * pm
        result[:,:,0] = np.clip(result[:,:,0] * (1 - cool_desat * mask) + gray * cool_desat * mask - cool_zone * 0.06 * pm * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] * (1 - cool_desat * mask) + gray * cool_desat * mask - cool_zone * 0.04 * pm * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] * (1 - cool_desat * mask * 0.7) + gray * cool_desat * mask * 0.7 + cool_zone * 0.03 * pm * mask, 0, 1)

        # --- Edges (halo rim): bright warm-white rim highlight ---
        rim = halo_glow * 0.22 * pm
        result[:,:,0] = np.clip(result[:,:,0] + rim * mask * 1.05, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] + rim * mask * 1.00, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] + rim * mask * 0.85, 0, 1)

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
    def _compute_wave(shape, yf, xf, seed):
        """Compute wave field 0-1 based on wave_type with domain warping."""
        h, w = shape
        # Domain warp for organic feel
        warp1 = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + seed_offset + 800)
        warp2 = _noise(shape, [24, 48, 96], [0.3, 0.4, 0.3], seed + seed_offset + 801)
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
            envelope = _noise(shape, [64, 128], [0.5, 0.5], seed + seed_offset + 300)
            envelope = np.clip(envelope * 0.5 + 0.7, 0.2, 1.0)
            cap1 = np.sin(yw * 0.12 + xw * 0.06) * 0.3
            cap2 = np.sin(yw * 0.08 - xw * 0.10) * 0.25
            cap3 = np.sin(yw * 0.15 + xw * 0.13) * 0.2
            fine = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 301) * 0.15
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
            # Airy function (diffraction pattern) from center point
            cy, cx = h / 2.0, w / 2.0
            dist = np.sqrt((yw - cy)**2 + (xw - cx)**2) + 1e-6
            x_norm = dist * 0.08
            airy = np.sin(x_norm) / (x_norm + 0.1)
            airy_intensity = airy ** 2
            wave = np.clip(airy_intensity / (np.max(airy_intensity) + 1e-6), 0, 1)
            # Secondary source for complexity
            cy2, cx2 = h * 0.35, w * 0.65
            dist2 = np.sqrt((yw - cy2)**2 + (xw - cx2)**2) + 1e-6
            x2 = dist2 * 0.06
            airy2 = (np.sin(x2) / (x2 + 0.1)) ** 2
            wave = np.clip(wave + airy2 / (np.max(airy2) + 1e-6) * 0.4, 0, 1)

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
            img_blur = Image.fromarray(np.clip(canvas * 255, 0, 255).astype(np.uint8))
            img_blur = img_blur.filter(ImageFilter.GaussianBlur(radius=5))
            wave = np.array(img_blur).astype(np.float32) / 255.0
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
        return wave

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)
        wave = _compute_wave(shape, yf, xf, seed)
        # R spans full 2-200 range for dramatic light band effect
        G = r_min + wave * (r_max - r_min) * sm
        # M tracks wave peaks: high M at crests = bright reflections
        M = np.clip(float(base_m) + (wave - 0.3) * 60 * sm, 0, 255)
        n = _noise(shape, [4, 8], [0.5, 0.5], seed + seed_offset + 50)
        M = M + n * 12 * sm
        # CC tracks wave inversely: smooth crests vs hazed troughs
        B = np.clip(float(base_cc) + (1 - wave) * 35 * sm, 16, 255)
        # Fine-scale texture riding the waves (more in troughs)
        n_fine = _noise(shape, [2, 4, 8], [0.3, 0.4, 0.3], seed + seed_offset + 150)
        G = G + n_fine * 15 * sm * (1 - wave)
        # Wave crest highlight via gradient energy
        wave_dx = np.abs(np.diff(wave, axis=1, prepend=wave[:, :1]))
        wave_dy = np.abs(np.diff(wave, axis=0, prepend=wave[:1, :]))
        edge_energy = np.clip((wave_dx + wave_dy) * 8, 0, 1)
        M = np.clip(M + edge_energy * 30 * sm, 0, 255)
        G = np.clip(G - edge_energy * 20 * sm, 0, 255)
        return _spec_out(shape, mask, M, G, B)

    def paint_fn(paint, shape, mask, seed, pm, bb):
        """Wave patterns: COLORSHOXX-style color zones married to wave field.
        UPGRADED: Was brightness/shimmer-only. Now creates real color zones:
        - Wave crests (high pv): warm color push (amber/gold tint) + brightening
        - Wave troughs (low pv): cool shadow push (desaturate toward grey, darken, retain blue)
        - Edges (Sobel): bright warm-white rim highlight"""
        h, w = shape
        y, x = _mgrid(shape)
        yf, xf = y.astype(np.float32), x.astype(np.float32)
        wave = _compute_wave(shape, yf, xf, seed)
        result = paint.copy()

        # --- High-pv zones (crests): warm color push + brightening ---
        crest = np.clip((wave - 0.4) * 2.5, 0, 1).astype(np.float32)
        warm_blend = crest * 0.22 * pm
        result[:,:,0] = np.clip(result[:,:,0] + warm_blend * mask * 0.12, 0, 1)   # warm red push
        result[:,:,1] = np.clip(result[:,:,1] + warm_blend * mask * 0.06, 0, 1)   # slight gold
        result[:,:,2] = np.clip(result[:,:,2] - warm_blend * mask * 0.04, 0, 1)   # reduce blue = warmer
        bright = crest * 0.18 * pm
        for c in range(3):
            result[:,:,c] = np.clip(result[:,:,c] + bright * mask, 0, 1)

        # --- Low-pv zones (troughs): cool desaturation + darkening ---
        trough = np.clip((0.3 - wave) * 3.0, 0, 1).astype(np.float32)
        gray = (result[:,:,0] * 0.299 + result[:,:,1] * 0.587 + result[:,:,2] * 0.114)
        cool_desat = trough * 0.20 * pm
        result[:,:,0] = np.clip(result[:,:,0] * (1 - cool_desat * mask) + gray * cool_desat * mask - trough * 0.06 * pm * mask, 0, 1)
        result[:,:,1] = np.clip(result[:,:,1] * (1 - cool_desat * mask) + gray * cool_desat * mask - trough * 0.04 * pm * mask, 0, 1)
        result[:,:,2] = np.clip(result[:,:,2] * (1 - cool_desat * mask * 0.7) + gray * cool_desat * mask * 0.7 + trough * 0.03 * pm * mask, 0, 1)

        # --- Edges (Sobel): bright warm-white rim highlight ---
        wave_dx = np.abs(np.diff(wave, axis=1, prepend=wave[:, :1]))
        wave_dy = np.abs(np.diff(wave, axis=0, prepend=wave[:1, :]))
        edge = np.clip(np.sqrt(wave_dx**2 + wave_dy**2) * 8, 0, 1)
        rim = edge * 0.20 * pm
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


# ================================================================
# PARADIGM 13: FRACTAL MATERIAL MIXING - 10 unique self-similar engines
# Each entry uses a fundamentally different fractal/chaos algorithm
# ================================================================

# 1. FRACTAL CHROME DECAY - Mandelbrot set edge detection drives metallic decay
def _mandelbrot_field(shape, cx=-0.75, cy=0.0, zoom=1.2, max_iter=80, seed=0):
    """Compute Mandelbrot escape-time field mapped onto shape."""
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
    return np.clip(escape / max_iter, 0, 1).astype(np.float32)

def _spec_fractal_chrome_decay(shape, mask, seed, sm):
    h, w = shape
    fractal = _mandelbrot_field(shape, seed=seed + 8200)
    # Edge detection: gradient magnitude of fractal field reveals boundary
    gy = np.diff(fractal, axis=0, prepend=fractal[:1, :])
    gx = np.diff(fractal, axis=1, prepend=fractal[:, :1])
    edge = np.clip(np.sqrt(gy**2 + gx**2) * 15, 0, 1)
    # Deep fractal (high iteration) = surviving chrome; low = corroded matte
    chrome = np.power(fractal, 0.7)
    decay_mix = chrome * (1.0 - edge * 0.6)
    M = np.clip(decay_mix * 255 * sm + (1 - decay_mix) * 5, 0, 255)
    G = np.clip((1 - decay_mix) * 220 * sm + decay_mix * 2, 0, 255)
    CC = np.clip(decay_mix * 16 + (1 - decay_mix) * 200 + edge * 80, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_chrome_decay(paint, shape, mask, seed, pm, bb):
    fractal = _mandelbrot_field(shape, seed=seed + 8200)
    corrosion = (1 - fractal)
    chrome = np.power(fractal, 0.7)
    result = paint.copy()
    # Increased coefficients + brightness variation (chrome bright, decay dark)
    bright = chrome * 0.15 * pm
    dark = corrosion * 0.10 * pm
    result[:,:,0] = np.clip(paint[:,:,0] + corrosion * 0.28 * pm * mask + bright * mask - dark * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] - corrosion * 0.12 * pm * mask + fractal * 0.08 * pm * mask + bright * mask - dark * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] - corrosion * 0.22 * pm * mask + bright * mask - dark * mask, 0, 1)
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
    rng = np.random.RandomState(seed + 8210)
    julia = _julia_field(shape, seed=seed + 8210)
    # Use Julia field as domain warp for Voronoi
    n_pts = 30
    pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
    y_g, x_g = _mgrid(shape)
    warp_strength = julia * 40
    yf = y_g.astype(np.float32) + warp_strength
    xf = x_g.astype(np.float32) + warp_strength * 0.8
    min_d = np.full((h, w), 1e9, np.float32)
    min_d2 = np.full((h, w), 1e9, np.float32)
    cell_id = np.zeros((h, w), dtype=np.int32)
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
    # Fractal chrome borders at edges
    M = np.clip(M_base * (1 - edge) + 255 * edge, 0, 255) * sm
    G = np.clip(R_base * (1 - edge) + 2 * edge, 0, 255)
    CC = np.clip(edge * 16 + (1 - edge) * 120, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_candy_chaos(paint, shape, mask, seed, pm, bb):
    h, w = shape
    rng = np.random.RandomState(seed + 8210)
    julia = _julia_field(shape, seed=seed + 8210)
    # Rebuild Voronoi cell_id for per-cell candy coloring
    n_pts = 30
    pts_y = rng.uniform(0, h, n_pts).astype(np.float32)
    pts_x = rng.uniform(0, w, n_pts).astype(np.float32)
    y_g, x_g = _mgrid(shape)
    warp_strength = julia * 40
    yf = y_g.astype(np.float32) + warp_strength
    xf = x_g.astype(np.float32) + warp_strength * 0.8
    min_d = np.full((h, w), 1e9, np.float32)
    cell_id = np.zeros((h, w), dtype=np.int32)
    for idx, (py, px) in enumerate(zip(pts_y, pts_x)):
        d = (yf - py)**2 + (xf - px)**2
        closer = d < min_d
        cell_id = np.where(closer, idx, cell_id)
        min_d = np.minimum(min_d, d)
    # Assign unique candy hue per cell using golden ratio spacing
    cell_hues = np.array([(i * 0.618033988749895) % 1.0 for i in range(n_pts)], dtype=np.float32)
    pixel_hue = cell_hues[cell_id]
    # Per-cell candy color shift
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + np.sin(pixel_hue * 6.2832) * 0.18 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + np.sin(pixel_hue * 6.2832 + 2.094) * 0.14 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + np.sin(pixel_hue * 6.2832 + 4.189) * 0.18 * pm * mask, 0, 1)
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
    w2a = _noise(shape, [24, 48], [0.5, 0.5], seed + 300)
    w2b = _noise(shape, [24, 48], [0.5, 0.5], seed + 400)
    w1a = w1a + w2a * 0.5
    w1b = w1b + w2b * 0.5
    # Layer 3 warp (warps the warp of the warp)
    w3a = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 500)
    w3b = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + 600)
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
        n = np.sin(yw * freq * 6.28 + _noise(shape, [max(2, 64 >> i)], [1.0], seed + 700 + i * 37) * 2) * \
            np.cos(xw * freq * 4.71 + _noise(shape, [max(2, 64 >> i)], [1.0], seed + 800 + i * 41) * 2)
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
    boundary_noise = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 8241)
    sierp_soft = np.clip(sierp + boundary_noise * 0.08, 0, 1)
    M = np.clip(sierp_soft * 255 * sm, 0, 255)
    G = np.clip((1 - sierp_soft) * 230 + sierp_soft * 2, 0, 255)
    CC = np.clip((1 - sierp_soft) * 200 + sierp_soft * 16, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_matte_chrome(paint, shape, mask, seed, pm, bb):
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
def _gray_scott_field(shape, seed, iterations=5):
    """Simplified Gray-Scott reaction-diffusion creating Turing patterns."""
    h, w = shape
    rng = np.random.RandomState(seed)
    U = np.ones((h, w), dtype=np.float32)
    V = np.zeros((h, w), dtype=np.float32)
    n_seeds = rng.randint(8, 20)
    for _ in range(n_seeds):
        sy, sx = rng.randint(0, h), rng.randint(0, w)
        sh, sw = rng.randint(h // 20, h // 8), rng.randint(w // 20, w // 8)
        V[sy:sy+sh, sx:sx+sw] = 1.0
    seed_noise = _noise(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 10)
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
    return U, V

def _spec_fractal_warm_cold(shape, mask, seed, sm):
    h, w = shape
    U, V = _gray_scott_field(shape, seed + 8250)
    blend = np.clip(V * 2.0, 0, 1)
    M = np.clip(blend * 30 + (1 - blend) * 245 * sm, 0, 255)
    G = np.clip(blend * 240 + (1 - blend) * 15, 0, 255)
    CC = np.clip(blend * 180 + (1 - blend) * 20, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_warm_cold(paint, shape, mask, seed, pm, bb):
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
def _rotated_ridge_fbm(shape, seed, octaves=6):
    """Ridge noise (1-|noise|) accumulated across octaves with 30deg rotation per octave.
    Uses rotated coordinates to warp the noise sampling via domain offset."""
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
        n = _noise(shape, [max(2, int(64 / freq))], [1.0], seed + i * 53)
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
    return ridges

def _spec_fractal_deep_organic(shape, mask, seed, sm):
    h, w = shape
    veins = _rotated_ridge_fbm(shape, seed + 8260)
    M = np.clip(veins * 220 * sm + (1 - veins) * 10, 0, 255)
    G = np.clip((1 - veins) * 200 + veins * 15, 0, 255)
    CC = np.clip(veins * 180 + (1 - veins) * 40, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_deep_organic(paint, shape, mask, seed, pm, bb):
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
def _dla_lightning(shape, seed, n_seeds=6, growth_steps=800):
    """DLA-approximated lightning: tree-like branching discharge from seed points.
    Uses frontier list instead of np.argwhere for performance."""
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
    glow = np.array(Image.fromarray((field * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius=3))).astype(np.float32) / 255.0
    result = np.clip(field * 0.7 + glow * 0.5, 0, 1)
    return result

def _spec_fractal_electric_noise(shape, mask, seed, sm):
    h, w = shape
    arcs = _dla_lightning(shape, seed + 8270)
    M = np.clip(arcs * 255 * sm + (1 - arcs) * 30, 0, 255)
    G = np.clip((1 - arcs) * 160 + arcs * 0, 0, 255)
    CC = np.clip(arcs * 16 + (1 - arcs) * 100, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_electric_noise(paint, shape, mask, seed, pm, bb):
    arcs = _dla_lightning(shape, seed + 8270)
    # Gaussian glow falloff instead of binary on/off
    # arcs already has blur glow from _dla_lightning; use smooth power curve
    glow_soft = np.power(arcs, 0.6)  # soften edges for gradual falloff
    glow_core = np.power(arcs, 2.0)  # bright core
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + glow_soft * 0.12 * pm * mask + glow_core * 0.08 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + glow_soft * 0.16 * pm * mask + glow_core * 0.10 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] + glow_soft * 0.25 * pm * mask + glow_core * 0.18 * pm * mask, 0, 1)
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
    lateral_warp = _noise(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 400) * 0.3
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
    M = np.clip(fire_m * 250 * sm + (1 - fire_m) * 5, 0, 255)
    G = np.clip((1 - fire_g) * 240 + fire_g * 3, 0, 255)
    CC = np.clip(fire_cc * 16 + (1 - fire_cc) * 160, 16, 255)
    return _spec_out(shape, mask, M, G, CC)

def _paint_fractal_liquid_fire(paint, shape, mask, seed, pm, bb):
    fire = _flame_simulation(shape, seed + 8290)
    result = paint.copy()
    result[:,:,0] = np.clip(paint[:,:,0] + fire * 0.30 * pm * mask - (1 - fire) * 0.08 * pm * mask, 0, 1)
    result[:,:,1] = np.clip(paint[:,:,1] + fire * 0.12 * pm * mask - (1 - fire) * 0.06 * pm * mask, 0, 1)
    result[:,:,2] = np.clip(paint[:,:,2] - fire * 0.10 * pm * mask - (1 - fire) * 0.04 * pm * mask, 0, 1)
    return result

spec_fractal_liquid_fire = _spec_fractal_liquid_fire
paint_fractal_liquid_fire = _paint_fractal_liquid_fire




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


def _spectral_field(shape, seed, seed_offset):
    """Domain-warped noise field with large scale variation for spectral mapping."""
    field = _noise(shape, [24, 48, 96, 192], [0.2, 0.3, 0.3, 0.2], seed + seed_offset)
    warp = _noise(shape, [32, 64, 128], [0.3, 0.4, 0.3], seed + seed_offset + 50)
    field = field + warp * 0.3
    return np.clip(field * 0.4 + 0.5, 0, 1).astype(np.float32)


def _make_spectral_fusion(mapping_type, m_range, g_range, base_cc, seed_offset=0):
    """Factory: spectral-reactive material properties with real wavelength mapping,
    thin-film interference, luminance reactivity, and photonic crystal behavior."""
    if _FF_V2 is not None:
        return _adapt_staging_factory_result(_FF_V2._make_spectral_fusion(mapping_type, m_range, g_range, base_cc, seed_offset))

    def spec_fn(shape, mask, seed, sm):
        h, w = shape
        field = _spectral_field(shape, seed, seed_offset)
        fine = _noise(shape, [4, 8], [0.5, 0.5], seed + seed_offset + 100)
        micro = _noise(shape, [2, 3], [0.5, 0.5], seed + seed_offset + 110)

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
            step = (field > np.float32(0.5)).astype(np.float32)
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
        """Spectral mapping: COLORSHOXX-style color zones married to spectral field.
        UPGRADED: Adds rainbow hue-rotation color push + warm/cool zones + edge rim
        ON TOP of per-mapping spectral effects.
        - High-field zones: spectral hue tint (rainbow push via cos mapping) + brightening
        - Low-field zones: cool shadow push (desaturate, darken, retain blue)
        - Edges (Sobel): bright warm-white rim highlight"""
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
            step = (field > np.float32(0.5)).astype(np.float32)
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


# ================================================================
# PARADIGM 15: MICRO-PANEL QUILTING - Material mosaic
# ================================================================

def _quilt_voronoi(shape, panel_size, seed, seed_offset):
    """Voronoi cell tessellation for quilting panels via cKDTree (fast).
    Returns (panel_id_map, min_dist, second_dist, n_pts) for grout line detection."""
    h, w = shape
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
        h, w = shape[:2]
        closest, min_d, second_d, n_pts = _quilt_voronoi(shape, panel_size, seed, seed_offset)

        rng_tint = np.random.RandomState(seed_offset + 999)
        tints = rng_tint.uniform(-0.14, 0.14, (_PALETTE_SIZE, 3)).astype(np.float32)
        idx = (closest % _PALETTE_SIZE)
        panel_tint = tints[idx, :]

        grout_width = max(2.0, panel_size * 0.06)
        grout = np.clip(1.0 - (second_d - min_d) / grout_width, 0, 1) ** 1.5

        out = np.zeros((h, w, 4), dtype=np.float32)
        out[:, :, :3] = np.clip(paint[:, :, :3] + panel_tint * pm * mask[:, :, np.newaxis] * (1 - grout[:, :, np.newaxis]), 0, 1)
        out[:, :, 3] = paint[:, :, 3] if paint.shape[2] > 3 else 1.0

        grout_bright = grout * 0.20 * pm
        for c in range(3):
            out[:, :, c] = np.clip(out[:, :, c] + grout_bright * mask, 0, 1)

        out[:, :, :3] = np.clip(out[:, :, :3] + bb * 0.35 * mask[:, :, np.newaxis], 0, 1)
        return out

    return spec_fn, paint_fn

def _quilt_hex_grid(shape, hex_size, seed, seed_offset):
    """True hexagonal cell tessellation (pointy-top) via cKDTree (fast).
    Returns (cell_id, min_dist, second_dist, n_cells) same as _quilt_voronoi."""
    h, w = shape
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
        h, w = shape[:2]
        closest, min_d, second_d, n_pts = _quilt_hex_grid(shape, hex_size, seed, seed_offset)
        rng_tint = np.random.RandomState(seed_offset + 999)
        tints = rng_tint.uniform(-0.14, 0.14, (_PALETTE_SIZE, 3)).astype(np.float32)
        idx = closest % _PALETTE_SIZE
        panel_tint = tints[idx, :]
        grout_w = max(2.0, hex_size * 0.06)
        grout = np.clip(1.0 - (second_d - min_d) / grout_w, 0, 1) ** 1.5
        out = np.zeros((h, w, 4), dtype=np.float32)
        out[:, :, :3] = np.clip(paint[:, :, :3] + panel_tint * pm * mask[:, :, np.newaxis] * (1 - grout[:, :, np.newaxis]), 0, 1)
        out[:, :, 3] = paint[:, :, 3] if paint.shape[2] > 3 else 1.0
        grout_bright = grout * 0.20 * pm
        for c in range(3):
            out[:, :, c] = np.clip(out[:, :, c] + grout_bright * mask, 0, 1)
        out[:, :, :3] = np.clip(out[:, :, :3] + bb * 0.35 * mask[:, :, np.newaxis], 0, 1)
        return out

    return spec_fn, paint_fn


def _quilt_diamond_grid(shape, diamond_size, seed, seed_offset):
    """Diamond (rhombus) cell tessellation via cKDTree (fast). 45-rotated square lattice.
    Returns (cell_id, min_dist, second_dist, n_cells)."""
    h, w = shape
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
        h, w = shape[:2]
        closest, min_d, second_d, n_pts = _quilt_diamond_grid(shape, diamond_size, seed, seed_offset)
        rng_tint = np.random.RandomState(seed_offset + 999)
        tints = rng_tint.uniform(-0.14, 0.14, (_PALETTE_SIZE, 3)).astype(np.float32)
        idx = closest % _PALETTE_SIZE
        panel_tint = tints[idx, :]
        grout_w = max(2.0, diamond_size * 0.06)
        grout = np.clip(1.0 - (second_d - min_d) / grout_w, 0, 1) ** 1.5
        out = np.zeros((h, w, 4), dtype=np.float32)
        out[:, :, :3] = np.clip(paint[:, :, :3] + panel_tint * pm * mask[:, :, np.newaxis] * (1 - grout[:, :, np.newaxis]), 0, 1)
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
                "depth_canyon", "depth_bubble", "depth_ripple", "depth_scale", "depth_honeycomb",
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
        },
    }


def get_fusion_counts():
    return {
        "fusions": len(FUSION_REGISTRY),
        "paradigm_shifts": 15,
        "per_paradigm": 10,
    }

