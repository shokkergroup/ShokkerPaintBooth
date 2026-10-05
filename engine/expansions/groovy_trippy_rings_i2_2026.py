"""Trippy Rings I2 — dense 1960s multi-spindle silk-screen rings.

SPB-105 / GV-TRIPPY-RINGS-I2 / 2026-08-30.  The old category idea was a
single giant bullseye. This version uses 2–7px ink rings from three off-canvas
screen centres. Their overlap changes the ink order, lip, mica and clearcoat
state at every small intersection; all colour stays in the period print.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE, _LOCK = OrderedDict(), RLock()


def _arrays(shape, seed):
    h,w=int(shape[0]),int(shape[1]); key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:
            _CACHE.move_to_end(key);return prior
    y,x=np.mgrid[:h,:w].astype(np.float32);phase=(int(seed)&8191)*.0017
    # Three centres remain outside the paint area: no obvious bullseye lands on
    # the hood/door, yet every visible arc is a 2–7px screen-print primitive.
    r1=np.hypot(x+318.+9*np.sin(y/97.), y-(-247.)+8*np.cos(x/131.))
    r2=np.hypot(x-(w+273.)+7*np.cos(y/113.), y-(h+386.)+11*np.sin(x/109.))
    r3=np.hypot(x-w*.56+8*np.sin(y/89.), y+319.+6*np.cos(x/83.))
    carrier=r1/8.3 + .23*np.sin(r2/13.7+phase) + .17*np.cos(r3/10.9-phase*.7)
    frac=carrier-np.floor(carrier)
    index=np.mod(np.floor(carrier).astype(np.int32),6)
    # Printed band, 1–2px registration edge and a 2–4px mica lip.
    ink=np.clip((.79-frac)/.21,0,1)
    lip=np.exp(-np.square((frac-.77)/.045))
    trough=np.clip((frac-.88)/.12,0,1)
    aux=.5+.5*np.sin(r2/7.1-r3/9.3+phase)
    cross=np.exp(-np.square(np.sin((r1-r2)/19.7)/.13))*np.clip(.35+.65*aux,0,1)
    mica=np.clip((aux-.78)/.22,0,1)*ink
    region=np.mod(np.floor((r1/61.+r2/89.+phase)).astype(np.int32),3)
    palette=np.array(((.91,.10,.38),(.95,.58,.06),(.11,.73,.63),(.34,.08,.66),(.96,.29,.10),(.76,.08,.57)),np.float32)
    shift=np.where(region==0,0,np.where(region==1,2,4))
    color=palette[np.mod(index+shift,6)]
    ground=np.array((.028,.012,.09),np.float32)
    black=np.array((.008,.003,.024),np.float32); pearl=np.array((.87,.80,.58),np.float32)
    cyan=np.array((.28,.90,.82),np.float32)
    paint=ground*(1-ink[...,None]*.87)+color*(ink[...,None]*.87)
    paint=paint*(1-lip[...,None]*.53)+pearl*(lip[...,None]*.53)
    paint=paint*(1-trough[...,None]*.68)+black*(trough[...,None]*.68)
    paint=paint*(1-cross[...,None]*.24)+cyan*(cross[...,None]*.24)
    paint=paint*(1-mica[...,None]*.20)+pearl*(mica[...,None]*.20)
    M=18+47*(index/5.)+92*ink+131*lip+49*cross+74*mica-28*trough+19*region
    R=232-39*(index/5.)-77*ink-126*lip-46*cross-69*mica+17*trough-13*region
    C=21+45*(index/5.)+96*ink+146*lip+58*cross+88*mica-19*trough+17*(2-region)
    value=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=value
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return value


def paint_trippy_rings(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3]
    if src.max(initial=0)>1.5:src=src/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_trippy_rings(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec
