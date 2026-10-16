# -*- coding: utf-8 -*-
"""Cross-survivor paint/spec topology audit for experimental Wilds.

Color is removed before paint comparison.  Spec values are converted to local
rank order and all six M/R/Cc channel permutations are tested, preventing a
channel swap or tier-value rewrite from hiding a shared topology.  Outputs are
owner-reviewable montages plus a compact all-pairs JSON report.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.expansions.fractured_wilds_accepted_2026 import (  # noqa: E402
    ACCEPTED_IDS, _accepted_authored,
)

OUT = ROOT / "_wilds_fullres_progress_20260824" / "accepted_runtime_rollout"


def _z(a):
    a = np.asarray(a, np.float32)
    return (a - float(a.mean())) / (float(a.std()) + 1e-6)


def _corr(a, b):
    return float(np.mean(_z(a) * _z(b)))


def _paint_features(paint):
    rgb = cv2.resize(np.asarray(paint, np.float32), (256, 256), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    low = cv2.resize(cv2.GaussianBlur(gray, (0, 0), 10.0), (64, 64), interpolation=cv2.INTER_AREA)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge = cv2.GaussianBlur(np.hypot(gx, gy), (0, 0), 1.2)
    return _z(low), _z(edge), gray


def _rank_channel(channel):
    values = np.asarray(channel, np.uint8)
    unique = np.unique(values)
    ranks = np.searchsorted(unique, values).astype(np.float32)
    if len(unique) > 1:
        ranks /= float(len(unique) - 1)
    ranks = cv2.resize(ranks, (256, 256), interpolation=cv2.INTER_NEAREST)
    gx = cv2.Sobel(ranks, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(ranks, cv2.CV_32F, 0, 1, ksize=3)
    return _z(ranks), _z(cv2.GaussianBlur(np.hypot(gx, gy), (0, 0), 1.0))


def _spec_features(spec):
    return tuple(_rank_channel(spec[:, :, i]) for i in range(3))


def _spec_similarity(a, b):
    best = -1.0
    best_perm = None
    best_rank = best_edge = None
    for perm in itertools.permutations(range(3)):
        ranks = [abs(_corr(a[i][0], b[perm[i]][0])) for i in range(3)]
        edges = [abs(_corr(a[i][1], b[perm[i]][1])) for i in range(3)]
        score = .55 * float(np.mean(ranks)) + .45 * float(np.mean(edges))
        if score > best:
            best, best_perm = score, perm
            best_rank, best_edge = float(np.mean(ranks)), float(np.mean(edges))
    return best, best_perm, best_rank, best_edge


def _montage(images, path, columns=5, tile=384, grayscale=False):
    rows = (len(images) + columns - 1) // columns
    canvas = np.zeros((rows * (tile + 34), columns * tile, 3), np.uint8)
    for index, (fid, image) in enumerate(images):
        y, x = divmod(index, columns)
        if grayscale:
            image = cv2.cvtColor(np.clip(image * 255, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        else:
            image = cv2.cvtColor(np.clip(image * 255, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        image = cv2.resize(image, (tile, tile), interpolation=cv2.INTER_AREA)
        y0, x0 = y * (tile + 34), x * tile
        canvas[y0:y0 + tile, x0:x0 + tile] = image
        cv2.putText(canvas, fid, (x0 + 8, y0 + tile + 24), cv2.FONT_HERSHEY_SIMPLEX,
                    .56, (235, 235, 235), 1, cv2.LINE_AA)
    cv2.imwrite(str(path), canvas)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = {}
    paint_images, gray_images = [], []
    for fid in ACCEPTED_IDS:
        paint, spec = _accepted_authored(fid)
        paint_f = _paint_features(paint)
        data[fid] = {"paint": paint_f, "spec": _spec_features(spec)}
        paint_images.append((fid, paint))
        gray_images.append((fid, paint_f[2]))

    pairs = []
    for a, b in itertools.combinations(ACCEPTED_IDS, 2):
        low = abs(_corr(data[a]["paint"][0], data[b]["paint"][0]))
        edge = abs(_corr(data[a]["paint"][1], data[b]["paint"][1]))
        paint_score = .55 * low + .45 * edge
        spec_score, perm, rank, spec_edge = _spec_similarity(data[a]["spec"], data[b]["spec"])
        pairs.append({
            "a": a, "b": b, "paint_structure": round(paint_score, 6),
            "paint_low": round(low, 6), "paint_edge": round(edge, 6),
            "spec_topology": round(spec_score, 6),
            "spec_rank": round(rank, 6), "spec_edge": round(spec_edge, 6),
            "spec_permutation": list(perm),
        })
    pairs.sort(key=lambda row: max(row["paint_structure"], row["spec_topology"]), reverse=True)
    payload = {
        "schema": "spb-wilds-accepted-collision-audit/1",
        "accepted_count": len(ACCEPTED_IDS), "pair_count": len(pairs),
        "paint_threshold": .85, "spec_threshold": .85,
        "actionable": [row for row in pairs
                       if row["paint_structure"] >= .85 or row["spec_topology"] >= .85],
        "max_paint_pair": max(pairs, key=lambda row: row["paint_structure"]),
        "max_spec_pair": max(pairs, key=lambda row: row["spec_topology"]),
        "pairs": pairs,
    }
    count = len(ACCEPTED_IDS)
    (OUT / f"collision_audit_{count}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _montage(paint_images, OUT / f"accepted_{count}_paint_montage.png")
    _montage(gray_images, OUT / f"accepted_{count}_hue_null_montage.png", grayscale=True)
    print(json.dumps({k: payload[k] for k in (
        "accepted_count", "pair_count", "actionable", "max_paint_pair", "max_spec_pair")},
        indent=2))
    return 1 if payload["actionable"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
