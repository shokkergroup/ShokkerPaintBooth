#!/usr/bin/env python3
"""Render-time profiler for ALL color functions: bases, monolithics, fusions.

Quality-neutral render-time optimization baseline. Times every base
(spec_fn + paint_fn), every monolithic (spec_fn + paint_fn), and every
fusion at a representative size, sorted slowest-first so we can target the
hot tail. Writes a JSON + Markdown report under _perf/.

Each function is timed in isolation with per-fn try/except so a single
broken finish (e.g. Codex mid-rebuild) cannot abort the whole run.

Usage:
    python scripts/spb_color_fn_profiler.py --size 1024 --repeat 2 --tag before
    python scripts/spb_color_fn_profiler.py --size 1024 --repeat 2 --tag after
    python scripts/spb_color_fn_profiler.py --compare before after
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "_perf"


def _quiet_import():
    """Import the engine without the noisy GPU/registry banner on stdout."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import shokker_engine_v2 as eng
        if hasattr(eng, "_ensure_expansions_loaded"):
            try:
                eng._ensure_expansions_loaded()
            except Exception:
                pass
    return eng


def _best_of(fn, repeat):
    """Run fn() `repeat` times, return (best_seconds, output, error).

    Best-of-N (min) is the standard for micro-timing: it filters OS jitter
    and reflects the achievable time. First call may include lazy JIT/cache
    warmup, so repeat>=2 is recommended.
    """
    best = float("inf")
    out = None
    err = None
    for _ in range(max(1, repeat)):
        t0 = time.perf_counter()
        try:
            out = fn()
        except Exception as exc:  # noqa: BLE001 - per-fn isolation is the point
            return (0.0, None, f"{type(exc).__name__}: {exc}")
        dt = time.perf_counter() - t0
        if dt < best:
            best = dt
    return (best, out, err)


def _valid_output(out):
    if isinstance(out, np.ndarray):
        return 0 not in out.shape
    if isinstance(out, (tuple, list)) and out:
        return all((not isinstance(a, np.ndarray)) or (0 not in a.shape) for a in out)
    return out is not None


def _try_conventions(fn, conventions):
    """Try each calling convention; return the first that doesn't raise."""
    last_err = None
    for make_args in conventions:
        try:
            args, kwargs = make_args()
            out = fn(*args, **kwargs)
            return (make_args, out, None)
        except TypeError as exc:
            last_err = f"TypeError: {exc}"
            continue
        except Exception as exc:  # noqa: BLE001
            last_err = f"{type(exc).__name__}: {exc}"
            continue
    return (None, None, last_err)


def profile_monolithics(eng, size, seed, repeat, rows):
    reg = getattr(eng, "MONOLITHIC_REGISTRY", {}) or {}
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    for fid, entry in reg.items():
        if not isinstance(entry, (tuple, list)) or len(entry) < 2:
            continue
        spec_fn, paint_fn = entry[0], entry[1]
        # spec_fn(shape, mask, seed, sm)
        if callable(spec_fn):
            conv = [
                lambda: ((shape, mask, seed, 1.0), {}),
                lambda: ((shape, mask), {"seed": seed, "sm": 1.0}),
                lambda: ((shape,), {"seed": seed, "sm": 1.0}),
            ]
            mk, _o, err = _try_conventions(spec_fn, conv)
            if mk is not None:
                dt, out, _ = _best_of(lambda mk=mk, fn=spec_fn: fn(*mk()[0], **mk()[1]), repeat)
                rows.append({"kind": "monolithic", "id": fid, "phase": "spec",
                             "sec": round(dt, 6), "ok": _valid_output(out), "error": None})
            else:
                rows.append({"kind": "monolithic", "id": fid, "phase": "spec",
                             "sec": 0.0, "ok": False, "error": err})
        # paint_fn(paint, shape, mask, seed, pm, bb)
        if callable(paint_fn):
            base_paint = np.full((size, size, 3), 0.30, dtype=np.float32)
            conv = [
                lambda: ((base_paint.copy(), shape, mask, seed, 1.0, bb), {}),
                lambda: ((base_paint.copy(), shape, mask), {"seed": seed, "pm": 1.0, "bb": bb}),
                lambda: ((base_paint.copy(), shape, mask, seed, 1.0), {}),
            ]
            mk, _o, err = _try_conventions(paint_fn, conv)
            if mk is not None:
                dt, out, _ = _best_of(lambda mk=mk, fn=paint_fn: fn(*mk()[0], **mk()[1]), repeat)
                rows.append({"kind": "monolithic", "id": fid, "phase": "paint",
                             "sec": round(dt, 6), "ok": _valid_output(out), "error": None})
            else:
                rows.append({"kind": "monolithic", "id": fid, "phase": "paint",
                             "sec": 0.0, "ok": False, "error": err})


