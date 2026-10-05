"""Diner Checkerboard I1 — fine porcelain tile, soda-glass and chrome seams.

SPB-105 / SH-DINER-CHECKER-I1, 2026-08-29.  Owner verdict: the previous
card read as dusty micro-noise with a flat olive spec panel.  This uses a
category-true 16px porcelain checker (with 2px silver grout and 8px glaze
states), never enlarged wallpaper.  Every visible material state owns a
different M/R/Cc response.  Direct 2048 and picker evidence are required
before any registry promotion.
"""
from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np


_CACHE, _LOCK = OrderedDict(), RLock()


def _soft(z, edge):
    return np.clip(z / edge, 0.0, 1.0)


def _arrays(shape, seed):
    h, w = int(shape[0]), int(shape[1]); key = (h, w, int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]

    # Render at 1024 only as a speed path; all geometry below is authored in
    # native 2048-space pixel dimensions and then restored with linear detail.
    q = min(1.0, 1024.0 / max(h, w)); hh, ww = max(16, round(h*q)), max(16, round(w*q))
    y, x = np.mgrid[0:hh, 0:ww].astype(np.float32); u, v = x/q, y/q
    # 16px diagonal porcelain tiles, each carrying a 2px chrome grout border.
    px = np.mod(u + 0.54*v, 16.0); py = np.mod(v - 0.18*u, 16.0)
    grout = np.maximum(_soft(1.75 - np.minimum(px, 16-px), 1.75),
                       _soft(1.75 - np.minimum(py, 16-py), 1.75))
    tx = np.floor((u + .54*v)/16.0).astype(np.int32)
    ty = np.floor((v - .18*u)/16.0).astype(np.int32)
    parity = (tx + ty) & 1
    # Eight tile-local glaze states stop same-color checker wallpaper.
    state = np.mod(tx*17 + ty*29 + (tx ^ ty)*7 + int(seed), 8).astype(np.int32)
    cx, cy = np.abs(px-8.0), np.abs(py-8.0)
    inset = np.clip(1.0 - np.maximum(cx, cy)/7.0, 0.0, 1.0)
    pin = np.clip(1.0 - np.hypot(cx, cy)/3.2, 0.0, 1.0)
    # Fine 8px soda-glass diagonals appear only in selected tiles, reading as
    # a diner counter reflection rather than a second macro pattern.
    glint_seed = np.mod(tx*11 + ty*5, 7)
    glass = ((glint_seed == 0) | (glint_seed == 4)).astype(np.float32) * np.power(inset, 2.6)
    diagonal = np.clip(1.0 - np.abs((px-py)-1.0)/1.15, 0.0, 1.0) * glass

    cream = np.array((.93, .78, .55), np.float32)
    coral = np.array((.78, .08, .12), np.float32)
    mint = np.array((.07, .58, .56), np.float32)
    pearl = np.array((.72, .82, .84), np.float32)
    chrome = np.array((.48, .63, .70), np.float32)
    tone = np.array((-.08,-.045,-.015,.025,.055,.085,.12,.16), np.float32)[state][..., None]
    base = np.where(parity[..., None] == 0, cream + tone, coral + tone*.45)
    paint = np.clip(base, 0, 1)
    paint = paint*(1-glass[..., None]*.27) + mint*(glass[..., None]*.27)
    paint = paint*(1-diagonal[..., None]*.58) + pearl*(diagonal[..., None]*.58)
    paint = paint*(1-pin[..., None]*.15) + pearl*(pin[..., None]*.15)
    paint = paint*(1-grout[..., None]*.93) + chrome*(grout[..., None]*.93)

    # Spec follows tile parity, per-tile glaze, soda glints and seam chrome.
    shade = state.astype(np.float32)
    M = np.where(parity == 0, 90 + shade*11, 34 + shade*12)
    R = np.where(parity == 0, 95 - shade*7, 190 - shade*11)
    C = np.where(parity == 0, 112 + shade*10, 38 + shade*13)
    M = M + glass*42 + diagonal*67 + pin*35 + grout*118
    R = R - glass*33 - diagonal*63 - pin*20 - grout*142
    C = C + glass*58 + diagonal*74 + pin*31 + grout*124

    if (hh, ww) != (h, w):
        up = lambda z: cv2.resize(z.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        paint = up(paint); M, R, C = map(up, (M, R, C))
    value = (np.clip(paint, 0, 1).astype(np.float32),
             np.stack((np.clip(M,0,255), np.clip(R,0,255), np.clip(C,0,255)), 2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2: _CACHE.popitem(last=False)
    return value


def paint_diner_enamel_checker(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed); src = np.asarray(paint, np.float32)[..., :3]
    if src.max(initial=0) > 1.5: src = src / 255.0
    m = np.asarray(mask, np.float32); m = m[...,0] if m.ndim == 3 else m
    mix = (np.clip(m,0,1) * float(pm))[...,None]
    return np.clip(src*(1-mix) + authored*mix, 0, 1).astype(np.float32)


def spec_diner_enamel_checker(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    _, spec = _arrays(shape, seed); return spec
