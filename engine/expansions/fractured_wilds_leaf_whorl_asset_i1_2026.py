# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Leaf Whorl I1, fractured carbon-lamella livery.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Dense unequal angular lamellae,
etched inner ribs, clipped chevrons, copper fracture lips and black seams give
this finish its name-led directional motion without literal leaves, rows,
plates, grain, or a shared swirl carrier.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fbl_leaf_whorl';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'leaf_whorl_i1.png'
@lru_cache(maxsize=2)
def _f():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);lip=np.hypot(gx,gy);lip/=lip.max()+1e-8;rib=np.abs(.83*gx+.55*gy);rib/=rib.max()+1e-8;etch=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.15));etch/=etch.max()+1e-8
 laminate=cv2.GaussianBlur(lum,(0,0),17);laminate=(laminate-laminate.min())/(laminate.max()-laminate.min()+1e-8);void=np.clip((.14-lum)/.14,0,1)
 green=np.clip((-.42*x[:,:,0]+1.17*x[:,:,1]+.24*x[:,:,2]-.31)/.44,0,1);olive=np.clip((.66*x[:,:,0]+.92*x[:,:,1]-.49*x[:,:,2]-.41)/.41,0,1);copper=np.clip((1.14*x[:,:,0]+.50*x[:,:,1]-.61*x[:,:,2]-.41)/.39,0,1);cyan=np.clip((-.58*x[:,:,0]+1.10*x[:,:,1]+1.17*x[:,:,2]-.61)/.32,0,1)
 return dict(x=x,sat=sat,lip=lip,rib=rib,etch=etch,laminate=laminate,void=void,green=green,olive=olive,copper=copper,cyan=cyan)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.58+np.dstack((.26*f['copper']*f['lip']+.10*f['olive']*f['etch'],.24*f['green']*f['lip']+.12*f['copper']*f['rib'],.22*f['cyan']*f['rib']+.10*f['green']*f['etch']))-.10*f['void'][:,:,None],0,1)
 if not b:return a,f
 p=.37+.63*np.clip(.34*f['laminate']+.28*f['sat']+.23*f['rib']+.15*f['etch'],0,1);b=.010*a+np.dstack((.35+.54*f['copper']+.27*f['olive'],.24+.57*f['green']+.25*f['copper'],.13+.58*f['cyan']+.25*f['green']))*p[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.30*f['green']+.24*f['olive']+.21*f['copper']+.16*f['cyan']+.09*f['etch'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.35*f['void']+.28*f['rib']+.22*f['lip']+.15*f['etch'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.33*f['laminate']+.25*f['sat']+.19*f['green']+.14*f['olive']+.09*f['lip'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'leaf_whorl_asset_i1'),indent=2))
