"""Owner-neutral local-contrast proposals for small repeated number copies.

Global probability quantiles miss compact copies when a paint contains much
stronger large decals.  This adapter finds locally prominent map regions,
derives intrinsic palette subinstances, then uses normalized template position
only to corroborate and bound the review set.  It never casts a vote or owns a
pixel; a separate frozen semantic scorer remains the sole decision authority.
"""

from __future__ import annotations

import hashlib
from typing import Mapping, Sequence

import cv2
import numpy as np

from .decal_subinstances import derive_intrinsic_subinstances
from .number_map_family_features import map_family_template_position_features
from .number_object_segmentation import project_local_support


def _intersection(first: Sequence[int], second: Sequence[int]) -> int:
    ax, ay, aw, ah = map(int, first)
    bx, by, bw, bh = map(int, second)
    return max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
        0, min(ay + ah, by + bh) - max(ay, by),
    )


def local_contrast_probability_proposals(
    probability: np.ndarray,
    output_shape: Sequence[int],
    *,
    window_size: int = 24,
    z_scores: Sequence[float] = (0.50, 0.75),
    min_model_pixels: int = 2,
) -> tuple[dict, ...]:
    """Expose locally prominent map components without semantic ownership."""
    values = np.asarray(probability, np.float32)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("probability must be a finite HxW array")
    out_height, out_width = map(int, output_shape)
    size = int(window_size)
    if size < 3:
        raise ValueError("window_size must be at least three pixels")
    mean = cv2.boxFilter(values, cv2.CV_32F, (size, size), normalize=True)
    square = cv2.boxFilter(values * values, cv2.CV_32F, (size, size), normalize=True)
    std = np.sqrt(np.maximum(0.0, square - mean * mean))
    global_floor = float(np.quantile(values, 0.50))
    proposals = []
    for z_score in z_scores:
        binary = (
            (values >= mean + float(z_score) * std)
            & (values >= global_floor)
            & ((values - mean) >= 0.01)
        ).astype(np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        count, labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, 8)
        for label in range(1, count):
            x, y, width, height, area = map(int, stats[label])
            if area < int(min_model_pixels):
                continue
            x0 = max(0, int(np.floor(x * out_width / values.shape[1])))
            y0 = max(0, int(np.floor(y * out_height / values.shape[0])))
            x1 = min(out_width, int(np.ceil((x + width) * out_width / values.shape[1])))
            y1 = min(out_height, int(np.ceil((y + height) * out_height / values.shape[0])))
            support = cv2.resize(
                (labels[y:y + height, x:x + width] == label).astype(np.uint8),
                (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST,
            ) > 0
            support.setflags(write=False)
            digest = hashlib.sha256()
            digest.update(support.tobytes())
            digest.update(f"{x0},{y0},{x1-x0},{y1-y0},{size},{z_score:.3f}".encode())
            selected = values[labels == label]
            proposals.append({
                "proposal_id": "number-local-map:" + digest.hexdigest()[:16],
                "proposal_bbox": [x0, y0, x1 - x0, y1 - y0],
                "raw_support": support,
                "owner_neutral": True,
                "ownership_authority": False,
                "provenance": {
                    "source_stage": "number_object_local_contrast_probability_map",
                    "window_size": size, "z_score": float(z_score),
                    "model_pixels": area,
                    "mean_probability": float(selected.mean()),
                    "max_probability": float(selected.max()),
                },
            })
    return tuple(proposals)


def palette_panel_local_copy_proposals(
    rgb: np.ndarray,
    probability: np.ndarray,
    panel_map: Mapping,
    *,
    maximum_per_number_block: int = 3,
) -> tuple[dict, ...]:
    """Return a small, position-corroborated set of intrinsic subinstances."""
    image = np.asarray(rgb, np.uint8)
    canvas_shape = image.shape[:2]
    probability_canvas = cv2.resize(
        np.asarray(probability, np.float32),
        (image.shape[1], image.shape[0]), interpolation=cv2.INTER_LINEAR,
    )
    raw = local_contrast_probability_proposals(probability, canvas_shape)
    palette = []
    for proposal in raw:
        x, y, width, height = map(int, proposal["proposal_bbox"])
        rectangle = np.ones((height, width), bool)
        broad_position = map_family_template_position_features(
            proposal["proposal_bbox"], rectangle, canvas_shape, panel_map,
        )
        if float(broad_position[0]) <= 0.0:
            continue
        crop = image[y:y + height, x:x + width]
        for subinstance in derive_intrinsic_subinstances(
            crop, rectangle, min_pixels=8, min_parent_fraction=0.003,
        ):
            sx, sy, sw, sh = subinstance.bbox
            support = np.ascontiguousarray(
                subinstance.local_mask[sy:sy + sh, sx:sx + sw], dtype=bool,
            )
            bbox = [x + sx, y + sy, sw, sh]
            position = map_family_template_position_features(
                bbox, support, canvas_shape, panel_map,
            )
            if float(position[0]) < 0.30:
                continue
            local_probability = probability_canvas[y + sy:y + sy + sh, x + sx:x + sx + sw]
            selected = local_probability[support]
            model_support = project_local_support(support, bbox, canvas_shape, probability.shape[0])
            maximum = float(selected.max()) if selected.size else 0.0
            digest = hashlib.sha256()
            digest.update(support.tobytes())
            digest.update(f"{bbox},{subinstance.hypothesis}".encode())
            support.setflags(write=False)
            palette.append({
                "proposal_id": "number-local-palette:" + digest.hexdigest()[:16],
                "proposal_bbox": bbox, "raw_support": support,
                "owner_neutral": True, "ownership_authority": False,
                "provenance": {
                    "source_stage": "number_object_local_palette_subinstance",
                    "relative_quantile": float(np.mean(probability <= maximum)),
                    "threshold": float(selected.mean()) if selected.size else 0.0,
                    "model_pixels": int(np.count_nonzero(model_support)),
                    "mean_probability": float(selected.mean()) if selected.size else 0.0,
                    "max_probability": maximum,
                    "palette_role": subinstance.source_role,
                    "parent_bbox": list(map(int, proposal["proposal_bbox"])),
                    "template_number_fraction": float(position[0]),
                    "template_sponsor_fraction": float(position[1]),
                },
            })

    unique = {}
    for proposal in palette:
        unique.setdefault(
            (tuple(proposal["proposal_bbox"]), proposal["raw_support"].tobytes()), proposal,
        )
    palette = list(unique.values())
    scaled_blocks = []
    for block in panel_map.get("number_blocks", ()):
        bx, by, bw, bh = map(int, block["bbox"])
        scaled_blocks.append((str(block["name"]), [
            int(round(bx * image.shape[1] / 1024.0)),
            int(round(by * image.shape[0] / 1024.0)),
            int(round(bw * image.shape[1] / 1024.0)),
            int(round(bh * image.shape[0] / 1024.0)),
        ]))
    ranked = []
    for block_name, block_bbox in scaled_blocks:
        candidates = []
        for proposal in palette:
            if not _intersection(proposal["proposal_bbox"], block_bbox):
                continue
            provenance = proposal["provenance"]
            score = float(provenance["template_number_fraction"]) * np.sqrt(
                max(1, int(np.count_nonzero(proposal["raw_support"])))
            )
            candidates.append((score, proposal))
        kept = []
        for score, proposal in sorted(
            candidates, key=lambda item: (-item[0], item[1]["proposal_id"]),
        ):
            bbox = proposal["proposal_bbox"]
            area = max(1, int(bbox[2]) * int(bbox[3]))
            if any(
                _intersection(bbox, item["proposal_bbox"]) / min(
                    area,
                    max(1, int(item["proposal_bbox"][2]) * int(item["proposal_bbox"][3])),
                ) >= 0.70
                for item in kept
            ):
                continue
            kept.append({
                **proposal,
                "provenance": {
                    **proposal["provenance"],
                    "panel_block": block_name, "panel_rank_score": float(score),
                },
            })
            if len(kept) >= int(maximum_per_number_block):
                break
        ranked.extend(kept)
    result = {item["proposal_id"]: item for item in ranked}
    return tuple(sorted(result.values(), key=lambda item: item["proposal_id"]))


__all__ = [
    "local_contrast_probability_proposals", "palette_panel_local_copy_proposals",
]
