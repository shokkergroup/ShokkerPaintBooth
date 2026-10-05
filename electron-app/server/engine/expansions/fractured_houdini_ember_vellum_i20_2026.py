"""Private Houdini I20 — ember vellum / hidden material flame field.

I17–I19 establish that isolated glyphs collapse to icons.  I20 is a complete
field relation: every 130–180px local cell carries a distinct five-tongue
flame anatomy, but only its metallic, roughness and offset-coat states change.
The paint is an innocent smoked-black ember vellum with fine 8–28px marks.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _h(a,b,s):return np.mod(np.sin(a*12.9898+b*78.233+s*37.719)*43758.5453,1.).astype(np.float32)
def _arr(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));yy,xx=np.mgrid[:hh,:ww].astype(np.float32);x,y=xx/sc,yy/sc;q=seed*.067
 # Innocent Vellum: five fine families—smoked enamel pools, molten hairlines,
 # dark-fiber curls, mica islands and polished interruptions.  No flame mask.
 # P4: P1–P3 painted as dark woven cloth.  This keeps the same fine carrier
 # marks but narrows their visible tonal contrast into a smoother black enamel.
 u=.79*x+.61*y+3.8*np.sin(y*.051+q);v=-.61*x+.79*y+3.5*np.sin(x*.046-q);pool=.5+.5*np.sin(u*.24+.7*np.sin(v*.07))*np.sin(v*.21-.6*np.sin(u*.058));hair=np.exp(-((np.sin(u*.34+v*.19))/ .095)**2);curl=.5+.5*np.sin((u-v)*.19+np.sin((u+v)*.068));mica=(np.sin(u*.84-v*.26)*np.sin(v*.72+u*.31)>.885).astype(np.float32);cut=np.exp(-((np.sin(u*.54-v*.16))/ .075)**2);tone=np.floor(np.clip(.34+.18*pool+.14*curl+.15*mica-.035*cut,0,1)*7)/6.;art=np.empty((hh,ww,3),np.float32);art[...,0]=.042+.049*tone+.011*curl;art[...,1]=.011+.015*tone+.007*pool;art[...,2]=.023+.031*tone+.014*curl;art+=np.array((.026,.004,.013),np.float32)*(mica[...,None]*.34);art=np.clip(art,0,1)
 # P3: keep I20 P2's filled flame relationship, but give the base/envelope
 # a wider roughness state ladder so it survives physical-channel inspection.
 # P5: P4's calmer paint carrier caused only the physical roughness ladder
 # to narrow.  Widen the seven base R cards, leaving RGB and flame masks intact.
 M=81+95*tone+24*mica+15*curl;R=161-108*tone-34*mica-24*curl;C=121-69*tone-33*mica-24*curl;M=np.where(cut>.89,np.maximum(M,223),M);R=np.where(cut>.89,np.minimum(R,20),R);C=np.where(cut>.89,np.minimum(C,23),C)
 # Full-canvas jittered cells.  Each local flame is a layered field, not an
 # outline: broad satin warmth, narrow chrome inner tongue, coat-broken edge,
 # side licks and tiny local ember wells, all made from 8–28px components.
 cell=146.;gi,gj=np.floor(x/cell),np.floor(y/cell);best=np.full((hh,ww),9e7,np.float32);lx=np.zeros((hh,ww),np.float32);ly=np.zeros((hh,ww),np.float32);sel=np.zeros((hh,ww),np.float32)
 for oy in(-1,0,1):
  for ox in(-1,0,1):
   a,b=gi+ox,gj+oy;cx=a*cell+(.14+.72*_h(a,b,seed+13))*cell;cy=b*cell+(.13+.70*_h(a,b,seed+29))*cell;dx,dy=x-cx,y-cy;d=dx*dx+dy*dy;t=d<best;best=np.where(t,d,best);lx=np.where(t,dx,lx);ly=np.where(t,dy,ly);sel=np.where(t,_h(a,b,seed+41),sel)
 X,Y=lx/47.,ly/65.;active=(sel>.46).astype(np.float32);rise=np.clip((Y+.66)/1.34,0,1);twist=.18*np.sin((Y+.25)*5.1)
 # P2: P1 read as neon line flames.  Eliminate its dotted ember baseline and
 # thin edge trace; let overlapping *filled* material cards create depth.
 outer=np.exp(-((np.abs(X-twist)/(.14+.39*rise*(1-rise)))/1.0)**2)*np.exp(-((Y+.05)/.80)**2);inner=np.exp(-((np.abs(X+.06*np.sin(Y*6))/(.080+.22*rise*(1-rise)))/1.0)**2)*np.exp(-((Y+.13)/.64)**2);left=np.exp(-(((X+.28+.11*np.sin(Y*7))/(.085+.21*rise*(1-rise)))**2))*np.exp(-((Y-.03)/.53)**2);right=np.exp(-(((X-.29-.10*np.sin(Y*6))/(.080+.20*rise*(1-rise)))**2))*np.exp(-((Y+.01)/.51)**2);edge=.42*np.exp(-((np.abs(X-twist)-(.14+.39*rise*(1-rise)))/.065)**2)*np.exp(-((Y+.05)/.75)**2);ember=np.exp(-(((X+.11*np.sin(Y*4))/.19)**2+((Y-.44)/.13)**2))*(np.sin(X*17-Y*11)>.74).astype(np.float32)
 outer*=active;inner*=active;left*=active;right*=active;edge*=active;ember*=active
 M=np.clip(M+34*outer+77*inner+51*left+44*right+32*edge+82*ember,0,255);R=np.clip(R-20*outer-62*inner+16*left+9*right-19*edge-68*ember,15,255);C=np.clip(C+24*np.roll(outer,5,axis=1)+91*np.roll(inner,-4,axis=0)-34*left+43*np.roll(right,4,axis=1)+38*np.roll(edge,3,axis=0)+98*np.roll(ember,5,axis=1),16,255)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);art,M,R,C=up(art),up(M),up(R),up(C)
 out=(art.astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_ember_vellum_i20(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_ember_vellum_i20(shape,seed,sm,bm,br):del sm,bm,br;return _arr(shape,seed)[1]
