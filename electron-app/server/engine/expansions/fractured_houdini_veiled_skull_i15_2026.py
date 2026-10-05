"""H1-I15: blackened forge-engraving skull relief.

New carrier family after I14: an actual worked titanium surface, using the
Foundry anisotropic shader.  The skull is a small repeated state choreography
inside the forged tooling and never enters RGB.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
from engine.expansions import fractured_foundry_kit_2026 as forge

_CACHE, _LOCK = OrderedDict(), RLock()
def _frac(a): return a - np.floor(a)
def _hash(x,y,s): return _frac(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)
def _up(a,w,h): return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)

def _arrays(shape, seed):
 h,w=map(int,shape); key=(h,w,int(seed))
 with _LOCK:
  if key in _CACHE: _CACHE.move_to_end(key); return _CACHE[key]
 sc=768/max(h,w); hh,ww=max(192,round(h*sc)),max(192,round(w*sc)); yy,xx=np.mgrid[:hh,:ww].astype(np.float32)
 # Forged cross-peen surface: 8–32px native hammer petals, chisel scars,
 # polishing lips, oxide pockets and mill tooth—five physical mark families.
 dx,dy,d,ident,d2=forge.cells(hh,8.2,seed+171,jit=.86)
 petal=np.clip(1-(d/4.1)**2,0,1); ridge=np.clip((1.20-np.abs(d2-d))/1.20,0,1)
 ang=np.arctan2(dy,dx); chisel=np.clip((.072-np.abs(np.sin(xx*.57+yy*.31+ident*8.0)))/.072,0,1)
 lip=np.clip((.19-np.abs(petal-.55))/.19,0,1); pocket=np.clip((.34-petal)/.34,0,1)
 height=np.clip(.40+.25*petal+.13*ridge+.10*chisel+.08*lip-.14*pocket,0,1)
 # I15-I2: I1 proved the forged surface, but its unbounded scalar detail
 # made the raw material map shout.  Soften the micro forge while retaining
 # its physical anisotropic travel for a quiet neutral-light carrier.
 recipe={"seed":int(seed)+73,"metal":"titanium","tooth":.14,"relief":9.6,"axis":.46,"aniso":.77,"gloss":.74,"rough":46,"clear":64,"wear":.36,"mvar":.98,"rvar":.74,"cvar":.74,"grime":.10,"heat":np.clip(petal*.72+ridge*.28,0,1),"heat_amt":.18,"temper_band":.40}
 art=forge.metal_art(height,recipe,hh); spec=forge.metal_spec(height,recipe,hh)[...,:3]
 # Recurring hidden skull: brow/socket/cheek/jaw/teeth are fine forged state
 # changes inside 72px-native assemblies. RGB art above is untouched.
 step=28.; gx,gy=np.floor(xx/step),np.floor(yy/step); cx=(gx+.2+.6*_hash(gx,gy,seed+31))*step; cy=(gy+.2+.6*_hash(gx,gy,seed+47))*step
 X=(xx-cx)/(6.3+.7*_hash(gx,gy,seed+61)); Y=(yy-cy)/(7.3+.7*_hash(gx,gy,seed+79))
 brow=np.exp(-((np.abs(X)-(.20+.33*np.clip(-Y,0,1)))/.07)**2)*np.exp(-((Y+.25)/.14)**2)
 socket=np.exp(-((np.abs(np.abs(X)+.55*np.abs(Y)-.38)/.065)**2))*np.exp(-((Y+.02)/.34)**2)
 cavity=np.maximum(np.clip(1-np.abs((X-.27)/.18)-np.abs(Y/.15),0,1),np.clip(1-np.abs((X+.27)/.18)-np.abs(Y/.15),0,1))
 jaw=np.exp(-((np.abs(Y-.49)-(.22-.20*np.abs(X)))/.06)**2)*np.clip(1-np.abs(X)/.74,0,1); teeth=jaw*np.exp(-((np.sin(X*27)*.5+.5-.60)/.13)**2)
 rel=np.clip(.72*brow+.67*socket+.62*jaw+.58*teeth,0,1)
 M,R,C=(spec[...,i].astype(np.float32) for i in range(3))
 # I15-I5: clearcoat travel belongs on the forge's actual polished lip and
 # dark oxide pocket, never on a separate decorative overlay.
 C=np.clip(C + lip*28.0 - pocket*18.0 + chisel*10.0,8,255)
 # I15-I4: material-relative offsets preserve forged continuity.  The relief
 # can only be read when light favors its adjacent chrome/velvet states.
 M0,R0,C0=M.copy(),R.copy(),C.copy()
 M=np.where(rel>.38,np.clip(M0+46,0,255),M); R=np.where(rel>.38,np.clip(R0-34,8,255),R); C=np.where(rel>.38,np.clip(C0+50,8,255),C)
 M=np.where(cavity>.40,np.clip(M0-44,0,255),M); R=np.where(cavity>.40,np.clip(R0+54,8,255),R); C=np.where(cavity>.40,np.clip(C0-36,8,255),C)
 M=np.where(jaw>.43,np.clip(M0+34,0,255),M); R=np.where(jaw>.43,np.clip(R0-23,8,255),R); C=np.where(jaw>.43,np.clip(C0+38,8,255),C)
 M=np.where(teeth>.47,np.clip(M0-26,0,255),M); R=np.where(teeth>.47,np.clip(R0-30,8,255),R); C=np.where(teeth>.47,np.clip(C0-18,8,255),C)
 if (hh,ww)!=(h,w): art=_up(art,w,h); M,R,C=(_up(a,w,h) for a in (M,R,C))
 val=(art.astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,8,255),np.clip(C,8,255)),2).astype(np.uint8))
 with _LOCK:
  _CACHE[key]=val
  if len(_CACHE)>2:_CACHE.popitem(last=False)
 return val

def paint_veiled_skull_i15(paint,shape,mask,seed,pm,bb):
 del bb; art,_=_arrays(shape,seed); src=np.asarray(paint,np.float32)[...,:3]; src=src/255. if src.max(initial=0)>1.5 else src; m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m; m=np.clip(m,0,1)[...,None]*pm
 return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_veiled_skull_i15(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r; return _arrays(shape,seed)[1]
