"""FRACTURED HOUDINI H1-I9 — Veiled Skull / compass lacquer.

Material-first replacement: the visible carrier is an original dark
compass-engraved lacquer built on Relics-style shared arc anatomy.  The skull
is absent from paint and only redirects material plates on that geometry.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
from engine.expansions import fractured_relics_2026 as _relic

_CACHE,_LOCK=OrderedDict(),RLock();_WORK=576
def _up(a,w,h):return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)
def _norm(a):
    a=np.asarray(a,np.float32);lo,hi=np.percentile(a,(1,99));return np.clip((a-lo)/max(hi-lo,1e-5),0,1)
def _points(rng,w,h,n):
    pts=[]
    for _ in range(n*190):
        if len(pts)>=n:break
        p=(float(rng.uniform(-36,w+36)),float(rng.uniform(-40,h+40)))
        if all((p[0]-q[0])**2+(p[1]-q[1])**2>70**2 for q in pts):pts.append(p)
    return pts

def _arrays(shape,seed):
    h,w=map(int,shape);key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
    sc=min(1.,_WORK/max(h,w));hh,ww=max(160,round(h*sc)),max(160,round(w*sc));rng=np.random.default_rng(int(seed)^0xC0A55)
    # I9h — Complete visible artifact: off-axis astrolabe engraving gives a
    # graceful field of fine, shared compass arcs. At final 2048² the 8.4-unit
    # construction resolves to about 30px intervals, not macro wallpaper.
    # This surface remains meaningful with every secret state switched off.
    T=_norm(_relic.g_astrolabe(max(hh,ww),int(seed),arc=8.4,fine=.14))
    if T.shape!=(hh,ww):T=cv2.resize(T,(ww,hh),interpolation=cv2.INTER_CUBIC)
    soft=cv2.GaussianBlur(T,(0,0),2.1); tooth=np.clip(T-cv2.GaussianBlur(T,(0,0),1.0),-.22,.22)
    ridge=np.clip((T-soft)*7.2,0,1);incise=np.clip((soft-T)*6.0,0,1)
    yy,xx=np.mgrid[:hh,:ww].astype(np.float32)
    drift=.5+.5*np.sin(xx/61+np.sin(yy/47)+np.cos((xx-yy)/89))

    skull=np.zeros((hh,ww),np.float32);hollow=np.zeros_like(skull);jaw=np.zeros_like(skull);halo=np.zeros_like(skull);ribs=np.zeros_like(skull)
    for cx,cy in _points(rng,ww,hh,max(18,int(hh*ww/35000))):
        rx,ry=rng.uniform(20,29),rng.uniform(27,37);a=rng.uniform(-.31,.31);ca,sa=np.cos(a),np.sin(a)
        X=((xx-cx)*ca+(yy-cy)*sa)/rx;Y=(-(xx-cx)*sa+(yy-cy)*ca)/ry
        crown=np.clip(1-(X*X+((Y+.13)/.87)**2),0,1);lower=np.clip(1-((X/.60)**2+((Y-.55)/.35)**2),0,1)
        skull=np.maximum(skull,np.maximum(crown,lower))
        eyes=np.maximum(np.clip(1-(((X+.31)/.28)**2+((Y+.04)/.21)**2),0,1),np.clip(1-(((X-.31)/.28)**2+((Y+.04)/.21)**2),0,1))
        nose=np.clip(1-((X/.12)**2+((Y-.28)/.17)**2),0,1);hollow=np.maximum(hollow,np.maximum(eyes,nose*.72))
        jaw=np.maximum(jaw,lower*np.clip((Y-.29)*2.7,0,1));rr=np.sqrt(X*X+Y*Y);halo=np.maximum(halo,np.clip(.09-np.abs(rr-1.05),0,1)*10)
        th=np.arctan2(Y,X);ribs=np.maximum(ribs,crown*np.clip(.075-np.abs(np.sin(th*5+rr*18)),0,1)*8)

    # Paint carrier: black-violet lacquer, aged indigo grooves, and restrained
    # pearl on the physical compass ridges. No skull field below.
    # I9g: the carrier must earn its place before the light trick arrives.
    # Raise contrast only along the pre-existing compass engraving; skull data
    # remains completely absent from this paint calculation.
    void=np.array((.022,.010,.058),np.float32);violet=np.array((.44,.070,.62),np.float32)
    ink=np.array((.025,.29,.56),np.float32);pearl=np.array((.76,.43,.94),np.float32)
    paint=np.broadcast_to(void,(hh,ww,3)).copy()
    paint=paint*(1-(soft*.58)[...,None])+violet*(soft*.58)[...,None]
    paint=paint*(1-(incise*.48)[...,None])+ink*(incise*.48)[...,None]
    paint=paint*(1-(ridge*.62)[...,None])+pearl*(ridge*.62)[...,None]
    paint=np.clip(paint*(.98+.25*drift[...,None])+tooth[...,None]*.28,0,1)

    # Four original artifact plates + material shoulders. The secret shifts
    # *which plate owns existing geometry*, never draws a new geometry.
    plate=np.digitize(soft,np.quantile(soft,(.25,.50,.75))).astype(np.int32)
    base=plate.copy(); hot=np.clip(base+2,0,3);cold=np.clip(base-2,0,3)
    secret=np.where(hollow>.20,cold,hot);secret=np.where(jaw>.18,np.clip(hot+1,0,3),secret)
    secret=np.where(halo>.18,np.clip(base+1,0,3),secret);secret=np.where(ribs>.20,hot,secret)
    # Only portions of the artifact's own arcs shift, so a skull is a material
    # relationship inside the ward—not an obvious uniform stamp.
    use=(skull>.09)&((ridge>.12)|(np.mod(np.floor(T*23).astype(np.int32)+np.floor(drift*7).astype(np.int32),3)!=0))
    state=np.where(use,secret,base)
    # I9e: the Combined swatch is an owner-facing artifact too. Keep all three
    # channels in a coherent smoked-sapphire family while retaining four
    # genuinely different material plate states.
    # Reserve headroom for ridge/tooth relief below; prior plates were already
    # near the 8-bit ceiling before physical detail was added.
    M=np.array((34,66,100,138),np.float32);R=np.array((70,102,132,162),np.float32);C=np.array((60,90,120,152),np.float32)
    metal=M[state]+ridge*39-incise*24+tooth*45;rough=R[state]-ridge*44+incise*35-tooth*56;coat=C[state]-ridge*42+incise*31-tooth*45
    metal+=skull*10-hollow*18+jaw*7+halo*8+ribs*9;rough+=-skull*12+hollow*24-jaw*8+halo*5-ribs*10;coat+=-skull*14+hollow*22-jaw*9+halo*7-ribs*11
    if (hh,ww)!=(h,w):paint=_up(paint,w,h);metal,rough,coat=(_up(q,w,h) for q in (metal,rough,coat))
    val=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=val
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return val

def paint_veiled_skull_i9(paint,shape,mask,seed,pm,bb):
    del bb
    art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-np.clip(m,0,1)[...,None]*pm)+art*(np.clip(m,0,1)[...,None]*pm),0,1).astype(np.float32)
def spec_veiled_skull_i9(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    return _arrays(shape,seed)[1]
