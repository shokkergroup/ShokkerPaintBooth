"""H10-I11 Marble Rose P14 — native fine black-cherry filigree.

A new Houdini carrier after all macro/noise/cell branches failed.  RGB carries
only continuous fine forged filaments; its secret ornamental relief is M/R/Cc.
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
 h,w=map(int,shape);sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));y,x=np.mgrid[:hh,:ww].astype(np.float32);q=seed*.137
 # Four warped, fine filament families: 8–24px-native formed detail, no cells.
 u=.71*x+.66*y+12*np.sin(x*.043-y*.031+q)+6*np.sin(x*.119+y*.071)
 v=.91*x-.37*y+15*np.sin(x*.027+y*.046-q)+5*np.sin(x*.079-y*.093)
 z=.28*x+.96*y+11*np.sin(x*.052-y*.025+q*.5)
 # P19: native 2048 audit rejected P18's handsome but oversized contours.
 # Compress the authored coordinate field itself, so every filament, petal and
 # spec transition is genuinely 8–32px native—not a 1024 thumbnail illusion.
 u*=2.35;v*=2.35;z*=2.35
 a=np.clip((.24-np.abs(np.sin(u*.182)))/.24,0,1);b=np.clip((.19-np.abs(np.sin(v*.197)))/.19,0,1);c=np.clip((.13-np.abs(np.sin(z*.221)))/.13,0,1);body=.5+.5*np.sin(u*.010+np.sin(v*.017)*1.4);grain=.5+.5*np.sin(z*.089+u*.053)
 # P17: P16 showed a body lift was still too timid at real card scale. This
 # is a deliberate visible aubergine/cherry lacquer, not a generic brightening.
 ink=np.array((.035,.008,.062),np.float32);cherry=np.array((.165,.025,.220),np.float32);plum=np.array((.315,.064,.365),np.float32);silver=np.array((.42,.24,.54),np.float32)
 art=ink*(.78+.22*(1-body[...,None]))+cherry*(.26+.29*body[...,None]);art+=plum*(.18*a+.11*b+.05*c)[...,None];art+=silver*(.12*a+.075*b+.034*c)[...,None];art*=.91+.09*grain[...,None]
 # P16: the exact engine picker correctly exposed P15's near-black collapse.
 # Raise the coherent black-cherry lacquer body only; filament and secret
 # contrast are untouched so the material event remains a reveal, not paint.
 art=np.clip(art*.98+np.array((.016,.003,.022),np.float32),0,1)
 # Eight state family follows the filaments, but stays in a controlled range.
 d=np.clip(.44*a+.33*b+.18*c+.16*grain,0,1);state=np.clip((d*8).astype(np.int32),0,7)
 # P15: authored Fractured-adjacent states, not a bright-green roughness map.
 # Adjacent filaments trade wet pearl, chrome, dark lacquer, and pink coat.
 M=np.array((78,126,174,236,97,214,157,249),np.float32)[state]
 R=np.array((92,61,104,19,137,42,118,26),np.float32)[state]
 C=np.array((126,207,151,247,94,219,178,240),np.float32)[state]
 # P20: the prior dense field was good material but not an authored enough
 # Houdini secret.  Lay dozens of proper rose medallions over the whole carrier:
 # six small petal arcs, a jewel heart and a fine outer relief—not giant decals.
 step=22.;gx=np.floor(u/step);gy=np.floor(v/step);cx=(gx+.5)*step+np.sin(gx*8+gy*3+seed)*2.4;cy=(gy+.5)*step+np.sin(gx*3+gy*9+seed)*2.4;X=(u-cx)/(step*.42);Y=(v-cy)/(step*.42);rad=np.sqrt(X*X+Y*Y)+1e-5;ang=np.arctan2(Y,X);phase=.26*np.sin(gx*1.7+gy*.9+seed);petal=np.exp(-((rad-(.43+.122*np.cos(6*ang+phase)))/.045)**2);inner=np.exp(-((rad-(.245+.052*np.cos(6*ang+phase+.4)))/.031)**2);rim=np.exp(-((rad-.66)/.027)**2);jewel=np.exp(-(rad/.10)**2);rel=np.clip(.60*petal+.46*inner+.20*rim+.33*jewel,0,1);M0,R0,C0=M.copy(),R.copy(),C.copy();M=np.clip(M0+52*rel,0,255);R=np.clip(R0-43*rel,12,255);C=np.clip(C0+58*rel,12,255)
 if(hh,ww)!=(h,w):
  up=lambda t:cv2.resize(t.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);art=up(art);M,R,C=map(up,(M,R,C))
 out=(np.clip(art,0,1).astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,12,255),np.clip(C,12,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i11(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_marble_rose_i11(shape,seed,sm,bm,br):del sm,bm,br;return _arr(shape,seed)[1]
