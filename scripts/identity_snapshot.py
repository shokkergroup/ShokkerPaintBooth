# -*- coding: utf-8 -*-
"""Snapshot all 70 LFR+FABLE items at 512 (seed 42) BEFORE optimization, or
compare AFTER (arg 'check'): renders must stay visually identical (max abs
diff <= 0.02 in [0,1] space, i.e. ~5/255)."""
import sys
import numpy as np
sys.path.insert(0, r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum")

mode = sys.argv[1] if len(sys.argv) > 1 else "save"
PATH = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\_opt_baseline.npz"
S = 512
mask = np.ones((S, S), np.float32)
base = np.full((S, S, 3), 0.5, np.float32)

from engine.registry import MONOLITHIC_REGISTRY
from engine import spec_patterns as sp
from engine.pattern_expansion import NEW_PATTERNS

FIN = [f for f in MONOLITHIC_REGISTRY if f.startswith(("lfr_", "fable_"))]
OVL = [p for p in sp.PATTERN_CATALOG if p.startswith("spec_lfr_")]
PAT = [p for p in NEW_PATTERNS if p.startswith("lfr_")]

cur = {}
for fid in sorted(FIN):
    spec_fn, paint_fn = MONOLITHIC_REGISTRY[fid]
    cur[fid + "/paint"] = paint_fn(base.copy(), (S, S), mask, 42, 1.0, {})[:, :, :3].astype(np.float16)
    cur[fid + "/spec"] = (spec_fn((S, S), mask, 42, 1.0)[:, :, :3].astype(np.float32) / 255.0).astype(np.float16)
for pid in sorted(OVL):
    out = np.asarray(sp.PATTERN_CATALOG[pid]((S, S), 42, 1.0), np.float32)
    cur[pid] = out.astype(np.float16)
for pid in sorted(PAT):
    bb = NEW_PATTERNS[pid]["texture_fn"]((S, S), mask, 42, 1.0)
    cur[pid + "/pv"] = np.asarray(bb["pattern_val"], np.float32).astype(np.float16)

if mode == "save":
    np.savez_compressed(PATH, **cur)
    print("SAVED baseline:", len(cur), "arrays")
else:
    ref = np.load(PATH)
    bad = 0
    for k in sorted(cur):
        if k not in ref.files:
            print("NEW (no baseline):", k); continue
        a, b = ref[k].astype(np.float32), cur[k].astype(np.float32)
        if a.shape != b.shape:
            print("SHAPE CHANGE", k, a.shape, b.shape); bad += 1; continue
        d = float(np.abs(a - b).max())
        md = float(np.abs(a - b).mean())
        if d > 0.02:
            print("DIFF %-44s max %.4f mean %.5f" % (k, d, md)); bad += 1
    print("IDENTITY:", "CLEAN (all <= 0.02)" if bad == 0 else "%d items drifted" % bad)
    sys.exit(1 if bad else 0)
