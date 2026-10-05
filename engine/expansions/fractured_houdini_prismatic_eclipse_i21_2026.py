"""Private Houdini I21 — prismatic veil / hidden eclipse-state field.

Unlike the rejected dark candidates, the ordinary surface is a fine 8–20px
dichroic prism material that is useful at picker scale.  Its hidden event is
not a printed symbol: discontinuous eclipse crescents arise only from local
changes in adjacent M/Rough/Cc cards across the same prism field.
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
 h,w=map(int,shape);sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));yy,xx=np.mgrid[:hh,:ww].astype(np.float32);x,y=xx/sc,yy/sc;q=seed*.083
 # 8–20px asymmetric prisms: two warped coordinate bases, cell-local facet
 # angles, fine ribs, mica sparks and offset film—an attractive carrier before
 # its secret exists.  This intentionally does not borrow Hologram Metal code.
 # P4: P1–P3 spread bright hues too evenly, reading as a random rainbow
 # lattice.  Keep every prismatic state but make the normal surface graphite/
 # indigo with rare cyan, violet and muted-gold flashes.
 u=.81*x+.58*y+3.7*np.sin(y*.046+q);v=-.58*x+.81*y+3.5*np.sin(x*.042-q);pitch=13.2;ci,cj=np.floor(u/pitch),np.floor(v/pitch);fu=np.mod(u/pitch,1)-.5;fv=np.mod(v/pitch,1)-.5;ang=np.arctan2(fv,fu);rad=np.sqrt(fu*fu+fv*fv);code=np.mod(13*ci.astype(np.int32)+29*cj.astype(np.int32)+5*ci.astype(np.int32)*cj.astype(np.int32),8);facet=np.clip(1-rad/.72,0,1);rib=np.exp(-((np.sin(ang*3.0+code*.77+rad*13))/ .22)**2)*facet;lip=np.exp(-((rad-.43)/.055)**2);mica=(np.sin(u*.88-v*.23)*np.sin(v*.69+u*.31)>.90).astype(np.float32);grade=.5+.5*np.sin(.027*u-.033*v+.6*np.sin(.013*v));palette=np.array(((.009,.014,.020),(.014,.055,.070),(.020,.115,.135),(.065,.023,.090),(.150,.052,.165),(.280,.115,.035),(.040,.220,.240),(.028,.025,.090)),np.float32);base=palette[code];art=base*(.43+.44*facet[...,None])+.18*np.dstack((rib*.25,rib*.76,rib));art+=np.array((.08,.07,.11),np.float32)*(mica[...,None]*.32);art*= (.73+.27*grade[...,None]);art=np.clip(art,0,1)
 # Eight adjacent physical cards per prism, plus independent rib/lip/mica
 # responses.  No channel is a recolored clone of the others.
 M=58+np.take(np.array((8,38,71,112,157,204,235,91),np.float32),code)+31*facet+28*rib+25*mica;R=156-np.take(np.array((12,38,77,105,138,165,191,58),np.float32),code)-37*facet-24*rib-28*mica;C=170-np.take(np.array((15,62,108,38,143,176,83,128),np.float32),code)-46*facet-31*np.roll(rib,3,axis=0)-33*mica;M=np.where(lip>.69,np.maximum(M,228),M);R=np.where(lip>.69,np.minimum(R,21),R);C=np.where(lip>.69,np.minimum(C,24),C)
 # Local eclipse cells repeat across all panels.  Their crescent is composed
 # from an outer satin corona, a displaced dark occluder, a broken chrome rim,
 # and small 8px diffraction moons—not paint pixels.
 cell=172.;gi,gj=np.floor(x/cell),np.floor(y/cell);best=np.full((hh,ww),9e7,np.float32);lx=np.zeros((hh,ww),np.float32);ly=np.zeros((hh,ww),np.float32);sel=np.zeros((hh,ww),np.float32)
 for oy in(-1,0,1):
  for ox in(-1,0,1):
   a,b=gi+ox,gj+oy;cx=a*cell+(.18+.64*_h(a,b,seed+17))*cell;cy=b*cell+(.17+.66*_h(a,b,seed+31))*cell;dx,dy=x-cx,y-cy;d=dx*dx+dy*dy;t=d<best;best=np.where(t,d,best);lx=np.where(t,dx,lx);ly=np.where(t,dy,ly);sel=np.where(t,_h(a,b,seed+47),sel)
 # P2: perfect rings read as printed icons.  Gate every hidden state through
 # the carrier's pre-existing prism cards/ribs, producing discontinuous
 # material shards that only assemble into an eclipse at favorable light.
 X,Y=lx/64.,ly/64.;active=(sel>.65).astype(np.float32);r=np.sqrt(X*X+Y*Y);outer=np.exp(-((r-.48)/.11)**2);occ=np.exp(-(((X-.18)/.45)**2+((Y+.02)/.45)**2));cres=np.clip(outer*(1-occ*1.25),0,1);rim=np.exp(-((r-.48)/.040)**2)*np.clip(1-occ*1.10,0,1);moon=np.exp(-(((X+.60)/.075)**2+((Y-.06)/.075)**2))+np.exp(-(((X-.51)/.062)**2+((Y+.31)/.062)**2));gate=((np.mod(code+2,3)!=0).astype(np.float32))*(.34+.66*np.clip(facet+.48*rib,0,1));cres*=active*gate;rim*=active*gate;moon*=active*gate
 # P3: P2's prism gating hid the event completely in grazing proof.  Raise
 # only the occluder/rim card contrast—not a colored circular outline.
 # P5: settle between P2's invisible result and P3's blotches.  This keeps
 # the shard gate and uses a balanced local card delta for a conditional read.
 M=np.clip(M+43*cres+86*rim-72*occ*active+91*moon,0,255);R=np.clip(R-30*cres-74*rim+88*occ*active-79*moon,15,255);C=np.clip(C+37*np.roll(cres,5,axis=1)+110*np.roll(rim,-4,axis=0)-67*occ*active+114*np.roll(moon,4,axis=1),16,255)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);art,M,R,C=up(art),up(M),up(R),up(C)
 out=(art.astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_prismatic_eclipse_i21(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_prismatic_eclipse_i21(shape,seed,sm,bm,br):del sm,bm,br;return _arr(shape,seed)[1]
