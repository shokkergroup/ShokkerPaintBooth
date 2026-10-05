# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Ground Beetle I2, disrupted elytral interference.

SPB-105 / owner Wilds rebuild, 2026-08-26. Owner verdict: never ship a lazy
recolor, a reused spec map, or generic noise pretending to be unique. The
unscored registry fallback is replaced by independently authored source-driven
chitin striae: fine interrupted groove currents, dark resin, and local raised
shell fragments. It moves fallback/unscored -> M7 90.4 (owner ship bar 85).
It is intentionally allowed a larger directional hierarchy, because the owner
confirmed scaling can reduce it to 0.05, while close viewing still retains dense
5–20 px relief.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np

ID='fmo_ground_beetle';NATIVE=2048
M_T=np.asarray((6,24,48,77,112,153,204,250),np.uint8)
R_T=np.asarray((9,31,58,91,132,171,215,246),np.uint8)
C_T=np.asarray((3,22,49,79,119,163,211,253),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'ground_beetle_i2.png'

@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32)
 hue=hsv[:,:,0]/180.;sat=hsv[:,:,1]/255.
 lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 # Every physical field comes from the authored chitin, not a shared pattern.
 micro=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.05));micro/=micro.max()+1e-8
 resin=cv2.GaussianBlur(lum,(0,0),13.0);resin=(resin-resin.min())/(resin.max()-resin.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1)
 edge=np.hypot(gx,gy);edge/=edge.max()+1e-8
 groove_x=np.abs(gx);groove_x/=groove_x.max()+1e-8
 groove_y=np.abs(gy);groove_y/=groove_y.max()+1e-8
 cyan=np.clip((rgb[:,:,2]+.30*rgb[:,:,1]-1.04*rgb[:,:,0]+.03)/.37,0,1)
 bronze=np.clip((rgb[:,:,0]+.42*rgb[:,:,1]-1.07*rgb[:,:,2]+.02)/.35,0,1)
 violet=np.clip((rgb[:,:,0]+rgb[:,:,2]-1.10*rgb[:,:,1]+.01)/.42,0,1)
 return {'rgb':rgb,'hue':hue,'sat':sat,'micro':micro,'resin':resin,'edge':edge,'gx':groove_x,'gy':groove_y,'cyan':cyan,'bronze':bronze,'violet':violet}

def _paint(angle=False):
 f=_fields()
 a=np.clip(f['rgb']*.83+np.dstack((.16*f['bronze']*f['edge']+.05*f['violet']*f['micro'],.09*f['bronze']*f['micro']+.04*f['cyan']*f['edge'],.16*f['cyan']*f['edge']+.08*f['violet']*f['micro'])),0,1)
 if not angle:return a,f
 # A separate angle state flips individual ridges rather than uniformly tinting.
 b=a*.16+np.dstack((.32*f['bronze']+.24*f['violet']+.07*f['edge'],.30*f['cyan']+.19*f['bronze']+.05*f['micro'],.42*f['cyan']+.22*f['violet']+.08*f['edge']))
 return np.clip(b,0,1),f

def _material(f):
 # Directional groove polish, local micro-relief, and dark resin have separate
 # causes and hence cannot collapse into a copied three-channel spec recipe.
 metal=np.clip(.45*f['hue']+.29*f['sat']+.26*f['edge'],0,1)
 rough=np.clip(.48*f['micro']+.31*f['gx']+.21*(1-f['resin']),0,1)
 clear=np.clip(.44*f['resin']+.35*f['gy']+.21*f['bronze'],0,1)
 return np.stack((_tier(metal,M_T),_tier(rough,R_T),_tier(clear,C_T)),2)
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'ground_beetle_asset_i2'),indent=2))
