# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090 2026-08-02] Car-band gate + ANTI-CHEAT guards.

Superset of verify_fields.py. Adds the three guards that make a high car-band
score mean "dense coherent micro-structure" instead of "static noise" (white
noise measures band ~0.95 and is a FAILURE):

  autocorr  lag-1 horizontal autocorrelation of the 512 luma      >= 0.55
  peaky     radial in-band profile, 4-px bins; top-20% bins share  >= 0.30
  shapefrac Otsu components (both polarities) of area >= 12 px     >= 0.55

plus the standing gates: band >= 0.70 per finish (module median >= 0.82),
fineness > 6.5, coverage >= 56/64, hue bins >= 5, cold render < 2.0 s @512,
intra-module descriptor pair-cosine <= 0.55.

Usage:  python verify_guard.py <frost|nebula|tempest> [--sheet] [--ids=a,b]
Writes guard_<mod>.json incrementally (token mandate: incremental output).
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
    inb = (r >= 64) & (r <= 256)
    band = P[inb].sum()
    # spectral peakiness: 4-px radial bins inside the band, top-20% share
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


# ── CRUSH-LAW GATES [SPB-FRACTURED-CRUSH 2026-08-03] ────────────────────────
# Opt-in per module: the module exposes CRUSH_GATES=True, SPEC_REF=(M,G,B)
# medians of the night-carrier reference (fs_core_crimson = 242/30/246), and
# RAINBOW_IDS (ids gated on >=8 evenly-spread hue bins instead of a family
# hue). Crush modules run DARK-LADDER paint gates + NEAR-UNIFORM spec gates
# (spec-mirrors-paint exemption documented in the module header), and
# coverage moves to the PAINT luma (a deliberately uniform spec has no
# 8x8 block signal by design). Band floor is 0.65 (median target 0.80).


def crush_ladder(luma):
    """-> (median luma, terraced level count, pit fraction, vein fraction).
    Levels: 64-bin histogram, bins in [0,0.55] holding >=2% mass that are
    PEAKS of the lightly-smoothed histogram with >=1.35x prominence over the
    local (+-3 bin) valley floor. A smooth ramp or flat continuum has no
    prominent local maxima (counts 0) — terraced, not ramped. [2026-08-03b:
    replaces the narrow-run counter, which zeroed any histogram whose AA
    baseline cleared 2% even when 8 authored terraces stood proud of it.]"""
    med = float(np.median(luma))
    hist, _ = np.histogram(np.clip(luma, 0.0, 1.0), bins=64, range=(0.0, 1.0))
    zone = (hist / float(luma.size))[:36]      # bin centers <= 0.5547
    sm = np.convolve(zone, np.float64([0.25, 0.5, 0.25]), mode="same")
    levels = 0
    for b in range(len(zone)):
        if zone[b] < 0.02:
            continue
        left = sm[b - 1] if b > 0 else 0.0
        right = sm[b + 1] if b < len(zone) - 1 else 0.0
        if not (sm[b] >= left and sm[b] > right):
            continue
        vlo = float(sm[max(0, b - 3):b + 4].min())
        if sm[b] >= 1.35 * max(vlo, 0.004):
            levels += 1
    pit = float((luma < 0.06).mean())
    vein = float((luma > 0.65).mean())
    return med, levels, pit, vein


def spec_stats(spec):
    """Per-channel (median, std) of the M/G/B spec planes (uint8 in, float out)."""
    meds = [float(np.median(spec[:, :, c])) for c in range(3)]
    stds = [float(spec[:, :, c].astype(np.float32).std()) for c in range(3)]
    return meds, stds


def coverage_luma(luma):
    """Paint-luma 8x8 coverage (crush modules: spec is uniform by design)."""
    n = 0
    bs = luma.shape[0] // 8
    for by in range(8):
        for bx in range(8):
            b = luma[by * bs:(by + 1) * bs, bx * bs:(bx + 1) * bs]
            if float(b.std()) > 4.0 / 255.0:
                n += 1
    return n


