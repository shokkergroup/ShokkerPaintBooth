"""H10 Marble Rose I12 P1 — black-cherry chased damask; private Houdini reset.

Owner verdict on I11: a beautiful neutral is insufficient if grazing light only
turns it into generic flow texture.  I12 uses a non-flow, non-grid material:
an old lacquer panel with fine chase marks; its repeated rose relief exists
only in M/R/Cc.  The ~80px assemblies are built from 3–18px-native arcs.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock();TAU=np.float32(6.283185307179586)
def _h(a,b,s):return np.mod(np.sin(a*12.9898+b*78.233+s*37.719)*43758.5453,1.).astype(np.float32)
def _arr(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));y,x=np.mgrid[:hh,:ww].astype(np.float32);q=seed*.119
 # P1 carrier: crossed hairline chase work and low, calm lacquer depth.
 # The chase units are only 3–18 native px, never a dominant wallpaper block.
 u=x+.85*np.sin(y*.19+q)+.45*np.sin(x*.31-y*.14);v=y+.72*np.sin(x*.17-q)+.38*np.sin(y*.27+x*.11)
 t1=np.clip((.82-np.abs(np.sin((u*.74+v*.18)*.5)))/.82,0,1);t2=np.clip((.75-np.abs(np.sin((-u*.27+v*.81)*.62)))/.75,0,1);pin=(np.sin(u*1.93+v*.43)*np.sin(v*1.67-u*.31)>.91).astype(np.float32)
 body=.5+.5*np.sin(u*.071)*np.sin(v*.059);wine=np.array((.075,.006,.038),np.float32);ruby=np.array((.265,.018,.118),np.float32);mauve=np.array((.42,.060,.225),np.float32)
 # P3: reset the neutral to a readable black-cherry pearl—not a dark pattern.
 # Its restrained micro-pearls are physical 8–16px lacquer events; the roses
 # remain completely absent from RGB and are discovered only in material light.
 pearl=.5+.5*np.sin(u*1.21+np.sin(v*.37))*np.sin(v*1.08-u*.19)
 art=np.array((.115,.010,.052),np.float32)+np.array((.205,.020,.112),np.float32)*(.42+.33*body[...,None]);art+=np.array((.145,.040,.102),np.float32)*(pearl[...,None]*.22);art+=np.array((.23,.08,.16),np.float32)*pin[...,None]*.16;art=np.clip(art,0,1)
 # A staggered rosette lattice is merely a coordinate frame.  No tile edge is
 # ever painted: only six individually offset petal arcs are material events.
 px,py=27.,23.4;i=np.floor(u/px);j=np.floor(v/py);lx=(u-(i+.5+np.mod(j,2)*.5)*px)/(px*.43);ly=(v-(j+.5)*py)/(py*.48);rad=np.sqrt(lx*lx+ly*ly)+1e-5;ang=np.arctan2(ly,lx);ph=_h(i,j,seed)*TAU
 petals=np.exp(-((rad-(.48+.105*np.cos(6*ang+ph)))/.052)**2);inner=np.exp(-((rad-(.235+.045*np.cos(6*ang+ph+.7)))/.035)**2);rim=np.exp(-((rad-.70)/.028)**2);heart=np.exp(-(rad/.085)**2);rose=np.clip(.63*petals+.50*inner+.23*rim+.30*heart,0,1)
 # P3: reject P2's independent high-frequency phase confetti.  A controlled
 # pearl/chrome field provides ordinary lacquer variation; the rose is the sole
 # sharp material event and carries the Houdini reveal.
 # P5: P4's technically broad support became a stripe field.  Keep ordinary
 # lacquer states deliberately quiet; only the repeated multi-arc rose relief
 # owns the high contrast.  This is the literal Houdini light-reveal test.
 M=102+18*t1;R=166+15*t2;C=114+18*pin
 M=np.clip(M+150*rose,0,255);R=np.clip(R-132*rose,12,255);C=np.clip(C+143*rose,12,255)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);art=up(art);M,R,C=map(up,(M,R,C))
 out=(art.astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,12,255),np.clip(C,12,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i12(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_marble_rose_i12(shape,seed,sm,bm,br):del sm,bm,br;return _arr(shape,seed)[1]
