# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Cassowary Quill I3, fractured keratin bristle field.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Crossing rigid quills, split
tips, transverse keratin striations, snapped ends, root collars and trapped
mineral grit form a sharp fibrous topology—not leaf feathers, fur, a weave or
carbon fiber.  Bundles give scale-down movement but resolve into dense fine
splinter/ridge/debris detail; all paint and specs are causal to those marks.
SPB-105 gate movement: fallback/unscored to M7 90.0; collision and
distinctness gates are clean across the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2
import numpy as np
ID="fmo_cassowary_quill"; NATIVE=2048
def _asset():return Path(__file__).resolve().parents[2]/"assets"/"generated"/"wilds"/"cassowary_quill_i3.png"
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2];gx=cv2.Sobel(l,cv2.CV_32F,1,0,ksize=3);gy=cv2.Sobel(l,cv2.CV_32F,0,1,ksize=3)
 ridge=np.hypot(gx,gy);ridge/=ridge.max()+1e-8;stri=np.abs(.77*gx+.64*gy);stri/=stri.max()+1e-8;splinter=np.abs(l-cv2.GaussianBlur(l,(0,0),.95));splinter/=splinter.max()+1e-8;bundle=cv2.GaussianBlur(l,(0,0),13.0);bundle=(bundle-bundle.min())/(bundle.max()-bundle.min()+1e-8);dark=np.clip((.25-l)/.25,0,1);copper=np.clip((1.18*x[:,:,0]+.54*x[:,:,1]-.43*x[:,:,2]-.39)/.45,0,1);teal=np.clip((-.45*x[:,:,0]+1.02*x[:,:,1]+1.16*x[:,:,2]-.52)/.41,0,1);blue=np.clip((.19*x[:,:,0]+.46*x[:,:,1]+1.14*x[:,:,2]-.48)/.41,0,1);violet=np.clip((.84*x[:,:,0]-.34*x[:,:,1]+1.11*x[:,:,2]-.49)/.41,0,1)
 return dict(x=x,sat=h[:,:,1]/255.,ridge=ridge,stri=stri,splinter=splinter,bundle=bundle,dark=dark,copper=copper,teal=teal,blue=blue,violet=violet)
def _paint(b=False):
 f=_f();wear=np.clip(.34*f['ridge']+.29*f['stri']+.22*f['splinter']+.15*f['copper'],0,1)
 if not b:
  a=f['x']*.48+np.dstack((.25*f['copper']+.13*f['violet']*wear,.12*f['copper']+.18*f['teal']*wear,.26*f['blue']*wear+.19*f['violet']*wear))-.10*f['dark'][:,:,None];return np.clip(a,0,1),f
 flash=np.clip(.35*f['bundle']+.29*f['ridge']+.21*f['sat']+.15*f['stri'],0,1);a=np.dstack((.20+.53*f['violet']+.31*f['copper'],.23+.58*f['teal']+.22*f['copper'],.36+.60*f['blue']+.43*f['violet']))*(.48+.52*flash[:,:,None])+.13*f['ridge'][:,:,None];return np.clip(a,0,1),f
def _spec(f):
 m=_q(np.clip(.30*f['blue']+.25*f['violet']+.19*f['teal']+.15*f['ridge']+.11*f['copper'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.35*f['splinter']+.30*f['stri']+.20*f['dark']+.15*f['ridge'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.31*f['bundle']+.24*f['copper']+.19*f['ridge']+.15*f['sat']+.11*f['blue'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
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
if __name__=="__main__":print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"cassowary_quill_asset_i3"),indent=2))
