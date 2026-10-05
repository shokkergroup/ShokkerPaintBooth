"""H1-I24 — Veiled Skull / planished mercury, pass 1.

Uses the Foundry lesson (a surface is a physical process) but not a Foundry
recipe: an original fine planished mercury field and Houdini-only hidden relief.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
from engine.expansions import fractured_foundry_2026 as _foundry
_C,_L,_W=OrderedDict(),RLock(),768
def _f(x):return x-np.floor(x)
def _h(x,y,s):return _f(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)
def _master(seed):
 h,_,_=_foundry.s_planish(_W,int(seed)+173,facet=4.7);h=np.asarray(h,np.float32);blur=cv2.GaussianBlur(h,(0,0),2.1);lip=np.clip(np.abs(h-blur)*8.5,0,1);yy,xx=np.mgrid[:_W,:_W].astype(np.float32);micro=np.clip(.5+.5*np.sin(.86*xx+.23*yy+.8*np.sin(.11*yy)),0,1)
 # 8--22px hand-planish dishes, bright outer lips and dark mercury bowls.
 body=np.stack((.020+.050*h,.027+.060*h,.050+.095*h),2);silver=np.stack((.31+.24*h,.38+.25*h,.50+.26*h),2);violet=np.stack((.44+.30*micro,.035+.05*h,.57+.28*h),2);cyan=np.stack((.015+.05*h,.43+.31*h,.60+.31*micro),2);peak=np.clip((lip-.34)/.66,0,1);art=body+silver*(peak*.21)[...,None]+violet*(peak*(1-micro)*.58)[...,None]+cyan*(peak*micro*.58)[...,None]+violet*((1-lip)*np.clip(h-.56,0,1)*.15)[...,None];art=np.power(np.clip(art,0,1),.74)*.83+np.array((.014,.021,.040),np.float32)
 M=46+138*h+52*lip;R=214-132*h-58*lip;C=31+145*h+72*lip
 # 160px repeated skull relief: all marks are 9--24px sub-elements and never enter art.
 q=60.;GU,GV=np.floor(xx/(q*.98)),np.floor(yy/(q*1.03));jx=(_h(GU,GV,seed+113)-.5)*.18;jy=(_h(GU,GV,seed+137)-.5)*.18;X=(_f(xx/(q*.98))-.5-jx)/.34;Y=(_f(yy/(q*1.03))-.5-jy)/.37
 brow=np.exp(-((np.abs(X)-(.20+.16*np.clip(-Y,0,1)))/.064)**2)*np.exp(-((Y+.18)/.10)**2);orbit=np.exp(-((np.abs(np.abs(X)+.58*np.abs(Y)-.39)/.060)**2))*np.exp(-((Y+.01)/.30)**2);cheek=np.maximum(np.clip(1-np.abs((X-.27)/.17)-np.abs(Y/.14),0,1),np.clip(1-np.abs((X+.27)/.17)-np.abs(Y/.14),0,1));jaw=np.exp(-((np.abs(Y-.47)-(.20-.17*np.abs(X)))/.054)**2)*np.clip(1-np.abs(X)/.75,0,1);tooth=jaw*np.exp(-((np.sin(X*34)*.5+.5-.58)/.105)**2);nose=np.clip(1-np.abs(X/.095)-np.abs((Y-.13)/.155),0,1);crown=np.exp(-((np.abs(Y+.43)-(.10+.08*np.cos(X*18)))/.045)**2)*np.clip(1-np.abs(X)/.65,0,1);rel=np.clip(.75*brow+.70*orbit+.64*cheek+.62*jaw+.55*tooth+.64*nose+.32*crown,0,1);emph=_h(GU,GV,seed+151);hot=rel>(.34+.16*emph);cold=cheek>(.36+.12*(1-emph));glint=np.exp(-((np.abs(np.abs(X)-.21)/.047)**2+((Y+.02)/.055)**2))
 M=np.where(hot,np.clip(M+76,0,255),M);R=np.where(hot,np.clip(R-61,8,255),R);C=np.where(hot,np.clip(C+84,8,255),C);M=np.where(cold,np.clip(M-58,0,255),M);R=np.where(cold,np.clip(R+67,8,255),R);C=np.where(cold,np.clip(C-47,8,255),C);C=np.where(glint>.35,np.clip(C+72,8,255),C);R=np.where(glint>.35,np.clip(R-30,8,255),R)
 return np.clip(art,0,1).astype(np.float32),np.stack((M,R,C),2).clip(0,255).astype(np.uint8)
def _a(shape,seed):
 h,w=map(int,shape);k=(h,w,int(seed))
 with _L:
  if k in _C:_C.move_to_end(k);return _C[k]
 a,s=_master(seed)
 if(h,w)!=(_W,_W):mode=cv2.INTER_AREA if h<_W else cv2.INTER_LINEAR;a=cv2.resize(a,(w,h),interpolation=mode);s=cv2.resize(s,(w,h),interpolation=mode)
 out=(a.astype(np.float32),s.astype(np.uint8))
 with _L:_C[k]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_veiled_skull_i24(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*pm)[...,None];return np.clip(src*(1-m)+a*m,0,1).astype(np.float32)
def spec_veiled_skull_i24(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _a(shape,seed)[1]
