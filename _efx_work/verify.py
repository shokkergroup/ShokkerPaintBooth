#!/usr/bin/env python3
"""FOUNDATION EFX verification harness — one process, one verdict line per finish.

Uses the FINISH LAW's own axis functions (scripts/spb_finish_law.py: scale_axis,
follow_axis, coverage_axis, richness_eff) on the same gray-plate render the law makes,
so a verdict here is the verdict the gate will give. Writes append-only JSONL and a
1:1 contact sheet (paint | spec crops).

    python _efx_work/verify.py --res 1024 --sheet r2 --tag r2      # all rows
    python _efx_work/verify.py --res 2048 --ids a,b                 # final, native
"""
from __future__ import annotations
import argparse, importlib.util, json, sys, time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from PIL import Image, ImageDraw  # noqa: E402

import engine.paint_v2.foundation_efx_2026 as X  # noqa: E402

_spec = importlib.util.spec_from_file_location("spb_finish_law", ROOT / "scripts" / "spb_finish_law.py")
LAW = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(LAW)

OUT = ROOT / "_efx_work"
OUT.mkdir(exist_ok=True)
PROG = OUT / "EFX_PROGRESS.jsonl"
GATES = dict(fine=0.20, follow=0.35, dead=0.70, t2048=3.0)


def render(fid, res):
    e = X.FOUNDATION_EFX[fid]
    shape = (res, res)
    mask = np.ones(shape, np.float32)
    t0 = time.perf_counter()
    paint = e["paint_fn"](np.full(shape + (3,), 0.5, np.float32), shape, mask, 51, 1.0, None)
    t1 = time.perf_counter()
    m, r, c = e["base_spec_fn"](shape, 51, 1.0, e["M"], e["R"])
    t2 = time.perf_counter()
    spec = np.dstack([np.asarray(x, np.float32) for x in (m, r, c)])
    return np.asarray(paint, np.float32)[..., :3], np.clip(spec, 0, 255), t1 - t0, t2 - t1


def axes(paint, spec):
    pl = LAW._luma(paint)
    sl = LAW._luma(spec / 255.0)
    band_p, coarse_p = LAW.scale_axis(pl)
    band_s, coarse_s = LAW.scale_axis(sl)
    mi, amp = LAW.follow_axis(paint, spec)
    dead = LAW.coverage_axis(paint)
    eff = LAW.richness_eff(spec)
    mats, shades = LAW.richness_axis(spec)
    return dict(fine_paint=round(band_p, 3), fine_spec=round(band_s, 3), fine=round(max(band_p, band_s), 3),
                coarse=round(max(coarse_p, coarse_s), 3), follow=round(amp, 3), mi=round(mi, 3),
                dead=round(dead, 3), rich=round(eff, 2), mats=mats, shades=shades)


def judge(fid, res):
    paint, spec, tp, ts = render(fid, res)
    row = dict(id=fid, res=res, t_paint=round(tp, 2), t_spec=round(ts, 2), t=round(tp + ts, 2))
    row.update(axes(paint, spec))
    row["std"] = [round(float(spec[..., i].std()), 1) for i in range(3)]
    ok = row["fine"] >= GATES["fine"] and row["follow"] >= GATES["follow"] and row["dead"] <= GATES["dead"]
    if res >= 2048:
        ok = ok and row["t"] <= GATES["t2048"]
    row["ok"] = bool(ok)
    return row, paint, spec


def crop_pair(paint, spec, crop):
    h = paint.shape[0]
    y0 = (h - crop) // 2
    p = (np.clip(paint[y0:y0 + crop, y0:y0 + crop], 0, 1) * 255).astype(np.uint8)
    s = np.clip(spec[y0:y0 + crop, y0:y0 + crop], 0, 255).astype(np.uint8)
    return np.concatenate([p, s], axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=1024)
    ap.add_argument("--ids", default="")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--crop", type=int, default=400)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    for p in X.check():
        print("CHECK", p)
    ids = [s for s in a.ids.split(",") if s] or [r["fid"] for r in X.ROWS]
    tiles, nbad = [], 0
    for fid in ids:
        try:
            row, paint, spec = judge(fid, a.res)
        except Exception as ex:                                  # noqa: BLE001
            row = dict(id=fid, res=a.res, ok=False, error=repr(ex)[:200])
            print(f"VERDICT FAIL {fid:24s} ERROR {row['error']}")
            nbad += 1
            with PROG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(dict(row, tag=a.tag, ts=time.strftime("%Y-%m-%dT%H:%M:%S"))) + "\n")
            continue
        nbad += (not row["ok"])
        flag = "ok  " if row["ok"] else "FAIL"
        print(f"VERDICT {flag} {fid:24s} t={row['t']:5.2f}s fine={row['fine']:.3f} (p{row['fine_paint']:.2f}/s{row['fine_spec']:.2f}) "
              f"coarse={row['coarse']:.2f} follow={row['follow']:.3f} dead={row['dead']:.2f} rich={row['rich']:.1f} mats={row['mats']:2d} std={row['std']}")
        with PROG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(row, tag=a.tag, ts=time.strftime("%Y-%m-%dT%H:%M:%S"))) + "\n")
        if a.sheet:
            tiles.append((fid, crop_pair(paint, spec, min(a.crop, a.res))))
    if a.sheet and tiles:
        cw, ch = tiles[0][1].shape[1], tiles[0][1].shape[0]
        cols = a.cols
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (cw + 8), rows * (ch + 26)), (14, 14, 16))
        d = ImageDraw.Draw(sheet)
        for i, (fid, tile) in enumerate(tiles):
            x, y = (i % cols) * (cw + 8), (i // cols) * (ch + 26)
            sheet.paste(Image.fromarray(tile), (x + 4, y + 4))
            d.text((x + 6, y + ch + 8), f"{fid}  ({X.BY_ID[fid]['name']})", fill=(235, 235, 235))
        p = OUT / f"sheet_{a.sheet}.png"
        sheet.save(p)
        print("SHEET", p, sheet.size)
    print(f"SUMMARY {len(ids) - nbad}/{len(ids)} ok at {a.res}")
    return 1 if nbad else 0


if __name__ == "__main__":
    sys.exit(main())
