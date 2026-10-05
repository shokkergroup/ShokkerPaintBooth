#!/usr/bin/env python3
"""
SPB Finish Quality Workbook — Metric M3: Cross-Variant Coherence.

Original M3 design was "render at 512/1024/2048 and compare." That's blocked
without a renderer harness. This pivots to a substitute that catches the same
class of bug using EXISTING data:

Spec-pattern finishes ship with three different render contexts:
  - thumbnails/spec_patterns/         (standard render)
  - thumbnails/spec_patterns_metal/   (metal substrate)
  - thumbnails/spec_patterns_visual/  (visual-only / 160px variant)

A coherent spec-pattern finish should LOOK LIKE THE SAME PATTERN across all
three variants — different lighting / substrate but same structure. A broken
finish will collapse, fragment, or tile-artifact in one variant.

Metric: per-finish, compute dHash for each variant that exists, then take the
MAX pairwise Hamming distance. Map to a 0-100 score where low max-distance =
coherent, high = breaks in at least one context.

Output: _workbook_metrics/m3_cross_variant.{json,js}

Only applies to spec_pattern surface; null elsewhere (M3 = null doesn't
penalize the composite, M7 renormalizes weights over present metrics).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageFilter  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
THUMBS = PROJECT_ROOT / "thumbnails"
SCORECARD = PROJECT_ROOT / "paint-booth-0-catalog-scorecard.js"
OUT_DIR = PROJECT_ROOT / "_workbook_metrics"
OUT_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)

VARIANT_FOLDERS = {
    "standard": ("spec_patterns", ""),
    "metal":    ("spec_patterns_metal", ""),
    "visual":   ("spec_patterns_visual", "_160"),
}


def load_scorecard() -> Dict[str, dict]:
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    body_match = re.search(r"=\s*(\{.*\});", txt, flags=re.S)
    if body_match is None:
        raise ValueError(f"Could not parse scorecard JSON body from {SCORECARD}")
    body = re.sub(r"//[^\n]*", "", body_match.group(1))
    return json.loads(body)


def dhash(path: Path, size: int = 8) -> int:
    with Image.open(path) as im:
        im = im.convert("L").resize((size + 1, size), Image.LANCZOS)
        px = im.load()
        bits = 0
        for y in range(size):
            for x in range(size):
                bits = (bits << 1) | (1 if px[x, y] > px[x + 1, y] else 0)
        return bits


def edge_hash(path: Path, size: int = 8) -> int:
    """Structure-only perceptual hash.

    M3 needs to compare pattern STRUCTURE across rendering contexts that differ
    in substrate brightness and color. Raw dHash gets dominated by substrate
    differences (returns d≈32, indistinguishable from random). This function
    extracts edges first, binarizes against the per-image mean, and hashes
    that. Result: substrate-invariant, captures only the structural pattern.
    """
    with Image.open(path) as im:
        gray = im.convert("L")
        # FIND_EDGES is a Sobel-like 3x3 kernel. Highlights structural edges.
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edges = edges.resize((size, size), Image.LANCZOS)
        px = list(edges.getdata())
        mean = sum(px) / len(px) if px else 0
        bits = 0
        for v in px:
            bits = (bits << 1) | (1 if v > mean else 0)
        return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def hamming_inv_aware(a: int, b: int, bits: int = 64) -> int:
    """Inversion-aware Hamming distance.

    M3 v1 ran raw Hamming between standard / metal / visual variants and got
    distance ~50+ on every spec_pattern. That's because metal-substrate renders
    are essentially brightness-inverted vs the visual variant (white pattern
    on dark substrate vs dark pattern on light substrate). The PATTERN
    STRUCTURE is identical; the dHash is just measuring the brightness flip.

    Fix: take min(d, bits - d). If a finish's hash is bit-inverted in one
    variant, this returns the SMALL distance, correctly reading the structure
    as coherent. Hashes that differ in actual STRUCTURE (genuinely different
    images) won't have their distance halved — they sit near the 32-bit
    midpoint and stay there.
    """
    d = hamming(a, b)
    return min(d, bits - d)


def main() -> int:
    cats = load_scorecard()
    spec_ids = [k for k in cats if k.startswith("spec_pattern:")]
    print(f"[m3] spec_pattern scorecard entries: {len(spec_ids)}")

    scores: Dict[str, dict] = {}
    cat_running: Dict[str, list] = {}
    missing_variants: int = 0
    coherent_count = 0
    incoherent_count = 0

    for fid in spec_ids:
        stem = fid.split(":", 1)[1]
        variant_hashes: Dict[str, Optional[int]] = {}
        variant_paths: Dict[str, Optional[str]] = {}

        for vname, (folder, suffix) in VARIANT_FOLDERS.items():
            path = THUMBS / folder / f"{stem}{suffix}.png"
            if path.is_file():
                try:
                    variant_hashes[vname] = edge_hash(path)
                    variant_paths[vname] = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
                except Exception as e:
                    logger.warning("hash fail %s: %s", path, e)
                    variant_hashes[vname] = None
                    variant_paths[vname] = None
            else:
                variant_hashes[vname] = None
                variant_paths[vname] = None

        present = [v for v in variant_hashes.values() if v is not None]
        if len(present) < 2:
            missing_variants += 1
            scores[fid] = {
                "score": None,
                "presentVariants": [k for k, v in variant_hashes.items() if v is not None],
                "reason": "fewer than 2 variants present",
            }
            continue

        # Pairwise distances.
        names = [k for k, v in variant_hashes.items() if v is not None]
        pairs = []
        max_d = 0
        worst_pair = None
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                d = hamming_inv_aware(variant_hashes[names[i]], variant_hashes[names[j]])
                pairs.append({"a": names[i], "b": names[j], "distance": d})
                if d > max_d:
                    max_d = d
                    worst_pair = (names[i], names[j])

        # 64-bit dhash. 0 = identical. 32 = random. 64 = inverted.
        # Score: 100 at d=0, 60 at d=8, 30 at d=16, 10 at d=24+.
        # Coherent variants should sit at d<=6 typically.
        if max_d <= 4:
            score = 100.0
            verdict = "coherent"
            coherent_count += 1
        elif max_d <= 8:
            score = 80.0 - (max_d - 4) * 5
            verdict = "minor_drift"
        elif max_d <= 16:
            score = 60.0 - (max_d - 8) * 3.5
            verdict = "drifting"
        elif max_d <= 24:
            score = 30.0 - (max_d - 16) * 2.0
            verdict = "fragmenting"
            incoherent_count += 1
        else:
            score = max(0.0, 14.0 - (max_d - 24) * 0.5)
            verdict = "broken_at_variant"
            incoherent_count += 1

        cat = cats.get(fid, {}).get("category")
        scores[fid] = {
            "score": round(score, 1),
            "maxDistance": max_d,
            "worstPair": list(worst_pair) if worst_pair else None,
            "verdict": verdict,
            "presentVariants": names,
            "pairwise": pairs,
        }
        if cat:
            cat_running.setdefault(cat, []).append(score)

    cat_summary = {
        cat: {
            "count": len(vals),
            "meanScore": round(sum(vals) / len(vals), 1),
            "below50": sum(1 for x in vals if x < 50),
        }
        for cat, vals in cat_running.items()
    }
    sorted_cats = sorted(cat_summary.items(), key=lambda r: r[1]["meanScore"])

    # Worst individual finishes.
    incoherent_list = sorted(
        [{"id": fid, **scores[fid], "category": cats[fid].get("category")}
         for fid in scores
         if scores[fid].get("score") is not None and scores[fid]["score"] < 50],
        key=lambda r: r["score"],
    )

    print(f"[m3] scored: {sum(1 for v in scores.values() if v.get('score') is not None)}")
    print(f"[m3] insufficient-variants: {missing_variants}")
    print(f"[m3] coherent (max_d ≤ 4): {coherent_count}")
    print(f"[m3] incoherent (score < 50): {incoherent_count}")
    print(f"[m3] worst 8 categories:")
    for name, c in sorted_cats[:8]:
        print(f"  {c['meanScore']:5.1f}  n={c['count']:3d}  below50={c['below50']:3d}  {name}")
    print(f"[m3] top 10 worst individual finishes:")
    for row in incoherent_list[:10]:
        print(f"  {row['score']:5.1f}  d={row['maxDistance']:2d}  worst={row['worstPair']}  {row['id']}")

    out = {
        "version": 1,
        "metric": "M3 — Cross-Variant Coherence (spec_patterns vs _metal vs _visual)",
        "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "appliesTo": "spec_pattern surface only",
        "byFinish": scores,
        "byCategory": cat_summary,
        "incoherentPreview": incoherent_list[:100],
    }
    (OUT_DIR / "m3_cross_variant.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (OUT_DIR / "m3_cross_variant.js").write_text(
        "// Auto-generated by scripts/spb_workbook_compute_m3.py — do not hand-edit.\n"
        "window.SPB_M3 = " + json.dumps(out) + ";\n",
        encoding="utf-8",
    )
    print(f"[m3] wrote _workbook_metrics/m3_cross_variant.{{json,js}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
