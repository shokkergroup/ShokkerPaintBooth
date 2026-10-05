"""Living Obsidian I1 — dark micro-faceted lacquer with local optical states.

SPB-105 / 2026-08-29.  A separate IMPOSSIBLE FINISHES material family:
not Hologram Metal, not a grid, and not coloured static.  Its authored carrier
contains dense irregular 8–32px glass/metal facets; M/R/Cc are extracted from
each facet's visible lips, pockets, and restrained spectral flashes.
"""
from collections import OrderedDict
from pathlib import Path
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()
_ASSET = Path(__file__).resolve().parents[2] / "assets" / "generated" / "impossible" / "obsidian_living_i1_2026.png"


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    source = cv2.imread(str(_ASSET), cv2.IMREAD_COLOR)
    if source is None:
        raise RuntimeError(f"Living Obsidian asset missing: {_ASSET}")
    rgb = cv2.cvtColor(cv2.resize(source, (w, h), interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    gray = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    hsv = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[..., 1] / 255.0
    # Native highlight lips survive without turning every dark pocket into a
    # bright dot.  The two radii intentionally form material hierarchy.
    fine = np.abs(gray - cv2.GaussianBlur(gray, (0, 0), 1.6))
    body = np.abs(gray - cv2.GaussianBlur(gray, (0, 0), 9.0))
    lip = np.clip(2.6 * fine + 1.15 * body, 0.0, 1.0)
    pocket = np.clip(1.0 - 1.45 * gray + .22 * (1.0 - lip), 0.0, 1.0)
    flash = np.clip((sat - .15) * 2.4, 0.0, 1.0) * np.clip((gray - .10) * 1.8, 0.0, 1.0)
    pearl = np.array((.26, .37, .47), np.float32)
    ink = np.array((.020, .027, .038), np.float32)
    spectral = np.stack((rgb[..., 0] * .88 + .06, rgb[..., 1] * 1.06, rgb[..., 2] * 1.12), axis=2)
    # I2 exposure correction: I1's dark pockets survived native view but
    # collapsed to black at picker scale.  Keep the same individual material
    # states, but give every pocket enough smoked-silver body to read on-car.
    paint = ink[None, None, :] * (.82 + .18 * pocket[..., None])
    paint += rgb * (.15 + .28 * gray[..., None] + .15 * lip[..., None])
    paint += pearl[None, None, :] * (lip[..., None] * (.34 + .46 * gray[..., None]))
    paint += spectral * (flash[..., None] * (.21 + .32 * lip[..., None]))
    paint += np.repeat((gray * (.05 + .18 * lip))[..., None], 3, axis=2)
    # Every local facet owns a different metal/roughness/clearcoat response.
    # Channel encoding is deliberately physical rather than a recoloured map.
    M = 20 + 164 * lip + 46 * gray + 22 * flash - 28 * pocket
    R = 229 - 155 * lip - 54 * flash + 22 * pocket + 18 * (1.0 - gray)
    C = 18 + 178 * lip + 38 * flash + 24 * gray - 18 * pocket
    value = (
        np.clip(paint, 0, 1).astype(np.float32),
        np.stack((np.clip(M, 0, 255), np.clip(R, 0, 255), np.clip(C, 0, 255)), axis=2).astype(np.uint8),
    )
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_impossible_living_obsidian(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed); src = np.asarray(paint, np.float32)[..., :3]
    if src.max(initial=0) > 1.5:
        src = src / 255.0
    m = np.asarray(mask, np.float32); m = m[..., 0] if m.ndim == 3 else m
    mix = (np.clip(m, 0, 1) * float(pm))[..., None]
    return np.clip(src * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_impossible_living_obsidian(shape, mask, seed, sm):
    del sm
    _, spec = _arrays(shape, seed); m = np.asarray(mask, np.float32); m = m[..., 0] if m.ndim == 3 else m
    out = np.empty(spec.shape[:2] + (4,), np.uint8)
    out[..., :3] = (spec.astype(np.float32) * np.clip(m, 0, 1)[..., None]).astype(np.uint8)
    out[..., 3] = (np.clip(m, 0, 1) * 255).astype(np.uint8)
    return out
