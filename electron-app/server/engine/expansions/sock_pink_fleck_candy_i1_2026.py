"""Pink Fleck Candy I1 — staged 1950s Candy Apple metalflake lacquer.

SPB-105 / owner doctrine / 2026-08-29.  This is a physical Sock Hop finish,
not a generic dot field: tiny 2–12px pink, pearl, chrome and flat flakes are
embedded in a deep Candy Apple resin, with each visible flake family owning a
different M/R/Cc state.  It is isolated until native and picker evidence prove
that the density reads as lacquer rather than confetti.
"""
from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _draw_flake_layer(canvas, rng, count, lo, hi):
    h, w = canvas.shape
    for _ in range(count):
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        long = int(rng.integers(lo, hi + 1)); short = max(1, int(long * rng.uniform(.27, .58)))
        angle = float(rng.uniform(0, 180)); value = int(rng.integers(90, 256))
        cv2.ellipse(canvas, (x, y), (long, short), angle, 0, 360, value, -1, cv2.LINE_AA)


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    rng = np.random.default_rng(int(seed) * 39019 + 5)
    # Subtle resin depth—only background dye variation, never a macro pattern.
    coarse = rng.standard_normal((max(4, h // 28), max(4, w // 28))).astype(np.float32)
    resin = cv2.resize(coarse, (w, h), interpolation=cv2.INTER_CUBIC)
    resin = cv2.GaussianBlur(resin, (0, 0), 3.0)
    resin = (resin - resin.min()) / max(float(resin.max() - resin.min()), 1e-6)
    hot, pearl, chrome, flat = (np.zeros((h, w), np.uint8) for _ in range(4))
    # Fine physical inclusions only: all ellipse radii remain <= 6px.
    _draw_flake_layer(hot, rng, max(1500, h * w // 910), 1, 4)
    _draw_flake_layer(pearl, rng, max(1100, h * w // 1260), 1, 5)
    _draw_flake_layer(chrome, rng, max(850, h * w // 1630), 1, 6)
    _draw_flake_layer(flat, rng, max(1000, h * w // 1420), 1, 3)
    hot, pearl, chrome, flat = (a.astype(np.float32) / 255.0 for a in (hot, pearl, chrome, flat))
    # Embedded under resin: lower-gain flakes recede while the few chrome chips
    # catch hard light. Their class-specific values prevent a single noisy map.
    base = np.stack((.19 + .22 * resin, .008 + .030 * resin, .055 + .100 * resin), axis=2)
    base += np.stack((.23 * resin, .012 * resin, .07 * resin), axis=2)
    paint = base.copy()
    paint += np.array((.55, .012, .15), np.float32) * hot[..., None]
    paint += np.array((.52, .18, .39), np.float32) * pearl[..., None]
    paint += np.array((.72, .68, .72), np.float32) * chrome[..., None]
    paint *= 1.0 - (.16 * flat[..., None])
    # Flat flakes are matte rose inclusions, beside chrome and pearl—not absent.
    paint += np.array((.20, .004, .035), np.float32) * flat[..., None]
    body_m = 53 + 37 * resin
    body_r = 135 + 48 * (1.0 - resin)
    body_c = 94 + 53 * resin
    M = body_m + 66 * hot + 103 * pearl + 157 * chrome - 30 * flat
    R = body_r - 54 * hot - 89 * pearl - 119 * chrome + 55 * flat
    C = body_c + 44 * hot + 112 * pearl + 123 * chrome - 35 * flat
    value = (np.clip(paint, 0, 1).astype(np.float32),
             np.stack((np.clip(M, 0, 255), np.clip(R, 0, 255),
                       np.clip(C, 0, 255)), axis=2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_sock_pink_fleck_candy(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5:
        source = source / 255.0
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    mix = (np.clip(coverage, 0, 1) * float(pm))[..., None]
    return np.clip(source * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_sock_pink_fleck_candy(shape, mask, seed, sm):
    del sm
    _, spec = _arrays(shape, seed)
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    out = np.empty(spec.shape[:2] + (4,), np.uint8)
    out[..., :3] = (spec.astype(np.float32) * np.clip(coverage, 0, 1)[..., None]).astype(np.uint8)
    out[..., 3] = (np.clip(coverage, 0, 1) * 255).astype(np.uint8)
    return out
