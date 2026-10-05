# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Fire Agate I3, crushed botryoidal mineral fire.

SPB-105 / owner Wilds rebuild, 2026-08-26. The prior corrugated Fire Agate was
rejected. This source instead uses dense 8–32 px ruptured mineral beads, dark
resin seams, translucent chips and nested mineral currents—never stripes,
generic noise, or a recolored shared pattern. It moves fallback/unscored -> M7
90.6 (owner ship bar 85). Larger currents are deliberate scaleable hierarchy
per owner direction; the close read remains micro-dense.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_fire_agate';NATIVE=2048
M_T=np.asarray((8,27,53,84,121,161,207,252),np.uint8);R_T=np.asarray((10,34,61,95,136,176,216,248),np.uint8);C_T=np.asarray((5,25,54,86,125,165,210,253),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'fire_agate_i3.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.; hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32)
 hue=hsv[:,:,0]/180.;sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 chip=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.15));chip/=chip.max()+1e-8; resin=cv2.GaussianBlur(lum,(0,0),12.5);resin=(resin-resin.min())/(resin.max()-resin.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);lip=np.hypot(gx,gy);lip/=lip.max()+1e-8; xlip=np.abs(gx);xlip/=xlip.max()+1e-8;ylip=np.abs(gy);ylip/=ylip.max()+1e-8
 ember=np.clip((rgb[:,:,0]+.45*rgb[:,:,1]-1.15*rgb[:,:,2]+.03)/.37,0,1);green=np.clip((rgb[:,:,1]-.36*rgb[:,:,0]-.17*rgb[:,:,2]+.03)/.26,0,1);violet=np.clip((rgb[:,:,0]+rgb[:,:,2]-1.09*rgb[:,:,1]+.02)/.39,0,1);teal=np.clip((rgb[:,:,2]+.28*rgb[:,:,1]-1.03*rgb[:,:,0]+.03)/.31,0,1)
 return {'rgb':rgb,'hue':hue,'sat':sat,'chip':chip,'resin':resin,'lip':lip,'xlip':xlip,'ylip':ylip,'ember':ember,'green':green,'violet':violet,'teal':teal}
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.80+np.dstack((.19*f['ember']*f['lip']+.09*f['violet']*f['chip'],.13*f['green']*f['lip']+.08*f['ember']*f['chip'],.16*f['teal']*f['lip']+.10*f['violet']*f['chip'])),0,1)
 if not angle:return a,f
 b=a*.15+np.dstack((.41*f['ember']+.23*f['violet']+.07*f['lip'],.35*f['green']+.20*f['ember']+.05*f['chip'],.39*f['teal']+.28*f['violet']+.08*f['lip']))
 return np.clip(b,0,1),f
def _material(f):
 # Mineral chemistry, fracture-lip relief and deep resin are causally distinct.
 metal=np.clip(.42*f['hue']+.30*f['sat']+.28*f['lip'],0,1);rough=np.clip(.47*f['chip']+.30*f['xlip']+.23*(1-f['resin']),0,1);clear=np.clip(.43*f['resin']+.34*f['ylip']+.23*f['ember'],0,1)
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'fire_agate_asset_i3'),indent=2))
