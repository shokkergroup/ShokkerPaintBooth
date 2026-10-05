"""Measure number-object probability as corroboration for the intrinsic scorer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from engine.spec_sculpt.number_context_component_features import FEATURE_NAMES
    from scripts.smart_tga_number_context_component_corpus_probe import (
        _cycle, _paint_records, _summary,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_component_features import FEATURE_NAMES  # type: ignore
    from scripts.smart_tga_number_context_component_corpus_probe import (  # type: ignore
        _cycle, _paint_records, _summary,
    )


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _fit_probabilities(matrix, truth, groups, c_value):
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler
    output = np.zeros(len(truth), np.float32)
    for train, test in GroupKFold(min(8, len(set(groups)))).split(matrix, truth, groups):
        scaler = StandardScaler().fit(matrix[train])
        model = LogisticRegression(C=c_value, class_weight="balanced", max_iter=4000, random_state=710)
        model.fit(scaler.transform(matrix[train]), truth[train])
        output[test] = model.predict_proba(scaler.transform(matrix[test]))[:, 1]
    return output


def _select(records, matrix, minimum_precision=0.95):
    truth = np.asarray([item["is_number"] for item in records], bool)
    groups = np.asarray([item["paint_label"] for item in records], object)
    candidates = []
    for c_value in (0.03, 0.10, 0.35, 1.0):
        probability = _fit_probabilities(matrix, truth, groups, c_value)
        for threshold in sorted(set(float(value) for value in probability), reverse=True):
            summary = _summary(records, probability >= threshold)
            if summary["component_precision"] >= minimum_precision:
                hits = int(summary["number_record_hits"].split("/")[0])
                candidates.append((hits, -summary["accepted_controls"], -c_value, threshold, c_value, probability, summary))
    if not candidates:
        raise AssertionError("no precision-floor operating point")
    return max(candidates, key=lambda item: item[:3])


def run(label_root: Path, segmentation_metrics: Path, output: Path, model_output: Path) -> dict:
    import joblib
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    model_root = Path("engine/spec_sculpt/models")
    family = np.load(model_root / "smart_tga_number_context_family_cycle704_v1.npz")
    prototypes = np.asarray(family["descriptors"], np.float32)
    prototype_labels = np.asarray(family["labels"], bool)
    pixel_models = joblib.load(model_root / "smart_tga_number_context_conformal_cycle703_v1.joblib")["pixel_ensemble"]
    paths = [path for path in sorted(label_root.glob("cycle*_numbers_v1.json")) if 681 <= _cycle(path) <= 690]
    records = []
    for path in paths:
        records.extend(_paint_records(Path.cwd(), path, prototypes, prototype_labels, pixel_models))
    segment = _read(segmentation_metrics)["cross_fitted_precision_floor"]["scores"]
    segment_scores = {
        (item["paint_label"], int(item["component_index"])): float(item["score"])
        for item in segment
    }
    for item in records:
        item["segment_score"] = segment_scores[(item["paint_label"], item["component_index"])]
    train = [item for item in records if item["cycle"] <= 689]
    holdout = [item for item in records if item["cycle"] == 690]
    truth = np.asarray([item["is_number"] for item in train], bool)
    groups = np.asarray([item["paint_label"] for item in train], object)
    intrinsic = np.asarray([item["vector"] for item in train], np.float32)
    fusion = np.column_stack((intrinsic, np.asarray([item["segment_score"] for item in train], np.float32)))
    baseline = _select(train, intrinsic)
    selected = _select(train, fusion)
    _hits, _neg, _c_sort, threshold, c_value, _probability, cross_summary = selected
    scaler = StandardScaler().fit(fusion)
    model = LogisticRegression(C=c_value, class_weight="balanced", max_iter=4000, random_state=710)
    model.fit(scaler.transform(fusion), truth)
    holdout_matrix = np.column_stack((
        np.asarray([item["vector"] for item in holdout], np.float32),
        np.asarray([item["segment_score"] for item in holdout], np.float32),
    ))
    probability = model.predict_proba(scaler.transform(holdout_matrix))[:, 1]
    model_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        model_output,
        feature_names=np.asarray((*FEATURE_NAMES, "number_object_segment_score")),
        mean=scaler.mean_.astype(np.float32), scale=scaler.scale_.astype(np.float32),
        coefficient=model.coef_[0].astype(np.float32),
        intercept=np.asarray([model.intercept_[0]], np.float32),
        threshold=np.asarray([threshold], np.float32),
    )
    payload = {
        "schema": "smart-tga-number-object-fusion-probe-v1",
        "validation": "paint-disjoint stacked cross-fit; segment scores and fusion scores exclude their paint",
        "train_paints": len(set(groups)), "train_records": len(train),
        "holdout_paints": len({item["paint_label"] for item in holdout}), "holdout_records": len(holdout),
        "component_only_cross_fit": baseline[-1],
        "segment_fusion_cross_fit": cross_summary,
        "segment_fusion_holdout_cycle690": _summary(holdout, probability >= threshold),
        "holdout_scores": [
            {"paint_label": item["paint_label"], "component_index": item["component_index"],
             "review_label": item["review_label"], "is_number": item["is_number"],
             "probability": round(float(score), 6), "accepted": bool(score >= threshold)}
            for item, score in zip(holdout, probability)
        ],
        "selected_c": c_value, "selected_threshold": threshold,
        "model_output": str(model_output).replace("\\", "/"),
        "runtime_integrated": False, "ownership_authority": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label-root", type=Path, default=Path("smart_tga_review_labels"))
    parser.add_argument("--segmentation-metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.label_root, args.segmentation_metrics, args.output, args.model_output), indent=2))


if __name__ == "__main__":
    main()
