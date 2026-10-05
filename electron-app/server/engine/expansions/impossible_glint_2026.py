# -*- coding: utf-8 -*-
"""IMPOSSIBLE FINISHES — the Cinder Pulse and Hologram Noir families (owner 2026-09-02).

Owner on Cinder Pulse: "LOVE IT AS IS ... glistens/sparkles and fractures AND has a hidden
pattern ... the red glints and then with the black sitting next to dark purples some of
the purples fire in unique ways under the lights ... If there were OTHER colors besides
just red ... yellow and blue and pink and green mixed in to fill in the spaces around the
dark black and dark purple (or any other DARK color like DARK red DARK blue DARK gold) ...
The SPEC ITSELF is pretty close ... SHADES of pinks and purples in the spec and SHADES of
green for the off part ... the key to iRacing paints firing in unique ways is these
subtle differences."

Owner on Hologram Noir: "the perfect squares with multiple colors at times in each square
is a chefs kiss. THIS microdetail ... could be improved with more colors some more
brights some more darks ... the spec could be more detailed too."

Two generators, each finish a short recipe:

  glint_matrix  — the Cinder lesson. A sheared micro-cell lattice (cell 14-20 px) holding
      four physical sub-states; a slow selector field owns coherent regions (the hidden
      pattern) and chooses which rare cell class fires and in which colour; the paint is
      mostly DARK populations (black beside a dark colour) with multi-colour glints in
      the spaces; the spec is two populations — metal/smooth/no-coat "on" cells (pinks and
      purples in the spec image) and dielectric/rough/glossed "off" cells (greens) — every
      state its own tier and every cell nudged, so no two neighbours fire alike.
  prism_mosaic  — the Hologram lesson. Perfect squares (12-20 px), each split into an n x n
      micro-grid whose sub-cells carry their own hue, so one square holds several colours;
      bright white-hot squares and near-black squares are seeded into the field; the spec
      gives every sub-cell its own M/R/Cc from eight-plus tiers with bevel lips.
"""
from collections import OrderedDict
from threading import RLock

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

_CACHE, _LOCK = OrderedDict(), RLock()
WORK = 1024


def _grid(shape):
    h, w = int(shape[0]), int(shape[1])
    q = min(1.0, WORK / float(max(h, w)))
    hh, ww = max(32, int(round(h * q))), max(32, int(round(w * q)))
    y, x = np.mgrid[0:hh, 0:ww].astype(np.float32)
    return (h, w), (hh, ww), x * (2048.0 / ww), y * (2048.0 / hh)   # 2048 reference canvas at any render size


def _finish(paint, M, R, C, native, work):
    if native != work and cv2 is not None:
        h, w = native
        paint = cv2.resize(paint, (w, h), interpolation=cv2.INTER_LINEAR)
        M, R, C = (cv2.resize(z.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) for z in (M, R, C))
    spec = np.stack((np.clip(M, 0, 255), np.clip(R, 0, 255), np.clip(C, 0, 255)), 2).astype(np.uint8)
    return np.clip(paint, 0, 1).astype(np.float32), spec


def _h01(a, b, salt):
    v = (a.astype(np.int64) * 1103515245 + b.astype(np.int64) * 12345 + a.astype(np.int64) * b.astype(np.int64) * 7919 + int(salt) * 113) & 0x7FFFFFFF
    v = (v ^ (v >> 13)) * 1274126177 & 0x7FFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFFFF).astype(np.float32) / float(0x1000000)


def _rgb(*hexes):
    return np.array([[int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)] for h in hexes], np.float32)


def _spec_tables(seed, n_on=6, n_mid=2):
    """16 material states: 'on' = metal/smooth/no-coat (pink-purple in the spec image),
    'off' = dielectric/rough/glossed (green), a couple of mids. Seeded shades, never uniform."""
    rng = np.random.default_rng(int(seed) & 0x7FFFFFFF)
    M, R, C, kind = np.zeros(16, np.float32), np.zeros(16, np.float32), np.zeros(16, np.float32), np.zeros(16, np.int32)
    order = rng.permutation(16)
    for i, st in enumerate(order):
        if i < n_on:
            M[st], R[st], C[st], kind[st] = rng.uniform(150, 236), rng.uniform(16, 70), rng.uniform(140, 240), 1
        elif i < n_on + n_mid:
            M[st], R[st], C[st], kind[st] = rng.uniform(85, 135), rng.uniform(85, 145), rng.uniform(55, 115), 2
        else:
            M[st], R[st], C[st], kind[st] = rng.uniform(14, 72), rng.uniform(168, 236), rng.uniform(14, 62), 0
    return M, R, C, kind


