"""
engine/paint_v2/anime_style.py — ★ ANIME INSPIRED Finishes (Pack #7)
10 anime/manga-inspired finishes with married paint+spec pairs.

ALL spatial features scaled for 2048x2048 full-car textures.
ALL rendering fully vectorized — ZERO per-pixel Python loops.
Uses scipy + vectorized numpy throughout.

Seed offsets: 9300-9309.
"""
import numpy as np
from scipy.ndimage import sobel, gaussian_filter
from engine.core import multi_scale_noise


# ════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ════════════════════════════════════════════════════════════════════

def _anime_micro(shape, seed):
    """Ultra-fine shimmer at 1-3px for anime metallic accents."""
    m = multi_scale_noise(shape, [1, 2, 3], [0.5, 0.3, 0.2], seed + 500)
    return np.clip(m * 0.5 + 0.5, 0, 1).astype(np.float32)


def _anime_mgrid(shape):
    """Return float32 Y, X coordinate grids."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    return yy.astype(np.float32), xx.astype(np.float32)


def _shape2(shape):
    """Normalize shape to (h, w)."""
    return shape[:2] if len(shape) > 2 else shape


def _blend_paint(paint, mask, pm, color, strength=0.90):
    """Standard masked color blend for paint_fn."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    m3 = mask[:, :, np.newaxis]
    bl = np.clip(pm * strength, 0, 1)
    paint[:, :, :3] = paint[:, :, :3] * (1 - m3 * bl) + np.clip(color, 0, 1) * m3 * bl
    return np.clip(paint, 0, 1).astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 01: ANIME CEL SHADE CHROME — flat shading with sharp metallic bands
# Seed: 9300
# ════════════════════════════════════════════════════════════════════

def paint_anime_cel_shade_chrome(paint, shape, mask, seed, pm, bb):
    """Cel-shaded chrome: quantized light bands with hard steps, metallic highlight pops."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, xf = _anime_mgrid((h, w))
    # Simulated light direction from top-right
    light = np.clip((1.0 - yf / h) * 0.6 + (xf / w) * 0.4, 0, 1).astype(np.float32)
    # Add surface variation
    turb = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 9300)
    light = np.clip(light + turb * 0.15, 0, 1)
    # Quantize to 5 cel-shade levels (anime-style hard steps)
    levels = 5
    cel = (np.floor(light * levels) / (levels - 1)).astype(np.float32)
    # Colors: dark steel base to bright chrome highlight
    dark = np.array([0.08, 0.10, 0.16], dtype=np.float32)
    mid = np.array([0.30, 0.35, 0.50], dtype=np.float32)
    bright = np.array([0.85, 0.88, 0.95], dtype=np.float32)
    # Lerp dark -> mid -> bright based on cel level
    low_mask = (cel < 0.5).astype(np.float32)
    t_low = cel * 2.0
    t_hi = (cel - 0.5) * 2.0
    color = (dark[None, None, :] * (1 - t_low[:, :, None]) + mid[None, None, :] * t_low[:, :, None]) * low_mask[:, :, None] + \
            (mid[None, None, :] * (1 - t_hi[:, :, None]) + bright[None, None, :] * t_hi[:, :, None]) * (1 - low_mask[:, :, None])
    return _blend_paint(paint, mask, pm, color, 0.92)


def spec_anime_cel_shade_chrome(shape, seed, sm, base_m, base_r):
    """Cel-shade chrome spec: high M on bright bands, low on dark. R >= 15."""
    h, w = _shape2(shape)
    yf, xf = _anime_mgrid((h, w))
    light = np.clip((1.0 - yf / h) * 0.6 + (xf / w) * 0.4, 0, 1)
    turb = multi_scale_noise((h, w), [8, 16, 32], [0.3, 0.4, 0.3], seed + 9300)
    light = np.clip(light + turb * 0.15, 0, 1)
    cel = (np.floor(light * 5) / 4).astype(np.float32)
    M = np.clip(40.0 + cel * 210.0 * sm, 0, 255)
    R = np.clip(120.0 - cel * 100.0 * sm, 15, 255)
    CC = np.clip(20.0 + (1 - cel) * 30.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 02: ANIME SPEED LINES — directional motion lines radiating from center
# Seed: 9301
# ════════════════════════════════════════════════════════════════════

def paint_anime_speed_lines(paint, shape, mask, seed, pm, bb):
    """Speed lines: radial streaks from center-right (anime motion effect)."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, xf = _anime_mgrid((h, w))
    # Focal point: center-right of texture
    cy, cx = h * 0.5, w * 0.7
    dy, dx = yf - cy, xf - cx
    theta = np.arctan2(dy, dx)
    r = np.sqrt(dy**2 + dx**2) + 1e-8
    # Radial lines via high-frequency angular sin
    rng = np.random.RandomState((seed + 9301) & 0x7FFFFFFF)
    n_lines = 120
    freq = n_lines / (2.0 * np.pi)
    phase = rng.uniform(0, 2 * np.pi)
    raw_lines = np.abs(np.sin(theta * freq + phase))
    # Sharpen to thin lines
    lines = np.clip((0.12 - raw_lines) * 20.0, 0, 1).astype(np.float32)
    # Fade near center (no lines at focal point)
    r_norm = np.clip(r / (max(h, w) * 0.5), 0, 1)
    lines *= np.clip(r_norm * 2.0 - 0.3, 0, 1)
    # Vary line intensity with noise
    turb = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 9301)
    lines *= np.clip(turb * 0.5 + 0.7, 0.3, 1.0)
    # White lines on dark base
    dark_base = np.array([0.06, 0.06, 0.10], dtype=np.float32)
    line_white = np.array([0.95, 0.95, 1.00], dtype=np.float32)
    color = dark_base[None, None, :] * (1 - lines[:, :, None]) + line_white[None, None, :] * lines[:, :, None]
    return _blend_paint(paint, mask, pm, color, 0.88)


