# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Bog Murk I2, peat current and wet-film fire.

SPB-105 / owner Wilds rebuild, 2026-08-26. Peat sediment currents, broken
bioluminescent wet-film veins, tiny gas glints and hairline silt fractures are
causal source marks—not cells, pavers or generic noise. A/B changes the deep
peat and teal/amber wet-film constituents; M/R/Cc remain distinct responses.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fc_bog_murk';NATIVE=2048
M_T=np.asarray((8,30,54,86,123,162,206,250),np.uint8);R_T=np.asarray((12,38,66,101,140,180,219,248),np.uint8);C_T=np.asarray((5,27,55,85,121,160,208,252),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'bog_murk_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 glint=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.1));glint/=glint.max()+1e-8
 silt=cv2.GaussianBlur(lum,(0,0),13.0);silt=(silt-silt.min())/(silt.max()-silt.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);vein=np.hypot(gx,gy);vein/=vein.max()+1e-8
 teal=np.clip((rgb[:,:,2]-.42*rgb[:,:,0]+.05)/.34,0,1)
 moss=np.clip((rgb[:,:,1]-.47*rgb[:,:,0]+.04)/.34,0,1)
 amber=np.clip((rgb[:,:,0]+.34*rgb[:,:,1]-.91*rgb[:,:,2]+.04)/.33,0,1)
 peat=np.clip((.36-lum)/.33,0,1)
 return {'rgb':rgb,'glint':glint,'silt':silt,'vein':vein,'teal':teal,'moss':moss,'amber':amber,'peat':peat}
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']+np.dstack((.10*f['amber']*f['glint'],.11*f['moss']*f['glint'],.16*f['teal']*f['glint'])),0,1)
 if not angle:return a,f
 b=a*.22+np.dstack((.31*f['amber']+.08*f['vein'],.35*f['moss']+.07*f['glint'],.49*f['teal']+.11*f['glint']))
 return np.clip(b,0,1),f
def _material(f):
 # Amber wet-film metal, slow silt roughness and teal/moss clearcoat bloom
 # are separated causal fields rather than a shared spec texture.
 m=.62*f['amber']+.25*f['glint']+.13*f['vein']
 r=.75*f['silt']+.25*f['peat']
 c=.59*f['teal']+.41*f['moss']
 return np.stack((_tier(m,M_T),_tier(r,R_T),_tier(c,C_T)),2)
def _authored():p,f=_paint(False);return p,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):
  clear_cache();q=time.perf_counter();a,f=_paint(False);b,_=_paint(True);s=_material(f);ts.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'bog_murk_asset_i2'),indent=2))
