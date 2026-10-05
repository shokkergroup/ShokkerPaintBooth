"""Owner-neutral proposal-local pixel features for Number-core selection."""

from __future__ import annotations

from typing import Mapping, Sequence

import cv2
import numpy as np


FEATURE_NAMES = (
    "red", "green", "blue", "lab_l", "lab_a", "lab_b", "gray",
    "gradient", "local_std", "local_x", "local_y", "global_x", "global_y",
    "raw_support", "palette_support", "contrast_support", "hybrid_support",
    "graphcut_support", "distance_to_raw", "distance_to_any_support",
)


def pixel_feature_cube(
    rgb: np.ndarray, proposal_bbox: Sequence[int], hypotheses: Mapping[str, np.ndarray],
) -> np.ndarray:
    x, y, width, height = (int(value) for value in proposal_bbox)
    crop = np.asarray(rgb, np.uint8)[y:y + height, x:x + width, :3]
    if crop.shape[:2] != (height, width):
        raise ValueError("proposal bbox must be inside source")
    scaled = crop.astype(np.float32) / 255.0
    lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB).astype(np.float32) / 255.0
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gradient = np.clip(np.hypot(gx, gy), 0.0, 1.0)
    mean = cv2.blur(gray, (5, 5))
    local_std = np.sqrt(np.maximum(0.0, cv2.blur(gray * gray, (5, 5)) - mean * mean))
    rows, columns = np.indices((height, width), dtype=np.float32)
    raw = np.asarray(hypotheses["raw_instance_union"], bool)
    supports = [
        raw,
        np.asarray(hypotheses["seed_palette"], bool),
        np.asarray(hypotheses["border_contrast"], bool),
        np.asarray(hypotheses["hybrid_evidence"], bool),
        np.asarray(hypotheses["seeded_graphcut"], bool),
    ]
    union = np.logical_or.reduce(supports)
    diagonal = max(1.0, float(np.hypot(width, height)))
    distance_raw = cv2.distanceTransform((~raw).astype(np.uint8), cv2.DIST_L2, 3) / diagonal
    distance_any = cv2.distanceTransform((~union).astype(np.uint8), cv2.DIST_L2, 3) / diagonal
    cube = np.dstack([
        scaled, lab, gray, gradient, local_std,
        columns / max(1.0, width - 1.0), rows / max(1.0, height - 1.0),
        (columns + x) / 1023.0, (rows + y) / 1023.0,
        *(mask.astype(np.float32) for mask in supports), distance_raw, distance_any,
    ]).astype(np.float32, copy=False)
    if cube.shape[2] != len(FEATURE_NAMES):
        raise AssertionError("pixel feature schema drift")
    return cube


__all__ = ["FEATURE_NAMES", "pixel_feature_cube"]
