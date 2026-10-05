"""Build offline same-number-family pair supervision from reviewed DLM paints.

Reviewed number-copy boxes select positive raw candidates.  Reviewed physical
groups supply hard negative candidates.  Coordinates and filenames are audit
keys only; emitted model features are intrinsic and cannot cast runtime votes.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations
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
GROUP_FIELDS = (
    "member_count", "area_fraction", "bbox_fraction", "fill_ratio",
    "largest_member_fraction", "smallest_member_fraction",
    "mean_edge_density", "max_edge_density", "mean_texture_entropy",
    "max_texture_entropy", "max_ocr_coverage", "max_digit_coverage",
    "palette_role_count", "palette_role_entropy", "lightness_span",
    "chroma_span", "proposal_conflict_fraction", "shape_occupancy_mean",
    "shape_occupancy_std", "shape_horizontal_symmetry",
    "shape_vertical_symmetry", "shape_center_edge_delta",
    "shape_adjacent_transition",
)


def _read(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _bbox_overlap(candidate: Sequence[int], review: Sequence[int]) -> tuple[float, float]:
    cx, cy, cw, ch = (int(value) for value in candidate)
    rx, ry, rw, rh = (int(value) for value in review)
    overlap = max(0, min(cx + cw, rx + rw) - max(cx, rx)) * max(
        0, min(cy + ch, ry + rh) - max(cy, ry)
    )
    return overlap / max(1, cw * ch), overlap / max(1, rw * rh)


def _candidate_records(inspections: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for inspection in inspections:
        paint = str(inspection.get("paint_label") or "")
        records = (
            (inspection.get("route_adjudicator_shadow") or {})
            .get("candidate_evidence", {}).get("decal_instances", {})
            .get("features", {}).get("records", ())
        )
        result[paint] = {
            str(row["instance_id"]): dict(row)
            for row in records if row.get("instance_id")
        }
    return result


def _audit_groups(audit: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        str(paint["paint_label"]): [dict(group) for group in paint.get("groups") or ()]
        for paint in audit.get("paints") or ()
    }


def _shape_grid(candidate: Mapping[str, Any]) -> np.ndarray:
    values = np.asarray(candidate.get("shape_occupancy") or [0.0] * 16, dtype=np.float64)
    if values.size != 16:
        return np.zeros((4, 4), dtype=np.float64)
    return values.reshape(4, 4)


def _decode_mask(candidate: Mapping[str, Any]) -> np.ndarray | None:
    rle = candidate.get("mask_rle") or {}
    shape = rle.get("shape") or ()
    counts = rle.get("counts") or ()
    if len(shape) != 2 or not counts:
        return None
    height, width = int(shape[0]), int(shape[1])
    total = height * width
    flat = np.zeros(total, dtype=np.uint8)
    cursor, value = 0, 0
    for raw_count in counts:
        count = max(0, int(raw_count))
        end = min(total, cursor + count)
        if value and end > cursor:
            flat[cursor:end] = 1
        cursor = end
        value = 1 - value
        if cursor >= total:
            break
    return flat.reshape(height, width)


def _mask_grid(candidate: Mapping[str, Any], size: int = 8) -> np.ndarray:
    mask = _decode_mask(candidate)
    if mask is None:
        return np.repeat(np.repeat(_shape_grid(candidate), size // 4, axis=0), size // 4, axis=1)
    height, width = mask.shape
    grid = np.zeros((size, size), dtype=np.float64)
    for row in range(size):
        y0, y1 = row * height // size, max((row + 1) * height // size, row * height // size + 1)
        for column in range(size):
            x0, x1 = column * width // size, max((column + 1) * width // size, column * width // size + 1)
            grid[row, column] = float(np.mean(mask[y0:min(y1, height), x0:min(x1, width)]))
    return grid


def _d4_distances(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    transforms = []
    for turns in range(4):
        rotated = np.rot90(b, turns)
        transforms.extend((rotated, np.fliplr(rotated)))
    l1 = min(float(np.mean(np.abs(a - item))) for item in transforms)
    av = a.ravel()
    an = float(np.linalg.norm(av))
    cosine = []
    for item in transforms:
        bv = item.ravel()
        denom = an * float(np.linalg.norm(bv))
        cosine.append(float(np.dot(av, bv) / denom) if denom else 0.0)
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


def _mask_topology(candidate: Mapping[str, Any]) -> dict[str, float]:
    grid = _mask_grid(candidate, 8)
    binary = grid >= 0.30
    return {
        "component_count": float(_component_count(binary)),
        "hole_count": float(_component_count(binary, count_holes=True)),
        "row_projection_std": float(np.std(np.mean(grid, axis=1))),
        "column_projection_std": float(np.std(np.mean(grid, axis=0))),
        "horizontal_transition": float(np.mean(np.abs(np.diff(grid, axis=1)))),
        "vertical_transition": float(np.mean(np.abs(np.diff(grid, axis=0)))),
        "center_edge_delta": float(np.mean(grid[2:6, 2:6]) - np.mean(np.concatenate((grid[0], grid[-1], grid[1:-1, 0], grid[1:-1, -1])))),
    }


def _shape_distances(left: Mapping[str, Any], right: Mapping[str, Any]) -> tuple[float, float]:
    return _d4_distances(_shape_grid(left), _shape_grid(right))


def _safe_log_ratio(left: float, right: float) -> float:
    return abs(math.log(max(left, 1e-8) / max(right, 1e-8)))


def _aspect_invariant(candidate: Mapping[str, Any]) -> float:
    value = max(float(candidate.get("aspect_ratio") or 1.0), 1e-8)
    return max(value, 1.0 / value)


def _hue_distance(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    a = float(left.get("perceptual_hue_degrees") or 0.0)
    b = float(right.get("perceptual_hue_degrees") or 0.0)
    delta = abs(a - b) % 360.0
    return min(delta, 360.0 - delta) / 180.0


def _jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    a, b = set(left), set(right)
    return len(a & b) / len(a | b) if a or b else 0.0


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


def pair_features(
    left: Mapping[str, Any], right: Mapping[str, Any],
    left_group: Mapping[str, Any] | None = None,
    right_group: Mapping[str, Any] | None = None,
) -> dict[str, float]:
    shape_l1, shape_cosine = _shape_distances(left, right)
    mask8_l1, mask8_cosine = _d4_distances(_mask_grid(left), _mask_grid(right))
    left_rgb = np.asarray(left.get("mean_rgb") or (0.0, 0.0, 0.0), dtype=np.float64)
    right_rgb = np.asarray(right.get("mean_rgb") or (0.0, 0.0, 0.0), dtype=np.float64)
    bbox_iou, bbox_overlap_min, bbox_center_distance = _bbox_relationship(left, right)
    features = {
        "shape_d4_l1": shape_l1,
        "shape_d4_cosine": shape_cosine,
        "mask8_d4_l1": mask8_l1,
        "mask8_d4_cosine": mask8_cosine,
        "area_log_ratio": _safe_log_ratio(
            float(left.get("area_fraction") or 0.0),
            float(right.get("area_fraction") or 0.0),
        ),
        "aspect_log_ratio": _safe_log_ratio(_aspect_invariant(left), _aspect_invariant(right)),
        "mean_rgb_distance": float(np.linalg.norm(left_rgb - right_rgb) / (255.0 * math.sqrt(3.0))),
        "hue_circular_distance": _hue_distance(left, right),
        "palette_role_match": float(left.get("palette_role") == right.get("palette_role")),
        "proposal_conflict_any": float(bool(left.get("proposal_conflict")) or bool(right.get("proposal_conflict"))),
        "proposed_owner_jaccard": _jaccard(
            left.get("proposed_owners") or (), right.get("proposed_owners") or (),
        ),
        "source_stage_jaccard": _jaccard(
            left.get("source_stages") or (), right.get("source_stages") or (),
        ),
        "bbox_iou": bbox_iou,
        "bbox_overlap_min": bbox_overlap_min,
        "bbox_center_distance": bbox_center_distance,
    }
    for name in SCALAR_FIELDS:
        features[f"{name}_difference"] = abs(float(left.get(name) or 0.0) - float(right.get(name) or 0.0))
        features[f"{name}_minimum"] = min(float(left.get(name) or 0.0), float(right.get(name) or 0.0))
        features[f"anchor_{name}"] = float(left.get(name) or 0.0)
        features[f"candidate_{name}"] = float(right.get(name) or 0.0)
    for prefix, candidate in (("anchor", left), ("candidate", right)):
        owners = set(candidate.get("proposed_owners") or ())
        stages = set(candidate.get("source_stages") or ())
        occupancy = np.asarray(candidate.get("shape_occupancy") or [0.0] * 16, dtype=np.float64)
        features[f"{prefix}_shape_mean"] = float(np.mean(occupancy))
        features[f"{prefix}_shape_std"] = float(np.std(occupancy))
        features[f"{prefix}_aspect_invariant"] = _aspect_invariant(candidate)
        for owner in ("numbers", "brand_graphics", "sponsors", "template"):
            features[f"{prefix}_proposes_{owner}"] = float(owner in owners)
        for stage in ("gpu_model_raw", "template_raw", "ocr_raw"):
            features[f"{prefix}_stage_{stage}"] = float(stage in stages)
        for name, value in _mask_topology(candidate).items():
            features[f"{prefix}_mask8_{name}"] = value
    for prefix, group in (("anchor_group", left_group or {}), ("candidate_group", right_group or {})):
        for name in GROUP_FIELDS:
            features[f"{prefix}_{name}"] = float(group.get(name) or 0.0)
    return features


def build_bank(
    missed_probes: Sequence[str | Path], group_labels: Sequence[str | Path],
    group_banks: Sequence[str | Path] | None = None,
    number_labels_dir: str | Path | None = None,
) -> dict[str, Any]:
    if len(missed_probes) != len(group_labels):
        raise ValueError("each missed probe requires matching physical-group labels")
    if group_banks is not None and len(group_banks) != len(missed_probes):
        raise ValueError("each missed probe requires a matching group feature bank")
    rows: list[dict[str, Any]] = []
    skipped = Counter()
    paint_counts = Counter()
    negative_sources = Counter()
    feature_names: list[str] | None = None
    for index, (probe_path, labels_path) in enumerate(zip(missed_probes, group_labels)):
        probe = _read(probe_path)
        labels = _read(labels_path)
        inspections = _read(labels["inspection_records"])
        audit = _read(labels["physical_group_audit"])
        candidates_by_paint = _candidate_records(inspections)
        audit_by_paint = _audit_groups(audit)
        group_features: dict[tuple[str, str], dict[str, Any]] = {}
        if group_banks is not None:
            group_document = _read(group_banks[index])
            group_features = {
                (str(row["paint_label"]), str(row["group_id"])): dict(row)
                for row in group_document.get("records") or ()
            }
        candidate_groups: dict[tuple[str, str], dict[str, Any]] = {}
        for paint, groups in audit_by_paint.items():
            for group in groups:
                features = group_features.get((paint, str(group.get("group_id") or "")), {})
                for instance_id in group.get("instance_ids") or ():
                    candidate_groups[(paint, str(instance_id))] = features
        targets_by_paint = labels.get("paint_group_targets") or {}
        cycle = Path(probe_path).parts[-2].split("_")[0]

        negative_ids: dict[str, dict[str, str]] = defaultdict(dict)
        for paint, targets in targets_by_paint.items():
            groups = audit_by_paint.get(str(paint), [])
            if len(groups) != len(targets):
                raise ValueError(f"group target count mismatch for {paint}")
            for group, target in zip(groups, targets):
                if target in {"numbers", "uncertain"}:
                    continue
                for instance_id in group.get("instance_ids") or ():
                    negative_ids[str(paint)][str(instance_id)] = str(target)
                    negative_sources["reviewed_physical_group"] += 1

        # False Number emissions are reviewed hard negatives too, including
        # raw candidates that never entered a physical group.  This closes a
        # dangerous availability shortcut without treating coordinates as
        # runtime evidence: boxes are used only to attach durable review truth.
        if number_labels_dir is not None:
            for number_path in Path(number_labels_dir).glob(
                f"{cycle}_dirtlatemodel_*_numbers_v1.json"
            ):
                number_review = _read(number_path)
                paint = str(number_review.get("paint_label") or "")
                candidate_map = candidates_by_paint.get(paint, {})
                for component in number_review.get("component_labels") or ():
                    target = str(component.get("target_layer") or "")
                    bbox = component.get("expected_bbox")
                    if target in {"numbers", "uncertain"} or not bbox:
                        continue
                    for instance_id, candidate in candidate_map.items():
                        candidate_bbox = candidate.get("bbox")
                        if not candidate_bbox:
                            continue
                        candidate_coverage, review_coverage = _bbox_overlap(candidate_bbox, bbox)
                        if candidate_coverage >= 0.50 and review_coverage >= 0.05:
                            if instance_id not in negative_ids[paint]:
                                negative_sources["reviewed_false_number_component"] += 1
                            negative_ids[paint][instance_id] = target

        families: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
        same_copy_negative_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
        for record in probe.get("records") or ():
            if record.get("status") not in {"candidate_present", "candidate_fragment_only"}:
                continue
            paint = str(record.get("paint_label") or "")
            family = str(record.get("family_id") or "")
            instance_id = str(record.get("best_instance_id") or "")
            candidate = candidates_by_paint.get(paint, {}).get(instance_id)
            if not family or not candidate:
                skipped["positive_candidate_missing"] += 1
                continue
            families[(paint, family)][instance_id] = candidate
            review_bbox = record.get("bbox")
            if review_bbox:
                for other_id, other in candidates_by_paint.get(paint, {}).items():
                    if other_id == instance_id or not other.get("bbox"):
                        continue
                    candidate_coverage, review_coverage = _bbox_overlap(other["bbox"], review_bbox)
                    if candidate_coverage >= 0.50 and review_coverage >= 0.02:
                        same_copy_negative_ids[(paint, family)].add(other_id)

        for (paint, family), positives in families.items():
            positive_items = sorted(positives.items())
            if len(positive_items) < 2:
                skipped["family_below_two_unique_candidates"] += 1
                continue
            for (left_id, left), (right_id, right) in combinations(positive_items, 2):
                # Keep both anchor directions so retrieval evaluation asks
                # whether every reviewed copy can find its sibling.
                for anchor_id, anchor, sibling_id, sibling in (
                    (left_id, left, right_id, right),
                    (right_id, right, left_id, left),
                ):
                    features = pair_features(
                        anchor, sibling,
                        candidate_groups.get((paint, anchor_id)),
                        candidate_groups.get((paint, sibling_id)),
                    )
                    feature_names = feature_names or list(features)
                    rows.append({
                        "cycle": cycle, "paint_label": paint, "family_id": family,
                        "left_instance_id": anchor_id, "right_instance_id": sibling_id,
                        "anchor_group_id": (candidate_groups.get((paint, anchor_id)) or {}).get("group_id"),
                        "candidate_group_id": (candidate_groups.get((paint, sibling_id)) or {}).get("group_id"),
                        "truth_same_number_family": True, "negative_owner": None,
                        **features,
                    })
                    paint_counts[paint] += 1
            candidate_map = candidates_by_paint.get(paint, {})
            family_negative_ids = dict(negative_ids.get(paint, {}))
            for instance_id in same_copy_negative_ids.get((paint, family), set()):
                if instance_id not in positives and instance_id not in family_negative_ids:
                    family_negative_ids[instance_id] = "same_copy_fragment"
                    negative_sources["same_copy_fragment"] += 1
            for left_id, left in positive_items:
                for right_id, owner in sorted(family_negative_ids.items()):
                    if right_id in positives:
                        continue
                    right = candidate_map.get(right_id)
                    if not right:
                        skipped["negative_candidate_missing"] += 1
                        continue
                    features = pair_features(
                        left, right,
                        candidate_groups.get((paint, left_id)),
                        candidate_groups.get((paint, right_id)),
                    )
                    feature_names = feature_names or list(features)
                    rows.append({
                        "cycle": cycle, "paint_label": paint, "family_id": family,
                        "left_instance_id": left_id, "right_instance_id": right_id,
                        "anchor_group_id": (candidate_groups.get((paint, left_id)) or {}).get("group_id"),
                        "candidate_group_id": (candidate_groups.get((paint, right_id)) or {}).get("group_id"),
                        "truth_same_number_family": False, "negative_owner": owner,
                        **features,
                    })
                    paint_counts[paint] += 1

    truth = Counter("positive" if row["truth_same_number_family"] else "negative" for row in rows)
    return {
        "schema": "smart-tga-number-family-pair-bank-v1",
        "feature_names": feature_names or [],
        "summary": {
            "pair_count": len(rows), "paint_count": len(paint_counts),
            "positive_pair_count": truth["positive"],
            "negative_pair_count": truth["negative"],
            "negative_candidate_source_counts": dict(sorted(negative_sources.items())),
            "skipped": dict(sorted(skipped.items())),
            "casts_votes": False, "ownership_authority": False, "adds_pixels": False,
        },
        "records": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--missed-probe", action="append", required=True)
    parser.add_argument("--group-labels", action="append", required=True)
    parser.add_argument("--group-bank", action="append")
    parser.add_argument("--number-labels-dir")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = build_bank(
        args.missed_probe, args.group_labels, args.group_bank,
        args.number_labels_dir,
    )
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
