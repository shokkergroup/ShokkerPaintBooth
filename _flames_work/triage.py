# -*- coding: utf-8 -*-
"""FRACTURED FLAMES triage — judge the 51 existing structures before rebuilding.

Owner 2026-08-30: "we have 3 FRACTURED FLAMES categories and way too many
finishes. We only need about 75 total flames. And MANY of them are repeats and
redundant or just lazy/not good. Keep some of the better one's but make new math
and styles."

The 135 shipped cards are a CROSS-PRODUCT: 51 structures x {ignite,topo,dance} x
a palette name. `flames_catalog_2026._art_work_cached` calls
FLAME_STRUCTURES[flame]((W,W), 7) with NO palette argument, so all 2-3 cards of a
structure carry byte-identical paint and differ only in the spec recipe. This
harness scores the 51 STRUCTURES (the only real axis) so the rebuild keeps the
ones worth keeping.

Scores, all on the 2048 canvas the car actually gets:
  band   car-band energy in r=32..256 (the 8-32px visible window) / total.
         Doctrine floor 0.45 (memory: field-not-poster).
  cover  fraction of an 8x8 grid carrying signal — full-canvas coverage law.
  fine   high-frequency energy ratio, brightness-normalised (fine/meanL).
  sim    nearest structural neighbour among the other 50 (colour-independent:
         luma, mean-removed, contrast-normalised). >=0.80 = a clone.

usage: python _flames_work/triage.py            (all 51, writes JSONL + sheet)
       python _flames_work/triage.py tongues …  (subset)
"""
import json
import os
import sys
import time

import cv2
import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT)
sys.path.insert(0, ROOT)
OUT = "_flames_work"
os.makedirs(OUT + "/thumbs", exist_ok=True)
PROG = "FRACTURED_FLAMES_PROGRESS.jsonl"

import engine.paint_v2.flame_math as fm                      # noqa: E402

N = 2048
SHAPE = (N, N)


def band_score(L):
    """Energy in the car-visible 8-32px window (r 32..256 of a 2048 canvas)."""
    F = np.fft.fftshift(np.abs(np.fft.fft2(L - L.mean())) ** 2)
    yy, xx = np.mgrid[0:L.shape[0], 0:L.shape[1]] - L.shape[0] // 2
    r = np.hypot(xx, yy)
    return float(F[(r >= 32) & (r <= 256)].sum() / max(F[r >= 2].sum(), 1e-9))


def coverage(L, grid=8, thr=0.02):
    h = L.shape[0] // grid
    hit = 0
    for i in range(grid):
        for j in range(grid):
            t = L[i * h:(i + 1) * h, j * h:(j + 1) * h]
            if t.std() > thr:
                hit += 1
    return hit / float(grid * grid)


def fineness(L):
    """HF ratio, normalised by mean level so a BRIGHT field can't fake detail."""
    blur = cv2.GaussianBlur(L, (0, 0), 2.0)
    return float(np.abs(L - blur).mean() / max(L.mean(), 1e-6))


def signature(L, k=64):
    """Colour-independent structural signature for the clone check."""
    s = cv2.resize(L, (k, k), interpolation=cv2.INTER_AREA).astype(np.float32)
    s -= s.mean()
    n = np.linalg.norm(s)
    return s / n if n > 1e-9 else s


def main(argv):
    only = set(argv[1:])
    names = [n for n in sorted(fm.FLAME_STRUCTURES) if not only or n in only]
    rows, sigs, thumbs = [], {}, {}

    for i, name in enumerate(names):
        t0 = time.time()
        try:
            art = np.asarray(fm.FLAME_STRUCTURES[name](SHAPE, 7), np.float32)
        except Exception as exc:                             # noqa: BLE001
            print("%-24s RENDER FAILED  %s" % (name, exc))
            continue
        dt = time.time() - t0
        if art.max() > 1.5:
            art = art / 255.0
        L = (0.2126 * art[..., 0] + 0.7152 * art[..., 1] + 0.0722 * art[..., 2]).astype(np.float32)
        row = {
            "structure": name, "band": round(band_score(L), 3),
            "cover": round(coverage(L), 3), "fine": round(fineness(L), 4),
            "meanL": round(float(L.mean()), 3), "stdL": round(float(L.std()), 3),
            "sec": round(dt, 2),
        }
        sigs[name] = signature(L)
        rows.append(row)
        # 1:1 car crop beside the whole canvas — the swatch always lies
        full = cv2.resize(art, (256, 256), interpolation=cv2.INTER_AREA)
        crop = art[N // 2 - 128:N // 2 + 128, N // 2 - 128:N // 2 + 128]
        tile = np.concatenate([full, crop], axis=1)
        thumbs[name] = np.clip(tile * 255, 0, 255).astype(np.uint8)[:, :, ::-1]
        cv2.imwrite("%s/thumbs/%s.png" % (OUT, name), thumbs[name])
        with open(PROG, "a", encoding="utf-8") as fh:        # incremental, append-only
            fh.write(json.dumps({"phase": "triage", **row}) + "\n")
        print("  %2d/%d %-24s band %.3f cover %.2f fine %.4f  %.1fs"
              % (i + 1, len(names), name, row["band"], row["cover"], row["fine"], dt))

    # nearest structural neighbour (the clone detector)
    keys = list(sigs)
    for a in keys:
        best, who = -1.0, ""
        for b in keys:
            if a == b:
                continue
            c = float((sigs[a] * sigs[b]).sum())
            if c > best:
                best, who = c, b
        for r in rows:
            if r["structure"] == a:
                r["sim"] = round(best, 3)
                r["twin"] = who

    rows.sort(key=lambda r: (r["band"], r["cover"]))
    print("\n%-24s %6s %6s %7s %6s  %s" % ("STRUCTURE", "band", "cover", "fine", "sim", "nearest twin"))
    for r in rows:
        flag = ""
        if r["band"] < 0.45:
            flag += " POSTER"
        if r["cover"] < 0.90:
            flag += " GAPS"
        if r.get("sim", 0) >= 0.80:
            flag += " CLONE"
        print("%-24s %6.3f %6.2f %7.4f %6.3f  %-22s%s"
              % (r["structure"], r["band"], r["cover"], r["fine"], r.get("sim", 0), r.get("twin", ""), flag))

    keep = [r for r in rows if r["band"] >= 0.45 and r["cover"] >= 0.90 and r.get("sim", 0) < 0.80]
    print("\npasses doctrine as-is: %d / %d" % (len(keep), len(rows)))

    # contact sheet, 6 wide
    cols, cell = 6, 512
    order = [r["structure"] for r in rows]
    sheetrows = []
    for i in range(0, len(order), cols):
        band = [thumbs[n] for n in order[i:i + cols]]
        while len(band) < cols:
            band.append(np.zeros_like(band[0]))
        sheetrows.append(np.concatenate(band, axis=1))
    if sheetrows:
        sheet = np.concatenate(sheetrows, axis=0)
        cv2.imwrite(OUT + "/triage_contact_sheet.png", sheet)
        print("contact sheet -> %s/triage_contact_sheet.png  (%dx%d)"
              % (OUT, sheet.shape[1], sheet.shape[0]))
    json.dump(rows, open(OUT + "/triage.json", "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
