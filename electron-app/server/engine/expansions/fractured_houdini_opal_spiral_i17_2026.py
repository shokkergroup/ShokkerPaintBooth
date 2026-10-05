"""Private Houdini replacement I17 — dark-opal micro lattice / hidden galaxy spirals.

H10 Marble Rose's procedural flower grammar was rejected.  This is a complete
replacement card, not a recolor: a dark-opal, Hologram-informed micro-lattice
uses coherent 8–16px facets and adjacent material cards.  Dozens of 70–100px
galaxy spirals are encoded only by how those cells change M/Rough/Cc; no spiral
exists in the paint image.  This directly tests the owner's galaxy-spiral
Houdini brief with a mechanism that has already proven compelling in Hologram
Metal, while using distinct geometry and state choreography.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock();TAU=np.float32(6.283185307179586)
def _h(a,b,s):return np.mod(np.sin(a*12.9898+b*78.233+s*37.719)*43758.5453,1.).astype(np.float32)
def _arr(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));yy,xx=np.mgrid[:hh,:ww].astype(np.float32);x,y=xx/sc,yy/sc;q=seed*.109
 # 8–16px native non-square facet lattice; two orientations form an opal
 # prismatic surface without borrowing Hologram Metal's exact grid/math.
 u=.79*x+.61*y+5.7*np.sin(y*.049+q)+1.7*np.sin(y*.141-q);v=-.61*x+.79*y+5.1*np.sin(x*.046-q)+1.6*np.sin(x*.133+q);pitch=10.4;fu=np.mod(u/pitch,1.);fv=np.mod(v/pitch,1.);diag=np.mod((u-v)/(pitch*.72),1.);edge=np.maximum.reduce([np.exp(-((fu-.5)/.105)**2),np.exp(-((fv-.5)/.105)**2),.48*np.exp(-((diag-.5)/.09)**2)]);facet=np.clip(.48+.52*np.sin((u+v)*.092+np.sin(v*.034))*np.sin((u-v)*.083-np.sin(u*.031)),0,1);mica=(np.sin(u*.73+v*.21)*np.sin(v*.66-u*.19)>.86).astype(np.float32)
 # RGB carrier deliberately has no galaxy mask: midnight plum/graphite opal
 # with six restrained neighbouring tones tied only to facet/mica structure.
 # P2: remove P1's 300px color bands.  The opal body varies only through
 # native-scale facet/mica neighborhoods so it cannot become macro wallpaper.
 # P10: P8/P9's discrete pigments made patchwork.  Return to continuous
 # dark-opal value, but make the underlying lattice 10.4px and doubly warped
 # so the surface flows as fine mineral fabric instead of carbon checker.
 region=np.clip(.24+.62*facet+.14*mica,0,1);tone=np.floor(region*6)/5.;art=np.empty((hh,ww,3),np.float32);art[...,0]=.070+.105*tone+.044*facet;art[...,1]=.010+.024*tone+.013*facet;art[...,2]=.045+.092*tone+.039*facet;art+=np.array((.046,.012,.053),np.float32)*(mica[...,None]*.46);art=np.clip(art,0,1)
 # Local complete material cards—dark pearl body, satin prism, wet mica and
 # narrow dark-chrome facet lips.  The screen must be attractive without any
 # active hidden feature.
 M=76+97*tone+38*facet+25*mica;R=118-53*tone-31*facet-27*mica;C=108-61*tone-38*facet-30*mica;M=np.where(edge>.62,np.maximum(M,224),M);R=np.where(edge>.62,np.minimum(R,22),R);C=np.where(edge>.62,np.minimum(C,24),C)
 # Jittered 96–145px galaxy centres.  Each hidden galaxy contains three
 # narrow 8–24px spiral-arm state bands, a satin core, and tiny companion
 # moons—all state reassignment, never paint/decal art.
 cell=126.;gi,gj=np.floor(x/cell),np.floor(y/cell);best=np.full((hh,ww),9e7,np.float32);ang=np.zeros((hh,ww),np.float32);sel=np.zeros((hh,ww),np.float32)
 for oy in(-1,0,1):
  for ox in(-1,0,1):
   a,b=gi+ox,gj+oy;cx=a*cell+(.14+.72*_h(a,b,seed+7))*cell+9*np.sin(a*.47+b*.81);cy=b*cell+(.16+.69*_h(a,b,seed+11))*cell+8*np.sin(b*.39-a*.67);dx,dy=x-cx,y-cy;d=dx*dx+dy*dy;t=d<best;best=np.where(t,d,best);ang=np.where(t,np.arctan2(dy,dx)-TAU*_h(a,b,seed+15),ang);sel=np.where(t,_h(a,b,seed+19),sel)
 r=np.sqrt(best)+1e-4;a=np.mod(ang,TAU);active=(sel>.60).astype(np.float32)
 # P5: a genuine two-arm logarithmic spiral—not the P4 C-shaped annuli.
 # At each local centre the arms travel through 12–58px radius, but their
 # actual material marks stay 6–18px wide and are interrupted by the facet
 # lattice.  The result should assemble only in reflective light.
 spiral=np.mod(a-.105*r,TAU);d1=np.minimum(spiral,TAU-spiral);d2=np.minimum(np.mod(spiral+np.pi,TAU),TAU-np.mod(spiral+np.pi,TAU));rad=np.exp(-((r-34)/25)**2);arm=np.exp(-(d1/.145)**2)*rad;arm2=np.exp(-(d2/.155)**2)*rad;arm3=np.exp(-((np.minimum(np.mod(spiral+TAU*.25,TAU),TAU-np.mod(spiral+TAU*.25,TAU)))/.11)**2)*np.exp(-((r-44)/15)**2);core=np.exp(-(r/7.5)**2);moon=np.exp(-((r-55)/2.8)**2)*np.clip(.38+.70*np.cos(6*a+.7),0,1);arm*=active;arm2*=active;arm3*=active;core*=active;moon*=active
 # Adjacent physical states: arms = dark chrome flare, core = wet pearl,
 # one arm = coat-broken Fractured interruption, companion moons = matte
 # satellite.  C is deliberately offset from the other two channel anatomy.
 # P4: P3 vanished entirely.  Increase only the selected 8–24px arm/core
 # cells, using separated physical cards rather than a colored outline or
 # broad field: chrome flare / satin interruption / coat-broken spark.
 M=np.clip(M+78*arm+37*arm2+112*arm3+67*core-34*moon,0,255);R=np.clip(R-51*arm+22*arm2-61*arm3-47*core+61*moon,15,255);C=np.clip(C-58*np.roll(arm,5,axis=1)+53*np.roll(arm2,-4,axis=0)+132*np.roll(arm3,7,axis=0)+54*core+69*moon,16,255)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);art,M,R,C=up(art),up(M),up(R),up(C)
 out=(art.astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_opal_spiral_i17(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_opal_spiral_i17(shape,seed,sm,bm,br):del sm,bm,br;return _arr(shape,seed)[1]
