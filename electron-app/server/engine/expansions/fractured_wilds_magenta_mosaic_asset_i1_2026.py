# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Magenta Mosaic I1, split lacquer livery collage.

SPB-105 / owner Wilds rebuild, 2026-08-26. Candidate only: unequal pigment
plaques, narrow charcoal cuts, foil shards, hatch scars and chip seams—not a
tile wall, repeated grid, generic crack map, or grain-driven recolor.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID="fpe_magenta_mosaic";NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"magenta_mosaic_i1.png"
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8;cut=np.abs(.84*gx+.54*gy);cut/=cut.max()+1e-8;hatch=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.5));hatch/=hatch.max()+1e-8
 field=cv2.GaussianBlur(lum,(0,0),15.0);field=(field-field.min())/(field.max()-field.min()+1e-8);dark=np.clip((.22-lum)/.22,0,1);magenta=np.clip((1.16*x[:,:,0]-.46*x[:,:,1]+.64*x[:,:,2]-.43)/.38,0,1);fuchsia=np.clip((1.05*x[:,:,0]-.57*x[:,:,1]+1.12*x[:,:,2]-.49)/.35,0,1);rose=np.clip((1.17*x[:,:,0]+.26*x[:,:,1]+.46*x[:,:,2]-.53)/.35,0,1);cyan=np.clip((-.53*x[:,:,0]+1.08*x[:,:,1]+1.16*x[:,:,2]-.60)/.34,0,1)
 return dict(x=x,sat=sat,rim=rim,cut=cut,hatch=hatch,field=field,dark=dark,magenta=magenta,fuchsia=fuchsia,rose=rose,cyan=cyan)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.57+np.dstack((.26*f['rose']*f['rim']+.12*f['magenta']*f['hatch'],.07*f['magenta']*f['cut']+.10*f['rose']*f['rim'],.25*f['fuchsia']*f['cut']+.13*f['cyan']*f['rim']))-.10*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.46+.54*np.clip(.37*f['field']+.34*f['sat']+.29*f['cut'],0,1);b=.006*a+np.dstack((.40+.54*f['rose']+.33*f['fuchsia'],.13+.35*f['magenta']+.26*f['rose'],.33+.60*f['fuchsia']+.28*f['cyan']))*p[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 # SPB-WILDS 2026-08-26: independent 10--18px misregistration tracks give
 # each material channel a different *fractured livery* cause, not grain.
 yy, xx = np.indices(f['field'].shape, np.float32)
 metal = .5 + .5*np.sin(.51*xx + .19*yy + 8.0*f['magenta'])
 rough = .5 + .5*np.sin(.17*xx - .63*yy + 9.0*f['cut'])
 gloss = .5 + .5*np.sin(.36*xx + .42*yy + 7.0*f['rose'])
 m=_q(np.clip(.40*(.32*f['magenta']+.26*f['fuchsia']+.18*f['rose']+.15*f['cyan']+.09*f['rim'])+.60*metal,0,1),(7,34,72,109,148,187,224,253))
 r=_q(np.clip(.40*(.37*f['dark']+.28*f['cut']+.20*f['hatch']+.15*f['rim'])+.60*rough,0,1),(5,29,61,99,140,179,220,251))
 c=_q(np.clip(.40*(.33*f['field']+.25*f['sat']+.20*f['fuchsia']+.13*f['magenta']+.09*f['rose'])+.60*gloss,0,1),(6,31,66,104,143,181,217,254))
 return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];z=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);z.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;v=np.abs(a-b)
 for n,x in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(v*2,0,1))):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
 o={"id":ID,"timings_s":t,"deterministic":len(set(z))==1,"spec_std":[float(s[:,:,i].std())for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],"angle_delta_mean":float(v.mean()),"angle_delta_p95":float(np.quantile(v,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'magenta_mosaic_asset_i1'),indent=2))
