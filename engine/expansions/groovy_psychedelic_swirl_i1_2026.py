"""Psychedelic Swirl I1 — connected silk-screen ink and pearl lacquer.

SPB-105 / Groovy Vibes picker-scale rebuild, 2026-08-29.  Replaces the old
cartoon/rainbow territory read only after visual gates.  The authored carrier
is dense, continuous 1960s ink flow: M/R/Cc derive from actual ink bodies,
fine screen lips, pearlescent pools and chroma—not a second colour map.
"""
from collections import OrderedDict
from pathlib import Path
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()
_ASSET = Path(__file__).resolve().parents[2] / "assets" / "generated" / "groovy" / "psychedelic_lacquer_i1_2026.png"


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    source = cv2.imread(str(_ASSET), cv2.IMREAD_COLOR)
    if source is None:
        raise RuntimeError(f"Psychedelic lacquer asset missing: {_ASSET}")
    bgr = cv2.resize(source, (w, h), interpolation=cv2.INTER_CUBIC)
    paint = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hue, sat, val = hsv[..., 0] / 179.0, hsv[..., 1] / 255.0, hsv[..., 2] / 255.0
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    # Two physically interpretable scales: tiny silk-screen lips and broader
    # pooled ink/pearl transitions.  Both are visible in the paint carrier.
    micro = np.abs(gray - cv2.GaussianBlur(gray, (0, 0), 1.35))
    pool = np.abs(gray - cv2.GaussianBlur(gray, (0, 0), 8.5))
    lip = np.clip(2.75 * micro + 1.35 * pool, 0.0, 1.0)
    pearl = np.clip((val - .48) * 1.75, 0.0, 1.0) * np.clip((.80 - sat) * 1.5, 0.0, 1.0)
    ink = np.clip(.30 + .70 * sat, 0.0, 1.0)
    # I2 spec spread repair: I1 rendered beautifully but M/R std were 19.4/
    # 19.6.  The extra separation follows the paint's actual hue population,
    # giving adjacent inks different physical states without a detached map.
    hue_m = .5 + .5 * np.cos(2*np.pi*(hue - .08))
    hue_r = .5 + .5 * np.cos(2*np.pi*(hue - .43))
    hue_c = .5 + .5 * np.cos(2*np.pi*(hue - .74))
    M = 18 + 102 * ink + 96 * lip + 49 * pearl + 34 * val + 28 * hue_m
    R = 239 - 104 * ink - 101 * lip - 53 * pearl + 24 * (1.0 - val) - 30 * hue_r
    C = 14 + 114 * ink + 108 * lip + 65 * pearl + 26 * val + 31 * hue_c
    value = (
        np.clip(paint, 0, 1).astype(np.float32),
        np.stack((np.clip(M, 0, 255), np.clip(R, 0, 255), np.clip(C, 0, 255)), axis=2).astype(np.uint8),
    )
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_psychedelic_swirl(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed); src = np.asarray(paint, np.float32)[..., :3]
    if src.max(initial=0) > 1.5:
        src = src / 255.0
    m = np.asarray(mask, np.float32); m = m[..., 0] if m.ndim == 3 else m
    mix = (np.clip(m, 0, 1) * float(pm))[..., None]
    return np.clip(src * (1 - mix) + authored * mix, 0, 1).astype(np.float32)


def spec_psychedelic_swirl(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    _, spec = _arrays(shape, seed)
    return spec