# ───────────────────────────── generator 1: glint matrix ─────────────────────────────
def glint_matrix(shape, seed, tile=16.0, shear=(0.87, 0.50), sub="quad", darks=None, glints=None, heats=None,
                 sel_scale=1.0, glint_states=5, heat_mod=(13, 11, 14, 12), wobble=1.0):
    native, work, X, Y = _grid(shape)
    ca, sa = shear
    u = ca * X + sa * Y + wobble * (2.4 * np.sin(Y / 173.0) + 0.9 * np.sin(Y / 43.0))
    v = -sa * X + ca * Y + wobble * (1.8 * np.sin(X / 151.0) + 0.7 * np.sin(X / 37.0))
    ix, iy = np.floor(u / tile).astype(np.int64), np.floor(v / tile).astype(np.int64)
    fu, fv = np.mod(u, tile) / tile, np.mod(v, tile) / tile
    # the hidden pattern: a slow selector owns 160-400 px regions
    s = sel_scale
    selector = (0.50 + 0.22 * np.sin(X / (247.0 * s) + 0.7 * np.sin(Y / (129.0 * s)))
                + 0.18 * np.cos(Y / (181.0 * s) - 0.5 * np.sin(X / (97.0 * s))) + 0.10 * np.sin((X + Y) / (311.0 * s)))
    region = np.clip(np.floor(selector * 4), 0, 3).astype(np.int32)
    cell = np.floor(_h01(ix, iy, seed) * 16).astype(np.int32)
    jit = _h01(iy, ix, seed + 5) - 0.5
    if sub == "quad":
        subst = (fu >= 0.5).astype(np.int32) + 2 * (fv >= 0.5).astype(np.int32)
    elif sub == "strips":
        subst = np.clip(np.floor(fu * 4), 0, 3).astype(np.int32)
    else:  # "diamond": two diagonal halves x inner/outer
        subst = (fu + fv >= 1.0).astype(np.int32) + 2 * (np.abs(fu - 0.5) + np.abs(fv - 0.5) < 0.32).astype(np.int32)
    state = np.mod(cell + subst * 3 + region * 2, 16)
    edge = np.clip((0.12 - np.minimum.reduce((fu, 1 - fu, fv, 1 - fv))) / 0.12, 0, 1)
    diag = np.clip((0.18 - np.abs(fu - fv)) / 0.18, 0, 1)
    # paint: 16 states, mostly darks, a few glint colours filling the spaces between them
    Ms, Rs, Cs, kind = _spec_tables(seed + 91, n_on=glint_states)
    pal = np.zeros((16, 3), np.float32)
    on_idx = np.where(kind == 1)[0]
    for k in range(16):
        pal[k] = darks[k % len(darks)]
    for i, k in enumerate(on_idx):
        pal[k] = glints[i % len(glints)]
    color = pal[state]
    heat = np.zeros(X.shape, bool)
    heat_col = np.zeros(X.shape + (3,), np.float32)
    for r in range(4):
        hr = (region == r) & (np.mod(cell, heat_mod[r]) == r)
        heat |= hr
        heat_col[hr] = heats[r % len(heats)]
    color = np.where(heat[..., None], color * 0.30 + heat_col * 0.70, color)
    ash = darks[-1] * 2.2 + 0.05
    paint = np.clip(color * (1 - 0.27 * edge[..., None]) + ash[None, None, :] * (0.12 * diag[..., None])
                    + heat_col * (0.12 * (heat * diag)[..., None]), 0, 1)
    # spec: two populations with shades; bevel/diagonal/heat attached to the same facets; per-cell nudge
    M = Ms[state] + 36 * edge + 23 * diag + 42 * heat + 18 * jit
    R = Rs[state] - 28 * edge - 31 * diag - 37 * heat + 16 * jit
    C = Cs[state] + 45 * edge + 52 * diag + 61 * heat + 20 * jit
    return _finish(paint, M, R, C, native, work)


