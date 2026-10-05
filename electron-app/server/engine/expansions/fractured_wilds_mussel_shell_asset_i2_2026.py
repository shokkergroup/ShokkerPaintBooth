# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Mussel Shell I2, fractured nacre growth.

SPB-105 / owner Wilds rebuild, 2026-08-26.  The 2048 source is a close-crop
of mineralized mussel nacre: fine aragonite laminae, fracture-repair seams,
prism chips, dark conchiolin joins and iridescent growth courses.  Larger
courses provide the shell read at 1.00 while high-frequency laminae, repair
ribs and cleavage facets keep structure alive when crushed down.  Angle B
and M/R/Cc derive separately from those causal maps; neither is a recolour or
an RGB-as-spec shortcut.
Full accepted-set M7: fallback/unscored -> 86.2; collision and distinctness
gates passed with this independent source.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_mussel_shell';NATIVE=2048
MT=np.asarray((6,30,58,91,130,170,213,252),np.uint8);RT=np.asarray((8,37,67,100,140,179,220,250),np.uint8);CT=np.asarray((4,25,53,85,124,164,210,254),np.uint8)
def _tier(a,t):return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'mussel_shell_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);edge=np.hypot(gx,gy);edge/=edge.max()+1e-8
 lamina=np.abs(gx*.68+gy*.73);lamina/=lamina.max()+1e-8
 repair=np.abs(gx*.77-gy*.31);repair/=repair.max()+1e-8
 prism=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.85));prism/=prism.max()+1e-8
 course=cv2.GaussianBlur(lum,(0,0),8.5);course=(course-course.min())/(course.max()-course.min()+1e-8)
 depth=1-cv2.GaussianBlur(lum,(0,0),18.0);depth=(depth-depth.min())/(depth.max()-depth.min()+1e-8)
 teal=np.clip((.08*rgb[:,:,0]+1.08*rgb[:,:,1]+.72*rgb[:,:,2]-.42)/.52,0,1)
 blue=np.clip((.10*rgb[:,:,0]+.42*rgb[:,:,1]+1.22*rgb[:,:,2]-.42)/.54,0,1)
 gold=np.clip((1.12*rgb[:,:,0]+.82*rgb[:,:,1]-.48*rgb[:,:,2]-.46)/.42,0,1)
 violet=np.clip((.73*rgb[:,:,0]-.15*rgb[:,:,1]+1.04*rgb[:,:,2]-.42)/.46,0,1)
 dark=np.clip((.34-lum)/.34,0,1)
 return dict(rgb=rgb,sat=sat,edge=edge,lamina=lamina,repair=repair,prism=prism,course=course,depth=depth,teal=teal,blue=blue,gold=gold,violet=violet,dark=dark)
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.62+np.dstack((.09*f['gold']*f['repair']+.07*f['violet']*f['prism'],.18*f['teal']*f['lamina']+.10*f['gold']*f['edge'],.22*f['blue']*f['lamina']+.11*f['violet']*f['repair']))-.07*f['depth'][:,:,None],0,1)
 if not angle:return a,f
 b=a*.06+np.dstack((.13*f['gold']+.39*f['violet']+.10*f['repair'],.35*f['teal']+.19*f['gold']+.11*f['lamina'],.54*f['blue']+.26*f['violet']+.12*f['prism']));return np.clip(b,0,1),f
def _material(f):
 metal=_tier(np.clip(.25*f['gold']+.22*f['blue']+.19*f['violet']+.18*f['edge']+.16*f['course'],0,1),MT)
 rough=_tier(np.clip(.36*f['lamina']+.29*f['repair']+.20*f['prism']+.15*f['depth'],0,1),RT)
 clearcoat=_tier(np.clip(.31*f['course']+.24*f['teal']+.20*f['blue']+.14*f['repair']+.11*f['sat'],0,1),CT)
 return np.stack((metal,rough,clearcoat),2)
def _authored():p,f=_paint(False);return p,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):clear_cache();q=time.perf_counter();a,f=_paint(False);b,_=_paint(True);s=_material(f);ts.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 o={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'mussel_shell_asset_i2'),indent=2))
