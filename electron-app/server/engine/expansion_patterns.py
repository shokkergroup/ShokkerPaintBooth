"""
engine/expansion_patterns.py - Dedicated texture_fn and paint_fn for each expansion pattern ID.

REWORK 2026-03-06: Each pattern now uses genuine per-variant geometry (not delegated to
unrelated legacy textures). Key categories: Flames, Decades, Music, Astro/Zodiac, Hero, Sport.
"""

from collections import OrderedDict
import numpy as np
import cv2
from scipy.spatial import cKDTree


def _engine():
    import shokker_engine_v2 as e
    return e


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _get_grid(shape):
    """Return normalised (y,x) grids in [-1,1]."""
    h, w = shape
    yy = np.linspace(-1, 1, h, dtype=np.float32)
    xx = np.linspace(-1, 1, w, dtype=np.float32)
    return np.meshgrid(yy, xx, indexing='ij')


def _radial_starburst(shape, n_rays, rotation=0.0):
    """Alternating wedge starburst. Returns float32 [0,1]."""
    Y, X = _get_grid(shape)
    angles = np.arctan2(Y, X) + rotation
    sector = (np.floor(angles / (np.pi * 2 / n_rays)) % 2).astype(np.float32)
    return sector


def _concentric_rings(shape, freq=8.0):
    """Concentric rings. Returns float32 [0,1]."""
    Y, X = _get_grid(shape)
    r = np.sqrt(X**2 + Y**2)
    return (np.sin(r * np.pi * freq) * 0.5 + 0.5).astype(np.float32)


def _stripe_horizontal(shape, n_stripes):
    """Horizontal stripes."""
    h, w = shape
    row = np.arange(h, dtype=np.float32)[:, None] / h * n_stripes
    return (np.floor(row) % 2).astype(np.float32) * np.ones((h, w), dtype=np.float32)


def _stripe_diagonal(shape, angle_deg=45.0, freq=10.0):
    Y, X = _get_grid(shape)
    a = np.deg2rad(angle_deg)
    proj = X * np.cos(a) + Y * np.sin(a)
    return (np.sin(proj * np.pi * freq) * 0.5 + 0.5).astype(np.float32)


def _checkerboard(shape, n=8):
    h, w = shape
    row = (np.arange(h)[:, None] * n // h)
    col = (np.arange(w)[None, :] * n // w)
    return ((row + col) % 2).astype(np.float32)


def _scatter_dots(shape, n_dots, radius_frac=0.04, seed=42):
    """Scattered circular dots."""
    h, w = shape
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float32)
    ys = (rng.random(n_dots) * h).astype(int)
    xs = (rng.random(n_dots) * w).astype(int)
    r = max(1, int(min(h, w) * radius_frac))
    yy, xx = np.ogrid[:h, :w]
    for cy, cx in zip(ys, xs):
        mask = (yy - cy)**2 + (xx - cx)**2 <= r**2
        out[mask] = 1.0
    return out


def _noise_simple(shape, seed=0, scale=8.0):
    """Very fast simple 2D perlin-ish noise via tiled sinusoids."""
    h, w = shape
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float32)
    for _ in range(4):
        fx = rng.random() * scale
        fy = rng.random() * scale
        px = rng.random() * 2 * np.pi
        py = rng.random() * 2 * np.pi
        yy = np.linspace(0, fy * np.pi * 2, h, dtype=np.float32)[:, None] + py
        xx = np.linspace(0, fx * np.pi * 2, w, dtype=np.float32)[None, :] + px
        out += np.sin(yy) * np.cos(xx)
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return out.astype(np.float32)





# ═══════════════════════════════════════════════════════════════════════════════
# FLAME PATTERNS — 10 all-new, each with a unique geometry
# ═══════════════════════════════════════════════════════════════════════════════
#
# PAINT: Every flame uses _paint_flame() — a dedicated hot→cool gradient that
#        maps pattern_val (0=none, 1=full flame) to:
#          1.0  → white/yellow core  (hottest)
#          0.6  → bright orange
#          0.3  → deep red
#          0.0  → dark charcoal / smoke  (coolest, background)
#        plus a specular boost (lower R) at the bright core.
#
# R_range / M_range in each texture are intentionally large so the flame
# interacts strongly with whatever base the user has chosen.
# ═══════════════════════════════════════════════════════════════════════════════


def _multi_scale_noise_fast(shape, scales, seed=0):
    """Lightweight multi-scale noise via summed sinusoids (no PIL/SciPy)."""
    h, w = shape
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float32)
    weight_total = 0.0
    for s in scales:
        w_i = 1.0 / s
        fx = rng.uniform(0.5, 1.5) / (s * max(w, 1))
        fy = rng.uniform(0.5, 1.5) / (s * max(h, 1))
        px = rng.uniform(0, 2 * np.pi)
        py = rng.uniform(0, 2 * np.pi)
        xx = np.arange(w, dtype=np.float32)[None, :] * fx * 2 * np.pi + px
        yy = np.arange(h, dtype=np.float32)[:, None] * fy * 2 * np.pi + py
        out += (np.sin(xx) * np.cos(yy)).astype(np.float32) * w_i
        weight_total += w_i
    out /= max(weight_total, 1e-8)
    mn, mx = out.min(), out.max()
    if mx > mn:
        out = (out - mn) / (mx - mn)
    return out.astype(np.float32)


# ─── 1. Classic Hot Rod Tongues ──────────────────────────────────────────────
def _tex_flame_hotrod_classic(shape, seed):
    """
    Traditional hot-rod licking tongues sweeping from left edge.
    Each tongue is unique: different centre-Y, length, curvature, taper.
    Seed changes the whole set so every use feels hand-painted.
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float32)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    n = rng.integers(18, 30)  # Many fine tongues (was 8-14 with fat widths)
    for _ in range(n):
        cy      = rng.uniform(0.05, 0.95) * h
        length  = rng.uniform(0.40, 0.95) * w
        base_hw = rng.uniform(0.015, 0.045) * h  # Fine tongues (was 0.06-0.18 = huge bands)
        curve   = rng.uniform(0.5, 2.5) * (1 if rng.random() > 0.5 else -1)
        taper   = rng.uniform(1.2, 2.2)
        wobble  = rng.uniform(0.5, 2.5)
        x_norm  = np.clip(xx / max(length, 1), 0, 1)
        tip_y   = cy + np.sin(x_norm * np.pi * wobble + rng.uniform(0, np.pi)) * h * 0.10 * curve
        hw_at_x = base_hw * (1 - x_norm) ** taper
        dist    = np.abs(yy[:, None] - tip_y[None, :])
        tongue  = np.clip(1.0 - dist / (hw_at_x[None, :] + 1e-4), 0, 1)
        tongue[:, xx >= length] = 0.0
        out = np.maximum(out, tongue)
    bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2130) * 0.13 + 0.08
    out = np.clip(out + bg, 0, 1)
    return out


# ─── 2. Ghost Flames ─────────────────────────────────────────────────────────
def _tex_flame_ghost(shape, seed):
    """
    Ultra-thin, barely-visible wisps.  Gaussian pencil-thin flames with
    strong noise-driven wobble.  Low peak value so they feel translucent.
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float32)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    noise = _noise_simple(shape, seed=seed + 7, scale=40.0)  # Fine wisp turbulence
    for i in range(rng.integers(10, 16)):  # More wisps (was 6-11)
        cx     = rng.uniform(0.0, 1.0) * w
        length = rng.uniform(0.55, 0.95) * w
        sigma  = rng.uniform(0.005, 0.015) * h    # Fine wisps (was 0.015-0.04 = too thick)
        peak   = rng.uniform(0.55, 0.90)          # Brighter (was 0.35-0.65)
        x_norm = np.clip(xx / max(length, 1), 0, 1)
        # Wobble driven by noise column
        wobble_amp = h * rng.uniform(0.06, 0.18)
        col_noise  = noise[:, np.clip((xx * noise.shape[1] / w).astype(int),
                                      0, noise.shape[1]-1).reshape(-1)]
        centre_y = (cx * 0 + h * 0.5 +
                    np.sin(x_norm * np.pi * rng.uniform(1.2, 3.5)) * wobble_amp)
        # One row per x: gaussian
        dist     = np.abs(yy[:, None] - centre_y[None, :])
        wisp     = np.exp(-(dist**2) / (sigma**2)) * np.clip(peak * 1.4, 0, 1)  # Sharper + brighter
        wisp    *= (1 - x_norm)[None, :] ** 0.6   # fade at tip
        wisp[:, xx >= length] = 0.0
        out = np.maximum(out, wisp.astype(np.float32))
    bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2120) * 0.13 + 0.08
    out = np.clip(out + bg, 0, 1)
    return out


# ─── 3. Blue Propane Flame ───────────────────────────────────────────────────
def _tex_flame_blue_propane(shape, seed):
    """
    Dense tight cones of propane-torch flame rising from the base edge.
    Geometry: narrow at base, slightly wider then needle-sharp tip.
    High-frequency flicker noise on the edges only.
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    # PERF: compute at 512 max to avoid slow per-cone noise at full res
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    out = np.zeros((sh, sw), dtype=np.float32)
    yy = np.arange(sh, dtype=np.float32)
    xx = np.arange(sw, dtype=np.float32)
    n_cones = rng.integers(14, 22)
    for i in range(n_cones):
        base_x  = rng.uniform(0.0, 1.0) * sw
        height  = rng.uniform(0.20, 0.60) * sh
        base_hw = rng.uniform(0.022, 0.050) * sw
        taper   = rng.uniform(2.8, 4.2)
        y_from_base = sh - 1 - yy
        progress    = np.clip(y_from_base / max(height, 1), 0, 1)
        hw_at_y     = base_hw * progress ** 0.45
        n_col       = _noise_simple((sh, sw), seed=seed + i * 13, scale=20.0)
        flicker     = n_col * base_hw * 0.25
        dist        = np.abs(xx[None, :] - base_x - flicker[:, 0:1])
        cone        = np.clip(1.0 - dist / (hw_at_y[:, None] + 1e-4), 0, 1)
        cone[y_from_base > height] = 0.0
        cone        = np.power(cone, taper * (1 - progress[:, None] * 0.15))
        out = np.maximum(out, cone.astype(np.float32))
    if ds > 1:
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
    # Heat shimmer background
    bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2110) * 0.16 + 0.10
    out = np.clip(out + bg, 0, 1)
    return out


# ─── 4. Tribal Knife Flame ───────────────────────────────────────────────────
def _tex_flame_tribal_knife(shape, seed):
    """
    Hard-edged angular tribal flame silhouettes.
    Geometry: signed-distance-field of kite/diamond polygons arranged
    in a sweep from left to right, each rotated to lean rearward.
    Pure binary mask (0 or 1) with soft edge.
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float32)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    n_blades = rng.integers(6, 12)  # More blades for density
    for i in range(n_blades):
        cx   = rng.uniform(0.05, 0.85) * w
        cy   = rng.uniform(0.15, 0.85) * h
        a    = rng.uniform(0.08, 0.20) * h
        b    = rng.uniform(0.02, 0.06) * w
        lean = rng.uniform(0.2, 0.6)
        dx   = xx - cx + (yy - cy) * lean
        dy   = yy - cy
        sdf  = 1.0 - (np.abs(dx) / (b + 1e-4) + np.abs(dy) / (a + 1e-4))
        blade = np.clip(sdf * 18.0, 0, 1)
        glow = np.clip(sdf * 4.0, 0, 1) * 0.3  # Heat glow halo
        out  = np.maximum(out, (blade + glow).astype(np.float32))
    # Secondary smaller blades for complexity
    for _ in range(rng.integers(8, 16)):
        cx2 = rng.uniform(0.0, 1.0) * w
        cy2 = rng.uniform(0.1, 0.9) * h
        a2  = rng.uniform(0.04, 0.10) * h
        b2  = rng.uniform(0.01, 0.03) * w
        lean2 = rng.uniform(0.15, 0.8)
        dx2 = xx - cx2 + (yy - cy2) * lean2
        dy2 = yy - cy2
        sdf2 = 1.0 - (np.abs(dx2) / (b2 + 1e-4) + np.abs(dy2) / (a2 + 1e-4))
        out = np.maximum(out, np.clip(sdf2 * 14.0, 0, 0.7).astype(np.float32))
    bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2100) * 0.16 + 0.10
    out = np.clip(out + bg, 0, 1)
    return out


