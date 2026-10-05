"""Hippie Rainbow I1 — hand-dyed macramé, wax knots and pearl thread.

SPB-105 / GV-HIPPIE-RAINBOW-I1, 2026-08-30.  Replaces the literal stripe
card after live picker review.  Interwoven 8–24px cords, 6–12px crossing
knots, fine wax halos and pearl threads make a 1960s/70s hand-dyed textile;
each material state drives its own M/R/Cc response.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _band(z,width):
    z=np.abs(np.mod(z,1.)-.5)*2.
    return np.clip((width-z)/(width*.42),0,1)


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);u,v=x/q,y/q
    # Two deliberately different braid flows.  Warps are native 8–24px
    # motion, preventing a simple lattice while retaining textile continuity.
    a=(.69*u+.71*v+7*np.sin(v/37)+4*np.cos((u+v)/83))/28.
    b=(-.79*u+.61*v+6*np.sin(u/43)-3*np.cos((u-v)/71))/25.
    cord_a=_band(a,.48);cord_b=_band(b,.42)
    # Each cord gets a narrow inner dyed filament plus a waxed outside lip.
    fila=_band(a+.19,.19)*cord_a;filb=_band(b-.16,.17)*cord_b
    lipa=np.clip(cord_a-fila,0,1);lipb=np.clip(cord_b-filb,0,1)
    crossing=cord_a*cord_b
    knot=np.power(crossing,1.45)*np.clip(.35+.65*np.sin((u+v)/17)**2,0,1)
    pearl=np.power(.5+.5*np.sin((u-v)/10.5+.4*np.sin(v/31)),13)*(fila+filb>0).astype(np.float32)
    # Batik color states vary per braided cell rather than in global bands.
    ia=np.floor(a).astype(np.int32);ib=np.floor(b).astype(np.int32)
    state=np.mod(ia*17+ib*31+(ia^ib)*5+int(seed),8).astype(np.int32)
    palette=np.array(((.91,.055,.26),(.98,.42,.04),(.93,.80,.04),(.12,.67,.36),(.03,.54,.83),(.34,.16,.78),(.72,.07,.54),(.90,.26,.49)),np.float32)
    dye=palette[state]
    ground=np.array((.050,.018,.080),np.float32)
    wax=np.array((.42,.16,.48),np.float32);thread=np.array((.72,.88,.86),np.float32)
    # Cord A lets dye lead; cord B offsets to nearby hues, so every crossing
    # presents adjacent rainbow material—not one huge rainbow gradient.
    dye_b=palette[(state+3)%8]
    paint=np.broadcast_to(ground,(hh,ww,3)).copy()
    paint=paint*(1-cord_a[...,None]*.86)+dye*(cord_a[...,None]*.86)
    paint=paint*(1-cord_b[...,None]*.66)+dye_b*(cord_b[...,None]*.66)
    paint=paint*(1-(lipa+lipb)[...,None]*.30)+wax*((lipa+lipb)[...,None]*.30)
    paint=paint*(1-knot[...,None]*.48)+thread*(knot[...,None]*.48)
    paint=paint*(1-pearl[...,None]*.70)+thread*(pearl[...,None]*.70)
    # The paint's dye/knot/wax categories are the spec categories.
    s=state.astype(np.float32)
    M=22+cord_a*(47+s*13)+cord_b*(31+((s+3)%8)*14)+lipa*35+lipb*39+knot*164+pearl*91
    R=226-cord_a*(65+s*7)-cord_b*(51+((s+3)%8)*7)-lipa*37-lipb*42-knot*169-pearl*79
    C=18+cord_a*(62+s*12)+cord_b*(54+((s+3)%8)*12)+lipa*48+lipb*52+knot*172+pearl*110
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_hippie_macrame(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_hippie_macrame(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
