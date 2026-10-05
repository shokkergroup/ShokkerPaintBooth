# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Lime Diatom I2, fractured silica spindle field.

SPB-105 / owner Wilds rebuild, 2026-08-26. The named diatom is interpreted as
irregular glassy silica spindles, serrated micro-needles and wet teal resin—
not cells, honeycomb, or generic random grain. The image remains 2048² source
artwork; the three physical channels are independently derived causal fields.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np

ID='fpe_lime_diatom';NATIVE=2048
M_T=np.asarray((7,28,51,82,119,160,208,251),np.uint8)
R_T=np.asarray((11,35,62,96,137,177,218,247),np.uint8)
C_T=np.asarray((4,25,52,83,122,161,207,253),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'lime_diatom_i2.png'

@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32)
 hue=hsv[:,:,0]/180.
 lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 # SPB-105 / owner: causal source marks, never generic noise. Silica spindles,
 # serrated edges and wet resin are source-derived at distinct scales.
 dust=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.9));dust/=dust.max()+1e-8
 film=cv2.GaussianBlur(lum,(0,0),10.5);film=(film-film.min())/(film.max()-film.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);edge=np.hypot(gx,gy);edge/=edge.max()+1e-8
 # Curl direction is source geometry: horizontal foil lips and vertical shard
 # snaps deliberately do not collapse into the same material-channel field.
 xedge=np.abs(gx);xedge/=xedge.max()+1e-8
 yedge=np.abs(gy);yedge/=yedge.max()+1e-8
 lime=np.clip((rgb[:,:,1]+.26*rgb[:,:,0]-1.08*rgb[:,:,2]+.03)/.34,0,1)
 teal=np.clip((rgb[:,:,2]+.33*rgb[:,:,1]-1.08*rgb[:,:,0]+.05)/.36,0,1)
 cyan=np.clip((rgb[:,:,2]-.31*rgb[:,:,0]+.08)/.31,0,1)
 acid=np.clip((rgb[:,:,0]+rgb[:,:,1]-1.25*rgb[:,:,2]+.03)/.39,0,1)
 return {'rgb':rgb,'hue':hue,'dust':dust,'film':film,'edge':edge,'xedge':xedge,'yedge':yedge,'lime':lime,'teal':teal,'cyan':cyan,'acid':acid}

def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']+np.dstack((.12*f['acid']*f['edge'],.16*f['lime']*f['dust'],.10*f['cyan']*f['edge']+.05*f['teal']*f['dust'])),0,1)
 if not angle:return a,f
 b=a*.18+np.dstack((.24*f['acid']+.12*f['lime']+.06*f['edge'],.34*f['lime']+.09*f['dust'],.33*f['cyan']+.23*f['teal']+.06*f['edge']))
 return np.clip(b,0,1),f

def _material(f):
 # Teal resin chemistry, silica micro-relief and embedded wet-film depth each
 # own a channel; this stays fractured rather than one copied Petri spec map.
 # Teal is chosen over global hue because it is the source's material phase,
 # not a correlated recolor of the bright lime spindles.
 m=f['teal']
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'lime_diatom_asset_i2'),indent=2))
