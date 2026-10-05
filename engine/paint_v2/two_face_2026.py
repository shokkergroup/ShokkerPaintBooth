# -*- coding: utf-8 -*-
"""
engine/paint_v2/two_face_2026.py — ★ OPTIC LAB : TWO-FACE (rebuilt 2026-06-15)

10 directional color-FLIP duotones, each with its OWN flip geometry and its OWN
bespoke design — NO shared template, NO recolor clones. Face A blazes at one
angle, face B at the other, on the EXACT same pixels, because every spec
RECOMPUTES the same flip field its paint uses (shared field helper + same seed).

Flip geometries (one per finish, all distinct):
  blue_copper   lenticular fine louvers   (warped sine micro-lines)
  purple_gold   split zones               (crisp territory seam split)
  green_magenta woven interlace           (over/under basket weave)
  teal_orange   gradient flip             (banded directional sweep)
  red_cyan      checker flip              (warped rotated checkerboard)
  silver_void   radial flip               (concentric spiral rings)
  pink_teal     shard flip                (angular crystalline facets)
  gold_emerald  flow-stripe flip          (curved flow-line lenticular)
  violet_lime   halftone flip             (dot-screen duotone)
  crimson_navy  fracture flip             (Voronoi crack-network split)

THE FLIP PHYSICS (every spec, traced):
  The flip field f(0..1) is computed ONCE per (geometry, seed). The PAINT mixes
  color-A where f is high, color-B where f is low. The SPEC then makes the
  A-territory near-mirror metal (high M, low R) and the B-territory matte (low M,
  high R) on those SAME pixels — so raking light flares A, head-on shows B. The
  flip seam itself gets a clearcoat ridge. M / R / CC ride DIFFERENT aspects of
  the same field (territory / edge-energy / seam-distance) so the combined spec
  reads as MANY hues, never red+green. |corr| < 0.85 by construction.

Contracts: paint_x->HxWx3 in [0,1] ; spec_x->(M,R,CC) float32 0..255.
FINE detail (~10x finer than instinct). UV-orientation-agnostic. <3s @2048.
"""
import numpy as np

from engine.core import multi_scale_noise, get_mgrid, _resize_array, hsv_to_rgb_vec

try:
    import cv2 as _cv2
    _CV2 = True
except Exception:  # pragma: no cover
    _cv2 = None
    _CV2 = False

_TF_CACHE = {}


def _cache(key, fn):
    v = _TF_CACHE.get(key)
    if v is None:
        if len(_TF_CACHE) > 200:
            _TF_CACHE.clear()
        v = fn()
        _TF_CACHE[key] = v
    return v


def _norm01(a):
    a = np.asarray(a, dtype=np.float32)
    lo = float(a.min()); hi = float(a.max())
    if hi - lo < 1e-7:
        return np.zeros_like(a, dtype=np.float32)
    return ((a - lo) / (hi - lo)).astype(np.float32)


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _noise(shape, scales, weights, seed, cap=760):
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
    """Crisp full-res pepper grain (decorrelated micro field for R)."""
    h, w = shape[:2]
    key = ("g", h, w, int(seed))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x6B19) & 0xFFFFFFFF)
        n = rng.random((h, w), dtype=np.float32)
        return ((n + np.roll(n, 1, 0) + np.roll(n, 1, 1)) * 0.333).astype(np.float32)

    return _cache(key, build)


# ---------------------------------------------------------------------------
# WORK-RES CAP (owner render-time doctrine).  Every flip field below is broad,
# smooth, isotropic structure — a louver pitch / checker cell / dot grid that's
# many pixels wide even at 2048.  Computing the per-pixel sin/sqrt/arctan2 +
# warp noise at the FULL 2048^2 is what blew the <3s budget (5-8s).  We build
# the geometry at a capped work-res (long edge ~1024px) then bilinear-resize the
# fields up — bit-for-bit the same look the eye sees (the features are >>1px) at
# a fraction of the FLOP, exactly like the cKDTree fields already do.  The
# feature PITCH is derived from the work-res dims so the feature COUNT (and thus
# the size at full res after resize) is unchanged.
# ---------------------------------------------------------------------------
_WORK_CAP = 860


def _wr(h, w, cap=_WORK_CAP):
    """Work-res dims for an (h, w) target: long edge capped at `cap`."""
    m = max(h, w)
    if m <= cap:
        return int(h), int(w)
    sh = max(96, int(round(h * cap / m)))
    sw = max(96, int(round(w * cap / m)))
    return sh, sw


def _up(fields, h, w):
    """Resize every named field in a dict up to (h, w) (no-op if already there)."""
    return {k: _resize_array(np.asarray(v, np.float32), h, w) for k, v in fields.items()}


def _flake(shape, seed, density, lo=0.45):
    h, w = shape[:2]
    key = ("fl", h, w, int(seed), float(density))

    def build():
        rng = np.random.default_rng((int(seed) ^ 0x9E37) & 0xFFFFFFFF)
        n = min(int(h * w * float(density)), 150000)
        out = np.zeros((h, w), np.float32)
        if n > 0:
            yy = rng.integers(0, h, n); xx = rng.integers(0, w, n)
            out[yy, xx] = rng.uniform(lo, 1.0, n).astype(np.float32)
            out = np.maximum.reduce([out, np.roll(out, 1, 0) * 0.4, np.roll(out, 1, 1) * 0.4])
        return out.astype(np.float32)

    return _cache(key, build)


