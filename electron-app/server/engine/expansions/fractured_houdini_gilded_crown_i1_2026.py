"""FRACTURED HOUDINI H11-I1 — Gilded Crown / black-gold filigree lacquer."""
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 sc=min(1.,768./max(h,w));hh,ww=max(96,round(h*sc)),max(96,round(w*sc));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);p=(int(seed)%2861)*.0061
 # I3 (owner 2026-08-30): remove the broad gold filigree lanes.  Build a
 # black-gold micro-damascene from 8–28px nested engraved arcs, foil halos,
 # tiny enamel nodes, warm patina pools and charcoal interruptions.
 uy=y/6.3;gy=np.floor(uy).astype(np.int32);ux=x/4.95+.41*np.mod(gy,2);gx=np.floor(ux).astype(np.int32);fx=np.mod(ux,1.);fy=np.mod(uy,1.);state=np.mod(gx*31+gy*49+(gx^gy)*11+int(seed),8);age=state.astype(np.float32)/7.
 cx=.27+.46*_fract(np.sin(gx*21.19+gy*37.61+int(seed)*.11)*17731.7);cy=.27+.46*_fract(np.sin(gx*63.73+gy*14.87+int(seed)*.17)*26319.4);dx,dy=fx-cx,fy-cy;rad=np.sqrt(dx*dx+dy*dy)
 engr=np.clip((.052-np.abs(rad-(.13+.18*age)))*17.,0,1)+np.clip((.035-np.abs(dx*.68-dy*.73))*20.,0,1)*np.clip((.30-rad)*3.2,0,1);engr=np.clip(engr,0,1)
 bloom=np.clip((.28-rad)*3.55,0,1)*(.25+.75*age)
 foil=((np.mod(gx*29+gy*17+int(seed),11)<3).astype(np.float32))*np.clip((.15-np.sqrt((dx+.10)**2+(dy-.12)**2))*7.0,0,1)*(1-.6*engr)
 nick=((np.mod(gx*13+gy*41+int(seed),9)<3).astype(np.float32))*np.clip((.09-np.sqrt((dx-.15)**2+(dy+.12)**2))*10.0,0,1)*(1-.55*engr)
 # H11-I7 / Houdini scale correction: 6x6-cell (~80–100px native) crown
 # assemblies emerge across the car, all composed from fine filigree cells.
 # The former random q palette remains retired—these are coherent gold states.
 sgx=np.floor_divide(gx,6);sgy=np.floor_divide(gy,6);u=(np.mod(gx,6)+fx)/3.-1.;v=(np.mod(gy,6)+fy)/3.-1.;chosen=np.mod(sgx*43+sgy*61+(sgx^sgy)*17+int(seed),29)==0
 base=(np.abs(v-.48)<.12)&(np.abs(u)<.76);left=(np.abs(u+.38+.24*v)<.11)&(v>-.58)&(v<.48);mid=(np.abs(u)<.11)&(v>-.72)&(v<.48);right=(np.abs(u-.38-.24*v)<.11)&(v>-.58)&(v<.48)
 secret=chosen&(base|left|mid|right);sm=np.where(secret,238,0).astype(np.float32);sr=np.where(secret,18,0).astype(np.float32);cc=np.where(secret,244,0).astype(np.float32)
 # I6: staged card audit found the corrected crown carrier underlit.
 # Enrich black-gold lacquer and its fine damascene only; crowns stay M/R/Cc.
 coal=np.array((.040,.026,.014),np.float32);umber=np.array((.35,.19,.055),np.float32);gold=np.array((.84,.56,.16),np.float32);bronze=np.array((.60,.35,.09),np.float32);pearl=np.array((.88,.68,.33),np.float32);paint=coal*(.52+.12*age[...,None])+umber*(.40+.18*(1-age[...,None]));z=(engr*.47)[...,None];paint=paint*(1-z)+gold*z;z=(bloom*.34)[...,None];paint=paint*(1-z)+bronze*z;z=(foil*.39+nick*.18)[...,None];paint=paint*(1-z)+pearl*z
 t=state.astype(np.float32)/7.;m=26+47*t+81*engr+53*bloom+77*foil+31*nick;r=226-42*t-68*engr-48*bloom-67*foil-27*nick;coat=23+50*t+86*engr+64*bloom+91*foil+37*nick;m=np.where(secret,sm,m);r=np.where(secret,sr,r);coat=np.where(secret,cc,coat)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,coat=map(up,(m,r,coat))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_gilded_crown_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_gilded_crown_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
