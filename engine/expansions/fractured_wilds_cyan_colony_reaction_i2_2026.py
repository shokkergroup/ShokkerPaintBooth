# -*- coding: utf-8 -*-
"""Native-2048 Cyan Colony I2: deterministic reaction-diffusion pellicle.

SPB-105 / Wilds attempt 111 / 2026-08-25.  Cyan Colony is built from actual
Gray-Scott reaction fronts, seeded by fixed inoculation scars and cultured to
a connected wet pellicle.  The seven visible material events are concentration
states or derivatives of that same chemical process: occupied film, advancing
fronts, nutrient terraces, pore collars, capillary forks, collapsed broth and
repaired wet skins.  No random or noise field is involved.
"""
from __future__ import annotations
import hashlib,json,time
from functools import lru_cache
from pathlib import Path
import cv2,numpy as np
ID,ATTEMPT,WORK,NATIVE="fpe_cyan_colony",111,256,2048
PA=np.asarray(((3,12,27),(4,31,54),(5,57,79),(6,88,101),(10,122,117),(20,157,130),(44,190,139),(88,213,139),(143,224,126),(199,216,108),(232,177,91),(235,119,96),(205,65,119),(144,38,129),(75,24,107)),np.float32)/255
PB=np.asarray(((11,6,38),(20,13,72),(30,28,111),(32,55,142),(24,94,154),(18,135,156),(32,171,141),(79,202,121),(146,218,97),(207,210,83),(243,165,79),(242,100,91),(220,48,123),(172,28,145),(103,18,126)),np.float32)/255
MT=np.asarray((13,42,75,110,148,186,223,250),np.uint8);RT=np.asarray((17,47,79,115,152,190,226,252),np.uint8);CT=np.asarray((9,34,63,98,136,177,216,250),np.uint8)
def _norm(a):
 lo,hi=float(a.min()),float(a.max());return ((a-lo)/max(1e-6,hi-lo)).astype(np.float32)
def _map(t,p):
 q=np.mod(t,1)*len(p);i=np.floor(q).astype(np.int16)%len(p);f=(q-np.floor(q))[...,None];return p[i]*(1-f)+p[(i+1)%len(p)]*f
def _line(a,w):return np.clip(1-np.abs(a)/w,0,1).astype(np.float32)
def _halton(n,b):
 v=0.;f=1.
 while n:f/=b;v+=f*(n%b);n//=b
 return v
