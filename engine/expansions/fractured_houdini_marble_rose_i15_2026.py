"""Private H10 I15 P1 — asymmetric calligraphic rose marquetry; no radial flower stamps.

Owner rejection evidence I12–I14: ordered rosettes, small flower sprites and
bright contour masses are all wrong.  I15 replaces them with irregular carved
scrolls: a curled petal, inner spiral, folded leaf and S-stem are separate
fine material events, repeated across the whole 2048-square canvas only via
M/Rough/Cc state choreography.  RGB contains a neutral black-cherry lacquer.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock(); TAU=np.float32(6.283185307179586)
def _h(a,b,s):return np.mod(np.sin(a*12.9898+b*78.233+s*37.719)*43758.5453,1.).astype(np.float32)
def _arr(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));yy,xx=np.mgrid[:hh,:ww].astype(np.float32);x,y=xx/sc,yy/sc;q=seed*.207
 # An innocent hand-rubbed black-cherry lacquer.  Fine 8–20px mica grains,
 # burnish arcs and shallow inlay seams are deliberately unrelated to roses.
 u=x+3.1*np.sin(y*.021+q)+1.5*np.sin(x*.043-y*.014);v=y+2.8*np.sin(x*.018-q)+1.3*np.sin(y*.038+x*.011);sz=15.6
 j=np.floor(v/sz);i=np.floor((u+.43*sz*np.mod(j,2))/sz);cx=(i+.5)*sz-.43*sz*np.mod(j,2);cy=(j+.5)*sz;lx=(u-cx)/(sz*.5);ly=(v-cy)/(sz*.5);tile=np.clip(1-(np.abs(lx)+np.abs(ly)),0,1);bevel=np.exp(-((np.abs(lx)+np.abs(ly)-.88)/.072)**2);facet=np.clip(.5+.5*(lx*.71+ly*.63),0,1);rnd=_h(i,j,seed)
 art=np.empty((hh,ww,3),np.float32);body=.12+.035*facet*tile+.018*(rnd-.5);art[...,0]=.102+body*.44;art[...,1]=.005+body*.052;art[...,2]=.039+body*.30;art=np.clip(art,0,1)
 # Sparse, jittered 120–180px distribution.  These cells only position the
 # full assemblies; each assembly is 50–85px of 8–32px calligraphic pieces.
 cell=151.;gi,gj=np.floor(u/cell),np.floor(v/cell);best=np.full((hh,ww),9e6,np.float32);phi=np.zeros((hh,ww),np.float32);sel=np.zeros((hh,ww),np.float32)
 for oy in(-1,0,1):
  for ox in(-1,0,1):
   a,b=gi+ox,gj+oy;px=a*cell+(.13+.76*_h(a,b,seed+5))*cell+11*np.sin(b*.73+a*.29);py=b*cell+(.12+.78*_h(a,b,seed+9))*cell+9*np.sin(a*.68-b*.33);dx,dy=u-px,v-py;d=dx*dx+dy*dy;t=d<best;best=np.where(t,d,best);phi=np.where(t,np.arctan2(dy,dx)-TAU*_h(a,b,seed+13),phi);sel=np.where(t,_h(a,b,seed+17),sel)
 r=np.sqrt(best)+1e-4;ang=np.mod(phi,TAU);X=r*np.cos(phi);Y=r*np.sin(phi)
 # A genuine curled, non-radial rose grammar: one Archimedean petal scroll,
 # its offset inner turn, a broad folded cup, two asymmetric leaves and a
 # 30px S-stem.  These are material-state regions, never RGB artwork.
 # P2: P1 exposed only the outer curl.  Widen and layer the nested folds so
 # the calligraphic feature has a visible rose-like cup, not a lonely crescent.
 curl=np.exp(-((r-(8.0+4.15*ang))/3.35)**2)*(r<38.)
 inner=np.exp(-((r-(5.0+2.72*np.mod(phi+1.40,TAU)))/2.85)**2)*(r<24.)
 cup=np.exp(-(((X+2.0)/19.5)**2+((Y-13.0)/12.0)**2))*np.clip(.48+.60*np.cos(phi-.25),0,1)
 leaf1=np.exp(-(((X-22.)/13.5)**2+((Y+24.)/6.6)**2))*np.clip(.45+.62*np.cos(phi+1.05),0,1)
 leaf2=np.exp(-(((X+18.)/11.5)**2+((Y+35.)/5.8)**2))*np.clip(.42-.58*np.cos(phi+.75),0,1)
 stem=np.exp(-((X-.085*(Y-22.)**2/12.)/2.35)**2)*np.exp(-((Y-31.)/25.)**8)
 active=(sel>.34).astype(np.float32);curl*=active;inner*=active;cup*=active;leaf1*=active;leaf2*=active;stem*=active
 # Complete physical cards by anatomy.  The rest is a dark pearl; bevels are
 # polished metal lips, mica pins are wet pearl, curls are dark chrome, cups
 # are satin pearl, leaves are weak-coated metal, and inner turns are matte
 # recesses.  Each channel therefore tells a different causal material story.
 # P4: P3 made every curl a chrome flare.  Use a dark-chrome rest and assign
 # complete contrasting cards by anatomy: satin curl, wet pearl cup, weak-coat
 # leaves, broken-coat stem and only a tiny mirror inner fold.  This makes the
 # pattern trade places with the body as the light/view angle changes.
 M=np.full((hh,ww),208.,np.float32);R=np.full((hh,ww),34.,np.float32);C=np.full((hh,ww),31.,np.float32)
 # P5: recover material breadth in the innocent carrier via tiny causal mica
 # and facet states, never through a second visible macro pattern.
 M=M+34*tile*facet-51*tile*(1-facet);R=R+46*tile*(1-facet)+19*tile*facet;C=C+71*tile*(1-facet)+17*tile*facet
 M=np.where(bevel>.35,231,M);R=np.where(bevel>.35,18,R);C=np.where(bevel>.35,16,C);pin=(np.sin((lx-ly)*TAU*1.4+rnd*TAU)>.71).astype(np.float32)*tile;M=np.where(pin>0,156,M);R=np.where(pin>0,56,R);C=np.where(pin>0,22,C)
 def card(mask,mm,rr,cc):
  nonlocal M,R,C
  M=M*(1-mask)+mm*mask;R=R*(1-mask)+rr*mask;C=C*(1-mask)+cc*mask
 card(curl,142,78,49);card(cup,94,42,18);card(leaf1,174,108,118);card(leaf2,156,132,156);card(stem,128,176,188);card(inner,252,15,16)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);art,M,R,C=up(art),up(M),up(R),up(C)
 out=(art.astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_marble_rose_i15(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_marble_rose_i15(shape,seed,sm,bm,br):del sm,bm,br;return _arr(shape,seed)[1]
