"""Immutable foreground-mask hypotheses for corroborated number contexts."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import cv2
import numpy as np


def _palette(pixels: np.ndarray, *, limit: int = 8) -> np.ndarray:
    values = np.asarray(pixels, np.uint8).reshape(-1, 3)
    if not len(values):
        return np.zeros((1, 3), np.float32)
    bins = (values // 16).astype(np.int16)
    unique, counts = np.unique(bins, axis=0, return_counts=True)
    return (unique[np.argsort(counts)[-limit:]] * 16 + 8).astype(np.float32)


def _distance(rgb: np.ndarray, palette: np.ndarray) -> np.ndarray:
    crop = np.asarray(rgb, np.float32)
    delta = crop[:, :, None, :] - np.asarray(palette, np.float32)[None, None, :, :]
    return np.sqrt(np.min(np.sum(delta * delta, axis=3), axis=2))


def _clean(mask: np.ndarray, *, minimum_area: int) -> np.ndarray:
    binary = np.asarray(mask, np.uint8)
    if not np.any(binary):
        return np.zeros(binary.shape, bool)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    result = np.zeros(binary.shape, bool)
    for label in range(1, count):
        if int(stats[label, cv2.CC_STAT_AREA]) >= int(minimum_area):
            result |= labels == label
    return result


def _raw_support(
    bbox: Sequence[int], instances: Sequence[Mapping[str, Any]],
) -> tuple[np.ndarray, list[str]]:
    x, y, width, height = (int(value) for value in bbox)
    result = np.zeros((height, width), bool)
    member_ids = []
    for instance in instances:
        ix, iy, iw, ih = (int(value) for value in instance["bbox"])
        x0, y0 = max(x, ix), max(y, iy)
        x1, y1 = min(x + width, ix + iw), min(y + height, iy + ih)
        if x1 <= x0 or y1 <= y0:
            continue
        local = np.asarray(instance["local_mask"], bool)
        result[y0 - y:y1 - y, x0 - x:x1 - x] |= local[
            y0 - iy:y1 - iy, x0 - ix:x1 - ix
        ]
        member_ids.append(str(instance.get("instance_id") or ""))
    return result, member_ids


def number_context_mask_hypotheses(
    rgb: np.ndarray, proposal: Mapping[str, Any], seed: Mapping[str, Any],
    instances: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return competing zero-authority masks and their immutable provenance."""
    x, y, width, height = (int(value) for value in proposal["bbox"])
    crop = np.asarray(rgb, np.uint8)[y:y + height, x:x + width]
    sx, sy, sw, sh = (int(value) for value in seed["bbox"])
    seed_mask = np.asarray(seed["local_mask"], bool)
    seed_pixels = np.asarray(rgb, np.uint8)[sy:sy + sh, sx:sx + sw][seed_mask]
    seed_palette = _palette(seed_pixels)

    border_pixels = np.concatenate((crop[0], crop[-1], crop[:, 0], crop[:, -1]), axis=0)
    border_palette = _palette(border_pixels, limit=12)
    seed_distance = _distance(crop, seed_palette)
    border_distance = _distance(crop, border_palette)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 45, 135) > 0
    raw, member_ids = _raw_support((x, y, width, height), instances)
    minimum_area = max(4, int(np.count_nonzero(seed_mask) * 0.02))

    palette_mask = _clean(seed_distance <= 40.0, minimum_area=minimum_area)
    contrast_mask = _clean(
        (border_distance >= 48.0) & (edges | (seed_distance <= 64.0)),
        minimum_area=minimum_area,
    )
    score = (
        0.38 * np.clip(1.0 - seed_distance / 72.0, 0.0, 1.0)
        + 0.27 * np.clip(border_distance / 96.0, 0.0, 1.0)
        + 0.15 * edges.astype(np.float32)
        + 0.20 * raw.astype(np.float32)
    )
    hybrid_mask = _clean(score >= 0.52, minimum_area=minimum_area)

    grabcut_state = np.full((height, width), cv2.GC_PR_BGD, np.uint8)
    border_width = max(1, min(3, min(width, height) // 12))
    grabcut_state[:border_width] = cv2.GC_BGD
    grabcut_state[-border_width:] = cv2.GC_BGD
    grabcut_state[:, :border_width] = cv2.GC_BGD
    grabcut_state[:, -border_width:] = cv2.GC_BGD
    probable = (seed_distance <= 48.0) & (border_distance >= 24.0)
    grabcut_state[probable] = cv2.GC_PR_FGD
    grabcut_state[raw] = cv2.GC_FGD
    graphcut_mask = np.zeros((height, width), bool)
    if np.any(grabcut_state >= cv2.GC_PR_FGD) and np.any(grabcut_state == cv2.GC_BGD):
        background = np.zeros((1, 65), np.float64)
        foreground = np.zeros((1, 65), np.float64)
        try:
            cv2.grabCut(
                cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), grabcut_state, None,
                background, foreground, 3, cv2.GC_INIT_WITH_MASK,
            )
            graphcut_mask = _clean(
                (grabcut_state == cv2.GC_FGD) | (grabcut_state == cv2.GC_PR_FGD),
                minimum_area=minimum_area,
            )
        except cv2.error:
            graphcut_mask = np.zeros((height, width), bool)

    masks = {
        "raw_instance_union": raw,
        "seed_palette": palette_mask,
        "border_contrast": contrast_mask,
        "hybrid_evidence": hybrid_mask,
        "seeded_graphcut": graphcut_mask,
    }
    for mask in masks.values():
        mask.setflags(write=False)
    return {
        "schema": "smart-tga-number-context-mask-hypotheses-v1",
        "bbox": [x, y, width, height],
        "proposal_id": str(proposal.get("proposal_id") or ""),
        "seed_instance_id": str(proposal.get("seed_instance_id") or ""),
        "raw_member_instance_ids": member_ids,
        "minimum_component_area": minimum_area,
        "masks": masks,
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }


__all__ = ["number_context_mask_hypotheses"]
