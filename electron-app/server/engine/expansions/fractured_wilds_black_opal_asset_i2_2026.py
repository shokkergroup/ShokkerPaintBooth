# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Black Opal I2, pinfire in a cracked black host.

SPB-105 / owner Wilds rebuild, 2026-08-26. This deliberately avoids a wing,
scale, cell, or paving topology: the source is a dense field of tiny mineral
pinfire inclusions caught beneath black opal glass.  Every material channel is
derived from that same inclusion/seam topology; B exposes a different physical
view of the same fire rather than recolouring A or adding random separation.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np

ID='fmo_black_opal';NATIVE=2048
M_T=np.asarray((6,27,51,82,119,159,205,251),np.uint8);R_T=np.asarray((12,37,66,101,139,179,218,248),np.uint8);C_T=np.asarray((4,25,52,83,118,158,207,252),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'black_opal_pinfire_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 micro=np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.05));micro/=micro.max()+1e-8
 pin=np.maximum.reduce((rgb[:,:,0]-.55*rgb[:,:,1],rgb[:,:,1]-.45*rgb[:,:,0],rgb[:,:,2]-.52*rgb[:,:,1]));pin=np.clip(pin/.55,0,1)
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);seam=np.hypot(gx,gy);seam/=seam.max()+1e-8
 bed=cv2.GaussianBlur(lum,(0,0),8.0);bed=(bed-bed.min())/(bed.max()-bed.min()+1e-8)
 cyan=np.clip((rgb[:,:,2]-.56*rgb[:,:,0]+.08)/.42,0,1); ember=np.clip((rgb[:,:,0]-.42*rgb[:,:,2]+.05)/.42,0,1)
 green=np.clip((rgb[:,:,1]-.43*rgb[:,:,0]-.32*rgb[:,:,2]+.08)/.34,0,1)
 return {'rgb':rgb,'micro':micro,'pin':pin,'seam':seam,'bed':bed,'cyan':cyan,'ember':ember,'green':green}
def _paint(angle_b=False):
 f=_fields();rgb=f['rgb'];fire=np.maximum(f['cyan'],np.maximum(f['ember'],f['green']))
 # Recover the real sub-pixel mineral fire that the source's black host
 # otherwise hides: this is a source-derived optical microfacet lift, not
 # synthetic noise. It gives the material a stronger crushed-scale read.
 a=np.clip(rgb+np.dstack((.45*f['ember']*f['micro'],.25*f['green']*f['micro'],.60*f['cyan']*f['micro'])),0,1)
 if not angle_b:return a,f
 # Angle B lets blue-green pinfire dominate while red/amber fire retreats into
 # the black host; seams remain coupled to the same real mineral fracture map.
 b=a*.22+np.dstack((.08*f['ember']+.06*f['seam'],.31*f['green']+.05*f['micro'],.63*f['cyan']+.14*f['micro']))
 b+=np.dstack((.03*f['pin'],.05*fire,.10*f['pin']));return np.clip(b,0,1),f
def _material(f):
 # The three maps deliberately follow different physical constituents:
 # ember pinfire drives metal, the black host's depth drives roughness, and
 # cyan fire drives clearcoat.  This preserves the fine material while
 # preventing the lazy "same spec recoloured three ways" failure mode.
 m=.74*f['ember']+.26*f['micro']
 r=.72*f['bed']+.28*f['seam']
 c=.76*f['cyan']+.24*f['seam']
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'black_opal_asset_i2'),indent=2))
