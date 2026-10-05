"""Lava Lamp Filament I1 — native 1960s/70s liquid-glass lacquer candidate.

SPB-105 / owner finish doctrine / 2026-08-29.  This is intentionally staged:
the prior authored-source search was rejected because its attractive liquid
forms scaled to 40–100px.  Here the visible hierarchy is generated natively
from connected 8–28px pools, membrane folds, pearl lips and narrow seams.
I1's periodic flow read as a capsule lattice at native scale; I2 adds only
small deterministic fluid warps, preserving the fine material scale.
M/R/Cc follows those same glass and wax events; it is never a recoloured map.
"""
from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    y, x = np.mgrid[:h, :w].astype(np.float32)
    phase = float(seed) * .037
    # Small deterministic 8–28px flow warps break I1's periodic capsule rows
    # without adding random flecks, grain, a tile, or macro geometry.
    rng = np.random.default_rng(int(seed) * 13007 + 29)
    gh, gw = max(3, h // 12 + 3), max(3, w // 12 + 3)
    n1 = cv2.resize(rng.standard_normal((gh, gw)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    n2 = cv2.resize(rng.standard_normal((gh, gw)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    n1 = cv2.GaussianBlur(n1, (0, 0), 2.2); n2 = cv2.GaussianBlur(n2, (0, 0), 2.2)
    n1 /= max(float(np.max(np.abs(n1))), 1e-6); n2 /= max(float(np.max(np.abs(n2))), 1e-6)
    # Two small, differently warped flows give liquid connection without a
    # regular tile, circle, macro blob, or a broad stripe carrier.
    u = (x + 5.8 * np.sin(y * .040 + phase) + 3.2 * np.sin((x + y) * .022 - phase) + 8.5 * n1)
    v = (y + 5.2 * np.sin(x * .046 - phase) - 3.6 * np.sin((x - y) * .019 + phase) + 8.0 * n2)
    wave_a = np.sin(u * .145 + .68 * np.sin(v * .081))
    wave_b = np.sin(v * .119 - .51 * np.sin(u * .094))
    weave = np.sin((u + .58 * v) * .076 + .42 * wave_a)
    fluid = np.clip(.50 + .29 * wave_a + .22 * wave_b + .16 * weave, 0.0, 1.0)
    # Threshold bands produce connected wax boundaries and 8–28px local pools.
    membrane = np.exp(-np.square((fluid - .50) / .075))
    lip = np.exp(-np.square((fluid - .69) / .060))
    pool = np.clip((fluid - .58) / .42, 0.0, 1.0)
    void = np.clip((.43 - fluid) / .43, 0.0, 1.0)
    micro = .5 + .5 * np.sin(u * .335 + .71 * np.sin(v * .214))
    # Dark plum glass, violet wax depth, raspberry wet edges and sparse copper
    # pearl inclusions.  Every accent has a material parent above.
    glass = np.array((.050, .018, .090), np.float32)
    violet = np.array((.26, .055, .37), np.float32)
    raspberry = np.array((.67, .025, .26), np.float32)
    copper = np.array((.77, .22, .055), np.float32)
    indigo = np.array((.045, .075, .22), np.float32)
    paint = np.broadcast_to(glass, (h, w, 3)).astype(np.float32).copy()
    paint += violet * (pool[..., None] * (.34 + .32 * micro[..., None]))
    paint += indigo * (void[..., None] * (.18 + .12 * (1.0 - micro[..., None])))
    paint += raspberry * (membrane[..., None] * (.20 + .35 * micro[..., None]))
    paint += copper * (lip[..., None] * (.10 + .21 * micro[..., None]))
    paint += np.repeat((lip * (.03 + .09 * micro))[..., None], 3, axis=2)
    # Wet/lip/pool/void layers form separate physical states with broad range.
    M = 18 + 153 * membrane + 71 * lip + 49 * pool - 38 * void + 17 * micro
    R = 232 - 134 * membrane - 96 * lip - 48 * pool + 22 * void + 15 * (1.0 - micro)
    C = 20 + 145 * membrane + 81 * lip + 44 * pool - 24 * void + 24 * micro
    value = (np.clip(paint, 0, 1).astype(np.float32),
             np.stack((np.clip(M, 0, 255), np.clip(R, 0, 255),
                       np.clip(C, 0, 255)), axis=2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_groovy_lava_lamp_filament(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5:
        source = source / 255.0
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    mix = (np.clip(coverage, 0, 1) * float(pm))[..., None]
    return np.clip(source * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_groovy_lava_lamp_filament(shape, mask, seed, sm):
    del sm
    _, spec = _arrays(shape, seed)
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    out = np.empty(spec.shape[:2] + (4,), np.uint8)
    out[..., :3] = (spec.astype(np.float32) * np.clip(coverage, 0, 1)[..., None]).astype(np.uint8)
    out[..., 3] = (np.clip(coverage, 0, 1) * 255).astype(np.uint8)
    return out
