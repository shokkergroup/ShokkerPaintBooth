"""Cross-fitted proposal abstention plus within-proposal Number pixel ranks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:
    from engine.spec_sculpt.number_context_conformal import (
        PROPOSAL_FEATURE_NAMES, proposal_score_features, select_ranked_pixels,
    )
    from engine.spec_sculpt.number_context_relative_pixels import relative_pixel_feature_cube
    from scripts.smart_tga_number_context_pixel_probe import _records as _legacy_records
    from scripts.smart_tga_number_context_relative_probe import _load_new
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.number_context_conformal import (  # type: ignore
        PROPOSAL_FEATURE_NAMES, proposal_score_features, select_ranked_pixels,
    )
    from engine.spec_sculpt.number_context_relative_pixels import relative_pixel_feature_cube  # type: ignore
    from scripts.smart_tga_number_context_pixel_probe import _records as _legacy_records  # type: ignore
    from scripts.smart_tga_number_context_relative_probe import _load_new  # type: ignore


def _fit_pixel(matrix: np.ndarray, labels: np.ndarray, seed: int) -> Any:
    from sklearn.ensemble import ExtraTreesClassifier
    return ExtraTreesClassifier(
        n_estimators=120, min_samples_leaf=4, max_features="sqrt",
        class_weight="balanced", random_state=seed, n_jobs=-1,
    ).fit(matrix, labels)


def _fit_proposal(matrix: np.ndarray, labels: np.ndarray, seed: int) -> Any:
    from sklearn.ensemble import ExtraTreesClassifier
    return ExtraTreesClassifier(
        n_estimators=600, min_samples_leaf=2, max_features="sqrt",
        class_weight="balanced", random_state=seed, n_jobs=-1,
    ).fit(matrix, labels)


def _sample(record: Mapping[str, Any], rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    cube = relative_pixel_feature_cube(record["rgb"], record["proposal_bbox"], record["hypotheses"])
    label = np.asarray(record["label_mask"], bool)
    union = np.logical_or.reduce(list(record["hypotheses"].values()))
    positive = np.flatnonzero(label.ravel())
    negative = np.flatnonzero((union & ~label).ravel())
    background = np.flatnonzero((~union & ~label).ravel())
    def take(values: np.ndarray, count: int) -> np.ndarray:
        return rng.choice(values, min(count, len(values)), replace=False) if len(values) else values
    indexes = np.concatenate([take(positive, 3500), take(negative, 4500), take(background, 500)])
    return cube.reshape(-1, cube.shape[2])[indexes], label.ravel()[indexes].astype(np.uint8)


def _score(model: Any, record: Mapping[str, Any]) -> np.ndarray:
    cube = relative_pixel_feature_cube(record["rgb"], record["proposal_bbox"], record["hypotheses"])
    return model.predict_proba(cube.reshape(-1, cube.shape[2]))[:, 1].reshape(cube.shape[:2])


def _metrics(
    records: Sequence[Mapping[str, Any]], scores: Sequence[np.ndarray],
    proposal_scores: Sequence[float], gate: float, fraction: float,
) -> dict[str, Any]:
    result = {"positive_pixels": 0, "predicted_pixels": 0, "true_positive_pixels": 0,
              "positive_records": 0, "positive_record_hits": 0, "control_pixels": 0,
              "proposal_accepts": 0}
    raw_result = {key: 0 for key in result}
    for record, pixel_score, proposal_score in zip(records, scores, proposal_scores):
        raw = np.asarray(record["hypotheses"]["raw_instance_union"], bool)
        prediction = (
            select_ranked_pixels(pixel_score, raw, fraction)
            if float(proposal_score) >= float(gate) else np.zeros(raw.shape, bool)
        )
        label = np.asarray(record["label_mask"], bool)
        for target, mask, accepted in (
            (result, prediction, np.any(prediction)), (raw_result, raw, np.any(raw)),
        ):
            target["positive_pixels"] += int(np.count_nonzero(label))
            target["predicted_pixels"] += int(np.count_nonzero(mask))
            target["true_positive_pixels"] += int(np.count_nonzero(mask & label))
            target["proposal_accepts"] += int(accepted)
            if record["label_kind"] == "empty_control":
                target["control_pixels"] += int(np.count_nonzero(mask))
            else:
                target["positive_records"] += 1
                target["positive_record_hits"] += int(np.count_nonzero(mask & label) >= 32)
    def finish(values: dict[str, Any]) -> dict[str, Any]:
        values["pixel_precision"] = round(values["true_positive_pixels"] / max(1, values["predicted_pixels"]), 6)
        values["pixel_recall"] = round(values["true_positive_pixels"] / max(1, values["positive_pixels"]), 6)
        return values
    return {"raw_union": finish(raw_result), "conformal": finish(result)}


def run(
    train_dataset: Path, holdout_dataset: Path, legacy_queue: Path,
    legacy_labels: Path, legacy_probes: Sequence[Path], model_output: Path,
) -> dict[str, Any]:
    from sklearn.model_selection import GroupKFold
    train = [item for item in _load_new(train_dataset) if item["role"] == "train"]
    legacy = _legacy_records(legacy_queue, legacy_labels, legacy_probes)
    train += [item for item in legacy if item["label_kind"] != "uncertain_excluded"]
    holdout = _load_new(holdout_dataset)
    rng = np.random.default_rng(703)
    samples = [_sample(item, rng) for item in train]
    matrix = np.concatenate([item[0] for item in samples])
    labels = np.concatenate([item[1] for item in samples])
    sample_groups = np.concatenate([
        np.full(len(sample[1]), item["paint_label"], object)
        for sample, item in zip(samples, train)
    ])
    record_groups = np.asarray([item["paint_label"] for item in train], object)
    splitter = GroupKFold(n_splits=4)
    fold_models = []
    oof_scores: list[np.ndarray | None] = [None] * len(train)
    for fold, (train_index, test_index) in enumerate(splitter.split(matrix, labels, sample_groups), 1):
        model = _fit_pixel(matrix[train_index], labels[train_index], 703 + fold)
        fold_models.append(model)
        test_paints = set(sample_groups[test_index])
        for index, record in enumerate(train):
            if record["paint_label"] in test_paints:
                oof_scores[index] = _score(model, record)
    if any(item is None for item in oof_scores):
        raise AssertionError("every training record must receive cross-fitted pixel scores")
    pixel_scores = [np.asarray(item) for item in oof_scores]
    proposal_matrix = np.asarray([
        [proposal_score_features(score, item["hypotheses"])[name] for name in PROPOSAL_FEATURE_NAMES]
        for score, item in zip(pixel_scores, train)
    ])
    proposal_labels = np.asarray([item["label_kind"] == "number_core" for item in train], np.uint8)
    proposal_oof = np.zeros(len(train), np.float32)
    proposal_splitter = GroupKFold(n_splits=5)
    for fold, (train_index, test_index) in enumerate(proposal_splitter.split(proposal_matrix, proposal_labels, record_groups), 1):
        proposal_oof[test_index] = _fit_proposal(
            proposal_matrix[train_index], proposal_labels[train_index], 713 + fold,
        ).predict_proba(proposal_matrix[test_index])[:, 1]
    gate = min(1.0, float(np.max(proposal_oof[proposal_labels == 0], initial=0.5)) + 1e-7)
    proposal_model = _fit_proposal(proposal_matrix, proposal_labels, 703)

    best_fraction, best_f1 = 0.0, -1.0
    for fraction in np.linspace(0.10, 1.0, 19):
        metric = _metrics(train, pixel_scores, proposal_oof, gate, float(fraction))["conformal"]
        if metric["control_pixels"]:
            continue
        precision, recall = metric["pixel_precision"], metric["pixel_recall"]
        f1 = 2 * precision * recall / max(1e-9, precision + recall)
        if f1 > best_f1:
            best_fraction, best_f1 = float(fraction), f1

    holdout_scores = []
    for record in holdout:
        holdout_scores.append(np.mean([_score(model, record) for model in fold_models], axis=0))
    holdout_matrix = np.asarray([
        [proposal_score_features(score, item["hypotheses"])[name] for name in PROPOSAL_FEATURE_NAMES]
        for score, item in zip(holdout_scores, holdout)
    ])
    holdout_proposal = proposal_model.predict_proba(holdout_matrix)[:, 1]
    import joblib
    model_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "pixel_ensemble": fold_models, "proposal_model": proposal_model,
        "proposal_feature_names": PROPOSAL_FEATURE_NAMES,
        "proposal_gate": gate, "pixel_fraction": best_fraction,
    }, model_output)
    return {
        "schema": "smart-tga-number-context-conformal-probe-v1",
        "train_paints": len(set(record_groups)), "train_records": len(train),
        "proposal_positive_records": int(np.count_nonzero(proposal_labels)),
        "proposal_control_records": int(np.count_nonzero(proposal_labels == 0)),
        "proposal_gate": gate, "pixel_fraction": best_fraction,
        "cross_fitted_train": _metrics(train, pixel_scores, proposal_oof, gate, best_fraction),
        "paint_disjoint_holdout_paints": sorted({item["paint_label"] for item in holdout}),
        "paint_disjoint_holdout": _metrics(holdout, holdout_scores, holdout_proposal, gate, best_fraction),
        "cross_fitted_proposals": [
            {
                "record_id": item.get("record_id", item.get("proposal_id", "")),
                "paint_label": item["paint_label"],
                "label_kind": item["label_kind"],
                "number_probability": round(float(score), 6),
            }
            for item, score in zip(train, proposal_oof)
        ],
        "holdout_proposal_scores": [round(float(value), 6) for value in holdout_proposal],
        "runtime_integrated": False, "ownership_authority": False,
        "model_output": str(model_output).replace("\\", "/"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-dataset", type=Path, required=True)
    parser.add_argument("--holdout-dataset", type=Path, required=True)
    parser.add_argument("--legacy-queue", type=Path, required=True)
    parser.add_argument("--legacy-labels", type=Path, required=True)
    parser.add_argument("--legacy-probes", nargs="+", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.train_dataset, args.holdout_dataset, args.legacy_queue, args.legacy_labels,
                 args.legacy_probes, args.model_output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
