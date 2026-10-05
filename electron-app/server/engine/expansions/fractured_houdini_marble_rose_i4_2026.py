"""H10-I4 Marble Rose — clouded rose alabaster, staged P1; no RGB roses."""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _a(shape,seed):
 k=(*map(int,shape),seed)
 with _L:
  if k in _C:_C.move_to_end(k);return _C[k]
 h,w=map(int,shape);f=min(1.,1024/max(h,w));hh,ww=max(160,round(h*f)),max(160,round(w*f));rng=np.random.default_rng(seed^0xA104);y,x=np.mgrid[:hh,:ww].astype(np.float32)
 # Continuous pigment clouds give card-scale depth; fine contour/pearl bands give the car tooth.
 lo=cv2.resize(rng.random((max(6,hh//105),max(6,ww//105))).astype(np.float32),(ww,hh),interpolation=cv2.INTER_CUBIC);mi=cv2.resize(rng.random((max(14,hh//32),max(14,ww//32))).astype(np.float32),(ww,hh),interpolation=cv2.INTER_CUBIC);hi=cv2.resize(rng.random((max(36,hh//10),max(36,ww//10))).astype(np.float32),(ww,hh),interpolation=cv2.INTER_CUBIC);bed=.58*lo+.30*mi+.12*hi;bed=(bed-bed.min())/(np.ptp(bed)+1e-6);cont=np.exp(-(np.sin((bed*7.4+x*.004-y*.003)*np.pi)/.14)**2);pearl=np.clip((cv2.GaussianBlur(hi,(0,0),1.3)-.62)*3.0,0,1)
 base=np.array((.115,.022,.052),np.float32);wine=np.array((.48,.078,.165),np.float32);rose=np.array((.77,.265,.365),np.float32);cream=np.array((.88,.57,.64),np.float32);paint=base*(1-bed[...,None]) + wine*bed[...,None];paint=paint*(1-(cont*.26)[...,None])+rose*(cont*.26)[...,None];paint=paint*(1-(pearl*.34)[...,None])+cream*(pearl*.34)[...,None]
 sec=np.zeros((hh,ww),np.uint8);st=np.zeros_like(sec)
 # Repeated ornate roses: 8–32px petal strokes, spiral cores and connecting sepals, M/R/Cc only.
 for n in range(max(29,int(hh*ww/35500))):
  cx,cy=rng.uniform(48,ww-48),rng.uniform(48,hh-48);u=rng.uniform(20,26);rot=rng.uniform(0,6.28)
  for j in range(12):
   a=rot+j*np.pi/6;px,py=int(cx+np.cos(a)*u*.48),int(cy+np.sin(a)*u*.48);tmp=np.zeros_like(sec);cv2.ellipse(tmp,(px,py),(max(2,int(u*.31)),max(1,int(u*.17))),a*57.2958,30,310,1,1,cv2.LINE_AA);sec=np.where(tmp>0,1,sec);st=np.where(tmp>0,((n*5+j*3+seed)%8)+1,st)
  th=np.linspace(.25,8.0,48);sp=np.column_stack((cx+(u*.05*th)*np.cos(th+rot),cy+(u*.05*th)*np.sin(th+rot))).astype(np.int32);tmp=np.zeros_like(sec);cv2.polylines(tmp,[sp],False,1,1,cv2.LINE_AA);sec=np.where(tmp>0,1,sec);st=np.where(tmp>0,((n*7+seed)%8)+1,st)
  for side in (-1,1):
   q=np.array([[cx+side*u*.12,cy+u*.34],[cx+side*u*.64,cy+u*.77],[cx+side*u*.30,cy+u*1.36],[cx+side*u*.79,cy+u*1.76]],np.int32);tmp=np.zeros_like(sec);cv2.polylines(tmp,[q],False,1,1,cv2.LINE_AA);sec=np.where(tmp>0,1,sec);st=np.where(tmp>0,((n*11+side+seed)%8)+1,st)
 halo=cv2.GaussianBlur((sec>0).astype(np.float32),(0,0),2);mp=.5+.5*np.sin(x/8.4+bed*4);rp=.5+.5*np.cos((x-y)/11.2+bed*3);cp=.5+.5*np.sin((x*.57+y*.64)/12.4+bed*5);m=48+bed*68+cont*52+pearl*71+mp*29+halo*14;r=214-bed*59-cont*46-pearl*63-rp*30-halo*13;cc=38+bed*75+cont*59+pearl*86+cp*34+halo*17;q=np.mod(np.maximum(st,1)-1,8);sm=np.array([249,153,218,89,239,171,118,203]);sr=np.array([12,72,31,134,20,86,108,46]);sc=np.array([250,146,205,87,237,164,113,194]);hit=sec>0;m=np.where(hit,sm[q],m);r=np.where(hit,sr[q],r);cc=np.where(hit,sc[q],cc)
 if(hh,ww)!=(h,w):
  up=lambda v:cv2.resize(v.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255))).astype(np.uint8))
 with _L:_C[k]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i4(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);p=np.asarray(paint,np.float32)[...,:3];p=p/255 if p.max(initial=0)>1.5 else p;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*min(1.,max(0.,float(pm))))[...,None];return np.clip(p*(1-m)+a*m,0,1).astype(np.float32)
def spec_marble_rose_i4(shape,seed,sm,bm,br):del sm,bm,br;return _a(shape,seed)[1]
