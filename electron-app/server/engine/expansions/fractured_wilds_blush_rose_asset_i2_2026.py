# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Blush Rose I2, couture motorsport lacquer.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Rose is expressed as blush and
burgundy lacquer, not literal botanical illustration: asymmetric wrap bands,
carbon releases, short printed hatches, champagne fault-lips, and cyan
registration marks form a legible race-car graphic.  The source crop excludes
the generated vignette so a dark card frame cannot appear when the pattern is
scaled or tiled.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fbl_blush_rose"; NATIVE = 2048
def _q(a, v): return np.asarray(v, np.uint8)[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "blush_rose_i2.png"

@lru_cache(maxsize=2)
def _f():
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    # Deliberately remove the source's outer vignette before any material math:
    # a card-edge treatment must never become a tiled livery border.
    raw = raw[96:-96, 96:-96]
    x = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.
    hsv = cv2.cvtColor(np.uint8(x * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1] / 255.; lum = .2126*x[:, :, 0] + .7152*x[:, :, 1] + .0722*x[:, :, 2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0); gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1)
    rim = np.hypot(gx, gy); rim /= rim.max() + 1e-8
    ribbon = np.abs(.82*gx + .57*gy); ribbon /= ribbon.max() + 1e-8
    detail = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.45)); detail /= detail.max() + 1e-8
    field = cv2.GaussianBlur(lum, (0, 0), 12.0); field = (field-field.min())/(field.max()-field.min()+1e-8)
    dark = np.clip((.31-lum)/.31, 0, 1)
    blush = np.clip((1.03*x[:, :, 0] + .65*x[:, :, 1] + .40*x[:, :, 2] - .82)/.24, 0, 1)
    burgundy = np.clip((1.18*x[:, :, 0] - .41*x[:, :, 1] + .23*x[:, :, 2] - .38)/.40, 0, 1)
    cyan = np.clip((-.48*x[:, :, 0] + 1.05*x[:, :, 1] + 1.14*x[:, :, 2] - .59)/.33, 0, 1)
    violet = np.clip((1.04*x[:, :, 0] - .48*x[:, :, 1] + .98*x[:, :, 2] - .48)/.36, 0, 1)
    teal = np.clip((-.54*x[:, :, 0] + 1.18*x[:, :, 1] + 1.10*x[:, :, 2] - .28)/.68, 0, 1)
    cobalt = np.clip((-.31*x[:, :, 0] + .24*x[:, :, 1] + 1.18*x[:, :, 2] - .30)/.58, 0, 1)
    purple = np.clip((.78*x[:, :, 0] - .43*x[:, :, 1] + 1.13*x[:, :, 2] - .32)/.56, 0, 1)
    return dict(x=x, sat=sat, rim=rim, ribbon=ribbon, detail=detail, field=field, dark=dark, blush=blush, burgundy=burgundy, cyan=cyan, violet=violet, teal=teal, cobalt=cobalt, purple=purple)

def _paint(b=False):
    f = _f()
    a = np.clip(f['x']*.66 + np.dstack((.18*f['blush']*f['rim'] + .17*f['burgundy']*f['detail'], .12*f['blush']*f['ribbon'] + .08*f['cyan']*f['rim'], .14*f['cyan']*f['ribbon'] + .10*f['violet']*f['detail'])) - .07*f['dark'][:, :, None], 0, 1)
    if not b: return a, f
    p = .30 + .70*np.clip(.36*f['field']+.25*f['sat']+.22*f['ribbon']+.17*f['rim'],0,1)
    b = .018*a + np.dstack((.16+.39*f['purple']+.14*f['cobalt'], .10+.55*f['teal']+.12*f['purple'], .25+.47*f['cobalt']+.36*f['purple']))*p[:, :, None]
    return np.clip(b, 0, 1), f

def _spec(f):
    # Independent Blush Rose material topology: metallic tracks exposed blush
    # and registration lips, roughness sits in carbon/hatch releases, while
    # clearcoat follows the broad wrap bands rather than Mosaic plate centers.
    yy, xx = np.indices(f['field'].shape, np.float32)
    # Couture pin-lips, carbon hatches, and satin ribs remain separate in
    # M/R/Cc so the visual Fractured breakup survives under material response.
    metal = .5 + .5*np.sin(.46*xx + .24*yy + 9.0*f['blush'])
    rough = .5 + .5*np.sin(.16*xx - .66*yy + 10.0*f['dark'])
    gloss = .5 + .5*np.sin(.34*xx + .47*yy + 7.0*f['burgundy'])
    m = _q(np.clip(.40*(.34*f['blush']+.24*f['cyan']+.18*f['rim']+.14*f['detail']+.10*f['burgundy'])+.60*metal, 0, 1), (7,34,72,109,148,187,224,253))
    r = _q(np.clip(.40*(.36*f['dark']+.27*f['detail']+.22*f['ribbon']+.15*(1-f['field']))+.60*rough, 0, 1), (5,29,61,99,140,179,220,251))
    c = _q(np.clip(.40*(.37*f['field']+.25*f['blush']+.18*f['sat']+.12*f['rim']+.08*f['burgundy'])+.60*gloss, 0, 1), (6,31,66,104,143,181,217,254))
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
if __name__ == "__main__": print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"blush_rose_asset_i2"),indent=2))
