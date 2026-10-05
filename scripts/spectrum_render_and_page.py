# -*- coding: utf-8 -*-
"""Render the CURRENT Spectrum Shift group (live registry — owner Image-Forge
art AND surviving procedurals) + build SPB_AUDIT_spectrumshift2.html.
Renders through the REAL registry entries, so what's on the page is exactly
what ships: forge-backed cards show the owner's art with its derived spec."""
import os, sys, time, json
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import shokker_engine_v2 as E
from engine.color_science import feature_fineness, mip_survival
from spb_audit_page_builder import build_page

S = 2048
OUT = os.path.join(ROOT, "thumbnails", "audit", "spectrumshift2")
os.makedirs(OUT, exist_ok=True)

FORGE_IDS = set()
fdir = os.path.join(ROOT, "image_forge", "spectrum shift")
if os.path.isdir(fdir):
    FORGE_IDS = {os.path.splitext(f)[0] for f in os.listdir(fdir) if f.endswith(".jpg")}

# carry over the original concept blurbs for procedural cards
try:
    OLD = {m["id"]: m["desc"] for m in json.load(
        open(os.path.join(ROOT, "scripts", "spectrumshift_audit_meta.json"), encoding="utf-8"))}
except Exception:
    OLD = {}


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


def crop(a):
    return (np.clip(a[768:1280, 768:1280], 0, 1) * 255).astype(np.uint8)


from engine.expansions import fusions as _fus
ids = sorted(k for k in _fus.FUSION_REGISTRY if k.startswith("spectrum_"))
mask = np.ones((S, S), np.float32)
base = np.full((S, S, 3), 0.5, np.float32)
meta = []
print("=== SPECTRUM SHIFT — current group (%d) ===" % len(ids))
for fid in ids:
    spec_fn, paint_fn = E.MONOLITHIC_REGISTRY[fid]
    t0 = time.perf_counter()
    paint = np.clip(np.asarray(paint_fn(base, (S, S), mask, 42, 1.0, 1.0), np.float32)[:, :, :3], 0, 1)
    sp = np.asarray(spec_fn((S, S), mask, 42, 1.0), np.float32)
    dt = time.perf_counter() - t0
    spec = np.clip(sp[:, :, :3] / 255.0, 0, 1)
    fin = feature_fineness(paint, full_size=S); mip = mip_survival(paint)
    ai = ai_rating(paint, mip, fin.get("fine_fraction", 0.5))
    forge = fid.replace("spectrum_", "") in {f.replace("spectrum_", "") for f in FORGE_IDS} or fid in FORGE_IDS
    short = fid.replace("spectrum_", "")
    name = "Spectrum " + short.replace("_", " ").title()
    if forge:
        desc = ("\U0001F58C OWNER ART (Image Forge) — your image verbatim; spec derived from it: "
                "stroke-flow gloss anisotropy, hue-banded sequential ignition (two flash angles), "
                "brightest-stroke clearcoat pins. Judge the SPEC here — say the word and I rework it.")
    else:
        desc = "PROCEDURAL — " + OLD.get(fid, "")
    print("%-30s %s ai%3d  %.2fs" % (fid, "FORGE" if forge else "proc ", ai, dt))
    img = np.hstack([label(cv2.cvtColor(crop(paint), cv2.COLOR_RGB2BGR),
                           "canvas (1:1 crop of 2048)" + (" — OWNER ART" if forge else "")),
                     np.full((512, 4, 3), 24, np.uint8),
                     label(cv2.cvtColor(crop(spec), cv2.COLOR_RGB2BGR), "spec  R=M G=R B=Cc")])
    cv2.imwrite(os.path.join(OUT, fid + ".png"), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    meta.append({"id": fid, "name": ("🖌 " + name + " (YOUR ART)") if forge else name, "kind": "finish",
                 "desc": desc, "ai_rating": ai, "mip": round(float(mip), 2), "render_s": round(dt, 2)})

json.dump(meta, open(os.path.join(ROOT, "scripts", "spectrumshift2_audit_meta.json"), "w", encoding="utf-8"), indent=1)

TITLE = ('<span class="flag">\U0001F308 SPECTRUM SHIFT — round 2 (Image Forge era)</span> '
         '<span style="color:var(--dim);font-weight:400">(every current member: your art + derived specs, and surviving procedurals)</span>')
SUB = ("The whole group on one page. \U0001F58C cards are YOUR images with the auto-derived married spec — "
       "if a spec reads wrong, flag the card (rebuild + note) and I retune that derivation immediately. "
       "Procedural cards are the survivors from round 1. LEFT = canvas, RIGHT = married spec "
       "(red=metallic, green=roughness, blue=clearcoat). <b>SUBMIT THIS ONE</b> saves a card.")

build_page("spectrumshift2", TITLE, SUB, meta, OUT, os.path.join(ROOT, "SPB_AUDIT_spectrumshift2.html"), accent="#ffd24a")
print("WROTE SPB_AUDIT_spectrumshift2.html (%d cards)" % len(meta))
