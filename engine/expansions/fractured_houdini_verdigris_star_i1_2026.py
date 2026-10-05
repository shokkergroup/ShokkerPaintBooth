"""FRACTURED HOUDINI H9-I5 — Velvet Dagger / hidden velvet-steel blades."""
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 sc=min(1.,736./max(h,w));hh,ww=max(96,round(h*sc)),max(96,round(w*sc));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);p=(int(seed)%2749)*.0063
 # H9-I5, owner directive 2026-08-30: Velvet Dagger needs an innocent
 # wine-velvet micro-lacquer; its repeated daggers exist only in M/R/Cc.
 uy=y/6.15;gy=np.floor(uy).astype(np.int32);ux=x/5.35+.43*np.mod(gy,2);gx=np.floor(ux).astype(np.int32);fx=np.mod(ux,1.);fy=np.mod(uy,1.);state=np.mod(gx*43+gy*23+(gx^gy)*7+int(seed),8);aging=state.astype(np.float32)/7.
 jx=_fract(np.sin(gx*17.71+gy*43.19+int(seed)*.13)*24137.3);jy=_fract(np.sin(gx*71.29+gy*11.73+int(seed)*.19)*18347.7);dx,dy=fx-jx,fy-jy;ang=(aging-.5)*2.1;ca,sa=np.cos(ang),np.sin(ang);along=ca*dx+sa*dy;across=-sa*dx+ca*dy
 line=np.clip((.045-np.abs(across))*18.,0,1)*np.clip((.34-np.abs(along))*3.0,0,1)
 pat=np.clip((.30-np.sqrt(dx*dx+dy*dy))*3.4,0,1)*(.25+.75*aging)
 verd=((np.mod(gx*31+gy*17+int(seed),13)<3).astype(np.float32))*np.clip((.22-np.sqrt((dx+.13)**2+(dy-.10)**2))*5.0,0,1)*(1-.6*line)
 pock=((np.mod(gx*19+gy*37+int(seed),11)<3).astype(np.float32))*np.clip((.12-np.sqrt((dx-.18)**2+(dy+.14)**2))*8.0,0,1)*(1-.5*line)
 # I9 / Houdini scale correction: repeated 6x6-cell (~85–105px native)
 # dagger assemblies are built only from pre-existing fine velvet cells.
 sgx=np.floor_divide(gx,6);sgy=np.floor_divide(gy,6);u=(np.mod(gx,6)+fx)/3.-1.;v=(np.mod(gy,6)+fy)/3.-1.;chosen=np.mod(sgx*43+sgy*61+(sgx^sgy)*17+int(seed),29)==0
 blade=(v>-.72)&(v<.28)&(np.abs(u)<(.045+.31*(v+.72)));guard=(np.abs(v-.27)<.10)&(np.abs(u)<.56);grip=(v>.27)&(v<.63)&(np.abs(u)<.12);pommel=((u*u+(v-.72)*(v-.72))<.035)
 secret=chosen&(blade|guard|grip|pommel);sm=np.where(secret,238,0).astype(np.float32);sr=np.where(secret,18,0).astype(np.float32);cc=np.where(secret,242,0).astype(np.float32)
 # I8 / owner-eye pass: the fine velvet nap was valid but read too near-black
 # at standard-card scale.  Enrich only the wine/ruby/mauve lacquer family;
 # dagger outlines remain M/R/Cc-only in `secret` above.
 ink=np.array((.058,.014,.032),np.float32);wine=np.array((.455,.042,.122),np.float32);ruby=np.array((.850,.085,.235),np.float32);mauve=np.array((.590,.070,.205),np.float32);pearl=np.array((.880,.340,.500),np.float32);paint=ink*(.66+.10*aging[...,None])+wine*(.50+.18*(1-aging[...,None]));z=(line*.32)[...,None];paint=paint*(1-z)+ruby*z;z=(pat*.18)[...,None];paint=paint*(1-z)+mauve*z;z=(verd*.22+pock*.10)[...,None];paint=paint*(1-z)+pearl*z
 # I7: the staged picker proved this carrier was roughness-green dominant.
 # Keep every mark local, but cross-bias the 8 material tiers so adjacent
 # velvet naps carry genuinely different M/R/Cc mixtures under moving light.
 t=state.astype(np.float32)/7.;m=16+126*t+84*line+58*pat+79*verd+34*pock;rgh=242-138*t-68*line-53*pat-70*verd-31*pock;coat=22+122*(1-t)+87*line+69*pat+88*verd+39*pock;m=np.where(secret,sm,m);rgh=np.where(secret,sr,rgh);coat=np.where(secret,cc,coat)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,rgh,coat=map(up,(m,rgh,coat))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(rgh,15,255),np.clip(coat,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_verdigris_star_i1(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov;mix=(np.clip(cov,0,1)*float(pm))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_verdigris_star_i1(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