def hue_spread(paint):
    """(occupied 36-bin count, largest angular gap in bins) for rainbow ids."""
    u8 = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    hsv = cv2.cvtColor(u8, cv2.COLOR_RGB2HSV)
    m = hsv[:, :, 1] > 38
    tot = paint.shape[0] * paint.shape[1]
    if not m.any():
        return 0, 36
    hist, _ = np.histogram(hsv[:, :, 0][m], bins=36, range=(0, 180))
    occ = np.where(hist > 0.005 * tot)[0]
    if len(occ) == 0:
        return 0, 36
    gaps = np.diff(np.concatenate([occ, [occ[0] + 36]]))
    return int(len(occ)), int(gaps.max())


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
    crush = bool(getattr(M, "CRUSH_GATES", False))
    spec_ref = getattr(M, "SPEC_REF", None)
    rainbow = set(getattr(M, "RAINBOW_IDS", ()))
    fids = sorted(KIT.ALL.keys())
    if only:
        fids = [f for f in fids if f in only]
    jpath = os.path.join(TRIAGE, "guard_%s.json" % mod)
    out = {"module": mod, "finishes": {}}
    lum = {}
    tiles = {}
    for fid in fids:
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
            band, peaky, lo = carband(luma)
            row = {"band": round(band, 4), "lo": round(lo, 3),
                   "ac": round(autocorr1(luma), 3),
                   "pk": round(peaky, 3), "sf": round(shapefrac(luma), 3),
                   "rms": round(float(luma.std() / max(luma.mean(), 1e-6)), 3),
                   "fine": round(fineness(luma), 2), "cov": coverage(s),
                   "hue": hue_bins(p), "t": round(dt, 3)}
            if crush:
                # [SPB-FRACTURED-CRUSH 2026-08-03] dark-ladder + uniform-spec
                medL, lvl, pit, vein = crush_ladder(luma)
                smed, sstd = spec_stats(s)
                covp = coverage_luma(luma)
                hb, hgap = hue_spread(p)
                row.update({"medL": round(medL, 3), "lvl": lvl,
                            "pit": round(pit, 3), "vein": round(vein, 4),
                            "covp": covp,
                            "smed": [round(x, 1) for x in smed],
                            "sstd": [round(x, 2) for x in sstd]})
                sok = spec_ref is None or (
                    abs(smed[0] - spec_ref[0]) <= 6.0
                    and abs(smed[1] - spec_ref[1]) <= 10.0
                    and abs(smed[2] - spec_ref[2]) <= 6.0
                    and max(sstd) <= 4.0)
                if fid in rainbow:
                    hok = hb >= 8 and hgap <= 12      # >=8 bins, no missing third
                    row["hgap"] = hgap
                else:
                    hok = row["hue"] >= 5
                row["ok"] = bool(row["band"] >= 0.65 and row["ac"] >= 0.55
                                 and row["pk"] >= 0.30 and row["sf"] >= 0.55
                                 and row["fine"] > 6.5 and covp >= 56
                                 and hok and row["t"] < 2.0
                                 and medL <= 0.32 and lvl >= 6
                                 and 0.03 <= pit <= 0.30
                                 and 0.005 <= vein <= 0.08 and sok)
            else:
                row["ok"] = bool(row["band"] >= 0.70 and row["ac"] >= 0.55
                                 and row["pk"] >= 0.30 and row["sf"] >= 0.55
                                 and row["fine"] > 6.5 and row["cov"] >= 56
                                 and row["hue"] >= 5 and row["t"] < 2.0)
            lum[fid] = luma
            tiles[fid] = p
        except Exception as e:  # noqa: BLE001 - gate reports, never dies
            row = {"error": "%s: %s" % (type(e).__name__, e), "ok": False}
        out["finishes"][fid] = row
        with open(jpath, "w") as fh:
            json.dump(out, fh, indent=1)
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

    def mn(key):
        v = [r[key] for r in out["finishes"].values() if key in r]
        return round(min(v), 3) if v else 0.0

    out["summary"] = {"band_median": round(med, 4),
                      "band_min": round(min(bands), 4) if bands else 0,
                      "ac_min": mn("ac"), "pk_min": mn("pk"), "sf_min": mn("sf"),
                      "fine_min": mn("fine"), "t_max": round(max(
                          [r["t"] for r in out["finishes"].values() if "t" in r] or [0]), 3),
                      "worst_pair": [worst[0], worst[1], round(worst[2], 4)],
                      "n_ok": sum(1 for r in out["finishes"].values() if r.get("ok")),
                      "n": len(fids)}
    with open(jpath, "w") as fh:
        json.dump(out, fh, indent=1)
    print("SUM %s med=%.4f min=%.4f ac>=%.3f pk>=%.3f sf>=%.3f fine>=%.2f "
          "tmax=%.2f pair=%s/%s %.3f ok=%d/%d"
          % (mod, med, out["summary"]["band_min"], out["summary"]["ac_min"],
             out["summary"]["pk_min"], out["summary"]["sf_min"],
             out["summary"]["fine_min"], out["summary"]["t_max"],
             worst[0], worst[1], worst[2],
             out["summary"]["n_ok"], len(fids)))

    if want_sheet and tiles:
        TS, cols = 384, 5
        rows = (len(fids) + cols - 1) // cols
        sheet = np.zeros((rows * (TS + 18), cols * TS, 3), np.uint8)
        for i, fid in enumerate(fids):
            if fid not in tiles:
                continue
            p = tiles[fid]
            if crush:
                # UN-NORMALIZED (absolute value): per-tile p/p.max() hides the
                # dark ladder — the whole point of a crush module.
                t8 = (np.clip(p, 0, 1) * 255).astype(np.uint8)
            else:
                t8 = (np.clip(p / max(float(p.max()), 1e-6), 0, 1) * 255).astype(np.uint8)
            t8 = cv2.resize(t8, (TS, TS), interpolation=cv2.INTER_AREA)
            r0, c0 = (i // cols) * (TS + 18), (i % cols) * TS
            sheet[r0:r0 + TS, c0:c0 + TS] = t8[:, :, ::-1]
            lbl = "%s  b=%.2f" % (fid, out["finishes"][fid].get("band", 0))
            cv2.putText(sheet, lbl, (c0 + 4, r0 + TS + 13),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(os.path.join(TRIAGE, "resheet_%s.png" % mod), sheet)
        print("SHEET resheet_%s.png" % mod)


if __name__ == "__main__":
    main()
