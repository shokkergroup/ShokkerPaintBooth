"""H1-I25 — Veiled Skull / black-mirror conchoid, pass 1."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
from engine.expansions import fractured_relics_2026 as _relics
_C,_L,_W=OrderedDict(),RLock(),768
def _f(x):return x-np.floor(x)
def _h(x,y,s):return _f(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)
def _master(seed):
 # Original Houdini palette/card logic over a true conchoidal process field.
 T0=np.asarray(_relics.g_obsidian(_W,int(seed)+281,shell=8.5,fine=.12),np.float32);T1=np.asarray(_relics.g_obsidian(_W,int(seed)+619,shell=5.9,fine=.10),np.float32);T=np.clip(.66*T0+.34*T1,0,1);yy,xx=np.mgrid[:_W,:_W].astype(np.float32);ridge=np.clip(np.abs(T-cv2.GaussianBlur(T,(0,0),2.4))*9.,0,1);flow=.5+.5*np.sin(8.0*T+2.6*ridge)
 void=np.stack((.010+.022*T,.014+.030*T,.030+.055*T),2);glass=np.stack((.045+.13*flow,.22+.34*T,.42+.42*flow),2);violet=np.stack((.26+.38*flow,.018+.038*T,.42+.42*T),2);pearl=np.stack((.48+.34*flow,.55+.28*T,.74+.26*flow),2);art=void+glass*(T*.52)[...,None]+violet*(np.clip(T-.31,0,1)*(.30+.32*flow))[...,None]+pearl*(ridge*.48)[...,None];art=np.power(np.clip(art,0,1),.72)*.84+np.array((.010,.018,.040),np.float32)
 M=36+134*T+58*ridge;R=222-129*T-63*ridge;C=24+145*T+77*ridge
 # Recurring intricate skull relief, M/R/Cc only.
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
def paint_veiled_skull_i25(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*pm)[...,None];return np.clip(src*(1-m)+a*m,0,1).astype(np.float32)
def spec_veiled_skull_i25(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _a(shape,seed)[1]
