"""FRACTURED HOUDINI H15-I1 — Porcelain Cipher / hidden material keyholes."""
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 scale=min(1.,800./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);ph=(int(seed)%3119)*.0051
 # I3 (owner 2026-08-30): remove the oversized pale porcelain forms.  The
 # carrier is now kiln-fired micro porcelain: hairline crazing, short cobalt
 # brushlets, small translucent glaze cups, gold scars and pearl pinpoints.
 uy=y/5.7;gy=np.floor(uy).astype(np.int32);ux=x/4.65+.44*np.mod(gy,2);gx=np.floor(ux).astype(np.int32);fx=np.mod(ux,1.);fy=np.mod(uy,1.);state=np.mod(gx*23+gy*41+(gx^gy)*13+int(seed),8)
 jx=_fract(np.sin(gx*13.97+gy*51.13+int(seed)*.15)*27317.4);jy=_fract(np.sin(gx*83.67+gy*17.51+int(seed)*.18)*19813.1);dx,dy=fx-jx,fy-jy;warm=state.astype(np.float32)/7.;ang=(warm-.5)*2.2;ca,sa=np.cos(ang),np.sin(ang);u=ca*dx-sa*dy;v=sa*dx+ca*dy;rad=np.sqrt(dx*dx+dy*dy)
 craze=np.clip((.032-np.abs(v-.10*np.sin(u*8.+warm*4.)))*29.,0,1)*np.clip((.34-np.abs(u))*3.0,0,1)
 brush=np.clip((.045-np.abs(u+.52*v-(warm-.5)*.17))*22.,0,1)*np.clip((.28-rad)*3.6,0,1)
 glaze=np.clip((.29-rad)*3.45,0,1)*(1-.50*craze)
 scar=np.clip((.040-np.abs(u*.71-v*.53-(warm-.5)*.13))*23.,0,1)*(.18+.82*glaze)
 pearl=(np.mod(gx*19+gy*43+(gx^gy)*7+int(seed),27)<2).astype(np.float32)*np.clip(.25+.75*glaze,0,1)
 # I4 / Houdini scale correction: repeated 6x6-cell (~75–100px native)
 # keyhole assemblies materialize through the fine porcelain states only.
 sgx=np.floor_divide(gx,6);sgy=np.floor_divide(gy,6);U=(np.mod(gx,6)+fx)/3.-1.;V=(np.mod(gy,6)+fy)/3.-1.;flip=np.mod(sgx*31+sgy*43+int(seed),2)>0;U=np.where(flip,-U,U);chosen=np.mod(sgx*47+sgy*59+(sgx^sgy)*19+int(seed),29)==0
 ring=U*U+(V+.28)**2<.28;hole=U*U+(V+.28)**2<.105;stem=(np.abs(U)<.18)&(V>-.08)&(V<.72);base=(np.abs(U)<.34)&(V>.58)&(V<.76);secret=chosen&((ring&~hole)|stem|base)
 q=np.mod(state+np.floor((fx+fy)*3).astype(np.int32)+np.floor(warm*7).astype(np.int32),8);sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(252,163,219,177,240,146,205),default=188).astype(np.float32);sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(9,62,43,91,25,79,46),default=71).astype(np.float32);cc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(249,139,199,121,227,155,174),default=136).astype(np.float32)
 ink=np.array((.012,.026,.065),np.float32);china=np.array((.12,.31,.63),np.float32);cobalt=np.array((.02,.11,.42),np.float32);white=np.array((.70,.80,.89),np.float32);gold=np.array((.68,.48,.14),np.float32)
 paint=ink*(.42+.13*(state[...,None]/7.))+china*(.40+.16*(1-state[...,None]/7.));z=(craze*.11)[...,None];paint=paint*(1-z)+gold*z;z=(brush*.18)[...,None];paint=paint*(1-z)+cobalt*z;z=(glaze*.34+scar*.08)[...,None];paint=paint*(1-z)+white*z;z=(pearl*.12)[...,None];paint=paint*(1-z)+np.array((.83,.74,.45),np.float32)*z
 t=state.astype(np.float32)/7.;m=24+52*t+77*craze+65*brush+84*glaze+43*scar+76*pearl;r=230-46*t-65*craze-54*brush-77*glaze-35*scar-68*pearl;co=25+55*t+85*craze+71*brush+97*glaze+47*scar+82*pearl;m=np.where(secret,sm,m);r=np.where(secret,sr,r);co=np.where(secret,cc,co)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,co=map(up,(m,r,co))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(co,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_porcelain_cipher_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_porcelain_cipher_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
