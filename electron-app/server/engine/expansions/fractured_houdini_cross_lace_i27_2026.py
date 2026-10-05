"""Private Houdini I27 — Cross Lace, P1. Material-only ornate cruciform field."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2
import numpy as np
_CACHE,_LOCK=OrderedDict(),RLock();_TAU=np.float32(6.283185307179586)
def _h(i,j,s):return np.mod(np.sin(i*127.1+j*311.7+s*73.9)*43758.5453,1.).astype(np.float32)
def _ell(x,y,sx,sy):return np.exp(-((x/sx)**2+(y/sy)**2)).astype(np.float32)
def _arrays(shape,seed):
 key=(*map(int,shape),int(seed))
 with _LOCK:
  if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
 h,w=map(int,shape);s=min(1.,1024./max(h,w));hh,ww=max(256,round(h*s)),max(256,round(w*s));yy,xx=np.mgrid[:hh,:ww].astype(np.float32);X,Y=xx/s,yy/s;ph=(seed%7919)*.00071
 # Innocent onyx-satin carrier: fine cloth ribs, lace tooth and deep blue tide.
 u=(X*.94+Y*.34+2*np.sin(Y*.015+ph))/7.3;v=(X*.34-Y*.94+2*np.sin(X*.013-ph))/9.1
 rib=.5+.5*np.sin(u*_TAU);weft=.5+.5*np.sin(v*_TAU);satin=np.clip(.52*rib+.37*weft+.22*rib*weft,0,1);tide=.5+.5*np.sin(X*.009-Y*.012+ph)
 # P4 — add fine sapphire/graphite interference to the real satin threads;
 # the hidden cruciform geometry remains absent from ordinary paint.
 shimmer=.5+.5*np.sin(X*.193-Y*.147+.62*np.sin(X*.028+Y*.021))
 paint=np.dstack((.061+.054*satin+.018*tide+.016*shimmer,.037+.032*satin+.011*tide+.007*shimmer,.028+.024*satin+.007*tide+.010*(1-shimmer)))
 # Repeated ornate cruciform settings. The complete cross is 42x47px but all
 # physical bar, lobe, bezel and cut components remain 4–28px.
 dx=3.4*np.sin(Y*.011+ph)+1.8*np.sin((X+Y)*.008-ph);dy=3*np.sin(X*.013-ph)-1.5*np.sin((X-Y)*.010+ph);GX,GY=(X+dx)/84.,(Y+dy)/86.;ci,cj=np.floor(GX),np.floor(GY)
 cx=ci+.5+(_h(ci,cj,seed+13)-.5)*.46+.12*np.sin(cj*1.23+ci*.39+ph);cy=cj+.5+(_h(ci,cj,seed+27)-.5)*.44+.11*np.sin(ci*1.19-cj*.47-ph)
 qx,qy=(GX-cx)*84.,(GY-cy)*86.;a=(_h(ci,cj,seed+43)-.5)*.70;ca,sa=np.cos(a),np.sin(a);qx,qy=qx*ca+qy*sa,-qx*sa+qy*ca;setting=.88+.22*_h(ci,cj,seed+61);qx,qy=qx/setting,qy/setting
 # P3 — distinguish every setting's vertical/horizontal proportion; all
 # pieces remain fine but the field no longer uses one stamped silhouette.
 vs=.78+.42*_h(ci,cj,seed+151);hs=.76+.44*_h(ci,cj,seed+163)
 vert=_ell(qx,qy+1.0,4.5,20.0*vs);horiz=_ell(qx,qy-2.0,18.0*hs,4.5);bar=np.maximum(vert,horiz)
 # Four terminal lobes and a ringed bezel turn a plain plus into ornate lace.
 lobes=np.maximum.reduce((_ell(qx,qy-19,6,5),_ell(qx,qy+18,6,5),_ell(qx-18,qy-2,5,6),_ell(qx+18,qy-2,5,6)))
 center=_ell(qx,qy-2,7.5,7.5);r=np.hypot(qx,qy+2);bezel=np.exp(-((r-12.5)/1.5)**2);cut=(.5+.5*np.sin((qx-qy)*1.2+_h(ci,cj,seed+83)*6))*bar
 lace=np.clip(.74*bar+.56*lobes+.63*center+.50*bezel+.22*cut,0,1)
 # Cruciform exists only as M/R/C roles. Paint above never reads `lace`.
 # P2 — P1 accidentally multiplied the normal weave's metallic delta and
 # made every cross a bright stamp. Let the bezel and fine cuts lead instead.
 delta=21*(rib-weft);M=68+31*satin+.35*delta;R=176-35*satin+delta;C=160-30*satin+.83*delta
 lobe_history=.26+.74*_h(ci,cj,seed+109)
 # P5 — do not activate a wallpaper. The same cross anatomy has a local
 # plating depth so forms recede, ghost, or resolve as light moves.
 visibility=.30+.70*_h(ci,cj,seed+193)
 M=M+(88*bar+57*lobes*lobe_history+76*center+121*bezel+54*cut)*visibility;R=R-(70*bar+42*lobes*lobe_history+57*center+93*bezel+43*cut)*visibility;C=C-(84*bar+49*lobes*lobe_history+66*center+105*bezel+52*cut)*visibility
 state=np.mod(ci.astype(np.int32)*5+cj.astype(np.int32)*7+np.floor((qx+qy)/8).astype(np.int32),6);tm=np.array((250,250,200,100,225,252),np.float32);tr=np.array((15,45,15,40,140,38),np.float32);tc=np.array((40,40,16,16,100,255),np.float32)
 history=.28+.72*_h(ci,cj,seed+137);parcel=(np.clip(.72*bar+.49*lobes+.61*bezel+.28*cut,0,1)>.42)&(history>.47);M=np.where(parcel,.56*M+.44*tm[state],M);R=np.where(parcel,.56*R+.44*tr[state],R);C=np.where(parcel,.56*C+.44*tc[state],C)
 M=np.clip(M,0,255);R=np.clip(R,15,255);C=np.clip(C,16,255);spec=np.dstack((M,R,C)).astype(np.uint8)
 if(hh,ww)!=(h,w):paint=cv2.resize(paint.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_CUBIC)
 result=(np.clip(paint,0,1).astype(np.float32),spec)
 with _LOCK:
  _CACHE[key]=result
  if len(_CACHE)>2:_CACHE.popitem(last=False)
 return result
def paint_cross_lace_i27(paint,shape,mask,seed,pattern_mix,bbox):
 del bbox;art,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
 if source.max(initial=0)>1.5:source/=255.
 alpha=np.asarray(mask,np.float32);alpha=alpha[...,0] if alpha.ndim==3 else alpha;alpha=(np.clip(alpha,0,1)*np.clip(float(pattern_mix),0,1))[...,None];return np.clip(source*(1-alpha)+art*alpha,0,1).astype(np.float32)
def spec_cross_lace_i27(shape,seed,spec_mix,base_metal,base_rough):
 del spec_mix,base_metal,base_rough;return _arrays(shape,seed)[1]
