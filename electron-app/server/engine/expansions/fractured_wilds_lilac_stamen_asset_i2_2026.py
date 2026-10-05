# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Lilac Stamen Star I2, fractured filament constellations.

SPB-105 / owner Wilds rebuild, 2026-08-26. The named stamen is interpreted as
irregular curled filament constellations, bead-tip glints and dark resin—not
repeated floral wallpaper. The image remains 2048² source artwork; the three
physical channels are independently derived causal fields.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np

ID='fbl_lilac_stamen';NATIVE=2048
M_T=np.asarray((7,28,51,82,119,160,208,251),np.uint8)
R_T=np.asarray((11,35,62,96,137,177,218,247),np.uint8)
C_T=np.asarray((4,25,52,83,122,161,207,253),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'lilac_stamen_i2.png'

@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32)
 hue=hsv[:,:,0]/180.
 lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 # SPB-105 / owner: causal source marks, never generic noise. Fine bead glints,
 # curled stamen edges and deep resin are source-derived at distinct scales.
 dust=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.9));dust/=dust.max()+1e-8
 film=cv2.GaussianBlur(lum,(0,0),10.5);film=(film-film.min())/(film.max()-film.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);edge=np.hypot(gx,gy);edge/=edge.max()+1e-8
 # Curl direction is source geometry: horizontal foil lips and vertical shard
 # snaps deliberately do not collapse into the same material-channel field.
 xedge=np.abs(gx);xedge/=xedge.max()+1e-8
 yedge=np.abs(gy);yedge/=yedge.max()+1e-8
 lilac=np.clip((rgb[:,:,2]+.37*rgb[:,:,0]-1.08*rgb[:,:,1]+.03)/.34,0,1)
 pearl=np.clip((rgb[:,:,0]+.31*rgb[:,:,1]-1.06*rgb[:,:,2]+.04)/.36,0,1)
 cyan=np.clip((rgb[:,:,2]-.39*rgb[:,:,0]+.06)/.31,0,1)
 gold=np.clip((rgb[:,:,0]+.61*rgb[:,:,1]-1.32*rgb[:,:,2]+.04)/.39,0,1)
 return {'rgb':rgb,'hue':hue,'dust':dust,'film':film,'edge':edge,'xedge':xedge,'yedge':yedge,'lilac':lilac,'pearl':pearl,'cyan':cyan,'gold':gold}

def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']+np.dstack((.11*f['lilac']*f['dust']+.05*f['gold']*f['edge'],.08*f['pearl']*f['edge'],.15*f['cyan']*f['dust'])),0,1)
 if not angle:return a,f
 b=a*.19+np.dstack((.34*f['lilac']+.24*f['gold']+.07*f['edge'],.15*f['pearl']+.07*f['dust'],.38*f['cyan']+.19*f['lilac']+.06*f['edge']))
 return np.clip(b,0,1),f

def _material(f):
 # Hue-isolated filament chemistry, bead-tip dust and embedded resin each own
 # a channel; this preserves a fractured response rather than one copied spec.
 m=f['hue']
 r=f['dust']
 c=f['film']
 return np.stack((_tier(m,M_T),_tier(r,R_T),_tier(c,C_T)),2)
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'lilac_stamen_asset_i2'),indent=2))
