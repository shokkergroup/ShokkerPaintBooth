"""FRACTURED HOUDINI H1-I13 — Veiled Skull / black-glass lattice.

Separate Houdini carrier built from a dark glass lattice and multistate local
materials. Angular skull engravings only redirect those M/Rough/Cc states.
"""
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
from engine.expansions import impossible_hologram_noir_i1_2026 as _noir

_CACHE,_LOCK=OrderedDict(),RLock()
def _up(a,w,h):return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)
def _frac(a):return a-np.floor(a)
def _hash(x,y,s):return _frac(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)

def _arrays(shape,seed):
 h,w=map(int,shape);key=(h,w,int(seed))
 with _LOCK:
  if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
 # Canonical 768 work scale keeps picker and 2048² geometry consistent.
 sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));yy,xx=np.mgrid[:hh,:ww].astype(np.float32)
 # Independent black-glass lattice: cells, diagonals, fine rail scars, mica
 # nodes and broken film—five connected fine mark families.
 u=.866*xx+.50*yy;v=-.50*xx+.866*yy;side=5.4;fu=np.mod(u,side)/side;fv=np.mod(v,side)/side;ix=np.floor(u/side);iy=np.floor(v/side)
 rail=np.clip((.145-np.minimum.reduce((fu,1-fu,fv,1-fv)))/.145,0,1);diag=np.clip((.080-np.abs(fu-fv))/.080,0,1);slash=np.clip((.070-np.abs(fu+fv-1))/.070,0,1)
 node=np.exp(-(((fu-.5)/.095)**2+((fv-.5)/.095)**2));film=np.clip((.09-np.abs(np.sin(u*.63-v*.38)))*8.0,0,1)*.20
 # I13b — state assignment follows carrier anatomy, so optical variation has
 # a material cause instead of uniformly scattered bright packing.
 code=np.zeros((hh,ww),np.int32);code[film>.12]=1;code[rail>.22]=2;code[diag>.18]=3;code[slash>.16]=4;code[node>.30]=5;code[(rail>.56)&(diag>.24)]=6;code[(node>.24)&(slash>.13)]=7
 # I13d — the reveal mechanism works; give the innocent carrier a richer
 # graphite/indigo/violet body without placing any skull geometry in paint.
 graphite=np.array((.018,.026,.048),np.float32);navy=np.array((.038,.115,.225),np.float32);vio=np.array((.28,.060,.42),np.float32);teal=np.array((.030,.31,.34),np.float32);pearl=np.array((.50,.42,.68),np.float32)
 p=np.broadcast_to(graphite,(hh,ww,3)).copy();p=p*(1-rail[...,None]*.55)+navy*(rail[...,None]*.55);p=p*(1-diag[...,None]*.34)+vio*(diag[...,None]*.34);p=p*(1-slash[...,None]*.28)+teal*(slash[...,None]*.28);p=p*(1-node[...,None]*.38)+pearl*(node[...,None]*.38);p=np.clip(p*(.90+.17*(.5+.5*np.sin(u*.09+v*.07))[...,None]),0,1)
 # Angular repeated skull material engravings, no paint access.
 # I13c — raise the full connected event from ~60px to ~75px at 2048²,
 # while its brow/socket/jaw/tooth strokes remain in the 8–32px doctrine.
 step=50.;gx=np.floor(xx/step);gy=np.floor(yy/step);cx=(gx+.24+.52*_hash(gx,gy,17))*step;cy=(gy+.20+.56*_hash(gx,gy,39))*step;X=(xx-cx)/(10.0+.5*_hash(gx,gy,61));Y=(yy-cy)/(11.8+.5*_hash(gx,gy,83))
 brow=np.exp(-((np.abs(X)-(.19+.37*np.clip(-(Y+.08),0,1)))/.060)**2)*np.exp(-((Y+.31)/.17)**2);socket=np.exp(-((np.abs(np.abs(X)+np.abs(Y+.01)-.43)/.055)**2));hollow=np.maximum(np.clip(1-(np.abs((X+.29)/.18)+np.abs((Y+.01)/.14)),0,1),np.clip(1-(np.abs((X-.29)/.18)+np.abs((Y+.01)/.14)),0,1));jaw=np.exp(-((np.abs(Y-.57)-(.27-.27*np.abs(X)))/.055)**2)*np.clip(1-np.abs(X)/.7,0,1);teeth=jaw*np.exp(-((np.sin(X*28)*.5+.5-.57)/.12)**2);cheek=np.exp(-((np.abs(np.abs(X)-(.29+.18*(Y+.05)))/.055)**2))*np.clip((Y+.04)*2.2,0,1)
 mask=np.clip(brow*.90+socket*.82+jaw*.78+teeth*.74+cheek*.65,0,1)
 # Ten unzipped material cards: channel values are not a decorative ramp.
 mt=np.array((72,98,148,208,248,36,250,40),np.float32);rt=np.array((78,130,98,56,18,168,15,16),np.float32);ct=np.array((132,154,184,218,244,60,40,16),np.float32)
 M=mt[code]+rail*31+diag*18;R=rt[code]-rail*28+film*19;C=ct[code]+rail*36+slash*20
 # Skull anatomy changes adjacent physical states: mirrors on contours,
 # dead-film sockets, chrome jaw, clearcoat tooth flashes.
 M=np.where(mask>.13,250,M);R=np.where(mask>.13,46,R);C=np.where(mask>.13,244,C)
 M=np.where(hollow>.28,28,M);R=np.where(hollow>.28,211,R);C=np.where(hollow>.28,58,C)
 M=np.where(jaw>.25,248,M);R=np.where(jaw>.25,16,R);C=np.where(jaw>.25,40,C)
 M=np.where(teeth>.28,40,M);R=np.where(teeth>.28,16,R);C=np.where(teeth>.28,16,C)
 if (hh,ww)!=(h,w):p=_up(p,w,h);M,R,C=(_up(q,w,h) for q in (M,R,C))
 val=(p.astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255)),2).astype(np.uint8))
 with _LOCK:_CACHE[key]=val;_CACHE.popitem(last=False) if len(_CACHE)>2 else None
 return val
def paint_veiled_skull_i13(paint,shape,mask,seed,pm,bb):
 del bb
 art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m
 return np.clip(src*(1-np.clip(m,0,1)[...,None]*pm)+art*(np.clip(m,0,1)[...,None]*pm),0,1).astype(np.float32)
def spec_veiled_skull_i13(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r
 return _arrays(shape,seed)[1]
