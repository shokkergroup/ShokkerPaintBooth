"""H1-I18 — Black-opal aperture: bright whole-car pass over a new optical response."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
from engine.expansions import fractured_houdini_veiled_skull_i17_2026 as _opal
_C,_L=OrderedDict(),RLock()
def _a(shape,seed):
 h,w=map(int,shape);k=(h,w,int(seed))
 with _L:
  if k in _C:_C.move_to_end(k);return _C[k]
 # I18 does not reuse the rejected I17 appearance: it recasts the same fine
 # optical substrate as bright black-opal apertures with a new response law.
 raw,spec=_opal._a((h,w),seed);y,x=np.mgrid[:h,:w].astype(np.float32);q=cv2.resize(np.random.default_rng(seed*811+73).random((23,31)).astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);q=cv2.GaussianBlur(q,(0,0),max(3,h/62));q=(q-q.min())/max(q.max()-q.min(),1e-5)
 # I18-I2: restrict the bright opal bloom to the fine substrate shoulders;
 # the slow field should steer energy, not turn into cloudy RGB islands.
 lift=np.clip(.31+.38*q,0,1)[...,None];opal=np.power(np.clip(raw,0,1),.64);hue=np.stack((.16+.15*q,.25+.12*(1-q),.38+.19*q),2);art=np.clip(opal*.67+hue*lift*.33,0,1).astype(np.float32)
 # Spec-only aperture shifts: add broad physical variation without touching
 # RGB anatomy. Fine skull relief remains authored by the substrate spec.
 # I18-I4: aperture brightness and spec travel have the same cause.  The
 # local opal shoulder changes M/R/Cc; no separate texture is introduced.
 mrc=spec.astype(np.float32);shoulder=np.clip((art.mean(axis=2)-.18)*3.2,0,1);mrc[...,0]=np.clip(mrc[...,0]+(q-.5)*34+shoulder*18,0,255);mrc[...,1]=np.clip(mrc[...,1]-(q-.5)*28-shoulder*17,8,255);mrc[...,2]=np.clip(mrc[...,2]+(q-.5)*38+shoulder*26,8,255);out=(art,mrc.astype(np.uint8))
 with _L:_C[k]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_veiled_skull_i18(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_a(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=np.clip(m,0,1)[...,None]*pm;return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_veiled_skull_i18(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _a(shape,seed)[1]
