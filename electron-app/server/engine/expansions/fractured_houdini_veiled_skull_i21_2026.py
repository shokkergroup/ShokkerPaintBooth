"""H1-I21 — Veiled Skull / opal brocade, pass 1.

SPB-HOUDINI-H1, owner 2026-08-31.  A card-visible ornate pearl brocade,
not a grid or dark lacquer. Skull anatomy is material-only and repeats across
the sheet as brow/orbit/cheek/jaw micro-relief assemblies.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_C,_L,_W=OrderedDict(),RLock(),768
def _f(x): return x-np.floor(x)
def _h(x,y,s): return _f(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)

def _master(seed):
    y,x=np.mgrid[:_W,:_W].astype(np.float32)
    # Fine flowing brocade threads: 9--24px native rails, curls, pearl eyes
    # and stitch dots.  Warped coordinates defeat global stripe wallpaper.
    u=x+8*np.sin(.014*y)+4*np.sin(.027*x-.019*y);v=y+7*np.sin(.016*x)-4*np.sin(.023*x+.014*y)
    p1=.88*u+.25*v+6.4*np.sin(.013*u+.019*v)+3.2*np.sin(.027*v)
    p2=-.31*u+.94*v+5.8*np.sin(.016*u-.014*v)+3.0*np.sin(.025*u)
    r1=np.clip((.92-np.abs(np.sin(.79*p1)))/.48,0,1);r2=np.clip((.90-np.abs(np.sin(.86*p2)))/.46,0,1)
    curl=np.clip((.86-np.abs(np.sin(.47*p1+.33*np.sin(.18*p2))))/.44,0,1)
    # Small pearl/rivet events sit *on* the thread intersections, never free.
    knot=np.exp(-((np.sin(.43*p1)**2+np.sin(.48*p2)**2)/.13))
    stitch=np.exp(-(np.sin(1.72*p1+.29*np.sin(.6*p2))/.15)**2)*np.clip(.35+.65*r2,0,1)
    rail=np.clip(.38*r1+.33*r2+.19*curl+.15*stitch,0,1)
    detail=np.clip(.48*knot+.24*stitch+.18*curl,0,1)
    # P15's continuous tier test created broad response stripes.  Retain the
    # P14 cell-local eight-tier ladder, whose value still belongs to the
    # woven geometry rather than an independent paint or symbol layer.
    gx,gy=np.floor(u/7.4),np.floor(v/7.4);tier=np.array((.17,.27,.38,.49,.60,.70,.81,.93),np.float32)[np.floor(_h(gx,gy,seed+11)*8).astype(np.int32)]
    # Visible material = rich midnight pearl with linked jade/amethyst/copper
    # thread states, not icon RGB and not a one-colour shadow field.
    z=np.zeros_like(x);ch=.5+.5*np.sin(.042*u-.031*v+.55*np.sin(.018*v));ch2=.5+.5*np.sin(.036*u+.047*v)
    base=np.stack((z+.115,z+.135,z+.180),2)
    jade=np.stack((.055+.12*ch,.34+.26*(1-ch),.42+.28*ch2),2)
    amethyst=np.stack((.34+.31*ch2,.075+.16*ch,.46+.34*(1-ch)),2)
    silver=np.stack((.46+.35*ch,.52+.35*ch2,.65+.28*(1-ch)),2)
    art=base+jade*(r1*(.34+.31*tier))[...,None]+amethyst*(r2*(.24+.25*tier))[...,None]+silver*(detail*(.20+.22*tier)+knot*(.11+.10*tier))[...,None]
    recess=np.clip(.56*r1*r2+.28*curl*(1-knot),0,1)
    art*=1-.16*recess[...,None]
    # Discrete guide-derived states bound to the exact thread anatomy.
    M=65+64*tier+26*r1+15*detail-11*curl;R=192-62*tier-33*r2+14*curl-9*knot;C=46+65*tier+30*rail+17*detail-11*stitch
    # Multiple ~100px-native skull relief assemblies; all component strokes
    # are 10--24px native and only reassign local physical states.
    q=60.;gu,gv=np.floor(u/q),np.floor(v/q);jx=(_h(gu,gv,seed+71)-.5)*.18;jy=(_h(gu,gv,seed+97)-.5)*.18
    X,Y=(_f(u/q)-.5-jx)/.34,(_f(v/q)-.5-jy)/.37
    brow=np.exp(-((np.abs(X)-(.20+.16*np.clip(-Y,0,1)))/.064)**2)*np.exp(-((Y+.18)/.10)**2)
    orbit=np.exp(-((np.abs(np.abs(X)+.58*np.abs(Y)-.39)/.060)**2))*np.exp(-((Y+.01)/.30)**2)
    cheek=np.maximum(np.clip(1-np.abs((X-.27)/.17)-np.abs(Y/.14),0,1),np.clip(1-np.abs((X+.27)/.17)-np.abs(Y/.14),0,1))
    jaw=np.exp(-((np.abs(Y-.47)-(.20-.17*np.abs(X)))/.054)**2)*np.clip(1-np.abs(X)/.75,0,1);tooth=jaw*np.exp(-((np.sin(X*34)*.5+.5-.58)/.105)**2);glint=np.exp(-((np.abs(np.abs(X)-.21)/.047)**2+((Y+.02)/.055)**2))
    nose=np.clip(1-np.abs(X/.095)-np.abs((Y-.13)/.155),0,1);crown=np.exp(-((np.abs(Y+.43)-(.10+.08*np.cos(X*18)))/.045)**2)*np.clip(1-np.abs(X)/.65,0,1)
    rel=np.clip(.75*brow+.70*orbit+.64*cheek+.62*jaw+.55*tooth+.64*nose+.32*crown,0,1);emph=_h(gu,gv,seed+151)
    hot=rel>(.34+.16*emph);cold=cheek>(.36+.12*(1-emph))
    M=np.where(hot,np.clip(M+76,0,255),M);R=np.where(hot,np.clip(R-61,8,255),R);C=np.where(hot,np.clip(C+84,8,255),C)
    M=np.where(cold,np.clip(M-58,0,255),M);R=np.where(cold,np.clip(R+67,8,255),R);C=np.where(cold,np.clip(C-47,8,255),C)
    C=np.where(glint>.35,np.clip(C+72,8,255),C);R=np.where(glint>.35,np.clip(R-30,8,255),R)
    return np.clip(art,0,1).astype(np.float32),np.stack((M,R,C),2).clip(0,255).astype(np.uint8)

def _a(shape,seed):
    h,w=map(int,shape);k=(h,w,int(seed))
    with _L:
        if k in _C:_C.move_to_end(k);return _C[k]
    a,s=_master(seed)
    if (h,w)!=(_W,_W):
        mode=cv2.INTER_AREA if h<_W else cv2.INTER_LINEAR;a=cv2.resize(a,(w,h),interpolation=mode);s=cv2.resize(s,(w,h),interpolation=mode)
    out=(a.astype(np.float32),s.astype(np.uint8))
    with _L:
        _C[k]=out
        while len(_C)>2:_C.popitem(last=False)
    return out

def paint_veiled_skull_i21(paint,shape,mask,seed,pm,bb):
    del bb;a,_=_a(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*pm)[...,None]
    return np.clip(src*(1-m)+a*m,0,1).astype(np.float32)
def spec_veiled_skull_i21(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r;return _a(shape,seed)[1]
