# -*- coding: utf-8 -*-
"""FRACTURED RELICS verification harness — runs OUTSIDE the authoring loop.
One verdict line per finish; appends to FRACTURED_RELICS_PROGRESS.jsonl; saves
paint+spec thumbs and a contact sheet for the mandatory eyeball pass.

Renders the REAL registry pair at 2048 (cold, caches cleared) so the timing is
the gate's timing, then measures on a 512 downsample (the car-band law's own
resolution).

usage:  python _relics_work/verify.py [fid ...]      env: RLC_ITER=<n>
"""
import importlib, json, os, sys, time
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT)
sys.path.insert(0, ROOT)
OUT = "_relics_work"
os.makedirs(OUT + "/thumbs", exist_ok=True)
PROG = "FRACTURED_RELICS_PROGRESS.jsonl"

import engine.expansions.fractured_relics_kit_2026 as rkit
import engine.expansions.fractured_relics_2026 as m
importlib.reload(rkit)
importlib.reload(m)

SHAPE = (2048, 2048)
MASK = np.ones(SHAPE, np.float32)
BASE = np.full(SHAPE + (3,), 0.5, np.float32)


def band_score(L):
    """Car-band energy: FFT ring r in [64,256] over total r>=2 (512 luma)."""
    F = np.fft.fftshift(np.abs(np.fft.fft2(L - L.mean())) ** 2)
    n = L.shape[0]
    yy, xx = np.mgrid[0:n, 0:n] - n // 2
    r = np.hypot(xx, yy)
    tot = F[r >= 2].sum()
    return float(F[(r >= 64) & (r <= 256)].sum() / max(tot, 1e-9))


def descriptor(L):
    """Compact shape descriptor for inter-finish similarity (cosine)."""
    F = np.fft.fftshift(np.abs(np.fft.fft2(L - L.mean())))
    n = L.shape[0]
    yy, xx = np.mgrid[0:n, 0:n] - n // 2
    r = np.hypot(xx, yy)
    th = (np.arctan2(yy, xx) % np.pi)
    d = []
    for lo, hi in ((8, 32), (32, 64), (64, 110), (110, 170), (170, 256)):
        ring = (r >= lo) & (r < hi)
        for k in range(6):
            sec = ring & (th >= k * np.pi / 6) & (th < (k + 1) * np.pi / 6)
            d.append(float(F[sec].mean()) if sec.any() else 0.0)
    h = np.histogram(L, bins=12, range=(0, 255))[0].astype(np.float64)
    d = np.log1p(np.asarray(d, np.float64))
    d = (d - d.mean()) / (d.std() + 1e-9)          # centred: shared 1/f decay out
    h = h / max(h.sum(), 1e-9)
    h = (h - h.mean()) / (h.std() + 1e-9)
    return np.concatenate([d, h * 0.5])


def hue_bins(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    sat = hsv[..., 1].astype(np.float32) / 255.0
    hue = hsv[..., 0].astype(np.float32) / 179.0
    good = hue[(sat > 0.18)]
    if good.size < 100:
        return 0, -1.0
    hist = np.histogram(good, bins=12, range=(0, 1))[0]
    # dominant hue (circular mean of the chromatic pixels) — the colour the car
    # reads at ten feet. Shelf diversity is measured on THIS, not on bin count.
    ang = good * 2 * np.pi
    dom = float((np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) / (2 * np.pi)) % 1.0)
    return int((hist > good.size * 0.02).sum()), dom