# ───────────────────────────── generator 2: prism mosaic ─────────────────────────────
def prism_mosaic(shape, seed, cell=16.0, n=3, body=(0.11, 0.12, 0.13), body_var=0.25, hue0=0.0, hue_span=1.0,
                 sat=0.85, bright_frac=0.06, dark_frac=0.10, chroma=0.42, gloss_bias=0.0):
    native, work, X, Y = _grid(shape)
    ix, iy = np.floor(X / cell).astype(np.int64), np.floor(Y / cell).astype(np.int64)
    fx, fy = np.mod(X, cell) / cell, np.mod(Y, cell) / cell
    sx, sy = np.clip(np.floor(fx * n), 0, n - 1).astype(np.int64), np.clip(np.floor(fy * n), 0, n - 1).astype(np.int64)
    sub = sx + n * sy
    c1 = _h01(ix, iy, seed + 1)                # the square's own scalar
    c2 = _h01(iy, ix, seed + 7)
    s1 = _h01(ix * n + sx, iy * n + sy, seed + 3)   # the sub-cell's own scalars
    s2 = _h01(iy * n + sy, ix * n + sx, seed + 11)
    s3 = _h01(ix * n + sx + 5, iy * n + sy + 9, seed + 17)
    flow = 0.5 + 0.5 * np.sin((X + 0.73 * Y) * 0.014 + 1.8 * np.sin(Y * 0.005))
    edge = np.maximum(np.abs(fx - 0.5), np.abs(fy - 0.5)) * 2.0
    bevel = np.clip((edge - 0.60) / 0.40, 0, 1)                       # square lip
    sub_edge = np.maximum(np.abs(np.mod(fx * n, 1.0) - 0.5), np.abs(np.mod(fy * n, 1.0) - 0.5)) * 2.0
    lip = np.clip((sub_edge - 0.78) / 0.22, 0, 1)                     # micro-grid lips
    hue = np.mod(hue0 + hue_span * (c1 + 0.30 * s1 + 0.06 * flow + 0.05 * c2), 1.0)
    r = 0.5 + 0.5 * np.sin(6.283185 * hue)
    g = 0.5 + 0.5 * np.sin(6.283185 * (hue + 0.333333))
    b = 0.5 + 0.5 * np.sin(6.283185 * (hue + 0.666667))
    tint = np.stack((r, g, b), 2) * sat + (1 - sat) * 0.5
    bright = c2 > 1.0 - bright_frac
    dark = (c2 < dark_frac) & ~bright
    lit = np.clip((c1 - 0.42) * 1.8, 0, 1) * (0.30 + 0.70 * s1)         # which squares carry colour, how strongly per sub-cell
    base = np.array(body, np.float32)[None, None, :] * (1 - body_var + 2 * body_var * c2[..., None])
    paint = base * (0.72 + 0.28 * flow[..., None]) + tint * (chroma * lit[..., None] + 0.08)
    paint += (bevel * 0.05 + lip * 0.035)[..., None]
    paint = np.where(bright[..., None], 0.30 + 0.70 * tint * (0.55 + 0.45 * s1[..., None]), paint)   # vivid colour squares, not white
    paint = np.where(dark[..., None], base * 0.18 + tint * 0.04, paint)
    # spec: sub-cell-owned tiers (each square holds several materials), lips and bevels attached
    t1, t2, t3 = (np.floor(z * 8) / 7.0 for z in (s1, s2, s3))           # three independent eight-tier scalars per sub-cell
    M = 18 + 220 * np.clip(0.22 + 0.62 * t1 + 0.25 * lit - 0.20 * bevel, 0, 1)
    R = 16 + 220 * np.clip(0.66 - 0.55 * t2 - 0.25 * lit + 0.22 * bevel + 0.10 * lip, 0, 1)
    C = 16 + 230 * np.clip(0.05 + 0.70 * t3 * (0.5 + 0.5 * c2) + 0.12 * flow - 0.22 * lit + 0.15 * bevel + gloss_bias, 0, 1)
    M = np.where(bright, 250.0, np.where(dark, 12.0 + 30 * s1, M))
    R = np.where(bright, 6.0 + 12 * s1, np.where(dark, 200.0 + 30 * s1, R))
    C = np.where(bright, 16.0, np.where(dark, 60.0 + 120 * s1, C))
    return _finish(paint, M, R, C, native, work)


