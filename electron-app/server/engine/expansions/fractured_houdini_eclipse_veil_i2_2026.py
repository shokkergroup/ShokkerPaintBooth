"""H7-I2 Eclipse Veil — isolated charcoal astral lacquer P1 (no microcells)."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _make(shape,seed):
 h,w=map(int,shape);f=min(1.,1024/max(h,w));hh,ww=max(128,round(h*f)),max(128,round(w*f));rng=np.random.default_rng(seed^0xE711);cut=np.zeros((hh,ww),np.uint8);orbit=np.zeros_like(cut);glint=np.zeros_like(cut);sec=np.zeros_like(cut);st=np.zeros_like(cut)
 # Neutral fine orbital/lapidary work, explicitly non-cellular.
 for _ in range(max(2500,int(hh*ww/390))):
  cx,cy=rng.uniform(-18,ww+18),rng.uniform(-18,hh+18);rx,ry=rng.uniform(3,10),rng.uniform(2,7);a0=rng.uniform(0,6.28);arc=rng.uniform(.38,1.72);t=np.linspace(a0,a0+arc,8);p=np.column_stack((cx+rx*np.cos(t),cy+ry*np.sin(t))).astype(np.int32);cv2.polylines(cut,[p],False,int(rng.integers(72,190)),int(rng.integers(1,3)),cv2.LINE_AA)
  if rng.random()<.5:cv2.polylines(orbit,[p[2:7]],False,int(rng.integers(88,220)),1,cv2.LINE_AA)
  if rng.random()<.3:cv2.circle(glint,tuple(p[4]),int(rng.integers(1,3)),int(rng.integers(115,255)),-1,cv2.LINE_AA)
 # P3: connected fine astrolabe filigree reduces P2's star-speck read without
 # creating a regular grid or a visible eclipse icon.
 for _ in range(max(170,int(hh*ww/8300))):
  cx,cy=rng.uniform(-28,ww+28),rng.uniform(-24,hh+24);a=rng.uniform(-.72,.72);span=rng.uniform(17,44);amp=rng.uniform(4,10);t=np.linspace(-1,1,13);p=np.column_stack((t*span,amp*np.sin(t*np.pi*.88)+t*t*amp*.25));R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);p=(p@R.T+[cx,cy]).astype(np.int32)
  for u,v in zip(p[::2][:-1],p[::2][1:]):cv2.line(cut,tuple(u),tuple(v),int(rng.integers(85,190)),2,cv2.LINE_AA)
  for q in p[3:-3:4]:cv2.circle(orbit,tuple(q),int(rng.integers(1,3)),int(rng.integers(90,205)),-1,cv2.LINE_AA)
 # Repeated small eclipse astrolabes, stroke-compatible with neutral carrier.
 for n in range(max(32,int(hh*ww/32000))):
  cx,cy=rng.uniform(27,ww-27),rng.uniform(27,hh-27);rad=rng.uniform(10,16);a=rng.uniform(-.6,.6);R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32)
  for k,(start,end) in enumerate(((.45,2.85),(3.30,5.85))):
   t=np.linspace(start,end,18);p=np.column_stack((rad*np.cos(t),rad*.83*np.sin(t)))@R.T+[cx,cy];p=p.astype(np.int32);cv2.polylines(cut,[p],False,int(rng.integers(76,162)),1,cv2.LINE_AA);cv2.polylines(sec,[p],False,int(110+(n+k)%8*17),int(rng.integers(1,3)),cv2.LINE_AA);tmp=np.zeros_like(st);cv2.polylines(tmp,[p],False,int((n*3+k*5+seed)%8+1),1,cv2.LINE_AA);st=np.where(tmp>0,tmp,st)
  for q in (-.6,0,.6):
   p=np.array([[np.cos(q)*rad*.68,np.sin(q)*rad*.57],[np.cos(q)*rad*1.02,np.sin(q)*rad*.86]])@R.T+[cx,cy];p=p.astype(np.int32);cv2.line(cut,tuple(p[0]),tuple(p[1]),int(rng.integers(75,154)),1,cv2.LINE_AA);cv2.line(sec,tuple(p[0]),tuple(p[1]),255,1,cv2.LINE_AA)
 # P2: picker-scale lift of the neutral astral lacquer, no eclipse RGB.
 # P4: existing mineral glints gain a quiet violet interference edge.
 c=cut.astype(np.float32)/255;o=orbit.astype(np.float32)/255;g=glint.astype(np.float32)/255;rel=cv2.GaussianBlur(np.maximum(c,o*.8),(0,0),2);z=cv2.GaussianBlur(rng.standard_normal((hh,ww)).astype(np.float32),(0,0),5);z=(z-z.min())/(np.ptp(z)+1e-6);coal=np.array((.050,.065,.105),np.float32);navy=np.array((.100,.205,.380),np.float32);teal=np.array((.060,.500,.505),np.float32);silver=np.array((.720,.800,.885),np.float32);violet=np.array((.405,.185,.620),np.float32);paint=coal*(.56+.16*z[...,None])+navy*(.36+.20*z[...,None]);paint=paint*(1-(rel*.42)[...,None])+navy*(rel*.42)[...,None];paint=paint*(1-(c*.57)[...,None])+teal*(c*.57)[...,None];paint=paint*(1-(o*.51)[...,None])+silver*(o*.51)[...,None];paint=paint*(1-(g*.42)[...,None])+silver*(g*.42)[...,None];paint=paint*(1-(g*.24)[...,None])+violet*(g*.24)[...,None]
 y,x=np.mgrid[0:hh,0:ww].astype(np.float32);mp=.5+.5*np.sin(x/7.4+np.sin(y/8.2));rp=.5+.5*np.cos((x-y)/9.3);cp=.5+.5*np.sin((x*.51+y*.74)/10.5);m=49+z*24+mp*60+rel*44+c*69+o*62+g*87;r=211-z*18-rp*54-rel*41-c*61-o*57-g*79;cc=42+z*20+cp*66+rel*52+c*77+o*68+g*94;q=np.mod(np.maximum(st,1)-1,8);sm=np.array([250,155,216,91,238,173,122,200]);sr=np.array([14,68,35,129,25,81,108,47]);sc=np.array([249,142,203,92,234,171,116,190]);hit=sec>0;m=np.where(hit,sm[q],m);r=np.where(hit,sr[q],r);cc=np.where(hit,sc[q],cc)
 if (hh,ww)!=(h,w):
  up=lambda a:cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 return np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255))).astype(np.uint8)
def _a(shape,seed):
 k=(*map(int,shape),seed)
 with _L:
  if k in _C:_C.move_to_end(k);return _C[k]
 v=_make(shape,seed)
 with _L:_C[k]=v;_C.popitem(last=False) if len(_C)>2 else None
 return v
def paint_eclipse_veil_i2(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);p=np.asarray(paint,np.float32)[...,:3];p=p/255 if p.max(initial=0)>1.5 else p;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*min(1.,max(0.,float(pm))))[...,None];return np.clip(p*(1-m)+a*m,0,1).astype(np.float32)
def spec_eclipse_veil_i2(shape,seed,sm,bm,br):del sm,bm,br;return _a(shape,seed)[1]
