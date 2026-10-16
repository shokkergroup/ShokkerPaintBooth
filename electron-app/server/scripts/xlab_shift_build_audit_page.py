# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_xlab_shift.html via the shared builder for the 20
X LAB // SHIFT WAVE finishes (owner commission 2026-08-29, x_lab_shift_2026.py).
Renders through the REAL registry path (one engine boot), composes per-card
swatch = [full-view paint | TRUE 1:1 crop | spec composite], then build_page.
Re-runnable each audit round."""
import io, json, os, sys, time, contextlib, logging

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import numpy as np
import cv2
from spb_audit_page_builder import build_page

IDS = ["xlab_prism_ivy", "xlab_shatter_royale", "xlab_moire_reactor", "xlab_serpent_scales",
       "xlab_stained_circuit", "xlab_riptide_parquet", "xlab_comet_terrace", "xlab_quasar_quilt",
       "xlab_glacier_chord", "xlab_murmuration", "xlab_ember_weave", "xlab_borealis_shards",
       "xlab_medusa_lattice", "xlab_static_bloom", "xlab_chrono_strata", "xlab_hex_reliquary",
       "xlab_velvet_meteor", "xlab_labyrinth_pulse", "xlab_opal_tessellate", "xlab_singularity_bloom"]

THUMBS = os.path.join(ROOT, "thumbnails", "audit", "xlab_shift")
os.makedirs(THUMBS, exist_ok=True)

logging.disable(logging.CRITICAL)
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    import shokker_engine_v2 as eng
from engine.expansions.x_lab_shift_2026 import BY_ID

shape = (2048, 2048)
mask = np.ones(shape, dtype=bool)
PANEL = 512

# Render times come from the CLEAN sequential look-ref bake (bake_refs.py), not
# from this composite pass, which often runs while suites/servers hog the box.
_man_path = os.path.join(ROOT, "_finish_look_refs", "2026-08-29", "manifest.json")
_man = json.load(open(_man_path, encoding="utf-8")) if os.path.exists(_man_path) else {}

meta = []
for fid in IDS:
    spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[fid]
    base = np.full(shape + (3,), 128, dtype=np.uint8)
    t0 = time.time()
    p = paint_fn(base.copy(), shape, mask, 51, 1.0, None)
    s = spec_fn(shape, mask, 51, 1.0)
    dt = _man.get(fid, {}).get("total_ms", (time.time() - t0) * 1000) / 1000.0
    p8 = np.clip(np.asarray(p, np.float32) * (255.0 if np.asarray(p).max() <= 1.5 else 1.0), 0, 255).astype(np.uint8)
    s8 = np.asarray(s)[..., :3].astype(np.uint8)
    full = cv2.resize(p8, (PANEL, PANEL), interpolation=cv2.INTER_AREA)
    c0 = (2048 - PANEL) // 2
    crop = p8[c0:c0 + PANEL, c0:c0 + PANEL]
    spec = cv2.resize(s8, (PANEL, PANEL), interpolation=cv2.INTER_NEAREST)
    tile = np.full((PANEL + 26, PANEL * 3 + 16, 3), 14, np.uint8)
    for i, (img, lab) in enumerate(((full, "FULL 2048 VIEW"), (crop, "TRUE 1:1 CROP"), (spec, "SPEC M/R/Cc"))):
        x0 = i * (PANEL + 8)
        tile[26:26 + PANEL, x0:x0 + PANEL] = img
        cv2.putText(tile, lab, (x0 + 4, 18), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
    cv2.imwrite(os.path.join(THUMBS, fid + ".png"), tile[..., ::-1])
    r = BY_ID[fid]
    meta.append({"id": fid, "name": r.name, "kind": "finish", "render_s": round(dt, 2),
                 "desc": r.story[0].upper() + r.story[1:]})
    print(f"{fid} {dt:.2f}s", flush=True)

TITLE = ('<span class="flag">\u26a1 X LAB // SHIFT WAVE</span> — Round 1 Audit '
         '<span style="color:var(--dim);font-weight:400">(20 new Hologram-Metal-mechanism finishes, X LAB 30\u219250)</span>')
SUB = ("Your commission: the Hologram Metal mechanism generalized \u2014 8-32px material cells in discrete chrome/gloss/satin/"
       "brushed/void states, flipped in COHERENT REGIONS by slow selector waves so whole panels trade colors with the light. "
       "Each card is a different partition math (florets, shards, moir\u00e9, scales, circuits, quasicrystals, flocks, mazes\u2026), "
       "not a recolor. LEFT = full 2048 view \u00b7 MIDDLE = true 1:1 on-car pixel crop \u00b7 RIGHT = real spec "
       "(red=metallic, green=roughness, blue=clearcoat \u2014 the flat plates ARE the mechanism). "
       "<b>SUBMIT THIS ONE</b> saves a card immediately. \u23f1 = full-size registry render (all \u22643s).")

build_page("xlab_shift", TITLE, SUB, meta, THUMBS,
           os.path.join(ROOT, "SPB_AUDIT_xlab_shift.html"), accent="#7affe8")
print("PAGE OK SPB_AUDIT_xlab_shift.html")
