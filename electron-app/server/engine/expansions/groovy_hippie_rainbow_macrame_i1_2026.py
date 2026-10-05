"""Hippie Rainbow Macramé I1 — candidate 1960s hand-dyed cord lacquer.

SPB-105 / owner finish doctrine / 2026-08-30.  The inherited Hippie Rainbow
card is a broad diagonal rainbow stripe field.  This replacement starts from
the actual period material: closely worked, hand-dyed cotton macramé.  Every
visible part is a 2–28px cord, twist ridge, knot face, shadow seam or small
fray; broad pigment pools decide *which cord family* receives which dye, but
never become bands or stand-alone painted shapes.  M/R/Cc is bound to the
over/under cord, twist and knot geometry instead of a separate noise layer.

Candidate only until native and live picker review; no registry side effect.
"""
from collections import OrderedDict
from threading import RLock

import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _smooth_regions(x, y, seed):
    """Slow, non-band dye-bath selector used only to rotate cord colours."""
    phase = (int(seed) % 7919) * 0.0017
    return (
        0.44 * np.sin(x / 221.0 + 0.33 * np.sin(y / 91.0) + phase)
        + 0.31 * np.sin(y / 187.0 - 0.26 * np.sin(x / 123.0) - phase * 0.7)
        + 0.25 * np.sin((x + y) / 313.0 + phase * 1.4)
    )


def _fields(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            _CACHE.move_to_end(key)
            return cached

    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    phase = (int(seed) & 0xFFFF) * 0.00091
    # Hand tension warps the strands by only a few pixels.  The primitive
    # lattice remains fine and the larger flow only stops wallpaper rigidity.
    u = x + 4.4 * np.sin(y / 109.0 + phase) + 1.8 * np.sin(x / 43.0 - y / 71.0)
    v = y + 4.1 * np.sin(x / 127.0 - phase * 1.3) + 1.6 * np.sin(y / 47.0 + x / 79.0)
    a = (u + v) * 0.70710678
    b = (u - v) * 0.70710678
    pitch = 22.0

    def line_distance(q):
        return np.abs(np.mod(q + pitch * .5, pitch) - pitch * .5)

    da, db = line_distance(a), line_distance(b)
    cord_a = np.clip((4.9 - da) / 2.25, 0.0, 1.0)
    cord_b = np.clip((4.9 - db) / 2.25, 0.0, 1.0)
    knot = np.clip((6.8 - np.hypot(da, db)) / 3.1, 0.0, 1.0)
    # Alternating crossings establish a visible over/under hierarchy rather
    # than a flat crosshatch.  A tiny knot crown turns crossings into cordwork.
    ia = np.floor((a + pitch * .5) / pitch).astype(np.int32)
    ib = np.floor((b + pitch * .5) / pitch).astype(np.int32)
    over_a = ((ia + ib) & 1) == 0
    top = np.where(over_a, cord_a, cord_b).astype(np.float32)
    under = np.where(over_a, cord_b, cord_a).astype(np.float32)
    body = np.clip(np.maximum(top, under * .73) + knot * .34, 0.0, 1.0)
    seam = np.clip(np.maximum((da - 2.4) / 1.65 * cord_a,
                              (db - 2.4) / 1.65 * cord_b), 0.0, 1.0)
    twist = (0.5 + 0.5 * np.sin((np.where(over_a, a, b)) * np.pi / 5.4
                                  + 0.78 * np.sin((np.where(over_a, b, a)) / 21.0)))
    ridge = np.clip(body * (0.23 + .77 * twist) - seam * .36, 0.0, 1.0)
    # Fine dry-cotton nibs are attached to exposed cord edges, not scattered.
    edge = np.clip((da - 4.15) / .72, 0, 1) * np.clip((5.05 - da) / .42, 0, 1)
    edge += np.clip((db - 4.15) / .72, 0, 1) * np.clip((5.05 - db) / .42, 0, 1)
    fray = np.clip(edge * (.36 + .64 * (0.5 + .5 * np.sin((x * .83 + y * 1.31) + phase))), 0, 1)
    # Seven period dyes.  Regional drift rotates the *cord* palette rather
    # than making broad visible rainbow bands across empty background.
    region = _smooth_regions(x, y, seed)
    dye = np.mod(np.floor((region + 1.05) * 2.75).astype(np.int32)
                 + ia * 2 - ib + (over_a.astype(np.int32) * 2), 7)
    value = (body.astype(np.float32), top.astype(np.float32), under.astype(np.float32),
             knot.astype(np.float32), seam.astype(np.float32), ridge.astype(np.float32),
             fray.astype(np.float32), dye, region.astype(np.float32))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


_PALETTE = np.array([
    (0.91, 0.08, 0.25),  # cherry-red cotton
    (1.00, 0.35, 0.05),  # tangerine
    (0.98, 0.78, 0.06),  # turmeric
    (0.10, 0.70, 0.57),  # turquoise
    (0.12, 0.25, 0.78),  # indigo
    (0.43, 0.11, 0.66),  # violet
    (0.90, 0.13, 0.58),  # magenta
], np.float32)


def _arrays(shape, seed):
    body, top, under, knot, seam, ridge, fray, dye, region = _fields(shape, seed)
    cord = _PALETTE[dye]
    # Coffee-black open weave makes this an actual textile/cord lacquer, not
    # a full-frame rainbow fill.  Shadows follow the same cord geometry.
    ground = np.zeros_like(cord) + np.array((0.022, 0.014, 0.036), np.float32)
    shadow = np.array((0.055, 0.017, 0.075), np.float32) * (under * .36 + seam * .45)[..., None]
    cord_lit = cord * (.31 + .55 * ridge[..., None])
    cord_lit += np.array((.20, .13, .22), np.float32) * (knot * .23 + fray * .11)[..., None]
    paint = np.clip(ground + shadow + cord_lit * body[..., None], 0, 1).astype(np.float32)
    # Material states are fully geometry-causal: top cords chrome-lacquer,
    # under cords satin, knot faces pearl, seams matte, and dry fibers break
    # clearcoat at 2–4px scale.
    M = 15 + 165 * top + 73 * knot + 34 * ridge + 22 * (dye == 3) + 17 * (dye == 5)
    R = 220 - 109 * top - 53 * knot - 34 * ridge + 37 * seam + 24 * fray
    C = 19 + 145 * top + 77 * knot + 42 * ridge + 31 * (dye == 4) + 19 * (dye == 6) - 29 * seam
    spec = np.stack((np.clip(M, 0, 255), np.clip(R, 15, 255), np.clip(C, 16, 255)), axis=2).astype(np.uint8)
    return paint, spec


def paint_hippie_rainbow_macrame(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5:
        source /= 255.0
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    mix = (np.clip(coverage, 0, 1) * float(pm))[..., None]
    return np.clip(source * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_hippie_rainbow_macrame(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    _, spec = _arrays(shape, seed)
    return spec[..., 0], spec[..., 1], spec[..., 2]
