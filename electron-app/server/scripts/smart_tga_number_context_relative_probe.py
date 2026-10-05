"""Train a palette-relative pixel scorer and evaluate paint-disjoint DLM holdouts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image

try:
    from engine.spec_sculpt.decal_instances import decode_instance_mask_rle
    from engine.spec_sculpt.number_context_relative_pixels import FEATURE_NAMES, relative_pixel_feature_cube
    from scripts.smart_tga_number_context_pixel_probe import _records as _legacy_records
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from engine.spec_sculpt.decal_instances import decode_instance_mask_rle  # type: ignore
    from engine.spec_sculpt.number_context_relative_pixels import FEATURE_NAMES, relative_pixel_feature_cube  # type: ignore
    from scripts.smart_tga_number_context_pixel_probe import _records as _legacy_records  # type: ignore


def _load_new(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for item in data["records"]:
        records.append({
            **item,
            "rgb": np.asarray(Image.open(item["source_1024"]).convert("RGB")),
            "label_mask": decode_instance_mask_rle(item["label_mask_rle"]),
            "hypotheses": {
                name: decode_instance_mask_rle(rle)
                for name, rle in item["hypothesis_masks"].items()
            },
        })
    return records


def _sample(record: Mapping[str, Any], rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    cube = relative_pixel_feature_cube(record["rgb"], record["proposal_bbox"], record["hypotheses"])
    label = np.asarray(record["label_mask"], bool)
    union = np.logical_or.reduce(list(record["hypotheses"].values()))
    positive = np.flatnonzero(label.ravel())
    negative = np.flatnonzero((union & ~label).ravel())
    background = np.flatnonzero((~union & ~label).ravel())
    def take(values: np.ndarray, count: int) -> np.ndarray:
        return rng.choice(values, min(count, len(values)), replace=False) if len(values) else values
    indexes = np.concatenate([take(positive, 6000), take(negative, 8000), take(background, 1000)])
    return cube.reshape(-1, cube.shape[2])[indexes], label.ravel()[indexes].astype(np.uint8)


def _fit(matrix: np.ndarray, labels: np.ndarray, seed: int) -> Any:
    from sklearn.ensemble import ExtraTreesClassifier
    return ExtraTreesClassifier(
        n_estimators=220, min_samples_leaf=4, max_features="sqrt",
        class_weight="balanced", random_state=seed, n_jobs=-1,
    ).fit(matrix, labels)


def _evaluate(model: Any, records: Sequence[Mapping[str, Any]], threshold: float) -> dict[str, Any]:
    values = {"positive_pixels": 0, "predicted_pixels": 0, "true_positive_pixels": 0,
              "positive_records": 0, "positive_record_hits": 0, "control_pixels": 0}
    raw_values = {key: 0 for key in values}
    for record in records:
        if record["label_kind"] == "uncertain_excluded":
            continue
        cube = relative_pixel_feature_cube(record["rgb"], record["proposal_bbox"], record["hypotheses"])
        prediction = model.predict_proba(cube.reshape(-1, cube.shape[2]))[:, 1].reshape(cube.shape[:2]) >= threshold
        label = np.asarray(record["label_mask"], bool)
        for target, mask in ((values, prediction), (raw_values, np.asarray(record["hypotheses"]["raw_instance_union"], bool))):
            target["positive_pixels"] += int(np.count_nonzero(label))
            target["predicted_pixels"] += int(np.count_nonzero(mask))
            target["true_positive_pixels"] += int(np.count_nonzero(mask & label))
            if record["label_kind"] == "empty_control":
                target["control_pixels"] += int(np.count_nonzero(mask))
            elif record["label_kind"] == "number_core":
                target["positive_records"] += 1
                target["positive_record_hits"] += int(np.count_nonzero(mask & label) >= 32)
    def finish(item: dict[str, Any]) -> dict[str, Any]:
        item["pixel_precision"] = round(item["true_positive_pixels"] / max(1, item["predicted_pixels"]), 6)
        item["pixel_recall"] = round(item["true_positive_pixels"] / max(1, item["positive_pixels"]), 6)
        return item
    return {"raw_union": finish(raw_values), "relative_scorer": finish(values)}


def run(
    dataset: Path, legacy_queue: Path, legacy_labels: Path,
    legacy_probes: Sequence[Path], output_model: Path,
) -> dict[str, Any]:
    from sklearn.model_selection import GroupKFold
    new_records = _load_new(dataset)
    legacy = _legacy_records(legacy_queue, legacy_labels, legacy_probes)
    for item in legacy:
        item["role"] = "train"
    train_records = [item for item in new_records if item["role"] == "train"] + [
        item for item in legacy if item["label_kind"] != "uncertain_excluded"
    ]
    holdout_records = [item for item in new_records if item["role"] == "holdout"]
    rng = np.random.default_rng(702)
    samples = [_sample(item, rng) for item in train_records]
    matrix = np.concatenate([item[0] for item in samples])
    targets = np.concatenate([item[1] for item in samples])
    groups = np.concatenate([
        np.full(len(sample[1]), item["paint_label"], object)
        for sample, item in zip(samples, train_records)
    ])
    control = np.concatenate([
        np.full(len(sample[1]), item["label_kind"] == "empty_control", bool)
        for sample, item in zip(samples, train_records)
    ])
    heldout = np.zeros(len(targets), np.float32)
    splitter = GroupKFold(n_splits=min(5, len(set(groups))))
    for fold, (train_index, test_index) in enumerate(splitter.split(matrix, targets, groups), 1):
        heldout[test_index] = _fit(matrix[train_index], targets[train_index], 702 + fold).predict_proba(matrix[test_index])[:, 1]
    control_scores = heldout[control & (targets == 0)]
    threshold = min(1.0, float(np.max(control_scores, initial=0.5)) + 1e-7)
    model = _fit(matrix, targets, 702)
    output_model.parent.mkdir(parents=True, exist_ok=True)
    import joblib
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES, "threshold": threshold}, output_model)
    return {
        "schema": "smart-tga-number-context-relative-pixel-probe-v1",
        "train_paint_count": len(set(groups)), "train_record_count": len(train_records),
        "holdout_paints": sorted({item["paint_label"] for item in holdout_records}),
        "holdout_record_count": len(holdout_records), "feature_count": len(FEATURE_NAMES),
        "threshold": threshold, "train_metrics": _evaluate(model, train_records, threshold),
        "paint_disjoint_holdout": _evaluate(model, holdout_records, threshold),
        "runtime_integrated": False, "ownership_authority": False,
        "model_output": str(output_model).replace("\\", "/"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--legacy-queue", type=Path, required=True)
    parser.add_argument("--legacy-labels", type=Path, required=True)
    parser.add_argument("--legacy-probes", nargs="+", type=Path, required=True)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.dataset, args.legacy_queue, args.legacy_labels, args.legacy_probes, args.model_output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
