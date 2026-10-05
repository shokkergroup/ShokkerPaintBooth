"""Intrinsic member features for assembling corroborated number contexts."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np
import cv2


SCALAR_FIELDS = (
    "area_fraction", "fill_ratio", "edge_density", "strong_gradient_fraction",
    "texture_entropy", "perceptual_lightness", "perceptual_chroma",
    "ocr_alpha_coverage", "ocr_digit_coverage", "ocr_max_coverage",
)


def member_feature_mapping(
    member: Mapping[str, Any], proposal: Mapping[str, Any], seed: Mapping[str, Any],
) -> dict[str, float]:
    x, y, width, height = (float(value) for value in member["bbox"])
    px, py, proposal_width, proposal_height = (float(value) for value in proposal["bbox"])
    _sx, _sy, seed_width, seed_height = (float(value) for value in seed["bbox"])
    center_x, center_y = x + width / 2.0, y + height / 2.0
    proposal_center_x = px + proposal_width / 2.0
    proposal_center_y = py + proposal_height / 2.0
    intersection = max(0.0, min(x + width, px + proposal_width) - max(x, px)) * max(
        0.0, min(y + height, py + proposal_height) - max(y, py)
    )
    result: dict[str, float] = {}
    for field in SCALAR_FIELDS:
        result[f"member_{field}"] = float(member.get(field) or 0.0)
    for index, value in enumerate(member.get("mean_rgb") or (0.0, 0.0, 0.0)):
        result[f"member_mean_rgb_{index}"] = float(value)
    for index, value in enumerate(member.get("std_rgb") or (0.0, 0.0, 0.0)):
        result[f"member_std_rgb_{index}"] = float(value)
    for index, value in enumerate(member.get("shape_occupancy") or (0.0,) * 16):
        result[f"member_shape_{index}"] = float(value)
    result.update({
        "relative_center_x": (center_x - proposal_center_x) / max(1.0, proposal_width),
        "relative_center_y": (center_y - proposal_center_y) / max(1.0, proposal_height),
        "relative_width": width / max(1.0, proposal_width),
        "relative_height": height / max(1.0, proposal_height),
        "relative_area": width * height / max(1.0, proposal_width * proposal_height),
        "proposal_containment": intersection / max(1.0, width * height),
        "member_log_aspect": math.log(max(width, 1.0) / max(height, 1.0)),
    })
    for field in SCALAR_FIELDS:
        result[f"seed_delta_{field}"] = abs(
            float(member.get(field) or 0.0) - float(seed.get(field) or 0.0)
        )
    member_rgb = np.asarray(member.get("mean_rgb") or (0.0, 0.0, 0.0), dtype=np.float64)
    seed_rgb = np.asarray(seed.get("mean_rgb") or (0.0, 0.0, 0.0), dtype=np.float64)
    result["seed_mean_rgb_distance"] = float(np.linalg.norm(member_rgb - seed_rgb))
    result["seed_aspect_delta"] = abs(
        math.log(max(width, 1.0) / max(height, 1.0))
        - math.log(max(seed_width, 1.0) / max(seed_height, 1.0))
    )
    return result


def assemble_member_mask(
    proposal_bbox: Sequence[int], members: Sequence[Mapping[str, Any]],
    scores: Sequence[float], *, threshold: float,
) -> tuple[np.ndarray, list[str]]:
    x, y, width, height = (int(value) for value in proposal_bbox)
    result = np.zeros((height, width), bool)
    selected = []
    for member, score in zip(members, scores):
        if float(score) < float(threshold):
            continue
        mx, my, mw, mh = (int(value) for value in member["bbox"])
        x0, y0 = max(x, mx), max(y, my)
        x1, y1 = min(x + width, mx + mw), min(y + height, my + mh)
        if x1 <= x0 or y1 <= y0:
            continue
        local = np.asarray(member["local_mask"], bool)
        result[y0 - y:y1 - y, x0 - x:x1 - x] |= local[
            y0 - my:y1 - my, x0 - mx:x1 - mx
        ]
        selected.append(str(member.get("instance_id") or ""))
    result.setflags(write=False)
    return result, selected


def grow_member_mask(
    rgb: np.ndarray, proposal_bbox: Sequence[int], core_mask: np.ndarray, *,
    color_distance: float = 56.0, support_radius: int = 7,
) -> np.ndarray:
    """Grow a precise raw-member core through connected source-palette pixels."""
    x, y, width, height = (int(value) for value in proposal_bbox)
    core = np.asarray(core_mask, bool)
    if core.shape != (height, width):
        raise ValueError("member core mask must match proposal bbox")
    if not np.any(core):
        result = np.zeros(core.shape, bool)
        result.setflags(write=False)
        return result
    crop = np.asarray(rgb, np.uint8)[y:y + height, x:x + width]
    pixels = crop[core]
    bins = (pixels // 16).astype(np.int16)
    unique, counts = np.unique(bins, axis=0, return_counts=True)
    palette = (unique[np.argsort(counts)[-12:]] * 16 + 8).astype(np.float32)
    delta = crop.astype(np.float32)[:, :, None, :] - palette[None, None, :, :]
    distance = np.sqrt(np.min(np.sum(delta * delta, axis=3), axis=2))
    candidate = (distance <= float(color_distance)) | core
    candidate = cv2.morphologyEx(candidate.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    radius = max(1, int(support_radius))
    support = cv2.dilate(core.astype(np.uint8), np.ones((radius, radius), np.uint8)) > 0
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, 8)
    result = np.zeros(core.shape, bool)
    minimum_area = max(4, int(np.count_nonzero(core) * 0.01))
    for label in range(1, count):
        component = labels == label
        if int(stats[label, cv2.CC_STAT_AREA]) >= minimum_area and np.any(component & support):
            result |= component
    result |= core
    result.setflags(write=False)
    return result


__all__ = [
    "SCALAR_FIELDS", "assemble_member_mask", "grow_member_mask", "member_feature_mapping",
]
