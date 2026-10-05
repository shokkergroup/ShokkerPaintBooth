"""Lava Lamp Purple I3 — candidate fine 1960s violet glass lacquer.

SPB-105 / owner doctrine / 2026-08-30.  Earlier Lava Lamp Filament had good
microdetail but collapsed into a dark capsule lattice.  I3 keeps each visible
event at 6–30px (gel cells, glass lips, plasma seams, mica cores and dark
troughs) while coherent purple/magenta glass territories survive card scale.
It is not a macro blob, repeated station, or re-use of Oil Slick/Melting film.
"""
from collections import OrderedDict
from threading import RLock
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()
_VIOLET=np.array(((.18,.025,.37),(.47,.035,.57),(.75,.035,.48),(.16,.11,.54)),np.float32)


def _arrays(shape,seed):
    h,w=int(shape[0]),int(shape[1]);key=(h,w,int(seed))
    with _LOCK:
        prior=_CACHE.get(key)
        if prior is not None:_CACHE.move_to_end(key);return prior
    y,x=np.mgrid[:h,:w].astype(np.float32);phase=(int(seed)&0xffff)*.00109
    # Coherent fluid territories are created by several offset warped pools,
    # but the actual visible structure remains compact gel/foam geometry.
    qx=(x-w*.5)/(w*.5);qy=(y-h*.5)/(h*.5)
    for cx,cy,rad,turn in ((-.43,-.30,.75,.52),(.35,-.39,.62,-.63),(.41,.30,.68,.48),(-.34,.38,.61,-.56)):
        dx=qx-cx;dy=qy-cy;ang=np.exp(-(dx*dx+dy*dy)/(rad*rad))*turn
        ca=np.cos(ang);sa=np.sin(ang);qx=cx+ca*dx-sa*dy;qy=cy+sa*dx+ca*dy
    qx+=.024*np.sin(19*qy+phase)+.012*np.sin(43*qx-10*qy)
    qy+=.022*np.sin(17*qx-phase*.7)+.011*np.sin(39*qy+8*qx)
    territory=(.49*np.sin(3.9*qx+1.0*qy+phase)+.30*np.sin(-2.1*qx+4.8*qy-phase*.7)+.21*np.sin(6.4*qx-3.6*qy))
    zone=np.clip(np.floor((territory+1.14)*1.88).astype(np.int32),0,3)
    u=qx*w;v=qy*h
    gel=.5+.5*np.sin(u*.198+.58*np.sin(v*.113)+.23*np.sin((u-v)*.073))
    plasma=.5+.5*np.sin(v*.173-.46*np.sin(u*.107)+.19*np.sin((u+v)*.089))
    cell=np.clip((gel*plasma-.31)/.64,0,1)
    lip=np.exp(-np.square((gel-.64)/.050))*np.clip(.24+.76*plasma,0,1)
    seam=np.exp(-np.square(np.sin((u-v)*.165+.53*np.sin((u+v)*.071))/.13))*np.clip(cell*.94,0,1)
    core=np.clip((plasma-.69)/.31,0,1)*cell
    trough=np.clip((.41-gel)/.35,0,1)
    base=_VIOLET[zone]
    adjacent=_VIOLET[np.mod(zone+1+(territory>.10).astype(np.int32),4)]
    paint=np.zeros((h,w,3),np.float32)+np.array((.014,.004,.031),np.float32)
    paint+=base*(.25+.38*gel)[...,None]
    paint+=adjacent*(cell*(.16+.25*plasma))[...,None]
    paint+=np.array((.96,.08,.63),np.float32)*(lip*.17)[...,None]
    paint+=np.array((.60,.23,.95),np.float32)*(core*.14)[...,None]
    paint+=np.array((.08,.012,.16),np.float32)*(trough*.30)[...,None]
    paint+=np.array((.77,.30,.98),np.float32)*(seam*.09)[...,None]
    M=16+63*gel+94*cell+87*lip+62*core+43*seam+25*(zone==2)-36*trough
    R=225-49*gel-87*cell-113*lip-76*core-61*seam+42*trough
    C=18+74*gel+112*cell+121*lip+94*core+58*seam+27*(zone==3)-26*trough
    res=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
    with _LOCK:
        _CACHE[key]=res
        while len(_CACHE)>2:_CACHE.popitem(last=False)
    return res


def paint_lava_lamp_regional(paint,shape,mask,seed,pm,bb):
    del bb
    authored,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
    if source.max(initial=0)>1.5:source=source/255.
    coverage=np.asarray(mask,np.float32);coverage=coverage[...,0] if coverage.ndim==3 else coverage
    mix=(np.clip(coverage,0,1)*float(pm))[...,None]
    return np.clip(source*(1-mix)+authored*mix,0,1).astype(np.float32)


def spec_lava_lamp_regional(shape,seed,sm,base_m,base_r):
    del sm,base_m,base_r
    _,spec=_arrays(shape,seed);return spec[...,0],spec[...,1],spec[...,2]
