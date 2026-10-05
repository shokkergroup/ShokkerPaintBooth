"""Soda Fountain Check I6 — fine counter enamel, soda glass and chrome.

SPB-105 / SH-SODA-CHECK-I6, 2026-08-29.  Replaces the prior 32px repeated
checker carrier after native audit.  This is a 20px enamel module with 2px
chrome joints, 8px tile-local soda glass and 3–7px ice/fizz marks.  Those
marks are anchored to physical tile states, not confetti or a recolor.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _arrays(shape, seed):
    h,w=int(shape[0]),int(shape[1]); key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    q=min(1.,1024./max(h,w)); hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32); u,v=x/q,y/q
    # Tight 20px counter-tile rhythm; the slight counter warp is deliberate
    # enamel layup variation, not a large repeating distortion.
    wx=1.1*np.sin(v/81.0)+.55*np.cos(v/39.0); wy=.9*np.sin(u/73.0)+.48*np.cos(u/29.0)
    gx,gy=u+wx,v+wy; px,py=np.mod(gx,20.),np.mod(gy,20.)
    ix,iy=np.floor(gx/20.).astype(np.int32),np.floor(gy/20.).astype(np.int32)
    edge=np.minimum.reduce((px,20-px,py,20-py))
    seam=np.clip((2.05-edge)/1.35,0,1)
    parity=((ix+iy)&1).astype(np.int32)
    state=np.mod(ix*13+iy*23+(ix^iy)*3+int(seed),8).astype(np.int32)
    cx,cy=px-10.,py-10.; radial=np.hypot(cx,cy)
    inset=np.clip(1-np.maximum(abs(cx),abs(cy))/8.8,0,1)
    # Cell-specific wet counter reflection: an 8px arc/patch, never a global
    # grid overlay. Aqua tiles get clustered fizz; cream tiles get ice shards.
    phase=np.mod(ix*7+iy*11,4).astype(np.float32)
    arc=np.clip(1-np.abs(radial-(5.7+.6*phase))/1.05,0,1)*np.clip((cy+4.5)/4.0,0,1)
    b1=np.clip(1-np.hypot(cx+4.3,cy+3.2)/2.1,0,1)
    b2=np.clip(1-np.hypot(cx-2.5,cy-1.1)/1.6,0,1)
    b3=np.clip(1-np.hypot(cx-5.2,cy+4.8)/1.05,0,1)
    fizz=np.clip(b1+b2*.8+b3*.65,0,1)
    shard=np.clip(1-(abs(cx-4.5)+abs(cy+4.0))/4.1,0,1)
    glass=(parity==1).astype(np.float32); porcelain=1-glass
    wet=arc*glass*inset; fizz=fizz*glass*inset; shard=shard*porcelain*inset

    cream=np.array((.93,.74,.48),np.float32); aqua=np.array((.035,.45,.52),np.float32)
    rose=np.array((.72,.095,.16),np.float32); cobalt=np.array((.07,.17,.38),np.float32)
    chrome=np.array((.58,.70,.74),np.float32); ice=np.array((.76,.96,.94),np.float32)
    shade=np.array((-.09,-.055,-.02,.015,.045,.075,.11,.145),np.float32)[state][...,None]
    base=np.where(glass[...,None]>0,aqua+shade*.42,cream+shade*.72)
    tint=np.where((state[...,None]&1)>0,rose,cobalt)
    tint_amount=((state%4==0)|(state%4==3)).astype(np.float32)[...,None]*.13
    paint=np.clip(base*(1-tint_amount)+tint*tint_amount,0,1)
    paint=paint*(1-wet[...,None]*.57)+ice*(wet[...,None]*.57)
    paint=paint*(1-fizz[...,None]*.70)+ice*(fizz[...,None]*.70)
    paint=paint*(1-shard[...,None]*.52)+ice*(shard[...,None]*.52)
    paint=paint*(1-seam[...,None]*.94)+chrome*(seam[...,None]*.94)

    s=state.astype(np.float32)
    M=np.where(glass>0,78+s*12,38+s*11); R=np.where(glass>0,118-s*10,208-s*9); C=np.where(glass>0,150+s*11,57+s*12)
    M=M+wet*80+fizz*108+shard*55+seam*151
    R=R-wet*64-fizz*91-shard*44-seam*166
    C=C+wet*98+fizz*105+shard*62+seam*144
    if (hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_soda_fountain_check(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_soda_fountain_check(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
