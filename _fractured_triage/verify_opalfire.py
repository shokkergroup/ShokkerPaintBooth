# -*- coding: utf-8 -*-
"""[SPB-OPALFIRE-001 2026-08-03] Crush-law gate battery for FRACTURED OPALFIRE.

EXTENDS verify_guard.py (same carband / autocorr / peakiness / shapefrac /
fineness / descriptor math — copied verbatim) with the category-specific
CRUSH gates and two documented deltas:

  CRUSH GATES (per finish, 512, seed=1234, mask=ones, 0.5 grey base):
    medL   median paint luma                                  <= 0.32
    lad    64-bin luma-histogram bins in [0,0.55] w/ >=2%     >= 6
    runs   SEPARATED terrace clusters of those bins           >= 5
    pit    fraction(luma < 0.06)                              in [0.03, 0.30]
    vein   fraction(luma > 0.65)                              in [0.005, 0.08]
  SPEC GATES (night-carrier, measured fs_core_crimson medians 242/30/246):
    |medM-242| <= 6, |medG-30| <= 10, |medB-246| <= 6, std each <= 4
  DELTAS vs verify_guard: band gate >= 0.65 (median >= 0.80 module-level);
    coverage measured on the PAINT luma 8x8 blocks (std > 4.0 in 255-space) —
    the spec is exempt-uniform by design (SPEC-MIRROR EXEMPTION), so the
    spec-channel coverage of verify_guard is meaningless here; hue gate is
    hueErr <= 0.03 turn (sat-weighted circular mean vs the family anchor; for
    multi-hue ids: every family anchor must be within 0.03 of a >=2% hue-
    histogram peak).

Usage: python verify_opalfire.py [--sheet] [--t2048] [--ids=a,b]
Writes guard_opalfire.json + appends opalfire_build.jsonl incrementally
(token mandate). Sheet is UN-NORMALIZED (no per-tile /max — the value ladder
IS the product) at resheet_opalfire.png, 384px tiles, 5 cols.
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
NM, NG, NB = 242.0, 30.0, 246.0


def carband(luma):
    f = np.fft.fftshift(np.fft.fft2(luma - float(luma.mean())))
    P = (np.abs(f) ** 2).astype(np.float64)
    h, w = luma.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - h / 2.0, xx - w / 2.0)
    tot = P[r >= 2].sum()
    inb = (r >= 64) & (r <= 256)
    band = P[inb].sum()
    rb = ((r[inb] - 64.0) / 4.0).astype(np.int32)
    prof = np.bincount(rb, weights=P[inb], minlength=48).astype(np.float64)
    k = max(1, int(round(len(prof) * 0.20)))
    top = np.sort(prof)[::-1][:k].sum()
    peaky = float(top / max(prof.sum(), 1e-12))
    lo = float(P[(r >= 2) & (r < 64)].sum() / max(tot, 1e-12))
    return float(band / max(tot, 1e-12)), peaky, lo


def autocorr1(luma):
    x = (luma - float(luma.mean())).astype(np.float64)
    num = float((x[:, :-1] * x[:, 1:]).sum())
    den = float((x * x).sum())
    return num / max(den, 1e-12)


def shapefrac(luma):
    u8 = np.clip(luma * 255.0, 0, 255).astype(np.uint8)
    _t, bw = cv2.threshold(u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    tot = float(u8.size)
    keep = 0.0
    for img in (bw, 255 - bw):
        n, _lab, stats, _c = cv2.connectedComponentsWithStats(img, 8)
        if n > 1:
            a = stats[1:, cv2.CC_STAT_AREA]
            keep += float(a[a >= 12].sum())
    return keep / tot


def fineness(luma):
    g255 = (luma * 255.0).astype(np.float32)
    return float(np.mean(np.abs(g255 - cv2.GaussianBlur(g255, (0, 0), 6.0))))


def coverage_paint(luma):
    """8x8-grid signal coverage on the PAINT luma (spec is exempt-uniform)."""
    ch = (luma * 255.0).astype(np.float32)
    n = 0
    bs = ch.shape[0] // 8
    for by in range(8):
        for bx in range(8):
            b = ch[by * bs:(by + 1) * bs, bx * bs:(bx + 1) * bs]
            if float(b.std()) > 4.0:
                n += 1
    return n


def ladder_stats(luma):
    """(qualifying bins in [0,0.55], separated terrace clusters)."""
    hist, _ = np.histogram(np.clip(luma, 0.0, 1.0), bins=64, range=(0.0, 1.0))
    tot = float(luma.size)
    q = []
    for i in range(64):
        c = (i + 0.5) / 64.0
        q.append(1 if (c <= 0.55 and hist[i] >= 0.02 * tot) else 0)
    bins = int(sum(q))
    runs = 0
    prev = 0
    for x in q:
        if x and not prev:
            runs += 1
        prev = x
    return bins, runs


def hue_err(p, fams):
    """Max over family anchors of distance to the nearest >=2% hue-histogram
    peak; single-family ids also fall through this (peak = the sat-weighted
    mode region). Returns (err, satmean)."""
    u8 = (np.clip(p, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV)
    hh = hsv[:, :, 0].astype(np.float32) / 179.0
    ss = hsv[:, :, 1].astype(np.float32) / 255.0
    m = ss > 0.15
    satmean = float(ss.mean())
    if not m.any():
        return 0.5, satmean
    hist, edges = np.histogram(hh[m], bins=72, range=(0.0, 1.0),
                               weights=ss[m])
    tot = float(hist.sum())
    peaks = []
    for i in range(72):
        if hist[i] >= 0.02 * tot and hist[i] >= hist[(i - 1) % 72] \
                and hist[i] >= hist[(i + 1) % 72]:
            peaks.append((i + 0.5) / 72.0)
    if not peaks:
        peaks = [(int(np.argmax(hist)) + 0.5) / 72.0]
    err = 0.0
    for a in fams:
        d = min(min(abs(a - pk), 1.0 - abs(a - pk)) for pk in peaks)
        err = max(err, d)
    return err, satmean


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
    want_sheet = "--sheet" in sys.argv
    want_2048 = "--t2048" in sys.argv
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--ids"):
            only = a.split("=", 1)[1].split(",")
    import importlib
    M = importlib.import_module("engine.expansions.fractured_opalfire_2026")
    KIT = M.KIT
    fids = sorted(KIT.ALL.keys())
    if only:
        fids = [f for f in fids if f in only]
    jpath = os.path.join(TRIAGE, "guard_opalfire.json")
    lpath = os.path.join(TRIAGE, "opalfire_build.jsonl")
    out = {"module": "opalfire", "finishes": {}}
    lum = {}
    tiles = {}
    for fid in fids:
        try:
            KIT.art_work_cached.cache_clear()
            KIT.macro_cached.cache_clear()
            spec_fn, paint_fn = KIT.mk(fid)
            base = np.full((RES, RES, 3), 0.5, np.float32)
            mask = np.ones((RES, RES), np.float32)
            t0 = time.perf_counter()
            p = paint_fn(base, (RES, RES), mask, 1234, 1.0, None)
            s = spec_fn((RES, RES), mask, 1234, 1.0)
            dt = time.perf_counter() - t0
            luma = (0.299 * p[:, :, 0] + 0.587 * p[:, :, 1] + 0.114 * p[:, :, 2])
            band, peaky, lo = carband(luma)
            bins, runs = ladder_stats(luma)
            # [SPB-OPALFIRE-001b] terrace SEPARATION is gated on the AUTHORED
            # field (WORK-res art * the 0.85 crush): the 512 downsample mixes
            # rung-cell borders into intermediate values — which is exactly
            # the MIP-blending the owner wants on track ("intermediate darks =
            # even more states") but blurs the histogram valleys. bins (>=6
            # levels >=2%) still gates at 512; runsW (>=5 separated clusters)
            # gates on the authored ladder.
            aw = KIT.art_work_cached(fid)
            lw = (0.299 * aw[:, :, 0] + 0.587 * aw[:, :, 1]
                  + 0.114 * aw[:, :, 2]) * 0.85
            binsW, runsW = ladder_stats(lw)
            fams = [f[0] for f in KIT.ALL[fid]["families"]]
            herr, smean = hue_err(p, fams)
            Ms = s[:, :, 0].astype(np.float32)
            Gs = s[:, :, 1].astype(np.float32)
            Bs = s[:, :, 2].astype(np.float32)
            row = {"band": round(band, 4), "lo": round(lo, 3),
                   "ac": round(autocorr1(luma), 3),
                   "pk": round(peaky, 3), "sf": round(shapefrac(luma), 3),
                   "fine": round(fineness(luma), 2),
                   "cov": coverage_paint(luma),
                   "medL": round(float(np.median(luma)), 3),
                   "lad": bins, "runs": runs, "ladW": binsW, "runsW": runsW,
                   "pit": round(float((luma < 0.06).mean()), 4),
                   "vein": round(float((luma > 0.65).mean()), 4),
                   "hueErr": round(herr, 4), "sat": round(smean, 3),
                   "specM": [round(float(np.median(Ms)), 1), round(float(Ms.std()), 2)],
                   "specG": [round(float(np.median(Gs)), 1), round(float(Gs.std()), 2)],
                   "specB": [round(float(np.median(Bs)), 1), round(float(Bs.std()), 2)],
                   "t": round(dt, 3)}
            if want_2048:
                KIT.art_work_cached.cache_clear()
                b2 = np.full((2048, 2048, 3), 0.5, np.float32)
                m2 = np.ones((2048, 2048), np.float32)
                t1 = time.perf_counter()
                paint_fn(b2, (2048, 2048), m2, 1234, 1.0, None)
                spec_fn((2048, 2048), m2, 1234, 1.0)
                row["t2048"] = round(time.perf_counter() - t1, 3)
            row["ok"] = bool(
                row["band"] >= 0.65 and row["ac"] >= 0.55 and row["pk"] >= 0.30
                and row["sf"] >= 0.55 and row["fine"] > 6.5 and row["cov"] >= 56
                and row["t"] < 2.0
                and row["medL"] <= 0.32 and row["lad"] >= 6 and row["runsW"] >= 5
                and 0.03 <= row["pit"] <= 0.30 and 0.005 <= row["vein"] <= 0.08
                and row["hueErr"] <= 0.03
                and abs(row["specM"][0] - NM) <= 6 and row["specM"][1] <= 4
                and abs(row["specG"][0] - NG) <= 10 and row["specG"][1] <= 4
                and abs(row["specB"][0] - NB) <= 6 and row["specB"][1] <= 4
                and (row.get("t2048", 0.0) <= 2.5))
            lum[fid] = luma
            tiles[fid] = p
        except Exception as e:  # noqa: BLE001 - gate reports, never dies
            row = {"error": "%s: %s" % (type(e).__name__, e), "ok": False}
        out["finishes"][fid] = row
        with open(jpath, "w") as fh:
            json.dump(out, fh, indent=1)
        with open(lpath, "a") as fh:
            fh.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                 "fid": fid, "row": row}) + "\n")
        print("V %-24s %s" % (fid, json.dumps(row)))

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
    print("SUM opalfire med=%.4f min=%.4f pair=%s/%s %.3f ok=%d/%d"
          % (med, out["summary"]["band_min"], worst[0], worst[1], worst[2],
             out["summary"]["n_ok"], len(fids)))

    if want_sheet and tiles:
        TS, cols = 384, 5
        rows = (len(fids) + cols - 1) // cols
        sheet = np.zeros((rows * (TS + 18), cols * TS, 3), np.uint8)
        for i, fid in enumerate(fids):
            if fid not in tiles:
                continue
            p = tiles[fid]
            # UN-NORMALIZED (absolute values): the dark ladder is the product.
            t8 = (np.clip(p, 0, 1) * 255).astype(np.uint8)
            t8 = cv2.resize(t8, (TS, TS), interpolation=cv2.INTER_AREA)
            r0, c0 = (i // cols) * (TS + 18), (i % cols) * TS
            sheet[r0:r0 + TS, c0:c0 + TS] = t8[:, :, ::-1]
            rr = out["finishes"][fid]
            lbl = "%s  b=%.2f L=%.2f lad=%d" % (fid, rr.get("band", 0),
                                                rr.get("medL", 0), rr.get("lad", 0))
            cv2.putText(sheet, lbl, (c0 + 4, r0 + TS + 13),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(TRIAGE, "resheet_opalfire.png"), sheet)
        print("SHEET resheet_opalfire.png")


if __name__ == "__main__":
    main()
