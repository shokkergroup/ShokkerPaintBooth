"""H4-I2 Cinder Cross — isolated charcoal/celadon mineral lacquer."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _make(shape,seed):
 h,w=map(int,shape);f=min(1.,1024/max(h,w));hh,ww=max(128,round(h*f)),max(128,round(w*f));rng=np.random.default_rng(seed^0xC412); y,x=np.mgrid[0:hh,0:ww].astype(np.float32); vein=np.zeros((hh,ww),np.uint8);chip=np.zeros_like(vein);glint=np.zeros_like(vein);secret=np.zeros_like(vein);state=np.zeros_like(vein)
 # Neutral carrier: fine mineral fissures, broken celadon inlays, ash chips, glaze pinwork.
 for _ in range(max(1900,int(hh*ww/540))):
  cx,cy=rng.uniform(-20,ww+20),rng.uniform(-20,hh+20);a=rng.uniform(-.9,.9);L=rng.uniform(3,12);bend=rng.uniform(-4,4);p=np.array([[-L,0],[-L*.25,bend],[L*.3,-bend*.5],[L,0]],np.float32);R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);p=(p@R.T+[cx,cy]).astype(np.int32);cv2.polylines(vein,[p],False,int(rng.integers(70,190)),int(rng.integers(1,3)),cv2.LINE_AA)
  if rng.random()<.5:cv2.circle(chip,tuple(p[1]),int(rng.integers(1,3)),int(rng.integers(80,210)),-1,cv2.LINE_AA)
  if rng.random()<.27:cv2.circle(glint,tuple(p[2]),int(rng.integers(1,3)),int(rng.integers(120,255)),-1,cv2.LINE_AA)
 # P3: authored small Byzantine arches and inlay returns replace much of the
 # anonymous P2 fissure density.  These are only short 8–28px-native marks.
 for _ in range(max(175,int(hh*ww/8000))):
  cx,cy=rng.uniform(-25,ww+25),rng.uniform(-22,hh+22);rx,ry=rng.uniform(10,24),rng.uniform(3,9);a=rng.uniform(-.65,.65);t=np.linspace(.16,2.98,11);p=np.column_stack((rx*np.cos(t),ry*np.sin(t)));R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);p=(p@R.T+[cx,cy]).astype(np.int32)
  for u,vv in zip(p[::2][:-1],p[::2][1:]):cv2.line(vein,tuple(u),tuple(vv),int(rng.integers(90,190)),2,cv2.LINE_AA)
  for q in p[2:-2:3]:cv2.circle(chip,tuple(q),int(rng.integers(1,3)),int(rng.integers(90,205)),-1,cv2.LINE_AA)
 # 34 non-rowed crosses: ordinary micro-fissures in neutral, material-only discovery.
 for n in range(max(34,int(hh*ww/31000))):
  cx,cy=rng.uniform(26,ww-26),rng.uniform(26,hh-26);u=rng.uniform(8,14);ang=rng.uniform(-.55,.55);R=np.array([[np.cos(ang),-np.sin(ang)],[np.sin(ang),np.cos(ang)]],np.float32)
  paths=[np.array([[0,-u],[0,u*.82]],np.float32),np.array([[-u*.62,-u*.14],[u*.62,-u*.14]],np.float32),np.array([[-u*.3,u*.38],[u*.3,u*.38]],np.float32)]
  for k,p in enumerate(paths):
   q=(p@R.T+[cx,cy]).astype(np.int32);cv2.polylines(vein,[q],False,int(rng.integers(76,166)),1,cv2.LINE_AA);cv2.polylines(secret,[q],False,int(110+(n+k)%8*17),int(rng.integers(1,3)),cv2.LINE_AA);tmp=np.zeros_like(state);cv2.polylines(tmp,[q],False,int((n*3+k*5+seed)%8+1),int(rng.integers(1,3)),cv2.LINE_AA);state=np.where(tmp>0,tmp,state)
  for dx,dy in ((-.48,-.14),(.48,-.14),(0,.38)):
   q=(np.array([dx*u,dy*u])@R.T+[cx,cy]).astype(int);cv2.circle(secret,tuple(q),2,255,-1,cv2.LINE_AA);cv2.circle(chip,tuple(q),1,int(rng.integers(88,170)),-1,cv2.LINE_AA)
 v=vein.astype(np.float32)/255;c=chip.astype(np.float32)/255;g=glint.astype(np.float32)/255;rel=cv2.GaussianBlur(np.maximum(v,c*.8),(0,0),2);z=cv2.GaussianBlur(rng.standard_normal((hh,ww)).astype(np.float32),(0,0),5);z=(z-z.min())/(np.ptp(z)+1e-6)
 # P2: P1 was a technically sound but too-dark green texture at picker
 # scale.  Lift only ordinary mineral layers and their fine local relief.
 # P4: only pre-existing glint grains receive cinder-bronze, yielding a
 # forged mineral counterpoint to celadon rather than a new graphic layer.
 soot=np.array((.050,.070,.060),np.float32);cel=np.array((.080,.330,.250),np.float32);jade=np.array((.165,.520,.385),np.float32);ash=np.array((.58,.76,.67),np.float32);bronze=np.array((.68,.355,.115),np.float32);paint=soot*(.58+.16*z[...,None])+cel*(.35+.20*z[...,None]);paint=paint*(1-(rel*.43)[...,None])+cel*(rel*.43)[...,None];paint=paint*(1-(v*.57)[...,None])+jade*(v*.57)[...,None];paint=paint*(1-(c*.52)[...,None])+ash*(c*.52)[...,None];paint=paint*(1-(g*.70)[...,None])+bronze*(g*.70)[...,None]
 mp=.5+.5*np.sin(x/7.7+np.sin(y/8.3));rp=.5+.5*np.cos((x-y)/9.1);cp=.5+.5*np.sin((x*.51+y*.73)/10.3);m=52+z*25+mp*58+rel*48+v*71+c*63+g*87;r=210-z*19-rp*53-rel*44-v*62-c*59-g*78;cc=43+z*21+cp*64+rel*55+v*77+c*69+g*94;q=np.mod(np.maximum(state,1)-1,8);sm=np.array([250,155,216,91,238,173,122,200]);sr=np.array([14,68,35,129,25,81,108,47]);sc=np.array([249,142,203,92,234,171,116,190]);hit=secret>0;m=np.where(hit,sm[q],m);r=np.where(hit,sr[q],r);cc=np.where(hit,sc[q],cc)
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
def paint_cinder_cross_i2(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);p=np.asarray(paint,np.float32)[...,:3];p=p/255 if p.max(initial=0)>1.5 else p;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*float(pm))[...,None];return np.clip(p*(1-m)+a*m,0,1).astype(np.float32)
def spec_cinder_cross_i2(shape,seed,sm,bm,br):del sm,bm,br;return _a(shape,seed)[1]
