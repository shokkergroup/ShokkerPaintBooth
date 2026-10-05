#!/usr/bin/env python3
"""
SPB Pattern Quality Metric (PQM) — comprehensive 8-component score for the
586 regular patterns (PATTERN_REGISTRY). NOT spec patterns.

Why this script exists
----------------------
The existing M1-M8 finish quality suite (see docs/METRICS.md) treats patterns
as one surface among many (M1 sibling diff, M5 spec/paint coherence, etc.).
That's good for catalog-wide health but doesn't give a per-pattern verdict
the owner can act on ("which patterns need a re-render?").

This script reads each pattern's baked thumbnail under thumbnails/pattern/,
computes 8 component scores, and writes a composite 0-100 PQM plus a
per-component breakdown. Outputs:

  _workbook_metrics/pattern_quality.json   (machine-readable)
  _workbook_metrics/pattern_quality.js     (sidecar: window.SPB_PQM = {...})

The HTML review surface SPB_PATTERN_QUALITY_REVIEW.html loads the .js
sidecar and renders a sortable / filterable grid.

Components (0-100 each)
-----------------------
  P1 Structural Energy   — tri-band activity (macro/mid/fine) — pattern actually present
  P2 Edge Definition     — Sobel magnitude + edge density — crispness
  P3 Coverage Uniformity — 8x8 block std uniformity — no dead zones
  P4 Tileability         — top/bottom + left/right RMS — seamless on car panels
  P5 Frequency Balance   — three octave bands all non-trivial (M8 doctrine)
  P6 Sibling Diff        — 64-bit dHash Hamming to category siblings (M1-like)
  P7 Dynamic Range       — p99-p1 luminance spread + histogram fill
  P8 Intent Fit          — category-aware profile (carbon=repetitive, fractal=recursive, etc.)

Composite weights (sum 1.0):
  P1 0.16, P2 0.14, P3 0.10, P4 0.10, P5 0.14, P6 0.10, P7 0.10, P8 0.16

Tier thresholds:
  >=85 keeper | 70-84 ok | 55-69 watch | 40-54 fix | <40 critical

Run: python scripts/spb_pattern_quality_metric.py
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


def _jsonable(obj):
    """Convert numpy scalars / arrays / dicts / lists into JSON-safe values."""
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj

PROJECT_ROOT = Path(__file__).resolve().parent.parent
THUMBS = PROJECT_ROOT / "thumbnails" / "pattern"
SCORECARD = PROJECT_ROOT / "paint-booth-0-catalog-scorecard.js"
OUT_DIR = PROJECT_ROOT / "_workbook_metrics"
OUT_DIR.mkdir(exist_ok=True)
OUT_JSON = OUT_DIR / "pattern_quality.json"
OUT_JS = OUT_DIR / "pattern_quality.js"

THUMB_PX = 256  # all pattern thumbnails baked at 256

# ---------------------------------------------------------------------------
# Category-aware intent profiles for P8.
# Each entry describes expected ranges for the four primary diagnostic axes:
#   edge_density: % pixels with strong edges
#   block_std_p50: median 32x32 block std (macro)
#   fine_energy: high-pass mean abs (fine)
#   color_entropy: Shannon entropy of quantized 32-bin luminance histogram
# Bands: 'LO' (below 33rd), 'MID' (33-66th), 'HI' (above 66th) of the pattern catalog.
INTENT_PROFILES: dict[str, dict[str, str]] = {
    "Carbon & Weave":          {"edge_density": "HI", "block_std_p50": "MID", "fine_energy": "HI", "color_entropy": "LO"},
    "Geometric":               {"edge_density": "HI", "block_std_p50": "MID", "fine_energy": "MID", "color_entropy": "MID"},
    "Op-Art & Optical":        {"edge_density": "HI", "block_std_p50": "HI",  "fine_energy": "MID", "color_entropy": "LO"},
    "Decades & Retro":         {"edge_density": "MID","block_std_p50": "HI",  "fine_energy": "MID", "color_entropy": "MID"},
    "Tech & Circuit":          {"edge_density": "HI", "block_std_p50": "MID", "fine_energy": "HI",  "color_entropy": "MID"},
    "Guilloché & Pattern":     {"edge_density": "HI", "block_std_p50": "MID", "fine_energy": "HI",  "color_entropy": "LO"},
    "Abstract & Experimental": {"edge_density": "MID","block_std_p50": "MID", "fine_energy": "MID", "color_entropy": "HI"},
    "Tribal & Mythology":      {"edge_density": "HI", "block_std_p50": "HI",  "fine_energy": "MID", "color_entropy": "MID"},
    "Cultural & World":        {"edge_density": "HI", "block_std_p50": "HI",  "fine_energy": "MID", "color_entropy": "MID"},
    "Sports & Motorsport":     {"edge_density": "MID","block_std_p50": "HI",  "fine_energy": "MID", "color_entropy": "MID"},
    "Music & Lifestyle":       {"edge_density": "MID","block_std_p50": "HI",  "fine_energy": "MID", "color_entropy": "MID"},
    "Astro & Cosmic":          {"edge_density": "MID","block_std_p50": "MID", "fine_energy": "HI",  "color_entropy": "HI"},
    "Heroes & Pop":            {"edge_density": "HI", "block_std_p50": "HI",  "fine_energy": "MID", "color_entropy": "MID"},
    "Flames & Fire":           {"edge_density": "MID","block_std_p50": "HI",  "fine_energy": "MID", "color_entropy": "MID"},
    "Animal & Nature":         {"edge_density": "MID","block_std_p50": "MID", "fine_energy": "MID", "color_entropy": "MID"},
    "Art Nouveau & Deco":      {"edge_density": "HI", "block_std_p50": "MID", "fine_energy": "MID", "color_entropy": "MID"},
    "Skate & Street":          {"edge_density": "MID","block_std_p50": "MID", "fine_energy": "MID", "color_entropy": "MID"},
    "Beach & Surf":            {"edge_density": "MID","block_std_p50": "HI",  "fine_energy": "MID", "color_entropy": "MID"},
    "Mortal Shokk":            {"edge_density": "HI", "block_std_p50": "HI",  "fine_energy": "MID", "color_entropy": "MID"},
    "SHOKK Series":            {"edge_density": "HI", "block_std_p50": "MID", "fine_energy": "HI",  "color_entropy": "MID"},
    "PARADIGM":                {"edge_density": "MID","block_std_p50": "MID", "fine_energy": "MID", "color_entropy": "MID"},
    "Seamless & Fabric":       {"edge_density": "MID","block_std_p50": "MID", "fine_energy": "HI",  "color_entropy": "LO"},
}

WEIGHTS = {
    "p1_structure": 0.16,
    "p2_edges": 0.14,
    "p3_coverage": 0.10,
    "p4_tileability": 0.10,
    "p5_freq_balance": 0.14,
    "p6_sibling_diff": 0.10,
    "p7_dynamic_range": 0.10,
    "p8_intent_fit": 0.16,
}


# ---------------------------------------------------------------------------
# Helpers

def load_scorecard() -> dict[str, dict]:
    """Read paint-booth-0-catalog-scorecard.js and return {id: {...}}.

    We only need the pattern: entries. JSON literal works since the file is
    already plain JSON-shaped under the `=` assignment.
    """
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"=\s*(\{.*\});", txt, flags=re.S)
    if not m:
        raise RuntimeError("scorecard literal not found")
    body = re.sub(r"//[^\n]*", "", m.group(1))
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        # fallback: regex extract category only
        data = {}
        for hit in re.finditer(
            r'"([^"]+)":\s*\{[^{}]*?"surface":\s*"([^"]+)"[^{}]*?"category":\s*"([^"]+)"',
            body,
            flags=re.S,
        ):
            data[hit.group(1)] = {"surface": hit.group(2), "category": hit.group(3)}
    # Slim down to patterns only
    return {k: v for k, v in data.items() if isinstance(v, dict) and k.startswith("pattern:")}


def load_thumb(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (luma 0-1 float32 256x256, rgb 0-255 uint8)."""
    img = Image.open(path).convert("RGB")
    if img.size != (THUMB_PX, THUMB_PX):
        img = img.resize((THUMB_PX, THUMB_PX), Image.LANCZOS)
    rgb = np.asarray(img, dtype=np.uint8)
    luma = (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]) / 255.0
    return luma.astype(np.float32), rgb


