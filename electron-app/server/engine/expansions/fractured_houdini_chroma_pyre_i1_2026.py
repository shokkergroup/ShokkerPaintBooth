"""FRACTURED HOUDINI H18-I1 — Chroma Pyre / hidden material flames."""
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 scale=min(1.,800./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);ph=(int(seed)%3371)*.0046
 # I3 (owner 2026-08-30): remove the visible red flow lattice.  Chroma-slag
 # becomes irregular angular heat parcels: carbon seams, fused rims, hot
 # micro-crazing, violet bloom pockets and sparse embedded ember points.
 ux,uy=x/6.35,y/7.05;gx=np.floor(ux).astype(np.int32);gy=np.floor(uy).astype(np.int32);near=np.full((hh,ww),99.,np.float32);next_near=np.full((hh,ww),99.,np.float32);dx0=np.zeros((hh,ww),np.float32);dy0=np.zeros((hh,ww),np.float32)
 for ox in (-1,0,1):
  for oy in (-1,0,1):
   nx,ny=gx+ox,gy+oy;jx=_fract(np.sin(nx*12.9898+ny*78.233+int(seed)*.17)*43758.545);jy=_fract(np.sin(nx*93.9898+ny*31.411+int(seed)*.11)*24634.635);dx,dy=ux-(nx+jx),uy-(ny+jy);dsq=dx*dx+dy*dy;take=dsq<near;next_near=np.where(take,near,np.minimum(next_near,dsq));near=np.where(take,dsq,near);dx0=np.where(take,dx,dx0);dy0=np.where(take,dy,dy0)
 dist=np.sqrt(near);gap=np.sqrt(next_near)-dist;plate=np.clip(1-dist/.88,0,1);seam=np.exp(-np.square((gap-.10)/.055));state=np.mod(gx*31+gy*17+(gx^gy)*19+int(seed),8);fx=np.mod(ux,1.);fy=np.mod(uy,1.);t=state.astype(np.float32)/7.;fuse=np.clip((.050-np.abs(dx0*.61-dy0*.59-(t-.5)*.15))*17.,0,1)*(1-seam*.55);craze=np.clip((.034-np.abs(dx0*.41+dy0*.78-(t-.5)*.11))*24.,0,1);ember=(np.mod(gx*37+gy*23+(gx^gy)*3,29)<2).astype(np.float32)*plate
 # H18-I5 / owner rejection 2026-08-30: no filled cartoon flame silhouettes.
 # Each 125–140px reveal is layered 8–20px flame filaments, forked tongues,
 # inner ember curls and small negative gaps, repeated across the slag field.
 sgx=np.floor_divide(gx,9);sgy=np.floor_divide(gy,9);U=(np.mod(gx,9)+fx)/4.5-1.;V=(np.mod(gy,9)+fy)/4.5-1.;flip=np.mod(sgx*31+sgy*43+int(seed),2)>0;U=np.where(flip,-U,U);chosen=np.mod(sgx*47+sgy*59+(sgx^sgy)*19+int(seed),10)==0
 lift=(V+.78)/1.58;center=.13*np.sin(7.2*V)+.06*np.sin(13.7*V);outer=.44*(1-lift)+.08
 left=np.clip((.055-np.abs(U-(center-outer)))*18.,0,1)*(V>-.82)*(V<.76);right=np.clip((.055-np.abs(U-(center+outer)))*18.,0,1)*(V>-.82)*(V<.76)
 tongue1=np.clip((.047-np.abs(U-(center+.18*np.sin(9.0*V+.7))))*21.,0,1)*(V>-.58)*(V<.72);tongue2=np.clip((.041-np.abs(U-(center-.14*np.sin(11.2*V-.4))))*24.,0,1)*(V>-.48)*(V<.62)
 ember=np.clip((.042-np.abs(np.sqrt((U-center)**2+(V-.13)**2)-.16))*23.,0,1);fork=(np.abs(np.sin((V+.58)*11))<.11)&(np.abs(U-center)<outer*.72)&(V>-.55)&(V<.32)
 secret=chosen&((left>.15)|(right>.15)|(tongue1>.15)|(tongue2>.15)|(ember>.16)|fork);heart=chosen&((ember>.22)|fork)
 # H18-I7 / owner 2026-08-30: I6 still read as a noisy field with a handful
 # of thin icons.  This is a dense, hand-engraved relief atlas: an all-over
 # fire tapestry of overlapping tongues, curl hooks, ember beads and channel
 # hatching. Each motif is ~85x110px at 2048; every material mark is 8-28px.
 # H18-I8: destroy the visible tile cadence.  These irregularly distributed,
 # rotated engravings are individual flame reliefs, each built from five
 # tongues, inset bead-curls, hook filigree and fine channel hatching.
 motif=np.zeros((hh,ww),np.uint8);rng=np.random.default_rng(int(seed)^0x5EED18);count=max(48,int(hh*ww/10500))
 for n in range(count):
  cx=float(rng.uniform(-14,ww+14));cy=float(rng.uniform(-18,hh+18));span=float(rng.uniform(31,48));amp=float(rng.uniform(12,21));thick=int(rng.integers(2,4));ang=float(rng.uniform(-.46,.46));ca,sa=np.cos(ang),np.sin(ang);phase=float(rng.uniform(0,6.283));lean=float(rng.uniform(-.20,.20))
  def _rot(points):
   p=np.asarray(points,np.float32);return np.rint(np.column_stack((cx+ca*p[:,0]-sa*p[:,1],cy+sa*p[:,0]+ca*p[:,1]))).astype(np.int32)
  ys=np.linspace(span,-span,45)
  for lane,val,p in ((-1,1,.10),(1,2,.82),(-1,3,1.52),(1,4,2.19),(0,5,2.82)):
   px=lean*amp*(1-(ys/span)**2)+lane*(amp*(.20+.74*(ys+span)/(2*span)))+amp*.20*np.sin(ys*.18+p+phase)
   cv2.polylines(motif,[_rot(np.column_stack((px,ys)))],False,val,thick if val<3 else max(1,thick-1),cv2.LINE_AA)
  for j,v in enumerate(np.linspace(-span*.65,span*.60,5)):
   px=amp*.22*np.sin(v*.19+phase);pt=_rot([[px,v]])[0];cv2.ellipse(motif,tuple(pt),(max(2,thick+(j&1))*2,max(2,thick+(j&1))),int(np.degrees(ang))-30,20,310,6,-1,cv2.LINE_AA)
  for side in (-1,1): cv2.polylines(motif,[_rot([(side*amp*.12,span*.17),(side*amp*.72,-span*.08),(side*amp*.48,-span*.47),(side*amp*.14,-span*.68)])],False,7,1,cv2.LINE_AA)
  for off in np.linspace(-amp*.52,amp*.52,6): cv2.line(motif,tuple(_rot([[off,span*.56]])[0]),tuple(_rot([[off*.32,span*.24]])[0]),8,1,cv2.LINE_AA)
 secret=motif>0;q=np.where(secret,motif%8,7).astype(np.int32);sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(248,34,212,92,231,62,174),default=126).astype(np.float32);sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(12,207,55,151,28,177,80),default=122).astype(np.float32);cc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(245,47,184,107,216,71,155),default=129).astype(np.float32)
 # I4: I3's isolated hot points read as confetti.  Build a connected dark
 # chroma-slag hierarchy: every parcel carries a related heat state, rims join
 # it, and only rare points brighten—not random floating embers.
 coal=np.array((.011,.006,.010),np.float32);oxide=np.array((.25,.032,.018),np.float32);violet=np.array((.30,.045,.42),np.float32);amber=np.array((.78,.18,.018),np.float32);gold=np.array((.90,.50,.08),np.float32);heat=oxide*(.55+.45*(1-t[...,None]))+violet*(.10+.22*t[...,None]);paint=coal*(.28+.09*t[...,None])+heat*(.58+.16*(1-t[...,None]));z=(seam*.31)[...,None];paint=paint*(1-z)+coal*z;z=(plate*.42)[...,None];paint=paint*(1-z)+(oxide*.48+violet*.52)*z;z=(fuse*.34)[...,None];paint=paint*(1-z)+amber*z;z=(craze*.18)[...,None];paint=paint*(1-z)+gold*z;z=(ember*.10)[...,None];paint=paint*(1-z)+gold*z
 m=22+53*t+85*seam+70*plate+79*fuse+44*craze+94*ember;r=236-47*t-78*seam-64*plate-72*fuse-37*craze-88*ember;co=20+57*t+92*seam+76*plate+88*fuse+48*craze+102*ember;m=np.where(secret,sm,m);r=np.where(secret,sr,r);co=np.where(secret,cc,co)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,co=map(up,(m,r,co))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(co,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_chroma_pyre_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_chroma_pyre_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
