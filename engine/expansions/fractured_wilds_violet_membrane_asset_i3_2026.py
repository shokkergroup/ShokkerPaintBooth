# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Violet Membrane I3, torn mineralized film.

SPB-105 / owner Wilds rebuild, 2026-08-26. Ripped translucent film, fibrous
meniscus seams, pore clusters, dark wet cavities and embedded crystal dust make
a fractured membrane material—not the closed foam/quilt pattern previously
rejected. Large folds retain fine edge, pore and dust detail. A/B/M/R/Cc causal.
Native 2048 evidence is 1.41-1.59 s, with A/B 0.204/0.438 mean/p95 and
M/R/Cc std 83.43/83.96/83.28. SPB-105 gate movement: fallback/unscored to
M7 85.5; collision and distinctness are clean across the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fpe_violet_membrane';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'violet_membrane_i3.png'
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);s=h[:,:,1]/255.;l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2];gx=cv2.Sobel(l,cv2.CV_32F,1,0);gy=cv2.Sobel(l,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8;fiber=np.abs(gx*.84+gy*.54);fiber/=fiber.max()+1e-8;pore=np.abs(l-cv2.GaussianBlur(l,(0,0),.96));pore/=pore.max()+1e-8;fold=cv2.GaussianBlur(l,(0,0),12.4);fold=(fold-fold.min())/(fold.max()-fold.min()+1e-8);dark=np.clip((.23-l)/.23,0,1);violet=np.clip((1.00*x[:,:,0]-.28*x[:,:,1]+1.16*x[:,:,2]-.40)/.42,0,1);blue=np.clip((-.28*x[:,:,0]+.36*x[:,:,1]+1.18*x[:,:,2]-.39)/.44,0,1);cyan=np.clip((-.48*x[:,:,0]+1.08*x[:,:,1]+1.08*x[:,:,2]-.54)/.36,0,1);mag=np.clip((1.12*x[:,:,0]-.43*x[:,:,1]+.92*x[:,:,2]-.44)/.35,0,1);return dict(x=x,s=s,rim=rim,fiber=fiber,pore=pore,fold=fold,dark=dark,violet=violet,blue=blue,cyan=cyan,mag=mag)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.52+np.dstack((.24*f['violet']*f['pore']+.14*f['mag']*f['rim'],.13*f['cyan']*f['fiber']+.10*f['violet']*f['pore'],.28*f['blue']*f['fiber']+.15*f['cyan']*f['rim']))-.08*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.43+.57*np.clip(.40*f['fold']+.34*f['rim']+.26*f['s'],0,1);return np.clip(.01*a+np.dstack((.34+.50*f['violet']+.27*f['mag'],.18+.35*f['cyan']+.25*f['violet'],.39+.56*f['blue']+.28*f['cyan']))*p[:,:,None],0,1),f
def _spec(f):
 m=_q(np.clip(.31*f['blue']+.25*f['violet']+.21*f['cyan']+.13*f['mag']+.10*f['pore'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.37*f['pore']+.29*f['fiber']+.22*f['rim']+.12*f['dark'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.34*f['fold']+.24*f['violet']+.19*f['blue']+.14*f['rim']+.09*f['s'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];z=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);z.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;v=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(v*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(z))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(v.mean()),'angle_delta_p95':float(np.quantile(v,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'violet_membrane_asset_i3'),indent=2))
