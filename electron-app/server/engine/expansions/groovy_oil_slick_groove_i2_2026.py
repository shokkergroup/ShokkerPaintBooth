"""Groovy Oil Slick Groove I2 — fine chromatic interference over black enamel.

SPB-105 / Oil Slick language, 2026-08-29. Dark carrier, 8–28px prismatic
grooves, black troughs, wet optical lips and microscopic mica highlights.
"""
import numpy as np
from engine.core import get_mgrid
_CACHE={}
def _field(shape,seed):
 key=(tuple(shape[:2]),int(seed))
 if key in _CACHE:return _CACHE[key]
 h,w=shape[:2];y,x=(a.astype(np.float32) for a in get_mgrid((h,w)));u=x/max(w-1,1);v=y/max(h-1,1)
 p=52*u+1.1*np.sin(2*np.pi*(2.0*v+.22*np.sin(2*np.pi*3*u)))+.32*np.sin(2*np.pi*(9*v-2*u+(seed%101)/101))
 f=p-np.floor(p);idx=np.floor(p).astype(np.int32)%8
 lip=np.power(.5+.5*np.cos(2*np.pi*f),18);edge=np.power(.5+.5*np.cos(2*np.pi*(f+.16)),30)
 trough=np.power(.5+.5*np.cos(2*np.pi*(f+.5)),15)
 shimmer=np.power(.5+.5*np.sin(2*np.pi*(x/7+y/13+(seed%97)/97)),34)*lip
 bead=np.power(.5+.5*np.sin(2*np.pi*(5*v+f*3)),18)*edge
 ans=tuple(np.ascontiguousarray(z,dtype=np.float32) for z in (idx,lip,edge,trough,shimmer,bead,f));_CACHE[key]=ans
 if len(_CACHE)>18:_CACHE.pop(next(iter(_CACHE)))
 return ans
def mix(a,c,t):
 t=np.clip(t,0,1)[:,:,None];return a*(1-t)+np.asarray(c,np.float32)[None,None,:]*t
def apply(paint,mask,c):
 if mask is not None and mask.size and float(mask.min())>=.999:return np.ascontiguousarray(c,dtype=np.float32)
 return (c*mask[:,:,None]+paint[:,:,:3]*(1-mask[:,:,None])).astype(np.float32)
def paint_oil_slick_groove(paint,shape,mask,seed,pm,bb):
 del pm,bb
 idx,lip,edge,trough,shimmer,bead,f=_field(shape,seed)
 pal=np.asarray(((.16,.04,.34),(.06,.25,.66),(.04,.57,.61),(.36,.07,.62),(.81,.05,.38),(.84,.31,.05),(.68,.72,.09),(.13,.48,.73)),np.float32)
 c=pal[idx.astype(np.int32)]*.78+np.asarray((.008,.006,.018),np.float32)*.22
 c=mix(c,(.004,.003,.010),trough*.88);c=mix(c,(.96,.88,.38),lip*.34);c=mix(c,(.92,.15,.62),edge*.38);c=mix(c,(.72,.96,1.),shimmer*.53);c=mix(c,(1.,.45,.10),bead*.32)
 return apply(paint,mask,np.clip(c,0,1))
def spec_oil_slick_groove(shape,seed,sm,base_m,base_r):
 del base_m,base_r
 idx,lip,edge,trough,shimmer,bead,f=_field(shape,seed);b=idx.astype(np.float32)/7
 M=15+91*b+142*np.clip(.26*lip+.23*edge+.20*trough+.17*shimmer+.14*bead,0,1)*sm
 R=242-105*b-142*np.clip(.28*trough+.21*edge+.19*lip+.17*bead+.15*shimmer,0,1)
 CC=10+141*(.58*f+.42*b)+113*np.clip(.27*shimmer+.23*lip+.20*edge+.17*bead+.13*trough,0,1)
 return tuple(np.clip(z,0,255).astype(np.float32) for z in (M,R,CC))
