"""H10-I7 Marble Rose P7 — brecciated garnet stone / hidden quatrefoil relief.

Owner Houdini rebuild, 2026-08-31. This abandons I4–I6's flower/grid grammar.
The RGB carrier is an all-over polished mineral breccia. Only M/R/Cc contains
the repeating, irregularly positioned ornamental quatrefoil relief.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _noise(rng,h,w,cell):return cv2.resize(rng.random((max(5,h//cell),max(5,w//cell))).astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)
def _f(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);sc=min(1.,896/max(h,w));hh,ww=max(192,round(h*sc)),max(192,round(w*sc));rng=np.random.default_rng(seed^0xA107);y,x=np.mgrid[:hh,:ww].astype(np.float32)
 a,b,c=_noise(rng,hh,ww,156),_noise(rng,hh,ww,47),_noise(rng,hh,ww,15);stone=.59*a+.30*b+.11*c;stone=(stone-stone.min())/(np.ptp(stone)+1e-6)
 # Mineral boundaries are a narrow, broken secondary texture—not a global net.
 q=np.floor(stone*9);seam=np.exp(-np.minimum(np.mod(stone*9,1),1-np.mod(stone*9,1))**2/.010);fizz=np.clip((cv2.GaussianBlur(c,(0,0),1.1)-.62)*3.2,0,1)
 lo=np.array((.026,.010,.043),np.float32);mid=np.array((.108,.028,.178),np.float32);hi=np.array((.235,.071,.315),np.float32);paint=lo*(1-stone[...,None])+mid*stone[...,None];paint=paint*(1-(fizz*.18)[...,None])+hi*(fizz*.18)[...,None];paint*=1-(seam*.21)[...,None]
 # Eight coordinated states remain within one stone neighbourhood.
 tier=np.mod(q.astype(np.int32)+np.floor(c*5).astype(np.int32),8);M=np.array((62,78,94,111,128,146,164,183),np.float32)[tier]+fizz*20;R=np.array((161,145,129,112,96,81,67,54),np.float32)[tier]-fizz*16;C=np.array((91,111,133,156,178,199,220,239),np.float32)[tier]+fizz*12
 # Repeating ornamental quatrefoils: four 8–20px lobes, an 8px ring core,
 # and asymmetric canted shoulders. It is material anatomy, never paint art.
 step=69.;gx=np.floor(x/step);gy=np.floor(y/step);cx=(gx+.5)*step+(np.mod(gy,2)*.5*step)+(np.sin(gx*12.7+gy*4.3+seed)*.5)*13;cy=(gy+.5)*step+(np.sin(gx*6.2+gy*9.9+seed)*.5)*13;X=x-cx;Y=y-cy;rel=np.zeros((hh,ww),np.float32)
 for angle in (0.,1.5708,3.1416,4.7124):
  ca,sa=np.cos(angle),np.sin(angle);U=X*ca+Y*sa;V=-X*sa+Y*ca;rel=np.maximum(rel,np.exp(-((U-13.)/6.3)**2-(V/8.2)**2))
 ring=np.exp(-((np.sqrt(X*X+Y*Y)-7.5)/2.2)**2);cut=np.exp(-((np.sqrt(X*X+Y*Y)-18.5)/2.4)**2)*(.5+.5*np.sin(np.arctan2(Y,X)*8))
 rel=np.clip(rel*.79+ring*.62+cut*.34,0,1);M0,R0,C0=M.copy(),R.copy(),C.copy();hot=rel>.42;M=np.where(hot,np.clip(M0+57,0,255),M);R=np.where(hot,np.clip(R0-45,12,255),R);C=np.where(hot,np.clip(C0+62,12,255),C);void=ring>.57;M=np.where(void,np.clip(M0-35,0,255),M);R=np.where(void,np.clip(R0+51,12,255),R);C=np.where(void,np.clip(C0-31,12,255),C)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);paint=up(paint);M,R,C=map(up,(M,R,C))
 out=(np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,12,255),np.clip(C,12,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i7(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_f(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_marble_rose_i7(shape,seed,sm,bm,br):del sm,bm,br;return _f(shape,seed)[1]
