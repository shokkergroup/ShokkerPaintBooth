"""FRACTURED HOUDINI H14-I1 — Verdigris Ankh / antique copper enamel.

SPB-HOUDINI, owner correction 2026-08-30: repeated M/R/Cc-only ankhs replace
the old one-centre symbol; RGB remains a complete fine copper-patina finish.
"""
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z): return z-np.floor(z)

def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 scale=min(1.,800./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);ph=(int(seed)%3491)*.0043
 # I3 (owner 2026-08-30): eliminate the broad copper lattice.  Make the
 # neutral carrier a small hand-hammered patina: 1–4px chisel cuts, 4–10px
 # repoussé rims, 8–28px enamel cups, oxidation freckles and gold leaf pins.
 uy=y/5.65;gy=np.floor(uy).astype(np.int32);ux=x/4.7+.48*np.mod(gy,2);gx=np.floor(ux).astype(np.int32);fx=np.mod(ux,1.);fy=np.mod(uy,1.);state=np.mod(gx*19+gy*37+(gx^gy)*9+int(seed),8)
 jx=_fract(np.sin(gx*17.93+gy*49.17+int(seed)*.12)*29681.5);jy=_fract(np.sin(gx*79.11+gy*21.37+int(seed)*.16)*18719.6);dx,dy=fx-jx,fy-jy;age=state.astype(np.float32)/7.;ang=(age-.5)*2.4;ca,sa=np.cos(ang),np.sin(ang);u=ca*dx-sa*dy;v=sa*dx+ca*dy;rad=np.sqrt(dx*dx+dy*dy)
 chase=np.clip((.038-np.abs(v))*25.,0,1)*np.clip((.30-np.abs(u))*3.3,0,1)
 rim=np.clip((.052-np.abs(rad-(.12+.16*age)))*18.,0,1)
 enamel=np.clip((.30-np.abs(u)-np.abs(v))*3.25,0,1)*(1-.48*chase)
 oxide=((np.mod(gx*29+gy*43+int(seed),13)<3).astype(np.float32))*np.clip((.18-np.sqrt((dx+.10)**2+(dy-.13)**2))*6.0,0,1)*(.18+.82*rim)
 leaf=(np.mod(gx*31+gy*17+(gx^gy)*5+int(seed),31)<2).astype(np.float32)*np.clip(.25+.75*enamel,0,1)
 # I5 / Houdini scale correction: repeat 6x6-cell (~85–105px native) ankhs
 # built from the fine hammered patina, never a lone icon or RGB decal.
 sgx=np.floor_divide(gx,6);sgy=np.floor_divide(gy,6);U=(np.mod(gx,6)+fx)/3.-1.;V=(np.mod(gy,6)+fy)/3.-1.;flip=np.mod(sgx*31+sgy*43+int(seed),2)>0;U=np.where(flip,-U,U);chosen=np.mod(sgx*47+sgy*59+(sgx^sgy)*19+int(seed),29)==0
 loop=(U/.42)**2+((V+.31)/.37)**2<1;hole=(U/.19)**2+((V+.31)/.18)**2<1;bar=(np.abs(U)<.76)&(np.abs(V)<.105);stem=(np.abs(U)<.16)&(V>.02)&(V<.76);secret=chosen&((loop&~hole)|bar|stem)
 q=np.mod(state+np.floor((fx+fy)*3).astype(np.int32)+np.floor(age*7).astype(np.int32),8)
 sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(254,16,207,247,41,174,251),default=161).astype(np.float32);sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(6,238,38,16,195,66,22),default=166).astype(np.float32);sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(255,25,158,249,62,112,249),default=149).astype(np.float32)
 # I4 / owner-eye pass: the copper-patina carrier was too black to read as
 # antique enamel.  Lift only visible patina/leaf states; ankhs remain wholly
 # in the independent M/R/Cc replacement below.
 umber=np.array((.115,.038,.015),np.float32);copper=np.array((.480,.165,.040),np.float32);verd=np.array((.075,.500,.400),np.float32);turq=np.array((.140,.700,.600),np.float32);gold=np.array((.900,.650,.180),np.float32)
 paint=umber*(.65+.14*(state[...,None]/7.))+copper*(.50+.18*(1-state[...,None]/7.));z=(chase*.18)[...,None];paint=paint*(1-z)+gold*z;z=(rim*.20)[...,None];paint=paint*(1-z)+copper*1.45*z;z=(enamel*.28+oxide*.13)[...,None];paint=paint*(1-z)+verd*z;z=(leaf*.16)[...,None];paint=paint*(1-z)+gold*z
 t=state.astype(np.float32)/7.;m=24+52*t+80*chase+67*rim+76*enamel+55*oxide+80*leaf;r=231-46*t-67*chase-58*rim-70*enamel-46*oxide-72*leaf;cc=25+55*t+87*chase+75*rim+90*enamel+61*oxide+86*leaf
 m=np.where(secret,sm,m);r=np.where(secret,sr,r);cc=np.where(secret,sc,cc)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255)),2).astype(np.uint8))
 with _L:
  _C[key]=out
  if len(_C)>2:_C.popitem(last=False)
 return out

def paint_verdigris_ankh_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_verdigris_ankh_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
