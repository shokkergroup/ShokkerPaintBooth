"""Atomic Charcoal Filigree I2 — nonperiodic mid-century enamel network.

SPB-105 / SH-ATOMIC-CHARCOAL-I2, 2026-08-30. I1 was rejected because its
small parts still repeated in a grid. I2 intentionally has no station,
cell, or repeated icon: deterministic orbit fragments, comet strokes,
nuclei, satellites and pin glints are arranged as a single irregular atomic
filigree. All parts are 4–28px native and own material response.
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
    q=min(1.,1024./max(h,w));hh,ww=max(64,round(h*q)),max(64,round(w*q));rng=np.random.default_rng((int(seed)*2654435761)&0xffffffff)
    orbit=np.zeros((hh,ww),np.float32);ray=np.zeros_like(orbit);core=np.zeros_like(orbit);sat=np.zeros_like(orbit);pin=np.zeros_like(orbit)
    # 470 irregularly spaced compact atomic gestures. Unlike I1, their sites,
    # rotations, axes and state are continuous-randomized—not a tile lattice.
    count=max(140,int(hh*ww/2200)); pts=rng.uniform((-18,-18),(ww+18,hh+18),(count,2))
    for i,(cx,cy) in enumerate(pts):
        st=(i*17+int(seed)*5)%6; a=float(rng.uniform(0,np.pi));rx=float(rng.uniform(5.0,13.5));ry=float(rng.uniform(2.6,7.4));
        # A broken 2–4px chrome ellipse is the structural connective tissue.
        start=float(rng.uniform(10,150)); end=start+float(rng.uniform(125,235))
        cv2.ellipse(orbit,(round(cx),round(cy)),(max(2,round(rx)),max(2,round(ry))),a*180/np.pi,start,end,1.0,max(1,round(rng.uniform(.9,2.0))),cv2.LINE_AA)
        # 5–24px comet stroke terminates into each orbit, sharing the center.
        arm=float(rng.uniform(8,22)); x2=cx+np.cos(a+np.pi*.5)*arm;y2=cy+np.sin(a+np.pi*.5)*arm
        cv2.line(ray,(round(cx),round(cy)),(round(x2),round(y2)),1.0,max(1,round(rng.uniform(.8,2.0))),cv2.LINE_AA)
        cv2.circle(core,(round(cx),round(cy)),max(2,round(rng.uniform(2.0,4.6))),1.0,-1,cv2.LINE_AA)
        # Small satellites stay physically connected to their parent gesture.
        for j in range(2):
            aa=a+(j*2-1)*float(rng.uniform(.66,1.46));dd=float(rng.uniform(7,18));sx=cx+np.cos(aa)*dd;sy=cy+np.sin(aa)*dd
            cv2.circle(sat,(round(sx),round(sy)),max(1,round(rng.uniform(1.4,3.0))),1.0,-1,cv2.LINE_AA)
            if (i+j+st)%3==0:cv2.circle(pin,(round(sx-0.7),round(sy-0.7)),1,1.0,-1,cv2.LINE_AA)
    # Connected components overlap naturally, making a designed filigree—not
    # sparse scatter. A dark enamel bed remains visible between gestures.
    y,x=np.mgrid[0:hh,0:ww].astype(np.float32);lot=.5+.5*np.sin((x+1.3*y)/57.+.45*np.sin(y/17.))
    charcoal=np.array((.015,.022,.030),np.float32);slate=np.array((.047,.065,.076),np.float32)
    coral=np.array((.89,.18,.09),np.float32);aqua=np.array((.025,.66,.70),np.float32);mustard=np.array((.91,.64,.12),np.float32);pearl=np.array((.83,.86,.78),np.float32)
    # Per-gesture color masks use offset copies, so hard adjoining parts vary
    # without painting a random color field on the background.
    coral_m=np.clip(ray*.91+core*.18,0,1);aqua_m=np.clip(orbit*.95+sat*.15,0,1);gold_m=np.clip(sat*.83+ray*.12,0,1);pearl_m=np.clip(pin*.98+core*.12,0,1)
    paint=charcoal*(.84+.13*lot[...,None])+slate*(.05+.025*(1-lot[...,None]))
    for field,color,alpha in ((coral_m,coral,.93),(aqua_m,aqua,.86),(gold_m,mustard,.84),(pearl_m,pearl,.94)):
        z=np.clip(field*alpha,0,1)[...,None];paint=paint*(1-z)+color*z
    M=25+18*lot+148*orbit+125*ray+172*core+132*sat+214*pin
    R=223-15*lot-141*orbit-104*ray-157*core-98*sat-201*pin
    C=23+15*lot+176*orbit+113*ray+139*core+118*sat+218*pin
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_atomic_charcoal_filigree(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_atomic_charcoal_filigree(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
