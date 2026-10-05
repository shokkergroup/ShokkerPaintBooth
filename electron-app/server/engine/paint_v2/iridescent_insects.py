"""
engine/paint_v2/iridescent_insects.py — ★ IRIDESCENT INSECTS Finishes (Pack #9)
10 insect-inspired iridescent/structural-color finishes with married paint+spec.

ALL spatial features scaled for 2048x2048 full-car textures.
ALL rendering fully vectorized — ZERO per-pixel Python loops.
Uses scipy + vectorized numpy throughout.

Seed offsets: 9400-9409.
"""
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import sobel, gaussian_filter
from engine.core import _resize_array, multi_scale_noise, get_mgrid


# ════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ════════════════════════════════════════════════════════════════════

def _insect_micro(shape, seed):
    """Ultra-fine micro shimmer for insect surfaces."""
    h, w = _shape2(shape)
    key = ("micro", int(h), int(w), int(seed))
    cached = _INSECT_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    wh, ww = _working_shape((h, w), 768)
    m = multi_scale_noise((wh, ww), [1, 2, 3], [0.5, 0.3, 0.2], seed + 600)
    out = np.clip(_resize_field(m, (h, w)) * 0.5 + 0.5, 0, 1).astype(np.float32)
    return _insect_cache_put(key, out)


def _insect_mgrid(shape):
    """Return float32 Y, X coordinate grids."""
    h, w = shape
    yy, xx = get_mgrid((h, w))
    return yy.astype(np.float32, copy=False), xx.astype(np.float32, copy=False)


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


_INSECT_FIELD_CACHE = {}
# SPB paint-finish perf loop tick 2026-05-31 05:23; owner: "Speed is king in this app."
# Exact cache/allocation cleanup only: butterfly_morpho 4800.0->4335.3 ms, butterfly_monarch 5265.6->5009.6 ms; std drift 0.


def _insect_cache_put(key, value):
    if len(_INSECT_FIELD_CACHE) > 96:
        _INSECT_FIELD_CACHE.clear()
    _INSECT_FIELD_CACHE[key] = value
    return value


def _working_shape(shape, cap=768):
    h, w = _shape2(shape)
    max_side = max(h, w)
    if max_side <= cap:
        return h, w
    scale = float(cap) / float(max_side)
    return max(96, int(round(h * scale))), max(96, int(round(w * scale)))


def _resize_field(field, shape):
    h, w = _shape2(shape)
    if field.shape == (h, w):
        return field.astype(np.float32)
    return _resize_array(np.asarray(field, dtype=np.float32), h, w).astype(np.float32)


def _firefly_fields(shape, seed):
    h, w = _shape2(shape)
    key = ("firefly", int(h), int(w), int(seed))
    cached = _INSECT_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    work = min(1024, int(h), int(w))
    sh, sw = h, w
    if work < min(h, w):
        sh = max(256, int(round(h * work / max(h, w))))
        sw = max(256, int(round(w * work / max(h, w))))
    yf, xf = _insect_mgrid((sh, sw))
    rng = np.random.RandomState((seed + 9409) & 0x7FFFFFFF)
    n_glows = 15
    gy = rng.uniform(sh * 0.4, sh * 0.95, n_glows).astype(np.float32)
    gx = rng.uniform(0, sw, n_glows).astype(np.float32)
    glow_r = rng.uniform(max(10, sh * 0.010), max(18, sh * 0.030), n_glows).astype(np.float32)
    brightness = rng.uniform(0.5, 1.0, n_glows).astype(np.float32)
    glow_map = np.zeros((sh, sw), dtype=np.float32)
    for k in range(n_glows):
        dist = np.sqrt((yf - gy[k])**2 + (xf - gx[k])**2)
        glow = np.exp(-(dist / glow_r[k])**2) * brightness[k]
        glow_map = np.maximum(glow_map, glow)
    glow_map = np.clip(glow_map, 0, 1).astype(np.float32)
    turb = multi_scale_noise((sh, sw), [16, 32, 64], [0.4, 0.35, 0.25], seed + 9409)
    if (sh, sw) != (h, w):
        glow_map = _resize_array(glow_map, h, w).astype(np.float32)
        turb = _resize_array(np.asarray(turb, dtype=np.float32), h, w)
    return _insect_cache_put(key, (glow_map, np.asarray(turb, dtype=np.float32)))


def _blend_paint(paint, mask, pm, color, strength=0.90):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    m3 = mask[:, :, np.newaxis]
    bl = np.clip(pm * strength, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1 - m3 * bl) + np.clip(color, 0, 1) * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)


def _iridescent_field(shape, seed, scale_mod=1.0):
    """Multi-scale organic flow field for iridescent zone mapping. Returns 0-1."""
    h, w = _shape2(shape)
    key = ("iridescent", int(h), int(w), int(seed), round(float(scale_mod), 4))
    cached = _INSECT_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    wh, ww = _working_shape((h, w), 768)
    scales = [int(16 * scale_mod), int(32 * scale_mod), int(64 * scale_mod)]
    n = multi_scale_noise((wh, ww), scales, [0.3, 0.4, 0.3], seed)
    out = np.clip(_resize_field(n, (h, w)) * 0.5 + 0.5, 0, 1).astype(np.float32)
    return _insect_cache_put(key, out)


def _voronoi_two(shape, seed, n_cells, cap=640):
    h, w = _shape2(shape)
    key = ("voronoi2", int(h), int(w), int(seed), int(n_cells), int(cap))
    cached = _INSECT_FIELD_CACHE.get(key)
    if cached is not None:
        return cached
    wh, ww = _working_shape((h, w), cap)
    yf, xf = _insect_mgrid((wh, ww))
    rng = np.random.RandomState(seed & 0x7FFFFFFF)
    pts = np.column_stack([rng.uniform(0, wh, n_cells), rng.uniform(0, ww, n_cells)]).astype(np.float32)
    grid_pts = np.column_stack([yf.ravel(), xf.ravel()])
    d, idx = cKDTree(pts).query(grid_pts, k=2, workers=-1)
    d1 = d[:, 0].reshape(wh, ww).astype(np.float32)
    d2 = d[:, 1].reshape(wh, ww).astype(np.float32)
    cell_id = idx[:, 0].reshape(wh, ww).astype(np.float32)
    out = (_resize_field(d1, (h, w)), _resize_field(d2, (h, w)), _resize_field(cell_id, (h, w)))
    return _insect_cache_put(key, out)


def _thin_film_color(thickness, base_hue_shift=0.0):
    """Compute thin-film interference color from thickness field (0-1).
    Returns (h, w, 3) RGB float32 array. Fully vectorized."""
    # Simulate constructive interference for R, G, B at different thicknesses
    r = np.clip(np.cos(thickness * np.pi * 4.0 + base_hue_shift) * 0.5 + 0.5, 0, 1)
    g = np.clip(np.cos(thickness * np.pi * 4.0 + base_hue_shift + 2.094) * 0.5 + 0.5, 0, 1)
    b = np.clip(np.cos(thickness * np.pi * 4.0 + base_hue_shift + 4.189) * 0.5 + 0.5, 0, 1)
    return np.stack([r, g, b], axis=-1).astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 01: BEETLE JEWEL — green-gold Chrysina beetle shell iridescence
