# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Magenta Whorl I1, broken chiral fracture collars.

SPB-105 / owner Wilds rebuild, 2026-08-26. Candidate only: incomplete vortex
collars, shear arcs, black rupture cuts and fine crystalline splinters create
a livery-scale whorl, not marble, a full-card spiral, or random grain.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID="fbl_magenta_whorl";NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"magenta_whorl_i1.png"
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8;curl=np.abs(.70*gx-.71*gy);curl/=curl.max()+1e-8;splinter=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.1));splinter/=splinter.max()+1e-8
 field=cv2.GaussianBlur(lum,(0,0),13.0);field=(field-field.min())/(field.max()-field.min()+1e-8);dark=np.clip((.22-lum)/.22,0,1);magenta=np.clip((1.15*x[:,:,0]-.45*x[:,:,1]+.56*x[:,:,2]-.38)/.42,0,1);fuchsia=np.clip((1.06*x[:,:,0]-.55*x[:,:,1]+1.08*x[:,:,2]-.48)/.35,0,1);rose=np.clip((1.15*x[:,:,0]+.28*x[:,:,1]+.42*x[:,:,2]-.50)/.38,0,1);cyan=np.clip((-.54*x[:,:,0]+1.10*x[:,:,1]+1.18*x[:,:,2]-.62)/.33,0,1)
 return dict(x=x,sat=sat,rim=rim,curl=curl,splinter=splinter,field=field,dark=dark,magenta=magenta,fuchsia=fuchsia,rose=rose,cyan=cyan)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.56+np.dstack((.27*f['rose']*f['rim']+.14*f['magenta']*f['splinter'],.08*f['magenta']*f['curl']+.10*f['rose']*f['rim'],.25*f['fuchsia']*f['curl']+.13*f['cyan']*f['rim']))-.10*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.45+.55*np.clip(.39*f['field']+.33*f['sat']+.28*f['curl'],0,1);b=.006*a+np.dstack((.42+.50*f['rose']+.36*f['fuchsia'],.12+.37*f['magenta']+.25*f['rose'],.34+.58*f['fuchsia']+.29*f['cyan']))*p[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.31*f['magenta']+.27*f['fuchsia']+.18*f['rose']+.15*f['cyan']+.09*f['rim'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.36*f['dark']+.29*f['curl']+.21*f['splinter']+.14*f['rim'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.34*f['field']+.25*f['sat']+.19*f['fuchsia']+.13*f['magenta']+.09*f['rose'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];z=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);z.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;v=np.abs(a-b)
 for n,x in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(v*2,0,1))):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
 o={"id":ID,"timings_s":t,"deterministic":len(set(z))==1,"spec_std":[float(s[:,:,i].std())for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],"angle_delta_mean":float(v.mean()),"angle_delta_p95":float(np.quantile(v,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'magenta_whorl_asset_i1'),indent=2))
