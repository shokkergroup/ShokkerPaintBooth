# -*- coding: utf-8 -*-
"""
engine/paint_v2/night_bloom_2026.py — ★ OPTIC LAB : NIGHT BLOOM (rebuilt 2026-06-15)

10 EXOTIC light-reactive / retroreflective finishes. Subtle, crushed-out daytime
albedo that DETONATES under track lights at night. The owner POLISH mandate: keep
the few that already read distinct, but push every weak one to an exotic, crushed
retroreflective design with an ALIVE multi-hue spec. NO two alike — every finish has
its OWN bespoke design algorithm and its OWN motif (no shared template / factory /
_RECIPES). The retro micro-optics live in the spec so the SAME pixels the paint
shows ignite under light.

ids (unchanged — registry wires by name):
  retroreflective_silver, hi_vis_lime, cats_eye_beaded, diamond_grade, ghost_graphic,
  amber_hazard, tribal_blaze, big_kahuna, chevron_blaze, starfield_reflective.

SPEC DOCTRINE (Viva-Mexico spec treatment): M / R / CC ride DIFFERENT geometry with
DIFFERENT value distributions so the combined map (R=M,G=R,B=CC viewed as RGB) shows
MANY hues — blues/purples/oranges/teals/browns — never "red+green+dark". Channels are
decorrelated by construction (|corr|<0.85). Each spec recomputes the SAME fields the
paint uses (same seed, shared field helpers) so the bloom traces the paint exactly.

Contracts: paint_x(paint,shape,mask,seed,pm,bb)->HxWx3 float32 [0,1] (DAYTIME albedo);
spec_x(shape,seed,sm,base_m,base_r)->(M,R,CC) three float32 HxW in 0..255.
M=metalness, R=roughness (floor 15, GGX), CC=clearcoat (16=wet). sm scales contrast.
FINE full-res micro-optics. <3s @2048 (work-res caps + windowed splats + cKDTree).
"""
import numpy as np
from engine.core import multi_scale_noise, get_mgrid, _resize_array, hsv_to_rgb_vec

try:
    import cv2 as _cv2
    _CV2 = True
except Exception:  # pragma: no cover
    _cv2 = None
    _CV2 = False

try:
    from scipy.spatial import cKDTree
    _KD = True
except Exception:  # pragma: no cover
    cKDTree = None
    _KD = False

_NB_CACHE = {}


def _cache(key, fn):
    v = _NB_CACHE.get(key)
    if v is None:
        if len(_NB_CACHE) > 200:
            _NB_CACHE.clear()
        v = fn()
        _NB_CACHE[key] = v
    return v


def _norm01(a):
    a = np.asarray(a, np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _noise(shape, scales, weights, seed, cap=768):
    h, w = shape[:2]
    key = ("n", h, w, tuple(scales), tuple(weights), int(seed), int(cap))

    def build():
        if cap and min(h, w) > cap:
            sh = max(64, int(round(h * cap / max(h, w))))
            sw = max(64, int(round(w * cap / max(h, w))))
            f = multi_scale_noise((sh, sw), scales, weights, seed)
            return _resize_array(np.asarray(f, np.float32), h, w)
        return np.asarray(multi_scale_noise((h, w), scales, weights, seed), np.float32)

    return _cache(key, build)


def _grain(shape, seed):
    """Fine 1px reproducible grain in [0,1] (per-channel decorrelator).
    Single horizontal smear (one roll) keeps it fine + cheap at 2048."""
    h, w = shape[:2]
    key = ("g", h, w, int(seed))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x2D71) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        n *= 0.6
        n += np.roll(n, 1, 1) * 0.6667                              # one roll, not two
        return np.clip(n, 0, 1).astype(np.float32)

    return _cache(key, build)


def _rot(shape, deg):
    h, w = shape[:2]
    y, x = get_mgrid((h, w))
    a = np.deg2rad(deg); ca, sa = np.cos(a), np.sin(a)
    return (x * ca + y * sa).astype(np.float32), (-x * sa + y * ca).astype(np.float32)


def _blur(a, px):
    if _CV2 and px > 0:
        return _cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), float(px))
    return np.asarray(a, np.float32)


