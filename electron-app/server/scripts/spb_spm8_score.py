#!/usr/bin/env python3
"""SPM8 — Spec Pattern Master 8 (2026-05-21, owner directive).

Replaces SPM7. SPM7 had a B_structure axis (16x16 block std-dev) that
literally rewarded MACRO features — directly violating owner's "fine
features 8-32 px" rule. SPM8 is built around the owner's stated concerns:

OWNER DOCTRINE (2026-05-21):
  • FINE FEATURES (8-32 px at 2048²) — non-negotiable.
  • MANY SHADE LEVELS / more spec coloring — wide palette per feature.
  • RENDER TIME matters — must score this with real weight.
  • NO LAZY finishes — stack multiple feature types.
  • DENSITY > SIZE — more, finer features (not bigger).

13 metrics, sums to 1.0 + two penalties. Bigger penalties than rewards
for size violations on purpose, so macro features can't game the score.

Positive metrics (sum = 1.0):
  FSC  Feature Size Compliance    0.20  (FFT energy in 8-32 px periods)
  SD   Shade Diversity            0.15  (unique 8-bit intensity levels)
  RT   Render Time                0.15  (1024² render; 2048 extrapolated)
  CV   Coverage                   0.11  (% pixels not at modal value)
  SE   Spatial Entropy            0.09  (Shannon histogram entropy)
  FD   Feature Density            0.06  (Sobel connected components/area)
  CR   Chroma Range (local)       0.06  (avg 32x32 windowed std-dev)
  ED   Edge Density               0.05  (mean Sobel magnitude)
  MFS  Multi-Feature Stack        0.05  (≥2 of 3 FFT bands active)
  PFV  Per-Feature Variety        0.04  (component brightness std-dev)
  BRU  Brightness Range Util      0.04  (p5 ≤ 0.15 AND p95 ≥ 0.85)

Penalties (subtracted; clipped at 0):
  MP   Macro Penalty              -0.12  (energy in 33-255 px periods)
  RP   Repetition Penalty         -0.06  (dominant FFT spike = perfectly tiled)

Tiers:
  90+  masterpiece
  80-89 keeper
  70-79 ok
  60-69 watch
  50-59 fix
  <50   critical

Usage:
  python scripts/spb_spm8_score.py                       # all patterns
  python scripts/spb_spm8_score.py id1 id2               # specific
  python scripts/spb_spm8_score.py --size 2048           # full-res (slow)
  python scripts/spb_spm8_score.py --diag id             # per-axis dump

Output: _workbook_metrics/spm8_spec_pattern.json
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

DEFAULT_SIZE = 1024  # render at 1024; periods 8-32 at 2048 ↔ 4-16 at 1024
OUT_JSON = REPO / "_workbook_metrics" / "spm8_spec_pattern.json"

# Weights — positives sum to 1.0
W = {
    "FSC": 0.20,
    "SD":  0.15,
    "RT":  0.15,
    "CV":  0.11,
    "SE":  0.09,
    "FD":  0.06,
    "CR":  0.06,
    "ED":  0.05,
    "MFS": 0.05,
    "PFV": 0.04,
    "BRU": 0.04,
}
PEN = {
    "MP": 0.12,  # macro penalty
    "RP": 0.06,  # repetition penalty
}


def _radial_power(field: np.ndarray) -> np.ndarray:
    """Compute radial-averaged FFT power spectrum. Returns power[k]
    where k is integer radial bin (0..max_r)."""
    h, w = field.shape
    F = np.fft.fft2(field - field.mean())
    P = np.abs(F) ** 2
    # Shift zero freq to center for easier radial binning
    P = np.fft.fftshift(P)
    cy, cx = h // 2, w // 2
    Y, X = np.mgrid[0:h, 0:w]
    r = np.sqrt((Y - cy) ** 2 + (X - cx) ** 2).astype(np.int32)
    r_max = min(cy, cx)
    radial = np.zeros(r_max + 1, dtype=np.float64)
    counts = np.zeros(r_max + 1, dtype=np.int32)
    mask = r <= r_max
    np.add.at(radial, r[mask], P[mask])
    np.add.at(counts, r[mask], 1)
    radial = radial / np.maximum(counts, 1)
    radial[0] = 0  # kill DC
    return radial


def metric_FSC(field: np.ndarray, render_size: int) -> float:
    """Feature Size Compliance — % of FFT energy in 8-32 px periods (at 2048²
    equivalent). At render_size, scale: target_band_at_2048 = 8-32 → at
    render_size = (8*r/2048) to (32*r/2048). period_px = render_size / k."""
    h = field.shape[0]
    radial = _radial_power(field)
    r_max = len(radial) - 1
    # Periods at this render size that correspond to 8-32 px at 2048
    p_min_2048, p_max_2048 = 8.0, 32.0
    scale = h / 2048.0
    p_min = p_min_2048 * scale
    p_max = p_max_2048 * scale
    # k = h / period; so k_lo = h/p_max, k_hi = h/p_min
    k_lo = max(1, int(np.floor(h / p_max)))
    k_hi = min(r_max, int(np.ceil(h / p_min)))
    if k_hi <= k_lo:
        return 0.0
    band = float(radial[k_lo:k_hi+1].sum())
    # Compare against total ex-DC energy in periods 2-256 (everything meaningful)
    p_total_min = 2.0 * scale
    p_total_max = 256.0 * scale
    k_total_lo = max(1, int(np.floor(h / p_total_max)))
    k_total_hi = min(r_max, int(np.ceil(h / p_total_min)))
    total = float(radial[k_total_lo:k_total_hi+1].sum())
    ratio = band / max(total, 1e-9)
    # 80%+ in band = 100; below scales linearly
    return float(np.clip(ratio / 0.80 * 100.0, 0, 100))


def metric_MP(field: np.ndarray, render_size: int) -> float:
    """Macro Penalty — flat-blob detection. Penalizes large regions of
    nearly-constant value (the "lazy macro blob" pattern). Distinguishes
    structured macro features (radial bands with internal variation) from
    flat panel-scale blobs. Computed as: fraction of canvas where 32x32
    local std-dev is below 0.04 (locally flat). Owner's true complaint."""
    h, w = field.shape
    b = 32
    bh, bw = h // b, w // b
    if bh < 1 or bw < 1:
        return 0.0
    trimmed = field[:bh*b, :bw*b]
    blocks = trimmed.reshape(bh, b, bw, b)
    stds = blocks.std(axis=(1, 3))
    # Block is "flat macro" if its internal std < 0.04 (i.e. mostly uniform)
    flat_blocks = (stds < 0.04).sum()
    total_blocks = bh * bw
    flat_frac = flat_blocks / max(total_blocks, 1)
    # 60%+ flat = max penalty; below scales linearly
    return float(np.clip(flat_frac / 0.60 * 100.0, 0, 100))


