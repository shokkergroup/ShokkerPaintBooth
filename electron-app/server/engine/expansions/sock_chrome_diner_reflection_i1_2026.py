"""Chrome Diner I1 — dark stainless, soda-counter reflections and clearcoat.

SPB-105 / SH-CHROME-DINER-I1, 2026-08-29.  The old card was a soft gray
stripe with an unrelated color-map.  This carrier uses a 6–24px directional
stainless polish hierarchy plus physically narrow aqua/cherry counter
reflections.  All M/R/Cc changes are drawn from the same polish/reflection
geometry.  It is a material, not a wallpaper or scattered flake field.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _arrays(shape, seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);u,v=x/q,y/q
    # Directional stainless grain: a nested 6/11/24px polish hierarchy with
    # smooth off-axis warping, not a global checker or a big stripe graphic.
    drift=8.0*np.sin(v/173.0)+4.5*np.sin((u+v)/251.0)+2.6*np.cos(u/89.0)
    rail=.82*u+.57*v+drift
    fine=.5+.5*np.sin(rail*1.08+.35*np.sin(v/13.0))
    mid=.5+.5*np.sin(rail*.53+.58*np.sin(u/37.0))
    long=.5+.5*np.sin(rail*.205+.46*np.sin(v/71.0))
    scratch=np.power(fine,9)*(.35+.65*np.power(mid,2.1))
    polish=np.clip(.12+.20*fine+.24*mid+.30*long+.26*scratch,0,1)
    # Narrow reflected counter tubes remain 3–12px wide in native space.
    aqua=np.exp(-np.square(np.sin((rail+20*np.sin(v/131.0))/31.0))/.020)
    cherry=np.exp(-np.square(np.sin((rail-35+15*np.cos(u/157.0))/43.0))/.012)
    aqua*=.30+.70*np.power(long,2.0);cherry*=.25+.75*np.power(mid,2.0)
    # Fine pin highlights become chrome micro-grazes, not loose specks.
    pin=np.power(.5+.5*np.sin(rail*1.71+.8*np.sin((u-v)/43.0)),17)*(.2+.8*long)
    dark=np.clip(.62-.48*polish-.12*aqua-.11*cherry,0,1)
    graphite=np.array((.024,.030,.040),np.float32);steel=np.array((.40,.51,.55),np.float32)
    ice=np.array((.76,.91,.91),np.float32); cyan=np.array((.02,.63,.70),np.float32); red=np.array((.80,.045,.085),np.float32)
    paint=graphite*(1-polish[...,None]*.78)+steel*(polish[...,None]*.78)
    paint=paint*(1-aqua[...,None]*.64)+cyan*(aqua[...,None]*.64)
    paint=paint*(1-cherry[...,None]*.51)+red*(cherry[...,None]*.51)
    paint=paint*(1-pin[...,None]*.56)+ice*(pin[...,None]*.56)
    paint=np.clip(paint*(.55+.45*(1-dark[...,None])),0,1)
    # Chrome base/polish/reflection states drive all three channels together.
    M=57+126*polish+37*aqua+24*cherry+66*pin
    R=170-116*polish-58*aqua-42*cherry-82*pin
    C=43+126*polish+94*aqua+53*cherry+107*pin
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_chrome_diner_reflection(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_chrome_diner_reflection(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
