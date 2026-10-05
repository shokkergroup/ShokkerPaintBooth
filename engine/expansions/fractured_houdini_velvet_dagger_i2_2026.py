"""H9-I2 Velvet Dagger — black-ruby micro-brocade, staged P1–P11.

Owner Houdini rebuild: reject childish points, use distributed formed motifs only in
M/R/Cc.  P1–P6 were rejected carriers; P7–P11 rebuilt the textile and raised
native roughness deviation from 19.88 to 22.18 without slowing the 2048² render.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _a(shape,seed):
 k=(*map(int,shape),seed)
 with _L:
  if k in _C:_C.move_to_end(k);return _C[k]
 h,w=map(int,shape);f=min(1.,1024/max(h,w));hh,ww=max(128,round(h*f)),max(128,round(w*f));rng=np.random.default_rng(seed^0xD409);curl=np.zeros((hh,ww),np.uint8);inlay=np.zeros_like(curl);glint=np.zeros_like(curl);sec=np.zeros_like(curl);st=np.zeros_like(curl)
 # P7 reset: irregular micro-brocade, built from small engraved diamonds and leaves.
 step=10
 for row,cy in enumerate(range(-6,hh+8,step)):
  for col,cx0 in enumerate(range(-7,ww+8,step)):
   cx=cx0+(row&1)*5+rng.uniform(-.9,.9);cy0=cy+rng.uniform(-.7,.7);rx=4.1+rng.uniform(-.7,.7);ry=3.6+rng.uniform(-.6,.6);d=np.array([[cx,cy0-ry],[cx+rx,cy0],[cx,cy0+ry],[cx-rx,cy0]],np.int32)
   cv2.polylines(curl,[d],True,int(rng.integers(95,160)),1,cv2.LINE_AA)
   if (row+col)%3:
    t=np.linspace(-1.1,1.1,8);leaf=np.column_stack((cx+rx*.54*np.cos(t),cy0+ry*.54*np.sin(t))).astype(np.int32);cv2.polylines(inlay,[leaf],False,int(rng.integers(118,196)),1,cv2.LINE_AA)
   if (row*7+col*11+seed)%13==0:
    for ang in (0.,np.pi/2):
     t=np.linspace(-1.05,1.05,8);petal=np.column_stack((cx+np.cos(ang)*rx*.46*np.cos(t)-np.sin(ang)*ry*.46*np.sin(t),cy0+np.sin(ang)*rx*.46*np.cos(t)+np.cos(ang)*ry*.46*np.sin(t))).astype(np.int32);cv2.polylines(inlay,[petal],False,205,1,cv2.LINE_AA)
   if (row*5+col*3+seed)%11==0:cv2.circle(glint,(int(cx),int(cy0)),1,222,-1,cv2.LINE_AA)
 # Fine repeated blade assemblies, also represented in neutral as ordinary curls.
 for n in range(max(56,int(hh*ww/18800))):
  cx,cy=rng.uniform(18,ww-18),rng.uniform(18,hh-18);u=rng.uniform(8.0,11.2);a=rng.uniform(-1.0,1.0);R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);parts=[np.array([[0,-u*.92],[-u*.24,u*.18],[u*.24,u*.18],[0,-u*.92]],np.float32),np.array([[-u*.62,u*.20],[u*.62,u*.20]],np.float32),np.array([[0,u*.20],[0,u*.72]],np.float32),np.array([[0,u*.72],[-u*.16,u*.88],[0,u*1.04],[u*.16,u*.88],[0,u*.72]],np.float32)]
  for j,p in enumerate(parts):
   p=(p@R.T+[cx,cy]).astype(np.int32);cv2.polylines(curl,[p],j==0,int(rng.integers(76,164)),1,cv2.LINE_AA);cv2.polylines(sec,[p],j==0,int(112+(n+j)%8*17),int(rng.integers(1,3)),cv2.LINE_AA);tmp=np.zeros_like(st);cv2.polylines(tmp,[p],j==0,int((n*3+j*5+seed)%8+1),1,cv2.LINE_AA);st=np.where(tmp>0,tmp,st)
 c=curl.astype(np.float32)/255;i=inlay.astype(np.float32)/255;g=glint.astype(np.float32)/255;rel=cv2.GaussianBlur(np.maximum(c,i*.8),(0,0),2);z=cv2.GaussianBlur(rng.standard_normal((hh,ww)).astype(np.float32),(0,0),5);z=(z-z.min())/(np.ptp(z)+1e-6);coal=np.array((.050,.010,.024),np.float32);wine=np.array((.300,.035,.095),np.float32);ruby=np.array((.690,.105,.220),np.float32);rose=np.array((.820,.320,.440),np.float32);paint=coal*(.62+.15*z[...,None])+wine*(.30+.19*z[...,None]);paint=paint*(1-(rel*.37)[...,None])+wine*(rel*.37)[...,None];paint=paint*(1-(c*.50)[...,None])+ruby*(c*.50)[...,None];paint=paint*(1-(i*.45)[...,None])+rose*(i*.45)[...,None];paint=paint*(1-(g*.65)[...,None])+rose*(g*.65)[...,None]
 y,x=np.mgrid[0:hh,0:ww].astype(np.float32);mp=.5+.5*np.sin(x/7.3+np.sin(y/8.1));rp=.5+.5*np.cos((x-y)/9.2);cp=.5+.5*np.sin((x*.51+y*.73)/10.5);halo=cv2.GaussianBlur((sec>0).astype(np.float32),(0,0),2.0);m=54+z*18+mp*34+rel*54+c*64+i*58+g*78+halo*16;r=208-z*18-rp*39-rel*55-c*62-i*57-g*80-halo*17;cc=48+z*17+cp*36+rel*59+c*71+i*63+g*84+halo*19;q=np.mod(np.maximum(st,1)-1,8);sm=np.array([250,155,216,91,238,173,122,200]);sr=np.array([14,68,35,129,25,81,108,47]);sc=np.array([249,142,203,92,234,171,116,190]);hit=sec>0;m=np.where(hit,sm[q],m);r=np.where(hit,sr[q],r);cc=np.where(hit,sc[q],cc)
 if (hh,ww)!=(h,w):
  up=lambda a:cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 v=(np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255))).astype(np.uint8))
 with _L:_C[k]=v;_C.popitem(last=False) if len(_C)>2 else None
 return v
def paint_velvet_dagger_i2(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);p=np.asarray(paint,np.float32)[...,:3];p=p/255 if p.max(initial=0)>1.5 else p;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*min(1.,max(0.,float(pm))))[...,None];return np.clip(p*(1-m)+a*m,0,1).astype(np.float32)
def spec_velvet_dagger_i2(shape,seed,sm,bm,br):del sm,bm,br;return _a(shape,seed)[1]
