# -*- coding: utf-8 -*-
"""Render the REDESIGN BATCH 10 review swatches + build SPB_AUDIT_redesign10.html.
Swatches render directly from engine/expansions/redesign_b10_2026.DESIGNS so the
review page == the actual design output. (Live-engine wiring happens AFTER owner
approves which survive — no point wiring 10 into 5 registries before the cut.)"""
import os, sys, time, json
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from engine.expansions.redesign_b10_2026 import DESIGNS, _PAT_TEX, _PAT_COLOR
from engine.color_science import feature_fineness, mip_survival
from spb_audit_page_builder import build_page

S = 2048
SW = 1024  # match the LIVE car render exactly: design at 1024 work grid, upscale to 2048
OUT = os.path.join(ROOT, "thumbnails", "audit", "redesign10")
os.makedirs(OUT, exist_ok=True)

INFO = {
 "butterfly_morpho": ("Butterfly Morpho", "finish",
   "Thousands of overlapping wing-scale shingles in curved rows — each a tiny ridged tile carrying structural-blue thin-film that travels cobalt→violet→teal across the rows; dark branching wing-veins show through and rare scales flare white."),
 "moth_luna": ("Moth Luna", "finish",
   "Pale jade luna-moth wing: downy radial fur striations, four concentric eyespot ocelli with gold rims and lilac crescents, pink leading-edge piping; glassy ocellus centers over matte fur."),
 "fable_comet_parade": ("Comet Parade", "finish",
   "A parade of comets across deep space: blown-out white-hot heads with prismatic dispersion and long chromatic tails (red leading → blue trailing), fine star-dust, faint violet nebula. The heads jump off the car."),
 "fable_magnetite_flow": ("Magnetite Flow", "finish",
   "Ferrofluid Rosensweig spikes — a dense field of SHARP peaked black-chrome spikes packed along the magnetic field, white-hot mirror tips, deep valleys, subtle violet polarity territories. All sharp peaks, zero blobs."),
 "lfr_freedom_forge": ("Freedom Forge", "finish",
   "Pattern-welded Damascus steel: flowing folded/watered grain of light polished bands and dark etched valleys with a cross-fold ladder, faint forge-heat glowing in the deepest etch lines."),
 "lfr_rockets_red_glare": ("Rockets Red Glare", "finish",
   "Layered night fireworks: chrysanthemum spokes with terminal dots, drooping willow trails, splitting crossettes, white-hot burst cores and dense spark fields in red/white/gold/blue over a deep blue night."),
 "lfr_liberty_filigree": ("Liberty Filigree", "pattern",
   "Fine engraved goldwork: interwoven logarithmic scroll-curls, mirrored C-scrolls and beadwork dots forming a dense antique-jewelry lace. Sharp thin metal linework, alpha-stamped."),
 "lfr_eagle_crest": ("Eagle Crest", "pattern",
   "Heraldic layered feather plumage: overlapping feathers each with a central shaft and fine angled barb lines, shingled into a crest. Bronze-gold metalwork, fine barbs."),
 "lfr_constellation_field": ("Constellation Field", "pattern",
   "Dense star cartography: thousands of magnitude-varied micro stars, bright anchor stars linked by thin constellation lines, faint nebula wash. Star-chart micro detail end to end."),
 "lfr_distressed_flag": ("Distressed Flag", "pattern",
   "Weathered battle-flag textile: over-under woven thread grid, sun-worn cracked paint patches, torn voids and frayed holes. Aged canvas realism, abstracted (no literal stripes)."),
}


