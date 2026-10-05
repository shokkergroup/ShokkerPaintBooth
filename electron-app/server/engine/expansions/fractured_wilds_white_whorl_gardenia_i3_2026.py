"""Gardenia Whorl I3 — fractured pearl-petal lacquer; SPB-105 2026-08-27.

I2 is a chrome-ribbon field with giant empty forms.  I3 uses dense, unequal
gardenia-like folded lacquer currents: fine brush lamellae, torn release seams
and cyan/violet optical lips.  The material channels come from separate source
causes, rather than a shared scalar or injected grain.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fbl_white_whorl"; NATIVE = 2048
M = np.asarray((7, 33, 67, 104, 142, 181, 219, 253), np.uint8)
R = np.asarray((5, 30, 61, 99, 140, 179, 220, 251), np.uint8)
C = np.asarray((6, 32, 65, 103, 143, 181, 217, 254), np.uint8)
def _norm(a):
    a = a.astype(np.float32); return (a-a.min())/(a.max()-a.min()+1e-8)
def _tier(a, levels): return levels[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)

@lru_cache(maxsize=2)
def _fields():
    asset = Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "white_whorl_gardenia_i3.png"
    raw = cv2.imread(str(asset), cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(asset)
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32)/255.
    hsv = cv2.cvtColor(np.uint8(rgb*255), cv2.COLOR_RGB2HSV).astype(np.float32)
    lum = .2126*rgb[:,:,0] + .7152*rgb[:,:,1] + .0722*rgb[:,:,2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)
    lip = _norm(np.hypot(gx, gy)); lamella = _norm(np.abs(lum-cv2.GaussianBlur(lum, (0,0), 1.05)))
    split = _norm(np.abs(.71*gx-.70*gy)); field = _norm(cv2.GaussianBlur(lum, (0,0), 17))
    heading = (np.arctan2(gy, gx)+np.pi)/(2*np.pi)
    cream = np.clip((1.12*rgb[:,:,0]+1.03*rgb[:,:,1]-.78*rgb[:,:,2]-.62)/.43, 0, 1)
    pearl = np.clip((lum-.42+.27*(1-hsv[:,:,1]/255.))/.42, 0, 1)
    dark = np.clip((.31-lum)/.31, 0, 1)
    cyan = np.clip((rgb[:,:,2]+.50*rgb[:,:,1]-1.08*rgb[:,:,0]-.08)/.38, 0, 1)
    violet = np.clip((rgb[:,:,2]+.38*rgb[:,:,0]-1.15*rgb[:,:,1]-.10)/.38, 0, 1)
    gold = np.clip((rgb[:,:,0]+.40*rgb[:,:,1]-1.10*rgb[:,:,2]-.14)/.40, 0, 1)
    return dict(rgb=rgb, lip=lip, lamella=lamella, split=split, field=field, heading=heading, cream=cream, pearl=pearl, dark=dark, cyan=cyan, violet=violet, gold=gold)

def _paint(angle_b=False):
    f = _fields()
    a = np.clip(f['rgb']*.78 + np.dstack((.13*f['cream']*f['lip']+.08*f['gold']*f['split'], .10*f['pearl']*f['lamella']+.06*f['gold']*f['lip'], .16*f['cyan']*f['lip']+.13*f['violet']*f['split'])) - .06*f['dark'][:,:,None], 0, 1)
    if not angle_b: return a, f
    # Fixed folded topology; view B reassigns the exposed optical foil only.
    b = a*.23 + np.dstack((.25*f['pearl']+.22*f['violet']+.09*f['gold'], .31*f['cream']+.22*f['cyan']+.08*f['pearl'], .47*f['cyan']+.39*f['violet']+.10*f['lip'])) + np.dstack((.03*f['split'], .05*f['lamella'], .10*f['lip']))
    return np.clip(b, 0, 1), f

def _material(f):
    metal = _norm(.39*f['pearl']+.28*f['cream']+.22*f['gold']+.18*f['lip']+.11*f['violet'])
    direction = np.abs(np.sin(2*np.pi*(f['heading']+.29*f['field'])))
    rough = _norm(.48*f['lamella']+.29*f['split']+.23*direction+.16*f['dark']-.18*f['lip'])
    # Clear is an anisotropic polish current, explicitly not an inverse or copy
    # of the pearl/cream metal response (SPB-105 independent spec doctrine).
    clear = _norm(.43*f['field']+.31*_norm(cv2.GaussianBlur(f['lip'], (0,0), 11))+.26*f['heading']-.14*f['lamella'])
    return np.stack((_tier(metal,M), _tier(rough,R), _tier(clear,C)), 2)

def _authored(): a, f = _paint(); return a, _material(f)
def clear_cache(): _fields.cache_clear()
def render_evidence(directory: Path):
    directory.mkdir(parents=True, exist_ok=True); timings=[]; hashes=[]; last=None
    for _ in range(3):
        clear_cache(); start=time.perf_counter(); a,f=_paint(); b,_=_paint(True); s=_material(f); timings.append(time.perf_counter()-start); hashes.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=a,b,s
    a,b,s=last; delta=np.abs(a-b)
    for name,image in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))): cv2.imwrite(str(directory/f"{ID}_{name}_2048.png"), cv2.cvtColor(np.uint8(image*255),cv2.COLOR_RGB2BGR))
    for index,name in enumerate(("metal","rough","clearcoat")): cv2.imwrite(str(directory/f"{ID}_{name}_2048.png"),s[:,:,index])
    corr=np.corrcoef(s.reshape(-1,3).astype(np.float32),rowvar=False)
    report={"id":ID,"timings_s":timings,"deterministic":len(set(hashes))==1,"spec_std":[float(s[:,:,i].std()) for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],"spec_corr_m_r_cc":[float(corr[0,1]),float(corr[0,2]),float(corr[1,2])],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))}; (directory/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf8"); return report
if __name__ == "__main__": print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"white_whorl_gardenia_i3"),indent=2))
