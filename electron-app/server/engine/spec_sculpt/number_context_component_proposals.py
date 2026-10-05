"""Owner-neutral immutable proposal adapter for existing raw components."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

import cv2
import numpy as np


def component_proposal_candidates(
    canvas_shape: Sequence[int],
    layer_masks: Mapping[str, np.ndarray],
    components: Sequence[Mapping[str, Any]],
    min_pixels: int = 400,
) -> tuple[dict[str, Any], ...]:
    """Expose component masks without using their current layer as semantic authority."""
    height, width = int(canvas_shape[0]), int(canvas_shape[1])
    proposals = []
    connected = {}
    for layer, mask in layer_masks.items():
        binary = np.asarray(mask, bool).astype(np.uint8)
        _count, labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, 8)
        connected[str(layer)] = (labels, stats)
    for item in components:
        source_layer = str(item.get("layer") or "")
        if source_layer not in layer_masks:
            continue
        x, y, box_width, box_height = (int(value) for value in item["bbox"])
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(width, x + box_width), min(height, y + box_height)
        if x1 <= x0 or y1 <= y0:
            continue
        labels, stats = connected[source_layer]
        expected_area = item.get("area_px")
        candidates = []
        for label in range(1, len(stats)):
            sx, sy, sw, sh, area = (int(value) for value in stats[label])
            box_error = abs(sx - x) + abs(sy - y) + abs(sw - box_width) + abs(sh - box_height)
            area_error = 0.0 if expected_area is None else abs(area - int(expected_area)) / max(1, int(expected_area))
            candidates.append((box_error * 10.0 + area_error, label))
        if not candidates:
            continue
        _error, selected_label = min(candidates)
        local = np.ascontiguousarray(labels[y0:y1, x0:x1] == selected_label)
        pixels = int(np.count_nonzero(local))
        if pixels < min_pixels:
            continue
        local.setflags(write=False)
        digest = hashlib.sha256()
        digest.update(local.tobytes())
        digest.update(f"{x0},{y0},{x1-x0},{y1-y0},{source_layer}".encode("utf-8"))
        proposals.append({
            "proposal_id": "ncc:" + digest.hexdigest()[:16],
            "proposal_bbox": [x0, y0, x1 - x0, y1 - y0],
            "raw_support": local,
            "owner_neutral": True,
            "ownership_authority": False,
            "provenance": {
                "source_layer": source_layer,
                "component_index": int(item.get("component_index", -1)),
                "component_pixels": pixels,
            },
        })
    return tuple(proposals)


def component_area_fraction(raw_support: np.ndarray, canvas_shape: Sequence[int]) -> float:
    """Intrinsic mask area normalized by canvas resolution; no bbox position is used."""
    denominator = max(1, int(canvas_shape[0]) * int(canvas_shape[1]))
    return int(np.count_nonzero(np.asarray(raw_support, bool))) / denominator


__all__ = ["component_proposal_candidates", "component_area_fraction"]