# ─── 5. Hellfire Columns ─────────────────────────────────────────────────────
def _tex_flame_hellfire_column(shape, seed):
    """
    Tall meandering hellfire columns that claw upward from the base.
    Each column is a polyline of connected Gaussian cross-sections with
    chaotic lateral drift — looks like the column is alive.
    Wide coverage, multiple overlapping columns.
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float32)
    n_cols = rng.integers(12, 22)
    xx = np.arange(w, dtype=np.float32)[None, :]
    yy = np.arange(h, dtype=np.float32)[:, None]
    # Ambient hellglow base
    glow = _noise_simple(shape, seed=seed + 1, scale=40.0) * 0.18  # Fine ambient hellglow
    out = np.maximum(out, glow)
    for _ in range(n_cols):
        x_base  = rng.uniform(-0.05, 1.05) * w
        sigma   = rng.uniform(0.015, 0.05) * w
        height  = rng.uniform(0.55, 1.0) * h
        peak    = rng.uniform(0.55, 1.0)
        # Generate meandering centre-x as a function of y (polyline)
        n_segs  = rng.integers(4, 10)
        seg_len = height / max(n_segs, 1)
        ys      = np.arange(h, dtype=np.float32)
        cx_arr  = np.zeros(h, dtype=np.float32)
        cur_x   = x_base
        for s in range(n_segs):
            y0 = int(h - (s + 1) * seg_len)
            y1 = int(h - s * seg_len)
            y0, y1 = max(0, y0), min(h, y1)
            next_x = cur_x + rng.uniform(-0.08, 0.08) * w
            if y1 > y0:
                cx_arr[y0:y1] = np.linspace(cur_x, next_x, y1 - y0)
            cur_x = next_x
        # Only rows within height
        in_range = (ys >= (h - height)).astype(np.float32)
        dist = np.abs(xx - cx_arr[:, None])
        col  = np.exp(-(dist**2) / (2 * sigma**2)) * peak
        col *= in_range[:, None]
        # Taper at tip
        tip_fade = np.clip((h - ys) / max(height * 0.25, 1), 0, 1)[:, None] ** 1.5
        col *= tip_fade
        out = np.maximum(out, col.astype(np.float32))
    return np.clip(out, 0, 1)


# ─── 6. Inferno Wall ─────────────────────────────────────────────────────────
def _tex_flame_inferno_wall(shape, seed):
    """
    Zero dead zones — the entire canvas is fire.
    Vertical flame structure drives from bottom; heat-shimmer noise
    ensures every pixel above 0.0.  Three overlapping density passes.
    OPTIMIZED: compute at 256x256 max, upscale.
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    # Resolution cap for performance
    ds = max(1, min(h, w) // 1024)
    sh, sw = max(64, h // ds), max(64, w // ds)
    yy = np.arange(sh, dtype=np.float32).reshape(-1, 1)
    xx = np.arange(sw, dtype=np.float32).reshape(1, -1)
    # Layer 1: heat shimmer base — uses full shape (has own resolution handling)
    heat = _noise_simple(shape, seed=seed + 1, scale=50.0)  # Fine heat shimmer
    if ds > 1:
        heat = cv2.resize(heat.astype(np.float32), (sw, sh), interpolation=cv2.INTER_LINEAR)
    out  = heat * 0.20
    # Layer 2: dense flame columns (~40) — at reduced resolution
    for _ in range(40):
        cx      = rng.uniform(-0.05, 1.05) * sw
        height  = rng.uniform(0.70, 1.0) * sh
        sigma   = rng.uniform(0.025, 0.10) * sw
        phase   = rng.uniform(0, 2 * np.pi)
        peak    = rng.uniform(0.50, 1.0)
        y_norm  = np.clip(1.0 - yy / max(height, 1), 0, 1)
        wobble  = (np.sin(yy * 0.055 * ds + phase) * sigma * 0.4 +
                   np.sin(yy * 0.12 * ds + phase * 2.3) * sigma * 0.18)
        dist    = np.abs(xx - cx - wobble)
        col     = np.clip(1.0 - dist / (sigma * y_norm + 1), 0, 1) * y_norm
        out     = np.maximum(out, col.astype(np.float32) * peak)
    # Layer 3: bright base glow
    base_glow = np.clip(1.0 - yy / (sh * 0.30), 0, 1) ** 1.8 * 0.4
    out = np.maximum(out, base_glow * np.ones((1, sw), dtype=np.float32))
    # Upscale to full resolution
    if ds > 1:
        out = cv2.resize(np.clip(out, 0, 1).astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return np.clip(out, 0, 1)


# ─── 7. Pinstripe Outline Flames ─────────────────────────────────────────────
def _tex_flame_pinstripe_outline(shape, seed):
    """
    Elegant drawn-line flame outlines — only the outer edge of each tongue
    is rendered as a thin double-line (like 1950s custom auto art).
    Uses SDF of the tongue profile to extract just the outline band.
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    # Build base fill (same as hotrod classic)
    fill = _tex_flame_hotrod_classic(shape, seed)
    # Outline = thin ring around fill > threshold
    # SDF approximation: gradient magnitude of fill
    fill_shifted_r = np.roll(fill, 1, axis=1)
    fill_shifted_l = np.roll(fill, -1, axis=1)
    fill_shifted_u = np.roll(fill, -1, axis=0)
    fill_shifted_d = np.roll(fill, 1, axis=0)
    grad = (np.abs(fill - fill_shifted_r) +
            np.abs(fill - fill_shifted_l) +
            np.abs(fill - fill_shifted_u) +
            np.abs(fill - fill_shifted_d))
    # Normalise and sharpen
    grad = grad / (grad.max() + 1e-8)
    # Two thick outline bands + gradient fill + edge gradient
    outer = np.exp(-((fill - 0.12) ** 2) / 0.005) * 1.0   # Wider outer line
    inner = np.exp(-((fill - 0.55) ** 2) / 0.004) * 0.85   # Wider inner line
    # Faint fill between outlines
    fill_between = np.where((fill > 0.15) & (fill < 0.52), fill * 0.3, 0)
    # Edge gradient for depth
    edge_glow = grad * 0.4
    outline = np.clip(outer + inner + fill_between + edge_glow, 0, 1).astype(np.float32)
    return outline


# ─── 8. Ember Field ──────────────────────────────────────────────────────────
def _tex_flame_ember_field(shape, seed):
    """
    No tongue shapes at all — pure floating ember particles drifting upward.
    Each ember is a small bright dot with a soft comet-tail trailing below.
    Embers cluster near the base and thin out toward the top.
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    # Resolution cap — N embers × per-ember Gaussian patch = O(N × patch²)
    ds = max(1, min(h, w) // 512)
    sh, sw = max(64, h // ds), max(64, w // ds)
    out = np.zeros((sh, sw), dtype=np.float32)
    n_embers = rng.integers(80, 180)
    yy = np.arange(sh, dtype=np.float32)[:, None]
    xx = np.arange(sw, dtype=np.float32)[None, :]
    for _ in range(n_embers):
        # Bias position toward lower half (use scaled coords)
        ex     = rng.uniform(0.0, 1.0) * sw
        ey     = rng.uniform(0.1, 1.0) ** 0.6 * sh   # power < 1 → bottom bias
        r_core = rng.uniform(1.5, 4.5) / ds           # scale radii with downsample
        r_halo = r_core * rng.uniform(2.5, 5.0)       # soft halo
        peak   = rng.uniform(0.75, 1.0)
        tail_l = rng.uniform(0.04, 0.14) * sh          # comet tail length
        # Core dot
        d2 = (xx - ex)**2 + (yy - ey)**2
        core = np.exp(-d2 / (2 * max(r_core, 0.5)**2)) * peak
        halo = np.exp(-d2 / (2 * max(r_halo, 0.5)**2)) * peak * 0.35
        # Tail: gaussian elongated downward (y > ey)
        dy    = np.clip(yy - ey, 0, None)            # only below ember
        tail  = np.exp(-(xx - ex)**2 / (2 * max(r_core, 0.5)**2)) * np.exp(-dy / max(tail_l, 1)) * peak * 0.5
        ember = np.clip(core + halo + tail, 0, 1).astype(np.float32)
        out   = np.maximum(out, ember)
    # Upscale to full resolution before adding noise (noise uses full shape)
    if ds > 1:
        out = cv2.resize(out.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    # Very faint ambient shimmer (uses full shape — has own resolution handling)
    out += _multi_scale_noise_fast(shape, [6, 12], seed + 9) * 0.06
    return np.clip(out, 0, 1)


# ─── 9. Split Fishtail ───────────────────────────────────────────────────────
def _tex_flame_split_fishtail(shape, seed):
    """
    Two symmetrical flame lobes splitting at a point, like a fish tail or
    a forked flame end.  The split grows progressively wider toward the
    trailing edge.  Works like a classic scallop split with a Gaussian SDF.
    Multiple pairs stacked for depth.
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), dtype=np.float32)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    n_pairs = rng.integers(5, 9)  # More pairs (was 3-6)
    for i in range(n_pairs):
        cy_top  = rng.uniform(0.15, 0.48) * h
        cy_bot  = h - cy_top
        x_start = rng.uniform(0.0, 0.35) * w
        x_end   = rng.uniform(0.6, 1.0) * w
        length  = x_end - x_start
        base_hw = rng.uniform(0.07, 0.14) * h  # Wider lobes (was 0.05-0.10)
        split_k = rng.uniform(0.15, 0.40)
        peak    = rng.uniform(0.80, 1.0)  # Brighter (was 0.65-1.0)
        x_norm  = np.clip((xx - x_start) / max(length, 1), 0, 1)
        # As x_norm increases, the two lobes spread apart
        spread  = h * split_k * x_norm
        hw_at_x = base_hw * (1 - x_norm) ** 1.6
        for cy in (cy_top - spread, cy_bot + spread):
            dist   = np.abs(yy[:, None] - cy[None, :])
            tongue = np.clip(1.0 - dist / (hw_at_x[None, :] + 1e-4), 0, 1) * peak
            tongue[:, xx < x_start] = 0.0
            tongue[:, xx > x_end]   = 0.0
            out = np.maximum(out, tongue.astype(np.float32))
    bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2140) * 0.13 + 0.08
    out = np.clip(out + bg, 0, 1)
    return out


# ─── 10. Smoke Fade ──────────────────────────────────────────────────────────
def _tex_flame_smoke_fade(shape, seed):
    """
    Flames at the bottom dissolve upward into loose, turbulent smoke.
    Lower 30% = solid tongue fill; middle 40% = soft transition;
    upper 30% = pure multi-scale noise wisps.
    Gradient alpha drives the blend: no abrupt cutoff.
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    yy = np.arange(h, dtype=np.float32)
    # Flame base (classic tongues) in the lower portion
    flame = _tex_flame_hotrod_classic(shape, seed)
    # Smoke layer: turbulent noise
    smoke = _noise_simple(shape, seed=seed + 50, scale=35.0)  # Fine smoke turbulence
    smoke = np.power(smoke, 0.7)  # lift midtones
    # Blend gradient: 0.0 at top (pure smoke), 1.0 at bottom (pure flame)
    blend = np.clip((h - 1 - yy) / max(h * 0.75, 1), 0, 1) ** 1.3
    blend_2d = blend[:, None] * np.ones((1, w), dtype=np.float32)
    out = flame * blend_2d + smoke * (1.0 - blend_2d) * 0.85
    return np.clip(out, 0, 1).astype(np.float32)


# ─── Dispatcher ──────────────────────────────────────────────────────────────
def _texture_flame_dispatch(shape, mask, seed, sm, variant):
    """Route new flame IDs to their dedicated texture functions."""
    h, w = shape
    _MAP = {
        "flame_hotrod_classic":    _tex_flame_hotrod_classic,
        "flame_ghost":             _tex_flame_ghost,
        "flame_blue_propane":      _tex_flame_blue_propane,
        "flame_tribal_knife":      _tex_flame_tribal_knife,
        "flame_hellfire_column":   _tex_flame_hellfire_column,
        "flame_inferno_wall":      _tex_flame_inferno_wall,
        "flame_pinstripe_outline": _tex_flame_pinstripe_outline,
        "flame_ember_field":       _tex_flame_ember_field,
        "flame_split_fishtail":    _tex_flame_split_fishtail,
        "flame_smoke_fade":        _tex_flame_smoke_fade,
    }
    fn = _MAP.get(variant)
    if fn is None:
        # Unknown new flame ID: safe fallback
        val = np.zeros((h, w), dtype=np.float32)
        return _pack(val, 0, 0)
    val = fn(shape, seed)
    # R_range / M_range chosen so flames work on all bases:
    # strong negative R (roughness → smooth in hot zones) + strong positive M (metallic pop)
    return _pack(val, R_range=-170.0, M_range=150.0)


# ─── Dedicated Flame Paint: hot→cool gradient ─────────────────────────────────
def _paint_flame(paint, shape, mask, seed, pm, bb, variant):
    """
    Drives the colour of each flame pixel based on the pattern_val
    coming from the texture.  Maps intensity → temperature colour:

        1.0  → white-yellow  (hottest core)
        0.7  → bright orange
        0.45 → deep orange-red
        0.25 → crimson red
        0.0  → near-black smoke / no effect

    For ghost and smoke variants the palette shifts to cooler / lower contrast
    so they stay subtle.  For blue_propane the hue shift is toward blue-white.
    """
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    is_ghost  = "ghost"   in variant
    is_blue   = "blue"    in variant
    is_smoke  = "smoke"   in variant
    is_ember  = "ember"   in variant
    is_pin    = "pinstripe" in variant

    # Retrieve pattern_val stored in bb if present
    pv = None
    if isinstance(bb, dict):
        pv = bb.get("pattern_val")
    if pv is None:
        # No pattern_val: use mask as proxy (still better than flat red push)
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)

    if is_ghost:
        # Ghost: barely-there cool tone, very low pm
        strength = pm * 0.30
        paint[:, :, 0] = np.clip(paint[:, :, 0] + pv * 0.12 * strength * mask, 0, 1)
        paint[:, :, 1] = np.clip(paint[:, :, 1] + pv * 0.06 * strength * mask, 0, 1)
        paint[:, :, 2] = np.clip(paint[:, :, 2] + pv * 0.04 * strength * mask, 0, 1)
        return paint

    if is_blue:
        # Blue propane: blue-white core, no red
        hot_zone   = np.clip((pv - 0.5) * 2, 0, 1)
        warm_zone  = np.clip((pv - 0.2) * 2.5, 0, 1) * (1 - hot_zone)
        cool_zone  = pv * (1 - warm_zone - hot_zone)
        strength   = pm * 0.85
        # Core: white-blue (all channels high, blue highest)
        paint[:, :, 0] = np.clip(paint[:, :, 0] + hot_zone  * 0.55 * strength * mask, 0, 1)
        paint[:, :, 1] = np.clip(paint[:, :, 1] + hot_zone  * 0.60 * strength * mask, 0, 1)
        paint[:, :, 2] = np.clip(paint[:, :, 2] + hot_zone  * 0.90 * strength * mask, 0, 1)
        # Warm: azure
        paint[:, :, 0] = np.clip(paint[:, :, 0] - warm_zone * 0.10 * strength * mask, 0, 1)
        paint[:, :, 1] = np.clip(paint[:, :, 1] + warm_zone * 0.25 * strength * mask, 0, 1)
        paint[:, :, 2] = np.clip(paint[:, :, 2] + warm_zone * 0.65 * strength * mask, 0, 1)
        return paint

    if is_smoke:
        # Smoke fade: flame at bottom (warm), smoke at top (desaturate + lighten)
        warm_push  = np.clip(pv * 1.6 - 0.3, 0, 1)  # only bright parts are warm
        strength   = pm * 0.55
        paint[:, :, 0] = np.clip(paint[:, :, 0] + warm_push * 0.30 * strength * mask, 0, 1)
        paint[:, :, 1] = np.clip(paint[:, :, 1] + warm_push * 0.12 * strength * mask, 0, 1)
        paint[:, :, 2] = np.clip(paint[:, :, 2] - warm_push * 0.05 * strength * mask, 0, 1)
        return paint

    if is_ember:
        # Embers: each spark is orange-white; background dark
        hot_zone  = np.clip((pv - 0.60) * 4, 0, 1)
        mid_zone  = np.clip((pv - 0.25) * 2.5, 0, 1) * (1 - hot_zone)
        strength  = pm * 0.90
        paint[:, :, 0] = np.clip(paint[:, :, 0] + (hot_zone * 0.80 + mid_zone * 0.50) * strength * mask, 0, 1)
        paint[:, :, 1] = np.clip(paint[:, :, 1] + (hot_zone * 0.65 + mid_zone * 0.22) * strength * mask, 0, 1)
        paint[:, :, 2] = np.clip(paint[:, :, 2] + hot_zone  * 0.30 * strength * mask, 0, 1)
        return paint

    if is_pin:
        # Pinstripe: outlines are drawn in hot white-yellow over a dark field
        strength  = pm * 0.80
        paint[:, :, 0] = np.clip(paint[:, :, 0] + pv * 0.70 * strength * mask, 0, 1)
        paint[:, :, 1] = np.clip(paint[:, :, 1] + pv * 0.45 * strength * mask, 0, 1)
        paint[:, :, 2] = np.clip(paint[:, :, 2] + pv * 0.05 * strength * mask, 0, 1)
        return paint

    # ── Default: full hot→cool temperature gradient ──────────────────────────
    # Zones derived from pattern_val
    hot_zone    = np.clip((pv - 0.70) * 3.3, 0, 1)          # >0.70 → white/yellow core
    orange_zone = np.clip((pv - 0.40) * 3.3, 0, 1) * (1 - hot_zone)
    red_zone    = np.clip((pv - 0.15) * 2.5, 0, 1) * (1 - hot_zone - orange_zone)
    dark_zone   = np.clip(1 - pv * 3.5, 0, 1)               # near-zero → pull dark

    strength    = pm * 0.90

    # White-yellow core: push all channels, esp R+G
    paint[:, :, 0] = np.clip(paint[:, :, 0] + hot_zone    * 0.90 * strength * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + hot_zone    * 0.80 * strength * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + hot_zone    * 0.40 * strength * mask, 0, 1)
    # Orange mid: push R hard, G moderate, suppress B
    paint[:, :, 0] = np.clip(paint[:, :, 0] + orange_zone * 0.80 * strength * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + orange_zone * 0.32 * strength * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - orange_zone * 0.08 * strength * mask, 0, 1)
    # Crimson: push R, pull G and B
    paint[:, :, 0] = np.clip(paint[:, :, 0] + red_zone    * 0.55 * strength * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] - red_zone    * 0.12 * strength * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - red_zone    * 0.06 * strength * mask, 0, 1)
    # Dark edges: slightly desaturate / cool at flame boundary
    paint[:, :, 0] = np.clip(paint[:, :, 0] - dark_zone   * 0.04 * strength * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] - dark_zone   * 0.04 * strength * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - dark_zone   * 0.04 * strength * mask, 0, 1)
    return paint

# ─────────────────────────────────────────────────────────────────────────────


    """Draw a recognisable zodiac glyph into a float32 mask."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return _concentric_rings(shape, 4)
    h, w = shape
    img = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2
    s = min(w, h) // 3

    if sign == 'aries':
        # Ram horns: two arcs going up-out from centre
        d.arc([cx - s, cy - s, cx, cy + s//2], 30, 180, fill=255, width=max(2, s//5))
        d.arc([cx, cy - s, cx + s, cy + s//2], 0, 150, fill=255, width=max(2, s//5))
    elif sign == 'taurus':
        d.ellipse([cx - s, cy - s//2, cx + s, cy + s//2 + s], outline=255, width=max(2, s//5))
        d.arc([cx - s - s//2, cy - s, cx + s + s//2, cy], 180, 360, fill=255, width=max(2, s//5))
    elif sign == 'gemini':
        lw = max(2, s // 5)
        d.line([(cx - s, cy - s), (cx - s, cy + s)], fill=255, width=lw)
        d.line([(cx + s, cy - s), (cx + s, cy + s)], fill=255, width=lw)
        d.line([(cx - s, cy - s), (cx + s, cy - s)], fill=255, width=lw)
        d.line([(cx - s, cy + s), (cx + s, cy + s)], fill=255, width=lw)
    elif sign == 'cancer':
        d.arc([cx - s, cy - s//2, cx, cy + s//2], 0, 300, fill=255, width=max(2, s//5))
        d.arc([cx, cy - s//2, cx + s, cy + s//2], 180, 480, fill=255, width=max(2, s//5))
    elif sign == 'leo':
        d.arc([cx - s, cy - s, cx + s//2, cy + s//2], 90, 360, fill=255, width=max(2, s//5))
        d.arc([cx + s//4, cy, cx + s, cy + s], 180, 90, fill=255, width=max(2, s//5))
    elif sign == 'virgo':
        lw = max(2, s // 5)
        d.line([(cx - s, cy - s), (cx - s, cy + s)], fill=255, width=lw)
        d.line([(cx - s, cy), (cx, cy)], fill=255, width=lw)
        d.line([(cx, cy - s), (cx, cy + s)], fill=255, width=lw)
        d.line([(cx, cy), (cx + s//2, cy)], fill=255, width=lw)
        d.arc([cx + s//2, cy - s//3, cx + s, cy + s//3], 270, 270 + 270, fill=255, width=lw)
    elif sign == 'libra':
        lw = max(2, s // 5)
        d.line([(cx - s, cy + s//3), (cx + s, cy + s//3)], fill=255, width=lw)
        d.arc([cx - s//2, cy - s, cx + s//2, cy + s//3], 180, 360, fill=255, width=lw)
    elif sign == 'scorpio':
        lw = max(2, s // 5)
        d.line([(cx - s, cy - s//2), (cx - s, cy + s//2)], fill=255, width=lw)
        d.line([(cx - s, cy), (cx + s//2, cy)], fill=255, width=lw)
        d.line([(cx + s//2, cy - s//2), (cx + s//2, cy + s//2)], fill=255, width=lw)
        # barbed tail
        d.line([(cx + s//2, cy + s//2), (cx + s, cy + s)], fill=255, width=lw)
        d.line([(cx + s, cy + s), (cx + s - s//4, cy + s//2)], fill=255, width=lw)
    elif sign == 'sagittarius':
        lw = max(2, s // 5)
        # Arrow diagonal + cross
        d.line([(cx - s, cy + s), (cx + s, cy - s)], fill=255, width=lw)
        d.line([(cx + s - s//2, cy - s), (cx + s, cy - s)], fill=255, width=lw)
        d.line([(cx + s, cy - s), (cx + s, cy - s + s//2)], fill=255, width=lw)
        d.line([(cx - s//3, cy - s//4), (cx + s//3, cy + s//4)], fill=255, width=lw)
    elif sign == 'capricorn':
        lw = max(2, s // 5)
        d.arc([cx - s, cy - s, cx, cy + s], 90, 360, fill=255, width=lw)
        d.arc([cx - s//2, cy, cx + s, cy + s + s//2], 270, 180, fill=255, width=lw)
    elif sign == 'aquarius':
        lw = max(2, s // 5)
        for dy in [-s//4, s//4]:
            pts = []
            for i, x in enumerate(range(cx - s, cx + s + 1, s // 4)):
                y = cy + dy + (s // 6 if i % 2 == 0 else -s // 6)
                pts.append((x, y))
            d.line(pts, fill=255, width=lw)
    elif sign == 'pisces':
        lw = max(2, s // 5)
        d.arc([cx - s, cy - s, cx, cy + s], 270, 450, fill=255, width=lw)
        d.arc([cx, cy - s, cx + s, cy + s], 90, 270, fill=255, width=lw)
        d.line([(cx - s//3, cy), (cx + s//3, cy)], fill=255, width=lw)

    arr = np.array(img).astype(np.float32) / 255.0
    return arr


def _pack(val, R_range=-80.0, M_range=80.0, cc_scale=None):
    """Pack pattern_val into standard return dict."""
    if cc_scale is None:
        cc_arr = np.clip(16 * (1 - val * 0.5), 0, 16).astype(np.uint8)
    else:
        cc_arr = np.full(val.shape, cc_scale, dtype=np.uint8)
    return {"pattern_val": val.astype(np.float32), "R_range": R_range, "M_range": M_range, "CC": cc_arr}


# === LET FREEDOM RING PATTERNS (lfr_*) 2026-06-09 START ===
# 10 patriotic patterns. UV-orientation-agnostic: scattered/radial/multi-angle
# motifs only, per-instance random rotations, no upright flag geometry.
# Dispatched from _texture_expansion/_paint_expansion via the lfr_ prefix.
def _lfr_star_sdf(xx, yy, cx, cy, R, rot, k=5):
    dx = xx - cx; dy = yy - cy
    ang = np.arctan2(dy, dx) - rot
    rad = np.hypot(dx, dy)
    m = 2.0 * np.pi / k
    a = np.mod(ang, m); a = np.abs(a - m * 0.5)
    edge = R * (0.42 + 0.58 * (a / (m * 0.5)))
    return np.clip(1.0 - rad / (edge + 1e-4), 0.0, 1.0)

# ---- texture ----
def _tex_lfr_star_lattice(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 4001)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    out = np.zeros((h, w), dtype=np.float32)
    dim = float(min(h, w))
    tiers = [
        (int(rng.integers(7, 11)),  0.085, 0.150, 1.00),
        (int(rng.integers(20, 30)), 0.040, 0.075, 0.85),
        (int(rng.integers(60, 90)), 0.014, 0.030, 0.60),
    ]
    for count, fmin, fmax, peak in tiers:
        for _ in range(count):
            cx = rng.uniform(-0.05, 1.05) * w
            cy = rng.uniform(-0.05, 1.05) * h
            R  = rng.uniform(fmin, fmax) * dim
            rot = rng.uniform(0.0, 2.0 * np.pi)
            # PERF: star SDF support is exactly rad < edge <= R, so evaluate
            # only the local window (identical math on the slice).
            x0 = max(0, int(cx - R) - 2); x1 = min(w, int(cx + R) + 3)
            y0 = max(0, int(cy - R) - 2); y1 = min(h, int(cy + R) + 3)
            if x0 >= x1 or y0 >= y1:
                continue
            star = _lfr_star_sdf(xx[:, x0:x1], yy[y0:y1, :], cx, cy, R, rot, k=5)
            star = np.power(star, 0.55) * peak
            out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], star.astype(np.float32))
    bg = _multi_scale_noise_fast(shape, [8, 16, 32], int(seed) + 4007) * 0.10 + 0.06
    return np.clip(out + bg, 0.0, 1.0).astype(np.float32)
# ---- paint ----
def _paint_lfr_star_lattice(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None: pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1); s = pm * 0.95
    core = np.clip((pv - 0.55) * 2.4, 0, 1)
    halo = np.clip((pv - 0.18) * 1.6, 0, 1) * (1 - core)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + core * 0.85 * s * mask - halo * 0.10 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + core * 0.85 * s * mask - halo * 0.04 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + core * 0.92 * s * mask + halo * 0.55 * s * mask, 0, 1)
    return paint

# ---- texture ----
def _tex_lfr_stripe_drift(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 4101)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    cx0, cy0 = w * 0.5, h * 0.5
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    n = int(rng.integers(16, 26))
    for _ in range(n):
        ang = rng.uniform(0.0, np.pi)
        ca, sa = np.cos(ang), np.sin(ang)
        proj = (xx - cx0) * sa - (yy - cy0) * ca
        # PERF: run = (xx-cx0)*ca + (yy-cy0)*sa is affine in x/y, so the two
        # full-grid sin() fields are computed via sin(U+V) = sinU*cosV +
        # cosU*sinV with 1-D row/col vectors (error ~1e-6 px, invisible).
        # Same rng draws in the same order as the original expressions.
        A = (xx - cx0) * ca          # (1, w)
        B = (yy - cy0) * sa          # (h, 1)
        c1 = rng.uniform(0.18, 0.42); p1 = rng.uniform(0, 6.28); a1 = rng.uniform(0.02, 0.06)
        u = A / (dim * c1); v = B / (dim * c1) + p1
        amp = np.float32(dim * a1)
        drift = (np.sin(u) * amp) * np.cos(v) + (np.cos(u) * amp) * np.sin(v)
        c4 = rng.uniform(0.012, 0.040); c5 = rng.uniform(0.25, 0.6); p2 = rng.uniform(0, 6.28)
        u2 = A / (dim * c5); v2 = B / (dim * c5) + p2
        s4 = np.float32(c4 * dim * 0.6)
        hw = (np.sin(u2) * s4) * np.cos(v2) + (np.cos(u2) * s4) * np.sin(v2)
        # hw0*(1+0.6*sin) > 0 always (0.6 < 1), so abs() is the identity.
        band = np.clip(1.0 - np.abs(proj - drift) / (hw + np.float32(c4 * dim + 1e-4)), 0, 1)
        # PERF: pow only where band > 0 (band is mostly zero; 0**0.8 == 0).
        bp = np.zeros_like(band, dtype=np.float32)
        nz = band > 0
        bp[nz] = np.power(band[nz], 0.8)
        out = np.maximum(out, bp)
    bg = _multi_scale_noise_fast(shape, [8, 16], int(seed) + 4109) * 0.08 + 0.05
    return np.clip(out + bg, 0.0, 1.0).astype(np.float32)
# ---- paint ----
def _paint_lfr_stripe_drift(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None: pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1); s = pm * 0.9
    h, w = shape
    yy = np.arange(h, dtype=np.float32)[:, None]; xx = np.arange(w, dtype=np.float32)[None, :]
    phase = (np.sin(xx * 0.012 + yy * 0.009 + (int(seed) % 19)) * 0.5 + 0.5)
    white_band = pv * phase; red_band = pv * (1.0 - phase)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + white_band * 0.75 * s * mask + red_band * 0.70 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + white_band * 0.75 * s * mask - red_band * 0.18 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + white_band * 0.78 * s * mask - red_band * 0.12 * s * mask, 0, 1)
    return paint

# ---- texture ----
def _tex_lfr_bunting_scallop(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 4201)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    n = int(rng.integers(10, 16))
    for _ in range(n):
        cx = rng.uniform(0.0, 1.0) * w; cy = rng.uniform(0.0, 1.0) * h
        rot = rng.uniform(0.0, 2.0 * np.pi); span = rng.uniform(0.7, 1.5)
        base_r = rng.uniform(0.10, 0.22) * dim; rings = int(rng.integers(3, 6))
        gap = base_r / (rings + 1)
        # PERF: arcs live strictly inside rad < base_r — local window only.
        x0 = max(0, int(cx - base_r) - 2); x1 = min(w, int(cx + base_r) + 3)
        y0 = max(0, int(cy - base_r) - 2); y1 = min(h, int(cy + base_r) + 3)
        if x0 >= x1 or y0 >= y1:
            continue
        dx = xx[:, x0:x1] - cx; dy = yy[y0:y1, :] - cy
        ang = np.arctan2(dy, dx) - rot
        ang = np.mod(ang + np.pi, 2 * np.pi) - np.pi
        rad = np.hypot(dx, dy)
        keep = (np.abs(ang) < span).astype(np.float32)
        swag = np.zeros(rad.shape, dtype=np.float32)
        for k in range(1, rings + 1):
            rr = k * gap
            arc = np.clip(1.0 - np.abs(rad - rr) / (gap * 0.42 + 1e-4), 0, 1)
            swag = np.maximum(swag, arc * (0.55 + 0.45 * (k / rings)))
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], (swag * keep).astype(np.float32))
    bg = _multi_scale_noise_fast(shape, [8, 16, 32], int(seed) + 4209) * 0.09 + 0.05
    return np.clip(out + bg, 0.0, 1.0).astype(np.float32)
# ---- paint ----
def _paint_lfr_bunting_scallop(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None: pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1); s = pm * 0.9
    h, w = shape
    yy = np.arange(h, dtype=np.float32)[:, None]; xx = np.arange(w, dtype=np.float32)[None, :]
    sel = (np.sin(xx * 0.018 + (int(seed) % 13)) + np.cos(yy * 0.016 - (int(seed) % 7))) * 0.5
    red = pv * np.clip(0.6 - sel, 0, 1); blue = pv * np.clip(0.6 + sel, 0, 1)
    white = pv * np.clip(1.0 - np.abs(sel) * 2.0, 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + red * 0.72 * s * mask + white * 0.78 * s * mask - blue * 0.08 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] - red * 0.16 * s * mask + white * 0.78 * s * mask - blue * 0.04 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - red * 0.10 * s * mask + white * 0.82 * s * mask + blue * 0.80 * s * mask, 0, 1)
    return paint

# ---- texture ----
def _tex_lfr_distressed_flag(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 4301)
    wear = _multi_scale_noise_fast(shape, [3, 6, 12, 24], int(seed) + 4302)
    crack = np.zeros((h, w), dtype=np.float32); wsum = 0.0
    for sc, wt in [(8, 1.0), (16, 0.6), (32, 0.35), (64, 0.2)]:
        nz = _noise_simple(shape, seed=int(seed) + 4310 + sc, scale=float(sc))
        ridged = 1.0 - np.abs(2.0 * nz - 1.0)
        crack += np.power(ridged, 3.0) * wt; wsum += wt
    crack /= max(wsum, 1e-6)
    crack = np.clip((crack - 0.55) * 3.2, 0, 1)
    pin = (rng.random((h, w), dtype=np.float32) > 0.992).astype(np.float32)
    out = np.clip(wear * 0.72 + crack * 0.55 + pin * 0.6, 0, 1)
    return out.astype(np.float32)
# ---- paint ----
def _paint_lfr_distressed_flag(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None: pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1); s = pm * 0.85
    h, w = shape
    yy = np.arange(h, dtype=np.float32)[:, None]; xx = np.arange(w, dtype=np.float32)[None, :]
    region = np.sin(xx * 0.006 + (int(seed) % 11)) + np.sin(yy * 0.005 - (int(seed) % 5))
    red = np.clip(0.7 - region, 0, 1); blue = np.clip(0.7 + region, 0, 1)
    white = np.clip(1.0 - np.abs(region) * 1.4, 0, 1)
    fade = (0.35 + 0.65 * pv)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (red * 0.34 + white * 0.26 - blue * 0.06) * fade * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (white * 0.24 - red * 0.10 - blue * 0.02) * fade * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (blue * 0.34 + white * 0.22 - red * 0.08) * fade * s * mask, 0, 1)
    crack = np.clip((pv - 0.55) * 2.5, 0, 1)
    for c in range(3):
        paint[:, :, c] = np.clip(paint[:, :, c] - crack * 0.10 * s * mask, 0, 1)
    return paint

# ---- texture ----
def _tex_lfr_eagle_crest(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 4401)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    n = int(rng.integers(9, 14))
    for _ in range(n):
        cx = rng.uniform(0.0, 1.0) * w; cy = rng.uniform(0.0, 1.0) * h
        rot = rng.uniform(0.0, 2.0 * np.pi); R = rng.uniform(0.09, 0.17) * dim
        rays = int(rng.integers(7, 11)); spread = rng.uniform(1.6, 2.6)
        # PERF: env support is exactly rad < 1 (dist < R); heart at R is
        # exp(-30) — local window only.
        x0 = max(0, int(cx - R) - 2); x1 = min(w, int(cx + R) + 3)
        y0 = max(0, int(cy - R) - 2); y1 = min(h, int(cy + R) + 3)
        if x0 >= x1 or y0 >= y1:
            continue
        dx = xx[:, x0:x1] - cx; dy = yy[y0:y1, :] - cy
        ang = np.arctan2(dy, dx) - rot
        ang = np.mod(ang + np.pi, 2 * np.pi) - np.pi
        rad = np.hypot(dx, dy) / (R + 1e-4)
        feathers = np.power(np.clip(np.cos(ang * rays), 0, 1), 3.0)
        env = np.exp(-((np.abs(ang) - spread) ** 2) * 1.2) + np.exp(-(ang ** 2) * 0.6)
        env = np.clip(env, 0, 1) * np.clip(1.0 - rad, 0, 1)
        crest = feathers * env
        heart = np.exp(-(rad * 5.5) ** 2) * 1.0
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], np.clip(crest * 0.9 + heart, 0, 1).astype(np.float32))
    bg = _multi_scale_noise_fast(shape, [8, 16, 32], int(seed) + 4409) * 0.09 + 0.05
    return np.clip(out + bg, 0.0, 1.0).astype(np.float32)
# ---- paint ----
def _paint_lfr_eagle_crest(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None: pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1); s = pm * 0.95
    heart = np.clip((pv - 0.7) * 3.3, 0, 1)
    feather = np.clip((pv - 0.2) * 1.6, 0, 1) * (1 - heart)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + heart * 0.85 * s * mask + feather * 0.60 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + heart * 0.80 * s * mask + feather * 0.45 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + heart * 0.55 * s * mask - feather * 0.06 * s * mask, 0, 1)
    return paint

# ---- texture ----
def _tex_lfr_firework_radial(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 4501)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    n = int(rng.integers(6, 10))
    for _ in range(n):
        cx = rng.uniform(0.05, 0.95) * w; cy = rng.uniform(0.05, 0.95) * h
        R  = rng.uniform(0.12, 0.30) * dim; rays = int(rng.integers(18, 34))
        rot = rng.uniform(0, 2 * np.pi)
        # PERF: burst support is rn < 1; shell at rn = 1.5 is exp(-9.3)
        # (~1e-4) — evaluate the local window only. The full-grid spark
        # noise draw is kept so the rng sequence is unchanged.
        rr = R * 1.5 + 2.0
        x0 = max(0, int(cx - rr) - 2); x1 = min(w, int(cx + rr) + 3)
        y0 = max(0, int(cy - rr) - 2); y1 = min(h, int(cy + rr) + 3)
        dx = xx[:, x0:x1] - cx; dy = yy[y0:y1, :] - cy
        ang = np.arctan2(dy, dx); rad = np.hypot(dx, dy); rn = rad / (R + 1e-4)
        spokes = np.power(np.clip(np.cos((ang - rot) * rays) * 0.5 + 0.5, 0, 1), 4.0)
        falloff = np.clip(1.0 - rn, 0, 1) * np.exp(-(rn ** 2) * 0.6)
        burst = spokes * falloff
        core = np.exp(-(rn * 6.0) ** 2)
        shell = np.exp(-((rn - 0.85) ** 2) * 22.0)
        spark = (rng.random((h, w), dtype=np.float32)[y0:y1, x0:x1] > 0.985).astype(np.float32) * shell
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], np.clip(burst * 0.9 + core + spark * 0.8, 0, 1).astype(np.float32))
    bg = _multi_scale_noise_fast(shape, [8, 16], int(seed) + 4509) * 0.07 + 0.04
    return np.clip(out + bg, 0.0, 1.0).astype(np.float32)
# ---- paint ----
def _paint_lfr_firework_radial(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None: pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1); s = pm * 1.0
    core = np.clip((pv - 0.72) * 3.6, 0, 1)
    mid  = np.clip((pv - 0.35) * 2.4, 0, 1) * (1 - core)
    rim  = np.clip((pv - 0.12) * 1.4, 0, 1) * (1 - core - mid)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + core * 0.9 * s * mask + mid * 0.70 * s * mask - rim * 0.06 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + core * 0.9 * s * mask + mid * 0.32 * s * mask - rim * 0.02 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + core * 0.92 * s * mask - mid * 0.10 * s * mask + rim * 0.60 * s * mask, 0, 1)
    return paint

# ---- texture ----
def _tex_lfr_constellation_field(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 4601)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    npts = int(rng.integers(70, 110))
    pts = np.stack([rng.uniform(0, w, npts), rng.uniform(0, h, npts)], axis=1).astype(np.float32)
    mags = rng.uniform(0.35, 1.0, npts).astype(np.float32)
    order = np.argsort(pts[:, 0])
    for i in range(npts - 1):
        if rng.random() > 0.35: continue
        a = pts[order[i]]; b = pts[order[i + 1]]
        if np.hypot(*(a - b)) > 0.22 * dim: continue
        # PERF: line support is exactly d < dim*0.0035 — local window only.
        pad = dim * 0.0035 + 3.0
        x0 = max(0, int(min(a[0], b[0]) - pad)); x1 = min(w, int(max(a[0], b[0]) + pad) + 2)
        y0 = max(0, int(min(a[1], b[1]) - pad)); y1 = min(h, int(max(a[1], b[1]) + pad) + 2)
        if x0 >= x1 or y0 >= y1:
            continue
        xs = xx[:, x0:x1]; ys = yy[y0:y1, :]
        ab = b - a; L2 = float(ab[0] ** 2 + ab[1] ** 2) + 1e-6
        t = np.clip(((xs - a[0]) * ab[0] + (ys - a[1]) * ab[1]) / L2, 0, 1)
        px = a[0] + t * ab[0]; py = a[1] + t * ab[1]
        d = np.hypot(xs - px, ys - py)
        line = np.clip(1.0 - d / (dim * 0.0035), 0, 1) * 0.30
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], line.astype(np.float32))
    sig = max(1.0, dim * 0.006)
    for (sx, sy), m in zip(pts, mags):
        # PERF: glow tail at 4.3 sigma is < 1e-4 — local window only.
        pad = sig * (0.6 + float(m)) * 4.3 + 2.0
        x0 = max(0, int(sx - pad)); x1 = min(w, int(sx + pad) + 2)
        y0 = max(0, int(sy - pad)); y1 = min(h, int(sy + pad) + 2)
        if x0 >= x1 or y0 >= y1:
            continue
        d2 = (xx[:, x0:x1] - sx) ** 2 + (yy[y0:y1, :] - sy) ** 2
        glow = np.exp(-d2 / (2 * (sig * (0.6 + m)) ** 2)) * m
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], glow.astype(np.float32))
    bg = _multi_scale_noise_fast(shape, [16, 32], int(seed) + 4609) * 0.05 + 0.03
    return np.clip(out + bg, 0.0, 1.0).astype(np.float32)
# ---- paint ----
def _paint_lfr_constellation_field(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None: pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1); s = pm * 0.9
    star = np.clip((pv - 0.45) * 2.2, 0, 1)
    line = np.clip((pv - 0.12) * 2.0, 0, 1) * (1 - star)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + star * 0.80 * s * mask - line * 0.04 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + star * 0.84 * s * mask + line * 0.18 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + star * 0.95 * s * mask + line * 0.55 * s * mask, 0, 1)
    return paint

# ---- texture ----
def _tex_lfr_ribbon_weave(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 4701)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    g = rng.uniform(0.0, np.pi); skew = rng.uniform(-0.18, 0.18)
    ca, sa = np.cos(g), np.sin(g)
    cb, sb = np.cos(g + np.pi / 2 + skew), np.sin(g + np.pi / 2 + skew)
    u = (xx - w * 0.5) * ca + (yy - h * 0.5) * sa
    v = (xx - w * 0.5) * cb + (yy - h * 0.5) * sb
    period = max(18.0, dim * rng.uniform(0.05, 0.09)); ribbon_w = period * 0.62
    uu = np.abs(np.mod(u, period) - period * 0.5)
    vv = np.abs(np.mod(v, period) - period * 0.5)
    rib_u = np.power(np.clip(1.0 - uu / (ribbon_w * 0.5), 0, 1), 0.7)
    rib_v = np.power(np.clip(1.0 - vv / (ribbon_w * 0.5), 0, 1), 0.7)
    cu = np.floor(u / period); cv = np.floor(v / period)
    over_u = (np.mod(cu + cv, 2) < 0.5).astype(np.float32)
    weave = rib_u * over_u + rib_v * (1.0 - over_u)
    under = (rib_u * (1.0 - over_u) + rib_v * over_u) * 0.45
    return np.clip(np.maximum(weave, under), 0, 1).astype(np.float32)
# ---- paint ----
def _paint_lfr_ribbon_weave(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None: pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1); s = pm * 0.9
    h, w = shape
    yy = np.arange(h, dtype=np.float32)[:, None]; xx = np.arange(w, dtype=np.float32)[None, :]
    g = (int(seed) % 360) * np.pi / 180.0
    u = (xx * np.cos(g) + yy * np.sin(g)) * 0.02
    tri = np.mod(u + (int(seed) % 3), 3.0)
    red = pv * (np.abs(tri - 0.5) < 0.5).astype(np.float32)
    white = pv * (np.abs(tri - 1.5) < 0.5).astype(np.float32)
    blue = pv * (np.abs(tri - 2.5) < 0.5).astype(np.float32)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + red * 0.72 * s * mask + white * 0.78 * s * mask - blue * 0.08 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] - red * 0.16 * s * mask + white * 0.78 * s * mask - blue * 0.04 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] - red * 0.10 * s * mask + white * 0.82 * s * mask + blue * 0.82 * s * mask, 0, 1)
    return paint

# ---- texture (reuses shared _lfr_star_sdf) ----
def _tex_lfr_stencil_stars(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 4801)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    grain = _noise_simple(shape, seed=int(seed) + 4805, scale=60.0)
    n = int(rng.integers(22, 36))
    for _ in range(n):
        cx = rng.uniform(-0.03, 1.03) * w; cy = rng.uniform(-0.03, 1.03) * h
        R  = rng.uniform(0.03, 0.10) * dim; rot = rng.uniform(0, 2 * np.pi)
        # PERF: body support < 0.82R; halo tail at 2.25R is exp(-8.6)*0.5
        # (~9e-5, invisible) — evaluate the local window only.
        rr = R * 2.25 + 2.0
        x0 = max(0, int(cx - rr) - 2); x1 = min(w, int(cx + rr) + 3)
        y0 = max(0, int(cy - rr) - 2); y1 = min(h, int(cy + rr) + 3)
        if x0 >= x1 or y0 >= y1:
            continue
        xs = xx[:, x0:x1]; ys = yy[y0:y1, :]; gr_w = grain[y0:y1, x0:x1]
        body = (_lfr_star_sdf(xs, ys, cx, cy, R, rot, k=5) > 0.18).astype(np.float32)
        rad = np.hypot(xs - cx, ys - cy) / (R + 1e-4)
        halo = np.exp(-((rad - 1.05) ** 2) * 6.0) * (0.35 + 0.65 * gr_w)
        spray = np.clip(body * (0.85 + 0.15 * gr_w) + halo * 0.5, 0, 1)
        spray = np.clip(spray - (gr_w > 0.85).astype(np.float32) * body * 0.25, 0, 1)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], spray.astype(np.float32))
    bg = _multi_scale_noise_fast(shape, [8, 16, 32], int(seed) + 4809) * 0.08 + 0.05
    return np.clip(out + bg, 0.0, 1.0).astype(np.float32)
# ---- paint ----
def _paint_lfr_stencil_stars(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None: pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1); s = pm * 0.9
    body = np.clip((pv - 0.5) * 2.2, 0, 1)
    bleed = np.clip((pv - 0.18) * 1.6, 0, 1) * (1 - body)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + body * 0.78 * s * mask - bleed * 0.06 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + body * 0.78 * s * mask - bleed * 0.03 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + body * 0.82 * s * mask + bleed * 0.45 * s * mask, 0, 1)
    return paint

# ---- texture ----
def _tex_lfr_liberty_filigree(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 4901)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    line_w = max(1.0, dim * 0.0030)
    n = int(rng.integers(8, 13))
    for _ in range(n):
        cx = rng.uniform(0.05, 0.95) * w; cy = rng.uniform(0.05, 0.95) * h
        R  = rng.uniform(0.10, 0.20) * dim; rot = rng.uniform(0, 2 * np.pi)
        k = int(rng.choice([3, 4, 5, 6]))
        # PERF: rose support < R + line_w, spiral support < 1.2R — window.
        rr = max(R * 1.2, R + line_w * 1.3) + 2.0
        x0 = max(0, int(cx - rr) - 2); x1 = min(w, int(cx + rr) + 3)
        y0 = max(0, int(cy - rr) - 2); y1 = min(h, int(cy + rr) + 3)
        dx = xx[:, x0:x1] - cx; dy = yy[y0:y1, :] - cy
        ang = np.arctan2(dy, dx) - rot; rad = np.hypot(dx, dy)
        rose_r = R * np.abs(np.cos(k * ang))
        rose = np.clip(1.0 - np.abs(rad - rose_r) / line_w, 0, 1)
        a = R * rng.uniform(0.05, 0.12)
        b = rng.uniform(0.18, 0.30) * (1 if rng.random() > 0.5 else -1)
        turns = rng.uniform(1.5, 3.0)
        theta_u = np.mod(ang, 2 * np.pi)
        spi_r = a * np.exp(b * (theta_u + 2 * np.pi * np.floor(rad / (R + 1e-4) * turns)))
        spiral = np.clip(1.0 - np.abs(rad - spi_r) / (line_w * 1.3), 0, 1) * np.clip(1.0 - rad / (R * 1.2), 0, 1)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], np.maximum(rose, spiral).astype(np.float32))
    bg = _multi_scale_noise_fast(shape, [8, 16, 32], int(seed) + 4909) * 0.07 + 0.05
    return np.clip(out + bg, 0.0, 1.0).astype(np.float32)
# ---- paint ----
def _paint_lfr_liberty_filigree(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None: pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1); s = pm * 0.95
    line = np.clip((pv - 0.35) * 2.4, 0, 1)
    fill = np.clip((pv - 0.10) * 1.3, 0, 1) * (1 - line)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + line * 0.72 * s * mask - fill * 0.05 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + line * 0.58 * s * mask - fill * 0.02 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + line * 0.20 * s * mask + fill * 0.30 * s * mask, 0, 1)
    return paint

def _texture_lfr_dispatch(shape, mask, seed, sm, variant):
    if variant=='lfr_star_lattice':        return _pack(_tex_lfr_star_lattice(shape, seed),        R_range=-118.0, M_range=90.0)
    if variant=='lfr_stripe_drift':        return _pack(_tex_lfr_stripe_drift(shape, seed),        R_range=-95.0,  M_range=70.0)
    if variant=='lfr_bunting_scallop':     return _pack(_tex_lfr_bunting_scallop(shape, seed),     R_range=-100.0, M_range=80.0)
    if variant=='lfr_distressed_flag':     return _pack(_tex_lfr_distressed_flag(shape, seed),     R_range=85.0,   M_range=-45.0)
    if variant=='lfr_eagle_crest':         return _pack(_tex_lfr_eagle_crest(shape, seed),         R_range=-120.0, M_range=95.0)
    if variant=='lfr_firework_radial':     return _pack(_tex_lfr_firework_radial(shape, seed),     R_range=-150.0, M_range=120.0)
    if variant=='lfr_constellation_field': return _pack(_tex_lfr_constellation_field(shape, seed),  R_range=-108.0, M_range=85.0)
    if variant=='lfr_ribbon_weave':        return _pack(_tex_lfr_ribbon_weave(shape, seed),        R_range=-90.0,  M_range=75.0)
    if variant=='lfr_stencil_stars':       return _pack(_tex_lfr_stencil_stars(shape, seed),       R_range=70.0,   M_range=-30.0)
    if variant=='lfr_liberty_filigree':    return _pack(_tex_lfr_liberty_filigree(shape, seed),    R_range=-115.0, M_range=92.0)
    return _pack(_tex_lfr_star_lattice(shape, seed), R_range=-118.0, M_range=90.0)  # safe default

def _paint_lfr_dispatch(paint, shape, mask, seed, pm, bb, variant):
    m = {'lfr_star_lattice':_paint_lfr_star_lattice,'lfr_stripe_drift':_paint_lfr_stripe_drift,'lfr_bunting_scallop':_paint_lfr_bunting_scallop,'lfr_distressed_flag':_paint_lfr_distressed_flag,'lfr_eagle_crest':_paint_lfr_eagle_crest,'lfr_firework_radial':_paint_lfr_firework_radial,'lfr_constellation_field':_paint_lfr_constellation_field,'lfr_ribbon_weave':_paint_lfr_ribbon_weave,'lfr_stencil_stars':_paint_lfr_stencil_stars,'lfr_liberty_filigree':_paint_lfr_liberty_filigree}
    fn = m.get(variant)
    if fn is None:
        if paint.ndim==3 and paint.shape[2]>3: paint=paint[:,:,:3].copy()
        return paint[:,:,:3].astype(np.float32)
    return fn(paint, shape, mask, seed, pm, bb)

# === LET FREEDOM RING PATTERNS (lfr_*) 2026-06-09 END ===

# ─────────────────────────────────────────────────────────
# TEXTURE FUNCTIONS
# ─────────────────────────────────────────────────────────

def _texture_expansion(shape, mask, seed, sm, variant):
    e = _engine()
    h, w = shape

    # ── FLAMES (new — 10 unique implementations) ────────────────────────────────
    # Dispatched below after all flame texture helpers are defined.
    if variant.startswith("flame_"):
        return _texture_flame_dispatch(shape, mask, seed, sm, variant)

    # ── LET FREEDOM RING (10 patriotic patterns, 2026-06-09) ────────────────────
    if variant.startswith("lfr_"):
        return _texture_lfr_dispatch(shape, mask, seed, sm, variant)

    # ── 50s ─────────────────────────────────────────────
    if "50s_starburst" in variant:
        val = _radial_starburst(shape, 16, rotation=0.1)
        return _pack(val, -80, 80)
    if "50s_bullet" in variant:
        # Speed lines: decreasing horizontal stripes + bullet oval
        val = _stripe_horizontal(shape, 14).astype(np.float32)
        Y, X = _get_grid(shape)
        oval = np.clip(1 - (X + 0.5)**2 * 4 - Y**2 * 8, 0, 1)
        return _pack(np.maximum(val * 0.6, oval), -80, 60)
    if "50s_rocket" in variant:
        # Tall pointed nose cone + stabilizer fins — LAZY-EXPAND-007 FIX
        Y, X = _get_grid(shape)
        nose = np.exp(-((X)**2 * 18 + (Y + 0.3)**2 * 1.5))
        fin_l = np.exp(-((X + 0.2)**2 * 80 + (Y - 0.5)**2 * 8)) * (Y > 0.3).astype(np.float32)
        fin_r = np.exp(-((X - 0.2)**2 * 80 + (Y - 0.5)**2 * 8)) * (Y > 0.3).astype(np.float32)
        return _pack(np.clip(nose + fin_l + fin_r, 0, 1).astype(np.float32), -80, 60)
    if "50s_tailfin" in variant:
        Y, X = _get_grid(shape)
        fin = np.clip(1 - np.abs(Y - X * 0.7) * 4, 0, 1) * (X > -0.2).astype(np.float32)
        return _pack(fin, -80, 60)
    if "50s_boomerang" in variant:
        Y, X = _get_grid(shape)
        boom = np.clip(1 - np.abs(Y - X**2 * 0.8) * 5, 0, 1)
        return _pack(boom, -80, 60)
    if "50s_diner_curve" in variant:
        Y, X = _get_grid(shape)
        curve = np.clip(1 - np.abs(Y - np.sin(X * np.pi * 0.7) * 0.4) * 6, 0, 1)
        return _pack(curve, -60, 60)
    if "50s_scallop" in variant:
        val = _concentric_rings(shape, 5)
        val = (val > 0.5).astype(np.float32)
        return _pack(val, -60, 60)
    if "50s_classic_stripe" in variant:
        e2 = _engine()
        return e2.texture_pinstripe(shape, mask, seed, sm)
    if "50s_diamond" in variant:
        val = _checkerboard(shape, 10)
        return _pack(val, -60, 60)
    if "50s_chrome_line" in variant:
        Y, _ = _get_grid(shape)
        lines = (np.abs(Y) < 0.03).astype(np.float32) + (np.abs(Y - 0.4) < 0.02).astype(np.float32)
        return _pack(np.clip(lines, 0, 1), -120, 120)

    # ── 60s ─────────────────────────────────────────────
    if "60s_flower" in variant or "60s_petal" in variant or "woodstock" in variant:
        Y, X = _get_grid(shape)
        r = np.sqrt(X**2 + Y**2)
        a = np.arctan2(Y, X)
        petals = np.clip(np.cos(a * 6) * 0.5 + 0.5, 0, 1) * np.clip(1 - r * 1.2, 0, 1)
        return _pack(petals, -60, 60)
    if "60s_peace_curve" in variant:
        Y, X = _get_grid(shape)
        r = np.sqrt(X**2 + Y**2)
        ring = np.exp(-(r - 0.6)**2 / 0.008)
        vert = np.exp(-X**2 / 0.003) * (Y > -0.65).astype(np.float32)
        left = np.exp(-(Y - (-X + -0.6 * 0.0))**2 * 30) * (Y < 0).astype(np.float32)
        right = np.exp(-(Y - (X + -0.6 * 0.0))**2 * 30) * (Y < 0).astype(np.float32)
        val = np.clip(ring + vert + left + right, 0, 1)
        return _pack(val, -60, 60)
    if "60s_swirl" in variant:
        # Groovy swirl: angular warp around center → hypnotic spiral poster art
        Y2, X2 = _get_grid(shape)
        r = np.sqrt(X2**2 + Y2**2) + 1e-8
        angle = np.arctan2(Y2, X2)
        warp = r * np.pi * 5
        sx = r * np.cos(angle + warp)
        sy = r * np.sin(angle + warp)
        val = ((np.sin(sx * np.pi * 2.5 + sy * np.pi * 2.5) * 0.5 + 0.5) > 0.5).astype(np.float32)
        return _pack(val, -60, 60)
    if "60s_lavalamp" in variant:
        # Lava lamp: coarse organic blobs biased toward rising from below
        Y2, X2 = _get_grid(shape)
        val = _noise_simple(shape, seed, 1.3)
        y_pull = (-Y2 * 0.15).astype(np.float32)  # negative Y = top → more blobs risen upward
        val = (np.clip(val + y_pull, 0, 1) > 0.5).astype(np.float32)
        return _pack(val, -60, 60)
    if "60s_mod_stripe" in variant:
        # Mod stripe: 6 even horizontal stripes (classic 60s equal-band design)
        val = _stripe_horizontal(shape, 6)
        return _pack(val, -80, 80)
    if "60s_wide_stripe" in variant:
        # Wide stripe: bold 2:1 wide-to-narrow pairs (Carnaby Street / Twiggy era)
        h2, w2 = shape
        y_pos = np.arange(h2, dtype=np.float32)[:, None] / h2 * 6.0  # 3 pairs
        cycle = y_pos % 2.0
        val = (cycle < 1.33).astype(np.float32) * np.ones((h2, w2), dtype=np.float32)
        return _pack(val, -80, 80)
    if "60s_thin_stripe" in variant:
        val = _stripe_horizontal(shape, 16)
        return _pack(val, -80, 80)
    if "60s_opart_ray" in variant:
        val = _radial_starburst(shape, 24)
        return _pack(val, -120, 0)
    if "60s_gogo_check" in variant:
        val = _checkerboard(shape, 6)
        return _pack(val, -120, 0)

    # ── 70s ─────────────────────────────────────────────
    if "70s_disco" in variant or "70s_studio54" in variant:
        # Mirror ball: grid of squares with highlight
        h2, w2 = shape
        cell = max(4, min(h2, w2) // 14)
        val = np.zeros((h2, w2), dtype=np.float32)
        for gy in range(0, h2, cell):
            for gx in range(0, w2, cell):
                # Highlight in top-left of each cell
                val[gy:gy + cell//3, gx:gx + cell//3] = 1.0
        return _pack(val, -120, 100)

    if "70s_sparkle" in variant:
        val = _scatter_dots(shape, 60, 0.025, seed)
        # Add 4-point star shapes
        h2, w2 = shape
        rng = np.random.default_rng(seed)
        for _ in range(40):
            cx = int(rng.random() * w2)
            cy = int(rng.random() * h2)
            r = max(2, int(min(h2, w2) * 0.03))
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if abs(dx) + abs(dy) <= r:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w2 and 0 <= ny < h2:
                            val[ny, nx] = 1.0
        return _pack(np.clip(val, 0, 1), -100, 80)

    if "patchwork" in variant:
        # 70s patchwork: rough checkerboard blocks + noise for organic quilt feel
        val = _checkerboard(shape, 6) * 0.7 + _noise_simple(shape, seed, 8) * 0.3
        return _pack(np.clip(val, 0, 1), -60, 60)
    if "70s_wide_stripe" in variant or "70s_bicentennial" in variant:
        val = _stripe_horizontal(shape, 5)
        return _pack(val, -80, 80)
    if "70s_funk_zigzag" in variant:
        val = _stripe_diagonal(shape, 60, 5)
        return _pack(val, -80, 80)
    if "70s_bell_flare" in variant:
        Y, X = _get_grid(shape)
        flare = np.clip(np.abs(X) * 1.5 - np.abs(Y) + 0.3, 0, 1)
        return _pack(flare, -60, 60)
    if "70s_shag" in variant:
        val = _noise_simple(shape, seed, 20) * 0.7 + _stripe_diagonal(shape, 45, 30) * 0.3
        return _pack(np.clip(val, 0, 1), -40, 40)
    if "70s_earth_geo" in variant:
        # Earth geo: topographic contour steps — 70s geological poster aesthetic
        Y, X = _get_grid(shape)
        geo = np.sin(X * np.pi * 3 + Y * np.pi * 2) * 0.5 + 0.5
        n_levels = 6
        stepped = (np.floor(geo * n_levels) / n_levels).astype(np.float32)
        return _pack(stepped, -60, 60)
    if "70s_orange_curve" in variant:
        # Orange curve: single bold sinusoidal arch band (The Racing Stripe)
        Y, X = _get_grid(shape)
        arch = np.exp(-((Y - np.sin(X * np.pi * 0.7) * 0.4)**2) * 5)
        return _pack(np.clip(arch, 0, 1).astype(np.float32), -60, 60)

    # ── 80s ─────────────────────────────────────────────
    if "80s_neon_grid" in variant or "80s_neon_hex" in variant or "80s_outrun" in variant:
        h2, w2 = shape
        val = np.zeros((h2, w2), dtype=np.float32)
        horizon = int(h2 * 0.45)
        # Perspective grid lines
        for i in range(1, 12):
            vx = int(w2 / 2 + (i - 6) * w2 * 0.12)
            vy = horizon
            # Line from vanishing point to bottom
            for y in range(horizon, h2):
                prog = (y - horizon) / (h2 - horizon + 1)
                x = int(w2 / 2 + (vx - w2 / 2) * prog)
                if 0 <= x < w2:
                    val[y, max(0, x - 1):x + 2] = 1.0
        # Horizontal lines
        for i in range(1, 8):
            y = horizon + int((h2 - horizon) * (i / 8) ** 1.5)
            val[y, :] = 1.0
        return _pack(val, -120, 120)

    if "80s_memphis" in variant:
        val = _checkerboard(shape, 8) * 0.4 + _stripe_diagonal(shape, 30, 8) * 0.3
        val += _scatter_dots(shape, 30, 0.04, seed) * 0.8
        return _pack(np.clip(val, 0, 1), -80, 80)
    if "80s_angle" in variant or "80s_triangle" in variant or "my_little_friend" in variant or "yo_joe" in variant:
        val = _stripe_diagonal(shape, 45, 6)
        return _pack(val, -80, 80)
    if "80s_synth_sun" in variant:
        Y, X = _get_grid(shape)
        sun_mask = (Y < 0).astype(np.float32)
        stripes = _stripe_horizontal(shape, 12) * sun_mask
        circle = np.clip(1 - (X**2 + (Y + 0.1)**2) / 0.5, 0, 1)
        return _pack(np.clip(stripes * circle + circle * 0.2, 0, 1), -80, 80)
    if "acid_washed" in variant:
        # 80s acid wash denim: mottled noise field over fine diagonal grain
        val = _noise_simple(shape, seed, 5) * 0.65 + _stripe_diagonal(shape, 75, 12) * 0.35
        return _pack(np.clip(val, 0, 1), -50, 50)
    if "80s_bolt" in variant:
        e2 = _engine()
        return e2.texture_lightning(shape, mask, seed, sm)
    if "80s_pastel_zig" in variant:
        val = _stripe_diagonal(shape, 70, 8)
        return _pack(val, -60, 60)
    if "80s_vapor" in variant:
        # Smooth large-scale noise blobs — vaporwave soft gradients — LAZY-EXPAND-006 FIX
        val = _noise_simple(shape, seed, 1.0)
        return _pack(val, -60, 60)
    if "80s_pixel" in variant:
        # Clean 8-bit pixel checkerboard — LAZY-EXPAND-006 FIX
        val = _checkerboard(shape, 16).astype(np.float32)
        return _pack(val, -60, 60)

    # ── 90s ─────────────────────────────────────────────
    if "90s_grunge" in variant:
        val = _noise_simple(shape, seed, 12) * 0.6 + _scatter_dots(shape, 80, 0.03, seed) * 0.6
        return _pack(np.clip(val, 0, 1), -60, 40)
    if "90s_minimal_stripe" in variant or "90s_bold_stripe" in variant:
        val = _stripe_horizontal(shape, 3 if "bold" in variant else 8)
        return _pack(val, -80, 80)
    if "trolls" in variant:
        # Mottled organic blob field — troll doll wild texture — LAZY-EXPAND-008 FIX
        val = (_noise_simple(shape, seed, 1.8) > 0.4).astype(np.float32)
        return _pack(val, -60, 80)
    if "tama90s" in variant:
        # Bold wide drum-wrap stripes — LAZY-EXPAND-008 FIX
        val = _stripe_horizontal(shape, 4)
        return _pack(val, -80, 80)
    if "90s_alt_cross" in variant:
        Y, X = _get_grid(shape)
        cross = (np.abs(X) < 0.08).astype(np.float32) + (np.abs(Y) < 0.08).astype(np.float32)
        return _pack(np.clip(cross, 0, 1), -120, 0)
    if "90s_rave_zig" in variant:
        val = _stripe_diagonal(shape, 60, 10)
        return _pack(val, -100, 100)
    if "90s_chrome_bubble" in variant:
        val = _concentric_rings(shape, 3) * 0.5 + _scatter_dots(shape, 15, 0.08, seed) * 0.8
        return _pack(np.clip(val, 0, 1), -120, 120)
    if "90s_y2k" in variant:
        val = _scatter_dots(shape, 20, 0.06, seed) * 0.8 + _checkerboard(shape, 18) * 0.3
        return _pack(np.clip(val, 0, 1), -100, 100)
    if "90s_geo_minimal" in variant:
        val = _checkerboard(shape, 5) * 0.4 + _stripe_diagonal(shape, 90, 4) * 0.4
        return _pack(np.clip(val, 0, 1), -60, 60)
    if "90s_dot_matrix" in variant:
        val = _scatter_dots(shape, 150, 0.015, seed)
        return _pack(val, -80, 80)
    if "floppy_disk" in variant:
        # 90s floppy disk: grid of data blocks + central access slot
        Y2, X2 = _get_grid(shape)
        val = _checkerboard(shape, 10) * 0.4
        slot = np.clip(1 - np.abs(Y2) * 6, 0, 1) * (np.abs(X2) < 0.28).astype(np.float32)
        return _pack(np.clip(val + slot * 0.9, 0, 1), -80, 80)
    if "90s_indie" in variant:
        val = _noise_simple(shape, seed, 6) * 0.5 + _stripe_diagonal(shape, 20, 6) * 0.3
        return _pack(np.clip(val, 0, 1), -50, 50)

    # ── MUSIC ────────────────────────────────────────────
    if "music_lightning_bolt" in variant:
        e2 = _engine()
        return e2.texture_lightning(shape, mask, seed, sm)
    if "music_arrow_bold" in variant:
        # Tiled rightward chevrons — many small arrows across the canvas
        h_s, w_s = shape
        yy = np.arange(h_s, dtype=np.float32).reshape(-1, 1)
        xx = np.arange(w_s, dtype=np.float32).reshape(1, -1)
        cell = max(20, min(h_s, w_s) // 30)  # ~68px cells at 2048
        ly = (yy % cell) / cell * 2 - 1  # Local [-1,1] within each cell
        lx = (xx % cell) / cell * 2 - 1
        arrow = np.clip(0.15 - (np.abs(ly) - lx * 0.7), 0, 1) * (lx > -0.3).astype(np.float32)
        bg = _noise_simple(shape, seed=seed + 2150, scale=40.0) * 0.1 + 0.06
        arrow = np.clip(arrow + bg, 0, 1)
        return _pack(arrow.astype(np.float32), -100, 80)
    if "music_wing_sweep" in variant:
        Y, X = _get_grid(shape)
        # Wing: multiple sweep lines fanning from centre — finer detail
        wing = np.zeros_like(Y)
        for i in range(5):
            offset = (i - 2) * 0.12
            curve = 0.3 + i * 0.1
            w = np.clip(1.0 - np.abs(Y - X * curve + offset) * 12.0, 0, 1) * (X > -0.3).astype(np.float32)
            wing = np.maximum(wing, w * (0.6 + i * 0.08))
        bg = _noise_simple(shape, seed=seed + 2160, scale=40.0) * 0.10 + 0.06
        wing = np.clip(wing + bg, 0, 1)
        return _pack(wing.astype(np.float32), -100, 80)
    if "music_script_curve" in variant:
        Y, X = _get_grid(shape)
        script = np.exp(-(Y - np.sin(X * np.pi * 1.5) * 0.35) ** 2 / 0.012)
        bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2170) * 0.13 + 0.08
        script = np.clip(script + bg, 0, 1)
        return _pack(script, -60, 60)
    if "music_skull_abstract" in variant:
        e2 = _engine()
        if hasattr(e2, 'texture_skull'):
            result = e2.texture_skull(shape, mask, seed, sm)
            bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2180) * 0.13 + 0.08
            result["pattern_val"] = np.clip(result["pattern_val"] + bg, 0, 1)
            return result
        else:
            skull_val = _noise_simple(shape, seed, 8)
            bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2180) * 0.13 + 0.08
            skull_val = np.clip(skull_val + bg, 0, 1)
            return _pack(skull_val, -60, 40)
    if "music_star_burst" in variant:
        val = _radial_starburst(shape, 12)
        return _pack(val, -80, 80)
    if "music_circle_ring" in variant:
        val = _concentric_rings(shape, 6)
        return _pack(val, -80, 80)
    if "music_slash_bold" in variant:
        val = _stripe_diagonal(shape, 50, 4)
        return _pack(val, -100, 80)
    if "music_chain_heavy" in variant:
        e2 = _engine()
        return e2.texture_chainmail(shape, mask, seed, sm) if hasattr(e2, 'texture_chainmail') else _pack(_checkerboard(shape, 6), -60, 60)
    if "music_flame_ribbon" in variant:
        val = _flame_tongues(shape, 5, seed) * 0.7 + _stripe_diagonal(shape, 15, 3) * 0.3
        return _pack(np.clip(val, 0, 1), -140, 120)
    if "music_blues" in variant:
        # Blues: rolling sine-wave staff lines — notes flowing across (finer lines)
        Y2, X2 = _get_grid(shape)
        val = (np.sin(Y2 * np.pi * 14 + np.sin(X2 * np.pi * 4) * 1.2) * 0.5 + 0.5).astype(np.float32)
        return _pack(val, -80, 60)
    if "music_strat" in variant:
        # Stratocaster: contoured body curves + fret lines — denser for finer detail
        Y2, X2 = _get_grid(shape)
        c1 = np.exp(-(np.abs(Y2 - np.sin(X2 * np.pi * 2.0) * 0.3))**2 / 0.003)
        c2 = np.exp(-(np.abs(Y2 + np.sin(X2 * np.pi * 1.5) * 0.25))**2 / 0.003)
        c3 = np.exp(-(np.abs(Y2 * 0.8 - np.sin(X2 * np.pi * 2.5) * 0.2))**2 / 0.003)
        # Fret lines (vertical detail) — more frets
        frets = (np.sin(X2 * np.pi * 24) * 0.5 + 0.5) * 0.12
        return _pack(np.clip(c1 + c2 + c3 * 0.6 + frets, 0, 1).astype(np.float32), -100, 80)
    if "music_the_artist" in variant:
        # The Artist (Prince): ornate symbol — concentric rings with radiating wedges
        val = _concentric_rings(shape, 5) * 0.6 + _radial_starburst(shape, 8) * 0.4
        return _pack(np.clip(val, 0, 1), -100, 80)
    if "music_smilevana" in variant:
        # Nirvana smiley: face circle + X-dot eyes
        Y2, X2 = _get_grid(shape)
        r = np.sqrt(X2**2 + Y2**2)
        ring = np.exp(-(r - 0.55)**2 / 0.006)
        leye = np.exp(-((X2 + 0.22)**2 + (Y2 - 0.15)**2) / 0.004)
        reye = np.exp(-((X2 - 0.22)**2 + (Y2 - 0.15)**2) / 0.004)
        smiley = np.clip(ring + leye + reye, 0, 1)
        bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2190) * 0.13 + 0.08
        smiley = np.clip(smiley + bg, 0, 1)
        return _pack(smiley.astype(np.float32), -120, 80)
    if "music_licked" in variant:
        # KISS tongue: tiled downward-curved bands across canvas
        h_s, w_s = shape
        yy = np.arange(h_s, dtype=np.float32).reshape(-1, 1)
        xx = np.arange(w_s, dtype=np.float32).reshape(1, -1)
        cell = max(20, min(h_s, w_s) // 25)
        ly = (yy % cell) / cell * 2 - 1
        lx = (xx % cell) / cell * 2 - 1
        tongue = np.exp(-(lx**2 * 8 + (ly + 0.1 + lx**2 * 0.5)**2 * 4))
        bg = _noise_simple(shape, seed=seed + 2200, scale=40.0) * 0.1 + 0.06
        tongue = np.clip(tongue + bg, 0, 1)
        return _pack(tongue.astype(np.float32), -120, 80)

    # ── ASTRO ────────────────────────────────────────────
    if "astro_moon_phases" in variant:
        h2, w2 = shape
        val = np.zeros((h2, w2), dtype=np.float32)
        phases = 4
        for i in range(phases):
            cx = int(w2 * (i + 0.5) / phases)
            cy = h2 // 2
            r = min(h2, w2) // (phases * 2 + 1)
            Y2, X2 = np.ogrid[:h2, :w2]
            circle = ((X2 - cx)**2 + (Y2 - cy)**2 <= r**2).astype(np.float32)
            # Shadow offset to create phase
            offset = int(r * (i - 1.5) * 0.8)
            shadow = ((X2 - cx - offset)**2 + (Y2 - cy)**2 <= r**2).astype(np.float32)
            moon = np.clip(circle - shadow, 0, 1)
            val = np.maximum(val, moon)
        return _pack(val, -60, 60)

    if "astro_stars_constellation" in variant or "astro_cosmic_dust" in variant:
        val = _scatter_dots(shape, 120, 0.018, seed)
        # Connecting lines (simplified)
        h2, w2 = shape
        rng = np.random.default_rng(seed)
        stars = [(int(rng.random() * h2), int(rng.random() * w2)) for _ in range(12)]
        for i in range(len(stars) - 1):
            y1, x1 = stars[i]
            y2, x2 = stars[i + 1]
            n_pts = max(abs(y2 - y1), abs(x2 - x1))
            for t in range(n_pts):
                py = int(y1 + (y2 - y1) * t / max(n_pts, 1))
                px = int(x1 + (x2 - x1) * t / max(n_pts, 1))
                if 0 <= py < h2 and 0 <= px < w2:
                    val[py, px] = 0.4
        return _pack(np.clip(val, 0, 1), -60, 60)

    if "astro_sun_rays" in variant:
        val = _radial_starburst(shape, 20)
        Y, X = _get_grid(shape)
        r = np.sqrt(X**2 + Y**2)
        sun = np.clip(1 - r * 1.5, 0, 1)
        return _pack(np.maximum(val * np.clip(1 - r, 0, 1), sun), -80, 80)

    if "astro_orbital_rings" in variant:
        Y, X = _get_grid(shape)
        val = np.zeros_like(X)
        for ri, tilt in enumerate([0.3, 0.5, 0.15, 0.08]):
            r_target = 0.25 + ri * 0.2
            r_eff = np.sqrt(X**2 + (Y / (tilt + 0.5))**2)
            ring = np.exp(-((r_eff - r_target) ** 2) / 0.0015)
            val = np.maximum(val, ring)
        return _pack(np.clip(val, 0, 1), -80, 80)

    if "astro_comet_trail" in variant:
        Y, X = _get_grid(shape)
        head = np.clip(1 - (X**2 + Y**2) * 8, 0, 1)
        trail = np.exp(-((Y)**2 / 0.03)) * np.clip(-X * 2, 0, 1)
        return _pack(np.clip(head + trail * 0.6, 0, 1), -60, 60)

    if "astro_galaxy_swirl" in variant:
        Y, X = _get_grid(shape)
        r = np.sqrt(X**2 + Y**2) + 1e-8
        a = np.arctan2(Y, X)
        # Logarithmic spiral: phi = a + b*ln(r)
        spiral = np.exp(-((a - np.log(r + 0.5) * 3) % (2 * np.pi) - np.pi) ** 2 / 0.2)
        val = np.clip(spiral * np.clip(1 - r, 0, 1) * 2, 0, 1)
        return _pack(val.astype(np.float32), -80, 80)

    # Zodiac signs
    for sign in ('aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo',
                 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces'):
        if f'zodiac_{sign}' in variant:
            val = _zodiac_glyph(shape, sign)
            # Tile glyph across surface
            h2, w2 = shape
            tiled = np.tile(val, (2, 2))[:h2, :w2]
            return _pack(tiled, -120, 0)

    # ── HERO / SPORT ─────────────────────────────────────
    if "hero_crest_curve" in variant:
        Y, X = _get_grid(shape)
        # Arch: crest curve at top
        arch = np.clip(1 - np.abs(Y - (-X**2 * 0.6 + 0.3)) * 14.0, 0, 1)  # Fine arch line (was *3.5 = fat band)
        bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2210) * 0.13 + 0.08
        arch = np.clip(arch + bg, 0, 1)
        return _pack(arch, -80, 80)
    if "hero_scallop_edge" in variant:
        # Batman-ish scalloped lower edge — dense small scallops
        h2, w2 = shape
        val = np.zeros((h2, w2), dtype=np.float32)
        n_scallops = 28  # Many small scallops (was 7 = huge circles)
        for i in range(n_scallops):
            cx = int(w2 * (i + 0.5) / n_scallops)
            cy = int(h2 * 0.62)
            r = int(w2 / (n_scallops * 2))
            Y2, X2 = np.ogrid[:h2, :w2]
            scallop = ((X2 - cx)**2 + (Y2 - cy)**2 <= r**2).astype(np.float32)
            val = np.maximum(val, scallop)
        bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2220) * 0.13 + 0.08
        val = np.clip(val + bg, 0, 1)
        return _pack(val, -120, 0)
    if "hero_pointed_cowl" in variant:
        Y, X = _get_grid(shape)
        # Two pointed upward triangles like bat ears
        # Wider cowl points with body fill
        left_ear = np.clip(1.3 - np.abs(X + 0.35) * 5 - np.abs(Y + 0.4) * 2.5, 0, 1) * (Y < 0.0).astype(np.float32)
        right_ear = np.clip(1.3 - np.abs(X - 0.35) * 5 - np.abs(Y + 0.4) * 2.5, 0, 1) * (Y < 0.0).astype(np.float32)
        # Add brow ridge connecting the ears
        brow = np.clip(1.0 - np.abs(Y + 0.15) * 8, 0, 1) * np.clip(1.0 - np.abs(X) / 0.55, 0, 1) * 0.6
        cowl = np.clip(left_ear + right_ear + brow, 0, 1)
        bg = _multi_scale_noise_fast(shape, [4, 8, 16, 32], seed + 2230) * 0.13 + 0.08
        cowl = np.clip(cowl + bg, 0, 1)
        return _pack(cowl, -120, 0)
    if "sport_stadium_line" in variant:
        val = _stripe_diagonal(shape, 80, 7)
        return _pack(val, -80, 80)
    if "sport_team_stripe" in variant:
        val = _stripe_horizontal(shape, 4)
        return _pack(val, -100, 100)

    # Fallback
    e2 = _engine()
    return e2.texture_ripple(shape, mask, seed, sm)


# ─────────────────────────────────────────────────────────
# PAINT FUNCTIONS
# ─────────────────────────────────────────────────────────

def _paint_expansion(paint, shape, mask, seed, pm, bb, variant):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    e = _engine()
    seed_off = hash(variant) % 10000

    # Flames → dedicated flame gradient paint
    if variant.startswith("flame_"):
        return _paint_flame(paint, shape, mask, seed, pm, bb, variant)

    # Let Freedom Ring → dedicated patriotic palette paints
    if variant.startswith("lfr_"):
        return _paint_lfr_dispatch(paint, shape, mask, seed, pm, bb, variant)

    # Decades
    if variant.startswith("decade_"):
        if any(k in variant for k in ("starburst", "rocket", "bullet", "tailfin", "boomerang",
                                       "scallop", "diner", "diamond", "chrome_line",
                                       "classic_stripe")):
            try:
                return e.paint_chevron_contrast(paint, shape, mask, seed + seed_off, pm, bb)
            except Exception:
                return e.paint_pinstripe(paint, shape, mask, seed + seed_off, pm, bb)

        if any(k in variant for k in ("flower", "petal", "peace", "swirl", "lavalamp",
                                       "orange_curve", "earth_geo", "woodstock", "patchwork")):
            try:
                return e.paint_wave_shimmer(paint, shape, mask, seed + seed_off, pm, bb)
            except Exception:
                return e.paint_ripple_reflect(paint, shape, mask, seed + seed_off, pm, bb)

        if any(k in variant for k in ("opart", "gogo", "vapor", "pixel", "geo_minimal",
                                       "chrome_bubble", "floppy_disk")):
            try:
                return e.paint_interference_shift(paint, shape, mask, seed + seed_off, pm, bb)
            except Exception:
                return e.paint_ripple_reflect(paint, shape, mask, seed + seed_off, pm, bb)

        if any(k in variant for k in ("disco", "studio54", "sparkle", "dot_matrix")):
            try:
                return e.paint_stardust_sparkle(paint, shape, mask, seed + seed_off, pm, bb)
            except Exception:
                return e.paint_coarse_flake(paint, shape, mask, seed + seed_off, pm, bb)

        if any(k in variant for k in ("neon_grid", "neon_hex", "outrun", "y2k", "synth_sun")):
            return e.paint_tron_glow(paint, shape, mask, seed + seed_off, pm, bb)

        if "grunge" in variant or "indie" in variant or "shag" in variant or "acid_washed" in variant:
            try:
                return e.paint_scratch_marks(paint, shape, mask, seed + seed_off, pm, bb)
            except Exception:
                return e.paint_static_noise_grain(paint, shape, mask, seed + seed_off, pm, bb)

        if "bolt" in variant:
            return e.paint_lightning_glow(paint, shape, mask, seed + seed_off, pm, bb)

        return e.paint_ripple_reflect(paint, shape, mask, seed + seed_off, pm, bb)

    # Music
    if variant.startswith("music_"):
        if any(k in variant for k in ("lightning_bolt", "slash_bold", "star_burst", "arrow_bold")):
            return e.paint_lightning_glow(paint, shape, mask, seed + seed_off, pm, bb)
        if any(k in variant for k in ("wing_sweep", "script_curve", "flame_ribbon",
                                       "blues", "strat")):
            try:
                return e.paint_wave_shimmer(paint, shape, mask, seed + seed_off, pm, bb)
            except Exception:
                return e.paint_lava_glow(paint, shape, mask, seed + seed_off, pm, bb)
        if "skull_abstract" in variant:
            try:
                return e.paint_skull_darken(paint, shape, mask, seed + seed_off, pm, bb)
            except Exception:
                return e.paint_ripple_reflect(paint, shape, mask, seed + seed_off, pm, bb)
        if "circle_ring" in variant:
            return e.paint_ripple_reflect(paint, shape, mask, seed + seed_off, pm, bb)
        if "chain_heavy" in variant:
            try:
                return e.paint_chainmail_emboss(paint, shape, mask, seed + seed_off, pm, bb)
            except Exception:
                return e.paint_hex_emboss(paint, shape, mask, seed + seed_off, pm, bb)
        return e.paint_lightning_glow(paint, shape, mask, seed + seed_off, pm, bb)

    # Astro
    if variant.startswith("astro_"):
        if any(k in variant for k in ("stars", "cosmic", "comet", "galaxy")):
            try:
                return e.paint_stardust_sparkle(paint, shape, mask, seed + seed_off, pm, bb)
            except Exception:
                return e.paint_coarse_flake(paint, shape, mask, seed + seed_off, pm, bb)
        if "sun_rays" in variant:
            return e.paint_lightning_glow(paint, shape, mask, seed + seed_off, pm, bb)
        # Zodiac signs
        if "zodiac" in variant:
            try:
                return e.paint_celtic_emboss(paint, shape, mask, seed + seed_off, pm, bb)
            except Exception:
                return e.paint_ripple_reflect(paint, shape, mask, seed + seed_off, pm, bb)
        return e.paint_ripple_reflect(paint, shape, mask, seed + seed_off, pm, bb)

    # Hero / Sport
    if variant.startswith("hero_") or variant.startswith("sport_"):
        try:
            return e.paint_chevron_contrast(paint, shape, mask, seed + seed_off, pm, bb)
        except Exception:
            return e.paint_pinstripe(paint, shape, mask, seed + seed_off, pm, bb)

    return e.paint_lava_glow(paint, shape, mask, seed + seed_off, pm, bb)


# ─────────────────────────────────────────────────────────
# REACTIVE SHIMMER PATTERN TEXTURES
# ─────────────────────────────────────────────────────────
# These 10 patterns are engineered specifically for Pattern-Reactive and
# Pattern-Pop blend modes. Each produces a float32 gradient mask 0.0→1.0
# where:
#   0.0 = full primary base material visible
#   1.0 = full secondary base (chrome/candy) visible
#   0.0–1.0 = specular interplay zone (iridescence lives here)
#
# Design rules for maximum shimmer effect:
#   • Keep most pixels 0.0–0.3 (let primary breathe through)
#   • Create sharp luminous peaks at 0.8–1.0 (specular hotspots)
#   • Smooth gradients between 0 and 1 (no hard edges)

# Reactive shimmer field cache: avoids recomputing the same heavy pattern field
# multiple times in one session (preview + render often reuse same seed/shape).
_REACTIVE_FIELD_CACHE = OrderedDict()
_REACTIVE_FIELD_CACHE_MAX = 24


def _cache_reactive_field(variant, shape, seed, builder):
    h, w = int(shape[0]), int(shape[1])
    key = (str(variant), h, w, int(seed))
    cached = _REACTIVE_FIELD_CACHE.get(key)
    if cached is not None:
        # LRU touch
        _REACTIVE_FIELD_CACHE.move_to_end(key)
        return cached
    val = builder()
    _REACTIVE_FIELD_CACHE[key] = val
    _REACTIVE_FIELD_CACHE.move_to_end(key)
    while len(_REACTIVE_FIELD_CACHE) > _REACTIVE_FIELD_CACHE_MAX:
        _REACTIVE_FIELD_CACHE.popitem(last=False)
    return val

def _reactive_iridescent_flake(shape, seed=0):
    """Scattered metallic flakes at random orientations — Voronoi-cell flake boundaries
    with per-cell brightness variation. Each flake is a polygonal facet with its own
    reflective intensity, separated by dark boundary gaps."""
    h, w = shape
    rng = np.random.default_rng(seed)
    # Dense Voronoi tessellation simulating individual metallic flakes
    n_flakes = 180 + rng.integers(0, 60)
    pts_y = rng.random(n_flakes).astype(np.float32) * h
    pts_x = rng.random(n_flakes).astype(np.float32) * w
    # Per-flake brightness (random orientation catching light differently)
    flake_bright = rng.uniform(0.15, 1.0, size=n_flakes).astype(np.float32)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    # Find nearest and second-nearest for each pixel
    d1 = np.full((h, w), np.inf, dtype=np.float32)
    d2 = np.full((h, w), np.inf, dtype=np.float32)
    nearest_id = np.zeros((h, w), dtype=np.int32)
    for i, (cy, cx) in enumerate(zip(pts_y, pts_x)):
        d = np.sqrt((yy - cy)**2 + (xx - cx)**2)
        update = d < d1
        d2 = np.where(update, d1, np.minimum(d2, d))
        nearest_id = np.where(update, i, nearest_id)
        d1 = np.minimum(d1, d)
    # Edge detection: thin dark boundary between flakes
    edge_width = d2 - d1
    edge_norm = np.clip(edge_width / (np.percentile(edge_width, 85) + 1e-8), 0, 1)
    boundary = np.power(edge_norm, 0.6).astype(np.float32)  # sharp boundary falloff
    # Map each pixel to its flake brightness
    cell_val = flake_bright[nearest_id]
    # Add micro-sparkle variation within each flake (sub-flake glitter)
    sparkle_phase_y = rng.uniform(0, 100, size=n_flakes)
    sparkle_phase_x = rng.uniform(0, 100, size=n_flakes)
    micro = np.zeros((h, w), dtype=np.float32)
    for i in range(min(n_flakes, 80)):
        fmask = nearest_id == i
        if not np.any(fmask):
            continue
        local_sparkle = (np.sin(yy * 0.7 + sparkle_phase_y[i]) *
                         np.cos(xx * 0.9 + sparkle_phase_x[i]) * 0.5 + 0.5).astype(np.float32)
        micro = np.where(fmask, local_sparkle * 0.25, micro)
    out = cell_val * boundary + micro
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return np.clip(out, 0, 1).astype(np.float32)


def _reactive_pearl_shift(shape, seed=0):
    """Pearlescent color-shift with smooth flowing luminance bands that wrap around
    curves. Large-scale gradient waves using warped domain coordinates for organic
    flow. No straight sine lines — everything curves and undulates."""
    h, w = shape
    Y, X = _get_grid(shape)
    rng = np.random.default_rng(seed)
    # Domain warping: displace coordinates with low-frequency noise for organic flow
    warp_x1 = _noise_simple(shape, seed=seed + 7, scale=2.5) * 0.6
    warp_y1 = _noise_simple(shape, seed=seed + 13, scale=2.8) * 0.6
    warp_x2 = _noise_simple(shape, seed=seed + 31, scale=1.8) * 0.35
    warp_y2 = _noise_simple(shape, seed=seed + 47, scale=2.0) * 0.35
    Xw = X + warp_x1 + warp_x2
    Yw = Y + warp_y1 + warp_y2
    # Three large-scale luminance bands at different orientations through warped space
    band1 = (np.sin(Xw * np.pi * 3.2 + Yw * np.pi * 1.1) * 0.5 + 0.5).astype(np.float32)
    band2 = (np.sin(Yw * np.pi * 2.7 - Xw * np.pi * 0.8) * 0.5 + 0.5).astype(np.float32)
    band3 = (np.cos((Xw + Yw) * np.pi * 1.9) * 0.5 + 0.5).astype(np.float32)
    # Blend bands with smooth max (pearlescent shimmer = brightest of overlapping bands)
    pearl = np.maximum(band1 * 0.45, np.maximum(band2 * 0.35, band3 * 0.20))
    # Add subtle broad luminance wash
    wash = _noise_simple(shape, seed=seed + 61, scale=1.2) * 0.3
    out = pearl + wash
    # Smooth S-curve contrast for that deep pearl look
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    out = 0.5 - np.cos(out * np.pi) * 0.5  # S-curve
    out = np.power(out, 0.75).astype(np.float32)
    return np.clip(out, 0, 1)


def _reactive_candy_depth(shape, seed=0):
    """Deep candy paint with visible depth layers — multiple transparent tinted
    layers stacked to create parallax-like depth illusion. Simulates looking through
    3-4 semi-transparent candy coat layers, each with its own pattern offset."""
    h, w = shape
    Y, X = _get_grid(shape)
    rng = np.random.default_rng(seed)
    # Simulate 4 candy depth layers at different "heights" with parallax offset
    layers = []
    for layer_i in range(4):
        # Each layer has its own spatial offset (parallax) and pattern
        ox = rng.uniform(-0.15, 0.15)
        oy = rng.uniform(-0.15, 0.15)
        Xl = X + ox * (layer_i + 1)
        Yl = Y + oy * (layer_i + 1)
        # Each layer uses a different organic pattern
        if layer_i == 0:
            # Bottom layer: broad smooth blobs (deep)
            warp = _noise_simple(shape, seed=seed + layer_i * 100, scale=2.0) * 0.4
            pat = (np.sin((Xl * 2.5 + warp) * np.pi) * 0.5 + 0.5).astype(np.float32)
        elif layer_i == 1:
            # Second layer: flowing curves
            r = np.sqrt(Xl**2 + Yl**2)
            pat = (np.sin(r * np.pi * 4.0 + Xl * np.pi * 2.0) * 0.5 + 0.5).astype(np.float32)
        elif layer_i == 2:
            # Third layer: diagonal streaks
            warp = _noise_simple(shape, seed=seed + 200, scale=3.0) * 0.3
            pat = (np.sin((Xl * 3.0 + Yl * 2.0 + warp) * np.pi * 1.8) * 0.5 + 0.5).astype(np.float32)
        else:
            # Top layer: fine cloudy detail
            pat = _noise_simple(shape, seed=seed + 300, scale=5.0)
        # Transparency per layer (deeper = more opaque, top = sheer)
        alpha = 0.8 - layer_i * 0.15
        layers.append(pat * alpha)
    # Stack layers with multiplicative candy effect (deeper = darker, luminous spots shine through)
    combined = np.ones((h, w), dtype=np.float32)
    for layer in layers:
        combined *= (0.3 + layer * 0.7)  # each layer filters light through
    combined = (combined - combined.min()) / (combined.max() - combined.min() + 1e-8)
    # Gamma push for candy depth look (dark midtones, bright hotspots)
    out = np.power(combined, 1.8).astype(np.float32)
    return np.clip(out, 0, 1)


def _reactive_chrome_veil(shape, seed=0):
    """Ultra-thin chrome membrane draped over surface — smooth reflective pools with
    sharp fold lines at edges. Like chrome-dipped fabric or liquid metal draping."""
    h, w = shape
    Y, X = _get_grid(shape)
    rng = np.random.default_rng(seed)
    # Create a smooth "draped fabric" height field using domain-warped low-freq noise
    warp1 = _noise_simple(shape, seed=seed + 3, scale=2.2)
    warp2 = _noise_simple(shape, seed=seed + 19, scale=3.1)
    Xw = X + warp1 * 0.45
    Yw = Y + warp2 * 0.45
    # Smooth height field (the "fabric")
    fabric = _noise_simple(shape, seed=seed + 37, scale=1.8)
    fabric += _noise_simple(shape, seed=seed + 53, scale=3.5) * 0.4
    fabric = (fabric - fabric.min()) / (fabric.max() - fabric.min() + 1e-8)
    # Chrome reflection = gradient magnitude of height field (folds catch light, flats are dark)
    # Compute numerical gradient
    gy = np.zeros_like(fabric)
    gx = np.zeros_like(fabric)
    gy[1:-1, :] = (fabric[2:, :] - fabric[:-2, :]) * 0.5
    gx[:, 1:-1] = (fabric[:, 2:] - fabric[:, :-2]) * 0.5
    grad_mag = np.sqrt(gy**2 + gx**2)
    grad_mag = (grad_mag - grad_mag.min()) / (grad_mag.max() - grad_mag.min() + 1e-8)
    # Chrome = smooth pools (low gradient = bright mirror) + sharp folds (high gradient = dark crease)
    chrome = 1.0 - grad_mag
    # Add specular highlights: sharp bright peaks on the smoothest areas
    smooth_mask = np.power(chrome, 3.0)
    # Directional anisotropic sheen on the pools (horizontal bias like real chrome)
    sheen = (np.sin(Yw * np.pi * 6.0 + Xw * np.pi * 0.8) * 0.5 + 0.5).astype(np.float32)
    out = chrome * 0.6 + smooth_mask * 0.25 + sheen * 0.15
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    # Hard contrast push: chrome is either very bright or very dark
    out = np.where(out > 0.45, np.power((out - 0.45) / 0.55, 0.5) * 0.6 + 0.4,
                   out * 0.4 / 0.45).astype(np.float32)
    return np.clip(out, 0, 1)


def _reactive_spectra_ripple(shape, seed=0):
    """Spectral dispersion ripples — like light through a prism hitting water.
    Concentric ring interference with rainbow-edge separation. Multiple wave sources
    create complex interference with thin bright fringes."""
    h, w = shape
    Y, X = _get_grid(shape)
    rng = np.random.default_rng(seed)
    # 5 wave emission sources at random positions (more than before, different approach)
    n_sources = 5
    sx = rng.uniform(-0.6, 0.6, size=n_sources)
    sy = rng.uniform(-0.6, 0.6, size=n_sources)
    freqs = rng.uniform(10.0, 25.0, size=n_sources)
    # Each source emits concentric waves; interference = sum of wave amplitudes
    wave_field = np.zeros((h, w), dtype=np.float32)
    for i in range(n_sources):
        r = np.sqrt((X - sx[i])**2 + (Y - sy[i])**2)
        # Each source has slightly different wavelength (spectral dispersion)
        wave = np.sin(r * np.pi * freqs[i]).astype(np.float32)
        wave_field += wave
    # Normalize the raw interference
    wave_field = (wave_field - wave_field.min()) / (wave_field.max() - wave_field.min() + 1e-8)
    # Create thin bright fringe lines from the interference pattern
    # Use derivative of the wave field to find constructive interference edges
    fringe = np.abs(np.sin(wave_field * np.pi * 6.0)).astype(np.float32)
    # Apply spectral dispersion: slightly offset the fringe for "rainbow edge" effect
    disp_r = np.roll(fringe, 2, axis=1)  # red channel shifted right
    disp_b = np.roll(fringe, -2, axis=1)  # blue channel shifted left
    # Combine into luminance with chromatic edge hints
    out = fringe * 0.5 + disp_r * 0.25 + disp_b * 0.25
    # Sharpen fringes: thin bright lines on dark background
    out = np.power(out, 1.5).astype(np.float32)
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return np.clip(out, 0, 1)


def _reactive_micro_weave(shape, seed=0):
    """Microscopic woven fiber structure — tight crosshatch at pixel scale with
    directional sheen. Over/under thread interlocking with per-thread brightness
    variation creating fabric-like directional reflection."""
    h, w = shape
    rng = np.random.default_rng(seed)
    # Thread spacing: very tight (pixel-level weave)
    thread_pitch = 3 + rng.integers(0, 2)  # 3-4 pixel thread pitch
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    # Warp (vertical) threads and weft (horizontal) threads
    warp_phase = (yy[:, None] % (thread_pitch * 2)) / (thread_pitch * 2)
    weft_phase = (xx[None, :] % (thread_pitch * 2)) / (thread_pitch * 2)
    # Thread profile: rounded (like real fiber cross-section)
    warp_profile = np.sin(warp_phase * np.pi * 2).astype(np.float32)
    weft_profile = np.sin(weft_phase * np.pi * 2).astype(np.float32)
    # Over/under interlocking: alternate which thread is on top
    cell_y = (np.arange(h)[:, None] // thread_pitch) % 2
    cell_x = (np.arange(w)[None, :] // thread_pitch) % 2
    on_top = (cell_y ^ cell_x).astype(np.float32)
    # Weave: visible thread depends on which is on top
    weave = np.where(on_top > 0.5, np.abs(warp_profile), np.abs(weft_profile))
    # Per-thread brightness variation (different fiber lots/dye)
    thread_y_id = np.arange(h)[:, None] // thread_pitch
    thread_x_id = np.arange(w)[None, :] // thread_pitch
    n_threads_y = h // thread_pitch + 1
    n_threads_x = w // thread_pitch + 1
    bright_y = rng.uniform(0.6, 1.0, size=n_threads_y).astype(np.float32)
    bright_x = rng.uniform(0.6, 1.0, size=n_threads_x).astype(np.float32)
    thread_bright = np.where(on_top > 0.5,
                             bright_y[np.clip(thread_y_id, 0, n_threads_y - 1)],
                             bright_x[np.clip(thread_x_id, 0, n_threads_x - 1)])
    # Directional sheen: horizontal bias (warp threads shimmer differently than weft)
    Y_norm, X_norm = _get_grid(shape)
    sheen = (np.sin(Y_norm * np.pi * 1.5) * 0.5 + 0.5).astype(np.float32) * 0.15
    out = weave * thread_bright * 0.85 + sheen
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return np.clip(out, 0, 1).astype(np.float32)


def _reactive_depth_cell(shape, seed=0):
    """Deep cellular structure like looking through frosted glass at honeycomb below.
    Hexagonal grid with Gaussian blur depth-of-field — cells have soft bright centers,
    blurred edges, and slight random displacement for organic feel."""
    h, w = shape
    rng = np.random.default_rng(seed)
    # Build hex grid with random displacement
    hex_pitch = max(20, min(h, w) // 16)
    rows = int(h / (hex_pitch * 0.866)) + 2
    cols = int(w / hex_pitch) + 2
    cell_centers = []
    for r in range(rows):
        for c in range(cols):
            cy = r * hex_pitch * 0.866
            cx = c * hex_pitch + (hex_pitch * 0.5 if r % 2 else 0)
            # Organic displacement
            cy += rng.uniform(-hex_pitch * 0.15, hex_pitch * 0.15)
            cx += rng.uniform(-hex_pitch * 0.15, hex_pitch * 0.15)
            cell_centers.append((cy, cx))
    pts_y = np.array([c[0] for c in cell_centers], dtype=np.float32)
    pts_x = np.array([c[1] for c in cell_centers], dtype=np.float32)
    n_cells = len(cell_centers)
    # Per-cell brightness (frosted glass depth variation)
    cell_bright = rng.uniform(0.3, 1.0, size=n_cells).astype(np.float32)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    d_min = np.full((h, w), np.inf, dtype=np.float32)
    nearest_id = np.zeros((h, w), dtype=np.int32)
    for i, (cy, cx) in enumerate(zip(pts_y, pts_x)):
        d = np.sqrt((yy - cy)**2 + (xx - cx)**2)
        update = d < d_min
        nearest_id = np.where(update, i, nearest_id)
        d_min = np.where(update, d, d_min)
    # Cell interior: Gaussian-like falloff from center (depth-of-field blur)
    sigma = hex_pitch * 0.4
    cell_glow = np.exp(-0.5 * (d_min / sigma)**2).astype(np.float32)
    # Map cell brightness
    out = cell_glow * cell_bright[nearest_id]
    # Add frosted glass diffusion: low-freq noise overlay
    frost = _noise_simple(shape, seed=seed + 71, scale=2.0) * 0.15
    out = out + frost
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    # Soft gamma for frosted-glass look
    out = np.power(out, 0.8).astype(np.float32)
    return np.clip(out, 0, 1)


def _reactive_shimmer_mist(shape, seed=0):
    """Fine atmospheric shimmer — heat haze + morning mist with embedded sparkle.
    Soft Gaussian cloud layer with bright pinpoint stars scattered through.
    Two distinct visual elements: soft haze base + hard sparkle points."""
    h, w = shape
    rng = np.random.default_rng(seed)
    # Layer 1: Soft Gaussian cloud base (atmospheric haze)
    cloud = np.zeros((h, w), dtype=np.float32)
    n_clouds = 30 + rng.integers(0, 15)
    for _ in range(n_clouds):
        cy = rng.random() * h
        cx = rng.random() * w
        sigma_y = rng.uniform(h * 0.05, h * 0.2)
        sigma_x = rng.uniform(w * 0.05, w * 0.2)
        intensity = rng.uniform(0.15, 0.45)
        yy = np.arange(h, dtype=np.float32)[:, None]
        xx = np.arange(w, dtype=np.float32)[None, :]
        g = np.exp(-0.5 * (((yy - cy) / sigma_y)**2 + ((xx - cx) / sigma_x)**2))
        cloud += g.astype(np.float32) * intensity
    cloud = np.clip(cloud, 0, 1)
    # Layer 2: Sharp sparkle points (pinpoint stars)
    sparkle = np.zeros((h, w), dtype=np.float32)
    n_stars = int(h * w * 0.0015)
    star_y = np.clip((rng.random(n_stars) * h).astype(int), 0, h - 1)
    star_x = np.clip((rng.random(n_stars) * w).astype(int), 0, w - 1)
    star_bright = rng.uniform(0.6, 1.0, size=n_stars).astype(np.float32)
    sparkle[star_y, star_x] = star_bright
    # Tiny 3x3 cross bloom on brightest stars
    n_bloom = min(n_stars, int(n_stars * 0.3))
    for i in range(n_bloom):
        sy, sx = int(star_y[i]), int(star_x[i])
        bv = star_bright[i] * 0.4
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = sy + dy, sx + dx
            if 0 <= ny < h and 0 <= nx < w:
                sparkle[ny, nx] = max(sparkle[ny, nx], bv)
    # Combine: mist base with sparkle overlay
    out = cloud * 0.55 + sparkle * 0.45
    # Heat-haze distortion hint: subtle wavy modulation
    Y, X = _get_grid(shape)
    haze = (np.sin(Y * np.pi * 8.0 + X * np.pi * 0.5) * 0.5 + 0.5).astype(np.float32) * 0.08
    out = out + haze
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return np.clip(out, 0, 1).astype(np.float32)


def _reactive_oil_slick(shape, seed=0):
    """Thin-film oil interference — classic rainbow oil-on-water. Irregular shaped
    pools with continuous luminance cycling within each pool. Uses Voronoi pools
    with smooth thickness-gradient inside each, producing interference bands."""
    h, w = shape
    Y, X = _get_grid(shape)
    rng = np.random.default_rng(seed)
    # Create irregular oil pools via Voronoi with organic warped coordinates
    warp = _noise_simple(shape, seed=seed + 5, scale=2.5) * 0.3
    Xw = X + warp
    Yw = Y + _noise_simple(shape, seed=seed + 11, scale=2.8) * 0.3
    n_pools = 18 + rng.integers(0, 8)
    pool_x = rng.uniform(-1.0, 1.0, size=n_pools).astype(np.float32)
    pool_y = rng.uniform(-1.0, 1.0, size=n_pools).astype(np.float32)
    # Per-pool "film thickness" base and gradient direction
    pool_thickness_base = rng.uniform(0.0, 1.0, size=n_pools).astype(np.float32)
    pool_grad_angle = rng.uniform(0, 2 * np.pi, size=n_pools).astype(np.float32)
    pool_grad_strength = rng.uniform(0.5, 2.0, size=n_pools).astype(np.float32)
    # Find nearest pool for each pixel
    d_min = np.full((h, w), np.inf, dtype=np.float32)
    nearest = np.zeros((h, w), dtype=np.int32)
    for i in range(n_pools):
        d = np.sqrt((Yw - pool_y[i])**2 + (Xw - pool_x[i])**2)
        update = d < d_min
        nearest = np.where(update, i, nearest)
        d_min = np.where(update, d, d_min)
    # Within each pool, thickness varies by position (gradient creates interference bands)
    thickness = np.zeros((h, w), dtype=np.float32)
    for i in range(n_pools):
        pmask = nearest == i
        if not np.any(pmask):
            continue
        a = pool_grad_angle[i]
        local_grad = (Yw * np.cos(a) + Xw * np.sin(a)) * pool_grad_strength[i]
        thickness = np.where(pmask, pool_thickness_base[i] + local_grad, thickness)
    # Thin-film interference: sinusoidal color cycling based on film thickness
    # Multiple harmonics for realistic rainbow banding
    interf = (np.sin(thickness * np.pi * 8.0) * 0.35 +
              np.sin(thickness * np.pi * 12.5) * 0.25 +
              np.sin(thickness * np.pi * 18.0) * 0.15 + 0.5).astype(np.float32)
    # Darken pool edges (oil thins at boundaries)
    edge_dark = np.clip(d_min * 3.0, 0, 1)
    edge_factor = np.power(1.0 - np.clip(edge_dark, 0, 0.3) / 0.3, 2.0)
    out = interf * (0.7 + edge_factor * 0.3)
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return np.clip(out, 0, 1).astype(np.float32)


def _reactive_wave_moire(shape, seed=0):
    """Moire interference from two overlapping wave grids at slightly different
    angles — classic moire beating pattern. Uses two high-frequency line grids
    with angular offset to produce large-scale interference diamonds/lozenges."""
    h, w = shape
    Y, X = _get_grid(shape)
    rng = np.random.default_rng(seed)
    # Grid 1: high-frequency parallel lines at angle A
    freq = 28.0 + rng.uniform(-3.0, 3.0)
    angle_a = rng.uniform(3.0, 12.0)  # degrees
    a1 = np.deg2rad(angle_a)
    proj1 = X * np.cos(a1) + Y * np.sin(a1)
    grid1 = (np.sin(proj1 * np.pi * freq) * 0.5 + 0.5).astype(np.float32)
    # Grid 2: same frequency, slightly different angle (moire requires small delta)
    angle_b = angle_a + rng.uniform(4.0, 8.0)  # offset by 4-8 degrees
    a2 = np.deg2rad(angle_b)
    proj2 = X * np.cos(a2) + Y * np.sin(a2)
    grid2 = (np.sin(proj2 * np.pi * freq) * 0.5 + 0.5).astype(np.float32)
    # Grid 3: third grid at perpendicular-ish angle for 2D moire (not just 1D)
    angle_c = angle_a + 90.0 + rng.uniform(-5.0, 5.0)
    a3 = np.deg2rad(angle_c)
    proj3 = X * np.cos(a3) + Y * np.sin(a3)
    freq3 = freq * rng.uniform(0.95, 1.05)
    grid3 = (np.sin(proj3 * np.pi * freq3) * 0.5 + 0.5).astype(np.float32)
    # Classic moire: multiply grids (interference beating)
    moire_ab = grid1 * grid2
    moire_full = moire_ab * 0.65 + grid3 * moire_ab * 0.35
    # Extract the low-frequency beating envelope
    # Smooth the moire to reveal the interference diamonds
    # Simple box-blur approximation via cumulative sum
    k = max(3, min(h, w) // 80)
    padded = np.pad(moire_full, k, mode='reflect')
    cs = np.cumsum(np.cumsum(padded, axis=0), axis=1)
    envelope = (cs[2*k:, 2*k:] - cs[2*k:, :-2*k] - cs[:-2*k, 2*k:] + cs[:-2*k, :-2*k]) / (2*k)**2
    envelope = envelope[:h, :w]
    # Blend sharp moire with smooth envelope for visual depth
    out = moire_full * 0.6 + envelope * 0.4
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    # Slight contrast push
    out = np.power(out, 0.85).astype(np.float32)
    return np.clip(out, 0, 1)


# ─────────────────────────────────────────────────────────
# REACTIVE PAINT FUNCTIONS — one unique paint per variant
# ─────────────────────────────────────────────────────────

def _paint_reactive_iridescent_flake(paint, shape, mask, seed, pm, bb):
    """Metallic flake paint: per-flake hue micro-shift + specular sparkle boost."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    rng = np.random.RandomState(seed)
    # Compute flake pattern for paint modulation
    pv = _reactive_iridescent_flake((h, w), seed=seed)
    # Per-pixel hue micro-rotation proportional to flake brightness
    hue_shift = (pv - 0.5) * 0.12 * pm  # subtle hue rotation
    # Approximate hue shift via channel rotation: R->G->B->R
    r, g, b = p[:, :, 0], p[:, :, 1], p[:, :, 2]
    cos_h = np.cos(hue_shift * np.pi * 2).astype(np.float32)
    sin_h = np.sin(hue_shift * np.pi * 2).astype(np.float32)
    lum = (r + g + b) / 3.0
    nr = lum + (r - lum) * cos_h + (g - b) * sin_h * 0.577
    ng = lum + (g - lum) * cos_h + (b - r) * sin_h * 0.577
    nb = lum + (b - lum) * cos_h + (r - g) * sin_h * 0.577
    # Specular sparkle: brighten the hot flake spots
    sparkle_boost = np.power(pv, 2.0) * pm * 40.0
    nr = nr + sparkle_boost
    ng = ng + sparkle_boost
    nb = nb + sparkle_boost
    result = np.stack([nr, ng, nb], axis=-1)
    return np.clip(result, 0, 255).astype(np.float32)


def _paint_reactive_pearl_shift(paint, shape, mask, seed, pm, bb):
    """Pearlescent paint: smooth luminance-driven warm/cool color shift."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    pv = _reactive_pearl_shift((h, w), seed=seed)
    # Pearl shift: warm tones in bright areas, cool tones in dark areas
    warm = pv * pm  # 0-1 range scaled by blend strength
    r_shift = warm * 15.0   # warm = more red
    b_shift = (1.0 - warm) * 10.0 * pm  # cool = more blue
    p[:, :, 0] = p[:, :, 0] + r_shift - b_shift * 0.3
    p[:, :, 1] = p[:, :, 1] + warm * 5.0  # slight green warmth
    p[:, :, 2] = p[:, :, 2] + b_shift - r_shift * 0.3
    # Luminance modulation: pearl bands brighten and darken
    lum_mod = (pv - 0.5) * pm * 25.0
    p += lum_mod[:, :, np.newaxis]
    return np.clip(p, 0, 255).astype(np.float32)


def _paint_reactive_candy_depth(paint, shape, mask, seed, pm, bb):
    """Candy depth paint: deep saturation boost in cell centers, darkened edges."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    pv = _reactive_candy_depth((h, w), seed=seed)
    # Candy effect: saturate and darken proportionally to depth
    lum = (p[:, :, 0] + p[:, :, 1] + p[:, :, 2]) / 3.0
    # In dark regions (low pv = cell edges), darken paint
    darken = (1.0 - pv) * pm * 0.4
    p *= (1.0 - darken)[:, :, np.newaxis]
    # In bright regions (high pv = cell centers), boost saturation
    sat_boost = (pv * pm * 0.5)[:, :, np.newaxis]
    p[:, :, :3] = lum[:, :, np.newaxis] + (p[:, :, :3] - lum[:, :, np.newaxis]) * (1.0 + sat_boost)
    return np.clip(p, 0, 255).astype(np.float32)


def _paint_reactive_chrome_veil(paint, shape, mask, seed, pm, bb):
    """Chrome veil paint: mirror-like reflection blending toward white in smooth
    pools and dark in fold creases."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    pv = _reactive_chrome_veil((h, w), seed=seed)
    # Chrome: blend toward pure white in reflective areas, desaturate everywhere
    chrome_white = pv * pm * 80.0
    # Desaturate proportionally (chrome is mostly achromatic)
    lum = (p[:, :, 0] + p[:, :, 1] + p[:, :, 2]) / 3.0
    desat = (pm * 0.6 * pv)[:, :, np.newaxis]
    cw3 = chrome_white[:, :, np.newaxis]
    p[:, :, :3] = p[:, :, :3] * (1.0 - desat) + lum[:, :, np.newaxis] * desat + cw3
    # Darken creases (low pv areas)
    crease_dark = (1.0 - pv) * pm * 0.3
    p *= (1.0 - crease_dark)[:, :, np.newaxis]
    return np.clip(p, 0, 255).astype(np.float32)


def _paint_reactive_spectra_ripple(paint, shape, mask, seed, pm, bb):
    """Spectral ripple paint: prismatic color fringing along interference fringes."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    pv = _reactive_spectra_ripple((h, w), seed=seed)
    # Map pattern value to spectral hue (rainbow mapping along fringe position)
    # R peaks at pv~0.0 and 1.0, G peaks at pv~0.33, B peaks at pv~0.67
    r_spec = np.clip(np.abs(pv - 0.0) * 3.0, 0, 1) * 0.5 + np.clip(np.abs(pv - 1.0) * 3.0, 0, 1) * 0.5
    g_spec = np.clip(1.0 - np.abs(pv - 0.33) * 3.0, 0, 1)
    b_spec = np.clip(1.0 - np.abs(pv - 0.67) * 3.0, 0, 1)
    strength = pm * 30.0
    p[:, :, 0] += r_spec * strength
    p[:, :, 1] += g_spec * strength
    p[:, :, 2] += b_spec * strength
    return np.clip(p, 0, 255).astype(np.float32)


def _paint_reactive_micro_weave(paint, shape, mask, seed, pm, bb):
    """Micro weave paint: directional darkening along thread valleys with cross-thread
    highlight at intersections."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    pv = _reactive_micro_weave((h, w), seed=seed)
    # Thread valleys darken, crossings brighten
    valley_dark = (1.0 - pv) * pm * 0.35
    cross_bright = np.power(pv, 2.5) * pm * 20.0
    p *= (1.0 - valley_dark)[:, :, np.newaxis]
    p += cross_bright[:, :, np.newaxis]
    # Slight directional tint: warm horizontal threads, cool vertical
    thread_pitch = 3
    cell_y = (np.arange(h)[:, None] // thread_pitch) % 2
    cell_x = (np.arange(w)[None, :] // thread_pitch) % 2
    on_top = (cell_y ^ cell_x).astype(np.float32)
    warm_tint = on_top * pm * 5.0
    p[:, :, 0] += warm_tint
    p[:, :, 2] -= warm_tint * 0.5
    return np.clip(p, 0, 255).astype(np.float32)


def _paint_reactive_depth_cell(paint, shape, mask, seed, pm, bb):
    """Depth cell paint: cells appear to glow from within with edge shadow bevel."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    pv = _reactive_depth_cell((h, w), seed=seed)
    # Cell centers: warm inner glow (slight orange/amber tint)
    glow = np.power(pv, 1.5) * pm
    p[:, :, 0] += glow * 18.0   # warm red
    p[:, :, 1] += glow * 10.0   # warm green
    p[:, :, 2] += glow * 3.0    # minimal blue
    # Cell edges: darken and desaturate (shadow bevel)
    edge_shadow = (1.0 - pv) * pm * 0.45
    p *= (1.0 - edge_shadow)[:, :, np.newaxis]
    return np.clip(p, 0, 255).astype(np.float32)


def _paint_reactive_shimmer_mist(paint, shape, mask, seed, pm, bb):
    """Shimmer mist paint: sparkle points get white-hot highlights, haze areas
    get soft luminance lift."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    pv = _reactive_shimmer_mist((h, w), seed=seed)
    # Sparkle points (high pv): white-hot highlight
    sparkle_mask = np.power(np.clip(pv - 0.5, 0, 1) * 2.0, 2.0)
    white_hot = sparkle_mask * pm * 100.0
    p += white_hot[:, :, np.newaxis]
    # Haze areas (low-mid pv): soft blue-white atmospheric lift
    haze = np.clip(pv * 2.0, 0, 1) * (1.0 - sparkle_mask)
    p[:, :, 0] += haze * pm * 6.0
    p[:, :, 1] += haze * pm * 8.0
    p[:, :, 2] += haze * pm * 12.0  # slight blue fog tint
    return np.clip(p, 0, 255).astype(np.float32)


def _paint_reactive_oil_slick(paint, shape, mask, seed, pm, bb):
    """Oil slick paint: continuous rainbow color cycling mapped to film thickness
    interference bands."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    pv = _reactive_oil_slick((h, w), seed=seed)
    # Thin-film interference rainbow: cycle through R->Y->G->C->B->M->R
    phase = pv * np.pi * 2.0
    r_oil = (np.sin(phase) * 0.5 + 0.5).astype(np.float32)
    g_oil = (np.sin(phase + np.pi * 2.0 / 3.0) * 0.5 + 0.5).astype(np.float32)
    b_oil = (np.sin(phase + np.pi * 4.0 / 3.0) * 0.5 + 0.5).astype(np.float32)
    strength = pm * 35.0
    p[:, :, 0] += r_oil * strength
    p[:, :, 1] += g_oil * strength
    p[:, :, 2] += b_oil * strength
    # Slight darkening in "thin film" transition zones
    transition = np.abs(np.sin(pv * np.pi * 6.0)).astype(np.float32)
    p *= (1.0 - (1.0 - transition) * pm * 0.12)[:, :, np.newaxis]
    return np.clip(p, 0, 255).astype(np.float32)


def _paint_reactive_wave_moire(paint, shape, mask, seed, pm, bb):
    """Wave moire paint: alternating warm/cool tint in moire interference diamonds
    with luminance modulation."""
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    pv = _reactive_wave_moire((h, w), seed=seed)
    # Warm/cool alternation mapped to moire pattern
    warm_zone = pv * pm
    cool_zone = (1.0 - pv) * pm
    p[:, :, 0] += warm_zone * 15.0 - cool_zone * 5.0
    p[:, :, 1] += warm_zone * 3.0 + cool_zone * 3.0
    p[:, :, 2] += cool_zone * 15.0 - warm_zone * 5.0
    # Luminance modulation: diamonds brighten and darken
    lum_mod = (pv - 0.5) * pm * 20.0
    p += lum_mod[:, :, np.newaxis]
    return np.clip(p, 0, 255).astype(np.float32)


# ─────────────────────────────────────────────────────────
# MICRO SHIMMER: 10 DISTINCT STRUCTURAL FAMILIES (no shared geometry).
# Each uses a different recipe: Voronoi, hex, FBM, anisotropic, radial bands,
# circular rings, binary weave, point sprites, log-spiral, distance-to-lines.
# ─────────────────────────────────────────────────────────

def _shimmer_quantum_shard(shape, seed=0):
    """VORONOI FACETS: random cell centers, per-cell random brightness, dark edges.
    Uses scipy cKDTree for O(n log n) nearest-neighbor queries. Resolution-capped for speed."""
    h, w = shape
    rng = np.random.default_rng(seed)
    # Resolution-cap: Voronoi at 1024 max for better edge detail
    MAX_DIM = 1024
    ds = max(1, min(h, w) // MAX_DIM)
    ch, cw = max(64, h // ds), max(64, w // ds)
    n_pts = 200 + rng.integers(0, 80)
    pts_y = (rng.random(n_pts).astype(np.float32) * 2.0 - 1.0)
    pts_x = (rng.random(n_pts).astype(np.float32) * 2.0 - 1.0)
    cell_bright = rng.uniform(0.25, 1.0, size=n_pts).astype(np.float32)
    pts = np.column_stack([pts_y, pts_x])
    tree = cKDTree(pts)
    yy = np.linspace(-1, 1, ch, dtype=np.float32)
    xx = np.linspace(-1, 1, cw, dtype=np.float32)
    grid_y, grid_x = np.meshgrid(yy, xx, indexing='ij')
    coords = np.column_stack([grid_y.ravel(), grid_x.ravel()])
    dists, ids = tree.query(coords, k=2)
    d_min = dists[:, 0].reshape(ch, cw).astype(np.float32)
    d_second = dists[:, 1].reshape(ch, cw).astype(np.float32)
    nearest_id = ids[:, 0].reshape(ch, cw)
    edge = np.clip((d_second - d_min) * 12.0, 0.0, 1.0)
    out = (1.0 - edge) * cell_bright[nearest_id]
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    out = np.clip(out, 0.0, 1.0).astype(np.float32)
    if (ch, cw) != (h, w):
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
    return out


def _shimmer_prism_frost(shape, seed=0):
    """HEX LATTICE: deterministic hex tiling, per-cell value from (iu,iv) hash — no sine grid."""
    Y, X = _get_grid(shape)
    hex_scale = 28.0
    u = (2.0 / 3.0) * X * hex_scale
    v = (-1.0 / 3.0 * X + 0.57735026919 * Y) * hex_scale
    iu = np.floor(u).astype(np.int32)
    iv = np.floor(v).astype(np.int32)
    fu = u - iu.astype(np.float32)
    fv = v - iv.astype(np.float32)
    # Deterministic per-cell value: hash(iu, iv, seed) -> [0.2, 1.0]
    h = ((iu * 31 + iv * 17 + seed) % 101) / 100.0
    cell_val = (h.astype(np.float32) * 0.8 + 0.2)
    # Soften by distance to hex edge (fu, fv in [0,1])
    edge_dist = np.minimum(np.minimum(fu, 1.0 - fu), np.minimum(fv, 1.0 - fv))
    out = cell_val * np.clip(edge_dist * 4.0 + 0.2, 0.0, 1.0)
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _shimmer_velvet_static(shape, seed=0):
    """Velvet Static: multi-scale noise FBM — fine grain like velvet fabric texture.
    All scales HIGH for small features (20-60px at 2048)."""
    n1 = _noise_simple(shape, seed=seed + 31, scale=30.0)   # ~68px features at 2048
    n2 = _noise_simple(shape, seed=seed + 32, scale=50.0)   # ~41px
    n3 = _noise_simple(shape, seed=seed + 33, scale=80.0)   # ~26px
    n4 = _noise_simple(shape, seed=seed + 34, scale=120.0)  # ~17px (finest)
    n5 = _noise_simple(shape, seed=seed + 35, scale=60.0)   # ~34px
    v = n1 * 0.25 + n2 * 0.25 + n3 * 0.20 + n4 * 0.15 + n5 * 0.15
    v = (v - v.min()) / (v.max() - v.min() + 1e-8)
    return np.power(np.clip(v, 0.0, 1.0), 1.05).astype(np.float32)  # Less dampening (was 1.2)


def _shimmer_chrome_flux(shape, seed=0):
    """Chrome Flux: liquid metal flow — fine organic chrome/matte patches.
    HIGH frequency noise = small features (20-60px at 2048). Like brushed metal grain."""
    h, w = shape
    # _noise_simple: scale = max sinusoid cycles across canvas
    # scale=40 = up to 40 cycles → ~50px features at 2048
    # scale=80 = up to 80 cycles → ~25px features at 2048
    flow1 = _noise_simple(shape, seed=seed + 41, scale=40.0)
    flow2 = _noise_simple(shape, seed=seed + 42, scale=60.0)
    grain = _noise_simple(shape, seed=seed + 43, scale=100.0)
    out = flow1 * 0.45 + flow2 * 0.35 + grain * 0.20
    # Strong contrast for visible chrome/matte differentiation
    out = np.clip((out - 0.25) * 2.5, 0.0, 1.0)
    return out.astype(np.float32)


def _shimmer_matte_halo(shape, seed=0):
    """Matte Halo: fine-grained matte/gloss cloudy patches — strong contrast bands.
    HIGH frequency noise = small features (20-60px at 2048)."""
    h, w = shape
    # _noise_simple: scale=50 → ~40px features, scale=80 → ~25px features at 2048
    n1 = _noise_simple(shape, seed=seed + 51, scale=50.0)  # Full 0-1 range
    n2 = _noise_simple(shape, seed=seed + 52, scale=80.0)
    n3 = _noise_simple(shape, seed=seed + 53, scale=30.0)  # Larger cloud layer
    # Quantize into sharp matte/gloss zones with visible transitions
    levels = 5.0
    banded = np.floor(n1 * levels) / (levels - 1.0)  # Spread to full 0-1
    frac = (n1 * levels) % 1.0
    smooth_edge = np.clip(frac * 5.0, 0, 1) * np.clip((1.0 - frac) * 5.0, 0, 1)
    v = banded * 0.7 + smooth_edge * 0.15 + n2 * 0.15 + n3 * 0.10
    # Stretch to full range
    v_min, v_max = float(v.min()), float(v.max())
    if v_max > v_min:
        v = (v - v_min) / (v_max - v_min)
    return np.clip(v, 0.0, 1.0).astype(np.float32)


def _shimmer_oil_tension(shape, seed=0):
    """Oil Tension: thin-film iridescence — fine warped rainbow bands like oil on water.
    HIGH frequency noise warp + tight band period = small intricate features."""
    h, w = shape
    dim = min(h, w)
    yy = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    # Fine warp via _noise_simple: scale=60 → ~34px distortion features at 2048
    warp_y = _noise_simple(shape, seed=seed + 61, scale=60.0) * 15.0
    warp_x = _noise_simple(shape, seed=seed + 62, scale=60.0) * 10.0
    # Tight band period — many thin color bands
    period = max(4, dim // 120)  # ~17px at 2048 — very fine bands
    flow = ((yy + warp_y + xx * 0.1 + warp_x * 0.2) / period * np.pi * 2)
    # Sawtooth = rainbow thin-film look
    phase = (flow % (2 * np.pi)) / (2 * np.pi)
    v = phase.astype(np.float32)
    return np.clip(v, 0.0, 1.0).astype(np.float32)


def _shimmer_neon_weft(shape, seed=0):
    """BINARY WEAVE: discrete horizontal and vertical bands, XOR — no sine."""
    h, w = shape
    yy = np.arange(h, dtype=np.float32)[:, None] / max(h, 1)
    xx = np.arange(w, dtype=np.float32)[None, :] / max(w, 1)
    freq = 52.0
    h_band = (np.floor(yy * freq) % 2).astype(np.float32)
    v_band = (np.floor(xx * freq) % 2).astype(np.float32)
    v = (h_band + v_band) % 2.0
    # Slight soften so it's not aliased
    v = v + _noise_simple(shape, seed=seed + 71, scale=80.0) * 0.06
    return np.clip(v, 0.0, 1.0).astype(np.float32)


def _shimmer_void_dust(shape, seed=0):
    """Void Dust: dense fine sparkle field covering entire canvas.
    3-layer approach: fine pixel dust (thousands) + medium sparkles + bright stars.
    Scales with canvas size so it looks detailed at 2048×2048."""
    h, w = shape
    rng = np.random.default_rng(seed)
    dim = min(h, w)
    out = np.zeros((h, w), dtype=np.float32)

    # Layer 1: Fine pixel dust — thousands of 1-2px bright pixels (fast, vectorized)
    n_fine = int(h * w * 0.008)  # 0.8% of pixels = ~33K at 2048 — DOUBLED for density
    fine_y = rng.integers(0, h, n_fine)
    fine_x = rng.integers(0, w, n_fine)
    fine_bright = rng.uniform(0.20, 0.65, n_fine).astype(np.float32)  # Brighter range
    out[fine_y, fine_x] = np.maximum(out[fine_y, fine_x], fine_bright)
    # Slight blur to make dust 2px wide instead of single pixels
    out = cv2.GaussianBlur(out, (3, 3), 0.8)

    # Layer 2: Medium sparkle particles — canvas-scaled sizes
    n_medium = max(200, int(dim * dim / 5000))
    for _ in range(n_medium):
        sy = rng.integers(0, h)
        sx = rng.integers(0, w)
        brightness = rng.uniform(0.3, 0.8)
        size = rng.uniform(0.001, 0.004) * dim  # Scale to canvas (2-8px at 2048)
        m = int(size * 2.5) + 1
        y0, y1 = max(0, sy - m), min(h, sy + m)
        x0, x1 = max(0, sx - m), min(w, sx + m)
        if y1 <= y0 or x1 <= x0:
            continue
        ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
        lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
        sparkle = np.exp(-((lx - sx)**2 + (ly - sy)**2) / (2 * max(0.5, size)**2)) * brightness
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], sparkle)

    # Layer 3: Bright stars with cross-spike diffraction (fewer, larger, dramatic)
    n_bright = max(15, int(dim / 60))
    for _ in range(n_bright):
        sy = rng.integers(0, h)
        sx = rng.integers(0, w)
        brightness = rng.uniform(0.7, 1.0)
        core_r = rng.uniform(0.002, 0.006) * dim
        spike_len = core_r * rng.uniform(3, 6)
        # Core glow
        m = int(core_r * 3) + 2
        y0, y1 = max(0, sy - m), min(h, sy + m)
        x0, x1 = max(0, sx - m), min(w, sx + m)
        if y1 > y0 and x1 > x0:
            ly = np.arange(y0, y1, dtype=np.float32).reshape(-1, 1)
            lx = np.arange(x0, x1, dtype=np.float32).reshape(1, -1)
            core = np.exp(-((lx - sx)**2 + (ly - sy)**2) / (2 * max(0.5, core_r)**2)) * brightness
            out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], core)
        # Cross spikes (4 directions)
        sl = int(spike_len)
        for dy, dx in [(1,0), (-1,0), (0,1), (0,-1)]:
            for t in range(1, sl + 1):
                py, px = sy + dy * t, sx + dx * t
                if 0 <= py < h and 0 <= px < w:
                    fade = brightness * (1.0 - t / sl) * 0.6
                    out[py, px] = max(out[py, px], fade)

    # Layer 4: Cosmic nebula dust — finer scales to avoid oversized blobs
    dust = _noise_simple(shape, seed=seed + 50, scale=40.0) * 0.15
    dust2 = _noise_simple(shape, seed=seed + 51, scale=20.0) * 0.10
    dust = dust + dust2 + 0.10
    # Layer 5: Very fine grain noise for constant-on shimmer
    grain = _noise_simple(shape, seed=seed + 99, scale=80.0) * 0.08
    return np.clip(out + dust + grain, 0.0, 1.0).astype(np.float32)


def _shimmer_turbine_sheen(shape, seed=0):
    """Turbine Sheen: very fine brushed-metal micro-streaks.
    HIGH frequency warp + tight period = tiny directional grain like real brushed metal."""
    h, w = shape
    dim = min(h, w)
    yy = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    # Fine warp via _noise_simple: scale=50 → ~40px warp features at 2048
    warp = _noise_simple(shape, seed=seed + 10, scale=50.0) * 6.0
    period = max(3, dim // 150)
    streak = np.sin((yy + warp) / period * np.pi * 2) * 0.5 + 0.5
    warp2 = _noise_simple(shape, seed=seed + 20, scale=70.0) * 4.0
    period2 = max(2, dim // 200)
    streak2 = np.sin((yy * 0.97 + xx * 0.03 + warp2) / period2 * np.pi * 2) * 0.5 + 0.5
    result = np.clip(streak * 0.55 + streak2 * 0.45, 0.0, 1.0)
    return result.astype(np.float32)


def _shimmer_spectral_mesh(shape, seed=0):
    """Spectral Mesh: fine diamond/hex wire mesh — NOT circular.
    Dense tiled wire grid with per-cell brightness variation for spectral shimmer."""
    h, w = shape
    yy = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    # Very fine mesh — tight cells, many wires
    cell = max(6, min(h, w) // 100)  # ~20px cells at 2048
    d1 = (yy + xx) % cell
    d2 = (yy - xx + 10000) % cell
    wire_w = max(1.0, cell * 0.10)
    wire1 = np.clip(1.0 - np.minimum(d1, cell - d1) / wire_w, 0, 1)
    wire2 = np.clip(1.0 - np.minimum(d2, cell - d2) / wire_w, 0, 1)
    mesh = np.maximum(wire1, wire2)
    # High-freq per-cell shimmer
    cell_noise = _noise_simple(shape, seed=seed + 80, scale=60.0) * 0.3 + 0.5  # Fine per-cell shimmer
    out = np.clip(mesh * 0.7 + (1 - mesh) * cell_noise * 0.4, 0.0, 1.0)
    return out.astype(np.float32)


_MICRO_SHIMMER_FIELD_MAP = {
    "shimmer_quantum_shard": _shimmer_quantum_shard,
    "shimmer_prism_frost": _shimmer_prism_frost,
    "shimmer_velvet_static": _shimmer_velvet_static,
    "shimmer_chrome_flux": _shimmer_chrome_flux,
    "shimmer_matte_halo": _shimmer_matte_halo,
    "shimmer_oil_tension": _shimmer_oil_tension,
    "shimmer_neon_weft": _shimmer_neon_weft,
    "shimmer_void_dust": _shimmer_void_dust,
    "shimmer_turbine_sheen": _shimmer_turbine_sheen,
    "shimmer_spectral_mesh": _shimmer_spectral_mesh,
}


def _get_micro_shimmer_field(variant, shape, seed):
    fn = _MICRO_SHIMMER_FIELD_MAP.get(variant)
    if fn is None:
        return _noise_simple(shape, seed=seed, scale=6.0)
    return _cache_reactive_field(variant, shape, seed, lambda: fn(shape, seed=seed))


def _paint_micro_shimmer(paint, shape, mask, seed, pm, bb, variant):
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32)
    pv = _get_micro_shimmer_field(variant, (h, w), seed)
    cx = (pv - 0.5) * pm
    if variant == "shimmer_quantum_shard":
        p[:, :, 0] += cx * 20.0
        p[:, :, 1] += cx * 8.0
        p[:, :, 2] += cx * 26.0
    elif variant == "shimmer_prism_frost":
        p += (np.clip(pv - 0.35, 0.0, 1.0) * pm * 16.0)[:, :, np.newaxis]
        p[:, :, 2] += cx * 12.0
    elif variant == "shimmer_velvet_static":
        # Complementary color hints — warm highlights in noise peaks, cool in troughs
        warm = np.clip(pv - 0.5, 0, 0.5) * pm * 2.0   # peaks get warm
        cool = np.clip(0.5 - pv, 0, 0.5) * pm * 2.0   # troughs get cool
        p[:, :, 0] += warm * 18.0   # Pink/magenta in peaks
        p[:, :, 1] += cool * 12.0   # Green/teal in troughs
        p[:, :, 2] += warm * 10.0 + cool * 8.0  # Purple hints
        p *= (1.0 - np.clip(pv, 0.0, 1.0) * pm * 0.06)[:, :, np.newaxis]  # Subtle depth
    elif variant == "shimmer_chrome_flux":
        # Liquid metal flow — bright chrome zones vs darker matte zones
        chrome_zone = np.clip(pv, 0.0, 1.0) * pm
        matte_zone = np.clip(1.0 - pv, 0.0, 1.0) * pm
        # Chrome zones brighten strongly (metallic highlight)
        p[:, :, 0] += chrome_zone * 35.0
        p[:, :, 1] += chrome_zone * 40.0
        p[:, :, 2] += chrome_zone * 30.0
        # Matte zones darken slightly (absorption)
        p[:, :, 0] -= matte_zone * 8.0
        p[:, :, 1] -= matte_zone * 6.0
        p[:, :, 2] -= matte_zone * 10.0
    elif variant == "shimmer_matte_halo":
        p *= (1.0 - np.clip(pv, 0.0, 1.0) * pm * 0.16)[:, :, np.newaxis]
        p[:, :, 1] += cx * 4.0
    elif variant == "shimmer_oil_tension":
        phase = pv * (2.0 * np.pi)
        p[:, :, 0] += (np.sin(phase) * 0.5 + 0.5) * pm * 16.0
        p[:, :, 1] += (np.sin(phase + 2.094) * 0.5 + 0.5) * pm * 14.0
        p[:, :, 2] += (np.sin(phase + 4.188) * 0.5 + 0.5) * pm * 18.0
    elif variant == "shimmer_neon_weft":
        p[:, :, 0] += np.clip(pv - 0.5, 0.0, 1.0) * pm * 24.0
        p[:, :, 2] += np.clip(0.5 - pv, 0.0, 1.0) * pm * 20.0
    elif variant == "shimmer_void_dust":
        # Dense sparkle dust — strong effect across full canvas
        spark = np.clip(pv * 1.5, 0.0, 1.0) * pm
        # Bright white core on high-intensity particles
        bright = np.clip((pv - 0.3) * 2.0, 0.0, 1.0) * pm
        p[:, :, 0] += spark * 40.0 + bright * 20.0
        p[:, :, 1] += spark * 45.0 + bright * 22.0
        p[:, :, 2] += spark * 35.0 + bright * 18.0
    elif variant == "shimmer_turbine_sheen":
        p += (np.abs(cx) * 28.0)[:, :, np.newaxis]
        p[:, :, 2] += cx * 10.0
    elif variant == "shimmer_spectral_mesh":
        p[:, :, 0] += cx * 14.0
        p[:, :, 1] += np.abs(cx) * 11.0
        p[:, :, 2] += cx * 18.0
    return np.clip(p, 0, 255).astype(np.float32)


# Reactive paint dispatch map (legacy + active shimmer variants).
_REACTIVE_PAINT_MAP = {
    "reactive_iridescent_flake": _paint_reactive_iridescent_flake,
    "reactive_pearl_shift":      _paint_reactive_pearl_shift,
    "reactive_candy_depth":      _paint_reactive_candy_depth,
    "reactive_chrome_veil":      _paint_reactive_chrome_veil,
    "reactive_spectra_ripple":   _paint_reactive_spectra_ripple,
    "reactive_micro_weave":      _paint_reactive_micro_weave,
    "reactive_depth_cell":       _paint_reactive_depth_cell,
    "reactive_shimmer_mist":     _paint_reactive_shimmer_mist,
    "reactive_oil_slick":        _paint_reactive_oil_slick,
    "reactive_wave_moire":       _paint_reactive_wave_moire,
}


# ─────────────────────────────────────────────────────────
# REACTIVE PATTERN DISPATCHER (add to _texture_expansion)
# ─────────────────────────────────────────────────────────

def _texture_reactive(shape, mask, seed, sm, variant):
    """Dispatch for reactive_* and shimmer_* pattern variants."""
    h, w = shape[:2] if len(shape) == 3 else shape
    _shape = (h, w)
    if variant.startswith("shimmer_"):
        pv = _get_micro_shimmer_field(variant, _shape, seed)
        return {"pattern_val": pv, "R_range": 0.0, "M_range": 0.0, "CC": None}
    fn_map = {
        "reactive_iridescent_flake": _reactive_iridescent_flake,
        "reactive_pearl_shift":      _reactive_pearl_shift,
        "reactive_candy_depth":      _reactive_candy_depth,
        "reactive_chrome_veil":      _reactive_chrome_veil,
        "reactive_spectra_ripple":   _reactive_spectra_ripple,
        "reactive_micro_weave":      _reactive_micro_weave,
        "reactive_depth_cell":       _reactive_depth_cell,
        "reactive_shimmer_mist":     _reactive_shimmer_mist,
        "reactive_oil_slick":        _reactive_oil_slick,
        "reactive_wave_moire":       _reactive_wave_moire,
    }
    fn = fn_map.get(variant)
    if fn is not None:
        pv = _cache_reactive_field(variant, _shape, seed, lambda: fn(_shape, seed=seed))
    else:
        pv = _noise_simple(_shape, seed=seed, scale=6.0)
    return {"pattern_val": pv, "R_range": 0.0, "M_range": 0.0, "CC": None}


# ─────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────

def build_expansion_entries(pattern_ids):
    """Build a dict pattern_id -> {texture_fn, paint_fn, variable_cc, desc} for each expansion ID."""
    out = {}
    for pid in pattern_ids:
        def _closure(v):
            def tex(shape, mask, seed, sm):
                if v.startswith("reactive_") or v.startswith("shimmer_"):
                    return _texture_reactive(shape, mask, seed, sm, v)
                return _texture_expansion(shape, mask, seed, sm, v)
            def paint(p, shape, mask, seed, pm, bb):
                if v.startswith("shimmer_"):
                    return _paint_micro_shimmer(p, shape, mask, seed, pm, bb, v)
                if v.startswith("reactive_"):
                    # Each reactive pattern has its own unique paint function
                    pfn = _REACTIVE_PAINT_MAP.get(v)
                    if pfn is not None:
                        try:
                            return pfn(p, shape, mask, seed, pm, bb)
                        except Exception:
                            pass
                    # Fallback: pass-through
                    return p[:, :, :3].astype(np.float32)
                return _paint_expansion(p, shape, mask, seed, pm, bb, v)
            return {"texture_fn": tex, "paint_fn": paint, "variable_cc": True, "desc": f"Expansion: {v}"}
        out[pid] = _closure(pid)
    return out


# === IGNITION REBUILD 2026-06-10 START ===
# --- IGNITION: lfr_star_lattice ---
def _ign_starlat_edge(xx, yy, cx, cy, R, rot, inner, k=5):
    dx = xx - cx
    dy = yy - cy
    ang = np.arctan2(dy, dx) - rot
    rad = np.hypot(dx, dy)
    m = 2.0 * np.pi / k
    a = np.abs(np.mod(ang, m) - m * 0.5)
    edge = R * (inner + (1.0 - inner) * (a / (m * 0.5)))
    return rad - edge

def _ign_starlat_texture(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 77001)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    px = max(dim / 2048.0, 0.05)
    out = np.zeros((h, w), dtype=np.float32)

    # band 1: stencil star badges — crisp double-stroke outline + offset solid
    # inner star + dashed orbit ring; every badge gets its own random rotation.
    hubs = []
    n_hub = int(rng.integers(13, 18))
    for _ in range(n_hub):
        cx = rng.uniform(0.04, 0.96) * w
        cy = rng.uniform(0.04, 0.96) * h
        R = rng.uniform(0.052, 0.112) * dim
        rot = rng.uniform(0.0, 2.0 * np.pi)
        ring = rng.random() < 0.6
        hubs.append((cx, cy, R))
        pad = R * 1.42 + 8.0 * px
        x0 = max(0, int(cx - pad)); x1 = min(w, int(cx + pad) + 2)
        y0 = max(0, int(cy - pad)); y1 = min(h, int(cy + pad) + 2)
        if x0 >= x1 or y0 >= y1:
            continue
        wx = xx[:, x0:x1]; wy = yy[y0:y1, :]
        d = _ign_starlat_edge(wx, wy, cx, cy, R, rot, 0.40)
        lw = 4.5 * px + R * 0.024
        stroke = np.clip(1.0 - np.abs(d) / lw, 0.0, 1.0)
        d2 = _ign_starlat_edge(wx, wy, cx, cy, R * 0.55, rot + np.pi / 5.0, 0.40)
        solid = np.clip(0.5 - d2 / (2.0 * px), 0.0, 1.0) * 0.86
        badge = np.maximum(stroke, solid)
        if ring:
            rad = np.hypot(wx - cx, wy - cy)
            angw = np.arctan2(wy - cy, wx - cx) - rot
            dash = (np.mod(angw, np.pi / 6.0) < np.pi / 9.0).astype(np.float32)
            orbit = np.clip(1.0 - np.abs(rad - R * 1.24) / (2.6 * px), 0.0, 1.0) * dash * 0.74
            badge = np.maximum(badge, orbit)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], badge.astype(np.float32))

    # band 2: lattice truss chords — each badge links to its 2 nearest peers
    # with twin pin rails + crossbar ticks, trimmed clear of the star bodies.
    if len(hubs) >= 3:
        pts = np.array([(p[0], p[1]) for p in hubs], dtype=np.float32)
        dmat = np.hypot(pts[:, 0][:, None] - pts[:, 0][None, :],
                        pts[:, 1][:, None] - pts[:, 1][None, :])
        np.fill_diagonal(dmat, 1e9)
        order = np.argsort(dmat, axis=1)
        done = set()
        for i in range(len(hubs)):
            for jj in order[i, :2]:
                j = int(jj)
                key = (min(i, j), max(i, j))
                if key in done:
                    continue
                done.add(key)
                x0p, y0p, r0 = hubs[i]
                x1p, y1p, r1 = hubs[j]
                seg_len = float(np.hypot(x1p - x0p, y1p - y0p))
                if seg_len < (r0 + r1) * 1.1 or seg_len > dim * 0.55:
                    continue
                pad = 10.0 * px
                xa = max(0, int(min(x0p, x1p) - pad)); xb = min(w, int(max(x0p, x1p) + pad) + 2)
                ya = max(0, int(min(y0p, y1p) - pad)); yb = min(h, int(max(y0p, y1p) + pad) + 2)
                if xa >= xb or ya >= yb:
                    continue
                wx = xx[:, xa:xb]; wy = yy[ya:yb, :]
                vx = x1p - x0p; vy = y1p - y0p
                tc = np.clip(((wx - x0p) * vx + (wy - y0p) * vy) / (seg_len * seg_len), 0.0, 1.0)
                dseg = np.hypot(wx - (x0p + tc * vx), wy - (y0p + tc * vy))
                trim = (np.clip((tc * seg_len - r0 * 1.18) / (6.0 * px), 0.0, 1.0)
                        * np.clip(((1.0 - tc) * seg_len - r1 * 1.18) / (6.0 * px), 0.0, 1.0))
                rail = np.clip(1.0 - np.abs(dseg - 4.2 * px) / (2.0 * px), 0.0, 1.0)
                bars = ((np.mod(tc * seg_len, 34.0 * px) < 5.0 * px) & (dseg < 4.2 * px)).astype(np.float32)
                truss = np.maximum(rail * 0.72, bars * 0.62) * trim
                out[ya:yb, xa:xb] = np.maximum(out[ya:yb, xa:xb], truss.astype(np.float32))

    # band 3: micro spark crosses, random rotation, 8-18px footprint at 2048.
    n_micro = int(rng.integers(150, 220))
    for _ in range(n_micro):
        cx = rng.uniform(0.0, 1.0) * w; cy = rng.uniform(0.0, 1.0) * h
        s_r = rng.uniform(4.0, 9.0) * px
        rot = rng.uniform(0.0, np.pi)
        ca = float(np.cos(rot)); sa = float(np.sin(rot))
        pad = s_r + 3.0 * px
        x0 = max(0, int(cx - pad)); x1 = min(w, int(cx + pad) + 2)
        y0 = max(0, int(cy - pad)); y1 = min(h, int(cy + pad) + 2)
        if x0 >= x1 or y0 >= y1:
            continue
        dx = xx[:, x0:x1] - cx; dy = yy[y0:y1, :] - cy
        u = dx * ca + dy * sa; v = dx * (-sa) + dy * ca
        armw = 1.3 * px
        arm1 = np.clip(1.0 - np.abs(v) / armw, 0.0, 1.0) * np.clip(1.0 - np.abs(u) / s_r, 0.0, 1.0)
        arm2 = np.clip(1.0 - np.abs(u) / armw, 0.0, 1.0) * np.clip(1.0 - np.abs(v) / s_r, 0.0, 1.0)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1],
                                       (np.maximum(arm1, arm2) * 0.58).astype(np.float32))

    g = rng.random(((h + 31) // 32, (w + 31) // 32)).astype(np.float32)
    bgf = np.repeat(np.repeat(g, 32, axis=0), 32, axis=1)[:h, :w]
    val = np.clip(out + bgf * 0.05 + 0.02, 0.0, 1.0).astype(np.float32)
    cc = np.clip(16 * (1 - val * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": val, "R_range": -128.0, "M_range": 98.0, "CC": cc}

def _ign_starlat_paint(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None:
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)
    h, w = shape
    # PERF: the hue field is >=570px wavelength — build it at 1/4 res and
    # block-upsample (visually identical, ~16x cheaper).
    ds = 4
    hs, ws = (h + ds - 1) // ds, (w + ds - 1) // ds
    yy = (np.arange(hs, dtype=np.float32) * ds)[:, None]
    xx = (np.arange(ws, dtype=np.float32) * ds)[None, :]
    rng = np.random.default_rng(int(seed) + 77031)
    ph = np.zeros((hs, ws), dtype=np.float32)
    for _ in range(4):
        cx = rng.uniform(0.0, w); cy = rng.uniform(0.0, h)
        fr = rng.uniform(0.0045, 0.0105)
        ph += np.sin(np.hypot(xx - cx, yy - cy) * fr + rng.uniform(0.0, 6.28))
    ph = np.clip(ph * 0.25 + 0.5, 0.0, 1.0)
    ph = np.repeat(np.repeat(ph, ds, axis=0), ds, axis=1)[:h, :w]
    sm_ = (pm * 1.0) * np.asarray(mask, dtype=np.float32)
    core = np.clip((pv - 0.62) * 3.4, 0, 1)
    mid = np.clip((pv - 0.33) * 2.6, 0, 1) * (1.0 - core)
    redz = mid * ph
    bluz = mid * (1.0 - ph)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (core * 0.94 + redz * 0.85 - bluz * 0.14) * sm_, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (core * 0.94 - redz * 0.20 + bluz * 0.02) * sm_, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (core * 0.97 - redz * 0.14 + bluz * 0.58) * sm_, 0, 1)
    return paint

# --- IGNITION: lfr_stripe_drift ---
def _ign_stripedrift_texture(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 78001)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    px = max(dim / 2048.0, 0.05)
    out = np.zeros((h, w), dtype=np.float32)

    # bands 1+2: finite chevron-staggered slash packs (3-5 hard-edged tapered
    # stripes each, heads cut into a V) flanked by thin pin rails. Every pack
    # has its own center + rotation: no global stripe axis survives UV scatter.
    n_pack = int(rng.integers(18, 24))
    for _ in range(n_pack):
        cx = rng.uniform(0.02, 0.98) * w; cy = rng.uniform(0.02, 0.98) * h
        ang = rng.uniform(0.0, np.pi)
        ca = float(np.cos(ang)); sa = float(np.sin(ang))
        L = rng.uniform(0.14, 0.30) * dim
        nst = int(rng.integers(3, 6))
        wb = rng.uniform(8.0, 15.0) * px
        gap = wb * rng.uniform(2.4, 3.2)
        offs = (np.arange(nst, dtype=np.float32) - (nst - 1) / 2.0) * gap
        chev = rng.uniform(0.55, 1.5) * (1.0 if rng.random() < 0.5 else -1.0)
        omax = float(np.abs(offs).max())
        Lu = L * 0.62 + abs(chev) * (omax + gap) + 6.0 * px
        Lv = omax + gap * 1.2 + wb * 2.0 + 6.0 * px
        hx = abs(ca) * Lu + abs(sa) * Lv
        hy = abs(sa) * Lu + abs(ca) * Lv
        x0 = max(0, int(cx - hx)); x1 = min(w, int(cx + hx) + 2)
        y0 = max(0, int(cy - hy)); y1 = min(h, int(cy + hy) + 2)
        if x0 >= x1 or y0 >= y1:
            continue
        wx = xx[:, x0:x1]; wy = yy[y0:y1, :]
        u = (wx - cx) * ca + (wy - cy) * sa
        v = (wx - cx) * (-sa) + (wy - cy) * ca
        pack = np.zeros(np.broadcast_shapes(u.shape, v.shape), dtype=np.float32)
        for k in range(nst):
            off = float(offs[k])
            uu = u - abs(off) * chev
            tpos = np.clip((uu + L * 0.5) / L, 0.0, 1.0)
            wloc = wb * (1.0 - 0.80 * tpos * tpos)
            edge = (np.clip((wloc - np.abs(v - off)) / (1.4 * px), 0.0, 1.0)
                    * np.clip((uu + L * 0.5) / (2.5 * px), 0.0, 1.0)
                    * np.clip((L * 0.5 - uu) / (2.5 * px), 0.0, 1.0))
            pack = np.maximum(pack, edge * (1.0 if k % 2 == 0 else 0.82))
        for sgn in (-1.0, 1.0):
            voff = float(offs[-1] if sgn > 0 else offs[0]) + sgn * gap * 0.85
            uu = u - abs(voff) * chev
            rail = (np.clip(1.0 - np.abs(v - voff) / (2.2 * px), 0.0, 1.0)
                    * np.clip((uu + L * 0.55) / (3.0 * px), 0.0, 1.0)
                    * np.clip((L * 0.42 - uu) / (3.0 * px), 0.0, 1.0))
            pack = np.maximum(pack, rail * 0.66)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], pack)

    # band 3: micro dash ticks at random angles, 8-16px at 2048.
    n_tick = int(rng.integers(200, 280))
    for _ in range(n_tick):
        cx = rng.uniform(0.0, 1.0) * w; cy = rng.uniform(0.0, 1.0) * h
        ang = rng.uniform(0.0, np.pi)
        ca = float(np.cos(ang)); sa = float(np.sin(ang))
        tl = rng.uniform(6.0, 14.0) * px
        pad = tl + 4.0 * px
        x0 = max(0, int(cx - pad)); x1 = min(w, int(cx + pad) + 2)
        y0 = max(0, int(cy - pad)); y1 = min(h, int(cy + pad) + 2)
        if x0 >= x1 or y0 >= y1:
            continue
        dx = xx[:, x0:x1] - cx; dy = yy[y0:y1, :] - cy
        u = dx * ca + dy * sa; v = dx * (-sa) + dy * ca
        dash = np.clip(1.0 - np.abs(v) / (1.6 * px), 0.0, 1.0) * np.clip(1.0 - np.abs(u) / tl, 0.0, 1.0)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], (dash * 0.52).astype(np.float32))

    g = rng.random(((h + 31) // 32, (w + 31) // 32)).astype(np.float32)
    bgf = np.repeat(np.repeat(g, 32, axis=0), 32, axis=1)[:h, :w]
    val = np.clip(out + bgf * 0.05 + 0.02, 0.0, 1.0).astype(np.float32)
    cc = np.clip(16 * (1 - val * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": val, "R_range": -112.0, "M_range": 84.0, "CC": cc}

def _ign_stripedrift_paint(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None:
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)
    h, w = shape
    # PERF: low-frequency hue field at 1/4 res + block-upsample.
    ds = 4
    hs, ws = (h + ds - 1) // ds, (w + ds - 1) // ds
    yy = (np.arange(hs, dtype=np.float32) * ds)[:, None]
    xx = (np.arange(ws, dtype=np.float32) * ds)[None, :]
    rng = np.random.default_rng(int(seed) + 78031)
    ph = np.zeros((hs, ws), dtype=np.float32)
    for _ in range(3):
        cx = rng.uniform(0.0, w); cy = rng.uniform(0.0, h)
        fr = rng.uniform(0.005, 0.011)
        ph += np.sin(np.hypot(xx - cx, yy - cy) * fr + rng.uniform(0.0, 6.28))
    ph = np.clip(ph * 0.30 + 0.5, 0.0, 1.0)
    ph = np.repeat(np.repeat(ph, ds, axis=0), ds, axis=1)[:h, :w]
    sm_ = (pm * 1.0) * np.asarray(mask, dtype=np.float32)
    hot = np.clip((pv - 0.68) * 4.0, 0, 1)
    mid = np.clip((pv - 0.40) * 3.0, 0, 1) * (1.0 - hot)
    pin = np.clip((pv - 0.24) * 2.6, 0, 1) * (1.0 - hot) * (1.0 - mid)
    red = mid * ph
    nvy = mid * (1.0 - ph)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (hot * 0.92 + red * 0.88 - nvy * 0.16 - pin * 0.04) * sm_, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (hot * 0.92 - red * 0.24 + nvy * 0.03 + pin * 0.10) * sm_, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (hot * 0.95 - red * 0.16 + nvy * 0.60 + pin * 0.30) * sm_, 0, 1)
    return paint

# --- IGNITION: lfr_bunting_scallop ---
def _ign_buntfan_grain(shape, seed, waves):
    # Isotropic micro-grain: summed plane waves at random angles (no axis bias).
    h, w = shape
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    out = np.zeros((h, w), dtype=np.float32)
    tot = 0.0
    for wl in waves:
        for _ in range(2):
            a = rng.uniform(0.0, np.pi)
            f = (2.0 * np.pi) / max(float(wl), 2.0)
            ph = rng.uniform(0.0, 2.0 * np.pi)
            out += np.sin((xx * np.cos(a) + yy * np.sin(a)) * f + ph).astype(np.float32) * (1.0 / float(wl))
            tot += 1.0 / float(wl)
    out /= max(tot, 1e-6)
    return (out * 0.5 + 0.5).astype(np.float32)

def _ign_buntfan_star(ang, rad, R, k=5):
    m = 2.0 * np.pi / k
    a = np.mod(ang, m)
    a = np.abs(a - m * 0.5)
    edge = R * (0.45 + 0.55 * (a / (m * 0.5)))
    return np.clip(1.0 - rad / (edge + 1e-4), 0.0, 1.0)

def _ign_buntfan_texture(shape, mask, seed, sm):
    """lfr_bunting_scallop rebuild: pleated half-fan bunting rosettes.

    Each rosette = crisp radial pleat rays + a scallop-waved rim with two
    nested echo arcs + a five-point star hub button. Three size tiers
    scattered at fully random rotations (UV-orientation-agnostic).
    Alpha-stamp: transparent field between rosettes, low isotropic grain only.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.default_rng(int(seed) + 52601)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    line_w = max(1.5, dim * 0.0040)      # pleat ray width  (~8 px @ 2048)
    band_w = max(2.0, dim * 0.0055)      # rim piping width (~11 px @ 2048)
    tiers = [
        (int(rng.integers(6, 9)),   0.105, 0.165, 1.00),
        (int(rng.integers(13, 19)), 0.052, 0.090, 0.88),
        (int(rng.integers(26, 38)), 0.024, 0.044, 0.72),
    ]
    for count, rmin, rmax, peak in tiers:
        for _ in range(count):
            cx = rng.uniform(-0.04, 1.04) * w
            cy = rng.uniform(-0.04, 1.04) * h
            R = rng.uniform(rmin, rmax) * dim
            rot = rng.uniform(0.0, 2.0 * np.pi)
            spread = rng.uniform(1.55, 2.45)          # fan half-angle (rad)
            n_pleat = int(rng.integers(7, 13))
            hubR = R * rng.uniform(0.16, 0.22)
            tw = rng.uniform(0.0, 2.0 * np.pi)
            # PERF: rosette support is strictly rad < R -- local window only.
            x0 = max(0, int(cx - R) - 2); x1 = min(w, int(cx + R) + 3)
            y0 = max(0, int(cy - R) - 2); y1 = min(h, int(cy + R) + 3)
            if x0 >= x1 or y0 >= y1:
                continue
            dx = xx[:, x0:x1] - cx
            dy = yy[y0:y1, :] - cy
            ang = np.arctan2(dy, dx) - rot
            ang = np.mod(ang + np.pi, 2.0 * np.pi) - np.pi
            rad = np.hypot(dx, dy)
            keep = (np.abs(ang) < spread).astype(np.float32)
            lw_eff = max(1.2, min(line_w, R * 0.06))
            bw_eff = max(1.5, min(band_w, R * 0.085))
            pitch = (2.0 * spread) / n_pleat
            phase = ang / pitch
            # pleat rays: angular distance to nearest ray, converted to pixels
            pa = np.abs(np.mod(phase + 0.5, 1.0) - 0.5) * pitch
            pleat = np.clip(1.0 - (pa * rad) / lw_eff, 0.0, 1.0)
            pleat *= np.clip((rad - R * 0.30) / (R * 0.05), 0, 1)
            pleat *= np.clip((R * 0.94 - rad) / (R * 0.05), 0, 1)
            # scallop-waved rim piping + two nested echo arcs (scallops keyed
            # to the pleat pitch so the wave lands between rays)
            sc = np.cos(phase * 2.0 * np.pi)
            fan = pleat * 0.80
            for kk in range(3):
                off = (0.0, 0.155, 0.30)[kk]
                wt = (1.0, 0.86, 0.70)[kk]
                r_edge = R * (0.875 - off) + R * 0.075 * sc
                arc = np.clip(1.0 - np.abs(rad - r_edge) / (bw_eff * (1.0 - 0.18 * kk)), 0.0, 1.0)
                fan = np.maximum(fan, arc * wt)
            fan = fan * keep
            # star hub button (full disc, proud of the fan) + hub ring
            star = _ign_buntfan_star(ang + tw, rad, hubR, k=5)
            starv = np.clip(star * 3.0, 0.0, 1.0) * 0.97
            ring = np.clip(1.0 - np.abs(rad - hubR * 1.30) / (bw_eff * 0.75), 0.0, 1.0) * 0.88
            stamp = np.maximum(np.maximum(fan, starv), ring)
            out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], (stamp * peak).astype(np.float32))
    bg = _ign_buntfan_grain((h, w), int(seed) + 52609, (9.0, 17.0, 33.0)) * 0.09 + 0.04
    pv = np.clip(out + bg, 0.0, 1.0).astype(np.float32)
    cc = np.clip(16.0 * (1.0 - pv * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": pv, "R_range": -112.0, "M_range": 88.0, "CC": cc}

def _ign_buntfan_paint(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None:
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)
    s = pm * 0.95
    h, w = shape[:2] if len(shape) > 2 else shape
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    # two oblique wave axes (seed-rotated, never upright) split red/white/blue
    a1 = (int(seed) % 89) * 0.0353 + 0.41
    a2 = a1 + 1.91
    sel = (np.sin((xx * np.cos(a1) + yy * np.sin(a1)) * 0.0145 + int(seed) % 13)
           + np.cos((xx * np.cos(a2) + yy * np.sin(a2)) * 0.0118 - int(seed) % 7)) * 0.5
    core = np.clip((pv - 0.64) * 3.0, 0, 1)                  # piping + star hubs
    body = np.clip((pv - 0.30) * 2.0, 0, 1) * (1.0 - core)   # pleat rays
    red = body * np.clip((-sel - 0.08) * 1.6, 0, 1)
    blue = body * np.clip((sel - 0.08) * 1.6, 0, 1)
    white = body * np.clip(1.0 - np.abs(sel) * 3.0, 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (core * 0.88 + white * 0.62 + red * 0.74 - blue * 0.10) * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (core * 0.88 + white * 0.62 - red * 0.16 - blue * 0.05) * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (core * 0.92 + white * 0.66 - red * 0.10 + blue * 0.82) * s * mask, 0, 1)
    return paint

# --- IGNITION: lfr_distressed_flag ---
def _ign_flagshred_grain(shape, seed, waves):
    # Isotropic micro-grain: summed plane waves at random angles (no axis bias).
    h, w = shape
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    out = np.zeros((h, w), dtype=np.float32)
    tot = 0.0
    for wl in waves:
        for _ in range(2):
            a = rng.uniform(0.0, np.pi)
            f = (2.0 * np.pi) / max(float(wl), 2.0)
            ph = rng.uniform(0.0, 2.0 * np.pi)
            out += np.sin((xx * np.cos(a) + yy * np.sin(a)) * f + ph).astype(np.float32) * (1.0 / float(wl))
            tot += 1.0 / float(wl)
    out /= max(tot, 1e-6)
    return (out * 0.5 + 0.5).astype(np.float32)

def _ign_flagshred_texture(shape, mask, seed, sm):
    """lfr_distressed_flag rebuild: torn banner shreds, not a noise field.

    Scattered rotated shreds with ragged eroded edges; each carries oblique
    bar art or spangle diamond-dot art plus a bright torn outline. Broken
    meandering scratch strokes and spark pins distress the field between
    shreds. Transparent background -- motif strokes only.
    """
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.default_rng(int(seed) + 52701)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    edge_w = max(1.2, dim * 0.0012)
    n_shred = int(rng.integers(20, 26))
    for _ in range(n_shred):
        cx = np.float32(rng.uniform(0.02, 0.98) * w)
        cy = np.float32(rng.uniform(0.02, 0.98) * h)
        rot = rng.uniform(0.0, np.pi)
        hl = np.float32(rng.uniform(0.055, 0.150) * dim)
        hwd = np.float32(rng.uniform(0.014, 0.038) * dim)
        ca, sa = np.float32(np.cos(rot)), np.float32(np.sin(rot))
        rr = hl + hwd + 4.0
        x0 = max(0, int(cx - rr) - 2); x1 = min(w, int(cx + rr) + 3)
        y0 = max(0, int(cy - rr) - 2); y1 = min(h, int(cy + rr) + 3)
        if x0 >= x1 or y0 >= y1:
            continue
        dx = xx[:, x0:x1] - cx
        dy = yy[y0:y1, :] - cy
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        f1 = np.float32(rng.uniform(0.05, 0.11)); f2 = np.float32(rng.uniform(0.16, 0.30))
        p1 = np.float32(rng.uniform(0, 6.28)); p2 = np.float32(rng.uniform(0, 6.28)); p3 = np.float32(rng.uniform(0, 6.28))
        # ragged long edges + torn ends
        wmod = hwd * (0.64 + 0.24 * np.sin(u * f1 + p1) + 0.12 * np.sin(u * f2 + p2))
        lmod = hl * (0.80 + 0.20 * np.sin(v * (f2 * 1.7) + p3))
        body = np.clip((wmod - np.abs(v)) / edge_w, 0, 1) * np.clip((lmod - np.abs(u)) / (edge_w * 2.5), 0, 1)
        if rng.random() < 0.62:
            # oblique bar art (off-axis even in local frame)
            bw = rng.uniform(0.30, 0.55) * (1.0 if rng.random() < 0.5 else -1.0)
            t = u * np.cos(bw) + v * np.sin(bw)
            per = rng.uniform(0.011, 0.020) * dim
            art = np.where(np.mod(t / per, 1.0) < 0.52, 1.0, 0.30).astype(np.float32)
        else:
            # spangle diamond-dot art
            g = rng.uniform(0.016, 0.026) * dim
            gu = np.abs(np.mod(u / g + 0.5, 1.0) - 0.5)
            gv = np.abs(np.mod(v / g + 0.5, 1.0) - 0.5)
            dot = np.clip(1.0 - (gu + gv) / 0.30, 0.0, 1.0)
            art = np.clip(0.45 + dot * 0.9, 0.0, 1.0)
        shred = body * art
        # bright torn outline along the ragged long edges
        outline = np.clip(1.0 - np.abs(wmod - np.abs(v)) / (edge_w * 1.6), 0, 1)
        outline *= np.clip((lmod - np.abs(u)) / (edge_w * 2.5), 0, 1)
        shred = np.maximum(shred, outline)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], shred.astype(np.float32))
    # broken meandering scratch strokes
    n_crack = int(rng.integers(7, 11))
    lw = np.float32(max(1.4, dim * 0.0020))
    for _ in range(n_crack):
        cx = np.float32(rng.uniform(0.05, 0.95) * w)
        cy = np.float32(rng.uniform(0.05, 0.95) * h)
        angc = rng.uniform(0.0, np.pi)
        L = rng.uniform(0.16, 0.34) * dim
        A1 = rng.uniform(0.008, 0.022) * dim
        A2 = A1 * rng.uniform(0.25, 0.5)
        fA = rng.uniform(2.0, 4.5) / L
        fB = rng.uniform(9.0, 16.0) / L
        ph1 = rng.uniform(0, 6.28); ph2 = rng.uniform(0, 6.28); phb = rng.uniform(0, 6.28)
        ca, sa = np.float32(np.cos(angc)), np.float32(np.sin(angc))
        m = A1 + A2 + lw * 3.0 + 4.0
        hx = L * abs(ca) + m * abs(sa)
        hy = L * abs(sa) + m * abs(ca)
        x0 = max(0, int(cx - hx) - 2); x1 = min(w, int(cx + hx) + 3)
        y0 = max(0, int(cy - hy) - 2); y1 = min(h, int(cy + hy) + 3)
        if x0 >= x1 or y0 >= y1:
            continue
        dx = xx[:, x0:x1] - cx
        dy = yy[y0:y1, :] - cy
        r = dx * ca + dy * sa
        p = -dx * sa + dy * ca
        off = A1 * np.sin(r * fA * 6.283 + ph1) + A2 * np.sin(r * fB * 6.283 + ph2)
        taper = np.clip((1.0 - np.abs(r) / L) * 3.0, 0, 1)
        broken = (np.sin(r * (fB * 2.6) * 6.283 + phb) > -0.62).astype(np.float32)
        stroke = np.clip(1.0 - np.abs(p - off) / lw, 0, 1) * taper * broken
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], (stroke * 0.96).astype(np.float32))
    # spark pins
    pins = (rng.random((h, w), dtype=np.float32) > 0.9962).astype(np.float32)
    if h > 2 and w > 2:
        pins[1:, :] = np.maximum(pins[1:, :], pins[:-1, :] * 0.5)
        pins[:, 1:] = np.maximum(pins[:, 1:], pins[:, :-1] * 0.5)
    out = np.maximum(out, pins * 0.85)
    bg = _ign_flagshred_grain((h, w), int(seed) + 52719, (9.0, 18.0, 35.0)) * 0.08 + 0.035
    pv = np.clip(out + bg, 0.0, 1.0).astype(np.float32)
    cc = np.clip(16.0 * (1.0 - pv * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": pv, "R_range": 82.0, "M_range": -42.0, "CC": cc}

def _ign_flagshred_paint(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None:
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)
    s = pm * 0.92
    h, w = shape[:2] if len(shape) > 2 else shape
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    # oblique seed-rotated selector waves: weathered red/cream/blue zoning
    a1 = (int(seed) % 83) * 0.0379 + 0.53
    a2 = a1 + 2.09
    sel = (np.sin((xx * np.cos(a1) + yy * np.sin(a1)) * 0.0052 + int(seed) % 17)
           + np.sin((xx * np.cos(a2) + yy * np.sin(a2)) * 0.0067 - int(seed) % 11)) * 0.5
    weather = 0.70 + 0.30 * (np.sin((xx * np.cos(a2) - yy * np.sin(a1)) * 0.0031 + int(seed) % 23) * 0.5 + 0.5)
    hi = np.clip((pv - 0.74) * 3.4, 0, 1)                    # scratches/spangles/outlines
    body = np.clip((pv - 0.28) * 1.9, 0, 1) * (1.0 - hi)     # shred bodies
    red = body * np.clip((-sel - 0.06) * 1.7, 0, 1)
    blue = body * np.clip((sel - 0.06) * 1.7, 0, 1)
    cream = body * np.clip(1.0 - np.abs(sel) * 2.8, 0, 1)
    sw = s * weather
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (hi * 0.80 + red * 0.66 + cream * 0.46 - blue * 0.08) * sw * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (hi * 0.78 - red * 0.15 + cream * 0.42 - blue * 0.04) * sw * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (hi * 0.72 - red * 0.10 + cream * 0.34 + blue * 0.70) * sw * mask, 0, 1)
    return paint

# --- IGNITION: lfr_eagle_crest ---
def _ign_ec_veil(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 60409)
    out = np.zeros((h, w), dtype=np.float32)
    tot = 0.0
    for cyc in (6.0, 13.0, 29.0):
        wt = 1.0 / cyc
        fx = cyc * rng.uniform(0.7, 1.4) * 2.0 * np.pi / max(w, 1)
        fy = cyc * rng.uniform(0.7, 1.4) * 2.0 * np.pi / max(h, 1)
        px = rng.uniform(0.0, 6.28318)
        py = rng.uniform(0.0, 6.28318)
        out += (np.sin(np.arange(w, dtype=np.float32)[None, :] * fx + px)
                * np.cos(np.arange(h, dtype=np.float32)[:, None] * fy + py)).astype(np.float32) * wt
        tot += wt
    out /= max(tot, 1e-6)
    return (out * 0.5 + 0.5).astype(np.float32)

def _ign_eaglecrest_texture(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 60401)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    dash_px = max(6.0, dim * 0.0075)  # barb-dash period ~15px @2048

    def _stamp(cx, cy, R, rot, quills, spread, lw_px, heart, arc):
        # PERF: all strokes live inside rad <= R -- local window only.
        x0 = max(0, int(cx - R) - 2); x1 = min(w, int(cx + R) + 3)
        y0 = max(0, int(cy - R) - 2); y1 = min(h, int(cy + R) + 3)
        if x0 >= x1 or y0 >= y1:
            return
        dx = xx[:, x0:x1] - cx
        dy = yy[y0:y1, :] - cy
        ca, sa = np.cos(rot), np.sin(rot)
        ang = np.arctan2(dy, dx) - rot
        ang = np.mod(ang + np.pi, 2.0 * np.pi) - np.pi
        rad = np.hypot(dx, dy)
        rn = rad / (R + 1e-4)
        loc = np.zeros(rad.shape, dtype=np.float32)
        step = (2.0 * spread) / float(max(quills, 2))
        ph = rng.uniform(0.0, 6.28318)
        infan = np.abs(ang) <= spread
        # staggered double feather tier: sharp tapered quill spines + barb dash
        for t0, t1, off in ((0.26, 0.72, 0.0), (0.50, 1.0, 0.5)):
            a = np.mod(ang + spread + step * off, step) - step * 0.5
            d = np.abs(a) * np.maximum(rad, 1.0)
            band = np.clip((rn - t0) / max(t1 - t0, 1e-4), 0.0, 1.0)
            lw = np.float32(lw_px) * (1.0 - 0.66 * band) + 0.55
            spine = np.clip(1.0 - d / lw, 0.0, 1.0)
            spine *= ((rn >= t0) & (rn <= t1) & infan).astype(np.float32)
            barb = 0.60 + 0.40 * np.cos(rad * (2.0 * np.pi / dash_px) + ph + off * 2.1)
            loc = np.maximum(loc, (spine * barb * 0.80).astype(np.float32))
        if arc:
            # thin tip-arc rib binding the fan, feathered at the fan edges
            aw = np.clip((spread - np.abs(ang)) / max(step * 0.8, 1e-4), 0.0, 1.0)
            rib = np.clip(1.0 - np.abs(rad - R * 0.985) / (lw_px * 0.62 + 0.5), 0.0, 1.0)
            loc = np.maximum(loc, (rib * aw * 0.92).astype(np.float32))
        if heart:
            # nested heraldic lozenge heart (rotated with the crest)
            xr = dx * ca + dy * sa
            yr = -dx * sa + dy * ca
            L = np.abs(xr) / (0.150 * R + 1e-4) + np.abs(yr) / (0.235 * R + 1e-4)
            gsc = 0.185 * R
            for k, amp in ((1.0, 1.0), (1.42, 0.93)):
                ring = np.clip(1.0 - np.abs(L - k) * gsc / (lw_px * 0.75 + 0.5), 0.0, 1.0)
                loc = np.maximum(loc, (ring * amp).astype(np.float32))
            loc = np.maximum(loc, np.clip((0.46 - L) / 0.46, 0.0, 1.0).astype(np.float32))
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], loc)

    for _ in range(int(rng.integers(4, 7))):       # grand crests
        _stamp(rng.uniform(0.0, 1.0) * w, rng.uniform(0.0, 1.0) * h,
               rng.uniform(0.110, 0.165) * dim, rng.uniform(0.0, 6.28318),
               int(rng.integers(11, 16)), rng.uniform(1.5, 2.4),
               max(2.4, dim * 0.0028), True, True)
    for _ in range(int(rng.integers(7, 11))):      # field crests
        _stamp(rng.uniform(0.0, 1.0) * w, rng.uniform(0.0, 1.0) * h,
               rng.uniform(0.052, 0.085) * dim, rng.uniform(0.0, 6.28318),
               int(rng.integers(8, 12)), rng.uniform(1.2, 2.0),
               max(1.9, dim * 0.0021), bool(rng.random() > 0.45), True)
    for _ in range(int(rng.integers(16, 24))):     # lone quill tufts
        _stamp(rng.uniform(0.0, 1.0) * w, rng.uniform(0.0, 1.0) * h,
               rng.uniform(0.018, 0.034) * dim, rng.uniform(0.0, 6.28318),
               int(rng.integers(3, 6)), rng.uniform(0.7, 1.3),
               max(1.5, dim * 0.0014), False, False)

    veil = _ign_ec_veil(shape, int(seed) + 60417) * 0.05 + 0.02
    val = np.clip(np.maximum(out, veil), 0.0, 1.0)
    cc = np.clip(16.0 * (1.0 - val * 0.5), 0.0, 16.0).astype(np.uint8)
    return {"pattern_val": val.astype(np.float32), "R_range": -125.0, "M_range": 100.0, "CC": cc}

def _ign_eaglecrest_paint(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None:
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)
    s = pm * 1.0
    core = np.clip((pv - 0.66) * 4.5, 0, 1)                      # hearts, rib peaks
    crim = np.clip((pv - 0.48) * 3.4, 0, 1) * (1.0 - core)       # barb crests -> crimson
    gold = np.clip((pv - 0.20) * 2.2, 0, 1) * (1.0 - core) * (1.0 - crim)  # spine bodies
    veil = np.clip(pv * 1.4, 0, 1) * (1.0 - np.maximum(core, np.maximum(crim, gold)))
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (core * 0.96 + crim * 0.88 + gold * 0.80 - veil * 0.04) * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (core * 0.93 + crim * 0.10 + gold * 0.58 - veil * 0.02) * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (core * 0.82 - crim * 0.06 + gold * 0.10 + veil * 0.12) * s * mask, 0, 1)
    return paint

# --- IGNITION: lfr_firework_radial ---
def _ign_fw_veil(shape, seed):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 61509)
    out = np.zeros((h, w), dtype=np.float32)
    tot = 0.0
    for cyc in (5.0, 11.0, 27.0):
        wt = 1.0 / cyc
        fx = cyc * rng.uniform(0.7, 1.4) * 2.0 * np.pi / max(w, 1)
        fy = cyc * rng.uniform(0.7, 1.4) * 2.0 * np.pi / max(h, 1)
        px = rng.uniform(0.0, 6.28318)
        py = rng.uniform(0.0, 6.28318)
        out += (np.sin(np.arange(w, dtype=np.float32)[None, :] * fx + px)
                * np.cos(np.arange(h, dtype=np.float32)[:, None] * fy + py)).astype(np.float32) * wt
        tot += wt
    out /= max(tot, 1e-6)
    return (out * 0.5 + 0.5).astype(np.float32)

def _ign_firework_texture(shape, mask, seed, sm):
    h, w = shape
    rng = np.random.default_rng(int(seed) + 61501)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)

    def _burst(cx, cy, R, streamers, curl, rot, lw_px, ring, crossed):
        # PERF: all strokes live inside rad <= R*1.04 -- local window only.
        rr = R * 1.04 + 2.0
        x0 = max(0, int(cx - rr) - 2); x1 = min(w, int(cx + rr) + 3)
        y0 = max(0, int(cy - rr) - 2); y1 = min(h, int(cy + rr) + 3)
        if x0 >= x1 or y0 >= y1:
            return
        dx = xx[:, x0:x1] - cx
        dy = yy[y0:y1, :] - cy
        ang = np.arctan2(dy, dx)
        rad = np.hypot(dx, dy)
        rn = rad / (R + 1e-4)
        # curved comet streamers: quadratic curl bends every spoke
        step = 2.0 * np.pi / float(max(streamers, 3))
        u = ang - curl * rn * rn - rot
        a = np.mod(u, step) - step * 0.5
        d = np.abs(a) * np.maximum(rad, 1.0)
        lw = np.float32(lw_px) * (1.0 - 0.60 * np.clip(rn, 0.0, 1.0)) + 0.55
        body = np.clip(1.0 - d / lw, 0.0, 1.0)
        body *= ((rn >= 0.085) & (rn <= 1.0)).astype(np.float32)
        # crackle: continuous near the heart, broken spark dashes at the tips
        per = max(5.0, rng.uniform(0.0058, 0.0102) * dim)
        ph = rng.uniform(0.0, 6.28318)
        kk = 0.85 * np.clip((rn - 0.38) / 0.62, 0.0, 1.0)
        dashm = 1.0 - kk * (0.5 + 0.5 * np.cos(rad * (2.0 * np.pi / per) + ph))
        stream = body * dashm * (0.95 - 0.20 * np.clip(rn, 0.0, 1.0))
        tip = body * np.clip((dashm - 0.72) / 0.28, 0.0, 1.0) * np.clip((rn - 0.74) / 0.26, 0.0, 1.0)
        loc = np.maximum(stream, tip).astype(np.float32)
        if crossed:
            # camera-glint core: thin cross spikes
            spikes = int(rng.integers(4, 7))
            a2 = np.mod(ang - rot * 1.7, 2.0 * np.pi / spikes) - np.pi / spikes
            d2 = np.abs(a2) * np.maximum(rad, 1.0)
            cross = np.clip(1.0 - d2 / (lw_px * 0.85 + 0.5), 0.0, 1.0) * np.clip(1.0 - rn / 0.17, 0.0, 1.0)
            loc = np.maximum(loc, (cross * 0.97).astype(np.float32))
        loc = np.maximum(loc, np.exp(-(rn * 13.0) ** 2).astype(np.float32))  # white-hot pin
        if ring:
            # dotted pearl ring
            rho = rng.uniform(0.58, 0.88)
            K = int(max(10, streamers * rng.uniform(1.4, 2.1)))
            dot = np.power(0.5 + 0.5 * np.cos(ang * K + ph), 3.0)
            ringv = np.clip(1.0 - np.abs(rad - rho * R) / (lw_px * 0.80 + 0.5), 0.0, 1.0)
            loc = np.maximum(loc, (ringv * dot * 0.88).astype(np.float32))
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], loc)

    for _ in range(int(rng.integers(4, 6))):    # grand chrysanthemum breaks
        _burst(rng.uniform(0.08, 0.92) * w, rng.uniform(0.08, 0.92) * h,
               rng.uniform(0.15, 0.26) * dim, int(rng.integers(16, 27)),
               rng.uniform(0.55, 1.25) * (1.0 if rng.random() > 0.5 else -1.0),
               rng.uniform(0.0, 6.28318), max(2.2, dim * 0.0026), True, True)
    for _ in range(int(rng.integers(6, 10))):   # mid shells
        _burst(rng.uniform(0.04, 0.96) * w, rng.uniform(0.04, 0.96) * h,
               rng.uniform(0.070, 0.120) * dim, int(rng.integers(10, 17)),
               rng.uniform(0.40, 1.05) * (1.0 if rng.random() > 0.5 else -1.0),
               rng.uniform(0.0, 6.28318), max(1.8, dim * 0.0019),
               bool(rng.random() > 0.5), bool(rng.random() > 0.5))
    for _ in range(int(rng.integers(12, 19))):  # micro pops
        _burst(rng.uniform(0.0, 1.0) * w, rng.uniform(0.0, 1.0) * h,
               rng.uniform(0.020, 0.042) * dim, int(rng.integers(5, 9)),
               rng.uniform(0.30, 0.80) * (1.0 if rng.random() > 0.5 else -1.0),
               rng.uniform(0.0, 6.28318), max(1.4, dim * 0.0013), False, False)

    veil = _ign_fw_veil(shape, int(seed) + 61517) * 0.05 + 0.015
    val = np.clip(np.maximum(out, veil), 0.0, 1.0)
    cc = np.clip(16.0 * (1.0 - val * 0.5), 0.0, 16.0).astype(np.uint8)
    return {"pattern_val": val.astype(np.float32), "R_range": -150.0, "M_range": 120.0, "CC": cc}

def _ign_firework_paint(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None:
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)
    s = pm * 1.0
    h, w = shape
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    # multi-angle drift selector (never axis-aligned): red / white / blue zones
    a1 = 0.31 + (int(seed) % 9) * 0.42
    ca, sa = np.cos(a1), np.sin(a1)
    sel = np.sin((xx * ca + yy * sa) * 0.0036 + (int(seed) % 13)) \
        + np.sin((xx * (-sa) + yy * ca) * 0.0049 - (int(seed) % 7))
    red_z = np.clip(0.55 - sel * 0.75, 0, 1)
    blu_z = np.clip(0.55 + sel * 0.75, 0, 1)
    wht_z = np.clip(1.0 - np.abs(sel) * 1.7, 0, 1)
    zs = red_z + blu_z + wht_z + 1e-4
    red_z = red_z / zs; blu_z = blu_z / zs; wht_z = wht_z / zs
    core = np.clip((pv - 0.68) * 4.5, 0, 1)                                  # pins, glints, tip sparks
    strm = np.clip((pv - 0.26) * 2.4, 0, 1) * (1.0 - core)                   # comet streamers + rings
    embr = np.clip((pv - 0.07) * 1.6, 0, 1) * (1.0 - core) * (1.0 - strm)    # smoke veil
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (core * 0.95 + strm * (red_z * 0.92 + wht_z * 0.85 - blu_z * 0.05) + embr * 0.05) * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (core * 0.95 + strm * (wht_z * 0.85 + red_z * 0.06 + blu_z * 0.10) - embr * 0.02) * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (core * 0.97 + strm * (blu_z * 0.94 + wht_z * 0.88 - red_z * 0.08) + embr * 0.14) * s * mask, 0, 1)
    return paint

# --- IGNITION: lfr_constellation_field ---
def _ign_constel_texture(shape, mask, seed, sm):
    h, w = int(shape[0]), int(shape[1])
    rng = np.random.default_rng((int(seed) + 46101) & 0xFFFFFFFF)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    hubs = int(rng.integers(5, 8))
    pts_list = []; mag_list = []; anc_list = []
    for _ in range(hubs):
        hx = rng.uniform(0.06, 0.94) * w
        hy = rng.uniform(0.06, 0.94) * h
        nk = int(rng.integers(9, 15))
        crad = rng.uniform(0.07, 0.15) * dim
        aa = rng.uniform(0.0, 2.0 * np.pi, nk)
        rr = crad * np.sqrt(rng.uniform(0.04, 1.0, nk))
        mg = rng.uniform(0.40, 0.95, nk)
        an = np.zeros(nk)
        ai = int(rng.integers(0, nk)); mg[ai] = 1.0; an[ai] = 1.0
        pts_list.append(np.stack([hx + rr * np.cos(aa), hy + rr * np.sin(aa)], axis=1))
        mag_list.append(mg); anc_list.append(an)
    pts = np.concatenate(pts_list, axis=0).astype(np.float32)
    mags = np.concatenate(mag_list).astype(np.float32)
    ancs = np.concatenate(anc_list).astype(np.float32)
    npts = int(pts.shape[0])
    d2 = ((pts[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
    np.fill_diagonal(d2, 1e18)
    near = np.argsort(d2, axis=1)[:, :2]
    lim2 = (0.14 * dim) ** 2
    edges = set()
    for i in range(npts):
        for jj in range(2):
            j = int(near[i, jj])
            if d2[i, j] < lim2:
                edges.add((min(i, j), max(i, j)))
    lw = max(1.2, dim * 0.0016)
    off = max(1.6, dim * 0.0024)
    dash_p = max(6.0, dim * 0.0070)
    for (i, j) in sorted(edges):
        a = pts[i]; b = pts[j]
        ab = b - a
        L = float(np.hypot(float(ab[0]), float(ab[1])))
        if L < 4.0:
            continue
        pad = off + lw + 4.0
        x0 = max(0, int(min(a[0], b[0]) - pad)); x1 = min(w, int(max(a[0], b[0]) + pad) + 2)
        y0 = max(0, int(min(a[1], b[1]) - pad)); y1 = min(h, int(max(a[1], b[1]) + pad) + 2)
        if x0 >= x1 or y0 >= y1:
            continue
        xs = xx[:, x0:x1]; ys = yy[y0:y1, :]
        t = np.clip(((xs - a[0]) * ab[0] + (ys - a[1]) * ab[1]) / (L * L), 0.0, 1.0)
        nx = -float(ab[1]) / L; ny = float(ab[0]) / L
        dperp = (xs - a[0]) * nx + (ys - a[1]) * ny
        eg = np.clip(t * L / 6.0, 0, 1) * np.clip((1.0 - t) * L / 6.0, 0, 1)
        dash = 0.5 + 0.5 * np.cos(t * L * (2.0 * np.pi / dash_p))
        s1 = np.clip(1.0 - np.abs(dperp - off) / lw, 0, 1)
        s2 = np.clip(1.0 - np.abs(dperp + off) / lw, 0, 1)
        modt = np.mod(t * L, dash_p) - dash_p * 0.5
        bead = np.clip(1.0 - np.sqrt(dperp * dperp + modt * modt) / (lw * 2.1), 0, 1)
        fil = np.maximum(np.maximum(s1, s2) * (0.46 + 0.22 * dash), bead * 0.70) * eg
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], fil.astype(np.float32))
    aaw = max(1.0, dim * 0.0011)
    mm = 2.0 * np.pi / 5.0
    for idx in range(npts):
        sx = float(pts[idx, 0]); sy = float(pts[idx, 1])
        m = float(mags[idx]); is_anchor = ancs[idx] > 0.5
        R = 0.0145 * dim if is_anchor else (0.0042 + 0.0078 * m) * dim
        rot = float(rng.uniform(0.0, 2.0 * np.pi))
        spike_R = R * (2.6 if is_anchor else 2.0)
        pad = spike_R + 3.0
        x0 = max(0, int(sx - pad)); x1 = min(w, int(sx + pad) + 2)
        y0 = max(0, int(sy - pad)); y1 = min(h, int(sy + pad) + 2)
        if x0 >= x1 or y0 >= y1:
            continue
        dx = xx[:, x0:x1] - sx; dy = yy[y0:y1, :] - sy
        ang = np.arctan2(dy, dx) - rot
        rad = np.hypot(dx, dy)
        a5 = np.abs(np.mod(ang, mm) - mm * 0.5)
        edge = R * (0.40 + 0.60 * (a5 / (mm * 0.5)))
        body = np.clip((edge - rad) / aaw, 0, 1) * (0.86 + 0.14 * m)
        spk = np.power(np.abs(np.cos(2.0 * ang)), 64.0) * np.exp(-((rad / spike_R) ** 2))
        spk = spk * np.clip(rad / (R * 0.6 + 1e-4), 0, 1) * (0.55 if is_anchor else 0.40)
        val = np.maximum(body, spk)
        if is_anchor:
            ring = np.clip(1.0 - np.abs(rad - R * 1.85) / max(1.0, dim * 0.0013), 0, 1) * 0.58
            val = np.maximum(val, ring)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], val.astype(np.float32))
    dust = (rng.random((h, w), dtype=np.float32) > 0.9974).astype(np.float32)
    if h > 2 and w > 2:
        dust[1:, :] = np.maximum(dust[1:, :], dust[:-1, :] * 0.6)
        dust[:, 1:] = np.maximum(dust[:, 1:], dust[:, :-1] * 0.6)
    out = np.maximum(out, dust * 0.34)
    s0 = float(int(seed) % 97)
    bg = np.sin(xx * 0.0061 + yy * 0.0043 + s0) + np.sin(yy * 0.0079 - xx * 0.0036 + s0 * 1.7) + np.sin((xx + yy) * 0.0027 + s0 * 0.6)
    bg = (bg - bg.min()) / float(bg.max() - bg.min() + 1e-6)
    out = np.clip(out + bg * 0.045 + 0.02, 0.0, 1.0).astype(np.float32)
    cc = np.clip(16.0 * (1.0 - out * 0.5), 0, 16).astype(np.uint8)
    return {'pattern_val': out, 'R_range': -118.0, 'M_range': 92.0, 'CC': cc}

def _ign_constel_paint(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None:
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)
    s = pm * 0.95
    h, w = int(shape[0]), int(shape[1])
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    g1 = (int(seed) % 360) * np.pi / 180.0
    g2 = g1 + 2.094
    sel = np.sin((xx * np.cos(g1) + yy * np.sin(g1)) * 0.0046 + (int(seed) % 9)) + 0.6 * np.sin((xx * np.cos(g2) + yy * np.sin(g2)) * 0.0031 - (int(seed) % 7))
    star = np.clip((pv - 0.70) * 3.4, 0, 1)
    web = np.clip((pv - 0.28) * 2.6, 0, 1) * (1.0 - star)
    dust = np.clip((pv - 0.10) * 1.6, 0, 1) * (1.0 - star) * (1.0 - web)
    red = web * np.clip(-sel * 1.2 - 0.12, 0, 1)
    blue = web * np.clip(sel * 1.2 - 0.12, 0, 1)
    wht = web * np.clip(1.0 - np.abs(sel) * 1.6, 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + star * 0.95 * s * mask + red * 0.82 * s * mask + wht * 0.70 * s * mask - blue * 0.10 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + star * 0.93 * s * mask - red * 0.16 * s * mask + wht * 0.70 * s * mask - blue * 0.05 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + star * 0.88 * s * mask - red * 0.10 * s * mask + wht * 0.74 * s * mask + blue * 0.84 * s * mask + dust * 0.26 * s * mask, 0, 1)
    return paint

# --- IGNITION: lfr_ribbon_weave ---
def _ign_ribweave_texture(shape, mask, seed, sm):
    h, w = int(shape[0]), int(shape[1])
    rng = np.random.default_rng((int(seed) + 47201) & 0xFFFFFFFF)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    aaw = max(1.0, dim * 0.0016)
    n = int(rng.integers(14, 20))
    for _ in range(n):
        th = rng.uniform(0.0, 2.0 * np.pi)
        ca = float(np.cos(th)); sa = float(np.sin(th))
        cx = rng.uniform(0.04, 0.96) * w; cy = rng.uniform(0.04, 0.96) * h
        L = rng.uniform(0.50, 0.95) * dim
        hwid = rng.uniform(0.009, 0.017) * dim
        A1 = rng.uniform(0.025, 0.055) * dim
        k1 = 2.0 * np.pi * rng.uniform(1.2, 2.4) / L
        A2 = A1 * rng.uniform(0.20, 0.40)
        k2 = k1 * rng.uniform(2.2, 3.4)
        p1 = rng.uniform(0.0, 2.0 * np.pi); p2 = rng.uniform(0.0, 2.0 * np.pi)
        per = rng.uniform(0.0042, 0.0070) * dim
        shw = dim * 0.0045
        wmax = A1 + A2 + hwid + shw + 4.0
        hx = ca * (L * 0.5 + 4.0); hy = sa * (L * 0.5 + 4.0)
        ox = -sa * wmax; oy = ca * wmax
        xs4 = [cx + hx + ox, cx + hx - ox, cx - hx + ox, cx - hx - ox]
        ys4 = [cy + hy + oy, cy + hy - oy, cy - hy + oy, cy - hy - oy]
        x0 = max(0, int(min(xs4))); x1 = min(w, int(max(xs4)) + 2)
        y0 = max(0, int(min(ys4))); y1 = min(h, int(max(ys4)) + 2)
        if x0 >= x1 or y0 >= y1:
            continue
        xs = xx[:, x0:x1]; ys = yy[y0:y1, :]
        u = (xs - cx) * ca + (ys - cy) * sa
        v = (ys - cy) * ca - (xs - cx) * sa
        act = (np.abs(u) < (L * 0.5 + 2.0)) & (np.abs(v) < wmax)
        if not bool(act.any()):
            continue
        u1 = u[act]; v1 = v[act]
        un = u1 / (L * 0.5)
        tap = hwid * np.power(np.clip(1.0 - un * un, 0.0, 1.0), 0.35)
        v0 = A1 * np.sin(k1 * u1 + p1) + A2 * np.sin(k2 * u1 + p2)
        dvc = np.abs(v1 - v0)
        body = np.clip((tap - dvc) / aaw, 0.0, 1.0)
        twill = 0.72 + 0.28 * (np.clip(np.cos(u1 * (2.0 * np.pi / per) + (v1 - v0) * 0.18) * 3.0, -1.0, 1.0) * 0.5 + 0.5)
        gate = np.clip((tap - aaw * 2.0) / aaw, 0.0, 1.0)
        pip = np.clip(1.0 - np.abs(dvc - tap * 0.84) / max(1.0, dim * 0.0011), 0.0, 1.0) * gate
        st = np.clip(1.0 - dvc / max(1.0, dim * 0.0009), 0.0, 1.0) * (np.cos(u1 * (2.0 * np.pi / (per * 2.0))) > 0.25) * gate
        rib = np.maximum(np.maximum(body * 0.60 * twill, pip * 0.97), st * 0.80)
        osh = np.clip(1.0 - (dvc - tap) / shw, 0.0, 1.0) * (dvc > tap) * np.clip((tap - aaw) / aaw, 0.0, 1.0)
        ow = out[y0:y1, x0:x1]
        sub = ow[act]
        sub = sub * (1.0 - osh * 0.55)
        sub = np.where(body > 0.05, rib, sub)
        ow[act] = sub.astype(np.float32)
    s0 = float(int(seed) % 89)
    bg = np.sin(xx * 0.0057 + yy * 0.0049 + s0) + np.sin(yy * 0.0071 - xx * 0.0031 + s0 * 1.9) + np.sin((xx - yy) * 0.0024 + s0 * 0.7)
    bg = (bg - bg.min()) / float(bg.max() - bg.min() + 1e-6)
    out = np.clip(out + bg * 0.05 + 0.02, 0.0, 1.0).astype(np.float32)
    cc = np.clip(16.0 * (1.0 - out * 0.5), 0, 16).astype(np.uint8)
    return {'pattern_val': out, 'R_range': -102.0, 'M_range': 84.0, 'CC': cc}

def _ign_ribweave_paint(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None:
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)
    s = pm * 0.95
    h, w = int(shape[0]), int(shape[1])
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    g1 = (int(seed) % 360) * np.pi / 180.0
    g2 = g1 + 1.917
    sel = np.sin((xx * np.cos(g1) + yy * np.sin(g1)) * 0.0052 + (int(seed) % 11)) + 0.6 * np.sin((xx * np.cos(g2) + yy * np.sin(g2)) * 0.0034 - (int(seed) % 7))
    pip = np.clip((pv - 0.74) * 3.8, 0, 1)
    body = np.clip((pv - 0.26) * 2.4, 0, 1) * (1.0 - pip)
    red = body * np.clip(-sel * 1.2 - 0.12, 0, 1)
    blue = body * np.clip(sel * 1.2 - 0.12, 0, 1)
    wht = body * np.clip(1.0 - np.abs(sel) * 1.6, 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + pip * 0.90 * s * mask + red * 0.80 * s * mask + wht * 0.72 * s * mask - blue * 0.10 * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + pip * 0.90 * s * mask - red * 0.16 * s * mask + wht * 0.72 * s * mask - blue * 0.05 * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + pip * 0.92 * s * mask - red * 0.10 * s * mask + wht * 0.76 * s * mask + blue * 0.82 * s * mask, 0, 1)
    return paint

# --- IGNITION: lfr_stencil_stars ---
def _ign_stenstar_field(xs, ys, cx, cy, R, rot, k=5, rin=0.40):
    dx = xs - cx
    dy = ys - cy
    ang = np.arctan2(dy, dx)
    rad = np.hypot(dx, dy)
    m = 2.0 * np.pi / k
    av = np.abs(np.mod(ang - rot, m) - m * 0.5)
    edge = R * (rin + (1.0 - rin) * (av / (m * 0.5)))
    return rad / (edge + 1e-4), ang, rad, av

def _ign_stenstar_texture(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.default_rng(int(seed) + 52801)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    pin_d = max(1.6, dim * 0.0024)

    # -- HERO tier: stencil-ring stars + valley bridges + pin-line + spray fan --
    n_hero = int(rng.integers(6, 9))
    for _ in range(n_hero):
        cx = rng.uniform(0.04, 0.96) * w
        cy = rng.uniform(0.04, 0.96) * h
        R = rng.uniform(0.060, 0.175) * dim
        rot = rng.uniform(0.0, 2.0 * np.pi)
        spray_dir = rng.uniform(0.0, 2.0 * np.pi)
        n_rays = int(rng.integers(9, 15))
        ray_ph = rng.uniform(0.0, 2.0 * np.pi)
        rr = R * 2.05 + 2.0
        x0 = max(0, int(cx - rr) - 2); x1 = min(w, int(cx + rr) + 3)
        y0 = max(0, int(cy - rr) - 2); y1 = min(h, int(cy + rr) + 3)
        if x0 >= x1 or y0 >= y1:
            continue
        xs = xx[:, x0:x1]; ys = yy[y0:y1, :]
        d, ang, rad, av = _ign_stenstar_field(xs, ys, cx, cy, R, rot, 5, 0.40)
        ring = ((d < 1.0) & (d > 0.80)).astype(np.float32)
        bridges = (av < (0.05 + 18.0 / max(R, 18.0))).astype(np.float32)
        ring = ring * (1.0 - bridges)
        core = (d < 0.50).astype(np.float32)
        pin = np.clip(1.0 - np.abs(d - 0.645) * (R * 0.5) / pin_d, 0.0, 1.0)
        rel = np.mod(ang - spray_dir + np.pi, 2.0 * np.pi) - np.pi
        gate = np.exp(-(rel / 0.62) ** 2)
        rays = np.power(np.clip(np.cos(ang * n_rays + ray_ph), 0.0, 1.0), 7.0)
        annu = np.exp(-(((rad / (R + 1e-4)) - 1.42) / 0.34) ** 2) * (d > 1.04)
        spray = gate * rays * annu
        star = np.maximum(np.maximum(ring * 0.88, core), pin * 0.78)
        star = np.maximum(star, np.clip(spray, 0.0, 1.0) * 0.50)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], star.astype(np.float32))

    # -- MID tier: solid stencil stamps with engraved pin ring --
    n_mid = int(rng.integers(13, 21))
    for _ in range(n_mid):
        cx = rng.uniform(-0.02, 1.02) * w
        cy = rng.uniform(-0.02, 1.02) * h
        R = rng.uniform(0.030, 0.064) * dim
        rot = rng.uniform(0.0, 2.0 * np.pi)
        rr = R + 2.0
        x0 = max(0, int(cx - rr) - 2); x1 = min(w, int(cx + rr) + 3)
        y0 = max(0, int(cy - rr) - 2); y1 = min(h, int(cy + rr) + 3)
        if x0 >= x1 or y0 >= y1:
            continue
        d, ang, rad, av = _ign_stenstar_field(xx[:, x0:x1], yy[y0:y1, :], cx, cy, R, rot, 5, 0.42)
        body = (d < 1.0).astype(np.float32)
        pinm = np.clip(1.0 - np.abs(d - 0.74) * (R * 0.5) / pin_d, 0.0, 1.0) * body
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1],
                                       np.maximum(body * 0.84, pinm * 0.95).astype(np.float32))

    # -- MICRO tier: scattered 4/5-point spark ticks (9-26px) --
    n_mic = int(rng.integers(150, 230))
    for _ in range(n_mic):
        cx = rng.uniform(0.0, 1.0) * w
        cy = rng.uniform(0.0, 1.0) * h
        R = rng.uniform(0.0022, 0.0062) * dim
        k = 4 if rng.random() < 0.5 else 5
        rot = rng.uniform(0.0, 2.0 * np.pi)
        rr = R + 2.0
        x0 = max(0, int(cx - rr) - 2); x1 = min(w, int(cx + rr) + 3)
        y0 = max(0, int(cy - rr) - 2); y1 = min(h, int(cy + rr) + 3)
        if x0 >= x1 or y0 >= y1:
            continue
        d, ang, rad, av = _ign_stenstar_field(xx[:, x0:x1], yy[y0:y1, :], cx, cy, R, rot, k, 0.34)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], (d < 1.0).astype(np.float32) * 0.82)

    # -- micro grain floor (8px-class spec detail, below all paint thresholds) --
    grain = (np.sin(xx * 0.83 + yy * 0.29 + (int(seed) % 97)) *
             np.sin(yy * 0.71 - xx * 0.31 + 1.7) * 0.5 + 0.5)
    out = np.maximum(out, grain.astype(np.float32) * 0.07)

    val = np.clip(out, 0.0, 1.0).astype(np.float32)
    cc = np.clip(16.0 * (1.0 - val * 0.55), 0, 16).astype(np.uint8)
    return {"pattern_val": val, "R_range": -132.0, "M_range": 104.0, "CC": cc}

def _ign_stenstar_paint(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None:
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)
    s = pm * 0.95
    h, w = shape[:2] if len(shape) > 2 else shape
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    g1 = (int(seed) % 360) * np.pi / 180.0
    g2 = g1 + 2.39996
    zone = (np.sin((xx * np.cos(g1) + yy * np.sin(g1)) * 0.0040 + (int(seed) % 7))
            + 0.8 * np.sin((xx * np.cos(g2) + yy * np.sin(g2)) * 0.0061 - (int(seed) % 5)))
    red = np.clip(-zone * 1.4, 0, 1)
    blue = np.clip(zone * 1.4, 0, 1)
    wht = np.clip(1.0 - np.abs(zone) * 1.6, 0, 1)
    hi = np.clip((pv - 0.62) * 2.8, 0, 1)
    mid = np.clip((pv - 0.26) * 1.9, 0, 1) * (1.0 - hi)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (hi * (red * 0.88 + wht * 0.86 + blue * 0.10)
                                               + mid * (red * 0.42 + wht * 0.20 - blue * 0.05)) * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (hi * (red * 0.16 + wht * 0.88 + blue * 0.16)
                                               + mid * (wht * 0.18 - red * 0.06 - blue * 0.03)) * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (hi * (blue * 0.92 + wht * 0.92 - red * 0.04)
                                               + mid * (blue * 0.46 + wht * 0.20 - red * 0.05)) * s * mask, 0, 1)
    return paint

# --- IGNITION: lfr_liberty_filigree ---
def _ign_libfil_spiral_d(rad, lograd, ang, a, b):
    t = ((lograd - np.log(a)) / b - ang) / (2.0 * np.pi)
    rc = a * np.exp(b * (ang + 2.0 * np.pi * np.round(t)))
    return np.abs(rad - rc)

def _ign_libfil_star(xs, ys, cx, cy, R, rot, k=5, rin=0.42):
    dx = xs - cx
    dy = ys - cy
    ang = np.arctan2(dy, dx) - rot
    rad = np.hypot(dx, dy)
    m = 2.0 * np.pi / k
    av = np.abs(np.mod(ang, m) - m * 0.5)
    edge = R * (rin + (1.0 - rin) * (av / (m * 0.5)))
    return rad / (edge + 1e-4)

def _ign_libfil_texture(shape, mask, seed, sm):
    h, w = shape[:2] if len(shape) > 2 else shape
    rng = np.random.default_rng(int(seed) + 52901)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dim = float(min(h, w))
    out = np.zeros((h, w), dtype=np.float32)
    lw0 = max(1.8, dim * 0.0042)

    # -- HUB tier: S-scroll pair + acanthus fan + pearls + boss + star tips --
    n_hub = int(rng.integers(7, 10))
    for _ in range(n_hub):
        cx = rng.uniform(0.06, 0.94) * w
        cy = rng.uniform(0.06, 0.94) * h
        R = rng.uniform(0.115, 0.215) * dim
        rot = rng.uniform(0.0, 2.0 * np.pi)
        b = rng.uniform(0.16, 0.24)
        a0 = R * rng.uniform(0.055, 0.085)
        rot2 = rot + rng.uniform(1.2, 2.8) * (1.0 if rng.random() > 0.5 else -1.0)
        kp = int(rng.integers(5, 8))
        Rb = R * rng.uniform(0.74, 0.88)
        rr = R * 1.06 + 2.0
        x0 = max(0, int(cx - rr) - 2); x1 = min(w, int(cx + rr) + 3)
        y0 = max(0, int(cy - rr) - 2); y1 = min(h, int(cy + rr) + 3)
        if x0 >= x1 or y0 >= y1:
            continue
        dx = xx[:, x0:x1] - cx; dy = yy[y0:y1, :] - cy
        ang = np.arctan2(dy, dx)
        rad = np.hypot(dx, dy)
        lograd = np.log(np.maximum(rad, 1e-3))
        rn = rad / (R + 1e-4)
        lw = lw0 * (0.35 + 1.05 * rn)
        d1 = _ign_libfil_spiral_d(rad, lograd, ang - rot, a0, b)
        d2 = _ign_libfil_spiral_d(rad, lograd, -(ang - rot), a0, b)
        arm = np.maximum(np.clip(1.0 - d1 / lw, 0, 1), np.clip(1.0 - d2 / lw, 0, 1))
        arm = arm * np.power(np.clip(1.18 - rn, 0, 1), 0.35) * (rn < 1.0)
        relang = np.mod(ang - rot2 + np.pi, 2.0 * np.pi) - np.pi
        fan_gate = (np.abs(relang) < 1.25)
        rl = R * 0.62 * np.power(np.abs(np.cos(kp * relang * 0.5)), 0.75)
        leaf = ((rad < rl) & fan_gate).astype(np.float32)
        hp = max(6.0, dim * 0.0062)
        hatch = (np.abs(np.mod(rad + relang * R * 0.05, hp) - hp * 0.5) < max(1.0, hp * 0.16)).astype(np.float32)
        leaf_v = leaf * 0.50 + leaf * hatch * 0.42
        nb = max(10, int(2.0 * np.pi * Rb / max(8.0, dim * 0.017)))
        ringp = np.exp(-((rad - Rb) / max(2.0, dim * 0.0036)) ** 2)
        beads = np.power(np.clip(np.cos(ang * nb + rot * 3.0), 0, 1), 10.0)
        pearls = ringp * beads
        boss = (rad < R * 0.045).astype(np.float32) * 0.94
        bring = np.clip(1.0 - np.abs(rad - R * 0.085) / max(1.5, lw0 * 0.6), 0, 1) * 0.85
        hub = np.maximum.reduce([arm, leaf_v, pearls, boss, bring])
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], np.clip(hub, 0, 1).astype(np.float32))
        # star terminals at both scroll tips
        the = np.log(0.92 * R / a0) / b
        for sgn in (1.0, -1.0):
            ex = cx + 0.92 * R * np.cos(rot + sgn * the)
            ey = cy + 0.92 * R * np.sin(rot + sgn * the)
            Rs = max(6.0, R * 0.085)
            sx0 = max(0, int(ex - Rs) - 2); sx1 = min(w, int(ex + Rs) + 3)
            sy0 = max(0, int(ey - Rs) - 2); sy1 = min(h, int(ey + Rs) + 3)
            if sx0 >= sx1 or sy0 >= sy1:
                continue
            ds = _ign_libfil_star(xx[:, sx0:sx1], yy[sy0:sy1, :], ex, ey, Rs,
                                  rng.uniform(0.0, 2.0 * np.pi), 5, 0.42)
            out[sy0:sy1, sx0:sx1] = np.maximum(out[sy0:sy1, sx0:sx1],
                                               (ds < 1.0).astype(np.float32) * 0.96)

    # -- MID tier: small comma scrolls scattered between hubs --
    n_mini = int(rng.integers(18, 28))
    lwm = max(1.4, dim * 0.0028)
    for _ in range(n_mini):
        cx = rng.uniform(0.0, 1.0) * w
        cy = rng.uniform(0.0, 1.0) * h
        R = rng.uniform(0.028, 0.052) * dim
        rot = rng.uniform(0.0, 2.0 * np.pi)
        b = rng.uniform(0.18, 0.30)
        rr = R * 1.05 + 2.0
        x0 = max(0, int(cx - rr) - 2); x1 = min(w, int(cx + rr) + 3)
        y0 = max(0, int(cy - rr) - 2); y1 = min(h, int(cy + rr) + 3)
        if x0 >= x1 or y0 >= y1:
            continue
        dx = xx[:, x0:x1] - cx; dy = yy[y0:y1, :] - cy
        ang = np.arctan2(dy, dx)
        rad = np.hypot(dx, dy)
        lograd = np.log(np.maximum(rad, 1e-3))
        rn = rad / (R + 1e-4)
        dmm = _ign_libfil_spiral_d(rad, lograd, ang - rot, R * 0.10, b)
        stroke = np.clip(1.0 - dmm / (lwm * (0.4 + rn)), 0, 1) * (rn < 1.0)
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], (stroke * 0.80).astype(np.float32))

    # -- micro grain floor (engraving tooth, below all paint thresholds) --
    grain = (np.sin(xx * 0.67 + yy * 0.41 + (int(seed) % 89)) *
             np.sin(yy * 0.59 - xx * 0.37 + 0.9) * 0.5 + 0.5)
    out = np.maximum(out, grain.astype(np.float32) * 0.06)

    val = np.clip(out, 0.0, 1.0).astype(np.float32)
    cc = np.clip(16.0 * (1.0 - val * 0.5), 0, 16).astype(np.uint8)
    return {"pattern_val": val, "R_range": -128.0, "M_range": 108.0, "CC": cc}

def _ign_libfil_paint(paint, shape, mask, seed, pm, bb):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    pv = bb.get('pattern_val') if isinstance(bb, dict) else None
    if pv is None:
        pv = mask.astype(np.float32)
    pv = np.clip(pv, 0, 1)
    s = pm * 0.95
    h, w = shape[:2] if len(shape) > 2 else shape
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    g1 = ((int(seed) * 7) % 360) * np.pi / 180.0
    g2 = g1 + 1.94161
    zone = (np.sin((xx * np.cos(g1) + yy * np.sin(g1)) * 0.0036 + (int(seed) % 11))
            + 0.7 * np.sin((xx * np.cos(g2) + yy * np.sin(g2)) * 0.0055 - (int(seed) % 6)))
    t = np.clip(zone * 0.55 + 0.5, 0, 1)
    gold = 1.0 - t
    silv = t
    hi = np.clip((pv - 0.58) * 3.0, 0, 1)
    mid = np.clip((pv - 0.22) * 1.7, 0, 1) * (1.0 - hi)
    pk = np.clip((pv - 0.90) * 9.0, 0, 1)
    paint[:, :, 0] = np.clip(paint[:, :, 0] + (hi * (gold * 0.80 + silv * 0.62) + pk * 0.18
                                               - mid * 0.06) * s * mask, 0, 1)
    paint[:, :, 1] = np.clip(paint[:, :, 1] + (hi * (gold * 0.62 + silv * 0.68) + pk * 0.18
                                               + mid * 0.02) * s * mask, 0, 1)
    paint[:, :, 2] = np.clip(paint[:, :, 2] + (hi * (gold * 0.24 + silv * 0.80) + pk * 0.20
                                               + mid * 0.34) * s * mask, 0, 1)
    return paint

_IGN_TEX_ROUTES = {
    "lfr_star_lattice": _ign_starlat_texture,
    "lfr_stripe_drift": _ign_stripedrift_texture,
    "lfr_bunting_scallop": _ign_buntfan_texture,
    "lfr_distressed_flag": _ign_flagshred_texture,
    "lfr_eagle_crest": _ign_eaglecrest_texture,
    "lfr_firework_radial": _ign_firework_texture,
    "lfr_constellation_field": _ign_constel_texture,
    "lfr_ribbon_weave": _ign_ribweave_texture,
    "lfr_stencil_stars": _ign_stenstar_texture,
    "lfr_liberty_filigree": _ign_libfil_texture,
}
_IGN_PAINT_ROUTES = {
    "lfr_star_lattice": _ign_starlat_paint,
    "lfr_stripe_drift": _ign_stripedrift_paint,
    "lfr_bunting_scallop": _ign_buntfan_paint,
    "lfr_distressed_flag": _ign_flagshred_paint,
    "lfr_eagle_crest": _ign_eaglecrest_paint,
    "lfr_firework_radial": _ign_firework_paint,
    "lfr_constellation_field": _ign_constel_paint,
    "lfr_ribbon_weave": _ign_ribweave_paint,
    "lfr_stencil_stars": _ign_stenstar_paint,
    "lfr_liberty_filigree": _ign_libfil_paint,
}

def _texture_lfr_dispatch(shape, mask, seed, sm, variant, _old=_texture_lfr_dispatch):
    fn = _IGN_TEX_ROUTES.get(variant)
    if fn is not None:
        return fn(shape, mask, seed, sm)
    return _old(shape, mask, seed, sm, variant)

def _paint_lfr_dispatch(paint, shape, mask, seed, pm, bb, variant, _old=_paint_lfr_dispatch):
    fn = _IGN_PAINT_ROUTES.get(variant)
    if fn is not None:
        return fn(paint, shape, mask, seed, pm, bb)
    return _old(paint, shape, mask, seed, pm, bb, variant)
# === IGNITION REBUILD 2026-06-10 END ===
