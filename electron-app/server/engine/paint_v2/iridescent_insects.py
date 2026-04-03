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
from engine.core import multi_scale_noise


# ════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ════════════════════════════════════════════════════════════════════

def _insect_micro(shape, seed):
    """Ultra-fine micro shimmer for insect surfaces."""
    m = multi_scale_noise(shape, [1, 2, 3], [0.5, 0.3, 0.2], seed + 600)
    return np.clip(m * 0.5 + 0.5, 0, 1).astype(np.float32)


def _insect_mgrid(shape):
    """Return float32 Y, X coordinate grids."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    return yy.astype(np.float32), xx.astype(np.float32)


def _shape2(shape):
    return shape[:2] if len(shape) > 2 else shape


def _blend_paint(paint, mask, pm, color, strength=0.90):
    m3 = mask[:, :, np.newaxis]
    bl = np.clip(pm * strength, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1 - m3 * bl) + np.clip(color, 0, 1) * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)


def _iridescent_field(shape, seed, scale_mod=1.0):
    """Multi-scale organic flow field for iridescent zone mapping. Returns 0-1."""
    h, w = shape
    scales = [int(16 * scale_mod), int(32 * scale_mod), int(64 * scale_mod)]
    n = multi_scale_noise((h, w), scales, [0.3, 0.4, 0.3], seed)
    return np.clip(n * 0.5 + 0.5, 0, 1).astype(np.float32)


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
    h, w = _shape2(shape)
    field = _iridescent_field((h, w), seed + 9401, scale_mod=0.8)
    micro = _insect_micro((h, w), seed + 9401)
    thickness = np.clip(field + micro * 0.12, 0, 1)
    color = _thin_film_color(thickness, base_hue_shift=0.5)
    # Boost saturation and darken slightly for beetle richness
    color = np.clip(color * 0.85 + 0.05, 0, 1)
    return _blend_paint(paint, mask, pm, color, 0.92)


def spec_beetle_rainbow(shape, seed, sm, base_m, base_r):
    """Beetle rainbow spec: high metallic throughout for shell reflection."""
    h, w = _shape2(shape)
    field = _iridescent_field((h, w), seed + 9401, scale_mod=0.8)
    M = np.clip(200.0 + field * 50.0 * sm, 0, 255)
    R = np.clip(20.0 + (1 - field) * 15.0, 15, 255)
    CC = np.clip(16.0 + field * 8.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 03: BUTTERFLY MORPHO — Morpho blue structural color (angle-dependent)
# Seed: 9402
# ════════════════════════════════════════════════════════════════════

def paint_butterfly_morpho(paint, shape, mask, seed, pm, bb):
    """Morpho butterfly: brilliant blue structural color with angle-dependent flash."""
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    # Simulated viewing-angle gradient (like Morpho wing scales)
    angle_sim = np.clip((1.0 - yf / h) * 0.5 + (xf / w) * 0.5, 0, 1).astype(np.float32)
    # Multi-scale scale pattern (wing scale structure)
    scale_pat = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 9402)
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
    """Morpho spec: extreme metallic on bright zones, mid on deep zones."""
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    angle_sim = np.clip((1.0 - yf / h) * 0.5 + (xf / w) * 0.5, 0, 1)
    scale_pat = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 9402)
    t = np.clip(angle_sim * (0.8 + np.clip(scale_pat * 0.5 + 0.5, 0, 1) * 0.2), 0, 1)
    M = np.clip(100.0 + t * 155.0 * sm, 0, 255)
    R = np.clip(30.0 - t * 15.0 * sm, 15, 255)
    CC = np.clip(16.0 + (1 - t) * 10.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 04: BUTTERFLY MONARCH — orange-black monarch wing pattern
# Seed: 9403
# ════════════════════════════════════════════════════════════════════

def paint_butterfly_monarch(paint, shape, mask, seed, pm, bb):
    """Monarch butterfly: orange-black wing pattern with white spots."""
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    # Wing vein network via Voronoi edges
    rng = np.random.RandomState((seed + 9403) & 0x7FFFFFFF)
    n_cells = 80
    pts_y = rng.uniform(0, h, n_cells).astype(np.float32)
    pts_x = rng.uniform(0, w, n_cells).astype(np.float32)
    pts = np.column_stack([pts_y, pts_x])
    grid_pts = np.column_stack([yf.ravel(), xf.ravel()])
    tree = cKDTree(pts)
    d, idx = tree.query(grid_pts, k=2, workers=-1)
    d1 = d[:, 0].reshape(h, w).astype(np.float32)
    d2 = d[:, 1].reshape(h, w).astype(np.float32)
    # Vein darkness at edges
    vein_width = np.median(d1) * 0.15
    vein = np.clip(1.0 - (d2 - d1) / (vein_width + 1e-8), 0, 1).astype(np.float32)
    # Orange wing fills
    orange = np.array([0.92, 0.48, 0.05], dtype=np.float32)
    black = np.array([0.03, 0.02, 0.02], dtype=np.float32)
    # White spots at border regions
    border = np.clip(np.maximum(yf / h, 1.0 - yf / h) + np.maximum(xf / w, 1.0 - xf / w) - 1.2, 0, 1)
    turb = multi_scale_noise((h, w), [4, 8], [0.5, 0.5], seed + 9403)
    spots = np.clip((turb - 0.3) * 5.0, 0, 1) * border
    white = np.array([0.95, 0.95, 0.95], dtype=np.float32)
    color = orange[None, None, :] * (1 - vein[:, :, None]) + black[None, None, :] * vein[:, :, None]
    color = color * (1 - spots[:, :, None]) + white[None, None, :] * spots[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.92)


def spec_butterfly_monarch(shape, seed, sm, base_m, base_r):
    """Monarch spec: orange zones are satiny, veins are dark matte."""
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    rng = np.random.RandomState((seed + 9403) & 0x7FFFFFFF)
    n_cells = 80
    pts = np.column_stack([rng.uniform(0, h, n_cells), rng.uniform(0, w, n_cells)]).astype(np.float32)
    grid_pts = np.column_stack([yf.ravel(), xf.ravel()])
    tree = cKDTree(pts)
    d, _ = tree.query(grid_pts, k=2, workers=-1)
    d1, d2 = d[:, 0].reshape(h, w).astype(np.float32), d[:, 1].reshape(h, w).astype(np.float32)
    vein = np.clip(1.0 - (d2 - d1) / (np.median(d1) * 0.15 + 1e-8), 0, 1).astype(np.float32)
    M = np.clip(60.0 * (1 - vein) * sm + 5.0 * vein, 0, 255)
    R = np.clip(70.0 * (1 - vein) + 200.0 * vein, 15, 255)
    CC = np.clip(25.0 * (1 - vein) + 100.0 * vein, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 05: DRAGONFLY WING — transparent wing with interference rainbow
# Seed: 9404
# ════════════════════════════════════════════════════════════════════

def paint_dragonfly_wing(paint, shape, mask, seed, pm, bb):
    """Dragonfly wing: semi-transparent wing membrane with rainbow interference."""
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    # Wing vein structure (sparse branching)
    turb = multi_scale_noise((h, w), [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 9404)
    # Detect veins via Sobel edges on turbulence
    ey = sobel(turb, axis=0)
    ex = sobel(turb, axis=1)
    veins = np.sqrt(ey**2 + ex**2)
    veins = np.clip(veins / (np.percentile(veins, 95) + 1e-8), 0, 1).astype(np.float32)
    veins = np.clip(gaussian_filter(veins, sigma=0.8) * 2.5, 0, 1).astype(np.float32)
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
    turb = multi_scale_noise((h, w), [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 9404)
    ey = sobel(turb, axis=0)
    ex = sobel(turb, axis=1)
    veins = np.sqrt(ey**2 + ex**2)
    veins = np.clip(veins / (np.percentile(veins, 95) + 1e-8), 0, 1).astype(np.float32)
    veins = np.clip(gaussian_filter(veins, sigma=0.8) * 2.5, 0, 1).astype(np.float32)
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
    """Scarab gold spec: gold zones extreme chrome, green zones mid-metallic."""
    h, w = _shape2(shape)
    field = _iridescent_field((h, w), seed + 9405)
    micro = _insect_micro((h, w), seed + 9405)
    t = np.clip(field * (0.8 + micro * 0.2), 0, 1)
    M = np.clip(90.0 + t * 165.0 * sm, 0, 255)
    R = np.clip(35.0 - t * 20.0 * sm, 15, 255)
    CC = np.clip(18.0 + (1 - t) * 12.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 07: MOTH LUNA — pale green Luna moth with eye-spot pattern
# Seed: 9406
# ════════════════════════════════════════════════════════════════════

def paint_moth_luna(paint, shape, mask, seed, pm, bb):
    """Luna moth: pale green with large concentric eye-spot patterns."""
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
    turb = multi_scale_noise((h, w), [4, 8, 16], [0.3, 0.4, 0.3], seed + 9406)
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
    M = np.clip(30.0 + eye_map * 80.0 * sm, 0, 255)
    R = np.clip(130.0 - eye_map * 40.0, 15, 255)
    CC = np.clip(80.0 - eye_map * 30.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 08: BEETLE STAG — dark metallic stag beetle armor plates
# Seed: 9407
# ════════════════════════════════════════════════════════════════════

def paint_beetle_stag(paint, shape, mask, seed, pm, bb):
    """Stag beetle: dark metallic brown-black armor plating with chitin shine."""
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    # Armor plate pattern: large Voronoi cells
    rng = np.random.RandomState((seed + 9407) & 0x7FFFFFFF)
    n_cells = 35
    pts = np.column_stack([rng.uniform(0, h, n_cells), rng.uniform(0, w, n_cells)]).astype(np.float32)
    grid_pts = np.column_stack([yf.ravel(), xf.ravel()])
    tree = cKDTree(pts)
    d, idx = tree.query(grid_pts, k=2, workers=-1)
    d1 = d[:, 0].reshape(h, w).astype(np.float32)
    d2 = d[:, 1].reshape(h, w).astype(np.float32)
    cell_id = idx[:, 0].reshape(h, w)
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
    yf, xf = _insect_mgrid((h, w))
    rng = np.random.RandomState((seed + 9407) & 0x7FFFFFFF)
    n_cells = 35
    pts = np.column_stack([rng.uniform(0, h, n_cells), rng.uniform(0, w, n_cells)]).astype(np.float32)
    grid_pts = np.column_stack([yf.ravel(), xf.ravel()])
    tree = cKDTree(pts)
    d, _ = tree.query(grid_pts, k=2, workers=-1)
    d1, d2 = d[:, 0].reshape(h, w).astype(np.float32), d[:, 1].reshape(h, w).astype(np.float32)
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
    M = np.clip(100.0 * band * sm + 40.0 * (1 - band) * sm, 0, 255)
    R = np.clip(30.0 * band + 80.0 * (1 - band), 15, 255)
    CC = np.clip(20.0 * band + 50.0 * (1 - band), 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 10: FIREFLY GLOW — bioluminescent green-yellow glow zones on dark body
# Seed: 9409
# ════════════════════════════════════════════════════════════════════

def paint_firefly_glow(paint, shape, mask, seed, pm, bb):
    """Firefly glow: dark exoskeleton with bioluminescent yellow-green lantern zones."""
    h, w = _shape2(shape)
    yf, xf = _insect_mgrid((h, w))
    rng = np.random.RandomState((seed + 9409) & 0x7FFFFFFF)
    # Dark body base
    dark_body = np.array([0.04, 0.04, 0.03], dtype=np.float32)
    # Glow zones: ~15 scattered lantern spots in lower half
    n_glows = 15
    gy = rng.uniform(h * 0.4, h * 0.95, n_glows).astype(np.float32)
    gx = rng.uniform(0, w, n_glows).astype(np.float32)
    glow_r = rng.uniform(20, 60, n_glows).astype(np.float32)
    brightness = rng.uniform(0.5, 1.0, n_glows).astype(np.float32)
    glow_map = np.zeros((h, w), dtype=np.float32)
    for k in range(n_glows):
        dist = np.sqrt((yf - gy[k])**2 + (xf - gx[k])**2)
        glow = np.exp(-(dist / glow_r[k])**2) * brightness[k]
        glow_map = np.maximum(glow_map, glow)
    glow_map = np.clip(glow_map, 0, 1).astype(np.float32)
    # Subtle body texture
    turb = multi_scale_noise((h, w), [2, 4, 8], [0.4, 0.35, 0.25], seed + 9409)
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
    yf, xf = _insect_mgrid((h, w))
    rng = np.random.RandomState((seed + 9409) & 0x7FFFFFFF)
    n_glows = 15
    gy = rng.uniform(h * 0.4, h * 0.95, n_glows).astype(np.float32)
    gx = rng.uniform(0, w, n_glows).astype(np.float32)
    glow_r = rng.uniform(20, 60, n_glows).astype(np.float32)
    brightness = rng.uniform(0.5, 1.0, n_glows).astype(np.float32)
    glow_map = np.zeros((h, w), dtype=np.float32)
    for k in range(n_glows):
        dist = np.sqrt((yf - gy[k])**2 + (xf - gx[k])**2)
        glow = np.exp(-(dist / glow_r[k])**2) * brightness[k]
        glow_map = np.maximum(glow_map, glow)
    glow_map = np.clip(glow_map, 0, 1).astype(np.float32)
    M = np.clip(10.0 + glow_map * 220.0 * sm, 0, 255)
    R = np.clip(170.0 - glow_map * 155.0 * sm, 15, 255)
    CC = np.clip(70.0 - glow_map * 54.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)
