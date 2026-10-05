"""Private H10 I14 — black-cherry tessera lacquer with spec-only rose state choreography.

H10 I13 proved that literal bright flower outlines read as clip art.  I14 uses
the Hologram Metal lesson without copying its grid: an irregular, locally
warped 8–16px tessera surface whose neighboring material cards differ in five
physical ways.  Roses exist only as a *change in card choreography* across
those tesserae; the paint remains an innocent black-cherry marquetry lacquer.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np

_C, _L = OrderedDict(), RLock(); TAU=np.float32(6.283185307179586)
def _h(a,b,s): return np.mod(np.sin(a*12.9898+b*78.233+s*37.719)*43758.5453,1.).astype(np.float32)

def _arr(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C: _C.move_to_end(key); return _C[key]
 h,w=map(int,shape); sc=768/max(h,w); hh,ww=max(192,round(h*sc)),max(192,round(w*sc)); yy,xx=np.mgrid[:hh,:ww].astype(np.float32); x,y=xx/sc,yy/sc; q=seed*.131
 # Fine, direction-changing tessera coordinates.  There is no 2048-wide grid:
 # each 8–16px native tile is warped locally before its state is selected.
 u=x+3.8*np.sin(y*.019+q)+1.9*np.sin(x*.041-y*.016); v=y+3.1*np.sin(x*.023-q)+1.7*np.sin(y*.037+x*.012); sz=13.2
 jj=np.floor(v/sz); ii=np.floor((u+.49*sz*np.mod(jj,2))/sz); cx=(ii+.5)*sz-.49*sz*np.mod(jj,2); cy=(jj+.5)*sz
 lx=(u-cx)/(sz*.5); ly=(v-cy)/(sz*.5); diamond=np.clip(1-(np.abs(lx)+np.abs(ly)),0,1); edge=np.exp(-((np.abs(lx)+np.abs(ly)-.90)/.075)**2); facet=np.clip(.5+.5*(lx*.73-ly*.69),0,1)
 rng=_h(ii,jj,seed); micro=(np.sin((lx+ly)*TAU*1.7+rng*TAU)>.66).astype(np.float32)*diamond
 # Innocent visible surface: restrained dark-cherry tessera lacquer, no rose
 # mask and no high RGB chroma.  Tile, bevel, mica dot and diagonal facet are
 # all 8–16px-scale material craft, not noise or oversized wallpaper.
 body=np.array((.092,.006,.040),np.float32)+np.array((.038,.007,.024),np.float32)*(rng[...,None]); body+=np.array((.023,.009,.021),np.float32)*(facet[...,None]*diamond[...,None]); body+=np.array((.045,.016,.034),np.float32)*(micro[...,None]*.38); body=np.clip(body,0,1)
 # An irregular 50–80px probability region governs where an authored rose
 # choreography occurs.  It does NOT paint a symbol; it reorders full cards in
 # neighboring tesserae.  The rosette itself is assembled from 8–32px facets.
 cell=132.; gi,gj=np.floor(u/cell),np.floor(v/cell); best=np.full((hh,ww),9e5,np.float32); ang=np.zeros((hh,ww),np.float32); kind=np.zeros((hh,ww),np.float32)
 for oy in (-1,0,1):
  for ox in (-1,0,1):
   a,b=gi+ox,gj+oy; px=a*cell+(.16+.70*_h(a,b,seed+5))*cell+7*np.sin(b*.87+a*.41); py=b*cell+(.14+.73*_h(a,b,seed+9))*cell+6*np.sin(a*.79-b*.36); dx,dy=u-px,v-py; ds=dx*dx+dy*dy; take=ds<best; best=np.where(take,ds,best); ang=np.where(take,np.arctan2(dy,dx)-TAU*_h(a,b,seed+15),ang); kind=np.where(take,_h(a,b,seed+21),kind)
 # P4: I13/I14's 15px six-petal icon becomes a real 50–80px floral assembly,
 # repeated in every broad region but built only from 8–32px constituent arcs,
 # folds, leaf lobes and stems.  The coarse cell governs distribution only.
 rad=np.sqrt(best)+1e-4
 # P5: P4 was literally tracing bright flower contours.  Use broad petal,
 # fold and leaf *masses* instead; the tessera boundaries provide the fine
 # detail, while card neighborhoods create sculpted relief rather than a line.
 outer=np.exp(-((rad-(29.0+6.0*np.cos(5*ang)))/10.5)**4)
 middle=np.exp(-((rad-(19.5+4.3*np.cos(5*ang+.58)))/7.8)**4)
 inner=np.exp(-((rad-(10.5+2.5*np.cos(5*ang+1.22)))/5.2)**4)
 heart=np.exp(-(rad/7.2)**4)
 leaf=np.exp(-((rad-44.0)/8.6)**4)*np.clip(.35+.68*np.cos(2*ang+.28),0,1)
 stem=np.exp(-((rad-55.0)/5.8)**4)*np.clip(.30+.72*np.cos(ang+.92),0,1)
 active=(kind>.31).astype(np.float32)
 rose=np.clip(.36*outer+.42*middle+.49*inner+.31*heart+.26*leaf+.13*stem,0,1)*active
 # P3: P2 still packed too many cell identities.  The carrier becomes one
 # coherent black-cherry pearl lacquer; only its tile bevel, mica pin and
 # diagonal facet are permitted to depart from the rest card.  This tests the
 # actual Houdini requirement: the secret must supply the optical surprise.
 M=np.full((hh,ww),112.,np.float32); R=np.full((hh,ww),46.,np.float32); C=np.full((hh,ww),22.,np.float32)
 M=np.where(facet>.72,M+19,M); R=np.where(facet>.72,R-8,R); C=np.where(facet>.72,C+7,C)
 M=np.where(edge>.36,np.maximum(M,178),M); R=np.where(edge>.36,np.minimum(R,26),R); C=np.where(edge>.36,np.minimum(C,16),C)
 M=np.where(micro>0, np.maximum(M,151), M); R=np.where(micro>0,np.minimum(R,37),R); C=np.where(micro>0,np.minimum(C,25),C)
 # Hidden rose is a local permutation of the same physical card palette, not
 # a flat fill or RGB drawing.  Petal/heart/leaf cells arrive at different
 # highlight thresholds under changing real light.
 M=np.clip(M+active*(38*outer+76*middle+125*inner+48*leaf+35*stem),0,255)
 R=np.clip(R-active*(16*outer+38*middle+71*inner+20*leaf+14*stem),15,255)
 C=np.clip(C+active*(24*outer+71*middle+151*inner+48*leaf+31*stem),16,255)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC); body,M,R,C=up(body),up(M),up(R),up(C)
 out=(body.astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8))
 with _L: _C[key]=out; _C.popitem(last=False) if len(_C)>2 else None
 return out

def paint_marble_rose_i14(paint,shape,mask,seed,pm,bb):
 del bb; art,_=_arr(shape,seed); src=np.asarray(paint,np.float32)[...,:3]; src=src/255 if src.max(initial=0)>1.5 else src; m=np.asarray(mask,np.float32); m=m[...,0] if m.ndim==3 else m; m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None]; return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_marble_rose_i14(shape,seed,sm,bm,br): del sm,bm,br; return _arr(shape,seed)[1]
