"""H1-I23 — Veiled Skull / mercury filigree, pass 1.

Fresh after I22: connected, jittered engraved rings/petals/lips built at a
768px canonical master. Every visible component lands in the 8--32px car band;
skull anatomy is only a redistribution of material cards.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
_C,_L,_W=OrderedDict(),RLock(),768
def _f(x):return x-np.floor(x)
def _h(x,y,s):return _f(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)

def _master(seed):
 y,x=np.mgrid[:_W,:_W].astype(np.float32);g=30.;gx,gy=np.floor(x/g),np.floor(y/g);near=np.full((_W,_W),1e6,np.float32);dx0=np.zeros_like(x);dy0=np.zeros_like(x);tag=np.zeros_like(x)
 # nearest jittered medallion, but ring anatomy is connected across cells
 # through its shared lipped seams; this is not a stamped or tiled pattern.
 for ox in (-1,0,1):
  for oy in (-1,0,1):
   ix,iy=gx+ox,gy+oy;jx=(_h(ix,iy,seed+11)-.5)*.48;jy=(_h(ix,iy,seed+29)-.5)*.48;dx=x-(ix+.5+jx)*g;dy=y-(iy+.5+jy)*g;d=dx*dx+dy*dy;take=d<near;near=np.where(take,d,near);dx0=np.where(take,dx,dx0);dy0=np.where(take,dy,dy0);tag=np.where(take,ix*41+iy*67,tag)
 stretch=.72+.58*_h(tag,gx+gy,seed+37);r=np.sqrt((dx0*stretch)**2+(dy0/stretch)**2);a=np.arctan2(dy0/stretch,dx0*stretch);phase=_h(tag,gx+gy,seed+47)*6.283
 # 8--26px native components: nested mercury rings, petal arcs, internal
 # engraving and tiny intersection pearls. Their widths never exceed 9px at
 # the master (24px on a car).
 ring1=np.exp(-((np.mod(r+2.2*np.sin(a*(2.0+2.5*_h(tag,gx+gy,seed+83))+phase),8.0)-4.0)/1.15)**2)
 ring2=np.exp(-((np.mod(r+1.5*np.sin(a*(3.0+4.0*_h(tag,gx+gy,seed+97))-phase),13.0)-6.5)/1.25)**2)
 petal=np.exp(-((np.sin(a*6+phase)/.34)**2)*((r-13.0)/7.5)**2)*np.exp(-((r-13.0)/8.5)**2)
 etch=np.exp(-((np.sin(.34*r+a*4.0+phase)/.24)**2)*((r-18.0)/9.0)**2)
 pearl=np.exp(-((np.mod(r,11.0)-5.5)/1.1)**2)*np.exp(-((np.sin(a*8-phase)/.27)**2))
 lip=np.clip(.44*ring1+.29*ring2+.18*petal+.13*etch,0,1);detail=np.clip(.45*pearl+.33*petal+.20*etch,0,1)
 tier=np.array((.17,.27,.38,.49,.60,.70,.81,.93),np.float32)[np.floor(_h(tag,gx+gy,seed+71)*8).astype(np.int32)]
 # The color is quiet lacquer, oxidized silver, violet enamel, and isolated
 # pearl—not a global gradient or a scatter of unrelated hues.
 z=np.zeros_like(x);body=np.stack((z+.075,z+.062,z+.105),2);silver=np.stack((z+.44,z+.52,z+.62),2);violet=np.stack((z+.35,z+.085,z+.48),2);teal=np.stack((z+.055,z+.29,z+.34),2)
 art=body+silver*(ring1*(.32+.28*tier))[...,None]+violet*(ring2*(.18+.21*tier))[...,None]+teal*(petal*(.14+.18*tier))[...,None]+silver*(pearl*(.24+.19*tier))[...,None]
 art=np.power(np.clip(art,0,1),.70)*.84+np.array((.024,.034,.062),np.float32)
 M=51+93*tier+52*ring1+31*petal-19*etch;R=202-91*tier-57*ring2+27*etch-16*pearl;C=34+96*tier+68*ring1+37*detail-18*etch
 # M/R/Cc-only skull assembly, repeated across the complete canvas.
 q=60.;GU,GV=np.floor(x/(q*.98)),np.floor(y/(q*1.03));jx=(_h(GU,GV,seed+113)-.5)*.18;jy=(_h(GU,GV,seed+137)-.5)*.18;X=(_f(x/(q*.98))-.5-jx)/.34;Y=(_f(y/(q*1.03))-.5-jy)/.37
 brow=np.exp(-((np.abs(X)-(.20+.16*np.clip(-Y,0,1)))/.064)**2)*np.exp(-((Y+.18)/.10)**2);orbit=np.exp(-((np.abs(np.abs(X)+.58*np.abs(Y)-.39)/.060)**2))*np.exp(-((Y+.01)/.30)**2);cheek=np.maximum(np.clip(1-np.abs((X-.27)/.17)-np.abs(Y/.14),0,1),np.clip(1-np.abs((X+.27)/.17)-np.abs(Y/.14),0,1));jaw=np.exp(-((np.abs(Y-.47)-(.20-.17*np.abs(X)))/.054)**2)*np.clip(1-np.abs(X)/.75,0,1);tooth=jaw*np.exp(-((np.sin(X*34)*.5+.5-.58)/.105)**2);nose=np.clip(1-np.abs(X/.095)-np.abs((Y-.13)/.155),0,1);crown=np.exp(-((np.abs(Y+.43)-(.10+.08*np.cos(X*18)))/.045)**2)*np.clip(1-np.abs(X)/.65,0,1);rel=np.clip(.75*brow+.70*orbit+.64*cheek+.62*jaw+.55*tooth+.64*nose+.32*crown,0,1);emph=_h(GU,GV,seed+151);hot=rel>(.34+.16*emph);cold=cheek>(.36+.12*(1-emph));glint=np.exp(-((np.abs(np.abs(X)-.21)/.047)**2+((Y+.02)/.055)**2))
 M=np.where(hot,np.clip(M+76,0,255),M);R=np.where(hot,np.clip(R-61,8,255),R);C=np.where(hot,np.clip(C+84,8,255),C);M=np.where(cold,np.clip(M-58,0,255),M);R=np.where(cold,np.clip(R+67,8,255),R);C=np.where(cold,np.clip(C-47,8,255),C);C=np.where(glint>.35,np.clip(C+72,8,255),C);R=np.where(glint>.35,np.clip(R-30,8,255),R)
 return np.clip(art,0,1).astype(np.float32),np.stack((M,R,C),2).clip(0,255).astype(np.uint8)
def _a(shape,seed):
 h,w=map(int,shape);k=(h,w,int(seed))
 with _L:
  if k in _C:_C.move_to_end(k);return _C[k]
 a,s=_master(seed)
 if (h,w)!=(_W,_W):mode=cv2.INTER_AREA if h<_W else cv2.INTER_LINEAR;a=cv2.resize(a,(w,h),interpolation=mode);s=cv2.resize(s,(w,h),interpolation=mode)
 out=(a.astype(np.float32),s.astype(np.uint8))
 with _L:_C[k]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_veiled_skull_i23(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*pm)[...,None];return np.clip(src*(1-m)+a*m,0,1).astype(np.float32)
def spec_veiled_skull_i23(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _a(shape,seed)[1]
