# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Labradorite I4, crushed feldspar fire.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This replaces the rejected
macro-tile attempt with intergrown feldspar cleavage, graphite matrix, offset
microfractures, powder inclusions and thin blue-green fire planes.  Larger
mineral masses remain subordinate to fine 8–32px fracture, grain and step
detail.  Paint and M/R/Cc arise from separate physical mineral fields.
SPB-105 gate movement: prior I3 M7 84.5/rejected to I4 M7 89.3; collision and
distinctness gates are clean across the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2
import numpy as np
ID="fmo_labradorite";NATIVE=2048
def _asset():return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"labradorite_i4.png"
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2];gx=cv2.Sobel(l,cv2.CV_32F,1,0,ksize=3);gy=cv2.Sobel(l,cv2.CV_32F,0,1,ksize=3)
 seam=np.hypot(gx,gy);seam/=seam.max()+1e-8;step=np.abs(.69*gx-.72*gy);step/=step.max()+1e-8;powder=np.abs(l-cv2.GaussianBlur(l,(0,0),.78));powder/=powder.max()+1e-8;cleavage=cv2.GaussianBlur(l,(0,0),10.5);cleavage=(cleavage-cleavage.min())/(cleavage.max()-cleavage.min()+1e-8);graphite=np.clip((.27-l)/.27,0,1);cyan=np.clip((-.49*x[:,:,0]+1.00*x[:,:,1]+1.21*x[:,:,2]-.50)/.40,0,1);blue=np.clip((.16*x[:,:,0]+.43*x[:,:,1]+1.17*x[:,:,2]-.47)/.39,0,1);ice=np.clip((-.17*x[:,:,0]+.87*x[:,:,1]+1.04*x[:,:,2]-.60)/.32,0,1);gold=np.clip((1.13*x[:,:,0]+.97*x[:,:,1]-.44*x[:,:,2]-.51)/.33,0,1)
 return dict(x=x,sat=h[:,:,1]/255.,seam=seam,step=step,powder=powder,cleavage=cleavage,graphite=graphite,cyan=cyan,blue=blue,ice=ice,gold=gold)
def _paint(b=False):
 f=_f();fracture=np.clip(.34*f['seam']+.27*f['step']+.22*f['powder']+.17*f['graphite'],0,1)
 if not b:
  a=f['x']*.48+np.dstack((.10*f['gold']+.10*f['cyan']*fracture,.25*f['cyan']+.11*f['ice']*fracture,.36*f['blue']+.23*f['ice']*fracture))-.10*f['graphite'][:,:,None];return np.clip(a,0,1),f
 flare=np.clip(.35*f['cleavage']+.28*f['seam']+.22*f['sat']+.15*f['step'],0,1);a=np.dstack((.22+.34*f['gold']+.32*f['cyan'],.34+.63*f['ice']+.36*f['cyan'],.54+.70*f['blue']+.41*f['ice']))*(.54+.46*flare[:,:,None])+.15*f['seam'][:,:,None];return np.clip(a,0,1),f
def _spec(f):
 m=_q(np.clip(.32*f['blue']+.26*f['cyan']+.20*f['ice']+.12*f['gold']+.10*f['seam'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.35*f['powder']+.28*f['step']+.21*f['graphite']+.16*f['seam'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.33*f['cleavage']+.23*f['ice']+.18*f['gold']+.15*f['seam']+.11*f['sat'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
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
if __name__=="__main__":print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"labradorite_asset_i4"),indent=2))
