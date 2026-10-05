"""FRACTURED HOUDINI H1-I12 — Veiled Skull / thornweave reliquary.

Dark woven-metal paint with irregular short bundles and stitched seams.  Hidden
skulls are angular material engraving assemblies, repeated full-canvas only in
M/Rough/Cc: brow chevrons, diamond sockets, cheek cuts, jaw rails and teeth.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock();_WORK=576
def _up(a,w,h):return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)
def _frac(a):return a-np.floor(a)
def _hash(x,y,s):return _frac(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)

def _arrays(shape,seed):
 h,w=map(int,shape);key=(h,w,int(seed))
 with _LOCK:
  if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
 sc=_WORK/max(h,w);hh,ww=max(160,round(h*sc)),max(160,round(w*sc));yy,xx=np.mgrid[:hh,:ww].astype(np.float32);sd=float(int(seed)^0x12A6)
 # Visible carrier: non-circular short thorn bundles, diagonal seam crossings,
 # mica peen points, grain cuts and dark interlaced pockets.
 cell=6.4;qx=np.floor(xx/cell);qy=np.floor(yy/cell);fx=_frac(xx/cell)-.5;fy=_frac(yy/cell)-.5;u=fx*.78+fy*.62;v=-fx*.62+fy*.78
 salt=_hash(qx,qy,sd);stripe=np.exp(-(v/.075)**2)*np.exp(-((np.abs(u)-.19)/.17)**2)
 cross=np.exp(-((u/.060)**2))*np.exp(-((np.abs(v)-.18)/.15)**2)*(.35+.65*(salt>.48))
 thorn=np.exp(-((np.abs(fx)-(.20+.10*salt+.16*fy))/.052)**2)*np.exp(-((fy+.07)/.22)**2)
 seam=np.exp(-((np.abs(np.sin(xx*.43-yy*.31+np.sin(yy*.09)*1.7))-.94)/.045)**2)*.30
 peen=np.exp(-(((fx-(salt-.5)*.30)/.052)**2+((fy-(_hash(qx,qy,sd+9)-.5)*.27)/.052)**2))
 weave=np.clip(stripe*.58+cross*.36+thorn*.52+seam+peen*.45,0,1);edge=np.clip(stripe+thorn*.70+cross*.55,0,1);pit=np.clip(peen*.55+seam*.65,0,1)
 void=np.array((.010,.018,.025),np.float32);steel=np.array((.050,.115,.135),np.float32);teal=np.array((.020,.24,.25),np.float32);vio=np.array((.20,.080,.30),np.float32);pearl=np.array((.36,.34,.44),np.float32);black=np.array((.004,.007,.012),np.float32)
 paint=np.broadcast_to(void,(hh,ww,3)).copy();paint=paint*(1-weave[...,None]*.72)+steel*(weave[...,None]*.72);paint=paint*(1-stripe[...,None]*.48)+teal*(stripe[...,None]*.48);paint=paint*(1-thorn[...,None]*.42)+vio*(thorn[...,None]*.42);paint=paint*(1-peen[...,None]*.52)+pearl*(peen[...,None]*.52);paint=paint*(1-pit[...,None]*.63)+black*(pit[...,None]*.63);paint=np.clip(paint*(.90+.17*(.5+.5*np.sin(xx/53+yy/61))[...,None]),0,1)
 # Vectorized jittered angular skull construction. Motifs are ~55px native,
 # made from fine 4–28px parts and repeated every ~155px over the sheet.
 # I12d — the prior 55px assembly vanished in whole-car grazing evidence.
 # Each stroke remains fine, but the repeated connected event grows to ~70px.
 step=50.;gx=np.floor(xx/step);gy=np.floor(yy/step);cx=(gx+.22+.56*_hash(gx,gy,sd+21))*step;cy=(gy+.20+.58*_hash(gx,gy,sd+37))*step;X=(xx-cx)/(8.8+.7*_hash(gx,gy,sd+51));Y=(yy-cy)/(10.2+.7*_hash(gx,gy,sd+67))
 brow=np.exp(-((np.abs(X)-(.20+.36*np.clip(-(Y+.08),0,1)))/.065)**2)*np.exp(-((Y+.31)/.18)**2)
 socket=np.exp(-((np.abs(np.abs(X)+np.abs(Y+.02)-.43)/.060)**2))*np.clip(1-(np.abs(X)/.62),0,1)
 hollow=np.maximum(np.clip(1-(np.abs((X+.29)/.19)+np.abs((Y+.01)/.15)),0,1),np.clip(1-(np.abs((X-.29)/.19)+np.abs((Y+.01)/.15)),0,1))
 nose=np.exp(-((np.abs(X)+np.abs(Y-.27)-.15)/.055)**2);cheek=np.exp(-((np.abs(np.abs(X)-(.28+.19*(Y+.05)))/.060)**2))*np.clip((Y+.06)*2.0,0,1)
 jaw=np.exp(-((np.abs(Y-.57)-(.27-.28*np.abs(X)))/.060)**2)*np.clip(1-np.abs(X)/.70,0,1);teeth=jaw*np.exp(-((np.sin(X*27)*.5+.5-.57)/.13)**2)
 crown=np.exp(-((np.abs(Y+.69)-(.13+.28*np.abs(X)))/.055)**2)*np.clip(1-np.abs(X)/.72,0,1)
 # I12e — the outline-only event did not resolve under grazing light. A quiet
 # spec-only face plane lets the fine engraving read as one material event;
 # sockets/jaw/teeth still break that plane into authored anatomy.
 face=np.clip(1-(X*X+((Y+.08)/.93)**2),0,1)
 skull=np.clip(np.maximum(face*.32,brow*.86+socket*.84+cheek*.62+jaw*.75+teeth*.72+crown*.63+nose*.58),0,1)
 # Hologram-proven state family, assigned causally to carrier and engraving.
 # I12b — quiet violet-metal ground; independent carrier anatomy, not a
 # blanket hot-pink card, creates the material hierarchy and channel spread.
 state=np.zeros((hh,ww),np.int32);state[weave>.20]=2;state[pit>.22]=1;state[stripe>.23]=3;state[thorn>.28]=4;state[edge>.56]=6;state[peen>.42]=5;state[(peen>.26)&(thorn>.20)]=7
 secret=np.where(hollow>.28,1,np.where(jaw>.26,6,np.where(teeth>.28,7,4)));state=np.where(skull>.13,secret,state)
 # I12c — independent physical roles: satin woven ground, porous pockets,
 # buried rose metal, hot thorn exposure, chipped film, flake and chrome lip.
 M=np.array((136,28,196,232,72,220,248,40),np.float32)
 R=np.array((130,184,86,34,156,66,15,16),np.float32)
 C=np.array((116,62,174,218,104,164,40,16),np.float32);metal=M[state];rough=R[state];coat=C[state]
 if (hh,ww)!=(h,w):paint=_up(paint,w,h);metal,rough,coat=(_up(q,w,h) for q in (metal,rough,coat))
 val=(paint.astype(np.float32),np.stack((np.clip(metal,0,255),np.clip(rough,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
 with _LOCK:_CACHE[key]=val;_CACHE.popitem(last=False) if len(_CACHE)>2 else None
 return val
def paint_veiled_skull_i12(paint,shape,mask,seed,pm,bb):
 del bb
 art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
 return np.clip(src*(1-np.clip(m,0,1)[...,None]*pm)+art*(np.clip(m,0,1)[...,None]*pm),0,1).astype(np.float32)
def spec_veiled_skull_i12(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r
 return _arrays(shape,seed)[1]
