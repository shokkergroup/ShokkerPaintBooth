# -*- coding: utf-8 -*-
# FLAMES-FIX 2026-10-07 (owner: "I didn't want you to delete the old one's just add new one's"):
# this is the 2026-10-06 FLAMES SHELF rebuild, MOVED here unchanged from flames_2026.py so the
# owner's original 20 flame_* renderers could be restored byte-identical to HEAD in flames_2026.py.
# The 20 looks below now register as 20 NEW finishes (flame2_*), see NEW_IDS at the bottom.
"""
engine/paint_v2/flames_2026_v2.py - FLAMES shelf (rebuilt as real flame-lick FIELDS,
FLAMES SHELF 2026-10-06).

Owner 2026-10-05: "build REAL flames before the beta". The 2026-06-15 build
promised flame licks but rendered blobs, clouds and rings, and 19/20 finishes
failed the Finish Law (docs/FINISH_LAW.md). Every finish is now a FIELD of real
tapered, hook-tipped flame licks flowing front -> back (+x) over the whole
2048 canvas, with 8-32 px licks riding on bigger lick bodies. One lick library
(below) + 20 short recipes, each a DIFFERENT idea (see each recipe's comment).

Contracts (unchanged; the registry resolves by name):
  paint_<id>(paint, shape, mask, seed, pm, bb) -> HxWx3 float32 [0,1]
  spec_<id>(shape, seed, sm, base_m, base_r)    -> (M, R, CC) float32 0..255
     M = metallic, R = roughness (0 mirror, floor 15), CC = clearcoat (16 = max gloss).
"""
import numpy as np

try:
    import cv2 as _cv2
    _CV2 = True
except Exception:  # pragma: no cover
    _cv2 = None
    _CV2 = False

from engine.core import multi_scale_noise, get_mgrid, _resize_array, hsv_to_rgb_vec  # noqa: F401

import cv2

# ===========================================================================
# FLAME-LICK FIELD LIBRARY  (FLAMES SHELF 2026-10-06)
#
# Owner 2026-10-05: "build REAL flames before the beta" - the 2026-06-15 shelf
# promised flame licks but rendered blobs, clouds and rings (19/20 failed the
# Finish Law). Every finish below is now a FIELD of real licks over the whole
# 2048 canvas, authored as a short recipe on ONE library (AI-as-compiler):
#
#   _licks / _center / _polys   one lick = a heading integrated along its centre
#                               line (stream heading + wave + a hook that curls
#                               the tip), a tapered width profile, a rounded root
#   _field                      a staggered root lattice over the canvas, headings
#                               from a smooth flow field (stream = +x = the car's
#                               front -> back, as js/spb-pro-flames.js), bodies
#                               drawn rear-first so every upstream lick covers the
#                               roots of the licks behind it; optional nested
#                               inner tongues (hotter cores), kids peeling off the
#                               body edges and grand-kids off the kids (the
#                               8-32 px detail rides on the bigger bodies)
#   per-pixel products          idx (which poly owns the pixel, painter order),
#                               t (root -> tip), per-lick attributes, top-edge
#                               distance (outlines / rims / bevels)
#
# Spec is ALWAYS computed from the same idx / t / edge fields as the paint, so
# the material change sits on the lick edges (FOLLOW) - never an independent
# noise dealt over the top.
#
# SEEDS: compose.py hands paint_fn the raw seed but base_spec_fn
# seed + abs(hash(base_id)) % 10000 (and str hashes are randomised per
# process), so a seed-driven layout could never line the spec up with the paint
# in the app. Each finish therefore uses its own FIXED layout seed (precedent:
# engine/paint_v2/money_shokk_claude.py _GATE_SEED). The runtime seed is ignored.
# ===========================================================================
_REF = 2048.0
_LOOK = {}
_GRID = {}


def _fl_scale(h, w):
    return float(np.sqrt(float(h) * float(w))) / _REF


def _fl_xy(h, w):
    v = _GRID.get((h, w))
    if v is None:
        _GRID.clear()
        X = np.broadcast_to(np.arange(w, dtype=np.float32)[None, :], (h, w))
        Y = np.broadcast_to(np.arange(h, dtype=np.float32)[:, None], (h, w))
        v = (X, Y)
        _GRID[(h, w)] = v
    return v


