"""H6-I6 Prism Moth — isolated smoky-violet feather lacquer P1, no grid."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _make(shape,seed):
 h,w=map(int,shape);f=min(1.,1024/max(h,w));hh,ww=max(128,round(h*f)),max(128,round(w*f));rng=np.random.default_rng(seed^0x6D071);quill=np.zeros((hh,ww),np.uint8);barb=np.zeros_like(quill);pearl=np.zeros_like(quill);sec=np.zeros_like(quill);st=np.zeros_like(quill)
 # Irregular quill/vane/barb carrier: 2–14 authored pixels, phase broken.
 for _ in range(max(2700,int(hh*ww/370))):
  cx,cy=rng.uniform(-18,ww+18),rng.uniform(-18,hh+18);a=rng.uniform(-1.1,1.1);L=rng.uniform(4,13);p=np.array([[-L,0],[-L*.25,rng.uniform(-4,4)],[L*.35,rng.uniform(-3,3)],[L,0]],np.float32);R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);p=(p@R.T+[cx,cy]).astype(np.int32);cv2.polylines(quill,[p],False,int(rng.integers(70,190)),int(rng.integers(1,3)),cv2.LINE_AA)
  for q in p[1:3]:
   if rng.random()<.55:cv2.circle(barb,tuple(q),int(rng.integers(1,3)),int(rng.integers(80,210)),-1,cv2.LINE_AA)
  if rng.random()<.3:cv2.circle(pearl,tuple(p[2]),int(rng.integers(1,3)),int(rng.integers(120,255)),-1,cv2.LINE_AA)
 # P3: connected fine vane sweeps turn the micro quills into a lacquered
 # feather field, without regular rows or broad ribbon geometry.
 for _ in range(max(165,int(hh*ww/8300))):
  cx,cy=rng.uniform(-28,ww+28),rng.uniform(-24,hh+24);a=rng.uniform(-.75,.75);span=rng.uniform(17,44);amp=rng.uniform(4,10);t=np.linspace(-1,1,13);p=np.column_stack((t*span,amp*np.sin(t*np.pi*.88)+t*t*amp*.25));R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);p=(p@R.T+[cx,cy]).astype(np.int32)
  for u,v in zip(p[::2][:-1],p[::2][1:]):cv2.line(quill,tuple(u),tuple(v),int(rng.integers(85,190)),2,cv2.LINE_AA)
  for q in p[3:-3:4]:cv2.circle(barb,tuple(q),int(rng.integers(1,3)),int(rng.integers(90,205)),-1,cv2.LINE_AA)
 # 30 small, irregular moths composed from ordinary feather-like wing strokes.
 for n in range(max(30,int(hh*ww/34000))):
  cx,cy=rng.uniform(30,ww-30),rng.uniform(28,hh-28);rx,ry=rng.uniform(11,17),rng.uniform(9,15);a=rng.uniform(-.65,.65);R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32)
  for side in (-1,1):
   wing=np.array([[0,ry*.35],[side*rx*.25,-ry*.06],[side*rx*.82,-ry*.68],[side*rx*1.04,-ry*.16],[side*rx*.78,ry*.38],[side*rx*.25,ry*.53],[0,ry*.35]],np.float32)@R.T+[cx,cy];wing=wing.astype(np.int32);cv2.polylines(quill,[wing],True,int(rng.integers(70,165)),1,cv2.LINE_AA);cv2.polylines(sec,[wing],True,int(108+(n+side)%8*18),int(rng.integers(1,3)),cv2.LINE_AA);tmp=np.zeros_like(st);cv2.polylines(tmp,[wing],True,int((n*3+(side+1)*3+seed)%8+1),1,cv2.LINE_AA);st=np.where(tmp>0,tmp,st)
   for k in range(3):
    p=np.array([[0,ry*.30],[side*rx*(.40+.12*k),-ry*(.30+.12*k)]],np.float32)@R.T+[cx,cy];p=p.astype(np.int32);cv2.line(quill,tuple(p[0]),tuple(p[1]),int(rng.integers(72,158)),1,cv2.LINE_AA);cv2.line(sec,tuple(p[0]),tuple(p[1]),int(122+(n+k)%7*16),1,cv2.LINE_AA)
  body=(np.array([[0,-ry*.25],[0,ry*.48]],np.float32)@R.T+[cx,cy]).astype(np.int32);cv2.line(quill,tuple(body[0]),tuple(body[1]),int(rng.integers(75,166)),2,cv2.LINE_AA);cv2.line(sec,tuple(body[0]),tuple(body[1]),255,2,cv2.LINE_AA)
 # P2: picker-scale lift for the normal smoky-violet lacquer only.
 # P4: existing barb clusters get deeper lilac/ice separation, still no moth RGB.
 q=quill.astype(np.float32)/255;b=barb.astype(np.float32)/255;p=pearl.astype(np.float32)/255;rel=cv2.GaussianBlur(np.maximum(q,b*.8),(0,0),2);z=cv2.GaussianBlur(rng.standard_normal((hh,ww)).astype(np.float32),(0,0),5);z=(z-z.min())/(np.ptp(z)+1e-6);char=np.array((.050,.040,.095),np.float32);violet=np.array((.180,.105,.390),np.float32);amethyst=np.array((.410,.225,.680),np.float32);ice=np.array((.735,.680,.970),np.float32);lilac=np.array((.575,.330,.805),np.float32);paint=char*(.58+.15*z[...,None])+violet*(.36+.20*z[...,None]);paint=paint*(1-(rel*.43)[...,None])+violet*(rel*.43)[...,None];paint=paint*(1-(q*.58)[...,None])+amethyst*(q*.58)[...,None];paint=paint*(1-(b*.34)[...,None])+lilac*(b*.34)[...,None];paint=paint*(1-(b*.28)[...,None])+ice*(b*.28)[...,None];paint=paint*(1-(p*.70)[...,None])+ice*(p*.70)[...,None]
 y,x=np.mgrid[0:hh,0:ww].astype(np.float32);mp=.5+.5*np.sin(x/7.5+np.sin(y/8));rp=.5+.5*np.cos((x-y)/9.5);cp=.5+.5*np.sin((x*.52+y*.71)/10.4);m=49+z*24+mp*60+rel*45+q*70+b*62+p*87;r=211-z*18-rp*54-rel*42-q*61-b*57-p*80;cc=42+z*20+cp*66+rel*53+q*77+b*68+p*94;q8=np.mod(np.maximum(st,1)-1,8);sm=np.array([250,155,216,91,238,173,122,200]);sr=np.array([14,68,35,129,25,81,108,47]);sc=np.array([249,142,203,92,234,171,116,190]);hit=sec>0;m=np.where(hit,sm[q8],m);r=np.where(hit,sr[q8],r);cc=np.where(hit,sc[q8],cc)
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
def paint_prism_moth_i6(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);p=np.asarray(paint,np.float32)[...,:3];p=p/255 if p.max(initial=0)>1.5 else p;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*min(1.,max(0.,float(pm))))[...,None];return np.clip(p*(1-m)+a*m,0,1).astype(np.float32)
def spec_prism_moth_i6(shape,seed,sm,bm,br):del sm,bm,br;return _a(shape,seed)[1]
