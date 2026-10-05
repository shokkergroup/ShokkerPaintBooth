"""Portable, zero-authority Smart TGA number-family shadow scorer.

The scorer compares immutable owner-neutral decal instances.  A pre-existing
Number proposal may act as an anchor, but pair similarity can only be emitted
as telemetry: it never creates ownership, changes masks, or adds pixels.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


SCALAR_FIELDS = (
    "area_fraction", "fill_ratio", "edge_density", "texture_entropy",
    "strong_gradient_fraction", "perceptual_lightness", "perceptual_chroma",
    "ocr_alpha_coverage", "ocr_digit_coverage", "ocr_max_coverage",
)
DEFAULT_MODEL_PATH = Path(__file__).with_name("models") / "smart_tga_number_family_cycle694_v3.npz"


def _grid(mask: np.ndarray, size: int) -> np.ndarray:
    source = np.asarray(mask, dtype=np.float64)
    height, width = source.shape
    result = np.zeros((size, size), dtype=np.float64)
    for row in range(size):
        y0 = row * height // size
        y1 = max((row + 1) * height // size, y0 + 1)
        for column in range(size):
            x0 = column * width // size
            x1 = max((column + 1) * width // size, x0 + 1)
            result[row, column] = float(np.mean(source[y0:min(y1, height), x0:min(x1, width)]))
    return result


def _d4_distances(left: np.ndarray, right: np.ndarray) -> tuple[float, float]:
    transforms = []
    for turns in range(4):
        rotated = np.rot90(right, turns)
        transforms.extend((rotated, np.fliplr(rotated)))
    l1 = min(float(np.mean(np.abs(left - item))) for item in transforms)
    left_vector = left.ravel()
    left_norm = float(np.linalg.norm(left_vector))
    cosine = []
    for item in transforms:
        right_vector = item.ravel()
        denominator = left_norm * float(np.linalg.norm(right_vector))
        cosine.append(float(np.dot(left_vector, right_vector) / denominator) if denominator else 0.0)
    return l1, max(cosine)


def _component_count(binary: np.ndarray, *, count_holes: bool = False) -> int:
    target = ~binary if count_holes else binary
    seen = np.zeros(target.shape, dtype=bool)
    count = 0
    height, width = target.shape
    for y in range(height):
        for x in range(width):
            if not target[y, x] or seen[y, x]:
                continue
            stack = [(y, x)]
            seen[y, x] = True
            touches_border = False
            while stack:
                cy, cx = stack.pop()
                touches_border = touches_border or cy in {0, height - 1} or cx in {0, width - 1}
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and target[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if not count_holes or not touches_border:
                count += 1
    return count


def _mask_topology(mask: np.ndarray) -> dict[str, float]:
    grid = _grid(mask, 8)
    binary = grid >= 0.30
    edge = np.concatenate((grid[0], grid[-1], grid[1:-1, 0], grid[1:-1, -1]))
    return {
        "component_count": float(_component_count(binary)),
        "hole_count": float(_component_count(binary, count_holes=True)),
        "row_projection_std": float(np.std(np.mean(grid, axis=1))),
        "column_projection_std": float(np.std(np.mean(grid, axis=0))),
        "horizontal_transition": float(np.mean(np.abs(np.diff(grid, axis=1)))),
        "vertical_transition": float(np.mean(np.abs(np.diff(grid, axis=0)))),
        "center_edge_delta": float(np.mean(grid[2:6, 2:6]) - np.mean(edge)),
    }


def _safe_log_ratio(left: float, right: float) -> float:
    return abs(math.log(max(left, 1e-8) / max(right, 1e-8)))


def _aspect_invariant(record: Mapping[str, Any]) -> float:
    value = max(float(record.get("aspect_ratio") or 1.0), 1e-8)
    return max(value, 1.0 / value)


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    a, b = set(left), set(right)
    return len(a & b) / len(a | b) if a or b else 0.0


def _hue_distance(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    delta = abs(float(left.get("perceptual_hue_degrees") or 0.0) - float(right.get("perceptual_hue_degrees") or 0.0)) % 360.0
    return min(delta, 360.0 - delta) / 180.0


def _bbox_relationship(left: Mapping[str, Any], right: Mapping[str, Any]) -> tuple[float, float, float]:
    ax, ay, aw, ah = (float(value) for value in (left.get("bbox_normalized") or (0, 0, 0, 0)))
    bx, by, bw, bh = (float(value) for value in (right.get("bbox_normalized") or (0, 0, 0, 0)))
    intersection = max(0.0, min(ax + aw, bx + bw) - max(ax, bx)) * max(
        0.0, min(ay + ah, by + bh) - max(ay, by)
    )
    area_a, area_b = max(aw * ah, 1e-12), max(bw * bh, 1e-12)
    iou = intersection / max(area_a + area_b - intersection, 1e-12)
    overlap_min = intersection / min(area_a, area_b)
    center_distance = math.hypot((ax + aw / 2) - (bx + bw / 2), (ay + ah / 2) - (by + bh / 2)) / math.sqrt(2.0)
    return iou, overlap_min, center_distance


def pair_features(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, float]:
    shape_l1, shape_cosine = _d4_distances(
        np.asarray(left["shape_occupancy"], dtype=np.float64).reshape(4, 4),
        np.asarray(right["shape_occupancy"], dtype=np.float64).reshape(4, 4),
    )
    mask_l1, mask_cosine = _d4_distances(_grid(left["local_mask"], 8), _grid(right["local_mask"], 8))
    left_rgb = np.asarray(left.get("mean_rgb") or (0.0, 0.0, 0.0), dtype=np.float64)
    right_rgb = np.asarray(right.get("mean_rgb") or (0.0, 0.0, 0.0), dtype=np.float64)
    bbox_iou, bbox_overlap_min, bbox_center_distance = _bbox_relationship(left, right)
    result = {
        "shape_d4_l1": shape_l1,
        "shape_d4_cosine": shape_cosine,
        "mask8_d4_l1": mask_l1,
        "mask8_d4_cosine": mask_cosine,
        "area_log_ratio": _safe_log_ratio(float(left.get("area_fraction") or 0.0), float(right.get("area_fraction") or 0.0)),
        "aspect_log_ratio": _safe_log_ratio(_aspect_invariant(left), _aspect_invariant(right)),
        "mean_rgb_distance": float(np.linalg.norm(left_rgb - right_rgb) / (255.0 * math.sqrt(3.0))),
        "hue_circular_distance": _hue_distance(left, right),
        "palette_role_match": float(left.get("palette_role") == right.get("palette_role")),
        "proposal_conflict_any": float(bool(left.get("proposal_conflict")) or bool(right.get("proposal_conflict"))),
        "proposed_owner_jaccard": _jaccard(left.get("proposed_owners") or (), right.get("proposed_owners") or ()),
        "source_stage_jaccard": _jaccard(left.get("source_stages") or (), right.get("source_stages") or ()),
        "bbox_iou": bbox_iou,
        "bbox_overlap_min": bbox_overlap_min,
        "bbox_center_distance": bbox_center_distance,
    }
    for name in SCALAR_FIELDS:
        left_value = float(left.get(name) or 0.0)
        right_value = float(right.get(name) or 0.0)
        result[f"{name}_difference"] = abs(left_value - right_value)
        result[f"{name}_minimum"] = min(left_value, right_value)
        result[f"anchor_{name}"] = left_value
        result[f"candidate_{name}"] = right_value
    for prefix, record in (("anchor", left), ("candidate", right)):
        owners = set(record.get("proposed_owners") or ())
        stages = set(record.get("source_stages") or ())
        occupancy = np.asarray(record.get("shape_occupancy") or [0.0] * 16, dtype=np.float64)
        result[f"{prefix}_shape_mean"] = float(np.mean(occupancy))
        result[f"{prefix}_shape_std"] = float(np.std(occupancy))
        result[f"{prefix}_aspect_invariant"] = _aspect_invariant(record)
        for owner in ("numbers", "brand_graphics", "sponsors", "template"):
            result[f"{prefix}_proposes_{owner}"] = float(owner in owners)
        for stage in ("gpu_model_raw", "template_raw", "ocr_raw"):
            result[f"{prefix}_stage_{stage}"] = float(stage in stages)
        for name, value in _mask_topology(record["local_mask"]).items():
            result[f"{prefix}_mask8_{name}"] = value
    return result


class PortableExtraTrees:
    def __init__(self, path: str | Path = DEFAULT_MODEL_PATH) -> None:
        with np.load(Path(path), allow_pickle=False) as archive:
            self.metadata = json.loads(str(archive["metadata_json"]))
            self.feature_names = tuple(str(item) for item in archive["feature_names"])
            self.offsets = archive["tree_offsets"].astype(np.int32)
            self.left = archive["children_left"].astype(np.int32)
            self.right = archive["children_right"].astype(np.int32)
            self.feature = archive["split_feature"].astype(np.int32)
            self.thresholds = archive["split_threshold"].astype(np.float64)
            self.positive = archive["positive_probability"].astype(np.float64)

    def score(self, features: Mapping[str, float]) -> float:
        values = np.asarray([float(features.get(name) or 0.0) for name in self.feature_names])
        total = 0.0
        for root in self.offsets[:-1]:
            node = int(root)
            while self.left[node] >= 0:
                node = int(self.left[node] if values[self.feature[node]] <= self.thresholds[node] else self.right[node])
            total += float(self.positive[node])
        return total / max(1, len(self.offsets) - 1)


def _record(instance: Any, feature: Any) -> dict[str, Any]:
    return {
        "instance_id": instance.instance_id,
        "local_mask": instance.local_mask,
        "source_stages": instance.source_stages,
        "proposed_owners": feature.proposed_owners,
        "proposal_conflict": feature.proposal_conflict,
        "area_fraction": feature.area_fraction,
        "bbox_normalized": feature.bbox_normalized,
        "fill_ratio": feature.fill_ratio,
        "aspect_ratio": feature.aspect_ratio,
        "shape_occupancy": feature.shape_occupancy,
        "edge_density": feature.edge_density,
        "strong_gradient_fraction": feature.strong_gradient_fraction,
        "texture_entropy": feature.texture_entropy,
        "mean_rgb": feature.mean_rgb,
        "perceptual_lightness": feature.perceptual_lightness,
        "perceptual_chroma": feature.perceptual_chroma,
        "perceptual_hue_degrees": feature.perceptual_hue_degrees,
        "palette_role": feature.palette_role,
        "ocr_max_coverage": feature.ocr_max_coverage,
        "ocr_alpha_coverage": feature.ocr_alpha_coverage,
        "ocr_digit_coverage": feature.ocr_digit_coverage,
    }


def number_family_shadow_telemetry(
    instances: Sequence[Any],
    features: Sequence[Any],
    *,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> dict[str, Any]:
    """Rank possible sibling number copies with no ownership/output authority."""
    model = PortableExtraTrees(model_path)
    feature_by_id = {item.instance_id: item for item in features}
    records = [
        _record(instance, feature_by_id[instance.instance_id])
        for instance in instances if instance.instance_id in feature_by_id
    ]
    anchors = [record for record in records if "numbers" in record["proposed_owners"]]
    threshold = float(model.metadata["decision_threshold"])
    mutual_threshold = float(model.metadata.get("mutual_threshold", threshold))
    single_pair_enabled = bool(model.metadata.get("single_pair_enabled", True))
    top_pairs = []
    scored_pair_count = 0
    record_by_id = {str(record["instance_id"]): record for record in records}
    for anchor in anchors:
        best: tuple[float, Mapping[str, Any]] | None = None
        for candidate in records:
            if candidate["instance_id"] == anchor["instance_id"]:
                continue
            score = model.score(pair_features(anchor, candidate))
            scored_pair_count += 1
            if best is None or score > best[0]:
                best = (score, candidate)
        if best is not None:
            top_pairs.append({
                "anchor_instance_id": anchor["instance_id"],
                "candidate_instance_id": best[1]["instance_id"],
                "score": round(float(best[0]), 6),
                "accepted": bool(single_pair_enabled and best[0] >= threshold),
            })
    accepted = [item for item in top_pairs if item["accepted"]]
    mutual_pairs = []
    for item in top_pairs:
        candidate = record_by_id[str(item["candidate_instance_id"])]
        return_scores = []
        for return_anchor in anchors:
            if return_anchor["instance_id"] == candidate["instance_id"]:
                continue
            return_scores.append((
                model.score(pair_features(candidate, return_anchor)),
                str(return_anchor["instance_id"]),
            ))
            scored_pair_count += 1
        if not return_scores:
            continue
        reverse_score, return_anchor_id = max(return_scores, key=lambda value: value[0])
        mutual = return_anchor_id == str(item["anchor_instance_id"])
        mutual_score = min(float(item["score"]), float(reverse_score)) if mutual else -1.0
        mutual_pairs.append({
            "anchor_instance_id": item["anchor_instance_id"],
            "candidate_instance_id": item["candidate_instance_id"],
            "forward_score": item["score"],
            "reverse_score": round(float(reverse_score), 6),
            "mutual_score": round(float(mutual_score), 6),
            "mutual": mutual,
            "accepted": bool(mutual_score >= mutual_threshold),
        })
    mutual_accepted = [item for item in mutual_pairs if item["accepted"]]
    parent: dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for item in mutual_accepted:
        union(str(item["anchor_instance_id"]), str(item["candidate_instance_id"]))
    mutual_family_count = len({find(node) for node in parent})
    return {
        "schema": "smart-tga-number-family-shadow-v1",
        "status": "shadow_only",
        "model_version": model.metadata["version"],
        "decision_threshold": threshold,
        "single_pair_enabled": single_pair_enabled,
        "mutual_threshold": mutual_threshold,
        "instance_count": len(records),
        "anchor_count": len(anchors),
        "scored_pair_count": scored_pair_count,
        "accepted_pair_count": len(accepted),
        "accepted_pairs": accepted[:24],
        "mutual_accepted_pair_count": len(mutual_accepted),
        "mutual_family_count": mutual_family_count,
        "mutual_accepted_pairs": mutual_accepted[:24],
        "mutual_pairs": sorted(mutual_pairs, key=lambda item: item["mutual_score"], reverse=True)[:24],
        "top_pairs": sorted(top_pairs, key=lambda item: item["score"], reverse=True)[:24],
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }


__all__ = ["PortableExtraTrees", "number_family_shadow_telemetry", "pair_features"]
