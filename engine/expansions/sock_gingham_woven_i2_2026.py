"""Gingham Red Woven I2 — candidate fine 1950s shirt/soda-shop textile.

SPB-105 / owner doctrine / 2026-08-30.  This retains the category's actual
signature instead of replacing it with an unrelated abstract: 8–28px red and
cream thread bundles, translucent woven crossings, stitch grain, yarn shadow
and tiny lint catchlights form a genuine fine gingham.  Slow dye uptake only
organizes the textile's colour response; it does not enlarge checks.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:_CACHE.move_to_end(key);return prior
    y,x=np.mgrid[:h,:w].astype(np.float32);phase=(int(seed)&0xffff)*.00101
    # Small woven bundles: 24px repeat with 8px thread faces and 2–4px seams.
    u=x+1.8*np.sin(y/83.+phase)+.7*np.sin(x/29.)
    v=y+1.7*np.sin(x/97.-phase*.6)+.7*np.sin(y/31.)
    p=24.;fx=np.mod(u,p);fy=np.mod(v,p)
    # Two 12px yarn-colour bands per repeat form real gingham; 2–4px
    # thread ribs are deliberately inside those bands, never macro squares.
    wx=(fx>=12.).astype(np.float32); wy=(fy>=12.).astype(np.float32)
    red_x=1.-wx; red_y=1.-wy
    rib_x=.52+.48*np.sin((fx%12.)*1.83+.21*np.sin(v*.19))
    rib_y=.52+.48*np.sin((fy%12.)*1.79-.18*np.sin(u*.17))
    thread_x=np.clip(.62+.38*rib_x,0,1);thread_y=np.clip(.62+.38*rib_y,0,1)
    crossing=red_x*red_y+(1-red_x)*(1-red_y)
    seam=np.clip((.84-np.minimum(np.minimum(fx,24-fx),np.minimum(fy,24-fy)))/.84,0,1)
    grain=.5+.5*np.sin(u*.81+.43*np.sin(v*.39))*np.sin(v*.73-.37*np.sin(u*.31))
    lint=np.clip((grain-.80)/.20,0,1)
    uptake=.5+.5*np.sin(x/217.+.22*np.sin(y/81.)+phase)*np.sin(y/193.-.17*np.sin(x/109.))
    red=np.array((.73,.035,.075),np.float32); cream=np.array((.82,.73,.56),np.float32)
    # Each axis carries its own yarn colour.  Crossing red/red gains depth;
    # cream/cream remains pearly; mixed crossings make the soda-shop check.
    cloth_x=red[None,None,:]*red_x[...,None]+cream[None,None,:]*(1-red_x[...,None])
    cloth_y=red[None,None,:]*red_y[...,None]+cream[None,None,:]*(1-red_y[...,None])
    paint=(cloth_x*(.46+.24*thread_x[...,None])+cloth_y*(.32+.20*thread_y[...,None]))
    red_cross=red_x*red_y;cream_cross=(1-red_x)*(1-red_y)
    paint+=np.array((.18,.008,.022),np.float32)*(red_cross*(.21+.18*grain))[...,None]
    paint+=np.array((.35,.30,.22),np.float32)*(cream_cross*(.13+.10*(1-grain)))[...,None]
    paint+=np.array((.80,.67,.57),np.float32)*(lint*.07)[...,None]
    paint*=1.-(seam*.10)[...,None]
    M=40+74*red_x*thread_x+62*red_y*thread_y+52*red_cross+31*lint+20*uptake-24*seam
    R=210-49*red_x-37*red_y-46*red_cross+26*seam+20*(1-grain)
    C=26+75*red_x*thread_x+58*red_y*thread_y+55*red_cross+35*lint+21*uptake-18*seam
    res=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=res
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return res


def paint_gingham_woven(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5:source=source/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(source*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_gingham_woven(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec[...,0],spec[...,1],spec[...,2]
