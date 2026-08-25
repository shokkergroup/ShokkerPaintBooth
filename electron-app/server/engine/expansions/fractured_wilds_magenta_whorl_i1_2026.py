# -*- coding: utf-8 -*-
"""Native-2048 Magenta Whorl I1: multi-focus folded-growth lamina.

SPB-105 / Wilds attempt 108 / 2026-08-25.  This is a continuous plant lamina
whose growth chronology is folded through three off-card organs and two
incompatible shear fields.  Its visible anatomy is not a generic gradient:
primary growth lips, split vein fans, cusp folds, bounded wound windows, and
crossed repair seams all derive from the same growing sheet.  No noise, stamps,
grid, cell pack, sparse icon, or shared Wilds composer is used. SPB-105 /
attempt 108 metric repair: initial M7 83.5 (M5 60.5) made the independently
busy spec maps outrun the visible paint anatomy. Fine epidermal micro-veins
now descend from the same growth chronology and material channels use that
anatomy rather than unrelated high-frequency oscillation (83.5 -> pending).
"""
from __future__ import annotations
import hashlib,json,time
from pathlib import Path
import cv2,numpy as np
ID,ATTEMPT,WORK,NATIVE="fbl_magenta_whorl",108,1024,2048
PA=np.asarray(((8,5,25),(25,7,53),(57,10,88),(101,17,121),(151,29,145),(197,48,147),(232,73,128),(249,109,99),(249,151,75),(231,196,74),(179,218,82),(101,205,105),(40,163,124),(14,103,125),(7,47,87)),np.float32)/255
PB=np.asarray(((4,17,32),(6,46,69),(9,84,103),(13,129,129),(26,173,131),(67,205,111),(137,220,87),(207,216,75),(245,183,77),(250,134,91),(239,88,120),(209,52,147),(163,31,153),(105,24,133),(49,19,94)),np.float32)/255
MT=np.asarray((14,39,70,105,143,181,220,248),np.uint8);RT=np.asarray((18,45,76,111,148,187,225,252),np.uint8);CT=np.asarray((10,34,63,98,136,176,216,250),np.uint8)
def _map(t,p):
 q=np.mod(t,1)*len(p);i=np.floor(q).astype(np.int16)%len(p);f=(q-np.floor(q))[...,None];return p[i]*(1-f)+p[(i+1)%len(p)]*f
def _fields():
 yy,xx=np.mgrid[0:WORK,0:WORK].astype(np.float32);x=(xx+.5)/WORK*2-1;y=(yy+.5)/WORK*2-1
 # Two explicit anisotropic shears first; the growth centres are off-card so
 # the canvas is an uninterrupted sheet rather than a central flower icon.
 sx=x+.12*np.sin(4.4*y+1.7*np.sin(2.9*x))+.055*np.sin(11.3*y-2.1*x)
 sy=y+.10*np.sin(3.6*x-1.1*np.cos(3.7*y))+.052*np.sin(9.1*x+2.8*y)
 centres=((-1.28,-.78,.83),(1.17,-.47,1.11),(-.31,1.25,.94))
 chron=0; fan=0; cusp=0
 for k,(cx,cy,weight) in enumerate(centres):
  dx,dy=sx-cx,sy-cy;r=np.sqrt((dx*(1+.12*k))**2+(dy*(1-.09*k))**2);a=np.arctan2(dy,dx)
  chron+=weight*(8.4*r+1.67*a+.48*np.sin(3*a+5*r)+.21*np.cos(7*a-3*r))
  fan+=np.sin(2.1*r-4.7*a+.5*k)
  cusp+=np.cos(5.3*a+3.8*r-.8*k)
 primary=(1-np.abs(np.sin(np.pi*chron)))**2
 split=(1-np.abs(np.sin(np.pi*(.61*chron+2.7*fan))))**4
 cusps=(1-np.abs(np.sin(np.pi*(.33*chron+3.1*cusp))))**5
 seam=(1-np.abs(np.sin(np.pi*(.47*chron-1.9*fan+1.7*cusp))))**6
 micro=(1-np.abs(np.sin(np.pi*(1.73*chron+2.1*fan-1.37*cusp))))**9
 wound=np.clip(primary*split*(1-cusps)*(.72+.28*np.sin(chron*.23+fan)),0,1)**2
 repair=np.clip(split*cusps*(1-wound),0,1)**2
 return {"x":x,"y":y,"chron":chron,"fan":fan,"cusp":cusp,"primary_lips":primary,"split_fans":split,"cusp_folds":cusps,"repair_seams":seam,"epidermal_microveins":micro,"wound_windows":wound,"repair_folds":repair}
