"""H10-I2 Marble Rose — staged P1, no RGB rose art.

Owner Houdini reset: intricate repeated material-only rosettes, each built from
8–32px native petals; neutral carrier remains charcoal rose marble.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
from engine.expansions.fractured_foundry_kit_2026 import cells,tooth,n01
_C,_L=OrderedDict(),RLock()
def _a(shape,seed):
 k=(*map(int,shape),seed)
 with _L:
  if k in _C:_C.move_to_end(k);return _C[k]
 h,w=map(int,shape);f=min(1.,1024/max(h,w));hh,ww=max(128,round(h*f)),max(128,round(w*f));rng=np.random.default_rng(seed^0xA10E);y,x=np.mgrid[:hh,:ww].astype(np.float32)
 # Neutral: multiple-scale mineral seam field, never a rose silhouette.
 dx,dy,d1,bid,d2=cells(hh,8.6,seed^0x310,jit=.72);seam=np.clip((d2-d1)*.78,0,1);facet=n01(bid);z=cv2.GaussianBlur(rng.standard_normal((hh,ww)).astype(np.float32),(0,0),7);z=(z-z.min())/(np.ptp(z)+1e-6);fine=n01(tooth(hh,seed^0x511,1.0))
 base=np.array((.115,.026,.050),np.float32);ash=np.array((.335,.108,.155),np.float32);mica=np.array((.710,.365,.425),np.float32);paint=base*(.66+.16*z[...,None])+ash*(.12+.18*facet[...,None]);paint=paint*(1-(seam*.54)[...,None])+mica*(seam*.54)[...,None];paint=paint*(1-(fine*.16)[...,None])+ash*(fine*.16)[...,None]
 sec=np.zeros((hh,ww),np.uint8);st=np.zeros_like(sec)
 # Rosettes repeat over the entire carrier, with petals/inner curls/seed ring split across spec states only.
 for n in range(max(28,int(hh*ww/40000))):
  cx,cy=rng.uniform(52,ww-52),rng.uniform(52,hh-52);u=rng.uniform(22.0,28.0);rot=rng.uniform(0,6.28)
  for j in range(13):
   ang=rot+j*np.pi*2/13;px,py=int(cx+np.cos(ang)*u*.46),int(cy+np.sin(ang)*u*.46);tmp=np.zeros_like(sec);cv2.ellipse(tmp,(px,py),(max(2,int(u*.32)),max(1,int(u*.18))),ang*57.2958,34,286,1,1,cv2.LINE_AA);sec=np.where(tmp>0,1,sec);st=np.where(tmp>0,((n*5+j*3+seed)%8)+1,st)
  t=np.linspace(.3,7.1,32);spir=np.column_stack((cx+(u*.055*t)*np.cos(t+rot),cy+(u*.055*t)*np.sin(t+rot))).astype(np.int32);tmp=np.zeros_like(sec);cv2.polylines(tmp,[spir],False,1,1,cv2.LINE_AA);sec=np.where(tmp>0,1,sec);st=np.where(tmp>0,((n*7+seed)%8)+1,st)
  cv2.circle(sec,(int(cx),int(cy)),max(2,int(u*.19)),1,-1,cv2.LINE_AA);st[int(max(0,cy-u*.19)):int(min(hh,cy+u*.19+1)),int(max(0,cx-u*.19)):int(min(ww,cx+u*.19+1))]=np.maximum(st[int(max(0,cy-u*.19)):int(min(hh,cy+u*.19+1)),int(max(0,cx-u*.19)):int(min(ww,cx+u*.19+1))],(n%8)+1)
 halo=cv2.GaussianBlur((sec>0).astype(np.float32),(0,0),2.0);fq=np.minimum((facet*8).astype(np.int32),7);mb=np.array([63,89,117,146,176,204,104,134],np.float32)[fq];rb=np.array([69,94,123,153,182,211,108,140],np.float32)[fq];cb=np.array([61,87,115,144,174,201,101,132],np.float32)[fq];m=mb+z*10+seam*24+fine*16+halo*13;r=rb-z*10-seam*22-fine*14-halo*12;cc=cb+z*11+seam*26+fine*17+halo*16;q=np.mod(np.maximum(st,1)-1,8);sm=np.array([246,164,216,92,235,139,188,121]);sr=np.array([13,71,32,135,21,88,111,49]);sc=np.array([250,147,205,84,239,161,118,193]);hit=sec>0;m=np.where(hit,sm[q],m);r=np.where(hit,sr[q],r);cc=np.where(hit,sc[q],cc)
 if (hh,ww)!=(h,w):
  up=lambda v:cv2.resize(v.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.dstack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255))).astype(np.uint8))
 with _L:_C[k]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i2(paint,shape,mask,seed,pm,bb):
 del bb;a,_=_a(shape,seed);p=np.asarray(paint,np.float32)[...,:3];p=p/255 if p.max(initial=0)>1.5 else p;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*min(1.,max(0.,float(pm))))[...,None];return np.clip(p*(1-m)+a*m,0,1).astype(np.float32)
def spec_marble_rose_i2(shape,seed,sm,bm,br):del sm,bm,br;return _a(shape,seed)[1]
