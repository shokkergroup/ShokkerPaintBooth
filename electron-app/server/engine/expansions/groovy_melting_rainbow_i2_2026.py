"""Groovy Melting Rainbow I2 — fine gravity-ribbon psychedelic enamel.

SPB-105 / owner scale audit, 2026-08-29.  The former broad rainbow field
and a few giant drips are replaced with 8–30px prismatic ribbon edges,
gravity tongues, enamel lips and dark troughs covering the entire car.
"""
import numpy as np
from engine.core import get_mgrid

_CACHE={}


def _field(shape,seed):
    key=(tuple(shape[:2]),int(seed))
    if key in _CACHE:return _CACHE[key]
    h,w=shape[:2]; y,x=(a.astype(np.float32) for a in get_mgrid((h,w)))
    u=x/max(w-1,1); v=y/max(h-1,1); phase=(int(seed)%997)/997.
    # 65 fine vertical enamel ribbons, with deterministic gravity tongue
    # warps at 8–30px scale instead of one banner-sized colour transition.
    ribbon=65*u+.52*np.sin(2*np.pi*(2.4*v+.20*np.sin(2*np.pi*4*u)))+.15*np.sin(2*np.pi*(8*v+phase))
    frac=ribbon-np.floor(ribbon); idx=(np.floor(ribbon).astype(np.int32)%6)
    edge=np.power(.5+.5*np.cos(2*np.pi*frac),10.0)
    lip=np.power(.5+.5*np.cos(2*np.pi*(frac+.18*np.sin(2*np.pi*(5*v+u)))),18.0)
    # Short gravity tongues grow within the ribbon itself; their endpoints
    # use two independent high-frequency waves, never a big field blob.
    tongue=.5+.5*np.sin(2*np.pi*(7.5*v+frac*2.8+.35*np.sin(2*np.pi*(4*u-v))))
    gravity=np.clip((tongue-.62)/.25,0,1)*np.power(.5+.5*np.sin(2*np.pi*(3.2*v+frac)),5.0)
    trough=np.power(.5+.5*np.sin(2*np.pi*(74*u-9*np.sin(2*np.pi*5*v))),20.0)
    _CACHE[key]=tuple(a.astype(np.float32) for a in (idx,edge,lip,gravity,trough,frac,tongue))
    if len(_CACHE)>18:_CACHE.pop(next(iter(_CACHE)))
    return _CACHE[key]


def _mix(base,color,alpha):
    a=np.clip(alpha,0,1)[:,:,None]
    return base*(1-a)+np.asarray(color,np.float32)[None,None,:]*a


def _apply(paint,mask,color):
    if mask is not None and mask.size and float(mask.min())>=.999:return np.ascontiguousarray(color,dtype=np.float32)
    if paint.ndim==3 and paint.shape[2]>3:paint=paint[:,:,:3].copy()
    return (color*mask[:,:,None]+paint*(1-mask[:,:,None])).astype(np.float32)


def paint_melting_rainbow(paint,shape,mask,seed,pm,bb):
    del pm,bb
    idx,edge,lip,gravity,trough,frac,tongue=_field(shape,seed)
    h,w=shape[:2]; col=np.empty((h,w,3),np.float32); col[:]=(.055,.025,.10)
    palette=np.asarray(((.92,.08,.24),(.98,.42,.06),(.95,.82,.08),(.08,.74,.48),(.05,.49,.91),(.55,.12,.84)),np.float32)
    pig=palette[idx.astype(np.int32)]
    col=col*.22+pig*.78
    # Dark troughs, bright enamel lips, and short white-hot drip ends are
    # layered physical paint passes inside every individual ribbon.
    col=_mix(col,(.055,.035,.12),trough*.72)
    col=_mix(col,(1.,.82,.42),edge*.35)
    col=_mix(col,(.97,.95,.72),lip*.45)
    col=_mix(col,(1.,.70,.26),gravity*.58)
    return _apply(paint,mask,np.clip(col,0,1))


def spec_melting_rainbow(shape,seed,sm,base_m,base_r):
    del base_m,base_r
    idx,edge,lip,gravity,trough,frac,tongue=_field(shape,seed)
    # Separate visible physics: coloured enamel body, recessed troughs, then
    # wet gravity tips and polished lips, all tied to the ribbon geometry.
    body=(idx.astype(np.float32)%3)/2
    M=18+102*body+124*np.clip(.25*edge+.22*lip+.20*gravity+.18*trough+.15*tongue,0,1)*sm
    R=238-113*(1-body)-123*np.clip(.27*trough+.22*edge+.19*gravity+.17*lip+.15*tongue,0,1)
    CC=14+127*(.62*frac+.38*tongue)+113*np.clip(.27*lip+.23*gravity+.20*edge+.17*trough+.13*body,0,1)
    return tuple(np.clip(a,0,255).astype(np.float32) for a in (M,R,CC))
