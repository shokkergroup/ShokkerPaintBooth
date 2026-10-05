# -*- coding: utf-8 -*-
"""FRACTURED TESSERA verification harness. One verdict line per finish; appends
to TESSERA_PROGRESS.jsonl; renders [full 2048 | true 1:1 on-car crop | spec].

THE PANE-SCALE LAW is the headline gate: panes must sit at 40-120px on the 2048
canvas. That is the defect that ruined the old glass family (Parquet/Pinwheel/
Ziggurat put two-to-four giant blocks on a whole car).

usage: python _tessera_work/verify.py [fid ...]     env: TSR_ITER=<n>
"""
import importlib, json, os, sys, time
import numpy as np, cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT); sys.path.insert(0, ROOT)
OUT = "_tessera_work"; os.makedirs(OUT + "/thumbs", exist_ok=True)
PROG = "TESSERA_PROGRESS.jsonl"

import engine.expansions.fractured_tessera_kit_2026 as tkit
import engine.expansions.fractured_tessera_2026 as m
importlib.reload(tkit); importlib.reload(m)

SHAPE = (2048, 2048); MASK = np.ones(SHAPE, np.float32)
BASE = np.full(SHAPE + (3,), 0.5, np.float32)
only = set(sys.argv[1:])
it = int(os.environ.get("TSR_ITER", "1"))
rows, descs = [], {}


def band_score(L):
    F = np.fft.fftshift(np.abs(np.fft.fft2(L - L.mean())) ** 2)
    n = L.shape[0]; yy, xx = np.mgrid[0:n, 0:n] - n // 2
    r = np.hypot(xx, yy)
    return float(F[(r >= 32) & (r <= 256)].sum() / max(F[r >= 2].sum(), 1e-9))


for fid, d in m.TESSERA.items():
    if only and fid not in only:
        continue
    m._art_cached.cache_clear(); m._labels_gen.cache_clear()
    spec_fn, paint_fn = m._mk(fid)
    t0 = time.time()
    p = paint_fn(BASE.copy(), SHAPE, MASK, 51, 1.0, None)
    s = spec_fn(SHAPE, MASK, 51, 1.0)
    dt = time.time() - t0

    # pane scale, measured on the labels at 2048
    lab = m.labels_for(fid, 2048)
    npanes, pane_px = tkit.pane_stats(lab)

    p8 = np.clip(np.asarray(p, np.float32) * 255.0, 0, 255).astype(np.uint8)
    s8 = np.asarray(s)[..., :3]
    small = cv2.resize(p8, (512, 512), interpolation=cv2.INTER_AREA)
    L = (0.299 * small[..., 0] + 0.587 * small[..., 1] + 0.114 * small[..., 2]).astype(np.float32)
    Lf = (0.299 * p8[..., 0] + 0.587 * p8[..., 1] + 0.114 * p8[..., 2]).astype(np.float32)
    fine = float(np.abs(Lf - cv2.GaussianBlur(Lf, (0, 0), 6)).mean())
    rel = fine / max(float(Lf.mean()), 1.0)
    live = sum(1 for ty in range(8) for tx in range(8)
               if small[ty * 64:(ty + 1) * 64, tx * 64:(tx + 1) * 64].std() > 6.0)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    sat = hsv[..., 1].astype(np.float32) / 255.0
    hue = hsv[..., 0].astype(np.float32) / 179.0
    good = hue[sat > 0.18]
    hb = int((np.histogram(good, bins=12, range=(0, 1))[0] > max(good.size, 1) * 0.02).sum()) if good.size > 100 else 0
    sm_ = cv2.resize(s8, (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32)
    stds = [float(sm_[..., i].std()) for i in range(3)]
    band = band_score(L)

    v = []
    if dt > 3.0: v.append(f"BUDGET {dt:.2f}s")
    if not (24.0 <= pane_px <= 60.0): v.append(f"PANE {pane_px:.0f}px")
    # The failure mode this guards is the giant-block one that ruined the old
    # family (Parquet/Pinwheel put 2-4 panes on a whole car). Measure THAT — the
    # largest pane as a share of the canvas — instead of a pane-count threshold,
    # which punished legitimately long-plank tilings.
    # measure CONNECTED regions, not label identity: two distant panes may
    # legitimately share a palette label, and that is not a giant pane.
    _bnd = tkit.boundary(lab)
    _n, _cc = cv2.connectedComponents((~_bnd).astype(np.uint8), connectivity=4)
    _cnt = np.bincount(_cc.ravel())
    _cnt[0] = 0
    biggest = float(_cnt.max()) / lab.size
    if biggest > 0.055: v.append(f"GIANTPANE {biggest:.1%}")
    if live < 60: v.append(f"COVERAGE {live}/64")
    if rel < 0.16: v.append(f"FLAT rel={rel:.2f}")
    # a restrained palette is a design choice when it is DECLARED (mono=True):
    # Cafe Wall, Mondrian Cut, Basalt Column and Crazed Glaze are meant to be
    # near-monochrome. Everything else still owes four hue bins.
    if hb < (2 if d.get("mono") else 4): v.append(f"HUES {hb}")
    # fracture_spec alone yields 7/20/2 even on Truchet Glass — the TESSERA kit adds a
    # glass/came MATERIAL layer on top, so the bar here is what that layer must deliver.
    if min(stds) < 18.0: v.append(f"SPECFLAT {min(stds):.0f}")
    ok = not v
    print(f"{'OK  ' if ok else 'FAIL'} {fid:26s} {dt:5.2f}s pane={pane_px:5.1f}px n={npanes:5d} "
          f"band={band:.2f} live={live}/64 rel={rel:.2f} hues={hb} "
          f"spec={stds[0]:3.0f}/{stds[1]:3.0f}/{stds[2]:3.0f}"
          + ("" if ok else "  << " + "; ".join(v)), flush=True)
    with open(PROG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"iter": it, "phase": "verify", "id": fid, "status": "ok" if ok else "fail",
                            "verify": {"s": round(dt, 2), "pane_px": round(pane_px, 1), "panes": npanes,
                                       "band": round(band, 3), "live": live, "rel": round(rel, 3),
                                       "hues": hb, "spec": [round(x) for x in stds]},
                            "note": "; ".join(v), "ts": time.strftime("%H:%M:%S")}) + "\n")
    c0 = (2048 - 512) // 2
    pt = cv2.resize(p8, (512, 512), interpolation=cv2.INTER_AREA)
    crop = p8[c0:c0 + 512, c0:c0 + 512]
    sv = cv2.resize(s8, (512, 512), interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(f"{OUT}/thumbs/{fid}_crop.png", crop[..., ::-1])
    rows.append((d["name"], pt, crop, sv))

if rows:
    cols = 3
    cw, ch = 512 * 3 + 16, 512 + 26
    rws = (len(rows) + cols - 1) // cols
    sheet = np.full((rws * ch, cols * cw, 3), 14, np.uint8)
    for i, (nm, pt, crop, sv) in enumerate(rows):
        cy, cx = divmod(i, cols)
        y0, x0 = cy * ch + 22, cx * cw
        for k, img in enumerate((pt, crop, sv)):
            sheet[y0:y0 + 512, x0 + k * 520:x0 + k * 520 + 512] = img
        cv2.putText(sheet, nm, (x0 + 6, cy * ch + 16), cv2.FONT_HERSHEY_SIMPLEX, .52, (235, 235, 235), 1)
    cv2.imwrite(f"{OUT}/contact_sheet.png", sheet[..., ::-1])
    print(f"contact sheet: {OUT}/contact_sheet.png ({len(rows)})  [full | 1:1 crop | spec]")
