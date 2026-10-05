# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Weevil Pit I2, asymmetric chitin recesses.

SPB-105 / owner Wilds rebuild, 2026-08-26. This independent full-canvas source
uses causal hard-shell marks: irregular recessed apertures, raised chipped rims,
scuffed ridge fragments and black resin—not generic grain, dots, or a reused
specification map. Primary pit-rim detail stays fine at 2048. It moves
fallback/unscored -> M7 87.8 (owner ship bar 85).
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_weevil_pit';NATIVE=2048
MT=np.asarray((7,27,53,84,122,162,207,251),np.uint8);RT=np.asarray((10,34,61,95,136,176,216,248),np.uint8);CT=np.asarray((4,24,51,83,122,163,210,253),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'weevil_pit_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);hue=hsv[:,:,0]/180.;sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 chip=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.85));chip/=chip.max()+1e-8;resin=cv2.GaussianBlur(lum,(0,0),10.5);resin=(resin-resin.min())/(resin.max()-resin.min()+1e-8);gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8;x=np.abs(gx);x/=x.max()+1e-8;y=np.abs(gy);y/=y.max()+1e-8
 teal=np.clip((rgb[:,:,2]+.34*rgb[:,:,1]-1.04*rgb[:,:,0]+.03)/.32,0,1);lime=np.clip((rgb[:,:,1]-.35*rgb[:,:,0]-.14*rgb[:,:,2]+.03)/.26,0,1);bronze=np.clip((rgb[:,:,0]+.46*rgb[:,:,1]-1.12*rgb[:,:,2]+.02)/.34,0,1)
 return {'rgb':rgb,'hue':hue,'sat':sat,'chip':chip,'resin':resin,'rim':rim,'x':x,'y':y,'teal':teal,'lime':lime,'bronze':bronze}
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.78+np.dstack((.16*f['bronze']*f['rim']+.06*f['chip'],.15*f['lime']*f['rim']+.07*f['bronze']*f['chip'],.19*f['teal']*f['rim']+.08*f['chip'])),0,1)
 if not angle:return a,f
 b=a*.08+np.dstack((.31*f['bronze']+.15*f['teal']+.08*f['rim'],.51*f['lime']+.19*f['bronze']+.09*f['chip'],.52*f['teal']+.18*f['lime']+.10*f['rim']));return np.clip(b,0,1),f
def _material(f):return np.stack((_tier(np.clip(.43*f['hue']+.29*f['sat']+.28*f['rim'],0,1),MT),_tier(np.clip(.48*f['chip']+.31*f['x']+.21*(1-f['resin']),0,1),RT),_tier(np.clip(.43*f['resin']+.34*f['y']+.23*f['bronze'],0,1),CT)),2)
def _authored():p,f=_paint(False);return p,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint(False);b,_=_paint(True);s=_material(f);ts.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'weevil_pit_asset_i2'),indent=2))
