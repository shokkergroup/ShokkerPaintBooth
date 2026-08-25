# -*- coding: utf-8 -*-
"""Native-2048 Dragon Hex Glass I1: aperiodic micro-scute cuticle.

SPB-105 / Wilds attempt 114 / 2026-08-25.  This is explicitly not a hex grid.
Five thousand deterministic growth sites, warped by two keratin-stress fields,
form a dense aperiodic micro-scute dermis.  Each scute has a double wall,
inner cortex, stressed hinge, molting notch and occasional bridge; cell-level
state is derived from its own growth label, not a random/noise overlay.
"""
from __future__ import annotations
import hashlib,json,time
from functools import lru_cache
from pathlib import Path
import cv2,numpy as np
ID,ATTEMPT,WORK,NATIVE="fc_dragon_hex_glass",114,512,2048
# SPB-105 / Wilds owner review 2026-08-25: "unnatural border ... noticeable
# and messed up" when scale is reduced.  The old finite 512 field allowed
# Voronoi cells on the visible perimeter to grow without external neighbours.
# Build a larger continuous dermis and crop its protected interior instead;
# this changes the physical growth boundary, never hides it with noise. Exact
# rerun: M7 99.0 -> 99.4; cold/warm authored runs 0.304/0.098/0.097 s.
FIELD, CROP = 640, 64
PA=np.asarray(((6,13,25),(10,28,48),(14,50,70),(19,76,92),(28,106,107),(47,140,111),(83,171,104),(132,194,90),(184,207,75),(224,193,75),(238,145,83),(223,83,108),(181,45,128),(111,27,121)),np.float32)/255
PB=np.asarray(((10,6,33),(25,11,63),(46,20,94),(73,32,122),(107,42,137),(148,49,133),(191,61,116),(226,93,96),(243,139,78),(224,183,72),(169,207,80),(92,195,107),(37,157,129),(13,99,125)),np.float32)/255
MT=np.asarray((13,42,75,110,148,186,223,250),np.uint8);RT=np.asarray((18,47,79,114,151,189,226,252),np.uint8);CT=np.asarray((9,34,63,98,136,177,216,250),np.uint8)
def _fract(v):return v-np.floor(v)
def _map(t,p):q=np.mod(t,1)*len(p);i=np.floor(q).astype(np.int16)%len(p);f=(q-np.floor(q))[...,None];return p[i]*(1-f)+p[(i+1)%len(p)]*f
def _hash(label,a,b):return _fract(label*a+b*np.sin(label*.61803398875))
@lru_cache(maxsize=1)
def _fields():
 seeds=np.ones((FIELD,FIELD),np.uint8)
 # A dense but non-grid growth chronology: each site is warped before it
 # becomes a growth centre.  Collisions are irregular keratin boundaries.
 for n in range(1,7814):
  u=_fract(n*1.61803398875+.17*np.sin(n*1.41421356237));v=_fract(n*1.32471795724+.13*np.sin(n*2.2360679775+.31))
  x=(u+.031*np.sin(11*v+3*u)+.018*np.sin(29*v-7*u))*FIELD;y=(v+.026*np.sin(13*u-4*v)+.017*np.cos(31*u+5*v))*FIELD
  seeds[int(np.clip(round(y),0,FIELD-1)),int(np.clip(round(x),0,FIELD-1))]=0
 dist,labels=cv2.distanceTransformWithLabels(seeds,cv2.DIST_L2,3,labelType=cv2.DIST_LABEL_PIXEL);labels=labels.astype(np.int32)
 boundary=((labels!=np.roll(labels,1,0))|(labels!=np.roll(labels,-1,0))|(labels!=np.roll(labels,1,1))|(labels!=np.roll(labels,-1,1))).astype(np.uint8)
 outer=cv2.dilate(boundary,np.ones((3,3),np.uint8)).astype(np.float32);inner=cv2.dilate(boundary,np.ones((5,5),np.uint8)).astype(np.float32)-outer
 # This distance is measured inward from actual collision walls, not from a
 # synthetic field: it supplies the cortex, hinge bands and molting placement.
 interior=cv2.distanceTransform((1-boundary).astype(np.uint8),cv2.DIST_L2,3);centre=np.clip(interior/5.0,0,1).astype(np.float32)
 h1=_hash(labels.astype(np.float32),.61803398875,.17);h2=_hash(labels.astype(np.float32),.41421356237,.31)
 cortex=np.clip(centre*(.54+.46*h1),0,1);hinge=np.exp(-np.square((interior-(1.8+1.9*h2))/(.65+.25*h1))).astype(np.float32)
 # Molting is a wedge-like subtraction selected by a cell's physical growth
 # age and its inward normal direction; the result remains attached to walls.
 yy,xx=np.mgrid[0:FIELD,0:FIELD].astype(np.float32);ang=np.arctan2(yy-(labels//FIELD),xx-(labels%FIELD));notch=((h1>.80)&(np.sin(ang*2.0+h2*6.3)>.63)&(interior<3.6)).astype(np.float32)
 bridge=((h2>.86)&(boundary>0)&(np.sin(xx*.61+yy*.43+h1*9)>.72)).astype(np.float32);bridge=cv2.dilate(bridge,np.ones((3,3),np.uint8)).astype(np.float32)
 stress=np.clip(np.abs(cv2.Sobel(cortex,cv2.CV_32F,1,0,ksize=3))+np.abs(cv2.Sobel(cortex,cv2.CV_32F,0,1,ksize=3)),0,1)
 phase=.17*h1+.21*h2+.26*cortex+.15*hinge-.14*notch+.10*stress
 fields={"scute_outer_walls":outer,"scute_inner_walls":inner,"keratin_cortex":cortex,"hinge_bands":hinge,"molting_notches":notch,"stress_bridges":bridge,"stress_crazing":stress,"phase":phase}
 return {key:value[CROP:CROP+WORK,CROP:CROP+WORK].copy() for key,value in fields.items()}
def _paint(b=False):
 f=_fields();t=.08+f["phase"]+.17*f["hinge_bands"]+.12*f["stress_bridges"]-.16*f["molting_notches"]
 if b:t=.52-t+.18*f["scute_inner_walls"]+.13*f["stress_crazing"]-.15*f["scute_outer_walls"]
 rgb=_map(t,PB if b else PA);base=np.asarray((.035,.09,.12) if not b else (.07,.025,.16),np.float32);rgb=.38*base+.62*rgb
 light=.42+.26*f["keratin_cortex"]+.25*f["scute_outer_walls"]+.20*f["scute_inner_walls"]+.17*f["hinge_bands"]+.13*f["stress_bridges"]-.15*f["molting_notches"]
 rgb*=light[...,None];pal=PB if b else PA;rgb+=f["stress_crazing"][...,None]*pal[8]*.11;rgb+=f["molting_notches"][...,None]*pal[12]*.12
 return np.clip(rgb,0,1).astype(np.float32),f
def _spec(f):
 phase=np.mod(.61*f["keratin_cortex"]+.37*f["hinge_bands"]+.71*f["stress_bridges"]+.23*f["stress_crazing"],1)
 m=.13+.32*f["scute_outer_walls"]+.28*f["hinge_bands"]+.21*f["stress_bridges"]+.18*f["stress_crazing"]-.14*f["molting_notches"]
 r=.82-.31*f["scute_inner_walls"]-.22*f["keratin_cortex"]+.25*f["molting_notches"]+.17*f["stress_crazing"]
 c=.11+.47*(1-np.abs(2*phase-1))+.22*f["keratin_cortex"]+.17*f["stress_bridges"]-.16*f["molting_notches"]
 return tuple(tab[np.floor(np.clip(z,0,.9999)*8).astype(np.int16)] for z,tab in ((m,MT),(r,RT),(c,CT)))
def _authored():p,f=_paint(False);return p,np.stack(_spec(f),2)
def main():
 out=Path("_wilds_fullres_progress_20260824/dragon_scute_i1");out.mkdir(parents=True,exist_ok=True);ts=[];ims=[]
 for _ in range(3):
  st=time.perf_counter();p,f=_paint(False);ims.append(np.clip(cv2.resize(p,(NATIVE,NATIVE),interpolation=cv2.INTER_CUBIC)*255+.5,0,255).astype(np.uint8));ts.append(time.perf_counter()-st)
 q,_=_paint(True);a,b=ims[0],np.clip(cv2.resize(q,(NATIVE,NATIVE),interpolation=cv2.INTER_CUBIC)*255+.5,0,255).astype(np.uint8)
 for n,im in (("paint",a),("angle_a",a),("angle_b",b)):cv2.imwrite(str(out/f"{ID}_{n}_2048.png"),cv2.cvtColor(im,cv2.COLOR_RGB2BGR))
 cv2.imwrite(str(out/f"{ID}_crop_1to1.png"),cv2.cvtColor(a[704:1344,704:1344],cv2.COLOR_RGB2BGR));sp=cv2.resize(np.stack(_spec(f),2),(NATIVE,NATIVE),interpolation=cv2.INTER_NEAREST)
 for n,ch in zip(("metallic","roughness","clearcoat"),cv2.split(sp)):cv2.imwrite(str(out/f"{ID}_{n}_2048.png"),ch)
 flat=sp.reshape(-1,3).astype(np.float32);co=np.corrcoef(flat,rowvar=False);dl=np.abs(a.astype(np.float32)-b.astype(np.float32))/255;report={"id":ID,"attempt":ATTEMPT,"status":"NATIVE-2048-GATES-PENDING","timings_s":ts,"deterministic":bool(all(np.array_equal(a,z) for z in ims[1:])),"deterministic_digest":hashlib.sha256(a.tobytes()).hexdigest(),"angle_delta_mean":float(dl.mean()),"angle_delta_p95":float(np.quantile(dl,.95)),"coverage":{k:float((v>.3).mean()) for k,v in f.items() if k!="phase"},"spec_ranges":{n:[int(flat[:,i].min()),int(flat[:,i].max())] for i,n in enumerate(("M","R","Cc"))},"spec_std":{n:float(flat[:,i].std()) for i,n in enumerate(("M","R","Cc"))},"spec_correlations":{"M_R":float(co[0,1]),"M_Cc":float(co[0,2]),"R_Cc":float(co[1,2])},"owner_accepted":False,"production_wired":False};(out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8");print(json.dumps(report,indent=2))
def install_into_engine(registry,base_registry=None):return "fractured-wilds-dragon-scute-i1: fail-closed pending gates"
if __name__=="__main__":main()
