"""H1-I20 Veiled Skull / nocturne cloisonne, pass 3.

SPB-HOUDINI-H1, owner 2026-08-31.  This abandons the Hologram-like test
lattice: the paint is a canonical-resolution fine celadon/copper enamel,
while recurring skull relief exists only as adjacent M/R/Cc state changes.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_C, _L, _W = OrderedDict(), RLock(), 768
def _f(x): return x-np.floor(x)
def _h(x,y,s): return _f(np.sin(x*127.1+y*311.7+float(s)*19.19)*43758.5453)

def _master(seed):
    """768 master: 11--18px native inlay marks stay truthful at card scale."""
    y,x=np.mgrid[:_W,:_W].astype(np.float32);u,v=.829*x+.559*y,-.559*x+.829*y
    p=5.;iu,iv=np.floor(u/p),np.floor(v/p);fu,fv=_f(u/p),_f(v/p);du,dv=fu-.5,fv-.5
    edge=np.minimum.reduce((fu,1-fu,fv,1-fv));rail=np.clip((.165-edge)/.165,0,1)
    diag=np.clip((.130-np.abs(fu-fv))/.130,0,1);bow=np.clip((.145-np.abs(fu+fv-1))/.145,0,1)
    bead=np.clip(1-(du*du+dv*dv)/.072,0,1)**2
    petal=np.clip(1-(np.abs(du*.72+dv)+np.abs(dv*.72-du))/.51,0,1)
    code=np.floor(_h(iu,iv,seed+41)*8).astype(np.int32);tier=np.array((.18,.28,.38,.48,.58,.68,.79,.92),np.float32)[code]
    tide=.5+.5*np.sin(.019*u-.013*v+.44*np.sin(.011*v));dusk=.5+.5*np.sin(.014*u+.021*v+.8)
    ink=np.stack((.035+.035*dusk,.095+.16*tide,.10+.15*(1-dusk)),2)
    cop=np.stack((.16+.11*tide,.075+.055*dusk,.040+.030*(1-tide)),2)
    pearl=np.stack((.16+.11*dusk,.22+.10*tide,.24+.13*(1-tide)),2)
    base=np.stack((.020+.020*dusk,.033+.026*tide,.040+.035*(1-dusk)),2)
    art=base+ink*(rail*(.28+.33*tier))[...,None]+cop*((diag+petal*.44)*(.08+.23*tier))[...,None]+pearl*((bow+bead*.35)*(.035+.10*tier))[...,None]
    # I20-P4: the P3 carrier passed native anatomy but went black in the
    # actual 256 card.  Lift the continuous smoke lacquer, never the marks.
    art=np.power(np.clip(art,0,1),.70)*.88+np.array((.036,.078,.105),np.float32)
    # Spec Guide physical cards: matte F0, seam F1, fractured P2/P4/P6,
    # dark-chrome E0 and isolated W0 all follow the visible inlay anatomy.
    M=36+114*tier+44*rail+26*diag-20*bow;R=212-124*tier-48*rail+28*bow-18*bead;C=28+124*tier+52*rail+34*diag-16*petal
    # 101px-native recurring skull relief, assembled from fine brow/orbit/
    # cheek/jaw/tooth strokes.  No term below enters art, only M/R/Cc.
    q=38.;gu,gv=np.floor(u/q),np.floor(v/q);cu=(_h(gu,gv,seed+101)-.5)*.20;cv=(_h(gu,gv,seed+127)-.5)*.20
    X,Y=(_f(u/q)-.5-cu)/.34,(_f(v/q)-.5-cv)/.37
    brow=np.exp(-((np.abs(X)-(.20+.16*np.clip(-Y,0,1)))/.065)**2)*np.exp(-((Y+.18)/.105)**2)
    orbit=np.exp(-((np.abs(np.abs(X)+.58*np.abs(Y)-.39)/.062)**2))*np.exp(-((Y+.01)/.31)**2)
    cheek=np.maximum(np.clip(1-np.abs((X-.27)/.17)-np.abs(Y/.14),0,1),np.clip(1-np.abs((X+.27)/.17)-np.abs(Y/.14),0,1))
    jaw=np.exp(-((np.abs(Y-.47)-(.20-.17*np.abs(X)))/.055)**2)*np.clip(1-np.abs(X)/.75,0,1)
    tooth=jaw*np.exp(-((np.sin(X*28)*.5+.5-.61)/.12)**2);rel=np.clip(.74*brow+.68*orbit+.63*cheek+.61*jaw+.55*tooth,0,1)
    hot=rel>.39;cold=cheek>.42
    M=np.where(hot,np.clip(M+38,0,255),M);R=np.where(hot,np.clip(R-33,8,255),R);C=np.where(hot,np.clip(C+49,8,255),C)
    M=np.where(cold,np.clip(M-37,0,255),M);R=np.where(cold,np.clip(R+45,8,255),R);C=np.where(cold,np.clip(C-28,8,255),C)
    return np.clip(art,0,1).astype(np.float32),np.stack((M,R,C),2).clip(0,255).astype(np.uint8)

def _a(shape,seed):
    h,w=map(int,shape);k=(h,w,int(seed))
    with _L:
        if k in _C:_C.move_to_end(k);return _C[k]
    art,spec=_master(seed)
    if (h,w)!=(_W,_W):
        method=cv2.INTER_AREA if h<_W else cv2.INTER_LINEAR
        art=cv2.resize(art,(w,h),interpolation=method);spec=cv2.resize(spec,(w,h),interpolation=method)
    out=(art.astype(np.float32),spec.astype(np.uint8))
    with _L:
        _C[k]=out
        while len(_C)>2:_C.popitem(last=False)
    return out

def paint_veiled_skull_i20(paint,shape,mask,seed,pm,bb):
    del bb;art,_=_a(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+art*mix,0,1).astype(np.float32)

def spec_veiled_skull_i20(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r;return _a(shape,seed)[1]
