"""Prism Mosaic I1 — an IMPOSSIBLE dark micro-prism lacquer candidate.

SPB-105 / owner finish doctrine / 2026-08-29: this is a staged, isolated
candidate, not a catalog replacement.  It takes the owner's Hologram Metal
lesson further without reusing that carrier: every native 12px cell has four
separate graphite/prismatic paint states and physically linked M/R/Cc values.
I1's 8px screen resolved as static at picker scale; I2 increased the cell to
12px. I3 corrected the channel relation. I4 uses a still-doctrinal 16px cell
with four 8px local states. I5 preserves that exact geometry and increases
only contrast after a protected Hologram Metal picker comparison showed I4
was too dark for cells to read at library scale.
"""
from collections import OrderedDict
from threading import RLock

import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _hash(ix, iy, salt):
    """Deterministic per-cell scalar in [0, 1), no global random field."""
    return np.mod(np.sin(ix * (12.9898 + salt * .73) + iy * (78.233 + salt * 1.19)
                         + salt * 37.719) * 43758.5453, 1.0)


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    y, x = np.mgrid[:h, :w].astype(np.float32)
    # [2026-09-02 owner: preview 'blows up the pattern'] squares are authored on the 2048 reference
    # canvas so a 1024 live preview / picker snapshot shows the same car, not squares twice as big.
    # At 2048 the factor is exactly 1.0: output is bit-identical to the protected bake.
    x, y = x * (2048.0 / w), y * (2048.0 / h)
    # 16px is still within the owner's 8–32px doctrine. The two 8px halves
    # per axis give 16,384 cells and four adjacent optical states each.
    ix, iy = np.floor(x / 16.0), np.floor(y / 16.0)
    fx, fy = np.mod(x, 16.0) / 16.0, np.mod(y, 16.0) / 16.0
    sub = (fx >= .5).astype(np.float32) + 2.0 * (fy >= .5).astype(np.float32)
    cell = _hash(ix, iy, float(seed) * .017 + 1.0)
    variation = _hash(ix, iy, float(seed) * .023 + 7.0)
    # A restrained underlying illumination flow gives the prism language a
    # connected material rhythm while cells, not broad stripes, carry detail.
    flow = .5 + .5 * np.sin((x + .73 * y) * .014 + 1.8 * np.sin(y * .005))
    edge = np.maximum(np.abs(fx - .5), np.abs(fy - .5)) * 2.0
    bevel = np.clip((edge - .56) / .44, 0.0, 1.0)
    facet = np.clip(1.0 - 1.55 * bevel + .16 * np.sin((fx - fy) * np.pi), 0.0, 1.0)

    # Dark graphite body; the sparse chroma is produced by each prism's own
    # hue rather than an unrelated rainbow territory map.
    hue = np.mod(cell + .113 * sub + .07 * flow + .04 * variation, 1.0)
    r = .5 + .5 * np.sin(6.283185 * (hue + .00))
    g = .5 + .5 * np.sin(6.283185 * (hue + .333333))
    b = .5 + .5 * np.sin(6.283185 * (hue + .666667))
    tint = np.stack((r, g, b), axis=2)
    silver = .112 + .235 * cell + .082 * flow + .096 * facet
    flare = np.clip((cell - .65) * 2.86, 0.0, 1.0) * (.24 + .76 * facet)
    paint = np.repeat((silver * (.76 + .24 * variation))[..., None], 3, axis=2)
    paint += tint * (.040 + .39 * flare[..., None])
    paint += np.repeat((bevel * (.045 + .055 * variation))[..., None], 3, axis=2)
    # Adjacent 4px quadrants differ visibly only when light gives them a reason.
    paint += tint * ((sub / 3.0)[..., None] * (.017 + .055 * flare[..., None]))

    # Eight-plus local response tiers arise from cell, quadrant, flow and bevel;
    # no channel is a recolor of another and every bright tile owns its response.
    metal_state = np.clip(.10 + .61 * cell + .18 * facet + .19 * flare
                          - .22 * bevel + .09 * (sub / 3.0), 0.0, 1.0)
    rough_state = np.clip(.74 - .47 * cell - .29 * flare + .25 * bevel
                          + .11 * variation - .08 * (sub / 3.0), 0.0, 1.0)
    coat_state = np.clip(.08 + .52 * variation + .20 * flow + .23 * flare
                         + .14 * facet - .19 * bevel + .10 * (sub / 3.0), 0.0, 1.0)
    M, R, C = 255.0 * metal_state, 255.0 * rough_state, 255.0 * coat_state
    value = (np.clip(paint, 0, 1).astype(np.float32),
             np.stack((np.clip(M, 0, 255), np.clip(R, 0, 255),
                       np.clip(C, 0, 255)), axis=2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_impossible_prism_mosaic(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5:
        source = source / 255.0
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    mix = (np.clip(coverage, 0, 1) * float(pm))[..., None]
    return np.clip(source * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_impossible_prism_mosaic(shape, mask, seed, sm):
    del sm
    _, spec = _arrays(shape, seed)
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    out = np.empty(spec.shape[:2] + (4,), np.uint8)
    out[..., :3] = (spec.astype(np.float32) * np.clip(coverage, 0, 1)[..., None]).astype(np.uint8)
    out[..., 3] = (np.clip(coverage, 0, 1) * 255).astype(np.uint8)
    return out
