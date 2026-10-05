# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_fable.html via the shared builder
(scripts/spb_audit_page_builder.py): per-card submit, expanded reason chips,
render-time badges. Re-runnable each audit round."""
import json, os, sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from spb_audit_page_builder import build_page

META = json.load(open(os.path.join(ROOT, "scripts", "fable_audit_meta.json"), encoding="utf-8"))

perf_path = os.path.join(ROOT, "scripts", "perf_results.json")
if os.path.exists(perf_path):
    perf = json.load(open(perf_path))
    for m in META:
        vals = [perf.get(m["id"] + "/paint"), perf.get(m["id"] + "/spec")]
        vals = [x for x in vals if x is not None]
        if vals:
            m["render_s"] = round(sum(vals), 2)

TITLE = ('<span class="flag">✨ FABLE</span> — Round 2 Audit '
         '<span style="color:var(--dim);font-weight:400">(18 crushed-fine rebuilds; your 2 keepers stay hidden)</span>')
SUB = ("Round-2 rebuilds per your verdicts — everything CRUSHED finer per your multipliers (25x oilforge, 50x tempered arcs, 30x lantern circles…). "
       "Swatch LEFT is now a TRUE 1:1 crop of the full 2048 render (real on-car pixel scale), RIGHT = real material spec "
       "(red=metallic, green=roughness, blue=clearcoat). <b>SUBMIT THIS ONE</b> saves a card immediately; “Submit ALL decided” still works. "
       "⏱ = full-size render time (target ~1s, red &gt;3s).")

build_page("fable", TITLE, SUB, META,
           os.path.join(ROOT, "thumbnails", "audit", "fable"),
           os.path.join(ROOT, "SPB_AUDIT_fable.html"), accent="#c9a2ff")
