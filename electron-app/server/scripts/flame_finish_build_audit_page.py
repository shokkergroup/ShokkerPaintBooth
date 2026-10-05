# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_flames.html via the shared builder (scripts/spb_audit_page_builder.py).
Round 1 = the 51 headline IGNITE finishes (one per flame). Each swatch is a 2-panel TRUTHFUL view:
LEFT = the colour flame paint, RIGHT = the on-car composite (paint x spec gloss/metal under a light)
so the owner judges the actual finished look, not a grayscale spec. Re-runnable each round."""
import os, sys, time
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from spb_audit_page_builder import build_page
from engine.paint_v2 import flame_spec_recipes as fsr

THUMB_DIR = os.path.join(ROOT, "thumbnails", "audit", "flame")
os.makedirs(THUMB_DIR, exist_ok=True)


def on_car(paint, spec):
    alb = np.clip(np.asarray(paint, np.float32), 0, 1)
    if alb.max() > 1.0:
        alb = alb / 255.0
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
    return np.clip(alb * (0.50 + 0.18 * (1 - r))[..., None] + speccol, 0, 1)


META = []
ign = [r for r in fsr.RECIPES if r["mode"] == "ignite"]
SZ = 460
for rec in ign:
    fl, pal = rec["flame"], rec["palette"]
    t0 = time.time()
    paint, spec = fsr.render_flame_spec_finish(fl, "ignite", pal, size=SZ)
    render_s = round(time.time() - t0, 2)
    p = np.asarray(paint, np.float32)
    p = p / 255.0 if p.max() > 1 else p
    car = on_car(paint, spec)
    pv = (np.clip(p[..., :3], 0, 1) * 255).astype(np.uint8)
    cv_ = (car * 255).astype(np.uint8)
    pad = np.full((SZ, 6, 3), 30, np.uint8)
    swatch = np.concatenate([pv, pad, cv_], axis=1)             # paint | on-car
    cv2.imwrite(os.path.join(THUMB_DIR, fl + ".png"), cv2.cvtColor(swatch, cv2.COLOR_RGB2BGR))
    META.append(dict(id=fl, name=fl.replace("_", " ").title(), kind="finish",
                     desc="Ignite finish - %s palette - trace %.2f. LEFT paint, RIGHT on-car (colour + gloss flash)." % (pal, rec.get("trace", 0)),
                     technique="spec_ignite/" + pal, render_s=render_s,
                     ai_rating=int(round(rec.get("trace", 0) * 100))))
    print(f"  {fl:20s} {pal:10s} {render_s:.2f}s")

TITLE = ('<span class="flag">\U0001F525 FLAME FINISHES</span> - Round 1 Audit '
         '<span style="color:var(--dim);font-weight:400">(51 ignite finishes, one per flame)</span>')
SUB = ("The flame PAINT (51 distinct generative structures) + its pattern-aware IGNITE spec (FRACTURED-carved "
       "metallic+clearcoat on the hot geometry). Each swatch: LEFT = colour flame paint, RIGHT = on-car composite "
       "(paint x spec gloss under a sweeping light - in iRacing that flash DANCES as the car moves). 6 colour palettes "
       "across the set. Topo (depth) + Dance (flicker) variants exist per flame for later rounds. <b>SUBMIT THIS ONE</b> "
       "saves a card immediately. AI badge = spec trace strength. ⏱ = render time.")

build_page("flame", TITLE, SUB, META, THUMB_DIR,
           os.path.join(ROOT, "SPB_AUDIT_flames.html"), accent="#ff7a30")
