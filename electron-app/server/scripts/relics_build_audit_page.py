# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_relics.html via the shared builder for the rebuilt
FRACTURED RELICS (owner mandate 2026-08-30: 100 -> 50, one occult /
cryptozoology identity). Renders each finish through the REAL registry once and
composes the swatch as [full 2048 view | TRUE 1:1 on-car crop | spec M/R/Cc],
grouped by the five chapters of the cabinet. Re-runnable each audit round."""
import io, json, os, sys, time, contextlib, logging

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT); sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import numpy as np, cv2
from spb_audit_page_builder import build_page

THUMBS = os.path.join(ROOT, "thumbnails", "audit", "relics")
os.makedirs(THUMBS, exist_ok=True)
logging.disable(logging.CRITICAL)
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    import shokker_engine_v2 as eng
import engine.expansions.fractured_relics_2026 as m

SHAPE = (2048, 2048)
MASK = np.ones(SHAPE, np.float32)
BASE = np.full(SHAPE + (3,), 0.5, np.float32)
PANEL = 512

# per-finish timings from the lane's own verify log (measured on an idle box)
times = {}
if os.path.exists("FRACTURED_RELICS_PROGRESS.jsonl"):
    for line in io.open("FRACTURED_RELICS_PROGRESS.jsonl", encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("phase") == "verify" and r.get("status") == "ok":
            times[r["id"]] = r["verify"]["s"]

meta = []
for gname, grp in m.GROUPS.items():
    for fid, d in grp.items():
        spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[fid]
        t0 = time.time()
        p = paint_fn(BASE.copy(), SHAPE, MASK, 51, 1.0, None)
        s = spec_fn(SHAPE, MASK, 51, 1.0)
        dt = times.get(fid, time.time() - t0)
        p8 = np.clip(np.asarray(p, np.float32) * 255.0, 0, 255).astype(np.uint8)
        s8 = np.asarray(s)[..., :3].astype(np.uint8)
        full = cv2.resize(p8, (PANEL, PANEL), interpolation=cv2.INTER_AREA)
        c0 = (2048 - PANEL) // 2
        crop = p8[c0:c0 + PANEL, c0:c0 + PANEL]
        spec = cv2.resize(s8, (PANEL, PANEL), interpolation=cv2.INTER_NEAREST)
        tile = np.full((PANEL + 26, PANEL * 3 + 16, 3), 14, np.uint8)
        for i, (img, lab) in enumerate(((full, "FULL 2048 VIEW"),
                                        (crop, "TRUE 1:1 ON-CAR CROP"),
                                        (spec, "SPEC M/R/Cc"))):
            x0 = i * (PANEL + 8)
            tile[26:26 + PANEL, x0:x0 + PANEL] = img
            cv2.putText(tile, lab, (x0 + 4, 18), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
        cv2.imwrite(os.path.join(THUMBS, fid + ".png"), tile[..., ::-1])
        meta.append({"id": fid, "name": "%s  ·  %s" % (d["name"], gname),
                     "kind": "finish", "render_s": round(float(dt), 2),
                     "desc": d["desc"].replace(" A FRACTURED RELICS finish.", "")})
        print(f"{fid} {dt:.2f}s", flush=True)

TITLE = ('<span class="flag">\U0001f3fa FRACTURED RELICS</span> — Round 1 Audit '
         '<span style="color:var(--dim);font-weight:400">(the full rebuild: 100 \u2192 50)</span>')
SUB = ("Your mandate: one identity, everything unique, no cathedral glass or guilloche, heavy occult "
       "and cryptozoology. The old 100 were five COMBINATORIAL GRIDS (6 materials \u00d7 4 archetypes, "
       "6 glass colours \u00d7 6 window types\u2026) \u2014 that is why they felt the same at M7 86-91: the metric "
       "scores a recolor as well as an original. These 50 are OBJECTS: <b>the cabinet of cursed things</b>, "
       "in five chapters \u2014 \u26e7 THE BINDING (witch-work) \u00b7 \U0001f9b4 THE BEAST (cryptid remains) \u00b7 "
       "\u26b1 THE BARROW (grave goods) \u00b7 \U0001f70f THE ORACLE (divination) \u00b7 \u2697 THE ALEMBIC (alchemy). "
       "Every one has its own generator \u2014 no engine is shared by two finishes. "
       "LEFT = full 2048 view \u00b7 MIDDLE = true 1:1 on-car pixel crop (judge the object here) \u00b7 "
       "RIGHT = the spec map, carved into four material zones taken from that finish's OWN geometry "
       "(void / matrix / polished relief / metal inlay) plus tool-mark shoulders, structural tooth, "
       "patina grain, gated pits, metal fleck and a burial gradient. "
       "\u23f1 = full-size render (all \u2264 3s).")

build_page("relics", TITLE, SUB, meta, THUMBS,
           os.path.join(ROOT, "SPB_AUDIT_relics.html"), accent="#c8a05a")
print("PAGE OK SPB_AUDIT_relics.html")
