"""FRACTURED HOUDINI H8-I5 — Aurora Wolf / sapphire kintsugi pack."""
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 scale=min(1.,640./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);ph=(int(seed)%2953)*.0062
 # I4 (owner 2026-08-30): retire the broad aurora-wave marquetry.  This
 # sapphiric carrier is irregular 8–28px enamel: gold hairline rims, lapis
 # pools, small pearl petals and iron fractures, all bound to local parcels.
 ux,uy=x/5.15,y/6.55;gx=np.floor(ux).astype(np.int32);gy=np.floor(uy).astype(np.int32);near=np.full((hh,ww),99.,np.float32);next_near=np.full((hh,ww),99.,np.float32);dx0=np.zeros((hh,ww),np.float32);dy0=np.zeros((hh,ww),np.float32)
 for ox in (-1,0,1):
  for oy in (-1,0,1):
   nx,ny=gx+ox,gy+oy;jx=_fract(np.sin(nx*12.9898+ny*78.233+int(seed)*.17)*43758.545);jy=_fract(np.sin(nx*93.9898+ny*31.411+int(seed)*.11)*24634.635);dx,dy=ux-(nx+jx),uy-(ny+jy);dsq=dx*dx+dy*dy;take=dsq<near;next_near=np.where(take,near,np.minimum(next_near,dsq));near=np.where(take,dsq,near);dx0=np.where(take,dx,dx0);dy0=np.where(take,dy,dy0)
 dist=np.sqrt(near);seamgap=np.sqrt(next_near)-dist;puddle=np.clip(1-dist/.88,0,1);state=np.mod(gx*17+gy*53+(gx^gy)*15+int(seed),8);field=state.astype(np.float32)/7.;seam=np.exp(-np.square((seamgap-.10)/.055));petal=np.clip((puddle-.50)*2.15,0,1)*(.25+.75*np.mod(gx*19+gy*11+int(seed),5)/4.);pool=np.clip((puddle-.24)*1.33,0,1)*(1-.61*seam);fract=np.clip((.052-np.abs(dx0*.63-dy0*.48-(field-.5)*.16))*16.,0,1)*(1-.55*seam)
 # H8-I7 / owner hard reset: explicit aurora-wolf reliefs replace formula
 # heads. Ear tufts, cheek fur, brow ridge, inset eyes, snout and moon-halo
 # are separate fine material states; sapphire RGB contains no wolf pixels.
 face=np.zeros((hh,ww),np.uint8);eye=np.zeros((hh,ww),np.uint8);fur=np.zeros((hh,ww),np.uint8);halo=np.zeros((hh,ww),np.uint8);rng=np.random.default_rng(int(seed)^0xA808);count=max(34,int(hh*ww/11000))
 for n in range(count):
  cx=float(rng.uniform(-22,ww+22));cy=float(rng.uniform(-25,hh+25));rx=float(rng.uniform(17,28));ry=float(rng.uniform(21,34));ang=float(rng.uniform(-.40,.40));ca,sa=np.cos(ang),np.sin(ang);th=int(rng.integers(2,4))
  def pt(px,py):return tuple(np.rint((cx+ca*px-sa*py,cy+sa*px+ca*py)).astype(np.int32))
  outline=[(0,-ry*.78),(-rx*.44,-ry*.31),(-rx*.78,-ry*.75),(-rx*.64,-ry*.05),(-rx*.48,ry*.42),(0,ry*.82),(rx*.48,ry*.42),(rx*.64,-ry*.05),(rx*.78,-ry*.75),(rx*.44,-ry*.31)]
  cv2.polylines(face,[np.array([pt(px,py) for px,py in outline],np.int32)],True,1,th,cv2.LINE_AA)
  for side,val in ((-1,3),(1,5)):
   brow=[(side*rx*.10,-ry*.14),(side*rx*.43,-ry*.02),(side*rx*.26,ry*.10)];cv2.polylines(face,[np.array([pt(px,py) for px,py in brow],np.int32)],False,val,th,cv2.LINE_AA)
   cv2.ellipse(eye,pt(side*rx*.25,-ry*.02),(max(3,int(rx*.12)),max(2,int(ry*.07))),int(np.degrees(ang))+side*11,0,360,255,-1,cv2.LINE_AA)
   for k in range(4):cv2.line(fur,pt(side*rx*(.18+.08*k),ry*(.16+.12*k)),pt(side*rx*(.52+.08*k),ry*(.38+.11*k)),val,1,cv2.LINE_AA)
  cv2.line(face,pt(0,ry*.07),pt(0,ry*.56),2,th,cv2.LINE_AA);cv2.ellipse(halo,pt(0,-ry*.10),(int(rx*.96),int(ry*.94)),int(np.degrees(ang)),205,335,255,1,cv2.LINE_AA)
 secret=(face>0)|(eye>0)|(fur>0)|(halo>0);sm=np.where(face>0,240,np.where(eye>0,252,np.where(fur>0,177,np.where(halo>0,205,0)))).astype(np.float32);sr=np.where(face>0,18,np.where(eye>0,9,np.where(fur>0,79,np.where(halo>0,53,0)))).astype(np.float32);sc=np.where(face>0,244,np.where(eye>0,251,np.where(fur>0,158,np.where(halo>0,184,0)))).astype(np.float32)
 abyss=np.array((.006,.015,.046),np.float32);lapis=np.array((.025,.10,.32),np.float32);azure=np.array((.08,.24,.56),np.float32);gold=np.array((.58,.32,.08),np.float32);pearlc=np.array((.48,.57,.83),np.float32)
 paint=abyss*(.52+.12*field[...,None])+lapis*(.34+.16*(1-field[...,None]));z=(seam*.32)[...,None];paint=paint*(1-z)+gold*z;z=(petal*.20)[...,None];paint=paint*(1-z)+azure*z;z=(pool*.25+fract*.10)[...,None];paint=paint*(1-z)+pearlc*z
 t=state.astype(np.float32)/7.;m=27+47*t+78*seam+53*petal+77*pool+31*fract;r=225-43*t-67*seam-47*petal-68*pool-27*fract;cc=24+50*t+83*seam+63*petal+90*pool+37*fract;m=np.where(secret,sm,m);r=np.where(secret,sr,r);cc=np.where(secret,sc,cc)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_seraph_eye_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_seraph_eye_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
