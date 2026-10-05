"""Cinder Matrix I3 — coherent ember/graphite material choreography.

SPB-105 / IMPOSSIBLE-CINDER-I3, 2026-08-30. This applies the verified
Hologram Metal lesson without reusing its carrier: a 16px micro-cell holds
four 8px physical sub-states, while a slow selector field makes adjacent
groups travel coherently under lighting. Dark graphite, ember, cobalt and
violet are visible material populations, never independent rainbow noise.
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
    q=min(1.,1024./max(h,w));hh,ww=max(32,round(h*q)),max(32,round(w*q));y,x=np.mgrid[0:hh,0:ww].astype(np.float32)
    # 16px native carrier, four 8px-native sub-states. Gentle shear prevents
    # literal square wallpaper while retaining the hand-impossible cell logic.
    # [2026-09-02 owner: 'brightness blows up the pattern in the preview'] the live preview renders at
    # 1024 and these coordinates were absolute pixels, so every cell doubled relative to the car. Cells
    # are now authored on the 2048 reference canvas at any render size; at 2048 this is x/q exactly.
    X,Y=x*(2048./ww),y*(2048./hh);u=.87*X+.50*Y+2.4*np.sin(Y/173.)+.9*np.sin(Y/43.);v=-.50*X+.87*Y+1.8*np.sin(X/151.)+.7*np.sin(X/37.)
    tile=16.;ix=np.floor(u/tile).astype(np.int32);iy=np.floor(v/tile).astype(np.int32);fu=np.mod(u,tile)/tile;fv=np.mod(v,tile)/tile
    # Slow selector creates coherent 160–400px regions; it owns the palette
    # family, while the deterministic cell code only varies physical state.
    selector=.50+.22*np.sin(X/247.+.7*np.sin(Y/129.))+.18*np.cos(Y/181.-.5*np.sin(X/97.))+.10*np.sin((X+Y)/311.)
    region=np.clip(np.floor(selector*4),0,3).astype(np.int32)
    raw=(ix*1103515245+iy*12345+ix*iy*7919+int(seed)*113)&0x7fffffff
    cell=np.mod(raw,16).astype(np.int32);sub=((fu>=.5).astype(np.int32)+2*(fv>=.5).astype(np.int32))
    state=np.mod(cell+sub*3+region*2,16).astype(np.int32)
    # 1–2px native bevel and local diagonal in each cell: actual material
    # geometry, not a flat digital square.
    edge=np.clip((.12-np.minimum.reduce((fu,1-fu,fv,1-fv)))/.12,0,1)
    diag=np.clip((.18-np.abs(fu-fv))/ .18,0,1)
    # Cinder palette deliberately remains dark. Regional selector shifts which
    # high-state appears but never paints a smooth gradient between cells.
    graphite=np.array((.035,.047,.060),np.float32);carbon=np.array((.015,.020,.028),np.float32);ash=np.array((.105,.120,.135),np.float32)
    ember=np.array((.76,.065,.014),np.float32);cobalt=np.array((.018,.13,.38),np.float32);violet=np.array((.20,.025,.30),np.float32);brass=np.array((.48,.19,.025),np.float32);teal=np.array((.012,.22,.25),np.float32)
    palette=np.stack((graphite,carbon,cobalt,ash,graphite,violet,carbon,graphite,brass,teal,carbon,graphite,ember,violet,ash,graphite),0)
    color=palette[state]
    # Selector only selects rare adjacent heat population, creating distinct
    # dark/bright contexts that travel as coherent regions.
    heat=((region==0)&((cell%13)==0))|((region==1)&((cell%11)==1))|((region==2)&((cell%14)==2))|((region==3)&((cell%12)==3))
    color=np.where(heat[...,None],color*.38+ember*.62,color)
    paint=np.clip(color*(1-.27*edge[...,None]) + ash*(.12*diag[...,None]) + ember*(.10*heat[...,None]*diag[...,None]),0,1)
    # Cell-state ordered M/R/Cc tiers; bevel and diagonal are attached to the
    # same visible microfacet, producing sharply contrasting neighbor response.
    ml=np.array((22,36,164,58,29,151,18,47,193,177,33,67,229,143,91,54),np.float32)[state]
    rl=np.array((224,207,44,188,216,58,232,193,31,51,219,166,18,66,136,181),np.float32)[state]
    cl=np.array((18,29,201,49,24,173,15,37,185,214,26,62,235,161,93,45),np.float32)[state]
    M=ml+36*edge+23*diag+42*heat;R=rl-28*edge-31*diag-37*heat;C=cl+45*edge+52*diag+61*heat
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_impossible_cinder_matrix(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_impossible_cinder_matrix(shape,mask,seed,sm):
    del sm
    _,spec=_arrays(shape,seed);m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    out=np.empty(spec.shape[:2]+(4,),np.uint8);out[...,:3]=(spec*np.clip(m,0,1)[...,None]).astype(np.uint8);out[...,3]=(np.clip(m,0,1)*255).astype(np.uint8)
    return out
