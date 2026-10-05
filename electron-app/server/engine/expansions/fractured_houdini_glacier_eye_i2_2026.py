"""FRACTURED HOUDINI H12-I2 — Glacier Eye, repeated material-only ice eyes.

SPB-HOUDINI / owner correction 2026-08-30: the prior single central eye failed
the whole-car test.  This carrier uses fine glacial lacquer detail and twenty
independently rotated eye events whose anatomy exists only in M/R/Cc.
"""
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np

_C, _L = OrderedDict(), RLock()

def _fract(z): return z - np.floor(z)

def _arrays(shape, seed):
 h, w = map(int, shape[:2]); key = (h, w, int(seed))
 with _L:
  if key in _C: _C.move_to_end(key); return _C[key]
 scale=min(1.,800./max(h,w)); hh,ww=max(96,round(h*scale)),max(96,round(w*scale)); y,x=np.mgrid[0:hh,0:ww].astype(np.float32); ph=(int(seed)%2791)*.0057
 # I4 (owner 2026-08-30): the multidirectional I2 marks still grouped as
 # wide blue water waves.  Use fine irregular ice-shards instead: local
 # 1–4px cuts, 5–12px rims, 8–26px crystal panes, mica and frost bridges.
 uy=y/5.85;gy=np.floor(uy).astype(np.int32);ux=x/4.75+.46*np.mod(gy,2);gx=np.floor(ux).astype(np.int32);fx=np.mod(ux,1.);fy=np.mod(uy,1.);state=np.mod(gx*29+gy*47+(gx^gy)*11+int(seed),8)
 jx=_fract(np.sin(gx*15.71+gy*47.23+int(seed)*.14)*31793.3);jy=_fract(np.sin(gx*81.31+gy*19.11+int(seed)*.18)*21317.1);dx,dy=fx-jx,fy-jy;angle=(state.astype(np.float32)/7.-.5)*2.3;ca,sa=np.cos(angle),np.sin(angle);u=ca*dx-sa*dy;v=sa*dx+ca*dy;rad=np.sqrt(dx*dx+dy*dy)
 engr=np.clip((.040-np.abs(v))*24.,0,1)*np.clip((.31-np.abs(u))*3.2,0,1)
 lip=np.clip((.048-np.abs(rad-(.12+.16*(state/7.))))*19.,0,1)
 crystal=np.clip((.33-np.abs(u)-np.abs(v))*3.15,0,1)*(1-.42*engr)
 frost=np.clip((.050-np.abs(u*.58+v*.72-(state.astype(np.float32)/7.-.5)*.16))*17.,0,1)*(.20+.80*lip)
 mica=(np.mod(gx*37+gy*19+(gx^gy)*5+int(seed),23)<2).astype(np.float32)*np.clip(.28+.72*crystal,0,1)
 # I5 / Houdini scale correction: repeated 6x6-cell (~75–100px native) ice
 # eyes are assembled through fine glacial-marquetry material changes only.
 sgx=np.floor_divide(gx,6);sgy=np.floor_divide(gy,6);U=(np.mod(gx,6)+fx)/3.-1.;V=(np.mod(gy,6)+fy)/3.-1.;flip=np.mod(sgx*31+sgy*43+int(seed),2)>0;U=np.where(flip,-U,U);chosen=np.mod(sgx*47+sgy*59+(sgx^sgy)*19+int(seed),29)==0
 outer=chosen&((U/.92)**2+(V/.37)**2<1);iris=chosen&((U/.47)**2+(V/.28)**2<1);pupil=chosen&((U/.13)**2+(V/.20)**2<1)
 q=np.mod(state+np.floor((fx+fy)*3).astype(np.int32)+np.floor(state.astype(np.float32)/7.*7).astype(np.int32),8); q=np.where(iris,(q+3)%8,q)
 sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(253,151,225,180,242,132,208),default=191).astype(np.float32)
 sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(8,67,39,94,23,83,45),default=72).astype(np.float32)
 sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(251,138,204,121,231,156,177),default=140).astype(np.float32)
 abyss=np.array((.009,.023,.058),np.float32); cobalt=np.array((.035,.15,.38),np.float32); ice=np.array((.16,.43,.72),np.float32); pearl=np.array((.59,.74,.90),np.float32); gold=np.array((.61,.43,.13),np.float32)
 paint=abyss*(.47+.13*(state[...,None]/7.))+cobalt*(.33+.17*(1-state[...,None]/7.)); z=(engr*.105)[...,None]; paint=paint*(1-z)+gold*z; z=(lip*.23)[...,None]; paint=paint*(1-z)+ice*z; z=(crystal*.34+frost*.075)[...,None]; paint=paint*(1-z)+pearl*z; z=(mica*.14)[...,None]; paint=paint*(1-z)+np.array((.90,.84,.60),np.float32)*z
 t=state.astype(np.float32)/7.; m=25+50*t+75*engr+66*lip+82*crystal+38*frost+78*mica; r=229-44*t-62*engr-58*lip-76*crystal-33*frost-70*mica; cc=24+53*t+80*engr+73*lip+96*crystal+45*frost+84*mica
 secret=outer; m=np.where(secret,sm,m); r=np.where(secret,sr,r); cc=np.where(secret,sc,cc); m=np.where(pupil,38,m); r=np.where(pupil,211,r); cc=np.where(pupil,33,cc)
 if (hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR); paint=up(paint); m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255)),2).astype(np.uint8))
 with _L:
  _C[key]=out
  if len(_C)>2: _C.popitem(last=False)
 return out

def paint_glacier_eye_i2(paint,shape,mask,seed,pm,bb):
 del bb; auth,_=_arrays(shape,seed); src=np.asarray(paint,np.float32)[...,:3]; src=src/255. if src.max(initial=0)>1.5 else src; cov=np.asarray(mask,np.float32); cov=cov[...,0] if cov.ndim==3 else cov; mix=(np.clip(cov,0,1)*float(pm))[...,None]; return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)

def spec_glacier_eye_i2(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r; return _arrays(shape,seed)[1]
