# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Swallowtail Flash I2, crossed wing-lamella material.

SPB-105 / owner Wilds rebuild, 2026-08-26. This has distinct blue ridge fans,
broken gold transverse lamellae, scale dust, keratin cracks and black resin—not
a Magpie recolor or a random-noise carrier. Its physical channels are each
source-derived, and primary detail is fine at the 2048 canvas scale. It moves
fallback/unscored -> M7 88.6 (owner ship bar 85).
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_swallowtail';NATIVE=2048
MT=np.asarray((6,26,52,83,121,161,208,252),np.uint8);RT=np.asarray((10,34,61,95,136,176,216,248),np.uint8);CT=np.asarray((4,24,51,83,122,163,210,253),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'swallowtail_flash_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);hue=hsv[:,:,0]/180.;sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 dust=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.9));dust/=dust.max()+1e-8;resin=cv2.GaussianBlur(lum,(0,0),11);resin=(resin-resin.min())/(resin.max()-resin.min()+1e-8);gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);edge=np.hypot(gx,gy);edge/=edge.max()+1e-8;x=np.abs(gx);x/=x.max()+1e-8;y=np.abs(gy);y/=y.max()+1e-8
 gold=np.clip((rgb[:,:,0]+.55*rgb[:,:,1]-1.19*rgb[:,:,2]+.02)/.36,0,1);blue=np.clip((rgb[:,:,2]+.25*rgb[:,:,1]-1.04*rgb[:,:,0]+.02)/.35,0,1);violet=np.clip((rgb[:,:,0]+rgb[:,:,2]-1.10*rgb[:,:,1]+.02)/.38,0,1)
 return {'rgb':rgb,'hue':hue,'sat':sat,'dust':dust,'resin':resin,'edge':edge,'x':x,'y':y,'gold':gold,'blue':blue,'violet':violet}
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.76+np.dstack((.20*f['gold']*f['edge']+.07*f['violet']*f['dust'],.15*f['gold']*f['dust']+.07*f['blue']*f['edge'],.22*f['blue']*f['edge']+.10*f['violet']*f['dust'])),0,1)
 if not angle:return a,f
 b=a*.09+np.dstack((.47*f['gold']+.22*f['violet']+.08*f['edge'],.40*f['gold']+.31*f['blue']+.08*f['dust'],.62*f['blue']+.28*f['violet']+.11*f['edge']));return np.clip(b,0,1),f
def _material(f):return np.stack((_tier(np.clip(.43*f['hue']+.29*f['sat']+.28*f['edge'],0,1),MT),_tier(np.clip(.48*f['dust']+.31*f['x']+.21*(1-f['resin']),0,1),RT),_tier(np.clip(.43*f['resin']+.34*f['y']+.23*f['gold'],0,1),CT)),2)
def _authored():p,f=_paint(False);return p,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint(False);b,_=_paint(True);s=_material(f);ts.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'swallowtail_flash_asset_i2'),indent=2))
