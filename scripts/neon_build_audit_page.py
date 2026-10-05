# -*- coding: utf-8 -*-
"""Generate the current 25-finish Neon Underground audit from live shipping routes.

Swatch = 2-panel [LEFT paint | RIGHT paint x packed M/R/Cc under a sweeping light].
Re-runnable each round.
"""
import os, sys, time
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from spb_audit_page_builder import build_page
from engine.paint_v2 import flame_spec as fs
from engine.expansions.neon_catalog_2026 import LIVE_PAIRS, NEON_FINISHES

THUMB_DIR = os.path.join(ROOT, "thumbnails", "audit", "neon")
os.makedirs(THUMB_DIR, exist_ok=True)
def on_car(paint, spec):
    alb = np.clip(np.asarray(paint, np.float32), 0, 1)
    s = np.asarray(spec, np.float32)
    m, r, cc = s[..., 0] / 255, s[..., 1] / 255, s[..., 2] / 255
    H, W = m.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    Lc = (xx / (W - 1)) * 0.6 + (yy / (H - 1)) * 0.4
    band = np.clip(1.0 - np.abs(Lc - 0.52) * 2.0, 0, 1)
    hi = np.power(band, 6.0 + (1 - r) * 200.0)
    refl = 0.18 + 0.85 * m + 0.40 * cc
    sky = np.array([0.85, 0.90, 1.0], np.float32)
    speccol = (0.55 * alb + 0.45 * sky) * ((refl * hi)[..., None])
    return np.clip(alb * (0.55 + 0.18 * (1 - r))[..., None] + speccol, 0, 1)


META = []
SZ = 460
for fid, (module_path, builder_name, name, swatch, desc) in NEON_FINISHES.items():
    t0 = time.time()
    spec_fn, paint_fn = LIVE_PAIRS[fid]
    mask = np.ones((SZ, SZ), np.float32)
    paint = paint_fn(np.zeros((SZ, SZ, 3), np.float32), (SZ, SZ), mask, 7, 1.0, None)
    spec = spec_fn((SZ, SZ), mask, 7, 1.0)
    render_s = round(time.time() - t0, 2)
    tr = fs.spec_traces_paint(spec, paint)
    pv = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    cvm = (on_car(paint, spec) * 255).astype(np.uint8)
    pad = np.full((SZ, 6, 3), 25, np.uint8)
    swatch_img = np.concatenate([pv, pad, cvm], axis=1)
    cv2.imwrite(os.path.join(THUMB_DIR, fid + ".png"), cv2.cvtColor(swatch_img, cv2.COLOR_RGB2BGR))
    META.append(dict(id=fid, name=name, kind="finish",
                     desc=desc + " LEFT paint, RIGHT on-car (authored packed M/R/Cc response).",
                     technique=module_path + "/" + builder_name,
                     render_s=render_s, ai_rating=int(round(tr * 100))))
    print(f"  {fid:28s} {render_s:.2f}s trace={tr:.2f}")

TITLE = ('<span class="flag">★ NEON UNDERGROUND</span> - Rework Audit '
         '<span style="color:var(--dim);font-weight:400">(25 authored causal materials)</span>')
SUB = ("Current live-dev Neon Underground: 25 independent automotive coating processes built from fine "
       "8–32px anatomy and causally co-registered, eight-tier M/R/Cc—not literal neon props or a shared "
       "colour-swap carrier. LEFT swatch = paint; RIGHT = deterministic material/light proxy. "
       "<b>SUBMIT THIS ONE</b> saves a card. AI badge = spec trace strength. ⏱ = live-route render time.")

build_page("neon", TITLE, SUB, META, THUMB_DIR,
           os.path.join(ROOT, "SPB_AUDIT_neon.html"), accent="#ff2fa0")