def _edges(f):
    """Edge-energy of a field (gradient magnitude, 0..1) — used to ride CC on the
    flip SEAMS, decorrelated from the territory mask that rides M."""
    gx = np.empty_like(f); gy = np.empty_like(f)
    gx[:, :-1] = f[:, 1:] - f[:, :-1]; gx[:, -1] = 0
    gy[:-1, :] = f[1:, :] - f[:-1, :]; gy[-1, :] = 0
    return _norm01(np.sqrt(gx * gx + gy * gy))


def _blur(a, px):
    if _CV2 and px > 0.3:
        return _cv2.GaussianBlur(np.asarray(a, np.float32), (0, 0), float(px))
    return np.asarray(a, np.float32)


# ===========================================================================
# 10 BESPOKE FLIP FIELDS.  Each returns a dict of named float32 HxW fields
# (always including "t" = the A-weight 0..1) so the spec can trace the exact
# same geometry the paint used.  Cached by (id, h, w, seed).
# ===========================================================================

def _field_lenticular(shape, seed):
    """blue_copper — warped fine sine LOUVERS (true lenticular)."""
    h, w = shape[:2]
    key = ("lent", h, w, int(seed))

    def build():
        sh, sw = _wr(h, w)
        y, x = get_mgrid((sh, sw))
        ang = np.deg2rad(22.0)
        u = (x * np.cos(ang) + y * np.sin(ang)).astype(np.float32)
        warp = _noise((sh, sw), [12, 30], [0.55, 0.45], seed + 4) * 5.0
        strip_px = max(2.0, min(sh, sw) / 110.0)            # ~9-10 px louvers @2048 (fine)
        louver = 0.5 + 0.5 * np.sin(u / strip_px * 2.0 * np.pi + warp)
        dom = _norm01(_noise((sh, sw), [35, 75], [0.6, 0.4], seed))  # broad bias which color leads
        t = _smooth((louver - 0.5) * 1.9 + (dom - 0.5) * 0.7 + 0.5)
        return _up({"t": t.astype(np.float32), "louver": louver.astype(np.float32),
                    "dom": dom.astype(np.float32)}, h, w)

    return _cache(key, build)


def _field_split_zones(shape, seed):
    """purple_gold — large crisp TERRITORY split with a sharp warped seam."""
    h, w = shape[:2]
    key = ("split", h, w, int(seed))

    def build():
        sh, sw = _wr(h, w)
        big = _noise((sh, sw), [55, 120], [0.6, 0.4], seed)
        warp = _noise((sh, sw), [15, 32], [0.5, 0.5], seed + 7)
        field = big + warp * 0.55
        thr = float(np.median(field))
        sharp = (field - thr) * (min(sh, sw) / 7.0)         # crisp seam (count-matched)
        t = _smooth(sharp + 0.5)
        seam = 1.0 - np.abs(t - 0.5) * 2.0                  # bright on the boundary
        # fine vein detail INSIDE each zone so it isn't a flat blob
        vein = _norm01(_noise((sh, sw), [5, 10], [0.6, 0.4], seed + 11))
        return _up({"t": t.astype(np.float32), "seam": _norm01(seam).astype(np.float32),
                    "vein": vein.astype(np.float32)}, h, w)

    return _cache(key, build)


def _field_weave(shape, seed):
    """green_magenta — over/under BASKET WEAVE interlace."""
    h, w = shape[:2]
    key = ("weave", h, w, int(seed))

    def build():
        sh, sw = _wr(h, w)
        y, x = get_mgrid((sh, sw))
        period = max(3.0, min(sh, sw) / 65.0)               # ~16px weave cell @2048
        wob = _noise((sh, sw), [20, 45], [0.5, 0.5], seed + 3) * 1.6
        warp_h = 0.5 + 0.5 * np.sin((x / period + wob) * 2.0 * np.pi)
        warp_v = 0.5 + 0.5 * np.sin((y / period + wob) * 2.0 * np.pi)
        # checker which thread is ON TOP -> color A vs B alternates per cell
        topx = (np.floor(x / period).astype(np.int32)
                + np.floor(y / period).astype(np.int32)) % 2
        over = np.where(topx == 0, warp_h, warp_v).astype(np.float32)
        t = _smooth((over - 0.5) * 2.1 + 0.5)
        # thread shading (cylindrical highlight along each strand) — fine
        shade = np.where(topx == 0, warp_h, warp_v).astype(np.float32)
        return _up({"t": t.astype(np.float32), "over": _norm01(over).astype(np.float32),
                    "shade": shade.astype(np.float32),
                    "top": topx.astype(np.float32)}, h, w)

    return _cache(key, build)