# ───────────────────────────── the recipes ─────────────────────────────
D = _rgb
FINISHES = {
    # ── Cinder family: dark populations + multi-colour glints, hidden regions, two-population spec
    "impossible_cinder_aurora": (glint_matrix, dict(
        tile=18.0, shear=(0.91, 0.41), sub="quad", sel_scale=1.15,
        darks=D("#07070B", "#1C0A2E", "#0C0C14", "#241040"),
        glints=D("#E6B72E", "#123A8C", "#E23A93", "#0F5A2A", "#7A1F12"),
        heats=D("#FFE066", "#FF4FB8", "#4DA3FF", "#5CFF8A"))),
    "impossible_cinder_oxblood": (glint_matrix, dict(
        tile=14.0, shear=(0.80, 0.60), sub="quad", sel_scale=0.85, wobble=0.7, heat_mod=(11, 13, 12, 14),
        darks=D("#080506", "#3A0810", "#120709", "#2C1A05"),
        glints=D("#E0AE2A", "#0E6C78", "#E12FC0", "#3E6A12", "#6B1020"),
        heats=D("#FFB020", "#30F0FF", "#FF4FD8", "#FFF5D6"))),
    "impossible_cinder_abyss": (glint_matrix, dict(
        tile=20.0, shear=(0.71, 0.71), sub="quad", sel_scale=1.4, wobble=1.6, heat_mod=(12, 14, 11, 13),
        darks=D("#05070C", "#071A3A", "#0A2A2E", "#0B0F1E"),
        glints=D("#E39A3A", "#8A1F5A", "#2E5A12", "#C92E2E", "#1C4E86"),
        heats=D("#FFC061", "#FF6FB5", "#B8FF5C", "#7FD8FF"))),
    # ── Hologram family: perfect squares, several colours per square, brights and darks, sub-cell spec
    "impossible_hologram_ember": (prism_mosaic, dict(
        cell=16.0, n=3, body=(0.16, 0.10, 0.07), body_var=0.30, hue0=0.02, hue_span=0.55, sat=0.9,
        bright_frac=0.05, dark_frac=0.08, chroma=0.80)),
    "impossible_hologram_ice": (prism_mosaic, dict(
        cell=12.0, n=2, body=(0.40, 0.44, 0.50), body_var=0.22, hue0=0.48, hue_span=0.40, sat=0.8,
        bright_frac=0.05, dark_frac=0.07, chroma=0.70, gloss_bias=-0.08)),
    "impossible_hologram_verdigris": (prism_mosaic, dict(
        cell=20.0, n=4, body=(0.05, 0.11, 0.09), body_var=0.35, hue0=0.10, hue_span=0.75, sat=0.95,
        bright_frac=0.045, dark_frac=0.10, chroma=0.85)),
}


def _arrays(fid, shape, seed):
    key = (fid, int(shape[0]), int(shape[1]), int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]
    fn, kw = FINISHES[fid]
    value = fn(shape, seed, **kw)
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 3:
            _CACHE.popitem(last=False)
    return value


def _mk(fid):
    def paint_fn(paint, shape, mask, seed, pm, bb, _fid=fid):
        del bb
        authored, _ = _arrays(_fid, shape, seed)
        src = np.asarray(paint, np.float32)[..., :3]
        if src.max(initial=0) > 1.5:
            src = src / 255.0
        m = np.asarray(mask, np.float32)
        m = m[..., 0] if m.ndim == 3 else m
        mix = (np.clip(m, 0, 1) * float(pm))[..., None]
        return np.clip(src * (1 - mix) + authored * mix, 0, 1).astype(np.float32)

    def spec_fn(shape, mask, seed, sm, _fid=fid):
        del sm
        _, spec = _arrays(_fid, shape, seed)
        m = np.asarray(mask, np.float32)
        m = m[..., 0] if m.ndim == 3 else m
        out = np.empty(spec.shape[:2] + (4,), np.uint8)
        out[..., :3] = (spec.astype(np.float32) * np.clip(m, 0, 1)[..., None]).astype(np.uint8)
        out[..., 3] = (np.clip(m, 0, 1) * 255).astype(np.uint8)
        return out
    return spec_fn, paint_fn


BUILDERS = {fid: (lambda shape, seed, _f=fid: _arrays(_f, shape, seed)) for fid in FINISHES}


def install_into_engine(mono_reg, base_reg=None, fusion_reg=None):
    for fid in FINISHES:
        mono_reg[fid] = _mk(fid)
    return "%d impossible glint/mosaic installed" % len(FINISHES)
