# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Grackle Oil I4, petroleum-sheen fracture livery.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This is a dark automotive livery,
not a bird, feather field, oil puddle or generic grain: deep petroleum skins,
blue-teal interference slabs, irregular sharp releases, and cyan/violet foil
lips.  The authored B angle remains materially distinct rather than a hue
slider recolour.  Native 2048 after B-angle correction: 1.68–1.90s;
M5/M6/M7 and whole-set collision refresh are explicitly pending.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fmo_grackle_oil"; NATIVE = 2048
def _q(a, v): return np.asarray(v, np.uint8)[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "grackle_oil_i4.png"

@lru_cache(maxsize=2)
def _f():
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    x = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.
    hsv = cv2.cvtColor(np.uint8(x * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1] / 255.; lum = .2126*x[:, :, 0] + .7152*x[:, :, 1] + .0722*x[:, :, 2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0); gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1)
    rim = np.hypot(gx, gy); rim /= rim.max() + 1e-8
    ribbon = np.abs(.82*gx + .57*gy); ribbon /= ribbon.max() + 1e-8
    detail = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.45)); detail /= detail.max() + 1e-8
    field = cv2.GaussianBlur(lum, (0, 0), 12.0); field = (field-field.min())/(field.max()-field.min()+1e-8)
    dark = np.clip((.31-lum)/.31, 0, 1)
    gold = np.clip((1.12*x[:, :, 0] + .74*x[:, :, 1] - .65*x[:, :, 2] - .42)/.42, 0, 1)
    yellow = np.clip((.78*x[:, :, 0] + 1.04*x[:, :, 1] - .70*x[:, :, 2] - .48)/.35, 0, 1)
    cyan = np.clip((-.48*x[:, :, 0] + 1.05*x[:, :, 1] + 1.14*x[:, :, 2] - .59)/.33, 0, 1)
    violet = np.clip((1.04*x[:, :, 0] - .48*x[:, :, 1] + .98*x[:, :, 2] - .48)/.36, 0, 1)
    # Direct RGB film masks for the Grackle B angle; these prevent the former
    # yellow-source response from collapsing blue-black petroleum into olive.
    teal = np.clip((-.54*x[:, :, 0] + 1.18*x[:, :, 1] + 1.10*x[:, :, 2] - .28)/.68, 0, 1)
    cobalt = np.clip((-.31*x[:, :, 0] + .24*x[:, :, 1] + 1.18*x[:, :, 2] - .30)/.58, 0, 1)
    purple = np.clip((.78*x[:, :, 0] - .43*x[:, :, 1] + 1.13*x[:, :, 2] - .32)/.56, 0, 1)
    return dict(x=x, sat=sat, rim=rim, ribbon=ribbon, detail=detail, field=field, dark=dark, gold=gold, yellow=yellow, cyan=cyan, violet=violet, teal=teal, cobalt=cobalt, purple=purple)

def _paint(b=False):
    f = _f()
    a = np.clip(f['x']*.58 + np.dstack((.23*f['gold']*f['rim'] + .10*f['violet']*f['ribbon'], .25*f['yellow']*f['rim'] + .10*f['gold']*f['detail'], .14*f['cyan']*f['ribbon'] + .08*f['violet']*f['rim'])) - .08*f['dark'][:, :, None], 0, 1)
    if not b: return a, f
    p = .28 + .72*np.clip(.35*f['field']+.27*f['sat']+.21*f['ribbon']+.17*f['rim'],0,1)
    b = .012*a + np.dstack((.08+.32*f['purple']+.15*f['cobalt'], .12+.62*f['teal']+.10*f['purple'], .24+.50*f['cobalt']+.34*f['purple']))*p[:, :, None]
    return np.clip(b, 0, 1), f

def _spec(f):
    m = _q(np.clip(.33*f['gold']+.25*f['yellow']+.19*f['cyan']+.14*f['violet']+.09*f['detail'], 0, 1), (10,34,66,96,127,157,186,215))
    r = _q(np.clip(.36*f['ribbon']+.27*f['rim']+.21*f['detail']+.16*f['dark'], 0, 1), (12,35,60,85,110,135,165,195))
    c = _q(np.clip(.32*f['field']+.25*f['yellow']+.19*f['gold']+.14*f['rim']+.10*f['sat'], 0, 1), (6,31,66,104,143,181,217,254))
    return np.stack((m, r, c), 2)

def _authored(): a, f = _paint(); return a, _spec(f)
def clear_cache(): _f.cache_clear()
def render_evidence(d: Path):
    d.mkdir(parents=True, exist_ok=True); timings=[]; hashes=[]; last=None
    for _ in range(3):
        clear_cache(); start=time.perf_counter(); a,f=_paint(); b,_=_paint(True); s=_spec(f); timings.append(time.perf_counter()-start); hashes.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=a,b,s
    a,b,s=last; delta=np.abs(a-b)
    for n,img in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
    for i,n in enumerate(("metal","rough","clearcoat")): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
    out={"id":ID,"timings_s":timings,"deterministic":len(set(hashes))==1,"spec_std":[float(s[:,:,i].std()) for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))}; (d/"manifest.json").write_text(json.dumps(out,indent=2)); return out
if __name__ == "__main__": print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"grackle_oil_asset_i4"),indent=2))