def spec_anime_speed_lines(shape, seed, sm, base_m, base_r):
    """Speed lines spec: lines are bright metallic, base is matte dark."""
    h, w = _shape2(shape)
    yf, xf = _anime_mgrid((h, w))
    cy, cx = h * 0.5, w * 0.7
    dy, dx = yf - cy, xf - cx
    theta = np.arctan2(dy, dx)
    r = np.sqrt(dy**2 + dx**2) + 1e-8
    rng = np.random.RandomState((seed + 9301) & 0x7FFFFFFF)
    freq = 120 / (2.0 * np.pi)
    phase = rng.uniform(0, 2 * np.pi)
    raw_lines = np.abs(np.sin(theta * freq + phase))
    lines = np.clip((0.12 - raw_lines) * 20.0, 0, 1).astype(np.float32)
    r_norm = np.clip(r / (max(h, w) * 0.5), 0, 1)
    lines *= np.clip(r_norm * 2.0 - 0.3, 0, 1)
    M = np.clip(30.0 + lines * 220.0 * sm, 0, 255)
    R = np.clip(140.0 - lines * 120.0 * sm, 15, 255)
    CC = np.clip(40.0 - lines * 20.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 03: ANIME SPARKLE BURST — concentrated starburst sparkle clusters
# Seed: 9302
# ════════════════════════════════════════════════════════════════════

_sparkle_burst_cache = {}

def _get_sparkle_burst_map(shape, seed):
    """Cached sparkle burst field — shared between paint and spec."""
    _key = (shape, seed)
    if _key in _sparkle_burst_cache:
        return _sparkle_burst_cache[_key]
    h, w = shape
    yf, xf = _anime_mgrid((h, w))
    rng = np.random.RandomState((seed + 9302) & 0x7FFFFFFF)
    n_sparkles = 40
    sy = rng.uniform(0, h, n_sparkles).astype(np.float32)
    sx = rng.uniform(0, w, n_sparkles).astype(np.float32)
    sizes = rng.uniform(15, 60, n_sparkles).astype(np.float32)
    brightnesses = rng.uniform(0.5, 1.0, n_sparkles).astype(np.float32)
    # Vectorized: only compute sparkles near their center (skip far pixels)
    sparkle_map = np.zeros((h, w), dtype=np.float32)
    for k in range(n_sparkles):
        # Only compute in a bounding box around the sparkle (3x size radius)
        radius = int(sizes[k] * 3)
        y0, y1 = max(0, int(sy[k]) - radius), min(h, int(sy[k]) + radius)
        x0, x1 = max(0, int(sx[k]) - radius), min(w, int(sx[k]) + radius)
        if y1 <= y0 or x1 <= x0:
            continue
        dy = yf[y0:y1, x0:x1] - sy[k]
        dx = xf[y0:y1, x0:x1] - sx[k]
        s = sizes[k]
        ax_v = np.exp(-np.abs(dx) / s) * np.exp(-np.abs(dy) / (s * 0.08))
        ax_h = np.exp(-np.abs(dy) / s) * np.exp(-np.abs(dx) / (s * 0.08))
        star = np.clip(ax_v + ax_h, 0, 1) * brightnesses[k]
        sparkle_map[y0:y1, x0:x1] = np.maximum(sparkle_map[y0:y1, x0:x1], star)
    sparkle_map = np.clip(sparkle_map, 0, 1).astype(np.float32)
    if len(_sparkle_burst_cache) > 4:
        _sparkle_burst_cache.pop(next(iter(_sparkle_burst_cache)))
    _sparkle_burst_cache[_key] = sparkle_map
    return sparkle_map

def paint_anime_sparkle_burst(paint, shape, mask, seed, pm, bb):
    """Sparkle burst: concentrated 4-pointed star clusters scattered across surface."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    sparkle_map = _get_sparkle_burst_map((h, w), seed)
    # Deep midnight blue base + white-gold sparkles
    base_col = np.array([0.04, 0.04, 0.12], dtype=np.float32)
    sparkle_col = np.array([1.0, 0.97, 0.85], dtype=np.float32)
    color = base_col[None, None, :] * (1 - sparkle_map[:, :, None]) + sparkle_col[None, None, :] * sparkle_map[:, :, None]
    return _blend_paint(paint, mask, pm, color, 0.90)


def spec_anime_sparkle_burst(shape, seed, sm, base_m, base_r):
    """Sparkle burst spec: sparkles are pure chrome, base is deep matte. Uses cached map."""
    h, w = _shape2(shape)
    sparkle_map = _get_sparkle_burst_map((h, w), seed)
    M = np.clip(15.0 + sparkle_map * 240.0 * sm, 0, 255)
    R = np.clip(180.0 - sparkle_map * 160.0 * sm, 15, 255)
    CC = np.clip(50.0 - sparkle_map * 34.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 04: ANIME GRADIENT HAIR — smooth anime-style vivid top to dark bottom
# Seed: 9303
# ════════════════════════════════════════════════════════════════════

def paint_anime_gradient_hair(paint, shape, mask, seed, pm, bb):
    """Gradient hair: vivid saturated color at top fading to deep dark at bottom."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, _ = _anime_mgrid((h, w))
    t = np.clip(yf / h, 0, 1).astype(np.float32)
    # Add subtle wave to the gradient boundary
    turb = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 9303)
    t = np.clip(t + turb * 0.08, 0, 1)
    # Vivid magenta-pink at top -> deep indigo at bottom
    top_col = np.array([0.90, 0.15, 0.55], dtype=np.float32)
    mid_col = np.array([0.55, 0.08, 0.65], dtype=np.float32)
    bot_col = np.array([0.06, 0.02, 0.18], dtype=np.float32)
    # Two-stage lerp
    upper = (t < 0.5).astype(np.float32)
    t1 = t * 2.0
    t2 = (t - 0.5) * 2.0
    color = (top_col[None, None, :] * (1 - t1[:, :, None]) + mid_col[None, None, :] * t1[:, :, None]) * upper[:, :, None] + \
            (mid_col[None, None, :] * (1 - t2[:, :, None]) + bot_col[None, None, :] * t2[:, :, None]) * (1 - upper[:, :, None])
    # Subtle hair strand texture
    strand = multi_scale_noise((h, w), [1, 2], [0.6, 0.4], seed + 9304)
    color = np.clip(color + strand[:, :, None] * 0.04, 0, 1)
    return _blend_paint(paint, mask, pm, color, 0.92)


