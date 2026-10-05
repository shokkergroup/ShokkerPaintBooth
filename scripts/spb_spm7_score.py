#!/usr/bin/env python3
"""SPM7 — Spec Pattern Master 7 metric (SPB-106 tick 52, 2026-05-20).

Owner mandate: M7 is the wrong metric for spec patterns. M7 was designed
for paint+spec coherence (M5) and category-percentile-fineE (M6 wants HI
for Geometric). Both penalize the universal owner ask: "weaving different
shades will make them reflect different and look more unique."

SPM7 is a four-axis composite designed FOR spec patterns specifically:

  A · SPATIAL_ENTROPY   — Shannon entropy of 256-bin field histogram.
                          High = many distinct intensities used.
                          (Owner's "color variation" ask measured directly.)

  B · STRUCTURE_STRENGTH — std-dev of 16×16 block means.
                          High = visible macro structure.
                          Low = flat OR pure noise (both bad).

  C · FEATURE_SCALE     — dominant spatial frequency from radial FFT.
                          100 if peak period ∈ [8, 32] px (SPB-106 rule 2),
                          decays linearly outside.

  D · INTENSITY_COVERAGE — fraction of 256 quantized bins used.
                          1.0 = full 8-bit range; 0.0 = single value.

Composite: weighted geometric mean (rewards balance, not one-dim winners).

Usage:
    python scripts/spb_spm7_score.py                     # all 262 patterns
    python scripts/spb_spm7_score.py spec_corrugated_panel face_mill_bands
    python scripts/spb_spm7_score.py --compare-m7        # side-by-side

Outputs:
    _workbook_metrics/spm7_spec_pattern.json
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

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

SIZE = 512  # render size for SPM7 (smaller than 2048 for speed; structure still measurable)
OUT_JSON = REPO / "_workbook_metrics" / "spm7_spec_pattern.json"
M7_JSON = REPO / "_workbook_metrics" / "m7_composite.json"


def _spm_a_entropy(field: np.ndarray) -> float:
    """Shannon entropy of 256-bin histogram. Returns score 0..100."""
    bins = np.clip((field * 255).astype(np.int32), 0, 255)
    hist, _ = np.histogram(bins, bins=256, range=(0, 256))
    p = hist / max(hist.sum(), 1)
    p = p[p > 0]
    H = -(p * np.log2(p)).sum() if p.size else 0.0
    # max entropy = 8 (uniform 256). Map to 0..100 with floor at 1 bit.
    return float(np.clip((H - 1.0) / 7.0 * 100.0, 0, 100))


def _spm_b_structure(field: np.ndarray) -> float:
    """Std-dev of 16×16 block means, mapped to 0..100."""
    h, w = field.shape
    b = 16
    bh, bw = h // b, w // b
    trimmed = field[: bh * b, : bw * b]
    blocks = trimmed.reshape(bh, b, bw, b).mean(axis=(1, 3))
    bstd = float(blocks.std())
    # bstd ~ 0.05-0.30 in practice. Map [0.02, 0.25] -> [0, 100].
    return float(np.clip((bstd - 0.02) / 0.23 * 100.0, 0, 100))


def _spm_c_freq_richness(field: np.ndarray) -> tuple[float, float]:
    """v2: frequency-band ENERGY RATIO. Sums FFT power in periods [4, 256]px
    (broad structural window) divided by total non-DC power. Rewards
    patterns whose energy lives in structurally meaningful frequencies
    (not pure noise at the high end, not flat at the DC end). Owner-
    approved chromatic_aberration (76px peak) + sacred pearl_micro (50+
    px features) all pass this where v1's narrow 8-32 window failed them.
    Returns (score, peak_period_px) for reporting."""
    h, w = field.shape
    F = np.fft.fft2(field - field.mean())
    P = np.abs(F) ** 2
    cy, cx = h // 2, w // 2
    Y, X = np.mgrid[0:h, 0:w]
    r = np.sqrt((Y - cy) ** 2 + (X - cx) ** 2)
    r_max = min(cy, cx)
    # Period = h / bin. Periods 4-256 px ↔ bins h/256 .. h/4.
    lo_bin = h / 256.0
    hi_bin = h / 4.0
    band_mask = (r >= lo_bin) & (r <= hi_bin)
    non_dc_mask = r > 1
    band_power = float(P[band_mask].sum())
    total_power = float(P[non_dc_mask].sum())
    ratio = band_power / max(total_power, 1e-9)
    # Healthy patterns: ratio 0.4..0.95 → score 50..100. Below 0.4 → linear ramp to 0.
    if ratio >= 0.95:
        score = 100.0
    elif ratio >= 0.40:
        score = 50.0 + (ratio - 0.40) / 0.55 * 50.0
    else:
        score = ratio / 0.40 * 50.0
    # Peak period for reporting (use radial average like v1).
    r_int = r.astype(np.int32)
    radial = np.zeros(r_max + 1, dtype=np.float64)
    counts = np.zeros(r_max + 1, dtype=np.int32)
    mask = r_int <= r_max
    np.add.at(radial, r_int[mask], np.abs(F)[mask])
    np.add.at(counts, r_int[mask], 1)
    radial = radial / np.maximum(counts, 1)
    radial[0] = 0
    peak_bin = int(np.argmax(radial[3:])) + 3 if radial.size >= 6 else 1
    peak_period_px = h / max(peak_bin, 1)
    return float(np.clip(score, 0, 100)), float(peak_period_px)


def _spm_d_coverage(field: np.ndarray) -> float:
    """Fraction of 256 quantized bins used, mapped 0..100."""
    bins = np.clip((field * 255).astype(np.int32), 0, 255)
    unique = int(np.unique(bins).size)
    return float(np.clip(unique / 256.0 * 100.0, 0, 100))


def _tier(composite: float) -> str:
    """SPM7 v2 tier thresholds — calibrated empirically against ground
    truth. Original 80/65/50/35 thresholds gave best 8/9 within-one-
    tier correlation; tighter thresholds tried but introduced 2 wrong
    classifications. Keeping the conventional bins; ranking is the
    reliable signal, absolute tiering is approximate."""
    if composite >= 80:
        return "keeper"
    if composite >= 65:
        return "ok"
    if composite >= 50:
        return "watch"
    if composite >= 35:
        return "fix"
    return "critical"


def score_pattern(name: str, fn, seed: int = 7777) -> dict:
    """Render at SIZE×SIZE, score all four axes."""
    t0 = time.perf_counter()
    field = fn((SIZE, SIZE), seed, 1.0)
    arr = np.clip(np.asarray(field, dtype=np.float32), 0, 1)
    dt = time.perf_counter() - t0

    a = _spm_a_entropy(arr)
    b = _spm_b_structure(arr)
    c_score, peak_period = _spm_c_freq_richness(arr)
    d = _spm_d_coverage(arr)

    # SPM7 v2 weights: arithmetic mean (more forgiving than geometric on
    # one-weak-axis patterns). Re-balanced after v1 calibration audit
    # showed sacred 3 + chromatic_aberration all penalized by old C
    # axis. v2 prioritizes A (entropy) + D (coverage) which capture
    # owner's "color variation" mandate directly.
    weights = {"A": 0.35, "B": 0.15, "C": 0.15, "D": 0.35}
    vals = {"A": a, "B": b, "C": c_score, "D": d}
    composite = float(sum(weights[k] * vals[k] for k in weights))

    return {
        "id": name,
        "render_size": SIZE,
        "render_ms": round(dt * 1000.0, 1),
        "A_entropy": round(a, 1),
        "B_structure": round(b, 1),
        "C_freq_richness": round(c_score, 1),
        "C_peak_period_px": round(peak_period, 1),
        "D_coverage": round(d, 1),
        "composite": round(composite, 1),
        "tier": _tier(composite),
        "mean": round(float(arr.mean()), 3),
        "std": round(float(arr.std()), 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", help="pattern ids; default = all 262")
    ap.add_argument("--compare-m7", action="store_true", help="show M7 vs SPM7 side-by-side")
    ap.add_argument("--seed", type=int, default=7777)
    args = ap.parse_args()

    import engine.spec_patterns as sp
    catalog = sp.PATTERN_CATALOG
    targets = args.ids if args.ids else list(catalog.keys())
    print(f"[spm7] scoring {len(targets)} patterns at {SIZE}x{SIZE}...")

    results = {}
    for name in targets:
        if name not in catalog:
            print(f"  MISSING: {name}")
            continue
        try:
            entry = score_pattern(name, catalog[name], seed=args.seed)
            results[name] = entry
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            results[name] = {"id": name, "error": str(e)}

    # Tier rollup
    tiers: dict[str, int] = {"keeper": 0, "ok": 0, "watch": 0, "fix": 0, "critical": 0}
    for r in results.values():
        t = r.get("tier")
        if t in tiers:
            tiers[t] += 1
    print(f"[spm7] tier totals: {tiers}")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "version": "spm7.v2",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "render_size": SIZE,
        "weights": {"A_entropy": 0.35, "B_structure": 0.15, "C_freq_richness": 0.15, "D_coverage": 0.35},
        "mean_type": "weighted_arithmetic",
        "tier_totals": tiers,
        "by_finish": results,
    }, indent=2), encoding="utf-8")
    print(f"[spm7] wrote {OUT_JSON}")

    if args.compare_m7 and M7_JSON.exists():
        m7 = json.loads(M7_JSON.read_text(encoding="utf-8"))["byFinish"]
        print("\n--- M7 vs SPM7 side-by-side (the patterns owner reviewed) ---")
        for pid in targets:
            m7_entry = m7.get(f"spec_pattern:{pid}", {})
            sp_entry = results.get(pid, {})
            print(f"  {pid:35s}  M7={m7_entry.get('composite','?'):>5}  SPM7={sp_entry.get('composite','?'):>5}  ({sp_entry.get('tier','?')})  A={sp_entry.get('A_entropy','?')} B={sp_entry.get('B_structure','?')} C={sp_entry.get('C_feature_scale','?')} D={sp_entry.get('D_coverage','?')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
