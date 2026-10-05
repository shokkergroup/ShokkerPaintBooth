"""Formica Boomerang I4 — compact nested 1950s laminate inlays.

SPB-105 / SH-FORMICA-BOOMERANG-I4, 2026-08-30.  The original I2 contained
good 1950s inlay language but its ~94px station was too large; I3d proved
that disconnected micro-icons lose material authority. I4 keeps an integrated
cluster, compresses the station to 52px, and uses 3–24px nested arcs plus
small terminals. It is a purposeful print process, not a checker wall.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _arc(u,v,offset,shift,width):
    arm=np.clip((width-np.abs(v-(.42*(u-shift)**2+offset)))/(.65*width),0,1)
    return arm*np.clip((.39-np.abs(u-shift))/.105,0,1)


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));hh,ww=max(16,round(h*q)),max(16,round(w*q))
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);X,Y=x/q,y/q
    # The 52px station is a composition. All actual arc widths/terminals are
    # native 3–24px—fine enough for the full-car carrier.
    per=52.0
    gx=X+1.0*np.sin(Y/121.)+.45*np.cos(Y/47.);gy=Y+.85*np.sin(X/109.)+.35*np.cos(X/39.)
    fx,fy=np.mod(gx/per,1.)-.5,np.mod(gy/per,1.)-.5
    ix,iy=np.floor(gx/per).astype(np.int32),np.floor(gy/per).astype(np.int32)
    parity=((ix+iy)&1).astype(np.float32);a=(parity-.5)*np.pi/2;ca,sa=np.cos(a),np.sin(a)
    u,v=fx*ca+fy*sa,-fx*sa+fy*ca
    shift=(np.mod(ix*7+iy*13+int(seed),5).astype(np.float32)-2.)*.014
    black=_arc(u,v,-.205,shift-.06,.060)
    teal=_arc(u,v,.005,shift+.06,.055)
    coral=_arc(u,v,.205,shift-.02,.051)
    brass=_arc(u,v,.325,shift+.10,.035)
    terminal=np.maximum(np.clip(1-np.hypot((u-.30)/.055,(v+.14)/.055),0,1),np.clip(1-np.hypot((u+.28)/.052,(v-.17)/.052),0,1))
    hair=np.clip((.022-np.abs(v+.33+(parity-.5)*.13))/.016,0,1)
    # No alternating square base: only a continuous parchment laminate lot.
    lot=.5+.5*np.sin((X+1.4*Y)/83.+.38*np.sin(Y/29.))
    cream=np.array((.88,.80,.65),np.float32);parchment=np.array((.72,.63,.49),np.float32)
    blackc=np.array((.035,.052,.064),np.float32);aqua=np.array((.025,.49,.55),np.float32)
    red=np.array((.88,.19,.10),np.float32);gold=np.array((.90,.65,.15),np.float32);pearl=np.array((.72,.86,.84),np.float32)
    paint=cream*(.84+.14*lot[...,None])+parchment*(.025+.025*(1-lot[...,None]))
    for field,color,amount in ((hair,parchment,.48),(black,blackc,1.0),(teal,aqua,1.0),(coral,red,1.0),(brass,gold,.93),(terminal,pearl,.82)):
        alpha=np.clip(field*amount,0,1)[...,None];paint=paint*(1-alpha)+color*alpha
    # Per-inlay material response: flat laminate, satin black, enamel aqua/
    # coral, brass terminal and pearl clearcoat. No cell-wide spec checker.
    M=42+10*lot+black*141+teal*183+coral*151+brass*194+terminal*113+hair*23
    R=205-13*lot-black*165-teal*153-coral*127-brass*181-terminal*89-hair*19
    C=35+13*lot+black*148+teal*194+coral*142+brass*170+terminal*131+hair*26
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_formica_compact_boomerang(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_formica_compact_boomerang(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