# Seed: 9400
# ════════════════════════════════════════════════════════════════════

def paint_beetle_jewel(paint, shape, mask, seed, pm, bb):
    """Beetle jewel: Chrysina-style green-gold iridescent shell. Organic flow zones."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    field = _iridescent_field((h, w), seed + 9400)
    micro = _insect_micro((h, w), seed + 9400)
    # Green-gold shift
    gold = np.array([0.75, 0.68, 0.12], dtype=np.float32)
    emerald = np.array([0.08, 0.55, 0.18], dtype=np.float32)
    deep = np.array([0.02, 0.25, 0.08], dtype=np.float32)
    t = field * (0.85 + micro * 0.15)
    upper = (t > 0.5).astype(np.float32)
    t1 = np.clip(t * 2.0, 0, 1)
    t2 = np.clip((t - 0.5) * 2.0, 0, 1)
    color = (deep[None, None, :] * (1 - t1[:, :, None]) + emerald[None, None, :] * t1[:, :, None]) * (1 - upper[:, :, None]) + \
            (emerald[None, None, :] * (1 - t2[:, :, None]) + gold[None, None, :] * t2[:, :, None]) * upper[:, :, None]
    return _blend_paint(paint, mask, pm, color, 0.92)


def spec_beetle_jewel(shape, seed, sm, base_m, base_r):
    """Beetle jewel spec: gold zones high-M chrome, green zones mid-M."""
    h, w = _shape2(shape)
    field = _iridescent_field((h, w), seed + 9400)
    micro = _insect_micro((h, w), seed + 9400)
    t = np.clip(field * (0.85 + micro * 0.15), 0, 1)
    M = np.clip(80.0 + t * 170.0 * sm, 0, 255)
    R = np.clip(40.0 - t * 25.0 * sm, 15, 255)
    CC = np.clip(18.0 + (1 - t) * 15.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 02: BEETLE RAINBOW — Chrysochroa full-spectrum wing case
# Seed: 9401
# ════════════════════════════════════════════════════════════════════

def paint_beetle_rainbow(paint, shape, mask, seed, pm, bb):
    """Beetle rainbow: full-spectrum Chrysochroa wing case via thin-film interference."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    field = _iridescent_field((h, w), seed + 9401, scale_mod=0.8)
    micro = _insect_micro((h, w), seed + 9401)
    thickness = np.clip(field + micro * 0.12, 0, 1)
    color = _thin_film_color(thickness, base_hue_shift=0.5)
    # Boost saturation and darken slightly for beetle richness
    color = np.clip(color * 0.85 + 0.05, 0, 1)
    return _blend_paint(paint, mask, pm, color, 0.92)


