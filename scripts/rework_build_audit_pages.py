# -*- coding: utf-8 -*-
"""Generate the 5 rework audit pages (SPB_AUDIT_<category>.html) via the shared
builder. Categories: insects, anime, neonunderground, chameleon, prizm."""
import json, os, sys

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from spb_audit_page_builder import build_page

META = json.load(open(os.path.join(ROOT, "scripts", "rework_audit_meta.json"), encoding="utf-8"))

PAGES = {
    "insects": ("🪲 IRIDESCENT INSECTS", "#7fd49a"),
    "anime": ("🌸 ANIME INSPIRED", "#ff9ec6"),
    "neonunderground": ("🌃 NEON UNDERGROUND", "#7df3ff"),
    "chameleon": ("🦎 CHAMELEON", "#b3ff70"),
    "prizm": ("🔮 PRIZM", "#c9a2ff"),
}

SUB = ("TOTAL REWORK with the new color-science engine (OKLab ramps, absorption, quantized interference, "
       "color-flip lattices, hue-travel specs) under the fineness doctrine — swatch LEFT is a TRUE 1:1 crop "
       "of the full 2048 render (real on-car pixel scale), RIGHT is the real material spec (red=metallic, "
       "green=roughness, blue=clearcoat). <b>SUBMIT THIS ONE</b> saves a card immediately; "
       "“Submit ALL decided” also works. ⏱ = full-size render time.")

for cat, (title, accent) in PAGES.items():
    items = [m for m in META if m["category"] == cat]
    if not items:
        print("skip", cat, "- no items"); continue
    build_page(cat, '<span class="flag">%s</span> — Rework Round 1 <span style="color:var(--dim);font-weight:400">(%d finishes)</span>' % (title, len(items)),
               SUB, items, os.path.join(ROOT, "thumbnails", "audit", cat),
               os.path.join(ROOT, "SPB_AUDIT_%s.html" % cat), accent=accent)
