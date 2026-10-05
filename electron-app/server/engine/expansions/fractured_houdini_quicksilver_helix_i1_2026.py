"""FRACTURED HOUDINI H17-I1 — Quicksilver Helix / liquid chrome material DNA."""
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 scale=min(1.,800./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);ph=(int(seed)%3257)*.0056
 # I3 (owner 2026-08-30): remove the large liquid-metal flow lanes.  This
 # is a true quicksilver micro-surface: 1–3px scratches, 3–8px mercury lips,
 # 7–22px interference droplets, facets and dark liquid-metal voids.
 uy=y/5.95;gy=np.floor(uy).astype(np.int32);ux=x/4.9+.45*np.mod(gy,2);gx=np.floor(ux).astype(np.int32);fx=np.mod(ux,1.);fy=np.mod(uy,1.);state=np.mod(gx*31+gy*21+(gx^gy)*15+int(seed),8)
 jx=_fract(np.sin(gx*16.71+gy*45.37+int(seed)*.14)*30317.8);jy=_fract(np.sin(gx*77.13+gy*15.91+int(seed)*.19)*19417.6);dx,dy=fx-jx,fy-jy;t=state.astype(np.float32)/7.;ang=(t-.5)*2.5;ca,sa=np.cos(ang),np.sin(ang);u=ca*dx-sa*dy;v=sa*dx+ca*dy;rad=np.sqrt(dx*dx+dy*dy)
 lip=np.clip((.055-np.abs(rad-(.11+.17*t)))*17.,0,1)
 scratch=np.clip((.034-np.abs(v))*28.,0,1)*np.clip((.30-np.abs(u))*3.3,0,1)
 pool=np.clip((.30-rad)*3.35,0,1)*(1-.45*lip)
 bead=((np.mod(gx*37+gy*17+int(seed),13)<3).astype(np.float32))*np.clip((.12-np.sqrt((dx+.12)**2+(dy-.10)**2))*8.0,0,1)*pool
 void=((np.mod(gx*23+gy*41+int(seed),17)<3).astype(np.float32))*np.clip((.17-np.sqrt((dx-.16)**2+(dy+.11)**2))*6.0,0,1)*(.20+.80*pool)
 # H17-I4 / owner rejection 2026-08-30: replace tiny generic zigzags with
 # distributed 125–140px engraved double helices.  The helix is linework:
 # paired 8–18px strands, offset secondary filaments, rungs and node collars.
 sgx=np.floor_divide(gx,9);sgy=np.floor_divide(gy,9);U=(np.mod(gx,9)+fx)/4.5-1.;V=(np.mod(gy,9)+fy)/4.5-1.;flip=np.mod(sgx*31+sgy*43+int(seed),2)>0;U=np.where(flip,-U,U);chosen=np.mod(sgx*47+sgy*59+(sgx^sgy)*19+int(seed),10)==0;phase=V*10.8
 spine=.39*np.sin(phase);s1=np.clip((.065-np.abs(U-spine))*15.4,0,1);s2=np.clip((.065-np.abs(U+spine))*15.4,0,1)
 fine1=np.clip((.036-np.abs(U-(spine+.105*np.cos(phase*2.0))))*27.7,0,1);fine2=np.clip((.036-np.abs(U-(-spine-.105*np.cos(phase*2.0))))*27.7,0,1)
 band=np.abs(V)<.86;rung=(np.abs(np.sin(phase*1.47))<.105)&(np.abs(U)<.37);collar=np.clip((.055-np.abs(np.cos(phase*1.47)))*18.,0,1)*(np.abs(U)<.16)
 secret=chosen&(((s1>.16)|(s2>.16)|(fine1>.16)|(fine2>.16)|rung|(collar>.16))&band);node=chosen&(rung&band)
 # H17-I5: explicit material-only DNA engraving atlas.  Two true spline
 # strands, secondary filament, collar nodes and rungs preserve DNA anatomy.
 motif=np.zeros((hh,ww),np.uint8);cw,ch=12*4.9,12*5.95
 for iy in range(int(np.ceil(hh/ch))+1):
  for ix in range(int(np.ceil(ww/cw))+1):
   if np.mod(ix*47+iy*59+(ix^iy)*19+int(seed),7): continue
   cx,cy=int((ix+.5)*cw),int((iy+.5)*ch);amp=max(11,int(cw*.36));span=max(29,int(ch*.56));thick=max(2,int(min(cw,ch)*.040));ys=np.linspace(-span,span,41);left=np.array([(int(cx+amp*np.sin(v*.20)),int(cy+v)) for v in ys],np.int32);right=np.array([(int(cx-amp*np.sin(v*.20)),int(cy+v)) for v in ys],np.int32)
   cv2.polylines(motif,[left],False,1,thick,cv2.LINE_AA);cv2.polylines(motif,[right],False,2,thick,cv2.LINE_AA)
   left2=np.array([(int(cx+(amp*.72)*np.sin(v*.20+.85)),int(cy+v)) for v in ys],np.int32);right2=np.array([(int(cx-(amp*.72)*np.sin(v*.20+.85)),int(cy+v)) for v in ys],np.int32);cv2.polylines(motif,[left2],False,3,1,cv2.LINE_AA);cv2.polylines(motif,[right2],False,4,1,cv2.LINE_AA)
   for v in range(-span+6,span-5,max(6,int(span*.26))):
    lx=int(cx+amp*np.sin(v*.20));rx=int(cx-amp*np.sin(v*.20));cv2.line(motif,(lx,cy+v),(rx,cy+v),5,1,cv2.LINE_AA);cv2.circle(motif,(lx,cy+v),max(2,thick),6,-1,cv2.LINE_AA);cv2.circle(motif,(rx,cy+v),max(2,thick),6,-1,cv2.LINE_AA)
 secret=motif>0;q=np.where(secret,motif%8,7).astype(np.int32);sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(248,34,212,92,231,62,174),default=126).astype(np.float32);sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(12,207,55,151,28,177,80),default=122).astype(np.float32);cc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(245,47,184,107,216,71,155),default=129).astype(np.float32)
 black=np.array((.008,.010,.016),np.float32);silver=np.array((.22,.27,.31),np.float32);blue=np.array((.07,.32,.56),np.float32);violet=np.array((.29,.07,.48),np.float32);pearl=np.array((.66,.73,.78),np.float32)
 paint=black*(.42+.15*t[...,None])+silver*(.32+.18*(1-t[...,None]));z=(lip*.36)[...,None];paint=paint*(1-z)+pearl*z;z=(scratch*.13)[...,None];paint=paint*(1-z)+np.array((.75,.47,.14),np.float32)*z;z=(pool*.29)[...,None];paint=paint*(1-z)+blue*z;z=(bead*.19)[...,None];paint=paint*(1-z)+violet*z;z=(void*.22)[...,None];paint=paint*(1-z)+black*z
 m=24+53*t+90*lip+42*scratch+73*pool+84*bead+28*void;r=230-47*t-86*lip-35*scratch-67*pool-79*bead-20*void;co=23+57*t+96*lip+45*scratch+81*pool+93*bead+30*void;m=np.where(secret,sm,m);r=np.where(secret,sr,r);co=np.where(secret,cc,co)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,co=map(up,(m,r,co))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(co,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_quicksilver_helix_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_quicksilver_helix_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
