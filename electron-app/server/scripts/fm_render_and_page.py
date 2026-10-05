# -*- coding: utf-8 -*-
"""FRACTURED MINDS round 3 — render the 22 v3 finishes (12 replacements with
all-new concepts + 10 rebuilds answering the owner's round-2 notes) through
the REAL registry entries and build SPB_AUDIT_fracturedminds5.html.
The 28 round-2 keeps are untouched and not re-shown."""
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
OUT = os.path.join(ROOT, "thumbnails", "audit", "fracturedminds5")
os.makedirs(OUT, exist_ok=True)

# per-card design story: NEW = replacement concept; REBUILT = your note -> the answer
BLURB = {
    "fm_petal_storm": "NEW (replaces Barbed Wire, your r14: 'make something else. Anything.') — a storm of drifting flower petals at every angle, each with a midrib vein. PASTEL spec: light-pink air, light-blue petals, light-purple ribs.",
    "fm_geode_slice": "PASTEL REBUILD (your note: 'Needs to be LIGHT PINK and LIGHT blue') — light-pink agate bands, LIGHT-blue rings and cores, light-purple druzy, rare gold ember sparks.",
    "fm_frost_lace": "PASTEL REBUILD (your r63 note) — the light-blue pane now keeps METAL HIGH so your body color explodes through it (that was the missing piece: dark blue = env mirror only; light blue = your color + env). Light-gray lace, light-pink tips.",
    "fm_inferno_veins": "PASTEL — light-pink plates, light-purple veins, light-blue halo rivers + REAL ORANGE embers inside the veins (the red/orange concoction: max metal + low clearcoat + mid rough).",
    "fm_thousand_eyes": "PASTEL horror — light-pink sclera, LIGHT-blue irises with light-purple spokes, light-gray veins; pupils stay dead-black voids for the stare.",
    "fm_glacier_core": "PASTEL — light-blue ice field, light-purple crevasses, light-pink frost ridges, light-gray grain shimmer.",
    "fm_ion_drift": "PASTEL — light-blue plasma field, light-purple stream cores, light-pink pulse heads, light-gray stars.",
    "fm_tide_glass": "PASTEL — light-blue pool floor, light-purple caustic web, light-pink nodes, light-gray depth swell.",
    "fm_witchlight": "PASTEL — light blue-gray mist, light-blue halos, light-pink orb cores, light-purple wisp tails.",
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


def crop(a):
    return (np.clip(a[768:1280, 768:1280], 0, 1) * 255).astype(np.uint8)


ids = sorted(BLURB)
mask = np.ones((S, S), np.float32)
base = np.full((S, S, 3), 0.5, np.float32)
meta = []
print("=== FRACTURED MINDS round 3 (%d changed) ===" % len(ids))
for fid in ids:
    spec_fn, paint_fn = E.MONOLITHIC_REGISTRY[fid]
    t0 = time.perf_counter()
    paint = np.clip(np.asarray(paint_fn(base, (S, S), mask, 42, 1.0, 1.0), np.float32)[:, :, :3], 0, 1)
    sp = np.asarray(spec_fn((S, S), mask, 42, 1.0), np.float32)
    dt = time.perf_counter() - t0
    spec = np.clip(sp[:, :, :3] / 255.0, 0, 1)
    fin = feature_fineness(paint, full_size=S); mip = mip_survival(paint)
    ai = ai_rating(paint, mip, fin.get("fine_fraction", 0.5))
    short = fid.replace("fm_", "")
    name = short.replace("_", " ").title()
    print("%-30s ai%3d  %.2fs" % (fid, ai, dt))
    img = np.hstack([label(cv2.cvtColor(crop(paint), cv2.COLOR_RGB2BGR), "canvas (1:1 crop of 2048)"),
                     np.full((512, 4, 3), 24, np.uint8),
                     label(cv2.cvtColor(crop(spec), cv2.COLOR_RGB2BGR), "spec  R=M G=R B=Cc")])
    cv2.imwrite(os.path.join(OUT, fid + ".png"), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    meta.append({"id": fid, "name": name, "kind": "finish",
                 "desc": BLURB[fid], "ai_rating": ai, "mip": round(float(mip), 2), "render_s": round(dt, 2)})

json.dump(meta, open(os.path.join(ROOT, "scripts", "fracturedminds5_audit_meta.json"), "w", encoding="utf-8"), indent=1)

TITLE = ('<span class="flag">🧠 FRACTURED MINDS round 5 — THE PASTEL DOCTRINE</span> '
         '<span style="color:var(--dim);font-weight:400">(your call: light pink / light blue / light purple / light gray in the combined spec — ingredient found: roughness 150-185 is what lightens it)</span>')
SUB = ("Round 5, built from your message: the combined spec now reads LIGHT pastels on all 9 non-keep cards "
       "(croc hide r68 untouched). Measured, not vibes: every card is gated on >=50% of spec pixels matching the four "
       "pastel targets. Barbed wire is gone — replaced by PETAL STORM. Inferno carries the orange-ember experiment. "
       "Ritual unchanged: assign as BASE + pick color + CRUSH brightness + daytime track. "
       "LEFT = canvas ghost (your color replaces it), RIGHT = combined spec "
       "(red=metal, green=rough, blue=clearcoat). <b>SUBMIT THIS ONE</b> saves a card.")

build_page("fracturedminds5", TITLE, SUB, meta, OUT, os.path.join(ROOT, "SPB_AUDIT_fracturedminds5.html"), accent="#7a5cff")
print("WROTE SPB_AUDIT_fracturedminds5.html (%d cards)" % len(meta))