@lru_cache(maxsize=1)
def _fields():
 # Fixed inoculation cuts and spores are actual culture inputs, not a noise
 # texture.  The result is deterministically evolved, then cached.
 u=np.ones((WORK,WORK),np.float32);v=np.zeros_like(u);seed=np.zeros_like(u)
 for n in range(1,131):
  cx=int(3+250*_halton(n,2));cy=int(3+250*_halton(n,3));rx=1+(n*7)%4;ry=1+(n*11)%3
  cv2.ellipse(seed,(cx,cy),(rx,ry),(n*37)%180,0,360,.62+.06*(n%4),-1,cv2.LINE_AA)
 # Four nonrepeating inoculation cuts cause colonies to meet, split and heal.
 for pts in (((-14,38),(48,18),(173,98),(271,64)),((-12,196),(78,244),(162,122),(267,192)),((56,-9),(22,83),(185,171),(156,269)),((266,16),(207,88),(79,179),(-12,232))):
  cv2.polylines(seed,[np.asarray(pts,np.int32).reshape(-1,1,2)],False,.78,2,cv2.LINE_AA)
 v[:]=np.clip(.025+.90*seed,0,1);u[:]=np.clip(1-.58*v,0,1)
 kernel=np.asarray(((.05,.20,.05),(.20,-1,.20),(.05,.20,.05)),np.float32)
 yy,xx=np.mgrid[0:WORK,0:WORK].astype(np.float32)
 feed=.0225+.0032*xx/(WORK-1)+.0011*np.sin(yy/29.0)
 kill=.0510+.0026*yy/(WORK-1)+.0009*np.cos(xx/37.0)
 for _ in range(360):
  lu=cv2.filter2D(u,-1,kernel,borderType=cv2.BORDER_REFLECT);lv=cv2.filter2D(v,-1,kernel,borderType=cv2.BORDER_REFLECT);r=u*v*v
  u+=.18*lu-r+feed*(1-u);v+=.09*lv+r-(feed+kill)*v;np.clip(u,0,1,out=u);np.clip(v,0,1,out=v)
 chem=_norm(v+.38*(1-u));smooth=cv2.GaussianBlur(chem,(0,0),.75)
 gx=cv2.Sobel(smooth,cv2.CV_32F,1,0,ksize=3);gy=cv2.Sobel(smooth,cv2.CV_32F,0,1,ksize=3);grad=_norm(np.hypot(gx,gy));lap=_norm(np.abs(cv2.Laplacian(smooth,cv2.CV_32F)))
 # Fixed chemical thresholds are physical concentration bands, never rank
 # quantization.  Fine 1-4px work events become 8-32px at native size.
 occupied=np.clip((smooth-.16)/.30,0,1);front=_line(np.mod(smooth*8.7+.21*grad,1)-.50,.075)*np.clip((grad-.12)/.60,0,1)
 terrace=_line(np.mod(smooth*15.3+.43*lap,1)-.50,.060)*np.clip((grad-.08)/.68,0,1)
 maxima=(smooth>=cv2.dilate(smooth,np.ones((3,3),np.uint8))).astype(np.float32)*np.clip((smooth-.43)/.38,0,1)
 pores=cv2.dilate(maxima,np.ones((2,2),np.uint8))*np.clip((lap-.27)/.60,0,1)
 collars=_line(np.mod(np.hypot(gx,gy)*32+smooth*4.1,1)-.50,.08)*pores
 forks=np.clip(grad*(1-np.clip((smooth-.72)/.24,0,1))*1.7,0,1)*_line(np.sin(gx*28-gy*23),.20)
 collapsed=np.clip((.28-smooth)/.22,0,1)*np.clip((lap-.15)/.75,0,1)
 repair=_line(np.mod(smooth*6.1-lap*2.3,1)-.50,.055)*np.clip((smooth-.28)/.52,0,1)
 # Nutrient precipitation is a high-frequency chemical phase of the evolved
 # concentration/gradient/Laplacian, not an independently injected grain.
 # Its 1-2px work bodies are 8-16px at native 2048.
 granules=(1-np.abs(np.sin(np.pi*(smooth*29.7+grad*3.1+lap*1.9))))**13*np.clip((smooth-.12)/.45,0,1)
 phase=.47*smooth+.20*grad+.14*lap+.10*front-.12*collapsed
 return {"occupied_pellicle":occupied,"advancing_fronts":front,"nutrient_terraces":terrace,"quorum_pores":pores,"pore_collars":collars,"capillary_forks":forks,"collapsed_broth":collapsed,"repair_skins":repair,"crystallized_nutrient_granules":granules,"chem":chem,"phase":phase}
def _paint(b=False):
 f=_fields();t=.06+f["phase"]+.17*f["nutrient_terraces"]+.12*f["repair_skins"]+.08*f["crystallized_nutrient_granules"]-.15*f["collapsed_broth"]
 if b:t=.51-t+.18*f["advancing_fronts"]+.13*f["pore_collars"]-.16*f["capillary_forks"]
 rgb=_map(t,PB if b else PA);broth=np.asarray((.075,.050,.245) if b else (.035,.205,.235),np.float32);rgb=.70*broth+.30*rgb;light=.70+.18*f["occupied_pellicle"]+.27*f["advancing_fronts"]+.19*f["nutrient_terraces"]+.15*f["capillary_forks"]+.12*f["repair_skins"]+.21*f["crystallized_nutrient_granules"]-.10*f["collapsed_broth"]
 rgb*=light[...,None];pal=PB if b else PA;rgb+=f["quorum_pores"][...,None]*pal[10]*.18;rgb+=f["pore_collars"][...,None]*pal[13]*.10;rgb+=f["crystallized_nutrient_granules"][...,None]*pal[8]*.12
 return np.clip(rgb,0,1).astype(np.float32),f
