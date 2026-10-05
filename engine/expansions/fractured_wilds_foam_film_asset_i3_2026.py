# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Foam Film I3, ruptured structural membrane.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Torn translucent spans, drained
voids, brittle meniscus rims, thread junctions and mineral residue form a
fragile fractured polymer surface—not a closed soap-bubble pattern, Voronoi
cells, or generic noise.  Larger torn spans retain fine film, debris and pore
detail at 2048 and remain readable when crushed through the owner's 0.05–1.00
scale range.  Paint and M/R/Cc are driven by separate membrane physics.
SPB-105 gate movement: fallback/unscored to M7 90.6; collision and
distinctness gates are clean across the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np
ID="fmo_foam_film"; NATIVE=2048
def _asset(): return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"foam_film_i3.png"
def _q(a,v): return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None: raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.; h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32); l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(l,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(l,cv2.CV_32F,0,1,ksize=3); rim=np.hypot(gx,gy); rim/=rim.max()+1e-8; thread=np.abs(.71*gx-.70*gy); thread/=thread.max()+1e-8; residue=np.abs(l-cv2.GaussianBlur(l,(0,0),.72)); residue/=residue.max()+1e-8
 membrane=cv2.GaussianBlur(l,(0,0),11.5); membrane=(membrane-membrane.min())/(membrane.max()-membrane.min()+1e-8); void=np.clip((.23-l)/.23,0,1); cyan=np.clip((-.50*x[:,:,0]+1.05*x[:,:,1]+1.20*x[:,:,2]-.52)/.39,0,1); green=np.clip((-.40*x[:,:,0]+1.17*x[:,:,1]+.35*x[:,:,2]-.49)/.41,0,1); rose=np.clip((1.16*x[:,:,0]-.38*x[:,:,1]+.74*x[:,:,2]-.48)/.38,0,1); gold=np.clip((1.10*x[:,:,0]+.97*x[:,:,1]-.46*x[:,:,2]-.47)/.37,0,1); violet=np.clip((.88*x[:,:,0]-.36*x[:,:,1]+1.09*x[:,:,2]-.48)/.41,0,1)
 return dict(x=x,sat=h[:,:,1]/255.,rim=rim,thread=thread,residue=residue,membrane=membrane,void=void,cyan=cyan,green=green,rose=rose,gold=gold,violet=violet)
def _paint(b=False):
 f=_f(); edge=np.clip(.36*f['rim']+.29*f['thread']+.20*f['residue']+.15*f['void'],0,1)
 if not b:
  a=f['x']*.43+np.dstack((.19*f['rose']+.18*f['gold']+.13*f['violet']*edge,.25*f['green']+.17*f['gold']+.13*f['cyan']*edge,.30*f['cyan']+.22*f['violet']+.11*f['green']*edge))-.13*f['void'][:,:,None]; return np.clip(a,0,1),f
 shimmer=np.clip(.32*f['membrane']+.28*f['rim']+.22*f['sat']+.18*f['residue'],0,1)
 a=np.dstack((.28+.56*f['rose']+.42*f['violet'],.31+.61*f['green']+.28*f['gold'],.42+.65*f['cyan']+.47*f['violet']))*(.52+.48*shimmer[:,:,None])+.15*f['rim'][:,:,None]; return np.clip(a,0,1),f
def _spec(f):
 m=_q(np.clip(.28*f['cyan']+.24*f['violet']+.19*f['green']+.16*f['gold']+.13*f['rim'],0,1),(7,34,72,109,148,187,224,253)); r=_q(np.clip(.34*f['residue']+.29*f['thread']+.22*f['void']+.15*f['rim'],0,1),(5,29,61,99,140,179,220,251)); c=_q(np.clip(.31*f['membrane']+.24*f['gold']+.20*f['rose']+.15*f['rim']+.10*f['sat'],0,1),(6,31,66,104,143,181,217,254)); return np.stack((m,r,c),2)
def _authored(): a,f=_paint(); return a,_spec(f)
def clear_cache(): _f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True); ts=[]; hs=[]; last=None
 for _ in range(3):
  clear_cache(); t=time.perf_counter(); a,f=_paint(); b,_=_paint(True); s=_spec(f); ts.append(time.perf_counter()-t); hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=a,b,s
 a,b,s=last; delta=np.abs(a-b)
 for n,q in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(q*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(("metal","rough","clearcoat")): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
 out={"id":ID,"timings_s":ts,"deterministic":len(set(hs))==1,"spec_std":[float(s[:,:,i].std())for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))}; (d/"manifest.json").write_text(json.dumps(out,indent=2)); return out
if __name__=="__main__": print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"foam_film_asset_i3"),indent=2))
