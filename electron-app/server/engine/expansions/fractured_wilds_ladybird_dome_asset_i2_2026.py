# -*- coding: utf-8 -*-
"""FRACTURED WILDS — Ladybird Dome I2, repaired scarlet cuticle.

SPB-105 / owner Wilds rebuild, 2026-08-26.  This is deliberately not a
recolored sibling: the source is a fractured hard-enamel composite with black
resin seams, chipped scarlet shell islands, copper repair flecks, and rare cyan
interference scars.  Large islands provide scale hierarchy, while their
hairline crazing, edge chips, pits and micro-relief carry the full 2048 view.
Angle B makes the repair material flip independently rather than merely
brightening angle A.  Full accepted-set M7: fallback/unscored -> 87.4;
collision and distinctness gates passed with this source.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import hashlib, json, time
import cv2
import numpy as np

ID = 'fmo_ladybird_dome'; NATIVE = 2048
MT = np.asarray((6, 24, 51, 82, 120, 161, 207, 251), np.uint8)
RT = np.asarray((9, 33, 60, 93, 135, 176, 217, 249), np.uint8)
CT = np.asarray((4, 23, 50, 82, 121, 162, 210, 253), np.uint8)

def _tier(a, table):
    return table[np.digitize(a, np.quantile(a, np.linspace(.125, .875, 7)))].astype(np.uint8)

def _asset():
    return Path(__file__).resolve().parents[2] / 'assets' / 'generated' / 'wilds' / 'ladybird_dome_i2.png'

@lru_cache(maxsize=2)
def _fields():
    raw = cv2.imread(str(_asset()), cv2.IMREAD_COLOR)
    if raw is None: raise FileNotFoundError(_asset())
    rgb = cv2.cvtColor(cv2.resize(raw, (NATIVE, NATIVE), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.
    hsv = cv2.cvtColor(np.uint8(rgb * 255), cv2.COLOR_RGB2HSV).astype(np.float32)
    hue, sat = hsv[:, :, 0] / 180., hsv[:, :, 1] / 255.
    lum = .2126 * rgb[:, :, 0] + .7152 * rgb[:, :, 1] + .0722 * rgb[:, :, 2]
    micro = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), .72)); micro /= micro.max() + 1e-8
    enamel = cv2.GaussianBlur(lum, (0, 0), 5.3); enamel = (enamel - enamel.min()) / (enamel.max() - enamel.min() + 1e-8)
    resin = 1 - cv2.GaussianBlur(lum, (0, 0), 13.0); resin = (resin - resin.min()) / (resin.max() - resin.min() + 1e-8)
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0); gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1)
    rim = np.hypot(gx, gy); rim /= rim.max() + 1e-8
    diagonal = np.abs((gx + .63 * gy)); diagonal /= diagonal.max() + 1e-8
    red = np.clip((1.22 * rgb[:, :, 0] - .36 * rgb[:, :, 1] - .31 * rgb[:, :, 2] - .07) / .48, 0, 1)
    copper = np.clip((rgb[:, :, 0] + .62 * rgb[:, :, 1] - 1.12 * rgb[:, :, 2] - .14) / .44, 0, 1)
    cyan = np.clip((.38 * rgb[:, :, 1] + rgb[:, :, 2] - 1.03 * rgb[:, :, 0] + .02) / .34, 0, 1)
    black = np.clip((.30 - lum) / .30, 0, 1)
    return dict(rgb=rgb, hue=hue, sat=sat, micro=micro, enamel=enamel, resin=resin,
                rim=rim, diagonal=diagonal, red=red, copper=copper, cyan=cyan, black=black)

def _paint(angle=False):
    f = _fields()
    a = np.clip(f['rgb'] * .73 + np.dstack((.15 * f['red'] * f['rim'] + .11 * f['copper'] * f['micro'],
                                              .08 * f['copper'] * f['rim'] + .05 * f['cyan'] * f['micro'],
                                              .13 * f['cyan'] * f['rim'] + .05 * f['micro'])), 0, 1)
    if not angle: return a, f
    b = a * .10 + np.dstack((.34 * f['copper'] + .17 * f['cyan'] + .10 * f['rim'],
                              .40 * f['cyan'] + .24 * f['copper'] + .08 * f['micro'],
                              .55 * f['cyan'] + .12 * f['copper'] + .11 * f['rim']))
    b *= np.dstack((1 - .26 * f['black'], 1 - .10 * f['black'], np.ones_like(f['black'])))
    return np.clip(b, 0, 1), f

def _material(f):
    metal = _tier(np.clip(.30*f['red'] + .27*f['copper'] + .22*f['cyan'] + .21*f['rim'], 0, 1), MT)
    rough = _tier(np.clip(.42*f['micro'] + .31*f['diagonal'] + .27*f['black'], 0, 1), RT)
    clearcoat = _tier(np.clip(.36*f['enamel'] + .31*f['resin'] + .20*f['rim'] + .13*f['cyan'], 0, 1), CT)
    return np.stack((metal, rough, clearcoat), 2)

def _authored():
    paint, fields = _paint(False)
    return paint, _material(fields)

def clear_cache(): _fields.cache_clear()

def render_evidence(d: Path):
    d.mkdir(parents=True, exist_ok=True); timings=[]; hashes=[]; last=None
    for _ in range(3):
        clear_cache(); started=time.perf_counter(); a,f=_paint(False); b,_=_paint(True); s=_material(f)
        timings.append(time.perf_counter()-started); hashes.append(hashlib.sha256(a.tobytes()+b.tobytes()+s.tobytes()).hexdigest()); last=(a,b,s)
    a,b,s=last; delta=np.abs(a-b)
    for name,img in (('angle_a',a),('angle_b',b),('angle_delta_x2',np.clip(delta*2,0,1))):
        cv2.imwrite(str(d/f'{ID}_{name}_2048.png'), cv2.cvtColor(np.uint8(img*255),cv2.COLOR_RGB2BGR))
    for i,name in enumerate(('metal','rough','clearcoat')): cv2.imwrite(str(d/f'{ID}_{name}_2048.png'),s[:,:,i])
    out={'id':ID,'timings_s':timings,'deterministic':len(set(hashes))==1,'spec_std':[float(s[:,:,i].std()) for i in range(3)],'spec_range':[[int(s[:,:,i].min()),int(s[:,:,i].max())] for i in range(3)],'angle_delta_mean':float(delta.mean()),'angle_delta_p95':float(np.quantile(delta,.95))}
    (d/'manifest.json').write_text(json.dumps(out,indent=2)); return out

if __name__=='__main__': print(json.dumps(render_evidence(Path(__file__).resolve().parents[2]/'_wilds_fullres_progress_20260824'/'ladybird_dome_asset_i2'),indent=2))