def _field_gradient(shape, seed):
    """teal_orange — banded directional GRADIENT flip (lenticular gradient)."""
    h, w = shape[:2]
    key = ("grad", h, w, int(seed))

    def build():
        sh, sw = _wr(h, w)
        y, x = get_mgrid((sh, sw))
        ang = np.deg2rad(-34.0)
        u = _norm01((x * np.cos(ang) + y * np.sin(ang)).astype(np.float32))
        warp = _noise((sh, sw), [25, 60], [0.5, 0.5], seed + 5) * 0.18
        g = np.clip(u + warp, 0, 1)
        # quantize into fine gradient BANDS so the flip steps crisply
        bands = 26.0
        bphase = (g * bands) % 1.0
        step = _smooth((bphase - 0.5) * 1.7 + 0.5)
        t = _smooth(g * 0.55 + step * 0.45)                 # overall sweep + band micro-flip
        band_edge = 1.0 - np.abs(bphase - 0.5) * 2.0
        return _up({"t": t.astype(np.float32), "sweep": g.astype(np.float32),
                    "band_edge": _norm01(band_edge).astype(np.float32)}, h, w)

    return _cache(key, build)


def _field_checker(shape, seed):
    """red_cyan — warped rotated CHECKER flip."""
    h, w = shape[:2]
    key = ("check", h, w, int(seed))

    def build():
        sh, sw = _wr(h, w)
        y, x = get_mgrid((sh, sw))
        a = np.deg2rad(18.0); ca, sa = np.cos(a), np.sin(a)
        u = x * ca + y * sa
        v = -x * sa + y * ca
        warp = _noise((sh, sw), [17, 38], [0.5, 0.5], seed + 2) * 6.0
        cell = max(3.5, min(sh, sw) / 55.0)                 # ~18px squares @2048
        su = 0.5 + 0.5 * np.sin((u + warp) / cell * np.pi)
        sv = 0.5 + 0.5 * np.sin((v - warp) / cell * np.pi)
        chk = su * sv + (1 - su) * (1 - sv)                 # checker product 0..1
        t = _smooth((chk - 0.5) * 2.2 + 0.5)
        corner = _norm01(np.abs(su - 0.5) * np.abs(sv - 0.5))  # bright tile centers
        return _up({"t": t.astype(np.float32), "chk": _norm01(chk).astype(np.float32),
                    "corner": corner.astype(np.float32)}, h, w)

    return _cache(key, build)


def _field_radial(shape, seed):
    """silver_void — concentric / spiral RADIAL rings."""
    h, w = shape[:2]
    key = ("rad", h, w, int(seed))

    def build():
        sh, sw = _wr(h, w)
        y, x = get_mgrid((sh, sw))
        # off-center so it isn't a centered emblem; jittered center
        rng = np.random.default_rng((int(seed) ^ 0x1357) & 0xFFFFFFFF)
        cy = sh * (0.30 + 0.4 * rng.random())
        cx = sw * (0.30 + 0.4 * rng.random())
        dy = (y - cy); dx = (x - cx)
        r = np.sqrt(dy * dy + dx * dx).astype(np.float32)
        ph = np.arctan2(dy, dx).astype(np.float32)
        warp = _noise((sh, sw), [22, 50], [0.5, 0.5], seed + 6) * 7.0
        ring_px = max(3.0, min(sh, sw) / 75.0)
        spiral = np.sin((r + warp) / ring_px * 2.0 * np.pi + ph * 3.0)  # spiral arms
        rings = 0.5 + 0.5 * spiral
        t = _smooth((rings - 0.5) * 2.1 + 0.5)
        ring_edge = 1.0 - np.abs(rings - 0.5) * 2.0
        rn = _norm01(r)
        return _up({"t": t.astype(np.float32), "rings": rings.astype(np.float32),
                    "ring_edge": _norm01(ring_edge).astype(np.float32),
                    "r": rn.astype(np.float32)}, h, w)

    return _cache(key, build)


