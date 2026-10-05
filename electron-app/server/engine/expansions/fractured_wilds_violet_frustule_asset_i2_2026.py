# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Violet Frustule I2, shattered silica microfauna.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This replaces the generic legacy
radial-disc lattice with a packed, asymmetric bed of perforated diatom valves,
silica needles, split skeletal rings, crystal wedges and fused dark seams.
Larger recognisable fragments are deliberately name-matched hierarchy; their
perforations, ribs, chips and mineral contacts retain the fine compressed read.
A/B and the material channels come from separate causal image fields.
Native 2048 evidence is 1.44-1.51 s, with A/B 0.117/0.255 mean/p95 and
M/R/Cc std 84.01/84.60/83.28. SPB-105 gate movement: fallback/unscored to
M7 85.8; collision and distinctness are recorded with the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np

ID='fpe_violet_frustule';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'violet_frustule_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=hsv[:,:,1]/255.;hue=hsv[:,:,0]/180.
 lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);edge=np.hypot(gx,gy);edge/=edge.max()+1e-8
 rib=np.abs(gx*.62+gy*.79);rib/=rib.max()+1e-8
 pore=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.18));pore/=pore.max()+1e-8
 plate=cv2.GaussianBlur(lum,(0,0),10.5);plate=(plate-plate.min())/(plate.max()-plate.min()+1e-8)
 dark=np.clip((.28-lum)/.28,0,1)
 violet=np.clip((1.08*rgb[:,:,0]-.26*rgb[:,:,1]+1.15*rgb[:,:,2]-.46)/.42,0,1)
 blue=np.clip((-.20*rgb[:,:,0]+.40*rgb[:,:,1]+1.22*rgb[:,:,2]-.42)/.48,0,1)
 cyan=np.clip((-.42*rgb[:,:,0]+1.10*rgb[:,:,1]+1.05*rgb[:,:,2]-.54)/.38,0,1)
 amber=np.clip((1.16*rgb[:,:,0]+.62*rgb[:,:,1]-.46*rgb[:,:,2]-.43)/.37,0,1)
 return dict(rgb=rgb,sat=sat,hue=hue,edge=edge,rib=rib,pore=pore,plate=plate,dark=dark,violet=violet,blue=blue,cyan=cyan,amber=amber)
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.54+np.dstack((.21*f['violet']*f['pore']+.13*f['amber']*f['edge'],.16*f['cyan']*f['pore']+.10*f['amber']*f['rib'],.28*f['blue']*f['pore']+.14*f['violet']*f['rib']))-.09*f['dark'][:,:,None],0,1)
 if not angle:return a,f
 phase=.34+.66*np.clip(.42*f['plate']+.31*f['pore']+.27*f['sat'],0,1)
 b=.025*a+np.dstack((.19+.43*f['violet']+.27*f['amber']+.16*f['edge'],.21+.54*f['cyan']+.19*f['amber']+.13*f['pore'],.34+.61*f['blue']+.29*f['violet']+.15*f['rib']))*phase[:,:,None]
 return np.clip(b,0,1),f
def _material(f):
 metal=_q(np.clip(.29*f['blue']+.25*f['cyan']+.22*f['violet']+.14*f['amber']+.10*f['pore'],0,1),(7,33,69,108,148,187,225,253))
 rough=_q(np.clip(.35*f['pore']+.29*f['rib']+.23*f['edge']+.13*f['dark'],0,1),(5,27,59,97,138,179,221,251))
 clearcoat=_q(np.clip(.30*f['plate']+.26*f['violet']+.20*f['blue']+.14*f['edge']+.10*f['sat'],0,1),(6,31,66,104,143,181,217,254))
 return np.stack((metal,rough,clearcoat),2)
def _authored():p,f=_paint(False);return p,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):
  clear_cache();q=time.perf_counter();a,f=_paint(False);b,_=_paint(True);s=_material(f);ts.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'violet_frustule_asset_i2'),indent=2))
