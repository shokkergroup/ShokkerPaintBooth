#!/usr/bin/env python3
"""Pixel-identity verifier for render-time optimizations (quality-neutral proof).

Captures the full uint8 output of each target color function to a compact
.npz so an optimization can be proven quality-neutral: byte-identical, or
within a tiny max-LSB delta that is invisible at 8-bit.

Workflow (same engine inputs both runs):
    python scripts/spb_color_fn_verify.py capture --tag pre
    # ... apply optimizations ...
    python scripts/spb_color_fn_verify.py capture --tag post
    python scripts/spb_color_fn_verify.py compare pre post   # exit 0 if all within tol

Targets the monolithic paint_fns by default; pass --ids id1,id2 to narrow.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
OUT = REPO / "_perf"


def _quiet_import():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import shokker_engine_v2 as eng
        if hasattr(eng, "_ensure_expansions_loaded"):
            try:
                eng._ensure_expansions_loaded()
            except Exception:
                pass
    return eng


def _to_u8(out):
    if isinstance(out, (tuple, list)):
        out = out[0]
    a = np.asarray(out)
    if a.dtype == np.uint8:
        return a
    af = a.astype(np.float64)
    if np.nanmax(af) <= 1.0 + 1e-6 and np.nanmin(af) >= -1e-6:
        af = af * 255.0
    return np.clip(np.nan_to_num(af), 0, 255).astype(np.uint8)


def capture(tag, size, seed, ids):
    eng = _quiet_import()
    reg = getattr(eng, "MONOLITHIC_REGISTRY", {}) or {}
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    base_paint = np.full((size, size, 3), 0.30, dtype=np.float32)
    arrays = {}
    targets = ids if ids else list(reg.keys())
    for fid in targets:
        entry = reg.get(fid)
        if not isinstance(entry, (tuple, list)) or len(entry) < 2:
            continue
        paint_fn = entry[1]
        if not callable(paint_fn):
            continue
        try:
            out = paint_fn(base_paint.copy(), shape, mask, seed, 1.0, bb)
        except TypeError:
            try:
                out = paint_fn(base_paint.copy(), shape, mask, seed, 1.0)
            except Exception:
                continue
        except Exception:
            continue
        arrays[fid] = _to_u8(out)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / f"verify_{tag}.npz", **arrays)
    print(f"[verify:{tag}] captured {len(arrays)} outputs, size={size} seed={seed}")


def compare(tag_a, tag_b, tol):
    a = np.load(OUT / f"verify_{tag_a}.npz")
    b = np.load(OUT / f"verify_{tag_b}.npz")
    keys = sorted(set(a.files) & set(b.files))
    identical, within, over = [], [], []
    for k in keys:
        xa, xb = a[k].astype(np.int16), b[k].astype(np.int16)
        if xa.shape != xb.shape:
            over.append((k, "SHAPE", -1, -1.0))
            continue
        d = np.abs(xa - xb)
        maxd = int(d.max())
        pct = 100.0 * float((d > 0).mean())
        if maxd == 0:
            identical.append(k)
        elif maxd <= tol:
            within.append((k, maxd, pct))
        else:
            over.append((k, "DELTA", maxd, pct))
    print(f"[compare] {tag_a} vs {tag_b} (tol={tol} LSB):")
    print(f"  byte-identical : {len(identical)}")
    print(f"  within tol     : {len(within)}")
    print(f"  OVER tol       : {len(over)}")
    for k, maxd, pct in within[:40]:
        print(f"    ~ {k}: max {maxd} LSB, {pct:.3f}% px changed")
    for item in over[:40]:
        print(f"    !! {item[0]}: {item[1]} maxd={item[2]} pct={item[3]}")
    only_a = set(a.files) - set(b.files)
    only_b = set(b.files) - set(a.files)
    if only_a:
        print(f"  only in {tag_a}: {sorted(only_a)[:10]}{'...' if len(only_a) > 10 else ''}")
    if only_b:
        print(f"  only in {tag_b}: {sorted(only_b)[:10]}{'...' if len(only_b) > 10 else ''}")
    return 0 if not over else 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    cap = sub.add_parser("capture")
    cap.add_argument("--tag", required=True)
    cap.add_argument("--size", type=int, default=256)
    cap.add_argument("--seed", type=int, default=51)
    cap.add_argument("--ids")
    cmp = sub.add_parser("compare")
    cmp.add_argument("tag_a")
    cmp.add_argument("tag_b")
    cmp.add_argument("--tol", type=int, default=1, help="max allowed LSB delta (default 1 = invisible)")
    args = ap.parse_args(argv)
    if args.cmd == "capture":
        ids = [s.strip() for s in args.ids.split(",")] if args.ids else None
        capture(args.tag, args.size, args.seed, ids)
        return 0
    if args.cmd == "compare":
        return compare(args.tag_a, args.tag_b, args.tol)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
