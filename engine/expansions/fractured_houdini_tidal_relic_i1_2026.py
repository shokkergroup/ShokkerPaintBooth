"""FRACTURED HOUDINI H19-I1 — Tidal Relic / deep-ocean material tridents."""
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 scale=min(1.,800./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);ph=(int(seed)%3413)*.0047
 # I3 (owner 2026-08-30): remove the broad diagonal water flow.  Deep-ocean
 # relic glaze becomes a fine submerged patina: salt cracks, coral lips,
 # sea-glass pockets, nacre sparks and abyss inclusions at local scale only.
 uy=y/5.85;gy=np.floor(uy).astype(np.int32);ux=x/4.8+.47*np.mod(gy,2);gx=np.floor(ux).astype(np.int32);fx=np.mod(ux,1.);fy=np.mod(uy,1.);state=np.mod(gx*27+gy*39+(gx^gy)*11+int(seed),8)
 jx=_fract(np.sin(gx*14.89+gy*53.11+int(seed)*.12)*28471.3);jy=_fract(np.sin(gx*85.21+gy*23.19+int(seed)*.17)*20317.8);dx,dy=fx-jx,fy-jy;t=state.astype(np.float32)/7.;ang=(t-.5)*2.25;ca,sa=np.cos(ang),np.sin(ang);u=ca*dx-sa*dy;v=sa*dx+ca*dy;rad=np.sqrt(dx*dx+dy*dy)
 crack=np.clip((.034-np.abs(v+.11*np.sin(u*7.+t*5.)))*28.,0,1)*np.clip((.34-np.abs(u))*3.0,0,1)
 coral=np.clip((.052-np.abs(rad-(.10+.16*t)))*18.,0,1)
 glass=np.clip((.30-rad)*3.35,0,1)*(1-.48*crack)
 nacre=np.clip((.041-np.abs(u*.64+v*.66-(t-.5)*.13))*21.,0,1)*(.20+.80*glass)
 abyss=(np.mod(gx*37+gy*13+(gx^gy)*5,23)<2).astype(np.float32)*(.32+.68*glass)
 # H19-I4 / owner rejection 2026-08-30: replace the tiny block trident with
 # repeated 125–140px oceanic relic engraving: tapered triple prongs, wave
 # collars, pearl rings and fine 8–20px filigree lines—not a flat symbol.
 sgx=np.floor_divide(gx,9);sgy=np.floor_divide(gy,9);U=(np.mod(gx,9)+fx)/4.5-1.;V=(np.mod(gy,9)+fy)/4.5-1.;flip=np.mod(sgx*31+sgy*43+int(seed),2)>0;U=np.where(flip,-U,U);chosen=np.mod(sgx*47+sgy*59+(sgx^sgy)*19+int(seed),10)==0
 wob=.045*np.sin(V*10.5);shaft=np.clip((.055-np.abs(U-wob))*18.,0,1)*(V>-.12)*(V<.78)
 prong_mid=np.clip((.048-np.abs(U-.07*np.sin((V+.8)*7.)))*20.8,0,1)*(V>-.80)*(V<.18)
 prong_l=np.clip((.050-np.abs(U-(-.39-.22*V+.055*np.sin(V*8.))))*19.4,0,1)*(V>-.72)*(V<.18)
 prong_r=np.clip((.050-np.abs(U-(.39+.22*V-.055*np.sin(V*8.))))*19.4,0,1)*(V>-.72)*(V<.18)
 collar=np.clip((.040-np.abs(np.sqrt(U*U+(V-.14)**2)-.35))*24.,0,1)+np.clip((.034-np.abs(np.sqrt(U*U+(V-.14)**2)-.53))*29.,0,1)
 wave=np.clip((.044-np.abs(V-(.24+.075*np.sin(U*12.))))*22.,0,1)*(np.abs(U)<.64)
 pearl=np.clip((.070-np.sqrt(U*U+(V-.14)**2))*14.,0,1);secret=chosen&((shaft>.15)|(prong_mid>.15)|(prong_l>.15)|(prong_r>.15)|(collar>.16)|(wave>.16)|(pearl>.16))
 q=np.mod(state+np.floor((fx+fy)*3).astype(np.int32)+np.floor((V+1)*4.3).astype(np.int32),8);sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(248,34,212,92,231,62,174),default=126).astype(np.float32);sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(12,207,55,151,28,177,80),default=122).astype(np.float32);co=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(245,47,184,107,216,71,155),default=129).astype(np.float32)
 aby=np.array((.006,.021,.029),np.float32);sea=np.array((.025,.20,.28),np.float32);teal=np.array((.05,.48,.45),np.float32);pearl=np.array((.52,.76,.72),np.float32);gold=np.array((.67,.51,.16),np.float32);paint=aby*(.48+.13*t[...,None])+sea*(.34+.16*(1-t[...,None]));z=(crack*.17)[...,None];paint=paint*(1-z)+gold*z;z=(coral*.20)[...,None];paint=paint*(1-z)+teal*z;z=(glass*.30+nacre*.10)[...,None];paint=paint*(1-z)+pearl*z;z=(abyss*.20)[...,None];paint=paint*(1-z)+aby*z
 m=23+52*t+78*crack+65*coral+80*glass+43*nacre+30*abyss;r=232-46*t-66*crack-56*coral-74*glass-35*nacre-22*abyss;cc=24+55*t+86*crack+72*coral+92*glass+48*nacre+32*abyss;m=np.where(secret,sm,m);r=np.where(secret,sr,r);cc=np.where(secret,co,cc)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_tidal_relic_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_tidal_relic_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
