"""IMPOSSIBLE FINISHES — non-hand-paintable material choreography.

SPB-105 / owner direction 2026-08-29: this is not a recolor or a generic
grid.  Every finish owns a visible carrier and a dense, deliberately offset
metal/rough/coat population so motion and track lighting appear to animate it.
"""

from collections import OrderedDict
from threading import RLock

import numpy as np


_CACHE, _ARRAY_CACHE, _LOCK = OrderedDict(), OrderedDict(), RLock()


def _coords(shape):
    h, w = int(shape[0]), int(shape[1])
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    return x / max(w - 1, 1) * 2 - 1, y / max(h - 1, 1) * 2 - 1


def _cinder_fields(shape, seed):
    """Dark microfacets crossed by locally offset combustion filaments."""
    h, w = int(shape[0]), int(shape[1])
    key = (h, w, int(seed))
    with _LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            _CACHE.move_to_end(key)
            return cached

    # Build the authored topology at 1024 then upscale it: the chosen density
    # still resolves as 8–32px native facets at 2048, but avoids spending the
    # entire render budget on identical per-pixel coordinate algebra.
    if max(h, w) > 1024:
        if h >= w: wh, ww = 1024, max(8, int(round(w * 1024 / h)))
        else: wh, ww = max(8, int(round(h * 1024 / w))), 1024
    else:
        wh, ww = h, w
    x, y = _coords((wh, ww))
    # Two light shears make the cells a material field rather than wallpaper.
    u = .81*x + .59*y + .026*np.sin(2*np.pi*(7*y-2*x))
    v = -.59*x + .81*y + .022*np.sin(2*np.pi*(6*x+3*y))
    density = 43.0  # ~24px native period; individual facet 8–20px.
    cu, cv = (u + 1.5) * density, (v + 1.5) * density
    ix, iy = np.floor(cu).astype(np.int32), np.floor(cv).astype(np.int32)
    fu, fv = np.mod(cu, 1.0) - .5, np.mod(cv, 1.0) - .5
    # A stable 16-state color/spec choreography, not sampled noise.
    code = np.mod(19*ix + 37*iy + 7*ix*iy, 16).astype(np.float32) / 15.0
    skew = ((5*ix + 3*iy) % 3).astype(np.float32) - 1.0
    face = np.clip((.33 - np.maximum(np.abs(fu + .19*skew*fv),
                                     np.abs(fv)*1.16)) / .070, 0, 1)
    # Combustion paths are continuous fine streamers beneath the same tiles.
    flame_axis = v + .090*np.sin(2.7*u) + .026*np.sin(13*u)
    flame = np.exp(-((np.sin(2*np.pi*(3.9*flame_axis + .28*np.sin(5*u))))/.17)**2)
    flame *= .42 + .58*(.5 + .5*np.sin(2*np.pi*(2.1*u - .9*v)))
    seam = np.clip((.39 - np.maximum(np.abs(fu - .075), np.abs(fv + .040)*1.16))/.050,0,1)
    if (wh, ww) != (h, w):
        import cv2
        def up(a): return cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        face, code, flame, seam = up(face), up(code), up(flame), up(seam)
    value = (face.astype(np.float32), code.astype(np.float32), flame.astype(np.float32), seam.astype(np.float32))
    with _LOCK:
        _CACHE[key] = value
        while len(_CACHE) > 3: _CACHE.popitem(last=False)
    return value


