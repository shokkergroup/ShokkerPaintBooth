"""Private Houdini I22 — Latticework Nocturne, pass 1.

An innocent dark woven prism surface carries no concealed illustration in its
paint.  The spec alone contains a recurring, hand-built-looking quattrofoil
arabesque: petal arcs, braid shoulders, offset inlays, pin dots and a broken
inner halo.  It repeats over the entire 2048 canvas so a car never depends on
one large logo landing on one panel.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _hash(a, b, seed):
    return np.mod(np.sin(a * 12.9898 + b * 78.233 + seed * 31.719) * 43758.5453, 1).astype(np.float32)


def _smooth_band(value, centre, width):
    return np.exp(-((value - centre) / width) ** 2).astype(np.float32)


def _build(shape, seed):
    key = (*map(int, shape), int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]
    h, w = map(int, shape)
    scale = 768 / max(h, w)
    hh, ww = max(192, round(h * scale)), max(192, round(w * scale))
    yy, xx = np.mgrid[:hh, :ww].astype(np.float32)
    x, y = xx / scale, yy / scale
    # Fine 8–24px innocent carrier: two warped weave bases, over-under ribs,
    # mica and tiny weave apertures.  It must be worth looking at before light
    # reveals anything else.
    q = seed * .071
    u = .84*x + .54*y + 3.2*np.sin(y*.041+q)
    v = -.54*x + .84*y + 3.1*np.sin(x*.046-q)
    thread = 9.4
    fu, fv = np.mod(u/thread, 1.0), np.mod(v/thread, 1.0)
    warp = _smooth_band(fu, .50, .115)
    weft = _smooth_band(fv, .50, .105)
    over = (np.floor(u/thread).astype(np.int32) + np.floor(v/thread).astype(np.int32)) & 1
    thread_light = np.where(over > 0, .72*warp+.28*weft, .72*weft+.28*warp)
    micro = (np.sin(u*1.63+v*.29)*np.sin(v*1.31-u*.24) > .91).astype(np.float32)
    pore = _smooth_band(np.mod(u+v, 16.0), 8.0, .62) * _smooth_band(np.mod(u-v, 16.0), 8.0, .62)
    grade = .50 + .50*np.sin(u*.018-v*.025+.8*np.sin(v*.011))
    # P2: P1's neutral was handsome only after crosslight; lift its woven
    # blue-black pigment enough that picker scale reads as material, not void.
    ground = np.dstack((.018+.018*grade, .024+.025*grade, .046+.052*grade))
    ink = np.dstack((.026+.041*thread_light, .060+.090*thread_light, .090+.128*thread_light))
    art = ground*.48 + ink*.52
    art += np.dstack((.024*micro, .094*micro, .132*micro))
    art += np.dstack((.040*pore, .016*pore, .060*pore))
    # Secret field: 104px recurring arabesques.  Every visible component is
    # 8–24px; the larger repeat is only an arrangement, never a macro icon.
    cell = 104.0
    gi, gj = np.floor(x/cell), np.floor(y/cell)
    lx = np.mod(x/cell, 1.0) - .5
    ly = np.mod(y/cell, 1.0) - .5
    parity = np.mod(gi.astype(np.int32) + gj.astype(np.int32), 2)
    # Swap and reverse alternate tiles so the field reads woven/organic, not
    # stamped wallpaper.  All forms are spec-only below.
    X = np.where(parity > 0, ly, lx)
    Y = np.where(parity > 0, -lx, ly)
    # P2: no identically oriented flower stamps.  Each repeat gets a small
    # deterministic turn before the same hand-built components are assembled.
    phi = (_hash(gi, gj, seed+19)-.5)*.86
    X, Y = np.cos(phi)*X-np.sin(phi)*Y, np.sin(phi)*X+np.cos(phi)*Y
    drift = (_hash(gi, gj, seed+7) - .5) * .052
    X, Y = X + drift, Y - drift*.63
    # Four orbital petal arcs, two offset braid shoulders, inner halo segments,
    # nested inlay and pearl pinwork.  This is ornamental anatomy, not a star.
    petals = np.zeros((hh, ww), np.float32)
    for px, py in ((.22,0.0),(-.22,0.0),(0.0,.22),(0.0,-.22)):
        d = np.sqrt((X-px)**2+(Y-py)**2)
        petals = np.maximum(petals, _smooth_band(d, .155, .030))
    diag_a = _smooth_band(np.abs(X+Y), .315, .035)
    diag_b = _smooth_band(np.abs(X-Y), .315, .035)
    braid = np.maximum(diag_a, diag_b) * np.clip(1.0 - 1.45*np.sqrt(X*X+Y*Y), 0, 1)
    radius = np.sqrt(X*X+Y*Y)
    theta = np.arctan2(Y, X)
    halo = _smooth_band(radius, .335, .022) * np.power(np.clip(.5+.5*np.cos(4*theta), 0, 1), 3.0)
    inlay = _smooth_band(np.abs(np.abs(X)-np.abs(Y)), .085, .022) * _smooth_band(radius, .205, .055)
    pins = (_smooth_band(np.mod(X*8.0+Y*5.0, 1.0), .5, .08) *
            _smooth_band(np.mod(X*5.0-Y*8.0, 1.0), .5, .08) *
            _smooth_band(radius, .405, .075))
    # P4: abandon the flower anatomy entirely.  These are fine, continuous
    # filigree strokes: two warped scroll ribbons, a narrow counter-ribbon and
    # pearl joints.  It should read as an impossible woven relief under light,
    # never as a stamped motif or an emoji-like symbol.
    scroll_a = _smooth_band(np.sin(15.0*X + 3.1*np.sin(8.0*Y)) - .52*np.cos(9.0*Y), 0.0, .105)
    scroll_b = _smooth_band(np.sin(14.0*Y - 2.7*np.sin(7.0*X)) + .47*np.cos(10.0*X), 0.0, .092)
    counter = _smooth_band(np.sin(9.0*(X-Y) + 2.4*np.sin(8.0*(X+Y))), .0, .072)
    joint = _smooth_band(np.mod(X*9.0+Y*11.0, 1.0), .5, .075) * _smooth_band(np.mod(X*11.0-Y*9.0, 1.0), .5, .075)
    filigree = np.clip(.62*scroll_a + .54*scroll_b + .40*counter, 0, 1)
    # P1 deliberately tests full neighbouring material cards.  It is not a
    # binary mask: every sub-mark gets a distinct M/R/Cc relationship.
    M = 61 + 80*thread_light + 22*micro + 38*pore
    R = 158 - 71*thread_light - 24*micro - 26*pore
    C = 168 - 76*thread_light - 37*micro - 21*pore
    # Different lobe placement per channel prevents an RGB-like recolor: a
    # scroll may flash as metal, while its neighbour reads satin or wet coat.
    reveal_gate = np.clip(.22 + .78*(.70*thread_light + .18*micro + .12*pore), 0, 1)
    # P5: P4's channel lobes were elegant only in code—the 8–16px strokes
    # fell below usable material separation after native-scale inspection.
    # Raise separation, not feature size, and retain the deliberate channel
    # offsets so the return is a shimmer rather than a bright painted line.
    M += reveal_gate*(137*filigree - 66*counter + 104*joint + 34*braid)
    R += reveal_gate*(-108*np.roll(filigree, 5, axis=1) + 116*counter - 93*joint - 37*braid)
    C += reveal_gate*(-141*np.roll(filigree, -4, axis=0) + 98*np.roll(counter, 3, axis=1) - 129*joint + 48*inlay)
    M = np.clip(M, 0, 255); R = np.clip(R, 15, 255); C = np.clip(C, 16, 255)
    art = np.clip(art, 0, 1).astype(np.float32)
    spec = np.dstack((M, R, C)).astype(np.uint8)
    if (hh, ww) != (h, w):
        art = cv2.resize(art, (w, h), interpolation=cv2.INTER_CUBIC)
        spec = cv2.resize(spec, (w, h), interpolation=cv2.INTER_CUBIC)
    result = (art.astype(np.float32), spec)
    with _LOCK:
        _CACHE[key] = result
        if len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return result


def paint_latticework_nocturne_i22(paint, shape, mask, seed, pattern_mix, bbox):
    del bbox
    art, _ = _build(shape, seed)
    source = np.asarray(paint, np.float32)[..., :3]
    if source.max(initial=0) > 1.5:
        source /= 255.0
    alpha = np.asarray(mask, np.float32)
    if alpha.ndim == 3:
        alpha = alpha[..., 0]
    alpha = (np.clip(alpha, 0, 1) * np.clip(float(pattern_mix), 0, 1))[..., None]
    return np.clip(source*(1-alpha) + art*alpha, 0, 1).astype(np.float32)


def spec_latticework_nocturne_i22(shape, seed, spec_mix, base_metal, base_rough):
    del spec_mix, base_metal, base_rough
    return _build(shape, seed)[1]
