# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Petri Magenta Plankton I3, luminous dazzle lacquer.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Plankton is expressed through
luminous deep-water magenta/violet color behavior—not literal organisms,
cells, or sparkles.  Black dazzle corridors, broken magenta stencils, cyan
phosphor registrations, champagne fracture slivers and fine etched insets form
a full-car racing livery distinct from Pollen's woven brush bundles.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fpe_magenta_plankton"; NATIVE = 2048
def _q(a, v): return np.asarray(v, np.uint8)[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "magenta_plankton_i3.png"

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
    magenta = np.clip((1.13*x[:, :, 0] - .38*x[:, :, 1] + .88*x[:, :, 2] - .55)/.36, 0, 1)
    cyan = np.clip((-.48*x[:, :, 0] + 1.05*x[:, :, 1] + 1.14*x[:, :, 2] - .59)/.33, 0, 1)
    violet = np.clip((1.04*x[:, :, 0] - .48*x[:, :, 1] + .98*x[:, :, 2] - .48)/.36, 0, 1)
    teal = np.clip((-.54*x[:, :, 0] + 1.18*x[:, :, 1] + 1.10*x[:, :, 2] - .28)/.68, 0, 1)
    cobalt = np.clip((-.31*x[:, :, 0] + .24*x[:, :, 1] + 1.18*x[:, :, 2] - .30)/.58, 0, 1)
    purple = np.clip((.78*x[:, :, 0] - .43*x[:, :, 1] + 1.13*x[:, :, 2] - .32)/.56, 0, 1)
    return dict(x=x, sat=sat, rim=rim, ribbon=ribbon, detail=detail, field=field, dark=dark, magenta=magenta, violet=violet, cyan=cyan, teal=teal, cobalt=cobalt, purple=purple)

def _paint(b=False):
    f = _f()
    a = np.clip(f['x']*.62 + np.dstack((.24*f['magenta']*f['rim'] + .12*f['violet']*f['detail'], .12*f['magenta']*f['ribbon'] + .10*f['cyan']*f['rim'], .16*f['violet']*f['ribbon'] + .12*f['magenta']*f['detail'])) - .10*f['dark'][:, :, None], 0, 1)
    if not b: return a, f
    p = .28 + .72*np.clip(.34*f['field']+.27*f['sat']+.22*f['ribbon']+.17*f['rim'],0,1)
    b = .014*a + np.dstack((.10+.36*f['purple']+.17*f['cobalt'], .12+.55*f['teal']+.13*f['purple'], .25+.51*f['cobalt']+.31*f['purple']))*p[:, :, None]
    return np.clip(b, 0, 1), f

def _spec(f):
    # Plankton's channel design keeps the spec causal: bright phosphor stencil
    # faces are metallic; etched insets and black corridors roughen; broad
    # dazzle fields carry clearcoat. This is independent of every Bloom source.
    yy, xx = np.indices(f['field'].shape, np.float32)
    metal = .5 + .5*np.sin(.48*xx + .28*yy + 8.0*f['cyan'])
    rough = .5 + .5*np.sin(.18*xx - .59*yy + 10.0*f['dark'])
    gloss = .5 + .5*np.sin(.39*xx + .39*yy + 7.0*f['violet'])
    m = _q(np.clip(.40*(.33*f['magenta']+.24*f['cyan']+.19*f['violet']+.14*f['rim']+.10*f['detail'])+.60*metal, 0, 1), (10,34,66,96,127,157,186,215))
    r = _q(np.clip(.40*(.38*f['dark']+.25*f['detail']+.22*f['ribbon']+.15*(1-f['field']))+.60*rough, 0, 1), (12,35,60,85,110,135,165,195))
    c = _q(np.clip(.40*(.36*f['field']+.23*f['magenta']+.19*f['sat']+.13*f['ribbon']+.09*f['violet'])+.60*gloss, 0, 1), (6,31,66,104,143,181,217,254))
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
if __name__ == "__main__": print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"magenta_plankton_asset_i3"),indent=2))
