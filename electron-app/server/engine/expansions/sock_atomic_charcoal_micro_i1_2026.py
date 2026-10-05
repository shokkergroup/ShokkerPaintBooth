"""Atomic Charcoal Micro I1 — dense mid-century cocktail enamel.

SPB-105 / SH-ATOMIC-CHARCOAL-I1, 2026-08-30. The legacy card reads as a
small number of oversized flat atomic blobs. This candidate uses 48px
compositions whose actual parts are 4–28px: charcoal enamel field, compact
nuclei, short screen-printed rays, broken chrome orbits, satellites, pins,
and attached pearlescent glints. Every material channel follows those parts.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _ad(a,b): return np.angle(np.exp(1j*(a-b)))


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);X,Y=x/q,y/q
    # 48px composition, but no global stationary grid: each station is gently
    # sheared before its own 4–28px atomic components are constructed.
    cell=48.;gx=X+1.7*np.sin(Y/103.)+.65*np.sin(Y/31.);gy=Y+1.3*np.cos(X/97.)+.55*np.sin(X/37.)
    ix,iy=np.floor(gx/cell).astype(np.int32),np.floor(gy/cell).astype(np.int32)
    fx=np.mod(gx,cell)-24.;fy=np.mod(gy,cell)-24.
    state=np.mod(ix*13+iy*29+(ix^iy)*7+int(seed),6).astype(np.int32)
    ang=(state.astype(np.float32)-2.5)*.34;ca,sa=np.cos(ang),np.sin(ang);u=fx*ca-fy*sa;v=fx*sa+fy*ca
    r=np.hypot(u,v);th=np.arctan2(v,u)
    nucleus=np.clip(1-r/5.4,0,1)
    # Five finite 4–24px rays: real marks, no radial burst wallpaper.
    rays=np.zeros_like(r)
    for k in range(5):
        a=-.34+k*1.256+(state%2)*.14
        rays=np.maximum(rays,np.exp(-np.square(_ad(th,a)/.075))*np.clip((23-r)/5,0,1)*np.clip((r-4.5)/3,0,1))
    # Two clipped 2–4px chrome orbit sections plus a 4–7px satellite suite.
    ell=np.sqrt((u/18.)**2+(v/8.)**2);orbit=np.exp(-np.square((ell-1)/.105))*np.clip(.30+.70*np.cos(th-.52),0,1)
    ell2=np.sqrt((u/8.)**2+(v/17.)**2);orbit2=np.exp(-np.square((ell2-1)/.085))*np.clip(.25+.75*np.cos(th+1.15),0,1)
    shift=(state.astype(np.float32)-2.5)*1.1
    def dot(cx,cy,rr):return np.clip(1-np.hypot(u-cx,v-cy)/rr,0,1)
    sat=np.maximum.reduce((dot(16+shift,6,4.8),dot(-16,9-shift,4.0),dot(5,17+shift,3.6),dot(-5,-18,3.3)))
    pin=np.maximum.reduce((dot(16+shift,6,1.55),dot(-16,9-shift,1.35),dot(5,17+shift,1.15)))
    # A local 3–7px enamel halo belongs to the nucleus, not a background grid.
    halo=np.exp(-np.square((r-10.5)/1.8))*np.clip(.40+.60*np.cos(3*th+.4),0,1)
    charcoal=np.array((.018,.026,.034),np.float32);slate=np.array((.055,.078,.090),np.float32)
    coral=np.array((.91,.20,.11),np.float32);aqua=np.array((.035,.68,.70),np.float32)
    mustard=np.array((.90,.63,.13),np.float32);pearl=np.array((.84,.86,.75),np.float32);chrome=np.array((.62,.78,.80),np.float32)
    lot=.5+.5*np.sin((X+1.6*Y)/83.+.28*np.sin(Y/21.))
    paint=charcoal*(.83+.11*lot[...,None])+slate*(.06+.025*(1-lot[...,None]))
    ray_col=np.where(((state[...,None]%3)==0),coral,np.where(((state[...,None]%3)==1),aqua,mustard))
    paint=paint*(1-halo[...,None]*.30)+slate*(halo[...,None]*.30)
    paint=paint*(1-rays[...,None]*.92)+ray_col*(rays[...,None]*.92)
    paint=paint*(1-nucleus[...,None]*.96)+coral*(nucleus[...,None]*.96)
    paint=paint*(1-orbit[...,None]*.84)+pearl*(orbit[...,None]*.84)
    paint=paint*(1-orbit2[...,None]*.82)+aqua*(orbit2[...,None]*.82)
    paint=paint*(1-sat[...,None]*.88)+mustard*(sat[...,None]*.88)
    paint=paint*(1-pin[...,None]*.97)+chrome*(pin[...,None]*.97)
    M=27+17*lot+29*halo+137*rays+174*nucleus+192*orbit+164*orbit2+129*sat+210*pin
    R=221-14*lot-25*halo-108*rays-158*nucleus-173*orbit-147*orbit2-93*sat-199*pin
    C=25+14*lot+34*halo+118*rays+134*nucleus+181*orbit+189*orbit2+116*sat+217*pin
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_atomic_charcoal_micro(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-(np.clip(m,0,1)*float(pm))[...,None])+authored*(np.clip(m,0,1)*float(pm))[...,None],0,1).astype(np.float32)


def spec_atomic_charcoal_micro(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
