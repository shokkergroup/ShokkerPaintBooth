"""H10-I3 Marble Rose — connected wine-marble garden, staged P1.

Replaces the rejected I2 microcell field.  Neutral RGB has only mineral
tendrils/inlay; rose anatomy is written solely into M/Rough/Cc.
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
 h,w=map(int,shape);f=min(1.,1024/max(h,w));hh,ww=max(160,round(h*f)),max(160,round(w*f));rng=np.random.default_rng(seed^0xA103);y,x=np.mgrid[:hh,:ww].astype(np.float32)
 z=cv2.GaussianBlur(rng.standard_normal((hh,ww)).astype(np.float32),(0,0),13);z=(z-z.min())/(np.ptp(z)+1e-6);tend=np.zeros((hh,ww),np.uint8);inlay=np.zeros_like(tend);spark=np.zeros_like(tend);sec=np.zeros_like(tend);st=np.zeros_like(tend)
 # Fine linked mineral curls: ordinary botanical marble anatomy, never roses in RGB.
 for n in range(0):
  cx,cy=rng.uniform(-18,ww+18),rng.uniform(-18,hh+18);u=rng.uniform(7,14);a=rng.uniform(0,6.28);R=np.array([[np.cos(a),-np.sin(a)],[np.sin(a),np.cos(a)]],np.float32);stem=np.array([[-u*.82,-u*.22],[-u*.34,-u*.10],[u*.05,u*.06],[u*.48,u*.22],[u*.84,u*.54]],np.float32)@R.T+np.array([cx,cy]);cv2.polylines(tend,[stem.astype(np.int32)],False,int(rng.integers(96,176)),2,cv2.LINE_AA)
  for side in (-1,1):
   q=np.array([[-u*.30,0],[u*.05,side*u*.38],[u*.39,side*u*.21]],np.float32)@R.T+np.array([cx,cy]);cv2.polylines(inlay,[q.astype(np.int32)],False,int(rng.integers(120,214)),1,cv2.LINE_AA)
  if n%4==0:cv2.circle(spark,tuple(stem[2].astype(np.int32)),1,225,-1,cv2.LINE_AA)
 # P4 reset: continuous warped wine-marble veins, not detached botanical marks.
 nw=cv2.resize(rng.random((max(8,hh//24),max(8,ww//24))).astype(np.float32),(ww,hh),interpolation=cv2.INTER_CUBIC);nw=(nw-nw.min())/(np.ptp(nw)+1e-6);u=x/8.7+2.9*(nw-.5)+.72*np.sin(y/19.0);v=(x*.43-y*.71)/10.8+2.2*(nw-.5)+.51*np.sin(x/23.0);q=(x*.28+y*.84)/12.3+2.5*(nw-.5)+.43*np.sin((x-y)/27.);a1=np.exp(-(np.sin(u)/.105)**2);a2=np.exp(-(np.sin(v)/.082)**2);a3=np.exp(-(np.sin(q)/.075)**2);tend=np.uint8(np.clip(np.maximum.reduce((a1*.43,a2*.56,a3*.38)),0,1)*255);inlay=np.uint8(np.clip(a1*.35+a2*.57+a3*.44,0,1)*255);spark=np.zeros_like(tend)
 # 31+ recurring flower reliquaries are connected to nearby ordinary curls only in material state.
 for n in range(max(31,int(hh*ww/33800))):
  cx,cy=rng.uniform(38,ww-38),rng.uniform(38,hh-38);u=rng.uniform(17,23);rot=rng.uniform(0,6.28)
  for j in range(11):
   a=rot+j*np.pi*2/11;px,py=int(cx+np.cos(a)*u*.48),int(cy+np.sin(a)*u*.48);tmp=np.zeros_like(sec);cv2.ellipse(tmp,(px,py),(max(2,int(u*.30)),max(1,int(u*.16))),a*57.2958,25,310,1,1,cv2.LINE_AA);sec=np.where(tmp>0,1,sec);st=np.where(tmp>0,((n*5+j*3+seed)%8)+1,st)
  th=np.linspace(.35,8.4,50);sp=np.column_stack((cx+(u*.045*th)*np.cos(th+rot),cy+(u*.045*th)*np.sin(th+rot))).astype(np.int32);tmp=np.zeros_like(sec);cv2.polylines(tmp,[sp],False,1,1,cv2.LINE_AA);sec=np.where(tmp>0,1,sec);st=np.where(tmp>0,((n*7+seed)%8)+1,st)
  # curled sepal/tendril material anatomy, intentionally repeated across the canvas.
  for side in (-1,1):
   q=np.array([[cx+side*u*.16,cy+u*.35],[cx+side*u*.78,cy+u*.72],[cx+side*u*.34,cy+u*1.30],[cx+side*u*.86,cy+u*1.72]],np.int32);tmp=np.zeros_like(sec);cv2.polylines(tmp,[q],False,1,1,cv2.LINE_AA);sec=np.where(tmp>0,1,sec);st=np.where(tmp>0,((n*3+side+seed)%8)+1,st)
 base=np.array((.145,.030,.060),np.float32);wine=np.array((.43,.075,.14),np.float32);mica=np.array((.72,.31,.42),np.float32);pearl=np.array((.84,.54,.60),np.float32);a=tend.astype(np.float32)/255;i=inlay.astype(np.float32)/255;g=spark.astype(np.float32)/255;paint=base*(.64+.19*z[...,None])+wine*(.22+.14*z[...,None]);paint=paint*(1-(a*.42)[...,None])+mica*(a*.42)[...,None];paint=paint*(1-(i*.48)[...,None])+pearl*(i*.48)[...,None];paint=paint*(1-(g*.62)[...,None])+pearl*(g*.62)[...,None]
 mp=.5+.5*np.sin(x/7.8+np.sin(y/9.2));rp=.5+.5*np.cos((x-y)/10.4);cp=.5+.5*np.sin((x*.61+y*.49)/11.8);rel=cv2.GaussianBlur(np.maximum(a,i*.84),(0,0),1.35);halo=cv2.GaussianBlur((sec>0).astype(np.float32),(0,0),2.0);m=51+z*19+mp*31+rel*67+a*53+i*61+g*82+halo*15;r=207-z*16-rp*32-rel*58-a*49-i*56-g*78-halo*14;cc=43+z*19+cp*36+rel*72+a*62+i*69+g*91+halo*18;q=np.mod(np.maximum(st,1)-1,8);sm=np.array([250,151,215,87,238,171,119,202]);sr=np.array([13,73,32,132,21,86,109,47]);sc=np.array([249,145,204,89,236,165,114,193]);hit=sec>0;m=np.where(hit,sm[q],m);r=np.where(hit,sr[q],r);cc=np.where(hit,sc[q],cc)
 if(hh,ww)!=(h,w):
  up=lambda v:cv2.resize(v.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255))).astype(np.uint8))
 with _L:_C[k]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i3(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);p=np.asarray(paint,np.float32)[...,:3];p=p/255 if p.max(initial=0)>1.5 else p;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*min(1.,max(0.,float(pm))))[...,None];return np.clip(p*(1-m)+a*m,0,1).astype(np.float32)
def spec_marble_rose_i3(shape,seed,sm,bm,br):del sm,bm,br;return _a(shape,seed)[1]
