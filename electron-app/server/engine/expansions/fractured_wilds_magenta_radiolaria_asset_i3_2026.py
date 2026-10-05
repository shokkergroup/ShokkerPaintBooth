# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Magenta Radiolaria I3, broken silica lace colony.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This replaces the rejected giant
repeated mesh with fractured radiolarian silica lace, perforated shell scraps,
broken needles, collapsed chambers, cultured magenta precipitate and nutrient
sediment.  Fine pores, rims and sediment persist at 2048; paint and M/R/Cc
derive from different microscopic structures, not a recolored Spineball cage.
SPB-105 gate movement: fallback/unscored to M7 91.2; collision and
distinctness gates are clean across the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2
import numpy as np
ID="fpe_magenta_radiolaria";NATIVE=2048
def _asset():return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"magenta_radiolaria_i3.png"
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2];gx=cv2.Sobel(l,cv2.CV_32F,1,0,ksize=3);gy=cv2.Sobel(l,cv2.CV_32F,0,1,ksize=3)
 rim=np.hypot(gx,gy);rim/=rim.max()+1e-8;needle=np.abs(.76*gx-.65*gy);needle/=needle.max()+1e-8;pore=np.abs(l-cv2.GaussianBlur(l,(0,0),1.05));pore/=pore.max()+1e-8;colony=cv2.GaussianBlur(l,(0,0),12);colony=(colony-colony.min())/(colony.max()-colony.min()+1e-8);sediment=np.clip((.31-l)/.31,0,1);mag=np.clip((1.11*x[:,:,0]-.35*x[:,:,1]+.84*x[:,:,2]-.43)/.45,0,1);pink=np.clip((1.21*x[:,:,0]-.28*x[:,:,1]+.60*x[:,:,2]-.50)/.37,0,1);violet=np.clip((.85*x[:,:,0]-.34*x[:,:,1]+1.12*x[:,:,2]-.45)/.43,0,1);cyan=np.clip((-.47*x[:,:,0]+.99*x[:,:,1]+1.17*x[:,:,2]-.56)/.36,0,1)
 return dict(x=x,sat=h[:,:,1]/255.,rim=rim,needle=needle,pore=pore,colony=colony,sediment=sediment,mag=mag,pink=pink,violet=violet,cyan=cyan)
def _paint(b=False):
 f=_f();lace=np.clip(.35*f['rim']+.28*f['needle']+.21*f['pore']+.16*f['sediment'],0,1)
 if not b:
  a=f['x']*.44+np.dstack((.39*f['mag']+.22*f['pink']+.12*f['violet']*lace,.12*f['pink']+.15*f['cyan']*lace,.29*f['violet']+.18*f['cyan']*lace))-.09*f['sediment'][:,:,None];return np.clip(a,0,1),f
 flash=np.clip(.33*f['colony']+.28*f['rim']+.23*f['sat']+.16*f['pore'],0,1);a=np.dstack((.37+.65*f['mag']+.39*f['pink'],.26+.37*f['pink']+.31*f['cyan'],.50+.66*f['violet']+.46*f['cyan']))*(.53+.47*flash[:,:,None])+.14*f['rim'][:,:,None];return np.clip(a,0,1),f
def _spec(f):
 m=_q(np.clip(.31*f['violet']+.27*f['cyan']+.20*f['mag']+.13*f['rim']+.09*f['needle'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.35*f['pore']+.28*f['needle']+.22*f['sediment']+.15*f['rim'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.31*f['colony']+.23*f['pink']+.19*f['mag']+.16*f['rim']+.11*f['sat'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):
  clear_cache();t=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);ts.append(time.perf_counter()-t);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,q in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(q*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
 out={"id":ID,"timings_s":ts,"deterministic":len(set(hs))==1,"spec_std":[float(s[:,:,i].std())for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))};(d/"manifest.json").write_text(json.dumps(out,indent=2));return out
if __name__=="__main__":print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"magenta_radiolaria_asset_i3"),indent=2))
