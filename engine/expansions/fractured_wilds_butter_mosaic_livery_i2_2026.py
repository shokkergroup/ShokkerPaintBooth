"""Butter Mosaic I2 — fused mica-lacquer candidate; SPB-105 2026-08-27.

I1 is a disconnected confetti/rail scatter. I2 is continuous black lacquer
broken by unequal butter-gold mica plates, foil abrasion and fracture lips.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fbl_butter_mosaic"; NATIVE = 2048
M = np.asarray((7, 33, 67, 104, 142, 181, 219, 253), np.uint8)
R = np.asarray((5, 30, 61, 99, 140, 179, 220, 251), np.uint8)
C = np.asarray((6, 32, 65, 103, 143, 181, 217, 254), np.uint8)
def _norm(a): a=a.astype(np.float32); return (a-a.min())/(a.max()-a.min()+1e-8)
def _tier(a, v): return v[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)

@lru_cache(maxsize=2)
def _fields():
    asset=Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"butter_mosaic_livery_i2.png"; raw=cv2.imread(str(asset),cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(asset)
    rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.; hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32)
    lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]; gx=cv2.Sobel(lum,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(lum,cv2.CV_32F,0,1,ksize=3)
    lip=_norm(np.hypot(gx,gy)); brush=_norm(np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.1))); split=_norm(np.abs(.76*gx-.65*gy)); flow=_norm(cv2.GaussianBlur(lum,(0,0),16)); heading=(np.arctan2(gy,gx)+np.pi)/(2*np.pi)
    mag=np.clip((1.08*rgb[:,:,0]+.67*rgb[:,:,2]-1.18*rgb[:,:,1]-.13)/.43,0,1); wine=np.clip((1.04*rgb[:,:,0]-.57*rgb[:,:,1]-.42*rgb[:,:,2]-.05)/.42,0,1); violet=np.clip((rgb[:,:,2]+.35*rgb[:,:,0]-1.14*rgb[:,:,1]-.07)/.38,0,1); cyan=np.clip((rgb[:,:,2]+.48*rgb[:,:,1]-1.08*rgb[:,:,0]-.07)/.38,0,1); gold=np.clip((rgb[:,:,0]+.42*rgb[:,:,1]-1.12*rgb[:,:,2]-.11)/.42,0,1); pearl=np.clip((lum-.39+.19*(1-hsv[:,:,1]/255.))/.42,0,1)
    return dict(rgb=rgb,lip=lip,brush=brush,split=split,flow=flow,heading=heading,mag=mag,wine=wine,violet=violet,cyan=cyan,gold=gold,pearl=pearl)

def _paint(angle_b=False):
    f=_fields(); a=np.clip(f['rgb']*.80+np.dstack((.14*f['mag']*f['lip']+.07*f['gold']*f['split'],.06*f['cyan']*f['lip']+.06*f['gold']*f['brush'],.17*f['violet']*f['lip']+.13*f['cyan']*f['split'])),0,1)
    if not angle_b:return a,f
    # Fixed paint flow; only the exposed fractured foil travels between views.
    b=a*.24+np.dstack((.37*f['mag']+.20*f['gold']+.10*f['pearl'],.14*f['cyan']+.12*f['gold']+.10*f['pearl'],.53*f['violet']+.42*f['cyan']+.10*f['lip']))+np.dstack((.03*f['split'],.05*f['brush'],.12*f['lip']))
    return np.clip(b,0,1),f

def _material(f):
    metal=_norm(.42*f['mag']+.30*f['violet']+.25*f['gold']+.21*f['pearl']+.16*f['lip']); directional=np.abs(np.sin(2*np.pi*(f['heading']+.31*f['flow']))); rough=_norm(.51*f['brush']+.28*directional+.23*f['split']-.18*f['lip'])
    # SPB-105: clearcoat is the anisotropic polish *around* the chiral flow,
    # not a luminance/color copy of the magenta bands used for metalness.
    clear=_norm(.40*f['flow']+.35*_norm(cv2.GaussianBlur(f['lip'],(0,0),11))+.25*f['heading']-.12*f['brush'])
    return np.stack((_tier(metal,M),_tier(rough,R),_tier(clear,C)),2)
def _authored(): a,f=_paint(); return a,_material(f)
def clear_cache(): _fields.cache_clear()

def render_evidence(directory:Path):
    directory.mkdir(parents=True,exist_ok=True); timings=[]; hashes=[]; last=None
    for _ in range(3):
        clear_cache(); start=time.perf_counter(); a,f=_paint(); b,_=_paint(True); s=_material(f); timings.append(time.perf_counter()-start); hashes.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=a,b,s
    a,b,s=last; delta=np.abs(a-b)
    for name,image in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))):cv2.imwrite(str(directory/f"{ID}_{name}_2048.png"),cv2.cvtColor(np.uint8(image*255),cv2.COLOR_RGB2BGR))
    for index,name in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(directory/f"{ID}_{name}_2048.png"),s[:,:,index])
    corr=np.corrcoef(s.reshape(-1,3).astype(np.float32),rowvar=False); report={"id":ID,"timings_s":timings,"deterministic":len(set(hashes))==1,"spec_std":[float(s[:,:,i].std()) for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],"spec_corr_m_r_cc":[float(corr[0,1]),float(corr[0,2]),float(corr[1,2])],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))}; (directory/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf8"); return report
if __name__=="__main__":print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"butter_mosaic_livery_i2"),indent=2))
