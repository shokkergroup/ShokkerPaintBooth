# -*- coding: utf-8 -*-
"""
engine/paint_v2/ceramic_glass_2026.py — ★ CERAMIC & GLASS (rebuild 2026-06-14)

Owner mandate: the old ceramic/glass were plain and the specs didn't read as glass.
This rebuild gives real glassy DEPTH (Beer-Lambert colored tint), fine MICROFACET
sparkle, CRACKLE networks, frost, and antique mercury mottle — with DIELECTRIC specs
that actually read wet-glass (M=0, low R, CC=16) vs matte ceramic (high R/CC). 20
finishes, color-diverse: clear/tempered + stained/sea/sapphire/ruby/emerald/amber/
smoked/milk/mercury glass + obsidian + white-glaze/matte/enamel/porcelain + teal raku
crackle + cobalt liquid glaze + terracotta + piano black.

Contracts (same as the rest of the engine):
  paint_x(paint, shape, mask, seed, pm, bb) -> HxWx3 float 0..1  (static fine-detail albedo)
  spec_x(shape, seed, sm, base_m, base_r)  -> (M, R, CC) float32 0..255  (R>=15, M<=255)
Dielectric M (flat 0) for glass/ceramic = trivially decorrelated; mercury rides a
mottle field on M with R on an independent grain field. <3s @2048.
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid, _resize_array
from engine.color_science import candy_absorb

_CG_CACHE = {}


def _cache(key, fn):
    v = _CG_CACHE.get(key)
    if v is None:
        if len(_CG_CACHE) > 160:
            _CG_CACHE.clear()
        v = fn()
        _CG_CACHE[key] = v
    return v


def _norm01(a):
    a = np.asarray(a, dtype=np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _broad(shape, scales, weights, seed, cap=640):
    h, w = shape[:2]
    key = ("b", h, w, tuple(scales), tuple(weights), int(seed), int(cap))

    def build():
        work = min(int(cap), h, w)
        if work < min(h, w):
            sh = max(64, int(round(h * work / max(h, w))))
            sw = max(64, int(round(w * work / max(h, w))))
            f = multi_scale_noise((sh, sw), scales, weights, seed)
            return _resize_array(np.asarray(f, np.float32), h, w)
        return np.asarray(multi_scale_noise((h, w), scales, weights, seed), np.float32)

    return _cache(key, build)


def _grain(shape, seed):
    h, w = shape[:2]
    key = ("g", h, w, int(seed))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x2B7F) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        n = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0) + np.roll(n, 1, 1) + np.roll(n, -1, 1)) * 0.2
        return n.astype(np.float32)

    return _cache(key, build)


def _facets(shape, seed, density, lo=0.30):
    """Fine microfacet glints — crisp sub-pixel glass sparkle (full-res)."""
    h, w = shape[:2]
    key = ("fc", h, w, int(seed), float(density), float(lo))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x6D1B) & 0xFFFFFFFF)
        n = min(int(h * w * float(density)), 150000)
        out = np.zeros((h, w), np.float32)
        if n > 0:
            yy = rng.integers(0, h, n); xx = rng.integers(0, w, n)
            out[yy, xx] = rng.uniform(lo, 1.0, n).astype(np.float32)
            out = np.maximum.reduce([out, np.roll(out, 1, 0) * 0.4, np.roll(out, 1, 1) * 0.4])
        return out.astype(np.float32)

    return _cache(key, build)


def _crackle(shape, seed, cells):
    """Crisp thin crack-network = Voronoi cell EDGES (where the two nearest seed
    distances are ~equal). Built at a work-res with cKDTree then resized. 0 flat, 1 on
    a crack line. `cells` = number of cells (more = denser, finer cracks)."""
    from scipy.spatial import cKDTree
    h, w = shape[:2]
    key = ("cr2", h, w, int(seed), int(cells))

    def build():
        work = 1280
        sh = work if h >= w else max(64, int(round(work * h / w)))
        sw = work if w >= h else max(64, int(round(work * w / h)))
        sh = min(sh, h); sw = min(sw, w)
        rng = np.random.default_rng((int(seed) ^ 0x55AA) & 0xFFFFFFFF)
        n = max(8, int(cells))
        pts = np.column_stack([rng.uniform(0, sh, n), rng.uniform(0, sw, n)]).astype(np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw]
        grid = np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float32)
        d, _ = cKDTree(pts).query(grid, k=2, workers=-1)
        d1 = d[:, 0].reshape(sh, sw); d2 = d[:, 1].reshape(sh, sw)
        width = (sh + sw) / (2.0 * np.sqrt(n)) * 0.05 + 0.8     # line width ~ cell size
        edge = np.clip(1.0 - (d2 - d1) / max(width, 0.8), 0, 1).astype(np.float32)
        if (sh, sw) != (h, w):
            edge = _resize_array(edge, h, w)
        return np.clip(edge, 0, 1).astype(np.float32)

    return _cache(key, build)


# =====================================================================
# ONE surface core handles glass + ceramic (params pick the behaviour)
# =====================================================================

def _surface(paint, shape, mask, seed, pm, bb, color, tint=None, depth=0.0, facet=0.45,
             frost=0.0, crackle=0.0, crackle_rgb=(0.02, 0.02, 0.03), crackle_cells=240,
             mottle=0.0, mottle_rgb=(0.90, 0.90, 0.93)):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    paint = paint.astype(np.float32)
    h, w = shape[:2]
    col = np.empty((h, w, 3), np.float32)
    col[:] = np.asarray(color, np.float32)

    if depth > 0:                                      # subsurface depth mottle (gentle)
        d = _norm01(_broad((h, w), [12, 26], [0.5, 0.5], seed + 11))
        col = col * (1.0 - depth * 0.16 * (d[:, :, None] - 0.5) * 2.0)
    if tint is not None:                               # colored-glass Beer-Lambert depth
        dd = np.full((h, w), 0.9, np.float32)
        col = candy_absorb(col, np.asarray(tint, np.float32), dd, 1.0)
    if mottle > 0:                                     # antique silvered mercury patches
        mt = _norm01(_broad((h, w), [8, 18, 40], [0.4, 0.35, 0.25], seed + 21))
        wsil = np.clip((mt - 0.35) * 1.8, 0, 1)[:, :, None] * mottle
        col = col * (1 - wsil) + np.asarray(mottle_rgb, np.float32)[None, None, :] * wsil
        col = col * (1 - _facets((h, w), seed + 22, 0.004, lo=0.4)[:, :, None] * mottle * 0.5)
    if facet > 0:                                      # crisp microfacet glints
        col = np.clip(col + _facets((h, w), seed + 5, 0.018)[:, :, None] * facet * 0.5, 0, 1)
    if frost > 0:                                      # milky frosted veil
        fr = _grain((h, w), seed + 7)
        col = col * (1 - frost * 0.22) + 0.90 * frost * 0.22 + (fr[:, :, None] - 0.5) * frost * 0.06
    if crackle > 0:                                    # dark crack lines
        cr = _crackle((h, w), seed + 61, crackle_cells)[:, :, None]
        col = col * (1 - cr * crackle) + np.asarray(crackle_rgb, np.float32)[None, None, :] * cr * crackle
    col = np.clip(col, 0, 1).astype(np.float32)
    m = mask[:, :, None]
    return col * m + paint * (1 - m)


def _surface_spec(shape, seed, sm, base_m, base_r, r_base=18.0, r_amp=12.0, cc=16.0,
                  m_flat=0.0, facet=0.45, frost=0.0, crackle=0.0, crackle_cells=240, mottle=0.0):
    h, w = shape[:2]
    grain = _grain((h, w), seed + 5)
    R = r_base + r_amp * (grain - 0.5) * 2.0 * sm
    if facet > 0:                                      # microfacet pins read sharper (lower R)
        R = R - np.clip(_facets((h, w), seed + 5, 0.018), 0, 1) * facet * 8.0 * sm
    if crackle > 0:
        R = R + _crackle((h, w), seed + 61, crackle_cells) * crackle * 70.0 * sm
    if frost > 0:
        R = R + frost * 42.0
    R = np.clip(R, 15, 255)
    if mottle > 0:                                     # silvered patches are metallic
        mt = _norm01(_broad((h, w), [8, 18, 40], [0.4, 0.35, 0.25], seed + 21))
        M = np.clip(m_flat + np.clip((mt - 0.35) * 1.8, 0, 1) * 205.0 * sm, 0, 255)
    else:
        M = np.full((h, w), float(m_flat), np.float32)
    CCv = np.full((h, w), float(cc), np.float32)
    return M.astype(np.float32), R.astype(np.float32), CCv.astype(np.float32)


# =====================================================================
# THE 20
# =====================================================================
# ---- GLASS ----
def paint_crystal_clear(paint, shape, mask, seed, pm, bb):
    return _surface(paint, shape, mask, seed, pm, bb, (0.86, 0.90, 0.93), depth=0.40, facet=0.50)
def spec_crystal_clear(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=16, r_amp=7, facet=0.50)

def paint_tempered_glass(paint, shape, mask, seed, pm, bb):
    return _surface(paint, shape, mask, seed, pm, bb, (0.84, 0.88, 0.91), depth=0.40, facet=0.45, crackle=0.12)
def spec_tempered_glass(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=18, r_amp=8, facet=0.45, crackle=0.12)

def paint_cathedral_glass(paint, shape, mask, seed, pm, bb):     # stained violet cathedral
    return _surface(paint, shape, mask, seed, pm, bb, (0.62, 0.50, 0.78), tint=(0.45, 0.10, 0.62),
                    depth=0.45, facet=0.60, crackle=0.18, crackle_rgb=(0.05, 0.02, 0.08))
def spec_cathedral_glass(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=18, r_amp=9, facet=0.60, crackle=0.18)

def paint_sea_glass(paint, shape, mask, seed, pm, bb):           # frosted seafoam
    return _surface(paint, shape, mask, seed, pm, bb, (0.58, 0.80, 0.74), depth=0.30, facet=0.25, frost=0.70)
def spec_sea_glass(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=55, r_amp=18, facet=0.25, frost=0.70, cc=40)

def paint_sapphire_glass(paint, shape, mask, seed, pm, bb):      # deep blue gem
    return _surface(paint, shape, mask, seed, pm, bb, (0.50, 0.60, 0.85), tint=(0.04, 0.12, 0.62),
                    depth=0.45, facet=0.62)
def spec_sapphire_glass(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=17, r_amp=8, facet=0.62)

def paint_ruby_glass(paint, shape, mask, seed, pm, bb):          # deep red gem
    return _surface(paint, shape, mask, seed, pm, bb, (0.85, 0.50, 0.50), tint=(0.62, 0.02, 0.08),
                    depth=0.45, facet=0.62)
def spec_ruby_glass(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=17, r_amp=8, facet=0.62)

def paint_emerald_glass(paint, shape, mask, seed, pm, bb):       # deep green gem
    return _surface(paint, shape, mask, seed, pm, bb, (0.50, 0.80, 0.60), tint=(0.02, 0.42, 0.16),
                    depth=0.45, facet=0.62)
def spec_emerald_glass(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=17, r_amp=8, facet=0.62)

def paint_amber_glass(paint, shape, mask, seed, pm, bb):         # honey amber gem
    return _surface(paint, shape, mask, seed, pm, bb, (0.90, 0.72, 0.42), tint=(0.78, 0.42, 0.04),
                    depth=0.45, facet=0.58)
def spec_amber_glass(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=18, r_amp=8, facet=0.58)

def paint_smoked_glass(paint, shape, mask, seed, pm, bb):        # charcoal translucent
    return _surface(paint, shape, mask, seed, pm, bb, (0.24, 0.24, 0.27), tint=(0.12, 0.12, 0.14),
                    depth=0.45, facet=0.42)
def spec_smoked_glass(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=17, r_amp=8, facet=0.42)

def paint_milk_glass(paint, shape, mask, seed, pm, bb):          # opaque milky white
    return _surface(paint, shape, mask, seed, pm, bb, (0.90, 0.91, 0.92), depth=0.22, facet=0.22, frost=0.50)
def spec_milk_glass(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=45, r_amp=15, facet=0.22, frost=0.50, cc=30)

def paint_mercury_glass(paint, shape, mask, seed, pm, bb):       # antique silvered mercury
    return _surface(paint, shape, mask, seed, pm, bb, (0.55, 0.56, 0.60), mottle=0.85, facet=0.50, depth=0.2)
def spec_mercury_glass(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=24, r_amp=12, facet=0.50, mottle=0.85)

def paint_obsidian(paint, shape, mask, seed, pm, bb):            # black volcanic glass
    """Near-black volcanic glass married to the authored fine spec topology."""
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    paint = paint.astype(np.float32)
    h, w = shape[:2]
    authored_m, authored_r, authored_cc = _obsidian_spec_layers((h, w), seed)

    # SPB-105 / TWENTY WINS Win A3: the paint now reveals the same six fine
    # conchoidal mark families as spec.  Eight dark value tiers plus independent
    # cool/warm tint shifts keep it recognizably obsidian, not colored confetti.
    mn = np.clip((authored_m - 4.0) / 240.0, 0.0, 1.0)
    rn = np.clip((authored_r - 15.0) / 169.0, 0.0, 1.0)
    cn = np.clip((authored_cc - 16.0) / 216.0, 0.0, 1.0)
    shade = 0.032 + 0.205 * mn + 0.050 * (1.0 - rn) + 0.040 * cn
    effect = np.empty((h, w, 3), np.float32)
    effect[:, :, 0] = shade * (0.955 + 0.045 * cn)
    effect[:, :, 1] = shade * (0.972 + 0.028 * (1.0 - mn))
    effect[:, :, 2] = shade * (1.015 + 0.055 * (1.0 - rn))
    effect = np.clip(effect, 0.0, 1.0)

    strength = float(np.clip(pm, 0.0, 1.0))
    inside = paint * (1.0 - strength) + effect * strength
    m3 = np.clip(mask.astype(np.float32), 0.0, 1.0)[:, :, None]
    return (inside * m3 + paint * (1.0 - m3)).astype(np.float32)


def _obsidian_spec_layers(shape, seed):
    """Dense, fine conchoidal-glass marks with independently shaded channels."""
    h, w = shape[:2]
    key = ("obsidian-spec-v2", h, w, int(seed))

    def build():
        # Every authored field stays in the owner's 8-32 px band at 2048.  The
        # different transforms make six legible mark families rather than one
        # noise field recolored three times: shards, ridges, sweeps, arcs, pits,
        # and flecks.
        shards = _norm01(multi_scale_noise((h, w), [16, 24, 32], [0.42, 0.34, 0.24], seed + 270))
        fracture = _norm01(multi_scale_noise((h, w), [12, 20, 28], [0.45, 0.35, 0.20], seed + 271))
        warp = _norm01(multi_scale_noise((h, w), [16, 24], [0.58, 0.42], seed + 272))
        pits = _norm01(multi_scale_noise((h, w), [8, 12], [0.62, 0.38], seed + 273))

        # Fine conchoidal shard boundaries.  They are clipped into independent
        # 16-30 px windows below so no ridge can become a canvas-long cord.
        ridge_core = np.abs(fracture - np.roll(fracture, 4, axis=0))
        ridge_core += np.abs(fracture - np.roll(fracture, 4, axis=1))
        ridge_core = _norm01(ridge_core)
        ridges = np.maximum.reduce([
            ridge_core,
            np.roll(ridge_core, 4, axis=0),
            np.roll(ridge_core, -4, axis=0),
            np.roll(ridge_core, 4, axis=1),
            np.roll(ridge_core, -4, axis=1),
        ]).astype(np.float32)

        yy = np.arange(h, dtype=np.float32)[:, None]
        xx = np.arange(w, dtype=np.float32)[None, :]

        # Local shell sweeps: one independently rotated/curved 8-12 x 16-28 px
        # capsule per jittered 32 px cell.  The earlier global sine had the right
        # 24 px spacing but its marks ran hundreds of pixels; owner doctrine says
        # BOTH axes of every primitive must stay fine.
        tile_px = 32
        cells_y = (h + tile_px - 1) // tile_px
        cells_x = (w + tile_px - 1) // tile_px
        cell_rng = np.random.default_rng((int(seed) ^ 0x0B51D1A) & 0xFFFFFFFF)

        def expand_cells(values):
            return np.repeat(np.repeat(values, tile_px, axis=0), tile_px, axis=1)[:h, :w]

        cell_angle = cell_rng.uniform(0.0, np.pi, (cells_y, cells_x)).astype(np.float32)
        ca = expand_cells(np.cos(cell_angle).astype(np.float32))
        sa = expand_cells(np.sin(cell_angle).astype(np.float32))
        jitter_x = expand_cells(cell_rng.uniform(-2.0, 2.0, (cells_y, cells_x)).astype(np.float32))
        jitter_y = expand_cells(cell_rng.uniform(-2.0, 2.0, (cells_y, cells_x)).astype(np.float32))
        local_x = np.mod(xx, float(tile_px)) - tile_px * 0.5 - jitter_x
        local_y = np.mod(yy, float(tile_px)) - tile_px * 0.5 - jitter_y
        along = ca * local_x + sa * local_y
        across = -sa * local_x + ca * local_y
        half_length = expand_cells(cell_rng.uniform(8.0, 14.0, (cells_y, cells_x)).astype(np.float32))
        half_width = expand_cells(cell_rng.uniform(4.5, 6.0, (cells_y, cells_x)).astype(np.float32))
        curve = expand_cells(cell_rng.uniform(-3.0, 3.0, (cells_y, cells_x)).astype(np.float32))
        across = across + curve * np.square(np.clip(along / half_length, -1.0, 1.0))
        capsule_edge = np.maximum(np.abs(along) / half_length, np.abs(across) / half_width)
        cell_shade = expand_cells(cell_rng.uniform(0.72, 1.0, (cells_y, cells_x)).astype(np.float32))
        sweeps = (np.clip(1.0 - capsule_edge, 0.0, 1.0) * cell_shade).astype(np.float32)

        # Independent 16-30 x 10-20 px ellipse windows break the fracture ridge
        # network into locally shaded chips without imposing another orientation.
        ridge_jx = expand_cells(cell_rng.uniform(-2.0, 2.0, (cells_y, cells_x)).astype(np.float32))
        ridge_jy = expand_cells(cell_rng.uniform(-2.0, 2.0, (cells_y, cells_x)).astype(np.float32))
        ridge_a = expand_cells(cell_rng.uniform(8.0, 15.0, (cells_y, cells_x)).astype(np.float32))
        ridge_b = expand_cells(cell_rng.uniform(5.0, 10.0, (cells_y, cells_x)).astype(np.float32))
        ridge_radius = np.square((np.mod(xx, float(tile_px)) - tile_px * 0.5 - ridge_jx) / ridge_a)
        ridge_radius += np.square((np.mod(yy, float(tile_px)) - tile_px * 0.5 - ridge_jy) / ridge_b)
        ridges *= np.clip(1.0 - ridge_radius, 0.0, 1.0).astype(np.float32)
        del ca, sa, jitter_x, jitter_y, local_x, local_y, along, across, half_length, half_width
        del curve, capsule_edge, cell_shade, ridge_jx, ridge_jy, ridge_a, ridge_b, ridge_radius

        # Staggered 32 px shell cells supply partial 8-16 px arcs/rings.  The
        # independent shard gate breaks the lattice before it can read as a tile.
        tile = float(tile_px)
        row = np.floor((yy + float(int(seed) % 31)) / tile)
        row_shift = np.mod(row, 2.0) * (tile * 0.5)
        rx = np.mod(xx + row_shift + float(int(seed) % 29), tile) - tile * 0.5
        ry = np.mod(yy + float((int(seed) * 3) % 29), tile) - tile * 0.5
        radius = np.sqrt(rx * rx + ry * ry)
        rings = 0.5 + 0.5 * np.cos((radius + (warp - 0.5) * 3.0) * (2.0 * np.pi / 10.0))
        arcs = (rings * np.clip((shards - 0.28) * 1.55, 0.0, 1.0)).astype(np.float32)

        # Flecks are 8 px chips cut from two independent fine fields, not
        # one-pixel salt-and-pepper sparkle.
        flecks = _norm01(np.abs(pits - np.roll(shards, 8, axis=1)))

        def tier(field):
            return np.minimum(np.floor(np.clip(field, 0.0, 0.9999) * 8.0), 7).astype(np.uint8)

        def balanced_tier(field):
            """Histogram-CDF tiers: all eight shades remain meaningfully populated."""
            bins = np.minimum(np.floor(np.clip(field, 0.0, 1.0) * 255.0), 255).astype(np.uint8)
            counts = np.bincount(bins.ravel(), minlength=256)
            midpoint = np.cumsum(counts, dtype=np.float64) - counts * 0.5
            lut = np.minimum(np.floor(midpoint * (8.0 / bins.size)), 7).astype(np.uint8)
            return lut[bins]

        m_idx = balanced_tier(shards)
        r_idx = balanced_tier(1.0 - 0.62 * shards + 0.38 * pits)
        cc_idx = balanced_tier(0.46 * shards + 0.31 * warp + 0.23 * (1.0 - pits))

        # Each mark family gets its own channel relationship (combined-spec
        # tint), and its own tier selection (brightness).  This is intentionally
        # not one shared grayscale mask copied into M/R/CC.
        ridge_mask = ridges > 0.34
        m_idx = np.where(ridge_mask, 5 + tier(ridges) // 3, m_idx)
        r_idx = np.where(ridge_mask, tier(1.0 - ridges) // 3, r_idx)
        cc_idx = np.where(ridge_mask, 4 + tier(fracture) // 2, cc_idx)

        sweep_mask = sweeps > 0.08
        m_idx = np.where(sweep_mask, 2 + tier(pits) // 2, m_idx)
        r_idx = np.where(sweep_mask, 1 + tier(sweeps) // 3, r_idx)
        cc_idx = np.where(sweep_mask, 5 + tier(warp) // 3, cc_idx)

        arc_mask = arcs > 0.70
        m_idx = np.where(arc_mask, 4 + tier(arcs) // 3, m_idx)
        r_idx = np.where(arc_mask, 5 + tier(1.0 - warp) // 3, r_idx)
        cc_idx = np.where(arc_mask, 2 + tier(shards) // 2, cc_idx)

        pit_mask = pits > 0.82
        m_idx = np.where(pit_mask, tier(1.0 - pits) // 2, m_idx)
        r_idx = np.where(pit_mask, 4 + tier(pits) // 2, r_idx)
        cc_idx = np.where(pit_mask, 1 + tier(fracture) // 2, cc_idx)

        fleck_mask = flecks > 0.82
        m_idx = np.where(fleck_mask, 6 + tier(flecks) // 4, m_idx)
        r_idx = np.where(fleck_mask, 2 + tier(warp) // 2, r_idx)
        cc_idx = np.where(fleck_mask, 6 + tier(1.0 - pits) // 4, cc_idx)

        m_palette = np.asarray([4, 12, 24, 42, 68, 108, 166, 244], np.float32)
        r_palette = np.asarray([15, 22, 34, 50, 72, 100, 138, 184], np.float32)
        cc_palette = np.asarray([16, 28, 44, 66, 94, 130, 176, 232], np.float32)
        return m_palette[m_idx], r_palette[r_idx], cc_palette[cc_idx]

    return _cache(key, build)


def spec_obsidian(shape, seed, sm, base_m, base_r):
    """Obsidian spec — fine conchoidal structure with a broad shade palette.

    SPB-105 / TWENTY WINS tick Win A3 regression repair (2026-08-23). Owner verdict:
    "WAY more spec coloring/shades" and "small, fine patterns." The June final
    override had flattened the proven fracture renderer to M/CC constants.
    Direct total spec std moves 1.514 -> 194.98 at 256 (M/R/CC independently
    varied); M7 composite moves 57.3 -> 85.0. Every ridge/sweep is segmented on
    both axes to 8-32 px; three cold active 2048 paint+spec passes top at 2.529 s.
    """
    h, w = shape[:2]
    authored_m, authored_r, authored_cc = _obsidian_spec_layers((h, w), seed)
    strength = float(np.clip(sm, 0.0, 1.0))
    M = float(base_m) + (authored_m - float(base_m)) * strength
    R = float(base_r) + (authored_r - float(base_r)) * strength
    CC = 16.0 + (authored_cc - 16.0) * strength
    return (
        np.clip(M, 0, 255).astype(np.float32),
        np.clip(R, 15, 255).astype(np.float32),
        np.clip(CC, 0, 255).astype(np.float32),
    )

# ---- CERAMIC ----
def paint_ceramic(paint, shape, mask, seed, pm, bb):            # glossy white glaze
    return _surface(paint, shape, mask, seed, pm, bb, (0.86, 0.86, 0.87), depth=0.30, facet=0.30)
def spec_ceramic(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=22, r_amp=10, facet=0.30)

def paint_ceramic_matte(paint, shape, mask, seed, pm, bb):     # matte fired ceramic
    return _surface(paint, shape, mask, seed, pm, bb, (0.80, 0.80, 0.81), frost=0.45, facet=0.10)
def spec_ceramic_matte(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=120, r_amp=28, facet=0.0, frost=0.45, cc=90)

def paint_enamel(paint, shape, mask, seed, pm, bb):            # glossy baked enamel
    return _surface(paint, shape, mask, seed, pm, bb, (0.87, 0.87, 0.88), depth=0.25, facet=0.35, crackle=0.05)
def spec_enamel(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=20, r_amp=9, facet=0.35)

def paint_porcelain(paint, shape, mask, seed, pm, bb):        # bone porcelain micro-crack
    return _surface(paint, shape, mask, seed, pm, bb, (0.93, 0.92, 0.90), crackle=0.35,
                    crackle_rgb=(0.55, 0.50, 0.45), crackle_cells=300, facet=0.20, depth=0.20)
def spec_porcelain(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=20, r_amp=9, facet=0.20, crackle=0.35, crackle_cells=300)

def paint_crackle_glaze(paint, shape, mask, seed, pm, bb):    # teal raku crackle
    return _surface(paint, shape, mask, seed, pm, bb, (0.45, 0.72, 0.70), crackle=0.62,
                    crackle_rgb=(0.06, 0.10, 0.10), crackle_cells=380, facet=0.30, depth=0.30)
def spec_crackle_glaze(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=24, r_amp=10, facet=0.30, crackle=0.62, crackle_cells=380)

def paint_liquid_glaze(paint, shape, mask, seed, pm, bb):     # cobalt ultra-wet glaze
    return _surface(paint, shape, mask, seed, pm, bb, (0.50, 0.60, 0.85), tint=(0.08, 0.18, 0.55),
                    depth=0.70, facet=0.40)
def spec_liquid_glaze(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=15, r_amp=6, facet=0.40)

def paint_terracotta_glaze(paint, shape, mask, seed, pm, bb): # warm glazed terracotta
    return _surface(paint, shape, mask, seed, pm, bb, (0.80, 0.45, 0.28), depth=0.30, facet=0.30, crackle=0.12,
                    crackle_rgb=(0.30, 0.14, 0.07))
def spec_terracotta_glaze(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=28, r_amp=12, facet=0.30, crackle=0.12)

def paint_piano_black(paint, shape, mask, seed, pm, bb):      # deep black lacquer mirror
    return _surface(paint, shape, mask, seed, pm, bb, (0.02, 0.02, 0.03), depth=0.30, facet=0.40)
def spec_piano_black(shape, seed, sm, base_m, base_r):
    return _surface_spec(shape, seed, sm, base_m, base_r, r_base=15, r_amp=6, m_flat=8, facet=0.40)
