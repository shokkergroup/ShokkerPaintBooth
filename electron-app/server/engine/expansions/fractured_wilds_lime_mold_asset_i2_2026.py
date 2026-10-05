# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Lime Mold I2, mineralized mycelial crust.

SPB-105 / owner Wilds rebuild, 2026-08-26. Chalky lime plates, lacy hyphae,
crystalline efflorescence, powdery spores and nutrient voids form a dry living
crust, not generic green noise. Large crust plates retain fissures, dust and
fine branching detail. A/B and M/R/Cc derive from different material fields.
Native 2048 evidence is 1.44-1.67 s, with A/B 0.120/0.262 mean/p95 and
M/R/Cc std 83.43/83.96/83.28. SPB-105 gate movement: fallback/unscored to
M7 88.7; collision and distinctness are clean across the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fpe_lime_mold';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'lime_mold_i2.png'
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);s=h[:,:,1]/255.;l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2];gx=cv2.Sobel(l,cv2.CV_32F,1,0);gy=cv2.Sobel(l,cv2.CV_32F,0,1);fiss=np.hypot(gx,gy);fiss/=fiss.max()+1e-8;hypha=np.abs(gx*.69-gy*.72);hypha/=hypha.max()+1e-8;spore=np.abs(l-cv2.GaussianBlur(l,(0,0),.89));spore/=spore.max()+1e-8;crust=cv2.GaussianBlur(l,(0,0),11.7);crust=(crust-crust.min())/(crust.max()-crust.min()+1e-8);dark=np.clip((.28-l)/.28,0,1);lime=np.clip((-.24*x[:,:,0]+1.22*x[:,:,1]-.12*x[:,:,2]-.43)/.50,0,1);chart=np.clip((.35*x[:,:,0]+1.10*x[:,:,1]-.55*x[:,:,2]-.50)/.40,0,1);cyan=np.clip((-.49*x[:,:,0]+1.06*x[:,:,1]+1.16*x[:,:,2]-.55)/.36,0,1);amber=np.clip((1.15*x[:,:,0]+.56*x[:,:,1]-.56*x[:,:,2]-.43)/.38,0,1);return dict(x=x,s=s,fiss=fiss,hypha=hypha,spore=spore,crust=crust,dark=dark,lime=lime,chart=chart,cyan=cyan,amber=amber)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.54+np.dstack((.13*f['amber']*f['spore']+.10*f['lime']*f['fiss'],.30*f['lime']*f['spore']+.16*f['chart']*f['hypha'],.12*f['cyan']*f['hypha']+.08*f['lime']*f['fiss']))-.08*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.40+.60*np.clip(.41*f['crust']+.33*f['fiss']+.26*f['s'],0,1);return np.clip(.01*a+np.dstack((.24+.28*f['amber']+.17*f['lime'],.45+.46*f['lime']+.22*f['chart'],.20+.38*f['cyan']+.18*f['lime']))*p[:,:,None],0,1),f
def _spec(f):
 m=_q(np.clip(.30*f['lime']+.24*f['chart']+.19*f['cyan']+.15*f['amber']+.12*f['spore'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.38*f['spore']+.28*f['hypha']+.22*f['fiss']+.12*f['dark'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.34*f['crust']+.23*f['lime']+.19*f['cyan']+.14*f['fiss']+.10*f['s'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];z=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);z.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;v=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(v*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(z))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(v.mean()),'angle_delta_p95':float(np.quantile(v,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'lime_mold_asset_i2'),indent=2))
