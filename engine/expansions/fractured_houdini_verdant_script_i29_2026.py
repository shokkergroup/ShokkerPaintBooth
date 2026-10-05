"""Private Houdini I29 Material Calligraphy P1. No catalog wiring."""
from __future__ import annotations
import cv2,numpy as np
from collections import OrderedDict
from threading import RLock
_C,_L=OrderedDict(),RLock();T=np.float32(6.283185307179586)
def H(i,j,s):return np.mod(np.sin(i*127.1+j*311.7+s*73.9)*43758.5453,1.).astype(np.float32)
def E(x,y,a,b):return np.exp(-((x/a)**2+(y/b)**2)).astype(np.float32)
def A(shape,seed):
 k=(*map(int,shape),seed)
 with _L:
  if k in _C:return _C[k]
 h,w=shape;sc=min(1.,1024/max(h,w));hh,ww=max(256,round(h*sc)),max(256,round(w*sc));yy,xx=np.mgrid[:hh,:ww].astype(np.float32);X,Y=xx/sc,yy/sc;p=(seed%7919)*.0007
 u=(X*.9+Y*.43+2*np.sin(Y*.014+p))/7.;v=(X*.43-Y*.9+2*np.sin(X*.013-p))/9.;wa=.5+.5*np.sin(u*T);we=.5+.5*np.sin(v*T);satin=np.clip(.5*wa+.4*we+.2*wa*we,0,1);oil=.5+.5*np.sin(X*.19-Y*.15+.4*np.sin(X*.03));paint=np.dstack((.055+.06*satin+.018*oil,.044+.04*satin+.009*oil,.034+.028*satin))
 # I29 P5 / owner verdict: P4 still read as repeated symbols (M/R/C std
 # 14.65/16.27/14.48).  Retire the stamp grammar.  This is a surface process:
 # a jeweller's micro-engraved lacquer, made from intersecting 8–28px tool runs.
 # It only becomes ornate in material response; its paint has no readable mark.
 u=(.71*X+.74*Y+18*np.sin(Y*.007+p)+9*np.sin(X*.018-p))/27.;v=(-.79*X+.58*Y+16*np.sin(X*.008-p)-8*np.sin(Y*.015+p))/31.;a=np.abs(np.sin(u*T));b=np.abs(np.sin(v*T));toola=np.exp(-(a/.18)**2);toolb=np.exp(-(b/.20)**2);turn=np.exp(-((np.abs(np.sin((u+v)*T*.47))-.42)/.18)**2)
 # Irregular engraved islands interrupt the two tool directions; their union
 # contains the hidden, non-literal calligraphic topology without a cell grid.
 pocket=.5+.5*np.sin(.53*u-.37*v+1.4*np.sin(.19*u)+.9*np.cos(.17*v));run_a=toola*(.30+.70*pocket);run_b=toolb*(.26+.74*(1-pocket));cross=toola*toolb;curl=turn*(.32+.68*np.sin((u-v)*T*.31)**2)
 glyph=np.clip(.66*run_a+.58*run_b+.71*cross+.44*curl,0,1)
 d=20*(wa-we);M=68+31*satin+.34*d;R=177-35*satin+d;C=161-30*satin+.82*d;his=.16+.84*(.5+.5*np.sin(u*1.31-v*.77));M=M+(132*run_a+118*run_b+161*cross+76*curl)*his;R=R-(101*run_a+89*run_b+122*cross+58*curl)*his;C=C-(121*run_a+106*run_b+145*cross+69*curl)*his
 st=np.mod(np.floor(u*3.0).astype(np.int32)*5+np.floor(v*3.0).astype(np.int32)*7+np.floor((u-v)*2.0).astype(np.int32),6);tm=np.array((250,250,200,100,225,252),np.float32);tr=np.array((15,45,15,40,140,38),np.float32);tc=np.array((40,40,16,16,100,255),np.float32);pa=(glyph>.42)&(his>.48);M=np.where(pa,.6*M+.4*tm[st],M);R=np.where(pa,.6*R+.4*tr[st],R);C=np.where(pa,.6*C+.4*tc[st],C);spec=np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8)
 if(hh,ww)!=(h,w):paint=cv2.resize(paint,(w,h),interpolation=cv2.INTER_CUBIC);spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_CUBIC)
 out=(paint.astype(np.float32),spec)
 with _L:_C[k]=out
 return out
def paint_verdant_script_i29(paint,shape,mask,seed,pattern_mix,bbox):
 del bbox;art,_=A(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0]if m.ndim==3 else m;return np.clip(src*(1-m[...,None])+art*m[...,None],0,1)
def spec_verdant_script_i29(shape,seed,spec_mix,base_metal,base_rough):return A(shape,seed)[1]