def _sm(a, b, x):
    t = np.clip((np.asarray(x, np.float32) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _vn(h, w, cy, cx, seed):
    """Value noise in [0,1] with cell cy x cx px (anisotropic allowed)."""
    cy = max(1.0, float(cy))
    cx = max(1.0, float(cx))
    gh = int(h / cy) + 3
    gw = int(w / cx) + 3
    g = np.random.default_rng(int(seed) & 0x7FFFFFFF).random((gh, gw), dtype=np.float32)
    big = cv2.resize(g, (int(round(gw * cx)), int(round(gh * cy))), interpolation=cv2.INTER_CUBIC)
    return np.clip(big[:h, :w], 0.0, 1.0)


def _fbm(h, w, cell, octaves, seed, aniso=1.0, gain=0.5):
    out = np.zeros((h, w), np.float32)
    amp, tot, c = 1.0, 0.0, float(cell)
    for o in range(int(octaves)):
        out += amp * _vn(h, w, c, c * aniso, seed + 101 * o)
        tot += amp
        amp *= gain
        c *= 0.5
    return out / tot


def _ramp(t, stops):
    """Piecewise-linear colour ramp; stops = [(pos, (r,g,b)), ...] -> HxWx3."""
    t = np.asarray(t, np.float32)
    xp = [p for p, _ in stops]
    out = np.empty(t.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(t, xp, [col[c] for _, col in stops]).astype(np.float32)
    return out


def _mix(a, b, k):
    k = np.asarray(k, np.float32)
    if k.ndim == a.ndim - 1:
        k = k[..., None]
    return a + (b - a) * k


def _U(rng, v, n):
    if isinstance(v, np.ndarray):
        return v.astype(np.float32)
    if isinstance(v, tuple):
        return rng.uniform(v[0], v[1], n).astype(np.float32)
    return np.full(n, v, np.float32)


def _licks(rng, x0, y0, L, hw, th, **kw):
    """Parameter arrays for n licks. Ranges are (lo, hi) tuples sampled per lick."""
    n = len(x0)
    K = {"x0": np.asarray(x0, np.float32), "y0": np.asarray(y0, np.float32),
         "L": np.asarray(L, np.float32), "hw": np.asarray(hw, np.float32),
         "th": np.asarray(th, np.float32)}
    for k, d in (("wave", 0.3), ("freq", 1.0), ("cs", 0.5), ("taper", 1.0),
                 ("belly", 0.3), ("asym", 0.0), ("prof", 0.0), ("neck", 0.0)):
        K[k] = _U(rng, kw.get(k, d), n)
    K["ph"] = _U(rng, kw.get("ph", (0.0, 6.2832)), n)
    side = kw.get("side")
    if side is None:
        side = np.where(rng.random(n) < 0.5, -1.0, 1.0).astype(np.float32)
    K["curl"] = _U(rng, kw.get("curl", 1.0), n) * np.asarray(side, np.float32)
    K["rid"] = _U(rng, kw.get("rid", (0.0, 1.0)), n)
    return K


def _center(K, N):
    """Centre line (x, y, heading, half-width), each n x N."""
    t = np.linspace(0.0, 1.0, N, dtype=np.float32)[None, :]
    hook = _sm(K["cs"][:, None], 1.0, t)
    a = (K["th"][:, None]
         + K["wave"][:, None] * np.sin(6.2832 * K["freq"][:, None] * t + K["ph"][:, None]) * (0.25 + 0.75 * t)
         + K["curl"][:, None] * hook * hook)
    ds = (K["L"] / (N - 1))[:, None]
    cx = np.cos(a) * ds
    cy = np.sin(a) * ds
    z = np.zeros_like(cx[:, :1])
    x = K["x0"][:, None] + np.concatenate([z, np.cumsum(cx[:, :-1], 1)], 1)
    y = K["y0"][:, None] + np.concatenate([z, np.cumsum(cy[:, :-1], 1)], 1)
    prof = K["prof"][:, None]
    w = (1.0 - t) ** K["taper"][:, None] * (1.0 + K["belly"][:, None] * np.sin(np.pi * np.minimum(1.0, t * 1.7)))
    if (prof == 1).any():      # BLADE: thin root, thickest ~1/4 out, long taper to a needle
        w = np.where(prof == 1, (0.5 + 0.5 * _sm(0.0, 0.22, t)) * (1.0 - t) ** 1.45 * 1.3, w)
    if (prof == 2).any():      # CONE: gas-jet cone, narrow nozzle, round shoulder, blunt tip
        w = np.where(prof == 2, (0.35 + 0.65 * _sm(0.0, 0.3, t)) * np.sqrt(np.clip(1.0 - t ** 2.2, 0.0, 1.0)), w)
    if (prof == 3).any():      # JET: near-constant sheath, needle only at the very end
        w = np.where(prof == 3, (1.0 - 0.45 * t) * np.clip(1.0 - t, 0.0, 1.0) ** 0.3, w)
    if (prof == 4).any():      # TEAR: fat round head right at the root, thin trailing tail
        w = np.where(prof == 4, np.sqrt(np.clip(np.sin(np.pi * np.minimum(1.0, t * 2.2)), 0, 1)) * (1.0 - t) ** 0.9 * 1.15, w)
    nk = K["neck"][:, None]
    if (nk > 0).any():         # NECK: the lick is born from a point (no blunt root head in a field)
        w = w * np.where(nk > 0, 0.06 + 0.94 * _sm(0.0, np.maximum(nk, 1e-3), t) ** 0.8, 1.0)
    w = K["hw"][:, None] * w
    return x, y, a, w


def _polys(x, y, a, w, asym=None, curl=None, cap=True):
    """Closed outline polygons n x P x 2 (left side, right side back, rounded root)."""
    nx = -np.sin(a)
    ny = np.cos(a)
    kl = kr = 1.0
    if asym is not None and curl is not None:
        s = np.sign(curl)[:, None] * asym[:, None]
        kl = 1.0 + s
        kr = 1.0 - s
    left = np.stack([x + nx * w * kl, y + ny * w * kl], -1)
    right = np.stack([x - nx * w * kr, y - ny * w * kr], -1)[:, ::-1]
    parts = [left, right]
    if cap:
        i = np.arange(1, 6, dtype=np.float32)[None, :]
        ang = a[:, :1] + 1.5 * np.pi - np.pi * i / 6.0
        r = w[:, :1]
        parts.append(np.stack([x[:, :1] + np.cos(ang) * r, y[:, :1] + np.sin(ang) * r], -1))
    return np.concatenate(parts, 1)


def _spawn(rng, K, cl, spec, s):
    """Kids peeling off a parent's EDGE: root just inside the edge, heading outward
    and downstream, hook curling back into the stream."""
    x, y, a, w = cl
    n, N = x.shape
    k = int(spec.get("n", 3))
    pi = np.repeat(np.arange(n), k)
    m = len(pi)
    t = rng.uniform(spec.get("t", (0.15, 0.75))[0], spec.get("t", (0.15, 0.75))[1], m)
    j = np.clip((t * (N - 1)).astype(np.int64), 0, N - 1)
    side = np.where(rng.random(m) < 0.5, -1.0, 1.0).astype(np.float32)
    px, py, pa, pw = x[pi, j], y[pi, j], a[pi, j], w[pi, j]
    off = side * pw * float(spec.get("inset", 0.55))
    x0 = px - np.sin(pa) * off
    y0 = py + np.cos(pa) * off
    th = pa + side * _U(rng, spec.get("ang", (0.25, 0.6)), m)
    L = K["L"][pi] * _U(rng, spec.get("L", (0.2, 0.35)), m)
    hw = np.maximum(pw * _U(rng, spec.get("w", (0.3, 0.45)), m), float(spec.get("min_hw", 1.6)) * s)
    rid = K["rid"][pi] if spec.get("inherit", True) else rng.random(m).astype(np.float32)
    kw = {kk: spec[kk] for kk in ("wave", "freq", "cs", "taper", "belly", "asym", "prof", "neck") if kk in spec}
    C = _licks(rng, x0, y0, L, hw, th, curl=spec.get("curl", (0.8, 1.5)),
               side=-side * float(spec.get("curl_dir", 1.0)), rid=rid, **kw)
    C["parent"] = pi
    return C


def _field(h, w, seed, B, nest=(), kids=None, grand=None, count_groups=0):
    """Build a whole-canvas lick field and rasterise it in painter order.

    B      body lattice: L, hw (ranges, REF px), dx, dy (lattice pitch), jit, flow
           (heading sway, rad), flow_cell (REF px), th (mean heading), N, order, and
           any lick shape keys (wave, freq, curl, cs, taper, belly, asym, prof).
    nest   ((len_frac, width_frac), ...) hotter inner tongues inside every body.
    kids   spawn spec for licks peeling off each body edge; grand = off each kid.

    Returns F: idx (int32, 0 = ground, code = draw rank) plus per-code arrays
    kind (0 body, 1.. nest level, 8 kid, 9 grand-kid), grp (outline group), rid,
    tx/ty/tch (root + chord for t), hw, th, and the lick dicts for extra drawing.
    """
    s = _fl_scale(h, w)
    rng = np.random.default_rng(seed)
    Lr = tuple(v * s for v in B["L"])
    dx, dy = B["dx"] * s, B["dy"] * s
    jit = B.get("jit", 0.3)
    ys = np.arange(-dy, h + dy, dy, dtype=np.float32)
    xs = np.arange(-Lr[1] * 0.9, w + dx * 0.5, dx, dtype=np.float32)
    YY, XX = np.meshgrid(ys, xs, indexing="ij")
    XX = XX + (np.arange(len(ys)) % 2)[:, None].astype(np.float32) * dx * 0.5
    n = XX.size
    X0 = XX.ravel() + rng.uniform(-jit, jit, n).astype(np.float32) * dx
    Y0 = YY.ravel() + rng.uniform(-jit, jit, n).astype(np.float32) * dy
    fc = B.get("flow_cell", 900) * s
    p = rng.uniform(0, 6.2832, 4)
    th = (B.get("th", 0.0) + B.get("flow", 0.2) * (
        0.6 * np.sin(X0 / fc * 6.2832 * 0.7 + Y0 / fc * 6.2832 * 0.45 + p[0])
        + 0.4 * np.sin(-X0 / fc * 6.2832 * 0.35 + Y0 / fc * 6.2832 * 1.1 + p[1]))).astype(np.float32)
    shape_kw = {k: B[k] for k in ("wave", "freq", "cs", "taper", "belly", "asym", "prof", "curl", "neck") if k in B}
    if B.get("side") == "band":      # hooks agree inside bands of rows -> neighbours nest instead of crossing
        shape_kw["side"] = np.where(np.sin(Y0 / (B.get("band_rows", 4) * dy) * np.pi + p[2]) >= 0, 1.0, -1.0).astype(np.float32)
    elif isinstance(B.get("side"), (int, float)):
        shape_kw["side"] = np.full(n, float(B["side"]), np.float32)
    K = _licks(rng, X0, Y0, _U(rng, Lr, n), _U(rng, tuple(v * s for v in B["hw"]), n), th, **shape_kw)
    if B.get("ph_add"):          # same layout, shifted wave phase (braids: two passes, ph_add 0 / pi)
        K["ph"] = (K["ph"] + np.float32(B["ph_add"])).astype(np.float32)
    order = B.get("order", "up")
    if order == "up":            # rear-most first, so upstream licks cover the roots behind them
        rank = np.argsort(-(K["x0"] + rng.uniform(-0.5, 0.5, n) * dx))
    elif order == "down":
        rank = np.argsort(K["x0"] + rng.uniform(-0.5, 0.5, n) * dx)
    else:
        rank = rng.permutation(n)
    clB = _center(K, int(B.get("N", 26)))
    cats = []     # (polys, kind, body_index, sub, tx, ty, tch, rid, hw, th)

    def chord(cl):
        x, y = cl[0], cl[1]
        return np.maximum(np.sqrt((x - x[:, :1]) ** 2 + (y - y[:, :1]) ** 2).max(1), 1.0)

    chB = chord(clB)
    cats.append((_polys(*clB, K["asym"], K["curl"]), 0, np.arange(n), 0, K["x0"], K["y0"], chB, K["rid"], K["hw"], K["th"]))
    tt = np.linspace(0.0, 1.0, clB[0].shape[1], dtype=np.float32)[None, :]
    for li, (lf, wf) in enumerate(nest):
        wn = clB[3] * wf * np.clip((lf - tt) / lf, 0.0, 1.0) ** 0.6
        cats.append((_polys(clB[0], clB[1], clB[2], wn, K["asym"], K["curl"]), li + 1, np.arange(n), li + 1,
                     K["x0"], K["y0"], chB, K["rid"], K["hw"] * wf, K["th"]))
    KD = KG = None
    if kids:
        KD = _spawn(rng, K, clB, kids, s)
        clD = _center(KD, int(kids.get("N", 14)))
        sub_d = -2 if kids.get("under", True) else 10
        cats.append((_polys(*clD, KD["asym"], KD["curl"]), 8, KD["parent"], sub_d, KD["x0"], KD["y0"], chord(clD),
                     KD["rid"], KD["hw"], KD["th"]))
        if grand:
            KG = _spawn(rng, KD, clD, grand, s)
            clG = _center(KG, int(grand.get("N", 10)))
            sub_g = -3 if grand.get("under", True) else 11
            cats.append((_polys(*clG, KG["asym"], KG["curl"]), 9, KD["parent"][KG["parent"]], sub_g, KG["x0"], KG["y0"],
                         chord(clG), KG["rid"], KG["hw"], KG["th"]))
    pos = np.empty(n, np.int64)
    pos[rank] = np.arange(n)
    keys_b, keys_s, refs = [], [], []
    for ci, c in enumerate(cats):
        m = len(c[2])
        keys_b.append(pos[c[2]])
        keys_s.append(np.full(m, c[3], np.int64))
        refs.append(np.stack([np.full(m, ci, np.int64), np.arange(m)], 1))
    kb = np.concatenate(keys_b)
    ks = np.concatenate(keys_s)
    rf = np.concatenate(refs)
    order_ix = np.lexsort((ks, kb))
    rf = rf[order_ix]
    tot = len(rf) + 1
    F = {"s": s, "h": h, "w": w, "K": K, "KD": KD, "KG": KG,
         "kind": np.full(tot, -1, np.int16), "grp": np.zeros(tot, np.int32),
         "rid": np.zeros(tot, np.float32), "tx": np.zeros(tot, np.float32),
         "ty": np.zeros(tot, np.float32), "tch": np.ones(tot, np.float32),
         "hw": np.zeros(tot, np.float32), "th": np.zeros(tot, np.float32),
         "body": np.full(tot, -1, np.int32)}
    for ci, c in enumerate(cats):
        sel = np.nonzero(rf[:, 0] == ci)[0]
        j = rf[sel, 1]
        code = sel + 1
        F["kind"][code] = c[1]
        F["rid"][code] = c[7][j]
        F["tx"][code] = c[4][j]
        F["ty"][code] = c[5][j]
        F["tch"][code] = c[6][j]
        F["hw"][code] = c[8][j]
        F["th"][code] = c[9][j]
        F["body"][code] = c[2][j]
    # outline group: nested tongues belong to their body; kids / grand-kids are their own
    F["grp"] = np.where((F["kind"] >= 1) & (F["kind"] <= 7), -(F["body"] + 2), np.arange(tot)).astype(np.int32)
    F["grp"][0] = 0
    img = np.zeros((h, w), np.int32)
    Q = [np.round(c[0] * 4.0).astype(np.int32) for c in cats]
    fp = cv2.fillPoly
    for code0, (ci, j) in enumerate(rf):
        fp(img, [Q[ci][j]], code0 + 1, cv2.LINE_8, 2)
    F["idx"] = img
    if count_groups:
        # OVERLAP COUNT: polys dealt round-robin into G layers, each rasterised alone,
        # summed -> how many licks are stacked over every pixel (translucent stacking)
        cnt = np.zeros((h, w), np.uint8)
        for g in range(int(count_groups)):
            lay = np.zeros((h, w), np.uint8)
            for code0 in range(g, len(rf), int(count_groups)):
                ci, j = rf[code0]
                fp(lay, [Q[ci][j]], 1, cv2.LINE_8, 2)
            cnt += lay
        F["count"] = cnt
    return F


def _px(F, name):
    return F[name][F["idx"]]


def _tmap(F):
    """Root -> tip parameter per pixel (chord distance from the owning lick's root)."""
    X, Y = _fl_xy(F["h"], F["w"])
    i = F["idx"]
    dx = X - F["tx"][i]
    dy = Y - F["ty"][i]
    return np.clip(np.sqrt(dx * dx + dy * dy) / F["tch"][i], 0.0, 1.0)


def _edge(F, by="grp", top=True, mask=3):
    """Distance (px) to the nearest VISIBLE lick edge. by='grp' ignores the seams between
    a body and its own nested tongues; top=True puts the edge inside the lick that is
    drawn on top (a pinstripe belongs to the upper lick, as on a real hot rod)."""
    c = F["idx"]
    g = F[by][c] if by else c
    b = np.zeros(c.shape, bool)
    d = g[1:, :] != g[:-1, :]
    if top:
        up = c[1:, :] > c[:-1, :]
        b[1:, :] |= d & up
        b[:-1, :] |= d & ~up
    else:
        b[1:, :] |= d
        b[:-1, :] |= d
    d = g[:, 1:] != g[:, :-1]
    if top:
        up = c[:, 1:] > c[:, :-1]
        b[:, 1:] |= d & up
        b[:, :-1] |= d & ~up
    else:
        b[:, 1:] |= d
        b[:, :-1] |= d
    # mask=5 (DIST_MASK_PRECISE) gives round iso-lines; 3 is faster but polygonal
    return cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE if mask == 5 else mask)


def _cov(F):
    return (F["idx"] > 0).astype(np.float32)


def _aa(rgb, s):
    """Light anti-alias of the hard painter edges (sub-2px, below the car window)."""
    return cv2.GaussianBlur(rgb, (0, 0), max(0.45, 0.6 * s))


_MIN_SIDE = 512


def _look(fid, h, w, fn):
    key = (fid, int(h), int(w))
    v = _LOOK.get(key)
    if v is None:
        if len(_LOOK) >= 2:
            _LOOK.clear()
        k = int(np.ceil(_MIN_SIDE / float(max(1, min(int(h), int(w))))))
        if k > 1:
            # Small canvases (picker thumbnails, previews): the looks are authored in px at 2048, so
            # at 128 px keylines / crack lines would cover whole pixels and swamp the colour. Render
            # the same design at >= _MIN_SIDE and area-downsample -> a true miniature of the 2048 look.
            big = fn(int(h) * k, int(w) * k)
            v = tuple(cv2.resize(np.ascontiguousarray(a, np.float32), (int(w), int(h)), interpolation=cv2.INTER_AREA)
                      for a in big)
        else:
            v = fn(int(h), int(w))
        _LOOK[key] = v
    return v


def _fin(M, R, C, sm):
    out = []
    for a, lo in ((M, 0.0), (R, 15.0), (C, 0.0)):
        a = np.asarray(a, np.float32)
        if sm is not None and abs(float(sm) - 1.0) > 1e-6:
            mu = float(a.mean())
            a = mu + (a - mu) * float(sm)
        out.append(np.clip(a, lo, 255.0).astype(np.float32))
    return tuple(out)


def _paint_out(fid, fn, paint, shape, mask):
    h, w = _wh(shape)
    rgb = _look(fid, h, w, fn)[0]
    return _compose(rgb, paint, mask)


def _spec_out(fid, fn, shape, sm):
    h, w = _wh(shape)
    v = _look(fid, h, w, fn)
    return _fin(v[1], v[2], v[3], sm)


def _flake(h, w, seed, s):
    """1-2 px metal flake (below the car window; sparkle, not structure)."""
    return np.random.default_rng(seed).random((h, w), dtype=np.float32)


def _wh(shape):
    return (int(shape[0]), int(shape[1]))


def _compose(col, paint, mask):
    if paint.ndim == 3 and paint.shape[2] > 3:
        paint = paint[:, :, :3].copy()
    m = mask[:, :, None] if mask.ndim == 2 else mask
    return (np.clip(col, 0, 1).astype(np.float32) * m + paint[:, :, :3] * (1 - m)).astype(np.float32)


def _codeclass(F, table, default=0):
    """Per-pixel class (uint8) from per-code kind via a small table {kind: class}."""
    cc = np.full(len(F["kind"]), default, np.uint8)
    for kd, cl in table.items():
        cc[F["kind"] == kd] = cl
    cc[0] = table.get(-1, default)
    return cc[F["idx"]]


def _tq(t):
    return np.clip(np.asarray(t, np.float32) * 255.0 + 0.5, 0, 255).astype(np.uint8)


def _pal(classes):
    """classes: list (index = class) of stop lists [(pos, (a, b, c)), ...] -> LUT C x 256 x 3."""
    xs = np.linspace(0.0, 1.0, 256, dtype=np.float32)
    lut = np.zeros((len(classes), 256, 3), np.float32)
    for ci, stops in enumerate(classes):
        if not isinstance(stops, (list, tuple)) or not isinstance(stops[0], (list, tuple)) or len(stops[0]) != 2 \
                or not isinstance(stops[0][1], (list, tuple)):
            stops = [(0.0, stops), (1.0, stops)]
        xp = [p for p, _ in stops]
        for c in range(3):
            lut[ci, :, c] = np.interp(xs, xp, [v[c] for _, v in stops])
    return lut


def _g(lut, cls, tq):
    """Gather LUT[cls, tq] -> HxWx3 float32 (one fancy-index pass)."""
    flat = cls.astype(np.int32) * 256 + tq
    return np.take(lut.reshape(-1, 3), flat, axis=0)


def _warp(img, amp, cell, seed, s, aniso=1.0, octaves=3):
    """Turbulent displacement (cv2.remap) - ragged, flickering edges."""
    h, w = img.shape[:2]
    X, Y = _fl_xy(h, w)
    dx = (_fbm(h, w, cell * s, octaves, seed, aniso) - 0.5) * (2.0 * amp * s)
    dy = (_fbm(h, w, cell * s, octaves, seed + 7, aniso) - 0.5) * (2.0 * amp * s)
    return cv2.remap(img, (X + dx).astype(np.float32), (Y + dy).astype(np.float32),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _glow(a, sigma):
    """Wide Gaussian bloom, computed at 1/4 res when the radius is large."""
    a = np.asarray(a, np.float32)
    if sigma < 6:
        return cv2.GaussianBlur(a, (0, 0), sigma)
    h, w = a.shape[:2]
    sm_ = cv2.resize(a, (max(1, w // 4), max(1, h // 4)), interpolation=cv2.INTER_AREA)
    sm_ = cv2.GaussianBlur(sm_, (0, 0), sigma / 4.0)
    return cv2.resize(sm_, (w, h), interpolation=cv2.INTER_LINEAR)


def _lut1(stops, n=256):
    xs = np.linspace(0.0, 1.0, n, dtype=np.float32)
    out = np.zeros((n, 3), np.float32)
    for c in range(3):
        out[:, c] = np.interp(xs, [p for p, _ in stops], [v[c] for _, v in stops])
    return out


def _heat_rgb(heat, stops):
    """Map a 0..1 scalar field through a colour ramp (LUT, one gather)."""
    return np.take(_lut1(stops), _tq(heat).astype(np.int32), axis=0)


def _lum(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def _r_follow(R, rgb, k, r_dark, r_light):
    """Roughness partly SOLVED from the paint's own luma (monotone), so the spec's
    car-window structure sits exactly on the artwork's (FOLLOW); k = share."""
    return (1.0 - k) * R + k * (r_dark + (r_light - r_dark) * np.clip(_lum(rgb), 0.0, 1.0))


def _cells(h, w, cell, seed, s, jit=0.9):
    """Voronoi plates on a jittered lattice via cv2 distance-transform labels.
    Returns (label HxW int32, distance to the nearest crack in px, seed-distance)."""
    c = cell * s
    rng = np.random.default_rng(seed)
    gy = np.arange(c * 0.5, h + c, c)
    gx = np.arange(c * 0.5, w + c, c)
    YY, XX = np.meshgrid(gy, gx, indexing="ij")
    py = np.clip(YY.ravel() + rng.uniform(-0.5, 0.5, YY.size) * c * jit, 0, h - 1).astype(np.int32)
    px = np.clip(XX.ravel() + rng.uniform(-0.5, 0.5, XX.size) * c * jit, 0, w - 1).astype(np.int32)
    src = np.ones((h, w), np.uint8)
    src[py, px] = 0
    dseed, lab = cv2.distanceTransformWithLabels(src, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    b = np.zeros((h, w), bool)
    b[1:, :] |= lab[1:, :] != lab[:-1, :]
    b[:, 1:] |= lab[:, 1:] != lab[:, :-1]
    dcrack = cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 3)
    return lab, dcrack, dseed


def _hsv(hh, ss, vv):
    """Vectorised HSV -> RGB, all arrays in [0,1]."""
    hh = (np.asarray(hh, np.float32) % 1.0) * 6.0
    i = np.floor(hh)
    f = hh - i
    p = vv * (1.0 - ss)
    q = vv * (1.0 - ss * f)
    t = vv * (1.0 - ss * (1.0 - f))
    i = i.astype(np.int32) % 6
    r = np.choose(i, [vv, q, p, p, t, vv])
    g = np.choose(i, [t, vv, vv, q, p, p])
    b = np.choose(i, [p, p, t, vv, vv, q])
    return np.stack([r, g, b], -1).astype(np.float32)


# ===========================================================================
# RECIPES. Each finish = one idea on the lick library. Ticket: FLAMES SHELF
# 2026-10-06 (owner 2026-10-05 "build REAL flames before the beta").
# Metric movement per finish (law fine / follow / dead, before -> after) is in
# the comment above each recipe; full numbers in docs/handoff_reports/FLAMES_SHELF.md.
# ===========================================================================

# ---------------------------------------------------------------------------
# 01 flame_hotrod - HOT ROD FLAMES: OUTLINED classic licks. Yellow root ->
#    orange -> red tip with two nested hotter tongues, every lick edged with a
#    pale-blue pinstripe (owned by the lick on top, so overlaps read as layered
#    hand-laid flames), kids + grand-kids peeling off the body edges.
#    Spec: candy-metallic licks graded by nest level, satin enamel pinstripe,
#    coarse metal-flake black-cherry ground.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.149->0.224, follow 0.167->0.683, dead 0.0->0.003, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_hotrod(h, w):
    F = _field(h, w, 1101,
               B=dict(L=(390, 560), hw=(40, 54), dx=250, dy=88, jit=0.2, wave=(0.22, 0.34),
                      freq=(0.8, 1.1), curl=(1.2, 1.7), cs=(0.6, 0.72), taper=0.85, belly=0.25,
                      neck=0.16, flow=0.15, flow_cell=1100, side="band", band_rows=2, N=56),
               nest=((0.72, 0.58), (0.46, 0.28)),
               kids=dict(n=6, t=(0.18, 0.8), L=(0.10, 0.17), w=(0.5, 0.7), ang=(0.3, 0.55),
                         curl=(1.2, 1.9), cs=0.45, taper=0.9, belly=0.2, neck=0.15, N=18),
               grand=dict(n=1, t=(0.3, 0.6), L=(0.45, 0.6), w=(0.5, 0.65), ang=(0.3, 0.55),
                          curl=(1.2, 1.9), cs=0.45, taper=0.9, belly=0.2, neck=0.15, N=12))
    s = F["s"]
    cls = _codeclass(F, {-1: 0, 0: 1, 1: 2, 2: 3, 8: 4, 9: 5})
    e = _edge(F)
    fl = _flake(h, w, 1102, s)
    P = _pal([(0.15, 0.045, 0.07),
              [(0.0, (1.0, 0.80, 0.20)), (0.45, (1.0, 0.44, 0.05)), (1.0, (0.70, 0.05, 0.04))],
              [(0.0, (1.0, 0.90, 0.40)), (0.6, (1.0, 0.62, 0.10)), (1.0, (1.0, 0.50, 0.08))],
              [(0.0, (1.0, 0.93, 0.62)), (1.0, (1.0, 0.93, 0.62))],
              [(0.0, (1.0, 0.55, 0.08)), (1.0, (0.80, 0.08, 0.05))],
              [(0.0, (1.0, 0.45, 0.06)), (1.0, (0.75, 0.06, 0.05))]])
    t = _tmap(F)
    #            M    R    CC   per class, graded root -> tip
    S = _pal([(70, 120, 70),
              [(0.0, (175, 22, 16)), (1.0, (150, 95, 40))],
              [(0.0, (205, 18, 16)), (1.0, (190, 60, 30))],
              (235, 15, 16),
              [(0.0, (140, 40, 20)), (1.0, (120, 110, 45))],
              [(0.0, (120, 50, 24)), (1.0, (100, 120, 50))]])
    tq = _tq(t)
    col = _g(P, cls, tq)
    sp = _g(S, cls, tq)
    bgm = (cls == 0)
    col[bgm] *= (0.8 + 0.4 * fl[bgm])[:, None]
    sp[..., 0] += np.where(bgm, 150.0 * fl, 25.0 * (fl - 0.5))
    sp[..., 1] += np.where(bgm, 70.0 * fl, 0.0)
    stripe = (1.0 - _sm(0.9 * s, 1.9 * s, e)) * (cls > 0)
    # second, inset pinstripe (a hand-laid double line) 6-7 px inside every visible edge
    inner = np.exp(-((e - 6.5 * s) / (0.8 * s)) ** 2) * (cls > 0)
    stripe = np.maximum(stripe, 0.85 * inner)
    # spec: contour ripples parallel to every lick edge (12 px pitch) - the candy flake is laid
    # in the direction of each tongue, so the shimmer follows the flame shapes
    rip = np.cos(e * (6.2832 / (12.0 * s))) * (cls > 0) * _sm(3.0 * s, 9.0 * s, e)
    sp[..., 1] += 34.0 * rip
    sp[..., 0] -= 22.0 * rip
    col = _mix(col, np.array([0.55, 0.86, 1.0], np.float32), stripe)
    sp = _mix(sp, np.array([8.0, 150.0, 120.0], np.float32), stripe)
    return _aa(col, s), sp[..., 0], sp[..., 1], sp[..., 2]


def paint_flame_hotrod(paint, shape, mask, seed, pm, bb):
    return _paint_out("hotrod", _look_hotrod, paint, shape, mask)


def spec_flame_hotrod(shape, seed, sm, base_m, base_r):
    return _spec_out("hotrod", _look_hotrod, shape, sm)



def _wrap(name, fn):
    """paint_/spec_ pair for one recipe (same cached look -> spec sits on the paint)."""
    def p(paint, shape, mask, seed, pm, bb):
        return _paint_out(name, fn, paint, shape, mask)

    def q(shape, seed, sm, base_m, base_r):
        return _spec_out(name, fn, shape, sm)
    return p, q


def _per_code(F, table, default=0.0):
    v = np.full(len(F["kind"]), default, np.float32)
    for kd, val in table.items():
        v[F["kind"] == kd] = val
    v[0] = table.get(-1, default)
    return v[F["idx"]]


# ---------------------------------------------------------------------------
# 02 flame_true_fire - TRUE FIRE: turbulent REALISTIC tongues. No outlines:
#    a scalar heat field (nested cores hotter, cooling root -> tip, softened at
#    the edges), torn by turbulent displacement and flicker streaks, bloomed,
#    then pushed through a blackbody ramp. Wisp kids fork off every tongue.
#    Spec: hottest cores flash metallic + mirror, cool soot is rough and
#    heavily cleared - all read off the SAME heat field.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.184->0.29, follow 0.015->0.466, dead 0.267->0.0, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
#    FLAMES SHELF 2026-10-06 M7 pass: spec M/CC ranges narrowed to the paint's busyness (M5 73.4->~98), M7 80.4->~88 predicted.
# ---------------------------------------------------------------------------
def _look_true_fire(h, w):
    F = _field(h, w, 1201,
               B=dict(L=(300, 460), hw=(26, 38), dx=235, dy=62, jit=0.3, wave=(0.3, 0.5),
                      freq=(1.0, 1.6), curl=(0.6, 1.4), cs=(0.4, 0.6), taper=1.3, belly=0.3,
                      neck=0.2, flow=0.25, flow_cell=700, N=40),
               nest=((0.62, 0.55), (0.34, 0.28)),
               kids=dict(n=4, t=(0.2, 0.8), L=(0.2, 0.4), w=(0.35, 0.5), ang=(0.15, 0.4),
                         curl=(0.8, 1.8), taper=1.4, neck=0.15, wave=0.4, freq=1.6, N=16),
               grand=dict(n=2, t=(0.2, 0.7), L=(0.35, 0.6), w=(0.4, 0.55), ang=(0.15, 0.4),
                          curl=(0.8, 1.8), taper=1.4, neck=0.15, N=10))
    s = F["s"]
    t = _tmap(F)
    e = _edge(F, by="grp", top=False)
    base = _per_code(F, {-1: 0.04, 0: 0.56, 1: 0.76, 2: 0.93, 8: 0.5, 9: 0.44})
    heat = base * (1.0 - 0.72 * t ** 0.9) * (0.75 + 0.25 * _sm(0.0, 5.0 * s, e))
    heat = np.where(F["idx"] > 0, heat, 0.04).astype(np.float32)
    heat = cv2.GaussianBlur(heat, (0, 0), 1.6 * s)
    heat = _warp(heat, 14.0, 30.0, 1202, s, aniso=2.0, octaves=4)
    streak = 0.6 * _vn(h, w, 4.0 * s, 26.0 * s, 1203) + 0.4 * _vn(h, w, 9.0 * s, 40.0 * s, 1204)
    heat = heat * (0.62 + 0.7 * streak)
    heat = np.clip(heat + 0.3 * _glow(heat, 12.0 * s), 0.0, 1.0)
    rgb = _heat_rgb(heat, [(0.0, (0.17, 0.045, 0.03)), (0.22, (0.42, 0.05, 0.02)), (0.45, (0.82, 0.17, 0.02)),
                           (0.65, (1.0, 0.46, 0.05)), (0.82, (1.0, 0.76, 0.24)), (1.0, (1.0, 0.91, 0.62))])
    M = 40.0 + 140.0 * _sm(0.55, 0.92, heat)
    # iso-heat contours (a thermal-camera banding in the clear) - fine detail laid on the
    # fire's own temperature field, so it follows every tongue
    iso = np.cos(heat * (6.2832 * 7.0))
    R = 205.0 - 185.0 * heat + 42.0 * iso
    C = 16.0 + 70.0 * (1.0 - heat) ** 2 - 10.0 * iso
    return rgb, M, R, C


paint_flame_true_fire, spec_flame_true_fire = _wrap("true_fire", _look_true_fire)


# ---------------------------------------------------------------------------
# 03 flame_blue - BLUE FLAME: GAS-TORCH licks. A bright outer mantle on every tongue,
#    a translucent blue body with flow striations, a soft cyan inner cone, glow halo
#    and blue sparks on gunmetal. Spec: mantle + cone chrome, body satin metal.
#    FLAMES SHELF 2026-10-06 REWORK (orchestrator look verdict: lattice of identical cones): rebuilt on irregular overlapping
#    licks (L 150-500 px, jit 0.5, curl), detail inside each tongue. Law fine 0.289, follow 0.604, PASS; M7 recorded in FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_blue(h, w):
    F = _field(h, w, 1311,
               B=dict(L=(170, 480), hw=(18, 38), dx=200, dy=56, jit=0.5, wave=(0.15, 0.35), freq=(0.8, 1.6),
                      curl=(0.9, 1.8), cs=(0.55, 0.75), taper=0.9, belly=0.3, neck=0.14, flow=0.3, flow_cell=900, N=40),
               nest=((0.55, 0.40),),
               kids=dict(n=3, t=(0.2, 0.75), L=(0.2, 0.42), w=(0.4, 0.6), ang=(0.25, 0.5), curl=(0.8, 1.6),
                         cs=0.5, taper=0.9, neck=0.12, N=14))
    s = F["s"]
    cls = _codeclass(F, {-1: 0, 0: 1, 8: 1, 9: 1, 1: 2})
    t = _tmap(F)
    e = _edge(F, by="grp", mask=5)
    depth = np.clip(e / np.maximum(_px(F, "hw"), 1.0), 0.0, 1.0)
    lick = (cls > 0).astype(np.float32)
    # gas flame: bright outer mantle + translucent dark-blue interior + cyan inner cone
    wob = _fbm(h, w, 40.0 * s, 3, 1312)
    stri = 0.5 + 0.5 * np.cos(e * (6.2832 / (5.0 * s)) + 5.0 * wob)
    mantle = np.exp(-e / (2.2 * s))
    sheath = _heat_rgb(t, [(0.0, (0.28, 0.47, 1.0)), (0.6, (0.24, 0.29, 0.85)), (1.0, (0.36, 0.22, 0.64))])
    col = sheath * (0.45 + 0.25 * stri * (1.0 - t) + 0.55 * mantle)[..., None]
    cone = (cls == 2).astype(np.float32)
    conec = _heat_rgb(t, [(0.0, (0.85, 1.0, 1.0)), (1.0, (0.40, 0.85, 1.0))])
    cw = cone * _sm(0.05, 0.75, depth) * (0.8 + 0.2 * stri) * (1.0 - 0.5 * t)
    col = _mix(col, conec, cw)
    fade = 1.0 - 0.6 * _sm(0.75, 1.0, t)
    pit = _vn(h, w, 2.0 * s, 2.0 * s, 1313)
    gnd = np.array([0.07, 0.08, 0.11], np.float32) * (0.8 + 0.4 * pit)[..., None]
    halo = _glow(lick, 7.0 * s)
    gnd = gnd + halo[..., None] * np.array([0.08, 0.14, 0.32], np.float32)
    spark = (_vn(h, w, 1.3 * s, 1.3 * s, 1314) > 0.9) * np.clip(1.6 * halo, 0.0, 1.0)
    col = gnd * (1.0 - (lick * fade))[..., None] + col * (lick * fade)[..., None]
    col = _mix(col, np.array([0.75, 0.95, 1.0], np.float32), spark * (1.0 - lick))
    M = np.where(lick > 0, 170.0 + 70.0 * mantle + 70.0 * cw, 110.0 + 60.0 * pit)
    R = np.where(lick > 0, 30.0 + 60.0 * depth * (1.0 - cw) + 25.0 * stri, 150.0 - 40.0 * halo)
    C = np.where(lick > 0, 16.0 + 10.0 * stri, 70.0 + 40.0 * pit)
    M = np.where(spark * (1.0 - lick) > 0.5, 250.0, M)
    R = np.where(spark * (1.0 - lick) > 0.5, 15.0, R)
    R = _r_follow(R, col, 0.6, 200.0, 15.0)
    return _aa(col, s), M, R, C


paint_flame_blue, spec_flame_blue = _wrap("blue", _look_blue)


# ---------------------------------------------------------------------------
# 06 flame_ghost - GHOST FLAMES: TONAL licks. Long slender wisps barely a
#    shade off the charcoal, edged by a faint ghost line; the PEARL spec is
#    where they live - pearl licks with edge-parallel ripples on a satin
#    ground, a mirror pin-line on every edge. Straight on: a dark car; at an
#    angle: flames.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.004->0.428, follow 0.117->0.378, dead 0.0->0.0, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_ghost(h, w):
    F = _field(h, w, 1401,
               B=dict(L=(520, 780), hw=(28, 40), dx=250, dy=66, jit=0.25, wave=(0.3, 0.45),
                      freq=(0.8, 1.2), curl=(0.9, 1.4), cs=(0.6, 0.72), taper=0.9, belly=0.3,
                      neck=0.18, flow=0.2, flow_cell=1000, side="band", band_rows=3, N=56),
               nest=((0.6, 0.45),),
               kids=dict(n=3, t=(0.2, 0.75), L=(0.08, 0.14), w=(0.5, 0.7), ang=(0.3, 0.55),
                         curl=(1.2, 1.9), cs=0.45, taper=0.9, neck=0.15, N=14))
    s = F["s"]
    cls = _codeclass(F, {-1: 0, 0: 1, 1: 2, 8: 3})
    t = _tmap(F)
    e = _edge(F)
    tq = _tq(t)
    P = _pal([(0.135, 0.135, 0.15),
              [(0.0, (0.19, 0.185, 0.205)), (1.0, (0.15, 0.148, 0.165))],
              [(0.0, (0.215, 0.21, 0.235)), (1.0, (0.18, 0.176, 0.195))],
              [(0.0, (0.18, 0.176, 0.195)), (1.0, (0.15, 0.148, 0.165))]])
    S = _pal([(28, 165, 70),
              [(0.0, (150, 30, 16)), (1.0, (115, 60, 24))],
              [(0.0, (185, 20, 16)), (1.0, (160, 40, 18))],
              [(0.0, (135, 40, 18)), (1.0, (110, 70, 26))]])
    col = _g(P, cls, tq)
    sp = _g(S, cls, tq)
    lick = cls > 0
    rip = np.cos(e * (6.2832 / (10.0 * s))) * lick * _sm(3.0 * s, 8.0 * s, e)
    col += (0.012 * rip)[..., None]
    sp[..., 1] += 30.0 * rip
    sp[..., 0] += 20.0 * rip
    line = (1.0 - _sm(0.8 * s, 2.0 * s, e)) * lick
    col = _mix(col, np.array([0.27, 0.27, 0.30], np.float32), line)
    sp = _mix(sp, np.array([210.0, 15.0, 16.0], np.float32), line)
    return _aa(col, s), sp[..., 0], sp[..., 1], sp[..., 2]


paint_flame_ghost, spec_flame_ghost = _wrap("ghost", _look_ghost)


# ---------------------------------------------------------------------------
# 19 flame_tribal - TRIBAL FLAME: sharp BARBED BLADES. Sickle blades (blade
#    profile: thin root, thickest a quarter out, long taper to a needle; the
#    convex side bulges) hooking hard, each throwing backward-leaning thorn
#    barbs off its edges. Flat graphic: blood-red blades, a black keyline, on
#    brushed gunmetal. Spec: gloss enamel blades, flat-black keyline, raw
#    brushed metal (no clear) ground.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.145->0.585, follow 0.449->0.361, dead 0.478->0.034, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_tribal(h, w):
    F = _field(h, w, 1501,
               B=dict(L=(320, 460), hw=(30, 40), dx=215, dy=84, jit=0.18, wave=(0.12, 0.25),
                      freq=(0.9, 1.2), curl=(0.9, 1.3), cs=(0.55, 0.7), prof=1, asym=0.35, neck=0.22,
                      flow=0.18, flow_cell=1000, side="band", band_rows=2, N=44),
               kids=dict(n=3, t=(0.22, 0.7), L=(0.12, 0.2), w=(0.5, 0.7), ang=(0.5, 0.85),
                         curl=(0.2, 0.5), cs=0.3, prof=1, asym=0.2, inset=0.6, N=12))
    s = F["s"]
    cls = _codeclass(F, {-1: 0, 0: 1, 8: 2})
    t = _tmap(F)
    e = _edge(F)
    tq = _tq(t)
    P = _pal([(0.30, 0.30, 0.32),
              [(0.0, (0.48, 0.04, 0.03)), (0.3, (0.70, 0.06, 0.04)), (1.0, (0.86, 0.16, 0.05))],
              [(0.0, (0.62, 0.05, 0.04)), (1.0, (0.86, 0.16, 0.05))]])
    S = _pal([(235, 80, 0),
              [(0.0, (215, 20, 16)), (1.0, (180, 40, 16))],
              [(0.0, (200, 35, 16)), (1.0, (170, 55, 16))]])
    col = _g(P, cls, tq)
    sp = _g(S, cls, tq)
    ground = cls == 0
    br = _vn(h, w, 1.5 * s, 48.0 * s, 1502)
    col[ground] *= (0.86 + 0.28 * br[ground])[:, None]
    sp[..., 1] += np.where(ground, 22.0 * br, 0.0)
    key = (1.0 - _sm(1.6 * s, 2.8 * s, e)) * (cls > 0)
    col = _mix(col, np.array([0.08, 0.04, 0.04], np.float32), key)
    sp = _mix(sp, np.array([0.0, 230.0, 230.0], np.float32), key)
    col = _aa(col, s)
    R = _r_follow(sp[..., 1], col, 0.65, 235.0, -130.0)
    return col, sp[..., 0], R, sp[..., 2]


paint_flame_tribal, spec_flame_tribal = _wrap("tribal", _look_tribal)



# ---------------------------------------------------------------------------
# 07 flame_inferno - INFERNO: a firestorm WALL in three DEPTH layers. A far
#    layer of many small crimson licks, a middle layer, and a near layer of big
#    bright hooked tongues with hot inner tongues and peeling kids - parallax
#    depth, not one sheet. Each layer is edge-shaded with a dark soot rim so it
#    separates from the one behind, and sparks drift in the gaps. Spec: depth IS
#    the material - far wall rough and dull, near tongues polished metal.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.008->0.326, follow 0.735->0.717, dead 0.075->0.061, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_inferno(h, w):
    common = dict(wave=(0.22, 0.36), freq=(0.9, 1.3), cs=(0.55, 0.7), taper=0.85, belly=0.28,
                  neck=0.14, side="band", band_rows=2)
    layers = [
        (1701, dict(L=(110, 170), hw=(9, 13), dx=96, dy=26, jit=0.3, curl=(1.0, 1.6), flow=0.3, N=24, **common), (), None),
        (1702, dict(L=(220, 320), hw=(18, 26), dx=190, dy=54, jit=0.3, curl=(1.1, 1.6), flow=0.25, N=32, **common),
         ((0.62, 0.45),), None),
        (1703, dict(L=(380, 520), hw=(30, 42), dx=400, dy=136, jit=0.35, curl=(1.2, 1.7), flow=0.2, N=44, **common),
         ((0.72, 0.56), (0.46, 0.3)),
         dict(n=4, t=(0.2, 0.75), L=(0.12, 0.2), w=(0.5, 0.7), ang=(0.3, 0.55), curl=(1.3, 1.9), cs=0.45,
              taper=0.9, neck=0.15, N=14)),
    ]
    body = [[(0.0, (0.62, 0.10, 0.04)), (1.0, (0.34, 0.04, 0.03))],
            [(0.0, (0.92, 0.30, 0.04)), (0.7, (0.70, 0.10, 0.03)), (1.0, (0.45, 0.05, 0.03))],
            [(0.0, (1.0, 0.62, 0.10)), (0.6, (0.92, 0.28, 0.04)), (1.0, (0.66, 0.08, 0.03))]]
    hot = [(0.0, (1.0, 0.95, 0.62)), (0.6, (1.0, 0.78, 0.25)), (1.0, (1.0, 0.55, 0.08))]
    specs = [(45.0, 175.0, 160.0), (135.0, 92.0, 80.0), (228.0, 24.0, 16.0)]
    col = np.zeros((h, w, 3), np.float32) + np.array([0.13, 0.03, 0.03], np.float32)
    M = np.full((h, w), 18.0, np.float32)
    R = np.full((h, w), 225.0, np.float32)
    C = np.full((h, w), 210.0, np.float32)
    s = _fl_scale(h, w)

    def layer(li, hh, ww):
        # one LUT gather for colour + one for spec (perf), then the soot rim on top
        sd, B, nest, kids = layers[li]
        F = _field(hh, ww, sd, B=B, nest=nest, kids=kids)
        ss = F["s"]
        tq = _tq(_tmap(F))
        cls = _codeclass(F, {-1: 0, 0: 1, 1: 2, 2: 3, 8: 1, 9: 1})
        m0, r0, c0 = specs[li]
        hot95 = [(k, tuple(0.95 * v for v in c)) for k, c in hot]
        P = _pal([(0.0, 0.0, 0.0), body[li], hot95, hot])
        S = _pal([(0.0, 0.0, 0.0),
                  [(0.0, (m0, r0, c0)), (1.0, (m0, r0 + 30.0, c0 + 50.0))],
                  [(0.0, (m0 + 12.0, r0 - 10.0, c0)), (1.0, (m0 + 12.0, r0 + 20.0, c0 + 50.0))],
                  [(0.0, (m0 + 24.0, r0 - 20.0, c0)), (1.0, (m0 + 24.0, r0 + 10.0, c0 + 50.0))]])
        rim = 1.0 - _sm(0.7 * ss, (2.0 + 0.6 * li) * ss, _edge(F, by="grp"))
        c = _g(P, cls, tq)
        c *= (1.0 - 0.75 * rim)[..., None]
        spc = _g(S, cls, tq)
        spc += rim[..., None] * np.array([-90.0, 150.0, 120.0], np.float32)
        lick = (cls > 0).astype(np.float32)
        sp = [spc[..., 0], spc[..., 1], spc[..., 2]]
        if (hh, ww) != (h, w):
            # the far wall is rasterised at half res (perf; its licks are 9-13 px wide)
            up = lambda x: cv2.resize(np.ascontiguousarray(x, np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
            return up(c), up(lick), [up(x) for x in sp]
        return c, lick, sp

    for li in range(3):
        c, lk, sp = layer(li, (h + 1) // 2, (w + 1) // 2) if li == 0 else layer(li, h, w)
        if li == 0:
            a = lk[..., None]
            col = col + (c - col) * a
            M = M + (sp[0] - M) * lk
            R = R + (sp[1] - R) * lk
            C = C + (sp[2] - C) * lk
            continue
        col += _glow(lk, 9.0 * s)[..., None] * np.array([0.11, 0.025, 0.0], np.float32)
        on = lk > 0.5
        col = np.where(on[..., None], c, col)
        M = np.where(on, sp[0], M)
        R = np.where(on, sp[1], R)
        C = np.where(on, sp[2], C)
    # sparks: tiny hot points in the gaps, smeared downstream
    rng = np.random.default_rng(1704)
    n = int(1400 * (h * w) / (2048.0 * 2048.0)) + 8
    sp = np.zeros((h, w), np.float32)
    sp[rng.integers(0, h, n), rng.integers(0, w, n)] = 1.0
    sp = cv2.GaussianBlur(sp, (0, 0), sigmaX=max(0.6, 4.0 * s), sigmaY=max(0.5, 1.0 * s))
    sp = np.clip(sp / max(1e-6, float(sp.max())) * 1.6, 0, 1) * (col.sum(-1) < 0.9)
    col = _mix(col, np.array([1.0, 0.85, 0.45], np.float32), sp)
    M = M + 180.0 * sp
    R = R - 180.0 * sp
    R = _r_follow(R, col, 0.35, 235.0, 20.0)
    return _aa(col, s), M, R, C


paint_flame_inferno, spec_flame_inferno = _wrap("inferno", _look_inferno)


# ---------------------------------------------------------------------------
# 08 flame_white_hot - WHITE HOT: SPARK FIRE. Crisp tongues graded violet rim -> gold
#    -> white core, heat-contour ripples, molten spark trails raked through each
#    tongue, a thinning spark shower past the tips, lavender haze on graphite.
#    FLAMES SHELF 2026-10-06 REWORK (orchestrator look verdict: read as woven strands): rebuilt on irregular overlapping
#    licks (L 150-500 px, jit 0.5, curl), detail inside each tongue. Law fine 0.211, follow 0.649, PASS; M7 recorded in FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_white_hot(h, w):
    F = _field(h, w, 1811,
               B=dict(L=(180, 470), hw=(20, 42), dx=225, dy=70, jit=0.5, wave=(0.2, 0.4), freq=(0.8, 1.4),
                      curl=(1.0, 1.8), cs=(0.55, 0.72), taper=0.9, belly=0.3, neck=0.13, flow=0.3, flow_cell=1000,
                      side="band", band_rows=2, N=40),
               kids=dict(n=3, t=(0.25, 0.7), L=(0.22, 0.4), w=(0.4, 0.6), ang=(0.25, 0.5), curl=(1.0, 1.7),
                         cs=0.5, taper=0.9, neck=0.1, N=14))
    s = F["s"]
    t = _tmap(F)
    e = _edge(F, mask=5)
    lick = (F["idx"] > 0).astype(np.float32)
    depth = np.clip(e / np.maximum(_px(F, "hw"), 1.0), 0.0, 1.0)
    # WHITE-HOT SPARK FIRE: crisp tongues graded violet rim -> gold -> white core,
    # every tongue raked by streaking white spark trails (thermite spray) that keep
    # flying past the tips as a thinning shower; graphite ground with lavender haze
    rip = np.cos(e * (6.2832 / (11.0 * s))) * lick * _sm(2.5 * s, 7.0 * s, e)
    heat = np.clip(1.15 * depth ** 0.7 * (1.0 - 0.55 * t) + 0.1 * (1.0 - t) + 0.16 * rip, 0.0, 1.0)
    fl = _heat_rgb(heat, [(0.0, (0.40, 0.34, 0.92)), (0.25, (0.72, 0.52, 0.95)), (0.5, (1.0, 0.78, 0.55)),
                          (0.75, (1.0, 0.93, 0.72)), (1.0, (1.0, 1.0, 0.97))])
    d1 = _sm(0.58, 0.78, _vn(h, w, 4.0 * s, 34.0 * s, 1812))
    d2 = _sm(0.72, 0.86, _vn(h, w, 3.0 * s, 16.0 * s, 1813))
    tipz = np.clip(1.6 * _glow((lick * _sm(0.45, 0.9, t)).astype(np.float32), 14.0 * s), 0.0, 1.0) * (1.0 - lick)
    trail = d1 * lick * (0.3 + 0.7 * heat)
    spray = d2 * tipz
    col = _mix(fl, np.array([1.0, 0.62, 0.22], np.float32), 0.55 * trail)
    rim = (1.0 - _sm(0.7 * s, 2.0 * s, e)) * lick
    col = _mix(col, np.array([0.30, 0.22, 0.75], np.float32), 0.6 * rim)
    haze = _vn(h, w, 8.0 * s, 70.0 * s, 1814)
    halo = _glow(lick, 8.0 * s)
    gnd = np.array([0.10, 0.09, 0.14], np.float32) + (0.05 * haze)[..., None] + halo[..., None] * np.array([0.22, 0.16, 0.42], np.float32)
    gnd = _mix(gnd, np.array([1.0, 0.95, 0.85], np.float32), spray)
    a = lick * _sm(0.0, 0.12, t)
    col = gnd * (1.0 - a)[..., None] + col * a[..., None]
    M = np.where(lick > 0, 150.0 + 90.0 * heat, 60.0 + 40.0 * haze)
    R = np.where(lick > 0, 90.0 - 70.0 * heat, 190.0 - 60.0 * halo)
    C = np.where(lick > 0, 16.0 + 20.0 * (1.0 - heat), 120.0 - 50.0 * halo)
    M = _mix(M, np.float32(250.0), np.maximum(trail, spray))
    R = _mix(R, np.float32(8.0), np.maximum(trail, spray))
    R = _mix(R, np.float32(140.0), rim) + 45.0 * rip
    return _aa(col, s), M, R, C


paint_flame_white_hot, spec_flame_white_hot = _wrap("white_hot", _look_white_hot)


# ---------------------------------------------------------------------------
# 09 flame_rainbow - RAINBOW FIRE: SPECTRAL CONTOUR licks. Every lick is
#    filled with nested inset iso-bands (exact distance from its own edge), each
#    band the next hue round the wheel - a topographic rainbow inside every
#    tongue, the start hue different per lick. Spec: thin-film chrome whose
#    roughness alternates band to band, so the bands flash in turn.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.12->0.528, follow 0.047->0.384, dead 0.061->0.0, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_rainbow(h, w):
    F = _field(h, w, 1901,
               B=dict(L=(360, 520), hw=(34, 46), dx=260, dy=86, jit=0.2, wave=(0.2, 0.32), freq=(0.8, 1.1),
                      curl=(1.0, 1.5), cs=(0.55, 0.7), taper=0.9, belly=0.3, neck=0.18, flow=0.18,
                      side="band", band_rows=2, N=44),
               kids=dict(n=3, t=(0.2, 0.75), L=(0.12, 0.2), w=(0.5, 0.7), ang=(0.3, 0.55),
                         curl=(1.2, 1.8), cs=0.45, taper=0.9, neck=0.15, inherit=False, N=14))
    s = F["s"]
    e = _edge(F, mask=5)
    e = cv2.GaussianBlur(e, (0, 0), max(0.5, 1.6 * s))
    rid = _px(F, "rid")
    lick = F["idx"] > 0
    q = e / (7.0 * s)
    band = np.floor(q)
    frac = q - band
    hue = rid + band * 0.11
    val = 0.62 + 0.3 * _sm(0.0, 0.3, frac) * (1.0 - _sm(0.7, 1.0, frac))
    col = _hsv(hue, np.full_like(hue, 0.78), val)
    key = 1.0 - _sm(0.6 * s, 1.6 * s, e)
    col = np.where(lick[..., None], col, np.array([0.12, 0.10, 0.16], np.float32))
    col = _mix(col, np.array([0.07, 0.06, 0.10], np.float32), key * lick)
    odd = (band % 2.0)
    M = np.where(lick, 205.0 + 30.0 * odd, 70.0)
    R = np.where(lick, 18.0 + 70.0 * odd + 40.0 * (1.0 - val), 160.0)
    C = np.where(lick, 16.0 + 30.0 * frac, 90.0)
    R = _mix(R, np.float32(210.0), key * lick)
    return _aa(col, s), M, R, C


paint_flame_rainbow, spec_flame_rainbow = _wrap("rainbow", _look_rainbow)


# ---------------------------------------------------------------------------
# 10 flame_ember - EMBER COALS: a COAL BED with small rising licks. Voronoi
#    coals, each a dome (glowing orange rim, grey ash crust on top), split by
#    white-hot cracks; small hooked licks rise out of the bed scattered at
#    random and lean downstream. Spec: ash rough and dull, cracks a wet mirror,
#    coal rims satin, the licks metallic.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.162->0.332, follow 0.014->0.732, dead 0.459->0.017, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_ember(h, w):
    s = _fl_scale(h, w)
    lab, dc, ds = _cells(h, w, 84.0, 2001, s)
    rng = np.random.default_rng(2002)
    shade = rng.random(int(lab.max()) + 1).astype(np.float32)[lab]
    crack = 1.0 - _sm(0.5 * s, 3.0 * s, dc)
    rim = np.exp(-dc / (9.0 * s))
    dome = _sm(4.0 * s, 26.0 * s, dc)
    ash = _vn(h, w, 3.0 * s, 3.0 * s, 2003)
    pit = _sm(0.55, 0.75, _vn(h, w, 9.0 * s, 9.0 * s, 2005))
    ashc = np.array([0.36, 0.33, 0.31], np.float32) * (0.7 + 0.5 * ash)[..., None]
    coal = np.array([0.14, 0.06, 0.04], np.float32) * (0.7 + 0.6 * shade)[..., None]
    a = (dome * (0.35 + 0.6 * shade) * (1.0 - 0.6 * pit))[..., None]
    col = coal * (1.0 - a) + ashc * a
    col = col + rim[..., None] * np.array([0.75, 0.22, 0.03], np.float32) * (0.5 + 0.7 * shade)[..., None]
    col = _mix(col, np.array([1.0, 0.74, 0.25], np.float32), crack)
    F = _field(h, w, 2004,
               B=dict(L=(110, 190), hw=(10, 15), dx=230, dy=80, jit=0.9, wave=(0.3, 0.5), freq=(1.0, 1.5),
                      curl=(1.0, 1.7), cs=(0.45, 0.6), taper=0.9, belly=0.3, neck=0.18, flow=0.45, N=18),
               nest=((0.6, 0.45),))
    t = _tmap(F)
    cls = _codeclass(F, {-1: 0, 0: 1, 1: 2})
    lick = cls > 0
    lc = np.where((cls == 2)[..., None], _heat_rgb(t, [(0.0, (1.0, 0.95, 0.6)), (1.0, (1.0, 0.75, 0.25))]),
                  _heat_rgb(t, [(0.0, (1.0, 0.62, 0.1)), (0.7, (0.9, 0.25, 0.03)), (1.0, (0.6, 0.08, 0.03))]))
    col = np.minimum(col, 1.0)
    col = np.where(lick[..., None], lc, col)
    col += _glow(lick.astype(np.float32), 6.0 * s)[..., None] * np.array([0.3, 0.1, 0.0], np.float32)
    A = a[..., 0]
    M = 40.0 + 40.0 * shade - 30.0 * A + 170.0 * crack + 60.0 * rim
    R = 150.0 + 80.0 * A + 25.0 * ash - 60.0 * rim - 120.0 * crack
    C = 120.0 + 110.0 * A - 80.0 * rim - 100.0 * crack
    M = np.where(lick, 190.0 + 40.0 * (cls == 2), M)
    R = np.where(lick, 30.0 + 80.0 * t, R)
    C = np.where(lick, 16.0 + 40.0 * t, C)
    R = _r_follow(R, col, 0.45, 230.0, 20.0)
    return _aa(col, s), M, R, C


paint_flame_ember, spec_flame_ember = _wrap("ember", _look_ember)


# ---------------------------------------------------------------------------
# 11 flame_candy - CANDY FLAME: TRANSLUCENT stacked licks over BASS-BOAT
#    METALFLAKE. The licks are tinted film, not paint: every overlap multiplies
#    the candy again (overlap count from round-robin layer rasters), so stacked
#    tongues go deeper red while the big hex-ish metalflake (8-14 px plates,
#    each its own tilt) glints through the thin single layers and bare base.
#    Spec: candy-over-flake - every flake its own metal/roughness, roughness
#    rising with candy depth, a gloss lip where each film edge pools.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.079->0.325, follow 0.448->0.581, dead 0.0->0.0, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
#    FLAMES SHELF 2026-10-06 M7 pass: gold metalflake under the candy, film glass-smooth + max gloss, bare flake satin no-clear; M7 50.8->~89 predicted.
# ---------------------------------------------------------------------------
def _look_candy(h, w):
    F = _field(h, w, 2101,
               B=dict(L=(420, 600), hw=(30, 40), dx=300, dy=92, jit=0.25, wave=(0.22, 0.34), freq=(0.8, 1.1),
                      curl=(1.2, 1.7), cs=(0.58, 0.72), taper=0.85, belly=0.28, neck=0.16, flow=0.18,
                      side="band", band_rows=2, order="random", N=44),
               count_groups=6)
    s = F["s"]
    n = np.minimum(F["count"].astype(np.float32), 5.0)
    lab, dc, _ = _cells(h, w, 11.0, 2102, s)
    tilt = np.random.default_rng(2103).random(int(lab.max()) + 1).astype(np.float32)[lab]
    edge = _sm(0.0, 1.2 * s, dc)
    fl = (0.55 + 0.45 * tilt) * (0.75 + 0.25 * edge)
    silver = np.array([0.90, 0.80, 0.58], np.float32)[None, None, :] * fl[..., None]
    film = np.array([0.92, 0.10, 0.18], np.float32)
    col = silver * (film[None, None, :] ** n[..., None])
    col = np.maximum(col, 0.07)
    e = _edge(F, by=None, top=False)
    lip = (1.0 - _sm(0.6 * s, 2.0 * s, e)) * (n > 0)
    col = col * (1.0 - 0.3 * lip[..., None])
    # flake glint survives each candy layer the way the paint's flake contrast does
    M = 255.0 * (0.5 + (tilt - 0.5) * 0.45 ** n) - 10.0 * n
    R = 15.0 + 60.0 * (1.0 - tilt) * (1.0 - 0.15 * n) + 18.0 * n
    C = np.where(n > 0, 16.0 + 8.0 * n + 40.0 * lip, 150.0 + 40.0 * (1.0 - tilt))
    R = _r_follow(R, col, 0.6, 15.0, 140.0)
    return _aa(col, s), M, R, C


paint_flame_candy, spec_flame_candy = _wrap("candy", _look_candy)

# ---------------------------------------------------------------------------
# 12 flame_plasma - PLASMA FLAME: FORKED ELECTRIC licks. Thin lick channels
#    that fork (kids at wide angles, grand-kids off those) like a Lichtenberg
#    discharge, jittered by a fine electric warp; a white-violet filament core
#    inside a magenta channel, a wide ionised glow on a midnight ground.
#    Spec: filaments chrome, channel satin metal, glow fading to a matte ground.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.003->0.204, follow 0.561->0.862, dead 0.047->0.293, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
#    FLAMES SHELF 2026-10-06 M7 pass: three independent spec stories (ion-dust metal / arc roughness / charge-pool clear); M7 71.3->~90 predicted.
# ---------------------------------------------------------------------------
def _look_plasma(h, w):
    F = _field(h, w, 2201,
               B=dict(L=(420, 600), hw=(8, 11), dx=420, dy=118, jit=0.35, wave=(0.35, 0.55), freq=(1.6, 2.4),
                      curl=(0.5, 0.9), cs=(0.6, 0.75), prof=2, taper=0.8, neck=0.1, flow=0.35, N=40),
               nest=((0.85, 0.4),),
               kids=dict(n=3, t=(0.15, 0.8), L=(0.22, 0.4), w=(0.55, 0.75), ang=(0.45, 0.85),
                         curl=(0.5, 1.0), cs=0.6, prof=2, taper=0.8, neck=0.08, under=False, N=18),
               grand=dict(n=1, t=(0.2, 0.7), L=(0.3, 0.5), w=(0.5, 0.7), ang=(0.5, 0.9),
                          curl=(0.4, 0.8), cs=0.6, prof=2, taper=0.8, neck=0.08, under=False, N=12))
    s = F["s"]
    cls = _codeclass(F, {-1: 0, 0: 1, 8: 1, 9: 1, 1: 2})
    t = _tmap(F)
    tq = _tq(t)
    P = _pal([(0.0, 0.0, 0.0),
              [(0.0, (0.95, 0.35, 1.0)), (1.0, (0.62, 0.18, 0.95))],
              [(0.0, (1.0, 0.95, 1.0)), (1.0, (0.82, 0.78, 1.0))]])
    S = _pal([(0.0, 0.0, 0.0),
              [(0.0, (170.0, 70.0, 30.0)), (1.0, (150.0, 95.0, 40.0))],
              [(0.0, (250.0, 15.0, 16.0)), (1.0, (240.0, 25.0, 16.0))]])
    lick = (cls > 0).astype(np.float32)
    col = _g(P, cls, tq) * lick[..., None]
    sp = _g(S, cls, tq)
    g1 = _glow(lick, 4.0 * s)
    g2 = _glow(lick, 16.0 * s)
    field = _fbm(h, w, 120.0 * s, 4, 2202)
    ground = np.array([0.05, 0.03, 0.14], np.float32) * (0.7 + 0.6 * field)[..., None]
    halo = np.clip(1.2 * g1 + 0.35 * g2, 0.0, 1.0)
    bg = ground + halo[..., None] * np.array([0.55, 0.12, 0.70], np.float32)
    arc = 1.0 - _sm(0.0, 0.07, np.abs(_fbm(h, w, 18.0 * s, 2, 2204) - 0.5))
    bg = bg + (arc * (0.5 + 0.5 * halo))[..., None] * np.array([0.42, 0.14, 0.58], np.float32)
    col = np.where((lick > 0)[..., None], col, bg)
    # three independent spec stories on the ground: metal = ionised dust speckle,
    # roughness = the glow/arc corridor (follows the paint), clearcoat = macro charge pooling
    ion = _sm(0.55, 0.75, _vn(h, w, 2.5 * s, 2.5 * s, 2205))
    gs = np.stack([60.0 + 130.0 * ion,
                   np.minimum(200.0 - 120.0 * halo - 110.0 * arc, 190.0),
                   16.0 + 210.0 * field], -1)
    sp = np.where((lick > 0)[..., None], sp, gs)
    sp[..., 2] = np.where(cls == 2, 16.0, 16.0 + 210.0 * field)
    stack = np.concatenate([col, sp / 255.0], -1).astype(np.float32)
    stack = _warp(stack, 3.0, 9.0, 2203, s, octaves=2)
    col, sp = stack[..., :3], stack[..., 3:] * 255.0
    return _aa(col, s), sp[..., 0], sp[..., 1], sp[..., 2]


paint_flame_plasma, spec_flame_plasma = _wrap("plasma", _look_plasma)


# ---------------------------------------------------------------------------
# 13 flame_cold - COLD FIRE: FACETED CRYSTAL licks. Blade-profile licks cut
#    into crystal facets: split down the axis into a lit and a shadow side, and
#    stepped along the length - every facet its own hashed shade, like cut ice.
#    Fine frost needles grow on the navy ground. Spec: facets alternate mirror /
#    satin ice-chrome by facet hash; frost rough, ground matte.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.063->0.253, follow 0.147->0.722, dead 0.001->0.003, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
#    FLAMES SHELF 2026-10-06 M7 pass: pale ice-steel palette + slate frost ground (name = low saturation); M7 58.3->~88 predicted.
# ---------------------------------------------------------------------------
def _look_cold(h, w):
    F = _field(h, w, 2301,
               B=dict(L=(340, 500), hw=(30, 42), dx=250, dy=84, jit=0.22, wave=(0.15, 0.25), freq=(0.8, 1.1),
                      curl=(0.7, 1.1), cs=(0.55, 0.7), prof=1, asym=0.25, taper=0.9, neck=0.18, flow=0.15,
                      side="band", band_rows=2, N=14),
               kids=dict(n=2, t=(0.25, 0.7), L=(0.15, 0.25), w=(0.5, 0.7), ang=(0.35, 0.6),
                         curl=(0.8, 1.2), cs=0.5, prof=1, taper=0.9, neck=0.15, N=10))
    s = F["s"]
    X, Y = _fl_xy(h, w)
    i = F["idx"]
    th = F["th"][i]
    side = ((X - F["tx"][i]) * np.sin(th) - (Y - F["ty"][i]) * np.cos(th)) > 0
    t = _tmap(F)
    step = np.floor(t * 6.0).astype(np.int32)
    fid = (i.astype(np.int64) * 31 + step * 7 + side.astype(np.int32) * 3) % 997
    hsh = np.random.default_rng(2302).random(997).astype(np.float32)[fid]
    lick = i > 0
    e = _edge(F)
    edge = 1.0 - _sm(0.6 * s, 1.8 * s, e)
    lit = np.where(side, 0.75 + 0.25 * hsh, 0.35 + 0.3 * hsh)
    ice = _heat_rgb(t, [(0.0, (0.90, 0.96, 1.0)), (0.5, (0.70, 0.82, 0.92)), (1.0, (0.46, 0.58, 0.74))])
    col = ice * lit[..., None]
    col = _mix(col, np.array([0.95, 0.99, 1.0], np.float32), edge)
    frost = _vn(h, w, 1.5 * s, 14.0 * s, 2303) * _vn(h, w, 14.0 * s, 1.5 * s, 2304)
    fr = _sm(0.35, 0.6, frost)
    gnd = np.array([0.09, 0.10, 0.13], np.float32) + fr[..., None] * np.array([0.36, 0.40, 0.45], np.float32)
    col = np.where(lick[..., None], col, gnd)
    mir = hsh > 0.5
    M = np.where(lick, np.where(mir, 235.0, 150.0) + 15.0 * lit, 40.0 + 80.0 * fr)
    R = np.where(lick, np.where(mir, 16.0, 90.0) + 40.0 * (1.0 - lit), 200.0 - 60.0 * fr)
    C = np.where(lick, 16.0 + 30.0 * (1.0 - lit), 160.0 - 60.0 * fr)
    R = np.where(lick, _mix(R, np.float32(20.0), edge), R)
    return _aa(col, s), M, R, C


paint_flame_cold, spec_flame_cold = _wrap("cold", _look_cold)


# ---------------------------------------------------------------------------
# 14 flame_lava - LAVA FLAME: MOLTEN licks carrying a BREAKING CRUST. Big
#    licks of glowing molten rock; floating on each a crust of dark basalt
#    plates (Voronoi) whose cracks open wider toward the tip as the flow tears
#    it apart. The ground is cooled ropy pahoehoe - fine folded ridges. Spec:
#    molten seams glossy metal, crust plates rough and dull, ground mid-satin.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.067->0.533, follow 0.732->0.724, dead 0.453->0.001, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_lava(h, w):
    F = _field(h, w, 2401,
               B=dict(L=(420, 600), hw=(44, 58), dx=330, dy=110, jit=0.25, wave=(0.2, 0.32), freq=(0.8, 1.1),
                      curl=(1.0, 1.5), cs=(0.58, 0.72), taper=0.85, belly=0.32, neck=0.16, flow=0.18,
                      side="band", band_rows=2, N=44))
    s = F["s"]
    t = _tmap(F)
    lick = F["idx"] > 0
    e = _edge(F, by=None)
    lab, dc, ds = _cells(h, w, 34.0, 2402, s)
    shade = np.random.default_rng(2403).random(int(lab.max()) + 1).astype(np.float32)[lab]
    gap = (0.8 + 7.0 * t * t) * s
    crust = _sm(gap, gap + 1.5 * s, dc) * _sm(3.0 * s, 9.0 * s, e)
    molten = _heat_rgb(t, [(0.0, (1.0, 0.86, 0.35)), (0.5, (1.0, 0.45, 0.06)), (1.0, (0.78, 0.12, 0.03))])
    basalt = np.array([0.13, 0.10, 0.10], np.float32) * (0.75 + 0.5 * shade)[..., None]
    lv = _mix(molten, basalt, crust)
    X, Y = _fl_xy(h, w)
    fold = _fbm(h, w, 90.0 * s, 3, 2404)
    rope = 0.5 + 0.5 * np.sin((X + 26.0 * s * np.sin(Y / (22.0 * s) + 6.0 * fold)) * (6.2832 / (11.0 * s)))
    gnd = np.array([0.09, 0.08, 0.08], np.float32) * (0.7 + 0.6 * rope)[..., None]
    gnd = gnd + _glow(lick.astype(np.float32), 10.0 * s)[..., None] * np.array([0.35, 0.08, 0.0], np.float32)
    col = np.where(lick[..., None], lv, gnd)
    M = np.where(lick, 210.0 - 150.0 * crust + 20.0 * shade, 90.0 + 50.0 * rope)
    R = np.where(lick, 20.0 + 200.0 * crust - 30.0 * shade * crust, 120.0 + 70.0 * (1.0 - rope))
    C = np.where(lick, 16.0 + 200.0 * crust, 110.0 + 50.0 * rope)
    return _aa(col, s), M, R, C


paint_flame_lava, spec_flame_lava = _wrap("lava", _look_lava)


# ---------------------------------------------------------------------------
# 15 flame_phoenix - PHOENIX FIRE: FEATHER-LICKS. Each lick is a fire feather:
#    a bright rachis down its axis and chevron barbs swept back from it (barb
#    phase = along-length minus distance-from-edge), gold at the root through
#    crimson to a dark wine tip; small feather-kids fan from the edges.
#    Spec: barbs alternate polished metal / satin, rachis chrome, the plumage
#    ground a dark satin.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.203->0.375, follow 0.909->0.695, dead 0.618->0.073, law PASS->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_phoenix(h, w):
    F = _field(h, w, 2501,
               B=dict(L=(360, 520), hw=(32, 44), dx=270, dy=90, jit=0.22, wave=(0.18, 0.3), freq=(0.8, 1.1),
                      curl=(0.9, 1.4), cs=(0.6, 0.72), taper=0.8, belly=0.35, neck=0.2, flow=0.15,
                      side="band", band_rows=2, N=44),
               kids=dict(n=3, t=(0.3, 0.8), L=(0.2, 0.3), w=(0.5, 0.65), ang=(0.3, 0.5),
                         curl=(1.0, 1.5), cs=0.5, taper=0.8, neck=0.15, N=14))
    s = F["s"]
    t = _tmap(F)
    tch = _px(F, "tch")
    hw = _px(F, "hw")
    e = _edge(F, mask=5)
    lick = F["idx"] > 0
    along = t * tch
    rid = _px(F, "rid")
    ph = (along + 1.25 * e) / ((8.0 + 5.0 * rid) * s)
    barb = 0.5 + 0.5 * np.cos(ph * 6.2832)
    # vane splits: a few barbs part from their neighbours (dark gap), hashed per barb + feather
    bi = (np.floor(ph).astype(np.int64) * 13 + F["idx"].astype(np.int64) * 7) % 509
    split = (np.random.default_rng(2503).random(509).astype(np.float32)[bi] < 0.14).astype(np.float32)
    split *= _sm(0.25, 0.5, np.abs((ph % 1.0) - 0.5))
    ridge = cv2.dilate(e, np.ones((5, 5), np.uint8)) - e
    rach = (1.0 - _sm(0.0, 0.6, ridge)) * _sm(3.0 * s, 8.0 * s, e)
    rach = cv2.GaussianBlur(cv2.dilate(rach, np.ones((3, 3), np.uint8)), (0, 0), max(0.5, 0.8 * s))
    fe = _heat_rgb(t, [(0.0, (1.0, 0.85, 0.30)), (0.35, (1.0, 0.48, 0.08)), (0.75, (0.82, 0.10, 0.06)),
                       (1.0, (0.40, 0.03, 0.08))])
    vane = _sm(0.0, 14.0 * s, e)
    col = fe * ((0.62 + 0.38 * barb) * (0.75 + 0.25 * vane) * (1.0 - 0.75 * split))[..., None]
    col = _mix(col, np.array([1.0, 0.95, 0.70], np.float32), 0.9 * rach)
    key = 1.0 - _sm(0.6 * s, 1.5 * s, e)
    col = col * (1.0 - 0.7 * key)[..., None]
    gn = _vn(h, w, 6.0 * s, 30.0 * s, 2502)
    gnd = np.array([0.16, 0.04, 0.05], np.float32) * (0.75 + 0.5 * gn)[..., None]
    col = np.where(lick[..., None], col, gnd)
    M = np.where(lick, 120.0 + 110.0 * barb + 30.0 * rach - 80.0 * split, 60.0)
    R = np.where(lick, 120.0 - 95.0 * barb - 60.0 * rach + 80.0 * key + 90.0 * split, 150.0 + 40.0 * gn)
    C = np.where(lick, 16.0 + 40.0 * (1.0 - barb), 60.0)
    return _aa(col, s), M, R, C


paint_flame_phoenix, spec_flame_phoenix = _wrap("phoenix", _look_phoenix)


# ---------------------------------------------------------------------------
# 16 flame_toxic - TOXIC FLAME: RADIOACTIVE FIRE. Tongues emerge white-hot (soft root
#    fade), cool to acid lime and fade at the tip; flicker + striation inside, a
#    particle stream shed off the tips, drifting toxic-violet smoke.
#    FLAMES SHELF 2026-10-06 REWORK (orchestrator look verdict: read as scales/leaves; slime-drip + bubble variants also read as foliage): rebuilt on irregular overlapping
#    licks (L 150-500 px, jit 0.5, curl), detail inside each tongue. Law fine 0.243, follow 0.735, PASS; M7 recorded in FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_toxic(h, w):
    F = _field(h, w, 2611,
               B=dict(L=(170, 460), hw=(18, 38), dx=205, dy=60, jit=0.5, wave=(0.25, 0.45), freq=(0.9, 1.5),
                      curl=(1.1, 2.0), cs=(0.55, 0.72), taper=0.9, belly=0.3, neck=0.12, flow=0.3, flow_cell=1000, N=44),
               nest=((0.55, 0.45),),
               kids=dict(n=3, t=(0.2, 0.75), L=(0.2, 0.4), w=(0.4, 0.6), ang=(0.3, 0.55), curl=(1.1, 1.9),
                         cs=0.5, taper=0.9, neck=0.1, N=14))
    s = F["s"]
    cls = _codeclass(F, {-1: 0, 0: 1, 8: 1, 9: 1, 1: 2})
    t = _tmap(F)
    e = _edge(F, by="grp", mask=5)
    lick = (cls > 0).astype(np.float32)
    # RADIOACTIVE FIRE: root-hot acid tongues fading out at the tip, a hotter inner
    # tongue, flicker streaks, a stream of glowing particles shed downstream off the
    # tips, all wrapped in drifting toxic-violet smoke
    flick = _vn(h, w, 5.0 * s, 28.0 * s, 2617)
    soft = _sm(0.0, 3.0 * s, e)
    heat = (0.75 + 0.3 * np.exp(-((t - 0.22) / 0.18) ** 2) - 0.75 * t + 0.25 * (cls == 2) * (1.0 - t) + 0.45 * (flick - 0.5)
            + 0.25 * np.exp(-e / (2.0 * s)) * (1.0 - t)) * lick
    stri = np.cos(e * (6.2832 / (11.0 * s)) + 4.0 * flick) * lick * (1.0 - t)
    heat = np.clip(cv2.GaussianBlur(heat.astype(np.float32), (0, 0), 1.4 * s) + 0.22 * stri, 0.0, 1.0)
    alpha = cv2.GaussianBlur((lick * (1.0 - _sm(0.55, 1.0, t)) * _sm(0.0, 0.2, t)).astype(np.float32), (0, 0), 1.2 * s)
    fire = _heat_rgb(heat, [(0.0, (0.05, 0.30, 0.10)), (0.3, (0.30, 0.78, 0.05)), (0.55, (0.80, 1.0, 0.10)),
                            (0.8, (0.95, 1.0, 0.25)), (1.0, (1.0, 1.0, 0.85))])
    smoke = _fbm(h, w, 90.0 * s, 4, 2618)
    curl = _vn(h, w, 8.0 * s, 46.0 * s, 2619)
    sm = np.clip(1.4 * (smoke - 0.35) + 0.25 * (curl - 0.5), 0.0, 1.0)
    gnd = _mix(np.array([0.05, 0.03, 0.08], np.float32), np.array([0.36, 0.14, 0.48], np.float32), sm[..., None])
    halo = _glow(alpha, 8.0 * s)
    gnd = gnd + halo[..., None] * np.array([0.30, 0.60, 0.05], np.float32)
    # particle stream: short streaks, denser just downstream of hot tips
    part = _sm(0.78, 0.9, _vn(h, w, 4.0 * s, 14.0 * s, 2620))
    feed = np.clip(1.8 * _glow((lick * _sm(0.5, 0.9, t)).astype(np.float32), 14.0 * s), 0.0, 1.0)
    part = part * feed * (1.0 - alpha)
    col = gnd * (1.0 - alpha)[..., None] + fire * alpha[..., None]
    col = _mix(col, np.array([0.85, 1.0, 0.35], np.float32), part)
    M = 40.0 + 100.0 * sm + 120.0 * alpha * heat + 200.0 * part
    R = 200.0 - 170.0 * alpha * (0.4 + 0.6 * heat) - 60.0 * sm - 150.0 * part
    C = 150.0 - 134.0 * alpha - 40.0 * sm
    R = R - 95.0 * stri * alpha
    return _aa(col, s), M, R, C


paint_flame_toxic, spec_flame_toxic = _wrap("toxic", _look_toxic)

# ---------------------------------------------------------------------------
# 17 flame_pink - PINK FLAME: HOLLOW NEON licks. No fill at all - every lick
#    is a bent glass neon tube tracing its own outline (all outlines kept, so
#    tubes cross over each other like a sign), a hot white core in a pink
#    tube, a soft magenta bloom on a deep plum ground. Spec: tubes glass-gloss
#    (low metal, mirror smooth), bloom satin, ground matte.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.034->0.478, follow 0.488->0.981, dead 0.032->0.348, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_pink(h, w):
    F = _field(h, w, 2701,
               B=dict(L=(420, 600), hw=(34, 46), dx=360, dy=124, jit=0.22, wave=(0.22, 0.34), freq=(0.8, 1.1),
                      curl=(1.2, 1.7), cs=(0.55, 0.7), taper=0.85, belly=0.3, neck=0.16, flow=0.18,
                      side="band", band_rows=2, N=48),
               kids=dict(n=2, t=(0.25, 0.7), L=(0.15, 0.25), w=(0.5, 0.7), ang=(0.3, 0.55),
                         curl=(1.2, 1.8), cs=0.45, taper=0.9, neck=0.15, N=14))
    s = F["s"]
    e = _edge(F, by=None, top=False)
    tube = np.exp(-(e / (1.6 * s)) ** 2)
    core = np.exp(-(e / (0.7 * s)) ** 2)
    bloom = np.clip(_glow(tube, 3.0 * s) * 2.2 + _glow(tube, 10.0 * s) * 0.9, 0.0, 1.0)
    gn = _vn(h, w, 40.0 * s, 40.0 * s, 2702)
    col = np.array([0.10, 0.03, 0.09], np.float32) * (0.8 + 0.4 * gn)[..., None]
    col = col + bloom[..., None] * np.array([0.55, 0.08, 0.38], np.float32)
    col = _mix(col, np.array([1.0, 0.32, 0.72], np.float32), tube)
    col = _mix(col, np.array([1.0, 0.92, 0.97], np.float32), 0.85 * core)
    M = 40.0 + 30.0 * bloom - 20.0 * tube
    R = 200.0 - 110.0 * bloom - 75.0 * tube
    C = 190.0 - 120.0 * bloom - 54.0 * tube
    return _aa(col, s), M, R, C


paint_flame_pink, spec_flame_pink = _wrap("pink", _look_pink)


# ---------------------------------------------------------------------------
# 18 flame_smoke - SMOKE & FIRE: licks DISSOLVING into smoke. Each lick is
#    solid fire at the root; past mid-length it breaks up - the tip is torn
#    by a strong curl-noise warp into grey smoke wisps (ridged fine noise) that
#    trail downstream, so fire turns to smoke along every tongue. Spec: fire
#    glossy metal, smoke rough satin with fine streaks, ground matte charcoal.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.041->0.229, follow 0.211->0.7, dead 0.0->0.004, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_smoke(h, w):
    F = _field(h, w, 2801,
               B=dict(L=(240, 340), hw=(18, 24), dx=240, dy=64, jit=0.25, wave=(0.2, 0.32), freq=(0.8, 1.1),
                      curl=(1.3, 1.9), cs=(0.32, 0.45), taper=0.75, belly=0.3, neck=0.1, flow=0.2,
                      side="band", band_rows=2, N=40),
               nest=((0.5, 0.45),))
    s = F["s"]
    t = _tmap(F)
    kind = _px(F, "kind")
    lick = (F["idx"] > 0).astype(np.float32)
    fire_a = lick * (1.0 - _sm(0.62, 0.95, t))
    src = lick * _sm(0.55, 0.85, t)
    trail = cv2.GaussianBlur(src, (0, 0), sigmaX=max(1.0, 30.0 * s), sigmaY=max(0.6, 5.0 * s))
    trail = np.roll(trail, int(round(44.0 * s)), axis=1)
    dens = np.clip(0.35 + cv2.GaussianBlur(src, (0, 0), 3.0 * s) + 3.2 * trail, 0.0, 1.0)
    # streak filaments are made in flow space and warped WITH the smoke, so they curl together
    # long meandering iso-lines of stretched noise = smoke filaments (not a cellular network)
    streak = np.maximum(1.0 - _sm(0.0, 0.05, np.abs(_vn(h, w, 7.0 * s, 70.0 * s, 2803) - 0.5)),
                        0.7 * (1.0 - _sm(0.0, 0.05, np.abs(_vn(h, w, 12.0 * s, 110.0 * s, 2807) - 0.5))))
    stack = np.dstack([fire_a, dens, t * lick, streak]).astype(np.float32)
    stack = _warp(stack, 26.0, 80.0, 2802, s, aniso=1.6, octaves=2)
    fa, dn, tw, wisp = stack[..., 0], stack[..., 1], stack[..., 2], stack[..., 3]
    smoke = np.clip(dn * (0.2 + 1.0 * wisp), 0.0, 1.0)
    hot = np.where((kind >= 1)[..., None],
                   _heat_rgb(tw, [(0.0, (1.0, 0.92, 0.55)), (1.0, (1.0, 0.7, 0.2))]),
                   _heat_rgb(tw, [(0.0, (1.0, 0.6, 0.1)), (0.5, (0.9, 0.25, 0.04)), (1.0, (0.55, 0.1, 0.05))]))
    gnd = np.array([0.07, 0.065, 0.065], np.float32) * (0.85 + 0.3 * _vn(h, w, 30.0 * s, 30.0 * s, 2804))[..., None]
    col = _mix(gnd, np.array([0.74, 0.72, 0.71], np.float32), 0.92 * smoke)
    fa = np.clip(fa, 0.0, 1.0)
    flick = 0.6 * _vn(h, w, 4.0 * s, 22.0 * s, 2805) + 0.4 * _vn(h, w, 7.0 * s, 36.0 * s, 2806)
    hot = hot * (0.45 + 0.85 * flick)[..., None]
    col = _mix(col, np.minimum(hot, 1.0), fa)
    # embers carried in the smoke: tiny hot points smeared downstream
    rng = np.random.default_rng(2808)
    n = int(2600 * (h * w) / (2048.0 * 2048.0)) + 8
    em = np.zeros((h, w), np.float32)
    em[rng.integers(0, h, n), rng.integers(0, w, n)] = 1.0
    em = cv2.GaussianBlur(em, (0, 0), sigmaX=max(0.6, 3.5 * s), sigmaY=max(0.5, 1.1 * s))
    em = np.clip(em / max(1e-6, float(em.max())) * 2.2, 0.0, 1.0) * _sm(0.08, 0.3, smoke) * (1.0 - fa)
    col = _mix(col, np.array([1.0, 0.72, 0.3], np.float32), em)
    M = 30.0 + 110.0 * smoke * wisp + 170.0 * fa + 180.0 * em
    R = 215.0 - 150.0 * smoke * wisp - fa * (200.0 - 90.0 * flick) - 170.0 * em
    C = 200.0 - 60.0 * smoke - 175.0 * fa
    R = _r_follow(R, col, 0.4, 230.0, 20.0)
    return _aa(col, s), M, R, C


paint_flame_smoke, spec_flame_smoke = _wrap("smoke", _look_smoke)


# ---------------------------------------------------------------------------
# 19 flame_dragon - DRAGON FIRE: SCROLL licks with SCALES. Licks whose tips
#    coil right round into spiral scrolls (cloud-dragon style curl), armoured
#    inside with scallop scales (Voronoi rings), a double gold keyline round
#    every scroll on a lacquer-black ground. Spec: gold keyline mirror metal,
#    scales alternating polished / satin metal, black lacquer gloss.
#    FLAMES SHELF 2026-10-06 audit (owner: build REAL flame licks before the beta): Finish Law
#    fine 0.006->0.385, follow 0.413->0.577, dead 0.504->0.411, law FAIL->PASS; M7 recorded in docs/handoff_reports/FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_dragon(h, w):
    F = _field(h, w, 2901,
               B=dict(L=(340, 480), hw=(30, 40), dx=270, dy=96, jit=0.22, wave=(0.15, 0.25), freq=(0.7, 1.0),
                      curl=(3.2, 4.2), cs=(0.45, 0.55), taper=0.75, belly=0.25, neck=0.18, flow=0.15,
                      side="band", band_rows=2, N=64),
               kids=dict(n=2, t=(0.2, 0.6), L=(0.18, 0.28), w=(0.45, 0.6), ang=(0.3, 0.5),
                         curl=(3.0, 4.0), cs=0.4, taper=0.8, neck=0.15, N=24))
    s = F["s"]
    t = _tmap(F)
    lick = F["idx"] > 0
    e = _edge(F, mask=5)
    lab, dc, ds = _cells(h, w, 15.0, 2902, s, jit=0.6)
    ring = 0.5 + 0.5 * np.cos(ds * (6.2832 / (5.0 * s)))
    sc = np.random.default_rng(2903).random(int(lab.max()) + 1).astype(np.float32)[lab]
    body = _heat_rgb(t, [(0.0, (0.92, 0.20, 0.06)), (0.6, (0.70, 0.06, 0.05)), (1.0, (0.45, 0.04, 0.06))])
    scale = (0.65 + 0.25 * ring + 0.15 * sc) * _sm(0.0, 1.5 * s, dc)
    col = body * scale[..., None]
    gold1 = np.exp(-((e - 1.4 * s) / (1.0 * s)) ** 2)
    gold2 = np.exp(-((e - 5.0 * s) / (0.7 * s)) ** 2)
    gold = np.clip(gold1 + 0.8 * gold2, 0.0, 1.0)
    col = _mix(col, np.array([1.0, 0.80, 0.30], np.float32), gold)
    gnd = np.array([0.035, 0.03, 0.03], np.float32) + (_vn(h, w, 60.0 * s, 60.0 * s, 2904) * 0.03)[..., None]
    col = np.where(lick[..., None], col, gnd)
    M = np.where(lick, 150.0 + 70.0 * ring * (sc > 0.5) + 90.0 * gold, 20.0)
    R = np.where(lick, 90.0 - 50.0 * ring + 40.0 * (sc <= 0.5) - 70.0 * gold, 30.0)
    C = np.where(lick, 40.0 + 40.0 * (1.0 - ring) - 24.0 * gold, 16.0)
    R = _r_follow(R, col, 0.55, 30.0, 220.0)
    return _aa(col, s), M, R, C


paint_flame_dragon, spec_flame_dragon = _wrap("dragon", _look_dragon)


# ---------------------------------------------------------------------------
# 04 flame_green - GREEN FIRE: WITCHFIRE AS LIGHT. Luminous mantle edges, a hollow
#    body that dissolves at root and tip, a hot flickering core, ghost filaments
#    parallel to each edge, embers. Spec read off the light field.
#    FLAMES SHELF 2026-10-06 REWORK (orchestrator look verdict: read as fish scales / leaves): rebuilt on irregular overlapping
#    licks (L 150-500 px, jit 0.5, curl), detail inside each tongue. Law fine 0.25, follow 0.917, PASS; M7 recorded in FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_green(h, w):
    F = _field(h, w, 3011,
               B=dict(L=(200, 500), hw=(11, 25), dx=190, dy=50, jit=0.5, wave=(0.3, 0.5), freq=(0.9, 1.6),
                      curl=(1.2, 2.1), cs=(0.55, 0.72), taper=0.9, belly=0.3, neck=0.12, flow=0.3, flow_cell=1000, N=40),
               kids=dict(n=3, t=(0.2, 0.7), L=(0.25, 0.45), w=(0.4, 0.6), ang=(0.3, 0.55), curl=(1.2, 2.0),
                         cs=0.5, taper=0.9, neck=0.1, N=14))
    s = F["s"]
    t = _tmap(F)
    e = _edge(F, by="grp", mask=5)
    lick = (F["idx"] > 0).astype(np.float32)
    # WITCHFIRE as LIGHT: a luminous mantle on every tongue, a hollow translucent body
    # that dissolves toward the tip, all bloomed and summed - crossings burn brighter
    life = (1.0 - _sm(0.30, 0.90, t)) * _sm(0.0, 0.22, t)
    mantle = np.exp(-e / (1.6 * s)) * lick
    flick = 0.55 + 0.9 * _vn(h, w, 5.0 * s, 26.0 * s, 3012)
    core = lick * life * (0.18 + 0.45 * np.exp(-((t - 0.25) / 0.15) ** 2)) * flick
    # inner filaments: two ghost lines parallel to every edge, flickering
    fil = (np.exp(-((e - 8.0 * s) / (2.0 * s)) ** 2) + 0.7 * np.exp(-((e - 17.0 * s) / (2.0 * s)) ** 2)) * lick
    light = 0.75 * mantle * (0.15 + 0.85 * life) + core + 0.35 * fil * life * flick
    light = light + 0.30 * _glow(mantle, 3.0 * s) + 0.16 * _glow(lick * life, 12.0 * s)
    wisp = _vn(h, w, 5.0 * s, 80.0 * s, 3013)
    light = light + 0.06 * wisp + 0.10 * _vn(h, w, 6.0 * s, 9.0 * s, 3015) * (1.0 - lick)
    spark = _sm(0.80, 0.9, _vn(h, w, 4.0 * s, 4.0 * s, 3014)) * np.clip(2.0 * _glow(lick, 6.0 * s), 0.0, 1.0) * (1.0 - lick)
    light = np.clip(light + 0.8 * spark, 0.0, 1.0)
    col = _heat_rgb(light, [(0.0, (0.03, 0.07, 0.05)), (0.18, (0.04, 0.24, 0.12)), (0.4, (0.10, 0.62, 0.22)),
                            (0.65, (0.45, 0.95, 0.30)), (0.85, (0.80, 1.0, 0.50)), (1.0, (0.95, 1.0, 0.80))])
    M = 50.0 + 200.0 * _sm(0.35, 0.9, light)
    R = 200.0 - 180.0 * light + 20.0 * (flick - 1.0)
    C = 16.0 + 120.0 * (1.0 - light) ** 2
    return _aa(col, s), M, R, C


paint_flame_green, spec_flame_green = _wrap("green", _look_green)


# ---------------------------------------------------------------------------
# 05 flame_purple - PURPLE FLAME: POP-ART COMIC flames. Flat violet/magenta/pink-white
#    cel tones, a 45-degree halftone screen shading each tongue toward edge and tip,
#    heavy ink outline, speed lines. Spec: halftone = matte dots on gloss, ink matte.
#    FLAMES SHELF 2026-10-06 REWORK (orchestrator look verdict: read as scales): rebuilt on irregular overlapping
#    licks (L 150-500 px, jit 0.5, curl), detail inside each tongue. Law fine 0.449, follow 0.711, PASS; M7 recorded in FLAMES_SHELF.md.
# ---------------------------------------------------------------------------
def _look_purple(h, w):
    F = _field(h, w, 3111,
               B=dict(L=(170, 460), hw=(24, 46), dx=215, dy=70, jit=0.5, wave=(0.2, 0.4), freq=(0.8, 1.4),
                      curl=(1.2, 2.0), cs=(0.55, 0.72), taper=0.85, belly=0.3, neck=0.15, flow=0.3, flow_cell=1000,
                      side="band", band_rows=2, N=48),
               nest=((0.66, 0.55), (0.36, 0.26)),
               kids=dict(n=4, t=(0.2, 0.75), L=(0.18, 0.34), w=(0.45, 0.6), ang=(0.3, 0.55), curl=(1.2, 1.9),
                         cs=0.45, taper=0.9, neck=0.14, N=16))
    s = F["s"]
    cls = _codeclass(F, {-1: 0, 0: 1, 8: 1, 9: 1, 1: 2, 2: 3})
    t = _tmap(F)
    e = _edge(F, mask=5)
    depth = np.clip(e / np.maximum(_px(F, "hw"), 1.0), 0.0, 1.0)
    # POP-ART comic flames: flat cel tones, a halftone screen shading every tongue
    # toward its edges and tip, a heavy ink outline, speed lines on the ground
    X, Y = _fl_xy(h, w)
    p = 8.0 * s
    u = (X + Y) * 0.7071
    v = (X - Y) * 0.7071
    du = np.mod(u, p) - 0.5 * p
    dv = np.mod(v, p) - 0.5 * p
    d = np.sqrt(du * du + dv * dv)
    shade = np.clip(0.95 * (1.0 - depth) ** 1.3 + 0.55 * t - 0.2, 0.0, 0.95)
    dot = 1.0 - _sm(-0.6 * s, 0.6 * s, d - 0.62 * p * shade)
    lick = cls > 0
    dot = dot * lick
    tone = _pal([(0.10, 0.05, 0.20),
                 [(0.0, (0.72, 0.32, 1.0)), (1.0, (0.55, 0.18, 0.88))],
                 [(0.0, (0.98, 0.38, 0.85)), (1.0, (0.90, 0.25, 0.80))],
                 [(0.0, (1.0, 0.88, 0.97)), (1.0, (1.0, 0.75, 0.95))]])
    tq = _tq(t)
    col = _g(tone, cls, tq)
    dark = np.array([0.24, 0.04, 0.40], np.float32)
    col = _mix(col, dark, 0.85 * dot)
    ink = (1.0 - _sm(1.6 * s, 2.8 * s, e)) * lick
    col = _mix(col, np.array([0.06, 0.02, 0.09], np.float32), ink)
    speed = _sm(0.72, 0.82, _vn(h, w, 2.5 * s, 140.0 * s, 3112)) * (1.0 - lick)
    star = _sm(0.955, 0.985, _vn(h, w, 3.0 * s, 3.0 * s, 3113)) * (1.0 - lick) * _sm(0.7, 0.8, _vn(h, w, 60.0 * s, 60.0 * s, 3114))
    col = _mix(col, np.array([0.38, 0.22, 0.62], np.float32), 0.8 * speed)
    col = _mix(col, np.array([1.0, 0.85, 1.0], np.float32), star)
    S = _pal([(60, 130, 70),
              [(0.0, (190, 30, 16)), (1.0, (170, 50, 20))],
              [(0.0, (220, 18, 16)), (1.0, (205, 30, 18))],
              (245, 12, 16)])
    sp = _g(S, cls, tq)
    sp = _mix(sp, np.array([40.0, 185.0, 120.0], np.float32), dot)
    sp = _mix(sp, np.array([0.0, 220.0, 200.0], np.float32), ink)
    sp = _mix(sp, np.array([210.0, 40.0, 30.0], np.float32), np.maximum(speed, star))
    return _aa(col, s), sp[..., 0], sp[..., 1], sp[..., 2]


paint_flame_purple, spec_flame_purple = _wrap("purple", _look_purple)


# FLAMES-FIX 2026-10-07: new ids for the rebuilt looks (old flame_* ids are the HEAD originals again).
NEW_IDS = {
    "flame2_pinstripe_licks": "hotrod",
    "flame2_blackbody": "true_fire",
    "flame2_gas_torch": "blue",
    "flame2_witchlight": "green",
    "flame2_pop_art": "purple",
    "flame2_charcoal_ghost": "ghost",
    "flame2_firestorm": "inferno",
    "flame2_spark_shower": "white_hot",
    "flame2_spectral": "rainbow",
    "flame2_coal_bed": "ember",
    "flame2_candy_film": "candy",
    "flame2_arc_discharge": "plasma",
    "flame2_crystal_blades": "cold",
    "flame2_crust_tear": "lava",
    "flame2_fire_feathers": "phoenix",
    "flame2_radioactive": "toxic",
    "flame2_neon_tube": "pink",
    "flame2_smoke_curl": "smoke",
    "flame2_barbed_blades": "tribal",
    "flame2_dragon_scroll": "dragon",
}
for _nid, _old in NEW_IDS.items():
    globals()['paint_' + _nid] = globals()['paint_flame_' + _old]
    globals()['spec_' + _nid] = globals()['spec_flame_' + _old]
