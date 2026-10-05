# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Chalcopyrite I2, brassy fractured sulfide.

SPB-105 / owner Wilds rebuild, 2026-08-26. Fine sulfide cleavages, granular
brass facets, black mineral joins and cyan/magenta tarnish are source-owned
causal marks—not a paver, scale or generic recolour. A/B changes which ore
constituent owns reflection; M/R/Cc retain separate physical ownership.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_chalcopyrite';NATIVE=2048
M_T=np.asarray((8,30,54,86,123,162,206,250),np.uint8);R_T=np.asarray((12,38,66,101,140,180,219,248),np.uint8);C_T=np.asarray((5,27,55,85,121,160,208,252),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'chalcopyrite_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 grain=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.0));grain/=grain.max()+1e-8
 bed=cv2.GaussianBlur(lum,(0,0),10.0);bed=(bed-bed.min())/(bed.max()-bed.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);cleavage=np.hypot(gx,gy);cleavage/=cleavage.max()+1e-8
 brass=np.clip((rgb[:,:,0]+.55*rgb[:,:,1]-1.08*rgb[:,:,2]+.08)/.42,0,1)
 cyan=np.clip((rgb[:,:,2]-.54*rgb[:,:,0]+.06)/.34,0,1)
 magenta=np.clip((rgb[:,:,0]+.42*rgb[:,:,2]-1.08*rgb[:,:,1]+.05)/.30,0,1)
 shadow=np.clip((.38-lum)/.35,0,1)
 return {'rgb':rgb,'grain':grain,'bed':bed,'cleavage':cleavage,'brass':brass,'cyan':cyan,'magenta':magenta,'shadow':shadow}
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']+np.dstack((.15*f['brass']*f['grain'],.08*f['magenta']*f['grain'],.13*f['cyan']*f['grain'])),0,1)
 if not angle:return a,f
 b=a*.22+np.dstack((.56*f['brass']+.08*f['cleavage'],.13*f['magenta']+.05*f['grain'],.39*f['cyan']+.09*f['cleavage']))
 return np.clip(b,0,1),f
def _material(f):
 # Brass facet reflectance, dark sulfide bedding, and cyan/magenta tarnish
 # remain intentionally separate material fields, avoiding shared spec maps.
 m=.69*f['brass']+.21*f['grain']+.10*f['cleavage']
 r=.67*f['bed']+.21*f['shadow']+.12*f['cleavage']
 c=.57*f['cyan']+.43*f['magenta']
 return np.stack((_tier(m,M_T),_tier(r,R_T),_tier(c,C_T)),2)
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'chalcopyrite_asset_i2'),indent=2))
