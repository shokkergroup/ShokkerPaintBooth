# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_flames.html for the rebuilt FRACTURED FLAMES.

Owner mandate 2026-08-30: three FLAMES shelves holding 144 cards down to ~75,
new math and styles, spec channel doing real work. Renders each finish through
the REAL registry once and composes [full 2048 view | TRUE 1:1 on-car crop |
spec M/R/Cc], grouped by the five chapters. Re-runnable each audit round.
"""
import contextlib
import io
import json
import logging
import os
import sys
import time

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import cv2                                                   # noqa: E402
import numpy as np                                           # noqa: E402
from spb_audit_page_builder import build_page                 # noqa: E402

THUMBS = os.path.join(ROOT, "thumbnails", "audit", "flames")
os.makedirs(THUMBS, exist_ok=True)
logging.disable(logging.CRITICAL)
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
    import shokker_engine_v2 as eng
import engine.expansions.fractured_flames_2026 as m           # noqa: E402

SHAPE = (2048, 2048)
MASK = np.ones(SHAPE, np.float32)
BASE = np.full(SHAPE + (3,), 0.5, np.float32)
PANEL = 512

# Prefer the lane's own measured times (best of 2 cold runs on an idle box) over
# whatever this pass happens to measure — the audit render competes with the
# app server for the CPU.
times = {}
if os.path.exists("FRACTURED_FLAMES_PROGRESS.jsonl"):
    for line in io.open("FRACTURED_FLAMES_PROGRESS.jsonl", encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("phase") == "verify" and r.get("fid"):
            times[r["fid"]] = r.get("sec")

meta = []
for fid, d in m.FLAMES.items():
    spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[fid]
    t0 = time.time()
    p = paint_fn(BASE.copy(), SHAPE, MASK, 51, 1.0, None)
    s = spec_fn(SHAPE, MASK, 51, 1.0)
    dt = times.get(fid) or (time.time() - t0)
    p8 = np.clip(np.asarray(p, np.float32) * 255.0, 0, 255).astype(np.uint8)
    s8 = np.asarray(s)[..., :3].astype(np.uint8)
    c0 = (2048 - PANEL) // 2
    full = cv2.resize(p8, (PANEL, PANEL), interpolation=cv2.INTER_AREA)
    crop = p8[c0:c0 + PANEL, c0:c0 + PANEL]
    # 1:1 too — a 2048 spec downsampled to 512 aliases 10px material cells into
    # pixel noise and makes a correct map look like confetti.
    spec = s8[c0:c0 + PANEL, c0:c0 + PANEL]
    tile = np.full((PANEL + 26, PANEL * 3 + 16, 3), 14, np.uint8)
    for i, (img, lab) in enumerate(((full, "FULL 2048 VIEW"),
                                    (crop, "TRUE 1:1 ON-CAR CROP"),
                                    (spec, "SPEC M/R/Cc  (1:1)"))):
        x0 = i * (PANEL + 8)
        tile[26:26 + PANEL, x0:x0 + PANEL] = img
        cv2.putText(tile, lab, (x0 + 4, 18), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
    cv2.imwrite(os.path.join(THUMBS, fid + ".png"), tile[..., ::-1])
    meta.append({"id": fid,
                 "name": "%s  \u00b7  %s" % (d["name"], m.CHAPTERS[d["chapter"]]),
                 "kind": "finish", "render_s": round(float(dt), 2),
                 "desc": "%s   [fuel: %s]" % (d["desc"], d["fuel"])})
    print("%s %.2fs" % (fid, dt), flush=True)

TITLE = ('<span class="flag">\U0001f525 FRACTURED FLAMES</span> \u2014 Round 1 Audit '
         '<span style="color:var(--dim);font-weight:400">(144 \u2192 75)</span>')
SUB = (
    "Your mandate: about 75 total, cut the repeats, new math and styles, and make the spec channel "
    "bring them to life. <b>The old 135 were a cross-product</b> \u2014 51 structures \u00d7 3 spec modes "
    "\u00d7 a palette NAME that never reached the paint, so a structure's 2\u20133 cards had "
    "<b>byte-identical paint</b> and every card labelled \u201c(Blue)\u201d or \u201c(Green Toxic)\u201d was "
    "orange. <b>42 of the 51 were posters, not fields</b> \u2014 one sunburst, one spiral, one cone per "
    "whole car (<code>radial</code> scored 0.005 on the 8\u201332px car-band). "
    "These 75 are one card per idea, in five chapters that trace the life of a fire: "
    "\U0001F702 IGNITION \u00b7 \U0001F525 FLAME \u00b7 \u26A1 PLASMA \u00b7 \U0001F30B MOLTEN \u00b7 \U0001F703 CINDER. "
    "<b>Colour is physics now</b>: Planck's law through the CIE observer plus real chemiluminescence, "
    "so the FUEL that is burning decides the hue \u2014 copper green, strontium crimson, sodium amber, "
    "potassium lilac, barium apple, boron emerald. "
    "LEFT = full 2048 view \u00b7 MIDDLE = true 1:1 on-car pixel crop (<b>judge the finish here</b>) \u00b7 "
    "RIGHT = the spec map at 1:1 \u2014 complete material cards chosen per coherent cell from the same "
    "heat field that made the paint, with dark-chrome hot edges on the reaction front and the "
    "clearcoat structure offset from the metal/roughness one. "
    "\u23f1 = full-size render (all \u2264 3s).")

build_page("flames", TITLE, SUB, meta, THUMBS,
           os.path.join(ROOT, "SPB_AUDIT_flames.html"), accent="#ff7a1a")
print("PAGE OK SPB_AUDIT_flames.html")
