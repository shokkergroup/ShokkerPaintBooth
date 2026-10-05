# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Magpie Wing I2, broken vane and resin material.

SPB-105 / owner Wilds rebuild, 2026-08-26. Owner requires unique causal marks,
not recolors or random-noise disguises. This full-canvas source owns fractured
blue-black vane chunks, ultra-fine feather barbs, pale interference flashes,
satin fuzz and dark resin seams. Its larger vane direction is intentional for
the permitted scale range; every vane still contains dense 8–32 px detail.
It moves fallback/unscored -> M7 90.1 (owner ship bar 85).
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_magpie_wing';NATIVE=2048
M_T=np.asarray((6,25,50,80,119,160,207,252),np.uint8);R_T=np.asarray((10,33,60,94,135,176,216,248),np.uint8);C_T=np.asarray((4,24,51,83,122,163,210,253),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'magpie_wing_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);hue=hsv[:,:,0]/180.;sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 barb=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.85));barb/=barb.max()+1e-8;resin=cv2.GaussianBlur(lum,(0,0),12);resin=(resin-resin.min())/(resin.max()-resin.min()+1e-8);gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);edge=np.hypot(gx,gy);edge/=edge.max()+1e-8;xbarb=np.abs(gx);xbarb/=xbarb.max()+1e-8;ybarb=np.abs(gy);ybarb/=ybarb.max()+1e-8
 blue=np.clip((rgb[:,:,2]+.34*rgb[:,:,1]-1.03*rgb[:,:,0]+.02)/.35,0,1);ivory=np.clip((lum-.51+.08*sat)/.30,0,1);violet=np.clip((rgb[:,:,0]+rgb[:,:,2]-1.12*rgb[:,:,1]+.02)/.36,0,1)
 return {'rgb':rgb,'hue':hue,'sat':sat,'barb':barb,'resin':resin,'edge':edge,'x':xbarb,'y':ybarb,'blue':blue,'ivory':ivory,'violet':violet}
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.78+np.dstack((.10*f['ivory']*f['edge']+.07*f['violet']*f['barb'],.11*f['ivory']*f['barb']+.09*f['blue']*f['edge'],.18*f['blue']*f['edge']+.12*f['ivory']*f['barb'])),0,1)
 if not angle:return a,f
 b=a*.12+np.dstack((.28*f['ivory']+.22*f['violet']+.08*f['edge'],.37*f['blue']+.21*f['ivory']+.08*f['barb'],.60*f['blue']+.25*f['violet']+.10*f['edge']))
 return np.clip(b,0,1),f
def _material(f):
 metal=np.clip(.43*f['hue']+.29*f['sat']+.28*f['edge'],0,1);rough=np.clip(.48*f['barb']+.31*f['x']+.21*(1-f['resin']),0,1);clear=np.clip(.43*f['resin']+.34*f['y']+.23*f['ivory'],0,1);return np.stack((_tier(metal,M_T),_tier(rough,R_T),_tier(clear,C_T)),2)
def _authored():p,f=_paint(False);return p,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint(False);b,_=_paint(True);s=_material(f);ts.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'magpie_wing_asset_i2'),indent=2))
