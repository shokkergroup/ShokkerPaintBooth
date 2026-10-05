# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Coral Cluster I3, fractured velocity livery.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Coral denotes a coordinated
coral-orange cluster of high-energy lacquer breaks—not literal coral, biology,
or microscopy.  Unequal acceleration cuts, black release channels, restrained
cyan fracture lips, and short engraved strata make it a full-car race graphic.
This source intentionally has neither a hub-and-spoke cluster nor Magenta
Mosaic's plate/mosaic topology.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fbl_coral_cluster"; NATIVE = 2048
def _q(a, v): return np.asarray(v, np.uint8)[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "coral_cluster_i3.png"

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
    coral = np.clip((1.22*x[:, :, 0] + .59*x[:, :, 1] - .74*x[:, :, 2] - .45)/.40, 0, 1)
    ember = np.clip((1.20*x[:, :, 0] - .49*x[:, :, 1] - .18*x[:, :, 2] - .27)/.48, 0, 1)
    cyan = np.clip((-.48*x[:, :, 0] + 1.05*x[:, :, 1] + 1.14*x[:, :, 2] - .59)/.33, 0, 1)
    violet = np.clip((1.04*x[:, :, 0] - .48*x[:, :, 1] + .98*x[:, :, 2] - .48)/.36, 0, 1)
    teal = np.clip((-.54*x[:, :, 0] + 1.18*x[:, :, 1] + 1.10*x[:, :, 2] - .28)/.68, 0, 1)
    cobalt = np.clip((-.31*x[:, :, 0] + .24*x[:, :, 1] + 1.18*x[:, :, 2] - .30)/.58, 0, 1)
    purple = np.clip((.78*x[:, :, 0] - .43*x[:, :, 1] + 1.13*x[:, :, 2] - .32)/.56, 0, 1)
    return dict(x=x, sat=sat, rim=rim, ribbon=ribbon, detail=detail, field=field, dark=dark, coral=coral, ember=ember, cyan=cyan, violet=violet, teal=teal, cobalt=cobalt, purple=purple)

def _paint(b=False):
    f = _f()
    a = np.clip(f['x']*.63 + np.dstack((.20*f['coral']*f['rim'] + .13*f['ember']*f['detail'], .10*f['coral']*f['ribbon'] + .09*f['cyan']*f['rim'], .17*f['cyan']*f['ribbon'] + .07*f['violet']*f['detail'])) - .11*f['dark'][:, :, None], 0, 1)
    if not b: return a, f
    p = .31 + .69*np.clip(.38*f['field']+.24*f['sat']+.22*f['ribbon']+.16*f['rim'],0,1)
    b = .018*a + np.dstack((.10+.30*f['purple']+.18*f['cobalt'], .13+.57*f['teal']+.13*f['purple'], .21+.55*f['cobalt']+.29*f['purple']))*p[:, :, None]
    return np.clip(b, 0, 1), f

def _spec(f):
    # This is a Coral-specific three-channel recipe: metallic favors coral lips,
    # roughness favors black releases and brushed strata, clearcoat favors broad
    # acceleration fields.  It is intentionally unlike the Mosaic source maps.
    m = _q(np.clip(.36*f['coral']+.21*f['cyan']+.17*f['ember']+.15*f['rim']+.11*f['detail'], 0, 1), (7,34,72,109,148,187,224,253))
    r = _q(np.clip(.39*f['dark']+.26*f['ribbon']+.20*f['detail']+.15*(1-f['field']), 0, 1), (5,29,61,99,140,179,220,251))
    c = _q(np.clip(.39*f['field']+.24*f['coral']+.17*f['sat']+.12*f['rim']+.08*f['cyan'], 0, 1), (6,31,66,104,143,181,217,254))
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
if __name__ == "__main__": print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"coral_cluster_asset_i3"),indent=2))
