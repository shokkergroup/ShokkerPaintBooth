"""Groovy Zigzag I2 — dense 1960s woven poster chevrons.

SPB-105 / owner scale audit, 2026-08-29.  The former broad zigzag is rebuilt
as 8–16px ink ribbons, 6px weave crossings, edge pin-lines and mica flecks.
The larger chevron rhythm is assembled from those small physical marks.
"""
import numpy as np
from engine.core import get_mgrid

_CACHE = {}


def _field(shape, seed):
    key=(tuple(shape[:2]),int(seed))
    if key in _CACHE:return _CACHE[key]
    h,w=shape[:2]; y,x=(a.astype(np.float32) for a in get_mgrid((h,w)))
    # 64px chevron cell, but the visible bands are only 8–16px wide.
    yy=np.mod(y,64.0); tooth=np.abs(yy-32.0)
    diag=(x + 1.12*tooth + 3*np.sin(2*np.pi*y/173.0)) / 15.0
    frac=diag-np.floor(diag); band=(np.floor(diag).astype(np.int32)%5)
    ink=np.power(.5+.5*np.cos(2*np.pi*frac),15.0)
    edge=np.power(.5+.5*np.cos(2*np.pi*(frac+.17)),27.0)
    # Fine counter-running warp threads make each stripe a woven material,
    # rather than a single flat neon polygon.
    cross=np.power(.5+.5*np.cos(2*np.pi*(x/7.0-y/11.0)),18.0)
    warp=np.power(.5+.5*np.sin(2*np.pi*(x/5.5+y/13.0)),23.0)
    fleck=np.power(.5+.5*np.sin(2*np.pi*(x/9.0+y/7.0+(seed%83)/83.0)),34.0)
    junction=np.power(np.clip(1-tooth/8.0,0,1),2.0)
    result=tuple(np.ascontiguousarray(z,dtype=np.float32) for z in (band,ink,edge,cross,warp,fleck,junction,frac))
    _CACHE[key]=result
    if len(_CACHE)>18:_CACHE.pop(next(iter(_CACHE)))
    return result


def _mix(base,pigment,alpha):
    a=np.clip(alpha,0,1)[:,:,None]
    return base*(1-a)+np.asarray(pigment,np.float32)[None,None,:]*a


def _apply(paint,mask,color):
    if mask is not None and mask.size and float(mask.min())>=.999:return np.ascontiguousarray(color,dtype=np.float32)
    if paint.ndim==3 and paint.shape[2]>3:paint=paint[:,:,:3].copy()
    return (color*mask[:,:,None]+paint*(1-mask[:,:,None])).astype(np.float32)


def paint_groovy_zigzag(paint,shape,mask,seed,pm,bb):
    del pm,bb
    band,ink,edge,cross,warp,fleck,junction,frac=_field(shape,seed)
    palette=np.asarray(((.065,.038,.19),(.12,.55,.53),(.88,.13,.32),(.95,.61,.07),(.35,.09,.58)),np.float32)
    col=palette[band.astype(np.int32)]
    # Poster ink trough, silk-screen lip, woven thread crossings and a tiny
    # glitter pin survive car-scale reduction without becoming confetti.
    col=_mix(col,(.030,.015,.075),ink*.42)
    col=_mix(col,(1.,.75,.18),edge*.24)
    col=_mix(col,(.06,.78,.70),cross*.18)
    col=_mix(col,(.94,.10,.42),warp*.15)
    col=_mix(col,(1.,.91,.50),fleck*.27)
    col=_mix(col,(.97,.38,.10),junction*.29)
    return _apply(paint,mask,np.clip(col,0,1))


def spec_groovy_zigzag(shape,seed,sm,base_m,base_r):
    del base_m,base_r
    band,ink,edge,cross,warp,fleck,junction,frac=_field(shape,seed)
    b=band.astype(np.float32)/4.0
    M=17+95*b+129*np.clip(.25*ink+.21*edge+.18*cross+.15*warp+.12*fleck+.09*junction,0,1)*sm
    R=240-104*b-133*np.clip(.27*ink+.20*warp+.18*cross+.15*edge+.11*fleck+.09*junction,0,1)
    CC=11+142*(.57*frac+.43*b)+105*np.clip(.24*edge+.20*fleck+.18*cross+.16*warp+.12*ink+.10*junction,0,1)
    return tuple(np.clip(z,0,255).astype(np.float32) for z in (M,R,CC))
