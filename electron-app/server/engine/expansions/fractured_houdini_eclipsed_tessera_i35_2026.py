"""Private I35 Eclipsed Tessera — dark opal cells, hidden only in material state.

SPB-H1 / 2026-09-01.  The carrier is a fine irregular glass tessera process.
No secret coordinate enters RGB paint.  M/R/Cc alone turns selected adjacent
8–32px cells into intermittent spiral-current relief under changing light.
"""
from __future__ import annotations
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_W=768; _C=OrderedDict(); _L=RLock(); _T=np.float32(6.283185307179586)
def _h(x,y,s): return np.mod(np.sin(x*127.1+y*311.7+s*73.9)*43758.5453,1.).astype(np.float32)
def _assets(shape,seed):
 key=(*map(int,shape),int(seed))
 with _L:
  if key in _C:return _C[key]
 yy,xx=np.mgrid[:_W,:_W].astype(np.float32);p=8.0
 # Each tessera is 21px native, with deliberately warped seams—not a grid.
 gx=(xx+2.5*np.sin(yy*.041+seed*.17)+1.3*np.sin(xx*.083))/p; gy=(yy+2.2*np.sin(xx*.048-seed*.11)-1.5*np.sin(yy*.071))/p; gi,gj=np.floor(gx),np.floor(gy); fx,fy=gx-gi-.5,gy-gj-.5; diamond=np.clip(1-(np.abs(fx)+np.abs(fy))*1.65,0,1); seam=np.clip((.16-np.minimum(np.abs(fx),np.abs(fy)))/.16,0,1); tile=_h(gi,gj,seed+31); facet=.5+.5*np.sin(fx*5.1-fy*4.7+tile*5.3)
 # No secret field in paint: black opal glass, local facets, fine dark seams.
 void=.14+.86*diamond; navy=np.stack((.015+.035*tile,.032+.070*facet,.072+.136*tile),2); plum=np.stack((.046+.082*facet,.016+.025*tile,.061+.108*facet),2); opal=np.stack((.22+.31*facet,.31+.37*tile,.50+.34*facet),2); art=np.clip((navy*.69+plum*.31)*void[...,None]+opal*(.12*diamond*(.22+.78*tile))[...,None]-seam[...,None]*.06,0,1).astype(np.float32)
 M=54+72*tile+63*diamond-41*seam+20*facet; R=191-65*facet-53*diamond+38*seam; C=43+116*facet+69*diamond+47*seam
 # Material-only spiral currents at multiple field locations; they select
 # existing small tesserae, never draw a large painted or decal symbol.
 cx=np.array((151.,418.,682.,-54.,785.,277.),np.float32); cy=np.array((106.,374.,635.,504.,196.,814.),np.float32); secret=np.zeros_like(xx)
 for k,(ax,ay) in enumerate(zip(cx,cy)):
  dx,dy=xx-ax,yy-ay; r=np.hypot(dx,dy); theta=np.arctan2(dy,dx); arm=np.abs(np.sin(theta*3.0+r*.082+k*.73)); ring=np.abs(np.sin(r*.118-k*.41)); secret=np.maximum(secret,np.clip((.17-arm)/.17,0,1)*np.clip((.20-ring)/.20,0,1))
 # Eight documented adjacent cards, selected only inside the material current.
 # I35 P2: P1's material current was too recessed to discover. Widen only the
 # connected current's state selection—not the tessera geometry or RGB paint.
 st=np.mod(gi.astype(np.int32)*5+gj.astype(np.int32)*7+np.floor((fx-fy)*5).astype(np.int32),8); cards=np.asarray(((250,15,40),(250,45,40),(200,15,16),(100,40,16),(225,140,100),(252,38,255),(80,120,140),(0,200,160)),np.float32); active=(secret>.09)&(diamond>.25); base=np.dstack((M,R,C)); base[active]=.42*base[active]+.58*cards[st][active]; spec=np.clip(base,0,255).astype(np.uint8)
 h,w=key[:2]
 if(h,w)!=(_W,_W):art=cv2.resize(art,(w,h),interpolation=cv2.INTER_AREA if max(h,w)<_W else cv2.INTER_LINEAR);spec=cv2.resize(spec,(w,h),interpolation=cv2.INTER_NEAREST)
 out=(art,spec)
 with _L:
  _C[key]=out
  if len(_C)>2:_C.popitem(last=False)
 return out
def paint_eclipsed_tessera_i35(paint,shape,mask,seed,pm,bb):
 del bb;art,_=_assets(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255 if src.max(initial=0)>1.5 else src;m=np.asarray(mask,np.float32);m=m[...,0]if m.ndim==3 else m;return np.clip(src*(1-(m*pm)[...,None])+art*(m*pm)[...,None],0,1).astype(np.float32)
def spec_eclipsed_tessera_i35(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _assets(shape,seed)[1]
