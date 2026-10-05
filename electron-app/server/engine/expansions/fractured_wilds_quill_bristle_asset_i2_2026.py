# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Quill Bristle I2, fractured cryptid quill coat.

SPB-105 / owner Wilds rebuild, 2026-08-26. Fine quill shafts, hooked tips,
follicle rings and pebbled under-hide are distinct causal creature marks.
Their shaft/host/follicle responses provide the fractured color flip without
recolouring a shared map or inventing random separation.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np

ID='fc_quill_bristle';NATIVE=2048
M_T=np.asarray((6,27,51,82,119,159,205,251),np.uint8);R_T=np.asarray((12,37,66,101,139,179,218,248),np.uint8);C_T=np.asarray((4,25,52,83,118,158,207,252),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'quill_bristle_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 barb=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.0));barb/=barb.max()+1e-8
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);shaft=np.hypot(gx,gy);shaft/=shaft.max()+1e-8
 direction=(np.arctan2(gy,gx)+np.pi)/(2*np.pi)
 hide=cv2.GaussianBlur(lum,(0,0),7.0);hide=(hide-hide.min())/(hide.max()-hide.min()+1e-8)
 teal=np.clip((rgb[:,:,2]-.56*rgb[:,:,0]+.08)/.42,0,1);bronze=np.clip((rgb[:,:,0]-.52*rgb[:,:,2]+.10)/.38,0,1)
 follicle=np.clip(barb*(1-hide),0,1)
 return {'rgb':rgb,'barb':barb,'shaft':shaft,'direction':direction,'hide':hide,'teal':teal,'bronze':bronze,'follicle':follicle}
def _paint(angle_b=False):
 f=_fields();rgb=f['rgb'];a=np.clip(rgb+np.dstack((.16*f['bronze']*f['barb'],.06*f['follicle'],.21*f['teal']*f['barb'])),0,1)
 if not angle_b:return a,f
 b=a*.25+np.dstack((.09*f['bronze']+.07*f['shaft'],.10*f['follicle']+.06*f['barb'],.58*f['teal']+.14*f['shaft']))
 return np.clip(b,0,1),f
def _material(f):
 m=.73*f['bronze']+.27*f['shaft']
 # Quill direction is a true physical roughness axis: shafts that turn away
 # from the grazing light broaden their highlight independently of color.
 r=.72*f['direction']+.28*f['hide']
 c=.76*f['teal']+.24*f['barb']
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'quill_bristle_asset_i2'),indent=2))
