"""FRACTURED HOUDINI H1-I8 — Veiled Skull / mercury facet velvet.

New carrier after the rejected I6 enamel and I7 rosette branches.  Applies the
protected Hologram Metal lesson without copying its carrier: tiny offset
mercury facets are the normal whole-car surface; hidden skulls only redirect
their complete M/Rough/Cc state choreography.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock();_WORK=640
def _f(a):return a-np.floor(a)
def _up(a,w,h):return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)
def _hash(x,y,s):return _f(np.sin(x*12.9898+y*78.233+s*.021)*43758.5453)

def _points(rng,w,h,n):
    out=[]
    for _ in range(n*190):
        if len(out)>=n:break
        p=(float(rng.uniform(-32,w+32)),float(rng.uniform(-40,h+40)))
        if all((p[0]-q[0])**2+(p[1]-q[1])**2>71**2 for q in out):out.append(p)
    return out

def _arrays(shape,seed):
    h,w=map(int,shape);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
    sc=min(1.,_WORK/max(h,w));hh,ww=max(160,round(h*sc)),max(160,round(w*sc))
    yy,xx=np.mgrid[:hh,:ww].astype(np.float32);rng=np.random.default_rng(int(seed)^0x81FACC)
    # Offset, warped 8–24px facet language.  The three geometric families are
    # related but never a single square/checker wallpaper.
    u=.824*xx+.566*yy+1.7*np.sin(yy/17.0);v=-.566*xx+.824*yy+1.3*np.sin(xx/19.0)
    pitch=5.4;fu,fv=np.mod(u/pitch,1.),np.mod(v/pitch,1.);gx,gy=np.floor(u/pitch),np.floor(v/pitch)
    edge=np.clip((.105-np.minimum.reduce((fu,1-fu,fv,1-fv)))/.105,0,1)
    diagonal=np.clip((.082-np.abs(fu-fv))/.082,0,1)
    facet=np.clip((.145-np.abs(fu+fv-1))/.145,0,1)
    inset=np.clip(.40-np.sqrt((fu-.5)**2+(fv-.5)**2),0,1)*2.5*(1-edge)
    # fine chipped diffraction, attached to facets rather than scatter
    code=np.mod(17*gx.astype(np.int32)+31*gy.astype(np.int32)+3*(gx*gy).astype(np.int32)+int(seed),16)
    fleck=((np.mod(code+np.floor(fu*3).astype(np.int32)+5*np.floor(fv*3).astype(np.int32),7)==0).astype(np.float32))*inset

    skull=np.zeros((hh,ww),np.float32); hollow=np.zeros_like(skull); jaw=np.zeros_like(skull); halo=np.zeros_like(skull); engrave=np.zeros_like(skull)
    for cx,cy in _points(rng,ww,hh,max(18,int(hh*ww/35000))):
        rx,ry=rng.uniform(20,29),rng.uniform(27,37);a=rng.uniform(-.34,.34);ca,sa=np.cos(a),np.sin(a)
        X=((xx-cx)*ca+(yy-cy)*sa)/rx;Y=(-(xx-cx)*sa+(yy-cy)*ca)/ry
        crown=np.clip(1-(X*X+((Y+.13)/.87)**2),0,1);lower=np.clip(1-((X/.60)**2+((Y-.55)/.35)**2),0,1)
        skull=np.maximum(skull,np.maximum(crown,lower))
        eyes=np.maximum(np.clip(1-(((X+.31)/.28)**2+((Y+.04)/.21)**2),0,1),np.clip(1-(((X-.31)/.28)**2+((Y+.04)/.21)**2),0,1))
        nose=np.clip(1-((X/.12)**2+((Y-.28)/.17)**2),0,1);hollow=np.maximum(hollow,np.maximum(eyes,nose*.72))
        jaw=np.maximum(jaw,lower*np.clip((Y-.29)*2.7,0,1));rr=np.sqrt(X*X+Y*Y);halo=np.maximum(halo,np.clip(.09-np.abs(rr-1.05),0,1)*10)
        th=np.arctan2(Y,X);engrave=np.maximum(engrave,crown*np.clip(.075-np.abs(np.sin(th*5+rr*18)),0,1)*8.0)

    # Visible carrier is independent mercury velvet—dark graphite facets,
    # violet-black insets, restrained silver catches. No skull values here.
    base=np.broadcast_to(np.array((.034,.041,.070),np.float32),(hh,ww,3)).copy()
    violet=np.array((.115,.078,.172),np.float32);steel=np.array((.22,.27,.39),np.float32);silver=np.array((.42,.43,.54),np.float32)
    base=base*(1-(inset*.37)[...,None])+violet*(inset*.37)[...,None]
    base=base*(1-(edge*.28)[...,None])+steel*(edge*.28)[...,None]
    base=base*(1-(diagonal*.20)[...,None])+violet*(diagonal*.20)[...,None]
    base=base*(1-(facet*.16)[...,None])+steel*(facet*.16)[...,None]
    base=base*(1-(fleck*.30)[...,None])+silver*(fleck*.30)[...,None]

    # Eight complete, adjacent material states.  State shifts inside a skull
    # make local facets light differently; they do not add any art to RGB.
    state=np.mod(code+(diagonal>.35).astype(np.int32)+2*(inset>.55).astype(np.int32),4)
    hot=4+np.mod(code+(edge>.35).astype(np.int32),3);cold=np.mod(code,2)
    secret=np.where(hollow>.20,cold,hot);secret=np.where(jaw>.18,np.minimum(hot+1,7),secret)
    secret=np.where(halo>.18,3+np.mod(code,3),secret);secret=np.where(engrave>.20,4+np.mod(code,3),secret)
    # I8e: do not substitute a solid pictogram.  Only an irregular subset of
    # existing facets changes state inside each skull, so the discovery is an
    # optical population effect rather than a printed silhouette.
    reveal=(skull>.09)&(np.mod(code+np.floor(fu*3).astype(np.int32)+2*np.floor(fv*3).astype(np.int32),3)!=0)
    state=np.where(reveal,secret,state)
    M=np.array((150,170,190,210,228,246,232,185),np.float32)
    R=np.array((155,130,105,80,60,34,73,112),np.float32)
    C=np.array((190,200,210,220,232,246,238,198),np.float32)
    metal=M[state]+edge*44+diagonal*25+fleck*20-inset*12
    rough=R[state]-edge*46-diagonal*24-fleck*27+inset*14
    coat=C[state]-edge*43-diagonal*20-fleck*17+inset*18
    metal+=skull*12-hollow*21+jaw*8+halo*8+engrave*9
    rough+=-skull*14+hollow*28-jaw*9+halo*5-engrave*10
    coat+=-skull*16+hollow*26-jaw*10+halo*7-engrave*11
    if (hh,ww)!=(h,w):base=_up(base,w,h);metal,rough,coat=(_up(q,w,h) for q in (metal,rough,coat))
    val=(np.clip(base,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=val
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return val

def paint_veiled_skull_i8(paint,shape,mask,seed,pm,bb):
    del bb
    art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-np.clip(m,0,1)[...,None]*pm)+art*(np.clip(m,0,1)[...,None]*pm),0,1).astype(np.float32)
def spec_veiled_skull_i8(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    return _arrays(shape,seed)[1]
