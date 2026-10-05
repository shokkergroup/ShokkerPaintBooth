#!/usr/bin/env python3
"""SPM10 — Spec Pattern Master 10 (2026-05-26, Tick 94 weight-rebalance experiment).

DERIVED FROM scripts/spm9_score.py — IDENTICAL except for four weight deltas:

  MP  (penalty, macro pollution)        -0.10 → -0.04
  CV  (regional brightness wander)       0.04 →  0.12
  CR  (contrast richness)                0.05 →  0.00  (-0.05 to pay for CV)
  ED  (edge-direction diversity)         0.05 →  0.02  (-0.03 to pay for CV)

Rationale (from tick 92 diagnostic):
- MP penalty was too aggressive — sank sparse-but-loved patterns (paint_drip_edge,
  salt_spray_corrosion, circuit_trace, spec_caustic_light, hex_cells).
- CV is the axis that literally measures "regional warm/cool wander", i.e. the
  owner's exact "247 shades across the panel" doctrine, but only carried 0.04
  weight — drowned by CR/ED that the owner has never cited as quality dimensions.

Acceptance criterion (tick 94 charter): Spearman rho ≥ 0.50 on the same 19-pattern
overlap (round3 ∪ round5 ratings × spm9_spec_pattern.json).

Output: _workbook_metrics/spm10_spec_pattern.json
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# spm9_score reassigns sys.stdout on import, which can close our buffer.
# Work around by reopening stdout in binary mode after the import.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import os as _os
_orig_stdout_fd = _os.dup(1)
from spm9_score import (  # type: ignore  # noqa: E402
    score_pattern_pass1,
    fingerprint,
    diagnostics as _spm9_diag,
    SIM_THRESHOLD,
)
# Replace sys.stdout with a fresh writer attached to the dup'd FD.
sys.stdout = _os.fdopen(_orig_stdout_fd, "w", encoding="utf-8", errors="replace", buffering=1)

DEFAULT_SIZE = 1024
OUT_JSON = REPO / "_workbook_metrics" / "spm10_spec_pattern.json"

# === SPM10 WEIGHTS — only differences from SPM9 are: MP, CV, CR, ED ===
W = {
    "UNQ": 0.22, "SCD": 0.20, "RT": 0.13, "WOW": 0.10,
    "PFV": 0.07, "FSC": 0.07,
    "ED":  0.02,   # ← was 0.05 in SPM9
    "CR":  0.00,   # ← was 0.05 in SPM9
    "CV":  0.12,   # ← was 0.04 in SPM9
    "MFS": 0.04,
    "BRU": 0.03,
}
PEN = {
    "MP":  0.04,   # ← was 0.10 in SPM9
    "RP":  0.04,
    "SIM": 0.06,
}


def _tier(c: float) -> str:
    if c >= 90: return "masterpiece"
    if c >= 80: return "keeper"
    if c >= 70: return "ok"
    if c >= 60: return "watch"
    if c >= 50: return "fix"
    return "critical"


# Local copy of the catalog-wide pass-2 finalize using SPM10 weights.
def finalize_with_catalog(results: dict) -> None:
    names = list(results.keys())
    fps = np.stack([np.asarray(results[n]["_fp"], dtype=np.float32) for n in names], axis=0)
    norms = np.linalg.norm(fps, axis=1, keepdims=True)
    fps_n = fps / np.maximum(norms, 1e-9)
    sim = fps_n @ fps_n.T
    np.fill_diagonal(sim, -1.0)

    max_sim = sim.max(axis=1)
    unq_raw = 1.0 - max_sim
    unq_score = np.clip((unq_raw - 0.05) / 0.50 * 100.0, 0, 100)
    sim_penalty = np.where(
        max_sim > SIM_THRESHOLD,
        np.clip((max_sim - SIM_THRESHOLD) / (1.0 - SIM_THRESHOLD) * 100.0, 0, 100),
        0.0,
    )
    sorted_unq = np.sort(unq_score)
    unq_rank = np.searchsorted(sorted_unq, unq_score) / max(len(unq_score) - 1, 1) * 100.0

    for i, n in enumerate(names):
        r = results[n]
        unq = float(unq_score[i])
        wow = float(np.clip(unq_rank[i] * 0.40 + r["CR"] * 0.30 + r["SCD"] * 0.30, 0, 100))

        r["UNQ"] = round(unq, 1)
        r["WOW"] = round(wow, 1)
        r["_max_sim_to"] = names[int(np.argmax(sim[i]))]
        r["_max_sim"] = round(float(max_sim[i]), 3)
        r["SIM"] = round(float(sim_penalty[i]), 1)

        positives = (
            W["UNQ"]*r["UNQ"] + W["SCD"]*r["SCD"] + W["RT"]*r["RT"] + W["WOW"]*r["WOW"] +
            W["PFV"]*r["PFV"] + W["FSC"]*r["FSC"] + W["ED"]*r["ED"] + W["CR"]*r["CR"] +
            W["CV"]*r["CV"] + W["MFS"]*r["MFS"] + W["BRU"]*r["BRU"]
        )
        penalties = PEN["MP"]*r["MP"] + PEN["RP"]*r["RP"] + PEN["SIM"]*r["SIM"]
        composite = max(0.0, positives - penalties)

        r["positives"] = round(positives, 1)
        r["penalties"] = round(penalties, 1)
        r["composite"] = round(composite, 1)
        r["tier"] = _tier(composite)
        r.pop("_fp", None)


def fast_path_from_spm9(spm9_json: Path) -> dict:
    """Re-use SPM9's raw axis scores + fingerprints — only re-weight, no re-render.
    This is valid because SPM10 changes ONLY weights, not axis definitions."""
    data = json.loads(spm9_json.read_text(encoding="utf-8"))
    by = data.get("by_finish", {})
    fp_cache_path = spm9_json.with_suffix(".fp_cache.json")
    fp_cache = json.loads(fp_cache_path.read_text(encoding="utf-8")) if fp_cache_path.exists() else {}

    results: dict = {}
    for name, entry in by.items():
        if "SCD" not in entry:  # errored row, skip
            continue
        r = dict(entry)
        r.pop("UNQ", None); r.pop("WOW", None); r.pop("SIM", None)
        r.pop("composite", None); r.pop("tier", None)
        r.pop("positives", None); r.pop("penalties", None)
        r.pop("_max_sim", None); r.pop("_max_sim_to", None)
        if name in fp_cache:
            r["_fp"] = fp_cache[name]
        else:
            # No fingerprint cached → skip (rare; would require full re-render)
            continue
        results[name] = r
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE)
    ap.add_argument("--seed", type=int, default=7777)
    ap.add_argument("--from-spm9", action="store_true", default=True,
                    help="Re-use SPM9 axis scores + fingerprints (only re-weight). DEFAULT.")
    ap.add_argument("--full-rescore", action="store_true",
                    help="Force full re-render. Slow; not needed for weight-only changes.")
    args = ap.parse_args()

    spm9_json = REPO / "_workbook_metrics" / "spm9_spec_pattern.json"

    if args.full_rescore or not spm9_json.exists():
        # Full re-render path (rarely used; SPM10 axes are identical to SPM9 so
        # numerically this gives the same per-axis numbers).
        import engine.spec_patterns as sp
        catalog = sp.PATTERN_CATALOG
        targets = args.ids if args.ids else list(catalog.keys())
        print(f"[spm10] FULL re-render of {len(targets)} patterns at {args.size}x{args.size}...")
        results: dict = {}
        t_start = time.perf_counter()
        for i, name in enumerate(targets):
            if name not in catalog:
                print(f"  MISSING: {name}"); continue
            try:
                results[name] = score_pattern_pass1(name, catalog[name], args.size, seed=args.seed)
            except Exception as e:
                print(f"  ERROR {name}: {e}")
            if (i + 1) % 50 == 0:
                print(f"  ... {i+1}/{len(targets)} ({time.perf_counter()-t_start:.0f}s)")
    else:
        print(f"[spm10] fast path: re-weight SPM9 axes from {spm9_json.name}")
        results = fast_path_from_spm9(spm9_json)
        if args.ids:
            results = {n: r for n, r in results.items() if n in args.ids}
        print(f"[spm10] re-weighting {len(results)} patterns")

    finalize_targets = {n: r for n, r in results.items() if "_fp" in r}
    print(f"[spm10] pass 2: catalog-wide UNQ/WOW/SIM over {len(finalize_targets)} patterns...")
    finalize_with_catalog(finalize_targets)
    for n, r in finalize_targets.items():
        results[n] = r

    tiers: dict = {"masterpiece":0, "keeper":0, "ok":0, "watch":0, "fix":0, "critical":0}
    for r in results.values():
        t = r.get("tier")
        if t in tiers: tiers[t] += 1
    print(f"[spm10] tier totals: {tiers}")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "version": "spm10.v1",
        "derived_from": "spm9.v1",
        "weight_deltas_vs_spm9": {
            "MP_penalty": {"spm9": -0.10, "spm10": -0.04},
            "CV":         {"spm9":  0.04, "spm10":  0.12},
            "CR":         {"spm9":  0.05, "spm10":  0.00},
            "ED":         {"spm9":  0.05, "spm10":  0.02},
        },
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "render_size": args.size,
        "weights": W,
        "penalty_weights": {k: -v for k, v in PEN.items()},
        "sim_threshold": SIM_THRESHOLD,
        "tier_thresholds": {"masterpiece":90, "keeper":80, "ok":70, "watch":60, "fix":50},
        "tier_totals": tiers,
        "by_finish": results,
    }, indent=2), encoding="utf-8")
    print(f"[spm10] wrote {OUT_JSON}")

    # Also produce a .js mirror (SPM9 doesn't have one but this is cheap and the
    # workbook may eventually consume it the same way M9 is consumed).
    js_path = OUT_JSON.with_suffix(".js")
    js_path.write_text(
        "// Auto-generated by scripts/spb_spm10_score.py — do not hand-edit.\n"
        "window.SPB_SPM10 = " + json.dumps({
            "by_finish": results,
            "weights": W,
            "tier_totals": tiers,
            "version": "spm10.v1",
        }) + ";\n",
        encoding="utf-8",
    )
    print(f"[spm10] wrote {js_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
