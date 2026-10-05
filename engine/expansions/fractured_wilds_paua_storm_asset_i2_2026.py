# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Paua Storm I2, interwoven nacre current.

SPB-105 / owner Wilds rebuild, 2026-08-26. The source is a densely interwoven
field of broken nacre filaments, tiny aragonite splinters and hairline storm
joins. It is deliberately neither a scale/paver field nor random noise. A/B
changes the nacre constituent that owns reflection; M/R/Cc are distinct
physical responses rather than a duplicated spec map.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_paua_storm';NATIVE=2048
M_T=np.asarray((8,30,54,86,123,162,206,250),np.uint8);R_T=np.asarray((12,38,66,101,140,180,219,248),np.uint8);C_T=np.asarray((5,27,55,85,121,160,208,252),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'paua_storm_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 micro=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.1));micro/=micro.max()+1e-8
 current=cv2.GaussianBlur(lum,(0,0),12.0);current=(current-current.min())/(current.max()-current.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);join=np.hypot(gx,gy);join/=join.max()+1e-8
 # The chroma-separated source constituents preserve the supplied fine
 # nacre marks, while their differing combinations provide genuine A/B flip.
 teal=np.clip((rgb[:,:,2]-.58*rgb[:,:,0]+.05)/.34,0,1)
 rose=np.clip((rgb[:,:,0]-.72*rgb[:,:,1]+.04)/.30,0,1)
 violet=np.clip((rgb[:,:,2]+.50*rgb[:,:,0]-1.15*rgb[:,:,1]+.06)/.31,0,1)
 copper=np.clip((rgb[:,:,0]+.22*rgb[:,:,1]-.70*rgb[:,:,2]+.05)/.30,0,1)
 return {'rgb':rgb,'micro':micro,'current':current,'join':join,'teal':teal,'rose':rose,'violet':violet,'copper':copper}
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']+np.dstack((.14*f['rose']*f['micro'],.04*f['violet']*f['micro'],.18*f['teal']*f['micro'])),0,1)
 if not angle:return a,f
 b=a*.24+np.dstack((.34*f['rose']+.25*f['copper']+.06*f['join'],.20*f['violet']+.05*f['micro'],.51*f['teal']+.12*f['micro']))
 return np.clip(b,0,1),f
def _material(f):
 # Copper/rose filament metal, slow nacre-current roughness and the cool
 # teal/violet clearcoat bloom each come from a distinct causal source field.
 m=.61*f['copper']+.29*f['rose']+.10*f['micro']
 r=.79*f['current']+.21*f['join']
 c=.63*f['teal']+.37*f['violet']
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'paua_storm_asset_i2'),indent=2))
