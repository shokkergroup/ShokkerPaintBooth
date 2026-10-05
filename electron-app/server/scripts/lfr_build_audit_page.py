# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_letfreedomring.html via the shared builder
(scripts/spb_audit_page_builder.py): per-card submit, expanded reason chips,
render-time badges. Re-runnable each audit round."""
import json, os, sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from spb_audit_page_builder import build_page

META = json.load(open(os.path.join(ROOT, "scripts", "lfr_audit_meta.json"), encoding="utf-8"))

# attach measured full-size render times (paint+spec / tex+paint / single)
perf_path = os.path.join(ROOT, "scripts", "perf_results.json")
if os.path.exists(perf_path):
    perf = json.load(open(perf_path))
    for m in META:
        i = m["id"]
        if m["kind"] == "finish":
            t = perf.get(i + "/paint"), perf.get(i + "/spec")
        elif m["kind"] == "pattern":
            t = perf.get(i + "/tex"), perf.get(i + "/paint")
        else:
            t = (perf.get(i),)
        vals = [x for x in t if x is not None]
        if vals:
            m["render_s"] = round(sum(vals), 2)

TITLE = ('<span class="flag">\U0001F386 LET FREEDOM RING</span> — Round 1 Audit '
         '<span style="color:var(--dim);font-weight:400">(10 spec overlays · 10 patterns · 10 finishes)</span>')
SUB = ("Rate each item: <b>Keep</b> ships it · <b>Replace</b> = brand-new idea in that slot · <b>Rebuild</b> = same idea, redone · "
       "<b>Rename</b> = keep the look, fix the name · <b>Remove</b> = cut it. Check any number of “what's wrong” reasons. "
       "<b>SUBMIT THIS ONE</b> saves a single card immediately (tell Claude to work on what's submitted while you keep rating); "
       "“Submit ALL decided” in the bar still works. ⏱ badge = measured full-size render time (target ~1s, red &gt;3s). "
       "Spec-overlay swatches: left = raw field, right = real 3-channel spec (red=metallic, green=roughness, blue=clearcoat).")

build_page("letfreedomring", TITLE, SUB, META,
           os.path.join(ROOT, "thumbnails", "audit", "letfreedomring"),
           os.path.join(ROOT, "SPB_AUDIT_letfreedomring.html"), accent="#e8c050")