only = set(a for a in sys.argv[1:])
it = int(os.environ.get("RLC_ITER", "1"))
rows, descs, doms = [], {}, {}
for gname, grp in m.GROUPS.items():
    for fid in grp:
        if only and fid not in only:
            continue
        m.KIT.art_work_cached.cache_clear()
        m.KIT.macro_cached.cache_clear()
        m.KIT.struct_cached.cache_clear()
        spec_fn, paint_fn = m.KIT.mk(fid)
        t0 = time.time()
        p = paint_fn(BASE.copy(), SHAPE, MASK, 51, 1.0, None)
        s = spec_fn(SHAPE, MASK, 51, 1.0)
        dt = time.time() - t0

        p8 = np.clip(np.asarray(p, np.float32) * 255.0, 0, 255).astype(np.uint8)
        s8 = np.asarray(s)[..., :3]
        small = cv2.resize(p8, (512, 512), interpolation=cv2.INTER_AREA)
        L = (0.299 * small[..., 0] + 0.587 * small[..., 1] + 0.114 * small[..., 2]).astype(np.float32)
        band = band_score(L)
        live = sum(1 for ty in range(8) for tx in range(8)
                   if small[ty * 64:(ty + 1) * 64, tx * 64:(tx + 1) * 64].std() > 6.0)
        Lf = (0.299 * p8[..., 0] + 0.587 * p8[..., 1] + 0.114 * p8[..., 2]).astype(np.float32)
        fine = float(np.abs(Lf - cv2.GaussianBlur(Lf, (0, 0), 6)).mean())
        hb, dom = hue_bins(small)
        sm_ = cv2.resize(s8, (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32)
        stds = [float(sm_[..., i].std()) for i in range(3)]
        # SPEC-FOLLOWS-PATTERN, measured honestly: does the spec carry its detail
        # WHERE the paint carries its detail? A plain Pearson of spec vs paint luma
        # is the wrong test — the thin-film LUT maps structure to luma
        # non-monotonically, so a spec that tracks the geometry perfectly can read
        # as uncorrelated. Gradient-magnitude agreement is immune to that.
        def _grad(a):
            gx = cv2.Sobel(cv2.GaussianBlur(a, (0, 0), 1.1), cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(cv2.GaussianBlur(a, (0, 0), 1.1), cv2.CV_32F, 0, 1, ksize=3)
            g = np.hypot(gx, gy)
            return (g - g.mean()) / (g.std() + 1e-6)
        # ...and measure it against the PATTERN GEOMETRY, not the paint luma. The
        # thin-film LUT is an oscillator, so a smooth ramp in the structure becomes
        # several luma bands: the paint's edge map is full of colour-band edges the
        # geometry never had. "The spec follows the pattern design" means the spec
        # tracks the FINISH'S OWN GENERATOR, which is what this measures.
        Sfield = cv2.resize(m.KIT.struct_cached(fid, 448), (512, 512),
                            interpolation=cv2.INTER_AREA).astype(np.float32)
        gS = _grad(Sfield)
        corr = max(abs(float((_grad(sm_[..., i]) * gS).mean())) for i in range(3))
        gL = _grad(L)
        corrL = max(abs(float((_grad(sm_[..., i]) * gL).mean())) for i in range(3))
        descs[fid] = descriptor(L)
        doms[fid] = dom

        v = []
        if dt > 3.0: v.append(f"BUDGET {dt:.2f}s")
        if band < 0.50: v.append(f"BAND {band:.2f}")
        if live < 56: v.append(f"COVERAGE {live}/64")
        # RELATIVE micro-contrast, not absolute fineness: paint_fn rescales the
        # art by `val`, so raw fineness only measures brightness. The approved
        # family (calibrate.py) sits at fine/meanL 0.16-0.28.
        rel = fine / max(float(Lf.mean()), 1.0)
        if rel < 0.185: v.append(f"FLAT rel={rel:.2f}")
        if fine < 7.0: v.append(f"DIM fine={fine:.1f}")
        if hb < 3: v.append(f"HUES {hb}<3")
        if min(stds) < 20.0: v.append(f"SPECFLAT {min(stds):.0f}")
        if corr < 0.35: v.append(f"SPECDRIFT {corr:.2f}")
        if not (34.0 <= float(Lf.mean()) <= 132.0): v.append(f"TONE meanL={Lf.mean():.0f}")
        ok = not v
        print(f"{'OK  ' if ok else 'FAIL'} {fid:24s} {dt:5.2f}s band={band:.2f} live={live}/64 "
              f"fine={fine:5.1f} hues={hb} dom={dom:.2f} spec={stds[0]:3.0f}/{stds[1]:3.0f}/{stds[2]:3.0f} "
              f"corr={corr:.2f} L={Lf.mean():3.0f} rel={fine / max(float(Lf.mean()), 1.0):.2f}" + ("" if ok else "  << " + "; ".join(v)), flush=True)
        with open(PROG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"iter": it, "phase": "verify", "id": fid,
                                "status": "ok" if ok else "fail",
                                "verify": {"s": round(dt, 2), "band": round(band, 3),
                                           "live": live, "fine": round(fine, 1),
                                           "hues": hb, "dom": round(dom, 3), "spec": [round(x) for x in stds],
                                           "corr": round(corr, 2), "corrL": round(corrL, 2), "rel": round(fine / max(float(Lf.mean()), 1.0), 3)},
                                "note": "; ".join(v), "ts": time.strftime("%H:%M:%S")}) + "\n")
        pt = cv2.resize(p8, (512, 512), interpolation=cv2.INTER_AREA)
        sv = cv2.resize(s8, (512, 512), interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(f"{OUT}/thumbs/{fid}_paint.png", pt[..., ::-1])
        cv2.imwrite(f"{OUT}/thumbs/{fid}_spec.png", sv[..., ::-1])
        # 1:1 crop — the honest on-car pixel scale
        c0 = (2048 - 512) // 2
        cv2.imwrite(f"{OUT}/thumbs/{fid}_crop.png", p8[c0:c0 + 512, c0:c0 + 512][..., ::-1])
        rows.append((fid, pt, sv, p8[c0:c0 + 512, c0:c0 + 512]))

# pair-similarity (design sameness proxy; official gate is the catalog script)
ids = list(descs)
if len(ids) > 2:
    mean = np.mean([descs[k] for k in ids], axis=0)   # compare DEVIATIONS from
    for k in ids:                                     # the category average, or
        descs[k] = descs[k] - mean                    # every dense pave cosines 1.0
if len(ids) > 1:
    worst = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = descs[ids[i]], descs[ids[j]]
            c = float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
            worst.append((c, ids[i], ids[j]))
    worst.sort(reverse=True)
    print("PAIRS  worst:", "  ".join(f"{c:.2f} {a.replace('frl_','')}~{b.replace('frl_','')}"
                                     for c, a, b in worst[:4]), flush=True)
    with open(PROG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"iter": it, "phase": "pairs",
                            "worst": [[round(c, 3), a, b] for c, a, b in worst[:6]],
                            "ts": time.strftime("%H:%M:%S")}) + "\n")

