"""Proposal-level score aggregation and within-proposal conformal masks."""

from __future__ import annotations

from typing import Mapping

import cv2
import numpy as np


PROPOSAL_FEATURE_NAMES = (
    "score_mean", "score_std", "score_q50", "score_q75", "score_q90",
    "score_q95", "score_q99", "score_max", "score_gt_50", "score_gt_70",
    "score_gt_85", "score_gt_90", "raw_fraction", "union_fraction",
    "palette_fraction", "contrast_fraction", "hybrid_fraction", "graphcut_fraction",
    "raw_palette_iou", "raw_contrast_iou", "raw_hybrid_iou", "raw_graphcut_iou",
    "raw_component_count", "union_component_count", "raw_tight_fill", "raw_tight_aspect",
)


def proposal_score_features(scores: np.ndarray, hypotheses: Mapping[str, np.ndarray]) -> dict[str, float]:
    score = np.asarray(scores, np.float32)
    raw = np.asarray(hypotheses["raw_instance_union"], bool)
    supports = [
        np.asarray(hypotheses[name], bool) for name in (
            "seed_palette", "border_contrast", "hybrid_evidence", "seeded_graphcut",
        )
    ]
    union = np.logical_or.reduce([raw, *supports])
    values = score[union] if np.any(union) else score.ravel()
    quantiles = np.quantile(values, (0.50, 0.75, 0.90, 0.95, 0.99))
    result = {
        "score_mean": float(np.mean(values)), "score_std": float(np.std(values)),
        "score_q50": float(quantiles[0]), "score_q75": float(quantiles[1]),
        "score_q90": float(quantiles[2]), "score_q95": float(quantiles[3]),
        "score_q99": float(quantiles[4]), "score_max": float(np.max(values)),
        "score_gt_50": float(np.mean(values >= 0.50)), "score_gt_70": float(np.mean(values >= 0.70)),
        "score_gt_85": float(np.mean(values >= 0.85)), "score_gt_90": float(np.mean(values >= 0.90)),
        "raw_fraction": float(np.mean(raw)), "union_fraction": float(np.mean(union)),
        "palette_fraction": float(np.mean(supports[0])), "contrast_fraction": float(np.mean(supports[1])),
        "hybrid_fraction": float(np.mean(supports[2])), "graphcut_fraction": float(np.mean(supports[3])),
    }
    for name, mask in zip(("palette", "contrast", "hybrid", "graphcut"), supports):
        denominator = int(np.count_nonzero(raw | mask))
        result[f"raw_{name}_iou"] = int(np.count_nonzero(raw & mask)) / denominator if denominator else 1.0
    result["raw_component_count"] = float(max(0, cv2.connectedComponents(raw.astype(np.uint8), 8)[0] - 1))
    result["union_component_count"] = float(max(0, cv2.connectedComponents(union.astype(np.uint8), 8)[0] - 1))
    rows, columns = np.nonzero(raw)
    if len(columns):
        width, height = int(columns.max() - columns.min() + 1), int(rows.max() - rows.min() + 1)
        result["raw_tight_fill"] = float(np.count_nonzero(raw) / max(1, width * height))
        result["raw_tight_aspect"] = float(np.log(max(1, width) / max(1, height)))
    else:
        result["raw_tight_fill"] = 0.0
        result["raw_tight_aspect"] = 0.0
    return result


def select_ranked_pixels(scores: np.ndarray, raw_support: np.ndarray, fraction: float) -> np.ndarray:
    raw = np.asarray(raw_support, bool)
    indexes = np.flatnonzero(raw.ravel())
    result = np.zeros(raw.shape, bool)
    if not len(indexes) or fraction <= 0.0:
        result.setflags(write=False)
        return result
    count = max(1, min(len(indexes), int(np.ceil(len(indexes) * float(fraction)))))
    values = np.asarray(scores, np.float32).ravel()[indexes]
    chosen = indexes[np.argpartition(values, len(values) - count)[-count:]]
    result.ravel()[chosen] = True
    result.setflags(write=False)
    return result


__all__ = ["PROPOSAL_FEATURE_NAMES", "proposal_score_features", "select_ranked_pixels"]