def sobel_edges(luma: np.ndarray) -> np.ndarray:
    """Sobel magnitude on luma 0-1, returns same shape 0+."""
    gx = np.zeros_like(luma)
    gy = np.zeros_like(luma)
    gx[:, 1:-1] = luma[:, 2:] - luma[:, :-2]
    gy[1:-1, :] = luma[2:, :] - luma[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def block_pool_std(luma: np.ndarray, block: int) -> np.ndarray:
    """Mean-pool into block-sized cells then return the per-cell std grid."""
    h, w = luma.shape
    n = h // block
    if n < 2:
        return np.array([luma.std()], dtype=np.float32)
    trimmed = luma[: n * block, : n * block]
    # mean per cell
    pooled = trimmed.reshape(n, block, n, block).mean(axis=(1, 3))
    # per-block std: stds of original pixels per block
    block_stds = trimmed.reshape(n, block, n, block).std(axis=(1, 3))
    return block_stds.astype(np.float32)


def high_pass(luma: np.ndarray, sigma: float = 3.0) -> np.ndarray:
    """Cheap high-pass: original - 3x3 box blur."""
    blurred = np.zeros_like(luma)
    blurred[1:-1, 1:-1] = (
        luma[:-2, :-2] + luma[:-2, 1:-1] + luma[:-2, 2:] +
        luma[1:-1, :-2] + luma[1:-1, 1:-1] + luma[1:-1, 2:] +
        luma[2:, :-2] + luma[2:, 1:-1] + luma[2:, 2:]
    ) / 9.0
    return luma - blurred


# ---------------------------------------------------------------------------
# Component scorers — each returns float 0-100

def p1_structural_energy(luma: np.ndarray) -> tuple[float, dict]:
    """Tri-band activity: macro (32px blocks), mid (Sobel edges), fine (high-pass)."""
    macro_std = float(block_pool_std(luma, 32).std()) * 100.0
    edges = sobel_edges(luma)
    edge_mean = float(edges.mean()) * 100.0
    fine = high_pass(luma)
    fine_energy = float(np.abs(fine).mean()) * 100.0
    bands = []
    # macro band: 2.5+ std means real macro variance
    bands.append(min(100.0, macro_std / 6.0 * 100.0))
    # mid band: edge_mean 3+ is meaningful
    bands.append(min(100.0, edge_mean / 8.0 * 100.0))
    # fine band: 0.6+ fine_energy is meaningful
    bands.append(min(100.0, fine_energy / 1.5 * 100.0))
    # Geometric mean penalizes zero bands hard
    bands = [max(b, 0.5) for b in bands]
    score = float((bands[0] * bands[1] * bands[2]) ** (1.0 / 3.0))
    return score, {"macro_std": macro_std, "edge_mean": edge_mean, "fine_energy": fine_energy}


def p2_edge_definition(luma: np.ndarray) -> tuple[float, dict]:
    """Pattern needs crisp edges — Sobel mean + edge density + histogram bimodality."""
    edges = sobel_edges(luma)
    mean_edge = float(edges.mean())
    threshold = max(0.04, mean_edge * 1.4)
    edge_density = float((edges > threshold).mean()) * 100.0
    # crisp pattern has bimodal luma histogram (edges create steep gradients)
    hist, _ = np.histogram(luma, bins=32, range=(0, 1))
    hist = hist / max(1, hist.sum())
    # bimodality proxy: 1 - entropy/log(32)
    eps = 1e-12
    entropy = -float(np.sum(hist * np.log(hist + eps)))
    crispness_proxy = max(0.0, 1.0 - entropy / math.log(32))
    sobel_score = min(100.0, mean_edge * 600.0)
    density_score = min(100.0, edge_density * 2.5)
    crisp_score = crispness_proxy * 100.0
    score = 0.45 * sobel_score + 0.35 * density_score + 0.20 * crisp_score
    return float(score), {"sobel_mean": mean_edge, "edge_density_pct": edge_density, "crispness": crispness_proxy}


def p3_coverage_uniformity(luma: np.ndarray) -> tuple[float, dict]:
    """8x8 grid of 32px blocks — min/median block std ratio. 1.0 = perfectly uniform."""
    blocks = block_pool_std(luma, 32)
    if blocks.size < 4:
        return 50.0, {"block_count": int(blocks.size)}
    median = float(np.median(blocks))
    if median < 1e-6:
        return 0.0, {"median_std": median, "uniformity": 0.0}
    min_block = float(blocks.min())
    p10 = float(np.percentile(blocks, 10))
    uniformity = min(1.0, p10 / median)
    score = uniformity * 100.0
    return score, {"median_std": median, "min_std": min_block, "p10_std": p10, "uniformity": uniformity}


def p4_tileability(luma: np.ndarray) -> tuple[float, dict]:
    """Top/bottom + left/right RMS difference. Lower = more tileable."""
    h, w = luma.shape
    band = max(2, h // 32)
    top = luma[:band, :]
    bot = luma[-band:, :]
    left = luma[:, :band]
    right = luma[:, -band:]
    vert_rms = float(np.sqrt(np.mean((top - bot) ** 2)))
    horiz_rms = float(np.sqrt(np.mean((left - right) ** 2)))
    seam_rms = (vert_rms + horiz_rms) / 2.0
    # 0.10+ RMS is a visible seam; 0.0 is perfect
    score = max(0.0, min(100.0, (1.0 - seam_rms / 0.15) * 100.0))
    return float(score), {"vert_seam_rms": vert_rms, "horiz_seam_rms": horiz_rms}


def p5_freq_balance(luma: np.ndarray) -> tuple[float, dict]:
    """Three octave bands each individually meeting a floor (M8 doctrine)."""
    macro = float(block_pool_std(luma, 32).std())   # 32px features
    mid_pool = block_pool_std(luma, 8)               # 8px features
    mid = float(mid_pool.std())
    fine = float(np.abs(high_pass(luma)).mean())
    # Each band scored on its own floor; band-floor must all be met
    bands = [
        ("macro_32", macro, 0.03),
        ("mid_8",    mid,   0.05),
        ("fine_hp",  fine,  0.012),
    ]
    band_scores = []
    detail = {}
    for name, val, floor in bands:
        s = min(100.0, val / (floor * 2.5) * 100.0)
        band_scores.append(s)
        detail[name] = {"value": val, "floor": floor, "score": s}
    # Use min so all 3 bands must be present (penalize one missing band heavily)
    score = float(min(band_scores) * 0.6 + (sum(band_scores) / 3.0) * 0.4)
    return score, detail


def dhash_64(luma: np.ndarray) -> int:
    """Cheap 64-bit dHash on the luminance plane."""
    small = np.asarray(
        Image.fromarray((luma * 255).astype(np.uint8)).resize((9, 8), Image.LANCZOS),
        dtype=np.uint8,
    )
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (1 if small[y, x] > small[y, x + 1] else 0)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def p6_sibling_diff_scores(hashes: dict[str, int], categories: dict[str, str]) -> dict[str, tuple[float, dict]]:
    """Mean Hamming distance to category siblings, scaled to 0-100."""
    by_cat: dict[str, list[str]] = defaultdict(list)
    for pid, cat in categories.items():
        if pid in hashes and cat:
            by_cat[cat].append(pid)
    out: dict[str, tuple[float, dict]] = {}
    for pid, h in hashes.items():
        cat = categories.get(pid, "")
        siblings = [s for s in by_cat.get(cat, []) if s != pid]
        if not siblings:
            out[pid] = (60.0, {"siblings": 0, "mean_distance": None, "note": "no siblings"})
            continue
        dists = [hamming(h, hashes[s]) for s in siblings]
        mean_d = sum(dists) / len(dists)
        # 0 = clone (0 score), 32 = random (~80), 64 = inverse (100)
        score = min(100.0, (mean_d / 32.0) * 80.0)
        out[pid] = (float(score), {"siblings": len(siblings), "mean_distance": mean_d})
    return out


def p7_dynamic_range(luma: np.ndarray, rgb: np.ndarray) -> tuple[float, dict]:
    """Luma p99-p1 spread + chroma entropy."""
    p1 = float(np.percentile(luma, 1))
    p99 = float(np.percentile(luma, 99))
    spread = (p99 - p1) * 100.0  # 100 = full
    # Chroma: HSV saturation distribution
    rgbf = rgb.astype(np.float32) / 255.0
    mx = rgbf.max(axis=2)
    mn = rgbf.min(axis=2)
    chroma = mx - mn
    chroma_mean = float(chroma.mean()) * 100.0  # 0-100
    # Score: spread is the main signal; chroma adds 20%
    score = min(100.0, spread * 0.8 + chroma_mean * 1.6)
    return float(score), {"luma_p1": p1, "luma_p99": p99, "spread": p99 - p1, "chroma_mean": chroma.mean()}


def p8_intent_fit(features: dict, profile: dict | None, percentiles: dict) -> tuple[float, dict]:
    """Score against category profile using catalog-wide percentile bands."""
    if not profile:
        return 65.0, {"note": "no category profile (default mid)"}
    axes_passed = 0
    axes_total = 0
    detail = {}
    for axis, expected_band in profile.items():
        if axis not in percentiles or axis not in features:
            continue
        axes_total += 1
        actual = features[axis]
        p33, p66 = percentiles[axis]
        if actual < p33:
            band = "LO"
        elif actual < p66:
            band = "MID"
        else:
            band = "HI"
        passed = band == expected_band
        if passed:
            axes_passed += 1
        detail[axis] = {"value": actual, "expected": expected_band, "actual_band": band, "pass": passed}
    if axes_total == 0:
        return 50.0, {"note": "profile axes missing in features"}
    score = (axes_passed / axes_total) * 100.0
    return float(score), detail


def tier_of(composite: float) -> str:
    """Tier thresholds calibrated against catalog distribution (top ~10% keeper).

    The PQM is catalog-relative so the absolute composite values are deliberately
    compressed; tiers map to action urgency for the owner:
      keeper   >= 70  ship-quality, no rework expected
      ok       55-69  acceptable, low priority polish
      watch    45-54  borderline, schedule a re-render if time permits
      fix      35-44  visible issues, queue for renderer rebuild
      critical < 35   broken / placeholder / clone — must rework before alpha
    """
    if composite >= 70:
        return "keeper"
    if composite >= 55:
        return "ok"
    if composite >= 45:
        return "watch"
    if composite >= 35:
        return "fix"
    return "critical"


# ---------------------------------------------------------------------------
# Driver

def collect_features(thumbs: list[Path]) -> dict[str, dict]:
    """Walk all thumbs once, extracting all measurable features for every pattern."""
    feats: dict[str, dict] = {}
    print(f"[PQM] Loading {len(thumbs)} pattern thumbnails ...", flush=True)
    for i, path in enumerate(thumbs):
        pid = "pattern:" + path.stem
        try:
            luma, rgb = load_thumb(path)
        except Exception as exc:
            print(f"[PQM]   skip {path.name}: {exc}", file=sys.stderr)
            continue
        blocks32 = block_pool_std(luma, 32)
        edges = sobel_edges(luma)
        edge_thresh = max(0.04, float(edges.mean()) * 1.4)
        hist, _ = np.histogram(luma, bins=32, range=(0, 1))
        hist = hist / max(1, hist.sum())
        eps = 1e-12
        ent = -float(np.sum(hist * np.log(hist + eps)))
        feats[pid] = {
            "_path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "luma": luma,
            "rgb": rgb,
            "hash": dhash_64(luma),
            "edge_density": float((edges > edge_thresh).mean()),
            "block_std_p50": float(np.median(blocks32)),
            "fine_energy": float(np.abs(high_pass(luma)).mean()),
            "color_entropy": ent,
        }
        if (i + 1) % 100 == 0:
            print(f"[PQM]   loaded {i + 1}/{len(thumbs)}", flush=True)
    return feats


def compute_percentiles(feats: dict[str, dict], axes: list[str]) -> dict[str, tuple[float, float]]:
    out = {}
    for axis in axes:
        vals = np.array([f[axis] for f in feats.values() if axis in f], dtype=np.float32)
        if vals.size == 0:
            out[axis] = (0.0, 0.0)
            continue
        out[axis] = (float(np.percentile(vals, 33)), float(np.percentile(vals, 66)))
    return out


def calibrate_to_catalog(raw_scores: dict[str, float], floor: float = 8.0, ceil: float = 100.0) -> dict[str, float]:
    """Map raw per-pattern scores onto [floor, ceil] using catalog percentile rank.

    Components emit raw values whose absolute magnitude varies per signal. Using
    catalog-relative percentile rank gives the score a stable interpretation:
    a pattern at 50 sits at the catalog median; 90 = top 10%; 10 = bottom 10%.
    Floor/ceiling are tightened so even the best pattern isn't a guaranteed 100
    (encourages future improvements). Critical floor stays > 0 so a single bad
    component can't drive composite negative.
    """
    vals = np.array(list(raw_scores.values()), dtype=np.float64)
    if vals.size == 0:
        return raw_scores
    order = np.argsort(vals, kind="stable")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(vals.size, dtype=np.float64)
    pct = ranks / max(1.0, vals.size - 1.0)
    scaled = floor + pct * (ceil - floor)
    keys = list(raw_scores.keys())
    return {k: float(scaled[i]) for i, k in enumerate(keys)}


def main() -> None:
    if not THUMBS.exists():
        raise SystemExit(f"Missing {THUMBS}")
    scorecard = load_scorecard()
    print(f"[PQM] {len(scorecard)} pattern scorecard entries (categories source)")

    thumbs = sorted(THUMBS.glob("*.png"))
    feats = collect_features(thumbs)
    print(f"[PQM] Loaded {len(feats)} feature rows")

    # Categories: prefer scorecard, fall back to "Uncategorized"
    categories = {pid: (scorecard.get(pid, {}).get("category") or "Uncategorized") for pid in feats}

    # Percentiles for intent-fit
    percentiles = compute_percentiles(feats, ["edge_density", "block_std_p50", "fine_energy", "color_entropy"])

    # P6 sibling diff (batch)
    hashes = {pid: f["hash"] for pid, f in feats.items()}
    p6_all = p6_sibling_diff_scores(hashes, categories)

    # Pass 1: compute raw absolute scores for P1-P5 + P7 (P6/P8 stay absolute).
    raw = {pid: {} for pid in feats}
    diag = {pid: {} for pid in feats}
    for pid, f in feats.items():
        luma = f["luma"]
        rgb = f["rgb"]
        raw[pid]["p1_structure"],    diag[pid]["p1"] = p1_structural_energy(luma)
        raw[pid]["p2_edges"],        diag[pid]["p2"] = p2_edge_definition(luma)
        raw[pid]["p3_coverage"],     diag[pid]["p3"] = p3_coverage_uniformity(luma)
        raw[pid]["p4_tileability"],  diag[pid]["p4"] = p4_tileability(luma)
        raw[pid]["p5_freq_balance"], diag[pid]["p5"] = p5_freq_balance(luma)
        raw[pid]["p7_dynamic_range"],diag[pid]["p7"] = p7_dynamic_range(luma, rgb)

    # Catalog-relative calibration for components whose absolute magnitude is
    # signal-dependent (P1, P2, P3, P4, P5, P7). P6 sibling-diff and P8 intent-fit
    # are already in interpretable 0-100 units (pass rates / hamming-distance),
    # so they stay as-is.
    calibrated = {pid: {} for pid in feats}
    for comp in ("p1_structure", "p2_edges", "p3_coverage", "p4_tileability", "p5_freq_balance", "p7_dynamic_range"):
        comp_raw = {pid: raw[pid][comp] for pid in feats}
        comp_cal = calibrate_to_catalog(comp_raw)
        for pid, val in comp_cal.items():
            calibrated[pid][comp] = val

    # P6 and P8 use absolute scores
    for pid, f in feats.items():
        p6, p6d = p6_all[pid]
        calibrated[pid]["p6_sibling_diff"] = p6
        diag[pid]["p6"] = p6d
        cat = categories[pid]
        profile = INTENT_PROFILES.get(cat)
        feat_for_intent = {
            "edge_density": f["edge_density"],
            "block_std_p50": f["block_std_p50"],
            "fine_energy": f["fine_energy"],
            "color_entropy": f["color_entropy"],
        }
        p8, p8d = p8_intent_fit(feat_for_intent, profile, percentiles)
        calibrated[pid]["p8_intent_fit"] = p8
        diag[pid]["p8"] = p8d

    # Composite + assemble rows
    rows: dict[str, dict] = {}
    for pid, f in feats.items():
        components = {k: round(calibrated[pid][k], 1) for k in WEIGHTS}
        composite = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
        rows[pid] = {
            "id": pid.split(":", 1)[1],
            "category": categories[pid],
            "tier": tier_of(composite),
            "composite": round(composite, 1),
            "components": components,
            "raw_components": {k: round(raw[pid].get(k, 0.0), 2) for k in (
                "p1_structure","p2_edges","p3_coverage","p4_tileability","p5_freq_balance","p7_dynamic_range"
            )},
            "thumb": f["_path"],
            "intent_profile_used": bool(INTENT_PROFILES.get(categories[pid])),
            "diagnostics": diag[pid],
        }

    # Category rollups + tier summary
    by_cat: dict[str, list[float]] = defaultdict(list)
    by_tier: dict[str, int] = defaultdict(int)
    for r in rows.values():
        by_cat[r["category"]].append(r["composite"])
        by_tier[r["tier"]] += 1
    cat_summary = {
        cat: {
            "n": len(vals),
            "mean": round(float(np.mean(vals)), 1),
            "median": round(float(np.median(vals)), 1),
            "min": round(float(np.min(vals)), 1),
            "max": round(float(np.max(vals)), 1),
        }
        for cat, vals in sorted(by_cat.items())
    }

    # STILL-WEAK list (lowest composites first)
    sorted_pids = sorted(rows.keys(), key=lambda p: rows[p]["composite"])
    still_weak = [
        {"id": rows[p]["id"], "composite": rows[p]["composite"], "tier": rows[p]["tier"], "category": rows[p]["category"], "thumb": rows[p]["thumb"]}
        for p in sorted_pids[:150]
    ]

    payload = {
        "generated_at": _dt.datetime.now(_dt.UTC).isoformat(),
        "thumb_count": len(rows),
        "weights": WEIGHTS,
        "tiers": {"keeper": ">=70", "ok": "55-69", "watch": "45-54", "fix": "35-44", "critical": "<35"},
        "percentiles": {k: {"p33": v[0], "p66": v[1]} for k, v in percentiles.items()},
        "tier_summary": dict(by_tier),
        "by_category": cat_summary,
        "still_weak": still_weak,
        "by_pattern": rows,
    }
    payload = _jsonable(payload)

    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_JS.write_text("// auto-generated by scripts/spb_pattern_quality_metric.py\n"
                      "window.SPB_PQM = " + json.dumps(payload) + ";\n",
                      encoding="utf-8")

    print(f"[PQM] Wrote {OUT_JSON.relative_to(PROJECT_ROOT)} ({OUT_JSON.stat().st_size // 1024} KB)")
    print(f"[PQM] Wrote {OUT_JS.relative_to(PROJECT_ROOT)}")
    print(f"[PQM] Tier summary: {dict(by_tier)}")
    print(f"[PQM] Top 5 weakest:")
    for w in still_weak[:5]:
        print(f"        {w['composite']:5.1f}  [{w['tier']:8s}]  {w['category']:30.30s}  {w['id']}")


if __name__ == "__main__":
    main()
