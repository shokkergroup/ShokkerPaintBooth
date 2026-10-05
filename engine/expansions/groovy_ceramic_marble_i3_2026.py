"""Ceramic Marble I3 — staged 1960s psychedelic mineral-glaze material.

SPB-105 / owner doctrine / 2026-08-29.  Replaces the rejected flat/murky
marble direction with non-repeating, jittered 10–28px mineral cells, hairline
pearl seams, translucent glaze pools and adjacent locally-owned M/R/Cc states.
No macro blob, stripe, grid or repeating station is used.
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
    rng = np.random.default_rng(int(seed) * 92821 + 77)
    # One jittered source in each 14–18px neighborhood forms irregular mineral
    # cells; labels yield connected geometry rather than a random dot field.
    sources = np.full((h, w), 255, np.uint8)
    for gy in range(8, h, 16):
        for gx in range(8, w, 16):
            px = int(np.clip(gx + rng.integers(-6, 7), 0, w - 1))
            py = int(np.clip(gy + rng.integers(-6, 7), 0, h - 1))
            sources[py, px] = 0
    dist, labels = cv2.distanceTransformWithLabels(sources, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    labels = labels.astype(np.int32)
    count = int(labels.max()) + 1
    cell_a = rng.random(count).astype(np.float32)
    cell_b = rng.random(count).astype(np.float32)
    cell_c = rng.random(count).astype(np.float32)
    a, b, c = cell_a[labels], cell_b[labels], cell_c[labels]
    edge = ((labels != np.roll(labels, 1, 0)) | (labels != np.roll(labels, 1, 1))).astype(np.float32)
    edge = cv2.GaussianBlur(edge, (0, 0), .68)
    edge = np.clip(edge / max(float(edge.max()), 1e-6), 0, 1)
    # Small-cell depth produces an actual glaze bowl/lip inside each mineral
    # event, rather than making every cell a flat colored polygon.
    radius = np.clip(dist / 10.0, 0, 1)
    bowl = np.clip(1.0 - radius, 0, 1)
    pearl = np.clip(edge * (.62 + .38 * c), 0, 1)
    # Muted psychedelic ceramics: plum, peacock, copper and raspberry vary per
    # individual mineral cell, with no category-foreign rainbow territory map.
    plum = np.array((.17, .035, .25), np.float32)
    peacock = np.array((.025, .30, .34), np.float32)
    copper = np.array((.55, .16, .055), np.float32)
    raspberry = np.array((.47, .035, .23), np.float32)
    choice0 = np.stack((a, 1 - a, b), axis=2)
    choice1 = np.stack((b, c, 1 - b), axis=2)
    paint = np.broadcast_to(plum, (h, w, 3)).astype(np.float32).copy()
    paint += peacock * ((.18 + .38 * a) * (1.0 - .42 * bowl))[..., None]
    paint += copper * ((.04 + .28 * b) * (.42 + .58 * bowl))[..., None]
    paint += raspberry * ((.05 + .29 * c) * (.30 + .70 * (1.0 - bowl)))[..., None]
    paint += choice0 * (pearl[..., None] * .15)
    paint += choice1 * (bowl[..., None] * (.025 + .055 * c[..., None]))
    # Cell-owned response: wet pearl seam / glazed bowl / mineral body all
    # receive different values with broad 8-tier variation inside the carrier.
    M = 21 + 117 * a + 44 * bowl + 83 * pearl + 18 * c
    R = 222 - 92 * a - 47 * bowl - 112 * pearl + 26 * b
    C = 26 + 108 * b + 51 * bowl + 99 * pearl + 19 * c
    value = (np.clip(paint, 0, 1).astype(np.float32),
             np.stack((np.clip(M, 0, 255), np.clip(R, 0, 255),
                       np.clip(C, 0, 255)), axis=2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_groovy_ceramic_marble(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5:
        source = source / 255.0
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    mix = (np.clip(coverage, 0, 1) * float(pm))[..., None]
    return np.clip(source * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_groovy_ceramic_marble(shape, mask, seed, sm):
    del sm
    _, spec = _arrays(shape, seed)
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    out = np.empty(spec.shape[:2] + (4,), np.uint8)
    out[..., :3] = (spec.astype(np.float32) * np.clip(coverage, 0, 1)[..., None]).astype(np.uint8)
    out[..., 3] = (np.clip(coverage, 0, 1) * 255).astype(np.uint8)
    return out
