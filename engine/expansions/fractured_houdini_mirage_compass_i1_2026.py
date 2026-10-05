"""FRACTURED HOUDINI H16-I1 — Mirage Compass / black-opal micro tessellation."""
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 scale=min(1.,800./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);ph=(int(seed)%3181)*.0053
 # I3 (owner 2026-08-30): the I2 opal cells still resolved as a conspicuous
 # diagonal grid.  Rebuild as irregular fine black-opal parcels—1–2px seams,
 # inset facets, pin-fire, and voids—with no repeating square station layout.
 ux,uy=x/6.15,y/6.75;gx=np.floor(ux).astype(np.int32);gy=np.floor(uy).astype(np.int32);near=np.full((hh,ww),99.,np.float32);next_near=np.full((hh,ww),99.,np.float32);dx0=np.zeros((hh,ww),np.float32);dy0=np.zeros((hh,ww),np.float32)
 for ox in (-1,0,1):
  for oy in (-1,0,1):
   nx,ny=gx+ox,gy+oy;jx=_fract(np.sin(nx*12.9898+ny*78.233+int(seed)*.17)*43758.545);jy=_fract(np.sin(nx*93.9898+ny*31.411+int(seed)*.11)*24634.635);dx,dy=ux-(nx+jx),uy-(ny+jy);dsq=dx*dx+dy*dy;take=dsq<near;next_near=np.where(take,near,np.minimum(next_near,dsq));near=np.where(take,dsq,near);dx0=np.where(take,dx,dx0);dy0=np.where(take,dy,dy0)
 dist=np.sqrt(near);gap=np.sqrt(next_near)-dist;puddle=np.clip(1-dist/.88,0,1);state=np.mod(gx*29+gy*43+(gx^gy)*17+int(seed),8);fx=np.mod(ux,1.);fy=np.mod(uy,1.);edge=np.exp(-np.square((gap-.10)/.055));facet=np.clip((puddle-.36)*1.6,0,1)*(1-edge*.6);inset=np.clip((.22-np.abs(dx0)-np.abs(dy0))*4.2,0,1);pin=(np.mod(gx*13+gy*31+(gx^gy)*7,19)<2).astype(np.float32)*inset;void=(np.mod(gx*41+gy*11,23)<2).astype(np.float32)*(.35+.65*facet)
 # H16-I4 / owner rejection 2026-08-30: discard the tiny four-point icon.
 # Each distributed reveal is a 125–140px antique cartographic medallion made
 # from fine 8–20px engraved rings, needle inlays, graduations and three curls.
 sgx=np.floor_divide(gx,9);sgy=np.floor_divide(gy,9);U=(np.mod(gx,9)+fx)/4.5-1.;V=(np.mod(gy,9)+fy)/4.5-1.;flip=np.mod(sgx*31+sgy*43+int(seed),2)>0;U=np.where(flip,-U,U);chosen=np.mod(sgx*47+sgy*59+(sgx^sgy)*19+int(seed),10)==0
 rad=np.sqrt(U*U+V*V);th=np.arctan2(V,U);turn=.18*(_fract(np.sin(sgx*17.9+sgy*31.7+int(seed))*613.1)-.5);ct,st=np.cos(turn),np.sin(turn);A=U*ct-V*st;B=U*st+V*ct
 # Triple engraved rings and regular but fine cartographic graduations.
 rings=np.clip((.045-np.abs(rad-.69))*22.,0,1)+np.clip((.038-np.abs(rad-.48))*27.,0,1)+np.clip((.032-np.abs(rad-.275))*32.,0,1)
 tick=(np.abs(np.sin((th+turn)*16))<.14)&(rad>.57)&(rad<.75)
 # Long/short compass needles are thin outlined diamonds, not solid triangles.
 major=np.minimum(np.abs(A)*1.25+np.abs(B)*.34,np.abs(B)*1.25+np.abs(A)*.34);needle=np.clip((.062-np.abs(major-.47))*17.,0,1)*(rad<.70)
 minor=np.minimum(np.abs(A)*.54+np.abs(B)*1.25,np.abs(B)*.54+np.abs(A)*1.25);cross=np.clip((.048-np.abs(minor-.36))*20.,0,1)*(rad<.55)
 # Three delicate rhumb-line curls close the medallion with organic linework.
 curl=np.zeros_like(rad)
 for k in range(3):
  a=th+turn-k*np.pi*2/3;target=.56-.065*a;curl=np.maximum(curl,np.clip((.040-np.abs(rad-target))*22.,0,1)*(rad>.28)*(rad<.83)*(np.cos(a)>.08))
 jewel=np.clip((.075-rad)*13.,0,1);secret=chosen&((rings>.15)|tick|(needle>.16)|(cross>.16)|(curl>.18)|(jewel>.16))
 # H16-I5 override: explicit engraved medallion atlas, not a distance-field icon.
 motif=np.zeros((hh,ww),np.uint8);cw,ch=12*6.15,12*6.75
 for iy in range(int(np.ceil(hh/ch))+1):
  for ix in range(int(np.ceil(ww/cw))+1):
   if np.mod(ix*47+iy*59+(ix^iy)*19+int(seed),7): continue
   cx,cy=int((ix+.5)*cw),int((iy+.5)*ch);rr=max(17,int(min(cw,ch)*.36));thick=max(2,int(rr*.12))
   cv2.circle(motif,(cx,cy),rr,1,thick,cv2.LINE_AA);cv2.circle(motif,(cx,cy),int(rr*.68),2,thick,cv2.LINE_AA);cv2.circle(motif,(cx,cy),int(rr*.36),3,thick,cv2.LINE_AA)
   for k in range(16):
    a=k*np.pi/8;d0=rr*.79 if k%2 else rr*.69;d1=rr*.96;cv2.line(motif,(int(cx+np.cos(a)*d0),int(cy+np.sin(a)*d0)),(int(cx+np.cos(a)*d1),int(cy+np.sin(a)*d1)),4 if k%4==0 else 1,thick,cv2.LINE_AA)
   for a,val in ((-.18,5),(np.pi/2-.18,6),(np.pi-.18,5),(3*np.pi/2-.18,6)):
    dx,dy=np.cos(a),np.sin(a);px,py=-dy,dx;tip=(int(cx+dx*rr*.78),int(cy+dy*rr*.78));left=(int(cx+px*rr*.15),int(cy+py*rr*.15));right=(int(cx-px*rr*.15),int(cy-py*rr*.15));cv2.polylines(motif,[np.array([left,tip,right,(cx,cy)],np.int32)],False,val,thick,cv2.LINE_AA)
   for side in (-1,1): cv2.polylines(motif,[np.array([(cx+side*int(rr*.45),cy+int(rr*.55)),(cx+side*int(rr*.92),cy+int(rr*.78)),(cx+side*int(rr*1.08),cy+int(rr*.50))],np.int32)],False,7,thick,cv2.LINE_AA)
 secret=motif>0;q=np.where(secret,motif%8,7).astype(np.int32);sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(248,34,212,92,231,62,174),default=126).astype(np.float32);sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(12,207,55,151,28,177,80),default=122).astype(np.float32);cc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(245,47,184,107,216,71,155),default=129).astype(np.float32)
 t=state.astype(np.float32)/7.;black=np.array((.006,.010,.024),np.float32);opal=np.stack((.035+.075*t,.075+.16*(1-t),.14+.25*t),2);paint=black*.46+opal*.54;z=(edge*.43)[...,None];paint=paint*(1-z)+np.array((.012,.018,.039),np.float32)*z;z=(facet*.30)[...,None];paint=paint*(1-z)+np.array((.08,.55,.50),np.float32)*z;z=(inset*.22)[...,None];paint=paint*(1-z)+np.array((.30,.11,.56),np.float32)*z;z=(pin*.21)[...,None];paint=paint*(1-z)+np.array((.86,.62,.17),np.float32)*z;z=(void*.20)[...,None];paint=paint*(1-z)+black*z
 m=20+55*t+83*edge+62*facet+74*inset+91*pin+27*void;r=238-47*t-76*edge-58*facet-69*inset-87*pin-21*void;co=19+59*t+89*edge+69*facet+83*inset+97*pin+29*void;m=np.where(secret,sm,m);r=np.where(secret,sr,r);co=np.where(secret,cc,co)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,co=map(up,(m,r,co))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(co,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_mirage_compass_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_mirage_compass_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
