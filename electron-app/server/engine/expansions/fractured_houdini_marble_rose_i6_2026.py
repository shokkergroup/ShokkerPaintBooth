"""H10-I6 Marble Rose P3 — garnet tesserae with relative hidden rosette relief.

SPB-HOUDINI / owner 2026-08-31.  I5 proved dense components but its fixed
hot-pink petal states were too literal.  Here the paint is only a coherent
fine enamel; rose relief offsets each local material neighbourhood instead.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np
_C,_L=OrderedDict(),RLock()
def _frac(a): return a-np.floor(a)
def _hash(a,b,s): return _frac(np.sin(a*127.1+b*311.7+s*19.19)*43758.5453)
def _up(a,w,h): return cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC)

def _arrays(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));y,x=np.mgrid[:hh,:ww].astype(np.float32)
 # Fine 8–24px-native tesserae; broad field only controls travel, never art.
 u=.91*x+.41*y;v=-.41*x+.91*y;side=8.6;fu,fv=np.mod(u,side)/side,np.mod(v,side)/side;gx,gy=np.floor(u/side),np.floor(v/side)
 rail=np.clip((.15-np.minimum.reduce((fu,1-fu,fv,1-fv)))/.15,0,1);diag=np.clip((.085-np.abs(fu+fv-1))/.085,0,1)
 field=.5+.5*np.sin(x*.021+y*.014+.75*np.sin(y*.011)+.35*np.sin(x*.031-y*.019));grain=.5+.5*np.sin(x*.83-y*.57+field*5)
 # BGR order is deliberate because the material carrier is written by OpenCV.
 dark=np.array((.030,.012,.078),np.float32);garnet=np.array((.105,.028,.315),np.float32);rose=np.array((.155,.061,.470),np.float32)
 art=dark*(1-field[...,None])+garnet*field[...,None];art=art*(1-(.12*grain)[...,None])+rose*(.12*grain)[...,None]
 art=art*(1-rail[...,None]*.42)+np.array((.31,.12,.62),np.float32)*(rail[...,None]*(.10+.12*field[...,None]));art=np.clip(art*(.93+.11*diag[...,None]),0,1)
 # P6: P5's full-range field made its background into cyan band art.  Keep
 # all eight local material shades inside one sober garnet neighbourhood;
 # only the hidden rosette may cross into an extreme response state.
 tier=np.mod(np.floor((gx*13+gy*31+field*7+grain*3+seed)*1.7),8).astype(np.int32)
 M=np.array((81,91,102,113,124,135,147,159),np.float32)[tier]+field*12+rail*8
 R=np.array((150,139,129,118,108,97,87,76),np.float32)[tier]-field*9+diag*6
 C=np.array((112,126,141,156,171,186,201,216),np.float32)[tier]+field*14+rail*10
 # P4: I6-P3 incorrectly centered a relief in *every* tessera, so no rose
 # could resolve.  These are full-canvas, staggered 54px cells (108px native)
 # assembled from the same 8–24px tesserae; RGB remains entirely innocent.
 step=54.;rgx=np.floor(u/step);rgy=np.floor(v/step);cx=(rgx+.5)*step+(np.mod(rgy,2)*step*.5)+(_hash(rgx,rgy,seed+9)-.5)*8;cy=(rgy+.5)*step+(_hash(rgx,rgy,seed+23)-.5)*8;X=(u-cx)/(17.6+.8*_hash(rgx,rgy,seed+37));Y=(v-cy)/(17.6+.8*_hash(rgx,rgy,seed+41));rad=np.sqrt(X*X+Y*Y)+1e-5;ang=np.arctan2(Y,X)
 petals=np.exp(-((rad-(.42+.14*np.cos(6*ang)))/.115)**2)*np.exp(-(rad/1.03)**6);inner=np.exp(-((rad-(.18+.055*np.cos(5*ang+.45)))/.060)**2);core=np.exp(-(rad/.105)**2);leaf=np.exp(-((np.abs(Y-.73)-(.15+.20*np.abs(X)))/.075)**2)*np.clip(1-np.abs(X)/.75,0,1)
 rel=np.clip(.72*petals+.63*inner+.48*leaf,0,1);cut=np.clip(.70*core+.56*np.exp(-((rad-.58)/.055)**2),0,1)
 M0,R0,C0=M.copy(),R.copy(),C.copy();M=np.where(rel>.38,np.clip(M0+61+18*field,0,255),M);R=np.where(rel>.38,np.clip(R0-48-13*field,12,255),R);C=np.where(rel>.38,np.clip(C0+68+19*field,12,255),C);M=np.where(cut>.43,np.clip(M0-47,0,255),M);R=np.where(cut>.43,np.clip(R0+60,12,255),R);C=np.where(cut>.43,np.clip(C0-43,12,255),C)
 if(hh,ww)!=(h,w):art=_up(art,w,h);M,R,C=(_up(z,w,h) for z in(M,R,C))
 out=(art.astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,12,255),np.clip(C,12,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i6(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_marble_rose_i6(shape,seed,sm,bm,br):
 del sm,bm,br;return _arrays(shape,seed)[1]
