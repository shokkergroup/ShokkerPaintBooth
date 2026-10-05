"""H1-I28 — Veiled Skull / blue-black oxide reliquary, pass 1.

An independent H1 carrier: carded black-oxide steel with cold oil bloom. The
visible paint has no skull; recurring engraved reliquaries are M/R/Cc only.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
from engine.expansions import fractured_foundry_2026 as _foundry
from engine.expansions.fractured_houdini_veiled_skull_i26_2026 import _skull_relief

_W=768; _C=OrderedDict(); _L=RLock()

def _master(seed):
    a,_,oil=_foundry.s_bluing(_W,int(seed)+419,swirl=6.6)
    b,_,_= _foundry.s_bluing(_W,int(seed)+811,swirl=10.4)
    a=np.asarray(a,np.float32); b=np.asarray(b,np.float32); oil=np.asarray(oil,np.float32)
    oxide=np.clip(.66*cv2.GaussianBlur(a,(0,0),2.2)+.34*cv2.GaussianBlur(b,(0,0),5.2),0,1)
    broad=cv2.GaussianBlur(oxide,(0,0),16.0)
    card=np.clip(np.abs(oxide-cv2.GaussianBlur(oxide,(0,0),3.0))*12.0,0,1)
    burnish=np.clip(np.abs(broad-cv2.GaussianBlur(broad,(0,0),7.0))*14.0,0,1)
    # Blue-black steel body, selectively carded to blue, plum and silver.
    base=np.stack((.022+.035*oxide,.026+.040*oxide,.040+.060*oxide),2)
    blue=np.stack((.045+.13*oxide,.085+.15*oxide,.17+.23*oxide),2)
    bloom=np.stack((.15+.17*oil,.022+.035*oil,.18+.24*oil),2)
    steel=np.stack((.34+.30*oxide,.38+.29*oxide,.47+.30*oxide),2)
    art=base+blue*(.48+.28*oxide)[...,None]+bloom*(.24*oil)[...,None]+steel*((.50*card+.30*burnish)[...,None])
    art=np.clip(np.power(np.clip(art,0,1),.80)*.95+np.array((.008,.009,.014),np.float32),0,1)
    # Oxide body / carded ridge / oiled bloom are distinct material states.
    M=30+142*oxide+58*card-34*oil
    R=178-102*oxide-78*card+55*oil
    C=38+124*oxide-58*card+72*oil
    yy,xx=np.mgrid[:_W,:_W].astype(np.float32)
    coat=.5+.5*np.sin(xx*.173+yy*.071+1.4*np.sin(yy*.051))
    C+=58*(coat-.5)
    spec=np.dstack((M,R,C)).clip(0,255).astype(np.int16)
    skull,glint=_skull_relief(xx,yy,seed)
    hot=skull>.38; cool=(skull>.18)&~hot
    spec[hot]=(.26*spec[hot]+.74*np.array((248,23,245),np.float32)).astype(np.int16)
    spec[cool]=(.34*spec[cool]+.66*np.array((25,196,42),np.float32)).astype(np.int16)
    spec[glint>.44]=(.20*spec[glint>.44]+.80*np.array((238,7,14),np.float32)).astype(np.int16)
    return art.astype(np.float32),np.clip(spec,0,255).astype(np.uint8)

def _assets(shape,seed):
    h,w=map(int,shape); key=(h,w,int(seed))
    with _L:
        if key in _C: _C.move_to_end(key); return _C[key]
    art,spec=_master(seed)
    if (h,w)!=(_W,_W):
        mode=cv2.INTER_AREA if max(h,w)<_W else cv2.INTER_LINEAR
        art=cv2.resize(art,(w,h),interpolation=mode); spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_NEAREST)
    out=(art.astype(np.float32),spec.astype(np.uint8))
    with _L:
        _C[key]=out
        if len(_C)>2: _C.popitem(last=False)
    return out

def paint_veiled_skull_i28(paint,shape,mask,seed,pm,bb):
    del bb; art,_=_assets(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.0
    m=np.asarray(mask,np.float32); m=m[...,0] if m.ndim==3 else m; m=(np.clip(m,0,1)*pm)[...,None]
    return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)

def spec_veiled_skull_i28(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r; return _assets(shape,seed)[1]
