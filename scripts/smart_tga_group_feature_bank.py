"""Join immutable group features to durable human review labels."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


PROFILE_FEATURES = (
    "area_fraction", "bbox_fraction", "fill_ratio", "largest_member_fraction",
    "mean_edge_density", "mean_texture_entropy", "max_ocr_coverage",
    "max_digit_coverage", "palette_role_entropy", "lightness_span",
    "chroma_span", "proposed_owner_count", "number_member_fraction",
    "sponsor_member_fraction", "template_member_fraction",
    "proposal_conflict_fraction", "shape_occupancy_mean",
    "shape_occupancy_std", "shape_horizontal_symmetry",
    "shape_vertical_symmetry", "shape_center_edge_delta",
    "shape_adjacent_transition",
)


def _shape_profile(values: object) -> dict[str, float]:
    """Summarize an immutable 4x4 occupancy grid without owner assumptions."""
    if not isinstance(values, list) or len(values) != 16:
        return {}
    cells = [float(value or 0.0) for value in values]
    mean = sum(cells) / 16.0
    variance = sum((value - mean) ** 2 for value in cells) / 16.0
    horizontal = 1.0 - sum(
        abs(cells[row * 4 + col] - cells[row * 4 + (3 - col)])
        for row in range(4) for col in range(2)
    ) / 8.0
    vertical = 1.0 - sum(
        abs(cells[row * 4 + col] - cells[(3 - row) * 4 + col])
        for row in range(2) for col in range(4)
    ) / 8.0
    center_indices = (5, 6, 9, 10)
    border_indices = tuple(index for index in range(16) if index not in center_indices)
    center = sum(cells[index] for index in center_indices) / len(center_indices)
    border = sum(cells[index] for index in border_indices) / len(border_indices)
    transitions = []
    for row in range(4):
        for col in range(3):
            transitions.append(abs(cells[row * 4 + col] - cells[row * 4 + col + 1]))
    for row in range(3):
        for col in range(4):
            transitions.append(abs(cells[row * 4 + col] - cells[(row + 1) * 4 + col]))
    return {
        "shape_occupancy_mean": round(mean, 6),
        "shape_occupancy_std": round(variance ** 0.5, 6),
        "shape_horizontal_symmetry": round(max(0.0, horizontal), 6),
        "shape_vertical_symmetry": round(max(0.0, vertical), 6),
        "shape_center_edge_delta": round(center - border, 6),
        "shape_adjacent_transition": round(sum(transitions) / len(transitions), 6),
    }


def build_bank(inspection: list[dict], review: dict) -> dict:
    labels = {
        (str(item["paint_label"]), str(item["group_id"])): item
        for item in review.get("group_labels") or ()
    }
    ordered_targets = {
        str(paint_label): [str(owner) for owner in owners]
        for paint_label, owners in (review.get("paint_group_targets") or {}).items()
    }
    records = []
    missing_feature_records = []
    seen = set()
    for paint in inspection:
        paint_label = str(paint["paint_label"])
        decal_instances = (
            paint.get("route_adjudicator_shadow", {})
            .get("candidate_evidence", {})
            .get("decal_instances", {})
        )
        physical = decal_instances.get("physical_groups", {})
        semantic_records = (
            decal_instances.get("semantic_objects", {}).get("records") or ()
        )
        semantic_groups = {
            str(item.get("physical_group_id")): item
            for item in semantic_records if item.get("physical_group_id")
        }
        features = physical.get("features", {}).get("records")
        if features is None:
            missing_feature_records.append(paint_label)
            continue
        ordered = ordered_targets.get(paint_label)
        if ordered is not None:
            if len(ordered) != len(features):
                raise ValueError(
                    f"ordered review count mismatch for {paint_label}: "
                    f"{len(ordered)} labels != {len(features)} feature records"
                )
            for item, owner in zip(features, ordered):
                key = (paint_label, str(item["group_id"]))
                labels.setdefault(key, {
                    "paint_label": paint_label,
                    "group_id": str(item["group_id"]),
                    "target_layer": owner,
                    "label": "ordered_visual_review",
                })
        for item in features:
            key = (paint_label, str(item["group_id"]))
            label = labels.get(key)
            row = dict(item)
            semantic_group = semantic_groups.get(str(item["group_id"]))
            if semantic_group:
                row.update(_shape_profile(semantic_group.get("shape_occupancy")))
            row["paint_label"] = paint_label
            row["review_target_layer"] = label.get("target_layer") if label else None
            row["review_family_id"] = label.get("family_id") if label else None
            row["review_label"] = label.get("label") if label else None
            row["reviewed"] = label is not None
            records.append(row)
            seen.add(key)
    missing_reviews = sorted(
        {key for key in labels if key not in seen}, key=lambda item: (item[0], item[1])
    )
    reviewed = [item for item in records if item["reviewed"]]
    class_counts = Counter(str(item["review_target_layer"]) for item in reviewed)
    class_paints: dict[str, set[str]] = defaultdict(set)
    for item in reviewed:
        class_paints[str(item["review_target_layer"])].add(str(item["paint_label"]))
    class_profiles = {}
    for owner in sorted(class_counts):
        owner_records = [item for item in reviewed if str(item["review_target_layer"]) == owner]
        class_profiles[owner] = {
            feature: round(sum(float(item.get(feature, 0.0)) for item in owner_records) / len(owner_records), 6)
            for feature in PROFILE_FEATURES
        }
    minimum_coverage_classes = sorted(
        owner for owner, count in class_counts.items()
        if owner != "uncertain" and count >= 12 and len(class_paints[owner]) >= 3
    )
    required = {"numbers", "sponsors", "template", "paint"}
    missing_coverage = sorted(required.difference(minimum_coverage_classes))
    return {
        "schema": "smart-tga-group-feature-bank-v1",
        "records": records,
        "summary": {
            "paint_count": len(inspection),
            "feature_record_count": len(records),
            "reviewed_record_count": len(reviewed),
            "class_counts": dict(sorted(class_counts.items())),
            "class_paint_counts": {key: len(value) for key, value in sorted(class_paints.items())},
            "class_feature_means": class_profiles,
            "minimum_coverage_classes": minimum_coverage_classes,
            "training_coverage_ready": not missing_coverage,
            "calibration_ready": False,
            "calibration_blockers": (
                [f"minimum_review_coverage:{owner}" for owner in missing_coverage]
                + ["no_held_out_calibration_model"]
            ),
            "missing_feature_record_paints": missing_feature_records,
            "missing_review_count": len(missing_reviews),
            "missing_reviews": [
                {"paint_label": paint_label, "group_id": group_id}
                for paint_label, group_id in missing_reviews[:40]
            ],
            "missing_reviews_truncated": len(missing_reviews) > 40,
            "casts_votes": False,
            "ownership_authority": False,
        },
    }


def load_documents(paths: list[str], *, list_key: str | None = None) -> list[dict]:
    """Load several corpus shards without giving any shard runtime authority."""
    merged: list[dict] = []
    for value in paths:
        document = json.loads(Path(value).read_text(encoding="utf-8"))
        records = document.get(list_key) if list_key and isinstance(document, dict) else document
        if not isinstance(records, list):
            raise ValueError(f"{value} does not contain a JSON list")
        merged.extend(records)
    return merged


def load_review_documents(paths: list[str]) -> dict:
    """Merge ID labels and audited ordered labels without inventing authority."""
    group_labels: list[dict] = []
    paint_group_targets: dict[str, list[str]] = {}
    for value in paths:
        document = json.loads(Path(value).read_text(encoding="utf-8"))
        if document.get("casts_votes") or document.get("ownership_authority"):
            raise ValueError(f"{value} claimed runtime authority")
        group_labels.extend(document.get("group_labels") or ())
        for paint_label, owners in (document.get("paint_group_targets") or {}).items():
            normalized = [str(owner) for owner in owners]
            existing = paint_group_targets.get(str(paint_label))
            if existing is not None and existing != normalized:
                raise ValueError(f"conflicting ordered reviews for {paint_label}")
            paint_group_targets[str(paint_label)] = normalized
    return {"group_labels": group_labels, "paint_group_targets": paint_group_targets}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", action="append", required=True)
    parser.add_argument("--labels", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    inspection = load_documents(args.inspection)
    review = load_review_documents(args.labels)
    bank = build_bank(inspection, review)
    Path(args.output).write_text(json.dumps(bank, indent=2), encoding="utf-8")
    print(json.dumps(bank["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
