"""Private Houdini I23 — Vesper Mesh, P1.

The ordinary surface is a dark enamel/engraved-metal process.  Five global
tool directions create a nonperiodic fine mesh; the same intersections, not a
second painted icon layer, become intermittent Vesper-knot material events.
All visible marks and all M/Rough/Cc states arise from that one geometry.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()
_TAU = np.float32(6.283185307179586)


def _line(position: np.ndarray, pitch: float, width: float) -> np.ndarray:
    """Fine engraved line, expressed as a smooth physical tool ridge."""
    return np.exp(-((np.sin(_TAU * position / pitch) / width) ** 2)).astype(np.float32)


def _arrays(shape: tuple[int, int], seed: int) -> tuple[np.ndarray, np.ndarray]:
    key = (*map(int, shape), int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]
    h, w = map(int, shape)
    scale = min(1.0, 1024.0 / max(h, w))
    hh, ww = max(256, round(h*scale)), max(256, round(w*scale))
    yy, xx = np.mgrid[:hh, :ww].astype(np.float32)
    x, y = xx/scale, yy/scale

    # A hand-ruled lacquer is never a perfect CAD lattice.  Two gentle global
    # registration drifts bend all five tool passes coherently; no random marks
    # or independent tiles are introduced.
    phase = (seed % 7919) * .00091
    dx = 3.4*np.sin(y*.019 + phase) + 1.8*np.sin((x+y)*.011 - phase)
    dy = 3.0*np.sin(x*.021 - phase) - 1.5*np.sin((x-y)*.013 + phase*.7)
    X, Y = x+dx, y+dy
    angles = np.deg2rad(np.array((0., 36., 72., 108., 144.), np.float32))
    strokes = []
    for n, a in enumerate(angles):
        projected = X*np.cos(a) + Y*np.sin(a)
        # 7–12px native ridges inside ~30px spacings: density comes from five
        # linked passes, never a single macro tile.
        strokes.append(_line(projected + n*4.3, 29.0 + n*.62, .205 + n*.011))
    stack = np.stack(strokes, axis=0)
    rank = np.sort(stack, axis=0)
    primary, secondary, tertiary = rank[-1], rank[-2], rank[-3]
    engrave = np.clip(primary*.72 + secondary*.31, 0, 1)
    shoulder = np.clip(secondary*.74 + tertiary*.26, 0, 1)
    # The hidden forms are genuine multi-direction intersections.  A two-pass
    # knot is an ordinary braid; a three/five-pass event becomes a Vesper knot
    # only through its deliberate material-card relationship below.
    knot = np.clip((tertiary-.22)/.72, 0, 1) ** 1.35
    core = np.clip((np.min(stack, axis=0)-.15)/.85, 0, 1) ** 1.45
    # Fine in-line tooth and small process-bound glints, phase locked to the
    # actual engraved passes.  No free noise or unrelated sparkle.
    tooth = np.maximum.reduce([_line((X*np.cos(a)+Y*np.sin(a))*3.35+n*11.0, 13.0, .18)
                               for n, a in enumerate(angles)])
    glow = np.clip(.38*engrave + .44*shoulder + .76*knot + .28*tooth, 0, 1)
    slow = .5 + .5*np.sin(X*.017 - Y*.021 + .4*np.sin((X+Y)*.007))

    # P1 carrier: black-indigo enamel, dim graphite incision, steel shoulders
    # and rare violet/copper tool glints. The Vesper knot has no paint-only
    # silhouette; paint merely shows a plausible worked surface.
    # P2: P1's ordinary surface advertised the lattice as a brown wallpaper.
    # Keep the same physical engraving but narrow the *paint* separation so it
    # reads as quiet blue-black enamel until the material cards take over.
    void = np.dstack((.020+.014*slow, .028+.020*slow, .046+.037*slow))
    graphite = np.dstack((.035+.026*slow, .052+.038*slow, .082+.061*slow))
    steel = np.dstack((.094+.054*slow, .130+.074*slow, .184+.100*slow))
    ink = void*(1-(engrave*.27)[...,None]) + graphite*(engrave*.27)[...,None]
    ink = ink*(1-(shoulder*.22)[...,None]) + steel*(shoulder*.22)[...,None]
    violet = np.array((.20, .050, .34), np.float32)
    copper = np.array((.34, .115, .030), np.float32)
    tint = np.where((np.sin(X*.071+Y*.053)>0)[...,None], violet, copper)
    paint = ink*(1-(knot*.055)[...,None]) + tint*(knot*.055)[...,None]
    paint += np.dstack((.004*tooth, .008*tooth, .014*tooth))

    # Material process map. Every field is a component of the same engraved
    # mesh: recessed enamel, satin cut, dark chrome shoulder, pearl knot,
    # hot Fractured core, then a tiny coat-active razor at five-way meetings.
    # P3: P2's entire mesh catches the same wide light band.  Keep its normal
    # state intentionally quiet satin, then reserve extreme material changes
    # for genuine three/five-direction meetings. This separates the ordinary
    # surface process from the light-only Vesper discovery.
    # P4 restores broad shoulder travel without restoring P1's loud all-over
    # chrome. The variation is still literally caused by engraved relief.
    M = 54 + 31*slow + 31*engrave + 71*shoulder + 21*knot + 28*tooth
    R = 202 - 28*slow - 34*engrave - 83*shoulder - 24*knot - 34*tooth
    C = 194 - 33*slow - 46*engrave - 97*shoulder - 31*knot - 43*tooth
    # A secret is a rare, nested knot rather than every two-direction crossing.
    node = np.clip((tertiary-.47)/.53, 0, 1) ** 2
    node_wide = cv2.GaussianBlur(node, (0,0), 1.35)
    node_core = np.clip((node-.37)/.63, 0, 1)
    node_rim = np.clip(node_wide-node_core*.68, 0, 1)
    hot = node_wide > .10
    # Node rim / body / core are three neighbouring physical neighborhoods,
    # so a Vesper knot can assemble under light rather than print a sticker.
    M = M + 96*node_rim + 42*node_wide
    R = R - 76*node_rim - 31*node_wide
    C = C - 101*node_rim - 46*node_wide
    M = np.where(hot, np.maximum(M, 222 + 31*node_core), M)
    R = np.where(hot, np.minimum(R, 75 - 57*node_core), R)
    C = np.where(hot, np.minimum(C, 144 - 128*node_core), C)
    # P5 — Hologram Metal lesson, applied only to the visible process anatomy:
    # 8–18px material cells march *along* engraved arms and turn at genuine
    # intersections.  Eight named neighborhoods sit side by side; there is no
    # paint recolor, random flake field, or second pattern underneath.
    dominant = np.argmax(stack, axis=0)
    arm_coord = np.zeros_like(X)
    for n, a in enumerate(angles):
        arm_coord = np.where(dominant == n, X*np.cos(a)+Y*np.sin(a), arm_coord)
    cell_code = np.mod(np.floor(arm_coord/11.0).astype(np.int32)
                       + 3*dominant + np.floor((X-Y)/31.0).astype(np.int32), 8)
    cell_m = np.array((246,250,205,148,94,42,226,252), np.float32)
    cell_r = np.array((32,16,18,54,98,172,138,42), np.float32)
    cell_c = np.array((255,40,16,74,126,166,104,210), np.float32)
    parcel = shoulder > .31
    M = np.where(parcel, cell_m[cell_code], M)
    R = np.where(parcel, cell_r[cell_code], R)
    C = np.where(parcel, cell_c[cell_code], C)
    spec = np.dstack((np.clip(M,0,255), np.clip(R,15,255), np.clip(C,16,255))).astype(np.uint8)
    if (hh, ww) != (h, w):
        paint = cv2.resize(paint.astype(np.float32), (w,h), interpolation=cv2.INTER_CUBIC)
        spec = cv2.resize(spec, (w,h), interpolation=cv2.INTER_CUBIC)
    result = (np.clip(paint,0,1).astype(np.float32), spec)
    with _LOCK:
        _CACHE[key] = result
        if len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return result


def paint_vesper_mesh_i23(paint, shape, mask, seed, pattern_mix, bbox):
    del bbox
    art, _ = _arrays(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5:
        source /= 255.0
    alpha = np.asarray(mask, np.float32)
    if alpha.ndim == 3:
        alpha = alpha[..., 0]
    alpha = (np.clip(alpha, 0, 1)*np.clip(float(pattern_mix), 0, 1))[..., None]
    return np.clip(source*(1-alpha) + art*alpha, 0, 1).astype(np.float32)


def spec_vesper_mesh_i23(shape, seed, spec_mix, base_metal, base_rough):
    del spec_mix, base_metal, base_rough
    return _arrays(shape, seed)[1]