dl = sorted(doms.items(), key=lambda t: t[1])
if len(dl) > 2:
    close = []
    for i in range(len(dl)):
        a, b = dl[i], dl[(i + 1) % len(dl)]
        gap = (b[1] - a[1]) % 1.0
        close.append((gap, a[0], b[0]))
    close.sort()
    print("HUES   shelf spread (nearest dominant-hue pairs):",
          "  ".join(f"{g:.03f} {a.replace('frl_','')}~{b.replace('frl_','')}"
                    for g, a, b in close[:3]), flush=True)

if rows:
    cols = 4
    cell_w, cell_h = 512 * 3 + 16, 512 + 26
    rws = (len(rows) + cols - 1) // cols
    sheet = np.full((rws * cell_h, cols * cell_w, 3), 12, np.uint8)
    for i, (fid, pt, sv, cr) in enumerate(rows):
        cy, cx = divmod(i, cols)
        y0, x0 = cy * cell_h + 24, cx * cell_w
        for k, img in enumerate((pt, cr, sv)):
            sheet[y0:y0 + 512, x0 + k * 520:x0 + k * 520 + 512] = img
        cv2.putText(sheet, fid, (x0 + 6, cy * cell_h + 17), cv2.FONT_HERSHEY_SIMPLEX,
                    .52, (235, 235, 235), 1)
    cv2.imwrite(f"{OUT}/contact_sheet.png", sheet[..., ::-1])
    print(f"contact sheet: {OUT}/contact_sheet.png ({len(rows)} finishes)  [full | 1:1 crop | spec]")
