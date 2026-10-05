# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Ammolite Skin I2, fractured fossil suture cuticle.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This replaces the rejected macro
ammonite/chamber study with a close mineral cuticle: fine suture filaments,
calcite bridge tissue, prism-grain terraces, healed fracture boundaries and
dark organic remnants.  It is neither a shell outline nor a repeated tile
field.  Fine mineral marks remain when crushed while bounded mineral drifts
make the named fossil material legible at full 2048 resolution.
Full accepted-set M7: fallback/unscored -> 90.0; collision and distinctness
gates passed with this independent source.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
import cv2,numpy as np
ID='fmo_ammolite_skin';NATIVE=2048
def _q(a,values):return np.asarray(values,np.uint8)[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset():return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'ammolite_skin_i2.png'
@lru_cache(maxsize=2)
def _fields():
 raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
 if raw is None:raise FileNotFoundError(_asset())
 rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
 hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32);sat=hsv[:,:,1]/255.;lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
 gx=cv2.Sobel(lum,cv2.CV_32F,1,0);gy=cv2.Sobel(lum,cv2.CV_32F,0,1);edge=np.hypot(gx,gy);edge/=edge.max()+1e-8
 suture=np.abs(gx*.77-gy*.61);suture/=suture.max()+1e-8
 terrace=np.abs(gx*.43+gy*.90);terrace/=terrace.max()+1e-8
 grain=np.abs(lum-cv2.GaussianBlur(lum,(0,0),.75));grain/=grain.max()+1e-8
 seam=cv2.GaussianBlur(edge,(0,0),3.6);seam=(seam-seam.min())/(seam.max()-seam.min()+1e-8)
 mineral=cv2.GaussianBlur(lum,(0,0),12.0);mineral=(mineral-mineral.min())/(mineral.max()-mineral.min()+1e-8)
 emerald=np.clip((.02*rgb[:,:,0]+1.14*rgb[:,:,1]+.47*rgb[:,:,2]-.38)/.54,0,1)
 cobalt=np.clip((.04*rgb[:,:,0]+.42*rgb[:,:,1]+1.20*rgb[:,:,2]-.40)/.57,0,1)
 fire=np.clip((1.18*rgb[:,:,0]+.43*rgb[:,:,1]-.75*rgb[:,:,2]-.25)/.52,0,1)
 gold=np.clip((1.10*rgb[:,:,0]+.74*rgb[:,:,1]-.30*rgb[:,:,2]-.43)/.45,0,1)
 dark=np.clip((.30-lum)/.30,0,1)
 return dict(rgb=rgb,sat=sat,edge=edge,suture=suture,terrace=terrace,grain=grain,seam=seam,mineral=mineral,emerald=emerald,cobalt=cobalt,fire=fire,gold=gold,dark=dark)
def _paint(angle=False):
 f=_fields();a=np.clip(f['rgb']*.62+np.dstack((.20*f['fire']*f['terrace']+.12*f['gold']*f['seam'],.20*f['emerald']*f['terrace']+.10*f['gold']*f['grain'],.23*f['cobalt']*f['suture']+.10*f['emerald']*f['seam']))-.06*f['dark'][:,:,None],0,1)
 if not angle:return a,f
 # Facets reverse their visible interference order at grazing angle; mineral
 # bridges remain gold while cobalt/emerald suture planes turn electric.
 phase=.48+.52*f['mineral']
 b=a*.012+np.dstack((.12+.30*f['fire']+.26*f['gold']+.14*f['seam'],.22+.53*f['emerald']+.25*f['gold']+.16*f['terrace'],.40+.68*f['cobalt']+.27*f['emerald']+.15*f['suture']))*phase[:,:,None];return np.clip(b,0,1),f
def _material(f):
 # Each material channel is tied to different fossil physics: metallic prism
 # faces, rough damaged suture/cavity walls, and clear sealed calcite fields.
 metal=_q(np.clip(.29*f['cobalt']+.25*f['emerald']+.20*f['fire']+.16*f['terrace']+.10*f['grain'],0,1),(9,36,74,109,146,181,219,251))
 rough=_q(np.clip(.34*f['suture']+.29*f['seam']+.22*f['grain']+.15*f['dark'],0,1),(7,28,57,94,137,177,221,249))
 clearcoat=_q(np.clip(.33*f['mineral']+.25*f['gold']+.18*f['emerald']+.14*f['edge']+.10*f['sat'],0,1),(5,31,69,105,143,180,217,253))
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
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'ammolite_skin_asset_i2'),indent=2))
