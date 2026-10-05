# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Lime Chains I3, calcified tube-link colony.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Broken calcite tube chains, fused
collars, chalk crust, wet acid seams, cavities and granular carbonate dust
form this distinct microbial-mineral surface—not Lime Mold's dry crust, a
cell wallpaper or generic green noise.  Fine chips, pores and wet seams stay
causal across paint/spec at 2048 and beneath its reduced-scale chain hierarchy.
SPB-105 gate movement: fallback/unscored to M7 89.6; collision and
distinctness gates are clean across the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2
import numpy as np
ID="fpe_lime_chains";NATIVE=2048
def _asset():return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"lime_chains_i3.png"
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2];gx=cv2.Sobel(l,cv2.CV_32F,1,0,ksize=3);gy=cv2.Sobel(l,cv2.CV_32F,0,1,ksize=3)
 collar=np.hypot(gx,gy);collar/=collar.max()+1e-8;seam=np.abs(.68*gx+.73*gy);seam/=seam.max()+1e-8;grain=np.abs(l-cv2.GaussianBlur(l,(0,0),.82));grain/=grain.max()+1e-8;tube=cv2.GaussianBlur(l,(0,0),11);tube=(tube-tube.min())/(tube.max()-tube.min()+1e-8);cavity=np.clip((.27-l)/.27,0,1);lime=np.clip((-.28*x[:,:,0]+1.10*x[:,:,1]+.28*x[:,:,2]-.43)/.45,0,1);mint=np.clip((-.25*x[:,:,0]+.99*x[:,:,1]+.72*x[:,:,2]-.55)/.37,0,1);acid=np.clip((-.36*x[:,:,0]+1.21*x[:,:,1]-.10*x[:,:,2]-.47)/.38,0,1);gold=np.clip((1.08*x[:,:,0]+.95*x[:,:,1]-.42*x[:,:,2]-.49)/.35,0,1)
 return dict(x=x,sat=h[:,:,1]/255.,collar=collar,seam=seam,grain=grain,tube=tube,cavity=cavity,lime=lime,mint=mint,acid=acid,gold=gold)
def _paint(b=False):
 f=_f();fract=np.clip(.34*f['collar']+.28*f['seam']+.22*f['grain']+.16*f['cavity'],0,1)
 if not b:
  a=f['x']*.48+np.dstack((.14*f['gold']+.08*f['acid']*fract,.34*f['lime']+.16*f['acid']*fract,.21*f['mint']+.15*f['lime']*fract))-.10*f['cavity'][:,:,None];return np.clip(a,0,1),f
 glow=np.clip(.34*f['tube']+.27*f['collar']+.22*f['sat']+.17*f['seam'],0,1);a=np.dstack((.31+.35*f['gold']+.30*f['acid'],.48+.66*f['acid']+.36*f['lime'],.43+.57*f['mint']+.35*f['lime']))*(.55+.45*glow[:,:,None])+.15*f['collar'][:,:,None];return np.clip(a,0,1),f
def _spec(f):
 m=_q(np.clip(.31*f['mint']+.26*f['acid']+.19*f['lime']+.14*f['collar']+.10*f['gold'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.35*f['grain']+.28*f['seam']+.22*f['cavity']+.15*f['collar'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.32*f['tube']+.22*f['lime']+.19*f['gold']+.16*f['collar']+.11*f['sat'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
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
if __name__=="__main__":print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"lime_chains_asset_i3"),indent=2))
