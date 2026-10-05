# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Monarch Vein I2, wounded lepidoptera membrane.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This full-resolution wing close-up
has causal biological hierarchy: nested overlapping scales, irregular dark
membrane veins, exposed powder, ruptured edge hooks and selected interference
strata.  The orange scale field is not a flat colourway—cyan/violet fire and
material variations belong to specific damaged scale stacks.  Small scales
carry the crush-down image while the varied veins preserve a larger identity.
Full accepted-set M7: fallback/unscored -> 89.3; collision and distinctness
gates passed with this independent source.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_monarch_vein';NATIVE=2048
MT=np.asarray((6,30,58,91,130,170,213,252),np.uint8);RT=np.asarray((8,37,67,100,140,179,220,250),np.uint8);CT=np.asarray((4,25,53,85,124,164,210,254),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'monarch_vein_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);edge=np.hypot(gx,gy);edge/=edge.max()+1e-8
 scale=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.05));scale/=scale.max()+1e-8
 vein=np.abs(gx*.76-gy*.49);vein/=vein.max()+1e-8
 hook=np.abs(gx*.31+gy*.89);hook/=hook.max()+1e-8
 membrane=cv2.GaussianBlur(lum,(0,0),10.5);membrane=(membrane-membrane.min())/(membrane.max()-membrane.min()+1e-8)
 powder=np.abs(sat-cv2.GaussianBlur(sat,(0,0),5.5));powder/=powder.max()+1e-8
 orange=np.clip((1.21*rgb[:,:,0]+.41*rgb[:,:,1]-.74*rgb[:,:,2]-.25)/.50,0,1)
 cyan=np.clip((.10*rgb[:,:,0]+.86*rgb[:,:,1]+1.13*rgb[:,:,2]-.46)/.48,0,1)
 violet=np.clip((.70*rgb[:,:,0]-.20*rgb[:,:,1]+1.12*rgb[:,:,2]-.40)/.48,0,1)
 gold=np.clip((1.04*rgb[:,:,0]+.74*rgb[:,:,1]-.28*rgb[:,:,2]-.48)/.38,0,1)
 black=np.clip((.27-lum)/.27,0,1)
 return dict(rgb=rgb,sat=sat,edge=edge,scale=scale,vein=vein,hook=hook,membrane=membrane,powder=powder,orange=orange,cyan=cyan,violet=violet,gold=gold,black=black)
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.69+np.dstack((.17*f['orange']*f['scale']+.09*f['gold']*f['vein'],.06*f['gold']*f['hook']+.13*f['cyan']*f['scale'],.08*f['violet']*f['scale']+.15*f['cyan']*f['hook']))-.08*f['black'][:,:,None],0,1)
 if not angle:return a,f
 # Grazing angle moves intact orange scales toward teal/cyan while powder-loss
 # and ruptured vein hooks throw violet/gold; the state follows the actual
 # scale/membrane maps instead of applying one global hue rotation.
 b=a*.035+np.dstack((.13*f['orange']+.32*f['violet']+.20*f['gold']+.10*f['vein'],.34*f['orange']+.38*f['cyan']+.15*f['gold']+.10*f['scale'],.29*f['orange']+.54*f['cyan']+.29*f['violet']+.12*f['hook']));return np.clip(b,0,1),f
def _material(f):
 metal=_tier(np.clip(.27*f['orange']+.21*f['cyan']+.19*f['violet']+.18*f['scale']+.15*f['gold'],0,1),MT)
 rough=_tier(np.clip(.35*f['scale']+.26*f['vein']+.22*f['powder']+.17*f['hook'],0,1),RT)
 clearcoat=_tier(np.clip(.29*f['membrane']+.23*f['cyan']+.20*f['orange']+.16*f['edge']+.12*f['sat'],0,1),CT)
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'monarch_vein_asset_i2'),indent=2))
