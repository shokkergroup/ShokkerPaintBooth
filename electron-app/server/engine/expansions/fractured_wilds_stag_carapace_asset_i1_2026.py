# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Stag Carapace I1, split armor impact field.

SPB-105 / owner Wilds rebuild, 2026-08-26. Candidate only: unequal chitin
shields, crescent bite fractures, horn-ridge splits, copper abrasion and dark
impact cavities form an automotive armor livery, not scales, a generic crack
map, or literal beetle art. Every paint/spec field is source-derived.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID="fmo_stag_carapace";NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"stag_carapace_i1.png"
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8;shear=np.abs(.62*gx+.79*gy);shear/=shear.max()+1e-8;wear=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.4));wear/=wear.max()+1e-8
 field=cv2.GaussianBlur(lum,(0,0),15.0);field=(field-field.min())/(field.max()-field.min()+1e-8);dark=np.clip((.22-lum)/.22,0,1);oxblood=np.clip((1.07*x[:,:,0]-.38*x[:,:,1]-.25*x[:,:,2]-.26)/.42,0,1);copper=np.clip((1.10*x[:,:,0]+.73*x[:,:,1]-.60*x[:,:,2]-.47)/.36,0,1);emerald=np.clip((-.49*x[:,:,0]+1.10*x[:,:,1]+.72*x[:,:,2]-.48)/.33,0,1);violet=np.clip((1.03*x[:,:,0]-.52*x[:,:,1]+1.11*x[:,:,2]-.48)/.37,0,1)
 return dict(x=x,sat=sat,rim=rim,shear=shear,wear=wear,field=field,dark=dark,oxblood=oxblood,copper=copper,emerald=emerald,violet=violet)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.56+np.dstack((.22*f['oxblood']*f['rim']+.14*f['copper']*f['wear'],.16*f['copper']*f['rim']+.12*f['emerald']*f['shear'],.16*f['violet']*f['shear']+.11*f['emerald']*f['rim']))-.09*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.45+.55*np.clip(.39*f['field']+.33*f['sat']+.28*f['shear'],0,1);b=.006*a+np.dstack((.31+.62*f['oxblood']+.31*f['violet'],.24+.61*f['copper']+.42*f['emerald'],.22+.57*f['violet']+.39*f['emerald']))*p[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.31*f['copper']+.27*f['oxblood']+.18*f['emerald']+.15*f['violet']+.09*f['rim'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.37*f['dark']+.28*f['shear']+.21*f['wear']+.14*f['rim'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.34*f['field']+.24*f['sat']+.21*f['copper']+.13*f['oxblood']+.08*f['violet'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];z=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);z.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;v=np.abs(a-b)
 for n,x in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(v*2,0,1))):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
 o={"id":ID,"timings_s":t,"deterministic":len(set(z))==1,"spec_std":[float(s[:,:,i].std())for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],"angle_delta_mean":float(v.mean()),"angle_delta_p95":float(np.quantile(v,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'stag_carapace_asset_i1'),indent=2))
