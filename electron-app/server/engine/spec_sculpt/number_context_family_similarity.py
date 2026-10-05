"""Orientation-invariant visual evidence for repeated Number decal families."""

from __future__ import annotations

from typing import Iterable

import cv2
import numpy as np


def normalized_visual_descriptor(
    rgb: np.ndarray, raw_support: np.ndarray, size: int = 32,
) -> np.ndarray:
    """Return a tight, palette-relative grayscale descriptor with no position input."""
    image = np.asarray(rgb, np.uint8)
    support = np.asarray(raw_support, bool)
    rows, columns = np.nonzero(support)
    if not len(columns):
        result = np.zeros((size, size), np.float32)
        result.setflags(write=False)
        return result
    y0, y1 = int(rows.min()), int(rows.max()) + 1
    x0, x1 = int(columns.min()), int(columns.max()) + 1
    local_support = support[y0:y1, x0:x1]
    gray = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_RGB2GRAY).astype(np.float32)
    values = gray[local_support]
    gray = np.clip((gray - float(values.mean())) / (float(values.std()) + 1e-5), -2.0, 2.0)
    gray = (gray / 4.0 + 0.5) * local_support
    result = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)
    result.setflags(write=False)
    return result


def d4_cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    """Maximum cosine similarity over rotations and horizontal mirrors."""
    source = np.asarray(left, np.float32)
    target = np.asarray(right, np.float32).ravel()
    target_norm = float(np.linalg.norm(target)) + 1e-6
    best = -1.0
    for mirrored in (source, np.fliplr(source)):
        for turns in range(4):
            candidate = np.rot90(mirrored, turns).ravel()
            similarity = float(np.dot(candidate, target) / ((float(np.linalg.norm(candidate)) + 1e-6) * target_norm))
            best = max(best, similarity)
    return best


def normalized_score_topology(
    scores: np.ndarray, raw_support: np.ndarray, size: int = 32,
) -> np.ndarray:
    """Normalize an intrinsic pixel-score map inside its tight raw support."""
    score = np.asarray(scores, np.float32)
    support = np.asarray(raw_support, bool)
    rows, columns = np.nonzero(support)
    if not len(columns):
        result = np.zeros((size, size), np.float32)
        result.setflags(write=False)
        return result
    y0, y1 = int(rows.min()), int(rows.max()) + 1
    x0, x1 = int(columns.min()), int(columns.max()) + 1
    local_support = support[y0:y1, x0:x1]
    local = score[y0:y1, x0:x1].copy()
    values = local[local_support]
    local = np.clip((local - float(values.mean())) / (float(values.std()) + 1e-5), -2.0, 2.0)
    local = (local / 4.0 + 0.5) * local_support
    result = cv2.resize(local, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)
    result.setflags(write=False)
    return result


def mask_iou(left: np.ndarray, right: np.ndarray) -> float:
    """Intersection-over-union of immutable proposal masks in common canvas space."""
    a, b = np.asarray(left, bool), np.asarray(right, bool)
    if a.shape != b.shape:
        raise ValueError("proposal masks must share canvas space")
    denominator = int(np.count_nonzero(a | b))
    return int(np.count_nonzero(a & b)) / denominator if denominator else 1.0


def prototype_margin(
    descriptor: np.ndarray,
    positive_prototypes: Iterable[np.ndarray],
    control_prototypes: Iterable[np.ndarray],
) -> float:
    """Number-family similarity minus closest reviewed hard-negative similarity."""
    positives = [d4_cosine_similarity(descriptor, item) for item in positive_prototypes]
    controls = [d4_cosine_similarity(descriptor, item) for item in control_prototypes]
    if not positives or not controls:
        raise ValueError("both positive and control prototypes are required")
    return max(positives) - max(controls)


__all__ = [
    "normalized_visual_descriptor", "normalized_score_topology",
    "d4_cosine_similarity", "mask_iou", "prototype_margin",
]
