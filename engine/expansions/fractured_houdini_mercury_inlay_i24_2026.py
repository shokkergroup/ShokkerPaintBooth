"""Private Houdini I24 — Mercury Inlay, P1.

An authored enamel-and-metal inlay process, not a printed motif.  The 8–32px
spines, paired leaf cuts, bezels and micro-cuts share one softly warped layout.
Paint and M/Rough/Cc are calculated from those same physical parcels.  This is
isolated evidence only: it must pass at least five native owner-eye iterations
before any catalog wiring is considered.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()
_TAU = np.float32(6.283185307179586)


def _hash(i: np.ndarray, j: np.ndarray, salt: float) -> np.ndarray:
    return np.mod(np.sin(i * 127.1 + j * 311.7 + salt * 71.3) * 43758.5453, 1.0).astype(np.float32)


def _ell(x: np.ndarray, y: np.ndarray, sx: float, sy: float) -> np.ndarray:
    return np.exp(-((x / sx) ** 2 + (y / sy) ** 2)).astype(np.float32)


def _arrays(shape: tuple[int, int], seed: int) -> tuple[np.ndarray, np.ndarray]:
    key = (*map(int, shape), int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]
    h, w = map(int, shape)
    scale = min(1.0, 1024.0 / max(h, w))
    hh, ww = max(256, round(h * scale)), max(256, round(w * scale))
    yy, xx = np.mgrid[:hh, :ww].astype(np.float32)
    X, Y = xx / scale, yy / scale

    # One authored registration drift governs every cut.  The result is a
    # family of small hand-set inlays, not a CAD grid or a random mark field.
    phase = (seed % 7919) * .00073
    dx = 3.1*np.sin(Y*.013 + phase) + 2.2*np.sin((X+Y)*.008 - phase)
    dy = 2.8*np.sin(X*.015 - phase*.7) - 1.6*np.sin((X-Y)*.010 + phase)
    U, V = (X + dx) / 29.0, (Y + dy) / 27.0
    # P2 — P1's equal ovals visibly advertised a childish rosette grid.
    # Replace the grid with an uneven hand-set inlay field: nearest and next
    # nearest deterministic stones create each bezel and every micro-cut.
    i0, j0 = np.floor(U), np.floor(V)
    best = np.full_like(U, 1e9); second = np.full_like(U, 1e9)
    ci, cj = i0.copy(), j0.copy(); qx = np.zeros_like(U); qy = np.zeros_like(V)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ii, jj = i0 + di, j0 + dj
            cx = ii + .5 + (_hash(ii, jj, seed + 31) - .5) * .46
            cy = jj + .5 + (_hash(ii, jj, seed + 47) - .5) * .42
            tx, ty = (U-cx)*29.0, (V-cy)*27.0
            dd = np.hypot(tx, ty)
            take = dd < best
            second = np.where(take, best, np.minimum(second, dd))
            best = np.where(take, dd, best)
            ci, cj = np.where(take, ii, ci), np.where(take, jj, cj)
            qx, qy = np.where(take, tx, qx), np.where(take, ty, qy)
    orient = (_hash(ci, cj, seed + 3) - .5) * 1.25
    ca, sa = np.cos(orient), np.sin(orient)
    qx, qy = qx*ca + qy*sa, -qx*sa + qy*ca
    temperament = _hash(ci, cj, seed + 17)

    # P1 anatomy: a narrow stem, two opposite hand-cut leaves, a recessed
    # central eye and a thin bezel.  Individual tools are 2–20px wide; broad
    # visual density comes from the linked anatomy, never a macro icon.
    # An irregular cloisonné stone is bounded by its neighbours, then cut by
    # three 2–8px engraving passes.  It is jewelry work rather than a stamped
    # icon: edge, face, directional cuts, rim-chip and a rare tiny setting.
    edge = np.exp(-((second-best) / 1.20) ** 2).astype(np.float32)
    face = np.clip(1.0 - (best / (12.4 + temperament*2.8)) ** 2, 0, 1) ** .72
    cut_a = np.exp(-((np.sin((qx*.92+qy*.38)/6.7 + temperament*3.0) / .16) ** 2)) * face
    cut_b = np.exp(-((np.sin((qx*.41-qy*1.08)/8.9 + temperament*5.0) / .13) ** 2)) * face
    stem = cut_a * (.30 + .70*face)
    paired = cut_b * (.25 + .75*face)
    bezel = edge
    bead = _ell(qx-(temperament-.5)*5.0, qy+(_hash(ci,cj,seed+97)-.5)*5.0, 1.25, 1.25) * (temperament > .70)
    tips = np.maximum(_ell(qx, qy, 3.2, 1.15), _ell(qx, qy, 1.15, 3.2)) * face
    vein = face * (.5+.5*np.sin((qx-qy)*1.58 + temperament*7.0))
    micro = ((np.sin(qx*1.71-qy*.67+temperament*11.0) > .72).astype(np.float32) * face * .36)
    relief = np.clip(.54*face + .78*bezel + .38*stem + .36*paired + .26*tips + .44*bead + .17*vein + .24*micro, 0, 1)
    recess = np.clip((1.0-relief)*(.16+.12*temperament), 0, 1)

    # Ordinary finish: blue-black enamel around hand-cut silver-garnet inlay.
    # Color remains deliberately restrained; discovery belongs to material,
    # not to a decal-like high-contrast paint silhouette.
    slow = .5 + .5*np.sin(X*.011 - Y*.009 + phase)
    # P4 — P3's face lift made the carrier read as bokeh pebbles.  Do not
    # brighten every stone: ordinary paint is blue-black enamel, interrupted
    # only by the literal inlay seams and their engraved cuts.
    enamel = np.dstack((.075+.028*slow, .048+.018*slow, .027+.011*slow))
    cut = np.dstack((.205+.065*slow, .125+.039*slow, .061+.022*slow))
    paint = enamel*(1-(bezel*.43)[...,None]) + cut*(bezel*.43)[...,None]
    paint = paint*(1-((stem*.42+paired*.38+micro*.24)[...,None])) + cut*((stem*.42+paired*.38+micro*.24)[...,None])
    garnet = np.array((.20, .040, .18), np.float32)
    paint = paint*(1-(bead*.11)[...,None]) + garnet*(bead*.11)[...,None]
    paint += np.dstack((.006*micro, .010*micro, .017*micro))

    # M/R/Cc follows exact cut anatomy.  Neighbouring stem/leaf/bezel/eye
    # parcels deliberately use different documented material families, so the
    # inlay assembles and disassembles with light without a paint-only symbol.
    M = 58 + 27*slow + 21*recess
    R = 190 - 22*slow + 17*recess
    C = 174 - 19*slow + 22*recess
    M = M + 155*stem + 188*bezel + 83*paired + 62*bead + 41*micro
    R = R - 102*stem - 142*bezel - 61*paired - 35*bead - 43*micro
    C = C - 118*stem - 151*bezel - 73*paired - 53*bead - 64*micro
    # Controlled neighbouring parcels: dark chrome, satin, candy, pearl,
    # frozen and Fractured states occur only inside the physical inlay.
    # P5 — retain P4's quiet face and test eight named material neighbours
    # *along the physical seams only*. This is the Hologram lesson without a
    # second grid: state changes turn only where a hand-set inlay turns.
    code = np.mod((ci.astype(np.int32)*3 + cj.astype(np.int32)*5 + np.floor((qx-qy)/7).astype(np.int32)), 8)
    parcel = np.clip(.74*paired + .75*bezel + .62*stem + .36*bead + .43*micro, 0, 1) > .34
    mtab = np.array((250,250,200,100,225,80,8,252), np.float32)
    rtab = np.array((15,45,15,40,140,120,210,38), np.float32)
    ctab = np.array((40,40,16,16,100,140,166,255), np.float32)
    M = np.where(parcel, .22*M + .78*mtab[code], M)
    R = np.where(parcel, .22*R + .78*rtab[code], R)
    C = np.where(parcel, .22*C + .78*ctab[code], C)
    spec = np.dstack((np.clip(M, 0, 255), np.clip(R, 15, 255), np.clip(C, 16, 255))).astype(np.uint8)
    if (hh, ww) != (h, w):
        paint = cv2.resize(paint.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
        spec = cv2.resize(spec, (w, h), interpolation=cv2.INTER_CUBIC)
    result = np.clip(paint, 0, 1).astype(np.float32), spec
    with _LOCK:
        _CACHE[key] = result
        if len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return result


def paint_mercury_inlay_i24(paint, shape, mask, seed, pattern_mix, bbox):
    del bbox
    art, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5:
        source /= 255.0
    alpha = np.asarray(mask, np.float32)
    if alpha.ndim == 3:
        alpha = alpha[..., 0]
    alpha = (np.clip(alpha, 0, 1) * np.clip(float(pattern_mix), 0, 1))[..., None]
    return np.clip(source*(1-alpha) + art*alpha, 0, 1).astype(np.float32)


def spec_mercury_inlay_i24(shape, seed, spec_mix, base_metal, base_rough):
    del spec_mix, base_metal, base_rough
    return _arrays(shape, seed)[1]
