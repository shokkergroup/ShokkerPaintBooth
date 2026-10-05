# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Cyan Membrane I3, stressed technical-film livery.

SPB-105 / owner Wilds rebuild, 2026-08-26.  Continuous cyan interference
film, tension folds, pinched seam junctions, optical crease grain and split
fracture lips form a scaleable automotive material—not cells, contour maps,
circuitry, stripes, an edge frame, or a noise substitute.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = "fpe_cyan_membrane"; NATIVE = 2048
def _q(a, v): return np.asarray(v, np.uint8)[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)
def _asset(): return Path(__file__).resolve().parents[2] / "assets" / "generated" / "wilds" / "cyan_membrane_i3.png"

@lru_cache(maxsize=2)
def _f():
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    x = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.
    hsv = cv2.cvtColor(np.uint8(x * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    sat = hsv[:, :, 1] / 255.; lum = .2126*x[:,:,0] + .7152*x[:,:,1] + .0722*x[:,:,2]
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0); gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1)
    seam = np.hypot(gx, gy); seam /= seam.max() + 1e-8
    tension = np.abs(.73*gx + .68*gy); tension /= tension.max() + 1e-8
    optic = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 1.15)); optic /= optic.max() + 1e-8
    film = cv2.GaussianBlur(lum, (0, 0), 23.0); film = (film-film.min())/(film.max()-film.min()+1e-8)
    shadow = np.clip((.12-lum)/.12, 0, 1)
    cyan = np.clip((-.62*x[:,:,0] + 1.06*x[:,:,1] + 1.20*x[:,:,2] - .53)/.37, 0, 1)
    blue = np.clip((-.40*x[:,:,0] + .20*x[:,:,1] + 1.20*x[:,:,2] - .44)/.39, 0, 1)
    aqua = np.clip((-.72*x[:,:,0] + 1.18*x[:,:,1] + .90*x[:,:,2] - .50)/.34, 0, 1)
    emerald = np.clip((-.48*x[:,:,0] + 1.15*x[:,:,1] + .30*x[:,:,2] - .44)/.33, 0, 1)
    return dict(x=x, sat=sat, seam=seam, tension=tension, optic=optic, film=film, shadow=shadow, cyan=cyan, blue=blue, aqua=aqua, emerald=emerald)

def _paint(b=False):
    f = _f()
    # SPB-105 / owner fine-detail doctrine, 2026-08-27: M5 finds the physical
    # material louder than the visible membrane. Expose more of the *same*
    # causal optical-fold response in paint; this is a fold-lip intensification,
    # not a new grain/noise layer or an RGB-as-spec workaround.
    a = np.clip(f['x']*.61 + np.dstack((.08*f['cyan']*f['seam']+.13*f['blue']*f['optic'], .21*f['aqua']*f['seam']+.20*f['emerald']*f['tension']+.18*f['aqua']*f['optic'], .29*f['blue']*f['tension']+.27*f['cyan']*f['optic']))-.08*f['shadow'][:,:,None], 0, 1)
    if not b: return a, f
    phase = .35 + .65*np.clip(.35*f['film']+.27*f['sat']+.23*f['tension']+.15*f['optic'], 0, 1)
    b = .010*a + np.dstack((.07+.42*f['cyan']+.22*f['emerald'], .35+.51*f['aqua']+.18*f['cyan'], .42+.50*f['blue']+.22*f['aqua']))*phase[:,:,None]
    return np.clip(b, 0, 1), f

def _spec(f):
    m = _q(np.clip(.31*f['cyan']+.24*f['blue']+.20*f['aqua']+.16*f['emerald']+.09*f['optic'],0,1),(7,34,72,109,148,187,224,253))
    r = _q(np.clip(.36*f['shadow']+.27*f['seam']+.22*f['tension']+.15*f['optic'],0,1),(5,29,61,99,140,179,220,251))
    c = _q(np.clip(.34*f['film']+.25*f['sat']+.18*f['blue']+.14*f['cyan']+.09*f['seam'],0,1),(6,31,66,104,143,181,217,254))
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
if __name__ == "__main__": print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/"_wilds_fullres_progress_20260824"/"cyan_membrane_asset_i3"),indent=2))
