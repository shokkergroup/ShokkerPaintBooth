# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Batwing I2, texture-backed close membrane material.

SPB-105 / owner Wilds rebuild, 2026-08-25. I1's analytic tension singularities
were rejected. I2 is a versioned, generated native-scale close-membrane asset
(``assets/generated/wilds/batwing_membrane_i2.png``), selected specifically
for its full-coverage 8–32px leathery corrugations, healed micro-tears and
attached copper/cyan stress flashes. The builder derives independent physical
M/R/Cc ownership from luminance relief, micro-roughness and cool/warm stress
responses; it does not synthesize noise, recolour a legacy finish, or reuse a
Wilds composer. A/B changes the optical owner of ridge highlights.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fc_batwing';NATIVE=2048
M_T=np.asarray((7,29,56,88,123,163,207,251),np.uint8);R_T=np.asarray((13,39,68,102,140,181,219,248),np.uint8);C_T=np.asarray((5,26,54,84,120,159,207,252),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'batwing_membrane_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 fine=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.15));fine/=fine.max()+1e-8
 broad=cv2.GaussianBlur(lum,(0,0),7.0);broad=(broad-broad.min())/(broad.max()-broad.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);ridge=np.hypot(gx,gy);ridge/=ridge.max()+1e-8
 cool=np.clip((rgb[:,:,2]-rgb[:,:,0]+.12)/.32,0,1);warm=np.clip((rgb[:,:,0]-.68*rgb[:,:,2]+.10)/.36,0,1)
 tear=np.clip(fine*(1-broad)*np.maximum(cool,warm),0,1)
 return {'rgb':rgb,'lum':lum,'fine':fine,'broad':broad,'ridge':ridge,'cool':cool,'warm':warm,'tear':tear}
def _paint(angle_b=False):
 f=_fields();rgb=f['rgb'];r=f['ridge'];cool=f['cool'];warm=f['warm'];tear=f['tear']
 if not angle_b:return rgb,f
 # B exposes cool interference on the same physical ridge system while copper
 # stress is suppressed; it is an optical ownership swap, never A hue rotation.
 b=rgb*.48+np.dstack((.08*warm+.08*r,.16*cool+.05*r,.35*cool+.17*r))
 b+=np.dstack((.12*tear,.03*tear,.18*tear));return np.clip(b,0,1),f
def _material(f):
 m=.44*f['warm']+.28*f['ridge']+.19*f['broad']+.14*f['tear']
 r=.48*f['fine']+.29*(1-f['broad'])+.23*f['tear']+.15*f['ridge']-.13*f['cool']
 c=.43*f['cool']+.31*f['ridge']*(1-f['tear'])+.24*f['broad']-.18*f['fine']
 return np.stack((_tier(m,M_T),_tier(r,R_T),_tier(c,C_T)),2)
def _authored():p,f=_paint(False);return p,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):
  clear_cache();q=time.perf_counter();a,f=_paint(False);b,_=_paint(True);s=_material(f);ts.append(time.perf_counter()-q);hs.append(hashlib.sha256(np.ascontiguousarray(a).tobytes()+np.ascontiguousarray(b).tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 co=np.corrcoef(s.reshape(-1,3).astype(np.float32),rowvar=False);out={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'spec_corr_m_r_cc':[float(co[0,1]),float(co[0,2]),float(co[1,2])],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(out,indent=2),encoding='utf8');return out
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'batwing_membrane_asset_i2'),indent=2))
