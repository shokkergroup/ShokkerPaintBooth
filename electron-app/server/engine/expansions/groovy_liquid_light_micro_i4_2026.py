"""Liquid Light I4 — fine overhead-projector dye membranes and caustics.

SPB-105 / GV-LIQUID-LIGHT-I4, 2026-08-30.  The live legacy renderer's
normalized waves accidentally made 150–300px bands.  This is an authored
native-pixel liquid-light field: 8–24px projected dye membranes, 3–8px
caustic rims, and darker projector-tray gaps.  The membrane/rim/void states
are the M/R/Cc states; there is no unrelated noise layer.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _hsv(h,s,v):
    h=np.mod(h,1.0); i=np.floor(h*6.).astype(np.int32); f=h*6.-i
    p=v*(1-s);q=v*(1-f*s);t=v*(1-(1-f)*s);i=np.mod(i,6)
    return np.stack((np.choose(i,[v,q,p,p,t,v]),np.choose(i,[t,v,v,q,p,p]),np.choose(i,[p,p,t,v,v,q])),2).astype(np.float32)


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);u,v=x/q,y/q
    # Domain warp dimensions are native px. Multiple unaligned small baths
    # form organic membranes instead of any global stripe or cell lattice.
    # I4b native-scale correction: the initial interference envelopes merged
    # into 80–200px cavities.  These three baths now turn over every 8–32px;
    # larger colour regions may organize them but never become a primitive.
    a=(u+4.2*np.sin(v/23.)+2.8*np.sin((u+v)/37.))/9.5
    b=(.53*u+.86*v+3.7*np.sin(u/27.)-2.9*np.cos(v/19.))/11.5
    c=(-.83*u+.48*v+3.1*np.sin((u-v)/31.)+1.9*np.cos(u/15.))/8.5
    f=.56*np.sin(a)+.34*np.sin(b+.72*np.sin(c))+.24*np.cos(c+.38*np.sin(a))
    f=(f+1.14)/2.28
    body=np.clip((f-.30)/.45,0,1)
    rim1=np.exp(-np.square((f-.43)/.038));rim2=np.exp(-np.square((f-.67)/.030));rim=np.clip(rim1*.78+rim2*.92,0,1)
    # Fine nearby hue populations are changes in the same oil bath, not dots.
    boil=.5+.5*np.sin(1.42*a-.83*b+.51*c)
    pool=.5+.5*np.sin(.72*a+1.16*b-.42*c)
    hue=(.74+.27*boil+.12*pool+.07*body)%1.0
    void=np.array((.025,.006,.055),np.float32)
    dye=_hsv(hue,.84,.24+.72*body)
    flare=_hsv(.49+.10*pool,.54,.96)
    hot=_hsv(.06+.08*boil,.72,.98)
    paint=void*(1-body[...,None]*.93)+dye*(body[...,None]*.93)
    paint=paint*(1-rim[...,None]*.62)+flare*(rim[...,None]*.62)
    hotmask=rim2*pool
    paint=paint*(1-hotmask[...,None]*.44)+hot*(hotmask[...,None]*.44)
    M=21+134*body+69*boil+83*rim+29*hotmask
    R=229-112*body-62*boil-149*rim-37*hotmask
    C=15+119*body+83*pool+155*rim+46*hotmask
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_liquid_light_micro(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_liquid_light_micro(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
