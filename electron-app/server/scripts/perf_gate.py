# -*- coding: utf-8 -*-
"""SPB RENDER-TIME HARD GATE  (owner mandate 2026-06-13)
=========================================================
THE rule, enforced over EVERY registered finish (no sampling, ever):
    * HARD FAIL  : any finish render > 4.0s at 2048x2048  -> exit code 1
    * WARN       : 1.5s .. 4.0s (above optimal, allowed but flagged)
    * PASS       : < 1.5s (the optimal target)

This is the audit that was missing: the Spectrum Shift family (and others)
slipped through because prior checks sampled a subset / specific categories.
This gate times the WHOLE catalog at the real render size the app uses.

Covers MONOLITHIC_REGISTRY (spec_fn + paint_fn), BASE_REGISTRY (compose_finish),
and spec_patterns.PATTERN_CATALOG. Each fn is WARMED once (first call pays the
noise-cache cost) then timed best-of-2.

INCREMENTAL by default: results are cached per finish keyed by a stable hash of
the render fn, in _audit/perf_gate_cache.json. Only finishes whose code changed
are re-timed, so repeat runs (and the preflight hook) are fast. Use --full to
ignore the cache and re-time everything (the authoritative baseline — run this
on a QUIET machine; CPU contention from other work inflates timings).

Usage:
    python scripts/perf_gate.py            # incremental, gate the catalog
    python scripts/perf_gate.py --full     # re-time everything (clean baseline)
    python scripts/perf_gate.py --only fs_ # only ids with this prefix (debug)
Exit code 1 if ANY finish exceeds the 4.0s hard ceiling.
"""
from __future__ import annotations
import sys, os, json, time, argparse
import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)

HARD_CEIL = 4.0     # owner: never over 4s
OPTIMAL = 1.5       # owner: optimally under 1.5s
S = 2048
CACHE_PATH = os.path.join(ROOT, "_audit", "perf_gate_cache.json")


def _fn_hash(fn):
    """Stable per-fn fingerprint so unchanged finishes are not re-timed.
    Reuse the engine's hardened hash when available; else hash the code +
    qualname + closure cells (unwrapping contract wrappers)."""
    try:
        import shokker_engine_v2 as eng
        if hasattr(eng, "_get_fn_hash"):
            h = eng._get_fn_hash(fn)
            if h:
                return str(h)
    except Exception:
        pass
    import hashlib
    parts = []
    seen = set()
    f = fn
    depth = 0
    while f is not None and id(f) not in seen and depth < 6:
        seen.add(id(f)); depth += 1
        try:
            parts.append(getattr(f, "__qualname__", "") + "@" + getattr(f, "__module__", ""))
        except Exception:
            pass
        code = getattr(f, "__code__", None)
        if code is not None:
            try:
                parts.append(code.co_code.hex())
                parts.append(repr(sorted(code.co_consts, key=lambda c: str(type(c)))[:8]))
            except Exception:
                pass
        nxt = getattr(f, "__wrapped__", None)
        if nxt is None:
            cl = getattr(f, "__closure__", None)
            if cl:
                for c in cl:
                    try:
                        v = c.cell_contents
                        if callable(v):
                            nxt = v; break
                    except Exception:
                        pass
        f = nxt
    return hashlib.blake2b("|".join(parts).encode(), digest_size=16).hexdigest()


