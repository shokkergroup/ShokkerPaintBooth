"""H5-I2 Ouroboros — isolated black-plum mother-of-pearl lacquer, P1."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _make(shape,seed):
 h,w=map(int,shape);f=min(1.,1024/max(h,w));hh,ww=max(128,round(h*f)),max(128,round(w*f));rng=np.random.default_rng(seed^0x0B0E);y,x=np.mgrid[0:hh,0:ww].astype(np.float32);etch=np.zeros((hh,ww),np.uint8);shell=np.zeros_like(etch);pearl=np.zeros_like(etch);sec=np.zeros_like(etch);st=np.zeros_like(etch)
 # Fine non-grid lacquer anatomy: overlapping crescent scales, hairline
 # inlays and shell flashes, all 2–14 authored px / 8–28 native px.
 for _ in range(max(1700,int(hh*ww/580))):
  cx,cy=rng.uniform(-18,ww+18),rng.uniform(-18,hh+18);rx,ry=rng.uniform(3,9),rng.uniform(2,6);a0=rng.uniform(0,6.28);arc=rng.uniform(.45,1.85);t=np.linspace(a0,a0+arc,8);p=np.column_stack((cx+rx*np.cos(t),cy+ry*np.sin(t))).astype(np.int32);cv2.polylines(etch,[p],False,int(rng.integers(70,190)),int(rng.integers(1,3)),cv2.LINE_AA)
  if rng.random()<.55:cv2.polylines(shell,[p[2:7]],False,int(rng.integers(85,225)),1,cv2.LINE_AA)
  if rng.random()<.33:cv2.circle(pearl,tuple(p[4]),int(rng.integers(1,3)),int(rng.integers(100,255)),-1,cv2.LINE_AA)
 # P3: fine shell filigree connects the carrier without a tile lattice.
 for _ in range(max(170,int(hh*ww/8200))):
  cx,cy=rng.uniform(-30,ww+30),rng.uniform(-24,hh+24);a=rng.uniform(-.72,.72);span=rng.uniform(18,46);amp=rng.uniform(4,11);t=np.linspace(-1,1,13);p=np.column_stack((t*span,amp*np.sin(t*np.pi*.9)+t*t*amp*.28));R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);p=(p@R.T+[cx,cy]).astype(np.int32)
  for u,v in zip(p[::2][:-1],p[::2][1:]):cv2.line(etch,tuple(u),tuple(v),int(rng.integers(88,190)),2,cv2.LINE_AA)
  for q in p[3:-3:4]:cv2.circle(shell,tuple(q),int(rng.integers(1,3)),int(rng.integers(90,200)),-1,cv2.LINE_AA)
 # Distributed broken serpent rings. Every arc is also normal etchwork; only
 # M/R/Cc connects it into an ouroboros under changing light.
 for n in range(max(32,int(hh*ww/32000))):
  cx,cy=rng.uniform(28,ww-28),rng.uniform(28,hh-28);rx,ry=rng.uniform(10,16),rng.uniform(9,14);ang=rng.uniform(-.6,.6);R=np.array([[np.cos(ang),-np.sin(ang)],[np.sin(ang),np.cos(ang)]],np.float32)
  for arm,(a,b) in enumerate(((.24,2.65),(3.05,5.74))):
   t=np.linspace(a,b,20);p=np.column_stack((rx*np.cos(t),ry*np.sin(t)))@R.T+[cx,cy];p=p.astype(np.int32);cv2.polylines(etch,[p],False,int(rng.integers(76,160)),1,cv2.LINE_AA);cv2.polylines(sec,[p],False,int(105+(n+arm)%8*18),int(rng.integers(1,3)),cv2.LINE_AA);tmp=np.zeros_like(st);cv2.polylines(tmp,[p],False,int((n*3+arm*5+seed)%8+1),int(rng.integers(1,3)),cv2.LINE_AA);st=np.where(tmp>0,tmp,st)
  head=(np.array([[rx*.86,-ry*.10],[rx*1.12,-ry*.22],[rx*1.22,ry*.06],[rx*.92,ry*.22]])@R.T+[cx,cy]).astype(np.int32);cv2.polylines(etch,[head],True,int(rng.integers(80,165)),1,cv2.LINE_AA);cv2.polylines(sec,[head],True,255,2,cv2.LINE_AA);cv2.circle(sec,tuple(head[1]),2,255,-1,cv2.LINE_AA)
 # P2: lift the ordinary black-plum shell lacquer after P1 picker review;
 # serpent geometry remains solely in the spec substitutions below.
 # P4: cool shell interference exists only along prior pearl pinwork.
 e=etch.astype(np.float32)/255;s=shell.astype(np.float32)/255;p=pearl.astype(np.float32)/255;rel=cv2.GaussianBlur(np.maximum(e,s*.8),(0,0),2);z=cv2.GaussianBlur(rng.standard_normal((hh,ww)).astype(np.float32),(0,0),5);z=(z-z.min())/(np.ptp(z)+1e-6);coal=np.array((.070,.022,.062),np.float32);plum=np.array((.355,.075,.275),np.float32);rose=np.array((.710,.180,.525),np.float32);frost=np.array((.850,.640,.885),np.float32);shellcool=np.array((.350,.720,.760),np.float32);paint=coal*(.57+.15*z[...,None])+plum*(.38+.21*z[...,None]);paint=paint*(1-(rel*.41)[...,None])+plum*(rel*.41)[...,None];paint=paint*(1-(e*.58)[...,None])+rose*(e*.58)[...,None];paint=paint*(1-(s*.51)[...,None])+frost*(s*.51)[...,None];paint=paint*(1-(p*.46)[...,None])+frost*(p*.46)[...,None];paint=paint*(1-(p*.24)[...,None])+shellcool*(p*.24)[...,None]
 mp=.5+.5*np.sin(x/7.1+np.sin(y/8.8));rp=.5+.5*np.cos((x-y)/9.4);cp=.5+.5*np.sin((x*.48+y*.79)/10.7);m=50+z*24+mp*60+rel*45+e*70+s*61+p*84;r=211-z*18-rp*54-rel*42-e*62-s*57-p*77;cc=42+z*20+cp*66+rel*53+e*77+s*68+p*91;q=np.mod(np.maximum(st,1)-1,8);sm=np.array([250,155,216,91,238,173,122,200]);sr=np.array([14,68,35,129,25,81,108,47]);sc=np.array([249,142,203,92,234,171,116,190]);hit=sec>0;m=np.where(hit,sm[q],m);r=np.where(hit,sr[q],r);cc=np.where(hit,sc[q],cc)
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
def paint_ouroboros_i2(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);p=np.asarray(paint,np.float32)[...,:3];p=p/255 if p.max(initial=0)>1.5 else p;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*float(pm))[...,None];return np.clip(p*(1-m)+a*m,0,1).astype(np.float32)
def spec_ouroboros_i2(shape,seed,sm,bm,br):del sm,bm,br;return _a(shape,seed)[1]
