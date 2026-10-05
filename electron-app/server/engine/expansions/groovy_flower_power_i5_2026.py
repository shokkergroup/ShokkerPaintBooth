"""Groovy Flower Power I5 — fine 1960s screen-printed garden cloth.

SPB-105 / owner scale audit, 2026-08-29.  Replaces the former huge blurred
daisies with two interlaced print scales: 18–30px rosettes, 8–16px buds,
leaf curls and registration strokes.  Nothing is a macro decal or filler.
"""
import numpy as np

from engine.core import get_mgrid, _resize_array

_CACHE={}


def _rosette(x,y,per,seed,petal_count,scale,tag):
    ix,iy=np.floor(x/per).astype(np.int32),np.floor(y/per).astype(np.int32)
    hsh=((ix.astype(np.int64)*1103515245+iy.astype(np.int64)*(12345+tag*129)+int(seed))&0x7fffffff).astype(np.float32)/2147483647.
    u=(x/per)%1-.5+(hsh-.5)*.18; v=(y/per)%1-.5+(.5-hsh)*.16
    rot=(hsh-.5)*.72; ca,sa=np.cos(rot),np.sin(rot); u,v=u*ca-v*sa,u*sa+v*ca
    rr=np.sqrt(u*u+v*v); a=np.arctan2(v,u)
    outer=scale*(.84+.24*np.cos(petal_count*a+hsh*4.5))
    # The rosette has individual lobes, a fine outer registration rim, and a
    # central seed disc—all 8–30px at native output.
    petals=np.clip((outer-rr)/(scale*.23),0,1)*np.clip((rr-scale*.24)/(scale*.19),0,1)
    rim=np.exp(-((rr-outer)/(scale*.11))**2)*np.power(.5+.5*np.cos(petal_count*a+hsh*4.5),4)
    center=np.clip((scale*.26-rr)/(scale*.11),0,1)
    leaf=np.clip((.050-np.abs(v-.28-.20*np.sin(8*u)))/.025,0,1)*np.clip((.40-np.abs(u+.22))/( .11),0,1)
    return petals,rim,center,leaf,hsh


def _field(shape,seed):
    key=(tuple(shape[:2]),int(seed))
    if key in _CACHE:return _CACHE[key]
    h,w=shape[:2]
    # I5.2: compose the screen plate at 1366px maximum, then scale its
    # 5–20px plate marks to the identical 8–30px native marks. This cuts
    # unnecessary 2048² construction cost without post-shrinking macro art.
    factor=min(1.0,1366.0/max(h,w))
    wh,ww=max(64,int(round(h*factor))),max(64,int(round(w*factor)))
    y,x=(a.astype(np.float32) for a in get_mgrid((wh,ww)))
    # Main 17-across flowers have a 21–29px diameter, with a secondary scale
    # of small buds to eliminate empty field without coarsening the pattern.
    p1,r1,c1,l1,h1=_rosette(x,y,max(wh,ww)/17.1,seed,7,.205,1)
    p2,r2,c2,l2,h2=_rosette(x+41*factor,y-29*factor,max(wh,ww)/25.4,seed+71,5,.132,2)
    ug=x/max(ww-1,1); vg=y/max(wh-1,1)
    vine=np.power(.5+.5*np.sin(2*np.pi*(45*ug+27*vg+.35*np.sin(2*np.pi*(3*ug-2*vg)))),17.0)
    weave_a=.5+.5*np.sin(2*np.pi*(62*ug+11*np.sin(2*np.pi*4*vg)))
    weave_b=.5+.5*np.sin(2*np.pi*(57*vg-9*np.sin(2*np.pi*3*ug)))
    # The secondary flower's tiny rim/leaf fields did not materially improve
    # the owner-eye carrier but consumed two full 2048² arrays. Keep its bud
    # and seed disc; remove only those redundant output buffers (I5.1).
    out=(p1,r1,c1,l1,p2,c2,vine,weave_a,weave_b,h1,h2)
    if factor < .999:
        out=tuple(_resize_array(a.astype(np.float32),h,w).astype(np.float32) for a in out)
    _CACHE[key]=tuple(a.astype(np.float32) for a in out)
    if len(_CACHE)>18:_CACHE.pop(next(iter(_CACHE)))
    return _CACHE[key]


def _mix(base,color,alpha):
    a=np.clip(alpha,0,1)[:,:,None]
    return base*(1-a)+np.asarray(color,np.float32)[None,None,:]*a


def _apply(paint,mask,color):
    if mask is not None and mask.size and float(mask.min())>=.999:return np.ascontiguousarray(color,dtype=np.float32)
    if paint.ndim==3 and paint.shape[2]>3:paint=paint[:,:,:3].copy()
    return (color*mask[:,:,None]+paint*(1-mask[:,:,None])).astype(np.float32)


def paint_flower_power(paint,shape,mask,seed,pm,bb):
    del pm,bb
    p1,r1,c1,l1,p2,c2,vine,wa,wb,h1,h2=_field(shape,seed)
    h,w=shape[:2]; col=np.empty((h,w,3),np.float32); col[:]=(.105,.23,.28) # peacock fabric
    col=_mix(col,(.07,.34,.31),vine*.37)                    # organic vine ink
    col=_mix(col,(.16,.27,.38),wa*.15)                      # quiet two-pass cloth
    # Print stations alternate palette subtly: pink/coral flowers beside blue
    # and violet, but every hue remains part of a visible flower pass.
    pink=p1*(.42+.42*h1); blue=p1*(.84-pink); coral=p2*(.45+.40*h2); violet=p2*(.86-coral)
    col=_mix(col,(.92,.13,.39),pink*.86); col=_mix(col,(.16,.62,.88),blue*.78)
    col=_mix(col,(.98,.38,.12),coral*.84); col=_mix(col,(.68,.20,.79),violet*.76)
    col=_mix(col,(.98,.73,.18),c1*.92); col=_mix(col,(.98,.88,.36),c2*.86)
    col=_mix(col,(.94,.62,.16),r1*.64); col=_mix(col,(.14,.75,.54),l1*.70)
    return _apply(paint,mask,np.clip(col,0,1))


def spec_flower_power(shape,seed,sm,base_m,base_r):
    del base_m,base_r
    p1,r1,c1,l1,p2,c2,vine,wa,wb,h1,h2=_field(shape,seed)
    # Satin petals, absorbent leaves and polished registration rims respond
    # independently; the fine cloth weave is visible in the paint itself.
    M=18+112*wa+106*np.clip(.26*p1+.19*r1+.17*c1+.16*p2+.13*vine+.09*l1,0,1)*sm
    R=238-116*wb-119*np.clip(.27*p1+.21*l1+.18*p2+.15*vine+.13*c1+.06*r1,0,1)
    CC=14+128*(.58*wa+.42*wb)+112*np.clip(.28*r1+.22*c1+.16*p1+.14*p2+.12*vine+.08*l1,0,1)
    return tuple(np.clip(a,0,255).astype(np.float32) for a in (M,R,CC))