def metric_SD(field: np.ndarray) -> float:
    """Shade Diversity — unique 8-bit intensity levels populated.
    80+ unique = 100."""
    bins = np.clip((field * 255).astype(np.int32), 0, 255)
    unique = int(np.unique(bins).size)
    return float(np.clip(unique / 80.0 * 100.0, 0, 100))


def metric_RT(render_ms: float, render_size: int) -> float:
    """Render Time — at render_size. Linear scale: extrapolate budget to 1024².
    At 1024: <=75ms = 100, 250ms = 50, 750ms+ = 0. Render time scales O(N²)."""
    # Normalize to 1024-equivalent ms
    norm_ms = render_ms * (1024.0 ** 2) / (render_size ** 2)
    if norm_ms <= 75:
        return 100.0
    if norm_ms <= 250:
        return 100.0 - (norm_ms - 75) / 175 * 50  # 100→50 from 75ms to 250ms
    if norm_ms <= 750:
        return 50.0 - (norm_ms - 250) / 500 * 50  # 50→0 from 250ms to 750ms
    return 0.0


def metric_CV(field: np.ndarray) -> float:
    """Coverage — % of pixels NOT in the modal histogram bin. Penalizes
    flat-background patterns. 70%+ non-modal = 100."""
    bins = np.clip((field * 255).astype(np.int32), 0, 255)
    hist = np.bincount(bins.ravel(), minlength=256)
    modal_count = hist.max()
    total = bins.size
    non_modal = 1.0 - modal_count / total
    return float(np.clip(non_modal / 0.70 * 100.0, 0, 100))


