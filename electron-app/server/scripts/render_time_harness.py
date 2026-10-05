# -*- coding: utf-8 -*-
"""Time ALL new items at REAL render sizes (what the app actually does):
- LFR + FABLE finishes: paint_fn + spec_fn at (2048, 2048), full mask
- LFR spec overlays: PATTERN_CATALOG fn at (2048, 2048)
- LFR patterns: texture_fn + paint_fn at (1024, 1024) work grid
Budget: <= 1.0s optimal, > 3.0s = FAIL (owner doctrine 2026-06-09).
Writes _perf_results.json {id: seconds}."""
import sys, time, json
import numpy as np
sys.path.insert(0, r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum")

results = {}

def clock(label, fn):
    t0 = time.perf_counter()
    fn()
    dt = time.perf_counter() - t0
    results[label] = round(dt, 2)
    status = "FAIL" if dt > 3.0 else ("warn" if dt > 1.0 else "ok")
    print("%6.2fs  %-4s  %s" % (dt, status, label))
    return dt

S = 2048
mask = np.ones((S, S), np.float32)
base = np.full((S, S, 3), 0.5, np.float32)

from engine.registry import MONOLITHIC_REGISTRY
FIN = sorted(f for f in MONOLITHIC_REGISTRY if f.startswith(("lfr_", "fable_")))
try:
    from engine.expansions.colorshift_rework_2026 import REWORK_MONOLITHICS
    for _rid, _rentry in REWORK_MONOLITHICS.items():
        MONOLITHIC_REGISTRY[_rid] = _rentry
    FIN += sorted(REWORK_MONOLITHICS)
except Exception:
    pass
print("== FINISHES (paint+spec @ 2048) ==")
for fid in FIN:
    spec_fn, paint_fn = MONOLITHIC_REGISTRY[fid]
    clock(fid + "/paint", lambda: paint_fn(base.copy(), (S, S), mask, 42, 1.0, {}))
    clock(fid + "/spec", lambda: spec_fn((S, S), mask, 42, 1.0))

print("== SPEC OVERLAYS (@ 2048) ==")
from engine import spec_patterns as sp
for pid in ["spec_lfr_starfield_scatter","spec_lfr_corridor_sheen","spec_lfr_firework_radial",
            "spec_lfr_brocade_relief","spec_lfr_liberty_colorflip","spec_lfr_anisotropic_drift",
            "spec_lfr_sparkler_embers","spec_lfr_torch_flicker","spec_lfr_capitol_veins",
            "spec_lfr_canyon_bevel"]:
    fn = sp.PATTERN_CATALOG[pid]
    clock(pid, lambda: fn((S, S), 42, 1.0))

print("== PATTERNS (tex+paint @ 1024 work grid) ==")
from engine.pattern_expansion import NEW_PATTERNS
P = 1024
pmask = np.ones((P, P), np.float32)
pbase = np.full((P, P, 3), 0.55, np.float32)
for pid in ["lfr_star_lattice","lfr_stripe_drift","lfr_bunting_scallop","lfr_distressed_flag",
            "lfr_eagle_crest","lfr_firework_radial","lfr_constellation_field","lfr_ribbon_weave",
            "lfr_stencil_stars","lfr_liberty_filigree"]:
    entry = NEW_PATTERNS[pid]
    bb = {}
    def tex():
        global bb
        bb = entry["texture_fn"]((P, P), pmask, 42, 1.0)
    clock(pid + "/tex", tex)
    clock(pid + "/paint", lambda: entry["paint_fn"](pbase.copy(), (P, P), pmask, 42, 1.0, bb))

json.dump(results, open(r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\scripts\perf_results.json", "w"), indent=1)
bad = {k: v for k, v in results.items() if v > 3.0}
warn = {k: v for k, v in results.items() if 1.0 < v <= 3.0}
print()
print("TOTAL %d timings | FAIL(>3s): %d | warn(1-3s): %d" % (len(results), len(bad), len(warn)))
