"""Acid Ink Silk-Screen I1 — staged 1970s print-lacquer material candidate.

SPB-105 / owner finish doctrine / 2026-08-29.  This uses an authored dense
1254² screen-ink source whose individual pigments and registration lips scale
to the required native 8–32px range at 2048².  It is not a generic recolor:
visible ink ridges, pearl overlap, saturated pools and dark paper/clearcoat
gaps each own their M/R/Cc behavior.  I2 keeps the source but independently
binds metal/coat to visible warm/cool pigment passes, correcting I1's
green-heavy response preview. Stage and inspect before wiring.
"""
from collections import OrderedDict
from pathlib import Path
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()
_ASSET = Path(__file__).resolve().parents[2] / "assets" / "generated" / "groovy" / "acid_ink_silkscreen_i1_2026.png"


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    source = cv2.imread(str(_ASSET), cv2.IMREAD_COLOR)
    if source is None:
        raise RuntimeError(f"Acid Ink source missing: {_ASSET}")
    rgb = cv2.cvtColor(cv2.resize(source, (w, h), interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    encoded = (rgb * 255).astype(np.uint8)
    gray = cv2.cvtColor(encoded, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(encoded, cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[..., 1] / 255.0
    fine = np.abs(gray - cv2.GaussianBlur(gray, (0, 0), 1.35))
    overlap = np.abs(gray - cv2.GaussianBlur(gray, (0, 0), 5.5))
    pearl = np.clip(2.3 * fine + 1.10 * overlap, 0.0, 1.0)
    ink_pool = np.clip((sat - .20) * 1.52 + .16 * gray, 0.0, 1.0)
    paper_gap = np.clip(1.0 - 1.24 * gray + .20 * (1.0 - ink_pool), 0.0, 1.0)
    # Preserve the authored pigment language but deepen it into automotive ink
    # lacquer.  Thin registration lips carry pearl, not arbitrary sparkle.
    lacquer = rgb * (.50 + .36 * ink_pool[..., None] + .17 * pearl[..., None])
    lacquer += np.array((.018, .010, .040), np.float32) * paper_gap[..., None]
    lacquer += np.array((.23, .11, .27), np.float32) * (pearl[..., None] * (.22 + .44 * sat[..., None]))
    red_ink, green_ink, blue_ink = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # Warm registration ink lifts M, cool ink lifts Cc, and pearl lips smooth
    # together. These are separate, source-visible print-process states.
    M = 12 + 98 * ink_pool + 93 * pearl + 53 * red_ink + 19 * gray - 31 * paper_gap
    R = 183 - 62 * ink_pool - 111 * pearl + 28 * paper_gap + 25 * green_ink + 13 * (1.0 - sat)
    C = 13 + 78 * ink_pool + 117 * pearl + 58 * blue_ink + 18 * sat - 23 * paper_gap
    value = (np.clip(lacquer, 0, 1).astype(np.float32),
             np.stack((np.clip(M, 0, 255), np.clip(R, 0, 255),
                       np.clip(C, 0, 255)), axis=2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_groovy_acid_ink_silkscreen(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5:
        source = source / 255.0
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    mix = (np.clip(coverage, 0, 1) * float(pm))[..., None]
    return np.clip(source * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_groovy_acid_ink_silkscreen(shape, mask, seed, sm):
    del sm
    _, spec = _arrays(shape, seed)
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    out = np.empty(spec.shape[:2] + (4,), np.uint8)
    out[..., :3] = (spec.astype(np.float32) * np.clip(coverage, 0, 1)[..., None]).astype(np.uint8)
    out[..., 3] = (np.clip(coverage, 0, 1) * 255).astype(np.uint8)
    return out