def _compose(col, paint, mask):
    col = np.clip(np.asarray(col, np.float32), 0, 1)
    m = np.asarray(mask, np.float32)
    # Full-coverage zone (the common case): the finish owns every masked pixel, so
    # skip the per-pixel blend + paint slicing entirely (saves ~0.9s/paint @2048).
    if m.ndim == 2 and m.min() >= 0.999:
        return col
    p = paint[:, :, :3] if (paint.ndim == 3 and paint.shape[2] > 3) else paint
    if m.ndim == 2:
        m = m[:, :, None]
    return (col * m + p * (1 - m)).astype(np.float32)


def _spec(M, R, CC):
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 0, 255).astype(np.float32))


# Work-res cap for the heavy trig lattice/flow field builders. The micro-optic
# lattices have ~9-26px periods; computing the dozens of full-res 4M-element
# arrays (arctan2/round/maximum.reduce) is the render-time cost, not the noise.
# We build the geometry at <=_WORK then upsample with linear interp — periods
# stay >= ~5px at work-res so the prism/hex/wedge edges survive crisp. (owner
# render-time doctrine: every paint+spec call < 3s @2048.)
_WORK = 1024


def _wsize(shape):
    h, w = shape[:2]
    if max(h, w) <= _WORK:
        return h, w
    wh = max(64, int(round(h * _WORK / max(h, w))))
    ww = max(64, int(round(w * _WORK / max(h, w))))
    return wh, ww


def _up(arr, shape):
    h, w = shape[:2]
    if arr.shape[:2] == (h, w):
        return np.asarray(arr, np.float32)
    return _resize_array(np.asarray(arr, np.float32), h, w)


# ----- shared low-level field builders (geometry only; each finish picks its own) ---

def _points(shape, seed, density, cap=180000):
    h, w = shape[:2]
    rng = np.random.default_rng((int(seed) ^ 0x9E37) & 0xFFFFFFFF)
    n = min(int(h * w * float(density)), cap)
    if n < 4:
        n = 4
    py = rng.uniform(0, h, n).astype(np.float32)
    px = rng.uniform(0, w, n).astype(np.float32)
    return py, px, rng


def _voronoi(shape, py, px, work=640):
    """Return (d1, d2, owner) at full res via KD-tree at work-res then upsample.
    d1=nearest dist, d2=2nd nearest (crackle = d2-d1), owner=cell index."""
    h, w = shape[:2]
    sh = min(h, work); sw = max(1, int(round(w * sh / h)))
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    sy = py * (sh / h); sx = px * (sw / w)
    pts = np.stack([sy, sx], 1)
    if _KD:
        dd, idx = cKDTree(pts).query(np.stack([yy.ravel(), xx.ravel()], 1), k=2, workers=-1)
        d1 = dd[:, 0].reshape(sh, sw).astype(np.float32)
        d2 = dd[:, 1].reshape(sh, sw).astype(np.float32)
        ow = idx[:, 0].reshape(sh, sw).astype(np.float32)
    else:  # safety net
        d1 = np.zeros((sh, sw), np.float32); d2 = np.zeros((sh, sw), np.float32)
        ow = np.zeros((sh, sw), np.float32)
    return (_resize_array(d1, h, w), _resize_array(d2, h, w), _resize_array(ow, h, w))


def _rfield(shape, seed, deg, per):
    """Independent roughness micro-field: a rotated wavy band system at its OWN
    angle/period, modulated by fine grain. Used to give R geometry that is NOT
    the inverse of M (kills the perfect-anticorrelation gate fail) while staying
    fine and traced to the same seed family."""
    h, w = shape[:2]
    key = ("rf", h, w, int(seed), float(deg), float(per))

    def build():
        wh, ww = _wsize((h, w))
        u, v = _rot((wh, ww), deg)
        band = 0.5 + 0.5 * np.sin(u * (2 * np.pi / per) + np.sin(v * (2 * np.pi / (per * 1.7))) * 1.3)
        band = _up(band, (h, w))
        g = _grain((h, w), seed + 17)
        return np.clip(0.5 * band + 0.5 * g, 0, 1).astype(np.float32)

    return _cache(key, build)


