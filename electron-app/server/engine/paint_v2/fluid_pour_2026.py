# -*- coding: utf-8 -*-
"""
engine/paint_v2/fluid_pour_2026.py — ★ OPTIC LAB : FLUID POUR  (bespoke rebuild 2026-06-15)

Owner complaint on the old module (verbatim): "Mostly just recolored, same pour
pattern, same weak/flat specs." The old file was ONE _pour() factory + a _RECIPES
palette dict + a single flat _pour_spec (M=0, one R band, CC=16). That is the cardinal
sin set: shared template, recolor clones, dead single-hue specs. It is GONE.

Every one of the 10 finishes is now its OWN acrylic/resin pour TECHNIQUE with its OWN
distinct algorithm and motif — NO shared paint factory:

  pour_ocean        DIRTY POUR     — interleaved poured ribbons that fold & marble
  pour_lava         DUTCH POUR     — air-blown cells radiating from blow points
  pour_galaxy       ALCOHOL INK    — concentric ink blooms, feathered diffusion fronts
  pour_gold_marble  MARBLING       — suminagashi: combed concentric rings raked to waves
  pour_tropical     SWIPE          — wet paint dragged across cells, lacing drag-trails
  pour_rose         RING POUR      — offset concentric bullseyes (puddle rings)
  ink_emerald       TREE-RING POUR — organic negative-space tree rings / loops
  ink_copper        RESIN GEODE    — agate pool ringed with a crystalline druzy edge
  pour_monochrome   PAINT SKIN     — silicone lacing web + wrinkled dried paint-skin
  pour_neon         LACING CELLS   — high-contrast voronoi cells with bright lacing nets

Each finish is a MARRIED pair: spec_<id> recomputes the SAME geometric fields its
paint_<id> uses (same seed, shared field helpers) so the spec IGNITES the exact
features the paint shows — the cell walls, ring crests, bloom fronts, drag trails.

Specs are ALIVE and MULTI-HUE (the Viva-Mexico treatment): M / R / CC ride DIFFERENT
geometry with DIFFERENT value distributions, so the combined map (R=M,G=R,B=CC) reads
in blues/purples/oranges/teals/browns — never "red+green with dark spots". Channels are
decorrelated by construction (|corr| well under 0.85). Spec materials differ per finish:
wet-resin clearcoat (low R, CC live), metallic-pour flake (high M on cell crests),
matte paint-skin (high R floor). Perf < 3s @ 2048 via work-res cKDTree + capped fields.

Contracts (unchanged — registry rewires by name):
  paint_<id>(paint, shape, mask, seed, pm, bb) -> HxWx3 float32 [0,1]
  spec_<id>(shape, seed, sm, base_m, base_r)   -> (M, R, CC) float32 HxW 0..255
        R floor 15 (GGX); CC=16 wet; high CC = flat. sm scales spec contrast.
"""
import numpy as np
from engine.core import multi_scale_noise, _resize_array, hsv_to_rgb_vec

_FP_CACHE = {}


def _cache(key, fn):
    v = _FP_CACHE.get(key)
    if v is None:
        if len(_FP_CACHE) > 220:
            _FP_CACHE.clear()
        v = fn()
        _FP_CACHE[key] = v
    return v


def _norm01(a):
    a = np.asarray(a, dtype=np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _smooth(a):
    return (a * a * (3.0 - 2.0 * a)).astype(np.float32)


def _work_dims(h, w, cap=820):
    """Work resolution preserving aspect — pour structure is smooth, so we build
    the heavy trig/warp/distance fields here then resize to full res (the owner's
    standard <3s @2048 cure). Fine grain stays full-res elsewhere."""
    work = min(int(cap), h, w)
    sh = work if h >= w else max(64, int(round(work * h / w)))
    sw = work if w >= h else max(64, int(round(work * w / h)))
    return min(sh, h), min(sw, w)


def _to_full(field, h, w):
    f = np.asarray(field, np.float32)
    if f.shape[:2] != (h, w):
        f = _resize_array(f, h, w)
    return f.astype(np.float32)


def _grain(shape, seed, soft=1):
    """FULL-RES fine micro-grain (1-3px) in 0..1 — the crisp surface mottle."""
    h, w = shape[:2]
    key = ("g", h, w, int(seed), int(soft))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x51A3) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        if soft > 0:
            # 3px box smoothing via cv2 (one pass, no 4x full-res np.roll copies)
            try:
                import cv2
                n = cv2.blur(n, (3, 3))
            except Exception:
                n = (n + np.roll(n, 1, 0) + np.roll(n, -1, 0)
                     + np.roll(n, 1, 1) + np.roll(n, -1, 1)) * 0.2
        return n.astype(np.float32)

    return _cache(key, build)


def _broad(shape, scales, weights, seed, cap=760):
    """Cached LOW-frequency field, capped+resized = smooth by design (the pour body)."""
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


