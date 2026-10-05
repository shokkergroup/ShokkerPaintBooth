# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_gradients.html via the shared builder (scripts/spb_audit_page_builder.py).
Renders the GRADIENT engine's looks to audit thumbs, then builds the interactive per-card page.
Re-runnable each round. Thumbs saved BGR via cv2 so the builder's imread/imencode round-trips colour."""
import os, sys, time
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from spb_audit_page_builder import build_page
from engine.paint_v2 import gradient_math as gm

THUMB_DIR = os.path.join(ROOT, "thumbnails", "audit", "gradient")
os.makedirs(THUMB_DIR, exist_ok=True)

# id -> (display name, one-line description, technique)
INFO = {
    "oklab_flow":           ("Sunset Drift",   "Perceptual sunset that flows organically across the panel.", "OKLab flow-warp"),
    "iridescent":           ("Oil Slick",      "Holographic spectrum rings with thin-film sheen.",           "OKLab radial hue-cycle"),
    "ridged_contour":       ("Topo Ridge",     "Topographic contour bands with bright ridge lines.",         "quantized contour + ridge"),
    "mesh_bleed":           ("Colour Mesh",    "Several colour sources pool and bleed together.",            "inverse-distance OKLab mesh"),
    "duotone_grain":        ("Duotone Grain",  "Two-tone ramp broken up by fine premium grain texture.",     "OKLab duotone + dither grain"),
    "chromatic_aberration": ("Prism Split",    "RGB channels diverge where the ramp bends — prism fringing.","per-channel ramp split"),
    "spectral_sweep":       ("Spectrum Sweep", "A clean full-spectrum rainbow sweeping along a warped axis.","warped OKLab spectrum"),
    "liquid_marble":        ("Liquid Marble",  "Stirred multi-hue marble veins.",                            "iterated domain-warp"),
    "moire_interference":   ("Moire Weave",    "Crossed waves beat into a fine woven interference pattern.",  "crossed-wave beat"),
    "holo_foil":            ("Holo Foil",      "Fine repeated rainbow strips with a holographic sheen.",     "repeated spectrum + sheen"),
    "radial_burst":         ("Colour Burst",   "An angular colour-wheel burst radiating from a point.",      "angular hue + radial falloff"),
}

META = []
for gid, fn in gm.GRADIENT_STRUCTURES.items():
    name, desc, tech = INFO.get(gid, (gid.replace("_", " ").title(), "Distinctive gradient.", ""))
    # render at 2048 for an honest render-time badge, then downscale the thumb to 768
    t0 = time.time()
    full = np.asarray(fn((2048, 2048), 7))
    render_s = round(time.time() - t0, 2)
    thumb = (np.clip(cv2.resize(full, (768, 768), interpolation=cv2.INTER_AREA), 0, 1) * 255).astype(np.uint8)
    cv2.imwrite(os.path.join(THUMB_DIR, gid + ".png"), cv2.cvtColor(thumb, cv2.COLOR_RGB2BGR))
    struct = round(gm.gradient_structure(np.asarray(fn((256, 256), 7))), 2)
    META.append(dict(id=gid, name=name, desc=desc, kind="finish", technique=tech,
                     render_s=render_s, ai_rating=int(round(struct * 100))))
    print(f"  {gid:22s} {render_s:.2f}s  struct={struct}")

TITLE = ('<span class="flag">\U0001F308 GRADIENTS</span> — Round 1 Audit '
         '<span style="color:var(--dim);font-weight:400">(11 distinctive OKLab gradients — rate each)</span>')
SUB = ("A new gradient ENGINE — not boring linear ramps. Every look interpolates in OKLab (clean hue travel, no "
       "muddy mid-tones) and adds real structure (flow-warp / bands / mesh / grain / iridescence / interference). "
       "All clear the gradient gate: distinct from each other, non-linear (anti-boring), &lt;3s. The AI badge here = "
       "the non-linear STRUCTURE meter (higher = more designed, not a flat ramp). <b>SUBMIT THIS ONE</b> saves a card "
       "immediately. ⏱ = full 2048 render time (target ~1s).")

build_page("gradient", TITLE, SUB, META, THUMB_DIR,
           os.path.join(ROOT, "SPB_AUDIT_gradients.html"), accent="#6fd0ff")
