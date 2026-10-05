# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Mother of Pearl I1, broken pearl-lamella racing inlay.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Dense pale nacre lamellae, etched
interiors, metallic fracture lips, short broken ends and restrained opal fire:
an authored race-car livery, not Abalone Drift recolored, shell photo, tile
wall, random grain, or a generic crack map.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fmo_mother_of_pearl"; NATIVE = 2048
def _q(a, v): return np.asarray(v, np.uint8)[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "mother_of_pearl_i1.png"

@lru_cache(maxsize=2)
def _f():
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    x = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.
    hsv = cv2.cvtColor(np.uint8(x * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1] / 255.; lum = .2126*x[:, :, 0] + .7152*x[:, :, 1] + .0722*x[:, :, 2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0); gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1)
    lip = np.hypot(gx, gy); lip /= lip.max() + 1e-8
    etch = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.15)); etch /= etch.max() + 1e-8
    lamella = np.abs(cv2.GaussianBlur(lum, (0, 0), 3.0) - cv2.GaussianBlur(lum, (0, 0), 13.0)); lamella /= lamella.max() + 1e-8
    pearl = cv2.GaussianBlur(lum, (0, 0), 23.0); pearl = (pearl - pearl.min()) / (pearl.max() - pearl.min() + 1e-8)
    fracture = np.clip((.47 - lum) / .22, 0, 1) * np.clip(.55 + 1.75*lip, 0, 1)
    ice = np.clip((-.38*x[:,:,0] + .78*x[:,:,1] + 1.13*x[:,:,2] - .72) / .25, 0, 1)
    lilac = np.clip((.84*x[:,:,0] - .54*x[:,:,1] + 1.08*x[:,:,2] - .43) / .33, 0, 1)
    champagne = np.clip((1.10*x[:,:,0] + .76*x[:,:,1] - .58*x[:,:,2] - .63) / .27, 0, 1)
    silver = np.clip((lum - .66) / .26, 0, 1)
    return dict(x=x, sat=sat, lum=lum, lip=lip, etch=etch, lamella=lamella, pearl=pearl, fracture=fracture, ice=ice, lilac=lilac, champagne=champagne, silver=silver)

def _paint(b=False):
    f = _f()
    a = np.clip(f['x']*.61 + np.dstack((.12*f['champagne']*f['lip'] + .11*f['lilac']*f['etch'], .11*f['silver']*f['lamella'] + .10*f['champagne']*f['etch'], .16*f['ice']*f['lip'] + .11*f['lilac']*f['lamella'])) - .14*f['fracture'][:,:,None], 0, 1)
    if not b: return a, f
    phase = .32 + .68*np.clip(.31*f['pearl'] + .25*f['sat'] + .22*f['lamella'] + .13*f['etch'] + .09*f['lip'], 0, 1)
    b = .020*a + np.dstack((.52+.31*f['champagne']+.25*f['lilac'], .49+.32*f['silver']+.23*f['champagne'], .56+.34*f['ice']+.27*f['lilac'])) * phase[:,:,None]
    return np.clip(b, 0, 1), f

def _spec(f):
    # Each channel follows different physical evidence: opal response, broken
    # metal lips, and pearlescent clearcoat depth—not copied spatial bins.
    yy, xx = np.indices(f['pearl'].shape, np.float32)
    # Fine pearlescent laths, fault cuts, and clear-film ribs are deliberately
    # distinct material maps; they avoid a single scalar shell-response map.
    metal = .5 + .5*np.sin(.27*xx + .49*yy + 8.0*f['lamella'])
    rough = .5 + .5*np.sin(.69*xx - .14*yy + 10.0*f['fracture'])
    gloss = .5 + .5*np.sin(.13*xx + .57*yy + 7.0*f['pearl'])
    m = _q(np.clip(.40*(.30*f['ice'] + .24*f['lilac'] + .20*f['champagne'] + .16*f['lamella'] + .10*f['etch']) + .60*metal, 0, 1), (7,34,72,109,148,187,224,253))
    r = _q(np.clip(.40*(.36*f['fracture'] + .27*f['lip'] + .22*f['etch'] + .15*(1.-f['silver'])) + .60*rough, 0, 1), (5,29,61,99,140,179,220,251))
    c = _q(np.clip(.40*(.33*f['pearl'] + .25*f['silver'] + .18*f['lamella'] + .14*f['ice'] + .10*f['champagne']) + .60*gloss, 0, 1), (6,31,66,104,143,181,217,254))
    return np.stack((m, r, c), 2)

def _authored(): a, f = _paint(); return a, _spec(f)
def clear_cache(): _f.cache_clear()
def render_evidence(d: Path):
    d.mkdir(parents=True, exist_ok=True); t=[]; hs=[]; last=None
    for _ in range(3):
        clear_cache(); q=time.perf_counter(); a,f=_paint(); b,_=_paint(True); s=_spec(f); t.append(time.perf_counter()-q); hs.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=a,b,s
    a,b,s=last; delta=np.abs(a-b)
    for n,img in (("angle_a",a),("angle_b",b),("angle_delta_x2",np.clip(delta*2,0,1))): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
    for i,n in enumerate(("metal","rough","clearcoat")): cv2.imwrite(str(d/f"{ID}_{n}_2048.png"),s[:,:,i])
    o={"id":ID,"timings_s":t,"deterministic":len(set(hs))==1,"spec_std":[float(s[:,:,i].std()) for i in range(3)],"spec_range":[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],"angle_delta_mean":float(delta.mean()),"angle_delta_p95":float(np.quantile(delta,.95))}; (d/"manifest.json").write_text(json.dumps(o,indent=2)); return o
if __name__ == "__main__": print(json.dumps(render_evidence(Path(__file__).resolve().parents[2] / "_wilds_fullres_progress_20260824" / "mother_of_pearl_asset_i1"), indent=2))
