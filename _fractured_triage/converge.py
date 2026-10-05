# -*- coding: utf-8 -*-
"""[SPB-FRACTURED-090d 2026-08-02] Drive the colour loop to convergence inside
ONE engine boot (token/time mandate: one process per round-set, not one per
round). measure -> fold -> reload -> measure ...

  python converge.py <mod> [rounds]
"""
import importlib
import json
import os
import runpy
import sys

import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
TRIAGE = os.path.join(ROOT, "_fractured_triage")
sys.path.insert(0, ROOT)
sys.path.insert(0, TRIAGE)

from colorfix import TARGET, circ_d, hue_stats  # noqa: E402

RES = 512


def measure(K, verbose=False):
    base = np.full((RES, RES, 3), 0.5, np.float32)
    mask = np.ones((RES, RES), np.float32)
    out = {}
    for fid in sorted(K.ALL):
        K.art_work_cached.cache_clear()
        K.macro_cached.cache_clear()
        _s, pf = K.mk(fid)
        p = pf(base, (RES, RES), mask, 1234, 1.0, None)
        tgt, satcap = TARGET[fid]
        hue, dom, sat, satA, bins, off, spine = hue_stats(p, tgt)
        d, sd = circ_d(hue, tgt), circ_d(spine, tgt)
        out[fid] = dict(hue=round(hue, 4), dom=round(dom, 4), sat=round(sat, 3),
                        satA=round(satA, 3), bins=bins, off=round(off, 3),
                        spine=round(spine, 4), sfix=round(sd, 4),
                        acc=round(circ_d(hue, spine), 4), target=tgt,
                        satcap=satcap, fix=round(d, 4),
                        ok=bool(abs(d) <= 0.03 and abs(sd) <= 0.03
                                and bins >= 5
                                and (satcap is None or satA <= satcap)))
        if verbose:
            print("C %-26s hue=%.3f spine=%.3f satA=%.3f bins=%2d off=%.3f "
                  "tgt=%.3f fix=%+0.4f sfix=%+0.4f %s"
                  % (fid, hue, spine, satA, bins, off, tgt, d, sd,
                     "" if out[fid]["ok"] else "<<"))
    return out


def main():
    mod = sys.argv[1]
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    name = "engine.expansions.fractured_%s_2026" % mod
    M = importlib.import_module(name)
    for r in range(rounds):
        last = r == rounds - 1
        out = measure(M.KIT, verbose=last)
        json.dump(out, open(os.path.join(TRIAGE, "color_%s.json" % mod), "w"),
                  indent=1)
        wh = max(abs(v["fix"]) for v in out.values())
        ws = max(abs(v["sfix"]) for v in out.values())
        nb = sum(1 for v in out.values() if not v["ok"])
        print("R%d %s bad=%d/%d worst_hue=%.4f worst_spine=%.4f worst_off=%.3f "
              "minbins=%d" % (r, mod, nb, len(out), wh, ws,
                              max(v["off"] for v in out.values()),
                              min(v["bins"] for v in out.values())))
        if last or (wh <= 0.028 and ws <= 0.028):
            break
        sys.argv = ["apply_colorfix.py", mod]
        runpy.run_path(os.path.join(TRIAGE, "apply_colorfix.py"),
                       run_name="__main__")
        M = importlib.reload(M)
    print("DONE %s" % mod)


if __name__ == "__main__":
    main()
