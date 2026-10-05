"""Melting Celluloid I1 — candidate 1960s liquid-light candy lacquer.

SPB-105 / owner doctrine / 2026-08-30.  The old Melting Rainbow is only wide
parallel rainbow bands.  This one uses four offset hand-dyed celluloid pools
whose 8–32px internal gel cells, crease lips, mica scars, ink tears and candy
depths all inherit the surrounding pigment/material state.  It intentionally
does not borrow Oil Slick's lens topology: this is opaque melted print film,
not wet thin-film interference.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()
_COL=np.array(((.90,.05,.30),(.98,.27,.03),(.98,.72,.04),
               (.05,.62,.56),(.10,.20,.78),(.47,.07,.66),(.86,.08,.50)),np.float32)


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        p=_CACHE.get(key)
        if p is not None:_CACHE.move_to_end(key);return p
    y,x=np.mgrid[:h,:w].astype(np.float32); phase=(int(seed)&0xffff)*.00083
    # Four subtle hand-pulled domains bend the pigment sheet without a single
    # central whirl or any straight ribbon family.
    qx=(x-w*.5)/(w*.5);qy=(y-h*.5)/(h*.5)
    for cx,cy,rad,turn in ((-.46,-.32,.72,.62),(.37,-.38,.58,-.70),(.46,.28,.66,.55),(-.31,.39,.59,-.61)):
        dx=qx-cx;dy=qy-cy;ang=np.exp(-(dx*dx+dy*dy)/(rad*rad))*turn
        ca=np.cos(ang);sa=np.sin(ang);qx=cx+ca*dx-sa*dy;qy=cy+sa*dx+ca*dy
    qx+=.026*np.sin(18*qy+phase)+.012*np.sin(41*qx-11*qy)
    qy+=.024*np.sin(16*qx-phase*.7)+.011*np.sin(37*qy+9*qx)
    # A nonperiodic broad pigment selector supplies thumbnail-scale movement.
    bath=(.49*np.sin(4.0*qx+1.13*qy+phase)+.31*np.sin(-2.3*qx+5.1*qy-phase*.8)
          +.20*np.sin(6.7*qx-3.8*qy+phase*.3))
    selector=np.clip(np.floor((bath+1.12)*3.16).astype(np.int32),0,6)
    neighbor=np.mod(selector+1+(bath>.18).astype(np.int32),7)
    # Fine physical marks live inside each melted pigment territory.
    u=qx*w;v=qy*h
    gel=.5+.5*np.sin(u*.215+.57*np.sin(v*.123)+.21*np.sin((u-v)*.079))
    mica=.5+.5*np.sin(v*.292-.46*np.sin(u*.181)+.23*np.sin((u+v)*.113))
    cell=np.clip((gel*mica-.34)/.62,0,1)
    crease=np.exp(-np.square(np.sin(u*.123+.35*np.sin(v*.087))/.16))*np.clip(.85-cell,0,1)
    tear=np.exp(-np.square(np.sin((u-v)*.176+.61*np.sin((u+v)*.073))/.14))*np.clip(cell*.92,0,1)
    pearl=np.clip((gel-.66)/.34,0,1)*np.clip((mica-.53)/.47,0,1)
    c0=_COL[selector];c1=_COL[neighbor]
    ground=np.array((.024,.008,.040),np.float32)
    paint=np.broadcast_to(ground,(h,w,3)).astype(np.float32).copy()
    paint+=c0*(.32+.38*gel)[...,None]
    paint+=c1*(cell*(.13+.27*mica))[...,None]
    paint+=np.array((.92,.55,.70),np.float32)*(pearl*.15)[...,None]
    paint+=np.array((.12,.035,.15),np.float32)*(crease*.28)[...,None]
    paint+=np.array((.74,.23,.37),np.float32)*(tear*.11)[...,None]
    # Each glass/candy cell, lip, mica event and pigment family has its own
    # material response; there is no separate texture-generated spec map.
    M=15+67*gel+77*cell+69*pearl+61*tear+29*(selector==3)+22*(selector==5)-35*crease
    R=225-52*gel-72*cell-108*pearl-71*tear+47*crease+23*(selector==2)
    C=17+65*gel+105*cell+119*pearl+53*tear+25*(selector==4)+20*(selector==6)-25*crease
    res=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=res
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return res


def paint_melting_celluloid(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5:source=source/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(source*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_melting_celluloid(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec[...,0],spec[...,1],spec[...,2]
