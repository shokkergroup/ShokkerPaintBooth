#!/usr/bin/env python3
"""SPM9 — Spec Pattern Master 9 (2026-05-23, owner directive — REJECT THE RECIPE).

Replaces SPM8. SPM8 was driving Claude to apply the same 5-primitive stack
(BRU mask + palette-disc + hairlines + dark dots + flecks) to every weak
pattern, optimizing the numerical axes while flattening visual identity.
Owner verdict (2026-05-23): "they look exactly the fucking same".

SPM9 is built around the OWNER'S FOUR PILLARS:

  1. UNIQUENESS / WEIRDNESS — how unlike every other pattern is this one?
  2. SPEC COLOR DIVERSITY — many shades, continuous depth, NOT 8-tier picks
  3. RENDER TIME — speed matters but isn't worth a generic finish
  4. WOW FACTOR — would this finish alone in a YouTube clip sell a copy?

Implemented as 12 axes (11 positive, 3 penalty), with a CATALOG-WIDE
similarity calculation that explicitly punishes recipe-stamping. Computing
UNQ and the SIM penalty requires a fingerprint vector per pattern — those
are stored in the result JSON so we can rebuild the similarity matrix
cheaply for partial reruns.

WEIGHTS (positives sum = 1.00):
  UNQ  Uniqueness               0.22
  SCD  Spec Color Diversity     0.20
  RT   Render Time              0.13
  WOW  Wow Factor               0.10
  PFV  Per-Feature Variance     0.07
  FSC  Fine-Scale Content       0.07
  ED   Edge-Direction Diversity 0.05
  CR   Contrast Richness        0.05
  CV   Chroma/Regional-Variation 0.04
  MFS  Multi-Feature Scale      0.04
  BRU  Brightness Range Use     0.03

PENALTIES (subtracted, clipped to 0):
  MP   Macro Pollution          -0.10  (energy in >32 px features)
  RP   Repetitive Periodicity   -0.04  (sharp FFT spike)
  SIM  Catalog Similarity       -0.06  (>0.85 cosine sim to another finish)

Tiers (composite 0-100):
  90+  masterpiece
  80-89 keeper
  70-79 ok
  60-69 watch
  50-59 fix
  <50   critical

Usage:
  python scripts/spm9_score.py                # all patterns
  python scripts/spm9_score.py id1 id2        # specific
  python scripts/spm9_score.py --diag id      # per-axis dump
  python scripts/spm9_score.py --size 2048    # full-res

Output: _workbook_metrics/spm9_spec_pattern.json
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

DEFAULT_SIZE = 1024
OUT_JSON = REPO / "_workbook_metrics" / "spm9_spec_pattern.json"

W = {
    "UNQ": 0.22, "SCD": 0.20, "RT": 0.13, "WOW": 0.10,
    "PFV": 0.07, "FSC": 0.07,
    "ED":  0.05, "CR":  0.05,
    "CV":  0.04, "MFS": 0.04,
    "BRU": 0.03,
}
PEN = {"MP": 0.10, "RP": 0.04, "SIM": 0.06}
SIM_THRESHOLD = 0.85  # cosine similarity above this triggers the SIM penalty

# ----------------------------------------------------------------------------
# Shared FFT helper
# ----------------------------------------------------------------------------

def _radial_power(field: np.ndarray) -> np.ndarray:
    h, w = field.shape
    F = np.fft.fft2(field - field.mean())
    P = np.fft.fftshift(np.abs(F) ** 2)
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
    radial[0] = 0
    return radial


# ----------------------------------------------------------------------------
# Fingerprint — used by UNQ, WOW, and the SIM penalty
# Returns a fixed-length unit-norm vector that's stable for identical inputs
# and discriminative against the recipe stamp.
# ----------------------------------------------------------------------------

def fingerprint(field: np.ndarray) -> np.ndarray:
    h, w = field.shape
    # 1) Brightness histogram (32 bins) — captures the spec coloring distribution
    bins32 = np.clip((field * 32).astype(np.int32), 0, 31)
    hist = np.bincount(bins32.ravel(), minlength=32).astype(np.float64)
    hist = hist / max(hist.sum(), 1)

    # 2) Radial FFT power, log-binned into 16 bins. Captures the spatial-frequency
    #    signature — recipe-stamped patterns share a very specific FFT shape.
    radial = _radial_power(field)
    r_max = len(radial) - 1
    if r_max < 16:
        fft_bins = np.zeros(16, dtype=np.float64)
    else:
        log_edges = np.linspace(np.log(1.5), np.log(r_max), 17)
        edges = np.exp(log_edges).astype(int).clip(1, r_max)
        fft_bins = np.array([radial[edges[i]:edges[i+1]+1].mean() if edges[i+1]>edges[i] else 0 for i in range(16)])
        s = fft_bins.sum()
        if s > 0:
            fft_bins = fft_bins / s

    # 3) Edge-orientation histogram (8 bins). Sobel-magnitude angles.
    gy = field[1:, :] - field[:-1, :]
    gx = field[:, 1:] - field[:, :-1]
    # Crop to common shape
    g_h = min(gy.shape[0], gx.shape[0])
    g_w = min(gy.shape[1], gx.shape[1])
    gy_c = gy[:g_h, :g_w]; gx_c = gx[:g_h, :g_w]
    mag = np.sqrt(gx_c*gx_c + gy_c*gy_c)
    ang = np.arctan2(gy_c, gx_c)  # -pi..pi
    # Bin into 8 directions, weight by magnitude
    strong = mag > (mag.mean() + mag.std() * 0.5)
    if strong.any():
        a = ang[strong]
        m = mag[strong]
        bidx = ((a + np.pi) / (2*np.pi) * 8).astype(int).clip(0, 7)
        edge_hist = np.bincount(bidx, weights=m, minlength=8).astype(np.float64)
        s = edge_hist.sum()
        if s > 0:
            edge_hist = edge_hist / s
    else:
        edge_hist = np.zeros(8, dtype=np.float64)

    # 4) Local-contrast distribution (16 bins of 32x32 window std-dev).
    #    Recipe-stamped patterns have very specific local-contrast profiles.
    b = 32
    bh, bw = h // b, w // b
    if bh >= 1 and bw >= 1:
        trimmed = field[:bh*b, :bw*b]
        blocks = trimmed.reshape(bh, b, bw, b).std(axis=(1,3)).ravel()
        std_hist, _ = np.histogram(blocks, bins=16, range=(0, 0.40))
        std_hist = std_hist.astype(np.float64)
        std_hist = std_hist / max(std_hist.sum(), 1)
    else:
        std_hist = np.zeros(16, dtype=np.float64)

    # 5) Scalar summary block (8 dims). Independent signals to ensure
    #    fingerprints differ even when histogram & FFT look similar.
    p = hist[hist > 0]
    bright_entropy = -(p * np.log2(p)).sum() / np.log2(32) if p.size else 0.0
    p2 = std_hist[std_hist > 0]
    contrast_entropy = -(p2 * np.log2(p2)).sum() / np.log2(16) if p2.size else 0.0
    p3 = edge_hist[edge_hist > 0]
    edge_entropy = -(p3 * np.log2(p3)).sum() / np.log2(8) if p3.size else 0.0
    summary = np.array([
        float(field.mean()),
        float(field.std()),
        float(np.percentile(field, 95) - np.percentile(field, 5)),
        float((field > 0.5).mean()),
        float(mag.mean()),
        bright_entropy,
        contrast_entropy,
        edge_entropy,
    ], dtype=np.float64)

    # Concat into one vector. Each section is already normalized so their
    # combined L2 norm is comparable.
    fp = np.concatenate([hist, fft_bins, edge_hist, std_hist, summary])
    n = np.linalg.norm(fp)
    if n > 0:
        fp = fp / n
    return fp.astype(np.float32)


# ----------------------------------------------------------------------------
# Per-pattern axes (NOT requiring catalog-wide info)
# ----------------------------------------------------------------------------

def metric_SCD(field: np.ndarray) -> float:
    """Spec Color Diversity. Rewards continuous shading and punishes the
    8-tier-pick fingerprint. Three components, averaged:
      a) effective brightness entropy (256-bin Shannon, normalized to 8 bits)
      b) count of histogram bins with >=0.05% pixel mass (out of 256)
      c) flatness vs 8-peak signature — penalty if too much mass concentrates
         in <=8 narrow bins.
    """
    bins = np.clip((field * 255).astype(np.int32), 0, 255)
    hist = np.bincount(bins.ravel(), minlength=256).astype(np.float64)
    total = hist.sum()
    p = hist / max(total, 1)
    nz = p[p > 0]
    H = -(nz * np.log2(nz)).sum() if nz.size else 0.0
    entropy_score = float(np.clip(H / 7.0 * 100.0, 0, 100))

    # Populated bins (>=0.05% of pixels)
    thresh = max(1, int(total * 0.0005))
    populated = int((hist >= thresh).sum())
    populated_score = float(np.clip(populated / 80.0 * 100.0, 0, 100))

    # n-Tier penalty: does the top-K mass concentrate in <=8 bins?
    sorted_hist = np.sort(hist)[::-1]
    top8_share = sorted_hist[:8].sum() / max(total, 1)
    # >0.75 share in top 8 bins = lazy palette; <0.30 = rich shading
    tier_penalty = float(np.clip((top8_share - 0.30) / 0.45 * 100.0, 0, 100))
    tier_score = 100.0 - tier_penalty  # 100 = good (rich), 0 = bad (8-tier)

    return float(np.mean([entropy_score, populated_score, tier_score]))


def metric_RT(render_ms: float, render_size: int) -> float:
    """Render Time score. Normalize to 1024² equivalent."""
    norm_ms = render_ms * (1024.0 ** 2) / (render_size ** 2)
    if norm_ms <= 75:
        return 100.0
    if norm_ms <= 250:
        return 100.0 - (norm_ms - 75) / 175 * 50
    if norm_ms <= 750:
        return 50.0 - (norm_ms - 250) / 500 * 50
    return 0.0


def metric_PFV(field: np.ndarray) -> float:
    """Per-Feature Variance — std-dev of brightness AT detected local maxima.
    Same formula as SPM8 PFV, doubled weight (this axis is now my friend)."""
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


def metric_FSC(field: np.ndarray, render_size: int) -> float:
    """Fine-Scale Content — FFT power in 8-32 px doctrine band (at 2048²
    equivalent). Halved weight vs SPM8."""
    h = field.shape[0]
    radial = _radial_power(field)
    r_max = len(radial) - 1
    scale = h / 2048.0
    p_min, p_max = 8.0 * scale, 32.0 * scale
    k_lo = max(1, int(np.floor(h / p_max)))
    k_hi = min(r_max, int(np.ceil(h / p_min)))
    if k_hi <= k_lo:
        return 0.0
    band = float(radial[k_lo:k_hi+1].sum())
    p_total_max = 256.0 * scale
    k_total_lo = max(1, int(np.floor(h / p_total_max)))
    k_total_hi = min(r_max, int(np.ceil(h / (2.0 * scale))))
    total = float(radial[k_total_lo:k_total_hi+1].sum())
    ratio = band / max(total, 1e-9)
    return float(np.clip(ratio / 0.70 * 100.0, 0, 100))


def metric_ED(field: np.ndarray) -> float:
    """Edge-Direction Diversity — entropy of 8-bin orientation histogram."""
    gy = field[1:, :] - field[:-1, :]
    gx = field[:, 1:] - field[:, :-1]
    g_h = min(gy.shape[0], gx.shape[0])
    g_w = min(gy.shape[1], gx.shape[1])
    gy_c = gy[:g_h, :g_w]; gx_c = gx[:g_h, :g_w]
    mag = np.sqrt(gx_c*gx_c + gy_c*gy_c)
    if mag.std() < 1e-6:
        return 0.0
    strong = mag > (mag.mean() + mag.std() * 0.5)
    if not strong.any():
        return 0.0
    ang = np.arctan2(gy_c, gx_c)
    a = ang[strong]; m = mag[strong]
    bidx = ((a + np.pi) / (2*np.pi) * 8).astype(int).clip(0, 7)
    edge_hist = np.bincount(bidx, weights=m, minlength=8).astype(np.float64)
    edge_hist = edge_hist / max(edge_hist.sum(), 1)
    p = edge_hist[edge_hist > 0]
    H = -(p * np.log2(p)).sum() if p.size else 0.0
    # max entropy on 8 bins = 3 bits. Reward >=2.4 bits = 100.
    return float(np.clip(H / 2.4 * 100.0, 0, 100))


def metric_CR(field: np.ndarray) -> float:
    """Contrast Richness — p99-p01 dynamic range AND count of distinct mid-tone
    bins (not just dark+bright). Catches the BRU=100 mask-injected fakes."""
    p01, p99 = np.percentile(field, [1, 99])
    spread = p99 - p01
    spread_score = float(np.clip((spread - 0.40) / 0.40 * 100.0, 0, 100))
    bins = np.clip((field * 255).astype(np.int32), 0, 255)
    hist = np.bincount(bins.ravel(), minlength=256).astype(np.float64)
    total = hist.sum()
    # Count populated mid-tone bins (0.15-0.85 range = bins 38..217)
    mid = hist[38:218]
    midpop = int((mid >= total * 0.0005).sum())
    mid_score = float(np.clip(midpop / 60.0 * 100.0, 0, 100))
    return float(np.mean([spread_score, mid_score]))


def metric_CV(field: np.ndarray) -> float:
    """Regional brightness wander — variance of 64x64 sliding-window means.
    This is the 'tint multiplier' axis. If mean over 64x64 windows is constant,
    the field has no regional warm/cool variation — boring."""
    h, w = field.shape
    b = 64
    bh, bw = h // b, w // b
    if bh < 2 or bw < 2:
        return 0.0
    trimmed = field[:bh*b, :bw*b]
    means = trimmed.reshape(bh, b, bw, b).mean(axis=(1,3))
    wander = float(means.std())
    # Range 0.02 = no wander, 0.10 = strong regional variation
    return float(np.clip((wander - 0.02) / 0.08 * 100.0, 0, 100))


def metric_MFS(field: np.ndarray, render_size: int) -> float:
    h = field.shape[0]
    radial = _radial_power(field)
    r_max = len(radial) - 1
    scale = h / 2048.0
    bands_2048 = [(4, 12), (12, 48), (48, 200)]
    energies = []
    for p_min, p_max in bands_2048:
        k_lo = max(1, int(np.floor(h / (p_max * scale))))
        k_hi = min(r_max, int(np.ceil(h / (p_min * scale))))
        energies.append(float(radial[k_lo:k_hi+1].sum()) if k_hi > k_lo else 0.0)
    total = sum(energies) + 1e-9
    shares = [e / total for e in energies]
    active = sum(1 for s in shares if s >= 0.20)
    if active >= 2:
        return 100.0 if active == 3 else 75.0
    return 30.0 if max(shares) > 0.50 else 0.0


def metric_BRU(field: np.ndarray) -> float:
    p5, p95 = np.percentile(field, [5, 95])
    low_ok = max(0.0, (0.15 - p5) / 0.15)
    high_ok = max(0.0, (p95 - 0.85) / 0.15)
    return float(np.clip((low_ok + high_ok) * 50.0, 0, 100))


def metric_MP(field: np.ndarray, render_size: int) -> float:
    h, w = field.shape
    b = 32
    bh, bw = h // b, w // b
    if bh < 1 or bw < 1:
        return 0.0
    trimmed = field[:bh*b, :bw*b]
    blocks = trimmed.reshape(bh, b, bw, b)
    stds = blocks.std(axis=(1, 3))
    flat_frac = (stds < 0.04).sum() / max(stds.size, 1)
    return float(np.clip(flat_frac / 0.60 * 100.0, 0, 100))


def metric_RP(field: np.ndarray) -> float:
    radial = _radial_power(field)
    r_max = len(radial) - 1
    if r_max < 20:
        return 0.0
    non_dc = radial[1:r_max+1]
    if non_dc.max() <= 0:
        return 0.0
    peak_idx = int(np.argmax(non_dc))
    peak = float(non_dc[peak_idx])
    lo = max(0, peak_idx - 5); hi = min(len(non_dc), peak_idx + 6)
    nbhd = np.concatenate([non_dc[lo:peak_idx], non_dc[peak_idx+1:hi]])
    if nbhd.size == 0:
        return 0.0
    nbhd_mean = float(nbhd.mean()) if nbhd.mean() > 0 else 1e-9
    ratio = peak / max(nbhd_mean, 1e-9)
    return float(np.clip((ratio - 20.0) / 80.0 * 60.0, 0, 60))


def _tier(c: float) -> str:
    if c >= 90: return "masterpiece"
    if c >= 80: return "keeper"
    if c >= 70: return "ok"
    if c >= 60: return "watch"
    if c >= 50: return "fix"
    return "critical"


# ----------------------------------------------------------------------------
# Per-pattern scoring (without catalog-wide UNQ/SIM/WOW — those are pass 2)
# ----------------------------------------------------------------------------

def score_pattern_pass1(name: str, fn, size: int, seed: int = 7777) -> dict:
    t0 = time.perf_counter()
    field = fn((size, size), seed, 1.0)
    raw = np.clip(np.asarray(field, dtype=np.float32), 0, 1)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    # 3-channel (h,w,3) patterns: collapse to luminance for legacy axes;
    # mark in result so downstream tooling can show channel coverage too.
    if raw.ndim == 3 and raw.shape[2] >= 3:
        arr = raw[:, :, :3].mean(axis=2).astype(np.float32)
        channels = 3
    else:
        arr = raw
        channels = 1

    fp = fingerprint(arr)
    scd = metric_SCD(arr)
    rt = metric_RT(dt_ms, size)
    pfv = metric_PFV(arr)
    fsc = metric_FSC(arr, size)
    ed = metric_ED(arr)
    cr = metric_CR(arr)
    cv = metric_CV(arr)
    mfs = metric_MFS(arr, size)
    bru = metric_BRU(arr)
    mp = metric_MP(arr, size)
    rp = metric_RP(arr)

    out = {
        "id": name,
        "render_size": size,
        "render_ms": round(dt_ms, 1),
        "channels": channels,
        "SCD": round(scd, 1),
        "RT":  round(rt, 1),
        "PFV": round(pfv, 1),
        "FSC": round(fsc, 1),
        "ED":  round(ed, 1),
        "CR":  round(cr, 1),
        "CV":  round(cv, 1),
        "MFS": round(mfs, 1),
        "BRU": round(bru, 1),
        "MP":  round(mp, 1),
        "RP":  round(rp, 1),
        "_fp": fp.tolist(),  # stored for pass 2; stripped from final JSON
        "mean": round(float(arr.mean()), 3),
        "std":  round(float(arr.std()), 3),
    }
    if channels == 3:
        # Per-channel means for owner visibility
        out["M_mean"] = round(float(raw[:, :, 0].mean()), 3)
        out["R_mean"] = round(float(raw[:, :, 1].mean()), 3)
        out["CC_mean"] = round(float(raw[:, :, 2].mean()), 3)
        out["M_std"] = round(float(raw[:, :, 0].std()), 3)
        out["R_std"] = round(float(raw[:, :, 1].std()), 3)
        out["CC_std"] = round(float(raw[:, :, 2].std()), 3)
    return out


# ----------------------------------------------------------------------------
# Pass 2 — fill in UNQ, WOW, and SIM penalty using cross-pattern similarity
# ----------------------------------------------------------------------------

def finalize_with_catalog(results: dict[str, dict]) -> None:
    """In-place pass 2: compute UNQ, WOW, SIM, composite, tier."""
    names = list(results.keys())
    # Build fingerprint matrix
    fps = np.stack([np.asarray(results[n]["_fp"], dtype=np.float32) for n in names], axis=0)
    # Cosine similarity matrix
    norms = np.linalg.norm(fps, axis=1, keepdims=True)
    fps_n = fps / np.maximum(norms, 1e-9)
    sim = fps_n @ fps_n.T  # n x n
    np.fill_diagonal(sim, -1.0)  # ignore self

    # UNQ score: 1 - max similarity to any OTHER pattern.
    max_sim = sim.max(axis=1)
    # Map similarity into a 0-100 score. 0.50 sim → 100, 0.95 sim → 0.
    unq_raw = 1.0 - max_sim
    unq_score = np.clip((unq_raw - 0.05) / 0.50 * 100.0, 0, 100)

    # SIM penalty: only triggers if max_sim > SIM_THRESHOLD.
    sim_penalty = np.where(
        max_sim > SIM_THRESHOLD,
        np.clip((max_sim - SIM_THRESHOLD) / (1.0 - SIM_THRESHOLD) * 100.0, 0, 100),
        0.0,
    )

    # Build a percentile rank of UNQ scores for the WOW formula
    sorted_unq = np.sort(unq_score)
    unq_rank = np.searchsorted(sorted_unq, unq_score) / max(len(unq_score) - 1, 1) * 100.0

    for i, n in enumerate(names):
        r = results[n]
        unq = float(unq_score[i])
        # WOW = UNQ-rank (40%) + local-contrast (CR) (30%) + entropy proxy via SCD (30%)
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
        r.pop("_fp", None)  # drop heavy field from final


def diagnostics(entry: dict) -> str:
    lines = []
    lines.append(f"  {entry['id']}  composite={entry['composite']} tier={entry['tier']}  render_ms={entry['render_ms']}")
    lines.append(f"  closest_to={entry.get('_max_sim_to')}  similarity={entry.get('_max_sim')}")
    lines.append(f"    POSITIVES:")
    order = ["UNQ","SCD","RT","WOW","PFV","FSC","ED","CR","CV","MFS","BRU"]
    for k in order:
        contrib = W[k] * entry[k]
        bar = "█" * int(entry[k] / 5)
        lines.append(f"      {k:4s} w={W[k]:.2f}  score={entry[k]:5.1f}  contrib={contrib:5.2f}  {bar}")
    lines.append(f"    PENALTIES:")
    for k in ("MP","RP","SIM"):
        contrib = PEN[k] * entry[k]
        bar = "▓" * int(entry[k] / 5)
        lines.append(f"      {k:4s} w=-{PEN[k]:.2f}  score={entry[k]:5.1f}  contrib=-{contrib:5.2f}  {bar}")
    lines.append(f"    positives={entry['positives']}  penalties={entry['penalties']}  composite={entry['composite']}")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE)
    ap.add_argument("--seed", type=int, default=7777)
    ap.add_argument("--diag", action="store_true")
    args = ap.parse_args()

    import engine.spec_patterns as sp
    catalog = sp.PATTERN_CATALOG
    targets = args.ids if args.ids else list(catalog.keys())
    print(f"[spm9] pass 1: scoring {len(targets)} patterns at {args.size}x{args.size}...")

    # For partial runs, MERGE: rescore targets, but reuse old fingerprints for the
    # rest of the catalog so UNQ/SIM compute against full set.
    results: dict[str, dict] = {}
    if args.ids and OUT_JSON.exists():
        try:
            prior = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            results = dict(prior.get("by_finish", {}))
            print(f"[spm9] merging into existing {len(results)} patterns")
            # If old fingerprints aren't in the file we need to rebuild them later;
            # for now we re-fingerprint targeted patterns and rely on prior _fp_cache
            # below. (We persist _fp_cache as a separate JSON sibling.)
        except Exception:
            results = {}

    # Load fp cache (sibling file) so partial runs can rebuild similarity matrix
    fp_cache_path = OUT_JSON.with_suffix(".fp_cache.json")
    fp_cache: dict[str, list] = {}
    if args.ids and fp_cache_path.exists():
        try:
            fp_cache = json.loads(fp_cache_path.read_text(encoding="utf-8"))
        except Exception:
            fp_cache = {}

    t_start = time.perf_counter()
    for i, name in enumerate(targets):
        if name not in catalog:
            print(f"  MISSING: {name}"); continue
        try:
            entry = score_pattern_pass1(name, catalog[name], args.size, seed=args.seed)
            fp_cache[name] = entry["_fp"]
            results[name] = entry
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            results[name] = {"id": name, "error": str(e)}
        if (i + 1) % 50 == 0:
            elapsed = time.perf_counter() - t_start
            print(f"  ... {i+1}/{len(targets)} ({elapsed:.0f}s elapsed)")

    # On partial runs, restore fingerprints for non-target patterns so pass-2
    # similarity is computed against the full catalog.
    if args.ids:
        for n, r in results.items():
            if "_fp" not in r and n in fp_cache:
                r["_fp"] = fp_cache[n]

    # Drop patterns missing _fp (errored) before pass 2
    finalize_targets = {n: r for n, r in results.items() if "_fp" in r}
    print(f"[spm9] pass 2: catalog-wide UNQ/WOW/SIM over {len(finalize_targets)} patterns...")
    finalize_with_catalog(finalize_targets)
    # Merge back: only finalized entries carry composites
    for n, r in finalize_targets.items():
        results[n] = r

    # Persist fp cache
    fp_cache_path.parent.mkdir(parents=True, exist_ok=True)
    fp_cache_path.write_text(json.dumps(fp_cache), encoding="utf-8")

    if args.diag:
        for n in targets:
            if n in results and "composite" in results[n]:
                print(diagnostics(results[n]))

    tiers: dict[str, int] = {"masterpiece":0, "keeper":0, "ok":0, "watch":0, "fix":0, "critical":0}
    for r in results.values():
        t = r.get("tier")
        if t in tiers: tiers[t] += 1
    print(f"[spm9] tier totals: {tiers}")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "version": "spm9.v1",
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "render_size": args.size,
        "weights": W,
        "penalty_weights": {k: -v for k, v in PEN.items()},
        "sim_threshold": SIM_THRESHOLD,
        "tier_thresholds": {"masterpiece":90, "keeper":80, "ok":70, "watch":60, "fix":50},
        "tier_totals": tiers,
        "by_finish": results,
    }, indent=2), encoding="utf-8")
    print(f"[spm9] wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
