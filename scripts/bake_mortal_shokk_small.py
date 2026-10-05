# -*- coding: utf-8 -*-
"""Bake 2048 near-lossless PNG derivatives of the Mortal Shokk 4K plates.

The 26 ms_* finishes ship 4096^2 PNG plates (~33-48MB each). A cold render decodes one
(~640ms) then downscales it to the <=1024 work grid / 256 swatch — so ~85% of render time
is PNG inflate that's thrown away. This bakes a 2048 derivative per finish into
assets/reference_textures/mortal_shokk/png_2048/<id>.png; cultural_mortal_shokk._texture_path
prefers it at runtime (SPB_MORTAL_SHOKK_USE_SMALL=0 to fall back to 4K).

PNG (not JPEG) keeps it near-lossless — the only change is the 4096->2048 downscale, which is
imperceptible since the work grid caps at 1024. Footer crop stays at LOAD time (resolution-
independent), so bake the FULL frame here. Run: python -B scripts/bake_mortal_shokk_small.py
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum")
ASSET = ROOT / "assets" / "reference_textures" / "mortal_shokk"
SMALL = ASSET / "png_2048"
TARGET = 2048

SMALL.mkdir(parents=True, exist_ok=True)
manifest = json.loads((ASSET / "manifest.json").read_text(encoding="utf-8"))

n = miss = 0
tot_in = tot_out = 0
for item in manifest.get("finishes", []):
    fid = str(item.get("id") or "")
    rel = item.get("file")
    if not fid or not rel:
        continue
    src = ASSET / str(rel)
    if not src.exists():
        print("MISSING src:", fid, "->", rel)
        miss += 1
        continue
    dst = SMALL / (fid + ".png")
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if max(w, h) > TARGET:
        s = TARGET / float(max(w, h))
        im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    im.save(dst, "PNG", optimize=True)
    si, so = src.stat().st_size, dst.stat().st_size
    tot_in += si
    tot_out += so
    n += 1
    print("baked %-26s %s  %.1fMB -> %.2fMB" % (fid, im.size, si / 1e6, so / 1e6))

print("DONE: %d baked, %d missing.  %.0f MB (4K) -> %.0f MB (2048)" % (n, miss, tot_in / 1e6, tot_out / 1e6))
