"""Tie-Dye Crumple I1 — wax-resist silk and pearlescent dye lacquer.

SPB-105 / Groovy Vibes rebuild, 2026-08-29.  This is a distinct late-1960s
material family: connected crumpled fabric folds, wax boundaries, pigment
pools and pearl lips.  M/R/Cc are extracted from those visible states.
"""
from collections import OrderedDict
from pathlib import Path
from threading import RLock

import cv2
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()
_ASSET = Path(__file__).resolve().parents[2] / "assets" / "generated" / "groovy" / "tie_dye_crumple_i1_2026.png"


def _arrays(shape, seed):
    h,w=int(shape[0]),int(shape[1]); key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    source=cv2.imread(str(_ASSET),cv2.IMREAD_COLOR)
    if source is None:
        raise RuntimeError(f"Tie-dye crumple asset missing: {_ASSET}")
    bgr=cv2.resize(source,(w,h),interpolation=cv2.INTER_CUBIC)
    paint=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB).astype(np.float32)/255.
    hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV).astype(np.float32)
    hue,sat,val=hsv[...,0]/179.,hsv[...,1]/255.,hsv[...,2]/255.
    gray=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY).astype(np.float32)/255.
    # Fine crumple ridges and broader wax-resist/pigment transitions are both
    # read from the paint itself; no freestanding noise or second pattern.
    ridge=np.abs(gray-cv2.GaussianBlur(gray,(0,0),1.15))
    resist=np.abs(gray-cv2.GaussianBlur(gray,(0,0),6.5))
    fold=np.clip(3.2*ridge+1.45*resist,0,1)
    wax=np.clip((val-.58)*1.65,0,1)*np.clip((.66-sat)*1.8,0,1)
    dye=np.clip(.12+.88*sat,0,1)
    # Multiple hue populations alter physical response only where that pigment
    # actually appears beside fold/wax geometry.
    hm=.5+.5*np.cos(2*np.pi*(hue-.12)); hr=.5+.5*np.cos(2*np.pi*(hue-.47)); hc=.5+.5*np.cos(2*np.pi*(hue-.76))
    M=18+105*dye+106*fold+56*wax+28*val+29*hm
    R=242-111*dye-111*fold-61*wax+20*(1-val)-31*hr
    C=14+119*dye+118*fold+71*wax+24*val+33*hc
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_tie_dye_crumple(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_tie_dye_crumple(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
