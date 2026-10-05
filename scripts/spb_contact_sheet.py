# -*- coding: utf-8 -*-
"""SPB CONTACT SHEET — render a shelf at 2048 and show it at 1:1.

CLAUDE.md: "never report a gate green without looking at a 1:1 contact sheet —
every failure in this project's history was visible instantly by eye."

Renders every finish in a module's CATALOG at the shipping size, times it against
the 3s budget, and writes two sheets of TRUE 1:1 crops (no downscaling — a
thumbnail hides exactly the faults that matter):

    <out>_paint.png   the finish over a mid-grey source
    <out>_spec.png    its spec map as RGB = (M, R, CC)

USAGE
    python scripts/spb_contact_sheet.py --module engine.paint_v2.wrap_shop_2026
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def sheet(module_name, out, res=2048, crop=440, cols=6, seed=51, source=None):
    mod = importlib.import_module(module_name)
    cat = mod.CATALOG
    ids = sorted(cat)
    shape = (res, res)
    mask = np.ones(shape, np.float32)
    if source is None:
        # the SAME livery source the variant search scores against, so what I judge
        # by eye and what the harness scores are the same picture
        src = np.zeros(shape + (3,), np.float32)
        src[:, :, 0], src[:, :, 1], src[:, :, 2] = 0.62, 0.13, 0.16
    else:
        src = source
    rows = (len(ids) + cols - 1) // cols
    pad, lab = 6, 16
    tile = crop + pad
    sheets = {"paint": np.zeros((rows * (tile + lab) + pad, cols * tile + pad, 3), np.float32),
              "spec": np.zeros((rows * (tile + lab) + pad, cols * tile + pad, 3), np.float32)}
    slow, timings = [], []
    for i, fid in enumerate(ids):
        r, c = divmod(i, cols)
        t0 = time.time()
        paint = np.asarray(getattr(mod, "paint_" + fid)(src, shape, mask, seed, 1.0, None), np.float32)
        t_paint = time.time() - t0
        t1 = time.time()
        M, R, CC = getattr(mod, "spec_" + fid)(shape, seed, 1.0,
                                               cat[fid].get("M", 0), cat[fid].get("R", 100))
        t_spec = time.time() - t1
        tot = t_paint + t_spec
        timings.append((fid, tot))
        if tot > 3.0:
            slow.append((fid, tot))
        o = (res - crop) // 2
        p = np.clip(paint[o:o + crop, o:o + crop, :3], 0, 1)
        s = np.dstack([np.asarray(M, np.float32)[o:o + crop, o:o + crop],
                       np.asarray(R, np.float32)[o:o + crop, o:o + crop],
                       np.asarray(CC, np.float32)[o:o + crop, o:o + crop]]) / 255.0
        y0 = pad + r * (tile + lab)
        x0 = pad + c * tile
        sheets["paint"][y0:y0 + crop, x0:x0 + crop] = p
        sheets["spec"][y0:y0 + crop, x0:x0 + crop] = np.clip(s, 0, 1)
    try:
        from PIL import Image, ImageDraw
        for k, arr in sheets.items():
            img = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
            d = ImageDraw.Draw(img)
            for i, fid in enumerate(ids):
                r, c = divmod(i, cols)
                d.text((pad + c * tile + 2, pad + r * (tile + lab) + crop + 2),
                       f"{i + 1:02d} {fid.replace('wrap_', '').replace('_', ' ')}",
                       fill=(255, 255, 255))
            img.save(f"{out}_{k}.png")
            print(f"-> {out}_{k}.png  ({img.size[0]}x{img.size[1]})")
    except Exception as exc:
        print(f"!! PIL unavailable ({exc}); sheets not written")
    timings.sort(key=lambda t: -t[1])
    print("slowest: " + ", ".join(f"{f} {t:.2f}s" for f, t in timings[:5]))
    if slow:
        print(f"!! OVER 3s BUDGET: {', '.join(f'{f} {t:.1f}s' for f, t in slow)}")
    else:
        print(f"OK all {len(ids)} finishes inside the 3s budget at {res}")
    return slow


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--res", type=int, default=2048)
    ap.add_argument("--crop", type=int, default=440)
    ap.add_argument("--cols", type=int, default=6)
    a = ap.parse_args()
    out = a.out or os.path.join(ROOT, "_sheets", a.module.rsplit(".", 1)[-1])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet(a.module, out, a.res, a.crop, a.cols)