def profile_bases(eng, size, seed, repeat, rows):
    try:
        from engine.registry import BASE_REGISTRY
    except Exception as exc:  # noqa: BLE001
        rows.append({"kind": "base", "id": "<registry>", "phase": "import",
                     "sec": 0.0, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    for bid, entry in BASE_REGISTRY.items():
        if not isinstance(entry, dict):
            continue
        M = float(entry.get("M", 128))
        R = float(entry.get("R", 128))
        base_spec_fn = entry.get("base_spec_fn")
        paint_fn = entry.get("paint_fn")
        if callable(base_spec_fn):
            conv = [lambda: ((shape, seed, 1.0, M, R), {}),
                    lambda: ((shape, seed, 1.0), {})]
            mk, _o, err = _try_conventions(base_spec_fn, conv)
            if mk is not None:
                dt, out, _ = _best_of(lambda mk=mk, fn=base_spec_fn: fn(*mk()[0], **mk()[1]), repeat)
                rows.append({"kind": "base", "id": bid, "phase": "spec",
                             "sec": round(dt, 6), "ok": _valid_output(out), "error": None})
        if callable(paint_fn):
            base_paint = np.full((size, size, 3), 0.30, dtype=np.float32)
            conv = [lambda: ((base_paint.copy(), shape, mask, seed, 1.0, 0.0), {}),
                    lambda: ((base_paint.copy(), shape, mask, seed, 1.0), {})]
            mk, _o, err = _try_conventions(paint_fn, conv)
            if mk is not None:
                dt, out, _ = _best_of(lambda mk=mk, fn=paint_fn: fn(*mk()[0], **mk()[1]), repeat)
                rows.append({"kind": "base", "id": bid, "phase": "paint",
                             "sec": round(dt, 6), "ok": _valid_output(out), "error": None})


def profile_fusions(eng, size, seed, repeat, rows):
    try:
        from engine.expansions import fusions
        reg = fusions.FUSION_REGISTRY
    except Exception:
        return
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    bb = np.zeros(shape, dtype=np.float32)
    for fid, entry in reg.items():
        if not isinstance(entry, (tuple, list)) or len(entry) < 2:
            continue
        spec_fn, paint_fn = entry[0], entry[1]
        if callable(spec_fn):
            conv = [lambda: ((shape, mask), {"seed": seed, "sm": 1.0}),
                    lambda: ((shape, mask, seed, 1.0), {})]
            mk, _o, err = _try_conventions(spec_fn, conv)
            if mk is not None:
                dt, out, _ = _best_of(lambda mk=mk, fn=spec_fn: fn(*mk()[0], **mk()[1]), repeat)
                rows.append({"kind": "fusion", "id": fid, "phase": "spec",
                             "sec": round(dt, 6), "ok": _valid_output(out), "error": None})
        if callable(paint_fn):
            base_paint = np.full((size, size, 3), 0.18, dtype=np.float32)
            conv = [lambda: ((base_paint.copy(), shape, mask), {"seed": seed, "pm": 1.0, "bb": bb}),
                    lambda: ((base_paint.copy(), shape, mask, seed, 1.0, bb), {})]
            mk, _o, err = _try_conventions(paint_fn, conv)
            if mk is not None:
                dt, out, _ = _best_of(lambda mk=mk, fn=paint_fn: fn(*mk()[0], **mk()[1]), repeat)
                rows.append({"kind": "fusion", "id": fid, "phase": "paint",
                             "sec": round(dt, 6), "ok": _valid_output(out), "error": None})


def run(size, seed, repeat, tag, kinds):
    eng = _quiet_import()
    rows = []
    if "monolithic" in kinds:
        profile_monolithics(eng, size, seed, repeat, rows)
    if "base" in kinds:
        profile_bases(eng, size, seed, repeat, rows)
    if "fusion" in kinds:
        profile_fusions(eng, size, seed, repeat, rows)

    timed = [r for r in rows if r["error"] is None]
    errored = [r for r in rows if r["error"] is not None]
    timed.sort(key=lambda r: r["sec"], reverse=True)
    total = sum(r["sec"] for r in timed)
    payload = {
        "tag": tag, "size": size, "seed": seed, "repeat": repeat,
        "n_timed": len(timed), "n_error": len(errored),
        "total_sec": round(total, 4),
        "rows": timed + errored,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"profile_{tag}.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")

    lines = [f"# Color-fn render profile: {tag}", "",
             f"- size={size} seed={seed} repeat={repeat}",
             f"- timed={len(timed)} errored={len(errored)} total={total:.3f}s", "",
             "## Top 60 slowest", "",
             "| sec | kind | id | phase |", "|---:|---|---|---|"]
    for r in timed[:60]:
        lines.append(f"| {r['sec']:.4f} | {r['kind']} | `{r['id']}` | {r['phase']} |")
    (OUT_DIR / f"profile_{tag}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[profile:{tag}] timed={len(timed)} errored={len(errored)} total={total:.3f}s")
    print(f"[profile:{tag}] slowest:")
    for r in timed[:15]:
        print(f"    {r['sec']:.4f}s  {r['kind']:11s} {r['phase']:5s} {r['id']}")
    print(f"[profile:{tag}] wrote {OUT_DIR / ('profile_' + tag + '.json')}")


def compare(tag_a, tag_b):
    a = json.loads((OUT_DIR / f"profile_{tag_a}.json").read_text(encoding="utf-8"))
    b = json.loads((OUT_DIR / f"profile_{tag_b}.json").read_text(encoding="utf-8"))

    def index(p):
        return {(r["kind"], r["id"], r["phase"]): r["sec"] for r in p["rows"] if r["error"] is None}
    ia, ib = index(a), index(b)
    keys = sorted(set(ia) & set(ib), key=lambda k: ia[k] - ib.get(k, ia[k]), reverse=True)
    print(f"[compare] {tag_a} total={a['total_sec']:.3f}s -> {tag_b} total={b['total_sec']:.3f}s "
          f"({a['total_sec'] - b['total_sec']:+.3f}s, {100*(a['total_sec']-b['total_sec'])/max(1e-9,a['total_sec']):+.1f}%)")
    print("[compare] biggest per-fn improvements (before -> after):")
    for k in keys[:25]:
        d = ia[k] - ib[k]
        if abs(d) < 1e-4:
            continue
        pct = 100 * d / max(1e-9, ia[k])
        print(f"    {ia[k]:.4f}->{ib[k]:.4f}  ({d:+.4f}s {pct:+.1f}%)  {k[0]} {k[2]} {k[1]}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=51)
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--tag", default="before")
    ap.add_argument("--kinds", default="monolithic,base,fusion")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    args = ap.parse_args(argv)
    if args.compare:
        compare(*args.compare)
        return 0
    run(args.size, args.seed, args.repeat, args.tag, set(args.kinds.split(",")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
