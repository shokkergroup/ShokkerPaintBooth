# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Lilac Rose I1, nonrepeating phase-flora fracture field.

SPB-105 / owner Wilds rebuild, 2026-08-26. Candidate only. This uses the
project's hyperflora 5/7-fold beat field and phase-reliquary singularities as
causal structure: broken lilac florets, phase collars, dark cut channels and
fine rose-gold/cyan mineral events. It is not noise, a radial stamp grid, or
image-derived floral wallpaper.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
from engine.paint_v2.fractured_math import hyperflora,phase_reliquary
ID="fbl_lilac_rose";NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
@lru_cache(maxsize=2)
def _f():
 flower=hyperflora(NATIVE,NATIVE,8129,res=760); phase=phase_reliquary(NATIVE,NATIVE,8137,res=448,waves=90)
 flower=(flower-flower.min())/(flower.max()-flower.min()+1e-8); phase=(phase-phase.min())/(phase.max()-phase.min()+1e-8)
 blur=cv2.GaussianBlur(flower,(0,0),10.5); petals=np.clip((flower-.47)/.26,0,1); collar=np.clip((phase-.38)/.42,0,1); cuts=np.clip((.42-flower)/.42,0,1); fine=np.abs(flower-cv2.GaussianBlur(flower,(0,0),1.1));fine/=fine.max()+1e-8
 gx=cv2.Sobel(flower,cv2.CV_32F,1,0);gy=cv2.Sobel(flower,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8
 return dict(flower=flower,phase=phase,blur=blur,petals=petals,collar=collar,cuts=cuts,fine=fine,rim=rim)
def _paint(b=False):
 f=_f();base=np.dstack((.12+.25*f['blur']+.34*f['petals'],.045+.11*f['flower']+.10*f['collar'],.15+.31*f['phase']+.35*f['petals']))
 a=np.clip(base+np.dstack((.17*f['collar']*f['rim'],.07*f['petals']*f['fine'],.16*f['collar']*f['fine']))-.12*f['cuts'][:,:,None],0,1)
 if not b:return a,f
 b=np.dstack((.34+.52*f['petals']+.21*f['collar'],.08+.30*f['flower']+.23*f['fine'],.38+.50*f['collar']+.26*f['petals']))*(.42+.58*np.clip(.45*f['phase']+.32*f['rim']+.23*f['fine'],0,1))[:,:,None]
 return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.31*f['petals']+.27*f['collar']+.20*f['rim']+.13*f['fine']+.09*f['phase'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.36*f['cuts']+.28*f['fine']+.22*f['rim']+.14*f['flower'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.34*f['phase']+.25*f['blur']+.19*f['petals']+.13*f['collar']+.09*f['rim'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];z=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);z.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;v=np.abs(a-b)
 for n,x in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(v*2,0,1))):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
 o={"id":ID,"timings_s":t,"deterministic":len(set(z))==1,"spec_std":[float(s[:,:,i].std())for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],"angle_delta_mean":float(v.mean()),"angle_delta_p95":float(np.quantile(v,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'lilac_rose_math_i1'),indent=2))
