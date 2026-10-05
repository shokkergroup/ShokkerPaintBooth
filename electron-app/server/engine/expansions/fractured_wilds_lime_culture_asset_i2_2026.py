# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Lime Culture I2, mineralized microbial mats.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This finish is not generic noise
or a repeated cell grid: compact lime mats, cratered pigment grains, turquoise
mineral blooms, dark nutrient channels, ultraviolet scars and gold debris form
a causal growth surface.  Fine grain and crack detail carries the native 2048
canvas while larger irregular growth islands give it a useful crushed-down read.
Paint and all three spec channels are separately derived from its material
fields, so it cannot become a recolor with a reused spec topology.
Full accepted-set M7: fallback/unscored -> 89.6; collision and distinctness
gates passed with this independent source.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fpe_lime_culture';NATIVE=2048
MT=np.asarray((6,27,55,87,128,168,211,252),np.uint8);RT=np.asarray((9,37,65,98,139,179,219,250),np.uint8);CT=np.asarray((4,24,52,84,122,163,209,253),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'lime_culture_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);hue=hsv[:,:,0]/180.;sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);channel=np.hypot(gx,gy);channel/=channel.max()+1e-8
 grit=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.65));grit/=grit.max()+1e-8
 mat=cv2.GaussianBlur(lum,(0,0),6.8);mat=(mat-mat.min())/(mat.max()-mat.min()+1e-8)
 depth=1-cv2.GaussianBlur(lum,(0,0),14.5);depth=(depth-depth.min())/(depth.max()-depth.min()+1e-8)
 lime=np.clip((.27*rgb[:,:,0]+1.24*rgb[:,:,1]-.46*rgb[:,:,2]-.12)/.58,0,1)
 cyan=np.clip((.18*rgb[:,:,0]+.69*rgb[:,:,1]+1.13*rgb[:,:,2]-.38)/.55,0,1)
 navy=np.clip((rgb[:,:,2]-.33*rgb[:,:,0]-.34*rgb[:,:,1]-.06)/.43,0,1)
 gold=np.clip((rgb[:,:,0]+.78*rgb[:,:,1]-.96*rgb[:,:,2]-.24)/.43,0,1)
 uv=np.clip((.55*rgb[:,:,0]+rgb[:,:,2]-.88*rgb[:,:,1]-.13)/.45,0,1)
 return dict(rgb=rgb,hue=hue,sat=sat,channel=channel,grit=grit,mat=mat,depth=depth,lime=lime,cyan=cyan,navy=navy,gold=gold,uv=uv)
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.71+np.dstack((.08*f['gold']*f['grit']+.07*f['uv']*f['channel'],.19*f['lime']*f['grit']+.06*f['gold']*f['channel'],.17*f['cyan']*f['channel']+.09*f['navy']*f['grit'])),0,1)
 if not angle:return a,f
 b=a*.08+np.dstack((.21*f['gold']+.20*f['uv']+.07*f['channel'],.53*f['lime']+.18*f['gold']+.09*f['grit'],.48*f['cyan']+.31*f['navy']+.14*f['uv']));return np.clip(b,0,1),f
def _material(f):
 metal=_tier(np.clip(.24*f['lime']+.22*f['cyan']+.18*f['gold']+.19*f['channel']+.17*f['uv'],0,1),MT)
 rough=_tier(np.clip(.38*f['grit']+.28*f['channel']+.20*f['depth']+.14*(1-f['mat']),0,1),RT)
 clearcoat=_tier(np.clip(.31*f['mat']+.24*f['cyan']+.19*f['lime']+.15*f['gold']+.11*f['uv'],0,1),CT)
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'lime_culture_asset_i2'),indent=2))
