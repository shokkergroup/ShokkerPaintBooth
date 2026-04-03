"""
Shokker Specials Overhaul - 2026-03-08
=======================================
Adds MISSING and REWRITES WEAK entries across:
  - Dark & Gothic (10 missing: cursed, eclipse, nightmare, possessed, reaper, rust_upgrade, voodoo, wraith, worn_chrome_v2, weathered_v2)
  - Effect & Visual (6 missing: depth_map, double_exposure, infrared, polarized, uv_blacklight, x_ray;
                    replace 13 boilerplate specs with custom PBR)
  - Shokk Series: replace flat spec stubs with custom ones

Called by shokker_engine_v2.py AFTER the 24k expansion loads.
"""
import numpy as np
from scipy.ndimage import gaussian_filter, zoom as _scipy_zoom


# ---------------------------------------------------------------------------
# INTERNAL NOISE HELPER
# ---------------------------------------------------------------------------
def _msn(shape, scales, weights, seed):
    """Multi-scale Perlin-like noise, returns float32 -1..1."""
    h, w = shape
    rng = np.random.RandomState(seed & 0x7FFFFFFF)
    out = np.zeros((h, w), dtype=np.float32)
    for s, wt in zip(scales, weights):
        coarse = rng.randn(max(2, h // s), max(2, w // s)).astype(np.float32)
        try:
            up = _scipy_zoom(coarse, (h / coarse.shape[0], w / coarse.shape[1]), order=1)
            up = up[:h, :w]
        except Exception:
            up = np.zeros((h, w), dtype=np.float32)
        out += up * wt
    mx = np.abs(out).max()
    return out / mx if mx > 1e-6 else out


def _mgrid(shape):
    h, w = shape
    y, x = np.mgrid[0:h, 0:w]
    return y.astype(np.float32), x.astype(np.float32)


# ===========================================================================
# DARK & GOTHIC - 10 MISSING ENTRIES
# Each one is genuinely distinct. No two share the same visual approach.
# ===========================================================================

# --- CURSED --- acid-etched arcane surface, verdigris veins, corroded chrome
def spec_cursed(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n1 = _msn(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 2100)
    n2 = _msn(shape, [2, 4, 8], [0.4, 0.35, 0.25], seed + 2101)
    veins = np.where(np.abs(n1) < 0.07, 1.0, 0.0).astype(np.float32)
    veins_s = gaussian_filter(veins, sigma=max(1, h * 0.003))
    M = np.clip(80 + veins_s * 120 + n2 * 20 * sm, 0, 255)
    R = np.clip(160 - veins_s * 140 + n2 * 15 * sm, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(veins_s * 12 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_cursed(paint, shape, mask, seed, pm, bb):
    """Cursed - acid-veined chrome: corrosion channels glow toxic green on dark base."""
    h, w = shape
    n = _msn(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 2102)
    veins = np.where(np.abs(n) < 0.07, 1.0, 0.0).astype(np.float32)
    vein_glow = gaussian_filter(veins, sigma=max(2, h * 0.010))
    paint = np.clip(paint - 0.32 * pm * mask[:, :, None], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.45 * pm * mask[:, :, None]) + gray * 0.45 * pm * mask[:, :, None]
    paint[:, :, 0] = np.clip(paint[:, :, 0] + vein_glow * 0.12 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + vein_glow * 0.55 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + vein_glow * 0.08 * pm * mask, 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + veins * 0.20 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + veins * 0.70 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.3 * mask[:, :, None], 0, 1)


# --- ECLIPSE --- solar corona edge-glow on vantablack disc
def spec_eclipse(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    corona = np.clip(1.0 - r * 2.5, 0, 1) ** 1.5
    M = np.clip(corona * 200 + 5, 0, 255)
    R = np.clip(200 - corona * 195, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(corona * 14 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_eclipse(paint, shape, mask, seed, pm, bb):
    """Eclipse - near-vantablack disc with blazing gold-white corona ring."""
    h, w = shape
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    disc = np.clip(1.0 - r * 4.5, 0, 1) ** 2
    ring = np.clip(np.abs(r - 0.22) < 0.06, 0, 1).astype(np.float32)
    ring_s = gaussian_filter(ring, sigma=max(2, h * 0.012))
    corona = np.clip(1.0 - (r - 0.22) / 0.3, 0, 1) * (r > 0.18).astype(np.float32)
    paint = np.clip(paint - disc * 0.55 * pm * mask[:, :, None], 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (ring_s * 0.80 + corona * 0.30) * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (ring_s * 0.60 + corona * 0.20) * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + ring_s * 0.15 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:, :, None], 0, 1)


# --- NIGHTMARE --- distorted mirror shards - fragmented reflections dissolving
def spec_nightmare(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 2200)
    shards = np.floor(n * 4) / 4
    M = np.clip(200 + shards * 40 + n * 15 * sm, 0, 255)
    R = np.clip(30 + np.abs(shards) * 80 + n * 10 * sm, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(10 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_nightmare(paint, shape, mask, seed, pm, bb):
    """Nightmare - fractured chrome mirror, each shard a different dark hue."""
    h, w = shape
    n = _msn(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 2201)
    shards = np.floor(n * 5) / 5
    # Each shard zone gets a different dark tint
    r_tint = np.sin(shards * np.pi * 3) * 0.15
    g_tint = np.sin(shards * np.pi * 5 + 1.0) * 0.12
    b_tint = np.sin(shards * np.pi * 7 + 2.0) * 0.18
    shard_edge = np.abs(n - np.floor(n * 5 + 0.5) / 5)
    edge_dark = np.clip(1.0 - shard_edge * 20, 0, 1).astype(np.float32)
    edge_s = gaussian_filter(edge_dark, sigma=max(1, h * 0.003))
    paint = np.clip(paint - 0.28 * pm * mask[:, :, None], 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + r_tint * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + g_tint * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + b_tint * pm * mask, 0, 1)
    paint = np.clip(paint - edge_s[:, :, None] * 0.40 * pm * mask[:, :, None], 0, 1)
    return np.clip(paint + bb * 0.3 * mask[:, :, None], 0, 1)


# --- POSSESSED --- pulsing red-black void: surface vibrates between chrome and nothing
def spec_possessed(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2300)
    puls = np.sin(n * np.pi * 6) * 0.5 + 0.5
    M = np.clip(5 + puls * 180 + n * 10 * sm, 0, 255)
    R = np.clip(220 - puls * 210 + n * 8 * sm, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(puls * 8 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_possessed(paint, shape, mask, seed, pm, bb):
    """Possessed - surface alive with pulsing red-black oscillations, eye-sockets glowing."""
    h, w = shape
    n = _msn(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 2301)
    puls = np.sin(n * np.pi * 6) * 0.5 + 0.5
    pulse_hot = np.clip(puls - 0.6, 0, 1) * 2.5
    paint = np.clip(paint - 0.40 * pm * mask[:, :, None], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.60 * pm * mask[:, :, None]) + gray * 0.60 * pm * mask[:, :, None]
    paint[:, :, 0] = np.clip(paint[:, :, 0] + pulse_hot * 0.65 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] - puls * 0.10 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - puls * 0.10 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:, :, None], 0, 1)


# --- REAPER --- scythe-slash streaks: diagonal rips revealing void beneath gloss
def spec_reaper(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    diag = (y / h + x / w)
    slash = np.abs(np.sin(diag * np.pi * 8)) ** 3
    M = np.clip(30 + slash * 200 + _msn(shape, [4, 8], [0.5, 0.5], seed + 2400) * 10 * sm, 0, 255)
    R = np.clip(200 - slash * 195, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(slash * 14 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_reaper(paint, shape, mask, seed, pm, bb):
    """Reaper - diagonal scythe slashes: chrome cuts through absolute darkness."""
    h, w = shape
    y, x = _mgrid(shape)
    diag = (y / h + x / w)
    slash = np.abs(np.sin(diag * np.pi * 8)) ** 3
    slash_edge = np.clip(slash - 0.7, 0, 1) * 3.3
    slash_glow = gaussian_filter(slash_edge, sigma=max(1, h * 0.004))
    paint = np.clip(paint - 0.45 * pm * mask[:, :, None], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.55 * pm * mask[:, :, None]) + gray * 0.55 * pm * mask[:, :, None]
    paint = np.clip(paint + slash_glow[:, :, None] * 0.55 * pm * mask[:, :, None], 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:, :, None], 0, 1)


# --- VOODOO --- ritual doll pins: scattered luminous needle-points in fetid swamp dark
def spec_voodoo(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 2500)
    pin_layer = np.zeros((h, w), dtype=np.float32)
    for _ in range(max(40, int((h * w) / 5000))):
        py, px = rng.randint(0, h), rng.randint(0, w)
        r = max(2, int(min(h, w) * 0.005))
        yy = np.clip(np.arange(py - r, py + r + 1), 0, h - 1)
        xx = np.clip(np.arange(px - r, px + r + 1), 0, w - 1)
        pin_layer[np.ix_(yy, xx)] = 1.0
    pin_s = gaussian_filter(pin_layer, sigma=max(1, h * 0.004))
    M = np.clip(20 + pin_s * 180, 0, 255)
    R = np.clip(200 - pin_s * 195, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(pin_s * 12 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_voodoo(paint, shape, mask, seed, pm, bb):
    """Voodoo - swamp-dark base with hot pin-prick ritual needle glows."""
    h, w = shape
    rng = np.random.RandomState(seed + 2501)
    pin_layer = np.zeros((h, w), dtype=np.float32)
    for _ in range(max(40, int((h * w) / 5000))):
        py, px = rng.randint(0, h), rng.randint(0, w)
        r = max(2, int(min(h, w) * 0.005))
        yy = np.clip(np.arange(py - r, py + r + 1), 0, h - 1)
        xx = np.clip(np.arange(px - r, px + r + 1), 0, w - 1)
        pin_layer[np.ix_(yy, xx)] = 1.0
    pin_glow = gaussian_filter(pin_layer, sigma=max(3, h * 0.015))
    n = _msn(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 2502)
    paint = np.clip(paint - 0.38 * pm * mask[:, :, None], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.50 * pm * mask[:, :, None]) + gray * 0.50 * pm * mask[:, :, None]
    # Green swamp tint on base
    paint[:, :, 1] = np.clip(paint[:, :, 1] + n * 0.06 * pm * mask, 0, 1)
    # Pin-glow: hot hellish purple-red
    paint[:, :, 0] = np.clip(paint[:, :, 0] + pin_glow * 0.60 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + pin_glow * 0.45 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:, :, None], 0, 1)


# --- WRAITH --- translucent whisp: iridescent anti-matter outline with void interior
def spec_wraith(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    edge = np.clip(np.abs(r - 0.38) < 0.08, 0, 1).astype(np.float32)
    edge_s = gaussian_filter(edge, sigma=max(2, h * 0.015))
    n = _msn(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 2600)
    warp = edge_s + n * 0.15
    M = np.clip(warp * 120 + 10, 0, 255)
    R = np.clip(210 - warp * 200, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(warp * 12 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_wraith(paint, shape, mask, seed, pm, bb):
    """Wraith - near-invisible void core with shimmering ethereal cyan-purple edge aura."""
    h, w = shape
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    edge = np.clip(1.0 - np.abs(r - 0.35) * 8, 0, 1).astype(np.float32)
    aura = gaussian_filter(edge, sigma=max(4, h * 0.025))
    n = _msn(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 2601)
    interior = np.clip(1.0 - r * 3.5, 0, 1)
    paint = np.clip(paint - 0.50 * pm * interior[:, :, None] * mask[:, :, None], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.60 * pm * interior[:, :, None] * mask[:, :, None]) + gray * 0.60 * pm * interior[:, :, None] * mask[:, :, None]
    paint[:, :, 0] = np.clip(paint[:, :, 0] + aura * 0.30 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + aura * 0.55 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + aura * 0.70 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:, :, None], 0, 1)


# ===========================================================================
# EFFECT & VISUAL - MISSING ENTRIES + CUSTOM SPEC REPLACEMENTS
# ===========================================================================

# --- DEPTH MAP --- real luminance-to-height gradient with center-bright vignette
def spec_depth_map(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    depth = np.clip(1.0 - np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w) * 1.5, 0, 1)
    n = _msn(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 3000)
    field = depth + n * 0.15
    M = np.clip(20 + field * 140 + n * 10 * sm, 0, 255)
    R = np.clip(120 - field * 100 + n * 8 * sm, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 60 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(field * 14 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_depth_map(paint, shape, mask, seed, pm, bb):
    """Depth Map - grayscale depth encoded as near=white, far=black, warm-tinted."""
    h, w = shape
    gray = paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114
    # Near objects warm, far objects cool
    blend = 0.55 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + (gray * 1.1) * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + gray * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + (gray * 0.85) * blend * mask, 0, 1)
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    depth = np.clip(1.0 - np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w) * 1.6, 0, 1)
    paint = np.clip(paint * (0.3 + depth[:, :, None] * 0.7), 0, 1)
    return np.clip(paint + bb * 0.3 * mask[:, :, None], 0, 1)


# --- DOUBLE EXPOSURE --- two images blended: ghost overlay of darkened twin
def spec_double_exposure(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n1 = _msn(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 3100)
    n2 = _msn(shape, [16, 32, 64], [0.3, 0.4, 0.3], seed + 3101)
    blend = n1 * 0.5 + n2 * 0.5
    M = np.clip(80 + blend * 60 + n1 * 15 * sm, 0, 255)
    R = np.clip(50 + blend * 40 + n2 * 10 * sm, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 50 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(12 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_double_exposure(paint, shape, mask, seed, pm, bb):
    """Double Exposure - ghost of shifted image overlaid on desaturated base."""
    h, w = shape
    shift_y = int(h * 0.07)
    shift_x = int(w * 0.09)
    ghost = np.roll(np.roll(paint, shift_y, axis=0), shift_x, axis=1)
    gray = paint.mean(axis=2, keepdims=True)
    desat = paint * 0.3 + gray * 0.7
    blend = 0.45 * pm
    merged = np.clip(desat * 0.6 + ghost * 0.4, 0, 1)
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] * (1 - blend * mask) + merged[:, :, c] * blend * mask, 0, 1)
    return np.clip(paint + bb * 0.3 * mask[:, :, None], 0, 1)


# --- INFRARED --- false-color infrared: foliage=white, sky=black, skin=magenta
def spec_infrared(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 3200)
    M = np.clip(60 + n * 30 * sm, 0, 255)
    R = np.clip(80 + n * 20 * sm, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 60 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(10 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_infrared(paint, shape, mask, seed, pm, bb):
    """Infrared - warm sources glow white-pink, cool areas shift to black-purple false-color."""
    h, w = shape
    # Luminance = "heat source"
    lum = paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114
    # False color: high lum → white-pink, low lum → dark purple
    r_ir = np.clip(lum * 1.2 + (1 - lum) * 0.35, 0, 1)
    g_ir = np.clip(lum * 0.4 + (1 - lum) * 0.10, 0, 1)
    b_ir = np.clip(lum * 0.5 + (1 - lum) * 0.60, 0, 1)
    blend = 0.70 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_ir * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_ir * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_ir * blend * mask, 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:, :, None], 0, 1)


# --- POLARIZED --- Maltese-cross extinction pattern from polarizing filters
def spec_polarized(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    theta = np.arctan2(y - cy, x - cx)
    polar = np.abs(np.sin(2 * theta)) ** 2
    M = np.clip(60 + polar * 130 + _msn(shape, [8, 16], [0.5, 0.5], seed + 3300) * 10 * sm, 0, 255)
    R = np.clip(80 - polar * 65, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 60 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(polar * 14 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_polarized(paint, shape, mask, seed, pm, bb):
    """Polarized - birefringent stress pattern: Maltese cross extinction bands + spectral fringes."""
    h, w = shape
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    theta = np.arctan2(y - cy, x - cx)
    r = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    # Maltese-cross extinction (dark bands along 0°/90°)
    extinction = np.abs(np.sin(2 * theta)) ** 2
    # Spectral interference fringe (isochromatic rings)
    fringe = np.sin(r * np.pi * 30) * 0.5 + 0.5
    r_c = fringe * extinction
    g_c = np.sin(r * np.pi * 30 + 1.05) * 0.5 + 0.5
    b_c = np.sin(r * np.pi * 30 + 2.09) * 0.5 + 0.5
    blend = 0.50 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + r_c * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + g_c * extinction * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + b_c * extinction * blend * mask, 0, 1)
    return np.clip(paint + bb * 0.3 * mask[:, :, None], 0, 1)


# --- UV BLACKLIGHT --- fluorescent bloom: UV reveals hidden glowing patterns
def spec_uv_blacklight(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 3400)
    hot = np.where(n > 0.5, (n - 0.5) * 2, 0).astype(np.float32)
    M = np.clip(100 + hot * 100 + n * 15 * sm, 0, 255)
    R = np.clip(20 + (1 - hot) * 20, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 40 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(16 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_uv_blacklight(paint, shape, mask, seed, pm, bb):
    """UV Blacklight - near-black base with explosive vivid neon UV florals blooming."""
    h, w = shape
    n = _msn(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 3401)
    uv_hot = np.where(n > 0.45, (n - 0.45) / 0.55, 0).astype(np.float32)
    uv_glow = gaussian_filter(uv_hot, sigma=max(2, h * 0.012))
    # Massive base darkening - UV room = black
    paint = np.clip(paint - 0.55 * pm * mask[:, :, None], 0, 1)
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.60 * pm * mask[:, :, None]) + gray * 0.60 * pm * mask[:, :, None]
    # Neon UV bloom per hue zone
    rng = np.random.RandomState(seed + 3402)
    hue_r = rng.random() > 0.5
    hue_g = rng.random() > 0.3
    hue_b = rng.random() > 0.4
    paint[:, :, 0] = np.clip(paint[:, :, 0] + uv_glow * (0.70 if hue_r else 0.20) * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + uv_glow * (0.80 if hue_g else 0.10) * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + uv_glow * (0.90 if hue_b else 0.30) * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.1 * mask[:, :, None], 0, 1)


# --- X-RAY --- interior skeleton: bones bright, tissue semi-transparent
def spec_x_ray(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 3500)
    dense = np.clip(n * 0.5 + 0.5, 0, 1) ** 2
    M = np.clip(20 + dense * 180, 0, 255)
    R = np.clip(160 - dense * 155, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(dense * 10 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_x_ray(paint, shape, mask, seed, pm, bb):
    """X-Ray - eerie blue-white radiograph: dense structures glow, tissue vanishes."""
    h, w = shape
    n = _msn(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 3501)
    dense = np.clip(n * 0.5 + 0.5, 0, 1) ** 2
    # Radiograph = near-black background, bright silhouettes
    gray = paint[:, :, 0] * 0.299 + paint[:, :, 1] * 0.587 + paint[:, :, 2] * 0.114
    xray_lum = np.clip(dense * 0.7 + gray * 0.3, 0, 1)
    blend = 0.75 * pm
    # Blue-gray radiograph tint
    paint[:, :, 0] = np.clip(paint[:, :, 0] * (1 - blend * mask) + xray_lum * 0.80 * blend * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] * (1 - blend * mask) + xray_lum * 0.90 * blend * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] * (1 - blend * mask) + xray_lum * 1.05 * blend * mask, 0, 1)
    # Darken very low-density areas
    paint = np.clip(paint - (1 - dense[:, :, None]) * 0.30 * pm * mask[:, :, None], 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:, :, None], 0, 1)


# ===========================================================================
# REPLACE WEAK EFFECT & VISUAL SPECS WITH CUSTOM ONES
# (The paint fns are fine; the specs were all the same flat boilerplate)
# ===========================================================================

def spec_chromatic_aberration_v2(shape, mask, seed, sm):
    """CA spec: prismatic edge-split - R/B channels slightly offset in metallic."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    fringe = np.clip(r * 2.5, 0, 1)
    M = np.clip(60 + fringe * 60 + _msn(shape, [8, 16], [0.5, 0.5], seed + 4000) * 10 * sm, 0, 255)
    R = np.clip(40 - fringe * 20, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 40 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(14 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_halftone_v2(shape, mask, seed, sm):
    """Halftone spec: dot-grid pattern stamped into roughness - raised dots vs flat field."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    dot_size = max(6, min(h, w) // 60)
    dy = (y % dot_size) - dot_size / 2.0
    dx = (x % dot_size) - dot_size / 2.0
    dist = np.sqrt(dy**2 + dx**2) / (dot_size * 0.5)
    dot = np.clip(1.0 - dist * 1.5, 0, 1)
    M = np.clip(30 + dot * 80, 0, 255)
    R = np.clip(120 - dot * 100, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 80 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(dot * 10 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_negative_v2(shape, mask, seed, sm):
    """Negative spec: inverted luminance - bright = flat matte, dark = high gloss."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 4200)
    inv = 1.0 - (n * 0.5 + 0.5)
    M = np.clip(20 + inv * 180, 0, 255)
    R = np.clip(180 - inv * 170, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 80 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(inv * 12 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_solarization_v2(shape, mask, seed, sm):
    """Solarization spec: midtone reversal - near-mirror at mid-luminance threshold."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 4300)
    lum = n * 0.5 + 0.5
    solar = np.where(lum < 0.5, lum * 2, (1 - lum) * 2).astype(np.float32)
    M = np.clip(80 + solar * 140, 0, 255)
    R = np.clip(20 + (1 - solar) * 20, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 20 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(solar * 14 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def spec_embossed_v2(shape, mask, seed, sm):
    """Embossed spec: directional relief - illuminated ridges high-metallic, shadow=rough."""
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 4400)
    shifted = np.roll(np.roll(n, 2, axis=0), 2, axis=1)
    relief = np.clip((n - shifted) * 3.0 + 0.5, 0, 1)
    M = np.clip(60 + relief * 140, 0, 255)
    R = np.clip(160 - relief * 150, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 80 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(relief * 12 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec


# ===========================================================================
# NEON & GLOW - 6 MISSING ENTRIES
# ===========================================================================

def spec_cyber_punk(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5000)
    grid_y = np.abs(np.sin(np.linspace(0, np.pi * 20, h))).reshape(h, 1)
    grid_x = np.abs(np.sin(np.linspace(0, np.pi * 30, w))).reshape(1, w)
    grid = np.clip(grid_y * grid_x + n * 0.2, 0, 1).astype(np.float32)
    M = np.clip(180 + grid * 60 + n * 10 * sm, 0, 255)
    R = np.clip(20 - grid * 15, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 10 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(16 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_cyber_punk(paint, shape, mask, seed, pm, bb):
    """Cyberpunk - dark chrome city grid with neon magenta/cyan line glow."""
    h, w = shape
    n = _msn(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5001)
    grid_y = np.abs(np.sin(np.linspace(0, np.pi * 20, h))).reshape(h, 1)
    grid_x = np.abs(np.sin(np.linspace(0, np.pi * 30, w))).reshape(1, w)
    grid = np.clip(grid_y * grid_x + n * 0.2, 0, 1).astype(np.float32)
    lines = np.clip(grid - 0.7, 0, 1) * 3.3
    lines_g = gaussian_filter(lines, sigma=max(1, h * 0.005))
    paint = np.clip(paint - 0.35 * pm * mask[:, :, None], 0, 1)
    # Alternating magenta and cyan lines
    cy_zone = np.sin(np.linspace(0, np.pi * 6, w)).reshape(1, w)
    cy_zone = np.clip(cy_zone * 0.5 + 0.5, 0, 1).astype(np.float32)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + lines_g * (1 - cy_zone) * 0.70 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + lines_g * cy_zone * 0.55 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + lines_g * 0.60 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:, :, None], 0, 1)


def spec_firefly(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 5100)
    fl = np.zeros((h, w), dtype=np.float32)
    for _ in range(max(60, (h * w) // 3000)):
        py, px = rng.randint(0, h), rng.randint(0, w)
        r = max(3, int(min(h, w) * 0.008))
        yy = np.clip(np.arange(py - r, py + r + 1), 0, h - 1)
        xx = np.clip(np.arange(px - r, px + r + 1), 0, w - 1)
        fl[np.ix_(yy, xx)] = 1.0
    fl_g = gaussian_filter(fl, sigma=max(2, h * 0.012))
    M = np.clip(80 + fl_g * 160, 0, 255)
    R = np.clip(120 - fl_g * 110, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 80 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(fl_g * 14 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_firefly(paint, shape, mask, seed, pm, bb):
    """Firefly - warm dark night with scattered warm-white yellow-green glow orbs."""
    h, w = shape
    rng = np.random.RandomState(seed + 5101)
    fl = np.zeros((h, w), dtype=np.float32)
    for _ in range(max(60, (h * w) // 3000)):
        py, px = rng.randint(0, h), rng.randint(0, w)
        r = max(3, int(min(h, w) * 0.008))
        yy = np.clip(np.arange(py - r, py + r + 1), 0, h - 1)
        xx = np.clip(np.arange(px - r, px + r + 1), 0, w - 1)
        fl[np.ix_(yy, xx)] = 1.0
    fl_glow = gaussian_filter(fl, sigma=max(4, h * 0.022))
    paint = np.clip(paint - 0.40 * pm * mask[:, :, None], 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + fl_glow * 0.60 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + fl_glow * 0.75 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + fl_glow * 0.20 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.15 * mask[:, :, None], 0, 1)


def spec_laser_grid(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    grid_h = max(8, h // 30)
    grid_w = max(8, w // 30)
    line_y = (y % grid_h < 2).astype(np.float32)
    line_x = (x % grid_w < 2).astype(np.float32)
    grid = np.clip(line_y + line_x, 0, 1)
    grid_s = gaussian_filter(grid, sigma=max(1, h * 0.004))
    M = np.clip(180 + grid_s * 70, 0, 255)
    R = np.clip(15 - grid_s * 12, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 10 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(14 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_laser_grid(paint, shape, mask, seed, pm, bb):
    """Laser Grid - deep black surface with precise brilliant red/green laser line grid."""
    h, w = shape
    y, x = _mgrid(shape)
    grid_h = max(8, h // 30)
    grid_w = max(8, w // 30)
    line_y = (y % grid_h < 2).astype(np.float32)
    line_x = (x % grid_w < 2).astype(np.float32)
    grid = np.clip(line_y + line_x, 0, 1)
    grid_glow = gaussian_filter(grid, sigma=max(1, h * 0.006))
    paint = np.clip(paint - 0.50 * pm * mask[:, :, None], 0, 1)
    # Red lines horizontal, green vertical
    paint[:, :, 0] = np.clip(paint[:, :, 0] + line_y * 0.80 * pm * mask + grid_glow * 0.25 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + line_x * 0.80 * pm * mask + grid_glow * 0.15 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.1 * mask[:, :, None], 0, 1)


def spec_led_matrix(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    cell = max(6, min(h, w) // 50)
    cy_local = (y % cell) - cell / 2.0
    cx_local = (x % cell) - cell / 2.0
    dot = np.clip(1.0 - np.sqrt(cy_local**2 + cx_local**2) / (cell * 0.35), 0, 1)
    M = np.clip(200 * dot + 20, 0, 255)
    R = np.clip(10 + (1 - dot) * 20, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 10 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(dot * 16 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_led_matrix(paint, shape, mask, seed, pm, bb):
    """LED Matrix - pixel-perfect RGB dot grid, each dot a vivid primary color."""
    h, w = shape
    y, x = _mgrid(shape)
    cell = max(6, min(h, w) // 50)
    cy_loc = (y % cell) - cell / 2.0
    cx_loc = (x % cell) - cell / 2.0
    dot = np.clip(1.0 - np.sqrt(cy_loc**2 + cx_loc**2) / (cell * 0.35), 0, 1)
    # Each cell column cycles R/G/B
    col_idx = (x // cell).astype(int) % 3
    r_dot = dot * (col_idx == 0).astype(np.float32)
    g_dot = dot * (col_idx == 1).astype(np.float32)
    b_dot = dot * (col_idx == 2).astype(np.float32)
    paint = np.clip(paint - 0.60 * pm * mask[:, :, None], 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + r_dot * 0.90 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + g_dot * 0.90 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + b_dot * 0.90 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.1 * mask[:, :, None], 0, 1)


def spec_neon_vegas(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 5400)
    y = np.linspace(0, 1, h).reshape(h, 1)
    tubes = np.abs(np.sin(y * np.pi * 12 + n * 2)) ** 4
    M = np.clip(100 + tubes * 140 + n * 15 * sm, 0, 255)
    R = np.clip(15 + (1 - tubes) * 15, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 10 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(tubes * 16 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_neon_vegas(paint, shape, mask, seed, pm, bb):
    """Neon Vegas - horizontal sign tubes cycling hot pink/orange/yellow in black."""
    h, w = shape
    n = _msn(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5401)
    y = np.linspace(0, 1, h).reshape(h, 1)
    tubes = np.abs(np.sin(y * np.pi * 12 + n * 2)) ** 4
    tube_g = gaussian_filter(tubes, sigma=max(1, h * 0.008))
    paint = np.clip(paint - 0.55 * pm * mask[:, :, None], 0, 1)
    # Tube color alternates per frequency band
    freq_row = (np.arange(h) // max(2, h // 12)) % 3
    r_band = (freq_row == 0).astype(np.float32).reshape(h, 1)
    g_band = (freq_row == 1).astype(np.float32).reshape(h, 1)
    b_band = (freq_row == 2).astype(np.float32).reshape(h, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + tube_g * (0.90 * r_band + 0.70 * g_band + 0.40 * b_band) * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + tube_g * (0.10 * r_band + 0.20 * g_band + 0.10 * b_band) * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + tube_g * (0.30 * r_band + 0.10 * g_band + 0.90 * b_band) * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.1 * mask[:, :, None], 0, 1)


def spec_plasma_globe(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    n = _msn(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5500)
    tendrils = np.clip(np.abs(n) - 0.3, 0, 1) * 1.4
    globe = np.clip(1.0 - r * 2.5, 0, 1) * tendrils
    M = np.clip(180 + globe * 70 + n * 10 * sm, 0, 255)
    R = np.clip(10 + (1 - globe) * 15, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 8 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(globe * 16 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_plasma_globe(paint, shape, mask, seed, pm, bb):
    """Plasma Globe - crackling purple-white lightning tendrils from glowing center point."""
    h, w = shape
    y, x = _mgrid(shape)
    cy, cx = h * 0.5, w * 0.5
    r = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    n = _msn(shape, [4, 8, 16], [0.3, 0.4, 0.3], seed + 5501)
    tendrils = np.clip(np.abs(n) - 0.35, 0, 1) * 1.5
    globe_fade = np.clip(1.0 - r * 2.2, 0, 1)
    lightning = tendrils * globe_fade
    lg = gaussian_filter(lightning, sigma=max(1, h * 0.006))
    center = np.clip(1.0 - r * 8, 0, 1) ** 2
    paint = np.clip(paint - 0.50 * pm * mask[:, :, None], 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (lg * 0.50 + center * 0.80) * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (lg * 0.25 + center * 0.60) * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (lg * 0.80 + center * 1.0) * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.1 * mask[:, :, None], 0, 1)


# ===========================================================================
# WEATHER & ELEMENT - 6 MISSING ENTRIES
# ===========================================================================

def spec_desert_mirage(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y = np.linspace(0, 1, h).reshape(h, 1)
    n = _msn(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 6000)
    heat = np.sin(y * np.pi * 25 + n * 2) * 0.5 + 0.5
    M = np.clip(80 + heat * 100 + n * 15 * sm, 0, 255)
    R = np.clip(50 + (1 - heat) * 60 + n * 10 * sm, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 60 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(heat * 12 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_desert_mirage(paint, shape, mask, seed, pm, bb):
    """Desert Mirage - shimmering heat distortion horizon bands, pale golden refraction."""
    h, w = shape
    n = _msn(shape, [8, 16, 32], [0.3, 0.4, 0.3], seed + 6001)
    y = np.linspace(0, 1, h).reshape(h, 1)
    shimmer = np.sin(y * np.pi * 25 + n * 2) * 0.5 + 0.5
    paint[:, :, 0] = np.clip(paint[:, :, 0] + shimmer * 0.10 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + shimmer * 0.06 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - shimmer * 0.04 * pm * mask, 0, 1)
    # Sky reflection in lower half
    sky = np.clip(1.0 - y, 0, 1).astype(np.float32)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + sky * 0.06 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + sky * 0.12 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.4 * mask[:, :, None], 0, 1)


def spec_frozen_lake(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 6100)
    crack = np.where(np.abs(n) < 0.08, 1.0, 0.0).astype(np.float32)
    crack_s = gaussian_filter(crack, sigma=max(1, h * 0.003))
    M = np.clip(40 + crack_s * 60, 0, 255)
    R = np.clip(12 + crack_s * 8, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 8 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(16 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_frozen_lake(paint, shape, mask, seed, pm, bb):
    """Frozen Lake - near-perfect ice mirror with dark trapped bubble cracks below."""
    h, w = shape
    n = _msn(shape, [8, 16, 32, 64], [0.15, 0.25, 0.35, 0.25], seed + 6101)
    crack = np.where(np.abs(n) < 0.08, 1.0, 0.0).astype(np.float32)
    crack_dark = gaussian_filter(crack, sigma=max(1, h * 0.002))
    # Near-perfect glassy ice surface - very slight blue tint
    paint[:, :, 1] = np.clip(paint[:, :, 1] + 0.04 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + 0.09 * pm * mask, 0, 1)
    # Cracks show dark trapped air
    paint = np.clip(paint - crack_dark[:, :, None] * 0.35 * pm * mask[:, :, None], 0, 1)
    return np.clip(paint + bb * 0.6 * mask[:, :, None], 0, 1)


def spec_meteor_shower(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    rng = np.random.RandomState(seed + 6200)
    meteor = np.zeros((h, w), dtype=np.float32)
    for _ in range(max(20, (h * w) // 8000)):
        sy, sx = rng.randint(0, h), rng.randint(0, w)
        length = rng.randint(max(20, w // 30), max(40, w // 10))
        angle = rng.uniform(-0.6, -0.3)
        for i in range(length):
            py = int(sy + i * np.sin(angle + np.pi / 2))
            px = int(sx + i * np.cos(angle + np.pi / 2))
            if 0 <= py < h and 0 <= px < w:
                meteor[py, px] = max(meteor[py, px], 1.0 - i / length)
    meteor_s = gaussian_filter(meteor, sigma=max(1, h * 0.004))
    M = np.clip(20 + meteor_s * 220, 0, 255)
    R = np.clip(180 - meteor_s * 175, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 100 * (1 - mask), 15, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(meteor_s * 12 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_meteor_shower(paint, shape, mask, seed, pm, bb):
    """Meteor Shower - deep space black with blazing streak trails of white-hot meteors."""
    h, w = shape
    rng = np.random.RandomState(seed + 6201)
    meteor = np.zeros((h, w), dtype=np.float32)
    for _ in range(max(20, (h * w) // 8000)):
        sy, sx = rng.randint(0, h), rng.randint(0, w)
        length = rng.randint(max(20, w // 30), max(40, w // 10))
        angle = rng.uniform(-0.6, -0.3)
        for i in range(length):
            py = int(sy + i * np.sin(angle + np.pi / 2))
            px = int(sx + i * np.cos(angle + np.pi / 2))
            if 0 <= py < h and 0 <= px < w:
                val = 1.0 - i / length
                meteor[py, px] = max(meteor[py, px], val)
    meteor_glow = gaussian_filter(meteor, sigma=max(2, h * 0.010))
    paint = np.clip(paint - 0.55 * pm * mask[:, :, None], 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (meteor_glow * 0.80 + meteor * 0.60) * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (meteor_glow * 0.70 + meteor * 0.50) * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (meteor_glow * 0.50 + meteor * 0.30) * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.1 * mask[:, :, None], 0, 1)


def spec_ocean_floor(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 6300)
    caustic = np.sin((n + 1) * np.pi * 8) * 0.5 + 0.5
    M = np.clip(30 + caustic * 60 + n * 10 * sm, 0, 255)
    R = np.clip(80 + caustic * 40 + n * 8 * sm, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 60 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(caustic * 10 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_ocean_floor(paint, shape, mask, seed, pm, bb):
    """Ocean Floor - deep blue pressure dark with dancing caustic light patterns above."""
    h, w = shape
    n = _msn(shape, [8, 16, 32, 64], [0.2, 0.3, 0.3, 0.2], seed + 6301)
    caustic = np.sin((n + 1) * np.pi * 8) * 0.5 + 0.5
    caustic_hot = np.clip(caustic - 0.65, 0, 1) * 2.9
    paint = np.clip(paint - 0.35 * pm * mask[:, :, None], 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + 0.08 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + 0.18 * pm * mask, 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + caustic_hot * 0.30 * pm * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + caustic_hot * 0.35 * pm * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + caustic_hot * 0.40 * pm * mask, 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:, :, None], 0, 1)


def spec_tornado_alley(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    y, x = _mgrid(shape)
    cy, cx = h * 0.55, w * 0.5
    theta = np.arctan2(y - cy, x - cx)
    r = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    spiral = np.sin(theta * 3 + r * 30) * 0.5 + 0.5
    cone = np.clip(1.0 - r * 2.0, 0, 1)
    vortex = spiral * cone
    M = np.clip(30 + vortex * 80 + _msn(shape, [4, 8], [0.5, 0.5], seed + 6400) * 10 * sm, 0, 255)
    R = np.clip(100 + (1 - vortex) * 80, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 80 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(vortex * 8 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_tornado_alley(paint, shape, mask, seed, pm, bb):
    """Tornado Alley - dark rotating funnel: debris-filled gray spiral with sickly green sky."""
    h, w = shape
    y, x = _mgrid(shape)
    cy, cx = h * 0.55, w * 0.5
    theta = np.arctan2(y - cy, x - cx)
    r = np.sqrt((y - cy)**2 + (x - cx)**2) / max(h, w)
    spiral = np.sin(theta * 3 + r * 30) * 0.5 + 0.5
    cone = np.clip(1.0 - r * 2.2, 0, 1)
    vortex = spiral * cone
    gray = paint.mean(axis=2, keepdims=True)
    paint = paint * (1 - 0.40 * pm * mask[:, :, None]) + gray * 0.40 * pm * mask[:, :, None]
    paint = np.clip(paint - 0.20 * pm * mask[:, :, None], 0, 1)
    sky = np.clip(1.0 - r * 1.5, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + sky * 0.12 * pm * mask, 0, 1)
    paint = np.clip(paint - vortex[:, :, None] * 0.18 * pm * mask[:, :, None], 0, 1)
    return np.clip(paint + bb * 0.3 * mask[:, :, None], 0, 1)


def spec_volcanic_glass(shape, mask, seed, sm):
    h, w = shape
    spec = np.zeros((h, w, 4), dtype=np.uint8)
    n = _msn(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 6500)
    obsidian = np.clip(n * 0.5 + 0.5, 0, 1) ** 3
    M = np.clip(180 + obsidian * 70, 0, 255)
    R = np.clip(8 + obsidian * 6, 15, 255)
    spec[:, :, 0] = np.clip(M * mask, 0, 255).astype(np.uint8)
    spec[:, :, 1] = np.clip(R * mask + 5 * (1 - mask), 0, 255).astype(np.uint8)
    spec[:, :, 2] = np.clip(obsidian * 16 * mask, 0, 16).astype(np.uint8)
    spec[:, :, 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)
    return spec

def paint_volcanic_glass(paint, shape, mask, seed, pm, bb):
    """Volcanic Glass - obsidian mirror: near-black with deep reflective conchoidal fracture."""
    h, w = shape
    n = _msn(shape, [4, 8, 16, 32], [0.2, 0.3, 0.3, 0.2], seed + 6501)
    obsidian = np.clip(n * 0.5 + 0.5, 0, 1) ** 3
    # Near absolute black - obsidian absorbs everything
    paint = np.clip(paint - 0.55 * pm * mask[:, :, None], 0, 1)
    # Mirror zones at high reflective peaks
    mirror = np.clip(obsidian - 0.85, 0, 1) * 6.7
    paint = np.clip(paint + mirror[:, :, None] * 0.40 * pm * mask[:, :, None], 0, 1)
    # Subtle rainbow sheen from iron oxide inclusions
    y, x = _mgrid(shape)
    theta = np.arctan2(y - h * 0.5, x - w * 0.5)
    sheen = np.sin(theta * 3 + obsidian * 5) * 0.03 * pm
    paint[:, :, 0] = np.clip(paint[:, :, 0] + sheen * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - sheen * 0.5 * mask, 0, 1)
    return np.clip(paint + bb * 0.2 * mask[:, :, None], 0, 1)


# ===========================================================================
# REGISTRATION - what to merge in
# ===========================================================================

OVERHAUL_MONOLITHICS = {
    # Dark & Gothic - 7 completely new
    "cursed":           (spec_cursed,           paint_cursed),
    "eclipse":          (spec_eclipse,           paint_eclipse),
    "nightmare":        (spec_nightmare,         paint_nightmare),
    "possessed":        (spec_possessed,         paint_possessed),
    "reaper":           (spec_reaper,            paint_reaper),
    "voodoo":           (spec_voodoo,            paint_voodoo),
    "wraith":           (spec_wraith,            paint_wraith),
    # Effect & Visual - 6 brand new
    "depth_map":        (spec_depth_map,         paint_depth_map),
    "double_exposure":  (spec_double_exposure,   paint_double_exposure),
    "infrared":         (spec_infrared,          paint_infrared),
    "polarized":        (spec_polarized,         paint_polarized),
    "uv_blacklight":    (spec_uv_blacklight,     paint_uv_blacklight),
    "x_ray":            (spec_x_ray,             paint_x_ray),
    # Neon & Glow - 6 brand new
    "cyber_punk":       (spec_cyber_punk,        paint_cyber_punk),
    "firefly":          (spec_firefly,           paint_firefly),
    "laser_grid":       (spec_laser_grid,        paint_laser_grid),
    "led_matrix":       (spec_led_matrix,        paint_led_matrix),
    "neon_vegas":       (spec_neon_vegas,        paint_neon_vegas),
    "plasma_globe":     (spec_plasma_globe,      paint_plasma_globe),
    # Weather & Element - 6 brand new
    "desert_mirage":    (spec_desert_mirage,     paint_desert_mirage),
    "frozen_lake":      (spec_frozen_lake,       paint_frozen_lake),
    "meteor_shower":    (spec_meteor_shower,     paint_meteor_shower),
    "ocean_floor":      (spec_ocean_floor,       paint_ocean_floor),
    "tornado_alley":    (spec_tornado_alley,     paint_tornado_alley),
    "volcanic_glass":   (spec_volcanic_glass,    paint_volcanic_glass),
}

# Upgraded specs - replace boilerplate spec fns while keeping existing paint fns
OVERHAUL_SPEC_REPLACEMENTS = {
    "chromatic_aberration": spec_chromatic_aberration_v2,
    "halftone":              spec_halftone_v2,
    "negative":              spec_negative_v2,
    "solarization":          spec_solarization_v2,
    "embossed":              spec_embossed_v2,
}


def integrate_specials_overhaul(engine_module):
    """
    Called from shokker_engine_v2.py after 24k expansion loads.
    Merges new monolithics and patches upgraded spec functions.
    """
    mono = getattr(engine_module, "MONOLITHIC_REGISTRY", None)
    if mono is None:
        print("[SPECIALS OVERHAUL] No MONOLITHIC_REGISTRY found - skipping")
        return

    # Add all new entries
    mono.update(OVERHAUL_MONOLITHICS)

    # Patch spec functions while preserving existing paint functions
    for finish_id, new_spec in OVERHAUL_SPEC_REPLACEMENTS.items():
        if finish_id in mono:
            _old_spec, old_paint = mono[finish_id]
            mono[finish_id] = (new_spec, old_paint)

    print(f"[SPECIALS OVERHAUL] Merged {len(OVERHAUL_MONOLITHICS)} new + "
          f"{len(OVERHAUL_SPEC_REPLACEMENTS)} spec upgrades")
