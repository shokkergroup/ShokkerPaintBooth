"""Turquoise Metalflake I2 — deep 1950s candy enamel over real flake beds.

SPB-105 / SH-TURQUOISE-METALFLAKE-I2 / 2026-08-30.  This is not decorative
confetti: every 2–10px mark is a buried metallic platelet with an orientation,
edge, candy depth and neighbouring lacquer state. Multiple incommensurate
fine flake beds cover the canvas so it reads as custom-car metalflake at every
car angle, while a slow enamel-depth field only changes the coat above them.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _fract(z): return z - np.floor(z)


def _bed(x, y, pitch, salt):
    """One physical flake bed: jittered 2–10px plates and 1–2px rim facets."""
    gx = np.floor(x / pitch); gy = np.floor(y / pitch)
    fx = _fract(x / pitch); fy = _fract(y / pitch)
    h1 = _fract(np.sin(gx*127.1 + gy*311.7 + salt)*43758.5453)
    h2 = _fract(np.sin(gx*269.5 - gy*183.3 + salt*1.7)*21347.2187)
    h3 = _fract(np.sin(gx*91.7 + gy*57.4 + salt*2.3)*11371.1291)
    cx=.18+.64*h1; cy=.18+.64*h2
    angle=(h3-.5)*2.45; ca=np.cos(angle);sa=np.sin(angle)
    dx=fx-cx;dy=fy-cy;u=dx*ca+dy*sa;v=-dx*sa+dy*ca
    # 2–10px native long-axis and 2–6px short-axis chips.
    long=(.15+.31*h2); short=(.10+.21*h1)
    d=np.sqrt((u/long)**2+(v/short)**2)
    body=np.clip((1-d)/.19,0,1)*(h1>.22)
    rim=np.clip((1.12-d)/.13,0,1)*np.clip((d-.66)/.22,0,1)*(h1>.22)
    face=np.clip(.36+.64*(.5+.5*np.cos(angle-.61)),0,1)*body
    return body.astype(np.float32), rim.astype(np.float32), face.astype(np.float32), h3.astype(np.float32)


def _arrays(shape, seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:
            _CACHE.move_to_end(key);return prior
    y,x=np.mgrid[:h,:w].astype(np.float32);phase=(int(seed)&8191)*.0011
    # Slight bath distortion keeps platelets tied to enamel flow rather than
    # a machine grid. The platelets themselves remain 2–10px native objects.
    u=x+2.1*np.sin(y/91.+phase)+1.3*np.sin((x+y)/57.)
    v=y+1.8*np.sin(x/107.-phase*.6)+1.1*np.sin((x-y)/63.)
    b1,r1,f1,h1=_bed(u,v,12.7,11.3+phase)
    b2,r2,f2,h2=_bed(u+5.7,v-3.1,18.4,37.9+phase)
    b3,r3,f3,h3=_bed(u-4.2,v+6.8,25.1,71.1+phase)
    plate=np.clip(b1*.74+b2*.62+b3*.51,0,1)
    rim=np.clip(r1*.78+r2*.61+r3*.48,0,1)
    face=np.clip(f1*.68+f2*.59+f3*.47,0,1)
    tier=np.clip(h1*.48+h2*.33+h3*.19,0,1)
    depth=.5+.5*np.sin(x/193.+.29*np.sin(y/67.)+phase)*np.sin(y/229.-.21*np.sin(x/83.))
    enamel=.5+.5*np.sin((x-y)/317.+.31*np.sin((x+y)/113.))
    trough=np.clip(.52-plate-rim*.27,0,1)
    turquoise=np.array((.008,.34,.39),np.float32); deep=np.array((.002,.055,.085),np.float32)
    aqua=np.array((.02,.73,.72),np.float32); silver=np.array((.67,.90,.86),np.float32)
    blue=np.array((.04,.31,.66),np.float32); pearl=np.array((.80,.95,.88),np.float32)
    paint=deep*(.71-.19*depth[...,None])+turquoise*(.26+.30*enamel[...,None])
    flake_col=aqua*(1-tier[...,None]) + blue*(tier[...,None])
    paint=paint*(1-plate[...,None]*.64)+flake_col*(plate[...,None]*.64)
    paint=paint*(1-face[...,None]*.34)+silver*(face[...,None]*.34)
    paint=paint*(1-rim[...,None]*.51)+pearl*(rim[...,None]*.51)
    paint*=.76+.24*(.35+.65*depth[...,None])
    M=22+31*depth+29*enamel+72*plate+96*face+142*rim+23*tier-19*trough
    R=224-29*depth-21*enamel-66*plate-92*face-139*rim+18*tier+21*trough
    C=27+34*depth+25*enamel+81*plate+109*face+153*rim+29*(1-tier)-17*trough
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_turquoise_metalflake(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_turquoise_metalflake(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
