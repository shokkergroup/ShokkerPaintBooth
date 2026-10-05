"""FRACTURED HOUDINI H6-I1 — Prism Moth / opaline feather enamel."""
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np
_CACHE,_LOCK=OrderedDict(),RLock()
def _fract(a):return a-np.floor(a)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _LOCK:
  if key in _CACHE:_CACHE.move_to_end(key);return _CACHE[key]
 scale=min(1.,864./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);p=(int(seed)%3469)*.0051
 a=(x+5.6*np.sin(y/27+p)+2.7*np.cos((x-y)/45))/5.9;b=(y-4.5*np.sin(x/36-.6*p)+3.2*np.cos((x+2*y)/63))/7.6;c=(x*.48-y*.52+4.4*np.sin((2*x+y)/71+.2*p))/11.5
 quill=np.maximum(np.exp(-np.square(np.sin(a)/.105)),np.exp(-np.square(np.sin(.57*b+.38*c)/.12)));barb=np.exp(-np.square(np.sin(.43*a-.71*b+c)/.19));sheen=.5+.5*np.sin(.81*a+.35*b-.29*c);opal=np.clip((sheen-.69)/.31,0,1)*(1-.60*quill);nick=np.exp(-np.square(np.sin(.26*a+.52*b-.49*c)/.068))*(1-.55*quill)
 gx=np.floor((a-.23*c)/1.46).astype(np.int32);gy=np.floor((b+.27*c)/1.59).astype(np.int32);state=np.mod(gx*31+gy*47+(gx^gy)*9+int(seed),8)
 # I3: reject regular cells completely.  Nearby hash-jittered feather puddles
 # make a continuous, non-rowed opaline surface; their individual cores/rims
 # retain 9–26px native detail without becoming grain or a geometric grid.
 ux,uy=x/6.9,y/6.2;ix=np.floor(ux).astype(np.int32);iy=np.floor(uy).astype(np.int32);near=np.full((hh,ww),99.,np.float32);next_near=np.full((hh,ww),99.,np.float32);scale_state=np.zeros((hh,ww),np.float32)
 for ox in (-1,0,1):
  for oy in (-1,0,1):
   nx,ny=ix+ox,iy+oy;jx=_fract(np.sin(nx*14.37+ny*82.19+int(seed)*.13)*41721.37);jy=_fract(np.sin(nx*91.17+ny*34.71+int(seed)*.19)*31847.91);dsq=(ux-(nx+jx))**2+(uy-(ny+jy))**2;take=dsq<near;next_near=np.where(take,near,np.minimum(next_near,dsq));near=np.where(take,dsq,near);local=np.mod(nx*29+ny*17+(nx^ny)*11+int(seed),8).astype(np.float32)/7.;scale_state=np.where(take,local,scale_state)
 scale_body=np.clip(1-np.sqrt(near)/.89,0,1);scale_rim=np.exp(-np.square((np.sqrt(next_near)-np.sqrt(near)-.10)/.052))
 X,Y=x/ww,y/hh;secret=np.zeros((hh,ww),bool)
 # Eighteen independent, rotated moths — paired wings, body and antennae are
 # M/R/Cc geometry only and therefore have no RGB moth/decal silhouette.
 for n in range(18):
  h1=_fract(np.sin((n+3)*73.63+p)*21917.51);h2=_fract(np.sin((n+8)*39.47+p*1.4)*18731.23);h3=_fract(np.sin((n+5)*93.19+p*1.8)*9127.83);cx=.04+.92*_fract(.151+n*.75487767+.18*h1);cy=.04+.92*_fract(.291+n*.56984029+.17*h2);s=.057+.034*h3;ux,vy=(X-cx)/s,(Y-cy)/s;ang=(h2-.5)*2.1;u=np.cos(ang)*ux-np.sin(ang)*vy;v=np.sin(ang)*ux+np.cos(ang)*vy
  wl=((u+.31)/.42)**2+((v+.02)/.53)**2<1;wr=((u-.31)/.42)**2+((v+.02)/.53)**2<1;cutl=((u+.29)/.18)**2+((v+.02)/.27)**2<1;cutr=((u-.29)/.18)**2+((v+.02)/.27)**2<1;body=(u/.105)**2+((v+.02)/.52)**2<1;antenna=(np.abs(u)-.10<.035)&(v<-.35)&(v>-.76);secret|=((wl|wr|body|antenna)&~(cutl&cutr))
 parcel=np.mod(gx*13+gy*5+np.floor(c*1.7).astype(np.int32)*7,9);secret&=(parcel<8)|(quill>.80)|(barb>.86)|(opal>.40)
 ink=np.array((.014,.010,.032),np.float32);violet=np.array((.12,.055,.30),np.float32);indigo=np.array((.06,.11,.34),np.float32);teal=np.array((.06,.31,.32),np.float32);pearl=np.array((.50,.34,.69),np.float32)
 # I4: quill/barb belong in the material response, not as a visible set of
 # global stripes.  Let the irregular feather puddles carry the RGB surface.
 paint=ink*(.42+.11*sheen[...,None])+violet*(.38+.16*(1-sheen[...,None]));scale_tint=indigo*(.48+.31*scale_state[...,None])+teal*(.12+.16*(1-scale_state[...,None]));z=(scale_body*.34)[...,None];paint=paint*(1-z)+scale_tint*z;z=(scale_rim*.20)[...,None];paint=paint*(1-z)+pearl*z;z=(opal*.21+nick*.09)[...,None];paint=paint*(1-z)+pearl*z
 t=state.astype(np.float32)/7.;m=27+47*t+78*quill+54*barb+76*opal+32*nick;r=225-42*t-67*quill-47*barb-67*opal-28*nick;cc=24+50*t+82*quill+63*barb+89*opal+38*nick;q=np.mod(state+np.floor(a*.44).astype(np.int32)+np.floor(c*.38).astype(np.int32),8);sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(251,165,221,177,241,151,202),default=187).astype(np.float32);sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(10,61,49,90,25,79,43),default=70).astype(np.float32);sc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(249,142,196,120,225,159,171),default=133).astype(np.float32);m=np.where(secret,sm,m);r=np.where(secret,sr,r);cc=np.where(secret,sc,cc)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255)),2).astype(np.uint8))
 with _LOCK:_CACHE[key]=out;_CACHE.popitem(last=False) if len(_CACHE)>2 else None
 return out
def paint_prism_moth_i1(paint,shape,mask,seed,pm,bb):
 del bb;authored,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+authored*mix,0,1).astype(np.float32)
def spec_prism_moth_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