def _cinder_arrays(shape, seed):
    key = (int(shape[0]), int(shape[1]), int(seed))
    with _LOCK:
        cached = _ARRAY_CACHE.get(key)
        if cached is not None:
            _ARRAY_CACHE.move_to_end(key)
            return cached
    face, code, flame, seam = _cinder_fields(shape, seed)
    # Charcoal first.  Most facets stay physically quiet; sparse adjacent
    # populations flare cyan, ember and violet so changing highlights scan.
    dark = np.array([.010, .016, .023], np.float32)
    graphite = np.array([.075, .095, .115], np.float32)
    ember = np.array([1.00, .115, .018], np.float32)
    cyan = np.array([.020, .78, .88], np.float32)
    violet = np.array([.43, .08, .88], np.float32)
    tone = np.zeros(face.shape + (3,), np.float32)
    tone[:] = dark
    body = graphite[None,None,:] * (.45 + .55*code[:,:,None])
    tone = tone*(1-face[:,:,None]) + body*face[:,:,None]
    # Tile-local rare-event hues: hard neighbors are intentionally different.
    cool = (code > .69).astype(np.float32) * face
    purple = ((code > .38) & (code < .56)).astype(np.float32) * face
    hot = np.clip(flame*(.20+.80*face),0,1)
    tone = tone*(1-cool[:,:,None]*.48) + cyan[None,None,:]*(cool[:,:,None]*.48)
    tone = tone*(1-purple[:,:,None]*.36) + violet[None,None,:]*(purple[:,:,None]*.36)
    tone = tone*(1-hot[:,:,None]*.72) + ember[None,None,:]*(hot[:,:,None]*.72)
    tone = np.clip(tone + seam[:,:,None]*np.array([.17,.22,.27],np.float32),0,1)
    # 16 neighboring spec strata, independently ordered across channels.
    state = np.floor(code*15.999).astype(np.int32)
    m_levels=np.array((18,34,57,79,103,126,151,174,196,218,236,54,91,143,189,248),np.uint8)
    r_levels=np.array((216,188,164,139,112,86,63,44,31,22,18,174,97,55,126,28),np.uint8)
    c_levels=np.array((18,33,49,67,86,107,129,151,174,198,226,71,118,163,207,244),np.uint8)
    M=m_levels[state].astype(np.float32); R=r_levels[state].astype(np.float32); C=c_levels[state].astype(np.float32)
    M=np.clip(M + 46*hot + 28*seam,0,255)
    R=np.clip(R - 64*hot + 34*(1-face),0,255)
    C=np.clip(C + 72*hot + 36*seam,0,255)
    value = (tone.astype(np.float32), np.stack((M,R,C),axis=2).astype(np.uint8))
    with _LOCK:
        _ARRAY_CACHE[key] = value
        while len(_ARRAY_CACHE) > 2: _ARRAY_CACHE.popitem(last=False)
    return value


