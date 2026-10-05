#!/usr/bin/env python3
"""
Tick 86 probe — diagnose the real-quality STILL-WEAK clusters that emerged
from tick 85's color-aware M1.

After SPB-97 unmasked false dHash clones (Gradient Vortex, Extended, Directional
got cleaned up because they were never bake-stale, only metric-blind), the
M7 STILL-WEAK list now shows TRUE quality clusters at the top:

  Weather & Age     n=10  mean 26.6  10/10 critical
  Textile-Inspired  n=6   mean 25.6   6/6 critical
  Ghost Geometry    n=10  mean 26.7   9/10 critical  (spec_driven)
  Abstract Art      n=17  mean 38.3  10/17 critical

This probe applies the technique from tick 81 (paradigm probe) — invoke each
finish's paint_fn (and spec_fn for monolithics) on a neutral substrate at
256² and measure the resulting structure (per-channel std). Classify each
finish as:

  bake-stale     : renderer produces structure (std > threshold), thumbnail
                   on disk looks flat → re-bake will help
  flat-by-design : renderer produces minimal structure on neutral substrate
                   → low M7 score is real; needs engine work, not re-bake
  under-rendered : renderer fails entirely or produces only color shifts →
                   needs engine attention

Output: _workbook_metrics/m_real_weak_probe.json with per-finish std stats and
a classification per category.

USAGE
-----
    python scripts/spb86_probe_real_weak_clusters.py
    python scripts/spb86_probe_real_weak_clusters.py --size 512  # slower, more accurate
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

V5_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V5_ROOT))

SCORECARD = V5_ROOT / "paint-booth-0-catalog-scorecard.js"
OUT_PATH = V5_ROOT / "_workbook_metrics" / "m_real_weak_probe.json"


# Categories to probe (from M7 STILL-WEAK after SPB-97).
TARGET_CATEGORIES = [
    "Weather & Age",
    "Textile-Inspired",
    "Ghost Geometry",
    "Abstract Art",
]


# Thresholds for classification, calibrated against tick 81 paradigm probe data:
#   paint std > 0.04 → renderer has paint-channel structure
#   M std > 6        → renderer has spec-channel structure (monolithic)
PAINT_STRUCTURE_THRESHOLD = 0.04
SPEC_STRUCTURE_THRESHOLD = 6.0


def load_scorecard() -> dict[str, dict]:
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    body_match = re.search(r"=\s*(\{.*\});", txt, flags=re.S)
    if body_match is None:
        raise ValueError(f"Could not parse scorecard JSON body from {SCORECARD}")
    body = re.sub(r"//[^\n]*", "", body_match.group(1))
    return json.loads(body)


def probe_monolithic(stem: str, entry, size: int) -> dict:
    """Invoke monolithic spec_fn + paint_fn on neutral input, measure structure."""
    spec_fn, paint_fn = entry[0], entry[1]
    seed = hash(stem) & 0x7FFFFFFF
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    out = {"stem": stem, "surface": "monolithic", "ok": True, "errors": []}

    # Spec channel
    t0 = time.perf_counter()
    try:
        spec = spec_fn(shape, mask, seed, 1.0)
        if spec is None or spec.ndim != 3 or spec.shape[2] < 3:
            raise ValueError(f"unexpected spec shape {None if spec is None else spec.shape}")
        out["t_spec_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["spec_M_std"] = round(float(np.std(spec[..., 0])), 3)
        out["spec_R_std"] = round(float(np.std(spec[..., 1])), 3)
        out["spec_CC_std"] = round(float(np.std(spec[..., 2])), 3)
        out["spec_M_mean"] = round(float(np.mean(spec[..., 0])), 2)
    except Exception as exc:
        out["ok"] = False
        out["errors"].append(f"spec_fn: {exc}")
        out["spec_M_std"] = out["spec_R_std"] = out["spec_CC_std"] = None

    # Paint channel
    neutral = np.full((size, size, 3), 0.5, dtype=np.float32)
    t0 = time.perf_counter()
    try:
        painted = paint_fn(neutral.copy(), shape, mask, seed, 1.0, 1.0)
        if painted is None:
            raise ValueError("paint_fn returned None")
        out["t_paint_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["paint_std"] = round(float(np.std(painted)), 4)
        delta = painted - neutral
        out["paint_delta_max"] = round(float(np.max(np.abs(delta))), 4)
        out["paint_delta_std"] = round(float(np.std(delta)), 4)
    except Exception as exc:
        out["ok"] = not out["ok"] and False or False
        if out["ok"] is not False:
            out["ok"] = False
        out["errors"].append(f"paint_fn: {exc}")
        out["paint_std"] = out["paint_delta_max"] = out["paint_delta_std"] = None

    return out


def probe_base(stem: str, entry, size: int) -> dict:
    """Invoke base spec_fn + paint_fn on neutral input."""
    seed = hash(stem) & 0x7FFFFFFF
    shape = (size, size)
    mask = np.ones(shape, dtype=np.float32)
    out = {"stem": stem, "surface": "base", "ok": True, "errors": []}

    spec_fn = entry.get("base_spec_fn")
    paint_fn = entry.get("paint_fn")

    # Spec
    t0 = time.perf_counter()
    try:
        result = spec_fn(shape, seed, 1.0, entry.get("M", 128), entry.get("R", 80))
        if len(result) == 2:
            M, R = result
            CC = np.full_like(M, max(16.0, float(entry.get("CC", 16))), dtype=np.float32)
        else:
            M, R, CC = result
        out["t_spec_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["spec_M_std"] = round(float(np.std(M)), 3)
        out["spec_R_std"] = round(float(np.std(R)), 3)
        out["spec_CC_std"] = round(float(np.std(CC)), 3)
        out["spec_M_mean"] = round(float(np.mean(M)), 2)
    except Exception as exc:
        out["ok"] = False
        out["errors"].append(f"base_spec_fn: {exc}")
        out["spec_M_std"] = out["spec_R_std"] = out["spec_CC_std"] = None

    # Paint
    neutral = np.full((size, size, 3), 0.5, dtype=np.float32)
    t0 = time.perf_counter()
    try:
        painted = paint_fn(neutral.copy(), shape, mask, seed, 1.0, 1.0)
        if painted is None:
            raise ValueError("paint_fn returned None")
        out["t_paint_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["paint_std"] = round(float(np.std(painted)), 4)
        delta = painted - neutral
        out["paint_delta_max"] = round(float(np.max(np.abs(delta))), 4)
        out["paint_delta_std"] = round(float(np.std(delta)), 4)
    except Exception as exc:
        if out["ok"] is True:
            out["ok"] = False
        out["errors"].append(f"paint_fn: {exc}")
        out["paint_std"] = out["paint_delta_max"] = out["paint_delta_std"] = None

    return out


def probe_spec_pattern(stem: str, fn, size: int) -> dict:
    """Invoke a spec_pattern function (signature: (shape, seed, sm) -> 2D float32).

    Tick 87 (SPB-99): spec_patterns return a single 2D float32 channel in [0,1]
    representing intensity, not the M/R/CC triple monolithic spec_fn returns.
    We measure std over the channel and treat it as the spec-structure proxy."""
    seed = hash(stem) & 0x7FFFFFFF
    shape = (size, size)
    out = {"stem": stem, "surface": "spec_pattern", "ok": True, "errors": []}
    t0 = time.perf_counter()
    try:
        result = fn(shape, seed, 1.0)
        if result is None:
            raise ValueError("returned None")
        arr = np.asarray(result, dtype=np.float32)
        out["t_spec_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        # Treat as spec-M proxy. Scale: spec_pattern outputs are [0,1] floats,
        # spec_M_std in monolithic is on a 0-255 byte scale. Multiply by 255 so
        # the classification threshold compares apples-to-apples.
        std01 = float(np.std(arr))
        out["spec_M_std"] = round(std01 * 255.0, 3)
        out["spec_R_std"] = None
        out["spec_CC_std"] = None
        out["spec_M_mean"] = round(float(np.mean(arr)) * 255.0, 2)
        out["paint_std"] = None  # spec_patterns have no paint_fn of their own
        out["paint_delta_max"] = None
        out["paint_delta_std"] = None
    except Exception as exc:
        out["ok"] = False
        out["errors"].append(f"spec_pattern_fn: {exc}")
        out["spec_M_std"] = None
    return out


def classify(probe: dict, intent_hint: str) -> str:
    """Return one of: bake-stale, flat-by-design, under-rendered, healthy."""
    if not probe.get("ok"):
        return "under-rendered"
    paint_struct = (probe.get("paint_std") or 0) > PAINT_STRUCTURE_THRESHOLD
    spec_struct  = (probe.get("spec_M_std") or 0) > SPEC_STRUCTURE_THRESHOLD

    # spec_driven categories: only the spec channel needs to have structure.
    if intent_hint == "spec_driven":
        if spec_struct:
            return "bake-stale"  # spec has structure, thumbnail might be paint-only flat
        else:
            return "flat-by-design"

    # full / pattern_design: paint channel is the primary signal.
    if paint_struct or spec_struct:
        return "bake-stale"
    return "flat-by-design"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--size", type=int, default=256,
                    help="Probe size (default 256, fast). 512 for higher fidelity.")
    ap.add_argument("--categories", nargs="+", default=TARGET_CATEGORIES,
                    help=f"Categories to probe. Default: {TARGET_CATEGORIES}")
    args = ap.parse_args()

    print(f"[probe] size={args.size}  categories={args.categories}")

    scorecard = load_scorecard()
    import shokker_engine_v2 as eng  # noqa
    base = getattr(eng, "BASE_REGISTRY", {})
    mono = getattr(eng, "MONOLITHIC_REGISTRY", {})

    # Tick 87: load spec_pattern catalog from engine.spec_patterns.PATTERN_CATALOG
    spec_patterns: dict = {}
    try:
        from engine.spec_patterns import PATTERN_CATALOG as _SPEC_PATTERN_CATALOG
        spec_patterns = dict(_SPEC_PATTERN_CATALOG)
    except Exception as exc:
        print(f"[probe][warn] could not load engine.spec_patterns.PATTERN_CATALOG: {exc}")

    print(f"[probe] BASE={len(base)}  MONOLITHIC={len(mono)}  SPEC_PATTERN={len(spec_patterns)}")

    # Get intent hints from surface_intent if available.
    try:
        from engine.paint_v2.surface_intent import get_intent
    except Exception:
        def get_intent(cat, fid=None):
            return "full"

    results_by_cat: dict[str, list[dict]] = {}
    for cat in args.categories:
        members = [fid for fid, e in scorecard.items() if e.get("category") == cat]
        members.sort()
        if not members:
            print(f"[probe] (no members)  {cat}")
            continue
        intent = get_intent(cat) if callable(get_intent) else "full"
        print()
        print(f"=== {cat}  (n={len(members)}, intent={intent}) ===")
        cat_results = []
        for fid in members:
            surface, _, stem = fid.partition(":")
            if surface == "monolithic":
                entry = mono.get(stem)
                if not entry:
                    print(f"  {stem:34s}  MISSING from MONOLITHIC_REGISTRY")
                    continue
                probe = probe_monolithic(stem, entry, args.size)
            elif surface == "base":
                entry = base.get(stem)
                if not entry:
                    print(f"  {stem:34s}  MISSING from BASE_REGISTRY")
                    continue
                probe = probe_base(stem, entry, args.size)
            elif surface == "spec_pattern":
                # Resolve `spec_<name>` aliases used by JS catalog to the
                # underlying entry in PATTERN_CATALOG. Many spec_pattern ids
                # were renamed in 2026-04-21 (HP2/HP3/H4HR-*) and now use a
                # `spec_` prefix to disambiguate from monolithic siblings.
                fn = spec_patterns.get(stem)
                if fn is None and stem.startswith("spec_"):
                    fn = spec_patterns.get(stem[5:])
                if fn is None:
                    print(f"  {stem:34s}  MISSING from spec_patterns.PATTERN_CATALOG")
                    continue
                probe = probe_spec_pattern(stem, fn, args.size)
            else:
                continue
            probe["fid"] = fid
            probe["category"] = cat
            probe["intent"] = intent
            probe["classification"] = classify(probe, intent)
            cat_results.append(probe)

            ps = probe.get("paint_std")
            ms = probe.get("spec_M_std")
            cl = probe["classification"]
            err = "  ERR:" + ";".join(probe["errors"])[:60] if probe.get("errors") else ""
            print(f"  {stem:34s}  paint_std={('--' if ps is None else f'{ps:.4f}')}  spec_M_std={('--' if ms is None else f'{ms:6.2f}')}  → {cl}{err}")

        results_by_cat[cat] = cat_results

    # Summary
    print()
    print("=== Classification summary ===")
    for cat, rs in results_by_cat.items():
        counts = {"bake-stale": 0, "flat-by-design": 0, "under-rendered": 0, "healthy": 0}
        for r in rs:
            counts[r["classification"]] = counts.get(r["classification"], 0) + 1
        print(f"  {cat:24s}  n={len(rs):3d}  bake-stale={counts['bake-stale']:3d}  flat-by-design={counts['flat-by-design']:3d}  under-rendered={counts['under-rendered']:3d}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "version": 1,
        "metric": "M_real_weak_probe — paint+spec channel structure on neutral input",
        "size": args.size,
        "paint_threshold": PAINT_STRUCTURE_THRESHOLD,
        "spec_threshold": SPEC_STRUCTURE_THRESHOLD,
        "byCategory": results_by_cat,
    }, indent=2), encoding="utf-8")
    print()
    print(f"[probe] wrote {OUT_PATH.relative_to(V5_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
