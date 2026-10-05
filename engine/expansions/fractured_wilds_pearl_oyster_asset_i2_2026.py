# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Pearl Oyster I2, nucleated nacre accretion.

SPB-105 / owner Wilds rebuild, 2026-08-26.  A different shell mechanism from
Mussel Shell: this is rough oyster accretion around unequal pearl nuclei.
Aragonite skins, conchiolin seams, pinholes, mineral void rims, chipped nacre
and local pearl growth knots make a continuous dense material.  Larger pearl
knots are name-matched hierarchy; fine mineral skins and fractured rims carry
the compressed-scale read.  A/B and M/R/Cc come from different causal maps.
Native 2048 evidence is 1.37-1.49 s, with A/B 0.151/0.465 mean/p95 and
M/R/Cc std 82.40/83.67/83.27.  SPB-105 gate movement: fallback/unscored to
M7 87.1; the 69-finish collision and distinctness audits are clean.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_pearl_oyster';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'pearl_oyster_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);edge=np.hypot(gx,gy);edge/=edge.max()+1e-8
 skin=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.82));skin/=skin.max()+1e-8
 seam=np.abs(gx*.78-gy*.43);seam/=seam.max()+1e-8
 rim=np.abs(gx*.37+gy*.93);rim/=rim.max()+1e-8
 pearl=cv2.GaussianBlur(lum,(0,0),7.8);pearl=(pearl-pearl.min())/(pearl.max()-pearl.min()+1e-8)
 void=np.clip((.34-lum)/.34,0,1)
 blue=np.clip((.13*rgb[:,:,0]+.54*rgb[:,:,1]+1.15*rgb[:,:,2]-.45)/.50,0,1)
 mint=np.clip((.12*rgb[:,:,0]+1.05*rgb[:,:,1]+.74*rgb[:,:,2]-.47)/.48,0,1)
 blush=np.clip((1.02*rgb[:,:,0]-.04*rgb[:,:,1]+.74*rgb[:,:,2]-.58)/.35,0,1)
 gold=np.clip((1.05*rgb[:,:,0]+.71*rgb[:,:,1]-.33*rgb[:,:,2]-.45)/.43,0,1)
 return dict(rgb=rgb,sat=sat,edge=edge,skin=skin,seam=seam,rim=rim,pearl=pearl,void=void,blue=blue,mint=mint,blush=blush,gold=gold)
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.61+np.dstack((.14*f['gold']*f['rim']+.14*f['blush']*f['skin'],.14*f['mint']*f['skin']+.11*f['gold']*f['seam'],.22*f['blue']*f['skin']+.10*f['mint']*f['rim']))-.05*f['void'][:,:,None],0,1)
 if not angle:return a,f
 phase=.45+.55*f['pearl'];b=a*.02+np.dstack((.15+.24*f['blush']+.23*f['gold']+.12*f['rim'],.23+.48*f['mint']+.19*f['gold']+.15*f['skin'],.34+.58*f['blue']+.23*f['blush']+.15*f['seam']))*phase[:,:,None];return np.clip(b,0,1),f
def _material(f):
 metal=_q(np.clip(.28*f['blue']+.23*f['mint']+.20*f['blush']+.17*f['skin']+.12*f['gold'],0,1),(8,35,73,111,149,185,221,253))
 rough=_q(np.clip(.35*f['skin']+.27*f['seam']+.22*f['rim']+.16*f['void'],0,1),(7,29,61,98,139,180,221,250))
 clearcoat=_q(np.clip(.32*f['pearl']+.25*f['mint']+.18*f['blue']+.15*f['edge']+.10*f['sat'],0,1),(5,30,67,104,142,180,216,254))
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'pearl_oyster_asset_i2'),indent=2))