def paint_impossible_cinder_pulse(paint, shape, mask, seed, pm, bb):
    del bb
    authored, _ = _cinder_arrays(shape, seed)
    src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.0
    m=np.asarray(mask,np.float32)
    if m.ndim==3: m=m[...,0]
    if m.shape != authored.shape[:2]:
        raise ValueError('mask shape must match Cinder Pulse render shape')
    mix=(np.clip(m,0,1)*float(pm))[:,:,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_impossible_cinder_pulse(shape, mask, seed, sm):
    del sm
    _, spec=_cinder_arrays(shape, seed)
    m=np.asarray(mask,np.float32)
    if m.ndim==3: m=m[...,0]
    if m.shape != spec.shape[:2]:
        raise ValueError('mask shape must match Cinder Pulse render shape')
    out=np.empty(spec.shape[:2]+(4,),np.uint8)
    out[...,:3]=(spec.astype(np.float32)*np.clip(m,0,1)[:,:,None]).astype(np.uint8)
    out[...,3]=(np.clip(m,0,1)*255).astype(np.uint8)
    return out


def _prism_matrix_arrays(shape, seed):
    """Dark tiled diffraction field; each native 12–18px tile owns a state."""
    h, w = int(shape[0]), int(shape[1])
    key = ("prism", h, w, int(seed))
    with _LOCK:
        cached = _ARRAY_CACHE.get(key)
        if cached is not None:
            _ARRAY_CACHE.move_to_end(key)
            return cached
    # Work at 1024 but preserve a 14px native tile after the final resize.
    q = min(1.0, 1024.0 / float(max(h, w)))
    wh, ww = max(8, int(round(h*q))), max(8, int(round(w*q)))
    y, x = np.mgrid[0:wh, 0:ww].astype(np.float32)
    # Micro-squares are subtly skewed in two directions; this is deliberate
    # diffraction construction rather than a generic checkerboard.
    u=x+.17*y+.72*np.sin(y*.20); v=y-.11*x+.58*np.sin(x*.23)
    tile=14.0*q
    ix=np.floor(u/tile).astype(np.int32); iy=np.floor(v/tile).astype(np.int32)
    fu=np.mod(u,tile)/tile; fv=np.mod(v,tile)/tile
    raw=(ix*1103515245 + iy*12345 + ix*iy*7919 + int(seed)*97) & 0x7fffffff
    state=np.mod(raw,32).astype(np.int32)
    hue=np.mod(state*0.61803398875 + .071*ix - .047*iy,1.0).astype(np.float32)
    # The gray majority has only rare chromatic events. Neighbor phases stay
    # intentionally discontinuous so the car scans under moving highlights.
    event=((state%7)==0)|((state%11)==3)|((state%13)==5)
    bright=np.where(event,.72+.26*((state%5)/4.0),.10+.20*((state%6)/5.0)).astype(np.float32)
    cr=.5+.5*np.cos(2*np.pi*hue)
    cg=.5+.5*np.cos(2*np.pi*(hue-.3333333))
    cb=.5+.5*np.cos(2*np.pi*(hue-.6666667))
    color=np.stack((cr,cg,cb),2).astype(np.float32)
    gray=(.065+.095*((state%9)/8.0)).astype(np.float32)
    paint=color*bright[...,None]*event[...,None]+gray[...,None]*(~event)[...,None]
    # Tile-local bevel and a 4px diagonal microfacet give every square internal
    # geometry, avoiding flat color stamps even before spec response is seen.
    edge=np.clip((.15-np.minimum.reduce((fu,1-fu,fv,1-fv)))/.15,0,1).astype(np.float32)
    diag=np.clip((.13-np.abs(fu-fv))/ .13,0,1).astype(np.float32)
    paint=np.clip(paint*(1-.34*edge[...,None]) + (.18+.35*event[...,None])*(.18*diag[...,None]),0,1)
    mlevels=np.array((18,31,46,62,79,97,116,137,159,182,205,229,247,54,87,126,
                      171,214,241,36,68,103,144,193,232,28,59,92,133,176,221,255),np.float32)
    rlevels=np.array((229,207,184,162,141,118,95,74,56,40,27,18,11,194,151,109,
                      65,31,16,218,174,132,88,48,23,201,158,119,79,45,20,8),np.float32)
    clevels=np.array((14,29,46,65,85,106,129,153,178,204,229,247,36,72,111,151,
                      192,229,253,22,54,91,135,181,221,43,81,124,169,211,240,255),np.float32)
    M=mlevels[state]+45*diag+29*edge
    R=rlevels[state]-37*diag+26*(1-edge)
    C=clevels[state]+62*diag+21*edge
    if (wh,ww)!=(h,w):
        import cv2
        def up(a): return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint); M=up(M); R=up(R); C=up(C)
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _ARRAY_CACHE[key]=value
        while len(_ARRAY_CACHE)>3: _ARRAY_CACHE.popitem(last=False)
    return value


def paint_impossible_prism_matrix(paint, shape, mask, seed, pm, bb):
    del bb
    authored,_=_prism_matrix_arrays(shape,seed)
    src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.0
    m=np.asarray(mask,np.float32)
    if m.ndim==3:m=m[...,0]
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_impossible_prism_matrix(shape, mask, seed, sm):
    del sm
    _,spec=_prism_matrix_arrays(shape,seed)
    m=np.asarray(mask,np.float32)
    if m.ndim==3:m=m[...,0]
    out=np.empty(spec.shape[:2]+(4,),np.uint8)
    out[...,:3]=(spec.astype(np.float32)*np.clip(m,0,1)[...,None]).astype(np.uint8)
    out[...,3]=(np.clip(m,0,1)*255).astype(np.uint8)
    return out


LIVE_PAIRS={
    'impossible_cinder_pulse': (spec_impossible_cinder_pulse, paint_impossible_cinder_pulse),
}


def install_into_engine(mono_reg, base_reg=None, fusion_reg=None):
    del base_reg, fusion_reg
    mono_reg.update(LIVE_PAIRS)
    return 'impossible-finishes-2026: 1 hero material live'