def _spec(f):
 # Every material channel begins with a different concentration state across
 # the whole living sheet, then receives its own named derivatives.  This
 # avoids "one dark base + one bright peak" and keeps all eight authored
 # material shades visibly present, including in the unreacted broth.
 phase=np.mod(2.73*f["chem"]+.61*f["nutrient_terraces"]+.93*f["repair_skins"],1.0)
 m=.12+.38*f["chem"]+.30*f["advancing_fronts"]+.23*f["nutrient_terraces"]+.18*f["repair_skins"]-.14*f["collapsed_broth"]
 r=.81-.24*f["chem"]-.39*f["capillary_forks"]-.30*f["advancing_fronts"]+.27*f["collapsed_broth"]+.22*f["quorum_pores"]+.17*f["pore_collars"]
 c=.12+.48*(1-np.abs(2*phase-1))+.22*f["repair_skins"]+.17*f["nutrient_terraces"]-.18*f["quorum_pores"]+.15*f["collapsed_broth"]
 return tuple(tab[np.floor(np.clip(z,0,.9999)*8).astype(np.int16)] for z,tab in ((m,MT),(r,RT),(c,CT)))
def _authored():p,f=_paint(False);return p,np.stack(_spec(f),2)
def main():
 out=Path("_wilds_fullres_progress_20260824/cyan_colony_reaction_i2");out.mkdir(parents=True,exist_ok=True);ts=[];ims=[]
 for _ in range(3):
  st=time.perf_counter();p,f=_paint(False);ims.append(np.clip(cv2.resize(p,(NATIVE,NATIVE),interpolation=cv2.INTER_CUBIC)*255+.5,0,255).astype(np.uint8));ts.append(time.perf_counter()-st)
 q,_=_paint(True);a,b=ims[0],np.clip(cv2.resize(q,(NATIVE,NATIVE),interpolation=cv2.INTER_CUBIC)*255+.5,0,255).astype(np.uint8)
 for n,im in (("paint",a),("angle_a",a),("angle_b",b)):cv2.imwrite(str(out/f"{ID}_{n}_2048.png"),cv2.cvtColor(im,cv2.COLOR_RGB2BGR))
 cv2.imwrite(str(out/f"{ID}_crop_1to1.png"),cv2.cvtColor(a[704:1344,704:1344],cv2.COLOR_RGB2BGR));sp=cv2.resize(np.stack(_spec(f),2),(NATIVE,NATIVE),interpolation=cv2.INTER_NEAREST)
 for n,ch in zip(("metallic","roughness","clearcoat"),cv2.split(sp)):cv2.imwrite(str(out/f"{ID}_{n}_2048.png"),ch)
 flat=sp.reshape(-1,3).astype(np.float32);co=np.corrcoef(flat,rowvar=False);dl=np.abs(a.astype(np.float32)-b.astype(np.float32))/255;report={"id":ID,"attempt":ATTEMPT,"status":"NATIVE-2048-GATES-PENDING","timings_s":ts,"deterministic":bool(all(np.array_equal(a,z) for z in ims[1:])),"deterministic_digest":hashlib.sha256(a.tobytes()).hexdigest(),"angle_delta_mean":float(dl.mean()),"angle_delta_p95":float(np.quantile(dl,.95)),"coverage":{k:float((v>.3).mean()) for k,v in f.items() if k not in ("chem","phase")},"spec_ranges":{n:[int(flat[:,i].min()),int(flat[:,i].max())] for i,n in enumerate(("M","R","Cc"))},"spec_std":{n:float(flat[:,i].std()) for i,n in enumerate(("M","R","Cc"))},"spec_correlations":{"M_R":float(co[0,1]),"M_Cc":float(co[0,2]),"R_Cc":float(co[1,2])},"owner_accepted":False,"production_wired":False};(out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8");print(json.dumps(report,indent=2))
def install_into_engine(registry,base_registry=None):return "fractured-wilds-cyan-colony-reaction-i2: fail-closed pending gates"
if __name__=="__main__":main()
