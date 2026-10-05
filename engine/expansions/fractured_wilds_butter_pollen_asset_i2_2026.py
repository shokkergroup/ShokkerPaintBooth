# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Butter Pollen I2, ruptured anther matrix.

SPB-105 / owner Wilds rebuild, 2026-08-26. Spiny and collapsed pollen grains,
ripped anther membranes, powdery filament ends, resin dust and dark cavities
form a close physical botanical material—not petals or a repeated dot field.
Large ruptures retain grain-scale spines and dust. A/B and M/R/Cc are causal.
Native 2048 evidence is 1.45-1.57 s, with A/B 0.247/0.519 mean/p95 and
M/R/Cc std 83.43/83.96/83.28. SPB-105 gate movement: fallback/unscored to
M7 86.2; collision and distinctness are clean across the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fbl_butter_pollen';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'butter_pollen_i2.png'
@lru_cache(maxsize=2)
def _f():
 r=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if r is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(r,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);s=h[:,:,1]/255.;l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2];gx=cv2.Sobel(l,cv2.CV_32F,1,0);gy=cv2.Sobel(l,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8;fiber=np.abs(gx*.66-gy*.75);fiber/=fiber.max()+1e-8;grain=np.abs(l-cv2.GaussianBlur(l,(0,0),.88));grain/=grain.max()+1e-8;mem=cv2.GaussianBlur(l,(0,0),10.2);mem=(mem-mem.min())/(mem.max()-mem.min()+1e-8);dark=np.clip((.27-l)/.27,0,1);yellow=np.clip((1.10*x[:,:,0]+1.02*x[:,:,1]-.63*x[:,:,2]-.54)/.34,0,1);amber=np.clip((1.15*x[:,:,0]+.63*x[:,:,1]-.58*x[:,:,2]-.40)/.42,0,1);cyan=np.clip((-.51*x[:,:,0]+1.04*x[:,:,1]+1.18*x[:,:,2]-.58)/.34,0,1);rose=np.clip((1.07*x[:,:,0]-.35*x[:,:,1]+.80*x[:,:,2]-.48)/.36,0,1);return dict(x=x,s=s,rim=rim,fiber=fiber,grain=grain,mem=mem,dark=dark,yellow=yellow,amber=amber,cyan=cyan,rose=rose)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.55+np.dstack((.26*f['amber']*f['grain']+.12*f['rose']*f['rim'],.28*f['yellow']*f['grain']+.14*f['amber']*f['fiber'],.12*f['cyan']*f['rim']+.08*f['rose']*f['fiber']))-.07*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.42+.58*np.clip(.38*f['mem']+.34*f['grain']+.28*f['s'],0,1);return np.clip(.01*a+np.dstack((.45+.44*f['amber']+.18*f['rose'],.39+.50*f['yellow']+.22*f['amber'],.17+.35*f['cyan']+.27*f['rose']))*p[:,:,None],0,1),f
def _spec(f):
 m=_q(np.clip(.32*f['amber']+.28*f['yellow']+.18*f['cyan']+.12*f['rose']+.10*f['grain'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.37*f['grain']+.28*f['fiber']+.22*f['rim']+.13*f['dark'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.33*f['mem']+.25*f['yellow']+.18*f['amber']+.14*f['rim']+.10*f['s'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];z=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);z.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;v=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(v*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(z))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(v.mean()),'angle_delta_p95':float(np.quantile(v,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'butter_pollen_asset_i2'),indent=2))
