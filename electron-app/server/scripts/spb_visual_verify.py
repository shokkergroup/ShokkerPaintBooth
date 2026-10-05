# -*- coding: utf-8 -*-
"""Render a shelf at FULL 2048 and look at it honestly.

Owner 2026-09-01: *"Can you make VISUAL PICTURES of these finishes, look at them
honestly at full 2048x2048 scale (along with their specs) and ENSURE they are
truly unique, interesting, different, etc?"*

Two things every gate in this repo has failed to catch at some point, and both
are only visible by eye:

1. A shelf can pass every numeric axis and still be one look recoloured. The
   FINISH LAW's own notes record this happening twice.
2. A 155px swatch and a 2048px car are different pictures. Detail that reads at
   swatch size can vanish on the car, and detail that reads on the car can
   average to flat in the picker.

So this renders at NATIVE 2048 and crops 1:1 — no downsampling anywhere in the
path — and puts PAINT beside SPEC for each finish.

`--repeats` is the decisive mode: it groups finishes that share a construction
and lays them adjacent, so "these two are the same thing recoloured" is a
judgement made by looking at them next to each other rather than by trusting a
similarity number.

USAGE
    python scripts/spb_visual_verify.py --group "PARADIGM"
    python scripts/spb_visual_verify.py --group "PARADIGM" --repeats
    python scripts/spb_visual_verify.py --group "FABLE" --crop 520 --cols 6
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT = REPO / "_verify"
RES = 2048


def _engine():
    logging.disable(logging.CRITICAL)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import shokker_engine_v2 as eng
        eng._ensure_expansions_loaded()
    return eng


def _groups():
    import subprocess
    js = REPO / "_groups.json"
    if not js.exists():
        subprocess.run(["node", "-e",
                        "const fs=require('fs');const g={};"
                        "new Function('g',fs.readFileSync('paint-booth-0-finish-data.js','utf8')"
                        "+';g.SG=SPECIAL_GROUPS;g.BG=BASE_GROUPS;')(g);"
                        "fs.writeFileSync('_groups.json',JSON.stringify({SG:g.SG,BG:g.BG}),'utf8');"],
                       cwd=str(REPO), check=True, capture_output=True)
    d = json.loads(js.read_text(encoding="utf-8"))
    out = {}
    out.update(d["SG"])
    out.update(d["BG"])
    return out


def render_native(eng, fid, res=RES):
    """Paint and spec at native `res`. Nothing here is resized."""
    shape = (res, res)
    mask = np.ones(shape, np.float32)
    mono, base = eng.MONOLITHIC_REGISTRY, eng.BASE_REGISTRY
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        if fid in mono:
            entry = mono[fid]
            sf, pf = (entry[0], entry[1]) if isinstance(entry, tuple) else (
                entry.get("spec_fn"), entry.get("paint_fn"))
            spec = np.asarray(sf(shape, mask, 51, 1.0), np.float32)[..., :3]
            paint = np.asarray(pf(np.full(shape + (3,), 0.5, np.float32),
                                  shape, mask, 51, 1.0, None), np.float32)
        elif fid in base:
            e = base[fid]
            m, r, c = e["base_spec_fn"](shape, 51, 1.0, e.get("M", 0), e.get("R", 100))
            spec = np.dstack([np.asarray(x, np.float32) for x in (m, r, c)])
            paint = np.asarray(e["paint_fn"](np.full(shape + (3,), 0.5, np.float32),
                                             shape, mask, 51, 1.0, None), np.float32)
        else:
            return None, None
    paint = paint[..., :3]
    if float(paint.max()) > 1.5:
        paint = paint / 255.0
    return np.clip(paint, 0, 1), np.clip(spec, 0, 255)


def _u8(a, is_paint):
    return (np.clip(a, 0, 1) * 255).astype(np.uint8) if is_paint else np.clip(a, 0, 255).astype(np.uint8)


def sheet(eng, ids, path, crop=430, cols=6, label=lambda f: f, note=None):
    """PAINT beside SPEC, both 1:1 crops out of a native 2048 render."""
    from PIL import Image, ImageDraw
    rows = (len(ids) + cols - 1) // cols
    pad = 17
    im = Image.new("RGB", (cols * crop * 2, rows * (crop + pad) + (26 if note else 0)), (10, 10, 12))
    d = ImageDraw.Draw(im)
    y0 = 26 if note else 0
    if note:
        d.text((6, 7), note, fill=(220, 220, 230))
    o = (RES - crop) // 2
    for i, fid in enumerate(ids):
        p, s = render_native(eng, fid)
        if p is None:
            continue
        x = (i % cols) * crop * 2
        y = y0 + (i // cols) * (crop + pad)
        im.paste(Image.fromarray(_u8(p, True)[o:o + crop, o:o + crop]), (x, y))
        im.paste(Image.fromarray(_u8(s, False)[o:o + crop, o:o + crop]), (x + crop, y))
        d.text((x + 4, y + crop + 3), label(fid)[:48], fill=(200, 200, 210))
    OUT.mkdir(exist_ok=True)
    im.save(path)
    return path


def construction_groups(gname):
    """Finishes that share a construction, so they can be judged side by side."""
    import collections, importlib
    MODS = {
        "ALL THAT": ("engine.paint_v2.era_1990s_2026", "stack", 50),
        "BAD & RAD": ("engine.paint_v2.era_1980s_2026", "stack", 50),
        "CYBERPUNK": ("engine.paint_v2.cyberpunk_2026", "stack", 50),
        "FAR OUT": ("engine.paint_v2.era_1970s_2026", "stack", 50),
        "TACTICAL & FIELD": ("engine.paint_v2.tactical_2026", "stack", 50),
        "FRACTURED FLAMES": ("engine.expansions.fractured_flames_2026", "build", 70),
        "PARADIGM": ("engine.expansions.paradigm_2026", "stack", 40),
        "WORLD OF COLOR": ("engine.expansions.world_of_color_2026", "stack", 90),
        "FRACTURED ELEMENTS": ("engine.expansions.fractured_elements_2026", "stack", 50),
    }
    hit = next((k for k in MODS if k.lower() in gname.lower()), None)
    if hit is None:
        return []
    mp, key, mn = MODS[hit]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        M = importlib.import_module(mp)
    tbl = None
    for a in dir(M):
        v = getattr(M, a)
        if isinstance(v, dict) and len(v) >= mn and all(isinstance(x, dict) for x in list(v.values())[:3]):
            tbl = v
            break
    if tbl is None:
        return []
    g = collections.defaultdict(list)
    for fid, d in tbl.items():
        st = d.get(key) or []
        g[tuple(sorted((s[0] if isinstance(s, (list, tuple)) else str(s)) for s in st))].append(fid)
    return sorted((v for v in g.values() if len(v) > 1), key=len, reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="")
    ap.add_argument("--repeats", action="store_true",
                    help="only finishes that SHARE a construction, laid adjacent")
    ap.add_argument("--crop", type=int, default=430)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--limit", type=int, default=24)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--ids", default="", help="comma-separated finish ids: render just these (any group)")
    ap.add_argument("--out", default="", help="sheet name override (used with --ids)")
    args = ap.parse_args()

    if args.ids:
        ids = [x.strip() for x in args.ids.split(",") if x.strip()]
        eng = _engine()
        name = args.out or "ids"
        path = OUT / ("verify_%s.png" % name)
        sheet(eng, ids, path, args.crop, args.cols,
              note="%d finishes by id - 1:1 crops from native 2048 renders. PAINT | SPEC" % len(ids))
        print("wrote %s" % path)
        return 0

    groups = _groups()
    if not args.group:
        print("need --group or --ids")
        return 2
    keys = [k for k in groups if args.group.lower() in k.lower()]
    if not keys:
        print("no group matching %r" % args.group)
        return 2
    key = keys[0]
    name = key.encode("ascii", "ignore").decode().strip().replace(" ", "_").replace("&", "and")
    eng = _engine()

    if args.repeats:
        gs = construction_groups(key)
        if not gs:
            print("no shared constructions found for %s" % name)
            return 0
        ids, labels = [], {}
        for gi, grp in enumerate(gs):
            for fid in grp:
                ids.append(fid)
                labels[fid] = "[g%d] %s" % (gi + 1, fid)
            if len(ids) >= args.limit:
                break
        path = OUT / ("repeats_%s.png" % name.lower())
        sheet(eng, ids[:args.limit], path, args.crop, args.cols,
              label=lambda f: labels.get(f, f),
              note="%s - finishes SHARING a construction, laid adjacent. 1:1 crops from native 2048. PAINT | SPEC" % name)
        print("shared-construction groups: %d covering %d finishes"
              % (len(gs), sum(len(g) for g in gs)))
        print("wrote %s" % path)
        return 0

    ids = groups[key][args.offset:args.offset + args.limit]
    path = OUT / ("verify_%s%s.png" % (name.lower(), ("_%d" % args.offset) if args.offset else ""))
    sheet(eng, ids, path, args.crop, args.cols,
          note="%s - 1:1 crops from native 2048 renders. PAINT | SPEC" % name)
    print("wrote %s" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