def _voronoi(shape, seed, n, salt=0):
    """Work-res cKDTree voronoi -> (cell_id 0..1, wall mask 0..1, dome 0..1) resized.
    Wall = thin ridge where two cells meet (silicone lacing). dome = 0 wall .. 1 center."""
    from scipy.spatial import cKDTree
    h, w = shape[:2]
    key = ("vor", h, w, int(seed), int(n), int(salt))

    def build():
        work = 480
        sh = work if h >= w else max(64, int(round(work * h / w)))
        sw = work if w >= h else max(64, int(round(work * w / h)))
        sh = min(sh, h); sw = min(sw, w)
        rng = np.random.default_rng((int(seed) ^ (0x42F1 + salt)) & 0xFFFFFFFF)
        pts = np.column_stack([rng.uniform(0, sh, n), rng.uniform(0, sw, n)]).astype(np.float32)
        ids = rng.random(n).astype(np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw]
        grid = np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float32)
        d, idx = cKDTree(pts).query(grid, k=2, workers=-1)
        d1 = d[:, 0].reshape(sh, sw); d2 = d[:, 1].reshape(sh, sw)
        cid = ids[idx[:, 0]].reshape(sh, sw)
        cell_r = (sh + sw) / (2.0 * np.sqrt(n))
        wall = np.clip(1.0 - (d2 - d1) / (cell_r * 0.18), 0, 1)
        dome = np.clip(1.0 - d1 / (cell_r * 0.95), 0, 1)
        if (sh, sw) != (h, w):
            cid = _resize_array(cid, h, w)
            wall = _resize_array(wall, h, w)
            dome = _resize_array(dome, h, w)
        return cid.astype(np.float32), wall.astype(np.float32), dome.astype(np.float32)

    return _cache(key, build)


def _seeds(shape, seed, n, salt=0):
    """Return n random (cy, cx) seed points in WORK terms scaled to (h,w). For blow
    points / ring centers / bloom drops. Returns float arrays in pixel coords."""
    h, w = shape[:2]
    rng = np.random.default_rng((int(seed) ^ (0x1234 + salt)) & 0xFFFFFFFF)
    cy = rng.uniform(0, h, n).astype(np.float32)
    cx = rng.uniform(0, w, n).astype(np.float32)
    return cy, cx, rng


def _apply(out, paint, mask):
    out = np.ascontiguousarray(out, dtype=np.float32)
    np.clip(out, 0.0, 1.0, out=out)                     # in-place, no extra full-res copy
    # Fast path: a fully-painted panel (the common case) needs no per-pixel blend.
    if float(mask.min()) >= 0.999:
        return out
    m = mask[:, :, None]
    return out * m + paint[:, :, :3].astype(np.float32) * (1 - m)


def _resize_rgb(col, h, w):
    if col.shape[:2] == (h, w):
        return col
    import cv2
    return cv2.resize(col, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)


def _finish(paint, shape, mask, seed, core, grain_amt=0.05, grain_seed=3):
    """Run a bespoke color `core(sh, sw)` at WORK resolution (the pour body is a
    smooth field), resize once to full res, then stamp full-res fine grain so the
    surface stays crisp at 2048. The owner's standard <3s @2048 paint recipe."""
    h, w = shape[:2]
    sh, sw = _work_dims(h, w)
    col = np.asarray(core(sh, sw), np.float32)
    col = _resize_rgb(col, h, w)
    if grain_amt > 0:
        g3 = _grain((h, w), seed + grain_seed)[:, :, None]
        col = col * (1.0 + grain_amt * (g3 - 0.5) * 2.0)
    return _apply(col, paint, mask)


def _pack3(M, R, CC):
    return (np.clip(M, 0, 255).astype(np.float32),
            np.clip(R, 15, 255).astype(np.float32),
            np.clip(CC, 0, 255).astype(np.float32))


# =====================================================================
# 1) DIRTY POUR — pour_ocean
#    Many colors layered in one cup then poured: interleaved ribbons that
#    fold over each other. Built from a domain-warped striped phase so the
#    bands marble and braid. Spec = metallic flake riding the ribbon crests.
# =====================================================================

def _dirty_phase(shape, seed):
    h, w = shape[:2]
    key = ("dirty", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w)
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        # scale stripe freq to work-res so the look is resolution-independent
        fx = 0.018 * w / sw; fy = 0.011 * h / sh
        base = (x * fx + y * fy)
        warp = _broad((sh, sw), [30, 70, 130], [0.5, 0.32, 0.18], seed + 4)
        warp2 = _broad((sh, sw), [18, 40], [0.6, 0.4], seed + 8)
        phase = base + warp * 5.2 + warp2 * 2.3
        ribbon = (np.sin(phase) * 0.5 + 0.5).astype(np.float32)
        fold = (np.sin(phase * 2.0 + warp2 * 3.0) * 0.5 + 0.5).astype(np.float32)
        return _to_full(ribbon, h, w), _to_full(fold, h, w)

    return _cache(key, build)


def paint_pour_ocean(paint, shape, mask, seed, pm, bb):
    def core(sh, sw):
        ribbon, fold = _dirty_phase((sh, sw), seed)
        t = np.clip(ribbon * 0.7 + fold * 0.3, 0, 1)
        # deep-sea ribbons: navy -> teal -> aqua -> foam, marbled
        hue = (0.52 + 0.12 * np.sin(t * 6.28) - 0.04 * fold).astype(np.float32)
        sat = (0.85 - 0.45 * t).astype(np.float32)
        val = (0.14 + 0.86 * _smooth(t)).astype(np.float32)
        r, g, b = hsv_to_rgb_vec(hue % 1.0, np.clip(sat, 0, 1), np.clip(val, 0, 1))
        return np.stack([r, g, b], -1)
    return _finish(paint, shape, mask, seed, core, grain_amt=0.05)


