"""H1-I16 — Obsidian prism territory / spec-only veiled skull.

Distinct Houdini carrier informed by the owner-approved Hologram lesson:
fine optical cells sit inside coherent regional territories.  It does not
reuse Hologram Metal's recipe or output; skull anatomy only offsets M/R/Cc.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np

_CACHE,_LOCK=OrderedDict(),RLock()
def _frac(a):return a-np.floor(a)
def _hash(x,y,s):return _frac(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)
def _up(a,w,h):return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)

def _arrays(shape,seed):
 h,w=map(int,shape);key=(h,w,int(seed))
 with _LOCK:
  if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
 sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));y,x=np.mgrid[:hh,:ww].astype(np.float32)
 # Fine 8–32px-native prism cell armature; broad regions drive colour travel.
 u=.82*x+.57*y;v=-.57*x+.82*y;side=8.4;fu,fv=np.mod(u,side)/side,np.mod(v,side)/side;gx,gy=np.floor(u/side),np.floor(v/side)
 rail=np.clip((.14-np.minimum.reduce((fu,1-fu,fv,1-fv)))/.14,0,1);diag=np.clip((.09-np.abs(fu-fv))/.09,0,1);facet=np.clip((.12-np.abs(fu+fv-1))/.12,0,1)
 # Coherent far-larger territories organize the cells, never become primitive art.
 field=.5+.5*np.sin(x*.017+y*.012+.8*np.sin(y*.009)+.4*np.sin(x*.026-y*.014));zone=np.digitize(field,(.25,.48,.70))
 # I16-I2: I1's territories showed as giant painted bands.  Keep regions as
 # an optical control field only; the neutral carrier stays black glass.
 base=np.empty((hh,ww,3),np.float32);base[...,0]=.048+.034*field;base[...,1]=.060+.050*(1-field);base[...,2]=.130+.090*field
 optic=np.array((.12,.74,.64),np.float32)*(zone[...,None]==1)+np.array((.54,.18,.70),np.float32)*(zone[...,None]==2)+np.array((.25,.28,.82),np.float32)*(zone[...,None]==3)
 # I16-I4: territory now changes the energy carried by the *same* fine
 # prisms—bright zones travel through the lattice instead of becoming bands.
 energy=.11+.30*field
 art=base*(1-rail[...,None]*.51)+optic*(rail[...,None]*energy[...,None]);art=art*(1-diag[...,None]*.18)+np.array((.38,.46,.78),np.float32)*(diag[...,None]*(.11+.12*field[...,None]));art=np.clip(art*(.91+.15*facet[...,None]),0,1)
 code=np.mod(19*gx+37*gy+5*gx*gy+int(seed),8).astype(np.int32);mt=np.array((58,92,134,176,218,244,38,202),np.float32)[code];rt=np.array((172,128,92,55,28,16,205,42),np.float32)[code];ct=np.array((72,110,150,190,226,246,42,214),np.float32)[code]
 M=mt+rail*25+diag*17;R=rt-rail*23+facet*13;C=ct+rail*34+diag*22
 # Repeated fine skull relief, spec only; relative material offsets preserve
 # the prism's own local state instead of painting a visible icon.
 step=32.;cx=(gx+.20+.60*_hash(gx,gy,seed+31))*side;cy=(gy+.18+.62*_hash(gx,gy,seed+47))*side;X=(u-cx)/(5.8+.7*_hash(gx,gy,seed+61));Y=(v-cy)/(6.9+.6*_hash(gx,gy,seed+79))
 brow=np.exp(-((np.abs(X)-(.20+.32*np.clip(-Y,0,1)))/.07)**2)*np.exp(-((Y+.25)/.14)**2);socket=np.exp(-((np.abs(np.abs(X)+.56*np.abs(Y)-.39)/.065)**2))*np.exp(-((Y+.02)/.34)**2);cav=np.maximum(np.clip(1-np.abs((X-.27)/.18)-np.abs(Y/.15),0,1),np.clip(1-np.abs((X+.27)/.18)-np.abs(Y/.15),0,1));jaw=np.exp(-((np.abs(Y-.49)-(.22-.20*np.abs(X)))/.06)**2)*np.clip(1-np.abs(X)/.74,0,1);teeth=jaw*np.exp(-((np.sin(X*27)*.5+.5-.60)/.13)**2);rel=np.clip(.72*brow+.67*socket+.62*jaw+.58*teeth,0,1);M0,R0,C0=M.copy(),R.copy(),C.copy();M=np.where(rel>.38,np.clip(M0+48,0,255),M);R=np.where(rel>.38,np.clip(R0-34,8,255),R);C=np.where(rel>.38,np.clip(C0+52,8,255),C);M=np.where(cav>.40,np.clip(M0-45,0,255),M);R=np.where(cav>.40,np.clip(R0+55,8,255),R);C=np.where(cav>.40,np.clip(C0-38,8,255),C);M=np.where(jaw>.43,np.clip(M0+29,0,255),M);R=np.where(jaw>.43,np.clip(R0-22,8,255),R);C=np.where(jaw>.43,np.clip(C0+34,8,255),C);M=np.where(teeth>.48,np.clip(M0-24,0,255),M);R=np.where(teeth>.48,np.clip(R0-25,8,255),R);C=np.where(teeth>.48,np.clip(C0-18,8,255),C)
 if(hh,ww)!=(h,w):art=_up(art,w,h);M,R,C=(_up(a,w,h) for a in(M,R,C))
 val=(art.astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,8,255),np.clip(C,8,255)),2).astype(np.uint8))
 with _LOCK:_CACHE[key]=val;_CACHE.popitem(last=False) if len(_CACHE)>2 else None
 return val
def paint_veiled_skull_i16(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=np.clip(m,0,1)[...,None]*pm;return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_veiled_skull_i16(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
