"""FRACTURED HOUDINI H20-I1 — Lapis Scarab / material-only beetle relics."""
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 scale=min(1.,800./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);ph=(int(seed)%3469)*.0048
 # I3 (owner 2026-08-30): remove the regular blue-gold lapis grid.  Build a
 # fine irregular lapis inlay: 5–10px chipped stones, narrow gold joins,
 # dark bezel corners, pearl facets and controlled turquoise inclusions.
 ux,uy=x/6.35,y/7.0;gx=np.floor(ux).astype(np.int32);gy=np.floor(uy).astype(np.int32);near=np.full((hh,ww),99.,np.float32);next_near=np.full((hh,ww),99.,np.float32);dx0=np.zeros((hh,ww),np.float32);dy0=np.zeros((hh,ww),np.float32)
 for ox in (-1,0,1):
  for oy in (-1,0,1):
   nx,ny=gx+ox,gy+oy;jx=_fract(np.sin(nx*12.9898+ny*78.233+int(seed)*.17)*43758.545);jy=_fract(np.sin(nx*93.9898+ny*31.411+int(seed)*.11)*24634.635);dx,dy=ux-(nx+jx),uy-(ny+jy);dsq=dx*dx+dy*dy;take=dsq<near;next_near=np.where(take,near,np.minimum(next_near,dsq));near=np.where(take,dsq,near);dx0=np.where(take,dx,dx0);dy0=np.where(take,dy,dy0)
 dist=np.sqrt(near);gap=np.sqrt(next_near)-dist;facet=np.clip(1-dist/.86,0,1);mortar=np.exp(-np.square((gap-.10)/.055));state=np.mod(gx*31+gy*19+(gx^gy)*17+int(seed),8);fx=np.mod(ux,1.);fy=np.mod(uy,1.);bevel=np.clip((.20-np.abs(dx0)-np.abs(dy0))*4.2,0,1)*(1-mortar*.5);inlay=(np.mod(gx*29+gy*37+(gx^gy)*5,17)<2).astype(np.float32)*facet;dark=(np.mod(gx*13+gy*41,23)<2).astype(np.float32)*(.32+.68*bevel)
 # H20-I5 / owner verdict 2026-08-30: procedural silhouettes still read as
 # noise.  Draw a precise material-only scarab relief atlas: every stroke is
 # 8–20px native, while each complete beetle is repeated over the whole sheet.
 motif=np.zeros((hh,ww),np.uint8);accent=np.zeros((hh,ww),np.uint8);cw,ch=9*6.35,9*7.0
 for iy in range(int(np.ceil(hh/ch))+1):
  for ix in range(int(np.ceil(ww/cw))+1):
   if np.mod(ix*47+iy*59+(ix^iy)*19+int(seed),10): continue
   jx=int((_fract(np.sin(ix*19.7+iy*31.1+int(seed))*917.)-.5)*.18*cw);jy=int((_fract(np.sin(ix*41.3+iy*13.7+int(seed))*631.)-.5)*.16*ch);cx=int((ix+.5)*cw)+jx;cy=int((iy+.5)*ch)+jy;ax,ay=max(7,int(cw*.24)),max(9,int(ch*.31));th=max(2,int(min(cw,ch)*.040))
   cv2.ellipse(motif,(cx,cy),(ax,ay),0,0,360,255,th,cv2.LINE_AA);cv2.ellipse(accent,(cx,cy),(max(3,ax-4),max(4,ay-5)),0,0,360,255,1,cv2.LINE_AA)
   cv2.ellipse(motif,(cx,cy-ay-int(ch*.11)),(max(4,int(ax*.48)),max(3,int(ay*.27))),0,0,360,255,th,cv2.LINE_AA);cv2.line(motif,(cx,cy-ay+2),(cx,cy+ay-2),255,th,cv2.LINE_AA)
   for k in (-2,-1,0,1,2): cv2.ellipse(accent,(cx,cy+int(k*ay*.27)),(max(3,ax-4),max(2,int(ay*.11))),0,190,350,255,1,cv2.LINE_AA)
   for sy in (-.45,0,.40):
    yy=cy+int(sy*ay);cv2.polylines(motif,[np.array([(cx-ax+2,yy),(cx-ax-int(cw*.16),yy-int(ch*.11)),(cx-ax-int(cw*.24),yy+int(ch*.05))],np.int32)],False,255,th,cv2.LINE_AA);cv2.polylines(motif,[np.array([(cx+ax-2,yy),(cx+ax+int(cw*.16),yy-int(ch*.11)),(cx+ax+int(cw*.24),yy+int(ch*.05))],np.int32)],False,255,th,cv2.LINE_AA)
   cv2.polylines(accent,[np.array([(cx-2,cy-ay-int(ch*.18)),(cx-int(cw*.15),cy-ay-int(ch*.33)),(cx-int(cw*.24),cy-ay-int(ch*.28))],np.int32)],False,255,1,cv2.LINE_AA);cv2.polylines(accent,[np.array([(cx+2,cy-ay-int(ch*.18)),(cx+int(cw*.15),cy-ay-int(ch*.33)),(cx+int(cw*.24),cy-ay-int(ch*.28))],np.int32)],False,255,1,cv2.LINE_AA)
 secret=motif>35;shell=(accent>35)&secret;q=np.mod(np.floor(x/13.).astype(np.int32)+np.floor(y/17.).astype(np.int32),8);q=np.where(shell,(q+2)%8,q);sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(248,34,212,92,231,62,174),default=126).astype(np.float32);sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(12,207,55,151,28,177,80),default=122).astype(np.float32);co=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(245,47,184,107,216,71,155),default=129).astype(np.float32)
 t=state.astype(np.float32)/7.;night=np.array((.007,.015,.050),np.float32);lapis=np.array((.025,.10,.35),np.float32);azure=np.array((.07,.27,.64),np.float32);turq=np.array((.08,.54,.48),np.float32);gold=np.array((.72,.50,.13),np.float32);paint=night*(.47+.13*t[...,None])+lapis*(.36+.16*(1-t[...,None]));z=(mortar*.31)[...,None];paint=paint*(1-z)+gold*z;z=(bevel*.24)[...,None];paint=paint*(1-z)+azure*z;z=(facet*.20+inlay*.19)[...,None];paint=paint*(1-z)+turq*z;z=(dark*.19)[...,None];paint=paint*(1-z)+night*z
 m=23+52*t+86*mortar+69*bevel+75*facet+91*inlay+28*dark;r=232-46*t-80*mortar-62*bevel-68*facet-86*inlay-21*dark;cc=24+56*t+93*mortar+75*bevel+84*facet+97*inlay+30*dark;m=np.where(secret,sm,m);r=np.where(secret,sr,r);cc=np.where(secret,co,cc)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_lapis_scarab_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_lapis_scarab_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
