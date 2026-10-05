"""H1-I22 — Veiled Skull / opaline shard garden, pass 1.

SPB-HOUDINI-H1, owner 2026-08-31.  Fresh carrier after I21's cap rejection:
irregular 8--28px pearl, chrome, jade and oxidized-copper shards; no grid,
textile, or paint-layer skull art.
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
 y,x=np.mgrid[:_W,:_W].astype(np.float32);p=6.2;u=x/p;v=y/p;gx,gy=np.floor(u),np.floor(v);near=np.full((_W,_W),99.,np.float32);second=near.copy();dx0=np.zeros_like(x);dy0=np.zeros_like(x);cid=np.zeros_like(x)
 # Irregular local cells, never a regular mosaic: nearest 3x3 seeded point.
 for ox in (-1,0,1):
  for oy in (-1,0,1):
   cx,cy=gx+ox,gy+oy;jx=_h(cx,cy,seed+17);jy=_h(cx,cy,seed+43);dx=u-(cx+jx);dy=v-(cy+jy);d=dx*dx+dy*dy;take=d<near;second=np.where(take,near,np.minimum(second,d));near=np.where(take,d,near);dx0=np.where(take,dx,dx0);dy0=np.where(take,dy,dy0);cid=np.where(take,cx*37+cy*61,cid)
 dist=np.sqrt(near);gap=np.sqrt(second)-dist;facet=np.clip(1-dist/.84,0,1);seam=np.exp(-((gap-.095)/.047)**2);bevel=np.clip((.32-dist)*2.9,0,1)*(1-.55*seam)
 ang=np.arctan2(dy0,dx0);chip=np.clip(.60+.40*np.sin(3*ang+_h(cid,gx+gy,seed+59)*6.28),0,1)*facet
 tier=np.array((.17,.27,.38,.49,.60,.70,.81,.93),np.float32)[np.floor(_h(cid,gx+gy,seed+71)*8).astype(np.int32)]
 # Local pigment lives inside each fractured plate, while pearl lives on its
 # actual edge; no macro gradient or free sparkle field.
 hue=.5+.5*np.sin(.53*cid+.8*np.sin(cid*.17));night=np.stack((x*0+.040,x*0+.045,x*0+.105),2)
 jade=np.stack((.045+.065*hue,.22+.24*(1-hue),.50+.32*hue),2);copper=np.stack((.38+.30*hue,.055+.075*(1-hue),.33+.34*(1-hue)),2);pearl=np.stack((.53+.26*hue,.54+.22*(1-hue),.76+.18*hue),2)
 art=night+jade*(facet*(.22+.28*tier)*chip)[...,None]+copper*(facet*(.08+.18*tier)*(1-chip))[...,None]+pearl*(seam*.55+bevel*.32)[...,None]
 # I22-P2: card-scale lift of the continuous opaline body; shard geometry
 # and material-only relief stay exactly where P1 authored them.
 art=np.power(np.clip(art,0,1),.68)*.82+np.array((.028,.052,.070),np.float32)
 M=48+96*tier+49*seam+37*bevel-22*facet;R=205-94*tier-58*seam-39*bevel+20*facet;C=34+99*tier+63*seam+44*bevel-21*facet
 # Repeated 160px skull relief, built from fine brow/orbit/nose/cheek/jaw/
 # tooth/crown components.  It is absent from RGB art above.
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
def paint_veiled_skull_i22(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*pm)[...,None];return np.clip(src*(1-m)+a*m,0,1).astype(np.float32)
def spec_veiled_skull_i22(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _a(shape,seed)[1]