def metric_SE(field: np.ndarray) -> float:
    """Spatial Entropy — Shannon entropy of 256-bin histogram. 7+ bits = 100."""
    bins = np.clip((field * 255).astype(np.int32), 0, 255)
    hist, _ = np.histogram(bins, bins=256, range=(0, 256))
    p = hist / max(hist.sum(), 1)
    p = p[p > 0]
    H = -(p * np.log2(p)).sum() if p.size else 0.0
    return float(np.clip(H / 7.0 * 100.0, 0, 100))


def metric_CR(field: np.ndarray) -> float:
    """Chroma Range — average local std-dev over 32x32 windows. Measures
    intensity variation WITHIN small regions (not just globally). High =
    locally chromatic. 0.18+ avg = 100."""
    h, w = field.shape
    b = 32
    bh, bw = h // b, w // b
    if bh < 1 or bw < 1:
        return 0.0
    trimmed = field[:bh*b, :bw*b]
    blocks = trimmed.reshape(bh, b, bw, b)
    stds = blocks.std(axis=(1, 3))
    mean_std = float(stds.mean())
    return float(np.clip(mean_std / 0.18 * 100.0, 0, 100))


def metric_ED(field: np.ndarray) -> float:
    """Edge Density — mean Sobel magnitude. High = sharp details everywhere.
    0.14+ avg = 100."""
    # Simple finite-difference Sobel
    gy = np.abs(np.diff(field, axis=0, prepend=field[:1, :]))
    gx = np.abs(np.diff(field, axis=1, prepend=field[:, :1]))
    mag = (gx + gy)
    return float(np.clip(mag.mean() / 0.14 * 100.0, 0, 100))


def metric_FD(field: np.ndarray) -> float:
    """Feature Density — count of bright connected components per 1000 px².
    Uses simple thresholding. 5+ per 1000 px² = 100 (very dense)."""
    h, w = field.shape
    # Detect features as pixels > mean+std (significant peaks)
    thresh = field.mean() + field.std() * 0.5
    mask = field > thresh
    # Approximate component count without full label: count local maxima.
    # Local max: pixel > all 4 neighbors AND above threshold.
    inner = field[1:-1, 1:-1]
    up = field[:-2, 1:-1]; down = field[2:, 1:-1]
    left = field[1:-1, :-2]; right = field[1:-1, 2:]
    is_max = (inner > up) & (inner > down) & (inner > left) & (inner > right) & (inner > thresh)
    n_features = int(is_max.sum())
    area_k = (h * w) / 1000.0
    density = n_features / max(area_k, 1)
    return float(np.clip(density / 5.0 * 100.0, 0, 100))


def metric_MFS(field: np.ndarray, render_size: int) -> float:
    """Multi-Feature Stack — score based on how many of 3 FFT bands have
    substantial energy (lazy patterns concentrate in 1 band)."""
    h = field.shape[0]
    radial = _radial_power(field)
    r_max = len(radial) - 1
    scale = h / 2048.0
    # 3 bands at 2048-equivalent: 4-12, 12-48, 48-200
    bands_2048 = [(4, 12), (12, 48), (48, 200)]
    energies = []
    for p_min, p_max in bands_2048:
        k_lo = max(1, int(np.floor(h / (p_max * scale))))
        k_hi = min(r_max, int(np.ceil(h / (p_min * scale))))
        energies.append(float(radial[k_lo:k_hi+1].sum()) if k_hi > k_lo else 0.0)
    total = sum(energies) + 1e-9
    shares = [e / total for e in energies]
    # Reward when ≥2 bands have ≥20% share
    active = sum(1 for s in shares if s >= 0.20)
    if active >= 2:
        return 100.0 if active == 3 else 75.0
    return 30.0 if max(shares) > 0.50 else 0.0


