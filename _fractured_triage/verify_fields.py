# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-AUDIT pass 2, 2026-08-02] Car-band field gate harness.

Gates (calibrated to FRACTURED MINDS, median 0.824):
  per finish : no exception; car-band >= 0.45; fineness > 6.5;
               coverage >= 56/64 (spec ch0 blockstd > 4); hue bins >= 5
               (36-bin, sat > 38, bin > 0.5% of pixels); cold time < 1.9 s @512
  per module : band median >= 0.60; max intra-module pair-cosine <= 0.55

Usage:  python verify_fields.py <frost|nebula|tempest> [--sheet] [--ids a,b]
Writes verify_<mod>.json incrementally (token mandate: incremental output).
"""
import json
import os
import sys
import time

import cv2
import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
TRIAGE = os.path.join(ROOT, "_fractured_triage")
sys.path.insert(0, ROOT)

RES = 512


def carband(luma):
    f = np.fft.fftshift(np.fft.fft2(luma - float(luma.mean())))
    P = (np.abs(f) ** 2).astype(np.float64)
    h, w = luma.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - h / 2.0, xx - w / 2.0)
    tot = P[r >= 2].sum()
    band = P[(r >= 64) & (r <= 256)].sum()
    return float(band / max(tot, 1e-12))


def fineness(luma):
    g255 = (luma * 255.0).astype(np.float32)
    return float(np.mean(np.abs(g255 - cv2.GaussianBlur(g255, (0, 0), 6.0))))


def coverage(spec):
    ch = spec[:, :, 0].astype(np.float32)
    n = 0
    bs = ch.shape[0] // 8
    for by in range(8):
        for bx in range(8):
            b = ch[by * bs:(by + 1) * bs, bx * bs:(bx + 1) * bs]
            if float(b.std()) > 4.0:
                n += 1
    return n


def hue_bins(paint):
    u8 = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV)
    m = hsv[:, :, 1] > 38
    tot = paint.shape[0] * paint.shape[1]
    if not m.any():
        return 0
    hist, _ = np.histogram(hsv[:, :, 0][m], bins=36, range=(0, 180))
    return int((hist > 0.005 * tot).sum())


def desc_vec(luma):
    g = cv2.resize(luma.astype(np.float32), (64, 64))

    def z(a):
        a = a.astype(np.float32).ravel()
        return (a - a.mean()) / (a.std() + 1e-9)

    sob = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3),
                   cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3))
    sp = np.log1p(np.abs(np.fft.fftshift(np.fft.fft2(g)))).astype(np.float32)
    v = np.concatenate([z(cv2.resize(g, (16, 16))),
                        z(cv2.resize(sob, (16, 16))),
                        z(cv2.resize(sp, (16, 16)))])
    return v / (np.linalg.norm(v) + 1e-9)


def main():
    mod = sys.argv[1]
    want_sheet = "--sheet" in sys.argv
    only = None
    for a in sys.argv[2:]:
        if a.startswith("--ids"):
            only = a.split("=", 1)[1].split(",")
    import importlib
    M = importlib.import_module("engine.expansions.fractured_%s_2026" % mod)
    KIT = M.KIT
    fids = sorted(KIT.ALL.keys())
    if only:
        fids = [f for f in fids if f in only]
    jpath = os.path.join(TRIAGE, "verify_%s.json" % mod)
    out = {"module": mod, "finishes": {}}
    lum = {}
    tiles = {}
    for fid in fids:
        row = {}
        try:
            KIT.art_work_cached.cache_clear()
            KIT.macro_cached.cache_clear()
            spec_fn, paint_fn = KIT.mk(fid)
            base = np.zeros((RES, RES, 3), np.float32)
            mask = np.ones((RES, RES), np.float32)
            t0 = time.perf_counter()
            p = paint_fn(base, (RES, RES), mask, 1234, 1.0, None)
            s = spec_fn((RES, RES), mask, 1234, 1.0)
            dt = time.perf_counter() - t0
            luma = (0.299 * p[:, :, 0] + 0.587 * p[:, :, 1] + 0.114 * p[:, :, 2])
            row = {"band": round(carband(luma), 4),
                   "fine": round(fineness(luma), 2),
                   "cov": coverage(s),
                   "hue": hue_bins(p),
                   "t": round(dt, 3)}
            row["ok"] = bool(row["band"] >= 0.45 and row["fine"] > 6.5
                             and row["cov"] >= 56 and row["hue"] >= 5
                             and row["t"] < 1.9)
            lum[fid] = luma
            tiles[fid] = p
        except Exception as e:  # noqa: BLE001 - gate reports, never dies
            row = {"error": "%s: %s" % (type(e).__name__, e), "ok": False}
        out["finishes"][fid] = row
        with open(jpath, "w") as fh:
            json.dump(out, fh, indent=1)
        print("VERDICT %-24s %s" % (fid, json.dumps(row)))

    bands = [r["band"] for r in out["finishes"].values() if "band" in r]
    med = float(np.median(bands)) if bands else 0.0
    worst = ("", "", -1.0)
    ids2 = [f for f in fids if f in lum]
    vecs = {f: desc_vec(lum[f]) for f in ids2}
    for i, a in enumerate(ids2):
        for b in ids2[i + 1:]:
            c = float(np.dot(vecs[a], vecs[b]))
            if c > worst[2]:
                worst = (a, b, c)
    out["summary"] = {"band_median": round(med, 4),
                      "band_min": round(min(bands), 4) if bands else 0,
                      "worst_pair": [worst[0], worst[1], round(worst[2], 4)],
                      "n_ok": sum(1 for r in out["finishes"].values() if r.get("ok")),
                      "n": len(fids)}
    with open(jpath, "w") as fh:
        json.dump(out, fh, indent=1)
    print("SUMMARY %s median=%.4f min=%.4f worst_pair=%s/%s cos=%.4f ok=%d/%d"
          % (mod, med, out["summary"]["band_min"], worst[0], worst[1], worst[2],
             out["summary"]["n_ok"], len(fids)))

    if want_sheet and tiles:
        TS, cols = 384, 5
        rows = (len(fids) + cols - 1) // cols
        sheet = np.zeros((rows * (TS + 18), cols * TS, 3), np.uint8)
        for i, fid in enumerate(fids):
            if fid not in tiles:
                continue
            p = tiles[fid]
            t8 = (np.clip(p / max(float(p.max()), 1e-6), 0, 1) * 255).astype(np.uint8)
            t8 = cv2.resize(t8, (TS, TS), interpolation=cv2.INTER_AREA)
            r0, c0 = (i // cols) * (TS + 18), (i % cols) * TS
            sheet[r0:r0 + TS, c0:c0 + TS] = t8[:, :, ::-1]
            cv2.putText(sheet, fid, (c0 + 4, r0 + TS + 13),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(TRIAGE, "resheet_%s.png" % mod), sheet)
        print("SHEET resheet_%s.png" % mod)


if __name__ == "__main__":
    main()