def _time(fn, *a):
    fn(*a)  # warm
    best = 1e9
    for _ in range(2):
        t = time.perf_counter()
        fn(*a)
        best = min(best, time.perf_counter() - t)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="ignore cache, re-time everything")
    ap.add_argument("--only", default="", help="only ids starting with this prefix")
    ap.add_argument("--json", default="", help="also write the full report JSON here")
    ap.add_argument("--batch", default="", help="K/N: time only the K-th of N strides, accumulating into the cache "
                                                 "(run each batch in a FRESH process so engine caches free between "
                                                 "batches — a single --full run leaked to ~39GB). See arm_perf_gate.py.")
    ap.add_argument("--report-only", action="store_true", dest="report_only",
                    help="read the cache + report; do NOT render/time anything (orchestrator's final pass)")
    args = ap.parse_args()

    from engine.registry import MONOLITHIC_REGISTRY, BASE_REGISTRY
    try:
        from engine import spec_patterns as sp
        SPEC = sp.PATTERN_CATALOG
    except Exception:
        SPEC = {}
    try:
        from engine import compose as C
    except Exception:
        C = None

    cache = {}
    # Load the cache for incremental/report/batch runs (so batches ACCUMULATE rather
    # than clobber each other). A plain --full (non-batch) intentionally starts clean.
    if (args.batch or args.report_only or not args.full) and os.path.exists(CACHE_PATH):
        try:
            cache = json.load(open(CACHE_PATH, encoding="utf-8"))
        except Exception:
            cache = {}

    mask = np.ones((S, S), np.float32)
    base = np.full((S, S, 3), 0.5, np.float32)
    results = {}   # id -> {seconds, kind}
    timed = reused = 0
    candidates = []  # (fid, kind, ck, runner) — collected first, then sliced/timed

    def add(fid, kind, hsh, runner):
        if args.only and not fid.startswith(args.only):
            return
        candidates.append((fid, kind, f"{kind}:{fid}:{hsh}", runner))

    print("== SPB PERF GATE @ %d (hard ceiling %.1fs, optimal <%.1fs) ==" % (S, HARD_CEIL, OPTIMAL))
    for fid, v in MONOLITHIC_REGISTRY.items():
        if not (isinstance(v, (tuple, list)) and len(v) >= 2):
            continue
        spec_fn, paint_fn = v[0], v[1]
        hsh = _fn_hash(paint_fn) + _fn_hash(spec_fn)
        add(fid, "monolithic", hsh,
            lambda pf=paint_fn, sf=spec_fn: _time(lambda: pf(base.copy(), (S, S), mask, 42, 1.0, {}))
                                            + _time(lambda: sf((S, S), mask, 42, 1.0)))
    if C is not None:
        for bid, v in BASE_REGISTRY.items():
            hsh = _fn_hash(v.get("paint_fn")) if isinstance(v, dict) else _fn_hash(v)
            add(bid, "base", hsh,
                lambda b=bid: _time(lambda: C.compose_finish(b, "none", (S, S), mask, 42, 1.0))
                              + _time(lambda: C.compose_paint_mod(b, "none", base.copy(), (S, S), mask, 42, 1.0, 0.0)))
    for pid, fn in SPEC.items():
        if not callable(fn):
            continue
        add("spec:" + pid, "spec_overlay", _fn_hash(fn),
            lambda f=fn: _time(lambda: f((S, S), 42, 1.0)))

    candidates.sort(key=lambda c: (c[1], c[0]))

    if args.report_only:
        # Read cached timings only — render NOTHING (orchestrator's final pass).
        for fid, kind, ck, _runner in candidates:
            if ck in cache:
                results[fid] = {"seconds": float(cache[ck]), "kind": kind}
                reused += 1
    else:
        force = args.full or bool(args.batch)
        if args.batch:
            try:
                _k, _n = (int(x) for x in args.batch.split("/"))
            except Exception:
                print("  bad --batch (use K/N, e.g. 0/24)")
                return 2
            candidates = candidates[_k::_n] if _n > 0 else candidates
            print("  batch %d/%d -> %d finish(es) this process (fresh-process arming)" % (_k, _n, len(candidates)))
        for fid, kind, ck, runner in candidates:
            if ck in cache and not force:
                results[fid] = {"seconds": float(cache[ck]), "kind": kind}
                reused += 1
                continue
            try:
                sec = runner()
            except Exception as e:
                results[fid] = {"seconds": -1.0, "kind": kind, "error": str(e)[:120]}
                continue
            results[fid] = {"seconds": sec, "kind": kind}
            cache[ck] = sec
            timed += 1

    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"))
    except Exception:
        pass

    fails = sorted([(d["seconds"], i, d["kind"]) for i, d in results.items() if d["seconds"] > HARD_CEIL], reverse=True)
    warns = sorted([(d["seconds"], i, d["kind"]) for i, d in results.items() if OPTIMAL < d["seconds"] <= HARD_CEIL], reverse=True)
    errs = [(i, d.get("error")) for i, d in results.items() if d["seconds"] == -1.0]

    if args.json:
        try:
            json.dump(results, open(args.json, "w", encoding="utf-8"), indent=1)
        except Exception:
            pass

    print("  timed %d, reused %d from cache, total %d finishes" % (timed, reused, len(results)))
    if errs:
        print("  ERRORS (%d): %s" % (len(errs), ", ".join(i for i, _ in errs[:10])))
    print("  PASS (<%.1fs): %d   WARN (%.1f-%.1fs): %d   FAIL (>%.1fs): %d"
          % (OPTIMAL, sum(1 for d in results.values() if 0 <= d["seconds"] <= OPTIMAL),
             OPTIMAL, HARD_CEIL, len(warns), HARD_CEIL, len(fails)))
    if fails:
        print("\n  *** HARD-FAIL: %d finish(es) over the %.1fs ceiling ***" % (len(fails), HARD_CEIL))
        for sec, fid, kind in fails[:60]:
            print("    %7.2fs  %-13s %s" % (sec, kind, fid))
    if warns[:20]:
        print("\n  warn (above optimal, get these under %.1fs too):" % OPTIMAL)
        for sec, fid, kind in warns[:20]:
            print("    %7.2fs  %-13s %s" % (sec, kind, fid))

    if fails:
        print("\nRESULT: FAIL — %d finish(es) exceed the %.1fs hard ceiling. Optimize before ship." % (len(fails), HARD_CEIL))
        return 1
    print("\nRESULT: PASS — every finish is within the %.1fs ceiling." % HARD_CEIL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
