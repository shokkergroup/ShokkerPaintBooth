# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Sunbird Throat I2, micro-flute lacquer livery.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Dense directional satin microflutes,
etched inner ribs, black split seams, chipped ends and jewel-metal lips make a
dark performance-car surface—not a literal feather, scale field, stripe or grain.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID="fmo_sunbird_throat"; NATIVE=2048
def _q(a,v): return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'sunbird_throat_i2.png'
@lru_cache(maxsize=2)
def _f():
    raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    x=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.; h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32); sat=h[:,:,1]/255.; lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
    gx=cv2.Sobel(lum,cv2.CV_32F,1,0); gy=cv2.Sobel(lum,cv2.CV_32F,0,1); lip=np.hypot(gx,gy); lip/=lip.max()+1e-8
    rib=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.05)); rib/=rib.max()+1e-8
    flute=np.abs(cv2.GaussianBlur(lum,(0,0),3.4)-cv2.GaussianBlur(lum,(0,0),14)); flute/=flute.max()+1e-8
    sweep=cv2.GaussianBlur(lum,(0,0),25); sweep=(sweep-sweep.min())/(sweep.max()-sweep.min()+1e-8); seam=np.clip((.13-lum)/.13,0,1)
    gold=np.clip((1.20*x[:,:,0]+.79*x[:,:,1]-.70*x[:,:,2]-.38)/.46,0,1); ruby=np.clip((1.18*x[:,:,0]-.58*x[:,:,1]+.31*x[:,:,2]-.36)/.43,0,1); emerald=np.clip((-.56*x[:,:,0]+1.17*x[:,:,1]+.36*x[:,:,2]-.42)/.38,0,1); violet=np.clip((.96*x[:,:,0]-.54*x[:,:,1]+1.16*x[:,:,2]-.39)/.42,0,1)
    return dict(x=x,sat=sat,lum=lum,lip=lip,rib=rib,flute=flute,sweep=sweep,seam=seam,gold=gold,ruby=ruby,emerald=emerald,violet=violet)
def _paint(b=False):
    f=_f(); a=np.clip(f['x']*.60+np.dstack((.22*f['ruby']*f['lip']+.15*f['gold']*f['rib'],.18*f['gold']*f['lip']+.12*f['emerald']*f['flute'],.16*f['violet']*f['rib']+.14*f['emerald']*f['lip']))-.08*f['seam'][:,:,None],0,1)
    if not b:return a,f
    phase=.35+.65*np.clip(.31*f['sweep']+.25*f['sat']+.20*f['flute']+.14*f['rib']+.10*f['lip'],0,1); b=.014*a+np.dstack((.30+.60*f['ruby']+.34*f['gold'],.18+.62*f['gold']+.33*f['emerald'],.14+.55*f['violet']+.39*f['emerald']))*phase[:,:,None]; return np.clip(b,0,1),f
def _spec(f):
    m=_q(np.clip(.27*f['gold']+.23*f['ruby']+.20*f['emerald']+.18*f['violet']+.12*f['rib'],0,1),(7,34,72,109,148,187,224,253)); r=_q(np.clip(.36*f['seam']+.25*f['lip']+.23*f['rib']+.16*f['flute'],0,1),(5,29,61,99,140,179,220,251)); c=_q(np.clip(.34*f['sweep']+.25*f['sat']+.19*f['flute']+.13*f['gold']+.09*f['lip'],0,1),(6,31,66,104,143,181,217,254)); return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
    d.mkdir(parents=True,exist_ok=True);t=[];hs=[];last=None
    for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
    a,b,s=last;delta=np.abs(a-b)
    for n,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
    for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
    o={'id':ID,'timings_s':t,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'sunbird_throat_asset_i2'),indent=2))
