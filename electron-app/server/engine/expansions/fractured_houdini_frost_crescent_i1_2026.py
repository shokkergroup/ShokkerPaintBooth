"""FRACTURED HOUDINI H10-I4 — Marble Rose / hidden mineral rosettes."""
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 sc=min(1.,800./max(h,w));hh,ww=max(96,round(h*sc)),max(96,round(w*sc));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);p=(int(seed)%2713)*.006
 # H10-I4, owner directive 2026-08-30: route identity is Marble Rose.
 # The neutral carrier is dark mineral marble in 8–28px seam/pearl/pit marks;
 # the rose is repeated only in its M/R/Cc topology, never in RGB paint.
 uy=y/5.9;gy=np.floor(uy).astype(np.int32);ux=x/4.9+.47*np.mod(gy,2);gx=np.floor(ux).astype(np.int32);fx=np.mod(ux,1.);fy=np.mod(uy,1.);state=np.mod(gx*41+gy*27+(gx^gy)*9+int(seed),8);freeze=state.astype(np.float32)/7.
 jx=_fract(np.sin(gx*19.37+gy*41.83+int(seed)*.14)*31917.4);jy=_fract(np.sin(gx*73.21+gy*13.67+int(seed)*.18)*20713.5);dx,dy=fx-jx,fy-jy;rad=np.sqrt(dx*dx+dy*dy)
 lip=np.clip((.060-np.abs(rad-.25))*16.,0,1)*(.30+.70*freeze)
 bloom=np.clip((.29-rad)*3.2,0,1)*(.25+.75*np.mod(gx*23+gy*13+int(seed),5)/4.)
 ice=((np.mod(gx*37+gy*19+int(seed),11)<3).astype(np.float32))*np.clip((.17-np.sqrt((dx+.12)**2+(dy-.11)**2))*6.0,0,1)*(1-.6*lip)
 fiss=np.clip((.050-np.abs(dx*.58+dy*.62-(freeze-.5)*.18))*17.,0,1)*(1-.55*lip)
 # I10: the catalog exposed a flat green material field behind the old roses.
 # Build the carrier as flowing 8–24px wine-marble seams and mica ribbons so
 # the secret is embedded in an authored material family rather than pasted on.
 flow=x/12.4+1.42*np.sin(y/27.0+p)+.72*np.sin((x+y)/41.0-p)
 vein=np.clip((.060-np.abs(np.sin(flow)))*16.7,0,1)
 ribbon=np.clip((.044-np.abs(np.sin(x/21.0-y/16.5+.7*np.sin(y/19.0))))*22.7,0,1)
 mica_seam=np.maximum(vein*.72,ribbon*.54)*(1-.48*lip)
 # H10-I16 / owner hard-reject 2026-08-30: remove the sparse tiled symbols.
 # This is an irregular full-canvas jewellery-grade rose relief: every rose
 # is composed from 8-28px outer petals, inner scroll petals, seed rings,
 # curled sepals and fine engraved veins.  It exists ONLY in M/R/Cc.
 motif=np.zeros((hh,ww),np.uint8);inner=np.zeros((hh,ww),np.uint8);centre=np.zeros((hh,ww),np.uint8);curl=np.zeros((hh,ww),np.uint8);rng=np.random.default_rng(int(seed)^0x10A5E);count=max(62,int(hh*ww/9500))
 for n in range(count):
  cx=float(rng.uniform(-18,ww+18));cy=float(rng.uniform(-18,hh+18));rx=float(rng.uniform(13,22));ry=float(rng.uniform(12,21));ang=float(rng.uniform(-.52,.52));ca,sa=np.cos(ang),np.sin(ang);phase=float(rng.uniform(0,6.283));thick=int(rng.integers(2,4))
  def _pt(px,py): return tuple(np.rint((cx+ca*px-sa*py,cy+sa*px+ca*py)).astype(np.int32))
  for k in range(7):
   a=phase+k*np.pi*2/7+.10*np.sin(k*2.43+phase);rad=.58+.07*np.sin(k*1.71+phase);px,py=np.cos(a)*rx*rad,np.sin(a)*ry*rad;axes=(max(5,int(rx*(.34+.045*np.sin(k+phase)))),max(3,int(ry*(.22+.030*np.cos(k*1.9)))))
   cv2.ellipse(motif,_pt(px,py),axes,int(np.degrees(a+ang)),34,326,(k%7)+1,thick,cv2.LINE_AA);cv2.line(motif,_pt(px*.28,py*.28),_pt(px*.84,py*.84),(k%6)+1,1,cv2.LINE_AA)
  for k in range(5):
   a=phase*.58+k*np.pi*2/5+.22;px,py=np.cos(a)*rx*.29,np.sin(a)*ry*.29;axes=(max(4,int(rx*.23)),max(3,int(ry*.15)))
   cv2.ellipse(inner,_pt(px,py),axes,int(np.degrees(a+ang)),24,338,(k%6)+1,thick,cv2.LINE_AA)
  # Three interlaced Fibonacci-like petal scrolls give the hidden flower a
  # genuine carved-rose centre, not a daisy/propeller outline.
  for strand,val in ((.0,2),(.82,4),(1.64,6)):
   th=np.linspace(.14,3.7*np.pi,96);rad=.055+.032*th+.012*np.sin(th*3.0+strand);pts=[_pt(np.cos(th0+phase+strand)*rx*rad0,np.sin(th0+phase+strand)*ry*rad0) for th0,rad0 in zip(th,rad)]
   cv2.polylines(inner,[np.array(pts,np.int32)],False,val,1,cv2.LINE_AA)
  for rr,val in ((.23,255),(.14,255),(.075,255)): cv2.ellipse(centre,_pt(0,0),(max(2,int(rx*rr)),max(2,int(ry*rr))),int(np.degrees(ang)),0,360,val,1 if rr<.2 else thick,cv2.LINE_AA)
  for k in (-1,1): cv2.polylines(curl,[np.array([_pt(px,py) for px,py in [(k*rx*.28,ry*.46),(k*rx*.74,ry*.84),(k*rx*.92,ry*.53),(k*rx*.55,ry*.22)]],np.int32)],False,255,thick,cv2.LINE_AA)
  for off in np.linspace(-rx*.38,rx*.38,5): cv2.line(curl,_pt(off,ry*.47),_pt(off*.48,ry*.19),255,1,cv2.LINE_AA)
  # Long, fine botanical tendrils let the repeated hidden roses read as an
  # intentional marble-garden composition instead of unrelated decals.
  for side in (-1,1):
   vine=[(side*rx*.16,ry*.38),(side*rx*.70,ry*.92),(side*rx*.31,ry*1.53),(side*rx*.86,ry*2.15),(side*rx*.42,ry*2.58)]
   cv2.polylines(curl,[np.array([_pt(px,py) for px,py in vine],np.int32)],False,255,max(1,thick-1),cv2.LINE_AA)
   for lx,ly,a in ((side*rx*.62,ry*1.08,-34*side),(side*rx*.42,ry*1.82,38*side)):
    cv2.ellipse(curl,_pt(lx,ly),(max(3,int(rx*.16)),max(2,int(ry*.10))),int(np.degrees(ang))+a,20,340,255,1,cv2.LINE_AA)
 secret=(motif>0)|(inner>0)|(centre>35)|(curl>35)
 # I5: staged card audit found I4 nearly black (mean 15.53, std 4.01).
 # Lift the mineral marble itself—charcoal, wine seam, mica and pearl—while
 # leaving every hidden rosette exclusively in the material channels.
 charcoal=np.array((.050,.030,.060),np.float32);slate=np.array((.21,.125,.23),np.float32);rose=np.array((.67,.13,.29),np.float32);mica=np.array((.56,.38,.55),np.float32);pearl=np.array((.86,.56,.70),np.float32);paint=charcoal*(.52+.11*freeze[...,None])+slate*(.34+.16*(1-freeze[...,None]));z=(lip*.35)[...,None];paint=paint*(1-z)+rose*z;z=(bloom*.24)[...,None];paint=paint*(1-z)+mica*z;z=(mica_seam*.31)[...,None];paint=paint*(1-z)+mica*z;z=(ice*.28+fiss*.13)[...,None];paint=paint*(1-z)+pearl*z
 # I11: I10's tile-state noise competed with the ornamental relief.  Keep the
 # marble carrier materially alive through smooth seam/lip/bloom responses,
 # leaving the multi-state rose linework legible rather than pixel-confetti.
 soft_state=cv2.GaussianBlur(state.astype(np.float32)/7.,(0,0),1.15)
 m=73+31*soft_state+88*lip+64*bloom+82*ice+42*fiss+71*mica_seam
 r=154-54*soft_state-74*lip-59*bloom-72*ice-35*fiss-66*mica_seam
 coat=82+34*soft_state+92*lip+77*bloom+98*ice+48*fiss+82*mica_seam
 # Eight adjacent physical states—not a flat neon silhouette.  Petal tiers,
 # rims and curls intentionally interleave chrome, satin, pearl and muted
 # metal so the rose reads as relief instead of printed color.
 q=np.where(motif>0,motif%8,np.where(inner>0,inner%8,np.where(centre>35,4,np.where(curl>35,6,7)))).astype(np.int32)
 sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(246,42,211,88,232,61,169),default=124).astype(np.float32)
 sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(13,204,56,149,29,178,81),default=121).astype(np.float32)
 cc=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(244,46,188,103,218,70,156),default=126).astype(np.float32)
 # Delicate contour highlights preserve rose anatomy even where petals overlap.
 contour=(motif>0)|(inner>0)|(centre>35)
 m=np.where(secret,sm,m);r=np.where(secret,sr,r);coat=np.where(secret,cc,coat)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,coat=map(up,(m,r,coat))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_frost_crescent_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_frost_crescent_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