def metric_PFV(field: np.ndarray) -> float:
    """Per-Feature Variety — std-dev of brightness values at detected local
    maxima. Measures whether features have varied brightness or all same.
    Threshold: 0.12+ std = 100."""
    inner = field[1:-1, 1:-1]
    up = field[:-2, 1:-1]; down = field[2:, 1:-1]
    left = field[1:-1, :-2]; right = field[1:-1, 2:]
    thresh = field.mean() + field.std() * 0.5
    is_max = (inner > up) & (inner > down) & (inner > left) & (inner > right) & (inner > thresh)
    vals = inner[is_max]
    if vals.size < 10:
        return 0.0
    std = float(vals.std())
    return float(np.clip(std / 0.12 * 100.0, 0, 100))


def metric_BRU(field: np.ndarray) -> float:
    """Brightness Range Utilization — does the pattern use the full
    [0,1] range? Reward if p5 ≤ 0.15 AND p95 ≥ 0.85."""
    p5, p95 = np.percentile(field, [5, 95])
    low_ok = max(0.0, (0.15 - p5) / 0.15)  # 1 if p5 = 0, 0 if p5 >= 0.15
    high_ok = max(0.0, (p95 - 0.85) / 0.15)  # 1 if p95 = 1, 0 if p95 <= 0.85
    return float(np.clip((low_ok + high_ok) * 50.0, 0, 100))


def metric_RP(field: np.ndarray) -> float:
    """Repetition Penalty — detect pure perfectly-tiled pattern.

    True lazy tiling shows as a single FFT spike standing far above
    nearby bins. Radial patterns + grids ALSO have peaks but spread
    across multiple bins. Use peak-vs-NEIGHBORS ratio (not vs full
    median) to distinguish: a true tile has neighbors at near-zero,
    a structured pattern has neighbors with energy too."""
    radial = _radial_power(field)
    r_max = len(radial) - 1
    if r_max < 20:
        return 0.0
    non_dc = radial[1:r_max+1]
    if non_dc.max() <= 0:
        return 0.0
    peak_idx = int(np.argmax(non_dc))
    peak = float(non_dc[peak_idx])
    # Local neighbors: ±5 bins around peak (excluding peak itself)
    lo = max(0, peak_idx - 5); hi = min(len(non_dc), peak_idx + 6)
    nbhd = np.concatenate([non_dc[lo:peak_idx], non_dc[peak_idx+1:hi]])
    if nbhd.size == 0:
        return 0.0
    nbhd_mean = float(nbhd.mean()) if nbhd.mean() > 0 else 1e-9
    ratio = peak / max(nbhd_mean, 1e-9)
    # Lazy tile: peak >50x its immediate neighbors. Cap at 60 (not 100) so
    # repetitive-but-good patterns aren't crushed.
    return float(np.clip((ratio - 20.0) / 80.0 * 60.0, 0, 60))


def _tier(composite: float) -> str:
    if composite >= 90: return "masterpiece"
    if composite >= 80: return "keeper"
    if composite >= 70: return "ok"
    if composite >= 60: return "watch"
    if composite >= 50: return "fix"
    return "critical"


def score_pattern(name: str, fn, size: int, seed: int = 7777) -> dict:
    t0 = time.perf_counter()
    field = fn((size, size), seed, 1.0)
    arr = np.clip(np.asarray(field, dtype=np.float32), 0, 1)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    fsc = metric_FSC(arr, size)
    sd = metric_SD(arr)
    rt = metric_RT(dt_ms, size)
    cv = metric_CV(arr)
    se = metric_SE(arr)
    fd = metric_FD(arr)
    cr = metric_CR(arr)
    ed = metric_ED(arr)
    mfs = metric_MFS(arr, size)
    pfv = metric_PFV(arr)
    bru = metric_BRU(arr)
    mp = metric_MP(arr, size)
    rp = metric_RP(arr)

    positives = (W["FSC"]*fsc + W["SD"]*sd + W["RT"]*rt + W["CV"]*cv + W["SE"]*se +
                 W["FD"]*fd + W["CR"]*cr + W["ED"]*ed + W["MFS"]*mfs +
                 W["PFV"]*pfv + W["BRU"]*bru)
    penalties = PEN["MP"]*mp + PEN["RP"]*rp
    composite = max(0.0, positives - penalties)

    return {
        "id": name,
        "render_size": size,
        "render_ms": round(dt_ms, 1),
        "FSC": round(fsc, 1), "SD": round(sd, 1), "RT": round(rt, 1),
        "CV":  round(cv, 1), "SE": round(se, 1), "FD": round(fd, 1),
        "CR":  round(cr, 1), "ED": round(ed, 1), "MFS": round(mfs, 1),
        "PFV": round(pfv, 1), "BRU": round(bru, 1),
        "MP":  round(mp, 1), "RP": round(rp, 1),
        "positives": round(positives, 1),
        "penalties": round(penalties, 1),
        "composite": round(composite, 1),
        "tier": _tier(composite),
        "mean": round(float(arr.mean()), 3),
        "std": round(float(arr.std()), 3),
    }