def spec_anime_gradient_hair(shape, seed, sm, base_m, base_r):
    """Gradient hair spec: glossy silky sheen that shifts from reflective top to matte bottom."""
    h, w = _shape2(shape)
    yf, _ = _anime_mgrid((h, w))
    t = np.clip(yf / h, 0, 1).astype(np.float32)
    M = np.clip(180.0 - t * 140.0 * sm, 0, 255)
    R = np.clip(25.0 + t * 80.0, 15, 255)
    CC = np.clip(18.0 + t * 20.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 05: ANIME MECHA PLATE — hard geometric panel lines with metallic zones
# Seed: 9304
# ════════════════════════════════════════════════════════════════════

def paint_anime_mecha_plate(paint, shape, mask, seed, pm, bb):
    """Mecha plate: hard rectangular panel lines with alternating metallic zones."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, xf = _anime_mgrid((h, w))
    # Panel grid: large panels with hard edges
    panel_h = max(20, h // 12)
    panel_w = max(20, w // 8)
    # Panel cell coords
    py = (yf % panel_h) / panel_h
    px = (xf % panel_w) / panel_w
    # Panel ID for alternating color
    pid_y = (yf // panel_h).astype(np.int32)
    pid_x = (xf // panel_w).astype(np.int32)
    checker = ((pid_y + pid_x) % 2).astype(np.float32)
    # Edge detection: seam lines at panel boundaries
    edge_y = np.clip((0.03 - np.minimum(py, 1.0 - py)) * 40.0, 0, 1).astype(np.float32)
    edge_x = np.clip((0.03 - np.minimum(px, 1.0 - px)) * 40.0, 0, 1).astype(np.float32)
    seam = np.clip(edge_y + edge_x, 0, 1)
    # Add subtle per-panel shade variation
    turb = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 9304)
    # Colors: gunmetal blue vs steel gray panels, dark seam lines
    panel_a = np.array([0.20, 0.25, 0.38], dtype=np.float32)
    panel_b = np.array([0.40, 0.42, 0.48], dtype=np.float32)
    seam_col = np.array([0.02, 0.02, 0.04], dtype=np.float32)
    # Rivet dots at intersections
    rivet = np.clip((0.02 - np.sqrt(np.minimum(py, 1.0 - py)**2 + np.minimum(px, 1.0 - px)**2)) * 60.0, 0, 1)
    rivet_col = np.array([0.55, 0.58, 0.62], dtype=np.float32)
    panel_color = panel_a[None, None, :] * checker[:, :, None] + panel_b[None, None, :] * (1 - checker[:, :, None])
    panel_color += turb[:, :, None] * 0.06
    color = panel_color * (1 - seam[:, :, None]) + seam_col[None, None, :] * seam[:, :, None]
    color = color * (1 - rivet[:, :, None]) + rivet_col[None, None, :] * rivet[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.92)


def spec_anime_mecha_plate(shape, seed, sm, base_m, base_r):
    """Mecha plate spec: panels are metallic, seams are rough dark gaps."""
    h, w = _shape2(shape)
    yf, xf = _anime_mgrid((h, w))
    panel_h = max(20, h // 12)
    panel_w = max(20, w // 8)
    py = (yf % panel_h) / panel_h
    px = (xf % panel_w) / panel_w
    edge_y = np.clip((0.03 - np.minimum(py, 1.0 - py)) * 40.0, 0, 1)
    edge_x = np.clip((0.03 - np.minimum(px, 1.0 - px)) * 40.0, 0, 1)
    seam = np.clip(edge_y + edge_x, 0, 1).astype(np.float32)
    M = np.clip(200.0 * (1 - seam) * sm + 10.0 * seam, 0, 255)
    R = np.clip(35.0 * (1 - seam) + 200.0 * seam, 15, 255)
    CC = np.clip(20.0 * (1 - seam) + 80.0 * seam, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 06: ANIME SAKURA SCATTER — cherry blossom petal scatter pattern
# Seed: 9305
# ════════════════════════════════════════════════════════════════════

_sakura_cache = {}

def _get_sakura_map(shape, seed):
    """Cached sakura petal field — shared between paint and spec."""
    _key = (shape, seed)
    if _key in _sakura_cache:
        return _sakura_cache[_key]
    h, w = shape
    yf, xf = _anime_mgrid((h, w))
    rng = np.random.RandomState((seed + 9305) & 0x7FFFFFFF)
    n_petals = 60
    py_c = rng.uniform(0, h, n_petals).astype(np.float32)
    px_c = rng.uniform(0, w, n_petals).astype(np.float32)
    angles = rng.uniform(0, np.pi, n_petals).astype(np.float32)
    sizes = rng.uniform(8, 25, n_petals).astype(np.float32)
    petal_map = np.zeros((h, w), dtype=np.float32)
    for k in range(n_petals):
        radius = int(sizes[k] * 4)
        y0, y1 = max(0, int(py_c[k]) - radius), min(h, int(py_c[k]) + radius)
        x0, x1 = max(0, int(px_c[k]) - radius), min(w, int(px_c[k]) + radius)
        if y1 <= y0 or x1 <= x0:
            continue
        dy = yf[y0:y1, x0:x1] - py_c[k]
        dx = xf[y0:y1, x0:x1] - px_c[k]
        ca, sa = np.cos(angles[k]), np.sin(angles[k])
        ry = dy * ca - dx * sa
        rx = dy * sa + dx * ca
        s = sizes[k]
        petal = np.exp(-(rx**2) / (s**2 * 0.15) - (ry**2) / (s**2 * 0.6))
        petal_map[y0:y1, x0:x1] = np.maximum(petal_map[y0:y1, x0:x1], petal)
    petal_map = np.clip(petal_map, 0, 1).astype(np.float32)
    if len(_sakura_cache) > 4:
        _sakura_cache.pop(next(iter(_sakura_cache)))
    _sakura_cache[_key] = petal_map
    return petal_map

def paint_anime_sakura_scatter(paint, shape, mask, seed, pm, bb):
    """Sakura scatter: cherry blossom petals drifting across a soft pink-white surface."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    petal_map = _get_sakura_map((h, w), seed)
    bg = np.array([0.95, 0.88, 0.90], dtype=np.float32)
    petal_col = np.array([0.92, 0.55, 0.62], dtype=np.float32)
    petal_center = np.array([0.98, 0.80, 0.82], dtype=np.float32)
    petal_color = petal_col[None, None, :] * 0.7 + petal_center[None, None, :] * 0.3
    color = bg[None, None, :] * (1 - petal_map[:, :, None]) + petal_color[None, None, :] * petal_map[:, :, None]
    return _blend_paint(paint, mask, pm, color, 0.88)


def spec_anime_sakura_scatter(shape, seed, sm, base_m, base_r):
    """Sakura spec: soft satin petals on smooth background. Uses cached petal map.

    2026-04-20 HEENAN AUTO-LOOP-15 — the weakest anime_style spec
    (measured dM=60 dR=20 dCC=8 at seed=42 shape=256²). Petals should
    pop against the background with stronger material contrast:
    background dielectric satin, petals chrome-bright pearlescent.
    Widen:
      M amp 60→130 (bg 80 dielectric, petal peaks 210 metallic)
      R amp 20→40 (petals smoother than before; bg scattered)
      CC amp 8→20 (petal surface film thickens)
    """
    h, w = _shape2(shape)
    petal_map = _get_sakura_map((h, w), seed)
    M = np.clip(80.0 + petal_map * 130.0 * sm, 0, 255)
    R = np.clip(55.0 - petal_map * 40.0, 15, 255)
    CC = np.clip(16.0 + petal_map * 20.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 07: ANIME ENERGY AURA — glowing energy field with radial power lines
# Seed: 9306
# ════════════════════════════════════════════════════════════════════

def paint_anime_energy_aura(paint, shape, mask, seed, pm, bb):
    """Energy aura: radial glowing lines emanating outward with power-up glow zones."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, xf = _anime_mgrid((h, w))
    cy, cx = h * 0.5, w * 0.5
    dy, dx = yf - cy, xf - cx
    r = np.sqrt(dy**2 + dx**2) + 1e-8
    theta = np.arctan2(dy, dx)
    r_norm = np.clip(r / (max(h, w) * 0.5), 0, 1)
    # Radial energy lines
    n_rays = 24
    ray_raw = np.abs(np.sin(theta * n_rays * 0.5))
    rays = np.clip((0.15 - ray_raw) * 12.0, 0, 1).astype(np.float32)
    # Pulsing concentric rings
    rings = np.clip(np.abs(np.sin(r * 0.08)) * 1.5, 0, 1).astype(np.float32)
    # Core glow
    core = np.exp(-r_norm * 3.0).astype(np.float32)
    # Turbulence
    turb = multi_scale_noise((h, w), [16, 32, 64], [0.3, 0.4, 0.3], seed + 9306)
    turb_n = np.clip(turb * 0.5 + 0.5, 0, 1)
    energy = np.clip(rays * 0.6 + rings * 0.3 + core * 0.8 + turb_n * 0.15, 0, 1)
    # Electric blue-white energy on dark base
    dark = np.array([0.02, 0.02, 0.08], dtype=np.float32)
    glow_inner = np.array([0.40, 0.75, 1.00], dtype=np.float32)
    glow_core = np.array([0.95, 0.98, 1.00], dtype=np.float32)
    color = dark[None, None, :] * (1 - energy[:, :, None]) + \
            glow_inner[None, None, :] * energy[:, :, None] * (1 - core[:, :, None] * 0.6) + \
            glow_core[None, None, :] * core[:, :, None] * 0.6
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.92)


def spec_anime_energy_aura(shape, seed, sm, base_m, base_r):
    """Energy aura spec: core is super chrome, rays are bright metallic, dark is matte."""
    h, w = _shape2(shape)
    yf, xf = _anime_mgrid((h, w))
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt((yf - cy)**2 + (xf - cx)**2) + 1e-8
    r_norm = np.clip(r / (max(h, w) * 0.5), 0, 1)
    core = np.exp(-r_norm * 3.0).astype(np.float32)
    theta = np.arctan2(yf - cy, xf - cx)
    rays = np.clip((0.15 - np.abs(np.sin(theta * 12.0))) * 12.0, 0, 1).astype(np.float32)
    energy = np.clip(core * 0.7 + rays * 0.3, 0, 1)
    M = np.clip(20.0 + energy * 235.0 * sm, 0, 255)
    R = np.clip(160.0 - energy * 145.0 * sm, 15, 255)
    CC = np.clip(45.0 - energy * 29.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 08: ANIME COMIC HALFTONE — Ben-Day dot pattern with size variation
# Seed: 9307
# ════════════════════════════════════════════════════════════════════

def paint_anime_comic_halftone(paint, shape, mask, seed, pm, bb):
    """Comic halftone: Ben-Day dots that vary in size based on a gradient field."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    yf, xf = _anime_mgrid((h, w))
    # Dot grid spacing
    spacing = max(6, min(h, w) // 100)
    # Dot center distance
    cy_mod = (yf % spacing) - spacing * 0.5
    cx_mod = (xf % spacing) - spacing * 0.5
    dist_to_center = np.sqrt(cy_mod**2 + cx_mod**2)
    # Size modulation: gradient from top-left (large dots) to bottom-right (small)
    gradient = np.clip((yf / h) * 0.6 + (xf / w) * 0.4, 0, 1).astype(np.float32)
    turb = multi_scale_noise((h, w), [16, 32], [0.5, 0.5], seed + 9307)
    gradient = np.clip(gradient + turb * 0.1, 0, 1)
    # Dot radius varies: big where gradient is low, small where high
    max_r = spacing * 0.45
    min_r = spacing * 0.08
    dot_r = min_r + (max_r - min_r) * (1 - gradient)
    dots = np.clip((dot_r - dist_to_center) / (spacing * 0.05 + 1e-6), 0, 1).astype(np.float32)
    # Magenta dots on cream-white paper
    paper = np.array([0.96, 0.94, 0.90], dtype=np.float32)
    dot_color = np.array([0.85, 0.10, 0.35], dtype=np.float32)
    color = paper[None, None, :] * (1 - dots[:, :, None]) + dot_color[None, None, :] * dots[:, :, None]
    return _blend_paint(paint, mask, pm, color, 0.90)


def spec_anime_comic_halftone(shape, seed, sm, base_m, base_r):
    """Halftone spec: paper is matte, dots have slight metallic ink sheen."""
    h, w = _shape2(shape)
    yf, xf = _anime_mgrid((h, w))
    spacing = max(6, min(h, w) // 100)
    cy_mod = (yf % spacing) - spacing * 0.5
    cx_mod = (xf % spacing) - spacing * 0.5
    dist_to_center = np.sqrt(cy_mod**2 + cx_mod**2)
    gradient = np.clip((yf / h) * 0.6 + (xf / w) * 0.4, 0, 1)
    dot_r = spacing * 0.08 + (spacing * 0.37) * (1 - gradient)
    dots = np.clip((dot_r - dist_to_center) / (spacing * 0.05 + 1e-6), 0, 1).astype(np.float32)
    # 2026-04-20 HEENAN AUTO-LOOP-16 — halftone paper + magenta ink
    # dots. Pre-tune dM=80 dR=50 dCC=20 — paper and dots looked too
    # similar. Real halftone ink has wet-metallic surface sheen vs
    # matte-absorbent paper. Widen:
    #   M amp 80→170 (paper 5 dielectric, dots 175 near-metallic ink)
    #   R amp 50→90 (paper 140 scattered, dots 50 smooth wet-ink)
    #   CC amp 20→40 (paper 80 thin/dull, dots 40 thicker glossy film)
    M = np.clip(5.0 + dots * 170.0 * sm, 0, 255)
    R = np.clip(140.0 - dots * 90.0, 15, 255)
    CC = np.clip(80.0 - dots * 40.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 09: ANIME NEON OUTLINE — dark base with bright neon edge highlights
# Seed: 9308
# ════════════════════════════════════════════════════════════════════

def paint_anime_neon_outline(paint, shape, mask, seed, pm, bb):
    """Neon outline: dark surface with glowing neon edge lines (Sobel-detected contours)."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    # Generate a structural pattern to find edges on
    turb = multi_scale_noise((h, w), [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 9308)
    # Sobel edge detection (vectorized)
    edge_y = sobel(turb, axis=0)
    edge_x = sobel(turb, axis=1)
    edges = np.sqrt(edge_y**2 + edge_x**2)
    edges = np.clip(edges / (np.percentile(edges, 98) + 1e-8), 0, 1).astype(np.float32)
    # Thicken edges slightly
    edges = np.clip(gaussian_filter(edges, sigma=1.0) * 2.0, 0, 1).astype(np.float32)
    # Micro noise for glow variation
    glow_var = multi_scale_noise((h, w), [32, 64], [0.5, 0.5], seed + 9309)
    glow_var_n = np.clip(glow_var * 0.3 + 0.7, 0.5, 1.0)
    edges *= glow_var_n
    # Dark base with neon cyan-magenta edges
    dark = np.array([0.03, 0.03, 0.06], dtype=np.float32)
    neon_cyan = np.array([0.10, 0.90, 0.95], dtype=np.float32)
    neon_magenta = np.array([0.90, 0.15, 0.80], dtype=np.float32)
    # Mix neon colors by position
    yf, xf = _anime_mgrid((h, w))
    mix = np.clip(xf / w, 0, 1).astype(np.float32)
    neon_col = neon_cyan[None, None, :] * (1 - mix[:, :, None]) + neon_magenta[None, None, :] * mix[:, :, None]
    color = dark[None, None, :] * (1 - edges[:, :, None]) + neon_col * edges[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1), 0.92)


def spec_anime_neon_outline(shape, seed, sm, base_m, base_r):
    """Neon outline spec: edges glow chrome, base is ultra-matte dark."""
    h, w = _shape2(shape)
    turb = multi_scale_noise((h, w), [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 9308)
    edge_y = sobel(turb, axis=0)
    edge_x = sobel(turb, axis=1)
    edges = np.sqrt(edge_y**2 + edge_x**2)
    edges = np.clip(edges / (np.percentile(edges, 98) + 1e-8), 0, 1).astype(np.float32)
    edges = np.clip(gaussian_filter(edges, sigma=1.0) * 2.0, 0, 1).astype(np.float32)
    M = np.clip(10.0 + edges * 245.0 * sm, 0, 255)
    R = np.clip(200.0 - edges * 185.0 * sm, 15, 255)
    CC = np.clip(60.0 - edges * 44.0, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)


# ════════════════════════════════════════════════════════════════════
# 10: ANIME CRYSTAL FACET — large angular crystalline facets with color
# Seed: 9309
# ════════════════════════════════════════════════════════════════════

def paint_anime_crystal_facet(paint, shape, mask, seed, pm, bb):
    """Crystal facet: large geometric Voronoi-style facets, each with unique color."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    h, w = _shape2(shape)
    rng = np.random.RandomState((seed + 9309) & 0x7FFFFFFF)
    # Voronoi cells for facets (~50 large cells)
    n_cells = 50
    pts_y = rng.uniform(0, h, n_cells).astype(np.float32)
    pts_x = rng.uniform(0, w, n_cells).astype(np.float32)
    pts = np.column_stack([pts_y, pts_x])
    yy, xx = np.mgrid[0:h, 0:w]
    grid_pts = np.column_stack([yy.ravel().astype(np.float32), xx.ravel().astype(np.float32)])
    from scipy.spatial import cKDTree
    tree = cKDTree(pts)
    d, idx = tree.query(grid_pts, k=2, workers=-1)
    cell_id = idx[:, 0].reshape(h, w)
    d1 = d[:, 0].reshape(h, w).astype(np.float32)
    d2 = d[:, 1].reshape(h, w).astype(np.float32)
    # Edge factor
    edge = np.clip(1.0 - (d2 - d1) / (np.median(d1) * 0.3 + 1e-8), 0, 1).astype(np.float32)
    # Per-cell colors (anime jewel tones)
    hues = rng.uniform(0, 1, n_cells).astype(np.float32)
    sats = rng.uniform(0.6, 1.0, n_cells).astype(np.float32)
    vals = rng.uniform(0.4, 0.85, n_cells).astype(np.float32)
    # HSV to RGB vectorized
    cell_colors = np.zeros((n_cells, 3), dtype=np.float32)
    for c in range(n_cells):
        hue = hues[c] * 6.0
        hi = int(hue) % 6
        f = hue - int(hue)
        v, s = vals[c], sats[c]
        p, q, t_v = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
        if hi == 0: cell_colors[c] = [v, t_v, p]
        elif hi == 1: cell_colors[c] = [q, v, p]
        elif hi == 2: cell_colors[c] = [p, v, t_v]
        elif hi == 3: cell_colors[c] = [p, q, v]
        elif hi == 4: cell_colors[c] = [t_v, p, v]
        else: cell_colors[c] = [v, p, q]
    # Map cell_id to color
    color = cell_colors[cell_id]
    # Add inner facet gradient (lighter toward center)
    max_d1 = np.maximum(d1.max(), 1.0)
    inner_grad = np.clip(1.0 - d1 / (max_d1 * 0.5), 0, 0.3)
    color = np.clip(color + inner_grad[:, :, None], 0, 1)
    # Dark edges
    edge_col = np.array([0.02, 0.02, 0.06], dtype=np.float32)
    color = color * (1 - edge[:, :, None]) + edge_col[None, None, :] * edge[:, :, None]
    return _blend_paint(paint, mask, pm, np.clip(color, 0, 1).astype(np.float32), 0.92)


def spec_anime_crystal_facet(shape, seed, sm, base_m, base_r):
    """Crystal facet spec: facet faces are glossy metallic, edges are rough gaps."""
    h, w = _shape2(shape)
    rng = np.random.RandomState((seed + 9309) & 0x7FFFFFFF)
    n_cells = 50
    pts_y = rng.uniform(0, h, n_cells).astype(np.float32)
    pts_x = rng.uniform(0, w, n_cells).astype(np.float32)
    pts = np.column_stack([pts_y, pts_x])
    yy, xx = np.mgrid[0:h, 0:w]
    grid_pts = np.column_stack([yy.ravel().astype(np.float32), xx.ravel().astype(np.float32)])
    from scipy.spatial import cKDTree
    tree = cKDTree(pts)
    d, idx = tree.query(grid_pts, k=2, workers=-1)
    d1 = d[:, 0].reshape(h, w).astype(np.float32)
    d2 = d[:, 1].reshape(h, w).astype(np.float32)
    edge = np.clip(1.0 - (d2 - d1) / (np.median(d1) * 0.3 + 1e-8), 0, 1).astype(np.float32)
    M = np.clip(220.0 * (1 - edge) * sm + 10.0 * edge, 0, 255)
    R = np.clip(20.0 * (1 - edge) + 180.0 * edge, 15, 255)
    CC = np.clip(16.0 * (1 - edge) + 70.0 * edge, 16, 255)
    return M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32)
