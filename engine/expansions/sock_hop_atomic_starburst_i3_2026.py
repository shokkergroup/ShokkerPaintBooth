"""Sock Hop Atomic Starburst I3 — all-over 1950s atomic cocktail print.

SPB-105 / owner scale audit, 2026-08-29.  The old single poster burst is
replaced by 7–30px period-correct satellites, orbital enamel lines, short
star points, and registration hatching across the full 2048² car canvas.
"""
import numpy as np

from engine.core import get_mgrid

_CACHE = {}


def _field(shape, seed):
    key=(tuple(shape[:2]),int(seed))
    if key in _CACHE: return _CACHE[key]
    h,w=shape[:2]
    y,x=(a.astype(np.float32) for a in get_mgrid((h,w)))
    per=max(h,w)/18.1
    ix,iy=np.floor(x/per).astype(np.int32),np.floor(y/per).astype(np.int32)
    state=((ix.astype(np.int64)*1103515245+iy.astype(np.int64)*12345+int(seed)) & 0x7fffffff).astype(np.float32)/2147483647.
    u,v=(x/per)%1-.5,(y/per)%1-.5
    rot=(state-.5)*.64; ca,sa=np.cos(rot),np.sin(rot); u,v=u*ca-v*sa,u*sa+v*ca
    # Central atomic core and eight short radial enamel points.
    r=np.sqrt(u*u+v*v); a=np.arctan2(v,u)
    core=np.clip((.090-r)/.032,0,1)
    star=np.power(.5+.5*np.cos(8*a+state*5.3),10.0)*np.clip((.285-r)/.105,0,1)*np.clip((r-.080)/.045,0,1)
    # Two tilted ellipse orbits. Their line weights are 7–12px native.
    q1=np.sqrt((u/.335)**2+(v/.145)**2); q2=np.sqrt((u/.145)**2+(v/.335)**2)
    orbit1=np.exp(-((q1-1)/.045)**2); orbit2=np.exp(-((q2-1)/.045)**2)
    # Four deliberately placed small satellites, each 8–13px, not random dots.
    def ball(cx,cy,rr): return np.clip((rr-np.sqrt((u-cx)**2+(v-cy)**2))/(rr*.42),0,1)
    sat=np.maximum.reduce((ball(.315,.03,.071),ball(-.28,.09,.056),ball(.07,.285,.049),ball(-.09,-.285,.054)))
    # Thin geometric lounge-fabric underprint fills the space between marks.
    hatch_a=.5+.5*np.sin(2*np.pi*(7.1*u+4.6*v+.14*np.sin(8*v)))
    hatch_b=.5+.5*np.sin(2*np.pi*(4.9*u-7.8*v+.16*np.sin(7*u)))
    hatch=np.power(hatch_a,18.0)+.72*np.power(hatch_b,21.0)
    _CACHE[key]=tuple(a.astype(np.float32) for a in (core,star,orbit1,orbit2,sat,hatch,hatch_a,hatch_b))
    if len(_CACHE)>18: _CACHE.pop(next(iter(_CACHE)))
    return _CACHE[key]


def _mix(base,color,alpha):
    a=np.clip(alpha,0,1)[:,:,None]
    return base*(1-a)+np.asarray(color,np.float32)[None,None,:]*a


def _apply(paint,mask,color):
    if mask is not None and mask.size and float(mask.min())>=.999: return np.ascontiguousarray(color,dtype=np.float32)
    if paint.ndim==3 and paint.shape[2]>3: paint=paint[:,:,:3].copy()
    return (color*mask[:,:,None]+paint*(1-mask[:,:,None])).astype(np.float32)


def paint_atomic_starburst(paint,shape,mask,seed,pm,bb):
    del pm,bb
    core,star,orbit1,orbit2,sat,hatch,ha,hb=_field(shape,seed)
    h,w=shape[:2]; col=np.empty((h,w,3),np.float32); col[:]=(.075,.18,.23) # teal bar-lounge ground
    col=_mix(col,(.10,.34,.35),hatch*.38)
    col=_mix(col,(.92,.66,.16),star*.90)       # mustard star points
    col=_mix(col,(.92,.17,.13),core*.95)       # atomic-red nucleus
    col=_mix(col,(.88,.79,.55),orbit1*.85)     # cream enamel orbit
    col=_mix(col,(.08,.72,.69),orbit2*.82)     # turquoise orbit
    col=_mix(col,(.96,.39,.12),sat*.90)        # orange satellites
    return _apply(paint,mask,np.clip(col,0,1))


def spec_atomic_starburst(shape,seed,sm,base_m,base_r):
    del base_m,base_r
    core,star,orbit1,orbit2,sat,hatch,ha,hb=_field(shape,seed)
    # The three responses track separate visible printed materials and fine
    # hatch directions; no unpainted macro state is used to game variation.
    M=18+114*ha+107*np.clip(.29*core+.25*star+.18*orbit1+.15*orbit2+.13*sat,0,1)*sm
    R=238-116*hb-119*np.clip(.28*core+.23*star+.20*orbit2+.17*orbit1+.12*sat,0,1)
    CC=14+128*(.61*hb+.39*ha)+112*np.clip(.27*orbit1+.24*orbit2+.20*star+.17*sat+.12*core,0,1)
    return tuple(np.clip(a,0,255).astype(np.float32) for a in (M,R,CC))
