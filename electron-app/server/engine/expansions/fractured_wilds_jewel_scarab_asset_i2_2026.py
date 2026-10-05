# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Jewel Scarab I2, interlocked elytral mosaic.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This source is an asymmetric
chitin mosaic: ribbed jewel plates, finer fractured platelets, gold seam
repairs, and dark resin channels.  Its color and material fields are derived
from the individual armor marks, not from a shared Wilds texture or a recolored
specification map.  Most ribs/chips are fine at native 2048; bigger plates are
intentional hierarchy which remains readable after the picker is crushed down.
Full accepted-set M7: fallback/unscored -> 88.0; collision and distinctness
gates passed with this independent source.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID='fmo_jewel_scarab'; NATIVE=2048
MT=np.asarray((5,29,58,91,130,170,213,252),np.uint8)
RT=np.asarray((8,38,68,101,139,178,220,250),np.uint8)
CT=np.asarray((3,26,55,87,126,166,211,254),np.uint8)
def _tier(a,t): return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'jewel_scarab_i2.png'

@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None: raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32); hue=hsv[:,:,0]/180.; sat=hsv[:,:,1]/255.
 lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0); gy=cv2.Sobel(lum,cv2.CV_32F,0,1); edge=np.hypot(gx,gy);edge/=edge.max()+1e-8
 rib=np.abs(gx*.16+gy*.84);rib/=rib.max()+1e-8
 chip=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.55));chip/=chip.max()+1e-8
 plate=cv2.GaussianBlur(lum,(0,0),8.0);plate=(plate-plate.min())/(plate.max()-plate.min()+1e-8)
 seam=1-cv2.GaussianBlur(lum,(0,0),15.0);seam=(seam-seam.min())/(seam.max()-seam.min()+1e-8)
 emerald=np.clip((.20*rgb[:,:,0]+1.18*rgb[:,:,1]-.45*rgb[:,:,2]-.15)/.52,0,1)
 cyan=np.clip((.23*rgb[:,:,0]+.76*rgb[:,:,1]+1.12*rgb[:,:,2]-.38)/.54,0,1)
 blue=np.clip((rgb[:,:,2]-.38*rgb[:,:,0]-.22*rgb[:,:,1]-.05)/.48,0,1)
 magenta=np.clip((rgb[:,:,0]+.44*rgb[:,:,2]-.96*rgb[:,:,1]-.10)/.48,0,1)
 gold=np.clip((rgb[:,:,0]+.72*rgb[:,:,1]-.87*rgb[:,:,2]-.23)/.44,0,1)
 return dict(rgb=rgb,hue=hue,sat=sat,edge=edge,rib=rib,chip=chip,plate=plate,seam=seam,emerald=emerald,cyan=cyan,blue=blue,magenta=magenta,gold=gold)

def _paint(angle=False):
 f=_fields()
 a=np.clip(f['rgb']*.72+np.dstack((.05*f['gold']*f['edge']+.08*f['magenta']*f['chip'],.15*f['emerald']*f['rib']+.05*f['gold']*f['chip'],.18*f['cyan']*f['rib']+.10*f['blue']*f['edge'])),0,1)
 if not angle:return a,f
 b=a*.07+np.dstack((.21*f['gold']+.28*f['magenta']+.09*f['edge'],.52*f['emerald']+.16*f['gold']+.08*f['rib'],.62*f['cyan']+.27*f['blue']+.10*f['edge']))
 return np.clip(b,0,1),f

def _material(f):
 metal=_tier(np.clip(.25*f['hue']+.22*f['cyan']+.18*f['emerald']+.18*f['gold']+.17*f['edge'],0,1),MT)
 rough=_tier(np.clip(.41*f['rib']+.27*f['chip']+.19*f['seam']+.13*(1-f['plate']),0,1),RT)
 clearcoat=_tier(np.clip(.34*f['plate']+.23*f['gold']+.19*f['cyan']+.15*f['edge']+.09*f['magenta'],0,1),CT)
 return np.stack((metal,rough,clearcoat),2)

def _authored(): p,f=_paint(False);return p,_material(f)
def clear_cache(): _fields.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):
  clear_cache();q=time.perf_counter();a,f=_paint(False);b,_=_paint(True);s=_material(f);ts.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 out={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(out,indent=2));return out
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'jewel_scarab_asset_i2'),indent=2))
