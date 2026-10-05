# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090d] satboost x gray -> measured satA calibration.

art_work builds saturation as  s = clip(s_lut * satboost + 0.08, 0, 1)  and
then the `gray` dial mixes toward each pixel's OWN luma. Both are
luma-preserving, so this sweep costs nothing in band/fineness — it only tells
me which dial pair lands a given id on a target mean saturation. Storm and ice
are GREY-WHITE subjects: satA ~0.30-0.42 for the tinted ids, <=0.20 for the
white/silver ids. One engine boot, one table.

  python satsweep.py <mod> <fid>[,<fid>...]
"""
import importlib
import sys

import cv2
import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + r"\_fractured_triage")
RES = 512
from verify_guard import carband, autocorr1, fineness, hue_bins  # noqa: E402


def main():
    mod, fids = sys.argv[1], sys.argv[2].split(",")
    M = importlib.import_module("engine.expansions.fractured_%s_2026" % mod)
    K = M.KIT
    base = np.full((RES, RES, 3), 0.5, np.float32)
    mask = np.ones((RES, RES), np.float32)
    for fid in fids:
        d = K.ALL[fid]
        sb0, kw0 = d.get("satboost", 1.35), dict(d.get("kw", {}))
        for sb in (1.0, 0.55, 0.40, 0.28, 0.18, 0.10):
            for gy in (0.0, 0.35, 0.60):
                d["satboost"] = sb
                d["kw"] = dict(kw0, gray=gy)
                K.art_work_cached.cache_clear()
                K.macro_cached.cache_clear()
                _s, pf = K.mk(fid)
                p = pf(base, (RES, RES), mask, 1234, 1.0, None)
                hsv = cv2.cvtColor((np.clip(p, 0, 1) * 255).astype(np.uint8),
                                   cv2.COLOR_RGB2HSV)
                satA = float(hsv[:, :, 1].mean() / 255.0)
                L = 0.299 * p[:, :, 0] + 0.587 * p[:, :, 1] + 0.114 * p[:, :, 2]
                b, pk, _lo = carband(L)
                print("S %-24s sb=%.2f gy=%.2f satA=%.3f bins=%2d band=%.4f "
                      "ac=%.3f fine=%.2f"
                      % (fid, sb, gy, satA, hue_bins(p), b, autocorr1(L),
                         fineness(L)))
        d["satboost"], d["kw"] = sb0, kw0


if __name__ == "__main__":
    main()
