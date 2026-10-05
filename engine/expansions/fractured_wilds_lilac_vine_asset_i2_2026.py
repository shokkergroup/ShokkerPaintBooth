# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Lilac Vine I2, broken engraved-lacquer linework.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Interrupted arabesque inlay,
forked flourishes, inner etching, collar joints and chrome fracture lips are
one line-led race-livery material—not leaves, damask wallpaper, plate cells,
or a palette-only cousin of an existing Wilds source.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fbl_lilac_vine';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'lilac_vine_i2.png'
@lru_cache(maxsize=2)
def _f():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);lip=np.hypot(gx,gy);lip/=lip.max()+1e-8
 etch=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.05));etch/=etch.max()+1e-8;stroke=np.abs(cv2.GaussianBlur(lum,(0,0),2.3)-cv2.GaussianBlur(lum,(0,0),10));stroke/=stroke.max()+1e-8
 flow=cv2.GaussianBlur(lum,(0,0),25);flow=(flow-flow.min())/(flow.max()-flow.min()+1e-8);ink=np.clip((.105-lum)/.105,0,1)
 lilac=np.clip((.93*x[:,:,0]-.56*x[:,:,1]+1.15*x[:,:,2]-.33)/.40,0,1);cyan=np.clip((-.60*x[:,:,0]+1.08*x[:,:,1]+1.18*x[:,:,2]-.52)/.32,0,1);silver=np.clip((lum-.58)/.35,0,1);violet=np.clip((.80*x[:,:,0]-.51*x[:,:,1]+1.13*x[:,:,2]-.35)/.37,0,1)
 return dict(x=x,sat=sat,lum=lum,lip=lip,etch=etch,stroke=stroke,flow=flow,ink=ink,lilac=lilac,cyan=cyan,silver=silver,violet=violet)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.58+np.dstack((.21*f['lilac']*f['lip']+.11*f['violet']*f['etch'],.15*f['silver']*f['stroke']+.10*f['cyan']*f['etch'],.22*f['cyan']*f['lip']+.13*f['violet']*f['stroke']))-.07*f['ink'][:,:,None],0,1)
 if not b:return a,f
 phase=.34+.66*np.clip(.31*f['flow']+.25*f['sat']+.20*f['stroke']+.14*f['etch']+.10*f['lip'],0,1);b=.015*a+np.dstack((.29+.53*f['lilac']+.32*f['violet'],.20+.47*f['silver']+.30*f['cyan'],.18+.58*f['cyan']+.31*f['violet']))*phase[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.30*f['lilac']+.24*f['cyan']+.19*f['violet']+.16*f['silver']+.11*f['etch'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.36*f['ink']+.26*f['lip']+.22*f['etch']+.16*f['stroke'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.33*f['flow']+.24*f['sat']+.19*f['stroke']+.14*f['silver']+.10*f['lip'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'lilac_vine_asset_i2'),indent=2))
