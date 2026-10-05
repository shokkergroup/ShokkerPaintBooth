# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Grackle Oil I3, schlieren oil-lacquer interference.

SPB-105 / owner Wilds rebuild, 2026-08-26.  A deterministic knife-edge
schlieren field gives this finish its fine physical refraction topology; it
is not a recoloured damascus, feather, cellular plate, or random-noise layer.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np
from engine.paint_v2.exotic_packs.pack_physical_fields import schlieren_refraction

ID = "fmo_grackle_oil"; NATIVE = 2048
def _q(a, v): return np.asarray(v, np.uint8)[np.digitize(a, np.quantile(a, np.linspace(.125,.875,7)))].astype(np.uint8)
@lru_cache(maxsize=2)
def _f():
    refraction = schlieren_refraction(NATIVE, NATIVE, 604903, res=384)
    micro = np.abs(refraction-cv2.GaussianBlur(refraction,(0,0),1.1)); micro /= micro.max()+1e-8
    broad = cv2.GaussianBlur(refraction,(0,0),19); broad=(broad-broad.min())/(broad.max()-broad.min()+1e-8)
    gx=cv2.Sobel(refraction,cv2.CV_32F,1,0); gy=cv2.Sobel(refraction,cv2.CV_32F,0,1)
    shock=np.hypot(gx,gy); shock/=shock.max()+1e-8
    twist=np.abs(.61*gx-.79*gy); twist/=twist.max()+1e-8
    return dict(refraction=refraction,micro=micro,broad=broad,shock=shock,twist=twist)
def _paint(b=False):
    f=_f(); r=f['refraction']; 
    # Oil-body A: black chrome with locally phase-locked green/cobalt/violet films.
    a=np.dstack((.028+.14*r+.20*f['twist']+.08*f['micro'], .038+.21*r+.42*f['shock']+.12*f['micro'], .047+.19*r+.49*f['twist']+.20*f['shock']))
    a += np.dstack((.23*f['shock']*f['twist'],.07*f['shock']*f['micro'],.19*f['shock']*f['micro']))
    a=np.clip(a,0,1)
    if not b:return a,f
    # Flip B is a distinct optical response, not an HSL recolour: emerald/gold/violet film phase.
    p=.24+.76*np.clip(.39*f['broad']+.31*f['twist']+.18*f['shock']+.12*f['micro'],0,1)
    b=.018*a+np.dstack((.20+.53*f['shock']+.31*f['twist'],.16+.61*f['broad']+.27*f['shock'],.28+.55*f['twist']+.22*f['micro']))*p[:,:,None]
    return np.clip(b,0,1),f
def _spec(f):
    m=_q(np.clip(.34*f['shock']+.27*f['twist']+.21*f['broad']+.18*f['micro'],0,1),(7,34,72,109,148,187,224,253))
    r=_q(np.clip(.37*(1-f['broad'])+.28*f['shock']+.22*f['micro']+.13*f['twist'],0,1),(5,29,61,99,140,179,220,251))
    c=_q(np.clip(.35*f['broad']+.25*f['twist']+.23*f['shock']+.17*f['micro'],0,1),(6,31,66,104,143,181,217,254))
    return np.stack((m,r,c),2)
def _authored():a,f=_paint();return a,_spec(f)
def clear_cache():_f.cache_clear()
def render_evidence(d:Path):
 d.mkdir(parents=True,exist_ok=True);times=[];hashes=[];last=None
 for _ in range(3):
  clear_cache();started=time.perf_counter();a,f=_paint();b,_=_paint(True);s=_spec(f);times.append(time.perf_counter()-started);hashes.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest());last=a,b,s
 a,b,s=last;delta=np.abs(a-b)
 for n,x in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(x*255),cv2.COLOR_RGB2BGR))
 for i,n in enumerate(("metal","rough","clearcoat")):cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
 o={"id":ID,"timings_s":times,"deterministic":len(set(hashes))==1,"spec_std":[float(s[:,:,i].std())for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())]for i in range(3)],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))};(d/'manifest.json').write_text(json.dumps(o,indent=2));return o
if __name__=='__main__':print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'grackle_oil_field_i3'),indent=2))