def label(bgr, text):
    cv2.rectangle(bgr, (0, bgr.shape[0] - 22), (bgr.shape[1] - 1, bgr.shape[0] - 1), (12, 12, 12), -1)
    cv2.putText(bgr, text, (7, bgr.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (210, 210, 210), 1, cv2.LINE_AA)
    return bgr


def ai_rating(paint, mip, fine):
    f = paint.mean(2); bands = 0.0
    for sg in (1.5, 6.0, 24.0):
        lo = cv2.GaussianBlur(f, (0, 0), sg); bands += min(float(np.abs(f - lo).mean()) / 0.04, 1.0); f = lo
    clip = float(((paint <= 0.002) | (paint >= 0.998)).mean())
    return int(np.clip(round(22 + bands * 12 + mip * 14 + fine * 22 - clip * 25), 1, 100))


def render(fid):
    paint_fn, spec_fn, kind = DESIGNS[fid]
    t0 = time.perf_counter()
    if kind == "pattern":
        tex = _PAT_TEX[fid](S, S, 42)   # patterns are cheap -> native 2048 (match live wiring)
        lo, hi = _PAT_COLOR[fid]
        metal = lo[None, None, :] + (hi - lo)[None, None, :] * tex[..., None]
        base = np.full((S, S, 3), 0.5, np.float32)
        paint = base * (1 - tex[..., None]) + metal * tex[..., None]
        M = np.clip(20 + 230 * tex, 0, 255); R = np.clip(180 - 120 * tex, 15, 255); Cc = np.clip(30 + 130 * tex, 16, 255)
    else:
        paint = np.clip(paint_fn(SW, SW, 42), 0, 1).astype(np.float32)
        M, R, Cc = spec_fn(SW, SW, 42)
    dt = time.perf_counter() - t0
    spec = np.clip(np.stack([M, R, Cc], -1) / 255.0, 0, 1).astype(np.float32)
    # upscale work-grid render to 2048 (INTER_LINEAR, as the engine does) for display + fineness
    paint = cv2.resize(paint, (S, S), interpolation=cv2.INTER_LINEAR)
    spec = cv2.resize(spec, (S, S), interpolation=cv2.INTER_LINEAR)
    fin = feature_fineness(paint, full_size=S); mip = mip_survival(paint)
    # COVERAGE gate (owner full-coverage rule): fraction of pixels carrying local
    # high-frequency detail. Sparse canvases (empty background) score low.
    g = paint.mean(2)
    hf = np.abs(g - cv2.GaussianBlur(g, (0, 0), 4.0))
    coverage = float((hf > 0.012).mean())
    return paint, spec, dt, fin, mip, coverage


def crop(a):
    return (np.clip(a[768:1280, 768:1280], 0, 1) * 255).astype(np.uint8)


meta = []
print("=== REDESIGN BATCH 10 ===")
for fid in DESIGNS:
    name, kind, desc = INFO[fid]
    paint, spec, dt, fin, mip, cov = render(fid)
    char = fin["char_px"]; luma = float(paint.mean())
    ai = ai_rating(paint, mip, fin.get("fine_fraction", 0.5))
    msgs = []
    if cov < 0.80: msgs.append("SPARSE cov%.2f" % cov)     # owner full-coverage gate
    if dt > 2.0: msgs.append("PERF %.1fs" % dt)
    if char > 12.0: msgs.append("char %.1f" % char)
    if luma < 0.06: msgs.append("dark %.3f" % luma)
    print(("%-24s ai%3d cov%.2f char%5.1f luma%.2f %.1fs  %s"
           % (fid, ai, cov, char, luma, dt, "FLAG:" + ";".join(msgs) if msgs else "ok")))
    img = np.hstack([label(cv2.cvtColor(crop(paint), cv2.COLOR_RGB2BGR), "canvas design (1:1 crop of 2048)"),
                     np.full((512, 4, 3), 24, np.uint8),
                     label(cv2.cvtColor(crop(spec), cv2.COLOR_RGB2BGR), "spec  R=M G=R B=Cc")])
    cv2.imwrite(os.path.join(OUT, fid + ".png"), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    meta.append({"id": fid, "name": name, "kind": kind, "desc": desc,
                 "ai_rating": ai, "mip": round(float(mip), 2), "render_s": round(dt, 2)})

json.dump(meta, open(os.path.join(ROOT, "scripts", "redesign10_audit_meta.json"), "w", encoding="utf-8"), indent=1)

TITLE = ('<span class="flag">\U0001F9E8 REDESIGN — 10 Fresh Concepts</span> '
         '<span style="color:var(--dim);font-weight:400">(the 10 worst offenders, totally new designs)</span>')
SUB = ("Owner mandate: the CANVAS DESIGNS were lazy/recycled — these are 10 completely different visual "
       "languages, no shared motif, colored with the new OKLab/oklch wheel. LEFT = the actual paint canvas "
       "(1:1 crop of the 2048), RIGHT = the married material spec (red=metallic, green=roughness, blue=clearcoat). "
       "Rate hard — this sets the bar before I roll the approach across the rest. <b>SUBMIT THIS ONE</b> saves a card.")

build_page("redesign10", TITLE, SUB, meta, OUT, os.path.join(ROOT, "SPB_AUDIT_redesign10.html"), accent="#ff8adf")
print("WROTE SPB_AUDIT_redesign10.html (%d cards)" % len(meta))
