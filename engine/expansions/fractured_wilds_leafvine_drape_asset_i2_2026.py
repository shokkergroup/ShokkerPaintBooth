# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Leafvine Drape I2, folded fabric-lacquer livery.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Overlapping draped satin folds,
fine woven interiors, brushed lanes, chipped foil cuts and dark crease seams:
name-led organic connection without literal leaves or a repeated leaf stamp.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fbl_leafvine_drape';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'leafvine_drape_i2.png'
@lru_cache(maxsize=2)
def _f():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);crease=np.hypot(gx,gy);crease/=crease.max()+1e-8
 weave=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.0));weave/=weave.max()+1e-8;brush=np.abs(cv2.GaussianBlur(lum,(0,0),3.0)-cv2.GaussianBlur(lum,(0,0),15));brush/=brush.max()+1e-8
 drape=cv2.GaussianBlur(lum,(0,0),31);drape=(drape-drape.min())/(drape.max()-drape.min()+1e-8);void=np.clip((.11-lum)/.11,0,1)
 green=np.clip((-.48*x[:,:,0]+1.16*x[:,:,1]+.18*x[:,:,2]-.31)/.46,0,1);olive=np.clip((.76*x[:,:,0]+.82*x[:,:,1]-.55*x[:,:,2]-.41)/.40,0,1);gold=np.clip((1.12*x[:,:,0]+.78*x[:,:,1]-.65*x[:,:,2]-.50)/.33,0,1);cyan=np.clip((-.62*x[:,:,0]+1.07*x[:,:,1]+1.17*x[:,:,2]-.60)/.30,0,1)
 return dict(x=x,sat=sat,lum=lum,crease=crease,weave=weave,brush=brush,drape=drape,void=void,green=green,olive=olive,gold=gold,cyan=cyan)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.60+np.dstack((.14*f['gold']*f['crease']+.09*f['olive']*f['brush'],.22*f['green']*f['crease']+.10*f['gold']*f['weave'],.17*f['cyan']*f['crease']+.08*f['green']*f['brush']))-.08*f['void'][:,:,None],0,1)
 if not b:return a,f
 phase=.34+.66*np.clip(.31*f['drape']+.25*f['sat']+.20*f['brush']+.14*f['weave']+.10*f['crease'],0,1);b=.014*a+np.dstack((.23+.52*f['gold']+.22*f['olive'],.25+.55*f['green']+.24*f['gold'],.13+.60*f['cyan']+.19*f['green']))*phase[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.29*f['gold']+.25*f['cyan']+.21*f['green']+.15*f['olive']+.10*f['weave'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.35*f['void']+.27*f['crease']+.22*f['weave']+.16*f['brush'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.33*f['drape']+.24*f['sat']+.19*f['brush']+.14*f['green']+.10*f['crease'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'leafvine_drape_asset_i2'),indent=2))
