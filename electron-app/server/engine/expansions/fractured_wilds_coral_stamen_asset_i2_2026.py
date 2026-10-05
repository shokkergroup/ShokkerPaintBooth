# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Coral Stamen I2, fractured anther filament field.

SPB-105 / owner Wilds rebuild, 2026-08-26. Fine branching stamen filaments,
bead-tip anthers, micro-pollen clusters and dark substrate fractures are causal
source marks—not pavers, cells or generic noise. A/B changes coral/amber versus
plum/cyan constituents; M/R/Cc remain distinct physical responses.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fbl_coral_stamen';NATIVE=2048
M_T=np.asarray((8,30,54,86,123,162,206,250),np.uint8);R_T=np.asarray((12,38,66,101,140,180,219,248),np.uint8);C_T=np.asarray((5,27,55,85,121,160,208,252),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'coral_stamen_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 pollen=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.0));pollen/=pollen.max()+1e-8
 substrate=cv2.GaussianBlur(lum,(0,0),12.0);substrate=(substrate-substrate.min())/(substrate.max()-substrate.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);filament=np.hypot(gx,gy);filament/=filament.max()+1e-8
 coral=np.clip((rgb[:,:,0]+.26*rgb[:,:,1]-1.04*rgb[:,:,2]+.05)/.34,0,1)
 amber=np.clip((rgb[:,:,0]+.48*rgb[:,:,1]-1.18*rgb[:,:,2]+.05)/.38,0,1)
 plum=np.clip((rgb[:,:,0]+.42*rgb[:,:,2]-1.10*rgb[:,:,1]+.05)/.32,0,1)
 cyan=np.clip((rgb[:,:,2]-.48*rgb[:,:,0]+.05)/.33,0,1)
 return {'rgb':rgb,'pollen':pollen,'substrate':substrate,'filament':filament,'coral':coral,'amber':amber,'plum':plum,'cyan':cyan}
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']+np.dstack((.17*f['coral']*f['pollen'],.10*f['amber']*f['pollen'],.05*f['plum']*f['pollen'])),0,1)
 if not angle:return a,f
 b=a*.23+np.dstack((.46*f['coral']+.17*f['amber']+.08*f['filament'],.17*f['amber']+.05*f['pollen'],.30*f['plum']+.23*f['cyan']+.06*f['filament']))
 return np.clip(b,0,1),f
def _material(f):
 # Anther/pollen metal, deep substrate roughness and cool plum/cyan clearcoat
 # each have independent causal fields rather than a copied organic spec map.
 m=.58*f['amber']+.29*f['coral']+.13*f['pollen']
 r=.76*f['substrate']+.24*f['filament']
 c=.58*f['plum']+.42*f['cyan']
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'coral_stamen_asset_i2'),indent=2))
