"""Private Houdini I19 — black-enamel reliquary / hidden cathedral knots.

I18 showed that a facial icon collapses to eyes-and-teeth.  I19 instead uses
recurring 130–170px Gothic/Art-Deco knotwork, built from 8–28px arch shoulders,
halo ribs, quatrefoil insets, keyline returns and broken mirror tesserae.  The
entire construction exists only as different M/Rough/Cc physical states.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock();TAU=np.float32(6.283185307179586)
def _h(a,b,s):return np.mod(np.sin(a*12.9898+b*78.233+s*37.719)*43758.5453,1.).astype(np.float32)
def _arc(x,y,cx,cy,r,w):return np.exp(-((np.sqrt((x-cx)**2+(y-cy)**2)-r)/w)**2)
def _arr(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));yy,xx=np.mgrid[:hh,:ww].astype(np.float32);x,y=xx/sc,yy/sc;q=seed*.073
 # Innocent black-enamel mineral: micro enamel pools, mica pinpoints, brushed
 # 8–24px curls and narrow polished breaks—no glyph information in RGB.
 # P4: P1–P3's normal carrier read as dark fabric.  Use a calmer black
 # enamel body with only fine mineral variation; the secret remains unchanged.
 u=.77*x+.64*y+4*np.sin(y*.047+q);v=-.64*x+.77*y+4*np.sin(x*.043-q);pool=.5+.5*np.sin(u*.21+.8*np.sin(v*.059))*np.sin(v*.24-.7*np.sin(u*.052));curl=.5+.5*np.sin((u-v)*.17+1.1*np.sin((u+v)*.061));mica=(np.sin(u*.81+v*.37)*np.sin(v*.74-u*.29)>.89).astype(np.float32);breaks=np.exp(-((np.sin(u*.36-v*.19))/ .10)**2);tone=np.floor(np.clip(.34+.17*pool+.12*curl+.16*mica,0,1)*7)/6.;art=np.empty((hh,ww,3),np.float32);art[...,0]=.040+.055*tone+.012*curl;art[...,1]=.021+.030*tone+.009*pool;art[...,2]=.055+.072*tone+.018*curl;art+=np.array((.030,.006,.038),np.float32)*(mica[...,None]*.38);art=np.clip(art,0,1)
 # P5: restore the base roughness ladder without adding a visual mark type.
 M=84+93*tone+24*mica+16*curl;R=141-76*tone-28*mica-20*curl;C=123-67*tone-33*mica-25*curl;M=np.where(breaks>.88,np.maximum(M,220),M);R=np.where(breaks>.88,np.minimum(R,22),R);C=np.where(breaks>.88,np.minimum(C,24),C)
 # Jittered reliquary centres; 25–35 motif assemblies cover the car canvas.
 cell=184.;gi,gj=np.floor(x/cell),np.floor(y/cell);best=np.full((hh,ww),9e7,np.float32);lx=np.zeros((hh,ww),np.float32);ly=np.zeros((hh,ww),np.float32);sel=np.zeros((hh,ww),np.float32)
 for oy in(-1,0,1):
  for ox in(-1,0,1):
   a,b=gi+ox,gj+oy;cx=a*cell+(.18+.63*_h(a,b,seed+11))*cell;cy=b*cell+(.17+.65*_h(a,b,seed+23))*cell;dx,dy=x-cx,y-cy;d=dx*dx+dy*dy;t=d<best;best=np.where(t,d,best);lx=np.where(t,dx,lx);ly=np.where(t,dy,ly);sel=np.where(t,_h(a,b,seed+37),sel)
 # P2: P1 reduced to a tiny four-loop mark.  Enlarge the full architectural
 # assembly, not its strokes, and add interrupted lancet ribs.  Components
 # remain 8–28px native at their brightest/largest point.
 X,Y=lx/75.,ly/84.;active=(sel>.68).astype(np.float32)
 # Architectural anatomy: a pointed crown, four offset arches, an open
 # quatrefoil, tiny inset pearls and a broken vertical key.  This is not a
 # cross silhouette: its nested state cards must assemble as ornament.
 # P3: abandon P2's circular-loop read.  Pointed ogive ribs and stepped
 # returns give the secret a cathedral-knot silhouette before its inner
 # clover/pearls fill the ornamental negative space.
 crown=np.exp(-((np.abs(X)-(.53-.73*np.abs(Y+.34)))/.060)**2)*np.exp(-((Y+.13)/.59)**2);side=np.exp(-((np.abs(X)-.43)/.058)**2)*np.exp(-((Y-.04)/.43)**2);q1=np.exp(-(((X-.18)/.13)**2+((Y-.03)/.13)**2));q2=np.exp(-(((X+.18)/.13)**2+((Y-.03)/.13)**2));q3=np.exp(-((X/.13)**2+((Y-.21)/.13)**2));q4=np.exp(-((X/.13)**2+((Y+.20)/.13)**2));quatre=np.maximum.reduce((q1,q2,q3,q4))*np.exp(-((np.sqrt(X*X+Y*Y)-.29)/.18)**2);spine=np.exp(-(X/.052)**2)*np.exp(-((Y-.08)/.48)**2);returner=np.exp(-((np.abs(Y-.48)-(.34-.20*np.abs(X)))/.064)**2)*np.clip(1-np.abs(X)/.62,0,1);lancet=np.maximum(np.exp(-((np.abs(X)-(.43-.31*np.abs(Y+.04)))/.050)**2)*np.exp(-((Y+.03)/.53)**2),np.exp(-((np.abs(Y-.05)-(.39-.24*np.abs(X)))/.050)**2)*np.exp(-((X/.54)**2)));pearls=(np.sin(np.arctan2(Y,X)*8+np.sqrt(X*X+Y*Y)*17)>.92).astype(np.float32)*np.exp(-((np.sqrt(X*X+Y*Y)-.48)/.08)**2)
 crown*=active;side*=active;quatre*=active;spine*=active;returner*=active;lancet*=active;pearls*=active
 # Six causal, offset physical states: wet pearl crown; dark inset clover;
 # chrome ribs; coat-broken inner line; satin return; tiny mirror pearls.
 M=np.clip(M+54*crown+71*side-56*quatre+83*spine+38*returner+64*lancet+93*pearls,0,255);R=np.clip(R-40*crown-62*side+83*quatre-73*spine-24*returner-48*lancet-81*pearls,15,255);C=np.clip(C+31*np.roll(crown,5,axis=1)+108*np.roll(side,-4,axis=0)-49*quatre+76*np.roll(spine,3,axis=0)+43*returner+84*np.roll(lancet,5,axis=1)+116*np.roll(pearls,4,axis=1),16,255)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);art,M,R,C=up(art),up(M),up(R),up(C)
 out=(art.astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_reliquary_knot_i19(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_reliquary_knot_i19(shape,seed,sm,bm,br):del sm,bm,br;return _arr(shape,seed)[1]
