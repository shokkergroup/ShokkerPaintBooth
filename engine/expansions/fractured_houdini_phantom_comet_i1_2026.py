"""FRACTURED HOUDINI H13-I1 — Phantom Comet / nocturne meteor lacquer.

SPB-HOUDINI, owner correction 2026-08-30: replaces one central starburst with
repeated material-only comet signatures across the complete 2048² carrier.
"""
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np

_C, _L = OrderedDict(), RLock()
def _fract(z): return z-np.floor(z)

def _arrays(shape,seed):
 h,w=map(int,shape[:2]); key=(h,w,int(seed))
 with _L:
  if key in _C: _C.move_to_end(key); return _C[key]
 scale=min(1.,800./max(h,w)); hh,ww=max(96,round(h*scale)),max(96,round(w*scale)); y,x=np.mgrid[0:hh,0:ww].astype(np.float32); ph=(int(seed)%3137)*.0049
 # I3 (owner 2026-08-30): remove the large purple flow waves.  The neutral
 # carrier is nocturne meteor lacquer: local engraving, short ion scratches,
 # blue-violet pools, mica beads, and dark micro-voids—never a global ribbon.
 uy=y/5.85;gy=np.floor(uy).astype(np.int32);ux=x/4.8+.45*np.mod(gy,2);gx=np.floor(ux).astype(np.int32);fx=np.mod(ux,1.);fy=np.mod(uy,1.);state=np.mod(gx*31+gy*17+(gx^gy)*13+int(seed),8)
 jx=_fract(np.sin(gx*17.37+gy*47.83+int(seed)*.13)*31173.6);jy=_fract(np.sin(gx*79.71+gy*19.47+int(seed)*.18)*21137.8);dx,dy=fx-jx,fy-jy;t=state.astype(np.float32)/7.;ang=(t-.5)*2.3;ca,sa=np.cos(ang),np.sin(ang);u=ca*dx-sa*dy;v=sa*dx+ca*dy;rad=np.sqrt(dx*dx+dy*dy)
 etch=np.clip((.035-np.abs(v))*27.,0,1)*np.clip((.32-np.abs(u))*3.1,0,1)
 trail=np.clip((.044-np.abs(u+.61*v-(t-.5)*.14))*22.,0,1)*np.clip((.28-rad)*3.5,0,1);pool=np.clip((.30-rad)*3.35,0,1)*(1-.55*etch)
 pulse=((np.mod(gx*29+gy*43+int(seed),13)<3).astype(np.float32))*np.clip((.12-np.sqrt((dx+.12)**2+(dy-.10)**2))*8.0,0,1)*pool
 mica=(np.mod(gx*23+gy*41+(gx^gy)*7,29)<2).astype(np.float32)*np.clip(.24+.76*pool,0,1)
 # I5 / Houdini scale correction: repeated 6x6-cell (~75–100px native)
 # comet assemblies built from fine nocturne-lacquer material states only.
 sgx=np.floor_divide(gx,6);sgy=np.floor_divide(gy,6);U=(np.mod(gx,6)+fx)/3.-1.;V=(np.mod(gy,6)+fy)/3.-1.;flip=np.mod(sgx*31+sgy*43+int(seed),2)>0;U=np.where(flip,-U,U);chosen=np.mod(sgx*47+sgy*59+(sgx^sgy)*19+int(seed),29)==0
 head=chosen&((U-.34)**2+V**2<.22);tail=chosen&(U<.34)&(U>-.98)&(np.abs(V)<(.055+.13*(U+.98)/1.32));sheath=chosen&(U<.25)&(U>-.80)&(np.abs(V)<(.028+.075*(U+.80)/1.05));secret=head|tail|sheath
 q=np.mod(state+np.floor((fx+fy)*3).astype(np.int32)+np.floor(t*7).astype(np.int32),8); q=np.where(head,(q+2)%8,q)
 sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(255,14,214,247,39,183,253),default=158).astype(np.float32)
 sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(4,240,34,15,198,61,19),default=165).astype(np.float32)
 sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(255,23,164,249,59,108,252),default=146).astype(np.float32)
 # I4: standard-stage audit found the nocturne carrier too crushed to black.
 # Increase the local indigo/violet/ion/mica layers, never the hidden comet.
 midnight=np.array((.018,.025,.075),np.float32); indigo=np.array((.070,.15,.40),np.float32); violet=np.array((.40,.17,.67),np.float32); blue=np.array((.22,.52,.86),np.float32); gold=np.array((.88,.66,.20),np.float32)
 paint=midnight*(.55+.12*(state[...,None]/7.))+indigo*(.30+.16*(1-state[...,None]/7.)); z=(etch*.22)[...,None]; paint=paint*(1-z)+gold*z; z=(trail*.21)[...,None]; paint=paint*(1-z)+blue*z; z=(pool*.31+pulse*.20)[...,None]; paint=paint*(1-z)+violet*z; z=(mica*.18)[...,None]; paint=paint*(1-z)+np.array((.94,.84,.57),np.float32)*z
 t=state.astype(np.float32)/7.;m=22+53*t+79*etch+68*trail+81*pool+58*pulse+76*mica;r=233-47*t-65*etch-58*trail-74*pool-49*pulse-69*mica;cc=23+56*t+86*etch+73*trail+94*pool+65*pulse+83*mica
 m=np.where(secret,sm,m);r=np.where(secret,sr,r);cc=np.where(secret,sc,cc)
 if (hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255)),2).astype(np.uint8))
 with _L:
  _C[key]=out
  if len(_C)>2:_C.popitem(last=False)
 return out

def paint_phantom_comet_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_phantom_comet_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
