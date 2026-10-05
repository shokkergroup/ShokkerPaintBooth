"""H1-I17 — irregular black-opal prism relief (independent Houdini carrier)."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
_C,_L=OrderedDict(),RLock()
def _f(a):return a-np.floor(a)
def _h(x,y,s):return _f(np.sin(x*127.1+y*311.7+s*19.19)*43758.5453)
def _up(a,w,h):return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)
def _a(shape,seed):
 h,w=map(int,shape);k=(h,w,int(seed))
 with _L:
  if k in _C:_C.move_to_end(k);return _C[k]
 sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));y,x=np.mgrid[:hh,:ww].astype(np.float32);u=.81*x+.59*y;v=-.59*x+.81*y
 # Nonperiodic 2-D control field, only energizing the fine prisms below.
 r=np.random.default_rng(seed*1669+517);q=cv2.resize(r.random((29,37)).astype(np.float32),(ww,hh),interpolation=cv2.INTER_CUBIC);q=cv2.GaussianBlur(q,(0,0),12);q=(q-q.min())/max(q.max()-q.min(),1e-5)
 side=7.2;fu,fv=np.mod(u,side)/side,np.mod(v,side)/side;gx,gy=np.floor(u/side),np.floor(v/side);rail=np.clip((.13-np.minimum.reduce((fu,1-fu,fv,1-fv)))/.13,0,1);dia=np.clip((.085-np.abs(fu-fv))/.085,0,1);cross=np.clip((.10-np.abs(fu+fv-1))/.10,0,1)
 # Five connected physical marks: rails, diagonal cuts, cross facets, tiny
 # cells and dark opal field. Their colour strength—not their size—travels.
 ix,iy=np.floor(u/side),np.floor(v/side);z=np.digitize(q,(.28,.50,.72));local=np.mod(17*ix+29*iy+5*ix*iy+seed,4).astype(np.int32);state=np.mod(local+z*2,8).astype(np.int32);pal=np.array(((.050,.10,.20),(.05,.42,.44),(.34,.13,.62),(.12,.26,.74)),np.float32);dark=np.stack((.072+.042*q,.082+.060*(1-q),.170+.125*q),2);optic=pal[z];shoulder=np.clip(rail*.72+dia*.35+cross*.22,0,1);art=dark*(1-shoulder[...,None]*.49)+optic*(shoulder[...,None]*(.19+.32*q[...,None]));art=np.clip(art*(.94+.12*cross[...,None]),0,1)
 mt=np.array((66,104,146,190,228,246,42,208),np.float32)[state];rt=np.array((166,124,86,50,25,14,202,39),np.float32)[state];ct=np.array((76,116,158,196,230,248,44,220),np.float32)[state];M=mt+rail*28+dia*16;R=rt-rail*22+cross*13;C=ct+rail*36+dia*20
 # Repeat small skull assemblies throughout: all state-relative M/R/Cc only.
 step=30.;cx=(np.floor(u/step)+.22+.56*_h(np.floor(u/step),np.floor(v/step),seed+31))*step;cy=(np.floor(v/step)+.20+.59*_h(np.floor(u/step),np.floor(v/step),seed+47))*step;X=(u-cx)/6.0;Y=(v-cy)/7.0;b=np.exp(-((np.abs(X)-(.20+.32*np.clip(-Y,0,1)))/.07)**2)*np.exp(-((Y+.25)/.14)**2);s=np.exp(-((np.abs(np.abs(X)+.56*np.abs(Y)-.39)/.065)**2))*np.exp(-((Y+.02)/.34)**2);c=np.maximum(np.clip(1-np.abs((X-.27)/.18)-np.abs(Y/.15),0,1),np.clip(1-np.abs((X+.27)/.18)-np.abs(Y/.15),0,1));j=np.exp(-((np.abs(Y-.49)-(.22-.20*np.abs(X)))/.06)**2)*np.clip(1-np.abs(X)/.74,0,1);t=j*np.exp(-((np.sin(X*27)*.5+.5-.60)/.13)**2);rel=np.clip(.72*b+.67*s+.62*j+.58*t,0,1);M0,R0,C0=M.copy(),R.copy(),C.copy();M=np.where(rel>.38,np.clip(M0+45,0,255),M);R=np.where(rel>.38,np.clip(R0-33,8,255),R);C=np.where(rel>.38,np.clip(C0+48,8,255),C);M=np.where(c>.40,np.clip(M0-42,0,255),M);R=np.where(c>.40,np.clip(R0+53,8,255),R);C=np.where(c>.40,np.clip(C0-34,8,255),C)
 if(hh,ww)!=(h,w):art=_up(art,w,h);M,R,C=(_up(a,w,h) for a in(M,R,C))
 out=(np.clip(art,0,1).astype(np.float32),np.stack((np.clip(M,0,255),np.clip(R,8,255),np.clip(C,8,255)),2).astype(np.uint8))
 with _L:_C[k]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_veiled_skull_i17(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_a(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=np.clip(m,0,1)[...,None]*pm;return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_veiled_skull_i17(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _a(shape,seed)[1]
