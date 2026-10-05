"""H1-I27 — Veiled Skull / mercury-vein reliquary, pass 1.

Second independent H1 carrier after I26: dark liquid-metal lenses and their
meniscus seams. The paint contains no skull; small, recurrent engraving lives
only in deliberately distinct M/R/Cc material states.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
from engine.expansions import fractured_relics_2026 as _relics
from engine.expansions.fractured_houdini_veiled_skull_i26_2026 import _skull_relief

_W=768; _C=OrderedDict(); _L=RLock()

def _master(seed):
    # Pass 2: coalesced mercury bodies, not a blanket of tiny pebbles. The
    # fine detail is retained at meniscus/nick edges, where material changes
    # are physically meaningful at 8–32px native scale.
    liquid=np.asarray(_relics.g_mercury(_W,int(seed)+613,bead=38.0,fine=.0),np.float32)
    liquid=(liquid-liquid.min())/(np.ptp(liquid)+1e-6)
    yy,xx=np.mgrid[:_W,:_W].astype(np.float32)
    # Pass 5: stretch the raw liquid field through a coherent current before
    # shading. This is the last process-level test for this carrier family.
    mapx=xx+26*np.sin(yy*.018+1.2*np.sin(xx*.009))
    mapy=yy+18*np.sin(xx*.022+0.9*np.sin(yy*.011))
    body=cv2.remap(liquid,mapx.astype(np.float32),mapy.astype(np.float32),cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT)
    body=cv2.GaussianBlur(body,(0,0),5.8)
    broad=cv2.GaussianBlur(body,(0,0),23.0)
    meniscus=np.clip(np.abs(body-cv2.GaussianBlur(body,(0,0),4.1))*15.0,0,1)
    nick=np.clip(np.abs(body-cv2.GaussianBlur(body,(0,0),1.6))*9.0,0,1)
    # Visible black mercury: graphite lens bodies, blue-steel domes, narrow
    # pearl menisci. No grid, no printed mark and no independent noise coat.
    void=np.stack((.012+.020*broad,.014+.020*broad,.020+.027*broad),2)
    lead=np.stack((.10+.17*body,.12+.18*body,.16+.22*body),2)
    ink=np.stack((.018+.046*body,.025+.050*body,.070+.090*body),2)
    pearl=np.stack((.36+.28*body,.42+.26*body,.55+.25*body),2)
    art=void+lead*(.62+.26*body)[...,None]+ink*(.42+.34*(1-body))[...,None]+pearl*((.48*meniscus+.20*nick)[...,None])
    art=np.clip(np.power(np.clip(art,0,1),.80)*.96+np.array((.009,.010,.016),np.float32),0,1)
    # Independent material anatomy: body is wet dark metal, rims pass through
    # chrome/Fractured/clear cards, and nicks carry a separate matte response.
    M=24+158*body+49*meniscus-28*nick
    R=188-122*body-73*meniscus+49*nick
    C=38+119*body-65*meniscus+68*nick
    # A second offset current prevents the clearcoat from being a recolored M.
    coat=.5+.5*np.sin(xx*.132-yy*.091+1.7*np.sin(yy*.041))
    C+=63*(coat-.5)
    spec=np.dstack((M,R,C)).clip(0,255).astype(np.int16)
    skull,glint=_skull_relief(xx,yy,seed)
    hot=skull>.38; cool=(skull>.18)&~hot
    spec[hot]=(.25*spec[hot]+.75*np.array((248,22,246),np.float32)).astype(np.int16)
    spec[cool]=(.32*spec[cool]+.68*np.array((22,198,40),np.float32)).astype(np.int16)
    spec[glint>.44]=(.18*spec[glint>.44]+.82*np.array((238,6,14),np.float32)).astype(np.int16)
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

def paint_veiled_skull_i27(paint,shape,mask,seed,pm,bb):
    del bb; art,_=_assets(shape,seed); src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5: src=src/255.0
    m=np.asarray(mask,np.float32); m=m[...,0] if m.ndim==3 else m; m=(np.clip(m,0,1)*pm)[...,None]
    return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)

def spec_veiled_skull_i27(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r; return _assets(shape,seed)[1]
