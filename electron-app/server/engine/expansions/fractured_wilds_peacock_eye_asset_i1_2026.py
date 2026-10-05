# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Peacock Eye I1, interrupted ocellus velocity field.

SPB-105 / owner Wilds rebuild, 2026-08-26. Candidate only: fragmented ocelli,
diagonal filament wakes, splintered structural-color plates, copper pupils and
black fracture channels make a race-car livery rather than feather wallpaper.
No random noise is introduced; source-derived features drive paint and specs.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID="fmo_peacock_eye"; NATIVE=2048
def _q(a,v): return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"peacock_eye_i1.png"
@lru_cache(maxsize=2)
def _f():
    raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    x=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
    hsv=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32); sat=hsv[:,:,1]/255.; lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
    gx=cv2.Sobel(lum,cv2.CV_32F,1,0); gy=cv2.Sobel(lum,cv2.CV_32F,0,1); rim=np.hypot(gx,gy); rim/=rim.max()+1e-8
    barb=np.abs(.91*gx-.42*gy); barb/=barb.max()+1e-8; detail=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.35)); detail/=detail.max()+1e-8
    field=cv2.GaussianBlur(lum,(0,0),13.0); field=(field-field.min())/(field.max()-field.min()+1e-8); dark=np.clip((.25-lum)/.25,0,1)
    teal=np.clip((-.43*x[:,:,0]+1.11*x[:,:,1]+.91*x[:,:,2]-.47)/.39,0,1); blue=np.clip((-.34*x[:,:,0]+.32*x[:,:,1]+1.18*x[:,:,2]-.42)/.41,0,1)
    violet=np.clip((1.08*x[:,:,0]-.49*x[:,:,1]+1.05*x[:,:,2]-.52)/.35,0,1); copper=np.clip((1.14*x[:,:,0]+.73*x[:,:,1]-.63*x[:,:,2]-.47)/.37,0,1)
    return dict(x=x,sat=sat,rim=rim,barb=barb,detail=detail,field=field,dark=dark,teal=teal,blue=blue,violet=violet,copper=copper)
def _paint(b=False):
    f=_f(); a=np.clip(f['x']*.54+np.dstack((.14*f['copper']*f['rim']+.13*f['violet']*f['barb'],.22*f['teal']*f['rim']+.08*f['copper']*f['detail'],.24*f['blue']*f['barb']+.10*f['violet']*f['rim']))-.10*f['dark'][:,:,None],0,1)
    if not b:return a,f
    p=.38+.62*np.clip(.37*f['field']+.32*f['sat']+.31*f['barb'],0,1)
    b=.012*a+np.dstack((.12+.38*f['copper']+.43*f['violet'],.20+.60*f['teal']+.18*f['copper'],.30+.52*f['blue']+.29*f['violet']))*p[:,:,None]
    return np.clip(b,0,1),f
def _spec(f):
    m=_q(np.clip(.31*f['teal']+.25*f['blue']+.19*f['copper']+.16*f['violet']+.09*f['rim'],0,1),(7,34,72,109,148,187,224,253))
    r=_q(np.clip(.35*f['barb']+.26*f['dark']+.22*f['detail']+.17*f['rim'],0,1),(5,29,61,99,140,179,220,251))
    c=_q(np.clip(.34*f['field']+.24*f['sat']+.20*f['violet']+.13*f['teal']+.09*f['copper'],0,1),(6,31,66,104,143,181,217,254))
    return np.stack((m,r,c),2)
def _authored(): a,f=_paint(); return a,_spec(f)
def clear_cache(): _f.cache_clear()
def render_evidence(d:Path):
    d.mkdir(parents=True,exist_ok=True); timings=[]; hashes=[]; last=None
    for _ in range(3):
        clear_cache(); start=time.perf_counter(); a,f=_paint(); b,_=_paint(True); s=_spec(f); timings.append(time.perf_counter()-start); hashes.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=a,b,s
    a,b,s=last; delta=np.abs(a-b)
    for n,img in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
    for i,n in enumerate(("metal","rough","clearcoat")): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
    out={"id":ID,"timings_s":timings,"deterministic":len(set(hashes))==1,"spec_std":[float(s[:,:,i].std())for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))}; (d/'manifest.json').write_text(json.dumps(out,indent=2)); return out
if __name__=='__main__': print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'peacock_eye_asset_i1'),indent=2))
