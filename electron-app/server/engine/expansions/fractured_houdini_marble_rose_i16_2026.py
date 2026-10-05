"""Private H10 I16 P1 — black-cherry Damascus lacquer, Houdini state rearrangement.

H10 I11–I15 showed that decorative overlays do not become a material merely by
moving them to M/R/C.  I16 begins with a named, physical surface process:
fine folded Damascus layers, dark-etched troughs, polished shoulders, mica
specks and sparse broken-lacquer seams.  The hidden rose is a rearrangement of
the same local cards within that real anatomy, never RGB/decal artwork.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
from engine.expansions.fractured_foundry_2026 import s_damascus
_C,_L=OrderedDict(),RLock();TAU=np.float32(6.283185307179586)
def _h(a,b,s):return np.mod(np.sin(a*12.9898+b*78.233+s*37.719)*43758.5453,1.).astype(np.float32)
def _arr(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);work=max(320,min(768,max(h,w)));S,_,P=s_damascus(work,seed+119,layers=178.);S2,_,P2=s_damascus(work,seed+151,layers=164.);S=.57*S+.43*np.rot90(S2);P=.61*(P if P is not None else S)+.39*np.rot90(P2 if P2 is not None else S2);S=cv2.resize(np.asarray(S,np.float32),(w,h),interpolation=cv2.INTER_CUBIC);P=cv2.resize(np.asarray(P,np.float32),(w,h),interpolation=cv2.INTER_CUBIC);yy,xx=np.mgrid[:h,:w].astype(np.float32);q=seed*.151
 # Six crushed lacquer shades, all tied to the folded/etched steel structure.
 # The carrier is deliberately attractive without any hidden motif in paint.
 z=np.clip(.13+.72*S+.16*P,0,1);step=np.floor(z*6)/5.;art=np.empty((h,w,3),np.float32);art[...,0]=.055+.165*step;art[...,1]=.004+.020*step;art[...,2]=.024+.086*step;micro=(np.sin(xx*.78+yy*.21+q)*np.sin(yy*.71-xx*.18-q)>.84).astype(np.float32);art+=np.array((.045,.012,.030),np.float32)*micro[...,None];art=np.clip(art,0,1)
 # Fine physical marks: polished shoulders, etched troughs, mica islands,
 # broken-lacquer scratches and scarce chrome sparks.  All follow S/P rather
 # than being an unrelated generic overlay.
 shoulder=np.exp(-((S-.76)/.075)**2);trough=np.exp(-((S-.23)/.095)**2);mica=np.clip(P-.63,0,1)*micro;scratch=np.exp(-((np.sin(xx*.31+yy*.17+q))/.11)**2)*np.clip(.72-S,0,1);spark=(micro>0)*(S>.82)
 M=84+102*S+28*P+53*shoulder-48*trough+24*mica+31*scratch;R=142-72*S-19*P-61*shoulder+57*trough-29*mica+38*scratch;C=126-79*S-29*P-72*shoulder+58*trough-34*mica+45*scratch
 # Irregular rose discovery: not petals painted over a surface.  A few broad
 # probability regions reroute the existing shoulder/trough cards into curled
 # local sequences that may cohere under a moving reflection but remain absent
 # from albedo.  Components are 8–32px native arcs/folds/leaf cuts.
 cell=156.;u=xx+4*np.sin(yy*.017+q);v=yy+3*np.sin(xx*.020-q);gi,gj=np.floor(u/cell),np.floor(v/cell);best=np.full((h,w),9e7,np.float32);ang=np.zeros((h,w),np.float32);pick=np.zeros((h,w),np.float32)
 for oy in(-1,0,1):
  for ox in(-1,0,1):
   a,b=gi+ox,gj+oy;cx=a*cell+(.15+.72*_h(a,b,seed+9))*cell;cy=b*cell+(.16+.69*_h(a,b,seed+13))*cell;dx,dy=u-cx,v-cy;d=dx*dx+dy*dy;t=d<best;best=np.where(t,d,best);ang=np.where(t,np.arctan2(dy,dx)-TAU*_h(a,b,seed+17),ang);pick=np.where(t,_h(a,b,seed+23),pick)
 r=np.sqrt(best)+1e-4;a=np.mod(ang,TAU);curl=np.exp(-((r-(8+4.1*a))/2.7)**2)*(r<34.);fold=np.exp(-((r-(15+2.2*np.cos(3*a+.6)))/4.4)**2);leaf=np.exp(-((r-39)/4.8)**2)*np.clip(.48+.58*np.cos(2*a),0,1);active=(pick>.70).astype(np.float32);curl*=active;fold*=active;leaf*=active
 # Channel roles are deliberately offset: curl gets polished dark chrome,
 # fold is satin pearl, leaf is a coat-broken etched state.
 # P4: narrow adjacent-card shift only.  The event must stay buried in normal
 # viewing and let the already-rich folded-lacquer surface lead the finish.
 M=np.clip(M+48*curl+22*fold-27*leaf,0,255);R=np.clip(R-24*curl+19*fold+34*leaf,15,255)
 # P5: clearcoat anatomy is intentionally offset by 8 native pixels from its
 # metal/roughness partner.  This is a real lobe-separation test, not a tint.
 curl_c=np.roll(curl,8,axis=1);fold_c=np.roll(fold,-6,axis=0);leaf_c=np.roll(leaf,5,axis=0)
 C=np.clip(C-46*curl_c+67*fold_c+78*leaf_c,16,255)
 out=(art,np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i16(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_marble_rose_i16(shape,seed,sm,bm,br):del sm,bm,br;return _arr(shape,seed)[1]
