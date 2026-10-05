"""FRACTURED HOUDINI H1-I4 — Veiled Skull / nocturne damascene.

Iteration 1 of the owner-authorized clean restart.  This is intentionally an
*unwired* candidate: a complete midnight damascene lacquer is authored first;
the recurring skulls are only a five-state M/Rough/Cc relief inside it.  No
skull geometry touches the RGB paint plate.
"""
from __future__ import annotations

from collections import OrderedDict
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()
_WORK = 768


def _fract(a):
    return a - np.floor(a)


def _up(a, w, h):
    return cv2.resize(a.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)


def _centres(rng, w, h, count):
    """Blue-noise-ish points; never a visible row/column placement grid."""
    pts = []
    tries = 0
    while len(pts) < count and tries < count * 180:
        tries += 1
        p = (float(rng.uniform(-36, w + 36)), float(rng.uniform(-44, h + 44)))
        if all((p[0]-q[0])**2 + (p[1]-q[1])**2 > 74.0**2 for q in pts):
            pts.append(p)
    return pts


def _arrays(shape, seed):
    h, w = map(int, shape)
    key = (h, w, int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]
    scale = min(1.0, _WORK / max(h, w))
    hh, ww = max(160, round(h * scale)), max(160, round(w * scale))
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    rng = np.random.default_rng(int(seed) ^ 0xA17D4)

    # The visible carrier is a dark, flowing damascene lacquer: engraved flow
    # bundles, irregular pearl pools, pit tooth, and isolated steel catches.
    # It has no symbol field and remains a complete finish by itself.
    warp_x = 7.2*np.sin(yy/23.0) + 3.1*np.sin((xx+yy)/51.0) + 2.7*np.cos(yy/9.7)
    warp_y = 6.4*np.cos(xx/27.0) + 2.8*np.sin((2*xx-yy)/63.0)
    a = (xx + warp_x) / 4.6
    b = (yy + warp_y) / 5.2
    engraving = np.clip(.24 - np.abs(np.sin(a*.82 + np.sin(b*.47)*.74))*.88, 0, 1)
    engraving = np.maximum(engraving, np.clip(.15 - np.abs(np.sin(b*.73 - np.sin(a*.31)*.88))*.63, 0, 1))
    # Nonperiodic pearl pools organize the fine engraving without becoming a
    # macro wallpaper cell.
    f1 = .5+.5*np.sin(xx/31.0 + 1.2*np.sin(yy/43.0) + np.sin((xx-yy)/71.0))
    f2 = .5+.5*np.cos(yy/37.0 + .8*np.sin(xx/29.0) - np.cos((xx+yy)/91.0))
    pool = np.clip((f1*f2-.56)*3.0, 0, 1)
    lip = np.clip(.17 - np.abs(f1-f2)*.86, 0, 1) * (1-pool*.45)
    qx, qy = np.floor((xx+warp_x)/5.7), np.floor((yy+warp_y)/6.1)
    hashv = _fract(np.sin(qx*12.9898 + qy*78.233 + seed*.077)*43758.5453)
    tooth = np.clip((hashv-.77)*4.35, 0, 1) * (1-pool*.38)
    # A few continuous hairline scrolls give the carrier a deliberate
    # old-world rhythm, not a checker or a generic optical grid.
    scroll = np.zeros((hh, ww), np.uint8)
    for _ in range(34):
        cx, cy = rng.uniform(-50, ww+50), rng.uniform(-50, hh+50)
        rx, ry = rng.uniform(10, 23), rng.uniform(7, 18)
        ang = int(rng.uniform(0, 180))
        cv2.ellipse(scroll, (round(cx), round(cy)), (round(rx), round(ry)), ang,
                    int(rng.uniform(190, 250)), int(rng.uniform(290, 350)), 255, 1, cv2.LINE_AA)
    scroll = scroll.astype(np.float32) / 255.0

    # M/R/Cc-only anatomy of recurring, ornate skull reliefs.  Each skull has
    # crown ribs, cheek/temple linework, recessed eyes and nose, toothed jaw,
    # and a broken filigree halo.  The event is 80–140px on the 2048 sheet,
    # built from 3–12px work primitives before the final upscale.
    ridge = np.zeros((hh, ww), np.uint8)
    recess = np.zeros((hh, ww), np.uint8)
    teeth = np.zeros((hh, ww), np.uint8)
    inlay = np.zeros((hh, ww), np.uint8)
    halo = np.zeros((hh, ww), np.uint8)
    for cx, cy in _centres(rng, ww, hh, max(19, int(hh*ww/31500))):
        rx, ry = rng.uniform(20, 30), rng.uniform(27, 38)
        ang = rng.uniform(-.34, .34); ca, sa = np.cos(ang), np.sin(ang)
        th = int(rng.integers(1, 3))
        def pt(px, py):
            return (round(cx + ca*px - sa*py), round(cy + sa*px + ca*py))
        # Crown is three nested arcs, deliberately incomplete like engraving.
        for k, shrink in enumerate((.91, .75, .59)):
            cv2.ellipse(ridge, pt(0, -ry*.06), (max(4, round(rx*shrink)), max(5, round(ry*shrink))),
                        int(np.degrees(ang)), 190+k*9, 349-k*12, 255, th, cv2.LINE_AA)
        for side in (-1, 1):
            ex, ey = side*rx*.31, -ry*.04
            cv2.ellipse(recess, pt(ex, ey), (max(4, round(rx*.235)), max(3, round(ry*.17))),
                        int(np.degrees(ang))+side*9, 0, 360, 255, -1, cv2.LINE_AA)
            cv2.ellipse(ridge, pt(ex, ey), (max(5, round(rx*.29)), max(4, round(ry*.22))),
                        int(np.degrees(ang))+side*9, 24, 336, 255, 1, cv2.LINE_AA)
            # temple -> cheek: a 4-node engraved path rather than cartoon jaws
            cheek = [(side*rx*.60, -ry*.09), (side*rx*.72, ry*.15),
                     (side*rx*.44, ry*.47), (side*rx*.15, ry*.55)]
            cv2.polylines(ridge, [np.array([pt(px, py) for px, py in cheek], np.int32)], False, 255, th, cv2.LINE_AA)
        nose = np.array([pt(0, ry*.10), pt(-rx*.105, ry*.31), pt(rx*.105, ry*.31)], np.int32)
        cv2.fillConvexPoly(recess, nose, 255, lineType=cv2.LINE_AA)
        cv2.polylines(ridge, [nose], True, 255, 1, cv2.LINE_AA)
        jaw = [(-rx*.43, ry*.43), (-rx*.34, ry*.70), (0, ry*.83), (rx*.34, ry*.70), (rx*.43, ry*.43)]
        cv2.polylines(ridge, [np.array([pt(px, py) for px, py in jaw], np.int32)], False, 255, th, cv2.LINE_AA)
        for k in range(-4, 5):
            xk = k*rx*.073
            cv2.line(teeth, pt(xk, ry*.51), pt(xk, ry*.69), 255, 1, cv2.LINE_AA)
        # each halo is a broken three-lobed cartouche with small inlay beads
        cv2.ellipse(halo, pt(0, -ry*.04), (round(rx*1.12), round(ry*.94)), int(np.degrees(ang)), 201, 334, 255, 1, cv2.LINE_AA)
        for k in range(6):
            t = np.pi*(1.12+k*.125)
            px, py = np.cos(t)*rx*1.04, np.sin(t)*ry*.88
            cv2.circle(inlay, pt(px, py), 1+(k%2), 255, -1, cv2.LINE_AA)
        for side in (-1, 1):
            curl = [pt(side*rx*.82, ry*.13), pt(side*rx*1.04, ry*.28), pt(side*rx*.78, ry*.45)]
            cv2.polylines(halo, [np.array(curl, np.int32)], False, 255, 1, cv2.LINE_AA)

    r = ridge.astype(np.float32)/255.0
    d = recess.astype(np.float32)/255.0
    t = teeth.astype(np.float32)/255.0
    i = inlay.astype(np.float32)/255.0
    o = halo.astype(np.float32)/255.0
    # RGB is deliberately *not* modulated by anatomy.  It only exposes the
    # independent damascene lacquer, so ordinary/light-neutral viewing has no
    # printed skull to discover.
    base = np.empty((hh, ww, 3), np.float32)
    base[:] = (.048, .069, .125)
    night = np.array((.105, .165, .274), np.float32)
    steel = np.array((.25, .38, .59), np.float32)
    pearl = np.array((.42, .54, .72), np.float32)
    base = base*(1-(pool*.39)[...,None]) + night*(pool*.39)[...,None]
    base = base*(1-(engraving*.42)[...,None]) + steel*(engraving*.42)[...,None]
    base = base*(1-(lip*.21)[...,None]) + pearl*(lip*.21)[...,None]
    base = base*(1-(scroll*.16)[...,None]) + steel*(scroll*.16)[...,None]
    base = np.clip(base * 1.42 + .012, 0, 1)

    # The carrier has its own causal multistate material logic.
    metal = 112 + pool*69 + engraving*57 + lip*35 - tooth*28 + scroll*41
    rough = 151 - pool*76 - engraving*53 - lip*34 + tooth*29 - scroll*24
    coat = 136 - pool*71 - engraving*62 - lip*49 + tooth*31 - scroll*39
    # I4b: the literal red/cyan silhouette in I4a was a disguised icon.  Each
    # anatomical line now inherits one of eight 8–18px material parcels.  The
    # same ridge may be old steel, mirror nick, satin pearl, buried metal, or
    # coat-broken graphite: only their organized adjacency can disclose a skull.
    statewave = (np.sin(a*1.37 + .42*np.sin(b*.91)) + np.cos(b*1.13 - .31*np.sin(a*.67)) + 2.0) * .249
    parcel = np.clip((statewave*8).astype(np.int32), 0, 7)
    rM=np.array((178,222,164,137,232,184,210,151),np.float32); rR=np.array((56,31,92,118,24,71,48,103),np.float32); rC=np.array((62,42,95,131,29,82,66,116),np.float32)
    dM=np.array((74,101,116,83,65,124,92,108),np.float32); dR=np.array((205,181,168,218,194,155,211,176),np.float32); dC=np.array((214,185,166,224,201,157,217,179),np.float32)
    tM=np.array((151,187,139,198,128,169,145,209),np.float32); tR=np.array((99,68,122,55,136,82,107,46),np.float32); tC=np.array((74,52,111,42,124,82,105,34),np.float32)
    oM=np.array((103,134,87,151,116,97,143,122),np.float32); oR=np.array((159,131,181,118,147,171,109,142),np.float32); oC=np.array((187,149,210,131,171,199,123,155),np.float32)
    iM=np.array((213,241,193,222,235,186,225,202),np.float32); iR=np.array((39,21,63,46,28,78,35,57),np.float32); iC=np.array((58,18,96,42,26,111,65,79),np.float32)
    # I4c: relief must be discovered as a *density of material events*, not
    # drawn as a high-contrast decal in the literal Combined proof.  Blend each
    # role with its surrounding damascene state; fine parcel variation remains
    # intact so light can still separate the adjacent physical responses.
    def blend(field, target, amount):
        return field*(1.0-amount) + target[parcel]*amount
    dm = .40*d; rm = .52*r; tm = .46*t; om = .34*o; im = .58*i
    metal = blend(metal,dM,dm); rough=blend(rough,dR,dm); coat=blend(coat,dC,dm)
    metal = blend(metal,rM,rm); rough=blend(rough,rR,rm); coat=blend(coat,rC,rm)
    metal = blend(metal,tM,tm); rough=blend(rough,tR,tm); coat=blend(coat,tC,tm)
    metal = blend(metal,oM,om); rough=blend(rough,oR,om); coat=blend(coat,oC,om)
    metal = blend(metal,iM,im); rough=blend(rough,iR,im); coat=blend(coat,iC,im)

    if (hh, ww) != (h, w):
        base = _up(base, w, h)
        metal, rough, coat = (_up(z, w, h) for z in (metal, rough, coat))
    value = (np.clip(base, 0, 1).astype(np.float32),
             np.stack((np.clip(metal, 0, 255), np.clip(rough, 15, 255), np.clip(coat, 16, 255)), axis=2).astype(np.uint8))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 2:
            _CACHE.popitem(last=False)
    return value


def paint_veiled_skull_i4(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _arrays(shape, seed)
    src = np.asarray(paint, np.float32)[..., :3]
    if src.max(initial=0) > 1.5: src /= 255.0
    coverage = np.asarray(mask, np.float32); coverage = coverage[..., 0] if coverage.ndim == 3 else coverage
    return np.clip(src*(1-np.clip(coverage,0,1)[...,None]*pm) + authored*(np.clip(coverage,0,1)[...,None]*pm), 0, 1).astype(np.float32)


def spec_veiled_skull_i4(shape, seed, sm, base_m, base_r):
    del sm, base_m, base_r
    return _arrays(shape, seed)[1]
