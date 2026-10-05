# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Coral Stamen I3, fractured fan-lacquer candidate.

SPB-105 / owner doctrine tick 2026-08-27.  I2 is literal photographed coral,
grit and tendrils, not a car finish.  I3 is an authored coral-red performance
livery: asymmetric tapered stamen fans, black fracture roots, fine inner vein
etches, narrow cyan foil cuts and small champagne collar breaks.  Metal derives
from warm/cool inlay pigment, roughness from fan-vein abrasion, and clearcoat
from fan-bay tension direction.  No biology photograph, random grain, shared
Wilds composer, tile border or palette-only rescue.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fbl_coral_stamen"; NATIVE = 2048
M_T=np.asarray((7,29,56,88,123,163,207,251),np.uint8)
R_T=np.asarray((13,39,68,102,140,181,219,248),np.uint8)
C_T=np.asarray((5,26,54,84,120,159,207,252),np.uint8)

def _norm(a):
    a=a.astype(np.float32); return (a-a.min())/(a.max()-a.min()+1e-8)
def _tier(a,t): return t[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2]/'assets'/'generated'/'wilds'/'coral_stamen_livery_i3.png'

@lru_cache(maxsize=2)
def _fields():
    raw=cv2.imread(str(_asset()),cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    rgb=cv2.cvtColor(cv2.resize(raw,(NATIVE,NATIVE),interpolation=cv2.INTER_LANCZOS4),cv2.COLOR_BGR2RGB).astype(np.float32)/255.
    hsv=cv2.cvtColor(np.uint8(rgb*255),cv2.COLOR_RGB2HSV).astype(np.float32)
    sat=hsv[:,:,1]/255.; lum=.2126*rgb[:,:,0]+.7152*rgb[:,:,1]+.0722*rgb[:,:,2]
    gx=cv2.Sobel(lum,cv2.CV_32F,1,0,ksize=3); gy=cv2.Sobel(lum,cv2.CV_32F,0,1,ksize=3)
    seam=_norm(np.hypot(gx,gy)); vein=_norm(np.abs(lum-cv2.GaussianBlur(lum,(0,0),1.1)))
    abrasion=_norm(np.abs(cv2.GaussianBlur(lum,(0,0),2.1)-cv2.GaussianBlur(lum,(0,0),8.5)))
    bay=_norm(cv2.GaussianBlur(lum,(0,0),18.0)); bgx=cv2.Sobel(bay,cv2.CV_32F,1,0,ksize=3); bgy=cv2.Sobel(bay,cv2.CV_32F,0,1,ksize=3)
    heading=(np.arctan2(bgy,bgx)+np.pi)/(2*np.pi); tension=_norm(np.hypot(bgx,bgy)); cross=_norm(np.abs(.69*gx+.72*gy))
    coral=np.clip((rgb[:,:,0]+.34*rgb[:,:,1]-1.04*rgb[:,:,2]-.06)/.43,0,1)
    ember=np.clip((rgb[:,:,0]+.72*rgb[:,:,1]-1.18*rgb[:,:,2]-.10)/.38,0,1)
    cyan=np.clip((rgb[:,:,2]+.48*rgb[:,:,1]-1.15*rgb[:,:,0]-.07)/.44,0,1)
    champagne=np.clip((lum-.48+.15*(1-sat))/.33,0,1)
    inlay=_norm(np.maximum(coral,ember)+.62*cyan+.42*champagne+.20*seam)
    return {'rgb':rgb,'sat':sat,'lum':lum,'seam':seam,'vein':vein,'abrasion':abrasion,'bay':bay,'heading':heading,'tension':tension,'cross':cross,'coral':coral,'ember':ember,'cyan':cyan,'champagne':champagne,'inlay':inlay}

def _paint(angle_b=False):
    f=_fields(); a=np.clip(f['rgb']*.83+np.dstack((.14*f['ember']+.07*f['champagne'],.08*f['coral']+.07*f['cyan'],.12*f['cyan']+.06*f['champagne'])),0,1)
    if not angle_b:return a,f
    # Angle B flips foil only: red fans/release roots remain named, while cyan
    # and violet optical response advances through the same inner vein cuts.
    b=a*.24+np.dstack((.43*f['coral']+.19*f['champagne'],.13*f['cyan']+.11*f['ember'],.63*f['cyan']+.26*f['coral']+.18*f['champagne']))
    b+=np.dstack((.05*f['seam'],.06*f['vein'],.14*f['cross']));return np.clip(b,0,1),f

def _material(f):
    metal=_norm(.52*f['inlay']+.25*f['champagne']+.19*f['cyan']+.18*_norm(cv2.GaussianBlur(f['inlay'],(0,0),7.0)))
    rough=_norm(.48*f['vein']+.30*f['abrasion']+.25*f['cross']+.19*_norm(cv2.GaussianBlur(f['abrasion'],(0,0),4.0)))
    clear=_norm(.56*f['heading']+.24*f['tension']+.17*f['bay']-.15*f['abrasion']+.17*_norm(cv2.GaussianBlur(f['tension'],(0,0),13.0)))
    return np.stack((_tier(metal,M_T),_tier(rough,R_T),_tier(clear,C_T)),2)
def _authored():p,f=_paint(False);return p,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(d):
 d.mkdir(parents=True,exist_ok=True);ts=[];hs=[];last=None
 for _ in range(3):
  clear_cache();q=time.perf_counter();a,f=_paint(False);b,_=_paint(True);s=_material(f);ts.append(time.perf_counter()-q);hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,x in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(('metal','rough','clearcoat')):cv2.imwrite(str(d/f'{ID}_{n}_2048.png'),s[:,:,i])
 corr=np.corrcoef(s.reshape(-1,3).astype(np.float32),rowvar=False);o={'id':ID,'timings_s':ts,'deterministic':len(set(hs))==1,'spec_std':[float(s[:,:,i].std())for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],'spec_corr_m_r_cc':[float(corr[0,1]),float(corr[0,2]),float(corr[1,2])],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2),encoding='utf8');return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'coral_stamen_livery_i3'),indent=2))
