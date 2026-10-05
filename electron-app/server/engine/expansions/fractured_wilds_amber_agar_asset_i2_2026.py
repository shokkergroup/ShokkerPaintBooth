# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Amber Agar I2, ruptured culture gel.

SPB-105 / owner Wilds rebuild, 2026-08-26. Unequal translucent agar sheets,
torn meniscus rims, embedded filament colonies, sediment islands, pinholes and
dry mineral ruptures form one dense, physical Petri material. Large gel seams
are name-matched hierarchy; their dust, bubbles, fissures and filament branches
preserve a crafted read at compressed scale. A/B and M/R/Cc are causal maps.
Native 2048 evidence is 1.47-1.52 s, with A/B 0.182/0.417 mean/p95 and
M/R/Cc std 83.22/84.28/83.20. SPB-105 gate movement: fallback/unscored to
M7 86.1; collision and distinctness are recorded with the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fpe_amber_agar';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'amber_agar_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8
 fiss=np.abs(gx*.87-gy*.49);fiss/=fiss.max()+1e-8
 grit=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.95));grit/=grit.max()+1e-8
 gel=cv2.GaussianBlur(lum,(0,0),13.5);gel=(gel-gel.min())/(gel.max()-gel.min()+1e-8)
 dark=np.clip((.30-lum)/.30,0,1)
 amber=np.clip((1.22*rgb[:,:,0]+.71*rgb[:,:,1]-.57*rgb[:,:,2]-.43)/.42,0,1)
 gold=np.clip((1.00*rgb[:,:,0]+.91*rgb[:,:,1]-.72*rgb[:,:,2]-.48)/.35,0,1)
 cyan=np.clip((-.48*rgb[:,:,0]+1.05*rgb[:,:,1]+1.18*rgb[:,:,2]-.55)/.36,0,1)
 rust=np.clip((1.18*rgb[:,:,0]+.13*rgb[:,:,1]-.50*rgb[:,:,2]-.36)/.40,0,1)
 return dict(rgb=rgb,sat=sat,rim=rim,fiss=fiss,grit=grit,gel=gel,dark=dark,amber=amber,gold=gold,cyan=cyan,rust=rust)
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.53+np.dstack((.28*f['amber']*f['grit']+.15*f['rust']*f['fiss'],.20*f['gold']*f['rim']+.12*f['amber']*f['grit'],.10*f['cyan']*f['rim']+.08*f['gold']*f['fiss']))-.10*f['dark'][:,:,None],0,1)
 if not angle:return a,f
 gel=.30+.70*np.clip(.47*f['gel']+.30*f['rim']+.23*f['sat'],0,1)
 b=.02*a+np.dstack((.43+.48*f['amber']+.22*f['rust']+.12*f['rim'],.25+.51*f['gold']+.24*f['amber']+.15*f['grit'],.11+.38*f['cyan']+.17*f['gold']+.14*f['fiss']))*gel[:,:,None]
 return np.clip(b,0,1),f
def _material(f):
 metal=_q(np.clip(.32*f['gold']+.24*f['amber']+.18*f['cyan']+.16*f['grit']+.10*f['rust'],0,1),(8,34,72,110,150,188,223,253))
 rough=_q(np.clip(.37*f['grit']+.28*f['fiss']+.22*f['rim']+.13*f['dark'],0,1),(5,28,60,99,140,180,220,251))
 clearcoat=_q(np.clip(.34*f['gel']+.25*f['amber']+.19*f['rim']+.13*f['gold']+.09*f['sat'],0,1),(6,31,66,104,143,180,217,254))
 return np.stack((metal,rough,clearcoat),2)
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'amber_agar_asset_i2'),indent=2))
