# -*- coding: utf-8 -*-
"""Overnight full-catalog health + spec-uniqueness audit.

Renders every base / pattern / monolithic (paint swatch + spec map) and every
spec pattern, at multiple sizes, through the SERVER'S OWN render path
(`server._render_swatch_bytes` / `_render_spec_swatch_bytes` / the spec
PATTERN_CATALOG) so it exercises the real registry conventions — no guessing.

For each finish it records: hard errors, NaN/inf, dead/flat output (near-zero
variance = "finish does nothing"), render time (perf), per-channel M/R/Cc stats,
and an 8x8 structural signature used later for near-duplicate detection.

Writes incrementally to _overnight_audit/catalog_audit.json so a crash mid-run
keeps everything rendered so far. READ-ONLY: never mutates a finish.

Usage:  python -B scripts/overnight_catalog_audit.py [--sample N]
"""
import os, sys, io, json, time, argparse

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.environ.setdefault("SHOKKER_SKIP_SPEC_PREBAKE", "1")   # don't spawn the prebake thread
os.environ.setdefault("SHOKKER_NO_CLEAN", "1")            # don't fight the live server
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, ROOT)

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--sample", type=int, default=0, help="only audit N finishes per type (smoke test)")
args = ap.parse_args()

print("[audit] importing server (loads full engine, ~20s)...", flush=True)
_t0 = time.time()
import server
engine = server.engine
from engine.spec_patterns import PATTERN_CATALOG as SPEC_CATALOG
print("[audit] server imported in %.1fs" % (time.time() - _t0), flush=True)

OUT = os.path.join(ROOT, "_overnight_audit")
os.makedirs(OUT, exist_ok=True)
JSON_PATH = os.path.join(OUT, "catalog_audit.json")

DEAD_EPS = 0.012          # overall std below this = effectively flat/dead output
PAINT_SIZES = [64, 160]   # bug surface for the picker/preview (pearl_micro broke <256)
SPEC_SIZE = 160
SPEC_PATTERN_SIZES = [64, 160, 512]

results = {"meta": {}, "paint": {}, "spec": {}, "spec_pattern": {}}


def _arr_from_png(b):
    return np.asarray(Image.open(io.BytesIO(b)).convert("RGB"), np.float32) / 255.0


def _stats(arr):
    finite = bool(np.isfinite(arr).all())
    a = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=0.0)
    ch = [[round(float(a[:, :, c].mean()), 4), round(float(a[:, :, c].std()), 4)] for c in range(3)]
    overall = round(float(a.std()), 4)
    return {"finite": finite, "ch": ch, "std": overall, "dead": overall < DEAD_EPS}


def _sig(arr):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype("uint8")).resize((8, 8))
    return [round(float(x), 3) for x in (np.asarray(im, np.float32) / 255.0).flatten()]


def _save():
    tmp = JSON_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(results, f)
    os.replace(tmp, JSON_PATH)


def audit_swatch(ftype, ids):
    rec = {}
    n = len(ids)
    for i, fid in enumerate(ids):
        entry = {"paint": {}, "spec": None}
        for sz in PAINT_SIZES:
            try:
                t = time.time()
                b = server._render_swatch_bytes(ftype, fid, "888888", sz, 42)
                st = _stats(_arr_from_png(b))
                st["ms"] = round((time.time() - t) * 1000, 1)
                entry["paint"][sz] = st
            except Exception as e:
                entry["paint"][sz] = {"error": ("%s: %s" % (type(e).__name__, e))[:200]}
        try:
            arr = _arr_from_png(server._render_spec_swatch_bytes(ftype, fid, SPEC_SIZE, 42))
            st = _stats(arr)
            st["sig"] = _sig(arr)
            entry["spec"] = st
        except Exception as e:
            entry["spec"] = {"error": ("%s: %s" % (type(e).__name__, e))[:200]}
        rec[fid] = entry
        if (i + 1) % 50 == 0:
            print("[audit] %s %d/%d (%.0fs)" % (ftype, i + 1, n, time.time() - _t0), flush=True)
            results["paint"][ftype] = rec
            _save()
    results["paint"][ftype] = rec
    _save()


def audit_spec_patterns(ids):
    rec = {}
    n = len(ids)
    for i, sid in enumerate(ids):
        fn = SPEC_CATALOG[sid]
        entry = {}
        for sz in SPEC_PATTERN_SIZES:
            try:
                a = np.asarray(fn((sz, sz), 42, 1.0), np.float32)
                if a.ndim == 2:
                    a = np.dstack([a, a, a])
                entry[sz] = _stats(np.clip(a[:, :, :3], 0, 1))
            except Exception as e:
                entry[sz] = {"error": ("%s: %s" % (type(e).__name__, e))[:200]}
        try:
            a = np.asarray(fn((160, 160), 42, 1.0), np.float32)
            if a.ndim == 2:
                a = np.dstack([a, a, a])
            entry["sig"] = _sig(np.clip(a[:, :, :3], 0, 1))
        except Exception:
            entry["sig"] = None
        rec[sid] = entry
        if (i + 1) % 40 == 0:
            print("[audit] spec_pattern %d/%d (%.0fs)" % (i + 1, n, time.time() - _t0), flush=True)
            results["spec_pattern"] = rec
            _save()
    results["spec_pattern"] = rec
    _save()


base_ids = list(getattr(engine, "BASE_REGISTRY", {}))
pattern_ids = list(getattr(engine, "PATTERN_REGISTRY", {}))
mono_ids = list(getattr(engine, "MONOLITHIC_REGISTRY", {}))
spec_ids = list(SPEC_CATALOG)
if args.sample:
    base_ids, pattern_ids, mono_ids, spec_ids = (
        base_ids[: args.sample], pattern_ids[: args.sample],
        mono_ids[: args.sample], spec_ids[: args.sample],
    )

results["meta"] = {
    "counts": {"base": len(base_ids), "pattern": len(pattern_ids),
               "monolithic": len(mono_ids), "spec_pattern": len(spec_ids)},
    "paint_sizes": PAINT_SIZES, "spec_size": SPEC_SIZE,
    "spec_pattern_sizes": SPEC_PATTERN_SIZES, "dead_eps": DEAD_EPS,
    "started": time.time(), "sample": args.sample,
}
_save()

print("[audit] bases (%d)..." % len(base_ids), flush=True)
audit_swatch("base", base_ids)
print("[audit] patterns (%d)..." % len(pattern_ids), flush=True)
audit_swatch("pattern", pattern_ids)
print("[audit] monolithics (%d)..." % len(mono_ids), flush=True)
audit_swatch("monolithic", mono_ids)
print("[audit] spec patterns (%d)..." % len(spec_ids), flush=True)
audit_spec_patterns(spec_ids)

results["meta"]["finished"] = time.time()
results["meta"]["elapsed_s"] = round(time.time() - results["meta"]["started"], 1)
_save()
print("[audit] DONE in %.0fs -> %s" % (time.time() - results["meta"]["started"], JSON_PATH), flush=True)
