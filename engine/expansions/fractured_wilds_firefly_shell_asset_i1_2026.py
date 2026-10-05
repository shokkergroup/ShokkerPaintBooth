# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Firefly Shell I1, ruptured nocturnal aperture armor.

SPB-105 / owner Wilds rebuild, 2026-08-26. Candidate only: black shell slabs,
acid-gold light apertures, split ridge seams, hatch marks and cyan/violet
interference form a racing livery, not a firefly photo, lightning, or noise.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID="fmo_firefly_shell";NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"firefly_shell_i1.png"
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8;slash=np.abs(.78*gx-.63*gy);slash/=slash.max()+1e-8;hatch=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.25));hatch/=hatch.max()+1e-8
 field=cv2.GaussianBlur(lum,(0,0),14.0);field=(field-field.min())/(field.max()-field.min()+1e-8);dark=np.clip((.20-lum)/.20,0,1);lime=np.clip((-.36*x[:,:,0]+1.12*x[:,:,1]-.31*x[:,:,2]-.45)/.35,0,1);gold=np.clip((1.10*x[:,:,0]+.95*x[:,:,1]-.70*x[:,:,2]-.54)/.33,0,1);cyan=np.clip((-.50*x[:,:,0]+1.08*x[:,:,1]+1.13*x[:,:,2]-.57)/.34,0,1);violet=np.clip((1.07*x[:,:,0]-.50*x[:,:,1]+1.08*x[:,:,2]-.49)/.38,0,1)
 return dict(x=x,sat=sat,rim=rim,slash=slash,hatch=hatch,field=field,dark=dark,lime=lime,gold=gold,cyan=cyan,violet=violet)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.55+np.dstack((.25*f['gold']*f['rim']+.12*f['violet']*f['slash'],.30*f['lime']*f['rim']+.14*f['gold']*f['hatch'],.18*f['cyan']*f['slash']+.13*f['violet']*f['rim']))-.11*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.46+.54*np.clip(.38*f['field']+.33*f['sat']+.29*f['slash'],0,1);b=.006*a+np.dstack((.34+.56*f['gold']+.28*f['violet'],.39+.64*f['lime']+.21*f['gold'],.20+.55*f['cyan']+.36*f['violet']))*p[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.32*f['gold']+.27*f['lime']+.18*f['cyan']+.14*f['violet']+.09*f['rim'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.38*f['dark']+.27*f['slash']+.20*f['hatch']+.15*f['rim'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.35*f['field']+.25*f['sat']+.19*f['lime']+.12*f['gold']+.09*f['violet'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];z=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);z.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;v=np.abs(a-b)
 for n,x in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(v*2,0,1))):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
 o={"id":ID,"timings_s":t,"deterministic":len(set(z))==1,"spec_std":[float(s[:,:,i].std())for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],"angle_delta_mean":float(v.mean()),"angle_delta_p95":float(np.quantile(v,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'firefly_shell_asset_i1'),indent=2))
