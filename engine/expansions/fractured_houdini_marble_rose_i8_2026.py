"""H10-I8 Marble Rose P8 — formed garnet enamel / spec-only secret filigree.

Owner Houdini rebuild, 2026-08-31.  I7's contour terrain is rejected.  This is
an original formed micro-surface: 8–32px-native enamel pebbles with controlled
highlight lips, not noise.  The ornamental inlay changes M/R/Cc only.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _frac(x):return x-np.floor(x)
def _hash(x,y,s):return _frac(np.sin(x*127.1+y*311.7+s*71.3)*43758.5453)
def _arrays(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);sc=min(1.,896/max(h,w));hh,ww=max(192,round(h*sc)),max(192,round(w*sc));y,x=np.mgrid[:hh,:ww].astype(np.float32);pitch=10.8;gx,gy=np.floor(x/pitch),np.floor(y/pitch);best=np.full((hh,ww),1e8,np.float32);second=best.copy();bid=np.zeros((hh,ww),np.float32)
 # Nine-neighbour seeded enamel pools: each pool is a formed 12–24px native
 # element with a crown, a wet lip, and an interstitial seam.
 for ox,oy in ((0,0),(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)):
  ix,iy=gx+ox,gy+oy;px=(ix+.5+(_hash(ix,iy,seed)-.5)*.64)*pitch;py=(iy+.5+(_hash(ix,iy,seed+17)-.5)*.64)*pitch;d=(x-px)**2+(y-py)**2;hit=d<best;second=np.where(hit,best,np.minimum(second,d));best=np.where(hit,d,best);bid=np.where(hit,_hash(ix,iy,seed+31),bid)
 d1=np.sqrt(best);edge=np.clip((np.sqrt(second)-d1)/pitch,0,1);lip=np.exp(-((edge-.16)/.075)**2);crown=np.clip(1-d1/(pitch*.66),0,1)**1.8;seam=np.clip(1-edge*5,0,1)
 # Innocent whole-car carrier: almost-black garnet enamel with sparse wine
 # reflections tied to each physical pool, never an RGB hidden symbol.
 ink=np.array((.012,.006,.026),np.float32);wine=np.array((.085,.021,.165),np.float32);rose=np.array((.19,.055,.34),np.float32);pearl=np.array((.34,.21,.44),np.float32)
 shade=.22+.66*bid;paint=ink[None,None,:]*(.90+.10*seam[...,None])+wine[None,None,:]*(crown[...,None]*(.32+.42*shade[...,None]))+rose[None,None,:]*(lip[...,None]*(.21+.25*shade[...,None]))+pearl[None,None,:]*(lip[...,None]*(.10+.16*bid[...,None]))
 # Every formed pool owns one of eight local responses, causally bound to its lip.
 tier=np.clip((bid*8).astype(np.int32),0,7);M=np.array((38,57,78,101,126,153,183,214),np.float32)[tier]+lip*37+crown*18-seam*12;R=np.array((191,170,145,119,94,69,43,22),np.float32)[tier]-lip*31-crown*13+seam*16;C=np.array((62,85,111,142,173,205,231,249),np.float32)[tier]+lip*44+crown*18-seam*12
 # Hidden complex rose-window relief, repeated with stagger/jitter across the
 # entire canvas. Its 8–32px lobes are only state offsets atop local enamel.
 step=62.;rgx=np.floor(x/step);rgy=np.floor(y/step);cx=(rgx+.5)*step+(np.mod(rgy,2)*step*.5)+(_hash(rgx,rgy,seed+53)-.5)*10;cy=(rgy+.5)*step+(_hash(rgx,rgy,seed+67)-.5)*10;X=(x-cx)/18.;Y=(y-cy)/18.;rad=np.sqrt(X*X+Y*Y)+1e-6;ang=np.arctan2(Y,X);outer=np.exp(-((rad-(.54+.095*np.cos(8*ang)))/.070)**2);inner=np.exp(-((rad-(.26+.060*np.cos(4*ang+.6)))/.052)**2);cross=np.exp(-((np.minimum(np.abs(X),np.abs(Y))-.18)/.060)**2)*np.exp(-(rad/.79)**6);rel=np.clip(.69*outer+.58*inner+.34*cross,0,1);void=np.exp(-(rad/.10)**2)
 M0,R0,C0=M.copy(),R.copy(),C.copy();hot=rel>.42;M=np.where(hot,np.clip(M0+54,0,255),M);R=np.where(hot,np.clip(R0-43,12,255),R);C=np.where(hot,np.clip(C0+57,12,255),C);cut=void>.50;M=np.where(cut,np.clip(M0-38,0,255),M);R=np.where(cut,np.clip(R0+51,12,255),R);C=np.where(cut,np.clip(C0-34,12,255),C)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);paint=up(paint);M,R,C=map(up,(M,R,C))
 out=(np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,12,255),np.clip(C,12,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i8(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_marble_rose_i8(shape,seed,sm,bm,br):del sm,bm,br;return _arrays(shape,seed)[1]
