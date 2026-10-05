# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Butter Whorl I1, broken brush-lacquer livery.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This is a dense motorsport
surface of interrupted butter-gold pull strokes, short hooked bristles,
black enamel voids and tiny cyan/lilac foil turns—not pollen, cells, a
macro pinwheel, random grain, or a framed image.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fbl_butter_whorl"; NATIVE = 2048
def _q(a, v): return np.asarray(v, np.uint8)[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "butter_whorl_i1.png"

@lru_cache(maxsize=2)
def _f():
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    x = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.
    hsv = cv2.cvtColor(np.uint8(x * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1] / 255.; lum = .2126*x[:,:,0] + .7152*x[:,:,1] + .0722*x[:,:,2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0); gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1)
    lip = np.hypot(gx, gy); lip /= lip.max() + 1e-8
    bristle = np.abs(.61*gx - .79*gy); bristle /= bristle.max() + 1e-8
    filament = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.0)); filament /= filament.max() + 1e-8
    sweep = cv2.GaussianBlur(lum, (0, 0), 17.0); sweep = (sweep-sweep.min())/(sweep.max()-sweep.min()+1e-8)
    enamel = np.clip((.17-lum)/.17, 0, 1)
    butter = np.clip((1.10*x[:,:,0] + .95*x[:,:,1] - .72*x[:,:,2] - .47)/.36, 0, 1)
    oldgold = np.clip((1.12*x[:,:,0] + .57*x[:,:,1] - .63*x[:,:,2] - .40)/.42, 0, 1)
    teal = np.clip((-.58*x[:,:,0] + 1.08*x[:,:,1] + 1.20*x[:,:,2] - .60)/.34, 0, 1)
    lilac = np.clip((1.00*x[:,:,0] - .49*x[:,:,1] + 1.08*x[:,:,2] - .51)/.34, 0, 1)
    return dict(x=x, sat=sat, lip=lip, bristle=bristle, filament=filament, sweep=sweep, enamel=enamel, butter=butter, oldgold=oldgold, teal=teal, lilac=lilac)

def _paint(b=False):
    f = _f()
    a = np.clip(f['x']*.57 + np.dstack((.25*f['oldgold']*f['lip']+.15*f['lilac']*f['bristle'], .27*f['butter']*f['lip']+.11*f['oldgold']*f['filament'], .23*f['teal']*f['bristle']+.14*f['lilac']*f['lip']))-.10*f['enamel'][:,:,None], 0, 1)
    if not b: return a, f
    phase = .39 + .61*np.clip(.36*f['sweep']+.28*f['sat']+.22*f['bristle']+.14*f['filament'], 0, 1)
    b = .010*a + np.dstack((.43+.50*f['butter']+.27*f['lilac'], .31+.53*f['oldgold']+.28*f['butter'], .15+.58*f['teal']+.30*f['lilac']))*phase[:,:,None]
    return np.clip(b, 0, 1), f

def _spec(f):
    m = _q(np.clip(.30*f['butter']+.24*f['oldgold']+.20*f['teal']+.17*f['lilac']+.09*f['filament'],0,1),(7,34,72,109,148,187,224,253))
    r = _q(np.clip(.35*f['enamel']+.28*f['bristle']+.22*f['lip']+.15*f['filament'],0,1),(5,29,61,99,140,179,220,251))
    c = _q(np.clip(.33*f['sweep']+.25*f['sat']+.20*f['butter']+.13*f['oldgold']+.09*f['lip'],0,1),(6,31,66,104,143,181,217,254))
    return np.stack((m,r,c),2)

def _authored(): a, f = _paint(); return a, _spec(f)
def clear_cache(): _f.cache_clear()
def render_evidence(d: Path):
    d.mkdir(parents=True, exist_ok=True); timings=[]; hashes=[]; last=None
    for _ in range(3):
        clear_cache(); started=time.perf_counter(); a,f=_paint(); b,_=_paint(True); s=_spec(f); timings.append(time.perf_counter()-started); hashes.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=a,b,s
    a,b,s=last; delta=np.abs(a-b)
    for n,img in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
    for i,n in enumerate(("metal","rough","clearcoat")): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
    out={"id":ID,"timings_s":timings,"deterministic":len(set(hashes))==1,"spec_std":[float(s[:,:,i].std()) for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))}; (d/"manifest.json").write_text(json.dumps(out,indent=2)); return out
if __name__ == "__main__": print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"butter_whorl_asset_i1"),indent=2))
