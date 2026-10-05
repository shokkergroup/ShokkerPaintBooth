"""FRACTURED HOUDINI H6-I5 — Prism Moth / dark prism-scale lacquer.

Owner correction 2026-08-30: replaces the rejected stripe-led I1–I4 trials
with a non-linear micro-scale carrier and repeated material-only moths.
"""
from collections import OrderedDict
from threading import RLock
import cv2,numpy as np
_C,_L=OrderedDict(),RLock()
def _fract(z):return z-np.floor(z)
def _arrays(shape,seed):
 h,w=map(int,shape[:2]);key=(h,w,int(seed))
 with _L:
  if key in _C:_C.move_to_end(key);return _C[key]
 scale=min(1.,800./max(h,w));hh,ww=max(96,round(h*scale)),max(96,round(w*scale));y,x=np.mgrid[0:hh,0:ww].astype(np.float32);ph=(int(seed)%3527)*.0044
 # Nonlinear 5–11px prism scales, narrow char seams, offset facets, tiny
 # spectral lips and dark voids—explicitly no stripe or ribbon field.
 u=x+2.5*np.sin(y/11+ph)+1.7*np.sin((x-y)/17);v=y+2.3*np.cos(x/13-ph)+1.3*np.sin((2*x+y)/20);gx=np.floor(u/6.4).astype(np.int32);gy=np.floor(v/7.3).astype(np.int32);fx=np.mod(u/6.4,1.);fy=np.mod(v/7.3,1.);seam=np.clip((.115-np.minimum(np.minimum(fx,1-fx),np.minimum(fy,1-fy)))*8.0,0,1);facet=np.clip((.19-np.abs(fx-fy))*5.25,0,1)*(1-seam*.55);scalept=np.clip((.27-np.abs(fx-.5)-np.abs(fy-.5))*3.75,0,1);lip=np.clip((.13-np.abs((fx+fy)-1))*7.5,0,1)*facet;void=(np.mod(gx*43+gy*17,23)<2).astype(np.float32)*(.30+.70*facet);state=np.mod(gx*37+gy*21+(gx^gy)*13+int(seed),8)
 # H6-I12 / owner hard reset 2026-08-30: remove ellipse-math moths.  Each
 # hidden moth is an irregular hand-engraved wing relief: outer wing contour,
 # four vein bays, eyespot rings, thorax, antennae and fringe all use distinct
 # M/R/Cc states; none of that geometry enters the RGB lacquer.
 wing=np.zeros((hh,ww),np.uint8);body=np.zeros((hh,ww),np.uint8);detail=np.zeros((hh,ww),np.uint8);antenna=np.zeros((hh,ww),np.uint8);rng=np.random.default_rng(int(seed)^0x6D071);count=max(36,int(hh*ww/13200))
 for n in range(count):
  cx=float(rng.uniform(-26,ww+26));cy=float(rng.uniform(-22,hh+22));rx=float(rng.uniform(24,38));ry=float(rng.uniform(22,34));ang=float(rng.uniform(-.55,.55));ca,sa=np.cos(ang),np.sin(ang);th=int(rng.integers(2,4))
  def pt(px,py): return tuple(np.rint((cx+ca*px-sa*py,cy+sa*px+ca*py)).astype(np.int32))
  for side,val in ((-1,1),(1,3)):
   outline=[(side*rx*.10,ry*.38),(side*rx*.31,-ry*.26),(side*rx*.78,-ry*.74),(side*rx*1.08,-ry*.26),(side*rx*.92,ry*.18),(side*rx*.54,ry*.58),(side*rx*.16,ry*.48)]
   cv2.polylines(wing,[np.array([pt(px,py) for px,py in outline],np.int32)],True,val,th,cv2.LINE_AA)
   # Wing bays and short fan veins create 8-28px purposeful substructure.
   for bay in range(4):
    yy=-ry*.43+bay*ry*.25;tip=(side*rx*(.70-.08*bay),yy);cv2.line(wing,pt(side*rx*.12,ry*.30),pt(*tip),(val+bay)%7+1,1 if bay else th,cv2.LINE_AA)
   for ring,val2 in ((.22,5),(.11,7)):
    cv2.ellipse(detail,pt(side*rx*.54,-ry*.17),(max(3,int(rx*ring)),max(3,int(ry*ring))),int(np.degrees(ang))+side*18,0,360,val2,1 if ring<.2 else th,cv2.LINE_AA)
   fringe=[(side*rx*.52,ry*.57),(side*rx*.70,ry*.69),(side*rx*.83,ry*.57)]
   cv2.polylines(detail,[np.array([pt(px,py) for px,py in fringe],np.int32)],False,6,1,cv2.LINE_AA)
  cv2.ellipse(body,pt(0,ry*.10),(max(3,int(rx*.105)),max(7,int(ry*.46))),int(np.degrees(ang)),0,360,255,th,cv2.LINE_AA)
  cv2.circle(body,pt(0,-ry*.39),max(3,th+1),255,-1,cv2.LINE_AA)
  for side in (-1,1):
   ant=[(side*rx*.05,-ry*.50),(side*rx*.23,-ry*.76),(side*rx*.47,-ry*.82),(side*rx*.58,-ry*.66)]
   cv2.polylines(antenna,[np.array([pt(px,py) for px,py in ant],np.int32)],False,255,1,cv2.LINE_AA)
 secret=(wing>0)|(body>0)|(detail>0)|(antenna>0)
 q=np.where(wing>0,wing%8,np.where(body>0,0,np.where(detail>0,detail%8,np.where(antenna>0,6,np.mod(state+np.floor((fx+fy)*5).astype(np.int32),8))))).astype(np.int32);sm=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(255,10,225,253,27,193,255),default=148).astype(np.float32);sr=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(2,248,25,10,210,46,13),default=181).astype(np.float32);co=np.select((q==0,q==1,q==2,q==3,q==4,q==5,q==6),(255,16,144,255,42,91,255),default=129).astype(np.float32)
 # I8 picker-scale correction (owner 2026-08-30): I7 was honest but collapsed
 # to a nearly black uniform field.  Keep RGB free of moth geometry, but give
 # every 5–11px prism cell one of eight restrained midnight/teal/indigo
 # lacquer states.  This is fine material behavior, not a recolored moth.
 # I10: picker-scale carrier remained underlit.  Raise only the individual
 # midnight/teal/indigo prism-scale states; moth outlines remain spec-only.
 t=state.astype(np.float32)/7.;black=np.array((.044,.052,.090),np.float32);navy=np.array((.105,.145,.235),np.float32);slate=np.array((.230,.290,.420),np.float32);ice=np.array((.390,.470,.620),np.float32);char=np.array((.022,.028,.050),np.float32);tints=np.array(((.066,.090,.145),(.075,.125,.190),(.115,.090,.205),(.065,.155,.195),(.145,.125,.235),(.085,.180,.220),(.155,.185,.270),(.125,.145,.230)),np.float32);paint=black*(.36+.17*t[...,None])+navy*(.49+.17*(1-t[...,None]));paint=paint*.78+tints[state]*.22;z=(seam*.25)[...,None];paint=paint*(1-z)+char*z;z=(facet*.34)[...,None];paint=paint*(1-z)+slate*z;z=(scalept*.30)[...,None];paint=paint*(1-z)+ice*z;z=(lip*.25)[...,None];paint=paint*(1-z)+navy*z;z=(void*.14)[...,None];paint=paint*(1-z)+char*z
 m=21+54*t+87*seam+68*facet+75*scalept+83*lip+27*void;r=237-48*t-81*seam-61*facet-68*scalept-77*lip-20*void;cc=20+58*t+94*seam+74*facet+85*scalept+92*lip+29*void;m=np.where(secret,sm,m);r=np.where(secret,sr,r);cc=np.where(secret,co,cc)
 if(hh,ww)!=(h,w):
  up=lambda z:cv2.resize(z.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR);paint=up(paint);m,r,cc=map(up,(m,r,cc))
 out=(np.clip(paint,0,1).astype(np.float32),np.stack((np.clip(m,0,255),np.clip(r,15,255),np.clip(cc,16,255)),2).astype(np.uint8))
 with _L:_C[key]=out;_C.popitem(last=False) if len(_C)>2 else None
 return out
def paint_prism_moth_i5(paint,shape,mask,seed,pm,bb):
 del bb;auth,_=_arrays(shape,seed);src=np.asarray(paint,np.float32)[...,:3];src=src/255. if src.max(initial=0)>1.5 else src;cov=np.asarray(mask,np.float32);cov=cov[...,0] if cov.ndim==3 else cov
 # Engine strengths may reach 2.0; a complete monolithic carrier must never
 # become negative when the engine applies its 1.5x thumbnail/render boost.
 mix=(np.clip(cov,0,1)*min(1.,max(0.,float(pm))))[...,None];return np.clip(src*(1-mix)+auth*mix,0,1).astype(np.float32)
def spec_prism_moth_i5(shape,seed,sm,base_m,base_r):
 del sm,base_m,base_r;return _arrays(shape,seed)[1]
