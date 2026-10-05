"""Hologram Noir I1 — graphite diffraction lattice with restrained prism travel.

Owner Impossible-finishes direction, 2026-08-29. Inspired by the lighting
lesson of protected Hologram Metal, but a separate dark material: continuous
lattice hierarchy first, sparse optical colour second, per-tile M/R/Cc always.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()

def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
    q=min(1.,1024./max(h,w));wh,ww=max(8,int(round(h*q))),max(8,int(round(w*q)))
    y,x=np.mgrid[0:wh,0:ww].astype(np.float32);u=.822*x+.570*y;v=-.570*x+.822*y
    side=16*q;fu=np.mod(u,side)/side;fv=np.mod(v,side)/side;ix=np.floor(u/side).astype(np.int32);iy=np.floor(v/side).astype(np.int32)
    # 8–12px native cross-hatched prism rails make one connected hierarchy.
    grid=np.clip((.165-np.minimum.reduce((fu,1-fu,fv,1-fv)))/.165,0,1)
    diag=np.clip((.105-np.abs(fu-fv))/ .105,0,1)
    facet=np.clip((.17-np.abs(fu+fv-1))/ .17,0,1)
    # Broad optical flow gives the lattice its changing colour language; no
    # isolated tile is allowed to become a free coloured dot.
    travel=.5+.5*np.sin((.019*u-.014*v)/q+.42*np.sin(.011*v/q))
    travel=.55*travel+.45*(.5+.5*np.sin((.013*u+.024*v)/q))
    hue=.57+.18*np.sin((.009*u+.017*v)/q)+.09*np.sin(.027*u/q)
    rr=.5+.5*np.cos(2*np.pi*hue);gg=.5+.5*np.cos(2*np.pi*(hue-.333));bb=.5+.5*np.cos(2*np.pi*(hue-.667))
    optic=np.stack((rr,gg,bb),2).astype(np.float32)
    graphite=.020+.080*(.5+.5*np.sin((.12*u-.08*v)/q))
    paint=np.repeat(graphite[...,None],3,axis=2)
    # Colour stays on rails and a very restrained adjacent glass shoulder;
    # it is a continuous response to the lattice, never RGB confetti.
    rail=np.clip(.74*grid+.26*diag,0,1)
    paint=paint*(1-rail[...,None]*.56)+optic*(rail[...,None]*(.15+.28*travel[...,None]))
    paint=paint*(1-facet[...,None]*.11)+np.array((.22,.25,.28),np.float32)*(facet[...,None]*.11)
    code=np.mod(23*ix+41*iy+5*ix*iy+int(seed),16).astype(np.int32)
    m=np.array((22,41,63,88,116,145,175,204,232,252,57,97,136,181,218,242),np.float32)[code]
    r=np.array((229,205,180,155,130,104,79,57,39,21,190,148,111,73,46,27),np.float32)[code]
    c=np.array((16,31,50,72,97,125,155,186,217,244,62,101,143,186,224,255),np.float32)[code]
    M=m+48*grid+31*diag;R=r-38*grid+24*(1-facet);C=c+64*grid+36*diag
    if (wh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value

def paint_impossible_hologram_noir(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)

def spec_impossible_hologram_noir(shape,mask,seed,sm):
    del sm
    _,spec=_arrays(shape,seed);m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;out=np.empty(spec.shape[:2]+(4,),np.uint8);out[...,:3]=(spec.astype(np.float32)*np.clip(m,0,1)[...,None]).astype(np.uint8);out[...,3]=(np.clip(m,0,1)*255).astype(np.uint8);return out