# =====================================================================
# 1. RETROREFLECTIVE SILVER — corner-cube prism lattice (engineer micro-prism).
#    Rotated diamond grid of tiny corner-cubes; each cube has 3 sub-facets that
#    catch light at 3 different angles. Silver daytime; rainbow bloom at night.
# =====================================================================
def _silver_fields(shape, seed):
    h, w = shape[:2]
    key = ("silv", h, w, int(seed))

    def build():
        wh, ww = _wsize((h, w))
        u, v = _rot((wh, ww), 31.0 + (seed % 7))
        per = 11.0 * (max(wh, ww) / max(h, w))                        # period in work px
        fu = (u / per) % 1.0; fv = (v / per) % 1.0
        cu = fu - 0.5; cv = fv - 0.5
        # 3 sub-facets per cube via 120deg sectoring of the cube-local angle
        ang = np.arctan2(cv, cu)
        facet = np.floor((ang / (2 * np.pi) + 0.5) * 3.0)            # 0,1,2
        rad = np.maximum(np.abs(cu), np.abs(cv))                      # diamond radius
        cube = np.clip(1.0 - rad / 0.5, 0, 1) ** 0.6                 # bright cube body
        seam = np.clip(1.0 - np.abs(rad - 0.42) / 0.06, 0, 1)       # cube-edge seams
        return (_up(facet, (h, w)), _up(cube, (h, w)), _up(seam, (h, w)))

    return _cache(key, build)


