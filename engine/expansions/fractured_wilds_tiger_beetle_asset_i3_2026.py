# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Tiger Beetle I3, worn enamel armor.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This is the opposite construction
to Emperor Scale's powdery plate field: broad black enamel armor is cut by
tawny abrasion channels, pitted with tiny dimples, and intermittently opened
to teal/violet fracture light.  The recognisable reduced-scale armor hierarchy
is supported by dense 8–32px pits, scratches, chips and ridge debris—not a
generic black-and-gold crack map or a recolored existing beetle.
SPB-105 gate movement: fallback/unscored to M7 88.3; collision and
distinctness gates are clean across the accepted set.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fmo_tiger_beetle"; NATIVE = 2048
def _asset(): return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "tiger_beetle_i3.png"
def _q(field, values): return np.asarray(values, np.uint8)[np.digitize(field, np.quantile(field, np.linspace(.125,.875,7)))].astype(np.uint8)

@lru_cache(maxsize=2)
def _f():
    raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    x=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.; h=cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2HSV).astype(np.float32)
    l=.2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]; gx=cv2.Sobel(l,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(l,cv2.CV_32F,0,1,ksize=3)
    rim=np.hypot(gx,gy); rim/=rim.max()+1e-8; scratch=np.abs(.48*gx-.88*gy); scratch/=scratch.max()+1e-8
    dimple=np.abs(l-cv2.GaussianBlur(l,(0,0),1.35)); dimple/=dimple.max()+1e-8; armor=cv2.GaussianBlur(l,(0,0),15.5); armor=(armor-armor.min())/(armor.max()-armor.min()+1e-8)
    black=np.clip((.29-l)/.29,0,1); copper=np.clip((1.20*x[:,:,0]+.54*x[:,:,1]-.44*x[:,:,2]-.38)/.47,0,1); teal=np.clip((-.45*x[:,:,0]+1.03*x[:,:,1]+1.04*x[:,:,2]-.50)/.40,0,1); violet=np.clip((.84*x[:,:,0]-.35*x[:,:,1]+1.16*x[:,:,2]-.47)/.42,0,1); blue=np.clip((.21*x[:,:,0]+.50*x[:,:,1]+1.13*x[:,:,2]-.50)/.39,0,1)
    return dict(x=x,sat=h[:,:,1]/255.,rim=rim,scratch=scratch,dimple=dimple,armor=armor,black=black,copper=copper,teal=teal,violet=violet,blue=blue)

def _paint(b=False):
    f=_f(); wear=np.clip(.39*f['rim']+.27*f['scratch']+.20*f['dimple']+.14*f['copper'],0,1)
    if not b:
        a=f['x']*.42+np.dstack((.39*f['copper']+.10*f['violet']*wear,.17*f['copper']+.17*f['teal']*wear,.20*f['blue']*wear+.16*f['violet']*wear))-.13*f['black'][:,:,None]; return np.clip(a,0,1),f
    flash=np.clip(.38*f['armor']+.30*f['rim']+.18*f['sat']+.14*f['dimple'],0,1)
    a=np.dstack((.22+.60*f['violet']+.27*f['copper'],.25+.63*f['teal']+.24*f['copper'],.38+.62*f['blue']+.46*f['violet']))*(.46+.54*flash[:,:,None])+.12*f['rim'][:,:,None]; return np.clip(a,0,1),f

def _spec(f):
    m=_q(np.clip(.31*f['teal']+.23*f['violet']+.19*f['blue']+.17*f['rim']+.10*f['copper'],0,1),(7,34,72,109,148,187,224,253))
    r=_q(np.clip(.36*f['dimple']+.29*f['scratch']+.22*f['black']+.13*f['rim'],0,1),(5,29,61,99,140,179,220,251))
    c=_q(np.clip(.32*f['armor']+.25*f['copper']+.18*f['rim']+.15*f['sat']+.10*f['blue'],0,1),(6,31,66,104,143,181,217,254))
    return np.stack((m,r,c),2)
def _authored(): a,f=_paint(); return a,_spec(f)
def clear_cache(): _f.cache_clear()
def render_evidence(d:Path):
    d.mkdir(parents=True,exist_ok=True); ts=[]; hs=[]; last=None
    for _ in range(3):
        clear_cache(); t=time.perf_counter(); a,f=_paint(); b,_=_paint(True); s=_spec(f); ts.append(time.perf_counter()-t); hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=a,b,s
    a,b,s=last; delta=np.abs(a-b)
    for n,q in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))): cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(q*255),cv2.COLOR_RGB2BGR))
    for i,n in enumerate(("metal","rough","clearcoat")): cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
    out={"id":ID,"timings_s":ts,"deterministic":len(set(hs))==1,"spec_std":[float(s[:,:,i].std()) for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))}; (d/'manifest.json').write_text(json.dumps(out,indent=2)); return out
if __name__=='__main__': print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'tiger_beetle_asset_i3'),indent=2))