def _paint(b=False):
 f=_fields();t=.047*f["chron"]+.13*f["fan"]+.05*f["cusp"]
 if b:t=.39-t+.22*np.sin(4*f["x"]-7*f["y"])+.07*np.cos(9*f["y"]+2*f["x"])
 rgb=_map(t,PB if b else PA);light=.22+.38*f["primary_lips"]+.21*f["split_fans"]+.14*f["cusp_folds"]+.10*f["repair_folds"]-.27*f["wound_windows"]
 light+=.12*f["epidermal_microveins"]
 rgb*=light[...,None];rgb+=f["repair_seams"][...,None]*((PB if b else PA)[8])*.11;rgb+=f["epidermal_microveins"][...,None]*((PB if b else PA)[10])*.08;rgb*=1-f["wound_windows"][...,None]*.52
 return np.clip(rgb,0,1).astype(np.float32),f
def _spec(f):
 c,fan,cu=f["chron"],f["fan"],f["cusp"]
 m=.22+.36*f["primary_lips"]+.22*f["repair_seams"]+.18*f["epidermal_microveins"]-.21*f["wound_windows"]+.12*np.sin(np.pi*.17*c)
 r=.69-.27*f["split_fans"]-.18*f["epidermal_microveins"]+.23*f["wound_windows"]+.16*f["cusp_folds"]+.10*np.cos(np.pi*(.13*c+.5*cu))
 q=.20+.34*f["repair_folds"]+.22*f["split_fans"]+.19*f["epidermal_microveins"]-.16*f["wound_windows"]+.16*np.sin(np.pi*(.19*c+.7*fan))
 return tuple(t[np.floor(np.clip(z,0,.9999)*8).astype(np.int16)] for z,t in ((m,MT),(r,RT),(q,CT)))
def _authored():
 p,f=_paint(False);return p,np.stack(_spec(f),2)
def main():
 out=Path("_wilds_fullres_progress_20260824/magenta_whorl_i1");out.mkdir(parents=True,exist_ok=True);ts=[];ims=[]
 for _ in range(3):
  st=time.perf_counter();p,f=_paint(False);ims.append(np.clip(cv2.resize(p,(NATIVE,NATIVE),interpolation=cv2.INTER_CUBIC)*255+.5,0,255).astype(np.uint8));ts.append(time.perf_counter()-st)
 q,_=_paint(True);a,b=ims[0],np.clip(cv2.resize(q,(NATIVE,NATIVE),interpolation=cv2.INTER_CUBIC)*255+.5,0,255).astype(np.uint8)
 for n,im in (("paint",a),("angle_a",a),("angle_b",b)):cv2.imwrite(str(out/f"{ID}_{n}_2048.png"),cv2.cvtColor(im,cv2.COLOR_RGB2BGR))
 cv2.imwrite(str(out/f"{ID}_crop_1to1.png"),cv2.cvtColor(a[704:1344,704:1344],cv2.COLOR_RGB2BGR));sp=cv2.resize(np.stack(_spec(f),2),(NATIVE,NATIVE),interpolation=cv2.INTER_NEAREST)
 for n,ch in zip(("metallic","roughness","clearcoat"),cv2.split(sp)):cv2.imwrite(str(out/f"{ID}_{n}_2048.png"),ch)
 flat=sp.reshape(-1,3).astype(np.float32);co=np.corrcoef(flat,rowvar=False);dl=np.abs(a.astype(np.float32)-b.astype(np.float32))/255;report={"id":ID,"attempt":ATTEMPT,"status":"NATIVE-2048-GATES-PENDING","timings_s":ts,"deterministic":bool(all(np.array_equal(a,z) for z in ims[1:])),"deterministic_digest":hashlib.sha256(a.tobytes()).hexdigest(),"angle_delta_mean":float(dl.mean()),"angle_delta_p95":float(np.quantile(dl,.95)),"coverage":{k:float((v>.3).mean()) for k,v in f.items() if k.endswith(("lips","fans","folds","seams","windows"))},"spec_ranges":{n:[int(flat[:,i].min()),int(flat[:,i].max())] for i,n in enumerate(("M","R","Cc"))},"spec_std":{n:float(flat[:,i].std()) for i,n in enumerate(("M","R","Cc"))},"spec_correlations":{"M_R":float(co[0,1]),"M_Cc":float(co[0,2]),"R_Cc":float(co[1,2])},"owner_accepted":False,"production_wired":False};(out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8");print(json.dumps(report,indent=2))
def install_into_engine(registry,base_registry=None):return "fractured-wilds-magenta-whorl-i1: fail-closed pending gates"
if __name__=="__main__":main()