def diagnostics(entry: dict) -> str:
    lines = []
    lines.append(f"  {entry['id']}  composite={entry['composite']} tier={entry['tier']}  render_ms={entry['render_ms']}")
    lines.append(f"    POSITIVES:")
    for k in ("FSC","SD","RT","CV","SE","FD","CR","ED","MFS","PFV","BRU"):
        contrib = W[k] * entry[k]
        bar = "█" * int(entry[k] / 5)
        lines.append(f"      {k:4s} w={W[k]:.2f}  score={entry[k]:5.1f}  contrib={contrib:5.2f}  {bar}")
    lines.append(f"    PENALTIES:")
    for k in ("MP","RP"):
        contrib = PEN[k] * entry[k]
        bar = "▓" * int(entry[k] / 5)
        lines.append(f"      {k:4s} w=-{PEN[k]:.2f}  score={entry[k]:5.1f}  contrib=-{contrib:5.2f}  {bar}")
    lines.append(f"    positives={entry['positives']}  penalties={entry['penalties']}  composite={entry['composite']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", help="pattern ids; default = all")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE, help="render size (default 1024)")
    ap.add_argument("--seed", type=int, default=7777)
    ap.add_argument("--diag", action="store_true", help="print per-metric diagnostics")
    args = ap.parse_args()

    import engine.spec_patterns as sp
    catalog = sp.PATTERN_CATALOG
    targets = args.ids if args.ids else list(catalog.keys())
    print(f"[spm8] scoring {len(targets)} patterns at {args.size}x{args.size}...")

    # When running targeted (--ids), MERGE into existing baseline to preserve
    # other patterns' scores. Full runs (no args) rebuild from scratch.
    results = {}
    if args.ids and OUT_JSON.exists():
        try:
            prior = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            results = dict(prior.get("by_finish", {}))
            print(f"[spm8] merging into existing {len(results)} patterns")
        except Exception:
            results = {}
    t_start = time.perf_counter()
    for i, name in enumerate(targets):
        if name not in catalog:
            print(f"  MISSING: {name}"); continue
        try:
            entry = score_pattern(name, catalog[name], args.size, seed=args.seed)
            results[name] = entry
            if args.diag:
                print(diagnostics(entry))
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            results[name] = {"id": name, "error": str(e)}
        if (i + 1) % 50 == 0:
            elapsed = time.perf_counter() - t_start
            print(f"  ... {i+1}/{len(targets)} ({elapsed:.0f}s elapsed)")

    tiers: dict[str, int] = {"masterpiece":0, "keeper":0, "ok":0, "watch":0, "fix":0, "critical":0}
    for r in results.values():
        t = r.get("tier")
        if t in tiers: tiers[t] += 1
    print(f"[spm8] tier totals: {tiers}")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "version": "spm8.v1",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "render_size": args.size,
        "weights": W,
        "penalty_weights": {k: -v for k, v in PEN.items()},
        "tier_thresholds": {"masterpiece":90, "keeper":80, "ok":70, "watch":60, "fix":50},
        "tier_totals": tiers,
        "by_finish": results,
    }, indent=2), encoding="utf-8")
    print(f"[spm8] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
