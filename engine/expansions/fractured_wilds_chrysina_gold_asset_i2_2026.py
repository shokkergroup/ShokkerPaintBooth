# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Chrysina Gold I2, mirror-facet scarab lacquer livery.

SPB-105 / owner Wilds rebuild, 2026-08-26. Dense emerald/gold mirror facets,
engraved interiors, hard fissure channels and foil insets—not panels, cells,
generic crack-map texture, or random grain.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_chrysina_gold';NATIVE=2048
def _q(a,v):return np.asarray(v,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'chrysina_gold_i2.png'
@lru_cache(maxsize=2)
def _f():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 x=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=h[:,:,1]/255.;lum=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);fiss=np.hypot(gx,gy);fiss/=fiss.max()+1e-8
 engr=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.25));engr/=engr.max()+1e-8;facet=cv2.GaussianBlur(lum,(0,0),17);facet=(facet-facet.min())/(facet.max()-facet.min()+1e-8);dark=np.clip((.16-lum)/.16,0,1)
 gold=np.clip((1.16*x[:,:,0]+.91*x[:,:,1]-.71*x[:,:,2]-.45)/.42,0,1);emer=np.clip((-.54*x[:,:,0]+1.13*x[:,:,1]+.40*x[:,:,2]-.42)/.42,0,1);cyan=np.clip((-.61*x[:,:,0]+1.08*x[:,:,1]+1.19*x[:,:,2]-.59)/.34,0,1);violet=np.clip((1.08*x[:,:,0]-.54*x[:,:,1]+1.12*x[:,:,2]-.50)/.35,0,1)
 return dict(x=x,sat=sat,fiss=fiss,engr=engr,facet=facet,dark=dark,gold=gold,emer=emer,cyan=cyan,violet=violet)
def _paint(b=False):
 f=_f();a=np.clip(f['x']*.58+np.dstack((.22*f['gold']*f['fiss']+.14*f['violet']*f['engr'],.20*f['emer']*f['fiss']+.09*f['gold']*f['engr'],.20*f['cyan']*f['fiss']+.13*f['violet']*f['engr']))-.10*f['dark'][:,:,None],0,1)
 if not b:return a,f
 p=.39+.61*np.clip(.36*f['facet']+.27*f['sat']+.22*f['fiss']+.15*f['engr'],0,1);b=.012*a+np.dstack((.46+.49*f['gold']+.26*f['violet'],.31+.58*f['emer']+.30*f['gold'],.17+.51*f['cyan']+.34*f['violet']))*p[:,:,None];return np.clip(b,0,1),f
def _spec(f):
 m=_q(np.clip(.30*f['gold']+.25*f['emer']+.20*f['cyan']+.16*f['violet']+.09*f['engr'],0,1),(7,34,72,109,148,187,224,253));r=_q(np.clip(.38*f['dark']+.26*f['fiss']+.21*f['engr']+.15*f['gold'],0,1),(5,29,61,99,140,179,220,251));c=_q(np.clip(.32*f['facet']+.24*f['sat']+.19*f['emer']+.15*f['gold']+.10*f['fiss'],0,1),(6,31,66,104,143,181,217,254));return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);t=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);t.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':t,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'chrysina_gold_asset_i2'),indent=2))
