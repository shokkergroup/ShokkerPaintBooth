# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_anime.html via the shared builder for the reworked ANIME INSPIRED (8 distinct
generative structures). Swatch = 2-panel [LEFT anime paint | RIGHT on-car composite = paint x spec
gloss under a sweeping light]. Re-runnable each round. Mirrors neon_build_audit_page."""
import os, sys, time
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from spb_audit_page_builder import build_page
from engine.paint_v2 import anime_math as am, flame_spec as fs
from engine.expansions.anime_catalog_2026 import ANIME_FINISHES

THUMB_DIR = os.path.join(ROOT, "thumbnails", "audit", "anime")
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
for fid, (structure, mode, name, swatch, desc) in ANIME_FINISHES.items():
    t0 = time.time()
    paint = np.asarray(am.ANIME_STRUCTURES[structure]((SZ, SZ), 7), np.float32)[:, :, :3]
    spec = np.asarray(SPEC[mode](paint))
    render_s = round(time.time() - t0, 2)
    tr = fs.spec_traces_paint(spec, paint)
    pv = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    cvm = (on_car(paint, spec) * 255).astype(np.uint8)
    pad = np.full((SZ, 6, 3), 25, np.uint8)
    swatch_img = np.concatenate([pv, pad, cvm], axis=1)
    cv2.imwrite(os.path.join(THUMB_DIR, fid + ".png"), cv2.cvtColor(swatch_img, cv2.COLOR_RGB2BGR))
    META.append(dict(id=fid, name=name, kind="finish",
                     desc=desc + " LEFT paint, RIGHT on-car (anime + " + mode + " spec gloss).",
                     technique="anime_math/" + structure + " + flame_spec/" + mode,
                     render_s=render_s, ai_rating=int(round(tr * 100))))
    print(f"  {fid:22s} {mode:6s} {render_s:.2f}s trace={tr:.2f}")

TITLE = ('<span class="flag">★ ANIME INSPIRED</span> - Rework Audit '
         '<span style="color:var(--dim);font-weight:400">(8 distinct generative anime structures)</span>')
SUB = ("Total rework of the old 10 colour-swap anime finishes -> 8 genuinely DIFFERENT anime "
       "TECHNIQUES (cel shading / manga screentone / sakura storm / mecha panels / speed lines / "
       "energy aura / crystal facet / gradient hair). Each: real animation craft (posterised toon "
       "bands + ink, Ben-Day halftone, motion-blurred petals, hard-surface plating, radial speed "
       "lines, charging ki aura, faceted jewels, flowing strands), full-canvas + fine, with a "
       "diverse spec (dance=flash, ignite=glossy, topo=depth). All clear the catalog uniqueness gate "
       "(<=51% vs any of ~2400 finishes). LEFT swatch = anime paint, RIGHT = on-car composite. "
       "<b>SUBMIT THIS ONE</b> saves a card. AI badge = spec trace strength. ⏱ = render time.")

build_page("anime", TITLE, SUB, META, THUMB_DIR,
           os.path.join(ROOT, "SPB_AUDIT_anime.html"), accent="#ff5a7a")
