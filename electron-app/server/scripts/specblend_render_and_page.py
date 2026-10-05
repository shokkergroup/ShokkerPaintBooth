# -*- coding: utf-8 -*-
"""SPEC BLEND physical modes — demo/review page. Renders each mode through the
REAL pipelines (compositing path + monolithic path) and builds
SPB_AUDIT_specblend.html so the owner can rate each mode like a finish."""
import os, sys, time, json
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import shokker_engine_v2 as E
from engine.compose import compose_finish_stacked
from engine.registry import PATTERN_REGISTRY
from spb_audit_page_builder import build_page

S = 1024
OUT = os.path.join(ROOT, "thumbnails", "audit", "specblend")
os.makedirs(OUT, exist_ok=True)
mask = np.ones((S, S), np.float32)

# a pattern with big readable shapes shows the modes best
PAT = next((p for p in ("camo", "tribal_flame", "skull", "carbon_fiber")
            if p in PATTERN_REGISTRY), sorted(PATTERN_REGISTRY)[0])

MODES = [
    ("ghost_carve", "\U0001F47B Ghost Carve",
     "THE one. Carves the Ghost Fracture color-shift contract into ANY base: the pattern becomes "
     "env-mirror cells (CC swings 64↔240), metal lobe untouched. Ritual: base + pattern + this mode "
     "+ crush color near black + daytime track — the pattern flashes sky-teal/sun-gold by angle on any finish/combo."),
    ("chrome_inlay", "\U0001FA9E Chrome Inlay",
     "Dielectric mirror inlay where the pattern is hot: metal dips, clearcoat ceilings, gloss floors "
     "(the blue-insight recipe). Hardest possible env flash — pattern reads as pure chrome inlays."),
    ("frost_etch", "❄ Frost Etch",
     "Pattern sandblasts the gloss: roughness way up, metal slightly down. Etched areas go milky in sun "
     "while the rest stays mirror — reads like acid-etched glass."),
    ("angle_flip", "\U0001F504 Angle Flip",
     "Pattern hot areas get metal-flash physics; the NEGATIVE SPACE gets mirror-flash physics. "
     "The pattern appears at one viewing angle and INVERTS at another. Nobody else has this."),
    ("ember_gate", "\U0001F525 Ember Gate",
     "Only the pattern's top ridges ignite (clearcoat pinned near max + gloss floor): sparkle ignition "
     "along edges, calm everywhere else. Best with patterns that have strong peaks."),
    ("depth_press", "\U0001F5DC Depth Press",
     "Emboss in spec only: every pattern element gets a lit rim and a shadow rim — the pattern reads "
     "STAMPED INTO the paint at speed, without touching the paint itself."),
]


def label(bgr, text):
    cv2.rectangle(bgr, (0, bgr.shape[0] - 22), (bgr.shape[1] - 1, bgr.shape[0] - 1), (12, 12, 12), -1)
    cv2.putText(bgr, text, (7, bgr.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (210, 210, 210), 1, cv2.LINE_AA)
    return bgr


def crop(spec):
    c = np.clip(spec[S // 4:S // 4 + 512, S // 4:S // 4 + 512, :3], 0, 255).astype(np.uint8)
    return c


def comp_spec(mode):
    return np.asarray(compose_finish_stacked(
        "metallic", [{"id": PAT, "opacity": 1.0}], (S, S), mask, 42, 1.0,
        base_spec_blend_mode=mode, monolithic_registry=E.MONOLITHIC_REGISTRY), np.float32)


def mono_spec(mode):
    spec = E.MONOLITHIC_REGISTRY["fm_python_skin"][0]((S, S), mask, 42, 1.0).copy()
    return np.asarray(E.overlay_pattern_on_spec(
        spec, PAT, (S, S), mask, 99, 1.0, 1.0, 1.0, blend_mode=mode), np.float32)


print("pattern:", PAT)
meta = []
ref_c, ref_m = comp_spec("normal"), mono_spec("normal")
for mode, name, desc in MODES:
    t0 = time.perf_counter()
    sc, sm_ = comp_spec(mode), mono_spec(mode)
    dt = time.perf_counter() - t0
    img = np.hstack([
        label(cv2.cvtColor(crop(sc), cv2.COLOR_RGB2BGR), f"{mode} on METALLIC base + {PAT}"),
        np.full((512, 4, 3), 24, np.uint8),
        label(cv2.cvtColor(crop(sm_), cv2.COLOR_RGB2BGR), f"{mode} on FM PYTHON SKIN + {PAT}"),
    ])
    cv2.imwrite(os.path.join(OUT, "blend_" + mode + ".png"), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    d = (np.abs(sc - ref_c).mean() + np.abs(sm_ - ref_m).mean()) / 2
    print("%-14s mean spec delta %5.1f  %.2fs" % (mode, d, dt))
    meta.append({"id": "blend_" + mode, "name": name, "kind": "finish",
                 "desc": desc, "ai_rating": int(np.clip(40 + d, 1, 99)),
                 "mip": 1.0, "render_s": round(dt, 2)})

json.dump(meta, open(os.path.join(ROOT, "scripts", "specblend_audit_meta.json"), "w", encoding="utf-8"), indent=1)

TITLE = ('<span class="flag">\U0001F47B SPEC BLEND — 6 physical blend modes (Spec Blend finally DOES something)</span> '
         '<span style="color:var(--dim);font-weight:400">(works on every base incl. FRACTURED MINDS — needs a pattern on the zone)</span>')
SUB = ("The old Photoshop modes were a silent no-op on monolithic bases and near-invisible elsewhere — replaced with "
       "OPTICAL behaviors. Every card: LEFT = mode on a classic metallic base, RIGHT = the same mode on Python Skin "
       "(spec view: red=metal, green=rough, blue=clearcoat). Both rendered through the real engine paths. "
       "In the app: Zones → Bases → Spec Blend dropdown — assign a PATTERN to the zone first, then pick a mode. "
       "\U0001F47B Ghost Carve + crush ritual = color shift on ANY finish/combo. Rate each mode; flag anything to retune. "
       "<b>SUBMIT THIS ONE</b> saves a card.")

build_page("specblend", TITLE, SUB, meta, OUT, os.path.join(ROOT, "SPB_AUDIT_specblend.html"), accent="#49e0c8")
print("WROTE SPB_AUDIT_specblend.html (%d cards)" % len(meta))
