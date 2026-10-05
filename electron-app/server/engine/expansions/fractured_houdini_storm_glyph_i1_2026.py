"""FRACTURED HOUDINI H7-I6 — Eclipse Veil / prismatic obsidian microcells."""
from collections import OrderedDict
from threading import RLock
import cv2, numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 # I3: 704² preserves the 9–22px native facet range while making room for a
 # properly connected multi-stroke glyph inside the whole-card budget.
 scale=min(1.,704./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);ph=(int(seed)%2551)*.0063
 # Non-uniform tiny prismatic cells: skewed 9–22px facets, inlaid rims, hot
 # teal/violet/cinder inclusions, and dark obsidian joints. Never a flat grid.
 u=x/5.9+.22*np.sin(y/19+ph);v=y/5.4+.17*np.sin(x/23-ph);row=np.floor(v).astype(np.int32);col=np.floor(u-.5*np.mod(row,2)).astype(np.int32);fx=u-.5*np.mod(row,2)-col-.5;fy=v-row-.5
 qx=fx+.13*fy; qy=fy-.09*fx;rad=np.maximum(np.abs(qx)/.46,np.abs(qy)/.42);facet=np.clip(1-rad,0,1);rim=np.exp(-np.square((rad-.83)/.06));state=np.mod(col*37+row*19+(col^row)*13+int(seed),8);twist=.5+.5*np.sin(col*.71+row*.43+ph)
 # H7-I9 / owner hard reset: replace sparse formula crescents with irregular
 # eclipse-astrolabe reliefs. Fine crescent rims, occulting discs, orbit arcs,
 # radial marks and constellation beads are M/R/Cc-only; obsidian RGB stays
 # completely innocent in neutral light.
 cres=np.zeros((hh,ww),np.uint8);orbit=np.zeros((hh,ww),np.uint8);bead=np.zeros((hh,ww),np.uint8);rng=np.random.default_rng(int(seed)^0xE711);count=max(42,int(hh*ww/12500))
 for n in range(count):
  cx=float(rng.uniform(-21,ww+21));cy=float(rng.uniform(-21,hh+21));rad=float(rng.uniform(16,27));ang=float(rng.uniform(-.56,.56));ca,sa=np.cos(ang),np.sin(ang);th=int(rng.integers(2,4))
  def pt(px,py):return tuple(np.rint((cx+ca*px-sa*py,cy+sa*px+ca*py)).astype(np.int32))
  cv2.ellipse(cres,pt(0,0),(int(rad),int(rad*.88)),int(np.degrees(ang)),42,320,1,th,cv2.LINE_AA);cv2.ellipse(cres,pt(rad*.29,-rad*.04),(int(rad*.72),int(rad*.65)),int(np.degrees(ang)),58,304,3,th,cv2.LINE_AA)
  for frac,val in ((1.16,5),(.76,7)) : cv2.ellipse(orbit,pt(0,0),(int(rad*frac),int(rad*frac*.82)),int(np.degrees(ang)),24,166,val,1,cv2.LINE_AA)
  for k in range(9):
   aa=k*np.pi*2/9+.18;cv2.line(orbit,pt(np.cos(aa)*rad*.82,np.sin(aa)*rad*.72),pt(np.cos(aa)*rad*1.03,np.sin(aa)*rad*.90),(k%6)+1,1,cv2.LINE_AA)
  for k in range(5):
   aa=k*np.pi*2/5+.35;cv2.circle(bead,pt(np.cos(aa)*rad*1.08,np.sin(aa)*rad*.91),max(2,th),255,-1,cv2.LINE_AA)
 secret=(cres>0)|(orbit>0)|(bead>0);sm=np.where(cres>0,240,np.where(orbit>0,174,np.where(bead>0,221,0))).astype(np.float32);sr=np.where(cres>0,18,np.where(orbit>0,73,np.where(bead>0,36,0))).astype(np.float32);sc=np.where(cres>0,244,np.where(orbit>0,155,np.where(bead>0,211,0))).astype(np.float32)
 # I7: staged card audit found the neutral obsidian too black.  Brighten
 # only the local facet/rim enamel layers; eclipses remain spec-only.
 obs=np.array((.020,.028,.058),np.float32);slate=np.array((.080,.145,.245),np.float32);teal=np.array((.035,.50,.53),np.float32);violet=np.array((.33,.11,.56),np.float32);silver=np.array((.66,.73,.82),np.float32)
 st=state.astype(np.float32)/7.;paint=obs*(.54+.13*twist[...,None])+slate*(.36+.15*(1-twist[...,None]));tint=teal*(.18+.31*st[...,None])+violet*(.14+.20*(1-st[...,None]));z=(facet*.36)[...,None];paint=paint*(1-z)+tint*z;z=(rim*.34)[...,None];paint=paint*(1-z)+silver*z
 m=25+47*st+94*facet+50*rim;r=228-42*st-79*facet-48*rim;cc=22+51*st+102*facet+59*rim;m=np.where(secret,sm,m);r=np.where(secret,sr,r);cc=np.where(secret,sc,cc)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_storm_glyph_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_storm_glyph_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
