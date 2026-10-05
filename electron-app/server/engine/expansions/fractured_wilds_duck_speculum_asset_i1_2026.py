# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Duck Speculum I1, structural-color flight-barb livery.

SPB-105 / owner Wilds rebuild, 2026-08-26. The source is an intentionally
nonliteral racing-livery composition: overlapping asymmetric lacquer barbs,
engraved vane rows, black split seams, cobalt/teal/violet/copper flashes and
fine foil splinters. It is not a bird illustration, repeating feather stamp,
generic carbon fibre, gradient carrier, or grain-driven texture.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fmo_duck_speculum"; NATIVE = 2048
def _q(a,v): return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"duck_speculum_i1.png"

@lru_cache(maxsize=2)
def _f():
    raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    x=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
    hsv=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32); sat=hsv[:,:,1]/255.; lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
    gx=cv2.Sobel(lum,cv2.CV_32F,1,0); gy=cv2.Sobel(lum,cv2.CV_32F,0,1); rim=np.hypot(gx,gy);rim/=rim.max()+1e-8
    barb=np.abs(.74*gx-.67*gy);barb/=barb.max()+1e-8
    engrave=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.2));engrave/=engrave.max()+1e-8
    field=cv2.GaussianBlur(lum,(0,0),18);field=(field-field.min())/(field.max()-field.min()+1e-8)
    dark=np.clip((.18-lum)/.18,0,1)
    blue=np.clip((-.32*x[:,:,0]+.49*x[:,:,1]+1.22*x[:,:,2]-.50)/.38,0,1)
    teal=np.clip((-.59*x[:,:,0]+1.12*x[:,:,1]+1.13*x[:,:,2]-.58)/.35,0,1)
    violet=np.clip((1.02*x[:,:,0]-.48*x[:,:,1]+1.10*x[:,:,2]-.50)/.36,0,1)
    copper=np.clip((1.18*x[:,:,0]+.47*x[:,:,1]-.39*x[:,:,2]-.50)/.36,0,1)
    return dict(x=x,sat=sat,rim=rim,barb=barb,engrave=engrave,field=field,dark=dark,blue=blue,teal=teal,violet=violet,copper=copper)

def _paint(b=False):
    f=_f(); a=np.clip(f['x']*.57+np.dstack((.14*f['violet']*f['barb']+.20*f['copper']*f['rim'],.17*f['teal']*f['rim']+.08*f['copper']*f['engrave'],.27*f['blue']*f['barb']+.16*f['teal']*f['rim']))-.11*f['dark'][:,:,None],0,1)
    if not b:return a,f
    phase=.39+.61*np.clip(.34*f['field']+.28*f['sat']+.23*f['barb']+.15*f['engrave'],0,1)
    b=.012*a+np.dstack((.17+.45*f['violet']+.46*f['copper'],.24+.48*f['teal']+.30*f['copper'],.38+.52*f['blue']+.33*f['teal']))*phase[:,:,None]
    return np.clip(b,0,1),f
def _spec(f):
    m=_q(np.clip(.27*f['blue']+.24*f['teal']+.20*f['violet']+.18*f['copper']+.11*f['engrave'],0,1),(7,34,72,109,148,187,224,253))
    r=_q(np.clip(.34*f['dark']+.28*f['barb']+.22*f['rim']+.16*f['engrave'],0,1),(5,29,61,99,140,179,220,251))
    c=_q(np.clip(.31*f['field']+.24*f['sat']+.20*f['blue']+.15*f['teal']+.10*f['rim'],0,1),(6,31,66,104,143,181,217,254))
    return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
    d.mkdir(parents=True,exist_ok=True);t=[];hs=[];last=None
    for _ in range(3):
        clear_cache();start=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-start);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
    a,b,s=last;delta=np.abs(a-b)
    for n,img in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
    for i,n in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
    out={"id":ID,"timings_s":t,"deterministic":len(set(hs))==1,"spec_std":[float(s[:,:,i].std())for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(out,indent=2));return out
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'duck_speculum_asset_i1'),indent=2))
