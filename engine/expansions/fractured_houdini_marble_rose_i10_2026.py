"""H10-I10 Marble Rose P10 — art-directed black-cherry lacquer carrier.

SPB-HOUDINI / owner 2026-08-31: isolated asset-backed trial after nine
procedural carriers failed the owner-eye gate.  The generated lacquer is only
the neutral carrier.  The repeating Houdini filigree is independently derived
as relative M/R/Cc changes; no symbol exists in RGB.
"""
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock();_ASSET=Path(__file__).resolve().parents[2]/'assets'/'generated'/'houdini'/'h10_black_cherry_lacquer_i10_2026.png'
def _arr(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);raw=cv2.imread(str(_ASSET),cv2.IMREAD_COLOR)
 if raw is None:raise RuntimeError('H10 I10 lacquer asset missing')
 bgr=cv2.resize(raw,(w,h),interpolation=cv2.INTER_CUBIC);art=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB).astype(np.float32)/255;gray=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY).astype(np.float32)/255;fine=np.abs(gray-cv2.GaussianBlur(gray,(0,0),1.4));body=np.abs(gray-cv2.GaussianBlur(gray,(0,0),8.5));lip=np.clip(2.8*fine+1.15*body,0,1);pocket=np.clip(1.0-gray*1.35+.18*(1-lip),0,1)
 # Car-readable lacquer lift, preserving the art-directed formed detail.
 paint=np.clip(art*.82+np.array((.025,.004,.034),np.float32)+np.repeat((lip*.075)[...,None],3,2),0,1)
 # P11 calibration: P10's quiet channels packed as a near-solid green card.
 # The carrier stays fixed; formed lips now move between polished pearl,
 # darker wet lacquer, and chrome-adjacent accents in the useful map range.
 detail=.31*gray+.49*lip+.20*body;detail=(detail-detail.min())/(np.ptp(detail)+1e-6)
 state=np.clip((detail*8).astype(np.int32),0,7)
 M=np.array((56,79,105,133,162,191,222,248),np.float32)[state]-pocket*14
 R=np.array((166,141,116,92,70,48,29,15),np.float32)[state]+pocket*16
 C=np.array((74,104,138,171,202,226,243,252),np.float32)[state]-pocket*12
 y,x=np.mgrid[:h,:w].astype(np.float32);step=max(36.,min(h,w)/20.);gx=np.floor(x/step);gy=np.floor(y/step);cx=(gx+.5)*step+(np.mod(gy,2)*step*.5)+np.sin(gx*7.1+gy*3.3+seed)*step*.09;cy=(gy+.5)*step+np.sin(gx*2.9+gy*8.7+seed)*step*.09;X=(x-cx)/(step*.31);Y=(y-cy)/(step*.31);rad=np.sqrt(X*X+Y*Y)+1e-6;ang=np.arctan2(Y,X)
 # A dense rosette engraving built from many short 8–32px-native arcs;
 # contrast is deliberately modest so it appears/disappears by light state.
 a=np.exp(-((rad-(.57+.085*np.cos(10*ang)))/.038)**2);b=np.exp(-((rad-(.32+.060*np.cos(5*ang+.55)))/.033)**2);c=np.exp(-((np.sin(5*ang+rad*14)-.80)/.13)**2)*np.exp(-((rad-.43)/.17)**2);rel=np.clip(.57*a+.48*b+.26*c,0,1);hot=rel>.43;M0,R0,C0=M.copy(),R.copy(),C.copy();M=np.where(hot,np.clip(M0+39,0,255),M);R=np.where(hot,np.clip(R0-31,12,255),R);C=np.where(hot,np.clip(C0+42,12,255),C)
 out=(paint.astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,12,255),np.clip(C,12,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i10(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_marble_rose_i10(shape,seed,sm,bm,br):del sm,bm,br;return _arr(shape,seed)[1]