def spec_beetle_rainbow(shape, seed, sm, base_m, base_r):
    """Beetle rainbow spec: iridescent shell, widely varying M/R/CC.

    2026-04-20 HEENAN AUTO-LOOP-17 — weakest insect_underground spec
    (dM=50 dR=15 dCC=8 at baseline). Rainbow-beetle shell should flash
    between chrome peaks and dielectric interstices as the iridescent
    field varies. Widen:
      M amp 50→130 (field low = 180 dielectric, peak = 250+ chrome)
      R amp 15→30 (peaks smooth, troughs scattered)
      CC amp 8→20 (ridges thicken clearcoat)
    """
    h, w = _shape2(shape)
    field = _iridescent_field((h, w), seed + 9401, scale_mod=0.8)
    M = np.clip(125.0 + field * 130.0 * sm, 0, 255)
    R = np.clip(15.0 + (1.0 - field) * 30.0, 15, 255)
    CC = np.clip(16.0 + field * 20.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 03: BUTTERFLY MORPHO — Morpho blue structural color (angle-dependent)
# Seed: 9402
# ════════════════════════════════════════════════════════════════════

def paint_butterfly_morpho(paint, shape, mask, seed, pm, bb):
    """Morpho butterfly: brilliant blue structural color with angle-dependent flash."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    # Simulated viewing-angle gradient (like Morpho wing scales)
    angle_sim = np.clip((1.0 - yf / h) * 0.5 + (xf / w) * 0.5, 0, 1).astype(np.float32)
    # Multi-scale scale pattern (wing scale structure)
    scale_pat = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 9402)
    scale_n = np.clip(scale_pat * 0.5 + 0.5, 0, 1)
    # Morpho blue shifts to deeper purple at grazing angles
    bright_blue = np.array([0.05, 0.30, 0.95], dtype=np.float32)
    deep_blue = np.array([0.02, 0.08, 0.55], dtype=np.float32)
    flash_white = np.array([0.60, 0.75, 1.00], dtype=np.float32)
    t = angle_sim * (0.8 + scale_n * 0.2)
    color = deep_blue[None, None, :] * (1 - t[:, :, None]) + bright_blue[None, None, :] * t[:, :, None]
    # Flash highlights at peak angle
    flash_mask = np.clip((t - 0.75) * 8.0, 0, 1)
    color = color * (1 - flash_mask[:, :, None]) + flash_white[None, None, :] * flash_mask[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.94)


def spec_butterfly_morpho(shape, seed, sm, base_m, base_r):
    """Morpho spec: extreme metallic on bright zones, mid on deep zones.

    2026-04-20 HEENAN AUTO-LOOP-21 — big M swing (155) but R amp only
    15 (t-range 15..30) — roughness ties the angle effect together
    weakly. Morpho structural color needs visible smoothness contrast:
    bright zones mirror-smooth vs deep zones diffusely-scattered.
    Widen R amp 15→50 (range 10..60 clipped at 15 floor: effective
    15..60). CC amp 10→22 (bright zones thin clear, deep thicker)."""
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    angle_sim = np.clip((1.0 - yf / h) * 0.5 + (xf / w) * 0.5, 0, 1)
    scale_pat = multi_scale_noise((h, w), [16, 32, 64], [0.4, 0.35, 0.25], seed + 9402)
    t = np.clip(angle_sim * (0.8 + np.clip(scale_pat * 0.5 + 0.5, 0, 1) * 0.2), 0, 1)
    M = np.clip(100.0 + t * 155.0 * sm, 0, 255)
    R = np.clip(65.0 - t * 50.0 * sm, 15, 255)
    CC = np.clip(16.0 + (1 - t) * 22.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 04: BUTTERFLY MONARCH — orange-black monarch wing pattern
# Seed: 9403
# ════════════════════════════════════════════════════════════════════

def paint_butterfly_monarch(paint, shape, mask, seed, pm, bb):
    """Monarch butterfly: orange-black wing pattern with white spots."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    # Wing vein network via Voronoi edges. Build the topology on a bounded
    # work grid; full-resolution KDTree queries are the slow path at 2048.
    d1, d2, _idx = _voronoi_two((h, w), seed + 9403, 80, cap=640)
    # Vein darkness at edges
    vein_width = np.median(d1) * 0.15
    vein = np.clip(1.0 - (d2 - d1) / (vein_width + 1e-8), 0, 1).astype(np.float32)
    # Orange wing fills
    orange = np.array([0.92, 0.48, 0.05], dtype=np.float32)
    black = np.array([0.03, 0.02, 0.02], dtype=np.float32)
    # White spots at border regions
    border = np.clip(np.maximum(yf / h, 1.0 - yf / h) + np.maximum(xf / w, 1.0 - xf / w) - 1.2, 0, 1)
    turb = _resize_field(multi_scale_noise(_working_shape((h, w), 768), [16, 32], [0.5, 0.5], seed + 9403), (h, w))
    spots = np.clip((turb - 0.3) * 5.0, 0, 1) * border
    white = np.array([0.95, 0.95, 0.95], dtype=np.float32)
    color = orange[None, None, :] * (1 - vein[:, :, None]) + black[None, None, :] * vein[:, :, None]
    color = color * (1 - spots[:, :, None]) + white[None, None, :] * spots[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.92)


def spec_butterfly_monarch(shape, seed, sm, base_m, base_r):
    """Monarch spec: orange zones are satiny, veins are dark matte."""
    h, w = _shape2(shape)
    d1, d2, _idx = _voronoi_two((h, w), seed + 9403, 80, cap=640)
    vein = np.clip(1.0 - (d2 - d1) / (np.median(d1) * 0.15 + 1e-8), 0, 1).astype(np.float32)
    # 2026-04-20 HEENAN AUTO-LOOP-18 — M was 60..5 (dM=55). Orange wing
    # zones should feel like waxy satin-metallic surface with the veins
    # reading as dead-matte dielectric seams. Widen M to 185..5 (dM=180)
    # keeping R/CC where they already had good contrast.
    M = np.clip(185.0 * (1 - vein) * sm + 5.0 * vein, 0, 255)
    R = np.clip(70.0 * (1 - vein) + 200.0 * vein, 15, 255)
    CC = np.clip(25.0 * (1 - vein) + 100.0 * vein, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 05: DRAGONFLY WING — transparent wing with interference rainbow
# Seed: 9404
# ════════════════════════════════════════════════════════════════════

def paint_dragonfly_wing(paint, shape, mask, seed, pm, bb):
    """Dragonfly wing: semi-transparent wing membrane with rainbow interference."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    # Wing vein structure (sparse branching)
    wh, ww = _working_shape((h, w), 768)
    turb = multi_scale_noise((wh, ww), [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 9404)
    # Detect veins via Sobel edges on turbulence
    ey = sobel(turb, axis=0)
    ex = sobel(turb, axis=1)
    veins = np.sqrt(ey**2 + ex**2)
    veins = np.clip(veins / (np.percentile(veins, 95) + 1e-8), 0, 1).astype(np.float32)
    veins = np.clip(gaussian_filter(veins, sigma=0.8) * 2.5, 0, 1).astype(np.float32)
    veins = _resize_field(veins, (h, w))
    # Thin-film interference between veins
    thickness = _iridescent_field((h, w), seed + 9405, scale_mod=0.6)
    rainbow = _thin_film_color(thickness, base_hue_shift=1.0)
    # Transparent membrane: very light, barely there
    membrane = np.clip(rainbow * 0.5 + 0.45, 0, 1)
    # Veins are dark
    vein_col = np.array([0.05, 0.05, 0.08], dtype=np.float32)
    color = membrane * (1 - veins[:, :, None]) + vein_col[None, None, :] * veins[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.85)


def spec_dragonfly_wing(shape, seed, sm, base_m, base_r):
    """Dragonfly wing spec: membrane is glassy transparent, veins are rough."""
    h, w = _shape2(shape)
    wh, ww = _working_shape((h, w), 768)
    turb = multi_scale_noise((wh, ww), [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 9404)
    ey = sobel(turb, axis=0)
    ex = sobel(turb, axis=1)
    veins = np.sqrt(ey**2 + ex**2)
    veins = np.clip(veins / (np.percentile(veins, 95) + 1e-8), 0, 1).astype(np.float32)
    veins = np.clip(gaussian_filter(veins, sigma=0.8) * 2.5, 0, 1).astype(np.float32)
    veins = _resize_field(veins, (h, w))
    M = np.clip(140.0 * (1 - veins) * sm + 20.0 * veins, 0, 255)
    R = np.clip(15.0 * (1 - veins) + 160.0 * veins, 15, 255)
    CC = np.clip(16.0 * (1 - veins) + 60.0 * veins, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 06: SCARAB GOLD — Egyptian scarab golden-green shift
# Seed: 9405
# ════════════════════════════════════════════════════════════════════

def paint_scarab_gold(paint, shape, mask, seed, pm, bb):
    """Scarab gold: Egyptian scarab golden-green iridescence with organic shell texture."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    field = _iridescent_field((h, w), seed + 9405)
    micro = _insect_micro((h, w), seed + 9405)
    # Gold to deep green shift
    gold = np.array([0.82, 0.72, 0.15], dtype=np.float32)
    olive = np.array([0.35, 0.50, 0.12], dtype=np.float32)
    deep_green = np.array([0.06, 0.30, 0.10], dtype=np.float32)
    t = np.clip(field * (0.8 + micro * 0.2), 0, 1)
    upper = (t > 0.5).astype(np.float32)
    t1 = np.clip(t * 2.0, 0, 1)
    t2 = np.clip((t - 0.5) * 2.0, 0, 1)
    color = (deep_green[None, None, :] * (1 - t1[:, :, None]) + olive[None, None, :] * t1[:, :, None]) * (1 - upper[:, :, None]) + \
            (olive[None, None, :] * (1 - t2[:, :, None]) + gold[None, None, :] * t2[:, :, None]) * upper[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.92)


def spec_scarab_gold(shape, seed, sm, base_m, base_r):
    """Scarab gold spec: gold zones extreme chrome, green zones mid-metallic.

    2026-04-20 HEENAN AUTO-LOOP-22 — dM=159 was strong already but
    dR=19 meant the iridescent shell had almost uniform smoothness.
    Real Egyptian-scarab shell has hard-polished gold ridges and
    rougher green interstices. Widen R amp 20→55 (green zones R=70
    scattered, gold R=15 mirror). CC amp 12→25."""
    h, w = _shape2(shape)
    field = _iridescent_field((h, w), seed + 9405)
    micro = _insect_micro((h, w), seed + 9405)
    t = np.clip(field * (0.8 + micro * 0.2), 0, 1)
    M = np.clip(90.0 + t * 165.0 * sm, 0, 255)
    R = np.clip(70.0 - t * 55.0 * sm, 15, 255)
    CC = np.clip(16.0 + (1 - t) * 25.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 07: MOTH LUNA — pale green Luna moth with eye-spot pattern
# Seed: 9406
# ════════════════════════════════════════════════════════════════════

def paint_moth_luna(paint, shape, mask, seed, pm, bb):
    """Luna moth: pale green with large concentric eye-spot patterns."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    rng = np.random.RandomState((seed + 9406) & 0x7FFFFFFF)
    # Base pale green
    pale_green = np.array([0.65, 0.82, 0.58], dtype=np.float32)
    # 4 eye spots
    n_eyes = 4
    ey_c = rng.uniform(h * 0.2, h * 0.8, n_eyes).astype(np.float32)
    ex_c = rng.uniform(w * 0.2, w * 0.8, n_eyes).astype(np.float32)
    eye_r = rng.uniform(min(h, w) * 0.06, min(h, w) * 0.12, n_eyes).astype(np.float32)
    eye_map = np.zeros((h, w), dtype=np.float32)
    ring_map = np.zeros((h, w), dtype=np.float32)
    for k in range(n_eyes):
        dist = np.sqrt((yf - ey_c[k])**2 + (xf - ex_c[k])**2)
        # Eye center
        center = np.exp(-(dist / (eye_r[k] * 0.4))**2).astype(np.float32)
        # Ring around eye
        ring = np.exp(-((dist - eye_r[k]) / (eye_r[k] * 0.15))**2).astype(np.float32)
        eye_map = np.maximum(eye_map, center)
        ring_map = np.maximum(ring_map, ring)
    # Wing texture
    turb = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 9406)
    wing_var = np.clip(turb * 0.08, -0.08, 0.08)
    # Colors
    eye_dark = np.array([0.10, 0.10, 0.18], dtype=np.float32)
    ring_yellow = np.array([0.85, 0.75, 0.20], dtype=np.float32)
    color = pale_green[None, None, :] + wing_var[:, :, None]
    color = color * (1 - ring_map[:, :, None]) + ring_yellow[None, None, :] * ring_map[:, :, None]
    color = color * (1 - eye_map[:, :, None]) + eye_dark[None, None, :] * eye_map[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.88)


def spec_moth_luna(shape, seed, sm, base_m, base_r):
    """Luna moth spec: soft fuzzy surface (moth wing scales are matte)."""
    h, w = _shape2(shape)
    rng = np.random.RandomState((seed + 9406) & 0x7FFFFFFF)
    yf, xf = _insect_mgrid((h, w))
    n_eyes = 4
    ey_c = rng.uniform(h * 0.2, h * 0.8, n_eyes).astype(np.float32)
    ex_c = rng.uniform(w * 0.2, w * 0.8, n_eyes).astype(np.float32)
    eye_r = rng.uniform(min(h, w) * 0.06, min(h, w) * 0.12, n_eyes).astype(np.float32)
    eye_map = np.zeros((h, w), dtype=np.float32)
    for k in range(n_eyes):
        dist = np.sqrt((yf - ey_c[k])**2 + (xf - ex_c[k])**2)
        center = np.exp(-(dist / (eye_r[k] * 0.4))**2)
        eye_map = np.maximum(eye_map, center)
    eye_map = np.clip(eye_map, 0, 1).astype(np.float32)
    # 2026-04-20 HEENAN AUTO-LOOP-20 — luna wing dM=80, eye spots too
    # similar to the wing. The "eye" spots on a luna moth wing are the
    # signature detail — should pop as satin-metallic islands vs the
    # fuzzy-matte wing field.
    #   Wing (eye_map=0): M=10 dielectric, R=160 fuzz, CC=90 thick clear
    #   Eyes (eye_map=1): M=190 satin-metallic, R=30 glossy, CC=16 thin
    #   dM 80→180, dR 40→130, dCC 30→74
    M = np.clip(10.0 + eye_map * 180.0 * sm, 0, 255)
    R = np.clip(160.0 - eye_map * 130.0, 15, 255)
    CC = np.clip(90.0 - eye_map * 74.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 08: BEETLE STAG — dark metallic stag beetle armor plates
# Seed: 9407
# ════════════════════════════════════════════════════════════════════

def paint_beetle_stag(paint, shape, mask, seed, pm, bb):
    """Stag beetle: dark metallic brown-black armor plating with chitin shine."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    # Armor plate pattern: large Voronoi cells
    rng = np.random.RandomState((seed + 9407) & 0x7FFFFFFF)
    n_cells = 35
    d1, d2, cell_id = _voronoi_two((h, w), seed + 9407, n_cells, cap=640)
    cell_id = np.clip(np.rint(cell_id), 0, n_cells - 1).astype(np.int32)
    # Plate edges
    edge = np.clip(1.0 - (d2 - d1) / (np.median(d1) * 0.2 + 1e-8), 0, 1).astype(np.float32)
    # Per-plate shade variation
    plate_shade = rng.uniform(0.7, 1.0, n_cells).astype(np.float32)
    shade = plate_shade[cell_id]
    # Colors: dark brown-black chitin
    chitin = np.array([0.15, 0.10, 0.06], dtype=np.float32)
    highlight = np.array([0.30, 0.22, 0.14], dtype=np.float32)
    seam = np.array([0.02, 0.01, 0.01], dtype=np.float32)
    # Inner plate highlight gradient
    max_d1 = np.maximum(d1.max(), 1.0)
    inner = np.clip(1.0 - d1 / (max_d1 * 0.4), 0, 0.4)
    plate_col = chitin[None, None, :] * shade[:, :, None] + highlight[None, None, :] * inner[:, :, None]
    color = plate_col * (1 - edge[:, :, None]) + seam[None, None, :] * edge[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.92)


def spec_beetle_stag(shape, seed, sm, base_m, base_r):
    """Stag beetle spec: plates are glossy metallic chitin, seams are matte."""
    h, w = _shape2(shape)
    d1, d2, _idx = _voronoi_two((h, w), seed + 9407, 35, cap=640)
    edge = np.clip(1.0 - (d2 - d1) / (np.median(d1) * 0.2 + 1e-8), 0, 1).astype(np.float32)
    M = np.clip(180.0 * (1 - edge) * sm + 15.0 * edge, 0, 255)
    R = np.clip(25.0 * (1 - edge) + 180.0 * edge, 15, 255)
    CC = np.clip(18.0 * (1 - edge) + 80.0 * edge, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 09: WASP WARNING — yellow-black warning pattern with metallic sheen
# Seed: 9408
# ════════════════════════════════════════════════════════════════════

def paint_wasp_warning(paint, shape, mask, seed, pm, bb):
    """Wasp warning: bold yellow-black aposematic banding with metallic shimmer."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    # Horizontal bands with slight wave
    turb = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 9408)
    band_freq = max(3, h // 120)
    wave_y = yf + turb * (h * 0.04)
    band_raw = np.sin(wave_y / band_freq * np.pi)
    band = np.clip(band_raw * 3.0, -1, 1).astype(np.float32)
    # Sharp threshold: > 0 = yellow, < 0 = black
    yellow_mask = np.clip(band * 5.0, 0, 1).astype(np.float32)
    # Micro-texture for exoskeleton pitting
    micro = _insect_micro((h, w), seed + 9408)
    yellow = np.array([0.92, 0.82, 0.08], dtype=np.float32)
    black = np.array([0.04, 0.03, 0.02], dtype=np.float32)
    color = black[None, None, :] * (1 - yellow_mask[:, :, None]) + yellow[None, None, :] * yellow_mask[:, :, None]
    color += micro[:, :, None] * 0.03
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.92)


def spec_wasp_warning(shape, seed, sm, base_m, base_r):
    """Wasp spec: yellow bands are glossy, black bands are slightly matte."""
    h, w = _shape2(shape)
    yf, _ = _insect_mgrid((h, w))
    turb = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 9408)
    band_freq = max(3, h // 120)
    wave_y = yf + turb * (h * 0.04)
    band = np.clip(np.sin(wave_y / band_freq * np.pi) * 5.0, 0, 1).astype(np.float32)
    # 2026-04-20 HEENAN AUTO-LOOP-19 — yellow bands 100/40 dM=60 too
    # similar. Real wasp exoskeleton has waxy semi-metallic yellow vs
    # dead-matte black chitin. Widen M to 220 yellow / 10 black (dM=210).
    # Also widen R: yellow smoother (25), black rougher (95); CC: yellow
    # thin (18), black thicker (65).
    M = np.clip(220.0 * band * sm + 10.0 * (1 - band) * sm, 0, 255)
    R = np.clip(25.0 * band + 95.0 * (1 - band), 15, 255)
    CC = np.clip(18.0 * band + 65.0 * (1 - band), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 10: FIREFLY GLOW — bioluminescent green-yellow glow zones on dark body
# Seed: 9409
# ════════════════════════════════════════════════════════════════════

def paint_firefly_glow(paint, shape, mask, seed, pm, bb):
    """Firefly glow: dark exoskeleton with bioluminescent yellow-green lantern zones."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    # Dark body base
    dark_body = np.array([0.04, 0.04, 0.03], dtype=np.float32)
    glow_map, turb = _firefly_fields((h, w), seed)
    # Subtle body texture
    body_var = np.clip(turb * 0.04 + 0.02, 0, 0.08)
    # Glow color: warm yellow-green
    glow_core = np.array([0.70, 0.90, 0.20], dtype=np.float32)
    glow_edge = np.array([0.30, 0.55, 0.08], dtype=np.float32)
    glow_color = glow_core[None, None, :] * glow_map[:, :, None] + glow_edge[None, None, :] * glow_map[:, :, None] * 0.3
    color = dark_body[None, None, :] + body_var[:, :, None]
    color = color * (1 - glow_map[:, :, None]) + glow_color * glow_map[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.92)


def spec_firefly_glow(shape, seed, sm, base_m, base_r):
    """Firefly spec: glow zones are emissive-bright metallic, body is dark matte."""
    h, w = _shape2(shape)
    glow_map, _turb = _firefly_fields((h, w), seed)
    M = np.clip(10.0 + glow_map * 220.0 * sm, 0, 255)
    R = np.clip(170.0 - glow_map * 155.0 * sm, 15, 255)
    CC = np.clip(70.0 - glow_map * 54.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# IRIDESCENT INSECTS 2026 — accepted one-card-at-a-time replacements.
# Owner 2026-09-01: every stable ID remains isolated until native/picker eye
# evidence passes. Beetle Jewel I2 P1-P5 replaced the rejected periodic field
# with a bounded-jitter Chrysina cuticle and Spec-Encyclopedia material flow.
from engine.paint_v2.iridescent_insects_beetle_jewel_i2_2026 import (
    paint_beetle_jewel_i2 as paint_beetle_jewel,
    spec_beetle_jewel_i2 as spec_beetle_jewel,
)

# Card 2/50 — Chrysochroa Ribbon I1 P3.  Research-correct emerald multilayer
# ribbons with irregular purple domains, copper transition lips, fine lamellar
# crosscuts and independently phased polarized M/R/Cc response.
from engine.paint_v2.iridescent_insects_beetle_rainbow_i1_2026 import (
    paint_beetle_rainbow_i1 as paint_beetle_rainbow,
    spec_beetle_rainbow_i1 as spec_beetle_rainbow,
)

# Card 3/50 — Morpho Lamella I1 P4.  Plate-bounded ridge ladders, broken
# buttress teeth, dark optical windows and broad cyan/violet structural flash.
from engine.paint_v2.iridescent_insects_butterfly_morpho_i1_2026 import (
    paint_butterfly_morpho_i1 as paint_butterfly_morpho,
    spec_butterfly_morpho_i1 as spec_butterfly_morpho,
)

# Card 4/50 — Tortoise Glass I1 P4.  Continuous honey-gold/red stress
# reflector beneath fine transparent Charidotella scutes; distinct M/R/Cc
# fluid states create the angle-dependent gold-to-red shell transition.
from engine.paint_v2.iridescent_insects_beetle_tortoise_i1_2026 import (
    paint_beetle_tortoise_i1 as paint_beetle_tortoise,
    spec_beetle_tortoise_i1 as spec_beetle_tortoise,
)

# Card 5/50 — Tiger Beetle Velocity I2 P1 identity correction.  The accepted
# copper/ivory pointillistic maculation paint is preserved; its generic wave
# spec is replaced by puncta-lip, pit-floor, seam, ivory edge/body and
# compression-tooth ownership.  M7 86.6; identity gate clean.
from engine.paint_v2.iridescent_insects_beetle_tiger_i2_2026 import (
    paint_beetle_tiger_i2 as paint_beetle_tiger,
    spec_beetle_tiger_i2 as spec_beetle_tiger,
)

# Card 6/50 — Rose Chafer Velvet I1 P2.  Warped staggered reflector bowls,
# scalloped lips, fan striae and pollen dimples turn Cetonia's chiral green
# cuticle into dense polarized velvet with independently phased material flow.
# Rose Chafer I2 P4 — owner cross-card correction.  Metallic-green chiral
# bowls now own their M/R/Cc tiers; the shared macro-wave field is gone.
# M7 99.4 -> 85.0, independence 0.817, 1.81s standard render, projected
# category breaches 13 -> 9.
from engine.paint_v2.iridescent_insects_beetle_rose_chafer_i2_2026 import (
    paint_beetle_rose_chafer_i2 as paint_beetle_rose_chafer,
    spec_beetle_rose_chafer_i2 as spec_beetle_rose_chafer,
)

# Card 7/50 — Buprestid Furnace I2 P4 identity correction.  Offset 25-31px
# refractory ingot cells contain nested 8-12px reflector lamellae, air gaps,
# oxide lips, soot vents and cell-local thermal states.  The old diagonal paint
# and generic f0/f1/f2 spec waves were rejected.  M7 88.2; identity gate clean.
from engine.paint_v2.iridescent_insects_beetle_buprestid_i2_2026 import (
    paint_beetle_buprestid_i2 as paint_beetle_buprestid,
    spec_beetle_buprestid_i2 as spec_beetle_buprestid,
)

# Card 8/50 — Ground Beetle Obsidian I1 P3.  Oil-black asymmetric Carabid
# plates carry 8-14px polygon engraving, dense transverse diffraction lines,
# continuous abrasion contours and a buried micro-cross array.  The restrained
# carrier stays dark while separate M/R/Cc flows wake the armor under light.
# Ground Beetle I2 P5 — owner cross-card correction.  Oil-black paint stays;
# spec ownership is now plates/gratings/crosses vs pits/abrasion vs mesh/lips.
# M7 85.9; 2.41s standard; projected category breaches 5 -> 3.
from engine.paint_v2.iridescent_insects_beetle_ground_i2_2026 import (
    paint_beetle_ground_i2 as paint_beetle_ground,
    spec_beetle_ground_i2 as spec_beetle_ground,
)

# Card 9/50 — Stag Carapace I1 P3.  Research-backed three-layer Lucanus
# armor: dense bent ribs, pore canals, sclerite seams and 18-26px native
# spiral-woven trabecular nodes over per-plate oxblood/cold-steel identities.
from engine.paint_v2.iridescent_insects_beetle_stag_i1_2026 import (
    paint_beetle_stag_i1 as paint_beetle_stag,
    spec_beetle_stag_i1 as spec_beetle_stag,
)

# Card 10/50 — Monarch Mosaic I1 P2.  Thousands of 8-26px orange scale
# windows sit inside absorptive black vein channels, with overlapping tile
# lips, lamina ridges/crossribs and pattern-bound cream marginal islands.
from engine.paint_v2.iridescent_insects_butterfly_monarch_i1_2026 import (
    paint_butterfly_monarch_i1 as paint_butterfly_monarch,
    spec_butterfly_monarch_i1 as spec_butterfly_monarch,
)

# Card 11/50 — Longhorn Filament I2 P2.  Cross-card correction removes the
# shared macro sinusoidal spec grammar: every 8-32px Cerambycid sack owns an
# independent color family and eight-tier M/R/Cc state (M7 99.5 -> 87.8,
# cross-card breaches 18 -> 13; owner eye and distinctiveness win).
from engine.paint_v2.iridescent_insects_beetle_longhorn_i2_2026 import (
    paint_beetle_longhorn_i2 as paint_beetle_longhorn,
    spec_beetle_longhorn_i2 as spec_beetle_longhorn,
)

# Card 12/50 — Click Beetle Plasma I1 P4.  Tiny superblack microtube eyes and
# yellow-green/orange lantern beads follow continuous cyan nerve routes through
# fine punctured/striated armor; three earlier wallpaper/confetti drafts died.
# Click Beetle I2 P4 — owner cross-card correction.  The accepted dark nerve
# paint is preserved; M/R/Cc now has orthogonal ownership by visible striae,
# pores/tubes, and routes/coronas. M7 88.6; 2.30s standard; projected breaches 9 -> 5.
from engine.paint_v2.iridescent_insects_beetle_click_i2_2026 import (
    paint_beetle_click_i2 as paint_beetle_click,
    spec_beetle_click_i2 as spec_beetle_click,
)

# Card 13/50 — Emperor Eyelet I1 P5.  Fine broken ocelli gather into braided
# bronze/violet streams over structural-blue Sasakia scales; P1-P2 disappeared
# at picker scale, P3 compressed spec response, and P4 over-stretched it.
# Emperor Eyelet I2 P3 — owner cross-card correction.  Braided eyelet paint
# stays; M/R/Cc now traces rings/ridges vs dark/spokes vs iris/pearl/lips.
# M7 86.5; 2.19s standard; projected category breaches 3 -> 1.
from engine.paint_v2.iridescent_insects_butterfly_emperor_i2_2026 import (
    paint_butterfly_emperor_i2 as paint_butterfly_emperor,
    spec_butterfly_emperor_i2 as spec_butterfly_emperor,
)

# Card 14/50 — Swallowtail Prism I1 P2.  Varied fork-tailed Papilio scales
# combine thin-film laminae, pigment ribs, melanin lanes and retroreflector
# wells; P1's machine-perfect cadence was biologically loosened before keep.
from engine.paint_v2.iridescent_insects_butterfly_swallowtail_i1_2026 import (
    paint_butterfly_swallowtail_i1 as paint_butterfly_swallowtail,
    spec_butterfly_swallowtail_i1 as spec_butterfly_swallowtail,
)

# Card 15/50 — Glasswing Lattice I2 P3 identity correction.  The broad haze
# fields were removed.  Irregular clear panes, three-layer doubled veins,
# independent nipple/wax-pillar populations, pane-local bristles and dew own
# distinct M/R/Cc.  M7 88.0, independence .750, identity gate clean.
from engine.paint_v2.iridescent_insects_butterfly_glasswing_i2_2026 import (
    paint_butterfly_glasswing_i2 as paint_butterfly_glasswing,
    spec_butterfly_glasswing_i2 as spec_butterfly_glasswing,
)

# Card 16/50 — Peacock Scale Furnace I2 P4 identity correction.  Seven-row
# feather fans are assembled from 27-32px spectral eyelets with 8-12px crossed
# scale ribs and dark refractory voids.  P1-P3's random-cell bubble carpet was
# rejected despite passing M7; I2 P4 clears M7 86.8 and the cross-card gate.
from engine.paint_v2.iridescent_insects_butterfly_peacock_i2_2026 import (
    paint_butterfly_peacock_i2 as paint_butterfly_peacock,
    spec_butterfly_peacock_i2 as spec_butterfly_peacock,
)

# Card 17/50 — Luna Silk I1 P4.  Overlapping celadon feather-scales ride
# coherent silk currents; scale shafts, barbs, crossribs, curled-tip gratings
# and interstices own separately phased material states.  Earlier passes read
# as isolated stitch wallpaper; P4 restores broad leaf-scale bodies.
from engine.paint_v2.iridescent_insects_moth_luna_i1_2026 import (
    paint_moth_luna_i1 as paint_moth_luna,
    spec_moth_luna_i1 as spec_moth_luna,
)

# Card 18/50 — Tiger Moth Ember I1 P2.  Fine tilted scale hairs assemble
# compact aposematic ember/ivory rivers over soot velvet; ridge fans, crossrib
# windows, keratin filaments and melanin interstices carry independent spec.
from engine.paint_v2.iridescent_insects_moth_tiger_i1_2026 import (
    paint_moth_tiger_i1 as paint_moth_tiger,
    spec_moth_tiger_i1 as spec_moth_tiger,
)

# Card 19/50 — Hummingbird Blur I1 P3.  Compact opposite-handed wingbeat
# vortices circulate retained forked bristles around shed-scale membrane cores;
# sockets, antireflective pillars, orbital wakes and pollen own separate spec.
from engine.paint_v2.iridescent_insects_moth_hummingbird_i1_2026 import (
    paint_moth_hummingbird_i1 as paint_moth_hummingbird,
    spec_moth_hummingbird_i1 as spec_moth_hummingbird,
)

# Card 20/50 — Owl Moth Sable I1 P3.  Eccentric incomplete bronze micro-ocelli
# braid through sable nap; roof scales, disorder ribs, layered bristles, pupil
# scars and abrasion rings each retain distinct material response.
from engine.paint_v2.iridescent_insects_moth_owl_i1_2026 import (
    paint_moth_owl_i1 as paint_moth_owl,
    spec_moth_owl_i1 as spec_moth_owl,
)

# Card 21/50 — Dragonfly Resilin I1 P6.  Corrugated primary rails support a
# dense irregular vein-cell membrane; blue elastic joints, suspension zones,
# spikes and pterostigma-like mass bars own separate material channels.
from engine.paint_v2.iridescent_insects_dragonfly_wing_i1_2026 import (
    paint_dragonfly_wing_i1 as paint_dragonfly_wing,
    spec_dragonfly_wing_i1 as spec_dragonfly_wing,
)

# Card 22/50 — Emerald Skimmer I1 P5.  Coherent-scattering nanosphere
# populations move through compact emerald/cyan/violet cuticle clouds; melanin
# stiffeners, pruinose platelets and attached articulation flashes each own
# distinct material states without repeating Dragonfly Resilin's vein carrier.
from engine.paint_v2.iridescent_insects_dragonfly_emerald_i1_2026 import (
    paint_dragonfly_emerald_i1 as paint_dragonfly_emerald,
    spec_dragonfly_emerald_i1 as spec_dragonfly_emerald,
)

# Card 23/50 — Damselfly Cobalt I1 P4.  Compact paired cobalt laminations,
# absorbing ventral troughs, minute cross-sutures and sparse oblique forks form
# a dense Calopteryx/Neurobasis wing stack rather than a textile or pinstripe.
from engine.paint_v2.iridescent_insects_damselfly_cobalt_i1_2026 import (
    paint_damselfly_cobalt_i1 as paint_damselfly_cobalt,
    spec_damselfly_cobalt_i1 as spec_damselfly_cobalt,
)

# Card 24/50 — Cicada Window I1 P5.  Unequal wandering bronze veins and
# compact tension ties carry capped hydrophobic nanocones, rare suture collars,
# flexible folds and condensate rims.  P3's macro waves and P4's pearl chains
# were rejected even though both passed M7; P5 is the owner-eye identity pass.
from engine.paint_v2.iridescent_insects_cicada_membrane_i1_2026 import (
    paint_cicada_membrane_i1 as paint_cicada_membrane,
    spec_cicada_membrane_i1 as spec_cicada_membrane,
)

# Card 25/50 — Lacewing Aurora I1 P3.  Sigmoid pseudomedial rails carry
# convergent radial branches, staggered inner/outer gradates, oval joints,
# pedicellate setae and nonperiodic thin-film panes.  P1's oval wallpaper was
# rejected; P4/P5 were calmer visually but failed the 85 ship bar at time cap.
from engine.paint_v2.iridescent_insects_lacewing_aurora_i1_2026 import (
    paint_lacewing_aurora_i1 as paint_lacewing_aurora,
    spec_lacewing_aurora_i1 as spec_lacewing_aurora,
)

# Card 26/50 — Mayfly Silverstream I1 P3.  Alternating positive/negative
# corrugation veins carry sparse cross-ties, intercalary forks, attached
# 8–20px highlight facets and rows of flexible bullae.  P1's woven grid was
# rejected; P3 is the strongest passing identity at the 20-minute cap.
from engine.paint_v2.iridescent_insects_mayfly_silver_i1_2026 import (
    paint_mayfly_silver_i1 as paint_mayfly_silver,
    spec_mayfly_silver_i1 as spec_mayfly_silver,
)

# Card 27/50 — Bee Venturi I1 P3.  A connected irregular shared-wall wax
# architecture carries transitional cells, wax grains, silk lamellae, honey
# menisci, propolis and attached pollen hairs.  P1's floating-ring wallpaper
# was rejected; P3 spans all M/R/Cc levels without changing P2's visual win.
from engine.paint_v2.iridescent_insects_bee_honeycomb_i1_2026 import (
    paint_bee_honeycomb_i1 as paint_bee_honeycomb,
    spec_bee_honeycomb_i1 as spec_bee_honeycomb,
)

# Card 28/50 — Bumble Velvet I1 P5.  Thousands of socketed 8–24px
# directional setae form interlocking ochre/sable nap packets; attached forked
# barbs, comb fringes, pollen hooks and polished chitin slits each own distinct
# material states.  P1–P4 established the carrier and channel separation; P5
# removes cubic clipping and clears the owner ship bar without changing paint.
from engine.paint_v2.iridescent_insects_bumble_velvet_i1_2026 import (
    paint_bumble_velvet_i1 as paint_bumble_velvet,
    spec_bumble_velvet_i1 as spec_bumble_velvet,
)

# Card 29/50 — Wasp Signal I2 P6.  Connected chains of nested tergite
# chevrons select compact duplex cuticle plates; packed yellow granules,
# epicuticle rosettes, central pores, setae, tracheal slits and bruised pigment
# own separate material states.  P1/P2 collapsed to stripes/fibres, P3 wandered,
# P4/P5 established the signal grammar, and P6 balances channel amplitude.
from engine.paint_v2.iridescent_insects_wasp_warning_i2_2026 import (
    paint_wasp_warning_i2 as paint_wasp_warning,
    spec_wasp_warning_i2 as spec_wasp_warning,
)

# Card 30/50 — Hoverfly Mirror I1 P3.  Fine rhomboid tergite mirrors form
# irregular paired pollinose maculae under sparse transparent wing-film lanes;
# paired true/spurious vein rails, microtrichia islands, bare windows, nodes
# and scuffs each own distinct M/R/Cc.  P1's broad bands were rejected.
from engine.paint_v2.iridescent_insects_hoverfly_mirror_i1_2026 import (
    paint_hoverfly_mirror_i1 as paint_hoverfly_mirror,
    spec_hoverfly_mirror_i1 as spec_hoverfly_mirror,
)

# Card 31/50 — Firefly Lantern I2 P4.  Every 12–32px module contains an
# ordered extraction-prism / photogenic cross-net / radial urate reflector
# stack.  Active/dormant regions, dark shell chips, tracheal twigs, bulbs,
# vesicles and sutures prevent a uniform glow carpet.  P1/P2 path carriers and
# P3's fully active textile were rejected; P4 is the time-cap visual winner.
from engine.paint_v2.iridescent_insects_firefly_glow_i2_2026 import (
    paint_firefly_glow_i2 as paint_firefly_lantern,
    spec_firefly_glow_i2 as spec_firefly_lantern,
)

# Card 32/50 — Firefly Emberglass I1 P2.  A connected triangulated sheet of
# soot-glass sclerites contains pH-tuned yellow/orange/red chamber wedges,
# active-site clamp rails, quenched pits, seam lips, prism edges and reinforced
# oxygen capillaries. P1 failed M7/FOLLOW; P3 passed but was visually weaker.
from engine.paint_v2.iridescent_insects_firefly_ember_i1_2026 import (
    paint_firefly_ember,
    spec_firefly_ember,
)

# Card 33/50 — Velvet Ant Armor I1 P3. Mutillid hard armor, not recolored
# bumble nap: offset capsule sclerites expose stacked lamella lips and pillar
# bars beneath coherent edge-born grooved setal fans. Armor-weighted regions
# suppress pile and add defensive spines plus compact stridulatory combs.
from engine.paint_v2.iridescent_insects_velvet_ant_i1_2026 import (
    paint_velvet_ant,
    spec_velvet_ant,
)

# Card 34/50 — Orchid Mantis Silk I1 P4. A complete white-pink sheet of
# overlapping bilateral femoral-lobe cuticle fans carries urate reservoirs,
# pigment-export seams, asymmetric growth veins, UV-dark clefts, articulation
# pearls, wet rims and raptorial toothlets as separately bound materials.
from engine.paint_v2.iridescent_insects_orchid_mantis_i1_2026 import (
    paint_orchid_mantis,
    spec_orchid_mantis,
)

# Card 35/50 — Leaf Mantis Patina I1 P6. Thousands of connected 10–29px
# angular crumple segments form a complete Deroplatys dead-leaf lamina with
# attached tear jaws, petiole remnants, patina windows, pore chains and
# serrated lobe edges. P1's perimeter loops were discarded outright.
from engine.paint_v2.iridescent_insects_leaf_mantis_i1_2026 import (
    paint_leaf_mantis,
    spec_leaf_mantis,
)

# Card 36/50 — Katydid Leafglass I1 P4. Branching tegmen midribs and short
# secondary/tertiary veins carry translucent cells, necrotic mimic panes,
# feeding-bite scallops, acoustic mirrors, file teeth and ocellata wet rings.
from engine.paint_v2.iridescent_insects_katydid_leafglass_i1_2026 import (
    paint_katydid_leafglass,
    spec_katydid_leafglass,
)

# Card 37/50 — Stick Insect Bark I1 P2. Long phasmid bark bundles are
# assembled from short splinter marks and interrupted by tergite sutures,
# lichen crust, scar collars, resin wells, tubercles and femoral spines.
from engine.paint_v2.iridescent_insects_stick_insect_bark_i1_2026 import (
    paint_stick_insect_bark,
    spec_stick_insect_bark,
)

# Card 38/50 — Roach Onyx Armor I1 P12. Staggered lacquered tergite shingles
# share one topology with their material states: membranes, gland crescents,
# tongue plates, wax pores, sensory sockets, lips and bounded abrasion.
from engine.paint_v2.iridescent_insects_roach_onyx_i1_2026 import (
    paint_roach_onyx,
    spec_roach_onyx,
)

# Card 39/50 — Weevil Opal Mosaic I1 P4. Thousands of concave scale pits
# carry scale-by-scale single-diamond photonic rosettes with clustered lattice
# classes, grain boundaries, ice rims, microbead points and empty sockets.
from engine.paint_v2.iridescent_insects_weevil_opal_i1_2026 import (
    paint_weevil_opal,
    spec_weevil_opal,
)

# Card 40/50 — Gilded Weevil Striae I1 P4. Broken punctured furrows divide
# convex elytral intervals packed with directional sawtooth scales, polished
# lips, boss crowns, interlocking fibre ridges and anatomy-bounded olive wear.
from engine.paint_v2.iridescent_insects_weevil_gilded_i1_2026 import (
    paint_gilded_weevil,
    spec_gilded_weevil,
)

# Card 41/50 — Scarab Sunplate I1 P4. Interlocking hexagonal shell plates
# contain compact radial helicoid wedges, pitch arcs, polarizer cores,
# diffraction teeth, pore canals, cobalt underplates and worn gold rims.
from engine.paint_v2.iridescent_insects_scarab_sunplate_i1_2026 import (
    paint_scarab_sunplate,
    spec_scarab_sunplate,
)

# Card 42/50 — Scarab Nightshift I1 P6. Flowing lenticular absorber armour
# carries chiral crescent seams, micropillars, moisture channels, cross-ply
# windows, mercury crowns and flooded clearcoat edges.
from engine.paint_v2.iridescent_insects_scarab_nightshift_i1_2026 import (
    paint_scarab_night,
    spec_scarab_night,
)

# Card 43/50 — Jewel Spider Cuticle I1 P2. Soft irregular guanocyte cells
# carry guanine platelet doublets, ruby fluorescent microspheres, silk-root
# filaments, triple junctions and transparent cuticle windows.
from engine.paint_v2.iridescent_insects_jewel_spider_i1_2026 import (
    paint_jewel_spider,
    spec_jewel_spider,
)

# Card 44/50 — Orb Weaver Silk I1 P3. Paired capture fibres cross diagonal
# load arcs and carry viscoelastic glue shells/cores, salt glints, capillary
# spools, pyriform plaques and branching anchor bridges.
from engine.paint_v2.iridescent_insects_orb_weaver_silk_i1_2026 import (
    paint_orb_weaver_silk,
    spec_orb_weaver_silk,
)

# Card 45/50 — Mantis Verdigris I1 P6. Separated articulated bronze
# raptorial chains carry joint membranes, socketed fixed/tilting spines,
# honeycomb grip grooves, worn tips and anatomy-bounded patina.
from engine.paint_v2.iridescent_insects_mantis_verdigris_i1_2026 import (
    paint_mantis_verdigris,
    spec_mantis_verdigris,
)

# Card 46/50 — Hornet Titanium I1 P6. Irregular aerodynamic streams of
# micro-turbine gaster plates carry gland pores, brush hubs, spiracles,
# black joint membranes, yellow cuticle blades and elastic hinge glints.
from engine.paint_v2.iridescent_insects_hornet_titanium_i1_2026 import (
    paint_hornet_titanium,
    spec_hornet_titanium,
)

# Card 47/50 — Leafcutter Copper I1 P8. Controlled diagonal copper
# mandible sheaves carry attached zinc-edged green leaf plates, wear,
# clay, oxide, secretion punctures and polished cutting tips.
from engine.paint_v2.iridescent_insects_leafcutter_copper_i1_2026 import (
    paint_leafcutter_copper,
    spec_leafcutter_copper,
)

# Card 48/50 — Dung Beetle Oilglass I1 P5. Petroleum thin-film contours
# follow corrugated shell basins with wax channels, cracks, pores, setae,
# helicoidal windows, wet troughs, mud contact and compass glints.
from engine.paint_v2.iridescent_insects_dung_beetle_oilglass_i1_2026 import (
    paint_dung_beetle_oilglass,
    spec_dung_beetle_oilglass,
)

# Card 49/50 — Bluebottle Mercury I1 P2. Direction-changing shoals of
# convex mercury ommatidia carry displaced pseudopupils, corneal pustules,
# calypter membranes, branching wing veins, setulae, spiracles and ginger hairs.
from engine.paint_v2.iridescent_insects_bluebottle_mercury_i1_2026 import (
    paint_bluebottle_mercury,
    spec_bluebottle_mercury,
)

# Card 50/50 — Caddiscase Riverstone I1 P3. Individually selected stream
# grains are assembled in imbricated courses and joined by paired wet silk,
# fuzzy adhesive, calcium knots, waterline lips, mica, algae and plant fibre.
from engine.paint_v2.iridescent_insects_caddiscase_riverstone_i1_2026 import (
    paint_caddiscase_riverstone,
    spec_caddiscase_riverstone,
)
