"""Train a paint-disjoint semantic scorer for number context proposals.

Context envelopes are high-recall and owner-neutral. Reviewed number copies
provide positives; reviewed false Numbers and physical Sponsor/Template/Paint
groups provide negatives. Coordinates select offline supervision only and are
never features or runtime authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.number_context_semantics import (
        SCALAR_SEED_FIELDS,
        canonical_d4 as _canonical_d4,
        context_feature_mapping,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...py`` execution.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_semantics import (  # type: ignore
        SCALAR_SEED_FIELDS,
        canonical_d4 as _canonical_d4,
        context_feature_mapping,
    )

try:
    from scripts.smart_tga_number_context_proposal_probe import (
        _coverage, _load_cycle, _read, generate_context_proposals,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...py`` execution.
    from smart_tga_number_context_proposal_probe import (  # type: ignore
        _coverage, _load_cycle, _read, generate_context_proposals,
    )


def _cycles(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _inspection_map(labels_dir: Path, cycles: Sequence[int]) -> dict[str, dict[str, Any]]:
    result = {}
    for cycle in cycles:
        annotations = _read(labels_dir / f"cycle{cycle}_missed_number_instances_v1.json")
        for item in _read(annotations["inspection_records"]):
            result[str(item.get("paint_label") or "")] = item
    return result


def _false_number_controls(labels_dir: Path, cycles: Sequence[int]) -> list[dict[str, Any]]:
    records = []
    for cycle in cycles:
        for path in labels_dir.glob(f"cycle{cycle}_*_numbers_v1.json"):
            payload = _read(path)
            for item in payload.get("component_labels") or ():
                target = str(item.get("target_layer") or "").lower()
                if target in {"numbers", "uncertain", ""}:
                    continue
                records.append({
                    "paint_label": str(payload.get("paint_label") or ""),
                    "bbox": list(item.get("expected_bbox") or ()),
                    "semantic": target,
                    "source": "reviewed_false_number",
                })
    return [item for item in records if len(item["bbox"]) == 4]


def _physical_group_controls(labels_dir: Path, cycles: Sequence[int]) -> list[dict[str, Any]]:
    records = []
    for cycle in cycles:
        path = labels_dir / f"cycle{cycle}_physical_groups_v1.json"
        if not path.exists():
            continue
        labels = _read(path)
        audit = _read(labels["physical_group_audit"])
        targets = labels.get("paint_group_targets") or {}
        audit_by_paint = {str(item["paint_label"]): item for item in audit.get("paints") or ()}
        for paint, semantic_targets in targets.items():
            groups = (audit_by_paint.get(str(paint)) or {}).get("groups") or ()
            for index, semantic in enumerate(semantic_targets or ()):
                target = str(semantic or "").lower()
                if target in {"numbers", "uncertain", ""} or index >= len(groups):
                    continue
                records.append({
                    "paint_label": str(paint),
                    "bbox": list(groups[index]["bbox"]),
                    "semantic": target,
                    "source": "reviewed_physical_group",
                })
    return records


def _proposal_matches(
    proposals: Sequence[Mapping[str, Any]], review_bbox: Sequence[int], *, limit: int,
) -> list[tuple[tuple[float, float, float], Mapping[str, Any]]]:
    ranked = sorted(
        ((_coverage(item["bbox"], review_bbox), item) for item in proposals),
        key=lambda item: (item[0][2], item[0][0]), reverse=True,
    )
    return [
        item for item in ranked
        if item[0][0] >= 0.50 and item[0][1] >= 0.10 and item[0][2] >= 0.20
    ][:limit]


def _feature_vector(
    image: np.ndarray, proposal: Mapping[str, Any], seed: Mapping[str, Any],
) -> tuple[list[str], np.ndarray]:
    mapping = context_feature_mapping(image, proposal, seed)
    return list(mapping), np.asarray(list(mapping.values()), dtype=np.float64)


def _build_split(
    labels_dir: Path, cycles: Sequence[int], prototypes: Sequence[Sequence[float]],
) -> dict[str, Any]:
    annotations, candidates, inspections = [], {}, _inspection_map(labels_dir, cycles)
    for cycle in cycles:
        cycle_annotations, cycle_candidates = _load_cycle(labels_dir, cycle)
        annotations.extend(cycle_annotations)
        candidates.update(cycle_candidates)
    negatives = _false_number_controls(labels_dir, cycles) + _physical_group_controls(labels_dir, cycles)
    by_paint_positive: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_paint_negative: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in annotations:
        by_paint_positive[str(item["paint_label"])].append(item)
    for item in negatives:
        by_paint_negative[str(item["paint_label"])].append(item)
    records, feature_names = [], None
    for paint, inspection in inspections.items():
        source = np.asarray(Image.open(inspection["source_1024"]).convert("RGB"))
        seed_records = candidates.get(paint, ())
        seed_by_id = {str(item.get("instance_id") or ""): item for item in seed_records}
        proposals = generate_context_proposals(seed_records, prototypes)
        seen = set()
        for label, regions, limit in ((1, by_paint_positive.get(paint, ()), 2), (0, by_paint_negative.get(paint, ()), 1)):
            for region in regions:
                for metrics, proposal in _proposal_matches(proposals, region["bbox"], limit=limit):
                    key = (tuple(proposal["bbox"]), proposal["seed_instance_id"], label)
                    if key in seen:
                        continue
                    seed = seed_by_id.get(str(proposal["seed_instance_id"])) or {}
                    names, vector = _feature_vector(source, proposal, seed)
                    feature_names = feature_names or names
                    seen.add(key)
                    records.append({
                        "paint_label": paint,
                        "label": label,
                        "semantic": "numbers" if label else region.get("semantic"),
                        "source": "reviewed_number_copy" if label else region.get("source"),
                        "region_bbox": list(region["bbox"]),
                        "proposal": dict(proposal),
                        "match_iou": round(float(metrics[2]), 6),
                        "features": vector,
                    })
    # A proposal that is supervised as both Number and a hard negative is
    # ambiguous region overlap, not clean training evidence.
    labels_by_key: dict[tuple[str, tuple[int, ...], str], set[int]] = defaultdict(set)
    for item in records:
        key = (item["paint_label"], tuple(item["proposal"]["bbox"]), item["proposal"]["seed_instance_id"])
        labels_by_key[key].add(int(item["label"]))
    clean = [
        item for item in records
        if len(labels_by_key[(item["paint_label"], tuple(item["proposal"]["bbox"]), item["proposal"]["seed_instance_id"])]) == 1
    ]
    return {"records": clean, "feature_names": feature_names or []}


def _threshold(scores: np.ndarray, labels: np.ndarray) -> tuple[float, dict[str, Any]]:
    negative = scores[labels == 0]
    threshold = min(1.0, float(np.max(negative)) + 1e-9) if negative.size else 0.5
    accepted = scores >= threshold
    tp = int(np.count_nonzero(accepted & (labels == 1)))
    fp = int(np.count_nonzero(accepted & (labels == 0)))
    fn = int(np.count_nonzero((~accepted) & (labels == 1)))
    return threshold, {
        "true_positive": tp, "false_positive": fp, "false_negative": fn,
        "precision": round(tp / max(1, tp + fp), 6),
        "recall": round(tp / max(1, tp + fn), 6),
    }


def _metrics(scores: np.ndarray, labels: np.ndarray, threshold: float) -> dict[str, Any]:
    accepted = scores >= threshold
    tp = int(np.count_nonzero(accepted & (labels == 1)))
    fp = int(np.count_nonzero(accepted & (labels == 0)))
    fn = int(np.count_nonzero((~accepted) & (labels == 1)))
    return {
        "sample_count": int(labels.size), "positive_count": int(np.count_nonzero(labels == 1)),
        "negative_count": int(np.count_nonzero(labels == 0)),
        "true_positive": tp, "false_positive": fp, "false_negative": fn,
        "precision": round(tp / max(1, tp + fp), 6),
        "recall": round(tp / max(1, tp + fn), 6),
    }


def _export_extra_trees(
    model: Any, feature_names: Sequence[str], *, threshold: float, output: Path,
) -> None:
    offsets = [0]
    children_left: list[int] = []
    children_right: list[int] = []
    split_feature: list[int] = []
    split_threshold: list[float] = []
    positive_probability: list[float] = []
    for estimator in model.estimators_:
        tree = estimator.tree_
        base = offsets[-1]
        children_left.extend(int(value + base) if value >= 0 else -1 for value in tree.children_left)
        children_right.extend(int(value + base) if value >= 0 else -1 for value in tree.children_right)
        split_feature.extend(int(value) for value in tree.feature)
        split_threshold.extend(float(value) for value in tree.threshold)
        for values in tree.value[:, 0, :]:
            total = float(np.sum(values))
            positive_probability.append(float(values[1] / total) if total else 0.0)
        offsets.append(base + int(tree.node_count))
    metadata = {
        "schema": "smart-tga-number-context-extra-trees-v1",
        "version": "cycle697-dlm-context-semantic-v1",
        "decision_threshold": float(threshold),
        "tree_count": len(model.estimators_),
        "train_cycles": list(range(683, 691)),
        "calibration_cycles": [693],
        "canary_cycles_excluded": [695],
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        metadata_json=np.asarray(json.dumps(metadata), dtype=np.str_),
        feature_names=np.asarray(list(feature_names), dtype=np.str_),
        tree_offsets=np.asarray(offsets, dtype=np.int32),
        children_left=np.asarray(children_left, dtype=np.int32),
        children_right=np.asarray(children_right, dtype=np.int32),
        split_feature=np.asarray(split_feature, dtype=np.int32),
        split_threshold=np.asarray(split_threshold, dtype=np.float64),
        positive_probability=np.asarray(positive_probability, dtype=np.float64),
    )


def run(labels_dir: Path, prototype_path: Path, *, model_output: Path | None = None) -> dict[str, Any]:
    from sklearn.ensemble import ExtraTreesClassifier
    from sklearn.model_selection import GroupKFold

    prototypes = _read(prototype_path)["prototypes"]
    train = _build_split(labels_dir, (683, 684, 685, 686, 687, 688, 689, 690), prototypes)
    validation = _build_split(labels_dir, (693,), prototypes)
    canary = _build_split(labels_dir, (695,), prototypes)
    train_records = train["records"]
    x = np.stack([item["features"] for item in train_records])
    y = np.asarray([item["label"] for item in train_records], dtype=np.int8)
    groups = np.asarray([item["paint_label"] for item in train_records], dtype=object)
    oof = np.zeros(y.shape[0], dtype=np.float64)
    splitter = GroupKFold(n_splits=min(5, len(set(groups.tolist()))))
    for train_index, test_index in splitter.split(x, y, groups):
        model = ExtraTreesClassifier(
            n_estimators=500, min_samples_leaf=2, max_features="sqrt",
            class_weight="balanced", random_state=697, n_jobs=-1,
        ).fit(x[train_index], y[train_index])
        oof[test_index] = model.predict_proba(x[test_index])[:, 1]
    oof_threshold, oof_metrics = _threshold(oof, y)
    model = ExtraTreesClassifier(
        n_estimators=700, min_samples_leaf=2, max_features="sqrt",
        class_weight="balanced", random_state=697, n_jobs=-1,
    ).fit(x, y)

    validation_matrix = np.stack([item["features"] for item in validation["records"]])
    validation_labels = np.asarray([item["label"] for item in validation["records"]], dtype=np.int8)
    validation_scores = model.predict_proba(validation_matrix)[:, 1]
    calibration_threshold, _ = _threshold(validation_scores, validation_labels)

    def score(split: Mapping[str, Any], cutoff: float) -> tuple[dict[str, Any], np.ndarray]:
        records = split["records"]
        matrix = np.stack([item["features"] for item in records])
        labels = np.asarray([item["label"] for item in records], dtype=np.int8)
        scores = model.predict_proba(matrix)[:, 1]
        result = _metrics(scores, labels, cutoff)
        def copy_count(cutoff: float) -> int:
            return len({
                (item["paint_label"], tuple(item["region_bbox"]))
                for item, value in zip(records, scores)
                if item["label"] == 1 and value >= cutoff
            })

        negative_scores = scores[labels == 0]
        positive_scores = scores[labels == 1]
        oracle_threshold = min(1.0, float(np.max(negative_scores)) + 1e-9) if negative_scores.size else 0.5
        result["positive_copy_count"] = len({
            (item["paint_label"], tuple(item["region_bbox"]))
            for item in records if item["label"] == 1
        })
        result["accepted_positive_copy_count"] = copy_count(cutoff)
        result["oracle_zero_fp_threshold"] = round(oracle_threshold, 9)
        result["oracle_zero_fp_positive_copy_count"] = copy_count(oracle_threshold)
        result["positive_score_quantiles"] = [
            round(float(value), 6) for value in np.quantile(positive_scores, (0, .25, .5, .75, 1))
        ] if positive_scores.size else []
        result["negative_score_quantiles"] = [
            round(float(value), 6) for value in np.quantile(negative_scores, (0, .25, .5, .75, 1))
        ] if negative_scores.size else []
        result["accepted_records"] = [
            {
                "paint_label": item["paint_label"], "label": int(item["label"]),
                "semantic": item["semantic"], "bbox": item["proposal"]["bbox"],
                "score": round(float(value), 6),
            }
            for item, value in zip(records, scores) if value >= cutoff
        ]
        return result, scores

    validation_metrics, _ = score(validation, calibration_threshold)
    canary_metrics, _ = score(canary, calibration_threshold)
    importances = sorted(zip(train["feature_names"], model.feature_importances_), key=lambda item: item[1], reverse=True)
    if model_output is not None:
        _export_extra_trees(
            model, train["feature_names"], threshold=calibration_threshold,
            output=model_output,
        )
    return {
        "schema": "smart-tga-number-context-semantic-probe-v1",
        "model_kind": "extra_trees",
        "train_cycles": list(range(683, 691)),
        "validation_cycles": [693],
        "canary_cycles": [695],
        "feature_count": len(train["feature_names"]),
        "threshold_source": "maximum Cycle693 reviewed hard-negative score plus epsilon; Cycle695 untouched",
        "decision_threshold": round(float(calibration_threshold), 9),
        "portable_model": str(model_output) if model_output is not None else None,
        "paint_grouped_oof_threshold": round(float(oof_threshold), 9),
        "train_oof": {**_metrics(oof, y, oof_threshold), **oof_metrics},
        "validation": validation_metrics,
        "canary": canary_metrics,
        "top_feature_importances": [
            {"feature": name, "importance": round(float(value), 6)}
            for name, value in importances[:24]
        ],
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-dir", default="smart_tga_review_labels")
    parser.add_argument("--prototypes", default="engine/spec_sculpt/models/smart_tga_number_context_cycle696_v1.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-output", required=True)
    args = parser.parse_args()
    result = run(
        Path(args.labels_dir), Path(args.prototypes),
        model_output=Path(args.model_output),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    compact = dict(result)
    compact["validation"] = {key: value for key, value in result["validation"].items() if key != "accepted_records"}
    compact["canary"] = {key: value for key, value in result["canary"].items() if key != "accepted_records"}
    print(json.dumps(compact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
