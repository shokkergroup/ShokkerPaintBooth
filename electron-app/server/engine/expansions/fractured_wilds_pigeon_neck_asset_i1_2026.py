# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Pigeon Neck I1, iridescent collar-laminate livery.

SPB-105 / owner Wilds rebuild, 2026-08-26. Counter-curved graphite collar
bands, broken inlay crescents, engraved rib fields, chips and foil pinlines;
not Duck Speculum's diagonal barbs, a radial target, grid, or grain texture.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_pigeon_neck';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'pigeon_neck_i1.png'
@lru_cache(maxsize=2)
def _f():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);rim=np.hypot(gx,gy);rim/=rim.max()+1e-8
 arc=np.abs(.52*gx+.85*gy);arc/=arc.max()+1e-8;rib=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.15));rib/=rib.max()+1e-8
 collar=cv2.GaussianBlur(lum,(0,0),19);collar=(collar-collar.min())/(collar.max()-collar.min()+1e-8);dark=np.clip((.16-lum)/.16,0,1)
 blue=np.clip((-.38*x[:,:,0]+.55*x[:,:,1]+1.21*x[:,:,2]-.49)/.39,0,1);teal=np.clip((-.58*x[:,:,0]+1.11*x[:,:,1]+1.14*x[:,:,2]-.57)/.34,0,1);violet=np.clip((1.10*x[:,:,0]-.52*x[:,:,1]+1.12*x[:,:,2]-.49)/.35,0,1);copper=np.clip((1.18*x[:,:,0]+.47*x[:,:,1]-.36*x[:,:,2]-.49)/.36,0,1)
 return dict(x=x,sat=sat,rim=rim,arc=arc,rib=rib,collar=collar,dark=dark,blue=blue,teal=teal,violet=violet,copper=copper)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.55+np.dstack((.19*f['violet']*f['arc']+.17*f['copper']*f['rim'],.20*f['teal']*f['rim']+.08*f['copper']*f['rib'],.29*f['blue']*f['arc']+.17*f['teal']*f['rim']))-.12*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.40+.60*np.clip(.33*f['collar']+.28*f['sat']+.23*f['arc']+.16*f['rib'],0,1);b=.012*a+np.dstack((.20+.48*f['violet']+.42*f['copper'],.25+.48*f['teal']+.29*f['copper'],.40+.52*f['blue']+.31*f['teal']))*p[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.29*f['blue']+.24*f['teal']+.20*f['violet']+.16*f['copper']+.11*f['rib'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.35*f['dark']+.27*f['arc']+.21*f['rim']+.17*f['rib'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.31*f['collar']+.25*f['sat']+.19*f['blue']+.15*f['teal']+.10*f['rim'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'pigeon_neck_asset_i1'),indent=2))
