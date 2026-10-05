# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090b 2026-08-02] Per-finish (span, lowcut) sweep.

Verification OUTSIDE the model loop (token mandate): one process, one verdict
line per finish, the winning knob pair written to tune_<mod>.json so the
recipe table can be updated in one edit.

Objective: maximise car-band subject to the anti-static guards
(ac >= 0.55, pk >= 0.30, sf >= 0.55, fine > 6.5); ties broken on ac.

  python tune_field.py <mod> [--ids=a,b] [--grid=span:lowcut,...]
"""
import importlib
import json
import os
import sys

import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
TRIAGE = os.path.join(ROOT, "_fractured_triage")
sys.path.insert(0, ROOT)
sys.path.insert(0, TRIAGE)
from verify_guard import autocorr1, carband, fineness, hue_bins, shapefrac  # noqa: E402

RES = 512
# (span, lowcut, val). val is the third knob: compressing the LUT walk also
# compresses luma contrast, so a low-span finish buys its fineness back by
# riding a brighter crush point instead of a wider (and lower-frequency) walk.
GRID = [(1.0, 0.0, 0.0, 0.0), (0.70, 0.0, 0.0, 0.0), (0.50, 0.0, 0.0, 0.0),
        (0.36, 0.0, 0.0, 0.0), (0.26, 0.0, 0.0, 0.0),
        (0.70, 1.6, 0.0, 0.0), (0.50, 1.6, 0.0, 0.0), (0.36, 1.6, 0.0, 0.0),
        (0.26, 1.6, 0.0, 0.0),
        (0.70, 1.0, 0.34, 0.0), (0.50, 1.0, 0.34, 0.0), (0.36, 1.0, 0.34, 0.0),
        (0.70, 0.0, 0.0, 0.55), (0.50, 0.0, 0.0, 0.55),
        (0.36, 0.0, 0.34, 0.55), (0.26, 0.0, 0.34, 0.55),
        (0.70, 1.0, 0.34, 0.55), (0.50, 0.0, 0.34, 0.85),
        (1.00, 0.0, 0.34, 0.85), (0.70, 0.0, 0.34, 0.85)]
AC, PK, SF, FI, HU = 0.555, 0.32, 0.56, 6.6, 5


def main():
    mod = sys.argv[1]
    only = None
    for a in sys.argv[2:]:
        if a.startswith("--ids"):
            only = a.split("=", 1)[1].split(",")
        if a.startswith("--grid"):
            GRID[:] = [tuple(float(x) for x in g.split(":"))
                       for g in a.split("=", 1)[1].split(",")]
    M = importlib.import_module("engine.expansions.fractured_%s_2026" % mod)
    K = M.KIT
    fids = [f for f in sorted(K.ALL) if not only or f in only]
    jp = os.path.join(TRIAGE, "tune_%s.json" % mod)
    out = json.load(open(jp)) if os.path.exists(jp) else {}
    base = np.zeros((RES, RES, 3), np.float32)
    mask = np.ones((RES, RES), np.float32)
    for fid in fids:
        d = K.ALL[fid]
        keep = dict(d.get("eargs", {}))
        best = None
        v0 = float(d.get("val", 0.24))
        for span, lc, vv, sof in GRID:
            d["eargs"] = dict(keep, span=span, lowcut=lc, soft=sof,
                              mid=M._lut_steep(d["lut"], span))
            d["val"] = vv if vv > 0 else v0
            K.art_work_cached.cache_clear()
            K.macro_cached.cache_clear()
            try:
                _s, pf = K.mk(fid)
                p = pf(base, (RES, RES), mask, 1234, 1.0, None)
            except Exception as e:  # noqa: BLE001
                print("ERR %s %s" % (fid, e))
                continue
            L = 0.299 * p[:, :, 0] + 0.587 * p[:, :, 1] + 0.114 * p[:, :, 2]
            r = carband(L)
            b, pk = float(r[0]), float(r[1])
            ac, sf, fi = autocorr1(L), shapefrac(L), fineness(L)
            hu = hue_bins(p)
            ok = (ac >= AC and pk >= PK and sf >= SF and fi > FI and hu >= HU)
            key = (1 if ok else 0, round(b, 4))
            if "--dump" in sys.argv:
                print("ROW %-22s sp=%.2f lc=%.1f v=%.2f b=%.3f ac=%.3f "
                      "pk=%.3f sf=%.3f fi=%.1f hu=%d so=%.2f" %
                      (fid, span, lc, float(d["val"]), b, ac, pk, sf, fi, hu,
                       sof))
            if best is None or key > best[0]:
                best = (key, dict(span=span, lowcut=lc, soft=sof,
                                  val=round(float(d["val"]), 3),
                                  band=round(b, 4),
                                  ac=round(ac, 3), pk=round(pk, 3),
                                  sf=round(sf, 3), fine=round(fi, 2),
                                  hue=hu, ok=ok))
        d["eargs"] = keep
        d["val"] = v0
        out[fid] = best[1]
        json.dump(out, open(jp, "w"), indent=1)
        print("BEST %-24s %s" % (fid, json.dumps(best[1])))
    b = [v["band"] for v in out.values()]
    print("TUNED %s median=%.4f min=%.4f nok=%d/%d"
          % (mod, float(np.median(b)), min(b),
             sum(1 for v in out.values() if v["ok"]), len(out)))


if __name__ == "__main__":
    main()
