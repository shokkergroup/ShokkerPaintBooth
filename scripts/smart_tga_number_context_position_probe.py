"""Train/calibrate a normalized DLM panel-position corroborator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:
    from engine.spec_sculpt.number_context_position import (
        POSITION_FEATURE_NAMES, position_feature_mapping,
    )
    from scripts.smart_tga_number_context_semantic_probe import _build_split
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_position import (  # type: ignore
        POSITION_FEATURE_NAMES, position_feature_mapping,
    )
    from scripts.smart_tga_number_context_semantic_probe import _build_split  # type: ignore
    from scripts.smart_tga_number_context_runtime_gate import _labels, _matches  # type: ignore


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _vector(proposal: Mapping[str, Any]) -> np.ndarray:
    features = position_feature_mapping(proposal)
    return np.asarray([features[name] for name in POSITION_FEATURE_NAMES], dtype=np.float64)


def _runtime_metrics(
    model: Any, inspections: Sequence[Mapping[str, Any]], labels_dir: Path, cycle: int,
    *, threshold: float | None = None,
) -> tuple[dict[str, Any], float]:
    positives, negatives = _labels(labels_dir, cycle)
    paint_labels = {str(item.get("paint_label") or "") for item in inspections}
    positives = [item for item in positives if str(item.get("paint_label") or "") in paint_labels]
    negatives = [item for item in negatives if str(item.get("paint_label") or "") in paint_labels]
    by_paint: dict[str, list[dict[str, Any]]] = {}
    for inspection in inspections:
        shadow = (
            inspection["route_adjudicator_shadow"]["candidate_evidence"]
            ["decal_instances"]["number_context_shadow"]
        )
        proposals = [
            dict(item) for item in shadow.get("proposal_records") or ()
            if item.get("semantic_status") == "accepted_number_candidate"
        ]
        if proposals:
            scores = model.predict_proba(np.stack([_vector(item) for item in proposals]))[:, 1]
            for item, score in zip(proposals, scores):
                item["position_score"] = float(score)
        by_paint[str(inspection.get("paint_label") or "")] = proposals

    negative_scores = [
        proposal["position_score"]
        for item in negatives
        for proposal in by_paint.get(str(item["paint_label"]), ())
        if _matches(proposal["bbox"], item["bbox"])
    ]
    cutoff = (
        float(threshold) if threshold is not None
        else min(1.0, max(negative_scores, default=0.5) + 1e-9)
    )
    accepted = {
        paint: [item for item in proposals if item["position_score"] >= cutoff]
        for paint, proposals in by_paint.items()
    }

    def hit(item: Mapping[str, Any]) -> bool:
        return any(
            _matches(proposal["bbox"], item["bbox"])
            for proposal in accepted.get(str(item["paint_label"]), ())
        )

    return ({
        "threshold": cutoff,
        "semantic_candidate_count": sum(len(items) for items in by_paint.values()),
        "corroborated_candidate_count": sum(len(items) for items in accepted.values()),
        "positive_copy_hits": sum(hit(item) for item in positives),
        "positive_copy_total": len(positives),
        "hard_negative_hits": sum(hit(item) for item in negatives),
        "hard_negative_total": len(negatives),
        "maximum_matching_negative_score": max(negative_scores, default=None),
    }, cutoff)


def _export(model: Any, threshold: float, output: Path) -> None:
    offsets = [0]
    left: list[int] = []
    right: list[int] = []
    split_feature: list[int] = []
    split_threshold: list[float] = []
    positive: list[float] = []
    for estimator in model.estimators_:
        tree = estimator.tree_
        base = offsets[-1]
        left.extend(int(value + base) if value >= 0 else -1 for value in tree.children_left)
        right.extend(int(value + base) if value >= 0 else -1 for value in tree.children_right)
        split_feature.extend(int(value) for value in tree.feature)
        split_threshold.extend(float(value) for value in tree.threshold)
        for values in tree.value[:, 0, :]:
            total = float(np.sum(values))
            positive.append(float(values[1] / total) if total else 0.0)
        offsets.append(base + int(tree.node_count))
    metadata = {
        "schema": "smart-tga-number-context-position-extra-trees-v1",
        "version": "cycle699-dlm-context-position-v1",
        "decision_threshold": float(threshold),
        "tree_count": len(model.estimators_),
        "train_cycles": list(range(683, 691)),
        "full_population_calibration_cycles": [693],
        "canary_cycles_excluded": [695],
        "role": "corroboration_only",
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        metadata_json=np.asarray(json.dumps(metadata), dtype=np.str_),
        feature_names=np.asarray(POSITION_FEATURE_NAMES, dtype=np.str_),
        tree_offsets=np.asarray(offsets, dtype=np.int32),
        children_left=np.asarray(left, dtype=np.int32),
        children_right=np.asarray(right, dtype=np.int32),
        split_feature=np.asarray(split_feature, dtype=np.int32),
        split_threshold=np.asarray(split_threshold, dtype=np.float64),
        positive_probability=np.asarray(positive, dtype=np.float64),
    )


def run(
    labels_dir: Path, prototype_path: Path, calibration_inspection: Path,
    canary_inspection: Path, model_output: Path,
) -> dict[str, Any]:
    from sklearn.ensemble import ExtraTreesClassifier

    prototypes = _read(prototype_path)["prototypes"]
    train = _build_split(labels_dir, list(range(683, 691)), prototypes)["records"]
    matrix = np.stack([_vector(item["proposal"]) for item in train])
    labels = np.asarray([int(item["label"]) for item in train], dtype=np.int8)
    model = ExtraTreesClassifier(
        n_estimators=700, min_samples_leaf=2, max_features=None,
        class_weight="balanced", random_state=697, n_jobs=-1,
    ).fit(matrix, labels)
    calibration, threshold = _runtime_metrics(
        model, _read(calibration_inspection), labels_dir, 693,
    )
    canary, _ = _runtime_metrics(
        model, _read(canary_inspection), labels_dir, 695, threshold=threshold,
    )
    _export(model, threshold, model_output)
    return {
        "schema": "smart-tga-number-context-position-probe-v1",
        "train_sample_count": len(train),
        "train_positive_count": int(np.count_nonzero(labels == 1)),
        "train_negative_count": int(np.count_nonzero(labels == 0)),
        "feature_names": list(POSITION_FEATURE_NAMES),
        "calibration_cycle693": calibration,
        "untouched_canary_cycle695": canary,
        "model_output": str(model_output).replace("\\", "/"),
        "casts_votes": False,
        "ownership_authority": False,
        "adds_pixels": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels-dir", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--prototype", type=Path, default=Path(
        "engine/spec_sculpt/models/smart_tga_number_context_cycle696_v1.json"
    ))
    parser.add_argument("--calibration-inspection", type=Path, required=True)
    parser.add_argument("--canary-inspection", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(
        args.labels_dir, args.prototype, args.calibration_inspection,
        args.canary_inspection, args.model_output,
    )
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
