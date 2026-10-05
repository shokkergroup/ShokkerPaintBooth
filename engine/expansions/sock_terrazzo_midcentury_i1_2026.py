"""Terrazzo Midnight I1 — restrained 1950s soda-counter aggregate.

SPB-105 / SH-TERRAZZO-CREAM-I1, 2026-08-30. The live card turns every
Voronoi fragment into a saturated different color and therefore reads as
confetti. This keeps 8–28px irregular aggregate but gives it a continuous
warm terrazzo matrix, a deliberately limited mineral palette, fine brass
seams, and component-specific M/R/Cc rather than independent rainbow noise.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
from engine.paint_v2.sock_hop_2026 import _terrazzo_field

_CACHE, _LOCK = OrderedDict(), RLock()


def _arrays(shape, seed):
    h,w=int(shape[0]),int(shape[1]); key=(h,w,int(seed))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key); return _CACHE[key]
    q=min(1.,1024./max(h,w)); hh,ww=max(16,round(h*q)),max(16,round(w*q))
    cid,edge=_terrazzo_field((hh,ww),seed)
    # Existing Voronoi components are 8–28px at final size. The matrix and
    # seams make them one material process rather than isolated candy chips.
    matrix=np.clip((.58-edge)/.32,0,1)
    chip=np.clip((edge-.30)/.31,0,1)
    heart=np.clip((edge-.82)/.18,0,1)
    seam=np.clip((.19-edge)/.14,0,1)
    code=np.mod(np.floor(cid*251).astype(np.int32)*17+int(seed)*3,11)
    # Mineral populations are sparse and muted: charcoal, diner turquoise,
    # oxblood, mustard and pale alabaster—not equal-area rainbow fragments.
    charcoal=((code==0)|(code==7)).astype(np.float32)*chip
    turquoise=((code==2)|(code==10)).astype(np.float32)*chip
    oxblood=(code==4).astype(np.float32)*chip
    mustard=(code==6).astype(np.float32)*chip
    alabaster=((code==1)|(code==9)).astype(np.float32)*chip
    shell=np.clip(chip-charcoal-turquoise-oxblood-mustard-alabaster,0,1)
    cream=np.array((.77,.69,.54),np.float32); bone=np.array((.91,.84,.67),np.float32)
    slate=np.array((.055,.070,.082),np.float32); teal=np.array((.035,.39,.42),np.float32)
    wine=np.array((.42,.045,.045),np.float32); gold=np.array((.72,.47,.09),np.float32)
    pearl=np.array((.78,.78,.68),np.float32); brass=np.array((.86,.64,.21),np.float32)
    paint=cream[None,None,:]*(.90+.08*np.sin((cid*13.0)+.4))[...,None]
    for field,color,alpha in ((shell,bone,.43),(alabaster,pearl,.85),(charcoal,slate,.94),
                              (turquoise,teal,.88),(oxblood,wine,.88),(mustard,gold,.84)):
        a=np.clip(field*alpha,0,1)[...,None];paint=paint*(1-a)+color*a
    # A 2–6px brass binder catches track light but follows real chip borders.
    a=(seam*.44)[...,None];paint=paint*(1-a)+brass*a
    # A light center polish is attached to every visible aggregate, not noise.
    polish=heart*(.23+.17*(code%3==0)); paint=paint*(1-polish[...,None]) + pearl*(polish[...,None])
    M=37+16*matrix+29*shell+181*charcoal+151*turquoise+129*oxblood+174*mustard+102*alabaster+153*seam+78*polish
    R=207-13*matrix-19*shell-166*charcoal-141*turquoise-112*oxblood-159*mustard-81*alabaster-148*seam-61*polish
    C=30+17*matrix+25*shell+159*charcoal+185*turquoise+109*oxblood+142*mustard+92*alabaster+173*seam+110*polish
    if(hh,ww)!=(h,w):
        up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
        paint=up(paint);M,R,C=map(up,(M,R,C))
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,0,255),np.clip(C,0,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_terrazzo_midcentury(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
    mix=(np.clip(m,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_terrazzo_midcentury(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
