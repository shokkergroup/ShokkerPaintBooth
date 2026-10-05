"""H10-I9 Marble Rose P9 — black-cherry lacquer, hidden guilloché relief.

Owner Houdini rebuild, 2026-08-31.  No flower sprites, cells, contours, or
RGB motif art.  The carrier is restrained optical lacquer; the reveal is dense
repeated guilloché made of 8–32px material-only line components.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _arr(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);sc=min(1.,896/max(h,w));hh,ww=max(192,round(h*sc)),max(192,round(w*sc));y,x=np.mgrid[:hh,:ww].astype(np.float32)
 # Innocent optical lacquer: 8–20px parallel curl marks under a deep cherry
 # glaze.  A broad tone field makes the whole-car card hold at picker scale.
 u=.84*x+.54*y;v=-.54*x+.84*y;roll=.5+.5*np.sin(u*.064+.85*np.sin(v*.027));fine=.5+.5*np.sin(u*.41+.55*np.sin(v*.13));glow=.5+.5*np.sin(x*.010+y*.008)
 ink=np.array((.010,.004,.022),np.float32);cherry=np.array((.090,.014,.128),np.float32);rose=np.array((.235,.040,.255),np.float32);paint=ink*(1-glow[...,None])+cherry*glow[...,None];paint=paint*(1-(.055*fine)[...,None])+rose*(.055*fine)[...,None];paint*=.91+.09*roll[...,None]
 # Eight quiet material neighbourhoods: enough adjacent state variation to
 # travel under light, but none of the background becomes a diagnostic rainbow.
 t=np.mod(np.floor((u*.055+v*.037+roll*6+fine*3)),8).astype(np.int32);M=np.array((68,82,97,113,130,148,167,187),np.float32)[t];R=np.array((154,139,123,108,92,77,62,47),np.float32)[t];C=np.array((88,109,132,156,180,204,226,246),np.float32)[t]
 # A staggered field of complex rosette/guilloché reliefs.  Each motif spans
 # many 8–24px loops; no one large design is relied on to land on a car panel.
 step=74.;gx=np.floor(u/step);gy=np.floor(v/step);cx=(gx+.5)*step+(np.mod(gy,2)*step*.5)+np.sin(gx*7.3+gy*2.7+seed)*7;cy=(gy+.5)*step+np.sin(gx*3.1+gy*8.9+seed)*7;X=(u-cx)/25.;Y=(v-cy)/25.;rad=np.sqrt(X*X+Y*Y)+1e-6;ang=np.arctan2(Y,X)
 # Nested 9/13-lobe curved engraving and a narrow outer chain are ornate at
 # full canvas scale, while remaining wholly within spec-state logic.
 p1=np.exp(-((rad-(.48+.105*np.cos(9*ang+.35*np.sin(3*ang))))/.040)**2);p2=np.exp(-((rad-(.76+.065*np.cos(13*ang-.42)))/.032)**2);p3=np.exp(-((rad-(.24+.052*np.cos(5*ang+.8)))/.030)**2);link=np.exp(-((np.sin(4*ang+rad*11)-.78)/.16)**2)*np.exp(-((rad-.61)/.16)**2);fil=np.clip(.64*p1+.50*p2+.48*p3+.28*link,0,1)
 # Offset the local material state instead of assigning a universal pink tile.
 M0,R0,C0=M.copy(),R.copy(),C.copy();hot=fil>.37;M=np.where(hot,np.clip(M0+55+12*roll,0,255),M);R=np.where(hot,np.clip(R0-44-8*fine,12,255),R);C=np.where(hot,np.clip(C0+61+10*roll,12,255),C);pocket=(p3>.45);M=np.where(pocket,np.clip(M0-32,0,255),M);R=np.where(pocket,np.clip(R0+46,12,255),R);C=np.where(pocket,np.clip(C0-29,12,255),C)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);paint=up(paint);M,R,C=map(up,(M,R,C))
 out=(np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,12,255),np.clip(C,12,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i9(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_marble_rose_i9(shape,seed,sm,bm,br):del sm,bm,br;return _arr(shape,seed)[1]
