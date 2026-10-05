"""H1-I19 — controlled Hologram-derived hidden-relief baseline.

Hologram Metal remains untouched. This is an isolated Houdini diagnostic that
uses its proven visible-material physics with separate spec-only skull shifts.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
from engine.expansions import x_lab_2026 as _xlab
_C,_L=OrderedDict(),RLock()
def _a(shape,seed):
 h,w=map(int,shape);k=(h,w,int(seed))
 with _L:
  if k in _C:_C.move_to_end(k);return _C[k]
 art,spec=_xlab.arrays('xlab_hologram_metal');art=cv2.resize(art,(w,h),interpolation=cv2.INTER_AREA);mrc=cv2.resize(spec,(w,h),interpolation=cv2.INTER_NEAREST).astype(np.float32)
 y,x=np.mgrid[:h,:w].astype(np.float32);step=max(30.,w/70.);gx,gy=np.floor(x/step),np.floor(y/step);cx=(gx+.22+.56*((np.sin(gx*127.1+gy*311.7+(seed+31)*19.19)*43758.5453)%1))*step;cy=(gy+.20+.59*((np.sin(gx*127.1+gy*311.7+(seed+47)*19.19)*43758.5453)%1))*step;X=(x-cx)/(step*.21);Y=(y-cy)/(step*.24);b=np.exp(-((np.abs(X)-(.20+.32*np.clip(-Y,0,1)))/.07)**2)*np.exp(-((Y+.25)/.14)**2);s=np.exp(-((np.abs(np.abs(X)+.56*np.abs(Y)-.39)/.065)**2))*np.exp(-((Y+.02)/.34)**2);c=np.maximum(np.clip(1-np.abs((X-.27)/.18)-np.abs(Y/.15),0,1),np.clip(1-np.abs((X+.27)/.18)-np.abs(Y/.15),0,1));j=np.exp(-((np.abs(Y-.49)-(.22-.20*np.abs(X)))/.06)**2)*np.clip(1-np.abs(X)/.74,0,1);t=j*np.exp(-((np.sin(X*27)*.5+.5-.60)/.13)**2);rel=np.clip(.72*b+.67*s+.62*j+.58*t,0,1);M,R,C=(mrc[...,i].copy() for i in range(3));M0,R0,C0=M.copy(),R.copy(),C.copy();M=np.where(rel>.38,np.clip(M0+42,0,255),M);R=np.where(rel>.38,np.clip(R0-31,8,255),R);C=np.where(rel>.38,np.clip(C0+46,8,255),C);M=np.where(c>.40,np.clip(M0-40,0,255),M);R=np.where(c>.40,np.clip(R0+50,8,255),R);C=np.where(c>.40,np.clip(C0-32,8,255),C);out=(art.astype(np.float32),np.stack((M,R,C),2).astype(np.uint8))
 with _L:_C[k]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_veiled_skull_i19(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_a(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=np.clip(m,0,1)[...,None]*pm;return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_veiled_skull_i19(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _a(shape,seed)[1]
