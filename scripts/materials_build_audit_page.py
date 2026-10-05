# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_materials.html via the shared builder for the reworked MATERIALS & PHYSICS
(8 distinct fabricated material surfaces). Swatch = 2-panel [LEFT material paint | RIGHT on-car
composite = paint x material_spec gloss under a sweeping light]. Re-runnable."""
import os, sys, time
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from spb_audit_page_builder import build_page
from engine.paint_v2 import materials_math as mat, flame_spec as fs
from engine.expansions.materials_catalog_2026 import MATERIALS_FINISHES

THUMB_DIR = os.path.join(ROOT, "thumbnails", "audit", "materials")
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
for fid, (structure, name, swatch, desc) in MATERIALS_FINISHES.items():
    params = mat.MATERIAL_SPEC_PARAMS[structure]
    t0 = time.time()
    paint = np.asarray(mat.MATERIALS_STRUCTURES[structure]((SZ, SZ), 7), np.float32)[:, :, :3]
    spec = np.asarray(mat.material_spec(paint, **params))
    render_s = round(time.time() - t0, 2)
    tr = fs.spec_traces_paint(spec, paint)
    pv = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    cvm = (on_car(paint, spec) * 255).astype(np.uint8)
    pad = np.full((SZ, 6, 3), 25, np.uint8)
    swatch_img = np.concatenate([pv, pad, cvm], axis=1)
    cv2.imwrite(os.path.join(THUMB_DIR, fid + ".png"), cv2.cvtColor(swatch_img, cv2.COLOR_RGB2BGR))
    META.append(dict(id=fid, name=name, kind="finish",
                     desc=desc + " LEFT paint, RIGHT on-car (metallic material_spec gloss).",
                     technique="materials_math/" + structure + " + material_spec",
                     render_s=render_s, ai_rating=int(round(tr * 100))))
    print(f"  {fid:20s} {render_s:.2f}s trace={tr:.2f}")

TITLE = ('<span class="flag">★ MATERIALS &amp; PHYSICS</span> - Rework Audit '
         '<span style="color:var(--dim);font-weight:400">(8 distinct fabricated material surfaces)</span>')
SUB = ("Total rework of the old 20 Material-Gradients + Exotic-Physics colour-swaps -> 8 genuinely "
       "DIFFERENT fabricated MATERIALS: carbon twill weave, forged carbon, engine-turned (jeweled) "
       "metal, liquid metal, crystal lattice, ferrofluid spikes, fracture net, and Damascus steel. "
       "These are METALS, so the spec is a dedicated physically-metallic material_spec (high metallic, "
       "structure-tracing roughness from mirror to satin, clearcoat on the highlights) — a diverse "
       "metal family, not flame gloss. Each: full-canvas + crushed-fine. All clear the catalog "
       "uniqueness gate (&lt;=41% vs any of ~2400 finishes). LEFT swatch = material paint, RIGHT = "
       "on-car composite. <b>SUBMIT THIS ONE</b> saves a card. AI badge = spec trace strength. "
       "⏱ = render time.")

build_page("materials", TITLE, SUB, META, THUMB_DIR,
           os.path.join(ROOT, "SPB_AUDIT_materials.html"), accent="#9094a0")
