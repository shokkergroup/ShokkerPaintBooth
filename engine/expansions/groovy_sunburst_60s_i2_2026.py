"""Groovy Sunburst 60s I2 — fine all-over screen-printed sun cloth.

SPB-105 / owner scale audit, 2026-08-29.  The former card was one giant
center burst.  This replacement is a period screen print: tiny sun discs,
registration rings, ray wedges, and two overprinted ray fabrics.  At 2048²,
the individual ink marks are 7–30px; no logo-sized centre exists.
"""
import numpy as np

from engine.core import get_mgrid

_CACHE = {}


def _field(shape, seed):
    key = (tuple(shape[:2]), int(seed))
    if key in _CACHE:
        return _CACHE[key]
    h, w = shape[:2]
    y, x = (a.astype(np.float32) for a in get_mgrid((h, w)))
    per = max(h, w) / 19.2
    ix, iy = np.floor(x / per).astype(np.int32), np.floor(y / per).astype(np.int32)
    # Staggered print stations break the old wallpaper-grid cadence without
    # introducing random flecks; each station is a deliberately offset sun.
    station = ((ix * 1664525 + iy * 1013904223 + int(seed)) & 0x7fffffff).astype(np.float32) / 2147483647.
    ox = (station - .5) * .16 + (((iy & 1).astype(np.float32)) - .5) * .18
    oy = (.5 - station) * .10
    u, v = (x / per) % 1.0 - .5 - ox, (y / per) % 1.0 - .5 - oy
    rad = np.sqrt(u*u + v*v)
    ang = np.arctan2(v, u)
    # 14 narrow, short ray wedges around a 12–15px disc, with one tiny
    # registration ring.  Each is a real silkscreen component.
    ray_phase = .5 + .5*np.cos(14.0*ang + station*4.7)
    rays = np.power(ray_phase, 8.0) * np.clip((.315-rad)/.125, 0, 1) * np.clip((rad-.105)/.050, 0, 1)
    disc = np.clip((.118-rad)/.040, 0, 1)
    ring = np.exp(-((rad-.145)/.020)**2)
    dot = np.clip((.040 - np.sqrt((u-.184)**2+(v+.080)**2))/.020,0,1)
    # Two fine fabrics give every nominally empty region purpose: 8–18px
    # overprinted diagonal rays, not generic grain or a single field.
    weave_a = .5+.5*np.sin(2*np.pi*(5.8*u+7.4*v+.15*np.sin(8*v)))
    weave_b = .5+.5*np.sin(2*np.pi*(8.7*u-4.9*v+.12*np.sin(7*u)))
    silk_a, silk_b = np.power(weave_a, 18.0), np.power(weave_b, 21.0)
    _CACHE[key] = tuple(a.astype(np.float32) for a in (disc, rays, ring, dot, silk_a, silk_b, weave_a, weave_b))
    if len(_CACHE) > 18: _CACHE.pop(next(iter(_CACHE)))
    return _CACHE[key]


def _mix(base, color, alpha):
    a = np.clip(alpha, 0, 1)[:, :, None]
    return base*(1-a) + np.asarray(color, np.float32)[None,None,:]*a


def _apply(paint, mask, color):
    if mask is not None and mask.size and float(mask.min()) >= .999:
        return np.ascontiguousarray(color, dtype=np.float32)
    if paint.ndim == 3 and paint.shape[2] > 3: paint = paint[:,:,:3].copy()
    return (color*mask[:,:,None] + paint*(1-mask[:,:,None])).astype(np.float32)


def paint_sunburst_60s(paint, shape, mask, seed, pm, bb):
    del pm, bb
    disc, rays, ring, dot, silk_a, silk_b, weave_a, weave_b = _field(shape, seed)
    h,w=shape[:2]; col=np.empty((h,w,3),np.float32); col[:]=(.205,.052,.105) # oxblood ground
    col=_mix(col,(.50,.085,.17),silk_a*.52)      # scarlet underprint
    col=_mix(col,(.045,.38,.42),silk_b*.47)      # oxidized teal print
    col=_mix(col,(.93,.55,.075),rays*.92)        # mustard ray wedges
    col=_mix(col,(.98,.18,.075),disc*.95)        # hot vermilion suns
    col=_mix(col,(.96,.82,.34),ring*.86)         # slightly misregistered cream ring
    col=_mix(col,(.12,.79,.73),dot*.88)          # tiny cyan registration dot
    return _apply(paint,mask,np.clip(col,0,1))


def spec_sunburst_60s(shape, seed, sm, base_m, base_r):
    del base_m, base_r
    disc, rays, ring, dot, silk_a, silk_b, weave_a, weave_b = _field(shape, seed)
    # Separate material records: satin sun pigment, absorbent textiles, then
    # polished registration edge.  All are pattern-bound to visible ink.
    M=18+118*weave_a+104*np.clip(.28*disc+.27*rays+.20*ring+.15*silk_a+.10*silk_b,0,1)*sm
    R=238-112*weave_b-120*np.clip(.31*disc+.24*rays+.18*silk_a+.16*silk_b+.11*ring,0,1)
    CC=14+126*(.64*weave_b+.36*weave_a)+118*np.clip(.30*ring+.25*rays+.18*silk_b+.15*disc+.12*silk_a,0,1)
    return tuple(np.clip(a,0,255).astype(np.float32) for a in (M,R,CC))
