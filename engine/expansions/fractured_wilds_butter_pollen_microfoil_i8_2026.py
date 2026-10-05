"""Butter Pollen I8 — dense fractured microfoil candidate; SPB-105 2026-08-27.

I3 was microscopic/botanical, I5 sparse giant shards, and I7 contour noodles.
I8 is a full-bleed automotive field of unequal butter-gold and charcoal foil
platelets with brush lamellae, torn release seams and selective optical lips.
It is deliberately fine and all-over, but the marks belong to clustered foil
currents rather than a noise or confetti layer.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID="fbl_butter_pollen"; NATIVE=2048
M=np.asarray((7,33,67,104,142,181,219,253),np.uint8)
R=np.asarray((5,30,61,99,140,179,220,251),np.uint8)
C=np.asarray((6,32,65,103,143,181,217,254),np.uint8)
def _norm(a): a=a.astype(np.float32); return (a-a.min())/(a.max()-a.min()+1e-8)
def _tier(a,v): return v[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)

@lru_cache(maxsize=2)
def _fields():
    asset=Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"butter_pollen_microfoil_i8.png"
    raw=cv2.imread(str(asset),cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(asset)
    rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
    hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32); sat=hsv[:,:,1]/255.
    lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
    gx=cv2.Sobel(lum,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(lum,cv2.CV_32F,0,1,ksize=3)
    seam=_norm(np.hypot(gx,gy)); brush=_norm(np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.0)))
    split=_norm(np.abs(.74*gx-.67*gy)); current=_norm(cv2.GaussianBlur(lum,(0,0),15)); heading=(np.arctan2(gy,gx)+np.pi)/(2*np.pi)
    gold=np.clip((1.12*rgb[:,:,0]+.62*rgb[:,:,1]-1.08*rgb[:,:,2]-.26)/.50,0,1)
    butter=np.clip((rgb[:,:,0]+.88*rgb[:,:,1]-.86*rgb[:,:,2]-.52)/.38,0,1)
    pearl=np.clip((lum-.38+.22*(1-sat))/.43,0,1); dark=np.clip((.34-lum)/.34,0,1)
    cyan=np.clip((rgb[:,:,2]+.48*rgb[:,:,1]-1.04*rgb[:,:,0]-.08)/.40,0,1)
    violet=np.clip((rgb[:,:,2]+.40*rgb[:,:,0]-1.16*rgb[:,:,1]-.10)/.40,0,1)
    return dict(rgb=rgb,seam=seam,brush=brush,split=split,current=current,heading=heading,gold=gold,butter=butter,pearl=pearl,dark=dark,cyan=cyan,violet=violet)

def _paint(angle_b=False):
    f=_fields(); a=np.clip(f['rgb']*.76+np.dstack((.15*f['gold']*f['seam']+.09*f['butter']*f['brush'],.12*f['butter']*f['seam']+.08*f['pearl']*f['brush'],.15*f['cyan']*f['seam']+.12*f['violet']*f['split']))-.05*f['dark'][:,:,None],0,1)
    if not angle_b:return a,f
    # The foil packets stay put; the reflected edge population changes view.
    b=a*.22+np.dstack((.38*f['gold']+.21*f['violet']+.12*f['pearl'],.27*f['butter']+.24*f['cyan']+.11*f['pearl'],.52*f['cyan']+.39*f['violet']+.10*f['seam']))+np.dstack((.03*f['split'],.04*f['brush'],.10*f['seam']))
    return np.clip(b,0,1),f

def _material(f):
    metal=_norm(.43*f['gold']+.28*f['butter']+.21*f['pearl']+.17*f['seam']+.10*f['violet'])
    direction=np.abs(np.sin(2*np.pi*(f['heading']+.27*f['current'])))
    rough=_norm(.48*f['brush']+.28*f['split']+.23*direction+.18*f['dark']-.17*f['seam'])
    # Polish follows the foil-current continuity, not gold chroma or cut density.
    clear=_norm(.43*f['current']+.32*_norm(cv2.GaussianBlur(f['seam'],(0,0),10))+.25*f['heading']-.13*f['brush'])
    return np.stack((_tier(metal,M),_tier(rough,R),_tier(clear,C)),2)

def _authored():a,f=_paint();return a,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(directory:Path):
    directory.mkdir(parents=True,exist_ok=True); timings=[]; hashes=[]; last=None
    for _ in range(3):
        clear_cache(); start=time.perf_counter(); a,f=_paint();b,_=_paint(True);s=_material(f);timings.append(time.perf_counter()-start);hashes.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
    a,b,s=last;delta=np.abs(a-b)
    for name,image in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))):cv2.imwrite(str(directory/f"{ID}_{name}_2048.png"),cv2.cvtColor(np.uint8(image*255),cv2.COLOR_RGB2BGR))
    for index,name in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(directory/f"{ID}_{name}_2048.png"),s[:,:,index])
    corr=np.corrcoef(s.reshape(-1,3).astype(np.float32),rowvar=False);report={"id":ID,"timings_s":timings,"deterministic":len(set(hashes))==1,"spec_std":[float(s[:,:,i].std()) for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],"spec_corr_m_r_cc":[float(corr[0,1]),float(corr[0,2]),float(corr[1,2])],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))};(directory/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf8");return report
if __name__=="__main__":print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"butter_pollen_microfoil_i8"),indent=2))
