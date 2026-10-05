"""Private Houdini I28 — Cinder Veil P1: material-only distributed flames."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_CACHE,_LOCK=OrderedDict(),RLock();_TAU=np.float32(6.283185307179586)
def _h(i,j,s):return np.mod(np.sin(i*127.1+j*311.7+s*73.9)*43758.5453,1.).astype(np.float32)
def _line(x,y,w):return np.exp(-((x/w)**2+(y/w)**2)).astype(np.float32)
def _arrays(shape,seed):
 key=(*map(int,shape),int(seed))
 with _LOCK:
  if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
 h,w=map(int,shape);s=min(1.,1024./max(h,w));hh,ww=max(256,round(h*s)),max(256,round(w*s));yy,xx=np.mgrid[:hh,:ww].astype(np.float32);X,Y=xx/s,yy/s;ph=(seed%7919)*.00083
 # Innocent obsidian pearl, with only fine 8–20px mineral threads in paint.
 u=(X*.89+Y*.46+2*np.sin(Y*.016+ph))/7.1;v=(X*.46-Y*.89+2*np.sin(X*.014-ph))/9.4;weave=.5+.5*np.sin(u*_TAU)*np.sin(v*_TAU);tide=.5+.5*np.sin(X*.010-Y*.012+ph);spark=.5+.5*np.sin(X*.23+Y*.16+.4*np.sin(Y*.028))
 # P4 — ordinary paint gets fine smoky teal/ember optical drift, never flame geometry.
 teal=.5+.5*np.sin(X*.008-Y*.012+ph);ember=.5+.5*np.sin(X*.011+Y*.007-ph)
 paint=np.dstack((.050+.058*weave+.023*tide+.013*spark+.025*teal,.037+.036*weave+.012*tide+.006*spark+.010*teal,.025+.025*weave+.008*tide+.018*ember))
 # Full-canvas hand-set compact flame anatomy: outer plume, inner lick, ember
 # core and smoke shoulder; every physical part is 4–28px.
 # P3 — break the ruler-grid cadence with bounded hand-set drift/scale.
 dx=3*np.sin(Y*.012+ph)+2*np.sin((X+Y)*.009-ph);dy=3*np.sin(X*.013-ph)-1.7*np.sin((X-Y)*.010+ph);GX,GY=(X+dx)/76.,(Y+dy)/80.;ci,cj=np.floor(GX),np.floor(GY);cx=ci+.5+(_h(ci,cj,seed+17)-.5)*.54+.14*np.sin(cj*1.29+ci*.39+ph);cy=cj+.5+(_h(ci,cj,seed+31)-.5)*.52+.13*np.sin(ci*1.17-cj*.47-ph);qx,qy=(GX-cx)*76.,(GY-cy)*80.;a=(_h(ci,cj,seed+47)-.5)*.72;ca,sa=np.cos(a),np.sin(a);qx,qy=qx*ca+qy*sa,-qx*sa+qy*ca;setting=.84+.28*_h(ci,cj,seed+59);qx,qy=qx/setting,qy/setting
 bend=7.5*np.sin((qy+18)*.10+_h(ci,cj,seed+63)*4);outer=np.exp(-(((qx-bend*.30)/(7.5+np.maximum(qy,0)*.12))**2+((qy-2)/25.)**2))* (qy>-23)*(qy<26);inner=np.exp(-(((qx+bend*.18)/(4.1+np.maximum(qy,0)*.08))**2+((qy+2)/15.)**2))*(qy>-17)*(qy<20);core=_line(qx,qy+8,4.7)*np.exp(-(qy/14)**2);shoulder=np.exp(-(((qx-bend*.45)/13.)**2+((qy-2)/29.)**2))*(qy>-27)*(qy<30);tip=np.exp(-(((qx-bend*.75)/(3.4))**2+((qy-22)/5.5)**2))
 # P2 — add split tongues and a crown cut so a setting reads as fire, not a dash.
 tongue_l=np.exp(-(((qx+8-bend*.56)/(3.5))**2+((qy-10)/12.)**2))*(qy>-12)*(qy<23);tongue_r=np.exp(-(((qx-8-bend*.18)/(3.2))**2+((qy-7)/11.)**2))*(qy>-13)*(qy<21);crown=np.exp(-(((qx+bend*.22)/(2.4))**2+((qy-25)/4.3)**2));flame=np.clip(.82*outer+.62*inner+.52*core+.25*shoulder+.44*tip+.52*tongue_l+.46*tongue_r+.34*crown,0,1)
 # Hidden fire has four material roles, but none is allowed to affect paint.
 delta=20*(np.sin(u*_TAU)-np.sin(v*_TAU));M=67+32*weave+.32*delta;R=177-36*weave+delta;C=161-31*weave+.82*delta;history=.28+.72*_h(ci,cj,seed+131);M=M+(113*outer+89*inner+66*core+42*tip+74*tongue_l+65*tongue_r+38*crown)*history;R=R-(87*outer+69*inner+48*core+31*tip+56*tongue_l+49*tongue_r+28*crown)*history;C=C-(104*outer+81*inner+58*core+38*tip+67*tongue_l+58*tongue_r+34*crown)*history
 # P5 — adjacent flame parcels alternate buried satin/dark chrome/active coat.
 state=np.mod(ci.astype(np.int32)*5+cj.astype(np.int32)*7+np.floor((qx-qy)/8).astype(np.int32),6);tm=np.array((250,250,200,100,225,252),np.float32);tr=np.array((15,45,15,40,140,38),np.float32);tc=np.array((40,40,16,16,100,255),np.float32);parcel=(np.clip(.76*outer+.65*inner+.44*core+.35*tip,0,1)>.42)&(history>.49);M=np.where(parcel,.61*M+.39*tm[state],M);R=np.where(parcel,.61*R+.39*tr[state],R);C=np.where(parcel,.61*C+.39*tc[state],C);chem=np.floor(_h(ci,cj,seed+211)*3)-1;anatomy=np.clip(.70*outer+.58*inner+.42*core+.33*tip,0,1);M=np.clip(M+chem*21*anatomy,0,255);R=np.clip(R-chem*16*anatomy,15,255);C=np.clip(C-chem*19*anatomy,16,255);spec=np.dstack((M,R,C)).astype(np.uint8)
 if(hh,ww)!=(h,w):paint=cv2.resize(paint.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_CUBIC)
 result=(np.clip(paint,0,1).astype(np.float32),spec)
 with _LOCK:
  _CACHE[key]=result
  if len(_CACHE)>2:_CACHE.popitem(last=False)
 return result
def paint_cinder_veil_i28(paint,shape,mask,seed,pattern_mix,bbox):
 del bbox;art,_=_arrays(shape,seed);source=np.asarray(paint,np.float32)[...,:3]
 if source.max(initial=0)>1.5:source/=255.
 alpha=np.asarray(mask,np.float32);alpha=alpha[...,0] if alpha.ndim==3 else alpha;alpha=(np.clip(alpha,0,1)*np.clip(float(pattern_mix),0,1))[...,None];return np.clip(source*(1-alpha)+art*alpha,0,1).astype(np.float32)
def spec_cinder_veil_i28(shape,seed,spec_mix,base_metal,base_rough):
 del spec_mix,base_metal,base_rough;return _arrays(shape,seed)[1]
