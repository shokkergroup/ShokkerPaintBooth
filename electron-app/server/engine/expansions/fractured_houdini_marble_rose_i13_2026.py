"""Private H10 I13 — irregular black-cherry rose marquetry, not a tiled decal.

SPB-H10 / owner verdict 2026-08-31: I12's coherent repeated rows proved that
material-only petals can reveal, but the coordinate-frame read as wallpaper.
I13 uses an irregular, multi-species inlay field.  Every visible relief is an
8–32px native assembly (petal, leaf, pearl, crescent) and is present only in
metallic/roughness/clearcoat.  The RGB carrier is a sober, premium black-cherry
lacquer with unrelated fine pearl depth; there is no RGB symbol or decal art.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np

_C, _L = OrderedDict(), RLock()
TAU = np.float32(6.283185307179586)

def _h(a, b, salt):
    return np.mod(np.sin(a * 12.9898 + b * 78.233 + salt * 37.719) * 43758.5453, 1.).astype(np.float32)

def _arr(shape, seed):
    key = (*map(int, shape), int(seed))
    with _L:
        if key in _C:
            _C.move_to_end(key)
            return _C[key]
    h, w = map(int, shape)
    scale = 768 / max(h, w)
    hh, ww = max(192, round(h * scale)), max(192, round(w * scale))
    yy, xx = np.mgrid[:hh, :ww].astype(np.float32)
    # Work in native pixels despite the inexpensive staging lattice: components
    # below are deliberately 8–32px in the final 2048-square carrier.
    x, y = xx / scale, yy / scale
    q = seed * .173
    u = x + 5.0 * np.sin(y * .013 + q) + 2.7 * np.sin(x * .021 - y * .009)
    v = y + 4.1 * np.sin(x * .015 - q) + 2.4 * np.sin(y * .019 + x * .007)

    # Neutral black-cherry lacquer.  These fine, unrelated pearl crossings make
    # a complete material at card scale without outlining or describing a rose.
    pearl_a = .5 + .5 * np.sin(u * .073 + np.sin(v * .021))
    pearl_b = .5 + .5 * np.sin(v * .061 - np.sin(u * .025))
    depth = .19 + .055 * pearl_a + .035 * pearl_b
    art = np.empty((hh, ww, 3), np.float32)
    art[..., 0] = .128 + .118 * depth
    art[..., 1] = .007 + .016 * depth
    art[..., 2] = .052 + .071 * depth
    art = np.clip(art, 0, 1)

    # An irregular point field: cells merely bound the search; their centres are
    # strongly jittered and globally warped, so it cannot form rows or tile seams.
    cell = 53.0
    gx, gy = np.floor(u / cell), np.floor(v / cell)
    near_d = np.full((hh, ww), 9e5, np.float32)
    near_a = np.zeros((hh, ww), np.float32)
    near_s = np.zeros((hh, ww), np.float32)
    near_k = np.zeros((hh, ww), np.float32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            ci, cj = gx + ox, gy + oy
            # Two independent offsets plus a broad warp deliberately destroy
            # lattice cadence; species, angle and scale change by locale.
            jx = (.14 + .72 * _h(ci, cj, seed + 3)) * cell
            jy = (.12 + .75 * _h(ci, cj, seed + 11)) * cell
            cx = ci * cell + jx + 8.0 * np.sin(cj * 1.71 + ci * .53)
            cy = cj * cell + jy + 7.0 * np.sin(ci * 1.37 - cj * .61)
            dx, dy = u - cx, v - cy
            dd = dx * dx + dy * dy
            take = dd < near_d
            near_d = np.where(take, dd, near_d)
            near_a = np.where(take, np.arctan2(dy, dx) - TAU * _h(ci, cj, seed + 17), near_a)
            near_s = np.where(take, .82 + .38 * _h(ci, cj, seed + 23), near_s)
            near_k = np.where(take, np.floor(_h(ci, cj, seed + 29) * 4), near_k)
    rr = np.sqrt(near_d) / near_s
    # P3: P2's isolated flowers read as decorative dots.  Each active location
    # now owns a complete miniature rose-and-vine assembly: petals, pearl,
    # two folded leaves and a curving stem.  This is ornamental anatomy rather
    # than a scatter of icons, yet all constituent features remain 8–32px.
    a = near_a
    six = np.exp(-((rr - (10.3 + 1.45 * np.cos(6 * a))) / 2.25) ** 2)
    four = np.exp(-((rr - (9.2 + 1.25 * np.cos(4 * a + .55))) / 2.05) ** 2)
    leaf = np.exp(-(((rr - 9.1) / 2.3) ** 2 + (np.sin(2 * a) / .48) ** 2))
    pearl = np.exp(-((rr - 5.2) / 1.55) ** 2)
    cres = np.exp(-((rr - 12.8) / 1.4) ** 2) * np.clip(.75 + .72 * np.cos(3 * a - .4), 0, 1)
    lx, ly = rr * np.cos(a), rr * np.sin(a)
    bud = np.exp(-(((lx-.9) / 4.4) ** 2 + ((ly-4.6) / 3.6) ** 2))
    # P4: turn P3's separated flower marks into a complete Art Nouveau sprig:
    # one primary rose, two differently scaled buds, a 30px curving stem and
    # alternating leaves.  The local orientation is per-sprig, so there is no
    # shared stem direction or copy-pasted tile.
    stem = np.exp(-((lx - .9*np.sin((ly-18.)*.21)) / 1.75) ** 2) * np.exp(-((ly-20.) / 17.2) ** 8)
    leaf_a = np.exp(-(((lx-7.3) / 5.7) ** 2 + ((ly-15.3) / 2.8) ** 2)) * np.clip(.8 + .45*np.cos(a), 0, 1)
    leaf_b = np.exp(-(((lx+7.0) / 5.4) ** 2 + ((ly-23.5) / 2.7) ** 2)) * np.clip(.8 - .45*np.cos(a), 0, 1)
    lx2, ly2 = lx-4.8, ly-28.5
    r2, a2 = np.sqrt(lx2*lx2+ly2*ly2), np.arctan2(ly2,lx2)
    bud2 = np.exp(-((r2-(5.8+.75*np.cos(5*a2+.4)))/1.7)**2) + .26*np.exp(-(r2/2.3)**2)
    lx3, ly3 = lx+6.7, ly-36.0
    r3, a3 = np.sqrt(lx3*lx3+ly3*ly3), np.arctan2(ly3,lx3)
    bud3 = np.exp(-((r3-(4.5+.55*np.cos(4*a3-.6)))/1.42)**2) + .22*np.exp(-(r3/1.9)**2)
    branch = np.exp(-((lx + .19*(ly-28.)) / 1.35) ** 2) * np.exp(-((ly-30.) / 9.5) ** 8)
    cluster = np.clip(.54*six + .29*pearl + .15*cres + .40*stem + .34*leaf_a + .31*leaf_b + .42*bud2 + .30*bud3 + .27*branch, 0, 1)
    rose = np.clip(cluster * (near_k == 0).astype(np.float32), 0, 1)

    # P5 / Spec Guide v1: never clone channels under a hidden outline.  Each
    # botanical part receives its own complete physical card: quiet pearl rest,
    # satin leaf, dark-chrome polished petal lip, coat-broken recess, and a
    # small suppressed-coat Fractured bud.  Adjacent cards peak/recede at
    # different angles; the geometry is still absent from the RGB paint.
    hot = np.clip(.58*six + .22*cres + .18*stem + .17*branch, 0, 1)
    satin = np.clip(.75*leaf_a + .71*leaf_b + .30*bud2, 0, 1)
    recess = np.clip(.68*pearl + .22*bud + .14*bud3, 0, 1)
    fractured = np.clip(.48*bud2 + .34*bud3, 0, 1) * (near_k == 0).astype(np.float32)
    M = 78 + 62*satin + 169*hot - 62*recess + 125*fractured
    R = 72 + 39*satin - 55*hot + 112*recess - 39*fractured
    C = 31 + 42*satin + 18*hot + 165*recess + 217*fractured
    if (hh, ww) != (h, w):
        up = lambda z: cv2.resize(z.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        art, M, R, C = up(art), up(M), up(R), up(C)
    out = (art.astype(np.float32), np.dstack((np.clip(M, 0, 255), np.clip(R, 12, 255), np.clip(C, 12, 255))).astype(np.uint8))
    with _L:
        _C[key] = out
        if len(_C) > 2:
            _C.popitem(last=False)
    return out

def paint_marble_rose_i13(paint, shape, mask, seed, pm, bb):
    del bb
    art, _ = _arr(shape, seed)
    src = np.asarray(paint, np.float32)[..., :3]
    src = src / 255 if src.max(initial=0) > 1.5 else src
    m = np.asarray(mask, np.float32)
    m = m[..., 0] if m.ndim == 3 else m
    m = (np.clip(m, 0, 1) * np.clip(float(pm), 0, 1))[..., None]
    return np.clip(src * (1 - m) + art * m, 0, 1).astype(np.float32)

def spec_marble_rose_i13(shape, seed, sm, bm, br):
    del sm, bm, br
    return _arr(shape, seed)[1]
