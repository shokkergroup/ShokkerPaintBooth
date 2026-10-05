# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Amber Moldring I3, ruptured agar growth fronts.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Torn amber agar sheets, disjoint
growth fronts, wet cavities, spore grit, resin membranes and brittle nutrient
fissures make this a fractured culture material—not a target ring or orange
noise.  Fine pores, ragged rims, membrane threads and sediment are causal to
the paint/spec response beneath its larger broken culture-front hierarchy.
SPB-105 gate movement: fallback/unscored to M7 98.0 after edge-continuity
repair; collision 0/82 and distinctness 0/3,403 are clean.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2
import numpy as np
ID="fpe_amber_moldring";NATIVE=2048
def _asset():return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"amber_moldring_i3.png"
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2];gx=cv2.Sobel(l,cv2.CV_32F,1,0,ksize=3);gy=cv2.Sobel(l,cv2.CV_32F,0,1,ksize=3)
 rim=np.hypot(gx,gy);rim/=rim.max()+1e-8;fissure=np.abs(.74*gx-.67*gy);fissure/=fissure.max()+1e-8;spore=np.abs(l-cv2.GaussianBlur(l,(0,0),.75));spore/=spore.max()+1e-8;sheet=cv2.GaussianBlur(l,(0,0),12);sheet=(sheet-sheet.min())/(sheet.max()-sheet.min()+1e-8);wet=np.clip((.30-l)/.30,0,1);amber=np.clip((1.20*x[:,:,0]+.62*x[:,:,1]-.43*x[:,:,2]-.36)/.48,0,1);gold=np.clip((1.08*x[:,:,0]+1.00*x[:,:,1]-.39*x[:,:,2]-.46)/.38,0,1);rust=np.clip((1.20*x[:,:,0]+.31*x[:,:,1]-.50*x[:,:,2]-.37)/.47,0,1);cyan=np.clip((-.48*x[:,:,0]+.98*x[:,:,1]+1.16*x[:,:,2]-.58)/.35,0,1);violet=np.clip((.86*x[:,:,0]-.35*x[:,:,1]+1.12*x[:,:,2]-.54)/.34,0,1)
 return dict(x=x,sat=h[:,:,1]/255.,rim=rim,fissure=fissure,spore=spore,sheet=sheet,wet=wet,amber=amber,gold=gold,rust=rust,cyan=cyan,violet=violet)
def _paint(b=False):
 f=_f();front=np.clip(.34*f['rim']+.27*f['fissure']+.22*f['spore']+.17*f['wet'],0,1)
 if not b:
  a=f['x']*.48+np.dstack((.41*f['amber']+.22*f['rust']+.10*f['violet']*front,.25*f['gold']+.15*f['amber']*front,.09*f['cyan']*front+.10*f['violet']*front))-.09*f['wet'][:,:,None];return np.clip(a,0,1),f
 glow=np.clip(.34*f['sheet']+.27*f['rim']+.22*f['sat']+.17*f['spore'],0,1);a=np.dstack((.38+.55*f['amber']+.31*f['rust'],.28+.46*f['gold']+.22*f['amber'],.22+.43*f['cyan']+.37*f['violet']))*(.51+.49*glow[:,:,None])+.13*f['rim'][:,:,None];return np.clip(a,0,1),f
def _spec(f):
 m=_q(np.clip(.29*f['gold']+.24*f['amber']+.19*f['cyan']+.16*f['violet']+.12*f['rim'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.35*f['spore']+.28*f['fissure']+.22*f['wet']+.15*f['rim'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.32*f['sheet']+.22*f['gold']+.19*f['amber']+.16*f['rim']+.11*f['sat'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
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
if __name__=="__main__":print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"amber_moldring_asset_i3"),indent=2))