def spec_pour_ocean(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    ribbon, fold = _dirty_phase((h, w), seed)
    grain = _grain((h, w), seed + 3)
    # two independent low-freq fields so M-body, R and CC each occupy their own range
    depth = _norm01(_broad((h, w), [40, 90], [0.55, 0.45], seed + 21))
    swell = _norm01(_broad((h, w), [22, 52], [0.55, 0.45], seed + 29))
    # M: pearlescent body lifted across the mid-range + flake on the bright crests
    crest = _smooth(np.clip((ribbon - 0.45) / 0.55, 0, 1))
    M = 90.0 + 150.0 * crest * sm + 60.0 * swell * sm + 25.0 * (grain - 0.5) * 2.0
    # R: wet in the deep valleys, rougher on the fold ridges (DIFFERENT geometry)
    R = 30.0 + 120.0 * fold * sm + 26.0 * (grain - 0.5) * 2.0 * sm
    # CC: clearcoat pools by an independent depth field, wide swing (more cool classes)
    CC = 16.0 + 200.0 * depth * sm
    return _pack3(M, R, CC)


# =====================================================================
# 2) DUTCH POUR — pour_lava
#    A base coat is poured, then air (straw/blower) pushes paint OUTWARD from
#    blow points creating radial cell blooms with crisp rims. Built from
#    distance-to-blow-point radial waves. Spec = molten flake on the rims.
# =====================================================================

def _dutch_field(shape, seed):
    h, w = shape[:2]
    key = ("dutch", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w)
        cy, cx, rng = _seeds((sh, sw), seed, 7, salt=1)
        rad = rng.uniform(0.18, 0.42, len(cy)).astype(np.float32) * min(sh, sw)
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        warp = _broad((sh, sw), [26, 58], [0.6, 0.4], seed + 5) * 26.0
        acc = np.zeros((sh, sw), np.float32)
        rim = np.zeros((sh, sw), np.float32)
        for i in range(len(cy)):
            d = np.sqrt((y - cy[i]) ** 2 + (x - cx[i]) ** 2) + warp
            push = np.clip(1.0 - d / rad[i], 0, 1)               # spread of this blow
            acc = np.maximum(acc, push)
            # concentric rim waves from the blow front
            ring = np.sin(d / (rad[i] * 0.10)) * push
            rim = np.maximum(rim, np.clip(ring, 0, 1))
        return _to_full(acc, h, w), _to_full(rim, h, w)

    return _cache(key, build)


def paint_pour_lava(paint, shape, mask, seed, pm, bb):
    def core(sh, sw):
        acc, rim = _dutch_field((sh, sw), seed)
        # cooled black crust where paint thinned, molten orange where it pooled
        t = np.clip(acc * 0.85 + rim * 0.3, 0, 1)
        hue = (0.02 + 0.10 * _smooth(t)).astype(np.float32)       # red -> orange -> yellow
        sat = (1.0 - 0.35 * t).astype(np.float32)
        val = (0.05 + 0.95 * (t ** 1.4)).astype(np.float32)
        r, g, b = hsv_to_rgb_vec(hue, np.clip(sat, 0, 1), np.clip(val, 0, 1))
        return np.stack([r, g, b], -1)
    return _finish(paint, shape, mask, seed, core, grain_amt=0.06)


def spec_pour_lava(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    acc, rim = _dutch_field((h, w), seed)
    grain = _grain((h, w), seed + 3)
    # independent crust noise so R rides its own geometry (not -acc)
    crust = _norm01(_broad((h, w), [10, 26, 60], [0.45, 0.35, 0.2], seed + 22))
    # independent clearcoat puddle field (decorrelated from acc rim/pool)
    puddle = _norm01(_broad((h, w), [44, 96], [0.55, 0.45], seed + 23))
    # M: hot flake on the blown rims (rings) — radial geometry
    M = 30.0 + 215.0 * rim * sm + 25.0 * (grain - 0.5) * 2.0
    # R: crust roughness rides its OWN noise + grain, lightly thinned in molten pools
    R = 70.0 + 110.0 * crust * sm - 30.0 * acc * sm + 30.0 * (grain - 0.5) * 2.0 * sm
    # CC: glassy clear pooled by an independent puddle field -> cool blue/teal combine
    CC = 16.0 + 170.0 * puddle * sm
    return _pack3(M, R, CC)


# =====================================================================
# 3) ALCOHOL INK — pour_galaxy
#    Drops of ink on yupo bloom outward in concentric diffusion fronts that
#    push pigment to feathered halos. Built from summed radial diffusion
#    rings with hard cores + soft fronts. Spec = nebula sparkle in the halos.
# =====================================================================

def _ink_bloom(shape, seed):
    """Concentric alcohol-ink blooms. Built at WORK-RES (the blooms are smooth
    diffusion fields) then resized — keeps the 22-drop loop cheap at 2048."""
    h, w = shape[:2]
    key = ("ink", h, w, int(seed))

    def build():
        work = 480
        sh = work if h >= w else max(64, int(round(work * h / w)))
        sw = work if w >= h else max(64, int(round(work * w / h)))
        sh = min(sh, h); sw = min(sw, w)
        cy, cx, rng = _seeds((sh, sw), seed, 22, salt=2)
        rad = rng.uniform(0.06, 0.22, len(cy)).astype(np.float32) * min(sh, sw)
        hueseed = rng.random(len(cy)).astype(np.float32)
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        warp = _broad((sh, sw), [20, 44], [0.6, 0.4], seed + 6) * 18.0
        dens = np.zeros((sh, sw), np.float32)    # pigment density
        front = np.zeros((sh, sw), np.float32)   # feathered diffusion front
        huef = np.zeros((sh, sw), np.float32)
        for i in range(len(cy)):
            d = (np.sqrt((y - cy[i]) ** 2 + (x - cx[i]) ** 2) + warp) / rad[i]
            core = np.exp(-(d ** 2) * 1.4)                       # dense ink core
            halo = np.clip(1.0 - np.abs(d - 1.0) / 0.35, 0, 1)   # pushed-pigment ring
            contrib = core + 0.7 * halo
            newer = contrib > dens
            huef = np.where(newer, hueseed[i], huef)
            dens = np.maximum(dens, contrib)
            front = np.maximum(front, halo)
        dens = _norm01(dens)
        if (sh, sw) != (h, w):
            dens = _resize_array(dens, h, w)
            front = _resize_array(front.astype(np.float32), h, w)
            huef = _resize_array(huef.astype(np.float32), h, w)
        return dens.astype(np.float32), front.astype(np.float32), huef.astype(np.float32)

    return _cache(key, build)


def paint_pour_galaxy(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]

    def core(sh, sw):
        dens, front, huef = _ink_bloom((sh, sw), seed)
        # deep-space ink: indigo void, magenta/violet blooms, white-hot cores
        hue = (0.74 + 0.22 * huef - 0.10 * front).astype(np.float32)
        sat = np.clip(0.95 - 0.7 * (dens ** 2), 0, 1).astype(np.float32)
        val = np.clip(0.04 + 0.96 * (dens ** 1.5), 0, 1).astype(np.float32)
        r, g, b = hsv_to_rgb_vec(hue % 1.0, sat, val)
        return np.stack([r, g, b], -1)

    sh, sw = _work_dims(h, w)
    col = _resize_rgb(np.asarray(core(sh, sw), np.float32), h, w)
    g3 = _grain((h, w), seed + 3)[:, :, None]
    col = col * (1.0 + 0.05 * (g3 - 0.5) * 2.0)
    # sparse star sparkle scattered in the void (full-res crisp pins). Star density
    # is gated by a cheap work-res void mask resized up — no second full bloom build.
    voidm = _resize_array(1.0 - _ink_bloom((sh, sw), seed)[0], h, w)
    rng = np.random.default_rng((int(seed) ^ 0xA17) & 0xFFFFFFFF)
    ns = min(int(h * w * 0.0016), 60000)
    yy = rng.integers(0, h, ns); xx = rng.integers(0, w, ns)
    spark = np.zeros((h, w), np.float32); spark[yy, xx] = rng.uniform(0.5, 1.0, ns)
    col = np.clip(col + spark[:, :, None] * voidm[:, :, None] * 0.9, 0, 1)
    return _apply(col, paint, mask)


def spec_pour_galaxy(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    dens, front, huef = _ink_bloom((h, w), seed)
    grain = _grain((h, w), seed + 3)
    rng = np.random.default_rng((int(seed) ^ 0xA17) & 0xFFFFFFFF)
    ns = min(int(h * w * 0.0016), 60000)
    yy = rng.integers(0, h, ns); xx = rng.integers(0, w, ns)
    spark = np.zeros((h, w), np.float32); spark[yy, xx] = rng.uniform(0.4, 1.0, ns)
    # independent varnish field so CC rides its own geometry (not +dens)
    varnish = _norm01(_broad((h, w), [36, 80], [0.55, 0.45], seed + 24))
    # M: star sparkle + bloom-front shimmer (fine pins)
    M = 25.0 + 230.0 * spark * sm + 120.0 * front * sm
    # R: the dense ink cores are wet-glossy, the dry void is rough (inverse geometry)
    R = 130.0 - 95.0 * dens * sm + 30.0 * (grain - 0.5) * 2.0 * sm
    # CC: clearcoat varnish by an independent field, hue-graded by huef for color spread
    CC = 16.0 + 120.0 * varnish * sm + 60.0 * huef * sm
    return _pack3(M, R, CC)


# =====================================================================
# 4) MARBLING / SUMINAGASHI — pour_gold_marble
#    Concentric rings dropped on water then RAKED with a comb into peacock
#    waves. Built from concentric ring phase warped by a directional comb +
#    domain warp. Spec = gold leaf on the ring crests, black ink in valleys.
# =====================================================================

def _marble_field(shape, seed):
    h, w = shape[:2]
    key = ("marble", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w)
        cy, cx, _ = _seeds((sh, sw), seed, 1, salt=3)
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        fx = 0.012 * w / sw; fyc = 0.01 * h / sh; rf = 0.05 * max(h, w) / max(sh, sw)
        # comb: a slow sinusoidal lateral displacement (the rake teeth)
        comb = np.sin(x * fx + _broad((sh, sw), [40], [1.0], seed + 9) * 2.0)
        dy = (y - cy[0]) + comb * 40.0
        dx = (x - cx[0]) + np.sin(y * fyc) * 60.0
        warp = _broad((sh, sw), [28, 60], [0.6, 0.4], seed + 5)
        d = (np.sqrt(dy ** 2 + dx ** 2) + warp * 28.0) * rf       # pre-scale ring freq
        rings = (np.sin(d) * 0.5 + 0.5).astype(np.float32)        # concentric raked rings
        # gold leaf clings to the THIN ring crest lines (sharply peaked, ≠ rings)
        crest = _smooth(np.clip(np.abs(np.sin(d)) ** 5, 0, 1))
        return _to_full(rings, h, w), _to_full(crest, h, w)

    return _cache(key, build)


def paint_pour_gold_marble(paint, shape, mask, seed, pm, bb):
    def core(sh, sw):
        rings, crest = _marble_field((sh, sw), seed)
        # black ink water, white marble bands, gold-leaf crests
        val = np.clip(0.06 + 0.9 * rings, 0, 1)
        base = np.stack([val, val, val * 0.98], -1)              # near-monochrome ink
        gold_rgb = np.array([0.92, 0.70, 0.22], np.float32)
        g = crest[:, :, None]
        return base * (1 - g * 0.85) + gold_rgb[None, None, :] * g * 0.85
    return _finish(paint, shape, mask, seed, core, grain_amt=0.05)


def spec_pour_gold_marble(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    rings, crest = _marble_field((h, w), seed)
    grain = _grain((h, w), seed + 3)
    # independent varnish field for CC so it does not anti-track the rings
    varnish = _norm01(_broad((h, w), [42, 92], [0.55, 0.45], seed + 25))
    # M: gold leaf is metallic ONLY on the thin crest lines (sharp, sparse geometry)
    M = 20.0 + 235.0 * crest * sm
    # R: white marble bands satin-rough, ink valleys wet; rides band + grain
    R = 45.0 + 85.0 * rings * sm + 30.0 * (grain - 0.5) * 2.0 * sm
    # CC: glassy resin pooled by an independent field -> blue/teal combine
    CC = 16.0 + 160.0 * varnish * sm
    return _pack3(M, R, CC)


# =====================================================================
# 5) SWIPE — pour_tropical
#    Wet paint laid in stripes, then a card/palette knife SWIPES across, smearing
#    the top color thin so the colors beneath cell up into lacing drag-trails.
#    Built from a directional smear of striped color + cells revealed in the drag.
#    Spec = the cells that popped through the swipe glint metallic.
# =====================================================================

def _swipe_smear(shape, seed):
    """Work-res stripe + drag smear (smooth) -> resized. Cheap; cached separately
    from the voronoi cells so the paint never rebuilds the cKDTree twice."""
    h, w = shape[:2]
    key = ("swipe", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w)
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        ang = 0.6
        sc = max(h, w) / max(sh, sw)
        u = (x * np.cos(ang) + y * np.sin(ang)) * sc            # res-independent
        stripe = (np.sin(u * 0.010 + _broad((sh, sw), [60], [1.0], seed + 7) * 1.5) * 0.5 + 0.5).astype(np.float32)
        drag_n = _broad((sh, sw), [4, 10], [0.6, 0.4], seed + 12)
        drag = (np.sin(u * 0.5 + drag_n * 8.0) * 0.5 + 0.5).astype(np.float32)
        return _to_full(stripe, h, w), _to_full(drag, h, w)

    return _cache(key, build)


def _swipe_field(shape, seed):
    h, w = shape[:2]
    stripe, drag = _swipe_smear((h, w), seed)
    _, wall, dome = _voronoi((h, w), seed, 340, salt=5)         # erupted cells
    cells = np.clip(wall * 1.2, 0, 1)
    return stripe, drag, cells.astype(np.float32), dome


def paint_pour_tropical(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]

    def core(sh, sw):
        stripe, drag = _swipe_smear((sh, sw), seed)              # no voronoi here
        # tropical lagoon: teal/green underneath, hot coral/yellow top swiped thin
        t = np.clip(stripe * 0.6 + drag * 0.4, 0, 1)
        hue = (0.45 - 0.45 * t).astype(np.float32)               # teal->green->yellow
        hue = np.where(t > 0.8, 0.08, hue).astype(np.float32)    # coral pops at the top
        sat = np.clip(0.92 - 0.25 * drag, 0, 1).astype(np.float32)
        val = np.clip(0.30 + 0.65 * t, 0, 1).astype(np.float32)
        r, g, b = hsv_to_rgb_vec(hue % 1.0, sat, val)
        return np.stack([r, g, b], -1)

    col = _resize_rgb(np.asarray(core(*_work_dims(h, w)), np.float32), h, w)
    g3 = _grain((h, w), seed + 3)[:, :, None]
    col = col * (1.0 + 0.05 * (g3 - 0.5) * 2.0)
    # erupted lacing cell walls = bright silvery drag-lace (single voronoi build,
    # the spec reuses the same cache entry -> traced + no double cost)
    _, wall, dome = _voronoi((h, w), seed, 340, salt=5)
    cells = np.clip(wall * 1.2, 0, 1)
    col = np.clip(col + dome[:, :, None] * 0.10, 0, 1)           # subtle cell dome lift
    col = col * (1 - cells[:, :, None] * 0.45) + 0.92 * cells[:, :, None] * 0.45
    return _apply(col, paint, mask)


def spec_pour_tropical(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    stripe, drag, cells, dome = _swipe_field((h, w), seed)
    grain = _grain((h, w), seed + 3)
    # M: the erupted cells (lacing walls) glint metallic — cell geometry
    M = 35.0 + 210.0 * cells * sm + 30.0 * dome * sm
    # R: the swiped/smeared drag is rougher (semi-dry), color stripes wet (drag geometry)
    R = 28.0 + 95.0 * drag * sm + 22.0 * (grain - 0.5) * 2.0 * sm
    # CC: clearcoat sits in the cell domes (pooled centers) -> teal/blue combine
    CC = 16.0 + 150.0 * _smooth(dome) * sm
    return _pack3(M, R, CC)


# =====================================================================
# 6) RING POUR / BULLSEYE — pour_rose
#    Paint poured in one spot builds offset concentric puddle rings (bullseye).
#    Multiple offset pours overlap. Built from min-distance to several ring
#    centers -> sharp concentric bands. Spec = wet rim highlights.
# =====================================================================

def _ring_field(shape, seed):
    h, w = shape[:2]
    key = ("ring", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w)
        cy, cx, rng = _seeds((sh, sw), seed, 5, salt=4)
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        warp = _broad((sh, sw), [34, 70], [0.6, 0.4], seed + 5) * 22.0
        rf = 0.06 * max(h, w) / max(sh, sw)
        best = np.full((sh, sw), 1e9, np.float32)
        which = np.zeros((sh, sw), np.float32)
        for i in range(len(cy)):
            d = np.sqrt((y - cy[i]) ** 2 + (x - cx[i]) ** 2) + warp
            closer = d < best
            which = np.where(closer, rng.random(), which).astype(np.float32)
            best = np.minimum(best, d)
        bd = best * rf
        band = (np.sin(bd) * 0.5 + 0.5).astype(np.float32)            # concentric bands
        rim = _smooth(np.clip(np.abs(np.sin(bd)) ** 6, 0, 1))         # sharp ring crests
        return _to_full(band, h, w), _to_full(rim, h, w), _to_full(which, h, w)

    return _cache(key, build)


def paint_pour_rose(paint, shape, mask, seed, pm, bb):
    def core(sh, sw):
        band, rim, which = _ring_field((sh, sw), seed)
        # rose petals: deep wine center rings, blush mid, cream highlights, gold rims
        t = np.clip(band, 0, 1)
        hue = (0.96 + 0.05 * which - 0.02 * t).astype(np.float32)    # rose/magenta
        sat = np.clip(0.75 - 0.55 * t, 0, 1).astype(np.float32)      # cream desaturates
        val = np.clip(0.30 + 0.70 * t, 0, 1).astype(np.float32)
        r, g, b = hsv_to_rgb_vec(hue % 1.0, sat, val)
        out = np.stack([r, g, b], -1)
        gold = np.array([0.95, 0.80, 0.45], np.float32)
        rm = rim[:, :, None]
        return out * (1 - rm * 0.5) + gold[None, None, :] * rm * 0.5
    return _finish(paint, shape, mask, seed, core, grain_amt=0.05)


def spec_pour_rose(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    band, rim, which = _ring_field((h, w), seed)
    grain = _grain((h, w), seed + 3)
    # independent clearcoat field so CC does not anti-track R's band
    glaze = _norm01(_broad((h, w), [38, 84], [0.55, 0.45], seed + 26))
    # M: gold rim crests are metallic (sharp ring geometry)
    M = 30.0 + 215.0 * rim * sm + 25.0 * (grain - 0.5) * 2.0
    # R: petal bodies satin, ring valleys wet (band geometry, different from rims)
    R = 38.0 + 80.0 * (1.0 - band) * sm + 26.0 * (grain - 0.5) * 2.0 * sm
    # CC: clearcoat by an independent glaze field + per-puddle id tint -> hue spread
    CC = 16.0 + 120.0 * glaze * sm + 60.0 * which * sm
    return _pack3(M, R, CC)


# =====================================================================
# 7) TREE-RING POUR — ink_emerald
#    Pour pulled into organic tree-ring loops (the "negative space" pour): nested
#    irregular closed loops, like wood grain / cross-section. Built from a strongly
#    domain-warped concentric phase so rings wander organically. Spec = sap-wet veins.
# =====================================================================

def _treering_field(shape, seed):
    h, w = shape[:2]
    key = ("tree", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w)
        cy, cx, _ = _seeds((sh, sw), seed, 1, salt=6)
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        # heavy multi-octave warp so the concentric rings bend into wood-loops
        w1 = _broad((sh, sw), [40, 90], [0.55, 0.45], seed + 5)
        w2 = _broad((sh, sw), [16, 34], [0.6, 0.4], seed + 8)
        w3 = _broad((sh, sw), [22, 50], [0.6, 0.4], seed + 14)
        dy = (y - cy[0]) + w1 * 90.0 + w2 * 30.0
        dx = (x - cx[0]) + w3 * 95.0 + w2 * 45.0
        rf = 0.045 * max(h, w) / max(sh, sw)
        d = np.sqrt(dy ** 2 + dx ** 2) * rf
        rings = (np.sin(d) * 0.5 + 0.5).astype(np.float32)
        grain_line = _smooth(np.clip(np.abs(np.sin(d)) ** 4, 0, 1))   # dark grain lines
        return _to_full(rings, h, w), _to_full(grain_line, h, w)

    return _cache(key, build)


def paint_ink_emerald(paint, shape, mask, seed, pm, bb):
    def core(sh, sw):
        rings, grain_line = _treering_field((sh, sw), seed)
        # emerald wood: deep forest valleys, jade rings, pale mint sap lines
        t = np.clip(rings, 0, 1)
        hue = (0.40 - 0.07 * t).astype(np.float32)               # teal-green -> green
        sat = np.clip(0.90 - 0.30 * t, 0, 1).astype(np.float32)
        val = np.clip(0.10 + 0.85 * (t ** 1.2), 0, 1).astype(np.float32)
        r, g, b = hsv_to_rgb_vec(hue, sat, val)
        out = np.stack([r, g, b], -1)
        mint = np.array([0.80, 1.0, 0.86], np.float32)
        gl = grain_line[:, :, None]
        return out * (1 - gl * 0.4) + mint[None, None, :] * gl * 0.4
    return _finish(paint, shape, mask, seed, core, grain_amt=0.05)


def spec_ink_emerald(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    rings, grain_line = _treering_field((h, w), seed)
    grain = _grain((h, w), seed + 3)
    # independent matte/wood-roughness noise so R is not just (1 - grain_line)
    woodr = _norm01(_broad((h, w), [8, 20, 44], [0.45, 0.35, 0.2], seed + 27))
    # M: thin metallic sheen on the sap grain-lines only (sparse line geometry)
    M = 25.0 + 185.0 * grain_line * sm
    # R: wood body matte (own noise) + ring banding + grain — distinct from M's lines
    R = 55.0 + 95.0 * woodr * sm + 30.0 * rings * sm + 22.0 * (grain - 0.5) * 2.0 * sm
    # CC: clearcoat varnish pools in the dark ring valleys (ring geometry)
    CC = 16.0 + 150.0 * (1.0 - rings) * sm
    return _pack3(M, R, CC)


# =====================================================================
# 8) RESIN GEODE w/ CRYSTAL EDGE — ink_copper
#    An agate-like pool of banded resin ringed by a band of sparkling druzy
#    crystals. Built from a central distance pool (smooth bands) + a crystalline
#    voronoi crust in an annulus near the rim. Spec = real crystal flake on the druzy.
# =====================================================================

def _geode_field(shape, seed):
    h, w = shape[:2]
    key = ("geode", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w)
        cy, cx, _ = _seeds((sh, sw), seed, 1, salt=7)
        y, x = np.mgrid[0:sh, 0:sw].astype(np.float32)
        warp = _broad((sh, sw), [30, 64], [0.6, 0.4], seed + 5) * 30.0
        rf = 0.05 * max(h, w) / max(sh, sw)
        d = np.sqrt((y - cy[0]) ** 2 + (x - cx[0]) ** 2) + warp
        dn = _norm01(d)
        agate = (np.sin(d * rf) * 0.5 + 0.5).astype(np.float32)   # banded agate pool
        crust_mask = np.clip(1.0 - np.abs(dn - 0.72) / 0.18, 0, 1)
        return _to_full(agate, h, w), _to_full(crust_mask, h, w), _to_full(dn, h, w)

    agate, crust_mask, dn = _cache(key, build)
    # druzy crystals: full-res voronoi (own cache) so crystal facets stay crisp
    _, wall, dome = _voronoi((h, w), seed + 1, 850, salt=7)
    crystal = np.clip(dome ** 0.6, 0, 1) * crust_mask
    return agate, crust_mask, crystal.astype(np.float32), dn


def paint_ink_copper(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    # single full-res geode build (smooth fields are work-capped; crystal voronoi
    # is the only full-res cost) — shared with the spec via cache, crystals crisp.
    agate, crust, crystal, dn = _geode_field((h, w), seed)
    g3 = _grain((h, w), seed + 3)
    # copper-teal agate: oxidized teal bands + warm copper bands in the pool
    t = np.clip(agate, 0, 1)
    hue = np.where(t > 0.5, 0.07, 0.48).astype(np.float32)       # copper vs teal bands
    sat = np.clip(0.85 - 0.2 * crust, 0, 1).astype(np.float32)
    val = np.clip(0.20 + 0.7 * t + 0.05 * (g3 - 0.5) * 2.0, 0, 1).astype(np.float32)
    r, g, b = hsv_to_rgb_vec(hue, sat, val)
    out = np.stack([r, g, b], -1)
    # white-pink sparkling crystal druzy rim (crisp facets)
    druzy = np.array([0.96, 0.90, 0.86], np.float32)
    cr = crystal[:, :, None]
    out = out * (1 - cr * 0.8) + druzy[None, None, :] * cr * 0.8
    return _apply(out, paint, mask)


def spec_ink_copper(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    agate, crust, crystal, dn = _geode_field((h, w), seed)
    grain = _grain((h, w), seed + 3)
    # independent resin-thickness field for CC (not tied to crust/agate product)
    resin = _norm01(_broad((h, w), [40, 88], [0.55, 0.45], seed + 28))
    # independent mineral-rough field for R (own noise, NOT the crystal facets) so R
    # does not ride the same druzy geometry as M (kills the M/R correlation).
    matte = _norm01(_broad((h, w), [18, 44], [0.55, 0.45], seed + 31))
    # M: druzy crystals flash hard metallic — crystal geometry ONLY (no crust term)
    M = 25.0 + 235.0 * crystal * sm
    # R: driven by the AGATE banding + an independent mineral-rough noise (own geometry,
    # NOT the crystal facets). The faceted druzy rim is anti-aligned glossy (R drops where
    # the crystals flash), so R rides different pixels than M -> decorrelated, multi-hue.
    R = 40.0 + 120.0 * agate * sm + 95.0 * matte * sm \
        - 70.0 * crystal * sm + 22.0 * (grain - 0.5) * 2.0 * sm
    # CC: heavy resin clearcoat by an independent thickness field, thinning on the agate
    # band crests -> teal/blue/purple combine that varies across the pool.
    CC = 16.0 + 165.0 * resin * sm + 45.0 * (1.0 - agate) * sm
    return _pack3(M, R, CC)


# =====================================================================
# 9) PAINT SKIN — pour_monochrome
#    The wrinkled, leathery DRIED SKIN that forms on a pour: a silicone-lacing
#    cell web overlaid with fine wrinkle creases. Built from voronoi walls +
#    a curl-noise wrinkle field. Monochrome graphite. Spec = matte skin + glossy creases.
# =====================================================================

def _skin_field(shape, seed):
    h, w = shape[:2]
    cid, wall, dome = _voronoi((h, w), seed, 220, salt=8)
    lace = np.clip(wall * 1.3, 0, 1)
    # wrinkle creases: thin ridged lines (the dried-skin crinkle), work-res + resize
    key = ("skin_wr", h, w, int(seed))

    def build():
        sh, sw = _work_dims(h, w)
        wn = _broad((sh, sw), [6, 14, 30], [0.5, 0.3, 0.2], seed + 13)
        wrinkle = _smooth(np.clip(np.abs(np.sin(wn * 9.0)) ** 5, 0, 1))
        return _to_full(wrinkle, h, w)

    wrinkle = _cache(key, build)
    return cid, lace.astype(np.float32), dome, wrinkle


def paint_pour_monochrome(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    cid, lace, dome, wrinkle = _skin_field((h, w), seed)        # all work-capped+resized
    g3 = _grain((h, w), seed + 3)
    # graphite skin: per-cell value + dome shading + dark lacing + creased highlights
    val = np.clip(0.20 + 0.55 * cid + 0.25 * dome + 0.06 * (g3 - 0.5) * 2.0, 0, 1)
    val *= (1 - lace * 0.7)                                      # dark silicone lacing valleys
    val = np.clip(val + wrinkle * 0.18, 0, 1)                   # bright crinkle ridges
    out = np.stack([val, val, val * 1.01], -1)                 # near-neutral graphite
    return _apply(out, paint, mask)


def spec_pour_monochrome(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    cid, lace, dome, wrinkle = _skin_field((h, w), seed)
    grain = _grain((h, w), seed + 3)
    # M: faint pewter sheen on the lacing web + crease ridges (line geometry)
    M = 20.0 + 150.0 * lace * sm + 90.0 * wrinkle * sm
    # R: dried skin is MATTE (high R floor); cell domes a touch glossier (dome geometry)
    R = 150.0 - 70.0 * dome * sm + 28.0 * (grain - 0.5) * 2.0 * sm
    # CC: thin clear only catching the wrinkle crests (inverse-ish of R) -> purple/gray combine
    CC = 16.0 + 120.0 * wrinkle * sm + 40.0 * cid * sm
    return _pack3(M, R, CC)


# =====================================================================
# 10) LACING CELLS — pour_neon
#    The headline silicone-cell pour: big open cells with razor-bright lacing
#    nets between them, each cell a hot neon hue. Built from voronoi cells with
#    per-cell rainbow ids + sharp wall lacing. Spec = electric flake on the nets.
# =====================================================================

def _neon_field(shape, seed):
    """Mixed-res neon-cell bundle: primary cells at the requested res (crisp lacing),
    secondary fine cells built at work-res cap then carried at requested res. Both
    paint and spec call this so they trace the SAME cells; the lace is crisp."""
    h, w = shape[:2]
    cid, wall, dome = _voronoi((h, w), seed, 300, salt=9)              # primary, full
    cid2, wall2, dome2 = _voronoi((h, w), seed + 4, 760, salt=9)      # nested fine
    lace = np.clip(np.maximum(wall * 1.25, wall2 * 0.8), 0, 1)
    return cid, cid2, lace.astype(np.float32), dome, dome2


def paint_pour_neon(paint, shape, mask, seed, pm, bb):
    h, w = shape[:2]
    cid, cid2, lace, dome, dome2 = _neon_field((h, w), seed)
    g3 = _grain((h, w), seed + 3)
    # full-wheel neon cells, darker toward cell walls, white-hot lacing net (crisp)
    hue = (cid + 0.18 * cid2) % 1.0
    sat = np.full((h, w), 0.95, np.float32)
    val = np.clip(0.35 + 0.6 * dome + 0.15 * dome2 + 0.05 * (g3 - 0.5) * 2.0, 0, 1)
    r, g, b = hsv_to_rgb_vec(hue.astype(np.float32), sat, val.astype(np.float32))
    out = np.stack([r, g, b], -1)
    out = out * (1 - lace[:, :, None] * 0.6) + 0.98 * lace[:, :, None] * 0.6
    return _apply(out, paint, mask)


def spec_pour_neon(shape, seed, sm, base_m, base_r):
    h, w = shape[:2]
    cid, cid2, lace, dome, dome2 = _neon_field((h, w), seed)
    grain = _grain((h, w), seed + 3)
    # CC pools by per-cell id (its own discrete geometry, ≠ dome), giving hue spread
    M = 30.0 + 220.0 * lace * sm + 30.0 * dome2 * sm
    # R: cell centers are wet-glossy, walls rougher (dome geometry — inverse of M)
    R = 26.0 + 95.0 * (1.0 - dome) * sm + 22.0 * (grain - 0.5) * 2.0 * sm
    # CC: per-cell clearcoat (cid) + secondary-cell domes -> wide hue spread, not -R
    CC = 16.0 + 150.0 * cid * sm + 60.0 * dome2 * sm
    return _pack3(M, R, CC)
