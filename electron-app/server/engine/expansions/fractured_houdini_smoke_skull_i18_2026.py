"""Private Houdini I18 — smoked memento metal / recurring hidden skull relief.

Fresh H10 replacement after I17's galaxy-on-lattice failure.  The ordinary
carrier is a dark, grid-free mineral smoke-metal.  Repeated 92–130px skulls
exist only in metallic, roughness and offset clearcoat assignments: cranium,
temple, eye wells, nasal bridge, cheek planes, jaw and 8px teeth are distinct
physical material cards, never paint/decal pixels or a simple clip-art shape.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np
_C,_L=OrderedDict(),RLock();TAU=np.float32(6.283185307179586)
def _hash(a,b,s): return np.mod(np.sin(a*12.9898+b*78.233+s*37.719)*43758.5453,1.).astype(np.float32)
def _ell(x,y,cx,cy,rx,ry): return np.exp(-(((x-cx)/rx)**2+((y-cy)/ry)**2))
def _arr(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 h,w=map(int,shape);sc=768/max(h,w);hh,ww=max(192,round(h*sc)),max(192,round(w*sc));yy,xx=np.mgrid[:hh,:ww].astype(np.float32);x,y=xx/sc,yy/sc;q=seed*.091
 # A grid-free smoke-metal: five fine mark families, all 8–28px at native
 # scale—cross-satin threads, mineral curls, mica islands, tiny wet seams and
 # blackened troughs.  None carries skull geometry.
 u=.74*x+.67*y+4.1*np.sin(y*.038+q)+1.7*np.sin(y*.121-q);v=-.67*x+.74*y+3.8*np.sin(x*.041-q)+1.5*np.sin(x*.113+q)
 satin=.5+.5*np.sin(u*.31+.32*np.sin(v*.074))*np.sin(v*.27-.28*np.sin(u*.067));curl=.5+.5*np.sin((u+v)*.18+1.2*np.sin((u-v)*.064));mica=(np.sin(u*.89-v*.31)*np.sin(v*.77+u*.22)>.875).astype(np.float32);seam=np.exp(-((np.sin(u*.143-v*.116+.7*np.sin(v*.052)))/.18)**2);trough=np.exp(-((np.sin(u*.41+v*.24))/ .105)**2)
 # P2: P1's neutral looked like an underexposed woven fabric.  Raise it to
 # smoked graphite/violet metal and reduce the trough dominance; this alters
 # only the innocent carrier, never the skull-state masks below.
 # P5: calm the fabric-like cross-satin and let the non-repeating mineral
 # curl be the visible character of the innocent smoke-metal.
 body=np.clip(.25+.14*satin+.40*curl+.22*mica-.035*trough,0,1);tone=np.floor(body*7)/6.;art=np.empty((hh,ww,3),np.float32);art[...,0]=.062+.105*tone+.041*curl;art[...,1]=.064+.096*tone+.019*satin;art[...,2]=.075+.116*tone+.054*curl;art+=np.array((.047,.034,.069),np.float32)*(mica[...,None]*.55);art=np.clip(art,0,1)
 # Material cards bound to the carrier—pearl, satin, wet-mica, dark chrome
 # lips and blackened seams.  They are independent M/R/C assignments.
 # P3: P2's ordinary states competed with the skull like scratches.  Keep
 # real multi-card smoke metal but compress its variance and make seam/trough
 # lips much rarer; the detailed relief must own the reflective discovery.
 # P6: retain seven quiet underlying material states but remove the noisy
 # mica/seam signal from grazing response.  The relief now owns contrast.
 # P7: P6 looked clean but its base R/C spread fell below the Houdini floor.
 # Expand only the seven quiet physical cards (no added scratches/glitter).
 M=101+51*tone+8*mica+7*curl;R=139-49*tone-12*mica-11*curl;C=128-58*tone-15*mica-13*curl;M=np.where(seam>.94,np.maximum(M,207),M);R=np.where(seam>.94,np.minimum(R,33),R);C=np.where(seam>.94,np.minimum(C,34),C);M=np.where(trough>.95,np.minimum(M,76),M);R=np.where(trough>.95,np.maximum(R,158),R);C=np.where(trough>.95,np.maximum(C,151),C)
 # Jittered local skulls recur across the entire canvas.  Overall anatomy is
 # 90–125px, while each optical element is 7–28px and broken by the carrier.
 # P4: P3 proved the anatomy but packed it into wallpaper.  Expand the
 # stochastic cadence to roughly 30–40 skulls across a full carrier—enough
 # for every car panel to catch one, sparse enough to read as discoveries.
 cell=172.;gi,gj=np.floor(x/cell),np.floor(y/cell);best=np.full((hh,ww),9e7,np.float32);ang=np.zeros((hh,ww),np.float32);sel=np.zeros((hh,ww),np.float32)
 for oy in(-1,0,1):
  for ox in(-1,0,1):
   a,b=gi+ox,gj+oy;cx=a*cell+(.17+.66*_hash(a,b,seed+13))*cell;cy=b*cell+(.16+.65*_hash(a,b,seed+29))*cell;dx,dy=x-cx,y-cy;d=dx*dx+dy*dy;t=d<best;best=np.where(t,d,best);ang=np.where(t,np.arctan2(dy,dx),ang);sel=np.where(t,_hash(a,b,seed+43),sel);lx=np.where(t,dx,lx if 'lx' in locals() else dx);ly=np.where(t,dy,ly if 'ly' in locals() else dy)
 # Build an engraved skull, not a flat silhouette.  The head is intentionally
 # absent from the paint image.  Its cards assemble only in light.
 X,Y=lx/52.,ly/61.;cranium=_ell(X,Y,0,-.30,.74,.67);temples=np.maximum(_ell(X,Y,-.58,-.14,.24,.36),_ell(X,Y,.58,-.14,.24,.36));eyes=np.maximum(_ell(X,Y,-.29,-.18,.22,.145),_ell(X,Y,.29,-.18,.22,.145));brow=np.maximum(_ell(X,Y,-.29,-.36,.30,.080),_ell(X,Y,.29,-.36,.30,.080));nose=_ell(X,Y,0,.06,.10,.16);cheeks=np.maximum(_ell(X,Y,-.34,.20,.29,.18),_ell(X,Y,.34,.20,.29,.18));jaw=np.exp(-((np.abs(Y-.47)-(.27-.20*np.abs(X)))/.070)**2)*np.clip(1-np.abs(X)/.62,0,1);toothrow=np.exp(-((Y-.47)/.071)**2)*(np.sin(X*39)**2>.43).astype(np.float32);tooth_mirror=toothrow*(np.sin(X*39)>.03);tooth_satin=toothrow*(1-(np.sin(X*39)>.03));crown=cranium*(1-eyes*.92)*(1-nose*.86);active=(sel>.70).astype(np.float32);crown*=active;temples*=active;eyes*=active;brow*=active;nose*=active;cheeks*=active;jaw*=active;tooth_mirror*=active;tooth_satin*=active
 # Crown/cheeks are wet pearl; eye and nasal wells become matte-black; brow
 # and jaw are chrome folds; teeth have their own tiny mirror/coat break.
 M=np.clip(M+56*crown+38*cheeks+86*brow+58*jaw+102*tooth_mirror+37*tooth_satin-83*eyes-69*nose+27*temples,0,255);R=np.clip(R-42*crown-27*cheeks-74*brow-42*jaw-89*tooth_mirror-28*tooth_satin+98*eyes+88*nose+19*temples,15,255);C=np.clip(C+28*np.roll(crown,5,axis=1)-58*np.roll(cheeks,-4,axis=0)+111*np.roll(brow,3,axis=0)+43*jaw+125*np.roll(tooth_mirror,4,axis=1)+31*np.roll(tooth_satin,-3,axis=0)-61*eyes+78*nose+22*temples,16,255)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_CUBIC);art,M,R,C=up(art),up(M),up(R),up(C)
 out=(art.astype(np.float32),np.dstack((np.clip(M,0,255),np.clip(R,15,255),np.clip(C,16,255))).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_smoke_skull_i18(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_arr(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0] if m.ndim==3 else m;m=(np.clip(m,0,1)*np.clip(float(pm),0,1))[...,None];return np.clip(src*(1-m)+art*m,0,1).astype(np.float32)
def spec_smoke_skull_i18(shape,seed,sm,bm,br): del sm,bm,br;return _arr(shape,seed)[1]
