"""Groovy Marble I2 — dense 1960s ink-bath paper marbling.

SPB-105 / owner scale audit, 2026-08-29.  Replaces broad empty marbling with
interleaved 8–32px pigment veins, combed ribs, oil pools, and registration
threads.  The pattern is a continuous fluid field, not tiled wallpaper.
"""
import numpy as np

from engine.core import get_mgrid

_CACHE = {}


def _field(shape, seed):
    key=(tuple(shape[:2]),int(seed))
    if key in _CACHE: return _CACHE[key]
    h,w=shape[:2]
    y,x=(a.astype(np.float32) for a in get_mgrid((h,w)))
    u=x/max(w-1,1); v=y/max(h-1,1)
    phase=(int(seed)%997)/997.0
    # Slow fluid displacement changes direction, but all visible paint marks
    # are high-frequency 8–32px combed veins inside that flow.
    du=.055*np.sin(2*np.pi*(3.2*v+.75*np.sin(2*np.pi*(2.3*u+phase))))+.023*np.sin(2*np.pi*(8.1*v-2.1*u))
    dv=.052*np.sin(2*np.pi*(2.7*u+.62*np.sin(2*np.pi*(2.8*v-phase))))+.020*np.sin(2*np.pi*(7.3*u+1.8*v))
    q=u+du; r=v+dv
    comb_a=.5+.5*np.sin(2*np.pi*(76*q+9*np.sin(2*np.pi*(4*r))))
    comb_b=.5+.5*np.sin(2*np.pi*(69*r-8*np.sin(2*np.pi*(5*q))))
    comb_c=.5+.5*np.sin(2*np.pi*(58*(q+r)+6*np.sin(2*np.pi*(3*q-r))))
    # Narrow interleaved veins and two broader-but-still-sub-32px pigment
    # pockets: physical bands of marbling ink, not random additive texture.
    vein_a=np.power(comb_a,13.0); vein_b=np.power(comb_b,16.0); thread=np.power(comb_c,19.0)
    pool_a=np.power(.5+.5*np.sin(2*np.pi*(42*q+19*r+2.2*np.sin(2*np.pi*3*r))),3.4)
    pool_b=np.power(.5+.5*np.sin(2*np.pi*(47*r-17*q+1.7*np.sin(2*np.pi*4*q))),3.7)
    ridge=np.power(.5+.5*np.sin(2*np.pi*(93*q-51*r)),28.0)
    _CACHE[key]=tuple(a.astype(np.float32) for a in (vein_a,vein_b,thread,pool_a,pool_b,ridge,comb_a,comb_b,comb_c))
    if len(_CACHE)>18:_CACHE.pop(next(iter(_CACHE)))
    return _CACHE[key]


def _mix(base,color,alpha):
    a=np.clip(alpha,0,1)[:,:,None]
    return base*(1-a)+np.asarray(color,np.float32)[None,None,:]*a


def _apply(paint,mask,color):
    if mask is not None and mask.size and float(mask.min())>=.999:return np.ascontiguousarray(color,dtype=np.float32)
    if paint.ndim==3 and paint.shape[2]>3:paint=paint[:,:,:3].copy()
    return (color*mask[:,:,None]+paint*(1-mask[:,:,None])).astype(np.float32)


def paint_groovy_marble(paint,shape,mask,seed,pm,bb):
    del pm,bb
    va,vb,thread,pa,pb,ridge,ca,cb,cc=_field(shape,seed)
    h,w=shape[:2]; col=np.empty((h,w,3),np.float32); col[:]=(.075,.045,.16) # deep indigo bath
    col=_mix(col,(.30,.055,.38),pa*.70)       # plum pool
    col=_mix(col,(.035,.32,.42),pb*.66)       # petrol pool
    # I2.1 keeps bright ink as a highlight hierarchy.  I2's fully saturated
    # three-colour wire field became thumbnail static despite a strong native
    # carrier; these lower-chroma inks retain the same physical geometry.
    col=_mix(col,(.58,.07,.28),va*.66)        # mulberry comb ink
    col=_mix(col,(.05,.49,.50),vb*.60)        # petrol-turquoise comb ink
    col=_mix(col,(.76,.37,.09),thread*.59)    # restrained ochre thread
    col=_mix(col,(.80,.58,.25),ridge*.42)     # rare fine brass ridge
    return _apply(paint,mask,np.clip(col,0,1))


def spec_groovy_marble(shape,seed,sm,base_m,base_r):
    del base_m,base_r
    va,vb,thread,pa,pb,ridge,ca,cb,cc=_field(shape,seed)
    # Each channel follows a different, visible ink pass, while the fine
    # continuous comb fields provide the required multi-shade material depth.
    M=18+116*ca+105*np.clip(.28*va+.24*pa+.19*thread+.17*pb+.12*ridge,0,1)*sm
    R=238-118*cb-116*np.clip(.29*vb+.23*pb+.20*va+.16*pa+.12*ridge,0,1)
    CC=14+129*(.56*cc+.44*ca)+111*np.clip(.27*thread+.23*ridge+.20*va+.17*vb+.13*pa,0,1)
    return tuple(np.clip(a,0,255).astype(np.float32) for a in (M,R,CC))
