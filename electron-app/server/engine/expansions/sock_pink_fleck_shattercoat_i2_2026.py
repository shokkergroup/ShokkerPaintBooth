"""Pink Fleck Shattercoat I2 — candidate 1950s Candy Apple material.

SPB-105 / owner doctrine / 2026-08-30.  Pink Fleck must not be random confetti.
This is a layered hot-rod candy lacquer: each 16px paint cell has four 8px
adjacent material sub-states (hot pink candy, smoked chrome, pearl mica,
and flat wine) while a slow painterly selector holds those states in coherent
shattercoat regions.  Fine cell geometry remains 8–32px across the full car;
the larger sweep only organizes the material story visible at picker scale.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        old=_CACHE.get(key)
        if old is not None:_CACHE.move_to_end(key);return old
    y,x=np.mgrid[:h,:w].astype(np.float32); phase=(int(seed)&0xffff)*.00121
    # A slow hand-spray selector yields contiguous Candy Apple regions; no
    # cell-level random hue assignment and no generic glitter scatter.
    sweep=(.48*np.sin(x/223.+.28*np.sin(y/83.)+phase)
           +.31*np.sin(y/181.-.23*np.sin(x/117.)-phase*.6)
           +.21*np.sin((x+y)/319.+phase*1.2))
    zone=np.clip(np.floor((sweep+1.12)*2.74).astype(np.int32),0,5)
    # 16px cell with four ordered 8px material faces. Hand-spray warping keeps
    # the field alive without making primitive cells exceed the detail limit.
    u=x+2.3*np.sin(y/71.+phase)+1.2*np.sin((x+y)/37.)
    v=y+2.0*np.sin(x/89.-phase*.8)+1.1*np.sin((x-y)/43.)
    cx=np.floor(u/16.).astype(np.int32);cy=np.floor(v/16.).astype(np.int32)
    fx=np.mod(u,16.);fy=np.mod(v,16.)
    quadrant=(fx>=8).astype(np.int32)+2*(fy>=8).astype(np.int32)
    # 2px seam and 3–7px local lacquer waves are visible physical structure.
    seam=np.clip(np.maximum((1.7-np.abs(fx-8.))/1.7,(1.7-np.abs(fy-8.))/1.7),0,1)
    micro=.5+.5*np.sin((u*.51+v*.28)+.62*np.sin((u-v)*.19))
    mica=np.clip((np.sin(u*.29+.37*np.sin(v*.17))*np.sin(v*.33-.41*np.sin(u*.21))-.30)/.70,0,1)
    family=np.mod(zone+quadrant+((cx-2*cy)&1),4)
    candy=(family==0).astype(np.float32);chrome=(family==1).astype(np.float32)
    pearl=(family==2).astype(np.float32);flat=(family==3).astype(np.float32)
    # Zone varies the Candy Apple body, while every adjacent face stays a
    # distinct material state. This is not a single recolored carrier.
    red_gain=.62+.31*(zone/5.)
    wine_gain=.28+.23*(1-zone/5.)
    paint=np.zeros((h,w,3),np.float32)+np.array((.045,.006,.019),np.float32)
    paint+=np.stack((.73*red_gain,.030+.035*red_gain,.18+.16*red_gain),2)*candy[...,None]*(.48+.39*micro[...,None])
    paint+=np.array((.34,.30,.38),np.float32)*chrome[...,None]*(.22+.39*(1-micro[...,None]))
    paint+=np.array((.72,.22,.48),np.float32)*pearl[...,None]*(.22+.32*(.35+.65*mica[...,None]))
    paint+=np.stack((.22*wine_gain,.008+.018*wine_gain,.055+.09*wine_gain),2)*flat[...,None]*(.43+.22*micro[...,None])
    paint+=np.array((.62,.33,.52),np.float32)*(mica*.11)[...,None]
    paint*=1.-(seam*.20)[...,None]
    M=18+122*candy+172*chrome+103*pearl+29*flat+47*micro+36*mica-35*seam
    R=225-89*candy-129*chrome-97*pearl+32*flat-35*micro+27*seam
    C=18+108*candy+147*chrome+151*pearl+31*flat+49*micro+71*mica-25*seam
    res=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=res
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return res


def paint_pink_fleck_shattercoat(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5:source=source/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(source*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_pink_fleck_shattercoat(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec[...,0],spec[...,1],spec[...,2]
