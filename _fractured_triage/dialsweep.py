# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090d] sparkle / ambient sweep for the ids whose lag-1
autocorrelation was being held up by CHANNEL CLIPPING.

Measured (satsweep.py): fte_violet_twister reads ac 0.581 at satboost 1.00 and
ac 0.465 at satboost <= 0.40 — with the FIELD BYTE-IDENTICAL. The old number
was an artefact: after art_work's luma renormalisation a fully-saturated pixel
has channels far above 1.0, and the final np.clip flattens exactly the bright
micro-detail that lag-1 coherence is measuring. Honest colour removes the
clip, so the field's TRUE coherence shows. `sparkle` is a 2-px fbm noise term
added on top of the art (it costs coherence AND costs band); backing it off
recovers the guard without touching a lattice, a cell pitch or a LUT dial.

  python dialsweep.py <mod> <fid>[,<fid>...]
"""
import importlib
import sys

import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + r"\_fractured_triage")
RES = 512
from verify_guard import (autocorr1, carband, coverage, fineness,  # noqa: E402
                          hue_bins, shapefrac)


def main():
    mod, fids = sys.argv[1], sys.argv[2].split(",")
    M = importlib.import_module("engine.expansions.fractured_%s_2026" % mod)
    K = M.KIT
    base = np.full((RES, RES, 3), 0.5, np.float32)
    mask = np.ones((RES, RES), np.float32)
    for fid in fids:
        d = K.ALL[fid]
        kw0 = dict(d.get("kw", {}))
        for sp in (0.05, 0.02, 0.0):
            for am in (0.05, 0.14, 0.24, 0.36):
                d["kw"] = dict(kw0, sparkle=sp, ambient=am)
                K.art_work_cached.cache_clear()
                K.macro_cached.cache_clear()
                sf_fn, pf = K.mk(fid)
                p = pf(base, (RES, RES), mask, 1234, 1.0, None)
                sm = sf_fn((RES, RES), mask, 1234, 1.0)
                L = 0.299 * p[:, :, 0] + 0.587 * p[:, :, 1] + 0.114 * p[:, :, 2]
                b, pk, _lo = carband(L)
                print("D %-24s sp=%.2f am=%.2f band=%.4f ac=%.3f pk=%.3f "
                      "sf=%.3f fine=%.1f cov=%d bins=%d"
                      % (fid, sp, am, b, autocorr1(L), pk, shapefrac(L),
                         fineness(L), coverage(sm), hue_bins(p)))
        d["kw"] = kw0


if __name__ == "__main__":
    main()
