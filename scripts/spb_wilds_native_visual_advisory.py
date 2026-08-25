#!/usr/bin/env python3
"""Advisory native-2048 topology screen for Fractured Wilds.

SPB-105 / owner doctrine / 2026-08-25.  M7 measures useful image statistics,
but it cannot decide whether a visible carrier is a macro hero, rail sheet,
isolated glyph field or repeating tile.  This lightweight report makes those
failure modes visible *before* M7/runtime work.  It is never an acceptance
gate: a human must inspect the full 2048 paint and A/B images.

Usage:
  python scripts/spb_wilds_native_visual_advisory.py path/to/paint_2048.png
  python scripts/spb_wilds_native_visual_advisory.py folder/of/paint_2048.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List

import cv2
import numpy as np


def _paint_paths(inputs: Iterable[str]) -> List[Path]:
    found: List[Path] = []
    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            found.extend(sorted(path.rglob("*_paint_2048.png")))
        elif path.is_file():
            found.append(path)
    # The first result for an ID should not silently hide an alternate trial.
    return sorted(dict.fromkeys(found))


def _patch_repeat(gray: np.ndarray, side: int = 64) -> float:
    """High score means 64px patches repeat unusually closely.

    This deliberately sees only a coarse 32x32 sampling of a full 2048 image;
    it is an indicator for pavers/checkers, never proof of a duplicate finish.
    """
    sample = cv2.resize(gray, (512, 512), interpolation=cv2.INTER_AREA)
    patches = []
    for y in range(0, 512, side):
        for x in range(0, 512, side):
            p = sample[y:y + side, x:x + side].astype(np.float32)
            p -= p.mean()
            patches.append(p.reshape(-1) / (np.linalg.norm(p) + 1e-6))
    bank = np.stack(patches)
    similarity = bank @ bank.T
    np.fill_diagonal(similarity, -1.0)
    return float(np.mean(np.max(similarity, axis=1)))


def _advisory(path: Path) -> Dict[str, object]:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Unreadable image: {path}")
    native_shape = [int(bgr.shape[1]), int(bgr.shape[0])]
    # Inspect the native asset, but analyze a 1024px proxy so a full 110-item
    # screen remains an inexpensive advisory.  Native 8–32px marks are still
    # 4–16px here, while the report preserves the true input dimensions.
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if max(gray.shape) > 1024:
        gray = cv2.resize(gray, (1024, 1024), interpolation=cv2.INTER_AREA)
    # Normalized gradients find repeated directional rails independent of hue.
    blur = cv2.GaussianBlur(gray, (0, 0), 2.2)
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy)
    active = mag > np.percentile(mag, 80)
    orientation = np.mod(np.arctan2(gy[active], gx[active]), np.pi)
    hist, _ = np.histogram(orientation, bins=18, range=(0, np.pi))
    direction_dominance = float(hist.max() / max(1, hist.sum()))
    direction_entropy = float(-np.sum((hist / max(1, hist.sum())) * np.log2(hist / max(1, hist.sum()) + 1e-12)))
    # Macro ratio: contrast surviving 96px blur relative to fine detail.
    macro = cv2.GaussianBlur(gray, (0, 0), 48).astype(np.float32)
    residual = gray.astype(np.float32) - macro
    macro_ratio = float(macro.std() / (macro.std() + residual.std() + 1e-6))
    # Connected components of a restrained edge map provide a warning for
    # isolated icons/glyphs over empty ground; it does not judge a real pore.
    edge = cv2.Canny(gray, 70, 150)
    edge = cv2.morphologyEx(edge, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(edge, 8)
    areas = stats[1:, cv2.CC_STAT_AREA] if count > 1 else np.empty(0)
    small = areas[(areas >= 18) & (areas <= 900)]
    glyph_density = float(len(small) / (gray.shape[0] * gray.shape[1] / 1_000_000))
    edge_coverage = float((edge > 0).mean())
    repeat = _patch_repeat(gray)
    warnings = []
    if macro_ratio > .42:
        warnings.append("macro-dominant: inspect for hero bands/large territories")
    if direction_dominance > .24 and direction_entropy < 3.25:
        warnings.append("rail-dominant: inspect for stripe/comb/parallel-line carrier")
    # Fine legitimate microcuticle (Dragon) can have hundreds of components;
    # a sparse glyph field has many bounded components *and little total edge
    # coverage.  Require both, otherwise merely report the raw diagnostic.
    if glyph_density > 30 and edge_coverage < .04:
        warnings.append("sparse-detail-coverage: inspect visually for detached glyph/confetti anatomy")
    if repeat > .89:
        warnings.append("patch-repeat: inspect for paver/checker/repeated-unit carrier")
    return {
        "paint": str(path),
        "native_shape": native_shape,
        "macro_ratio": round(macro_ratio, 4),
        "direction_dominance": round(direction_dominance, 4),
        "direction_entropy_bits": round(direction_entropy, 4),
        "small_edge_components_per_mp": round(glyph_density, 2),
        "edge_coverage": round(edge_coverage, 4),
        "coarse_patch_repeat": round(repeat, 4),
        "advisory_warnings": warnings,
        "verdict": "HUMAN-NATIVE-2048-REVIEW-REQUIRED",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="native paint PNG(s) or directories")
    parser.add_argument("--out", type=Path, help="optional JSON report path")
    args = parser.parse_args()
    paths = _paint_paths(args.paths)
    if not paths:
        raise SystemExit("No *_paint_2048.png files found.")
    report = {"schema": "spb-wilds-native-visual-advisory/v1", "items": [_advisory(path) for path in paths]}
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
