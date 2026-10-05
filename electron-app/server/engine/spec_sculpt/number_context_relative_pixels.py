"""Palette-relative and D4-invariant Number-core pixel features."""

from __future__ import annotations

from typing import Mapping, Sequence

import cv2
import numpy as np


FEATURE_NAMES = (
    "rank_r", "rank_g", "rank_b", "rank_l", "rank_a", "rank_lab_b",
    "seed_delta_r", "seed_delta_g", "seed_delta_b",
    "seed_delta_l", "seed_delta_a", "seed_delta_lab_b",
    "local_luma_contrast", "gradient_rank", "texture_rank",
    "d4_near_edge", "d4_far_edge", "d4_center_radius", "d4_edge_product",
    "raw_support", "palette_support", "contrast_support", "hybrid_support",
    "graphcut_support", "raw_density_3", "raw_density_9", "raw_density_21",
    "union_density_3", "union_density_9", "union_density_21",
    "distance_to_raw", "distance_to_union",
)


def _rank_channel(channel: np.ndarray) -> np.ndarray:
    values = np.asarray(channel, np.uint8)
    counts = np.bincount(values.ravel(), minlength=256)
    cumulative = np.cumsum(counts) - counts / 2.0
    return (cumulative[values] / max(1.0, float(values.size))).astype(np.float32)


def _robust_delta(values: np.ndarray, seed: np.ndarray) -> np.ndarray:
    reference = values[seed] if np.any(seed) else values.reshape(-1, values.shape[-1])
    center = np.median(reference, axis=0)
    scale = np.percentile(reference, 75, axis=0) - np.percentile(reference, 25, axis=0)
    return np.clip((values.astype(np.float32) - center) / np.maximum(scale, 12.0), -4.0, 4.0)


def relative_pixel_feature_cube(
    rgb: np.ndarray, proposal_bbox: Sequence[int], hypotheses: Mapping[str, np.ndarray],
) -> np.ndarray:
    x, y, width, height = (int(value) for value in proposal_bbox)
    crop = np.asarray(rgb, np.uint8)[y:y + height, x:x + width, :3]
    if crop.shape[:2] != (height, width):
        raise ValueError("proposal bbox must be inside source")
    lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    gradient = np.hypot(
        cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3),
        cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3),
    )
    mean = cv2.blur(gray, (7, 7))
    texture = np.sqrt(np.maximum(0.0, cv2.blur(gray * gray, (7, 7)) - mean * mean))
    supports = [
        np.asarray(hypotheses[name], bool) for name in (
            "raw_instance_union", "seed_palette", "border_contrast",
            "hybrid_evidence", "seeded_graphcut",
        )
    ]
    raw = supports[0]
    union = np.logical_or.reduce(supports)
    rgb_delta = _robust_delta(crop, raw)
    lab_delta = _robust_delta(lab, raw)
    rows, columns = np.indices((height, width), dtype=np.float32)
    nx = columns / max(1.0, width - 1.0)
    ny = rows / max(1.0, height - 1.0)
    edge_x, edge_y = np.minimum(nx, 1.0 - nx), np.minimum(ny, 1.0 - ny)
    near_edge, far_edge = np.minimum(edge_x, edge_y), np.maximum(edge_x, edge_y)
    diagonal = max(1.0, float(np.hypot(width, height)))
    density = [
        cv2.blur(mask.astype(np.float32), (kernel, kernel))
        for mask in (raw, union) for kernel in (3, 9, 21)
    ]
    distance_raw = cv2.distanceTransform((~raw).astype(np.uint8), cv2.DIST_L2, 3) / diagonal
    distance_union = cv2.distanceTransform((~union).astype(np.uint8), cv2.DIST_L2, 3) / diagonal
    cube = np.dstack([
        *(_rank_channel(crop[..., index]) for index in range(3)),
        *(_rank_channel(lab[..., index]) for index in range(3)),
        rgb_delta, lab_delta,
        (gray - mean) / np.maximum(texture, 0.03),
        _rank_channel(np.clip(gradient * 255.0, 0, 255).astype(np.uint8)),
        _rank_channel(np.clip(texture * 1024.0, 0, 255).astype(np.uint8)),
        near_edge, far_edge, np.hypot(nx - 0.5, ny - 0.5), edge_x * edge_y,
        *(mask.astype(np.float32) for mask in supports), *density,
        distance_raw, distance_union,
    ]).astype(np.float32, copy=False)
    if cube.shape[2] != len(FEATURE_NAMES):
        raise AssertionError("relative pixel feature schema drift")
    return cube


__all__ = ["FEATURE_NAMES", "relative_pixel_feature_cube"]
