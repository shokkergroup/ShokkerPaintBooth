"""FRACTURED HOUDINI H1-I7 — Veiled Skull / black-velvet filigree.

Fresh H1 replacement after the I6 cut-enamel concept was rejected at its
20-iteration cap.  The neutral carrier is continuous velvet-and-wire filigree,
not a cell field.  Repeated skulls only phase-shift existing material threads.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock();_WORK=640
def _up(a,w,h):return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)
def _f(a):return a-np.floor(a)

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
    sc=min(1.,_WORK/max(h,w));hh,ww=max(160,round(h*sc)),max(160,round(w*sc))
    yy,xx=np.mgrid[:hh,:ww].astype(np.float32);rng=np.random.default_rng(int(seed)^0x7A11CE)
    # Three off-sheet rosette fields make drifting engraved wire, not an even
    # pattern. Their intersections create 8–28px velvet pockets and threads.
    centers=((-0.22*ww,.24*hh),(1.18*ww,.72*hh),(.48*ww,-.38*hh))
    z=[]
    for cx,cy in centers:
        dx,dy=xx-cx,yy-cy;z.append(np.arctan2(dy,dx)*6.6+np.hypot(dx,dy)/3.85)
    weave=np.minimum.reduce([np.abs(np.sin(q)) for q in z])
    thread=np.clip((.105-weave)*8.3,0,1)
    swirl=.5+.5*np.sin(z[0]*.47+z[1]*.31-z[2]*.24)
    pocket=np.clip((swirl-.63)*3.0,0,1)*(1-thread*.36)
    lip=np.clip(.11-np.abs(swirl-.51)*.50,0,1)*(1-pocket*.5)
    grain=.5+.5*np.sin((xx*.82+yy*.18)/2.15+np.sin(yy/9.0)*1.5)
    glint=np.clip((grain-.89)*8.6,0,1)*(thread*.72+pocket*.25)

    skull=np.zeros((hh,ww),np.float32); hollow=np.zeros_like(skull); jaw=np.zeros_like(skull); halo=np.zeros_like(skull); ribs=np.zeros_like(skull)
    for cx,cy in _points(rng,ww,hh,max(18,int(hh*ww/35000))):
        rx,ry=rng.uniform(20,29),rng.uniform(27,37);a=rng.uniform(-.33,.33);ca,sa=np.cos(a),np.sin(a)
        X=((xx-cx)*ca+(yy-cy)*sa)/rx;Y=(-(xx-cx)*sa+(yy-cy)*ca)/ry
        crown=np.clip(1-(X*X+((Y+.13)/.87)**2),0,1); lower=np.clip(1-((X/.60)**2+((Y-.55)/.35)**2),0,1)
        skull=np.maximum(skull,np.maximum(crown,lower))
        e=np.maximum(np.clip(1-(((X+.31)/.28)**2+((Y+.04)/.21)**2),0,1),np.clip(1-(((X-.31)/.28)**2+((Y+.04)/.21)**2),0,1))
        n=np.clip(1-((X/.12)**2+((Y-.28)/.17)**2),0,1);hollow=np.maximum(hollow,np.maximum(e,n*.72))
        jaw=np.maximum(jaw,lower*np.clip((Y-.29)*2.7,0,1));rr=np.sqrt(X*X+Y*Y)
        halo=np.maximum(halo,np.clip(.095-np.abs(rr-1.05),0,1)*9.0)
        theta=np.arctan2(Y,X);ribs=np.maximum(ribs,crown*np.clip(.08-np.abs(np.sin(theta*5.0+rr*17.0)),0,1)*8.0)

    # RGB carrier has no skull input. It is black velvet threaded with plum,
    # indigo and antique silver, bright enough to read at picker scale.
    velvet=np.array((.042,.032,.077),np.float32);plum=np.array((.18,.075,.25),np.float32)
    indigo=np.array((.08,.13,.27),np.float32);silver=np.array((.37,.34,.52),np.float32)
    paint=np.broadcast_to(velvet,(hh,ww,3)).copy()
    paint=paint*(1-(pocket*.48)[...,None])+plum*(pocket*.48)[...,None]
    paint=paint*(1-(thread*.36)[...,None])+indigo*(thread*.36)[...,None]
    paint=paint*(1-(lip*.18)[...,None])+plum*(lip*.18)[...,None]
    paint=paint*(1-(glint*.28)[...,None])+silver*(glint*.28)[...,None]

    # Near-neighbour violet/rose material cards. Skull regions phase shift the
    # existing filigree state: high response on raised thread, buried response
    # in cavities; no single RGB channel ever carries a silhouette.
    phase=.5+.5*np.sin(z[0]*.39+z[1]*.27+z[2]*.18+swirl*2.4)
    state=np.clip((phase*5+pocket*1.6+thread*.9).astype(np.int32),0,6)
    secret=np.clip((phase*2+3+thread*1.2).astype(np.int32),0,6)
    secret=np.where(hollow>.20,np.clip(state-3,0,6),secret)
    secret=np.where(jaw>.18,np.clip(secret+1,0,6),secret)
    secret=np.where(halo>.18,3+((phase*3).astype(np.int32)%3),secret)
    secret=np.where(ribs>.22,4+((phase*2).astype(np.int32)%3),secret)
    state=np.where(skull>.09,secret,state)
    M=np.array((156,178,199,218,235,247,226),np.float32)
    R=np.array((152,122,93,66,42,22,78),np.float32)
    C=np.array((170,190,211,229,246,255,205),np.float32)
    metal=M[state]+thread*28+pocket*19+glint*21-lip*8
    rough=R[state]-thread*31-pocket*18-glint*25+lip*12
    coat=C[state]-thread*29-pocket*20-glint*18+lip*15
    metal+=skull*13-hollow*21+jaw*8+halo*9+ribs*10
    rough+=-skull*15+hollow*28-jaw*9+halo*5-ribs*11
    coat+=-skull*17+hollow*26-jaw*10+halo*7-ribs*12
    if (hh,ww)!=(h,w):paint=_up(paint,w,h);metal,rough,coat=(_up(q,w,h) for q in (metal,rough,coat))
    val=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=val
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return val

def paint_veiled_skull_i7(paint,shape,mask,seed,pm,bb):
    del bb
    art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    return np.clip(src*(1-np.clip(m,0,1)[...,None]*pm)+art*(np.clip(m,0,1)[...,None]*pm),0,1).astype(np.float32)
def spec_veiled_skull_i7(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    return _arrays(shape,seed)[1]
