"""FRACTURED HOUDINI H1-I14 — smoked mother-of-pearl / veiled skull.

Purpose-built H1 replacement after I13 failed the live card: a complete,
brighter ornamental lacquer first.  Repeated skull relief only rearranges
the carrier's discrete M/R/Cc material cards; RGB never receives skull art.
SPB-2026-08-30 / owner: dense 8–32px native anatomy, not sparse icons.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_CACHE: OrderedDict[tuple[int, int, int], tuple[np.ndarray, np.ndarray]] = OrderedDict()
_LOCK = RLock()


def _frac(a):
    return a - np.floor(a)


def _hash(x, y, salt):
    return _frac(np.sin(x * 127.1 + y * 311.7 + salt * 19.19) * 43758.5453)


def _up(a, w, h):
    return cv2.resize(a.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)


def _arrays(shape, seed):
    h, w = map(int, shape)
    key = (h, w, int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]

    # Canonical design scale makes picker and 2048² geometry agree.
    sc = 768.0 / max(h, w)
    hh, ww = max(192, round(h * sc)), max(192, round(w * sc))
    yy, xx = np.mgrid[:hh, :ww].astype(np.float32)
    u = .923 * xx + .385 * yy
    v = -.385 * xx + .923 * yy

    # I14-I3: reject I2's wave-wallpaper.  This is a nonperiodic smoke-marble
    # surface: low-frequency pressure pools organize fine contour/lip/fleck
    # detail, but are not large graphic shapes themselves.
    rng = np.random.default_rng(int(seed) * 8191 + 331)
    def pressure(n, sigma):
        q = cv2.resize(rng.random((n, n)).astype(np.float32), (ww, hh), interpolation=cv2.INTER_CUBIC)
        return cv2.GaussianBlur(q, (0, 0), sigma)
    slow, middle, fine = pressure(17, 18.0), pressure(53, 6.0), pressure(129, 1.8)
    phi = 3.1 * slow + 1.25 * middle + .23 * fine
    tide = .5 + .5 * np.sin(phi * 9.7)
    vein = np.clip((.052 - np.abs(tide - .5)) / .052, 0, 1)
    lip = np.clip((.13 - np.abs(tide - .5)) / .085, 0, 1) - vein * .46
    hair = np.clip((.026 - np.abs(np.sin(phi * 32.0) - .38)) / .026, 0, 1)
    leaf = np.clip((middle - np.percentile(middle, 62)) / max(float(np.ptp(middle)) * .34, 1e-5), 0, 1) * (.35 + .65 * lip)
    lace = np.clip((.07 - np.abs(np.sin(phi * 18.0 + slow * 4.0) - .54)) / .07, 0, 1)
    pearl = np.clip((fine - np.percentile(fine, 87)) / max(float(np.ptp(fine)) * .13, 1e-5), 0, 1) * (.22 + .78 * leaf)
    scar = np.clip((.075 - np.abs(np.sin(phi * 5.4 + middle * 9.0) - .16)) / .075, 0, 1)

    # Paint is innocent lacquer: pearl/indigo/teal variation follows the
    # visible ornament, not the hidden skull mask.
    base = np.empty((hh, ww, 3), np.float32)
    base[..., 0] = .165 + .115 * tide
    base[..., 1] = .120 + .150 * (1.0 - tide)
    base[..., 2] = .285 + .155 * tide
    pearl_rgb = np.array((.68, .42, .82), np.float32)
    teal_rgb = np.array((.055, .48, .50), np.float32)
    violet_rgb = np.array((.47, .12, .60), np.float32)
    steel_rgb = np.array((.53, .56, .78), np.float32)
    art = base * (1.0 - vein[..., None] * .43) + pearl_rgb * (vein[..., None] * .43)
    art = art * (1.0 - leaf[..., None] * .16) + teal_rgb * (leaf[..., None] * .16)
    art = art * (1.0 - lace[..., None] * .14) + violet_rgb * (lace[..., None] * .14)
    art = art * (1.0 - pearl[..., None] * .24) + steel_rgb * (pearl[..., None] * .24)
    art = np.clip(art * (.94 + .12 * scar[..., None]), 0, 1)

    # Discrete physical material cards: matrix, wet pearl vein, velvet leaf,
    # lacquer thread, chrome pearl, broken-film scar, and double crossings.
    code = np.zeros((hh, ww), np.int32)
    code[leaf > .25] = 1
    code[vein > .34] = 2
    code[hair > .22] = 3
    code[lace > .24] = 4
    code[pearl > .24] = 5
    code[scar > .22] = 6
    code[(vein > .48) & (lace > .22)] = 7
    # I14-I5: use a narrower but still eight-state physical ladder.  The
    # relief test must not depend on neon raw-map contrast masquerading as a
    # hidden reveal; every channel retains a real >=20-point working spread.
    mtab = np.array((104, 132, 184, 118, 224, 166, 82, 238), np.float32)
    rtab = np.array((142, 91, 48, 114, 28, 67, 178, 20), np.float32)
    ctab = np.array((118, 170, 206, 138, 232, 194, 70, 238), np.float32)
    M, R, C = mtab[code], rtab[code], ctab[code]

    # Full-canvas repeated ornamental skull relief.  The complete assembly is
    # ~80px native; every individual brow/socket/jaw/teeth stroke remains
    # 8–32px.  It has no influence on `art` above.
    step = 37.0
    gx, gy = np.floor(xx / step), np.floor(yy / step)
    ox = (.18 + .61 * _hash(gx, gy, seed + 41)) * step
    oy = (.16 + .63 * _hash(gx, gy, seed + 67)) * step
    X = (xx - (gx * step + ox)) / (8.4 + .9 * _hash(gx, gy, seed + 101))
    Y = (yy - (gy * step + oy)) / (9.5 + .8 * _hash(gx, gy, seed + 131))
    brow = np.exp(-((np.abs(X) - (.22 + .33 * np.clip(-Y, 0, 1))) / .075) ** 2) * np.exp(-((Y + .25) / .14) ** 2)
    socket = np.exp(-((np.abs(np.abs(X) + .56 * np.abs(Y + .02) - .40) / .070) ** 2)) * np.exp(-((Y + .03) / .34) ** 2)
    cavity = np.maximum(np.clip(1 - np.abs((X - .28) / .18) - np.abs((Y + .015) / .14), 0, 1),
                        np.clip(1 - np.abs((X + .28) / .18) - np.abs((Y + .015) / .14), 0, 1))
    nose = np.clip(1 - np.abs(X / .11) - np.abs((Y - .13) / .14), 0, 1)
    jaw = np.exp(-((np.abs(Y - .50) - (.23 - .22 * np.abs(X))) / .065) ** 2) * np.clip(1 - np.abs(X) / .76, 0, 1)
    teeth = jaw * np.exp(-((np.sin(X * 27) * .5 + .5 - .60) / .13) ** 2)
    cheek = np.exp(-((np.abs(np.abs(X) - (.25 + .20 * (Y + .06))) / .060) ** 2)) * np.clip((Y + .04) * 2.0, 0, 1)
    relief = np.clip(brow * .72 + socket * .68 + jaw * .66 + teeth * .60 + cheek * .53 + nose * .36, 0, 1)

    # Skull relief reuses adjacent cards: chrome edges, buried cavities and
    # wet-pearl jaw.  The raw Combined map is intricate, never a few symbols.
    M = np.where(relief > .36, 238, M); R = np.where(relief > .36, 24, R); C = np.where(relief > .36, 238, C)
    M = np.where(cavity > .36, 72, M); R = np.where(cavity > .36, 188, R); C = np.where(cavity > .36, 72, C)
    M = np.where(jaw > .40, 214, M); R = np.where(jaw > .40, 34, R); C = np.where(jaw > .40, 212, C)
    M = np.where(teeth > .42, 92, M); R = np.where(teeth > .42, 18, R); C = np.where(teeth > .42, 50, C)

    if (hh, ww) != (h, w):
        art = _up(art, w, h)
        M, R, C = (_up(a, w, h) for a in (M, R, C))
    value = (art.astype(np.float32), np.stack((np.clip(M, 0, 255), np.clip(R, 10, 255), np.clip(C, 10, 255)), axis=2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        if len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_veiled_skull_i14(paint, shape, mask, seed, pm, bb):
    del bb
    art, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    source = source / 255.0 if source.max(initial=0) > 1.5 else source
    m = np.asarray(mask, np.float32); m = m[..., 0] if m.ndim == 3 else m
    m = np.clip(m, 0, 1)[..., None] * float(pm)
    return np.clip(source * (1 - m) + art * m, 0, 1).astype(np.float32)


def spec_veiled_skull_i14(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    return _arrays(shape, seed)[1]