def paint_retroreflective_silver(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    facet, cube, seam = _silver_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    # daytime: cool silver, faint per-facet value step (matte sheeting look)
    val = 0.50 + 0.10 * (facet / 2.0) + 0.16 * cube + 0.05 * (g - 0.5)
    col = np.empty((h, w, 3), np.float32)
    col[..., 0] = val * 0.97; col[..., 1] = val; col[..., 2] = val * 1.03
    col = np.clip(col - 0.10 * seam[..., None], 0, 1)               # dark prism grout
    return _compose(col, paint, mask)


def spec_retroreflective_silver(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    facet, cube, seam = _silver_fields((h, w), seed)
    rf = _rfield((h, w), seed, 71.0, 23.0)
    # M rides the cube bodies (retro detonates there); facet gives per-cube hue step
    M = 150 + 105 * cube * (0.7 + 0.3 * (facet / 2.0))
    M = M * sm + (1 - sm) * 60
    # R rides its OWN band field + seams; only a mild glossy dip on cubes (decorrelate)
    R = 50 + 120 * rf + 70 * seam - 22 * cube
    R = R * sm + (1 - sm) * 120
    # CC rides facet index terraces (own geometry) lifted to cross 120 on facet 2
    CC = 30 + 110 * (facet / 2.0) + 55 * seam
    return _spec(M, R, CC)


# =====================================================================
# 2. HI-VIS LIME — engineer-grade hex micro-prism honeycomb.
#    Tight hexagonal cell array (the real DG3 sheeting look). Acid lime daytime.
# =====================================================================
def _hex_fields(shape, seed, per=10.0):
    h, w = shape[:2]
    key = ("hex", h, w, int(seed), float(per))

    def build():
        wh, ww = _wsize((h, w))
        u, v = _rot((wh, ww), 7.0 + (seed % 5))
        pw = per * (max(wh, ww) / max(h, w))                          # period in work px
        # axial hex distance field
        q = (u * (2.0 / 3.0)) / pw
        r = (-u / 3.0 + (np.sqrt(3.0) / 3.0) * v) / pw
        cq = np.round(q); cr = np.round(r); cs = np.round(-q - r)
        # cell center distance (hex "depth")
        dist = np.maximum.reduce([np.abs(q - cq), np.abs(r - cr), np.abs((-q - r) - cs)])
        cell_id = ((cq * 73.0 + cr * 91.0) % 6.0)
        body = np.clip(1.0 - dist / 0.5, 0, 1) ** 0.5
        wall = np.clip(1.0 - np.abs(dist - 0.46) / 0.07, 0, 1)
        return (_up(body, (h, w)), _up(wall, (h, w)), _up(cell_id, (h, w)))

    return _cache(key, build)


def paint_hi_vis_lime(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    body, wall, cid = _hex_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    # acid lime, per-cell value flicker, dark walls
    base = np.array([0.62, 0.86, 0.10], np.float32)
    val = 0.55 + 0.4 * body + 0.06 * (cid / 5.0) + 0.05 * (g - 0.5)
    col = base[None, None, :] * val[..., None]
    col = np.clip(col - 0.18 * wall[..., None], 0, 1)
    return _compose(col, paint, mask)


def spec_hi_vis_lime(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    body, wall, cid = _hex_fields((h, w), seed)
    rf = _rfield((h, w), seed, 84.0, 16.0)
    g = _grain((h, w), seed + 3)
    # M on hex bodies (bloom)
    M = 130 + 120 * body
    M = M * sm + (1 - sm) * 55
    # R rides its OWN band field (own angle/period) + fine grain; only a light glossy
    # dip on the hex bodies so it is NOT the inverse of M (the wall field is near-
    # complementary to body and sharpens that anti-coupling at native res -> gate fail).
    R = 55 + 110 * rf + 28 * g - 16 * body
    R = R * sm + (1 - sm) * 120
    # CC on per-cell id (6-level mosaic, own geometry) -> teal/amber/purple cells
    CC = 16 + 38 * cid + 24 * wall
    return _spec(M, R, CC)


# =====================================================================
# 3. CAT'S-EYE BEADED — scattered glass retro-beads (Voronoi bead caps).
#    Each bead is a tiny lens; matrix is dark. Crushed-fine bead field.
# =====================================================================
def _bead_fields(shape, seed):
    h, w = shape[:2]
    key = ("bead", h, w, int(seed))

    def build():
        py, px, rng = _points((h, w), seed, 0.0016, cap=60000)
        d1, d2, ow = _voronoi((h, w), py, px, work=560)
        d1 = _norm01(d1)
        cap = np.clip(1.0 - d1 / 0.42, 0, 1) ** 0.7                  # bead dome
        rim = np.clip(1.0 - np.abs(d1 - 0.5) / 0.10, 0, 1)          # bead edge halo
        cellv = (ow % 5.0) / 4.0                                     # per-bead value
        return cap.astype(np.float32), rim.astype(np.float32), cellv.astype(np.float32)

    return _cache(key, build)


def paint_cats_eye_beaded(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    cap, rim, cellv = _bead_fields((h, w), seed)
    # near-black matrix, pale glass bead caps with slight cool tint
    base = np.array([0.07, 0.08, 0.11], np.float32)
    glass = np.array([0.74, 0.80, 0.92], np.float32)
    col = base[None, None, :] * (1 - cap[..., None]) + glass[None, None, :] * cap[..., None]
    col = np.clip(col + 0.10 * rim[..., None], 0, 1)
    return _compose(col, paint, mask)


def spec_cats_eye_beaded(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    cap, rim, cellv = _bead_fields((h, w), seed)
    rf = _rfield((h, w), seed, 39.0, 19.0)
    # M on bead caps (the lenses bloom)
    M = 25 + 230 * cap
    M = M * sm + (1 - sm) * 40
    # R rides its OWN band field; only a light glossy dip on bead caps (decorrelate)
    R = 70 + 110 * rf - 26 * cap
    R = R * sm + (1 - sm) * 130
    # CC rides bead rim + per-bead value step (own geometry), lifted to cross 120
    CC = 30 + 130 * rim + 90 * cellv
    return _spec(M, R, CC)


# =====================================================================
# 4. DIAMOND GRADE — full-cube prism array with diagonal interference flare bands.
#    Square micro-cube tiles overlaid by a crossing band system (the DG "sparkle
#    sweep"). Steel-gray daytime; banded rainbow bloom.
# =====================================================================
def _diamond_fields(shape, seed):
    h, w = shape[:2]
    key = ("dia", h, w, int(seed))

    def build():
        wh, ww = _wsize((h, w))
        sc = max(wh, ww) / max(h, w)
        u, v = _rot((wh, ww), 45.0)
        per = 9.0 * sc
        fu = np.abs((u / per) % 1.0 - 0.5); fv = np.abs((v / per) % 1.0 - 0.5)
        tile = np.clip(1.0 - np.minimum(fu, fv) / 0.34, 0, 1)        # cube tiles
        seam = np.clip(np.minimum(fu, fv) / 0.5, 0, 1)              # grout
        # crossing flare bands at a DIFFERENT angle / period (independent geometry)
        b1, _ = _rot((wh, ww), 18.0)
        band = 0.5 + 0.5 * np.sin(b1 * (2 * np.pi / (70.0 * sc)))   # smooth sweep
        return (_up(tile, (h, w)), _up(seam, (h, w)), _up(band, (h, w)))

    return _cache(key, build)


def paint_diamond_grade(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    tile, seam, band = _diamond_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    val = 0.34 + 0.30 * tile + 0.10 * band + 0.05 * (g - 0.5)
    col = np.empty((h, w, 3), np.float32)
    col[..., 0] = val * 1.0; col[..., 1] = val * 1.02; col[..., 2] = val * 1.08
    col = np.clip(col - 0.14 * seam[..., None], 0, 1)
    return _compose(col, paint, mask)


def spec_diamond_grade(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    tile, seam, band = _diamond_fields((h, w), seed)
    rf = _rfield((h, w), seed, 63.0, 17.0)
    # M on cube tiles, modulated by the flare band (sweep of bloom intensity)
    M = 90 + 165 * tile * (0.5 + 0.5 * band)
    M = M * sm + (1 - sm) * 55
    # R on its OWN band field + grout seams; light glossy dip on tiles (decorrelate)
    R = 55 + 110 * rf + 80 * seam - 18 * tile
    R = R * sm + (1 - sm) * 120
    # CC on the diagonal interference band ALONE (own geometry) -> moving teal/violet
    CC = 16 + 150 * band + 24 * seam
    return _spec(M, R, CC)


# =====================================================================
# 5. GHOST GRAPHIC — hidden crackle-vein graphic that blazes only at night.
#    A crackle network (Voronoi ridge) carries the secret motif; near-invisible
#    by day, white-hot bloom at night. Crushed-fine vein web.
# =====================================================================
def _ghost_fields(shape, seed):
    h, w = shape[:2]
    key = ("ghost", h, w, int(seed))

    def build():
        py, px, rng = _points((h, w), seed, 0.0009, cap=40000)
        d1, d2, ow = _voronoi((h, w), py, px, work=560)
        crack = _norm01(d2 - d1)
        vein = np.clip(1.0 - crack / 0.10, 0, 1) ** 1.2             # thin ridge web
        plate = (ow % 7.0) / 6.0                                    # plate territory id
        warp = _norm01(_noise((h, w), [50, 120], [0.6, 0.4], seed + 5))  # broad ghost glow
        return vein.astype(np.float32), plate.astype(np.float32), warp.astype(np.float32)

    return _cache(key, build)


def paint_ghost_graphic(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    vein, plate, warp = _ghost_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    # charcoal body, the veins are only a touch lighter (hidden by day)
    base = np.array([0.085, 0.085, 0.10], np.float32)
    col = base[None, None, :] + (0.10 + 0.05 * warp)[..., None] * vein[..., None]
    col = np.clip(col + 0.03 * (g[..., None] - 0.5), 0, 1)
    return _compose(col, paint, mask)


def spec_ghost_graphic(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    vein, plate, warp = _ghost_fields((h, w), seed)
    rf = _rfield((h, w), seed, 51.0, 21.0)
    # M on the crackle veins (the graphic detonates)
    M = 18 + 235 * vein
    M = M * sm + (1 - sm) * 35
    # R on its OWN band field; light glossy dip on the veins only (decorrelate)
    R = 70 + 110 * rf - 26 * vein
    R = R * sm + (1 - sm) * 125
    # CC on the broad ghost-glow warp + plate id (own geometry) -> drifting purple/teal
    CC = 16 + 140 * warp + 70 * plate
    return _spec(M, R, CC)


# =====================================================================
# 6. AMBER HAZARD — radial chevron caution wedges (rotated, UV-agnostic).
#    Wedge spokes from a scattered center; amber/black hazard read by day,
#    molten-orange bloom by night. Crushed wedge edges.
# =====================================================================
def _hazard_fields(shape, seed):
    h, w = shape[:2]
    key = ("haz", h, w, int(seed))

    def build():
        wh, ww = _wsize((h, w))
        sc = max(wh, ww) / max(h, w)
        rng = np.random.default_rng((int(seed) ^ 0x5A11) & 0xFFFFFFFF)
        cy = rng.uniform(0.3, 0.7) * wh; cx = rng.uniform(0.3, 0.7) * ww
        y, x = get_mgrid((wh, ww))
        ang = np.arctan2(y - cy, x - cx)
        rad = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
        spokes = 34.0
        sp = (ang / (2 * np.pi) * spokes) % 1.0
        wedge = (sp < 0.5).astype(np.float32)                       # alternating wedges
        edge = np.clip(1.0 - np.abs(sp - 0.5) / 0.07, 0, 1)        # wedge seams
        # concentric hazard rings (independent geometry) for the CC channel
        ring = 0.5 + 0.5 * np.sin(rad * (2 * np.pi / (48.0 * sc)))
        return (_up(wedge, (h, w)), _up(edge, (h, w)), _up(ring, (h, w)))

    return _cache(key, build)


def paint_amber_hazard(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    wedge, edge, ring = _hazard_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    amber = np.array([0.85, 0.46, 0.04], np.float32)
    blk = np.array([0.10, 0.07, 0.03], np.float32)
    col = amber[None, None, :] * wedge[..., None] + blk[None, None, :] * (1 - wedge[..., None])
    col = np.clip(col * (1.0 + 0.05 * (g[..., None] - 0.5)) - 0.10 * edge[..., None], 0, 1)
    return _compose(col, paint, mask)


def spec_amber_hazard(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    wedge, edge, ring = _hazard_fields((h, w), seed)
    rf = _rfield((h, w), seed, 12.0, 25.0)
    # M on the amber wedges (those bloom orange)
    M = 35 + 215 * wedge
    M = M * sm + (1 - sm) * 45
    # R on its OWN band field + wedge edges; light glossy dip on amber (decorrelate)
    R = 60 + 110 * rf + 60 * edge - 22 * wedge
    R = R * sm + (1 - sm) * 120
    # CC on concentric rings ALONE (own geometry) -> pulsing blue/violet bands
    CC = 16 + 150 * ring
    return _spec(M, R, CC)


# =====================================================================
# 7. TRIBAL BLAZE — flowing flame-tongue tribal strokes + spike spurs.
#    Bold organic strokes (sine-warped) with sharp spikes; ash-black by day,
#    white-gold blaze by night. Crisp stroke edges.
# =====================================================================
def _tribal_fields(shape, seed):
    h, w = shape[:2]
    key = ("trib", h, w, int(seed))

    def build():
        wh, ww = _wsize((h, w))
        sc = max(wh, ww) / max(h, w)
        u, v = _rot((wh, ww), 18.0 + (seed % 11))
        w1 = _noise((wh, ww), [60, 130], [0.6, 0.4], seed) * 60.0 * sc
        w2 = _noise((wh, ww), [28, 70], [0.5, 0.5], seed + 1) * 36.0 * sc
        f = np.sin((u + w1) * (0.045 / sc)) * np.cos((v + w2) * (0.045 / sc) + w1 * 0.02)
        stroke = np.clip(1.0 - np.abs(f) / 0.20, 0, 1)
        spike = np.clip(1.0 - np.abs(np.sin((u - v + w1) * (0.035 / sc))) / 0.06, 0, 1)
        heat = _norm01(_noise((h, w), [40, 90], [0.6, 0.4], seed + 2))  # broad ember field
        return (_up(stroke, (h, w)), _up(spike, (h, w)), heat.astype(np.float32))

    return _cache(key, build)


def paint_tribal_blaze(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    stroke, spike, heat = _tribal_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    body = np.clip(np.maximum(stroke, spike * 0.7), 0, 1)
    base = np.array([0.06, 0.06, 0.08], np.float32)
    gold = np.array([0.95, 0.84, 0.55], np.float32)
    col = base[None, None, :] * (1 - body[..., None]) + gold[None, None, :] * (0.30 + 0.25 * heat)[..., None] * body[..., None]
    col = np.clip(col + 0.03 * (g[..., None] - 0.5), 0, 1)
    return _compose(col, paint, mask)


def spec_tribal_blaze(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    stroke, spike, heat = _tribal_fields((h, w), seed)
    rf = _rfield((h, w), seed, 78.0, 20.0)
    body = np.clip(np.maximum(stroke, spike * 0.7), 0, 1)
    # M on the stroke cores (blaze)
    M = 25 + 225 * body
    M = M * sm + (1 - sm) * 40
    # R on its OWN band field + spikes; light glossy dip on stroke cores (decorrelate)
    R = 60 + 110 * rf + 55 * spike - 24 * body
    R = R * sm + (1 - sm) * 125
    # CC on the broad ember heat field (own geometry) lifted to cross 120 widely
    CC = 16 + 175 * heat + 26 * spike
    return _spec(M, R, CC)


# =====================================================================
# 8. BIG KAHUNA — scalloped surf-wave tribal (horizontal swell flow).
#    Stacked breaking-wave scallops with foam crests; teal lagoon by day,
#    sunset-orange wave bloom by night. Distinct from tribal_blaze (wave flow,
#    not flame strokes; foam grain not spikes).
# =====================================================================
def _kahuna_fields(shape, seed):
    h, w = shape[:2]
    key = ("kah", h, w, int(seed))

    def build():
        wh, ww = _wsize((h, w))
        sc = max(wh, ww) / max(h, w)
        u, v = _rot((wh, ww), 6.0)
        w1 = _noise((wh, ww), [70, 150], [0.6, 0.4], seed) * 55.0 * sc
        w2 = _noise((wh, ww), [30, 70], [0.5, 0.5], seed + 1) * 30.0 * sc
        swell = np.sin((v + w1) * (0.05 / sc) + np.sin((u + w2) * (0.025 / sc)) * 2.2)
        wave = np.clip(1.0 - np.abs(swell) / 0.30, 0, 1)            # wave body
        crest = np.clip(1.0 - np.abs(swell - 0.55) / 0.10, 0, 1)   # foam crest line
        wave = _up(wave, (h, w)); crest = _up(crest, (h, w))
        foam = (_norm01(_noise((h, w), [6, 14], [0.5, 0.5], seed + 4)) * crest)  # fine foam fizz
        under = _norm01(_noise((h, w), [55, 120], [0.6, 0.4], seed + 7))  # broad undertow
        return wave.astype(np.float32), foam.astype(np.float32), under.astype(np.float32)

    return _cache(key, build)


def paint_big_kahuna(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    wave, foam, under = _kahuna_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    teal = np.array([0.04, 0.30, 0.34], np.float32)
    orange = np.array([0.92, 0.45, 0.10], np.float32)
    col = teal[None, None, :] * (1 - wave[..., None]) + orange[None, None, :] * wave[..., None]
    col = np.clip(col + 0.45 * foam[..., None] + 0.03 * (g[..., None] - 0.5), 0, 1)
    return _compose(col, paint, mask)


def spec_big_kahuna(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    wave, foam, under = _kahuna_fields((h, w), seed)
    rf = _rfield((h, w), seed, 96.0, 24.0)
    # M on the wave bodies (the swells bloom)
    M = 40 + 205 * wave
    M = M * sm + (1 - sm) * 45
    # R on its OWN band field + foam fizz; light glossy dip on wave bodies (decorrelate)
    R = 55 + 105 * rf + 70 * foam - 20 * wave
    R = R * sm + (1 - sm) * 120
    # CC on the broad undertow field (own geometry) lifted to cross 120 -> deep
    # blue/green tidal drift, a third hue axis separate from the wave + foam
    CC = 16 + 185 * under + 30 * foam
    return _spec(M, R, CC)


# =====================================================================
# 9. CHEVRON BLAZE — battenburg micro-checker (rotated) + retro corner studs.
#    Yellow/blue emergency checker with a stud at each checker corner; flat
#    livery by day, checker + stud bloom by night. Fine checker + crisp studs.
# =====================================================================
def _chevron_fields(shape, seed):
    h, w = shape[:2]
    key = ("chev", h, w, int(seed))

    def build():
        wh, ww = _wsize((h, w))
        u, v = _rot((wh, ww), 27.0)
        per = 26.0 * (max(wh, ww) / max(h, w))
        chk = (((np.floor(u / per) + np.floor(v / per)) % 2) == 0).astype(np.float32)
        # studs at the lattice corners (own fine geometry)
        fu = np.abs((u / per) % 1.0); fv = np.abs((v / per) % 1.0)
        cu = np.minimum(fu, 1 - fu); cv = np.minimum(fv, 1 - fv)
        stud = np.clip(1.0 - np.sqrt(cu * cu + cv * cv) / 0.16, 0, 1) ** 0.7
        edge = np.clip(1.0 - np.minimum(np.abs(fu - 0.5), np.abs(fv - 0.5)) / 0.04, 0, 1)
        return (_up(chk, (h, w)), _up(stud, (h, w)), _up(edge, (h, w)))

    return _cache(key, build)


def paint_chevron_blaze(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    chk, stud, edge = _chevron_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    yel = np.array([0.78, 0.70, 0.10], np.float32)
    blu = np.array([0.05, 0.12, 0.40], np.float32)
    col = yel[None, None, :] * chk[..., None] + blu[None, None, :] * (1 - chk[..., None])
    col = np.clip(col + 0.30 * stud[..., None] + 0.03 * (g[..., None] - 0.5), 0, 1)
    return _compose(col, paint, mask)


def spec_chevron_blaze(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    chk, stud, edge = _chevron_fields((h, w), seed)
    rf = _rfield((h, w), seed, 117.0, 18.0)
    warp = _norm01(_noise((h, w), [55, 120], [0.6, 0.4], seed + 11))  # broad CC drift
    # M on the yellow checker squares + studs (those bloom)
    M = 45 + 150 * chk + 80 * stud
    M = M * sm + (1 - sm) * 50
    # R on its OWN band field + checker edges; light glossy dip on yellow (decorrelate)
    R = 55 + 110 * rf + 55 * edge - 18 * chk
    R = R * sm + (1 - sm) * 120
    # CC on a broad drift field + studs (own geometry) -> teal/violet wash + stud glints
    CC = 16 + 150 * warp + 90 * stud
    return _spec(M, R, CC)


# =====================================================================
# 10. STARFIELD REFLECTIVE — sparse retro micro-stars + diffraction cross spikes.
#     Pinpoint glass stars over deep-space blue; each star throws a 4-arm
#     diffraction cross. Calm by day, glittering bloom by night. Distinct from
#     cats_eye (sparse + cross spikes + nebula, not dense bead caps).
# =====================================================================
def _star_fields(shape, seed):
    h, w = shape[:2]
    key = ("star", h, w, int(seed))

    def build():
        py, px, rng = _points((h, w), seed, 0.0004, cap=14000)
        n = len(py)
        core = np.zeros((h, w), np.float32)
        spike = np.zeros((h, w), np.float32)
        yi = py.astype(np.int32); xi = px.astype(np.int32)
        mag = rng.uniform(0.5, 1.0, n).astype(np.float32)
        core[yi, xi] = mag
        # 4-arm diffraction cross: spread each star's magnitude along H/V arms with
        # falloff (read from the ORIGINAL core so arms stay clean straight spikes).
        # cumulative max in 4 directions = the full cross in 4 cheap roll-pairs.
        sx = np.maximum(np.roll(core, 1, 1) * 0.75, np.roll(core, -1, 1) * 0.75)
        sx = np.maximum(sx, np.maximum(np.roll(core, 3, 1) * 0.40, np.roll(core, -3, 1) * 0.40))
        sy = np.maximum(np.roll(core, 1, 0) * 0.75, np.roll(core, -1, 0) * 0.75)
        sy = np.maximum(sy, np.maximum(np.roll(core, 3, 0) * 0.40, np.roll(core, -3, 0) * 0.40))
        spike = np.maximum(sx, sy)
        core2 = np.maximum(core, np.maximum(np.roll(core, 1, 0) * 0.5, np.roll(core, 1, 1) * 0.5))
        nebula = _norm01(_noise((h, w), [60, 140, 280], [0.4, 0.35, 0.25], seed + 9, cap=512))  # broad gas
        return core2.astype(np.float32), spike.astype(np.float32), nebula.astype(np.float32)

    return _cache(key, build)


def paint_starfield_reflective(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    core, spike, nebula = _star_fields((h, w), seed)
    g = _grain((h, w), seed + 3)
    # deep-space gradient: blue body tinted by nebula, white star points
    body = np.empty((h, w, 3), np.float32)
    body[..., 0] = 0.03 + 0.10 * nebula
    body[..., 1] = 0.05 + 0.06 * nebula
    body[..., 2] = 0.13 + 0.14 * nebula
    star = np.clip(core + spike * 0.5, 0, 1)
    col = body + star[..., None] * np.array([0.95, 0.97, 1.0], np.float32)[None, None, :]
    col = np.clip(col + 0.02 * (g[..., None] - 0.5), 0, 1)
    return _compose(col, paint, mask)


def spec_starfield_reflective(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    core, spike, nebula = _star_fields((h, w), seed)
    rf = _rfield((h, w), seed, 33.0, 22.0)
    # M on the star cores + a faint nebula-glow floor so the sky carries some bloom
    # (otherwise the whole field is one class). Cores still detonate brightest.
    neb2 = nebula * nebula                                          # cheap gamma vs **1.4
    M = 35 + 235 * core + 130 * neb2
    M = M * sm + (1 - sm) * 50
    # R on its OWN band field; reduced on cores & spikes (glossy) -> decorrelate
    R = 60 + 110 * rf - 35 * spike - 45 * core
    R = R * sm + (1 - sm) * 130
    # CC on a SECOND, independent gas field (different seed) + diffraction spikes, so it
    # is neither M's glow nor its inverse -> teal/violet clouds offset from the M glow
    gas2 = _norm01(_noise((h, w), [70, 160, 320], [0.4, 0.35, 0.25], seed + 23, cap=512))
    CC = 16 + 175 * gas2 + 90 * spike
    return _spec(M, R, CC)
