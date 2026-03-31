"""
engine/expansion_patterns.py - Dedicated texture_fn and paint_fn for each expansion pattern ID.

REWORK 2026-03-06: Each pattern now uses genuine per-variant geometry (not delegated to
unrelated legacy textures). Key categories: Flames, Decades, Music, Astro/Zodiac, Hero, Sport.
"""

from collections import OrderedDict
import numpy as np


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
    n = rng.integers(5, 9)
    for _ in range(n):
        cy      = rng.uniform(0.1, 0.9) * h
        length  = rng.uniform(0.45, 0.92) * w
        base_hw = rng.uniform(0.05, 0.14) * h
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
    noise = _multi_scale_noise_fast(shape, [8, 16, 32], seed + 7)
    for i in range(rng.integers(6, 11)):
        cx     = rng.uniform(0.0, 1.0) * w
        length = rng.uniform(0.55, 0.95) * w
        sigma  = rng.uniform(0.008, 0.022) * h   # very thin
        peak   = rng.uniform(0.35, 0.65)          # keep it ghostly
        x_norm = np.clip(xx / max(length, 1), 0, 1)
        # Wobble driven by noise column
        wobble_amp = h * rng.uniform(0.06, 0.18)
        col_noise  = noise[:, np.clip((xx * noise.shape[1] / w).astype(int),
                                      0, noise.shape[1]-1).reshape(-1)]
        centre_y = (cx * 0 + h * 0.5 +
                    np.sin(x_norm * np.pi * rng.uniform(1.2, 3.5)) * wobble_amp)
        # One row per x: gaussian
        dist     = np.abs(yy[:, None] - centre_y[None, :])
        wisp     = np.exp(-(dist**2) / (2 * sigma**2)) * peak
        wisp    *= (1 - x_norm)[None, :] ** 0.6   # fade at tip
        wisp[:, xx >= length] = 0.0
        out = np.maximum(out, wisp.astype(np.float32))
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
    out = np.zeros((h, w), dtype=np.float32)
    yy = np.arange(h, dtype=np.float32)
    xx = np.arange(w, dtype=np.float32)
    n_cones = rng.integers(7, 13)
    for i in range(n_cones):
        base_x  = rng.uniform(0.02, 0.98) * w
        height  = rng.uniform(0.25, 0.55) * h
        base_hw = rng.uniform(0.018, 0.038) * w   # very narrow
        taper   = rng.uniform(2.8, 4.2)            # sharp tip
        # y = 0 is top of canvas; flame rises from bottom (y = h-1)
        y_from_base = h - 1 - yy                   # 0 at tip, grows downward
        progress    = np.clip(y_from_base / max(height, 1), 0, 1)
        hw_at_y     = base_hw * progress ** 0.45   # widen near base
        # Edge flicker via small noise
        n_col       = _multi_scale_noise_fast(shape, [3, 6], seed + i * 13)
        flicker     = n_col * base_hw * 0.25
        dist        = np.abs(xx[None, :] - base_x - flicker[:, 0:1])
        cone        = np.clip(1.0 - dist / (hw_at_y[:, None] + 1e-4), 0, 1)
        # Only in height range
        cone[y_from_base > height] = 0.0
        # Sharp power taper
        cone        = np.power(cone, taper * (1 - progress[:, None] * 0.5))
        out = np.maximum(out, cone.astype(np.float32))
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
    n_blades = rng.integers(4, 8)
    for i in range(n_blades):
        # Blade centre
        cx   = rng.uniform(0.05, 0.75) * w
        cy   = rng.uniform(0.2, 0.8) * h
        # Half-lengths of the kite along its axes
        a    = rng.uniform(0.10, 0.22) * h   # height half-extent
        b    = rng.uniform(0.025, 0.07) * w  # width half-extent
        lean = rng.uniform(0.25, 0.70)       # lean right (rearward)
        dx   = xx - cx + (yy - cy) * lean    # shear x by lean * dy
        dy   = yy - cy
        # SDF of a kite: |dx|/b + |dy|/a <= 1
        sdf  = 1.0 - (np.abs(dx) / (b + 1e-4) + np.abs(dy) / (a + 1e-4))
        blade = np.clip(sdf * 8.0, 0, 1)    # soft 1-pixel antialiased edge
        out  = np.maximum(out, blade.astype(np.float32))
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
    glow = _multi_scale_noise_fast(shape, [16, 32, 64], seed + 1) * 0.18
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
    """
    h, w = shape
    rng = np.random.default_rng(seed)
    yy = np.arange(h, dtype=np.float32).reshape(-1, 1)
    xx = np.arange(w, dtype=np.float32).reshape(1, -1)
    # Layer 1: heat shimmer base — full canvas
    heat = _multi_scale_noise_fast(shape, [8, 16, 32], seed + 1)
    out  = heat * 0.20
    # Layer 2: dense flame columns (~40)
    for _ in range(40):
        cx      = rng.uniform(-0.05, 1.05) * w
        height  = rng.uniform(0.70, 1.0) * h
        sigma   = rng.uniform(0.025, 0.10) * w
        phase   = rng.uniform(0, 2 * np.pi)
        peak    = rng.uniform(0.50, 1.0)
        y_norm  = np.clip(1.0 - yy / max(height, 1), 0, 1)
        wobble  = (np.sin(yy * 0.055 + phase) * sigma * 0.4 +
                   np.sin(yy * 0.12 + phase * 2.3) * sigma * 0.18)
        dist    = np.abs(xx - cx - wobble)
        col     = np.clip(1.0 - dist / (sigma * y_norm + 1), 0, 1) * y_norm
        out     = np.maximum(out, col.astype(np.float32) * peak)
    # Layer 3: bright base glow
    base_glow = np.clip(1.0 - yy / (h * 0.30), 0, 1) ** 1.8 * 0.4
    out = np.maximum(out, base_glow * np.ones((1, w), dtype=np.float32))
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
    # Two lines: outer (at fill ≈ 0.12) and inner (at fill ≈ 0.55)
    outer = np.exp(-((fill - 0.12) ** 2) / 0.004) * 0.9
    inner = np.exp(-((fill - 0.55) ** 2) / 0.003) * 0.65
    outline = np.clip(outer + inner, 0, 1).astype(np.float32)
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
    out = np.zeros((h, w), dtype=np.float32)
    n_embers = rng.integers(80, 180)
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    for _ in range(n_embers):
        # Bias position toward lower half
        ex     = rng.uniform(0.0, 1.0) * w
        ey     = rng.uniform(0.1, 1.0) ** 0.6 * h   # power < 1 → bottom bias
        r_core = rng.uniform(1.5, 4.5)               # core dot radius px
        r_halo = r_core * rng.uniform(2.5, 5.0)      # soft halo
        peak   = rng.uniform(0.75, 1.0)
        tail_l = rng.uniform(0.04, 0.14) * h          # comet tail length
        # Core dot
        d2 = (xx - ex)**2 + (yy - ey)**2
        core = np.exp(-d2 / (2 * r_core**2)) * peak
        halo = np.exp(-d2 / (2 * r_halo**2)) * peak * 0.35
        # Tail: gaussian elongated downward (y > ey)
        dy    = np.clip(yy - ey, 0, None)            # only below ember
        tail  = np.exp(-(xx - ex)**2 / (2 * r_core**2)) * np.exp(-dy / max(tail_l, 1)) * peak * 0.5
        ember = np.clip(core + halo + tail, 0, 1).astype(np.float32)
        out   = np.maximum(out, ember)
    # Very faint ambient shimmer
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
    n_pairs = rng.integers(3, 6)
    for i in range(n_pairs):
        # Each pair: two tongues mirrored about a vertical centre axis
        cy_top  = rng.uniform(0.2, 0.45) * h
        cy_bot  = h - cy_top
        x_start = rng.uniform(0.0, 0.4) * w
        x_end   = rng.uniform(0.6, 1.0) * w
        length  = x_end - x_start
        base_hw = rng.uniform(0.05, 0.10) * h
        split_k = rng.uniform(0.18, 0.42)  # how far apart the lobes spread
        peak    = rng.uniform(0.65, 1.0)
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
    smoke = _multi_scale_noise_fast(shape, [6, 12, 24], seed + 50)
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
        # Rightward ">" chevron: interior-fill cone, vertex at right, opening at left — WARN-EXPAND-001 FIX
        # clip(0.18 - (|Y| - X*0.7), 0, 1) * (X>0): bright inside cone abs(Y) < X*0.7, tip at right edge
        Y, X = _get_grid(shape)
        arrow = np.clip(0.18 - (np.abs(Y) - X * 0.7), 0, 1) * (X > 0).astype(np.float32)
        return _pack(arrow.astype(np.float32), -100, 80)
    if "music_wing_sweep" in variant:
        Y, X = _get_grid(shape)
        # Wing: broad sweep from centre-right, curving up
        wing = np.clip(1 - np.abs(Y - X * 0.5) * 3, 0, 1) * (X > -0.2).astype(np.float32)
        return _pack(wing, -100, 80)
    if "music_script_curve" in variant:
        Y, X = _get_grid(shape)
        script = np.exp(-(Y - np.sin(X * np.pi * 1.5) * 0.35) ** 2 / 0.012)
        return _pack(np.clip(script, 0, 1), -60, 60)
    if "music_skull_abstract" in variant:
        e2 = _engine()
        return e2.texture_skull(shape, mask, seed, sm) if hasattr(e2, 'texture_skull') else _pack(_noise_simple(shape, seed, 8), -60, 40)
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
        # Blues: rolling sine-wave staff lines — notes flowing across
        Y2, X2 = _get_grid(shape)
        val = (np.sin(Y2 * np.pi * 6 + np.sin(X2 * np.pi * 2) * 0.8) * 0.5 + 0.5).astype(np.float32)
        return _pack(val, -80, 60)
    if "music_strat" in variant:
        # Stratocaster: contoured body double-curve silhouette
        Y2, X2 = _get_grid(shape)
        c1 = np.exp(-(np.abs(Y2 - np.sin(X2 * np.pi * 0.8) * 0.35))**2 / 0.015)
        c2 = np.exp(-(np.abs(Y2 + np.sin(X2 * np.pi * 0.6) * 0.25))**2 / 0.015)
        return _pack(np.clip(c1 + c2, 0, 1).astype(np.float32), -100, 80)
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
        return _pack(np.clip(ring + leye + reye, 0, 1).astype(np.float32), -120, 80)
    if "music_licked" in variant:
        # KISS tongue: bold downward-curved band (Simmons-style tongue logo)
        Y2, X2 = _get_grid(shape)
        tongue = np.exp(-(X2**2 * 12 + (Y2 + 0.1 + X2**2 * 0.5)**2 * 5))
        return _pack(np.clip(tongue, 0, 1).astype(np.float32), -120, 80)

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
        arch = np.clip(1 - np.abs(Y - (-X**2 * 0.4 + 0.3)) * 6, 0, 1)
        return _pack(arch, -80, 80)
    if "hero_scallop_edge" in variant:
        # Batman-ish scalloped lower edge
        h2, w2 = shape
        val = np.zeros((h2, w2), dtype=np.float32)
        n_scallops = 7
        for i in range(n_scallops):
            cx = int(w2 * (i + 0.5) / n_scallops)
            cy = int(h2 * 0.62)
            r = int(w2 / (n_scallops * 2))
            Y2, X2 = np.ogrid[:h2, :w2]
            scallop = ((X2 - cx)**2 + (Y2 - cy)**2 <= r**2).astype(np.float32)
            val = np.maximum(val, scallop)
        return _pack(val, -120, 0)
    if "hero_pointed_cowl" in variant:
        Y, X = _get_grid(shape)
        # Two pointed upward triangles like bat ears
        left_ear = np.clip(1 - np.abs(X + 0.4) * 4 - np.abs(Y + 0.5) * 2, 0, 1) * (Y < -0.1).astype(np.float32)
        right_ear = np.clip(1 - np.abs(X - 0.4) * 4 - np.abs(Y + 0.5) * 2, 0, 1) * (Y < -0.1).astype(np.float32)
        return _pack(np.clip(left_ear + right_ear, 0, 1), -120, 0)
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
    e = _engine()
    seed_off = hash(variant) % 10000

    # Flames → dedicated flame gradient paint
    if variant.startswith("flame_"):
        return _paint_flame(paint, shape, mask, seed, pm, bb, variant)

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
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
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
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
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
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
    pv = _reactive_candy_depth((h, w), seed=seed)
    # Candy effect: saturate and darken proportionally to depth
    lum = (p[:, :, 0] + p[:, :, 1] + p[:, :, 2]) / 3.0
    # In dark regions (low pv = cell edges), darken paint
    darken = (1.0 - pv) * pm * 0.4
    p *= (1.0 - darken)[:, :, np.newaxis]
    # In bright regions (high pv = cell centers), boost saturation
    sat_boost = pv * pm * 0.5
    for c in range(3):
        p[:, :, c] = lum + (p[:, :, c] - lum) * (1.0 + sat_boost)
    return np.clip(p, 0, 255).astype(np.float32)


def _paint_reactive_chrome_veil(paint, shape, mask, seed, pm, bb):
    """Chrome veil paint: mirror-like reflection blending toward white in smooth
    pools and dark in fold creases."""
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
    pv = _reactive_chrome_veil((h, w), seed=seed)
    # Chrome: blend toward pure white in reflective areas, desaturate everywhere
    chrome_white = pv * pm * 80.0
    # Desaturate proportionally (chrome is mostly achromatic)
    lum = (p[:, :, 0] + p[:, :, 1] + p[:, :, 2]) / 3.0
    desat = pm * 0.6 * pv
    for c in range(3):
        p[:, :, c] = p[:, :, c] * (1.0 - desat) + lum * desat + chrome_white
    # Darken creases (low pv areas)
    crease_dark = (1.0 - pv) * pm * 0.3
    p *= (1.0 - crease_dark)[:, :, np.newaxis]
    return np.clip(p, 0, 255).astype(np.float32)


def _paint_reactive_spectra_ripple(paint, shape, mask, seed, pm, bb):
    """Spectral ripple paint: prismatic color fringing along interference fringes."""
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
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
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
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
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
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
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
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
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
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
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
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
    """VORONOI FACETS: random cell centers, per-cell random brightness, dark edges."""
    h, w = shape
    rng = np.random.default_rng(seed)
    n_pts = 42 + rng.integers(0, 14)
    pts_y = (rng.random(n_pts).astype(np.float32) * 2.0 - 1.0)
    pts_x = (rng.random(n_pts).astype(np.float32) * 2.0 - 1.0)
    cell_bright = rng.uniform(0.25, 1.0, size=n_pts).astype(np.float32)
    yy = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    xx = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    d_min = np.full((h, w), np.inf, dtype=np.float32)
    d_second = np.full((h, w), np.inf, dtype=np.float32)
    nearest_id = np.zeros((h, w), dtype=np.int32)
    for i in range(n_pts):
        d = np.sqrt((yy - pts_y[i])**2 + (xx - pts_x[i])**2)
        update = d < d_min
        d_second = np.where(update, d_min, np.minimum(d_second, d))
        nearest_id = np.where(update, i, nearest_id)
        d_min = np.where(update, d, d_min)
    edge = np.clip((d_second - d_min) * 12.0, 0.0, 1.0)
    out = (1.0 - edge) * cell_bright[nearest_id]
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


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
    """PURE FBM: multi-scale noise only — no single dominant frequency, no sine grids."""
    n1 = _noise_simple(shape, seed=seed + 31, scale=5.0)
    n2 = _noise_simple(shape, seed=seed + 32, scale=14.0)
    n3 = _noise_simple(shape, seed=seed + 33, scale=38.0)
    n4 = _noise_simple(shape, seed=seed + 34, scale=95.0)
    v = n1 * 0.45 + n2 * 0.30 + n3 * 0.18 + n4 * 0.07
    v = (v - v.min()) / (v.max() - v.min() + 1e-8)
    return np.power(np.clip(v, 0.0, 1.0), 1.2).astype(np.float32)


def _shimmer_chrome_flux(shape, seed=0):
    """ANISOTROPIC STREAKS: noise smeared along one axis — horizontal brush streaks."""
    h, w = shape
    raw = _noise_simple(shape, seed=seed + 41, scale=18.0)
    # Smear along rows (axis 0) to create horizontal streaks
    out = (raw + np.roll(raw, 5, axis=0) + np.roll(raw, -5, axis=0) +
           np.roll(raw, 11, axis=0) + np.roll(raw, -11, axis=0)) / 5.0
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _shimmer_matte_halo(shape, seed=0):
    """RADIAL HARD BANDS: concentric rings from floor(r*freq + noise), binary bands — no sin(r)."""
    Y, X = _get_grid(shape)
    r = np.sqrt(X * X + Y * Y)
    n = _noise_simple(shape, seed=seed + 51, scale=2.5) * 0.35
    band = np.floor(r * 24.0 + n).astype(np.int32) % 2
    v = band.astype(np.float32)
    # Soften band edges slightly
    frac = (r * 24.0 + n) % 1.0
    v = v * (1.0 - frac) + (1.0 - v) * frac
    return np.clip(v, 0.0, 1.0).astype(np.float32)


def _shimmer_oil_tension(shape, seed=0):
    """CIRCULAR THIN-FILM: rings from radius + noise (Newton-style), sawtooth per ring — no sin."""
    Y, X = _get_grid(shape)
    r = np.sqrt(X * X + Y * Y)
    n = _noise_simple(shape, seed=seed + 61, scale=2.0) * 0.08
    ring_phase = ((r + n) * 32.0) % 1.0
    v = ring_phase.astype(np.float32)
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
    """POINT SPRITES: scattered Gaussian blobs — each point adds exp(-dist^2/sigma^2)."""
    h, w = shape
    rng = np.random.default_rng(seed)
    n_pts = 26
    pts_y = (rng.random(n_pts).astype(np.float32) * 2.0 - 1.0)
    pts_x = (rng.random(n_pts).astype(np.float32) * 2.0 - 1.0)
    yy = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    xx = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    # (n_pts, h, w) distance squared
    dy = yy - pts_y.reshape(-1, 1, 1)
    dx = xx - pts_x.reshape(-1, 1, 1)
    dist_sq = dy * dy + dx * dx
    sigma = 0.11
    out = np.exp(-0.5 * dist_sq / (sigma * sigma)).sum(axis=0).astype(np.float32)
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _shimmer_turbine_sheen(shape, seed=0):
    """LOG-SPIRAL ARMS: binary arms from (angle + k*log(r)) % 2pi — no sin(angle)."""
    Y, X = _get_grid(shape)
    ang = np.arctan2(Y, X)
    r = np.sqrt(X * X + Y * Y) + 0.25
    spiral_phase = (ang + 1.7 * np.log(r + 0.2)) % (2.0 * np.pi)
    # Arm = band around phase pi
    arm = 1.0 - np.clip(np.abs(spiral_phase - np.pi) / 0.5, 0.0, 1.0)
    return np.clip(arm.astype(np.float32), 0.0, 1.0)


def _shimmer_spectral_mesh(shape, seed=0):
    """DISTANCE-TO-LINES: three families of parallel lines at 0°, 60°, 120° — triangular mesh."""
    Y, X = _get_grid(shape)
    rng = np.random.default_rng(seed)
    line_width = 0.035
    spacing = 0.08
    phases = rng.uniform(0, spacing, size=3).astype(np.float32)
    angles = np.array([0.0, np.pi / 3.0, 2.0 * np.pi / 3.0], dtype=np.float32)
    out = np.zeros((shape[0], shape[1]), dtype=np.float32)
    for i in range(3):
        a = angles[i]
        p = phases[i]
        proj = X * np.cos(a) + Y * np.sin(a) + p
        # Distance to nearest line (periodic with spacing)
        proj_mod = (proj + 2.0) % spacing - spacing * 0.5
        dist = np.abs(proj_mod)
        line_val = np.maximum(0.0, 1.0 - dist / line_width)
        out = np.maximum(out, line_val.astype(np.float32))
    out = (out - out.min()) / (out.max() - out.min() + 1e-8)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


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
    if pm == 0.0:
        return paint[:, :, :3].astype(np.float32)
    h, w = shape[:2] if len(shape) > 2 else shape
    p = paint[:, :, :3].astype(np.float32).copy()
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
        p *= (1.0 - np.clip(pv, 0.0, 1.0) * pm * 0.12)[:, :, np.newaxis]
    elif variant == "shimmer_chrome_flux":
        lift = np.power(np.clip(pv, 0.0, 1.0), 0.6) * pm
        p += (lift * 28.0)[:, :, np.newaxis]
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
        spark = np.clip((pv - 0.82) / 0.18, 0.0, 1.0) * pm
        p += (spark * 54.0)[:, :, np.newaxis]
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

