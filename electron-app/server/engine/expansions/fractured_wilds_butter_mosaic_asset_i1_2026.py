# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Butter Mosaic I1, fractured motorsport inlay.

SPB-105 / owner Wilds rebuild, 2026-08-26. Candidate source is a seamless,
asymmetric race-livery plate: butter-gold deck panels, charcoal split cuts,
cyan/violet foil slashes, inlay islands, and pinstripe runs. It deliberately
uses no stochastic grain, shared carrier, or one-shape recolor shortcut.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fbl_butter_mosaic"; NATIVE = 2048
def _q(a, v): return np.asarray(v, np.uint8)[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "butter_mosaic_i1.png"

@lru_cache(maxsize=2)
def _f():
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    x = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.
    hsv = cv2.cvtColor(np.uint8(x * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1] / 255.; lum = .2126*x[:, :, 0] + .7152*x[:, :, 1] + .0722*x[:, :, 2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0); gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1)
    rim = np.hypot(gx, gy); rim /= rim.max() + 1e-8
    cut = np.abs(.84*gx + .54*gy); cut /= cut.max() + 1e-8
    fine = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.3)); fine /= fine.max() + 1e-8
    field = cv2.GaussianBlur(lum, (0, 0), 15.0); field = (field-field.min())/(field.max()-field.min()+1e-8)
    dark = np.clip((.21-lum)/.21, 0, 1)
    gold = np.clip((1.12*x[:,:,0] + .82*x[:,:,1] - .75*x[:,:,2] - .41)/.38, 0, 1)
    orange = np.clip((1.18*x[:,:,0] + .42*x[:,:,1] - .62*x[:,:,2] - .47)/.36, 0, 1)
    cyan = np.clip((-.60*x[:,:,0] + 1.12*x[:,:,1] + 1.18*x[:,:,2] - .58)/.33, 0, 1)
    violet = np.clip((1.05*x[:,:,0] - .55*x[:,:,1] + 1.10*x[:,:,2] - .50)/.34, 0, 1)
    return dict(x=x, sat=sat, rim=rim, cut=cut, fine=fine, field=field, dark=dark, gold=gold, orange=orange, cyan=cyan, violet=violet)

def _paint(b=False):
    f = _f()
    a = np.clip(f['x']*.55 + np.dstack((.24*f['orange']*f['rim']+.15*f['violet']*f['cut'], .25*f['gold']*f['rim']+.09*f['orange']*f['fine'], .23*f['cyan']*f['cut']+.12*f['violet']*f['rim']))-.09*f['dark'][:,:,None], 0, 1)
    if not b: return a, f
    phase = .38 + .62*np.clip(.34*f['field']+.29*f['sat']+.22*f['cut']+.15*f['fine'], 0, 1)
    b = .012*a + np.dstack((.37+.52*f['gold']+.28*f['violet'], .28+.54*f['orange']+.25*f['gold'], .16+.56*f['cyan']+.31*f['violet']))*phase[:,:,None]
    return np.clip(b, 0, 1), f

def _spec(f):
    # Eight wide, intentionally less-extreme M/R tiers keep this rich graphic
    # coherent with its calm enamel paint; Cc remains the full flip carrier.
    m = _q(np.clip(.29*f['gold']+.23*f['orange']+.21*f['cyan']+.18*f['violet']+.09*f['fine'],0,1),(10,34,66,96,127,157,186,215))
    r = _q(np.clip(.35*f['dark']+.28*f['cut']+.22*f['rim']+.15*f['fine'],0,1),(12,35,60,85,110,135,165,195))
    c = _q(np.clip(.31*f['field']+.25*f['sat']+.19*f['gold']+.15*f['orange']+.10*f['rim'],0,1),(6,31,66,104,143,181,217,254))
    return np.stack((m,r,c),2)

def _authored(): a,f = _paint(); return a,_spec(f)
def clear_cache(): _f.cache_clear()
def render_evidence(d:Path):
    d.mkdir(parents=True,exist_ok=True); timings=[]; hashes=[]; last=None
    for _ in range(3):
        clear_cache(); start=time.perf_counter(); a,f=_paint(); b,_=_paint(True); s=_spec(f); timings.append(time.perf_counter()-start); hashes.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=a,b,s
    a,b,s=last; delta=np.abs(a-b)
    for n,img in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
    for i,n in enumerate(("metal","rough","clearcoat")): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
    out={"id":ID,"timings_s":timings,"deterministic":len(set(hashes))==1,"spec_std":[float(s[:,:,i].std()) for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))}; (d/"manifest.json").write_text(json.dumps(out,indent=2)); return out
if __name__ == "__main__": print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"butter_mosaic_asset_i1"),indent=2))