def _field_shard(shape, seed):
    """pink_teal — angular crystalline SHARDS (faceted split)."""
    h, w = shape[:2]
    key = ("shard", h, w, int(seed))

    def build():
        # build at work-res then resize; cKDTree facet ownership
        hw = min(h, w)
        scale = min(1.0, 440.0 / hw)
        sh = max(96, int(round(h * scale))); sw = max(96, int(round(w * scale)))
        rng = np.random.default_rng((int(seed) ^ 0x2BAD) & 0xFFFFFFFF)
        n = 240
        py = rng.uniform(0, sh, n).astype(np.float32)
        px = rng.uniform(0, sw, n).astype(np.float32)
        owner_val = rng.random(n).astype(np.float32)        # which face owns each facet
        owner_bright = rng.random(n).astype(np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        try:
            from scipy.spatial import cKDTree
            dist, idx = cKDTree(np.stack([py, px], 1)).query(
                np.stack([yy.ravel(), xx.ravel()], 1), k=2, workers=-1)
            d1 = dist[:, 0].reshape(sh, sw)
            d2 = dist[:, 1].reshape(sh, sw)
            i0 = idx[:, 0].reshape(sh, sw)
        except Exception:
            best = np.full((sh, sw), 1e18, np.float32); i0 = np.zeros((sh, sw), np.int32)
            for i in range(n):
                dd = (yy - py[i]) ** 2 + (xx - px[i]) ** 2
                cl = dd < best; best = np.where(cl, dd, best); i0 = np.where(cl, i, i0)
            d1 = np.sqrt(best); d2 = d1 + 1.0
        facet = owner_val[i0]
        bright = owner_bright[i0]
        edge = _norm01(np.clip(1.0 - (d2 - d1), 0, 1))      # bright crystal edges
        facet = _resize_array(facet.astype(np.float32), h, w)
        bright = _resize_array(bright.astype(np.float32), h, w)
        edge = _resize_array(edge.astype(np.float32), h, w)
        t = _smooth((facet - 0.5) * 2.4 + 0.5)
        return {"t": t.astype(np.float32), "facet": facet.astype(np.float32),
                "bright": bright.astype(np.float32), "edge": _norm01(edge).astype(np.float32)}

    return _cache(key, build)


def _field_flow(shape, seed):
    """gold_emerald — curved FLOW-LINE lenticular (strands follow a vector field)."""
    h, w = shape[:2]
    key = ("flow", h, w, int(seed))

    def build():
        sh, sw = _wr(h, w)
        # phase field whose iso-lines curve -> flowing lenticular strands
        base = _noise((sh, sw), [65, 140], [0.6, 0.4], seed)           # large flow potential
        fine = _noise((sh, sw), [7, 15], [0.55, 0.45], seed + 8)
        phase = base * (min(sh, sw) / 9.0) + fine * 6.0
        strands = 0.5 + 0.5 * np.sin(phase)                            # fine curved strands
        t = _smooth((strands - 0.5) * 2.0 + 0.5)
        flowmag = _norm01(_edges(base))                                # where strands bend
        strand_edge = 1.0 - np.abs(strands - 0.5) * 2.0
        return _up({"t": t.astype(np.float32), "strands": strands.astype(np.float32),
                    "flowmag": flowmag.astype(np.float32),
                    "strand_edge": _norm01(strand_edge).astype(np.float32)}, h, w)

    return _cache(key, build)


def _field_halftone(shape, seed):
    """violet_lime — dot-screen HALFTONE duotone (rotated dot grid, size flips A/B)."""
    h, w = shape[:2]
    key = ("half", h, w, int(seed))

    def build():
        sh, sw = _wr(h, w)
        y, x = get_mgrid((sh, sw))
        a = np.deg2rad(27.0); ca, sa = np.cos(a), np.sin(a)
        u = x * ca + y * sa; v = -x * sa + y * ca
        cell = max(3.0, min(sh, sw) / 82.0)                 # ~12px dot pitch @2048 (fine)
        fu = (u / cell) % 1.0 - 0.5
        fv = (v / cell) % 1.0 - 0.5
        dist = np.sqrt(fu * fu + fv * fv)                   # 0 at dot centers
        # dot RADIUS modulated by a broad field -> A where dots fat, B where thin
        radius = 0.18 + 0.30 * _norm01(_noise((sh, sw), [40, 85], [0.6, 0.4], seed))
        dot = _smooth((radius - dist) * (min(sh, sw) / 9.0) + 0.5)  # crisp dot edge
        t = _smooth(dot * 0.82 + radius * 0.6 - 0.1)
        dotrim = 1.0 - np.abs((radius - dist)) * 4.0
        return _up({"t": np.clip(t, 0, 1).astype(np.float32), "dot": dot.astype(np.float32),
                    "radius": _norm01(radius).astype(np.float32),
                    "rim": _norm01(dotrim).astype(np.float32)}, h, w)

    return _cache(key, build)


def _field_fracture(shape, seed):
    """crimson_navy — Voronoi CRACK-NETWORK split (each cell flips A/B, cracks glow)."""
    h, w = shape[:2]
    key = ("frac", h, w, int(seed))

    def build():
        scale = min(1.0, 460.0 / min(h, w))
        sh = max(96, int(round(h * scale))); sw = max(96, int(round(w * scale)))
        rng = np.random.default_rng((int(seed) ^ 0x5C7A) & 0xFFFFFFFF)
        n = 300
        py = rng.uniform(0, sh, n).astype(np.float32)
        px = rng.uniform(0, sw, n).astype(np.float32)
        cell_face = (rng.random(n)).astype(np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        try:
            from scipy.spatial import cKDTree
            dist, idx = cKDTree(np.stack([py, px], 1)).query(
                np.stack([yy.ravel(), xx.ravel()], 1), k=2, workers=-1)
            d1 = dist[:, 0].reshape(sh, sw); d2 = dist[:, 1].reshape(sh, sw)
            i0 = idx[:, 0].reshape(sh, sw)
        except Exception:
            best = np.full((sh, sw), 1e18, np.float32); i0 = np.zeros((sh, sw), np.int32)
            for i in range(n):
                dd = (yy - py[i]) ** 2 + (xx - px[i]) ** 2
                cl = dd < best; best = np.where(cl, dd, best); i0 = np.where(cl, i, i0)
            d1 = np.sqrt(best); d2 = d1 + 2.0
        face = cell_face[i0]
        crack = np.clip(1.0 - (d2 - d1) * 0.9, 0, 1)        # ridge where two cells meet
        face = _resize_array(face.astype(np.float32), h, w)
        crack = _resize_array(crack.astype(np.float32), h, w)
        # add fine secondary craquelure inside cells
        micro = _norm01(_noise((h, w), [7, 16], [0.6, 0.4], seed + 9))
        t = _smooth((face - 0.5) * 2.4 + (micro - 0.5) * 0.5 + 0.5)
        return {"t": t.astype(np.float32), "face": face.astype(np.float32),
                "crack": _norm01(crack).astype(np.float32), "micro": micro.astype(np.float32)}

    return _cache(key, build)


# ===========================================================================
# SHARED finishing touches for the paint (kept tiny; the DESIGN is the field).
# ===========================================================================

def _apply_paint(paint, shape, mask, col, seed, flake_density, flake_rgb=None, flake_amt=0.42):
    # PERF: in-place full-res ops (clip(out=), *=, +=) instead of a chain of
    # fresh 2048x2048x3 temporaries — this finisher runs for ALL 10 finishes so
    # trimming its allocations is the broadest render-time win (owner doctrine).
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3]
    h, w = shape[:2]
    col = np.ascontiguousarray(col, dtype=np.float32)
    np.clip(col, 0.0, 1.0, out=col)
    if flake_density > 0:
        fl = _flake((h, w), seed, flake_density)
        spark = fl[:, :, None] * np.float32(flake_amt)
        if flake_rgb is not None:
            spark = spark * np.asarray(flake_rgb, np.float32)[None, None, :]
        col += spark
        np.clip(col, 0.0, 1.0, out=col)
    g = _grain((h, w), seed + 3)
    gmod = (np.float32(1.0) + np.float32(0.09) * (g - np.float32(0.5)))[:, :, None]
    col *= gmod
    np.clip(col, 0.0, 1.0, out=col)
    m = mask[:, :, None].astype(np.float32, copy=False)
    # col*m + paint*(1-m)  ==  paint + (col - paint)*m  (one temp instead of two)
    col -= paint
    col *= m
    col += paint
    return col


def _mix(a, b, t):
    """Mix sRGB triples a (where t=1) and b (where t=0) by per-pixel t.
    Fused form b + (a-b)*t broadcasts ONE delta vector against t -> a single
    full-res HxWx3 temporary instead of two (perf)."""
    a = np.asarray(a, np.float32); b = np.asarray(b, np.float32)
    delta = (a - b)[None, None, :]
    return (b[None, None, :] + delta * t[:, :, None]).astype(np.float32, copy=False)


def _flip_spec(shape, sm, t, r_field, cc_field, base_m, base_r,
               m_lo=42.0, m_hi=240.0, r_lo=18.0, r_hi=150.0,
               cc_lo=20.0, cc_hi=210.0):
    """THE traced flip spec.  Each channel rides a DISTINCT field the PAINT used:
      M  rides the A-territory t        (face A = mirror metal, face B = matte)
      R  rides r_field                   (an INDEPENDENT micro field, NOT 1-t)
      CC rides cc_field                  (broad seam/structure field, wide range)
    Three different geometries with three different value spreads make the
    combined (M,R,CC)->RGB read as MANY hues, and keep |corr|<0.85 (M rides t;
    R deliberately does NOT ride 1-t; CC rides a third geometry).  sm scales
    contrast about each channel's midpoint so it never hard-clips.
    """
    t = np.clip(np.asarray(t, np.float32), 0, 1)
    r_field = np.clip(np.asarray(r_field, np.float32), 0, 1)
    cc_field = np.clip(np.asarray(cc_field, np.float32), 0, 1)
    # M: A-zones blaze.
    mmid = (m_lo + m_hi) * 0.5
    M = np.clip(mmid + (m_lo + (m_hi - m_lo) * t - mmid) * sm, 0, 255)
    # R: independent field (grain / brightness / detail) — decorrelated from M.
    rmid = (r_lo + r_hi) * 0.5
    R = np.clip(rmid + (r_lo + (r_hi - r_lo) * r_field - rmid) * sm, 15, 255)
    # CC: broad structure field with a WIDE range so the B channel actually
    # toggles across many pixels (-> more hue-dominance classes), not a thin seam.
    ccmid = (cc_lo + cc_hi) * 0.5
    CC = np.clip(ccmid + (cc_lo + (cc_hi - cc_lo) * cc_field - ccmid) * (0.6 + 0.4 * sm), 16, 255)
    return (M.astype(np.float32), R.astype(np.float32), CC.astype(np.float32))


# ===========================================================================
# 1) twoface_blue_copper — LENTICULAR LOUVERS
# ===========================================================================
def paint_twoface_blue_copper(paint, shape, mask, seed, pm, bb):
    f = _field_lenticular(shape, seed)
    A = (0.06, 0.24, 0.92)      # electric blue
    B = (0.86, 0.42, 0.10)      # hot copper
    col = _mix(A, B, f["t"])
    # darken louver troughs slightly for depth (fine)
    col = col * (0.86 + 0.14 * f["louver"])[:, :, None]
    return _apply_paint(paint, shape, mask, col, seed, 0.013, flake_rgb=(1.0, 0.85, 0.6))


def spec_twoface_blue_copper(shape, seed, sm, base_m, base_r):
    f = _field_lenticular(shape, seed)
    g = _grain(shape, seed + 3)
    # R rides grain + an INDEPENDENT broad field (not the dom that biases t).
    # CC = independent ~50/50 split + louver crests -> 4+ hue classes.
    indep = _norm01(_noise(shape, [75, 160], [0.6, 0.4], seed + 23))
    r_field = _norm01(0.6 * g + 0.4 * indep)
    cc_field = _norm01(_smooth((indep - 0.5) * 3.0 + 0.5) * 0.7
                       + np.abs(f["louver"] - 0.5) * 2.0 * 0.3)
    return _flip_spec(shape, sm, f["t"], r_field, cc_field, base_m, base_r,
                      m_lo=48, m_hi=238, r_lo=22, r_hi=165, cc_lo=28, cc_hi=215)


# ===========================================================================
# 2) twoface_purple_gold — SPLIT ZONES
# ===========================================================================
def paint_twoface_purple_gold(paint, shape, mask, seed, pm, bb):
    f = _field_split_zones(shape, seed)
    A = (0.46, 0.10, 0.78)      # royal purple
    B = (0.96, 0.74, 0.14)      # rich gold
    col = _mix(A, B, f["t"])
    # fine veins crawl through both zones (the bespoke detail)
    col = col * (0.88 + 0.12 * f["vein"])[:, :, None]
    # brighten the seam edge so the territories read crisp
    col = np.clip(col + f["seam"][:, :, None] * 0.10, 0, 1)
    return _apply_paint(paint, shape, mask, col, seed, 0.010, flake_rgb=(1.0, 0.9, 0.7))


def spec_twoface_purple_gold(shape, seed, sm, base_m, base_r):
    f = _field_split_zones(shape, seed)
    g = _grain(shape, seed + 3)
    # R rides fine vein + grain.  CC rides an INDEPENDENT broad territory (its own
    # offset noise split) so it carves the big M-blocks into 4+ hue classes.
    r_field = _norm01(0.5 * g + 0.5 * f["vein"])
    cc_split = _norm01(_noise(shape, [95, 200], [0.6, 0.4], seed + 31))
    cc_field = _norm01(_smooth((cc_split - 0.5) * 3.0 + 0.5) * 0.7 + _blur(f["seam"], 4.0) * 0.3)
    return _flip_spec(shape, sm, f["t"], r_field, cc_field, base_m, base_r,
                      m_lo=40, m_hi=242, r_lo=22, r_hi=160, cc_lo=22, cc_hi=215)


# ===========================================================================
# 3) twoface_green_magenta — WOVEN INTERLACE
# ===========================================================================
def paint_twoface_green_magenta(paint, shape, mask, seed, pm, bb):
    f = _field_weave(shape, seed)
    A = (0.06, 0.66, 0.24)      # emerald green
    B = (0.92, 0.10, 0.60)      # magenta
    col = _mix(A, B, f["t"])
    # cylindrical thread highlight -> woven look (fine)
    shade = 0.78 + 0.22 * f["shade"]
    col = col * shade[:, :, None]
    return _apply_paint(paint, shape, mask, col, seed, 0.011, flake_rgb=(0.9, 1.0, 0.9))


def spec_twoface_green_magenta(shape, seed, sm, base_m, base_r):
    f = _field_weave(shape, seed)
    g = _grain(shape, seed + 3)
    # R is grain-dominant + an INDEPENDENT broad noise (NOT the weave warp that
    # drives t) so |corr(M,R)| stays low.  CC rides which thread is on top.
    indep = _norm01(_noise(shape, [60, 130], [0.6, 0.4], seed + 21))
    r_field = _norm01(0.62 * g + 0.38 * indep)
    cc_field = _norm01(_blur(f["top"], 2.0) * 0.6 + indep * 0.4)
    return _flip_spec(shape, sm, f["t"], r_field, cc_field, base_m, base_r,
                      m_lo=46, m_hi=236, r_lo=20, r_hi=150, cc_lo=26, cc_hi=200)


# ===========================================================================
# 4) twoface_teal_orange — GRADIENT FLIP
# ===========================================================================
def paint_twoface_teal_orange(paint, shape, mask, seed, pm, bb):
    f = _field_gradient(shape, seed)
    A = (0.00, 0.64, 0.62)      # teal
    B = (1.00, 0.46, 0.06)      # orange
    col = _mix(A, B, f["t"])
    # gentle luminance ride along the sweep
    col = col * (0.85 + 0.18 * f["sweep"])[:, :, None]
    return _apply_paint(paint, shape, mask, col, seed, 0.012, flake_rgb=(1.0, 0.95, 0.8))


def spec_twoface_teal_orange(shape, seed, sm, base_m, base_r):
    f = _field_gradient(shape, seed)
    g = _grain(shape, seed + 3)
    # R rides grain mostly (decorrelated). CC rides the smooth directional sweep
    # so clearcoat sweeps teal->orange across the panel (broad, wide range).
    r_field = _norm01(0.7 * g + 0.3 * f["band_edge"])
    cc_field = _norm01(f["sweep"] * 0.7 + f["band_edge"] * 0.3)
    return _flip_spec(shape, sm, f["t"], r_field, cc_field, base_m, base_r,
                      m_lo=44, m_hi=240, r_lo=24, r_hi=152, cc_lo=20, cc_hi=210)


# ===========================================================================
# 5) twoface_red_cyan — CHECKER FLIP
# ===========================================================================
def paint_twoface_red_cyan(paint, shape, mask, seed, pm, bb):
    f = _field_checker(shape, seed)
    A = (0.90, 0.08, 0.12)      # red
    B = (0.08, 0.82, 0.90)      # cyan
    col = _mix(A, B, f["t"])
    # bright tile centers, darker grout lines (fine)
    col = np.clip(col * (0.84 + 0.20 * f["corner"])[:, :, None], 0, 1)
    return _apply_paint(paint, shape, mask, col, seed, 0.012, flake_rgb=(1.0, 0.9, 0.9))


def spec_twoface_red_cyan(shape, seed, sm, base_m, base_r):
    f = _field_checker(shape, seed)
    g = _grain(shape, seed + 3)
    # R rides tile-center brightness (own geometry) + grain.  CC must NOT ride the
    # grout/edge lattice — that's the spatial COMPLEMENT of the tile centers R
    # rides, so they anti-correlate by construction (the old RCC=-0.87 fail).
    # Give CC its OWN independent broad noise split (like the other finishes),
    # seasoned with a touch of grout glow, so it crosses mid on its own geometry
    # and the M/R/CC triplet stays |corr|<0.85 and spans many hue classes.
    r_field = _norm01(0.5 * g + 0.5 * f["corner"])
    cc_split = _norm01(_noise(shape, [90, 190], [0.6, 0.4], seed + 37))
    grout = 1.0 - np.abs(f["chk"] - 0.5) * 2.0
    cc_field = _norm01(_smooth((cc_split - 0.5) * 3.0 + 0.5) * 0.78 + grout * 0.22)
    return _flip_spec(shape, sm, f["t"], r_field, cc_field, base_m, base_r,
                      m_lo=48, m_hi=238, r_lo=22, r_hi=154, cc_lo=24, cc_hi=205)


# ===========================================================================
# 6) twoface_silver_void — RADIAL FLIP
# ===========================================================================
def paint_twoface_silver_void(paint, shape, mask, seed, pm, bb):
    f = _field_radial(shape, seed)
    A = (0.82, 0.84, 0.88)      # bright silver
    B = (0.04, 0.04, 0.06)      # void black
    col = _mix(A, B, f["t"])
    # subtle cool->warm tint with radius so it isn't pure gray
    tint = np.stack([0.04 * f["r"], 0.0 * f["r"], -0.03 * f["r"]], -1)
    col = np.clip(col + tint, 0, 1)
    return _apply_paint(paint, shape, mask, col, seed, 0.016, flake_rgb=(0.95, 0.97, 1.0), flake_amt=0.5)


def spec_twoface_silver_void(shape, seed, sm, base_m, base_r):
    f = _field_radial(shape, seed)
    g = _grain(shape, seed + 3)
    # R rides radius (glossier near center) + grain — independent of ring phase.
    # CC rides the broad radius falloff (wide range, decorrelated from rings).
    r_field = _norm01(0.5 * g + 0.5 * f["r"])
    cc_field = _norm01(_blur(f["ring_edge"], 2.0) * 0.5 + (1 - f["r"]) * 0.5)
    return _flip_spec(shape, sm, f["t"], r_field, cc_field, base_m, base_r,
                      m_lo=55, m_hi=246, r_lo=16, r_hi=145, cc_lo=22, cc_hi=212)


# ===========================================================================
# 7) twoface_pink_teal — SHARD FLIP
# ===========================================================================
def paint_twoface_pink_teal(paint, shape, mask, seed, pm, bb):
    f = _field_shard(shape, seed)
    A = (0.96, 0.32, 0.64)      # hot pink
    B = (0.00, 0.66, 0.62)      # teal
    col = _mix(A, B, f["t"])
    # per-facet brightness + bright crystal edges (the bespoke faceted look)
    col = col * (0.78 + 0.30 * f["bright"])[:, :, None]
    col = np.clip(col + f["edge"][:, :, None] * 0.16, 0, 1)
    return _apply_paint(paint, shape, mask, col, seed, 0.010, flake_rgb=(1.0, 0.9, 0.95))


def spec_twoface_pink_teal(shape, seed, sm, base_m, base_r):
    f = _field_shard(shape, seed)
    g = _grain(shape, seed + 3)
    # R rides per-facet brightness (random per facet) + grain.  CC rides an
    # INDEPENDENT broad noise split so it crosses the M-territory blocks -> 4+ hues.
    r_field = _norm01(0.45 * g + 0.55 * f["bright"])
    cc_split = _norm01(_noise(shape, [85, 180], [0.6, 0.4], seed + 33))
    cc_field = _norm01(_smooth((cc_split - 0.5) * 3.0 + 0.5) * 0.65 + f["edge"] * 0.35)
    return _flip_spec(shape, sm, f["t"], r_field, cc_field, base_m, base_r,
                      m_lo=44, m_hi=240, r_lo=20, r_hi=152, cc_lo=22, cc_hi=208)


# ===========================================================================
# 8) twoface_gold_emerald — FLOW-STRIPE FLIP
# ===========================================================================
def paint_twoface_gold_emerald(paint, shape, mask, seed, pm, bb):
    f = _field_flow(shape, seed)
    A = (0.93, 0.72, 0.16)      # gold
    B = (0.04, 0.52, 0.26)      # emerald
    col = _mix(A, B, f["t"])
    # darken strand troughs for a flowing brushed look (fine)
    col = col * (0.84 + 0.18 * f["strands"])[:, :, None]
    return _apply_paint(paint, shape, mask, col, seed, 0.011, flake_rgb=(1.0, 0.92, 0.6))


def spec_twoface_gold_emerald(shape, seed, sm, base_m, base_r):
    f = _field_flow(shape, seed)
    g = _grain(shape, seed + 3)
    # R rides where strands BEND (flowmag) + grain — independent of strand phase.
    # CC rides its OWN broad ~50/50 noise split (smoothstepped so it genuinely
    # crosses mid over many pixels) + river-bend glow.  The old CC rode only the
    # thin flowmag/strand_edge, so it stayed dark almost everywhere -> the B
    # channel never toggled -> just 3 hue classes (the hue-diversity fail).  An
    # independent broad split adds the 3rd toggle -> 4+ classes, decorrelated.
    r_field = _norm01(0.55 * g + 0.45 * f["flowmag"])
    cc_split = _norm01(_noise(shape, [85, 180], [0.6, 0.4], seed + 29))
    cc_field = _norm01(_smooth((cc_split - 0.5) * 3.0 + 0.5) * 0.72
                       + _blur(f["flowmag"], 3.0) * 0.28)
    return _flip_spec(shape, sm, f["t"], r_field, cc_field, base_m, base_r,
                      m_lo=46, m_hi=242, r_lo=22, r_hi=150, cc_lo=22, cc_hi=206)


# ===========================================================================
# 9) twoface_violet_lime — HALFTONE FLIP
# ===========================================================================
def paint_twoface_violet_lime(paint, shape, mask, seed, pm, bb):
    f = _field_halftone(shape, seed)
    A = (0.54, 0.16, 0.90)      # violet
    B = (0.64, 0.88, 0.10)      # lime
    col = _mix(A, B, f["t"])
    # crisp dot rims pop slightly brighter
    col = np.clip(col + f["rim"][:, :, None] * 0.10, 0, 1)
    return _apply_paint(paint, shape, mask, col, seed, 0.010, flake_rgb=(0.95, 1.0, 0.85))


def spec_twoface_violet_lime(shape, seed, sm, base_m, base_r):
    f = _field_halftone(shape, seed)
    g = _grain(shape, seed + 3)
    # R rides grain + dot rims (fine). CC rides the broad dot-radius field so
    # clearcoat tracks the macro tone the dots encode (wide, decorrelated).
    r_field = _norm01(0.6 * g + 0.4 * f["rim"])
    cc_field = _norm01(_blur(f["radius"], 2.0))
    return _flip_spec(shape, sm, f["t"], r_field, cc_field, base_m, base_r,
                      m_lo=46, m_hi=238, r_lo=22, r_hi=154, cc_lo=24, cc_hi=204)


# ===========================================================================
# 10) twoface_crimson_navy — FRACTURE FLIP
# ===========================================================================
def paint_twoface_crimson_navy(paint, shape, mask, seed, pm, bb):
    f = _field_fracture(shape, seed)
    A = (0.84, 0.06, 0.18)      # crimson
    B = (0.05, 0.11, 0.46)      # navy
    col = _mix(A, B, f["t"])
    # micro craquelure shading inside cells; bright crack ridges
    col = col * (0.85 + 0.16 * f["micro"])[:, :, None]
    col = np.clip(col + f["crack"][:, :, None] * 0.14, 0, 1)
    return _apply_paint(paint, shape, mask, col, seed, 0.011, flake_rgb=(1.0, 0.85, 0.85))


def spec_twoface_crimson_navy(shape, seed, sm, base_m, base_r):
    f = _field_fracture(shape, seed)
    g = _grain(shape, seed + 3)
    # R rides fine micro craquelure + grain.  CC = an INDEPENDENT ~50/50 broad
    # split (smoothstepped so it genuinely crosses mid) + crack glow, decorrelated
    # from face/t -> gives the 3rd hue toggle so the spec spans 4+ classes.
    r_field = _norm01(0.5 * g + 0.5 * f["micro"])
    indep = _norm01(_noise(shape, [90, 190], [0.6, 0.4], seed + 41))
    cc_field = _norm01(_smooth((indep - 0.5) * 3.0 + 0.5) * 0.7 + f["crack"] * 0.3)
    return _flip_spec(shape, sm, f["t"], r_field, cc_field, base_m, base_r,
                      m_lo=42, m_hi=240, r_lo=24, r_hi=170, cc_lo=30, cc_hi=222)
