# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_optics.html via the shared builder for the reworked LIGHT & OPTICS (8 distinct
physically-grounded optical phenomena). Swatch = 2-panel [LEFT optics paint | RIGHT on-car composite
= paint x spec gloss under a sweeping light]. Re-runnable. Mirrors neon/anime audit builders."""
import os, sys, time
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from spb_audit_page_builder import build_page
from engine.paint_v2 import optics_math as opm, flame_spec as fs
from engine.expansions.optics_catalog_2026 import OPTICS_FINISHES

THUMB_DIR = os.path.join(ROOT, "thumbnails", "audit", "optics")
os.makedirs(THUMB_DIR, exist_ok=True)
SPEC = {"ignite": fs.spec_ignite, "topo": fs.spec_topo, "dance": fs.spec_dance}


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
for fid, (structure, mode, name, swatch, desc) in OPTICS_FINISHES.items():
    t0 = time.time()
    paint = np.asarray(opm.OPTICS_STRUCTURES[structure]((SZ, SZ), 7), np.float32)[:, :, :3]
    spec = np.asarray(SPEC[mode](paint))
    render_s = round(time.time() - t0, 2)
    tr = fs.spec_traces_paint(spec, paint)
    pv = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    cvm = (on_car(paint, spec) * 255).astype(np.uint8)
    pad = np.full((SZ, 6, 3), 25, np.uint8)
    swatch_img = np.concatenate([pv, pad, cvm], axis=1)
    cv2.imwrite(os.path.join(THUMB_DIR, fid + ".png"), cv2.cvtColor(swatch_img, cv2.COLOR_RGB2BGR))
    META.append(dict(id=fid, name=name, kind="finish",
                     desc=desc + " LEFT paint, RIGHT on-car (optics + " + mode + " spec gloss).",
                     technique="optics_math/" + structure + " + flame_spec/" + mode,
                     render_s=render_s, ai_rating=int(round(tr * 100))))
    print(f"  {fid:18s} {mode:6s} {render_s:.2f}s trace={tr:.2f}")

TITLE = ('<span class="flag">★ LIGHT &amp; OPTICS</span> - Rework Audit '
         '<span style="color:var(--dim);font-weight:400">(8 distinct optical phenomena)</span>')
SUB = ("Total rework of the old 20 Light-Waves + Spectral-Reactive colour-swaps -> 8 genuinely "
       "DIFFERENT optical PHENOMENA on a real wavelength-&gt;sRGB spectral engine: diffraction spiral "
       "(CD/DVD log-spiral grating), thin-film oil slick, refractive caustics (1/|Jacobian| ray folds), "
       "Newton's rings, prism dispersion (spectral fans), moire interference, aurora veil, and a "
       "soap-bubble froth (translucent thin-film spheres). Each: full-canvas + crushed-fine, with a "
       "diverse spec (dance=flash, ignite=glossy, topo=depth). All clear the catalog uniqueness gate "
       "(&lt;=47% vs any of ~2400 finishes). LEFT swatch = optics paint, RIGHT = on-car composite. "
       "<b>SUBMIT THIS ONE</b> saves a card. AI badge = spec trace strength. ⏱ = render time.")

build_page("optics", TITLE, SUB, META, THUMB_DIR,
           os.path.join(ROOT, "SPB_AUDIT_optics.html"), accent="#36d0ff")
