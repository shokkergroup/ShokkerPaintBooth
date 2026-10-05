"""Jukebox Neon I2 — continuous 1950s acrylic/chrome bezel material.

SPB-105 / SH-JUKEBOX-NEON-I2 / 2026-08-30.  Owner native-scale audit found
I1's rails left too much inert black. I2 tightens the same 8–32px chrome,
coral, cyan, and ivory rail geometry while deepening the visible acrylic.
This is a material-density correction—not a recolour, grid, or macro icon.
Direct 2048² I2 audit: 0.536s; M/R/Cc std 65.3/57.7/63.0.  The legacy
adapter has no entry for this base, so no M7 score is fabricated.
chrome, coral, cyan, and ivory rails all follow the same curved jukebox-glass
geometry.  There are no checker cells, icons, or scattered particles.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _band(z, width):
    f = z - np.floor(z)
    return np.clip((width - np.minimum(f, 1-f)) / width, 0, 1)


def _arrays(shape, seed):
    h,w=int(shape[0]),int(shape[1]); key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    q=min(1.,1024./max(h,w)); hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32); u=x/q; v=y/q
    # Three off-canvas bezel centres yield a continuous, asymmetrical family of
    # arcs. Spacing/rail widths are native pixels, never macro fill regions.
    d1=np.sqrt((u+310)**2+(v-680)**2); d2=np.sqrt((u-1780)**2+(v+240)**2); d3=np.sqrt((u-1030)**2+(v-2230)**2)
    flow=.64*d1+.27*d2+.17*d3+5.5*np.sin(v/127)+3.2*np.cos(u/83)
    # I2 closes I1's wasted whole-car voids: the same curved bezel family is
    # 35–45% tighter, while every individual rail/glint remains 2–24px.
    rail1=_band(flow/14.5,.125); rail2=_band((flow+7.5)/23.0,.090); rail3=_band((flow-5.0)/38.0,.062)
    # Cross-polish marks are short, flow-bound glints rather than a second grid.
    gleam=rail1*np.power(.5+.5*np.sin((.11*u-.07*v)+.6*np.sin(v/61)),10)
    lip=rail2*np.power(.5+.5*np.cos((.08*u+.12*v)+.7*np.sin(u/71)),7)
    glass=np.clip(.5+.5*np.sin(flow/94.0+.4*np.sin((u-v)/221)),0,1)
    body=np.stack((.032+.043*glass,.035+.036*glass,.066+.095*glass),2).astype(np.float32)
    coral=np.array((.96,.12,.10),np.float32); cyan=np.array((.05,.82,.91),np.float32); ivory=np.array((1.,.71,.28),np.float32); chrome=np.array((.62,.76,.82),np.float32)
    paint=body
    paint=paint*(1-rail1[...,None]*.82)+coral*(rail1[...,None]*.82)
    paint=paint*(1-rail2[...,None]*.78)+cyan*(rail2[...,None]*.78)
    paint=paint*(1-rail3[...,None]*.70)+ivory*(rail3[...,None]*.70)
    paint=paint*(1-gleam[...,None]*.86)+chrome*(gleam[...,None]*.86)
    paint=paint*(1-lip[...,None]*.45)+ivory*(lip[...,None]*.45)
    # Each visible rail/glass state owns its own M/R/Cc response.
    M=24+58*glass+155*rail1+186*rail2+205*rail3+71*gleam+34*lip
    R=226-44*glass-118*rail1-156*rail2-178*rail3-104*gleam-61*lip
    C=18+66*glass+132*rail1+171*rail2+195*rail3+89*gleam+46*lip
    if (hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_jukebox_neon(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_jukebox_neon(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
