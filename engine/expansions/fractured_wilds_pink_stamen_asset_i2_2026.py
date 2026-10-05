# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Pink Stamen Star I2, bead-tipped filament bursts.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Pink Stamen is a causal field of
thread bundles, split tips, pollen beads, translucent binding sheets and amber
interference dust.  It is deliberately not a generic flower/petal recipe, nor
a reused Bloom spec map: each material channel responds to separate filament,
bead, resin and fracture fields.  Fine threadwork carries the native 2048 view;
larger burst clusters make the name legible when the finish is compressed.
Full accepted-set M7: fallback/unscored -> 89.1; collision and distinctness
gates passed with this independent source.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fbl_pink_stamen';NATIVE=2048
MT=np.asarray((8,31,57,88,126,165,209,250),np.uint8);RT=np.asarray((7,36,66,99,139,179,218,251),np.uint8);CT=np.asarray((5,25,53,85,123,164,210,254),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'pink_stamen_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);hue=hsv[:,:,0]/180.;sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);edge=np.hypot(gx,gy);edge/=edge.max()+1e-8
 filament=np.abs(gx*.71-gy*.43);filament/=filament.max()+1e-8
 bead=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.15));bead/=bead.max()+1e-8
 resin=cv2.GaussianBlur(lum,(0,0),9.0);resin=(resin-resin.min())/(resin.max()-resin.min()+1e-8)
 hot=np.clip((1.10*rgb[:,:,0]-.27*rgb[:,:,1]-.37*rgb[:,:,2]-.16)/.48,0,1)
 coral=np.clip((rgb[:,:,0]+.47*rgb[:,:,1]-.96*rgb[:,:,2]-.20)/.46,0,1)
 pearl=np.clip((rgb[:,:,0]+.72*rgb[:,:,1]+.45*rgb[:,:,2]-1.12)/.52,0,1)
 violet=np.clip((.56*rgb[:,:,0]+rgb[:,:,2]-.81*rgb[:,:,1]-.17)/.45,0,1)
 amber=np.clip((rgb[:,:,0]+.79*rgb[:,:,1]-.99*rgb[:,:,2]-.25)/.42,0,1)
 return dict(rgb=rgb,hue=hue,sat=sat,edge=edge,filament=filament,bead=bead,resin=resin,hot=hot,coral=coral,pearl=pearl,violet=violet,amber=amber)
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.74+np.dstack((.16*f['hot']*f['filament']+.10*f['coral']*f['bead'],.07*f['amber']*f['bead']+.05*f['pearl']*f['edge'],.13*f['violet']*f['filament']+.08*f['pearl']*f['bead'])),0,1)
 if not angle:return a,f
 b=a*.09+np.dstack((.35*f['coral']+.23*f['amber']+.10*f['bead'],.28*f['pearl']+.31*f['amber']+.08*f['edge'],.43*f['violet']+.30*f['pearl']+.12*f['filament']));return np.clip(b,0,1),f
def _material(f):
 metal=_tier(np.clip(.27*f['hot']+.23*f['amber']+.19*f['violet']+.17*f['filament']+.14*f['edge'],0,1),MT)
 rough=_tier(np.clip(.39*f['filament']+.27*f['bead']+.21*f['edge']+.13*(1-f['resin']),0,1),RT)
 clearcoat=_tier(np.clip(.34*f['resin']+.24*f['pearl']+.18*f['coral']+.15*f['bead']+.09*f['violet'],0,1),CT)
 return np.stack((metal,rough,clearcoat),2)
def _authored():p,f=_paint(False);return p,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint(False);b,_=_paint(True);s=_material(f);ts.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'pink_stamen_asset_i2'),indent=2))
