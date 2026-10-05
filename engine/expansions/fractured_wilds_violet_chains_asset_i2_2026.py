# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Violet Chains I2, broken iridescent micro-links.

SPB-105 / owner Wilds rebuild, 2026-08-26. Irregular broken bead-and-filament
chains, glassy micro-links, small bridge fragments and dark substrate grain are
causal source marks—not a cell lattice, paver or generic noise. A/B changes
violet/rose versus blue/copper link constituents; M/R/Cc remain distinct.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fpe_violet_chains';NATIVE=2048
M_T=np.asarray((8,30,54,86,123,162,206,250),np.uint8);R_T=np.asarray((12,38,66,101,140,180,219,248),np.uint8);C_T=np.asarray((5,27,55,85,121,160,208,252),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'violet_chains_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 glint=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.0));glint/=glint.max()+1e-8
 flow=cv2.GaussianBlur(lum,(0,0),14.0);flow=(flow-flow.min())/(flow.max()-flow.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);stress=np.hypot(gx,gy);stress/=stress.max()+1e-8
 blue=np.clip((rgb[:,:,2]-.47*rgb[:,:,0]+.05)/.34,0,1)
 violet=np.clip((rgb[:,:,2]+.38*rgb[:,:,0]-1.02*rgb[:,:,1]+.05)/.31,0,1)
 rose=np.clip((rgb[:,:,0]-.68*rgb[:,:,1]+.05)/.31,0,1)
 copper=np.clip((rgb[:,:,0]+.29*rgb[:,:,1]-.82*rgb[:,:,2]+.04)/.32,0,1)
 return {'rgb':rgb,'glint':glint,'flow':flow,'stress':stress,'blue':blue,'violet':violet,'rose':rose,'copper':copper}
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']+np.dstack((.13*f['rose']*f['glint'],.05*f['violet']*f['glint'],.15*f['blue']*f['glint'])),0,1)
 if not angle:return a,f
 b=a*.22+np.dstack((.42*f['rose']+.25*f['copper']+.06*f['stress'],.25*f['violet']+.05*f['glint'],.42*f['blue']+.10*f['glint']))
 return np.clip(b,0,1),f
def _material(f):
 # Copper link glint, slower dark-substrate roughness and cool blue/violet
 # clearcoat use separated causal source fields.
 m=.57*f['copper']+.31*f['rose']+.12*f['glint']
 r=.76*f['flow']+.24*f['stress']
 c=.61*f['blue']+.39*f['violet']
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'violet_chains_asset_i2'),indent=2))
