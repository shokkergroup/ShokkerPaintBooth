"""Soda Fountain Glass I1 — candidate 1950s counter-glass material.

SPB-105 / owner finish doctrine / 2026-08-30.  The legacy Soda Check card is
just a uniform purple grid.  This candidate uses a continuous aqua soda-glass
surface worked from fine 4–28px effervescence cells, 2–6px glass lips, 8–24px
frosted inclusions and occasional cherry-syrup pockets.  The large-scale
colour drift only chooses which glass mixture each connected fine cell uses;
it is not a checker, a stripe, confetti, or an unrelated spec noise layer.
"""
from collections import OrderedDict
from threading import RLock

import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        found = _CACHE.get(key)
        if found is not None:
            _CACHE.move_to_end(key)
            return found

    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    phase = (int(seed) & 0xFFFF) * .00113
    # Gentle refraction only disturbs the 8–28px bubbles; it does not make
    # macro waves or a repeated tile.
    u = x + 5.1 * np.sin(y / 103.0 + phase) + 2.8 * np.sin((x + y) / 47.0)
    v = y + 4.4 * np.sin(x / 127.0 - phase * .7) - 2.5 * np.sin((x - y) / 59.0)
    f0 = np.sin(u * .177 + .51 * np.sin(v * .079))
    f1 = np.sin(v * .151 - .43 * np.sin(u * .113))
    f2 = np.sin((u + v) * .096 + .33 * np.sin((u - v) * .067))
    froth = np.clip(.5 + .29 * f0 + .24 * f1 + .18 * f2, 0, 1)
    # Cell centers and their annular glass lips are both fine physical events.
    core = np.clip((froth - .62) / .27, 0, 1)
    lip = np.exp(-np.square((froth - .58) / .052))
    hollow = np.clip((.43 - froth) / .34, 0, 1)
    split = np.exp(-np.square((f0 - f1) / .20)) * core
    fizz = .5 + .5 * np.sin(u * .322 + .61 * np.sin(v * .207))
    # Regional liquid composition moves coherently through the glass without
    # turning fine fizz into random multicolor particles.
    bath = (.46 * np.sin(x / 241.0 + .25 * np.sin(y / 87.0) + phase)
            + .34 * np.sin(y / 193.0 - .19 * np.sin(x / 109.0))
            + .20 * np.sin((x + y) / 337.0 - phase))
    cherry = np.clip((bath - .56) / .25, 0, 1) * core
    cream = np.clip((-.32 - bath) / .38, 0, 1) * (core * .78 + lip * .42)
    aqua = np.clip(1.0 - cherry * .72 - cream * .45, 0, 1)

    glass = np.array((.018, .105, .130), np.float32)
    cyan = np.array((.025, .52, .58), np.float32)
    mint = np.array((.18, .72, .61), np.float32)
    soda_cream = np.array((.90, .67, .45), np.float32)
    syrup = np.array((.78, .035, .18), np.float32)
    chrome = np.array((.58, .77, .76), np.float32)
    paint = np.broadcast_to(glass, (h, w, 3)).astype(np.float32).copy()
    paint += cyan * ((.17 + .39 * froth) * aqua)[..., None]
    paint += mint * (hollow * (.13 + .18 * (1.0 - fizz)))[..., None]
    paint += soda_cream * (cream * (.17 + .28 * fizz))[..., None]
    paint += syrup * (cherry * (.20 + .32 * (1.0 - fizz)))[..., None]
    paint += chrome * (lip * (.07 + .21 * fizz))[..., None]
    paint += np.repeat((split * (.025 + .075 * fizz))[..., None], 3, axis=2)

    # Distinct, pattern-bound material states: syrup darkens to a candy coat;
    # cream centers pearl; soda glass carries clearcoat; lip/refraction turns
    # chrome; hollows are frosted/matte.
    M = 19 + 115 * core + 85 * lip + 42 * split + 39 * cherry + 21 * fizz - 37 * hollow
    R = 222 - 88 * core - 113 * lip - 44 * split - 32 * cherry + 39 * hollow + 18 * cream
    C = 21 + 122 * core + 99 * lip + 68 * split + 54 * cream + 31 * cherry - 26 * hollow
    result = (np.clip(paint, 0, 1).astype(np.float32),
              np.stack((np.clip(M, 0, 255), np.clip(R, 15, 255),
                        np.clip(C, 16, 255)), axis=2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = result
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return result


def paint_soda_fountain_glass(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5:
        source = source / 255.0
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    return np.clip(source * (1 - (coverage * float(pm))[..., None])
                   + authored * (coverage * float(pm))[..., None], 0, 1).astype(np.float32)


def spec_soda_fountain_glass(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    _, spec = _arrays(shape, seed)
    return spec[..., 0], spec[..., 1], spec[..., 2]
