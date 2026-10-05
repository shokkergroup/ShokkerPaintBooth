# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090b 2026-08-02] Where does the sub-band power sit?

Ablation probe for bloom/petri/relic: measures car-band + guards for a few
ids under kit-level variants (ambient/sparkle, vd/tmod, engine low-cut) so the
rebuild spends effort on the term that actually leaks.

Usage: python ablate_field.py <mod> <id,id,...>
"""
import importlib
import sys

import cv2
import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + r"\_fractured_triage")
from verify_guard import autocorr1, carband, fineness, shapefrac  # noqa: E402

RES = 512


def measure(KIT, fid):
    KIT.art_work_cached.cache_clear()
    KIT.macro_cached.cache_clear()
    _s, paint_fn = KIT.mk(fid)
    p = paint_fn(np.zeros((RES, RES, 3), np.float32), (RES, RES),
                 np.ones((RES, RES), np.float32), 1234, 1.0, None)
    L = 0.299 * p[:, :, 0] + 0.587 * p[:, :, 1] + 0.114 * p[:, :, 2]
    b, pk = carband(L)
    return b, autocorr1(L), pk, shapefrac(L), fineness(L)


def main():
    mod, ids = sys.argv[1], sys.argv[2].split(",")
    M = importlib.import_module("engine.expansions.fractured_%s_2026" % mod)
    KIT = M.KIT
    gauss = M.gauss

    def lowcut_wrap(fn, px):
        def g(res, seed, **kw):
            T = np.asarray(fn(res, seed, **kw), np.float32)
            return np.clip(T - (gauss(T, px * res / 640.0) - float(T.mean())),
                           0.002, 0.998)
        return g

    orig_engines = dict(KIT.engines)
    for fid in ids:
        d = KIT.ALL[fid]
        snap = (dict(d["kw"]), d["vd"], d["tmod"])
        rows = []
        rows.append(("base", measure(KIT, fid)))
        d["kw"]["ambient"] = 0.05
        d["kw"]["sparkle"] = 0.08
        rows.append(("amb+spk", measure(KIT, fid)))
        d["vd"] = (0.96, 1.06)
        d["tmod"] = 0.0
        rows.append(("+vd/tmod", measure(KIT, fid)))
        for px in (6.0, 3.0):
            KIT.engines = dict(orig_engines)
            KIT.engines[d["engine"]] = lowcut_wrap(orig_engines[d["engine"]], px)
            rows.append(("+lowcut%g" % px, measure(KIT, fid)))
        KIT.engines = dict(orig_engines)
        d["kw"], d["vd"], d["tmod"] = snap
        for tag, (b, ac, pk, sf, fi) in rows:
            print("%-22s %-10s band=%.3f ac=%.3f pk=%.3f sf=%.3f fine=%.1f"
                  % (fid, tag, b, ac, pk, sf, fi))


if __name__ == "__main__":
    main()
