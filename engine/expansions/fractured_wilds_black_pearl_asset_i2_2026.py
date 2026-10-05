# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Black Pearl I2, folded nacre orient.

SPB-105 / owner Wilds rebuild, 2026-08-26.  A black pearl is neither a scale
field nor generic sparkles: its topology is densely ribbed nacre growth that
folds over a black body, with naturally fractured joins and angle-owned orient.
The code maintains those source structures in every material response.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np

ID='fmo_black_pearl';NATIVE=2048
M_T=np.asarray((8,30,55,87,124,164,207,249),np.uint8);R_T=np.asarray((11,38,65,100,139,179,218,247),np.uint8);C_T=np.asarray((5,28,54,86,121,160,206,252),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'black_pearl_orient_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 ribs=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.1));ribs/=ribs.max()+1e-8
 flow=cv2.GaussianBlur(lum,(0,0),10.0);flow=(flow-flow.min())/(flow.max()-flow.min()+1e-8)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);join=np.hypot(gx,gy);join/=join.max()+1e-8
 direction=np.arctan2(gy,gx)
 # The local rib direction is an authentic nacre constituent: adjacent folds
 # turn the pearly highlight differently as a panel moves under light.
 grain_a=.5+.5*np.sin(3.0*direction+.45)
 grain_b=.5+.5*np.cos(5.0*direction-.70)
 cyan=np.clip((rgb[:,:,2]-.55*rgb[:,:,0]+.08)/.38,0,1);rose=np.clip((rgb[:,:,0]-.58*rgb[:,:,1]+.10)/.38,0,1)
 pearl=np.clip((rgb[:,:,1]+.42*rgb[:,:,2]-.76*rgb[:,:,0]+.08)/.48,0,1)
 return {'rgb':rgb,'ribs':ribs,'flow':flow,'join':join,'grain_a':grain_a,'grain_b':grain_b,'cyan':cyan,'rose':rose,'pearl':pearl}
def _paint(angle_b=False):
 f=_fields();rgb=f['rgb']
 # Nacre's fine ribs catch separate glints from the broad folds. This adds
 # actual source-owned orient detail that still settles into a clear low-scale
 # charcoal/peacock read, per the owner's scale clarification.
 a=np.clip(rgb+np.dstack((.12*f['rose']*f['ribs'],.10*f['pearl']*f['ribs'],.16*f['cyan']*f['ribs'])),0,1)
 if not angle_b:return a,f
 # At the alternate angle cyan orient takes ownership and rose fold fire fades;
 # all three terms are tied to the same nacre folds/ribs, never hue-rotated.
 b=a*.28+np.dstack((.10*f['rose']+.06*f['join'],.26*f['pearl']+.07*f['ribs'],.58*f['cyan']+.12*f['ribs']))
 return np.clip(b,0,1),f
def _material(f):
 # Separate real constituents: rose orient = metal, dark fold depth = rough,
 # cyan orient = clearcoat. Quantile tiers create many physical responses
 # without a shared/recoloured spec-map shortcut.
 m=.76*f['rose']+.24*f['ribs']
 r=.74*f['grain_a']+.26*f['flow']
 c=.66*f['cyan']+.34*f['grain_b']
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'black_pearl_asset_i2'),indent=2))
