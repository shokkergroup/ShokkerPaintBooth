"""Tie-Dye Spiral I2 — dense late-1960s wax-resist dye spiral.

SPB-105 / GV-TIE-DYE-SPIRAL-I2, 2026-08-30. The live card's giant flat
concentric rings waste a whole-car canvas. I2 retains one recognizable
spiral-dye action but builds it from 5–28px dye bands, 2–7px wax-resist
boundaries, compact pigment blooms, threadlike cracks, and pearl lips.
M/R/Cc derives from each visible dye/wax/lacquer component.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);X,Y=x/q,y/q
    # One offset hand-twisted spiral. At any radius its physical dye lanes are
    # 5–28px, but their flow has no tiled station or vertical stripe field.
    cx=.46*w+19*np.sin(Y/193.);cy=.52*h+15*np.cos(X/217.)
    dx,dy=X-cx,Y-cy;r=np.hypot(dx,dy)+1e-3;a=np.arctan2(dy,dx)
    phase=.205*r+5.75*a+.58*np.sin(a*3.0+r*.026)+.22*np.sin((X-Y)/39.)
    wave=.5+.5*np.sin(phase)
    # Six discrete dye states are separated by narrow connected wax boundaries.
    band=np.mod(np.floor((phase+np.pi)*1.91).astype(np.int32),6)
    local=np.mod(np.floor((phase+np.pi)*5.67).astype(np.int32)+np.floor(r/19.).astype(np.int32)*3+int(seed),8)
    frac=np.mod(phase/(2*np.pi),1.);wax=np.clip((.055-np.minimum(frac,1-frac))/.040,0,1)
    lip=np.clip((.15-np.minimum(np.abs(frac-.17),np.abs(frac-.83)))/.085,0,1)*(1-wax)
    # Compact pigment pools are modulated inside the actual dye lanes, never
    # scattered over a smooth background.
    pool=np.clip(.5+.5*np.sin(r*.41+2.6*np.sin(a*4.)+.6*np.sin((X+Y)/17.)),0,1)*(1-wax)
    fiss=np.clip((.055-np.abs(np.sin(X*.41+Y*.27+1.9*np.sin(a*5.))))/.038,0,1)*(1-wax)*(.24+.76*wave)
    cyan=np.array((.03,.66,.76),np.float32);magenta=np.array((.82,.06,.50),np.float32)
    amber=np.array((.95,.48,.06),np.float32);violet=np.array((.31,.07,.65),np.float32)
    lime=np.array((.51,.76,.10),np.float32);cream=np.array((.91,.76,.39),np.float32)
    dyes=np.stack((cyan,magenta,amber,violet,lime,cream),0); color=dyes[band]
    # Band-local second ink makes the dye look flooded/handled, not a digital
    # flat ring. Choice is confined to its paint-causal lane.
    alt=dyes[(band+2+((local%3)==0).astype(np.int32))%6]
    ink=np.clip(.16+.45*pool+.18*(local%4==1),0,.72)[...,None]
    paint=color*(1-ink)+alt*ink
    waxcol=np.array((.12,.055,.13),np.float32);pearl=np.array((.90,.82,.70),np.float32)
    paint=paint*(1-wax[...,None]*.88)+waxcol*(wax[...,None]*.88)
    paint=paint*(1-lip[...,None]*.34)+pearl*(lip[...,None]*.34)
    paint=paint*(1-fiss[...,None]*.25)+waxcol*(fiss[...,None]*.25)
    # Local pigment state, wax and lacquer lips all own material state; values
    # deliberately interleave across adjacent dye bands for light travel.
    tier=(band*3+local)%8
    ml=np.array((31,58,92,127,163,196,224,248),np.float32)[tier]
    rl=np.array((218,179,137,96,62,41,24,15),np.float32)[tier]
    cl=np.array((19,43,71,106,143,178,215,246),np.float32)[tier]
    M=ml+49*pool+39*lip+96*wax+71*fiss
    R=rl-37*pool-55*lip+34*wax-21*fiss
    C=cl+64*pool+78*lip+102*wax+51*fiss
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_tie_dye_spiral_i2(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_tie_dye_spiral_i2(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
