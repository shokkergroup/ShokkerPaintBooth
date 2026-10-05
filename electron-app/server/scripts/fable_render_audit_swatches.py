# -*- coding: utf-8 -*-
"""Render FABLE audit swatches via the REAL engine to thumbnails/audit/fable/.
Round-2 style: LEFT = TRUE 1:1 crop of the full 2048 paint render (real on-car
pixel scale — the fineness doctrine's honest view), RIGHT = real spec crop.
Enriches scripts/fable_audit_meta.json with ai/mip/fineness/render_s."""
import sys, os, json, time
import numpy as np
sys.path.insert(0, r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum")
import cv2
from engine.paint_v2.fable_collection import FABLE_MONOLITHICS
from engine.color_science import mip_survival, feature_fineness

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
OUT = os.path.join(ROOT, "thumbnails", "audit", "fable")
os.makedirs(OUT, exist_ok=True)
META = json.load(open(os.path.join(ROOT, "scripts", "fable_audit_meta.json"), encoding="utf-8"))

F = 2048
fmask = np.ones((F, F), np.float32)
fbase = np.full((F, F, 3), 0.5, np.float32)


def label(bgr, text):
    cv2.rectangle(bgr, (0, bgr.shape[0] - 24), (bgr.shape[1] - 1, bgr.shape[0] - 1), (12, 12, 12), -1)
    cv2.putText(bgr, text, (8, bgr.shape[0] - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (210, 210, 210), 1, cv2.LINE_AA)
    return bgr


def ai_rating(field, mip, fine):
    f = field.astype(np.float32).mean(axis=2)
    bands = 0.0
    for sigma in (1.5, 6.0, 24.0):
        lo = cv2.GaussianBlur(f, (0, 0), sigma)
        bands += min(float(np.abs(f - lo).mean()) / 0.04, 1.0)
        f = lo
    clip = float(((field <= 0.002) | (field >= 0.998)).mean())
    score = 22.0 + bands * 12.0 + mip * 14.0 + fine * 22.0 - clip * 25.0
    return int(np.clip(round(score), 1, 100))


for m in META:
    spec_fn, paint_fn = FABLE_MONOLITHICS[m["id"]]
    t0 = time.perf_counter(); pf = paint_fn(fbase.copy(), (F, F), fmask, 42, 1.0, {})[:, :, :3]; tp = time.perf_counter() - t0
    t0 = time.perf_counter(); sf = spec_fn((F, F), fmask, 42, 1.0); ts = time.perf_counter() - t0
    fin = feature_fineness(pf, full_size=F)
    mip = mip_survival(pf)
    m["mip"] = round(float(mip), 2)
    m["render_s"] = round(tp + ts, 2)
    m["fineness"] = fin
    m["ai_rating"] = ai_rating(pf, mip, fin["fine_fraction"])
    crop = pf[768:1280, 768:1280]
    scrop = sf[768:1280, 768:1280, :3]
    l = label(cv2.cvtColor((np.clip(crop, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), "paint (1:1 crop of 2048)")
    r = label(cv2.cvtColor(scrop, cv2.COLOR_RGB2BGR), "spec  R=M G=R B=Cc")
    img = np.hstack([l, np.full((512, 4, 3), 24, np.uint8), r])
    cv2.imwrite(os.path.join(OUT, m["id"] + ".png"), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    print(m["id"], "ai", m["ai_rating"], "mip", m["mip"], "char", fin["char_px"], "%.1f+%.1fs" % (tp, ts))

json.dump(META, open(os.path.join(ROOT, "scripts", "fable_audit_meta.json"), "w", encoding="utf-8"), indent=1)
print("DONE: %d swatches -> %s" % (len(META), OUT))
