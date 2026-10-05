"""Butter Pollen I7 — laminar microfoil candidate; SPB-105 2026-08-27.

I3 was a literal botanical/microscopy collage; I5 over-corrected into sparse
gold shards.  I7 treats the name as butter-gold microfoil carried in aerodynamic
flow: dense analytic 8–32px filaments, attached split dashes, fracture lips,
cross-cuts and interrupted glints.  It contains no noise layer or detached
particle scatter, and each material channel has its own physical cause.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fbl_butter_pollen"; NATIVE = 2048
M = np.asarray((7, 33, 67, 104, 142, 181, 219, 253), np.uint8)
R = np.asarray((5, 30, 61, 99, 140, 179, 220, 251), np.uint8)
C = np.asarray((6, 32, 65, 103, 143, 181, 217, 254), np.uint8)
TAU = np.float32(2*np.pi)
def _norm(a):
    a=a.astype(np.float32); return (a-a.min())/(a.max()-a.min()+1e-8)
def _tier(a,v): return v[np.digitize(a,np.quantile(a,np.linspace(.125,.875,7)))].astype(np.uint8)
def _line(phase, width): return np.clip((np.cos(phase)-width)/(1-width+1e-8),0,1)

@lru_cache(maxsize=2)
def _fields():
    yy,xx=np.mgrid[:NATIVE,:NATIVE].astype(np.float32); x=xx/NATIVE; y=yy/NATIVE
    # Two nonparallel advected coordinate systems are the carrier; all mark
    # families attach to them, so this cannot devolve into generic confetti.
    u=x+.075*np.sin(TAU*(1.7*y+.17*np.sin(TAU*(2.3*x-y))))+.028*np.sin(TAU*(7.1*y-3.2*x))
    v=y+.061*np.sin(TAU*(1.3*x+.19*np.sin(TAU*(1.8*y+x))))-.023*np.sin(TAU*(6.4*x+2.1*y))
    bank=.5+.5*np.sin(TAU*(2.35*u-1.42*v+.13*np.sin(TAU*(3.2*u+v))))
    filament=_line(TAU*(34.0*u+2.2*np.sin(TAU*(2.7*v))),.825)
    filament2=_line(TAU*(27.0*v-1.6*np.sin(TAU*(3.1*u))),.875)
    # Fine broken bodies are phase-gated on the filament family, never free dots.
    gate=np.clip(.52+.48*np.sin(TAU*(8.2*v+1.7*u+.18*np.sin(TAU*5.1*u))),0,1)
    dash=filament*np.clip((gate-.49)/.51,0,1)
    cross=filament2*np.clip((.54-.5*np.cos(TAU*(11.0*u-2.0*v))-.20)/.34,0,1)
    split=_line(TAU*(51.0*u+13.0*v+.6*np.sin(TAU*3.0*v)),.955)*np.clip(bank*.9+.05,0,1)
    microcut=_line(TAU*(63.0*v-9.0*u+.3*np.sin(TAU*6.0*u)),.978)*filament
    lip=_norm(np.maximum(cv2.Sobel(filament+cross,cv2.CV_32F,1,0),0)+np.maximum(cv2.Sobel(dash+split,cv2.CV_32F,0,1),0))
    body=np.clip(.60*filament+.46*dash+.34*cross+.22*bank-.28*split,0,1)
    release=np.clip(.70*split+.48*microcut+.25*(1-bank),0,1)
    direction=np.abs(np.sin(TAU*(.61*u+.39*v+.16*bank)))
    polish=_norm(.55*bank+.30*direction+.15*np.cos(TAU*(4.3*u-2.2*v)))
    return dict(body=body,dash=dash,cross=cross,split=split,microcut=microcut,lip=lip,release=release,bank=bank,direction=direction,polish=polish)

def _paint(angle_b=False):
    f=_fields(); black=np.dstack((.012+.026*f['bank'],.014+.019*f['bank'],.020+.028*f['bank']))
    gold=np.dstack((.70*f['body']+.25*f['dash'],.44*f['body']+.36*f['cross'],.055*f['body']+.12*f['dash']))
    pearl=np.dstack((.30*f['cross']+.18*f['lip'],.24*f['cross']+.22*f['lip'],.13*f['cross']+.28*f['lip']))
    a=np.clip(black+gold+pearl-np.dstack((.20*f['release'],.12*f['release'],.05*f['release'])),0,1)
    if not angle_b:return a,f
    # Fixed laminar topology; only the exposed foil changes ownership in B.
    foil=np.dstack((.25*f['split']+.20*f['lip'],.58*f['lip']+.16*f['cross'],.74*f['lip']+.42*f['split']))
    b=np.clip(a*.22+foil+np.dstack((.20*f['body']+.10*f['bank'],.10*f['body']+.16*f['dash'],.05*f['cross']+.11*f['bank']))-.05*f['release'][:,:,None],0,1)
    return b,f

def _material(f):
    metal=_norm(.49*f['body']+.27*f['dash']+.20*f['cross']+.17*f['lip']-.16*f['release'])
    rough=_norm(.46*f['microcut']+.28*f['split']+.22*f['direction']+.18*f['release']-.17*f['lip'])
    # Clearcoat follows the laminar polish current, independent of the gold
    # body/metal and cut/roughness narratives (SPB-105 spec doctrine).
    clear=_norm(.48*f['polish']+.31*_norm(cv2.GaussianBlur(f['lip'],(0,0),9))+.21*f['bank']-.14*f['microcut'])
    return np.stack((_tier(metal,M),_tier(rough,R),_tier(clear,C)),2)

def _authored():a,f=_paint();return a,_material(f)
def clear_cache():_fields.cache_clear()
def render_evidence(directory:Path):
    directory.mkdir(parents=True,exist_ok=True); timings=[]; hashes=[]; last=None
    for _ in range(3):
        clear_cache(); start=time.perf_counter(); a,f=_paint(); b,_=_paint(True); s=_material(f); timings.append(time.perf_counter()-start); hashes.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
    a,b,s=last;delta=np.abs(a-b)
    for name,image in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))):cv2.imwrite(str(directory/f"{ID}_{name}_2048.png"),cv2.cvtColor(np.uint8(image*255),cv2.COLOR_RGB2BGR))
    for index,name in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(directory/f"{ID}_{name}_2048.png"),s[:,:,index])
    corr=np.corrcoef(s.reshape(-1,3).astype(np.float32),rowvar=False); report={"id":ID,"timings_s":timings,"deterministic":len(set(hashes))==1,"spec_std":[float(s[:,:,i].std()) for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],"spec_corr_m_r_cc":[float(corr[0,1]),float(corr[0,2]),float(corr[1,2])],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))};(directory/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf8");return report
if __name__=="__main__":print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"butter_pollen_laminar_i7"),indent=2))
