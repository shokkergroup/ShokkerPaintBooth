# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Cyan Mold I2, wet mineral biofilm.

SPB-105 / owner Wilds rebuild, 2026-08-26. Translucent aqueous films, dark
nutrient seams, crusted cyan colonies, sediment grains and ruptured meniscus
edges form a wet bio-mineral surface, unlike Lime Mold's dry chalk crust.
Fine film fractures and grains persist under scale; A/B and M/R/Cc are causal.
Native 2048 evidence is 1.49-1.51 s, with A/B 0.213/0.436 mean/p95 and
M/R/Cc std 83.43/83.96/83.28. SPB-105 gate movement: fallback/unscored to
M7 86.7; collision and distinctness are clean across the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fpe_cyan_mold';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'cyan_mold_i2.png'
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);s=h[:,:,1]/255.;l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2];gx=cv2.Sobel(l,cv2.CV_32F,1,0);gy=cv2.Sobel(l,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8;vein=np.abs(gx*.81-gy*.58);vein/=vein.max()+1e-8;sed=np.abs(l-cv2.GaussianBlur(l,(0,0),.91));sed/=sed.max()+1e-8;film=cv2.GaussianBlur(l,(0,0),12.1);film=(film-film.min())/(film.max()-film.min()+1e-8);dark=np.clip((.25-l)/.25,0,1);cyan=np.clip((-.48*x[:,:,0]+1.11*x[:,:,1]+1.12*x[:,:,2]-.48)/.42,0,1);teal=np.clip((-.34*x[:,:,0]+1.14*x[:,:,1]+.78*x[:,:,2]-.46)/.42,0,1);blue=np.clip((-.21*x[:,:,0]+.31*x[:,:,1]+1.18*x[:,:,2]-.39)/.44,0,1);mag=np.clip((1.08*x[:,:,0]-.43*x[:,:,1]+.88*x[:,:,2]-.47)/.34,0,1);return dict(x=x,s=s,rim=rim,vein=vein,sed=sed,film=film,dark=dark,cyan=cyan,teal=teal,blue=blue,mag=mag)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.53+np.dstack((.10*f['mag']*f['rim']+.08*f['cyan']*f['sed'],.28*f['teal']*f['sed']+.14*f['cyan']*f['vein'],.29*f['blue']*f['sed']+.17*f['cyan']*f['rim']))-.08*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.41+.59*np.clip(.41*f['film']+.33*f['rim']+.26*f['s'],0,1);return np.clip(.01*a+np.dstack((.18+.27*f['mag']+.24*f['cyan'],.34+.51*f['teal']+.19*f['cyan'],.42+.56*f['blue']+.21*f['teal']))*p[:,:,None],0,1),f
def _spec(f):
 m=_q(np.clip(.31*f['blue']+.27*f['cyan']+.22*f['teal']+.12*f['mag']+.08*f['sed'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.37*f['sed']+.28*f['vein']+.22*f['rim']+.13*f['dark'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.34*f['film']+.24*f['cyan']+.19*f['blue']+.14*f['rim']+.09*f['s'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];z=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);z.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;v=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(v*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(z))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(v.mean()),'angle_delta_p95':float(np.quantile(v,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'cyan_mold_asset_i2'),indent=2))
