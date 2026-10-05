# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Sasquatch Fur I3: engineered bristle-armour candidate.

SPB-105 / owner full-canvas doctrine tick 2026-08-27. I2 is a literal fibre
micrograph. I3 turns the name into an automotive mechanism: unequal pressure
banks built from packed hooked bristle blades, each with etched interiors,
dark releases, copper tips and cyan/violet optical cuts. It is not a photo,
random grain, a shared Wilds carrier or a palette-only variation.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID='fc_sasquatch_fur'; NATIVE=2048
MT=np.asarray((7,29,56,88,123,163,207,251),np.uint8)
RT=np.asarray((13,39,68,102,140,181,219,248),np.uint8)
CT=np.asarray((5,26,54,84,120,159,207,252),np.uint8)

def _norm(a):
 a=a.astype(np.float32); return (a-a.min())/(a.max()-a.min()+1e-8)
def _tier(a,t): return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'sasquatch_fur_livery_i3.png'

@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None: raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32)
 lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]; sat=hsv[:,:,1]/255.
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(lum,cv2.CV_32F,0,1,ksize=3)
 edge=_norm(np.hypot(gx,gy)); etch=_norm(np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.2)))
 bank=_norm(cv2.GaussianBlur(lum,(0,0),19.0)); bgx=cv2.Sobel(bank,cv2.CV_32F,1,0,ksize=3); bgy=cv2.Sobel(bank,cv2.CV_32F,0,1,ksize=3)
 heading=(np.arctan2(bgy,bgx)+np.pi)/(2*np.pi); tension=_norm(np.hypot(bgx,bgy)); rake=_norm(np.abs(.71*gx-.70*gy))
 cyan=np.clip((rgb[:,:,2]+.48*rgb[:,:,1]-1.10*rgb[:,:,0]-.08)/.40,0,1)
 violet=np.clip((rgb[:,:,2]+.27*rgb[:,:,0]-1.12*rgb[:,:,1]-.08)/.38,0,1)
 copper=np.clip((rgb[:,:,0]+.36*rgb[:,:,1]-1.14*rgb[:,:,2]-.12)/.38,0,1)
 foil=_norm(.63*cyan+.54*violet+.45*copper+.16*edge)
 return {'rgb':rgb,'edge':edge,'etch':etch,'bank':bank,'heading':heading,'tension':tension,'rake':rake,'cyan':cyan,'violet':violet,'copper':copper,'foil':foil}

def _paint(angle_b=False):
 f=_fields(); a=np.clip(f['rgb']*.78+np.dstack((.13*f['copper']+.05*f['violet'],.07*f['copper']+.08*f['cyan'],.17*f['cyan']+.12*f['violet'])),0,1)
 if not angle_b:return a,f
 # Angle flip resides in optical blade cuts; structural black bristle banks remain stable.
 b=a*.23+np.dstack((.26*f['copper']+.32*f['violet'],.15*f['cyan']+.14*f['copper'],.68*f['cyan']+.54*f['violet']+.10*f['edge']))
 return np.clip(b,0,1),f

def _material(f):
 metal=_norm(.57*f['foil']+.25*f['cyan']+.20*f['copper']+.17*_norm(cv2.GaussianBlur(f['foil'],(0,0),6.0)))
 rough=_norm(.50*f['etch']+.30*f['rake']+.24*f['edge']+.17*_norm(cv2.GaussianBlur(f['etch'],(0,0),4.0)))
 clear=_norm(.55*f['heading']+.26*f['tension']+.20*f['bank']-.17*f['etch']+.16*_norm(cv2.GaussianBlur(f['tension'],(0,0),13.0)))
 return np.stack((_tier(metal,MT),_tier(rough,RT),_tier(clear,CT)),2)

def _authored():
 p,f=_paint(False); return p,_material(f)
def clear_cache(): _fields.cache_clear()
def render_evidence(d):
 d.mkdir(parents=True,exist_ok=True); ts=[]; hs=[]; last=None
 for _ in range(3):
  clear_cache(); t=time.perf_counter(); a,f=_paint(False); b,_=_paint(True); s=_material(f); ts.append(time.perf_counter()-t); hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=a,b,s
 a,b,s=last; delta=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 co=np.corrcoef(s.reshape(-1,3).astype(np.float32),rowvar=False);out={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'spec_corr_m_r_cc':[float(co[0,1]),float(co[0,2]),float(co[1,2])],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(out,indent=2),encoding='utf8');return out
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'sasquatch_fur_livery_i3'),indent=2))
