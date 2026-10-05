"""H8-I2 Aurora Wolf — isolated sapphire kintsugi lacquer P1."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _a(shape,seed):
 k=(*map(int,shape),seed)
 with _L:
  if k in _C:_C.move_to_end(k);return _C[k]
 h,w=map(int,shape);f=min(1.,1024/max(h,w));hh,ww=max(128,round(h*f)),max(128,round(w*f));rng=np.random.default_rng(seed^0xA808);line=np.zeros((hh,ww),np.uint8);gold=np.zeros_like(line);pearl=np.zeros_like(line);sec=np.zeros_like(line);st=np.zeros_like(line)
 for _ in range(max(2800,int(hh*ww/360))):
  cx,cy=rng.uniform(-18,ww+18),rng.uniform(-18,hh+18);a=rng.uniform(-1,1);L=rng.uniform(3,12);p=np.array([[-L,0],[-L*.2,rng.uniform(-4,4)],[L*.38,rng.uniform(-3,3)],[L,0]],np.float32);R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);p=(p@R.T+[cx,cy]).astype(np.int32);cv2.polylines(line,[p],False,int(rng.integers(75,190)),int(rng.integers(1,3)),cv2.LINE_AA)
  if rng.random()<.43:cv2.circle(gold,tuple(p[1]),int(rng.integers(1,3)),int(rng.integers(90,210)),-1,cv2.LINE_AA)
  if rng.random()<.28:cv2.circle(pearl,tuple(p[2]),int(rng.integers(1,3)),int(rng.integers(120,255)),-1,cv2.LINE_AA)
 # P3: connected fine kintsugi sweepwork adds authored flow without a grid.
 for _ in range(max(165,int(hh*ww/8300))):
  cx,cy=rng.uniform(-28,ww+28),rng.uniform(-24,hh+24);a=rng.uniform(-.72,.72);span=rng.uniform(17,44);amp=rng.uniform(4,10);t=np.linspace(-1,1,13);p=np.column_stack((t*span,amp*np.sin(t*np.pi*.88)+t*t*amp*.25));R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);p=(p@R.T+[cx,cy]).astype(np.int32)
  for u,v in zip(p[::2][:-1],p[::2][1:]):cv2.line(line,tuple(u),tuple(v),int(rng.integers(85,190)),2,cv2.LINE_AA)
  for q in p[3:-3:4]:cv2.circle(gold,tuple(q),int(rng.integers(1,3)),int(rng.integers(90,205)),-1,cv2.LINE_AA)
 # many small wolf masks, each built from ordinary fine fractures in neutral.
 for n in range(max(30,int(hh*ww/33000))):
  cx,cy=rng.uniform(27,ww-27),rng.uniform(28,hh-28);rx,ry=rng.uniform(10,16),rng.uniform(12,18);a=rng.uniform(-.5,.5);R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);parts=[np.array([[0,-ry*.76],[-rx*.42,-ry*.23],[-rx*.76,-ry*.66],[-rx*.58,ry*.18],[0,ry*.72],[rx*.58,ry*.18],[rx*.76,-ry*.66],[rx*.42,-ry*.23],[0,-ry*.76]],np.float32),np.array([[-rx*.38,-ry*.02],[0,ry*.12],[rx*.38,-ry*.02]],np.float32)]
  for j,p in enumerate(parts):
   p=(p@R.T+[cx,cy]).astype(np.int32);cv2.polylines(line,[p],j==0,int(rng.integers(74,165)),1,cv2.LINE_AA);cv2.polylines(sec,[p],j==0,int(112+(n+j)%8*17),int(rng.integers(1,3)),cv2.LINE_AA);tmp=np.zeros_like(st);cv2.polylines(tmp,[p],j==0,int((n*3+j*5+seed)%8+1),1,cv2.LINE_AA);st=np.where(tmp>0,tmp,st)
 # P2: picker-scale lift of normal sapphire/ice kintsugi only.
 # P4: existing pearl glints get a small cool interference split.
 l=line.astype(np.float32)/255;g=gold.astype(np.float32)/255;p=pearl.astype(np.float32)/255;rel=cv2.GaussianBlur(np.maximum(l,g*.8),(0,0),2);z=cv2.GaussianBlur(rng.standard_normal((hh,ww)).astype(np.float32),(0,0),5);z=(z-z.min())/(np.ptp(z)+1e-6);ink=np.array((.035,.060,.130),np.float32);lapis=np.array((.100,.255,.540),np.float32);azure=np.array((.235,.520,.820),np.float32);aurum=np.array((.820,.535,.180),np.float32);ice=np.array((.745,.825,1.0),np.float32);cyan=np.array((.280,.780,.860),np.float32);paint=ink*(.57+.16*z[...,None])+lapis*(.36+.20*z[...,None]);paint=paint*(1-(rel*.46)[...,None])+lapis*(rel*.46)[...,None];paint=paint*(1-(l*.58)[...,None])+azure*(l*.58)[...,None];paint=paint*(1-(g*.60)[...,None])+aurum*(g*.60)[...,None];paint=paint*(1-(p*.48)[...,None])+ice*(p*.48)[...,None];paint=paint*(1-(p*.24)[...,None])+cyan*(p*.24)[...,None]
 y,x=np.mgrid[0:hh,0:ww].astype(np.float32);mp=.5+.5*np.sin(x/7.2+np.sin(y/8.4));rp=.5+.5*np.cos((x-y)/9.4);cp=.5+.5*np.sin((x*.5+y*.75)/10.6);m=49+z*24+mp*60+rel*45+l*70+g*62+p*87;r=211-z*18-rp*54-rel*42-l*61-g*57-p*80;cc=42+z*20+cp*66+rel*53+l*77+g*68+p*94;q=np.mod(np.maximum(st,1)-1,8);sm=np.array([250,155,216,91,238,173,122,200]);sr=np.array([14,68,35,129,25,81,108,47]);sc=np.array([249,142,203,92,234,171,116,190]);hit=sec>0;m=np.where(hit,sm[q],m);r=np.where(hit,sr[q],r);cc=np.where(hit,sc[q],cc)
 if (hh,ww)!=(h,w):
  up=lambda a:cv2.resize(a.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 v=(np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255))).astype(np.uint8))
 with _L:_C[k]=v;_C.popitem(last=False) if len(_C)>2 else None
 return v
def paint_aurora_wolf_i2(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);p=np.asarray(paint,np.float32)[...,:3];p=p/255 if p.max(initial=0)>1.5 else p;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*min(1.,max(0.,float(pm))))[...,None];return np.clip(p*(1-m)+a*m,0,1).astype(np.float32)
def spec_aurora_wolf_i2(shape,seed,sm,bm,br):del sm,bm,br;return _a(shape,seed)[1]
